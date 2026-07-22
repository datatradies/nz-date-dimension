import re
from datetime import date
from nz_date_dimension.sql_common import (
    column_kind, sql_literal, create_table_sql, insert_statements_sql,
    relative_view_sql, relative_select_sql, DIALECTS,
)
from nz_date_dimension.build import STABLE_COLUMNS, build_dataset

def test_column_kind_classification():
    assert column_kind("Date") == "date"
    assert column_kind("FiscalStartOfYear") == "date"
    assert column_kind("DateKey") == "int"
    assert column_kind("FiscalYear") == "int"
    assert column_kind("MonthName") == "str"
    assert column_kind("HolidayName") == "str"
    assert column_kind("IsWeekend") == "bool"
    assert column_kind("IsHoliday_AUK") == "bool"
    assert column_kind("IsHoliday_WTC") == "bool"

def test_sql_literal_null_and_types():
    assert sql_literal(None, "str", "tsql") == "NULL"
    assert sql_literal(True, "bool", "tsql") == "1"
    assert sql_literal(False, "bool", "tsql") == "0"
    assert sql_literal(True, "bool", "snowflake") == "TRUE"
    assert sql_literal(False, "bool", "databricks") == "FALSE"
    assert sql_literal(date(2025, 12, 25), "date", "tsql") == "'2025-12-25'"
    assert sql_literal(20251225, "int", "snowflake") == "20251225"
    assert sql_literal("O'Brien", "str", "tsql") == "'O''Brien'"

def test_create_table_has_every_stable_column_for_each_dialect():
    for dialect in DIALECTS:
        ddl = create_table_sql("NZDateDimension", dialect)
        assert "CREATE TABLE" in ddl
        for col in STABLE_COLUMNS:
            assert col in ddl, f"{dialect} DDL missing {col}"
        assert "HolidayName" in ddl

def test_insert_statements_cover_every_row_and_batch_correctly():
    rows = build_dataset(2025, 2025)  # 365 rows
    for dialect in DIALECTS:
        stmts = insert_statements_sql(rows, "NZDateDimension", dialect, batch_size=150)
        assert len(stmts) == 3  # 150 + 150 + 65 rows => ceil(365/150) == 3
        total_row_tuples = sum(s.count("),\n(") + 1 for s in stmts)
        assert total_row_tuples == 365
        for s in stmts:
            assert s.strip().startswith("INSERT INTO")
            assert s.strip().endswith(";")

def test_relative_view_sql_references_base_table_and_current_date():
    for dialect in DIALECTS:
        view = relative_view_sql("NZDateDimension", "vw_NZDateDimensionRelative", dialect,
                                  fiscal_start_month=4)
        assert "CREATE VIEW" in view
        assert "NZDateDimension" in view
        for col in ["DayOffset", "WeekOffset", "MonthOffset", "QuarterOffset", "YearOffset",
                    "FiscalYearOffset", "FiscalQuarterOffset", "IsToday", "IsCurrentWeek",
                    "IsCurrentMonth", "IsCurrentQuarter", "IsCurrentYear",
                    "IsCurrentFiscalYear", "IsCalendarYTD", "IsFiscalYTD", "IsMonthToDate",
                    "IsQuarterToDate", "IsLast7Days", "IsLast30Days", "IsLast90Days",
                    "IsPriorMonth", "IsPriorYear", "IsRolling12Months"]:
            assert col in view, f"{dialect} view missing {col}"

def test_relative_select_sql_quotes_all_base_table_column_references():
    """Regression for review finding C1: create_table_sql() emits quoted,
    case-preserved column names (e.g. "Year" on Snowflake). An unquoted
    t.Year reference in the companion relative view/model folds to T.YEAR
    on Snowflake, which does NOT match the quoted "Year" column -> invalid
    identifier, and the whole relative SELECT fails to compile. Every
    t.<Column> reference must go through the dialect's own quoter, for all
    three SQL dialects (kept consistent even though only Snowflake is
    case-sensitive).
    """
    for dialect in DIALECTS:
        q = DIALECTS[dialect]["quote"]
        quote_char = q("X")[0]  # dialect's opening quote char: " [ `
        sql = relative_select_sql("NZDateDimension", dialect, fiscal_start_month=4)
        # A bare "t.<word>" not immediately followed by the dialect's own
        # quote character is an unquoted, dialect-unsafe base-table
        # reference. "t.*" is fine (wildcard, no identifier to quote).
        bare_refs = re.findall(rf"\bt\.(?!\*)(?!{re.escape(quote_char)})\w+", sql)
        assert not bare_refs, f"{dialect}: unquoted base-table column refs: {bare_refs}"

def test_snowflake_int_div_floors_to_integer():
    """Regression for review finding I1: Snowflake '/' is decimal division
    (7/3 -> 2.333333), unlike T-SQL/Databricks integer division, so
    TodayFiscalQuarter (and any offset built from int_div, e.g.
    WeekOffset) surfaces fractional/decimal instead of the spec's required
    int (spec section 4.5) unless explicitly floored.
    """
    expr = DIALECTS["snowflake"]["int_div"]("a", "b")
    assert expr.upper().startswith("FLOOR("), f"snowflake int_div not floored: {expr}"

def test_relative_select_sql_snowflake_fiscal_quarter_offset_is_floored():
    sql = relative_select_sql("NZDateDimension", "snowflake", fiscal_start_month=4)
    assert "FLOOR(" in sql

def test_databricks_create_table_has_no_enforced_primary_key_constraint():
    """Regression for review finding M3: PRIMARY KEY is a hard syntax error
    on Databricks outside Unity Catalog (and merely informational/
    unenforced even inside it) -- must not appear as a real constraint,
    only (optionally) as a documentation comment.
    """
    ddl = create_table_sql("NZDateDimension", "databricks")
    assert "PRIMARY KEY" not in ddl
    assert "CONSTRAINT" not in ddl

def test_tsql_and_snowflake_create_table_still_declare_primary_key():
    # Unaffected by M3 -- T-SQL and Snowflake PRIMARY KEY is valid there.
    for dialect in ("tsql", "snowflake"):
        ddl = create_table_sql("NZDateDimension", dialect)
        assert "PRIMARY KEY" in ddl
