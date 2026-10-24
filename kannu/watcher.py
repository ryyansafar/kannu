"""Spots new sensors: polls the I2C bus, the 1-Wire list and free GPIO pins and reports what changed."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Event:
    kind: str       # i2c_added, i2c_removed, w1_added, w1_removed, gpio_activity
    detail: str
    t: float


def list_w1(root: str = "/sys/bus/w1/devices") -> set[str]:
    """1-Wire devices appear as folders; w1_bus_master1 is the bus itself."""
    try:
        return {n for n in os.listdir(root) if not n.startswith("w1_bus_master")}
    except OSError:
        return set()


class Watcher:
    def __init__(self, i2c_scan: Callable[[], set[int]],
                 w1_list: Callable[[], set[str]] | None = None,
                 gpio_activity: Callable[[], set[int]] | None = None,
                 on_event: Callable[[Event], None] | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self._i2c_scan = i2c_scan
        self._w1_list = w1_list
        self._gpio_activity = gpio_activity
        self._on_event = on_event
        self._clock = clock
        self.known_i2c: set[int] | None = None
        self.known_w1: set[str] | None = None
        self.errors = 0

    def _emit(self, events: list[Event], kind: str, detail: str) -> None:
        ev = Event(kind, detail, self._clock())
        events.append(ev)
        if self._on_event:
            self._on_event(ev)

    def poll(self) -> list[Event]:
        events: list[Event] = []
        try:
            now = self._i2c_scan()
        except Exception:
            self.errors += 1  # a transient error is not a removal
            now = None
        if now is not None:
            if self.known_i2c is not None:
                for addr in sorted(now - self.known_i2c):
                    self._emit(events, "i2c_added", f"0x{addr:02x}")
                for addr in sorted(self.known_i2c - now):
                    self._emit(events, "i2c_removed", f"0x{addr:02x}")
            self.known_i2c = now
        if self._w1_list:
            try:
                w1 = self._w1_list()
            except Exception:
                self.errors += 1
                w1 = None
            if w1 is not None:
                if self.known_w1 is not None:
                    for name in sorted(w1 - self.known_w1):
                        self._emit(events, "w1_added", name)
                    for name in sorted(self.known_w1 - w1):
                        self._emit(events, "w1_removed", name)
                self.known_w1 = w1
        if self._gpio_activity:
            for pin in sorted(self._gpio_activity()):
                self._emit(events, "gpio_activity", f"GPIO{pin}")
        return events
