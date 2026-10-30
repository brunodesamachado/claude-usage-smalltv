# Contributing

Thanks for helping! Bug reports, firmware reports and pull requests are all welcome.

## Set up

```bash
git clone https://github.com/YOUR_GITHUB_USER/claude-usage-smalltv
cd claude-usage-smalltv
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Before opening a pull request:

```bash
pytest
ruff check .
ruff format --check .
```

Tests never touch the network: HTTP is replaced by `tests/fakes.py`.

## Project layout

```
src/claude_usage_smalltv/
├── credentials.py   read Claude Code's OAuth token; renewal is delegated to the `claude` CLI
├── usage.py         fetch and parse the 5-hour and weekly windows
├── render.py        draw the 240×240 panel (layout in 240 px units, any integer scale)
├── devices/         one driver per display firmware, chosen by probing
├── daemon.py        frame every minute, usage on a slower cadence with 429 backoff
├── discovery.py     LAN scan
└── cli.py           argparse entry point
```

## Adding a firmware driver

1. Open the display's web UI and read its HTML/JS to find the upload and display endpoints.
   Never call restart, firmware update, Wi-Fi or delete endpoints from the driver.
2. Add `devices/<name>.py` with a class that subclasses `HttpDevice` and implements:
   - `probe(dev) -> bool` (static): a cheap, read-only request that only your firmware answers.
   - `push(jpeg)`: upload the frame as `PANEL_FILENAME`, overwriting the previous one.
   - `setup() -> dict` and `restore(snapshot)`: make the panel the only thing on screen, and undo it.
3. Register it in `devices/__init__.py` (`DRIVERS`) and add tests with `FakeSession`.
4. Mention it in the firmware table in both READMEs.

## Reporting a firmware

Open an issue with the output of `claude-usage-smalltv doctor <ip>`, the page title of `http://<ip>/` and what you saw on screen. Please **don't** paste the output of the display's `/config` endpoint: on some firmwares it contains your Wi-Fi password.
