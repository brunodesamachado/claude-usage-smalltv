"""Regenerate the images in docs/ from demo data (no login, no device).

    python scripts/generate_assets.py

Outputs:
    docs/preview.png         the panel at 2x
    docs/states.png          normal / near the limit / stale data, side by side
    docs/social-preview.png  1280x640 card for GitHub's social preview and LinkedIn posts
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from claude_usage_smalltv.demo import demo_usage
from claude_usage_smalltv.render import Frame, Renderer, Theme, load_font

DOCS = Path(__file__).resolve().parent.parent / "docs"
NOW = datetime(2026, 10, 29, 14, 32).astimezone()


def preview() -> Image.Image:
    return Renderer("en", scale=2).render(Frame(demo_usage(NOW), NOW))


def states() -> Image.Image:
    renderer = Renderer("en", scale=2)
    frames = [
        Frame(demo_usage(NOW), NOW),
        Frame(demo_usage(NOW, session=93, weekly=78), NOW),
        Frame(demo_usage(NOW), NOW, stale_since=NOW - timedelta(minutes=25)),
    ]
    tiles = [renderer.render(f) for f in frames]
    gap = 24
    w, h = tiles[0].size
    # Transparent gutters read well on both GitHub light and dark themes.
    sheet = Image.new("RGBA", (w * len(tiles) + gap * (len(tiles) - 1), h), (0, 0, 0, 0))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (i * (w + gap), 0))
    return sheet


def rounded(size: tuple[int, int], radius: int, fill: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill)
    return img


def social_preview() -> Image.Image:
    theme = Theme()
    card = Image.new("RGB", (1280, 640), (14, 14, 16))
    d = ImageDraw.Draw(card)

    # The display: a white cube with a black screen, like the SmallTV Ultra.
    body = rounded((440, 470), 36, (236, 236, 232))
    card.paste(body, (90, 85), body)
    screen = preview().resize((380, 380), Image.LANCZOS)
    card.paste(screen, (120, 115))
    d.rounded_rectangle((240, 520, 410, 530), 5, fill=(214, 214, 208))  # stand lip

    x = 600
    d.text((x, 170), "claude-usage-smalltv", font=load_font(54, True), fill=(245, 245, 245))
    d.text(
        (x, 245),
        "Your Claude plan usage, live on your desk.",
        font=load_font(30),
        fill=(170, 170, 170),
    )
    bullets = [
        "5-hour session and weekly limits, plus a clock",
        "Uses your Claude Code login: no cookies, no API keys",
        "Runs on a GeekMagic SmallTV · Python · MIT",
    ]
    for i, text in enumerate(bullets):
        y = 330 + i * 58
        d.ellipse((x, y + 9, x + 14, y + 23), fill=theme.accent)
        d.text((x + 32, y), text, font=load_font(26), fill=(220, 220, 220))
    return card


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    for name, image in {
        "preview.png": preview(),
        "states.png": states(),
        "social-preview.png": social_preview(),
    }.items():
        image.save(DOCS / name, optimize=True)
        print(f"wrote docs/{name} {image.size[0]}x{image.size[1]}")


if __name__ == "__main__":
    main()
