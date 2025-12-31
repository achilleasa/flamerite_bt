"""Device wrapper for the NITRAFlame Fireplace device."""

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClient,  # type: ignore
    establish_connection,
)

from .state import State
from .const import (
    DEVICE_RESPONSE_TIMEOUT_SECONDS,
    Command,
    Color,
    HeatMode,
    DeviceAttribute,
)

_LOGGER = logging.getLogger(__name__)


class Device:
    """A wrapper class to interact with NITRAFLame Bluetooth devices."""

    _ble_device: BLEDevice
    _connection: BleakClient
    _connection_lock = asyncio.Lock()
    _is_connected: bool
    _mac: str
    _model_number: str
    _srial_number: str
    _manufacturer: str

    _state_lock = asyncio.Lock()
    _state: State
    _state_updated: asyncio.Event = asyncio.Event()

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._is_connected = False
        self._mac = ble_device.address
        self._state = State()

    def disconnected_callback(self, client):  # pylint: disable=unused-argument
        """Handle disconnection events."""

        _LOGGER.warning("Disconnected from %s", self._mac)
        self._is_connected = False

    async def connect(self, retry_attempts=4) -> None:
        """Connect to the device."""

        if self._is_connected or self._connection_lock.locked():
            return

        async with self._connection_lock:
            try:
                _LOGGER.debug("Connecting to %s", self._mac)

                self._connection = await establish_connection(
                    client_class=BleakClient,
                    device=self._ble_device,
                    name=self._mac,
                    disconnected_callback=self.disconnected_callback,
                    max_attempts=retry_attempts,
                    use_services_cache=True,
                )

                self._is_connected = True

                self._model_number = (
                    (
                        await self._connection.read_gatt_char(
                            DeviceAttribute.MODEL_NUMBER.value
                        )
                    )
                    .decode("utf-8")
                    .strip("\x00")
                )
                self._serial_number = (
                    (
                        await self._connection.read_gatt_char(
                            DeviceAttribute.SERIAL_NUMBER.value
                        )
                    )
                    .decode("utf-8")
                    .strip("\x00")
                )
                self._manufacturer = (
                    (
                        await self._connection.read_gatt_char(
                            DeviceAttribute.MANUFACTURER.value
                        )
                    )
                    .decode("utf-8")
                    .strip("\x00")
                )
                _LOGGER.info(
                    "Connected to device %s (Model: %s, Serial: %s, Manufacturer: %s)",
                    self._mac,
                    self._model_number,
                    self._serial_number,
                    self._manufacturer,
                )

                # To interface with the device we first write a command to DEVICE_WRITE_ATTR_UUID and wait for an
                # asynchronous notification to be received on DEVICE_READ_ATTR_UUID.
                def on_notify(sender: int, data: bytearray):
                    """Notification handler which updates the device state."""
                    if self._state.update_from_bytes(data):
                        self._state_updated.set()

                await self._connection.start_notify(
                    DeviceAttribute.CMD_RES_ATTR.value, on_notify
                )
            except BleakError as ex:
                _LOGGER.error("Failed to connect to %s: %s", self._mac, ex)
                self._is_connected = False

    async def disconnect(self) -> None:
        """Disconnect the device."""
        if not self._is_connected:
            return

        await self._connection.disconnect()
        _LOGGER.debug("Disconnected from %s", self._mac)

    def update_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the underlying BLE device reference."""
        self._ble_device = ble_device

    async def query_state(self) -> None:
        """Query the device state."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            self._state_updated.clear()
            await self._send_cmd(Command.QUERY_STATE.value)
            try:
                await asyncio.wait_for(
                    self._state_updated.wait(), timeout=DEVICE_RESPONSE_TIMEOUT_SECONDS
                )
                _LOGGER.debug("Updated state: %s", self._state)
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout waiting for state response from %s", self._mac)
                pass

    async def _send_cmd(self, cmd_bytes: bytes) -> None:
        """Send a command to the device."""
        await self._connection.write_gatt_char(
            DeviceAttribute.CMD_REQ_ATTR.value, cmd_bytes, response=True
        )

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        return self._is_connected

    @property
    def mac(self) -> str:
        """Return the MAC address of the connected device."""
        return self._mac

    @property
    def model_number(self) -> str:
        """Return the model number of the connected device."""
        return self._model_number

    @property
    def serial_number(self) -> str:
        """Return the serial number of the connected device."""
        return self._serial_number

    @property
    def manufacturer(self) -> str:
        """Return the manufacturer of the connected device."""
        return self._manufacturer

    @property
    def is_powered_on(self) -> bool:
        """Return true if the device is powered on."""
        return self._state.is_powered_on

    async def set_powered_on(self, value: bool) -> None:
        """Set the device power state."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            old_value = self._state.is_powered_on
            self._state.is_powered_on = value

            # Toggle power only if the state has changed.
            if old_value == value:
                return
            await self._send_cmd(Command.POWER_TOGGLE.value)

    @property
    def heat_mode(self) -> HeatMode:
        """Return the current heat mode."""
        return self._state.heat_mode

    async def set_heat_mode(self, mode: HeatMode) -> None:
        """Set the heat mode."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            if not self.is_powered_on and mode != HeatMode.OFF:
                # Cannot set heat mode if the device is powered off.
                _LOGGER.warning("Cannot set heat mode when device is powered off")
                return

            old_value = self._state.heat_mode
            self._state.heat_mode = mode

            # Only send commands if the heat mode has changed.
            if old_value == mode:
                return

            # Heat selection works in sequential steps as follows:
            # To go from off to low -> send SET_HEAT_LOW cmd (step up)
            # To go from low -> off -> send SET_HEAT_LOW cmd (step down)
            # To go from low -> high -> send SET_HEAT_HIGH cmd (step up)
            # To go from high -> low -> send SET_HEAT_LOW cmd (step down)
            if old_value == HeatMode.OFF:
                if mode == HeatMode.LOW:
                    await self._send_cmd(Command.SET_HEAT_LOW.value)
                elif mode == HeatMode.HIGH:
                    await self._send_cmd(Command.SET_HEAT_LOW.value)
                    await self._send_cmd(Command.SET_HEAT_HIGH.value)
            elif old_value == HeatMode.LOW:
                if mode == HeatMode.OFF:
                    await self._send_cmd(Command.SET_HEAT_LOW.value)
                elif mode == HeatMode.HIGH:
                    await self._send_cmd(Command.SET_HEAT_HIGH.value)
            elif old_value == HeatMode.HIGH:
                if mode == HeatMode.LOW:
                    await self._send_cmd(Command.SET_HEAT_HIGH.value)
                elif mode == HeatMode.OFF:
                    await self._send_cmd(Command.SET_HEAT_HIGH.value)
                    await self._send_cmd(Command.SET_HEAT_LOW.value)

    @property
    def thermostat(self) -> int:
        """Return the current thermostat temperature."""
        return self._state.thermostat

    async def set_thermostat(self, temperature: int) -> None:
        """Set the thermostat temperature."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            self._state.set_thermostat(temperature)
            await self._send_cmd(
                Command.SET_THERMOSTAT.value + bytes([self._state.thermostat])
            )

    @property
    def flame_color(self) -> Color:
        """Return the current flame color."""
        return self._state.flame_color

    async def set_flame_color(self, color: Color) -> None:
        """Set the flame color."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            self._state.flame_color = color
            await self._send_cmd(
                Command.SET_FLAME_COLOR.value + bytes([self._state.flame_color.value])
            )

    @property
    def bed_color(self) -> Color:
        """Return the current bed color."""
        return self._state.bed_color

    async def set_bed_color(self, color: Color) -> None:
        """Set the bed color."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            self._state.bed_color = color
            await self._send_cmd(
                Command.SET_BED_COLOR.value + bytes([self._state.bed_color.value])
            )

    @property
    def flame_brightness(self) -> int:
        """Return the current flame brightness level."""
        return self._state.flame_brightness

    async def set_flame_brightness(self, brightness: int) -> None:
        """Set the flame brightness level."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            old_value = self._state.flame_brightness
            self._state.set_flame_brightness(brightness)

            # Only send commands if the brightness level has changed.
            if old_value == brightness:
                return

            while self._state.flame_brightness < old_value:
                await self._send_cmd(Command.FLAME_BRIGHTNESS_DEC.value)
                old_value -= 1

            while self._state.flame_brightness > old_value:
                await self._send_cmd(Command.FLAME_BRIGHTNESS_INC.value)
                old_value += 1

    @property
    def bed_brightness(self) -> int:
        """Return the current bed brightness level."""
        return self._state.bed_brightness

    async def set_bed_brightness(self, brightness: int) -> None:
        """Set the bed brightness level."""
        if not self._is_connected:
            await self.connect(retry_attempts=1)

        async with self._state_lock:
            old_value = self._state.bed_brightness
            self._state.set_bed_brightness(brightness)

            # Only send commands if the brightness level has changed.
            if old_value == brightness:
                return

            while self._state.bed_brightness < old_value:
                await self._send_cmd(Command.BED_BRIGHTNESS_DEC.value)
                old_value -= 1

            while self._state.bed_brightness > old_value:
                await self._send_cmd(Command.BED_BRIGHTNESS_INC.value)
                old_value += 1
