"""Made-up usage numbers for `preview --demo`, docs and tests. No login needed."""

from __future__ import annotations

from datetime import datetime, timedelta

from claude_usage_smalltv.usage import Usage, Window


def demo_usage(now: datetime, session: float = 37, weekly: float = 62) -> Usage:
    return Usage(
        session=Window(session, now + timedelta(hours=2, minutes=48)),
        weekly=Window(weekly, now + timedelta(days=3, hours=5)),
        breakdown=(("Claude Code", 81), ("Chats", 19)),
        plan="max",
    )
