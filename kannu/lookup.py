"""Plain-code checks of what a Devin datasheet lookup returned. Never trust it blindly: the real chip is the proof."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema

from .bus import Bus

SCHEMA = json.loads((Path(__file__).resolve().parent.parent / "devin" / "lookup.schema.json").read_text())
PI_LOGIC = 3.3
LOW_CONFIDENCE = 0.6


@dataclass(frozen=True)
class Validation:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_lookup(record: dict, live_addresses: set[int] | None = None) -> Validation:
    errors: list[str] = []
    warnings: list[str] = []
    for err in jsonschema.Draft7Validator(SCHEMA).iter_errors(record):
        errors.append(f"{'.'.join(str(p) for p in err.path) or 'record'}: {err.message}")
    if record.get("interface") == "i2c" and not record.get("i2c_addresses"):
        errors.append("i2c part without i2c_addresses")
    if record.get("id_register") and not record.get("id_value"):
        errors.append("id_register given without an id_value")
    if live_addresses and record.get("i2c_addresses"):
        listed = {int(a, 16) for a in record["i2c_addresses"]}
        for addr in sorted(live_addresses):
            if addr not in listed:
                errors.append(f"live address 0x{addr:02x} is not in the datasheet addresses {sorted(record['i2c_addresses'])}")
    if isinstance(record.get("logic_level"), (int, float)) and record["logic_level"] > PI_LOGIC + 0.3:
        warnings.append(f"signals are {record['logic_level']} V: a Pi pin is 3.3 V only, use a divider or level shifter")
    if isinstance(record.get("confidence"), (int, float)) and record["confidence"] < LOW_CONFIDENCE:
        warnings.append(f"low confidence ({record['confidence']}): check the datasheet by hand")
    return Validation(not errors, errors, warnings)


def prove_identity(record: dict, bus: Bus, addr: int) -> tuple[bool, str]:
    reg, want = record.get("id_register"), record.get("id_value")
    if not reg or not want:
        return False, "no identity register to read, so the address alone cannot prove the chip"
    try:
        got = bus.read_byte_data(addr, int(reg, 16))
    except OSError as exc:
        return False, f"could not read {reg} at 0x{addr:02x}: {exc}"
    if got == int(want, 16):
        return True, f"register {reg} returned 0x{got:02x} as expected"
    return False, f"register {reg} returned 0x{got:02x}, expected {want}"
