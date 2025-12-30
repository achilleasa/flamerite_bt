"""Simple scanner for locating NITRAFlame devices based on the advertised manufacturer name."""

import asyncio
import logging
import sys
from typing import Callable

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .const import DEVICE_NAME

_LOGGER = logging.getLogger(__name__)

DeviceCallbackType = Callable[[BLEDevice], None]

lock = asyncio.Lock()


def _is_nitraflame_device(
    ble_device: BLEDevice,
    ble_advertisement_data: AdvertisementData,
)-> bool:
    return DEVICE_NAME in (ble_advertisement_data.local_name or "")


async def scan_for_nitraflame_devices(
    scan_timeout_seconds=60,
    max_devices=-1,
) -> list[BLEDevice]:
    """Scan for NITRAFlame devices and invoke the callback for each found device."""

    device_list: list[BLEDevice] = []
    _LOGGER.debug("Scanning for NITRAFlame devices")

    scan_done = asyncio.Event()
    def _detection_callback(
        ble_device: BLEDevice,
        ble_advertisement_data: AdvertisementData,
    ) -> None:
        if not _is_nitraflame_device(ble_device, ble_advertisement_data):
            return

        already_seen = [d for d in device_list if d.address == ble_device.address]
        if len(already_seen) > 0:
            return

        _LOGGER.debug("Found NITRAFlame device: %s", ble_device)
        device_list.append(ble_device)

        # If we've reached the threshold, signal to stop scanning early.
        if max_devices != -1 and len(device_list) == max_devices:
            scan_done.set()

    # Scan for compatible devices up to scan_timeout_seconds seconds or until the required number of devices is found. 
    async with BleakScanner(_detection_callback) as scanner:
        try:
            await asyncio.wait_for(scan_done.wait(), timeout=scan_timeout_seconds)
        except asyncio.TimeoutError:
            # Timeout elapsed; proceed with whatever devices were found.
            pass
    
    _LOGGER.debug("Scan complete, found %d NITRAFlame devices", len(device_list))
    return device_list
