# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-30

### Added

- Settings page in the browser (`http://127.0.0.1:8765`), served by the service itself:
  a 4-step assistant (Claude login, find the display, language with live preview, set up)
  and a status page with usage, display health, preview, recent activity, change display
  and give the display back. English and Portuguese, light and dark.
- Running with no command (or double-clicking the `.exe`) starts the service and opens the
  page; if the service is already running, it just opens the page.
- "Start with the computer" switch: Task Scheduler on Windows, launchd on macOS, systemd
  on Linux.
- "Show the IP on the display" option: the display's address in small print under the logo.
- Settings are saved to `config.json`, so `run`, `doctor`, `setup` and `restore` work
  without passing the IP.
- Standalone Windows `.exe` (no Python needed), built and attached to each GitHub release.
- `run --port`, `--no-web` and `--open`.

### Changed

- The service keeps refreshing usage while the display is off, and switches display or
  language without a restart.

### Fixed

- `run` now waits for a display that is off or off the network, retrying every minute,
  instead of exiting. Windows Task Scheduler does not restart a task that exits with an
  error, so the panel stayed frozen until the next logon. `run --once` still fails fast.
- An unreachable display is no longer reported as "firmware is not supported".

## [0.1.0] - 2026-10-29

### Added

- Panel with clock, 5-hour session and weekly meters, reset countdowns and weekly breakdown.
- Usage from Claude Code's login; expired tokens are renewed by the official `claude` CLI.
- Usage polled every 5 minutes with exponential backoff on HTTP 429; stale data is flagged.
- Drivers for the SD PRO firmware (tested) and the GeekMagic stock firmware (experimental).
- Commands: `scan`, `doctor`, `preview`, `setup`, `run`, `restore`.
- English and Portuguese panels.
- `claude-usage-smalltvw` console-less entry point for Windows Task Scheduler.
