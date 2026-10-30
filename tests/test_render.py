from datetime import datetime, timedelta, timezone

import pytest

from claude_usage_smalltv.demo import demo_usage
from claude_usage_smalltv.render import Frame, Renderer, Theme, to_jpeg
from claude_usage_smalltv.usage import Window

NOW = datetime(2026, 10, 29, 20, 45, tzinfo=timezone(timedelta(hours=-3)))


@pytest.mark.parametrize("scale", [1, 2])
def test_render_is_square_black_and_scaled(scale):
    img = Renderer(scale=scale).render(Frame(demo_usage(NOW), NOW))
    assert img.size == (240 * scale, 240 * scale)
    assert img.mode == "RGB"
    assert img.getpixel((img.width - 1, img.height // 2)) == (0, 0, 0)


@pytest.mark.parametrize(
    "frame",
    [
        Frame(None, NOW),
        Frame(None, NOW, problem="login"),
        Frame(demo_usage(NOW), NOW, stale_since=NOW - timedelta(minutes=20)),
        Frame(demo_usage(NOW, session=0, weekly=100), NOW),
        Frame(demo_usage(NOW), NOW, ip="192.168.100.200"),
    ],
)
@pytest.mark.parametrize("lang", ["en", "pt"])
def test_every_state_renders(frame, lang):
    assert to_jpeg(Renderer(lang).render(frame))[:2] == b"\xff\xd8"


def test_unknown_language_is_rejected():
    with pytest.raises(ValueError, match="unsupported language"):
        Renderer("xx")


@pytest.mark.parametrize(("pct", "expected"), [(10, "accent"), (70, "warning"), (95, "danger")])
def test_bar_color_follows_thresholds(pct, expected):
    theme = Theme()
    assert theme.level(pct) == getattr(theme, expected)


def test_reset_text_counts_down_within_a_day_and_shows_weekday_beyond():
    r = Renderer("pt")
    soon = Window(5, NOW + timedelta(hours=4, minutes=45))
    later = Window(44, datetime(2026, 11, 2, 19, 0, tzinfo=timezone.utc))
    assert r.reset_text(soon, NOW) == "renova em 4h45 · 01:30"
    assert r.reset_text(later, NOW) == "renova seg 02/11 16:00"
    assert r.reset_text(None, NOW) == "sem janela ativa"
    assert Renderer("en").reset_text(later, NOW) == "resets Mon 11/02 16:00"
