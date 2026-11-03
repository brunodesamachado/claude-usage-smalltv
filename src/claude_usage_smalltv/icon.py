"""The app icon: a SmallTV with the orange spark on its screen (the .exe and the tray).

Drawn in code at 4x and scaled down, so it stays crisp from 16 px in the tray to 256 px.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from claude_usage_smalltv.render import draw_spark

RGB = tuple[int, int, int]

ORANGE: RGB = (217, 119, 87)
BODY: RGB = (58, 58, 56)
EDGE: RGB = (150, 150, 146)  # light rim: the dark cube stays visible on a dark taskbar
SCREEN: RGB = (12, 12, 12)
RING: RGB = (20, 20, 19)
SUPERSAMPLE = 4


def app_icon(size: int = 64, dot: RGB | None = None) -> Image.Image:
    """The icon on a transparent square; `dot` adds a status light in the bottom-right."""
    s = size * SUPERSAMPLE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin, screen = s * 0.06, s * 0.17
    d.rounded_rectangle(
        (margin, margin, s - margin, s - margin),
        radius=s * 0.16,
        fill=BODY,
        outline=EDGE,
        width=round(s * 0.045),
    )
    bottom = s * 0.80  # the cube's chin under the screen, like the real display
    d.rounded_rectangle((screen, screen, s - screen, bottom), radius=s * 0.05, fill=SCREEN)
    spark = draw_spark(round(s * 0.50), ORANGE)
    top = round(screen + (bottom - screen - spark.height) / 2)
    img.paste(spark, (round((s - spark.width) / 2), top), spark)
    if dot:
        r = s * 0.21
        c = s - r - SUPERSAMPLE
        d.ellipse((c - r, c - r, c + r, c + r), fill=dot, outline=RING, width=s // 24)
    return img.resize((size, size), Image.LANCZOS)
