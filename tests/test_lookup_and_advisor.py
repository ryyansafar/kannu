import json
from pathlib import Path

import pytest

from kannu.advisor import plan_wiring
from kannu.bus import FakeBus
from kannu.lookup import prove_identity, validate_lookup

RAW = json.loads((Path(__file__).resolve().parent.parent / "data" / "lookups_raw.json").read_text())
MPU = RAW["MPU6050"]


def test_real_devin_lookup_for_the_mpu6050_validates():
    v = validate_lookup(MPU, live_addresses={0x68})
    assert v.ok, v.errors


def test_missing_required_field_is_an_error():
    bad = {k: v for k, v in MPU.items() if k != "voltage_max"}
    v = validate_lookup(bad)
    assert not v.ok and any("voltage_max" in e for e in v.errors)


def test_live_address_not_in_datasheet_is_an_error():
    v = validate_lookup(MPU, live_addresses={0x50})
    assert not v.ok and any("0x50" in e for e in v.errors)


def test_five_volt_logic_is_a_warning_not_a_silent_pass():
    rec = dict(MPU, logic_level=5.0)
    v = validate_lookup(rec)
    assert any("5" in w and "level" in w.lower() for w in v.warnings)


def test_low_confidence_is_a_warning():
    v = validate_lookup(dict(MPU, confidence=0.3))
    assert any("confidence" in w for w in v.warnings)


def test_id_register_without_value_is_an_error():
    v = validate_lookup(dict(MPU, id_register="0x75", id_value=None))
    assert not v.ok


def test_prove_identity_reads_the_real_chip():
    bus = FakeBus()
    bus.plug(0x68, {0x75: 0x68})
    ok, detail = prove_identity(dict(MPU, id_register="0x75", id_value="0x68"), bus, 0x68)
    assert ok and "0x68" in detail
    bus.plug(0x68, {0x75: 0x70})
    ok, detail = prove_identity(dict(MPU, id_register="0x75", id_value="0x68"), bus, 0x68)
    assert not ok and "0x70" in detail


def test_prove_identity_without_register_cannot_prove():
    ok, detail = prove_identity(dict(MPU, id_register=None, id_value=None), FakeBus(), 0x68)
    assert not ok and "no identity register" in detail


def wiring_for(key):
    return plan_wiring(RAW[key])


def test_i2c_module_goes_to_the_i2c_pins_on_3v3():
    w = wiring_for("MPU6050")
    pins = {s.module_pin: s.pi_pin for s in w.steps}
    assert pins["SDA"] == 3 and pins["SCL"] == 5
    assert pins["VCC"] == 1 and pins["GND"] == 6
    assert not w.warnings or all("5 V" not in x for x in w.warnings)


def test_every_planned_pin_comes_from_the_safe_table():
    from kannu.advisor import ALLOWED_PINS
    for key in RAW:
        if not RAW[key]:
            continue
        for s in plan_wiring(RAW[key]).steps:
            assert s.pi_pin in ALLOWED_PINS, (key, s)


def test_analog_module_warns_about_the_missing_adc():
    w = wiring_for("MQ135")
    assert any("analog" in x.lower() and "adc" in x.lower() for x in w.warnings)


def test_digital_module_gets_a_free_gpio_for_its_signal():
    w = wiring_for("DHT11")
    sig = [s for s in w.steps if s.kind == "signal"]
    assert sig and sig[0].pi_pin in {11, 13, 15, 16, 18, 22}


def test_unknown_interface_is_refused_not_guessed():
    rec = dict(MPU, interface="uart")
    w = plan_wiring(rec)
    assert w.steps == [] and w.warnings
