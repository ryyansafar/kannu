import pytest

from kannu.bus import FakeBus, parse_i2cdetect


I2CDETECT_OUT = """     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- 27 -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
"""


def test_parse_i2cdetect_reads_addresses():
    assert parse_i2cdetect(I2CDETECT_OUT) == {0x27, 0x3C, 0x68}


def test_parse_i2cdetect_handles_uu_busy_markers_and_garbage():
    out = "60: -- -- -- -- -- -- -- -- UU -- -- -- -- -- -- --\nnot a row\n"
    assert parse_i2cdetect(out) == {0x68}


def test_parse_empty():
    assert parse_i2cdetect("") == set()


def test_fakebus_reads_registers_and_raises_for_missing_device():
    bus = FakeBus()
    bus.plug(0x68, {0x75: 0x68, 0x3B: 0x12})
    assert bus.read_byte_data(0x68, 0x75) == 0x68
    assert bus.addresses() == {0x68}
    with pytest.raises(OSError) as exc:
        bus.read_byte_data(0x50, 0x00)
    assert exc.value.errno == 121


def test_fakebus_unplug_removes_the_device():
    bus = FakeBus()
    bus.plug(0x68, {0x75: 0x68})
    bus.unplug(0x68)
    assert bus.addresses() == set()
    with pytest.raises(OSError):
        bus.read_byte_data(0x68, 0x75)


def test_fakebus_unknown_register_reads_zero_like_a_real_chip_default():
    bus = FakeBus()
    bus.plug(0x68, {0x75: 0x68})
    assert bus.read_byte_data(0x68, 0x10) == 0


def test_fakebus_block_read_and_write():
    bus = FakeBus()
    bus.plug(0x76, {0xD0: 0x58, 0xF7: 1, 0xF8: 2, 0xF9: 3})
    assert bus.read_i2c_block_data(0x76, 0xF7, 3) == [1, 2, 3]
    bus.write_byte_data(0x76, 0xF4, 0x27)
    assert bus.read_byte_data(0x76, 0xF4) == 0x27


def test_fakebus_register_can_be_a_callable_for_changing_readings():
    bus = FakeBus()
    values = iter([10, 11, 12])
    bus.plug(0x68, {0x3B: lambda: next(values)})
    assert [bus.read_byte_data(0x68, 0x3B) for _ in range(3)] == [10, 11, 12]
