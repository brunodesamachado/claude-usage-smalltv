"""Command line: `claude-usage-smalltv scan | doctor | preview | setup | run | restore`."""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

from claude_usage_smalltv import __version__
from claude_usage_smalltv.credentials import CredentialsError, load_token
from claude_usage_smalltv.daemon import Daemon
from claude_usage_smalltv.demo import demo_usage
from claude_usage_smalltv.devices import DeviceError, connect
from claude_usage_smalltv.discovery import scan
from claude_usage_smalltv.paths import backup_file, state_dir
from claude_usage_smalltv.render import LABELS, Frame, Renderer, to_jpeg
from claude_usage_smalltv.usage import RateLimited, UsageClient, UsageError

log = logging.getLogger("claude_usage_smalltv")

HOST_ENV = "SMALLTV_HOST"
LANG_ENV = "CLAUDE_USAGE_LANG"


def _now() -> datetime:
    return datetime.now().astimezone()


# --------------------------------------------------------------------------- commands


def cmd_scan(args: argparse.Namespace) -> int:
    print("Scanning your network for displays (port 80)...")
    hosts = scan(args.subnet)
    if not hosts:
        print(
            "Nothing answered. Is the display on the same network? "
            "Its IP is shown on screen right after power-on."
        )
        return 1
    for host in hosts:
        mark = "  <- SmallTV" if host.looks_like_smalltv else ""
        print(f"  {host.ip:15}  {host.title or '(no title)'}{mark}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Read-only checks, from Claude login to the display's firmware."""
    ok = True

    def report(passed: bool, label: str, detail: str) -> None:
        nonlocal ok
        ok &= passed
        print(f"  [{'ok' if passed else '!!'}] {label:16} {detail}")

    print("Claude")
    try:
        token = load_token()
        minutes = (token.expires_at - time.time()) / 60
        state = (
            f"token valid for {minutes:.0f} min" if minutes > 0 else "token expired (will renew)"
        )
        report(True, "login", f"plan {token.plan or '?'}, {state}")
        usage = UsageClient().fetch()
        session = f"{usage.session.percent:.0f}%" if usage.session else "-"
        weekly = f"{usage.weekly.percent:.0f}%" if usage.weekly else "-"
        report(True, "usage endpoint", f"session {session}, weekly {weekly}")
    except CredentialsError as exc:
        report(False, "login", str(exc))
    except RateLimited:
        report(True, "usage endpoint", "rate limited right now (normal if polled recently)")
    except (UsageError, OSError) as exc:
        report(False, "usage endpoint", str(exc))

    if args.host:
        print(f"Display at {args.host}")
        started = time.perf_counter()
        try:
            with socket.create_connection((args.host, 80), timeout=10):
                pass
            report(
                True, "network", f"port 80 open in {(time.perf_counter() - started) * 1000:.0f} ms"
            )
            device = connect(args.host)
            report(True, "firmware", device.firmware)
        except OSError as exc:
            report(False, "network", f"cannot reach port 80 ({exc})")
        except DeviceError as exc:
            report(False, "firmware", str(exc))
    else:
        print(f"Display: skipped (pass HOST or set {HOST_ENV})")
    return 0 if ok else 1


def cmd_preview(args: argparse.Namespace) -> int:
    now = _now()
    try:
        usage = demo_usage(now) if args.demo else UsageClient().fetch()
    except RateLimited:
        print("Claude's usage endpoint is rate limiting (HTTP 429). It clears in a few minutes;")
        print("meanwhile, `preview --demo` renders sample numbers.")
        return 1
    img = Renderer(args.lang, scale=args.scale).render(Frame(usage, now))
    img.save(args.output)
    print(f"Saved {args.output}")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    device = connect(args.host)
    print(f"Found {device.firmware} at {args.host}")
    device.push(to_jpeg(Renderer(args.lang).render(Frame(None, _now()))))
    snapshot = device.setup()
    path = backup_file(args.host)
    if path.exists():
        print(f"Kept the earlier backup at {path} (setup had already run)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        print(f"Previous settings saved to {path}")
    print("Done: the display now shows only the usage panel.")
    print(f"Next: claude-usage-smalltv run {args.host}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    device = connect(args.host)
    daemon = Daemon(device, UsageClient(), Renderer(args.lang), usage_interval=args.usage_interval)
    if args.once:
        daemon.tick()
        return 0
    try:
        daemon.run_forever()
    except KeyboardInterrupt:
        log.info("stopped")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    path = backup_file(args.host)
    if not path.exists():
        print(f"No backup for {args.host} at {path}; nothing to restore.")
        return 1
    device = connect(args.host)
    device.restore(json.loads(path.read_text(encoding="utf-8")))
    path.unlink()
    print("Restored the display's previous photos and theme.")
    return 0


# ---------------------------------------------------------------------------- parsing


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-usage-smalltv",
        description="Show your Claude plan usage on a GeekMagic SmallTV.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    parser.add_argument("--log-file", type=Path, help="also write logs to this file")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def host_arg(p: argparse.ArgumentParser, required: bool = True) -> None:
        default = os.environ.get(HOST_ENV)
        p.add_argument(
            "host",
            nargs="?" if default or not required else None,
            default=default,
            metavar="HOST",
            help=f"display IP or hostname (or set {HOST_ENV})",
        )

    def lang_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--lang",
            choices=sorted(LABELS),
            default=os.environ.get(LANG_ENV, "en"),
            help=f"panel language (default: en, or {LANG_ENV})",
        )

    p = sub.add_parser("scan", help="find displays on your network")
    p.add_argument("--subnet", help="e.g. 192.168.1.0/24 (default: your /24)")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("doctor", help="check Claude login, usage API and the display")
    host_arg(p, required=False)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("preview", help="render the panel to a PNG, no display needed")
    p.add_argument("--demo", action="store_true", help="use sample numbers instead of your usage")
    p.add_argument("-o", "--output", type=Path, default=Path("claude-usage-preview.png"))
    p.add_argument("--scale", type=int, default=1, choices=(1, 2, 3, 4))
    lang_arg(p)
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("setup", help="make the display show only the panel (undo: restore)")
    host_arg(p)
    lang_arg(p)
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("run", help="keep the display updated (every minute)")
    host_arg(p)
    lang_arg(p)
    p.add_argument("--once", action="store_true", help="push a single frame and exit")
    p.add_argument(
        "--usage-interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="how often to poll Claude usage (default 300; lower risks HTTP 429)",
    )
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("restore", help="undo setup: previous photos and theme")
    host_arg(p)
    p.set_defaults(func=cmd_restore)
    return parser


def configure_logging(verbose: bool, log_file: Path | None) -> None:
    handlers: list[logging.Handler] = []
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    if log_file is None and sys.stderr is None:  # pythonw / background service: no console
        log_file = state_dir() / "claude-usage-smalltv.log"
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
            )
        )
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if sys.stdout is None:  # pythonw: make print() harmless
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115

    args = build_parser().parse_args(argv)
    configure_logging(args.verbose, args.log_file)
    try:
        return int(args.func(args))
    except (DeviceError, CredentialsError, UsageError) as exc:
        log.error("%s", exc)
        return 1
