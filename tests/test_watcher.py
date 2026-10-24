import os

from kannu.watcher import Watcher, list_w1


class Seq:
    """Returns the given values one by one, then repeats the last."""
    def __init__(self, *values):
        self.values = list(values)

    def __call__(self):
        v = self.values.pop(0) if len(self.values) > 1 else self.values[0]
        if isinstance(v, Exception):
            raise v
        return v


def kinds(events):
    return [(e.kind, e.detail) for e in events]


def test_first_poll_records_a_baseline_without_events():
    w = Watcher(i2c_scan=Seq({0x3C}))
    assert w.poll() == []
    assert w.known_i2c == {0x3C}


def test_new_address_raises_one_added_event():
    w = Watcher(i2c_scan=Seq({0x3C}, {0x3C}, {0x3C, 0x68}, {0x3C, 0x68}))
    w.poll()
    assert w.poll() == []
    assert kinds(w.poll()) == [("i2c_added", "0x68")]
    assert w.poll() == []


def test_removed_address_raises_removed_event():
    w = Watcher(i2c_scan=Seq({0x3C, 0x68}, {0x3C}))
    w.poll()
    assert kinds(w.poll()) == [("i2c_removed", "0x68")]


def test_scan_error_is_counted_and_is_not_a_removal():
    w = Watcher(i2c_scan=Seq({0x68}, OSError("bus busy"), {0x68}))
    w.poll()
    assert w.poll() == []
    assert w.errors == 1
    assert w.poll() == []


def test_callback_receives_every_event():
    seen = []
    w = Watcher(i2c_scan=Seq(set(), {0x68}), on_event=seen.append)
    w.poll()
    w.poll()
    assert [e.kind for e in seen] == ["i2c_added"]


def test_one_wire_devices_are_tracked_by_folder_name():
    w = Watcher(i2c_scan=Seq(set()), w1_list=Seq(set(), {"28-0000053a1b2c"}, set()))
    w.poll()
    assert kinds(w.poll()) == [("w1_added", "28-0000053a1b2c")]
    assert kinds(w.poll()) == [("w1_removed", "28-0000053a1b2c")]


def test_gpio_activity_events_name_the_pins():
    w = Watcher(i2c_scan=Seq(set()), gpio_activity=Seq(set(), {17, 27}, set()))
    w.poll()
    assert sorted(kinds(w.poll())) == [("gpio_activity", "GPIO17"), ("gpio_activity", "GPIO27")]
    assert w.poll() == []


def test_events_carry_a_timestamp_from_the_injected_clock():
    w = Watcher(i2c_scan=Seq(set(), {0x68}), clock=lambda: 123.0)
    w.poll()
    assert w.poll()[0].t == 123.0


def test_list_w1_ignores_the_bus_master_and_missing_dir(tmp_path):
    (tmp_path / "w1_bus_master1").mkdir()
    (tmp_path / "28-abc").mkdir()
    assert list_w1(str(tmp_path)) == {"28-abc"}
    assert list_w1(str(tmp_path / "missing")) == set()
