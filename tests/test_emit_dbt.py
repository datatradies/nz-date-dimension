import csv
import io
import re
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.relative import RELATIVE_COLUMNS
from nz_date_dimension.holidays_nz import NZ_SUBDIVISIONS
from nz_date_dimension.emit_dbt import build_dbt_model_sql, build_dbt_seed_csv, SEED_COLUMNS

def test_seed_csv_has_holiday_and_regional_columns_only():
    rows = build_dataset(2025, 2025)  # 365 rows
    csv_text = build_dbt_seed_csv(rows)
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(reader) == 365
    assert reader[0].keys() == set(SEED_COLUMNS)
    assert "Date" in SEED_COLUMNS and "IsHoliday" in SEED_COLUMNS
    assert "HolidayName" in SEED_COLUMNS and "IsObserved" in SEED_COLUMNS
    for code in NZ_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in SEED_COLUMNS
    # calendar/fiscal columns are NOT duplicated into the seed -- the dbt
    # model derives them from the date_spine itself.
    assert "Year" not in SEED_COLUMNS and "FiscalYear" not in SEED_COLUMNS

def test_seed_csv_christmas_row_is_a_holiday():
    rows = build_dataset(2025, 2025)
    csv_text = build_dbt_seed_csv(rows)
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    xmas = next(r for r in reader if r["Date"] == "2025-12-25")
    assert xmas["IsHoliday"] == "true"
    assert "Christmas" in xmas["HolidayName"]

def test_dbt_model_uses_date_spine_and_pins_dbt_utils_version():
    sql = build_dbt_model_sql(start_year=2015, end_year=2050, fiscal_start_month=4)
    assert "dbt_utils.date_spine" in sql
    assert "dbt_utils" in sql and "1.1" in sql  # version pin comment

def test_dbt_model_has_boundary_note_about_inclusive_end_date():
    sql = build_dbt_model_sql()
    assert "inclusive" in sql.lower()
    assert "end_date" in sql

def test_dbt_model_references_the_holiday_seed():
    sql = build_dbt_model_sql()
    assert "ref('nz_date_dimension_holidays')" in sql

def test_dbt_model_uses_current_date_for_relative_columns():
    sql = build_dbt_model_sql()
    assert "current_date()" in sql.lower()

def test_dbt_model_includes_every_stable_and_relative_column():
    sql = build_dbt_model_sql()
    for col in STABLE_COLUMNS:
        assert col in sql, f"missing stable column {col}"
    for col in RELATIVE_COLUMNS:
        assert col in sql, f"missing relative column {col}"

def test_dbt_model_has_no_dangling_trailing_commas():
    # A trailing comma immediately before FROM or a closing CTE paren is a
    # syntax error in Snowflake SQL -- guards against string-templating
    # bugs in the column lists (e.g. the 17 regional-flag columns).
    sql = build_dbt_model_sql()
    assert not re.search(r",\s*\n\s*from\b", sql, re.IGNORECASE)
    assert not re.search(r",\s*\n\)", sql)
