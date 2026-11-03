"""Build the standalone Windows executable: dist/claude-usage-smalltv.exe.

    pip install -e ".[build]"
    python scripts/build_exe.py

One file, no console window, no Python needed on the target machine. Double-clicking it
starts the service, puts its icon in the notification area and opens the settings page.
"""

from __future__ import annotations

from pathlib import Path

import PyInstaller.__main__

from claude_usage_smalltv.icon import app_icon

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"


def main() -> None:
    icon = BUILD / "icon.ico"
    icon.parent.mkdir(parents=True, exist_ok=True)
    app_icon(256).save(icon, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    PyInstaller.__main__.run(
        [
            str(ROOT / "src" / "claude_usage_smalltv" / "__main__.py"),
            "--name=claude-usage-smalltv",
            "--onefile",
            "--noconsole",
            f"--icon={icon}",
            f"--paths={ROOT / 'src'}",
            "--collect-data=claude_usage_smalltv",  # the web page (index.html, app.js, style.css)
            "--hidden-import=pystray._win32",  # pystray picks its backend at runtime
            f"--workpath={BUILD / 'pyinstaller'}",
            f"--specpath={BUILD}",
            f"--distpath={ROOT / 'dist'}",
            "--noconfirm",
            "--clean",
        ]
    )


if __name__ == "__main__":
    main()
