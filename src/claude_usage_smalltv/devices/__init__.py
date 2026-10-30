"""Firmware drivers for GeekMagic SmallTV displays, picked by probing the device."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

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
    "connect_when_reachable",
]

log = logging.getLogger(__name__)


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


def connect_when_reachable(
    host: str, retry_every: float = 60, sleep: Callable[[float], None] = time.sleep
) -> Device:
    """Like `connect`, but wait for a display that is off or asleep instead of giving up.

    A background service started at logon must not die because the display was unplugged
    at that moment: Windows Task Scheduler does not restart a task that exits with an error.
    """
    while True:
        try:
            return connect(host)
        except DeviceUnreachable as exc:
            log.warning("display: %s Retrying in %.0fs.", exc, retry_every)
            sleep(retry_every)
