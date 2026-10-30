"""Draw the 240x240 panel: logo, clock, session and weekly meters on a black background.

Coordinates are written for a 240 px canvas and multiplied by `scale`, so the same layout
renders crisp README/social images at 2x or 3x.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from claude_usage_smalltv.usage import Usage, Window

BASE = 240

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    background: RGB = (0, 0, 0)
    accent: RGB = (217, 119, 87)  # Claude orange, #D97757
    warning: RGB = (232, 178, 60)
    danger: RGB = (226, 80, 70)
    text: RGB = (240, 240, 240)
    muted: RGB = (140, 140, 140)
    dim: RGB = (90, 90, 90)
    track: RGB = (38, 38, 38)
    warn_at: float = 70
    danger_at: float = 90

    def level(self, percent: float) -> RGB:
        if percent >= self.danger_at:
            return self.danger
        if percent >= self.warn_at:
            return self.warning
        return self.accent


LABELS: dict[str, dict[str, object]] = {
    "en": {
        "session": "5-hour session",
        "weekly": "Weekly",
        "resets_in": "resets in {h}h{m:02d} · {t}",
        "resets_on": "resets {wd} {md} {t}",
        "month_day": "%m/%d",
        "no_window": "no active window",
        "waiting": "waiting for usage data",
        "stale": "data from {t} · retrying",
        "problem_login": "sign in: run `claude`",
        "problem_usage": "usage unavailable",
        "weekdays": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    },
    "pt": {
        "session": "Sessão 5h",
        "weekly": "Semana",
        "resets_in": "renova em {h}h{m:02d} · {t}",
        "resets_on": "renova {wd} {md} {t}",
        "month_day": "%d/%m",
        "no_window": "sem janela ativa",
        "waiting": "aguardando dados de uso",
        "stale": "dados de {t} · tentando de novo",
        "problem_login": "faça login: rode `claude`",
        "problem_usage": "uso indisponível",
        "weekdays": ("seg", "ter", "qua", "qui", "sex", "sáb", "dom"),
    },
}

FONT_CANDIDATES = {
    False: [
        "arial.ttf",
        "Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
        "segoeui.ttf",
    ],
    True: [
        "arialbd.ttf",
        "Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
        "segoeuib.ttf",
    ],
}


@lru_cache(maxsize=32)
def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


@dataclass(frozen=True)
class Frame:
    """Everything one screen shows. `problem` (red footer) wins over `stale_since` (amber)."""

    usage: Usage | None
    now: datetime
    stale_since: datetime | None = None
    problem: str | None = None  # "login" or "usage"; translated by the renderer


def draw_spark(px: int, color: RGB) -> Image.Image:
    """Rounded starburst in the spirit of the Claude mark, antialiased by 4x supersampling."""
    ss = 4
    s = px * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    lengths = (1.0, 0.80, 0.94, 0.74, 0.98, 0.84, 0.90, 0.72, 1.0, 0.82, 0.95, 0.76)
    w_base, w_tip = s * 0.040, s * 0.068
    for i, k in enumerate(lengths):
        a = 2 * math.pi * i / len(lengths) - math.pi / 2 + 0.12
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux
        r0, r1 = s * 0.05, (c - w_tip - 1) * k  # keeps the rounded tip inside the canvas
        tx, ty = c + ux * r1, c + uy * r1
        d.polygon(
            [
                (c + ux * r0 + nx * w_base, c + uy * r0 + ny * w_base),
                (tx + nx * w_tip, ty + ny * w_tip),
                (tx - nx * w_tip, ty - ny * w_tip),
                (c + ux * r0 - nx * w_base, c + uy * r0 - ny * w_base),
            ],
            fill=color,
        )
        d.ellipse((tx - w_tip, ty - w_tip, tx + w_tip, ty + w_tip), fill=color)
    d.ellipse((c - s * 0.11, c - s * 0.11, c + s * 0.11, c + s * 0.11), fill=color)
    return img.resize((px, px), Image.LANCZOS)


class Renderer:
    def __init__(self, lang: str = "en", theme: Theme | None = None, scale: int = 1) -> None:
        if lang not in LABELS:
            raise ValueError(f"unsupported language {lang!r}; choose one of {sorted(LABELS)}")
        self.labels = LABELS[lang]
        self.theme = theme or Theme()
        self.scale = scale

    def render(self, frame: Frame) -> Image.Image:
        size = BASE * self.scale
        img = Image.new("RGB", (size, size), self.theme.background)
        d = ImageDraw.Draw(img)
        self._header(img, d, frame.now)
        if frame.usage:
            self._meter(d, 100, str(self.labels["session"]), frame.usage.session, frame.now)
            self._meter(d, 162, str(self.labels["weekly"]), frame.usage.weekly, frame.now)
        self._footer(d, frame)
        return img

    # --- layout helpers (all coordinates in 240 px units) -------------------------------

    def _p(self, v: float) -> int:
        return round(v * self.scale)

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(size * self.scale, bold)

    def _weekday(self, dt: datetime) -> str:
        return self.labels["weekdays"][dt.weekday()]  # type: ignore[index]

    def _header(self, img: Image.Image, d: ImageDraw.ImageDraw, now: datetime) -> None:
        t = self.theme
        logo = draw_spark(self._p(46), t.accent)
        img.paste(logo, (self._p(12), self._p(11)), logo)
        d.text(
            (self._p(228), self._p(32)),
            f"{now:%H:%M}",
            font=self._font(42, True),
            fill=t.text,
            anchor="rm",
        )
        date = f"{self._weekday(now)} {now.strftime(str(self.labels['month_day']))}"
        d.text((self._p(228), self._p(60)), date, font=self._font(14), fill=t.muted, anchor="rm")
        d.line(
            (self._p(14), self._p(74), self._p(226), self._p(74)),
            fill=t.track,
            width=max(1, self.scale),
        )

    def _meter(
        self, d: ImageDraw.ImageDraw, y: int, label: str, window: Window | None, now: datetime
    ) -> None:
        t, p = self.theme, self._p
        pct = window.percent if window else 0.0
        d.text((p(14), p(y)), label, font=self._font(15), fill=t.muted, anchor="ls")
        d.text(
            (p(226), p(y + 2)), f"{pct:.0f}%", font=self._font(26, True), fill=t.text, anchor="rs"
        )
        top, height, left, width = y + 8, 12, 14, 212
        d.rounded_rectangle(
            (p(left), p(top), p(left + width), p(top + height)), radius=p(height / 2), fill=t.track
        )
        filled = width * min(max(pct, 0), 100) / 100
        if filled > 0:
            # Never draw a fill narrower than the bar is tall: tiny values become a dot.
            d.rounded_rectangle(
                (p(left), p(top), p(left + max(filled, height)), p(top + height)),
                radius=p(height / 2),
                fill=t.level(pct),
            )
        d.text(
            (p(14), p(top + 18)),
            self.reset_text(window, now),
            font=self._font(13),
            fill=t.muted,
            anchor="lt",
        )

    def _footer(self, d: ImageDraw.ImageDraw, frame: Frame) -> None:
        t = self.theme
        if frame.problem:
            text, color = str(self.labels[f"problem_{frame.problem}"]), t.danger
        elif frame.stale_since:
            text, color = (
                str(self.labels["stale"]).format(t=f"{frame.stale_since:%H:%M}"),
                t.warning,
            )
        elif frame.usage:
            text = " · ".join(f"{name} {pct}%" for name, pct in frame.usage.breakdown[:2])
            color = t.dim
        else:
            text, color = str(self.labels["waiting"]), t.muted
        d.text((self._p(120), self._p(226)), text, font=self._font(12), fill=color, anchor="mm")

    def reset_text(self, window: Window | None, now: datetime) -> str:
        if window is None or window.resets_at is None:
            return str(self.labels["no_window"])
        at = window.resets_at.astimezone(now.tzinfo)
        left = (at - now).total_seconds()
        if left < 24 * 3600:
            h, m = divmod(max(0, int(left // 60)), 60)
            return str(self.labels["resets_in"]).format(h=h, m=m, t=f"{at:%H:%M}")
        md = at.strftime(str(self.labels["month_day"]))
        return str(self.labels["resets_on"]).format(wd=self._weekday(at), md=md, t=f"{at:%H:%M}")


def to_jpeg(img: Image.Image, quality: int = 92) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()
