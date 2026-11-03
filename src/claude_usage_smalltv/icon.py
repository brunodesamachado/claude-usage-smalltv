"""The pixel mascot used as the app icon: the .exe, the tray and (as SVG) the web page."""

from __future__ import annotations

from PIL import Image, ImageDraw

# 11 x 6 cells: "#" body, "o" eyes. Same drawing as the <svg> in web/index.html.
MASCOT = [
    "..#######..",
    "..#o###o#..",
    "###########",
    "..#######..",
    "..#.#.#.#..",
    "..#.#.#.#..",
]
ORANGE = (217, 119, 87, 255)
EYES = (20, 20, 19, 255)

RGB = tuple[int, int, int]


def mascot(size: int = 64, dot: RGB | None = None) -> Image.Image:
    """The mascot on a transparent square; `dot` adds a status light in the bottom-right."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cell = size // 12
    width, height = len(MASCOT[0]) * cell, len(MASCOT) * cell
    left, top = (size - width) // 2, (size - height) // 2
    if dot:
        top = max(0, top - cell)  # leave room for the light under the legs
    for y, row in enumerate(MASCOT):
        for x, ch in enumerate(row):
            if ch != ".":
                box = (
                    left + x * cell,
                    top + y * cell,
                    left + (x + 1) * cell - 1,
                    top + (y + 1) * cell - 1,
                )
                d.rectangle(box, fill=EYES if ch == "o" else ORANGE)
    if dot:
        r = size * 0.21
        cx = cy = size - r - 1
        outline = max(1, size // 24)  # dark ring keeps the light visible on any taskbar
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*dot, 255), outline=EYES, width=outline)
    return img
