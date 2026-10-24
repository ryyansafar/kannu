import json
from pathlib import Path

import pytest

from kannu.bus import FakeBus
from kannu.chips import ChipDB, identify

DB = ChipDB.load(Path(__file__).resolve().parent.parent / "data" / "chips.json")


def bus_with(addr, regs):
    b = FakeBus()
    b.plug(addr, regs)
    return b


def test_mpu6050_is_confirmed_by_its_identity_register():
    m = identify(bus_with(0x68, {0x75: 0x68}), 0x68, DB)
    assert m.part == "MPU6050" and m.status == "confirmed"


def test_a_clone_returning_another_id_is_named_honestly():
    m = identify(bus_with(0x68, {0x75: 0x70}), 0x68, DB)
    assert m.status == "confirmed" and "MPU6500" in m.part


def test_unexpected_id_is_a_mismatch_not_a_guess():
    m = identify(bus_with(0x68, {0x75: 0x42}), 0x68, DB)
    assert m.status == "mismatch" and "0x42" in m.detail


def test_address_only_chip_is_reported_as_unconfirmed():
    m = identify(bus_with(0x3C, {}), 0x3C, DB)
    assert m.part == "SSD1306 OLED" and m.status == "address_only"


def test_unknown_address_returns_none():
    assert identify(bus_with(0x55, {}), 0x55, DB) is None


def test_shared_address_prefers_the_chip_that_can_be_confirmed():
    # 0x68 is both an MPU6050 and a DS3231; the identity register decides
    m = identify(bus_with(0x68, {0x75: 0x68}), 0x68, DB)
    assert m.part == "MPU6050"
    m2 = identify(bus_with(0x68, {0x75: 0x00}), 0x68, DB)
    assert m2.status in ("mismatch", "address_only")


def test_bmp280_vs_bme280():
    assert identify(bus_with(0x76, {0xD0: 0x58}), 0x76, DB).part == "BMP280"
    assert identify(bus_with(0x76, {0xD0: 0x60}), 0x76, DB).part == "BME280"


def test_db_rejects_a_bad_file(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"x": {"part": "X"}}))
    with pytest.raises(ValueError):
        ChipDB.load(p)


def test_db_lists_all_addresses():
    assert {0x68, 0x3C, 0x27, 0x76} <= DB.known_addresses()
