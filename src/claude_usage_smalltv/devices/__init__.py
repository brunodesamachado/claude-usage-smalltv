"""Firmware drivers for GeekMagic SmallTV displays, picked by probing the device."""

from __future__ import annotations

from claude_usage_smalltv.devices.base import (
    PANEL_FILENAME,
    Device,
    DeviceError,
    DeviceUnreachable,
    HttpDevice,
)
from claude_usage_smalltv.devices.geekmagic import GeekMagicDevice
from claude_usage_smalltv.devices.sdpro import SdProDevice

DRIVERS = (SdProDevice, GeekMagicDevice)

__all__ = [
    "DRIVERS",
    "PANEL_FILENAME",
    "Device",
    "DeviceError",
    "DeviceUnreachable",
    "GeekMagicDevice",
    "HttpDevice",
    "SdProDevice",
    "connect",
]


def connect(host: str, timeout: float = 15, retries: int = 3) -> Device:
    """Return the driver matching the firmware running at `host`."""
    probe = HttpDevice(host, timeout=timeout, retries=retries)
    try:
        for driver in DRIVERS:
            if driver.probe(probe):
                return driver(host, session=probe.session, timeout=timeout, retries=retries)
    except DeviceUnreachable as exc:
        raise DeviceUnreachable(
            f"{host} is not answering. Is the display on and on the same Wi-Fi? ({exc})"
        ) from exc
    raise DeviceError(
        f"{host} answered, but its firmware is not supported. "
        "Supported: SD PRO, GeekMagic stock (experimental)."
    )
