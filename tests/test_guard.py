from kannu.guard import Guard, Reading


def guard(**kw):
    defaults = dict(low=-10.0, high=60.0, max_jump=5.0, stuck_after=5, recover_after=3, power_on_values=(85.0,))
    defaults.update(kw)
    return Guard(**defaults)


def feed(g, values):
    return [g.check(Reading(v)) for v in values]


def test_normal_readings_are_certified():
    g = guard()
    out = feed(g, [3.0, 3.2, 3.1, 3.3])
    assert all(v.certify for v in out)
    assert all(v.reason is None for v in out)


def test_missing_reading_is_refused():
    v = guard().check(Reading(None))
    assert not v.certify and v.reason == "no_reading"


def test_bad_checksum_is_refused_even_if_the_value_looks_fine():
    v = guard().check(Reading(3.0, crc_ok=False))
    assert not v.certify and v.reason == "bad_crc"


def test_power_on_value_appearing_suddenly_is_a_fault():
    g = guard(high=125.0)
    out = feed(g, [3.0, 3.1, 85.0])
    assert out[-1].reason == "power_on_value" and not out[-1].certify


def test_power_on_value_is_not_a_fault_when_it_is_the_steady_state():
    g = guard(high=125.0, max_jump=10.0, stuck_after=50)
    out = feed(g, [84.0, 85.0, 85.0, 85.0])
    assert out[-1].reason is None


def test_out_of_range_is_refused():
    v = guard().check(Reading(99.0))
    assert v.reason == "out_of_range"


def test_big_jump_is_refused():
    g = guard()
    out = feed(g, [3.0, 3.1, 14.0])
    assert out[-1].reason == "jump"


def test_stuck_value_is_detected_after_n_identical_readings():
    g = guard(stuck_after=4)
    out = feed(g, [3.0, 3.0, 3.0, 3.0])
    assert out[-1].reason == "stuck"
    assert all(v.reason is None for v in out[:-1])


def test_after_a_fault_it_stays_refused_until_enough_good_readings():
    g = guard(recover_after=3)
    feed(g, [3.0, 3.1])
    assert g.check(Reading(None)).reason == "no_reading"
    after = feed(g, [3.2, 3.3, 3.2, 3.4])
    assert [v.certify for v in after] == [False, False, True, True]
    assert after[0].reason == "recovering"


def test_events_log_the_first_fault_only_once_per_run():
    g = guard()
    feed(g, [3.0, None, None, None, 3.1])
    assert [e.reason for e in g.events] == ["no_reading"]


def test_jump_is_measured_from_the_last_good_value_not_the_bad_one():
    g = guard(max_jump=5.0)
    out = feed(g, [3.0, 3.1, 30.0, 3.2])
    assert out[2].reason == "out_of_range" or out[2].reason == "jump"
    assert out[3].reason in (None, "recovering")


def test_defaults_work_without_a_power_on_value():
    g = Guard(low=0, high=100, max_jump=50)
    assert g.check(Reading(85.0)).certify
