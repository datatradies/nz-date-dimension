"""Tests for the country-driven holidays engine (refactored from
holidays_nz.py per spec §7: "Refactor holidays_nz.py -> a generic
country-driven holidays module. Keep NZ behaviour byte-identical.").

NZ cases mirror the old tests/test_holidays_nz.py assertions exactly (same
dates, same expected values) but through the new country-parameterised
API -- this is the behavioural half of the NZ regression guard (the CSV
byte-identical test in test_build.py/test_cli.py is the output half).

AU cases exercise the "diff" observed-detection strategy (spec §7
resolution 4): AU's Australia-Day make-up Monday has no "(observed)"
suffix and REMOVES the original date, so observed = present under
observed=True but NOT under observed=False.
"""
import holidays
from datetime import date
import pytest
from nz_date_dimension.holidays_engine import (
    build_national, national_holiday_columns, warn_if_beyond_cap, NationalHolidays,
)
from nz_date_dimension.countries import NZ, AU

def nz_cols(d, y0, y1):
    nat = build_national(NZ, y0, y1)
    return national_holiday_columns(d, nat, is_weekend=d.isoweekday() >= 6)

def au_cols(d, y0, y1):
    nat = build_national(AU, y0, y1)
    return national_holiday_columns(d, nat, is_weekend=d.isoweekday() >= 6)

# --- NZ regression: identical assertions to the pre-refactor holidays_nz tests ---

def test_nz_christmas_is_holiday_and_not_business_day():
    c = nz_cols(date(2025, 12, 25), 2025, 2025)
    assert c["IsHoliday"] is True and c["IsBusinessDay"] is False
    assert "Christmas" in c["HolidayName"]

def test_nz_waitangi_mondayisation_2021():
    observed = nz_cols(date(2021, 2, 8), 2021, 2021)
    assert observed["IsHoliday"] is True
    assert observed["IsObserved"] is True
    assert observed["IsBusinessDay"] is False

def test_nz_waitangi_actual_weekend_date_is_not_observed():
    actual = nz_cols(date(2021, 2, 6), 2021, 2021)
    assert actual["IsHoliday"] is True
    assert actual["IsObserved"] is False
    assert actual["IsBusinessDay"] is False

def test_nz_new_year_mondayisation_2022():
    for observed_day in (date(2022, 1, 3), date(2022, 1, 4)):
        c = nz_cols(observed_day, 2022, 2022)
        assert c["IsHoliday"] is True
        assert c["IsObserved"] is True
        assert c["IsBusinessDay"] is False

def test_nz_matariki_2022():
    assert nz_cols(date(2022, 6, 24), 2022, 2022)["IsHoliday"] is True

def test_nz_matariki_not_before_2022():
    assert nz_cols(date(2021, 6, 24), 2021, 2021)["IsHoliday"] is False

def test_nz_qe2_memorial_one_off_2022():
    assert nz_cols(date(2022, 9, 26), 2022, 2022)["IsHoliday"] is True

def test_nz_ordinary_weekday_is_business_day():
    c = nz_cols(date(2025, 7, 23), 2025, 2025)
    assert c["IsHoliday"] is False and c["IsBusinessDay"] is True

def test_nz_warns_beyond_matariki_cap():
    with pytest.warns(UserWarning, match="Matariki"):
        warn_if_beyond_cap(NZ, 2053)

def test_nz_does_not_warn_within_matariki_cap():
    with warnings_none():
        warn_if_beyond_cap(NZ, 2052)

def warnings_none():
    import warnings as _w
    class _Ctx:
        def __enter__(self):
            _w.simplefilter("error")
            return self
        def __exit__(self, *a):
            _w.resetwarnings()
    return _Ctx()

# --- AU: national (no-subdiv) layer -- fixed common holidays, never shifted ---
# (python-holidays' Australia() with no subdiv literally never calls its own
# observed-shift logic -- there is no single nationally-legislated
# Mondayisation rule in Australia, only state-level ones. Verified live
# against holidays==0.101.)

def test_au_national_australia_day_present_on_nominal_date():
    # 26 Jan 2026 is a Monday -- present as a holiday on its own nominal date
    # with no shifting needed.
    c = au_cols(date(2026, 1, 26), 2026, 2026)
    assert c["IsHoliday"] is True
    assert "Australia Day" in c["HolidayName"]

def test_au_national_layer_never_flags_observed():
    # 26 Jan 2025 is a Sunday. The no-subdiv national layer does not shift
    # it (that's a state-level concern) -- IsHoliday is True on the actual
    # Sunday and there's no separate observed Monday at the national level.
    sunday = au_cols(date(2025, 1, 26), 2025, 2025)
    assert sunday["IsHoliday"] is True
    assert sunday["IsObserved"] is False
    monday = au_cols(date(2025, 1, 27), 2025, 2025)
    assert monday["IsHoliday"] is False

def test_au_national_christmas_is_holiday_and_not_business_day():
    c = au_cols(date(2025, 12, 25), 2025, 2025)
    assert c["IsHoliday"] is True and c["IsBusinessDay"] is False
    assert "Christmas" in c["HolidayName"]

def test_au_ordinary_weekday_is_business_day():
    c = au_cols(date(2025, 7, 23), 2025, 2025)
    assert c["IsHoliday"] is False and c["IsBusinessDay"] is True

def test_au_does_not_warn_beyond_any_year_no_cap():
    with warnings_none():
        warn_if_beyond_cap(AU, 2100)

# --- Country-agnostic "diff" observed-detection mechanism (spec §7
# resolution 4), exercised directly against AU's real per-state calendars,
# where the make-up Monday genuinely has no "(observed)" suffix. ---

def test_diff_strategy_detects_au_state_makeup_monday_as_observed():
    # NSW, Australia Day 2025: 26 Jan (Sun) removed under observed=True,
    # replaced by 27 Jan (Mon) "Australia Day" with NO "(observed)" suffix.
    years = range(2025, 2026)
    observed_true = holidays.Australia(subdiv="NSW", years=years, observed=True)
    observed_false = holidays.Australia(subdiv="NSW", years=years, observed=False)
    national = NationalHolidays(observed_true, observed_false, strategy="diff")

    monday = national_holiday_columns(date(2025, 1, 27), national, is_weekend=False)
    assert monday["IsHoliday"] is True
    assert monday["HolidayName"] == "Australia Day"
    assert "(observed)" not in monday["HolidayName"]
    assert monday["IsObserved"] is True  # present under observed=True, absent under observed=False

    sunday = national_holiday_columns(date(2025, 1, 26), national, is_weekend=True)
    assert sunday["IsHoliday"] is False  # removed under observed=True (the make-up day replaces it)
    assert sunday["IsObserved"] is False

def test_diff_strategy_non_shifted_holiday_is_not_observed():
    years = range(2025, 2026)
    observed_true = holidays.Australia(subdiv="NSW", years=years, observed=True)
    observed_false = holidays.Australia(subdiv="NSW", years=years, observed=False)
    national = NationalHolidays(observed_true, observed_false, strategy="diff")
    c = national_holiday_columns(date(2025, 12, 25), national, is_weekend=False)  # Thursday
    assert c["IsHoliday"] is True
    assert c["IsObserved"] is False

def test_suffix_strategy_still_used_for_nz_national_holidays_object():
    nat = build_national(NZ, 2021, 2021)
    assert isinstance(nat, NationalHolidays)
    assert nat.strategy == "suffix"

def test_diff_strategy_used_for_au_national_holidays_object():
    nat = build_national(AU, 2025, 2025)
    assert nat.strategy == "diff"
