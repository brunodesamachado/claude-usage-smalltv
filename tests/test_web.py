"""The page's HTTP API, through a real server on an ephemeral localhost port."""

import pytest
import requests
from test_service import Connector, FakeAutostart, FakeClient, FakeDevice

from claude_usage_smalltv import paths
from claude_usage_smalltv.service import Service
from claude_usage_smalltv.web import WebServer


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "state_dir", lambda: tmp_path)
    service = Service(
        config_path=tmp_path / "config.json",
        client=FakeClient(),
        connector=Connector(FakeDevice()),
        autostart=FakeAutostart(),
    )
    web = WebServer(service, port=0)
    web.start()
    yield web, service
    web.close()


def test_serves_the_page_and_status(server):
    web, _ = server
    page = requests.get(web.url, timeout=5)
    assert page.ok and "app.js" in page.text
    assert requests.get(web.url + "app.js", timeout=5).ok
    status = requests.get(web.url + "api/status", timeout=5).json()
    assert status["configured"] is False
    png = requests.get(web.url + "api/preview.png?lang=pt", timeout=5)
    assert png.headers["Content-Type"] == "image/png"
    assert png.content.startswith(b"\x89PNG")


def test_post_actions_change_settings(server):
    web, service = server
    resp = requests.post(web.url + "api/settings", json={"lang": "pt"}, timeout=5)
    assert resp.json() == {"ok": True}
    assert service.config.lang == "pt"
    resp = requests.post(web.url + "api/settings", json={"lang": "xx"}, timeout=5)
    assert resp.status_code == 400
    assert "unsupported language" in resp.json()["error"]


def test_other_websites_cannot_drive_the_service(server):
    web, service = server
    # DNS rebinding: a foreign hostname pointing at 127.0.0.1.
    rebound = requests.get(web.url + "api/status", headers={"Host": "evil.example:8765"}, timeout=5)
    assert rebound.status_code == 403
    # A cross-site form can only send "simple" content types.
    form = requests.post(web.url + "api/settings", data='{"lang": "pt"}', timeout=5)
    assert form.status_code == 403
    # A cross-site fetch carries its own Origin.
    foreign = requests.post(
        web.url + "api/settings",
        json={"lang": "pt"},
        headers={"Origin": "https://evil.example"},
        timeout=5,
    )
    assert foreign.status_code == 403
    assert service.config.lang == "en"
