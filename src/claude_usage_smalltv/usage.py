"""Claude plan usage: the 5-hour session window and the weekly window.

Data comes from the endpoint behind Claude Code's `/usage` command. It is undocumented and
rate-limited aggressively (HTTP 429), so poll it sparingly and keep the last good result —
`daemon.Daemon` does exactly that.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from claude_usage_smalltv.credentials import OAuthToken, load_token, renew_token

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
BETA_HEADER = "oauth-2025-04-20"
RENEW_MARGIN_S = 120


class UsageError(RuntimeError):
    """The usage endpoint answered with something we cannot use."""


class RateLimited(UsageError):
    def __init__(self, retry_after: float | None) -> None:
        super().__init__("usage endpoint is rate limiting (HTTP 429)")
        self.retry_after = retry_after


@dataclass(frozen=True)
class Window:
    percent: float
    resets_at: datetime | None


@dataclass(frozen=True)
class Usage:
    session: Window | None
    weekly: Window | None
    breakdown: tuple[tuple[str, int], ...] = ()  # (product, % of weekly use), largest first
    plan: str | None = None


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_window(raw: Any) -> Window | None:
    if not isinstance(raw, dict) or raw.get("utilization") is None:
        return None
    return Window(percent=float(raw["utilization"]), resets_at=_parse_time(raw.get("resets_at")))


def parse_usage(payload: dict[str, Any], plan: str | None = None) -> Usage:
    rows = (payload.get("seven_day_breakdown") or {}).get("rows") or []
    breakdown = sorted(
        ((str(r["display_name"]), int(r["percent"])) for r in rows if r.get("percent")),
        key=lambda item: item[1],
        reverse=True,
    )
    return Usage(
        session=_parse_window(payload.get("five_hour")),
        weekly=_parse_window(payload.get("seven_day")),
        breakdown=tuple(breakdown),
        plan=plan,
    )


def _retry_after(resp: requests.Response) -> float | None:
    try:
        return float(resp.headers.get("retry-after", ""))
    except ValueError:
        return None


class UsageClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        load: Callable[[], OAuthToken] = load_token,
        renew: Callable[[], None] = renew_token,
        timeout: float = 15,
    ) -> None:
        self._http = session or requests.Session()
        self._load = load
        self._renew = renew
        self._timeout = timeout

    def fetch(self) -> Usage:
        token = self._load()
        if token.expires_within(RENEW_MARGIN_S):
            self._renew()
            token = self._load()

        resp = self._get(token)
        if resp.status_code == 401:  # revoked or expired early: renew once and retry
            self._renew()
            token = self._load()
            resp = self._get(token)

        if resp.status_code == 429:
            raise RateLimited(_retry_after(resp))
        if resp.status_code != 200:
            raise UsageError(f"usage endpoint returned HTTP {resp.status_code}")
        try:
            return parse_usage(resp.json(), token.plan)
        except (ValueError, KeyError, TypeError) as exc:
            raise UsageError("usage endpoint returned an unexpected payload") from exc

    def _get(self, token: OAuthToken) -> requests.Response:
        return self._http.get(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {token.access_token}",
                "anthropic-beta": BETA_HEADER,
            },
            timeout=self._timeout,
        )
