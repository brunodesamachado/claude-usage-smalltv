"""Firmware drivers for GeekMagic SmallTV displays, picked by probing the device."""

from __future__ import annotations

from claude_usage_smalltv.devices.base import PANEL_FILENAME, Device, DeviceError, HttpDevice
from claude_usage_smalltv.devices.geekmagic import GeekMagicDevice
from claude_usage_smalltv.devices.sdpro import SdProDevice

DRIVERS = (SdProDevice, GeekMagicDevice)

__all__ = [
    "DRIVERS",
    "PANEL_FILENAME",
    "Device",
    "DeviceError",
    "GeekMagicDevice",
    "HttpDevice",
    "SdProDevice",
    "connect",
]


def connect(host: str, timeout: float = 15, retries: int = 3) -> Device:
    """Return the driver matching the firmware running at `host`."""
    probe = HttpDevice(host, timeout=timeout, retries=retries)
    for driver in DRIVERS:
        if driver.probe(probe):
            return driver(host, session=probe.session, timeout=timeout, retries=retries)
    raise DeviceError(
        f"{host} answered, but its firmware is not supported. "
        "Supported: SD PRO, GeekMagic stock (experimental)."
    )
