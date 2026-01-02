"""Debug CLI for interfacing with NITRAFlame Fireplace devices over Bluetooth."""

import asyncio
import logging
import sys
from typing import List

import aioconsole
from bleak.backends.device import BLEDevice

from nitraflame_bt.device import Device
from nitraflame_bt.scanner import scan_for_nitraflame_devices

from nitraflame_bt.const import Color, HeatMode

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("bleak").setLevel(logging.WARNING)

_LOGGER = logging.getLogger(__name__)


async def main():
    ble_devices = await scan_for_nitraflame_devices(
        max_devices=1, scan_timeout_seconds=40
    )
    if len(ble_devices) == 0:
        _LOGGER.warning("No devices found")
        return

    device = Device(ble_devices[0])
    await device.connect()

    while True:
        await device.query_state()

        # Take user input
        line = await aioconsole.ainput(
            "Commands:\n"
            + "fc=<value> -> set flame color\n"
            + "bc=<value> -> set bed/fuel color\n"
            + "fb=<value> -> set flame brightness\n"
            + "bb=<value> -> set bed/fuel brightness\n"
            + "t=<value>  -> set thermostat temperature\n"
            + "hm=<value> -> set heat mode (OFF, LOW, HIGH)\n"
            + "on         -> turn on\n"
            + "off        -> turn off\n"
            + "cmd=<value>-> run command\n"
            + "\nOr 'exit' to disconnect:\n"
        )

        if line == "exit":
            await device.disconnect()
            sys.exit(0)
        elif line.startswith("fc="):
            color_name = line.split("=")[1]
            match = [c for c in list(Color) if c.name == color_name]
            if len(match) != 1:
                _LOGGER.warning(f"Invalid color name: {color_name}")
                continue
            await device.set_flame_color(match[0])
        elif line.startswith("bc="):
            color_name = line.split("=")[1]
            match = [c for c in list(Color) if c.name == color_name]
            if len(match) != 1:
                _LOGGER.warning(f"Invalid color name: {color_name}")
                continue
            await device.set_fuel_color(match[0])
        elif line == "on":
            await device.set_powered_on(True)
        elif line == "off":
            await device.set_powered_on(False)
        elif line.startswith("t="):
            temperature = int(line.split("=")[1])
            await device.set_thermostat(temperature)
        elif line.startswith("fb="):
            brightness = int(line.split("=")[1])
            await device.set_flame_brightness(brightness)
        elif line.startswith("bb="):
            brightness = int(line.split("=")[1])
            await device.set_fuel_brightness(brightness)
        elif line.startswith("hm="):
            mode = line.split("=")[1]
            match = [hm for hm in list(HeatMode) if hm.name == mode]
            if len(match) != 1:
                _LOGGER.warning(f"Invalid heat mode: {mode}")
                continue
            await device.set_heat_mode(match[0])
        elif line.startswith("cmd="):
            cmd_hex = line.split("=")[1]
            cmd_bytes = bytes.fromhex(cmd_hex)
            await device._send_cmd(cmd_bytes)
        else:
            _LOGGER.warn("Invalid command")

        continue


asyncio.run(main())
