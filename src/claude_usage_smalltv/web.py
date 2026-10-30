"""The local web page: a small JSON API plus static files, served on 127.0.0.1 only.

Any website open in the browser can send requests to localhost, so every request must carry
a Host header naming this server (blocks DNS rebinding) and every POST must be JSON from
this page's own origin (a cross-site form or fetch cannot do both without our consent).
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import parse_qs, urlsplit

from claude_usage_smalltv.service import Service, ServiceError

log = logging.getLogger(__name__)

DEFAULT_PORT = 8765
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


def static_file(name: str) -> bytes:
    return resources.files("claude_usage_smalltv").joinpath("web", name).read_bytes()


class Handler(BaseHTTPRequestHandler):
    server_version = "claude-usage-smalltv"

    def __init__(self, *args: Any, service: Service, port: int, **kwargs: Any) -> None:
        self.service = service
        self.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        super().__init__(*args, **kwargs)

    # --------------------------------------------------------------- routing

    def do_GET(self) -> None:
        if not self._trusted_host():
            return
        url = urlsplit(self.path)
        if url.path in STATIC:
            name, content_type = STATIC[url.path]
            self._send(HTTPStatus.OK, static_file(name), content_type)
        elif url.path == "/api/status":
            self._json(HTTPStatus.OK, self.service.status())
        elif url.path == "/api/preview.png":
            lang = parse_qs(url.query).get("lang", [None])[0]
            self._send(HTTPStatus.OK, self.service.preview_png(lang), "image/png")
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._trusted_host() or not self._trusted_post():
            return
        actions = {
            "/api/scan": lambda body: {"hosts": self.service.scan()},
            "/api/test": lambda body: self.service.test(str(body.get("host", ""))),
            "/api/setup": lambda body: self.service.setup(
                str(body.get("host", "")), str(body.get("lang", ""))
            ),
            "/api/restore": lambda body: self.service.restore(),
            "/api/settings": lambda body: self.service.update_settings(
                lang=str(body["lang"]) if "lang" in body else None,
                show_ip=bool(body["show_ip"]) if "show_ip" in body else None,
            ),
            "/api/autostart": lambda body: self.service.set_autostart(bool(body.get("enabled"))),
        }
        action = actions.get(urlsplit(self.path).path)
        if action is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        try:
            self._json(HTTPStatus.OK, action(body))
        except ServiceError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception:
            log.exception("web: %s failed", self.path)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "unexpected error, see log"})

    # ------------------------------------------------------------- safeguards

    def _trusted_host(self) -> bool:
        if self.headers.get("Host") in self.allowed_hosts:
            return True
        self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden host"})
        return False

    def _trusted_post(self) -> bool:
        origin = self.headers.get("Origin")
        json_body = (self.headers.get("Content-Type") or "").startswith("application/json")
        if json_body and (origin is None or urlsplit(origin).netloc in self.allowed_hosts):
            return True
        self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden origin"})
        return False

    # ---------------------------------------------------------------- output

    def _json(self, status: HTTPStatus, payload: Any) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("web: " + format, *args)


class _HTTPServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second process bind a port that is already in use, so a
    # second copy of the service would start silently instead of finding the first one.
    allow_reuse_address = sys.platform != "win32"


class WebServer:
    """Serves the page from a background thread. Raises OSError if the port is taken."""

    def __init__(self, service: Service, port: int = DEFAULT_PORT) -> None:
        handler = partial(Handler, service=service, port=port)
        self.httpd = _HTTPServer(("127.0.0.1", port), handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        if port == 0:  # tests: the real port is only known after binding
            self.httpd.RequestHandlerClass = partial(Handler, service=service, port=self.port)
        self.url = f"http://127.0.0.1:{self.port}/"

    def start(self) -> None:
        threading.Thread(target=self.httpd.serve_forever, name="web", daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
