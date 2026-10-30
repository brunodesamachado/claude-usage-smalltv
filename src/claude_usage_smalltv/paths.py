"""Per-user state directory, without pulling in platformdirs for a single path."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "claude-usage-smalltv"


def state_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / APP_NAME


def backup_file(host: str) -> Path:
    """Where `setup` keeps the device's previous photo/theme settings for `restore`."""
    safe = "".join(c if c.isalnum() or c in ".-" else "_" for c in host)
    return state_dir() / f"backup-{safe}.json"
