"""Start the service at logon: Task Scheduler on Windows, launchd on macOS, systemd on Linux.

Enabling only registers the service for the *next* logon; it never starts a second copy next
to the one already running (both would fight over the display and the web port).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from xml.sax.saxutils import escape

from claude_usage_smalltv.paths import APP_NAME

LAUNCHD_LABEL = "dev.claude-usage-smalltv"

Runner = Callable[[Sequence[str]], int]


class AutostartError(RuntimeError):
    """The operating system refused to register or remove the logon entry."""


def _run(cmd: Sequence[str]) -> int:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        list(cmd), capture_output=True, timeout=30, creationflags=flags
    ).returncode


def launch_command() -> list[str]:
    """The command that starts this same installation of the service, without a console."""
    if getattr(sys, "frozen", False):  # packaged .exe / app
        return [sys.executable, "run"]
    python = Path(sys.executable)
    if sys.platform == "win32" and python.with_name("pythonw.exe").is_file():
        python = python.with_name("pythonw.exe")
    return [str(python), "-m", "claude_usage_smalltv", "run"]


def _quote_windows(args: Sequence[str]) -> str:
    return subprocess.list2cmdline(list(args))


def windows_task_xml(command: Sequence[str], user: str) -> str:
    user, program, arguments = escape(user), escape(command[0]), escape(_quote_windows(command[1:]))
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Claude usage on a GeekMagic SmallTV</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled><UserId>{user}</UserId></LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>{program}</Command><Arguments>{arguments}</Arguments></Exec>
  </Actions>
</Task>
"""


def launchd_plist(command: Sequence[str], log_file: Path) -> str:
    args = "\n".join(f"    <string>{escape(a)}</string>" for a in command)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
{args}
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardErrorPath</key><string>{escape(str(log_file))}</string>
</dict>
</plist>
"""


def systemd_unit(command: Sequence[str]) -> str:
    exec_start = " ".join(f'"{a}"' if " " in a else a for a in command)
    return f"""[Unit]
Description=Claude usage on GeekMagic SmallTV
After=network-online.target

[Service]
ExecStart={exec_start}
Restart=always
RestartSec=60

[Install]
WantedBy=default.target
"""


class Autostart:
    def __init__(
        self,
        platform: str = sys.platform,
        home: Path | None = None,
        run: Runner = _run,
        command: Callable[[], list[str]] = launch_command,
    ) -> None:
        self.platform = platform
        self.home = home or Path.home()
        self._run = run
        self._command = command

    @property
    def supported(self) -> bool:
        return self.platform in ("win32", "darwin") or self.platform.startswith("linux")

    @property
    def _plist(self) -> Path:
        return self.home / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"

    @property
    def _unit(self) -> Path:
        return self.home / ".config" / "systemd" / "user" / f"{APP_NAME}.service"

    def is_enabled(self) -> bool:
        if self.platform == "win32":
            return self._run(["schtasks", "/Query", "/TN", APP_NAME]) == 0
        if self.platform == "darwin":
            return self._plist.is_file()
        return self._unit.is_file()

    def enable(self) -> None:
        command = self._command()
        if self.platform == "win32":
            user = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"
            with tempfile.TemporaryDirectory() as tmp:
                xml = Path(tmp) / "task.xml"
                xml.write_text(windows_task_xml(command, user), encoding="utf-16")
                self._check(["schtasks", "/Create", "/TN", APP_NAME, "/XML", str(xml), "/F"])
        elif self.platform == "darwin":
            self._plist.parent.mkdir(parents=True, exist_ok=True)
            log_file = self.home / "Library" / "Logs" / f"{APP_NAME}.log"
            self._plist.write_text(launchd_plist(command, log_file), encoding="utf-8")
        else:
            self._unit.parent.mkdir(parents=True, exist_ok=True)
            self._unit.write_text(systemd_unit(command), encoding="utf-8")
            self._check(["systemctl", "--user", "daemon-reload"])
            self._check(["systemctl", "--user", "enable", f"{APP_NAME}.service"])

    def disable(self) -> None:
        if self.platform == "win32":
            if self.is_enabled():
                self._check(["schtasks", "/Delete", "/TN", APP_NAME, "/F"])
        elif self.platform == "darwin":
            self._plist.unlink(missing_ok=True)
        else:
            if self._unit.is_file():
                self._run(["systemctl", "--user", "disable", f"{APP_NAME}.service"])
                self._unit.unlink()
                self._run(["systemctl", "--user", "daemon-reload"])

    def _check(self, cmd: Sequence[str]) -> None:
        try:
            code = self._run(cmd)
        except (OSError, subprocess.SubprocessError) as exc:
            raise AutostartError(f"could not run {cmd[0]}: {exc}") from exc
        if code != 0:
            raise AutostartError(f"{' '.join(cmd[:2])} failed with exit code {code}")
