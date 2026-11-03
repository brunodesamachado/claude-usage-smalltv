import json
from datetime import datetime

import pytest

from claude_usage_smalltv import paths
from claude_usage_smalltv.config import load_config
from claude_usage_smalltv.demo import demo_usage
from claude_usage_smalltv.devices import DeviceError, DeviceUnreachable
from claude_usage_smalltv.discovery import Host
from claude_usage_smalltv.service import SEARCH_AFTER_S, SEARCH_EVERY_S, Service, ServiceError

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

    def __init__(self, panel: bool | None = True) -> None:
        self.frames: list[bytes] = []
        self.restored = None
        self.fail: Exception | None = None
        self.panel = panel
        self.setups = 0

    def push(self, jpeg: bytes) -> None:
        if self.fail:
            raise self.fail
        self.frames.append(jpeg)

    def setup(self):
        self.setups += 1
        return {"theme": 5}

    def restore(self, snapshot):
        self.restored = snapshot

    def has_panel(self):
        return self.panel


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


class Network:
    """Connector and scanner for a fake LAN: {ip: FakeDevice or the exception it raises}."""

    def __init__(self, hosts) -> None:
        self.hosts = hosts
        self.scans = 0

    def connect(self, host: str):
        outcome = self.hosts.get(host, DeviceUnreachable("off"))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def scan(self):
        self.scans += 1
        return [
            Host(ip, "Smart Weather Clock")
            for ip, d in self.hosts.items()
            if not isinstance(d, DeviceUnreachable)
        ]


class FakeAutostart:
    supported = True
    platform = "linux"

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


def make(tmp_path, connector, host=None, scanner=lambda: [], **config_values):
    config = tmp_path / "config.json"
    if host:
        config_values["host"] = host
    if config_values:
        config.write_text(json.dumps(config_values), encoding="utf-8")
    clock = Clock()
    service = Service(
        config_path=config,
        client=FakeClient(),
        connector=connector,
        autostart=FakeAutostart(),
        clock=clock,
        scanner=scanner,
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
    assert service.status()["autostart"] == {"supported": True, "enabled": True, "windows": False}


# ------------------------------------------------------------- the display's IP changes


def backup(state_dir, host):
    return state_dir / f"backup-{host}.json"


def test_change_host_follows_the_same_display_without_a_new_setup(tmp_path, state_dir):
    moved = FakeDevice(panel=True)
    service, _ = make(tmp_path, Network({"10.0.0.103": moved}).connect, host="10.0.0.102")
    backup(state_dir, "10.0.0.102").write_text('{"theme": 5}', encoding="utf-8")

    assert service.change_host("10.0.0.103") == {
        "ok": True,
        "host": "10.0.0.103",
        "firmware": "fake",
    }
    assert load_config(tmp_path / "config.json").host == "10.0.0.103"
    assert service.daemon.device is moved
    assert moved.setups == 0  # its photos and theme are already set
    assert backup(state_dir, "10.0.0.103").is_file()  # "give the display back" still works
    assert not backup(state_dir, "10.0.0.102").exists()


def test_change_host_sets_up_a_display_that_lacks_the_panel(tmp_path):
    fresh = FakeDevice(panel=False)
    service, _ = make(tmp_path, Network({"10.0.0.103": fresh}).connect, host="10.0.0.102")
    assert service.change_host("10.0.0.103")["ok"]
    assert fresh.setups == 1 and len(fresh.frames) == 1


def test_change_host_explains_failures_and_keeps_the_old_address(tmp_path):
    network = Network({"10.0.0.50": DeviceError("router")})
    service, _ = make(tmp_path, network.connect, host="10.0.0.102")
    assert service.change_host("10.0.0.103")["reason"] == "unreachable"
    assert service.change_host("10.0.0.50")["reason"] == "unsupported"
    assert load_config(tmp_path / "config.json").host == "10.0.0.102"


def test_a_lost_display_is_found_at_its_new_ip(tmp_path, state_dir):
    ours, other = FakeDevice(panel=True), FakeDevice(panel=False)
    network = Network({"10.0.0.20": other, "10.0.0.103": ours})
    service, clock = make(tmp_path, network.connect, host="10.0.0.102", scanner=network.scan)
    backup(state_dir, "10.0.0.102").write_text('{"theme": 5}', encoding="utf-8")

    service.step()  # first miss: just retry later
    assert network.scans == 0
    clock.t += SEARCH_AFTER_S
    service.step()

    assert network.scans == 1
    assert service.config.host == "10.0.0.103"  # another SmallTV without the panel is skipped
    assert service.daemon.device is ours and len(ours.frames) == 1
    assert backup(state_dir, "10.0.0.103").is_file()
    assert service.status()["display"]["state"] == "online"


def test_another_device_on_the_old_ip_also_starts_a_search(tmp_path):
    ours = FakeDevice(panel=True)
    network = Network({"10.0.0.102": DeviceError("a printer"), "10.0.0.103": ours})
    service, clock = make(tmp_path, network.connect, host="10.0.0.102", scanner=network.scan)
    service.step()
    clock.t += SEARCH_AFTER_S
    service.step()
    assert service.config.host == "10.0.0.103"


def test_searches_are_spaced_out_and_can_be_turned_off(tmp_path):
    network = Network({})
    service, clock = make(tmp_path, network.connect, host="10.0.0.102", scanner=network.scan)
    service.step()
    for _ in range(5):  # 5 more minutes lost: one search only
        clock.t += 60
        service.step()
    assert network.scans == 1
    clock.t += SEARCH_EVERY_S
    service.step()
    assert network.scans == 2

    network = Network({})
    service, clock = make(
        tmp_path, network.connect, host="10.0.0.102", scanner=network.scan, auto_find=False
    )
    for _ in range(20):
        service.step()
        clock.t += 60
    assert network.scans == 0


def test_test_connection_reconnects_at_once(tmp_path):
    device = FakeDevice()
    network = Network({"10.0.0.102": DeviceUnreachable("asleep")})
    service, _ = make(tmp_path, network.connect, host="10.0.0.102", scanner=network.scan)
    service.step()
    assert service.status()["display"]["state"] == "offline"

    network.hosts["10.0.0.102"] = device  # woke up; no need to wait for the next retry
    assert service.test_connection() == {"ok": True, "host": "10.0.0.102", "firmware": "fake"}
    assert service.daemon.device is device


def test_a_failed_test_starts_the_network_search_right_away(tmp_path):
    ours = FakeDevice(panel=True)
    network = Network({"10.0.0.101": ours})
    service, _ = make(tmp_path, network.connect, host="10.0.0.103", scanner=network.scan)
    result = service.test_connection()
    assert result == {
        "ok": False,
        "reason": "unreachable",
        "host": "10.0.0.103",
        "searching": True,
    }
    service.step()  # same minute: no 2-minute wait after a test from the page
    assert network.scans == 1
    assert service.config.host == "10.0.0.101"
