"""I2C access behind one interface, so the real Pi and a simulated chip run the same code."""
from __future__ import annotations

import re
import subprocess
from typing import Callable, Protocol, Union

RegisterValue = Union[int, Callable[[], int]]
_ROW = re.compile(r"^([0-7]0):\s*(.*)$")


def parse_i2cdetect(text: str) -> set[int]:
    """Parse the grid printed by `i2cdetect -y N` into a set of 7-bit addresses.
    Entries shown as 'UU' are busy but present, so they count."""
    found: set[int] = set()
    for line in text.splitlines():
        m = _ROW.match(line.strip())
        if not m:
            continue
        row = int(m.group(1), 16)
        for col, cell in enumerate(m.group(2).split()):
            if cell == "--":
                continue
            if cell == "UU":
                found.add(row + col)
            elif re.fullmatch(r"[0-9a-fA-F]{2}", cell):
                found.add(int(cell, 16))
    return found


class Bus(Protocol):
    def read_byte_data(self, addr: int, reg: int) -> int: ...
    def read_i2c_block_data(self, addr: int, reg: int, length: int) -> list[int]: ...
    def write_byte_data(self, addr: int, reg: int, value: int) -> None: ...
    def addresses(self) -> set[int]: ...


class FakeBus:
    """A simulated I2C bus. Mark any demo using it as SIMULATED."""

    def __init__(self) -> None:
        self._devices: dict[int, dict[int, RegisterValue]] = {}

    def plug(self, addr: int, registers: dict[int, RegisterValue]) -> None:
        self._devices[addr] = dict(registers)

    def unplug(self, addr: int) -> None:
        self._devices.pop(addr, None)

    def addresses(self) -> set[int]:
        return set(self._devices)

    def _device(self, addr: int) -> dict[int, RegisterValue]:
        if addr not in self._devices:
            raise OSError(121, "Remote I/O error")
        return self._devices[addr]

    def read_byte_data(self, addr: int, reg: int) -> int:
        val = self._device(addr).get(reg, 0)
        return val() if callable(val) else val

    def read_i2c_block_data(self, addr: int, reg: int, length: int) -> list[int]:
        return [self.read_byte_data(addr, reg + i) for i in range(length)]

    def write_byte_data(self, addr: int, reg: int, value: int) -> None:
        self._device(addr)[reg] = value


class SmbusBus:
    """The real bus on the Pi (needs smbus2 and i2c-tools installed there)."""

    def __init__(self, number: int = 1, runner: Callable[..., str] | None = None) -> None:
        from smbus2 import SMBus  # imported here so laptops without smbus2 can still run tests

        self._number = number
        self._bus = SMBus(number)
        self._runner = runner or self._run_i2cdetect

    def _run_i2cdetect(self, number: int) -> str:
        return subprocess.run(["i2cdetect", "-y", str(number)], capture_output=True, text=True, timeout=5).stdout

    def addresses(self) -> set[int]:
        return parse_i2cdetect(self._runner(self._number))

    def read_byte_data(self, addr: int, reg: int) -> int:
        return self._bus.read_byte_data(addr, reg)

    def read_i2c_block_data(self, addr: int, reg: int, length: int) -> list[int]:
        return self._bus.read_i2c_block_data(addr, reg, length)

    def write_byte_data(self, addr: int, reg: int, value: int) -> None:
        self._bus.write_byte_data(addr, reg, value)
