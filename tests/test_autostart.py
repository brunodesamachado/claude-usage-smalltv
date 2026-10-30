import sys

from claude_usage_smalltv.autostart import Autostart, launch_command

COMMAND = ["C:\\Program Files\\Python\\pythonw.exe", "-m", "claude_usage_smalltv", "run"]


class Runner:
    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.calls: list[list[str]] = []
        self.task_xml = ""

    def __call__(self, cmd):
        cmd = list(cmd)
        self.calls.append(cmd)
        if "/XML" in cmd:  # read before the temporary file is deleted
            with open(cmd[cmd.index("/XML") + 1], encoding="utf-16") as f:
                self.task_xml = f.read()
        return self.code


def make(platform, tmp_path, runner):
    return Autostart(platform=platform, home=tmp_path, run=runner, command=lambda: COMMAND)


def test_windows_registers_a_logon_task_that_never_times_out(tmp_path):
    runner = Runner()
    make("win32", tmp_path, runner).enable()
    create = runner.calls[0]
    assert create[:4] == ["schtasks", "/Create", "/TN", "claude-usage-smalltv"]
    xml = runner.task_xml
    assert "<LogonTrigger>" in xml
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in xml
    assert "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>" in xml
    assert "<Command>C:\\Program Files\\Python\\pythonw.exe</Command>" in xml
    assert "<Arguments>-m claude_usage_smalltv run</Arguments>" in xml


def test_windows_status_and_removal_use_schtasks(tmp_path):
    runner = Runner(code=0)
    auto = make("win32", tmp_path, runner)
    assert auto.is_enabled()
    auto.disable()
    assert runner.calls[-1] == ["schtasks", "/Delete", "/TN", "claude-usage-smalltv", "/F"]
    assert not make("win32", tmp_path, Runner(code=1)).is_enabled()


def test_macos_writes_and_removes_a_launch_agent(tmp_path):
    auto = make("darwin", tmp_path, Runner())
    auto.enable()
    plist = tmp_path / "Library" / "LaunchAgents" / "dev.claude-usage-smalltv.plist"
    assert "<string>claude_usage_smalltv</string>" in plist.read_text(encoding="utf-8")
    assert auto.is_enabled()
    auto.disable()
    assert not plist.exists() and not auto.is_enabled()


def test_linux_writes_and_enables_a_user_unit(tmp_path):
    runner = Runner()
    auto = make("linux", tmp_path, runner)
    auto.enable()
    unit = tmp_path / ".config" / "systemd" / "user" / "claude-usage-smalltv.service"
    assert '"C:\\Program Files\\Python\\pythonw.exe" -m claude_usage_smalltv run' in unit.read_text(
        encoding="utf-8"
    )
    assert ["systemctl", "--user", "enable", "claude-usage-smalltv.service"] in runner.calls
    auto.disable()
    assert not unit.exists()


def test_launch_command_reuses_this_installation():
    command = launch_command()
    assert command[-3:] == ["-m", "claude_usage_smalltv", "run"]
    if sys.platform == "win32":
        assert command[0].lower().endswith("pythonw.exe")
