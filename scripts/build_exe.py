"""Build the standalone Windows executable: dist/claude-usage-smalltv.exe.

    pip install -e ".[build]"
    python scripts/build_exe.py

One file, no console window, no Python needed on the target machine. Double-clicking it
starts the service and opens the settings page.
"""

from __future__ import annotations

from pathlib import Path

import PyInstaller.__main__
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"

# Same pixel mascot as the web page (web/index.html): 11 x 6 cells, "#" body, "o" eyes.
MASCOT = [
    "..#######..",
    "..#o###o#..",
    "###########",
    "..#######..",
    "..#.#.#.#..",
    "..#.#.#.#..",
]
ORANGE, EYES = (217, 119, 87, 255), (20, 20, 19, 255)


def mascot_icon(path: Path, size: int = 256) -> None:
    cell = size // 12
    width, height = len(MASCOT[0]) * cell, len(MASCOT) * cell
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    left, top = (size - width) // 2, (size - height) // 2
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
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def main() -> None:
    icon = BUILD / "icon.ico"
    mascot_icon(icon)
    PyInstaller.__main__.run(
        [
            str(ROOT / "src" / "claude_usage_smalltv" / "__main__.py"),
            "--name=claude-usage-smalltv",
            "--onefile",
            "--noconsole",
            f"--icon={icon}",
            f"--paths={ROOT / 'src'}",
            "--collect-data=claude_usage_smalltv",  # the web page (index.html, app.js, style.css)
            f"--workpath={BUILD / 'pyinstaller'}",
            f"--specpath={BUILD}",
            f"--distpath={ROOT / 'dist'}",
            "--noconfirm",
            "--clean",
        ]
    )


if __name__ == "__main__":
    main()
