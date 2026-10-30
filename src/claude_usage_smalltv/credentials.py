"""Read the OAuth token that Claude Code stores when you sign in with `claude`.

This module only ever *reads* Claude Code's credential store. Renewing an expired token is
delegated to the official CLI (`claude auth status`), so this tool never writes credentials
and never needs you to copy cookies or API keys around.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

KEYCHAIN_SERVICE = "Claude Code-credentials"  # macOS keeps the token in the login keychain


class CredentialsError(RuntimeError):
    """Claude Code login is missing, unreadable or cannot be renewed."""


@dataclass(frozen=True)
class OAuthToken:
    access_token: str = field(repr=False)
    expires_at: float  # unix seconds
    plan: str | None = None

    def expires_within(self, seconds: float) -> bool:
        return self.expires_at - time.time() < seconds


def claude_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def parse_credentials(raw: str) -> OAuthToken:
    try:
        oauth = json.loads(raw)["claudeAiOauth"]
        return OAuthToken(
            access_token=oauth["accessToken"],
            expires_at=float(oauth.get("expiresAt") or 0) / 1000,
            plan=oauth.get("subscriptionType"),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise CredentialsError("Claude Code credentials have an unexpected format") from exc


def _read_keychain() -> str | None:
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def load_token() -> OAuthToken:
    path = claude_config_dir() / ".credentials.json"
    if path.is_file():
        return parse_credentials(path.read_text(encoding="utf-8"))
    raw = _read_keychain()
    if raw:
        return parse_credentials(raw)
    raise CredentialsError(
        "No Claude Code login found. Install Claude Code and run `claude` once to sign in."
    )


def find_claude_cli() -> str | None:
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        Path.home() / ".local" / "bin" / "claude",
        Path.home() / ".local" / "bin" / "claude.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def renew_token(timeout: float = 60) -> None:
    """Let the official CLI refresh the token; it rewrites Claude Code's credential store."""
    exe = find_claude_cli()
    if exe is None:
        raise CredentialsError("Claude Code token expired and the `claude` CLI was not found")
    # Without CREATE_NO_WINDOW a console window flashes when running under pythonw.
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.run(
            [exe, "auth", "status"], capture_output=True, timeout=timeout, creationflags=flags
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CredentialsError(f"could not run `claude auth status`: {exc}") from exc
