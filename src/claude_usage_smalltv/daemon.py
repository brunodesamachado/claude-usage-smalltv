"""The update loop: redraw every minute, poll the usage endpoint far less often.

The clock needs a new frame every minute, but the usage endpoint answers HTTP 429 when polled
that often. So usage is cached and refreshed on its own, slower cadence, with exponential
backoff on rate limiting; the last good numbers stay on screen (flagged as stale) meanwhile.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime

import requests

from claude_usage_smalltv.credentials import CredentialsError
from claude_usage_smalltv.devices import Device, DeviceError
from claude_usage_smalltv.render import Frame, Renderer, to_jpeg
from claude_usage_smalltv.usage import RateLimited, Usage, UsageClient, UsageError

log = logging.getLogger(__name__)


def _local(ts: float) -> datetime:
    return datetime.fromtimestamp(ts).astimezone()


class Daemon:
    def __init__(
        self,
        device: Device,
        client: UsageClient,
        renderer: Renderer,
        *,
        frame_interval: float = 60,
        usage_interval: float = 300,
        stale_after: float = 900,
        max_backoff: float = 1800,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.device = device
        self.client = client
        self.renderer = renderer
        self.frame_interval = frame_interval
        self.usage_interval = usage_interval
        self.stale_after = stale_after
        self.max_backoff = max_backoff
        self._clock = clock
        self._sleep = sleep

        self.usage: Usage | None = None
        self.fetched_at: float | None = None
        self.problem: str | None = None
        self.next_fetch = 0.0
        self._backoff = usage_interval

    def tick(self) -> None:
        now = self._clock()
        if now >= self.next_fetch:
            self._refresh(now)
        frame = self.frame(now)
        try:
            self.device.push(to_jpeg(self.renderer.render(frame)))
        except DeviceError as exc:
            log.warning("display: %s", exc)
            return
        log.info("frame pushed%s", self._summary())

    def frame(self, now: float) -> Frame:
        stale = self.fetched_at is not None and now - self.fetched_at > self.stale_after
        return Frame(
            usage=self.usage,
            now=_local(now),
            stale_since=_local(self.fetched_at) if stale and self.fetched_at else None,
            problem=self.problem if self.usage is None else None,
        )

    def run_forever(self) -> None:
        log.info(
            "updating %s every %ss (usage every %ss)",
            self.device.firmware,
            self.frame_interval,
            self.usage_interval,
        )
        while True:
            self.tick()
            # Wake just after the next interval boundary so the clock flips on time.
            self._sleep(self.frame_interval - self._clock() % self.frame_interval + 0.5)

    def _refresh(self, now: float) -> None:
        try:
            self.usage = self.client.fetch()
        except RateLimited as exc:
            self._backoff = min(self._backoff * 2, self.max_backoff)
            delay = max(exc.retry_after or 0, self._backoff)
            self.next_fetch = now + delay
            log.warning("usage: rate limited, next try in %.0fs", delay)
            return
        except CredentialsError as exc:
            self.problem = "login"
            self.next_fetch = now + self.frame_interval
            log.error("usage: %s", exc)
            return
        except (UsageError, requests.RequestException, OSError) as exc:
            self.problem = "usage"
            self.next_fetch = now + self.frame_interval
            log.warning("usage: %s", exc)
            return
        self.fetched_at = now
        self.problem = None
        self._backoff = self.usage_interval
        self.next_fetch = now + self.usage_interval

    def _summary(self) -> str:
        if not self.usage:
            return ""
        parts = []
        if self.usage.session:
            parts.append(f"session {self.usage.session.percent:.0f}%")
        if self.usage.weekly:
            parts.append(f"weekly {self.usage.weekly.percent:.0f}%")
        return f" ({', '.join(parts)})" if parts else ""
