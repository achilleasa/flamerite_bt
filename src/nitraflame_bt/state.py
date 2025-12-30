"""NITRAFlame state parsing logic."""

import logging
from .const import HeatMode, Color, THERMOSTAT_MIN, THERMOSTAT_MAX, BRIGHTNESS_MIN, BRIGHTNESS_MAX, COLOR_MIN, COLOR_MAX

_LOGGER = logging.getLogger(__name__)

class State:
    """Representation of the NITRAFlame device state."""

    is_on: bool
    heat_mode: HeatMode
    thermostat: int
    flame_color: Color
    bed_color: Color
    flame_brightness: int
    bed_brightness: int

    def __init__(self) -> None:
        self.is_powered_on = False
        self.heat_mode = HeatMode.OFF
        self.thermostat = THERMOSTAT_MIN
        self.flame_color = Color.ORANGE_0 
        self.bed_color = Color.ORANGE_0
        self.flame_brightness = BRIGHTNESS_MIN 
        self.bed_brightness = BRIGHTNESS_MIN 
    
    def update_from_bytes(self, data: bytearray) -> bool:
        """Update state from raw byte data read from the device. Returns True if the update was successful."""

        # All async responses have the following structure:
        # --------------
        # [0] space (0x20)
        # [1] payload length in bytes
        # [...] response payload; variable
        if len(data) < 2 or data[0] != 0x20:
            return False

        # We only care about QUERY_STATE responses (cmd: a1010a) which always contain exactly 7 bytes.
        exp_res_payload_len = 7
        state_payload = data[2:]
        if len(state_payload) != exp_res_payload_len:
          return False

        # Response payload has the following structure:
        # [0] device state (0x0a: off; 0x0b: on - no heat, 0x0c: on - low heat, 0x0d: on - high heat)
        # [1] unknown
        # [2] thermostat temperature offset (0 to 15); add 16 to convert to the actual thermostat value
        # [3] flame brightness (0 to 9)
        # [4] bed brightness (0 to 9)
        # [5] flame color
        # [6] bed color
        self.is_powered_on = int(state_payload[0]) > 0x0a
        self.heat_mode = HeatMode(int(state_payload[0])) if self.is_powered_on else HeatMode.OFF
        self.thermostat = clamp(int(state_payload[2]) + 16, THERMOSTAT_MIN, THERMOSTAT_MAX)
        self.flame_brightness = clamp(1 + int(state_payload[3]), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
        self.bed_brightness = clamp(1 + int(state_payload[4]), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
        self.flame_color = Color(clamp(int(state_payload[5]), COLOR_MIN, COLOR_MAX))
        self.bed_color = Color(clamp(int(state_payload[6]), COLOR_MIN, COLOR_MAX))
        return True

    def set_thermostat(self, temperature_celsius: int) -> None:
        """Set the thermostat temperature in Celsius."""
        self.thermostat = clamp(temperature_celsius, THERMOSTAT_MIN, THERMOSTAT_MAX)

    def set_bed_brightness(self, brightness: int) -> None:
        """Set the bed brightness level (1-10)."""
        self.bed_brightness = clamp(brightness, BRIGHTNESS_MIN, BRIGHTNESS_MAX) 

    def set_flame_brightness(self, brightness: int) -> None:
        """Set the flame brightness level (1-10)."""
        self.flame_brightness = clamp(brightness, BRIGHTNESS_MIN, BRIGHTNESS_MAX)

    def __str__(self):
        return (
            f"Status: {'ON' if self.is_powered_on else 'OFF'}, "
            f"Heat Mode: {self.heat_mode}, "
            f"Thermostat: {self.thermostat}C, "
            f"Flame Brightness: {self.flame_brightness}, "
            f"Flame Color: {self.flame_color}, "
            f"Bed Brightness: {self.bed_brightness}, "
            f"Bed Color: {self.bed_color}"
        )


def clamp(value: int, min_value: int, max_value: int) -> int:
    """Clamp an integer value between min_value and max_value (inclusive)."""
    return max(min_value, min(value, max_value))