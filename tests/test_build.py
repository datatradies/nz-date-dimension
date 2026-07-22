from datetime import date
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.columns import stable_columns

# --- NZ regression (unchanged pre-refactor behaviour + defaults) ---

def test_dataset_spans_every_day_inclusive():
    rows = build_dataset(2024, 2024)
    assert len(rows) == 366          # 2024 is a leap year
    assert rows[0]["Date"] == date(2024, 1, 1)
    assert rows[-1]["Date"] == date(2024, 12, 31)

def test_rows_carry_all_stable_columns():
    row = build_dataset(2025, 2025)[0]
    for col in STABLE_COLUMNS:
        assert col in row, f"missing {col}"

def test_business_day_false_on_christmas():
    rows = {r["Date"]: r for r in build_dataset(2025, 2025)}
    assert rows[date(2025, 12, 25)]["IsBusinessDay"] is False

def test_warns_beyond_2052(recwarn):
    build_dataset(2052, 2053)
    assert any("Matariki" in str(w.message) for w in recwarn.list)

def test_default_country_is_nz():
    rows = build_dataset(2025, 2025)
    row = rows[0]
    assert "IsHoliday_AUK" in row  # bare NZ flag, no country param needed

def test_stable_columns_still_exported_and_byte_identical_to_nz_shape():
    assert STABLE_COLUMNS == stable_columns(["NZ"])

def test_default_fiscal_start_month_is_still_april_for_nz():
    # fiscal_start_month=None (the new default) must fall back to NZ's own
    # config (4), not silently break existing April-fiscal-year callers.
    rows = {r["Date"]: r for r in build_dataset(2025, 2025)}
    assert rows[date(2025, 4, 1)]["FiscalMonth"] == 1

# --- AU ---

def test_au_dataset_uses_bare_state_flags():
    rows = build_dataset(2025, 2025, country="AU")
    assert len(rows) == 365
    row = rows[0]
    assert "IsHoliday_WA" in row
    assert "IsHoliday_AUK" not in row  # no NZ flags leak into AU-only output

def test_au_default_fiscal_start_month_is_july_not_april():
    # Regression for spec §7 resolution: --country au must NOT silently get
    # an April fiscal year just because fiscal_start_month wasn't passed.
    rows = {r["Date"]: r for r in build_dataset(2025, 2026, country="AU")}
    row = rows[date(2025, 8, 1)]
    assert row["FiscalYear"] == 2026
    assert row["FiscalStartOfYear"] == date(2025, 7, 1)
    assert row["FiscalEndOfYear"] == date(2026, 6, 30)

def test_au_explicit_fiscal_start_month_overrides_country_default():
    rows = {r["Date"]: r for r in build_dataset(2025, 2025, fiscal_start_month=1, country="AU")}
    assert rows[date(2025, 6, 1)]["FiscalMonth"] == 6  # calendar-year fiscal (start_month=1)

def test_au_state_holiday_does_not_flip_main_business_day():
    # WA Labour Day 2025 = 3 Mar (Monday) is a state-only holiday -- like
    # NZ's provincial anniversaries, it must NOT affect the main
    # IsBusinessDay/IsHoliday (those reflect AU's national-only calendar);
    # it only shows up in the per-state IsHoliday_WA flag.
    rows = {r["Date"]: r for r in build_dataset(2025, 2025, country="AU")}
    row = rows[date(2025, 3, 3)]
    assert row["IsHoliday_WA"] is True
    assert row["IsHoliday"] is False
    assert row["IsBusinessDay"] is True

def test_au_national_holiday_flips_main_business_day():
    rows = {r["Date"]: r for r in build_dataset(2025, 2025, country="AU")}
    xmas = rows[date(2025, 12, 25)]
    assert xmas["IsHoliday"] is True
    assert xmas["IsBusinessDay"] is False

def test_au_does_not_warn_regardless_of_end_year(recwarn):
    build_dataset(2025, 2100, country="AU")
    assert not any("Matariki" in str(w.message) for w in recwarn.list)

# --- Combined ---

def test_combined_dataset_unions_both_countries():
    rows = build_dataset(2025, 2025, country="combined")
    assert len(rows) == 365 + 365
    countries_seen = {r["Country"] for r in rows}
    assert countries_seen == {"NZ", "AU"}

def test_combined_rows_carry_country_prefixed_flags_only():
    rows = build_dataset(2025, 2025, country="combined")
    row = rows[0]
    assert "IsHoliday_NZ_AUK" in row
    assert "IsHoliday_AU_WA" in row
    assert "IsHoliday_AUK" not in row  # bare form must not appear in combined
    assert "IsHoliday_WA" not in row

def test_combined_nz_row_never_carries_au_flags_and_vice_versa():
    # Structural isolation check, independent of which specific dates
    # happen to be holidays: an NZ row's AU_* flags must always be False
    # (never overlaid), and an AU row's NZ_* flags must always be False --
    # regardless of whether that date happens to be a real AU or NZ
    # holiday. Checked across every day of the year, both directions.
    rows = build_dataset(2025, 2025, country="combined")
    au_codes = ("ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA")
    nz_codes = ("AUK", "BOP", "CAN", "CIT", "GIS", "HKB", "MBH", "MWT",
                "NSN", "NTL", "OTA", "STL", "TAS", "TKI", "WGN", "WKO", "WTC")
    for row in rows:
        if row["Country"] == "NZ":
            assert all(row[f"IsHoliday_AU_{code}"] is False for code in au_codes)
        else:
            assert all(row[f"IsHoliday_NZ_{code}"] is False for code in nz_codes)

def test_combined_auckland_anniversary_flags_nz_row_only():
    # Auckland Anniversary 2025 = 27 Jan -- true for NZ's row (via the
    # country-prefixed flag); the AU row on the same date is unaffected
    # (it may or may not itself be an AU holiday, but never because of NZ).
    rows = build_dataset(2025, 2025, country="combined")
    by_key = {(r["Date"], r["Country"]): r for r in rows}
    assert by_key[(date(2025, 1, 27), "NZ")]["IsHoliday_NZ_AUK"] is True

def test_combined_ordinary_weekday_has_every_flag_false():
    # 23 Jul 2025 (Wednesday) is not a holiday anywhere in NZ or AU --
    # every regional flag, for both rows, must be false.
    rows = build_dataset(2025, 2025, country="combined")
    by_key = {(r["Date"], r["Country"]): r for r in rows}
    nz_row = by_key[(date(2025, 7, 23), "NZ")]
    au_row = by_key[(date(2025, 7, 23), "AU")]
    for k, v in nz_row.items():
        if k.startswith("IsHoliday_"):
            assert v is False, f"NZ row {k} unexpectedly true on an ordinary weekday"
    for k, v in au_row.items():
        if k.startswith("IsHoliday_"):
            assert v is False, f"AU row {k} unexpectedly true on an ordinary weekday"

def test_combined_fiscal_columns_are_per_row_country():
    # 1 Aug 2025: NZ row is FY2026 (Apr-start, already mid-year);
    # AU row is FY2026 (Jul-start, just started).
    rows = build_dataset(2025, 2026, country="combined")
    by_key = {(r["Date"], r["Country"]): r for r in rows}
    nz_row = by_key[(date(2025, 8, 1), "NZ")]
    au_row = by_key[(date(2025, 8, 1), "AU")]
    assert nz_row["FiscalYear"] == 2026
    assert nz_row["FiscalStartOfYear"] == date(2025, 4, 1)
    assert au_row["FiscalYear"] == 2026
    assert au_row["FiscalStartOfYear"] == date(2025, 7, 1)

def test_combined_national_holidays_are_per_row_country():
    rows = build_dataset(2025, 2025, country="combined")
    by_key = {(r["Date"], r["Country"]): r for r in rows}
    # ANZAC Day 25 Apr 2025 is a national holiday in both NZ and AU.
    assert by_key[(date(2025, 4, 25), "NZ")]["IsHoliday"] is True
    assert by_key[(date(2025, 4, 25), "AU")]["IsHoliday"] is True
    # Waitangi Day 6 Feb is NZ-only.
    assert by_key[(date(2025, 2, 6), "NZ")]["IsHoliday"] is True
    assert by_key[(date(2025, 2, 6), "AU")]["IsHoliday"] is False

def test_combined_rows_sorted_by_date_then_country():
    rows = build_dataset(2025, 2025, country="combined")
    keys = [(r["Date"], r["Country"]) for r in rows]
    assert keys == sorted(keys)
