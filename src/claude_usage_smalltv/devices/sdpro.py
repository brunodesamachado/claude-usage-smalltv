"""Driver for the SD PRO firmware ("Smart Weather Clock", github.com/JUZIPi-tech/SD_PRO).

Endpoints were taken from the firmware's own web UI (index.html, photo page, javascript.js).
Only the ones below are used; restart, OTA, Wi-Fi and delete endpoints are never called.
"""

from __future__ import annotations

from typing import Any

from claude_usage_smalltv.devices.base import (
    PANEL_FILENAME,
    DeviceError,
    DeviceUnreachable,
    HttpDevice,
)

PHOTO_THEME = 2  # THEME_DICT in the firmware's javascript.js: 2 = "Photo"


class SdProDevice(HttpDevice):
    firmware = "SD PRO"

    @staticmethod
    def probe(dev: HttpDevice) -> bool:
        try:
            return isinstance(dev.get_json("/photo/list").get("files"), list)
        except DeviceUnreachable:
            raise
        except (DeviceError, AttributeError):
            return False

    def push(self, jpeg: bytes) -> None:
        self.post_file("/photo/upload", PANEL_FILENAME, jpeg, "image/jpeg")

    def current_theme(self) -> int | None:
        # /config also returns the Wi-Fi SSID and password in clear text: keep one key only.
        theme = self.get_json("/config").get("theme")
        return int(theme) if theme is not None else None

    def setup(self) -> dict[str, Any]:
        photos = self.get_json("/photo/list").get("files", [])
        themes = self.get_json("/theme/list").get("themes", [])
        if not any(f.get("name") == PANEL_FILENAME for f in photos):
            raise DeviceError(f"{PANEL_FILENAME} is not on the device yet; push a frame first")

        snapshot = {
            "photos": {
                f["name"]: bool(f.get("enabled", True))
                for f in photos
                if f["name"] != PANEL_FILENAME
            },
            "themes": {str(t["id"]): bool(t["enabled"]) for t in themes},
            "theme": self.current_theme(),
        }
        for f in photos:
            self._toggle_photo(f["name"], f["name"] == PANEL_FILENAME)
        # Enable Photo before disabling the rest: the firmware refuses an empty theme loop.
        self.get("/theme/toggle", id=PHOTO_THEME, state=1)
        for t in themes:
            if t["id"] != PHOTO_THEME and t["enabled"]:
                self.get("/theme/toggle", id=t["id"], state=0)
        self.get("/api/set", key="theme", value=PHOTO_THEME)
        return snapshot

    def restore(self, snapshot: dict[str, Any]) -> None:
        for name, enabled in snapshot.get("photos", {}).items():
            self._toggle_photo(name, enabled)
        self._toggle_photo(PANEL_FILENAME, False)
        themes = {int(k): v for k, v in snapshot.get("themes", {}).items()}
        for theme_id, enabled in sorted(themes.items(), key=lambda kv: not kv[1]):
            self.get("/theme/toggle", id=theme_id, state=int(enabled))
        if snapshot.get("theme") is not None:
            self.get("/api/set", key="theme", value=snapshot["theme"])

    def _toggle_photo(self, name: str, enabled: bool) -> None:
        self.get("/photo/toggle", name=name, state=int(enabled))
