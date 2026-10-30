# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
