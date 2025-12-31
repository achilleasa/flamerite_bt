"""Constants for the NITRAFlame Bluetooth integration."""

from enum import Enum,IntEnum

DEVICE_NAME = "NITRAFlame"

# The maximum time to wait for a response from the device when querying its state.
DEVICE_RESPONSE_TIMEOUT_SECONDS = 5

class DeviceAttribute(Enum):
    """Device attributes that can be queried."""

    MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
    SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
    MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"

    CMD_REQ_ATTR = "0000fff2-0000-1000-8000-00805f9b34fb"
    CMD_RES_ATTR = "0000fff1-0000-1000-8000-00805f9b34fb"

class Color(IntEnum):
    """Available flame and bed colors.

    NITRAFlame devices support 5 color palettes. Each color has 4 variations (e.g., ORANGE_0 to ORANGE_3) 
    with increasing intensity. In addition, there are 5 FLOW modes that cycle through all colors with FLOW_ORANGE_ONLY cycling
    only between orange hues."""

    ORANGE_0 = 0x00
    ORANGE_1 = 0x01
    ORANGE_2 = 0x02
    ORANGE_3 = 0x03
    RED_0 = 0x04
    RED_1 = 0x05
    RED_2 = 0x06
    RED_3 = 0x07
    GREEN_0 = 0x08
    GREEN_1 = 0x09
    GREEN_2 = 0x0a
    GREEN_3 = 0x0b
    BLUE_0 = 0x0c
    BLUE_1 = 0x0d
    BLUE_2 = 0x0e
    BLUE_3 = 0x0f
    WHITE_0 = 0x10
    WHITE_1 = 0x11
    WHITE_2 = 0x12
    WHITE_3 = 0x13

    FLOW_0 = 0x14
    FLOW_1 = 0x15
    FLOW_2 = 0x16
    FLOW_3 = 0x17
    FLOW_ORANGE_ONLY = 0x18

    def __str__(self):
        return self.name

class HeatMode(IntEnum):
    """Available heat modes for the NITRAFlame device."""

    OFF = 0x0b
    LOW = 0x0c
    HIGH = 0x0d

    def __str__(self):
        return self.name

# Valid ranges for device-reported values.
THERMOSTAT_MIN = 16
THERMOSTAT_MAX = 31
BRIGHTNESS_MIN = 1
BRIGHTNESS_MAX = 10
COLOR_MIN = Color.ORANGE_0.value 
COLOR_MAX = Color.FLOW_ORANGE_ONLY.value

# Commands that can be sent to the device.
class Command(Enum):
    """Commands that can be sent to the NITRAFlame device."""
    QUERY_STATE = bytes.fromhex('a1010a')
    POWER_TOGGLE = bytes.fromhex('a10100') 

    SET_HEAT_LOW = bytes.fromhex('a10101')
    SET_HEAT_HIGH = bytes.fromhex('a10103')

    FLAME_BRIGHTNESS_INC = bytes.fromhex('a10104')
    FLAME_BRIGHTNESS_DEC = bytes.fromhex('a10105')
    BED_BRIGHTNESS_INC = bytes.fromhex('a10106')
    BED_BRIGHTNESS_DEC = bytes.fromhex('a10107')
    
    # Set Color commands ('c201' + color) and ('c101' + color)
    SET_FLAME_COLOR = bytes.fromhex('c101')
    SET_BED_COLOR = bytes.fromhex('c201')

    # Thermostat control command ('a201' + temp) where temp is in the [16, 31] range.
    SET_THERMOSTAT = bytes.fromhex('a201')