from datetime import datetime

import pytest

from claude_usage_smalltv.credentials import CredentialsError
from claude_usage_smalltv.daemon import Daemon
from claude_usage_smalltv.demo import demo_usage
from claude_usage_smalltv.devices import DeviceError
from claude_usage_smalltv.render import Renderer
from claude_usage_smalltv.usage import RateLimited


class Clock:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t


class FakeClient:
    def __init__(self, *outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def fetch(self):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeDevice:
    firmware = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.frames: list[bytes] = []
        self.fail = fail

    def push(self, jpeg: bytes) -> None:
        if self.fail:
            raise DeviceError("asleep")
        self.frames.append(jpeg)


USAGE = demo_usage(datetime.now().astimezone())


def make(client, device=None, **kw):
    clock = Clock()
    daemon = Daemon(device or FakeDevice(), client, Renderer(), clock=clock, **kw)
    return daemon, clock


def test_frames_every_tick_but_usage_only_every_usage_interval():
    client = FakeClient(USAGE)
    daemon, clock = make(client, usage_interval=300)
    for _ in range(5):  # 4 minutes of ticks
        daemon.tick()
        clock.t += 60
    assert client.calls == 1
    assert len(daemon.device.frames) == 5
    daemon.tick()  # minute 5: due again
    assert client.calls == 2


def test_rate_limit_backs_off_exponentially_and_honours_retry_after():
    client = FakeClient(RateLimited(None), RateLimited(None), RateLimited(5000))
    daemon, clock = make(client, usage_interval=300, max_backoff=1800)
    daemon.tick()
    assert daemon.next_fetch - clock.t == 600
    clock.t = daemon.next_fetch
    daemon.tick()
    assert daemon.next_fetch - clock.t == 1200
    clock.t = daemon.next_fetch
    daemon.tick()
    assert daemon.next_fetch - clock.t == 5000  # server asked for longer than our cap


def test_backoff_resets_after_a_success():
    client = FakeClient(RateLimited(None), USAGE)
    daemon, clock = make(client, usage_interval=300)
    daemon.tick()
    clock.t = daemon.next_fetch
    daemon.tick()
    assert daemon.usage is USAGE
    assert daemon.next_fetch - clock.t == 300


def test_old_data_is_flagged_stale_instead_of_dropped():
    client = FakeClient(USAGE, RateLimited(None))
    daemon, clock = make(client, usage_interval=300, stale_after=900)
    daemon.tick()
    clock.t += 1000
    daemon.tick()
    frame = daemon.frame(clock.t)
    assert frame.usage is USAGE
    assert frame.stale_since is not None
    assert frame.problem is None


@pytest.mark.parametrize(
    ("error", "problem"), [(CredentialsError("no login"), "login"), (OSError("dns"), "usage")]
)
def test_errors_without_cached_data_show_a_problem(error, problem):
    daemon, clock = make(FakeClient(error))
    daemon.tick()
    assert daemon.frame(clock.t).problem == problem
    assert daemon.next_fetch - clock.t == 60  # retried on the next frame


def test_display_errors_do_not_stop_the_loop():
    daemon, _ = make(FakeClient(USAGE), device=FakeDevice(fail=True))
    daemon.tick()  # must not raise
    assert daemon.usage is USAGE
