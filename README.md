# flamerite_bt
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An unofficial python package for controlling [Flamerite](https://flameritefires.com) fireplace devices via bluetooth.

While the package is designed to encapsulate the required logic for building a HomeAssistant automation, it can also be used in standalone mode.

## Supported devices
The package has been tested with and known to work with a `NITRAFlame` fireplace.

Other Flamerite devices, provided they are controlled via the eControl app, will likely also work but must be explicitly added to the `SUPPORTED_DEVICE_NAMES` list in `const.py` so they can be detected.

## Supported features
The following features are supported:

- Turn on/off.
- Select color for flame / fuel.
- Adjust brighness for flame / fuel.
- Adjust thermostat.
- Adjust heat level (off, low, high)

Programmable timers are **not** yet supported.

### Color support for flame/fuel
The device supports 5 palettes with 4 hues in each palette for a total of 20 colors.

In addition, the device also supports 5 color cycling modes. The first 4 just cycle through all available colors whereas the last one only cycles through orange hues.

## Using the CLI
The package provides a rudimentary CLI that scans for the presence of supported Flamerite devices, and attempts to connect to the first one it finds. It then provides
a small text-based UI for interacting with the device.

To use (you will need to install [poetry](https://python-poetry.org/docs/) to manage Python dependencies):

```
$ poetry install
$ poetry run python cli.py
```

**NOTE**: you will need to pair your bluetooth adaptor to the device before you can control it. To do this, once the CLI detects the device and attempts to connect to it, press the physical link button on the device control panel to complete the pairing process.