from datetime import datetime

import pytest

from claude_usage_smalltv import paths
from claude_usage_smalltv.config import load_config
from claude_usage_smalltv.demo import demo_usage
from claude_usage_smalltv.devices import DeviceError, DeviceUnreachable
from claude_usage_smalltv.service import Service, ServiceError

USAGE = demo_usage(datetime.now().astimezone())


class Clock:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t


class FakeClient:
    def fetch(self):
        return USAGE


class FakeDevice:
    firmware = "fake"

    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.restored = None
        self.fail: Exception | None = None

    def push(self, jpeg: bytes) -> None:
        if self.fail:
            raise self.fail
        self.frames.append(jpeg)

    def setup(self):
        return {"theme": 5}

    def restore(self, snapshot):
        self.restored = snapshot


class Connector:
    """Answers each connect() with the next outcome (the last one repeats)."""

    def __init__(self, *outcomes) -> None:
        self.outcomes = list(outcomes)
        self.hosts: list[str] = []

    def __call__(self, host: str):
        self.hosts.append(host)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeAutostart:
    supported = True

    def __init__(self) -> None:
        self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@pytest.fixture(autouse=True)
def state_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "state_dir", lambda: tmp_path)
    return tmp_path


def make(tmp_path, connector, host=None):
    config = tmp_path / "config.json"
    if host:
        config.write_text(f'{{"host": "{host}"}}', encoding="utf-8")
    clock = Clock()
    service = Service(
        config_path=config,
        client=FakeClient(),
        connector=connector,
        autostart=FakeAutostart(),
        clock=clock,
    )
    return service, clock


def test_without_a_display_usage_is_still_fetched_for_the_page(tmp_path):
    connector = Connector(AssertionError("must not connect"))
    service, _ = make(tmp_path, connector)
    service.step()
    status = service.status()
    assert not status["configured"]
    assert status["display"]["state"] == "none"
    assert status["usage"]["session"]["percent"] == USAGE.session.percent
    assert connector.hosts == []


def test_an_unreachable_display_is_retried_every_minute_until_it_answers(tmp_path):
    device = FakeDevice()
    connector = Connector(DeviceUnreachable("off"), device)
    service, clock = make(tmp_path, connector, host="10.0.0.9")

    service.step()
    assert service.status()["display"]["state"] == "offline"
    assert service.daemon.usage is USAGE  # fetched first: a slow probe never delays the page
    service.step()  # same minute: no new probe
    assert connector.hosts == ["10.0.0.9"]

    clock.t += 60
    service.step()
    assert service.status()["display"]["state"] == "online"
    assert len(device.frames) == 1


def test_an_unknown_firmware_is_reported_as_unsupported(tmp_path):
    service, _ = make(tmp_path, Connector(DeviceError("not supported")), host="10.0.0.9")
    service.step()
    assert service.status()["display"]["state"] == "unsupported"


def test_a_display_lost_mid_run_goes_back_to_reconnecting(tmp_path):
    device = FakeDevice()
    connector = Connector(device)
    service, clock = make(tmp_path, connector, host="10.0.0.9")
    service.step()
    device.fail = DeviceUnreachable("gone")
    clock.t += 60
    service.step()
    assert service.daemon.device is None
    assert service.status()["display"]["state"] == "offline"


def test_setup_saves_the_display_and_takes_over_at_once(tmp_path, state_dir):
    device = FakeDevice()
    service, _ = make(tmp_path, Connector(device))
    result = service.setup(" http://10.0.0.9/ ", "pt")

    assert result == {"ok": True, "firmware": "fake", "backup_created": True}
    saved = load_config(tmp_path / "config.json")
    assert (saved.host, saved.lang) == ("10.0.0.9", "pt")
    assert (state_dir / "backup-10.0.0.9.json").is_file()
    assert service.daemon.device is device
    assert len(device.frames) == 1  # first frame uploaded before switching the theme


def test_restore_hands_the_display_back_and_forgets_it(tmp_path, state_dir):
    device = FakeDevice()
    service, _ = make(tmp_path, Connector(device))
    service.setup("10.0.0.9", "en")
    assert service.restore() == {"ok": True, "restored": True}
    assert device.restored == {"theme": 5}
    assert load_config(tmp_path / "config.json").host is None
    assert not (state_dir / "backup-10.0.0.9.json").exists()
    assert service.daemon.device is None


def test_test_explains_why_a_display_cannot_be_used(tmp_path):
    service, _ = make(tmp_path, Connector(DeviceUnreachable("off")))
    assert service.test("10.0.0.9") == {"ok": False, "reason": "unreachable", "host": "10.0.0.9"}
    service, _ = make(tmp_path, Connector(DeviceError("unknown")))
    assert service.test("10.0.0.9")["reason"] == "unsupported"
    service, _ = make(tmp_path, Connector(FakeDevice()))
    assert service.test("10.0.0.9") == {"ok": True, "host": "10.0.0.9", "firmware": "fake"}


@pytest.mark.parametrize("bad", ["", "   ", "10.0.0.9/admin", "user@10.0.0.9", "a b"])
def test_host_input_is_validated(tmp_path, bad):
    service, _ = make(tmp_path, Connector(FakeDevice()))
    with pytest.raises(ServiceError):
        service.test(bad)


def test_the_ip_is_drawn_on_the_panel_only_when_asked(tmp_path):
    service, clock = make(tmp_path, Connector(FakeDevice()), host="10.0.0.9")
    assert service.daemon.frame(clock.t).ip is None
    service.update_settings(show_ip=True)
    assert service.daemon.frame(clock.t).ip == "10.0.0.9"
    assert load_config(tmp_path / "config.json").show_ip is True
    assert service.status()["show_ip"] is True


def test_settings_and_autostart_are_applied(tmp_path):
    service, _ = make(tmp_path, Connector(FakeDevice()))
    service.update_settings("pt")
    assert load_config(tmp_path / "config.json").lang == "pt"
    with pytest.raises(ServiceError):
        service.update_settings("klingon")
    assert service.set_autostart(True) == {"ok": True, "enabled": True}
    assert service.status()["autostart"] == {"supported": True, "enabled": True}
