"""Test doubles: a scripted HTTP session so no test touches the network."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeResponse:
    status_code: int = 200
    payload: Any = None
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        if self.payload is None:
            raise ValueError("no JSON body")
        return self.payload

    @property
    def text(self) -> str:
        return json.dumps(self.payload) if self.payload is not None else ""


class FakeSession:
    """Answers by (method, path) and records every call; unknown routes return 404."""

    def __init__(self, routes: dict[tuple[str, str], Any] | None = None) -> None:
        self.routes = dict(routes or {})
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.headers: list[dict[str, str]] = []

    def request(self, method: str, url: str, params=None, files=None, timeout=None):
        path = "/" + url.split("://", 1)[-1].split("/", 1)[-1]
        self.calls.append((method, path, params))
        answer = self.routes.get((method, path), FakeResponse(404))
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            return answer(params)
        return answer if isinstance(answer, FakeResponse) else FakeResponse(200, answer)

    def get(self, url: str, headers=None, timeout=None):
        self.headers.append(dict(headers or {}))
        return self.request("GET", url)

    def paths(self, method: str = "GET") -> list[tuple[str, dict[str, Any] | None]]:
        return [(p, q) for m, p, q in self.calls if m == method]


def sequence(*responses: FakeResponse):
    """Route handler that answers with each response in turn (the last one repeats)."""
    queue = list(responses)

    def answer(_params):
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return answer


USAGE_PAYLOAD = {
    "five_hour": {"utilization": 5.0, "resets_at": "2026-10-30T04:30:00.081072+00:00"},
    "seven_day": {"utilization": 44.0, "resets_at": "2026-11-02T19:00:00.081093+00:00"},
    "seven_day_opus": None,
    "seven_day_breakdown": {
        "rows": [
            {"key": "chat", "display_name": "Chats", "percent": 2},
            {"key": "claude_code", "display_name": "Claude Code", "percent": 98},
            {"key": "cowork", "display_name": "Cowork", "percent": 0},
        ]
    },
}
