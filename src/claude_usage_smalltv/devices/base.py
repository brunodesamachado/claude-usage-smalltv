"""HTTP plumbing shared by the firmware drivers.

The SmallTV is an ESP8266 on 2.4 GHz Wi-Fi with power saving: replies of several seconds and
dropped connections are normal. Timeouts are generous and connection errors are retried;
HTTP errors (404, 500) are not, because retrying them never helps.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

import requests

PANEL_FILENAME = "claude_usage.jpg"


class DeviceError(RuntimeError):
    """The display could not be reached or rejected a request."""


class DeviceUnreachable(DeviceError):
    """No answer at all: the display is off, asleep or off the network."""


class Device(Protocol):
    firmware: str

    def push(self, jpeg: bytes) -> None:
        """Upload the panel image, overwriting the previous one."""

    def setup(self) -> dict[str, Any]:
        """Make the panel the only thing on screen; return what is needed to undo it."""

    def restore(self, snapshot: dict[str, Any]) -> None:
        """Undo `setup` using the snapshot it returned."""


class HttpDevice:
    def __init__(
        self,
        host: str,
        session: requests.Session | None = None,
        timeout: float = 15,
        retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        self.host = host
        self.base_url = host.rstrip("/") if "://" in host else f"http://{host}"
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

    def get(self, path: str, **params: Any) -> requests.Response:
        return self._request("GET", path, params=params or None)

    def get_json(self, path: str, **params: Any) -> Any:
        try:
            return self.get(path, **params).json()
        except ValueError as exc:
            raise DeviceError(f"{path} did not return JSON") from exc

    def post_file(
        self, path: str, filename: str, data: bytes, content_type: str, **params: Any
    ) -> requests.Response:
        return self._request(
            "POST",
            path,
            params=params or None,
            files_factory=lambda: {"file": (filename, data, content_type)},
            timeout=max(self.timeout, 30),
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        files_factory: Any = None,
        timeout: float | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    files=files_factory() if files_factory else None,
                    timeout=timeout or self.timeout,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last = exc
                if attempt < self.retries:
                    time.sleep(self.retry_delay)
                continue
            if resp.status_code >= 400:
                raise DeviceError(f"{method} {path} returned HTTP {resp.status_code}")
            return resp
        raise DeviceUnreachable(
            f"{method} {path} failed after {self.retries} attempts: {last}"
        ) from last
