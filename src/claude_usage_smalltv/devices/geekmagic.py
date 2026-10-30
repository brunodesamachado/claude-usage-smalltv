"""Driver for the stock GeekMagic SmallTV / SmallTV-Ultra firmware — EXPERIMENTAL.

The endpoints follow the stock web UI as documented by other open-source projects
(`/doUpload?dir=/image/`, `/set?theme=`, `/set?img=`), but this driver has not been tested on
real hardware by the maintainers yet. Reports are welcome in the issue tracker.
"""

from __future__ import annotations

from typing import Any

from claude_usage_smalltv.devices.base import PANEL_FILENAME, DeviceError, HttpDevice

ALBUM_THEME = 3  # "Photo Album" on the stock SmallTV-Ultra firmware
IMAGE_DIR = "/image/"


class GeekMagicDevice(HttpDevice):
    firmware = "GeekMagic stock (experimental)"

    @staticmethod
    def probe(dev: HttpDevice) -> bool:
        try:
            return isinstance(dev.get_json("/app.json"), dict)
        except DeviceError:
            return False

    def push(self, jpeg: bytes) -> None:
        self.post_file("/doUpload", PANEL_FILENAME, jpeg, "image/jpeg", dir=IMAGE_DIR)

    def setup(self) -> dict[str, Any]:
        try:
            theme = self.get_json("/app.json").get("theme")
        except (DeviceError, AttributeError):
            theme = None
        self.get("/set", theme=ALBUM_THEME)
        self.get("/set", img=f"{IMAGE_DIR}{PANEL_FILENAME}")
        return {"theme": theme}

    def restore(self, snapshot: dict[str, Any]) -> None:
        if snapshot.get("theme") is not None:
            self.get("/set", theme=snapshot["theme"])
