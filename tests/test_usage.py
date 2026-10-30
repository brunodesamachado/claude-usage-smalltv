import time

import pytest
from fakes import USAGE_PAYLOAD, FakeResponse, FakeSession, sequence

from claude_usage_smalltv.credentials import OAuthToken
from claude_usage_smalltv.usage import RateLimited, UsageClient, UsageError, parse_usage

ROUTE = ("GET", "/api/oauth/usage")


def make_client(session, tokens, renewals):
    queue = list(tokens)

    def load():
        return queue[0]

    def renew():
        renewals.append(1)
        if len(queue) > 1:
            queue.pop(0)

    return UsageClient(session=session, load=load, renew=renew)


def token(value="tok-1", ttl=3600):
    return OAuthToken(value, time.time() + ttl, "pro")


def test_parse_usage_reads_both_windows_and_sorts_breakdown():
    usage = parse_usage(USAGE_PAYLOAD, plan="pro")
    assert usage.session.percent == 5
    assert usage.weekly.percent == 44
    assert usage.weekly.resets_at.utcoffset().total_seconds() == 0
    assert usage.breakdown == (("Claude Code", 98), ("Chats", 2))  # zero rows dropped
    assert usage.plan == "pro"


def test_parse_usage_tolerates_missing_windows():
    usage = parse_usage({"five_hour": None, "seven_day": {"utilization": 3, "resets_at": None}})
    assert usage.session is None
    assert usage.weekly.percent == 3
    assert usage.weekly.resets_at is None
    assert usage.breakdown == ()


def test_fetch_sends_bearer_token_and_beta_header():
    session = FakeSession({ROUTE: USAGE_PAYLOAD})
    usage = make_client(session, [token()], []).fetch()
    assert usage.session.percent == 5
    assert session.headers[0]["Authorization"] == "Bearer tok-1"
    assert session.headers[0]["anthropic-beta"] == "oauth-2025-04-20"


def test_fetch_renews_before_use_when_token_is_about_to_expire():
    session = FakeSession({ROUTE: USAGE_PAYLOAD})
    renewals = []
    make_client(session, [token("old", ttl=30), token("new")], renewals).fetch()
    assert renewals == [1]
    assert session.headers[0]["Authorization"] == "Bearer new"


def test_fetch_renews_and_retries_once_on_401():
    session = FakeSession({ROUTE: sequence(FakeResponse(401), FakeResponse(200, USAGE_PAYLOAD))})
    renewals = []
    usage = make_client(session, [token("old"), token("new")], renewals).fetch()
    assert usage.weekly.percent == 44
    assert renewals == [1]
    assert [h["Authorization"] for h in session.headers] == ["Bearer old", "Bearer new"]


def test_fetch_raises_rate_limited_with_retry_after():
    session = FakeSession({ROUTE: FakeResponse(429, headers={"retry-after": "120"})})
    with pytest.raises(RateLimited) as err:
        make_client(session, [token()], []).fetch()
    assert err.value.retry_after == 120


@pytest.mark.parametrize("response", [FakeResponse(500), FakeResponse(200, None)])
def test_fetch_raises_usage_error_on_bad_answers(response):
    session = FakeSession({ROUTE: response})
    with pytest.raises(UsageError):
        make_client(session, [token()], []).fetch()


def test_token_repr_never_leaks_the_secret():
    assert "s3cret" not in repr(OAuthToken("s3cret", 0))
