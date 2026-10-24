"""The fast path: decides in plain code, with no network and no model, whether a reading can be trusted."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Reading:
    value: float | None
    crc_ok: bool = True


@dataclass(frozen=True)
class Verdict:
    certify: bool
    reason: str | None = None


@dataclass(frozen=True)
class Event:
    reason: str
    value: float | None


@dataclass
class Guard:
    low: float
    high: float
    max_jump: float
    stuck_after: int = 8
    recover_after: int = 3
    power_on_values: tuple[float, ...] = ()
    events: list[Event] = field(default_factory=list)
    _last_good: float | None = field(default=None, repr=False)
    _same_count: int = field(default=0, repr=False)
    _good_streak: int = field(default=0, repr=False)
    _in_fault: bool = field(default=False, repr=False)

    def _fault(self, reason: str, value: float | None) -> Verdict:
        if not self._in_fault:
            self.events.append(Event(reason, value))
        self._in_fault = True
        self._good_streak = 0
        return Verdict(False, reason)

    def check(self, reading: Reading) -> Verdict:
        v = reading.value
        if v is None:
            return self._fault("no_reading", v)
        if not reading.crc_ok:
            return self._fault("bad_crc", v)
        if v in self.power_on_values and self._last_good is not None and abs(self._last_good - v) > self.max_jump:
            return self._fault("power_on_value", v)
        if not (self.low <= v <= self.high):
            return self._fault("out_of_range", v)
        if self._last_good is not None and abs(v - self._last_good) > self.max_jump:
            return self._fault("jump", v)

        # the reading itself looks fine
        self._same_count = self._same_count + 1 if v == self._last_good else 1
        self._last_good = v
        if self._same_count >= self.stuck_after:
            return self._fault("stuck", v)
        if self._in_fault:
            self._good_streak += 1
            if self._good_streak < self.recover_after:
                return Verdict(False, "recovering")
            self._in_fault = False
        return Verdict(True, None)
