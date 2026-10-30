"""Saved settings, so the service starts with no arguments: which display and which language."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from claude_usage_smalltv.paths import state_dir

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    host: str | None = None  # None until a display is set up
    lang: str = "en"
    usage_interval: int = 300
    show_ip: bool = False  # print the display's IP on the panel, small, under the logo


def config_file() -> Path:
    return state_dir() / "config.json"


def load_config(path: Path | None = None) -> Config:
    path = path or config_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Config()
    except (OSError, ValueError) as exc:
        log.warning("ignoring unreadable %s: %s", path, exc)
        return Config()
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in raw.items() if k in known})


def save_config(config: Config, path: Path | None = None) -> None:
    path = path or config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    os.replace(tmp, path)  # atomic: a crash never leaves a half-written file
