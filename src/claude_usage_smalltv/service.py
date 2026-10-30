"""The long-running service: keeps the display updated and backs the local web page.

One process does both. The main thread runs the display loop; the web server calls the
actions below from its own threads. `_lock` serialises everything that talks to the display,
so a setup started from the page never interleaves with a frame upload.
"""

from __future__ import annotations

import io
import json
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_usage_smalltv import __version__
from claude_usage_smalltv.autostart import Autostart
from claude_usage_smalltv.config import Config, load_config, save_config
from claude_usage_smalltv.credentials import CredentialsError, load_token
from claude_usage_smalltv.daemon import Daemon
from claude_usage_smalltv.devices import Device, DeviceError, DeviceUnreachable, connect
from claude_usage_smalltv.discovery import scan
from claude_usage_smalltv.paths import backup_file
from claude_usage_smalltv.render import LABELS, Renderer, to_jpeg
from claude_usage_smalltv.usage import UsageClient, Window

log = logging.getLogger(__name__)

RECONNECT_S = 60  # display off or asleep
UNSUPPORTED_RETRY_S = 600  # answered with an unknown firmware: unlikely to change soon


class ServiceError(RuntimeError):
    """An action from the web page cannot be done; the message is shown to the user."""


def install_panel(device: Device, host: str, jpeg: bytes) -> tuple[Path, bool]:
    """Upload a first frame and make it the only thing on screen. Returns (backup, created)."""
    device.push(jpeg)
    snapshot = device.setup()
    path = backup_file(host)
    if path.exists():  # keep the oldest backup: it holds the settings from before any setup
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return path, True


def uninstall_panel(device: Device, host: str) -> bool:
    """Bring back the photos and theme saved by `install_panel`. False if there is no backup."""
    path = backup_file(host)
    if not path.exists():
        return False
    device.restore(json.loads(path.read_text(encoding="utf-8")))
    path.unlink()
    return True


class RecentLog(logging.Handler):
    """Keeps the last messages for the page's activity list (per-minute frame logs excluded)."""

    def __init__(self, size: int = 40) -> None:
        super().__init__(logging.INFO)
        self.records: deque[dict[str, str]] = deque(maxlen=size)

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.endswith(".daemon") and record.levelno < logging.WARNING:
            return
        self.records.append(
            {
                "time": datetime.fromtimestamp(record.created).astimezone().isoformat(),
                "level": record.levelname.lower(),
                "message": record.getMessage(),
            }
        )


def _window(window: Window | None) -> dict[str, Any] | None:
    if window is None:
        return None
    resets = window.resets_at.isoformat() if window.resets_at else None
    return {"percent": round(window.percent, 1), "resets_at": resets}


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts).astimezone().isoformat() if ts else None


class Service:
    def __init__(
        self,
        config_path: Path | None = None,
        client: UsageClient | None = None,
        connector: Callable[[str], Device] = lambda host: connect(host, timeout=10, retries=2),
        autostart: Autostart | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._config_path = config_path
        self.config = load_config(config_path)
        self._connect = connector
        self.autostart = autostart or Autostart()
        self._clock = clock
        self.daemon = Daemon(
            None,
            client or UsageClient(),
            Renderer(self.config.lang),
            usage_interval=self.config.usage_interval,
            clock=clock,
        )
        self.recent = RecentLog()
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._device_host: str | None = None
        self._next_connect = 0.0
        self._connect_state: str | None = None  # "offline" | "unsupported" while unconnected
        self._connect_error: str | None = None
        self._login: tuple[float, dict[str, Any]] | None = None
        self._apply_config()

    # ---------------------------------------------------------------- display loop

    def step(self) -> None:
        with self._lock:
            self._tick()
        # Probing a display that is off takes a while: never hold the lock or delay the usage.
        if self._ensure_device():
            with self._lock:
                self._tick()  # just connected: show the panel now, not in a minute

    def _tick(self) -> None:
        self.daemon.tick()
        if isinstance(self.daemon.display_error, DeviceUnreachable):
            # Went away mid-run: probe it once a minute instead of re-uploading frames.
            error = str(self.daemon.display_error)
            self.daemon.device, self._device_host = None, None
            self.daemon.display_error = None
            self._unconnected("offline", error, self._clock() + RECONNECT_S)

    def run_forever(self) -> None:
        interval = self.daemon.frame_interval
        while not self._stop.is_set():
            self.step()
            # Wake just after the next minute boundary (so the clock flips on time), or at once
            # when the page changed something.
            self._wake.wait(interval - self._clock() % interval + 0.5)
            self._wake.clear()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def wake(self) -> None:
        self._wake.set()

    def _ensure_device(self) -> bool:
        """Connect to the configured display if needed. True when it just got connected."""
        with self._lock:
            host = self.config.host
            if self.daemon.device is not None and host != self._device_host:
                self.daemon.device, self._device_host = None, None  # removed from the page
            if host is None or self.daemon.device is not None:
                return False
            now = self._clock()
            if now < self._next_connect:
                return False
        try:
            device = self._connect(host)
        except DeviceUnreachable as exc:
            self._unconnected("offline", str(exc), now + RECONNECT_S, host)
            return False
        except DeviceError as exc:
            self._unconnected("unsupported", str(exc), now + UNSUPPORTED_RETRY_S, host)
            return False
        with self._lock:
            if self.config.host != host or self.daemon.device is not None:
                return False  # the page set up another display meanwhile
            self.daemon.device, self._device_host = device, host
            self._connect_state = self._connect_error = None
        log.info("connected to %s at %s", device.firmware, host)
        return True

    def _unconnected(
        self, state: str, error: str, retry_at: float, host: str | None = None
    ) -> None:
        with self._lock:
            if host is not None and self.config.host != host:
                return  # stale result for a display that is no longer configured
            if self._connect_state != state:  # log once per change, not every minute
                log.warning("display: %s", error)
            self._connect_state, self._connect_error = state, error
            self._next_connect = retry_at

    # ------------------------------------------------------------------ status

    def status(self) -> dict[str, Any]:
        d = self.daemon
        usage = d.usage
        return {
            "version": __version__,
            "configured": self.config.host is not None,
            "host": self.config.host,
            "lang": self.config.lang,
            "show_ip": self.config.show_ip,
            "languages": sorted(LABELS),
            "display": self._display_status(),
            "login": self._login_status(),
            "usage": {
                "session": _window(usage.session) if usage else None,
                "weekly": _window(usage.weekly) if usage else None,
                "breakdown": list(usage.breakdown) if usage else [],
                "fetched_at": _iso(d.fetched_at),
                "stale": d.frame(self._clock()).stale_since is not None,
                "problem": d.problem,
            },
            "autostart": {
                "supported": self.autostart.supported,
                "enabled": self._autostart_enabled(),
            },
            "activity": list(reversed(self.recent.records)),
        }

    def _display_status(self) -> dict[str, Any]:
        d = self.daemon
        if self.config.host is None:
            state, error = "none", None
        elif d.device is None:
            state, error = self._connect_state or "connecting", self._connect_error
        elif d.display_error:
            state, error = "offline", str(d.display_error)
        else:
            state, error = ("online" if d.pushed_at else "connecting"), None
        return {
            "state": state,
            "error": error,
            "firmware": d.device.firmware if d.device else None,
            "pushed_at": _iso(d.pushed_at),
        }

    def _login_status(self) -> dict[str, Any]:
        now = self._clock()
        if self._login and now - self._login[0] < 30:  # macOS reads the Keychain: cache it
            return self._login[1]
        try:
            token = load_token()
            result = {"ok": True, "plan": token.plan, "error": None}
        except CredentialsError as exc:
            result = {"ok": False, "plan": None, "error": str(exc)}
        if self.daemon.problem == "login":
            result = {**result, "ok": False}
        self._login = (now, result)
        return result

    def _autostart_enabled(self) -> bool:
        try:
            return self.autostart.supported and self.autostart.is_enabled()
        except Exception:  # never let a status poll fail because of the OS scheduler
            log.debug("autostart status unavailable", exc_info=True)
            return False

    def preview_png(self, lang: str | None = None) -> bytes:
        lang = lang if lang in LABELS else self.config.lang
        img = Renderer(lang, scale=2).render(self.daemon.frame(self._clock()))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    # ----------------------------------------------------------------- actions

    def scan(self) -> list[dict[str, Any]]:
        return [{"ip": h.ip, "title": h.title, "smalltv": h.looks_like_smalltv} for h in scan()]

    def test(self, host: str) -> dict[str, Any]:
        host = self._clean_host(host)
        try:
            device = self._connect(host)
        except DeviceUnreachable:
            return {"ok": False, "reason": "unreachable", "host": host}
        except DeviceError:
            return {"ok": False, "reason": "unsupported", "host": host}
        return {"ok": True, "host": host, "firmware": device.firmware}

    def setup(self, host: str, lang: str) -> dict[str, Any]:
        host = self._clean_host(host)
        if lang not in LABELS:
            raise ServiceError(f"unsupported language {lang!r}")
        try:
            device = self._connect(host)
        except DeviceError as exc:
            raise ServiceError(str(exc)) from exc
        with self._lock:
            frame = replace(
                self.daemon.frame(self._clock()), ip=host if self.config.show_ip else None
            )
            try:
                _, created = install_panel(device, host, to_jpeg(Renderer(lang).render(frame)))
            except DeviceError as exc:
                raise ServiceError(str(exc)) from exc
            self._save(replace(self.config, host=host, lang=lang))
            self.daemon.device, self._device_host = device, host
            self._connect_state = self._connect_error = None
        log.info("panel set up on %s at %s", device.firmware, host)
        self.wake()
        return {"ok": True, "firmware": device.firmware, "backup_created": created}

    def restore(self) -> dict[str, Any]:
        host = self.config.host
        if host is None:
            raise ServiceError("no display is set up")
        with self._lock:
            try:
                device = self.daemon.device or self._connect(host)
                restored = uninstall_panel(device, host)
            except DeviceError as exc:
                raise ServiceError(str(exc)) from exc
            self._save(replace(self.config, host=None))
            self.daemon.device, self._device_host = None, None
        log.info("display at %s handed back (previous photos restored: %s)", host, restored)
        return {"ok": True, "restored": restored}

    def update_settings(
        self, lang: str | None = None, show_ip: bool | None = None
    ) -> dict[str, Any]:
        if lang is not None and lang not in LABELS:
            raise ServiceError(f"unsupported language {lang!r}")
        given = (("lang", lang), ("show_ip", show_ip))
        with self._lock:
            self._save(replace(self.config, **{k: v for k, v in given if v is not None}))
        self.wake()
        return {"ok": True}

    def set_autostart(self, enabled: bool) -> dict[str, Any]:
        if not self.autostart.supported:
            raise ServiceError("starting at logon is not supported on this system")
        try:
            self.autostart.enable() if enabled else self.autostart.disable()
        except Exception as exc:
            raise ServiceError(str(exc)) from exc
        log.info("start at logon %s", "enabled" if enabled else "disabled")
        return {"ok": True, "enabled": self._autostart_enabled()}

    def apply_cli(
        self, host: str | None, lang: str | None, usage_interval: int | None = None
    ) -> None:
        """Command-line options win over the saved settings, and are saved too."""
        given = (("host", host), ("lang", lang), ("usage_interval", usage_interval))
        changes = {k: v for k, v in given if v is not None}
        if changes:
            self._save(replace(self.config, **changes))

    def _save(self, config: Config) -> None:
        save_config(config, self._config_path)
        self.config = config
        self._apply_config()

    def _apply_config(self) -> None:
        d = self.daemon
        d.renderer = Renderer(self.config.lang)
        d.usage_interval = self.config.usage_interval
        d.ip_label = self.config.host if self.config.show_ip else None

    @staticmethod
    def _clean_host(host: str) -> str:
        host = (host or "").strip()
        for prefix in ("http://", "https://"):
            host = host.removeprefix(prefix)
        host = host.rstrip("/")
        if not host or any(c.isspace() or c in "/?#@" for c in host):
            raise ServiceError("type the display's IP address, e.g. 192.168.1.50")
        return host
