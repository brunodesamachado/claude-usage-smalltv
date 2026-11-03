"""Notification-area (tray) icon on Windows: status at a glance, quick actions and Quit.

A click opens the settings page; right-click shows the menu. The icon carries a status
light and the tooltip shows the usage, refreshed every few seconds from `Service.brief`.
pystray is imported lazily: it is only installed on Windows.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import threading
import webbrowser
from collections.abc import Callable
from typing import Any

from claude_usage_smalltv.icon import RGB, app_icon
from claude_usage_smalltv.service import Service

log = logging.getLogger(__name__)

REFRESH_S = 10
AUTOSTART_REFRESH_S = 300  # asking Task Scheduler spawns a process: not every refresh

GREEN, AMBER, RED, GRAY = (76, 175, 80), (232, 178, 60), (226, 80, 70), (150, 150, 150)

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "app": "Claude Usage SmallTV",
        "usage": "Session {session}% · Weekly {weekly}%",
        "no_usage": "Waiting for usage data",
        "login": "Sign in to Claude Code: run claude",
        "online": "Display up to date ({host})",
        "connecting": "Connecting to the display ({host})",
        "offline": "Display not answering ({host})",
        "searching": "Looking for the display on the network",
        "unsupported": "No supported display at {host}",
        "none": "No display set up yet",
        "open": "Open settings",
        "test": "Test connection",
        "autostart": "Start with Windows",
        "quit": "Quit",
        "test_ok": "The display answered at {host}.",
        "test_fail": "{host} did not answer.",
        "test_searching": "Looking for it on the network now.",
        "moved": "Display found at a new IP: {host}",
        "error": "Something went wrong: {msg}",
    },
    "pt": {
        "app": "Claude Usage SmallTV",
        "usage": "Sessão {session}% · Semana {weekly}%",
        "no_usage": "Aguardando dados de uso",
        "login": "Faça login no Claude Code: rode claude",
        "online": "Display atualizado ({host})",
        "connecting": "Conectando ao display ({host})",
        "offline": "Display não responde ({host})",
        "searching": "Procurando o display na rede",
        "unsupported": "Nenhum display compatível em {host}",
        "none": "Nenhum display configurado",
        "open": "Abrir configurações",
        "test": "Testar conexão",
        "autostart": "Iniciar com o Windows",
        "quit": "Encerrar",
        "test_ok": "O display respondeu em {host}.",
        "test_fail": "{host} não respondeu.",
        "test_searching": "Procurando na rede agora.",
        "moved": "Display encontrado em um novo IP: {host}",
        "error": "Algo deu errado: {msg}",
    },
}


def texts(lang: str) -> dict[str, str]:
    return TEXT.get(lang, TEXT["en"])


def status_light(brief: dict[str, Any]) -> RGB:
    if brief["problem"] == "login" or brief["state"] == "unsupported":
        return RED
    return {"online": GREEN, "none": GRAY, "connecting": GRAY}.get(brief["state"], AMBER)


def display_line(brief: dict[str, Any]) -> str:
    return texts(brief["lang"])[brief["state"]].format(host=brief["host"] or "")


def usage_line(brief: dict[str, Any]) -> str:
    t = texts(brief["lang"])
    if brief["problem"] == "login":
        return t["login"]
    if brief["session"] is None and brief["weekly"] is None:
        return t["no_usage"]
    pct = {k: "-" if brief[k] is None else f"{brief[k]:.0f}" for k in ("session", "weekly")}
    return t["usage"].format(**pct)


def tooltip(brief: dict[str, Any]) -> str:
    text = f"{texts(brief['lang'])['app']}\n{usage_line(brief)}\n{display_line(brief)}"
    return text[:127]  # Windows truncates longer tooltips anyway


class Tray:
    def __init__(self, service: Service, url: str | None, on_quit: Callable[[], None]) -> None:
        self.service = service
        self.url = url
        self.on_quit = on_quit
        self.icon: Any = None
        self._stopped = threading.Event()
        self._brief = service.brief()
        self._autostart = False

    @staticmethod
    def supported() -> bool:
        return sys.platform == "win32" and importlib.util.find_spec("pystray") is not None

    def t(self, key: str) -> str:
        return texts(self._brief["lang"])[key]

    def start(self) -> None:
        import pystray

        item, menu = pystray.MenuItem, pystray.Menu
        self._autostart = self._autostart_enabled()
        self.icon = pystray.Icon(
            "claude-usage-smalltv",
            app_icon(64, status_light(self._brief)),
            tooltip(self._brief),
            menu(
                item(lambda _: display_line(self._brief), None, enabled=False),
                item(lambda _: usage_line(self._brief), None, enabled=False),
                menu.SEPARATOR,
                # default=True: a left click on the icon runs this item.
                item(lambda _: self.t("open"), self._open, default=True, visible=bool(self.url)),
                item(
                    lambda _: self.t("test"),
                    self._test,
                    enabled=lambda _: self._brief["host"] is not None,
                ),
                item(
                    lambda _: self.t("autostart"),
                    self._toggle_autostart,
                    checked=lambda _: self._autostart,
                    visible=self.service.autostart.supported,
                ),
                menu.SEPARATOR,
                item(lambda _: self.t("quit"), self._quit),
            ),
        )
        threading.Thread(target=self.icon.run, name="tray", daemon=True).start()
        threading.Thread(target=self._refresh_loop, name="tray-refresh", daemon=True).start()
        log.info("tray icon ready")

    def stop(self) -> None:
        self._stopped.set()
        if self.icon is not None:
            self.icon.stop()

    # ------------------------------------------------------------------ refresh

    def _refresh_loop(self) -> None:
        light, ticks = status_light(self._brief), 0
        while not self._stopped.wait(REFRESH_S):
            ticks += 1
            try:
                old_host = self._brief["host"]
                self._brief = self.service.brief()
                if ticks * REFRESH_S % AUTOSTART_REFRESH_S == 0:
                    self._autostart = self._autostart_enabled()
                if status_light(self._brief) != light:
                    light = status_light(self._brief)
                    self.icon.icon = app_icon(64, light)
                self.icon.title = tooltip(self._brief)
                self.icon.update_menu()
                moved = old_host and self._brief["host"] not in (None, old_host)
                if moved and self._brief["state"] == "online":
                    self._notify(self.t("moved").format(host=self._brief["host"]))
            except Exception:  # a broken refresh must never take the service down
                log.debug("tray refresh failed", exc_info=True)

    def _autostart_enabled(self) -> bool:
        try:
            auto = self.service.autostart
            return auto.supported and auto.is_enabled()
        except Exception:
            return False

    # ------------------------------------------------------------------ actions

    def _open(self) -> None:
        if self.url:
            webbrowser.open(self.url)

    def _test(self) -> None:
        threading.Thread(target=self._run_test, name="tray-test", daemon=True).start()

    def _run_test(self) -> None:
        try:
            result = self.service.test_connection()
        except Exception as exc:
            self._notify(self.t("error").format(msg=exc))
            return
        if result["ok"]:
            self._notify(self.t("test_ok").format(host=result["host"]))
        else:
            message = self.t("test_fail").format(host=result["host"])
            if result.get("searching"):
                message += " " + self.t("test_searching")
            self._notify(message)

    def _toggle_autostart(self) -> None:
        try:
            self._autostart = self.service.set_autostart(not self._autostart)["enabled"]
        except Exception as exc:
            self._notify(self.t("error").format(msg=exc))
        self.icon.update_menu()

    def _quit(self) -> None:
        log.info("quit from the tray icon")
        self.on_quit()
        self.stop()

    def _notify(self, message: str) -> None:
        try:
            self.icon.notify(message, self.t("app"))
        except Exception:  # notifications can be disabled by the user or by policy
            log.debug("tray notification failed", exc_info=True)
