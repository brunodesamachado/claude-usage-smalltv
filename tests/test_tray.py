"""Tray texts, status light and actions, with a fake icon (pystray only exists on Windows)."""

from claude_usage_smalltv.icon import mascot
from claude_usage_smalltv.tray import AMBER, GRAY, GREEN, RED, Tray, status_light, tooltip


def brief(**changes):
    base = {
        "state": "online",
        "host": "10.0.0.101",
        "lang": "pt",
        "session": 37.4,
        "weekly": 62.0,
        "problem": None,
    }
    return {**base, **changes}


def test_the_light_follows_the_display_and_login():
    assert status_light(brief()) == GREEN
    assert status_light(brief(state="offline")) == AMBER
    assert status_light(brief(state="searching")) == AMBER
    assert status_light(brief(state="unsupported")) == RED
    assert status_light(brief(problem="login")) == RED
    assert status_light(brief(state="none", host=None)) == GRAY


def test_tooltip_shows_usage_and_display_in_the_panel_language():
    assert tooltip(brief()) == (
        "Claude Usage SmallTV\nSessão 37% · Semana 62%\nDisplay atualizado (10.0.0.101)"
    )
    english = tooltip(brief(lang="en", state="offline", session=None, weekly=None))
    assert english.splitlines()[1:] == [
        "Waiting for usage data",
        "Display not answering (10.0.0.101)",
    ]
    assert len(tooltip(brief(host="x" * 200))) <= 127


def test_the_icon_gets_a_status_light():
    plain, lit = mascot(64), mascot(64, GREEN)
    assert plain.size == lit.size == (64, 64)
    assert plain.getpixel((52, 52))[3] == 0  # transparent corner without a light
    assert lit.getpixel((52, 52))[:3] == GREEN


class FakeIcon:
    def __init__(self) -> None:
        self.notes: list[str] = []
        self.stopped = False

    def notify(self, message, title):
        self.notes.append(message)

    def stop(self):
        self.stopped = True

    def update_menu(self):
        pass


class FakeAutostart:
    supported = True

    def __init__(self) -> None:
        self.enabled = False

    def is_enabled(self):
        return self.enabled


class FakeService:
    def __init__(self, test_result) -> None:
        self.test_result = test_result
        self.autostart = FakeAutostart()
        self.stopped = False

    def brief(self):
        return brief()

    def test_connection(self):
        return self.test_result

    def set_autostart(self, enabled):
        self.autostart.enabled = enabled
        return {"ok": True, "enabled": enabled}


def make(test_result=None):
    quits = []
    service = FakeService(test_result or {"ok": True, "host": "10.0.0.101"})
    tray = Tray(service, "http://127.0.0.1:8765/", on_quit=lambda: quits.append(1))
    tray.icon = FakeIcon()
    return tray, service, quits


def test_test_connection_reports_through_a_notification():
    tray, _, _ = make()
    tray._run_test()
    assert tray.icon.notes == ["O display respondeu em 10.0.0.101."]

    tray, _, _ = make({"ok": False, "host": "10.0.0.101", "searching": True})
    tray._run_test()
    assert tray.icon.notes == ["10.0.0.101 não respondeu. Procurando na rede agora."]


def test_autostart_can_be_toggled_from_the_menu():
    tray, service, _ = make()
    tray._toggle_autostart()
    assert service.autostart.enabled and tray._autostart
    tray._toggle_autostart()
    assert not service.autostart.enabled


def test_quit_stops_the_service_and_the_icon():
    tray, _, quits = make()
    tray._quit()
    assert quits == [1]
    assert tray.icon.stopped
