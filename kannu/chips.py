"""Names a chip from its bus address and identity register. The register read is the ground truth."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .bus import Bus

REQUIRED = {"part", "interface", "addresses"}


@dataclass(frozen=True)
class ChipMatch:
    part: str
    status: str   # confirmed | mismatch | address_only
    detail: str


class ChipDB:
    def __init__(self, chips: dict[str, dict]):
        self.chips = chips

    @classmethod
    def load(cls, path: str | Path) -> "ChipDB":
        data = json.loads(Path(path).read_text())
        for key, chip in data.items():
            missing = REQUIRED - set(chip)
            if missing:
                raise ValueError(f"chip {key} is missing {sorted(missing)}")
        return cls(data)

    def at(self, addr: int) -> list[dict]:
        return [c for c in self.chips.values()
                if addr in {int(a, 16) for a in c.get("addresses", [])}]

    def known_addresses(self) -> set[int]:
        return {int(a, 16) for c in self.chips.values() for a in c.get("addresses", [])}


def identify(bus: Bus, addr: int, db: ChipDB) -> ChipMatch | None:
    candidates = db.at(addr)
    if not candidates:
        return None
    mismatch: ChipMatch | None = None
    address_only: ChipMatch | None = None
    for chip in candidates:
        reg = chip.get("id_register")
        if reg is None:
            address_only = address_only or ChipMatch(chip["part"], "address_only",
                                                     f"answers at 0x{addr:02x}; no identity register to confirm it")
            continue
        try:
            got = bus.read_byte_data(addr, int(reg, 16))
        except OSError as exc:
            mismatch = mismatch or ChipMatch(chip["part"], "mismatch", f"could not read {reg}: {exc}")
            continue
        names = {int(k, 16): v for k, v in chip.get("id_values", {}).items()}
        if got in names:
            return ChipMatch(names[got], "confirmed", f"register {reg} returned 0x{got:02x}")
        mismatch = mismatch or ChipMatch(chip["part"], "mismatch",
                                         f"register {reg} returned 0x{got:02x}, not one of "
                                         f"{', '.join(sorted(chip.get('id_values', {})))}")
    return mismatch or address_only
