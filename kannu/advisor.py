"""Tells the builder which Pi pin each wire goes to. Only pins from the safe table are ever suggested."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

PINMAP = json.loads((Path(__file__).resolve().parent.parent / "data" / "pinmap.json").read_text())
ALLOWED_PINS = (
    {v["pin"] for v in PINMAP["i2c"].values()} | {v["pin"] for v in PINMAP["onewire"].values()}
    | {v["pin"] for v in PINMAP["spi"].values()} | set(PINMAP["power_3v3"]) | set(PINMAP["power_5v"])
    | set(PINMAP["ground"]) | {g["pin"] for g in PINMAP["free_gpio"]}
)


@dataclass(frozen=True)
class Step:
    module_pin: str
    pi_pin: int
    pi_label: str
    kind: str      # power | ground | signal
    note: str = ""


@dataclass(frozen=True)
class Wiring:
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _power(record: dict, steps: list, warnings: list) -> None:
    vmin, vmax = record.get("voltage_min", 3.3), record.get("voltage_max", 3.3)
    if vmin <= 3.3 <= vmax:
        steps.append(Step("VCC", PINMAP["power_3v3"][0], "3.3 V", "power", "power from 3.3 V"))
    else:
        steps.append(Step("VCC", PINMAP["power_5v"][0], "5 V", "power", f"needs {vmin} to {vmax} V"))
        warnings.append(f"this part needs {vmin} to {vmax} V: powered from 5 V, so keep its signal pins away from the Pi unless the signals are 3.3 V")
    steps.append(Step("GND", PINMAP["ground"][0], "GND", "ground"))


def plan_wiring(record: dict) -> Wiring:
    steps: list[Step] = []
    warnings: list[str] = []
    iface = record.get("interface")
    logic = record.get("logic_level", 3.3)
    if iface == "i2c":
        _power(record, steps, warnings)
        steps.append(Step("SDA", PINMAP["i2c"]["SDA"]["pin"], "GPIO2 (SDA)", "signal"))
        steps.append(Step("SCL", PINMAP["i2c"]["SCL"]["pin"], "GPIO3 (SCL)", "signal"))
        if logic > 3.6:
            warnings.append("I2C lines on this module are 5 V: use a level shifter or run it from 3.3 V")
    elif iface == "digital":
        _power(record, steps, warnings)
        gpio = PINMAP["free_gpio"][0]
        steps.append(Step("DATA/OUT", gpio["pin"], f"GPIO{gpio['bcm']}", "signal", "any free GPIO works"))
        if logic > 3.6:
            warnings.append("the output is 5 V: add a resistor divider before it reaches the Pi pin")
    elif iface == "analog":
        _power(record, steps, warnings)
        warnings.append("analog output: the Pi has no analog input, so this needs an ADC (MCP3008, ADS1115 or the Pico's ADC)")
        gpio = PINMAP["free_gpio"][0]
        if any(p.get("name", "").upper().startswith("DO") for p in record.get("pins", [])):
            steps.append(Step("DO", gpio["pin"], f"GPIO{gpio['bcm']}", "signal", "the digital output works without an ADC"))
    elif iface == "onewire":
        _power(record, steps, warnings)
        steps.append(Step("DATA", PINMAP["onewire"]["DATA"]["pin"], "GPIO4 (1-Wire)", "signal",
                          "4.7 kOhm pull-up from data to 3.3 V"))
    else:
        warnings.append(f"interface '{iface}' is not supported by the wiring advisor; wire it by hand from the datasheet")
    return Wiring(steps, warnings)
