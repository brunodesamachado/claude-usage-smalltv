import pytest
import requests
from fakes import FakeResponse, FakeSession

from claude_usage_smalltv.devices import (
    PANEL_FILENAME,
    DeviceError,
    DeviceUnreachable,
    GeekMagicDevice,
    HttpDevice,
    SdProDevice,
    connect,
)
from claude_usage_smalltv.devices import base as devices_base

PHOTOS = {
    "files": [
        {"name": "cat.jpg", "size": 1, "enabled": True},
        {"name": "old.gif", "size": 1, "enabled": False},
        {"name": PANEL_FILENAME, "size": 1, "enabled": True},
    ]
}
THEMES = {"themes": [{"id": 2, "enabled": False}, {"id": 5, "enabled": True}]}
CONFIG = {"theme": 5, "ssid": "home", "password": "wifi-secret"}


def sdpro(routes=None):
    session = FakeSession(
        {
            ("GET", "/photo/list"): PHOTOS,
            ("GET", "/theme/list"): THEMES,
            ("GET", "/config"): CONFIG,
            ("GET", "/photo/toggle"): FakeResponse(200, {}),
            ("GET", "/theme/toggle"): FakeResponse(200, {}),
            ("GET", "/api/set"): FakeResponse(200, {}),
            ("POST", "/photo/upload"): FakeResponse(200, {}),
            **(routes or {}),
        }
    )
    return SdProDevice("10.0.0.9", session=session, retry_delay=0), session


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(devices_base.time, "sleep", lambda _s: None)


def test_sdpro_setup_shows_only_the_panel_and_snapshots_previous_state():
    device, session = sdpro()
    snapshot = device.setup()

    assert snapshot == {
        "photos": {"cat.jpg": True, "old.gif": False},
        "themes": {"2": False, "5": True},
        "theme": 5,
    }
    assert "wifi-secret" not in str(snapshot)
    calls = session.paths()
    assert ("/photo/toggle", {"name": "cat.jpg", "state": 0}) in calls
    assert ("/photo/toggle", {"name": PANEL_FILENAME, "state": 1}) in calls
    # Photo theme must be enabled before the others are disabled.
    assert calls.index(("/theme/toggle", {"id": 2, "state": 1})) < calls.index(
        ("/theme/toggle", {"id": 5, "state": 0})
    )
    assert calls[-1] == ("/api/set", {"key": "theme", "value": 2})


def test_sdpro_setup_requires_a_pushed_frame():
    device, _ = sdpro({("GET", "/photo/list"): {"files": [{"name": "cat.jpg"}]}})
    with pytest.raises(DeviceError, match="push a frame first"):
        device.setup()


def test_sdpro_restore_replays_snapshot():
    device, session = sdpro()
    device.restore({"photos": {"cat.jpg": True}, "themes": {"2": False, "5": True}, "theme": 5})
    calls = session.paths()
    assert ("/photo/toggle", {"name": "cat.jpg", "state": 1}) in calls
    assert ("/photo/toggle", {"name": PANEL_FILENAME, "state": 0}) in calls
    assert calls.index(("/theme/toggle", {"id": 5, "state": 1})) < calls.index(
        ("/theme/toggle", {"id": 2, "state": 0})
    )
    assert calls[-1] == ("/api/set", {"key": "theme", "value": 5})


def test_push_uploads_jpeg_to_the_firmware_specific_endpoint():
    device, session = sdpro()
    device.push(b"\xff\xd8jpeg")
    assert session.paths("POST") == [("/photo/upload", None)]

    stock = GeekMagicDevice("10.0.0.9", session=FakeSession({("POST", "/doUpload"): {}}))
    stock.push(b"\xff\xd8jpeg")
    assert stock.session.paths("POST") == [("/doUpload", {"dir": "/image/"})]


def test_connection_errors_are_retried_but_http_errors_are_not():
    attempts = []

    def flaky(_params):
        attempts.append(1)
        if len(attempts) < 3:
            raise requests.ConnectionError("asleep")
        return FakeResponse(200, {"ok": True})

    dev = HttpDevice("x", session=FakeSession({("GET", "/a"): flaky}), retry_delay=0)
    assert dev.get_json("/a") == {"ok": True}
    assert len(attempts) == 3

    dev = HttpDevice("x", session=FakeSession({("GET", "/b"): FakeResponse(404)}), retry_delay=0)
    with pytest.raises(DeviceError, match="404"):
        dev.get("/b")
    assert len(dev.session.calls) == 1


def test_connect_picks_driver_by_probing(monkeypatch):
    sd_routes = {("GET", "/photo/list"): PHOTOS}
    stock_routes = {("GET", "/app.json"): {"theme": 1}}
    for routes, expected in ((sd_routes, SdProDevice), (stock_routes, GeekMagicDevice)):
        session = FakeSession(routes)
        monkeypatch.setattr(devices_base.requests, "Session", lambda s=session: s)
        assert isinstance(connect("10.0.0.9"), expected)

    monkeypatch.setattr(devices_base.requests, "Session", lambda: FakeSession())
    with pytest.raises(DeviceError, match="not supported"):
        connect("10.0.0.9")


def unreachable_session() -> FakeSession:
    down = requests.ConnectTimeout("timed out")
    return FakeSession({("GET", "/photo/list"): down, ("GET", "/app.json"): down})


def test_connect_tells_an_unreachable_display_from_an_unsupported_one(monkeypatch):
    monkeypatch.setattr(devices_base.requests, "Session", unreachable_session)
    with pytest.raises(DeviceUnreachable, match="not answering") as caught:
        connect("10.0.0.9")
    assert "not supported" not in str(caught.value)
