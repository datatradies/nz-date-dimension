"""Shared, dialect-parameterised SQL generation for T-SQL / Snowflake /
Databricks (spec §8). Per spec: SQL is data MATERIALIZATION, not
in-database computation — Python already did the thinking (Matariki,
Mondayisation, provincial logic); these helpers just render the identical
pre-computed rows as CREATE TABLE + INSERT, plus a companion VIEW that
derives the relative/time-intelligence columns from CURRENT_DATE so they
stay live on refresh (spec §7, §4.5).

emit_tsql.py / emit_snowflake.py / emit_databricks.py are the public
entry points; this module only holds logic genuinely shared across all
three dialects (column typing, literal formatting, view SQL shape),
matching the existing repo pattern of regional.py importing shared
constants from holidays_nz.py.
"""
from .build import STABLE_COLUMNS

_DATE_COLUMNS = {
    "Date", "StartOfMonth", "EndOfMonth", "StartOfQuarter", "EndOfQuarter",
    "StartOfYear", "EndOfYear", "FiscalStartOfYear", "FiscalEndOfYear",
}
_STRING_COLUMNS = {
    "QuarterName", "MonthName", "MonthShort", "DayName", "DayShort",
    "FiscalYearLabel", "HolidayName",
}
_BOOL_COLUMNS_EXACT = {"IsWeekend", "IsWeekday", "IsHoliday", "IsObserved", "IsBusinessDay"}

def column_kind(col: str) -> str:
    """Classify a STABLE_COLUMNS name as 'date' | 'str' | 'bool' | 'int'."""
    if col in _DATE_COLUMNS:
        return "date"
    if col in _STRING_COLUMNS:
        return "str"
    if col in _BOOL_COLUMNS_EXACT or col.startswith("IsHoliday_"):
        return "bool"
    return "int"

# Per-dialect syntax. Each value is either a constant string or a small
# callable producing an SQL expression fragment — kept as data so
# create_table_sql / insert_statements_sql / relative_view_sql stay
# dialect-agnostic and the three emit_*.py wrappers stay thin.
DIALECTS = {
    "tsql": {
        "quote": lambda c: f"[{c}]",
        "types": {"date": "DATE", "int": "INT", "bool": "BIT", "str": "NVARCHAR(60)"},
        "true": "1", "false": "0",
        "today": "CAST(GETDATE() AS DATE)",
        "year": lambda x: f"YEAR({x})",
        "month": lambda x: f"MONTH({x})",
        "quarter": lambda x: f"DATEPART(QUARTER, {x})",
        # DATEFIRST-independent ISO weekday (Mon=1..Sun=7); see PLAN-B-REPORT.md.
        "iso_weekday": lambda x: f"((DATEPART(WEEKDAY, {x}) + @@DATEFIRST - 2) % 7) + 1",
        "date_from_parts": lambda y, m, d: f"DATEFROMPARTS({y}, {m}, {d})",
        "add_years": lambda x, n: f"DATEADD(year, {n}, {x})",
        "add_days": lambda x, n: f"DATEADD(day, {n}, {x})",
        "datediff_day": lambda a, b: f"DATEDIFF(day, {a}, {b})",
        "int_div": lambda a, b: f"(({a}) / {b})",
        "pos_mod": lambda a, m: f"((({a}) % {m}) + {m}) % {m}",
        "bool_wrap": lambda cond: f"CASE WHEN {cond} THEN 1 ELSE 0 END",
        "statement_sep": "\nGO\n",
    },
    "snowflake": {
        "quote": lambda c: f'"{c}"',
        "types": {"date": "DATE", "int": "NUMBER(9,0)", "bool": "BOOLEAN", "str": "VARCHAR(60)"},
        "true": "TRUE", "false": "FALSE",
        "today": "CURRENT_DATE()",
        "year": lambda x: f"YEAR({x})",
        "month": lambda x: f"MONTH({x})",
        "quarter": lambda x: f"QUARTER({x})",
        "iso_weekday": lambda x: f"DAYOFWEEKISO({x})",  # native ISO weekday, Mon=1..Sun=7
        "date_from_parts": lambda y, m, d: f"DATE_FROM_PARTS({y}, {m}, {d})",
        "add_years": lambda x, n: f"DATEADD(year, {n}, {x})",
        "add_days": lambda x, n: f"DATEADD(day, {n}, {x})",
        "datediff_day": lambda a, b: f"DATEDIFF(day, {a}, {b})",
        # Snowflake '/' is decimal division (7/3 -> 2.333...), unlike T-SQL
        # (INT truncates) and Databricks (DIV) -- FLOOR to keep fiscal
        # quarter/week offsets integer-typed per spec 4.5 (I1).
        "int_div": lambda a, b: f"FLOOR(({a}) / {b})",
        "pos_mod": lambda a, m: f"MOD(MOD({a}, {m}) + {m}, {m})",
        "bool_wrap": lambda cond: cond,
        "statement_sep": "\n;\n",
    },
    "databricks": {
        "quote": lambda c: f"`{c}`",
        "types": {"date": "DATE", "int": "INT", "bool": "BOOLEAN", "str": "STRING"},
        "true": "TRUE", "false": "FALSE",
        "today": "current_date()",
        "year": lambda x: f"year({x})",
        "month": lambda x: f"month({x})",
        "quarter": lambda x: f"quarter({x})",
        # Spark dayofweek() is fixed Sun=1..Sat=7; convert to ISO Mon=1..Sun=7.
        "iso_weekday": lambda x: f"(((dayofweek({x}) + 5) % 7) + 1)",
        "date_from_parts": lambda y, m, d: f"make_date({y}, {m}, {d})",
        "add_years": lambda x, n: f"add_months({x}, {n} * 12)",
        "add_days": lambda x, n: f"date_add({x}, {n})",
        "datediff_day": lambda a, b: f"datediff({b}, {a})",  # Spark: datediff(end, start)
        "int_div": lambda a, b: f"(({a}) DIV {b})",
        "pos_mod": lambda a, m: f"((({a}) % {m}) + {m}) % {m}",
        "bool_wrap": lambda cond: cond,
        "statement_sep": "\n;\n",
    },
}

def sql_literal(value, kind: str, dialect: str) -> str:
    cfg = DIALECTS[dialect]
    if value is None:
        return "NULL"
    if kind == "bool":
        return cfg["true"] if value else cfg["false"]
    if kind == "date":
        return f"'{value.isoformat()}'"
    if kind == "int":
        return str(int(value))
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"

def create_table_sql(table_name: str, dialect: str) -> str:
    cfg = DIALECTS[dialect]
    q = cfg["quote"]
    col_defs = []
    for col in STABLE_COLUMNS:
        sql_type = cfg["types"][column_kind(col)]
        nullability = "NULL" if col == "HolidayName" else "NOT NULL"
        col_defs.append(f"    {q(col)} {sql_type} {nullability}")
    if dialect == "databricks":
        # PRIMARY KEY is a hard syntax error on Databricks outside Unity
        # Catalog (and merely informational/unenforced even inside it) --
        # document the natural key as a comment instead of a real
        # constraint so the script runs on any Databricks target (M3).
        note = f"-- Primary key: {q('Date')} (informational only -- requires Unity Catalog)\n"
        return note + f"CREATE TABLE {q(table_name)} (\n" + ",\n".join(col_defs) + "\n);"
    # T-SQL/Snowflake PRIMARY KEY constraints are fully supported.
    col_defs.append(f"    CONSTRAINT PK_{table_name} PRIMARY KEY ({q('Date')})")
    return f"CREATE TABLE {q(table_name)} (\n" + ",\n".join(col_defs) + "\n);"

def insert_statements_sql(rows: list, table_name: str, dialect: str, batch_size: int = 1000) -> list:
    cfg = DIALECTS[dialect]
    q = cfg["quote"]
    col_list = ", ".join(q(c) for c in STABLE_COLUMNS)
    statements = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        value_rows = [
            "(" + ", ".join(sql_literal(row[c], column_kind(c), dialect) for c in STABLE_COLUMNS) + ")"
            for row in batch
        ]
        statement = f"INSERT INTO {q(table_name)} ({col_list}) VALUES\n" + ",\n".join(value_rows) + ";"
        statements.append(statement)
    return statements

def relative_select_sql(table_name: str, dialect: str, fiscal_start_month: int = 4) -> str:
    """The reusable core of the relative-columns query: a `WITH
    today_attrs AS (...) SELECT ... FROM <table_name> AS t CROSS JOIN
    today_attrs AS c` fragment (no trailing semicolon, no CREATE VIEW
    wrapper) deriving the relative/time-intelligence columns (spec §4.5)
    from CURRENT_DATE, layered on top of the materialized base table's own
    stable columns (Year, Month, Quarter, DayOfWeek, FiscalYear,
    FiscalQuarter) rather than re-deriving calendar attributes from
    scratch — the base table already computed those once.

    `table_name` may be a real table OR a CTE name — emit_dbt.py reuses
    this verbatim against its own staged CTE so the relative-column
    formulas can never drift between the raw Snowflake SQL emitter and the
    dbt model.
    """
    cfg = DIALECTS[dialect]
    q = cfg["quote"]
    tq = lambda c: f"t.{q(c)}"  # quoted base-table column reference (C1)
    fsm = fiscal_start_month
    today = cfg["today"]

    today_year = cfg["year"](today)
    today_month = cfg["month"](today)
    today_quarter = cfg["quarter"](today)
    today_iso_weekday = cfg["iso_weekday"](today)

    fiscal_start_this_year = cfg["date_from_parts"](today_year, str(fsm), "1")
    fiscal_start_prior_year = cfg["date_from_parts"](f"{today_year} - 1", str(fsm), "1")
    today_fiscal_start = (
        f"CASE WHEN {today_month} >= {fsm} "
        f"THEN {fiscal_start_this_year} ELSE {fiscal_start_prior_year} END"
    )
    today_fiscal_end = cfg["add_days"](cfg["add_years"](today_fiscal_start, 1), -1)
    today_fiscal_year = cfg["year"](today_fiscal_end)
    today_fiscal_month = f"{cfg['pos_mod'](f'{today_month} - {fsm}', 12)} + 1"
    today_fiscal_quarter = cfg["int_div"](f"({today_fiscal_month}) - 1", 3) + " + 1"

    cte_sql = (
        "WITH today_attrs AS (\n"
        "    SELECT\n"
        f"        {today} AS TodayDate,\n"
        f"        {today_year} AS TodayYear,\n"
        f"        {today_month} AS TodayMonth,\n"
        f"        {today_quarter} AS TodayQuarter,\n"
        f"        {today_iso_weekday} AS TodayIsoWeekday,\n"
        f"        {today_fiscal_year} AS TodayFiscalYear,\n"
        f"        {today_fiscal_quarter} AS TodayFiscalQuarter\n"
        ")"
    )

    t_date = tq("Date")
    day_offset = cfg["datediff_day"]("c.TodayDate", t_date)
    week_offset = cfg["int_div"](f"({day_offset}) - {tq('DayOfWeek')} + c.TodayIsoWeekday", 7)
    month_offset = f"({tq('Year')} - c.TodayYear) * 12 + ({tq('Month')} - c.TodayMonth)"
    quarter_offset = f"({tq('Year')} * 4 + {tq('Quarter')}) - (c.TodayYear * 4 + c.TodayQuarter)"
    year_offset = f"{tq('Year')} - c.TodayYear"
    fiscal_year_offset = f"{tq('FiscalYear')} - c.TodayFiscalYear"
    fiscal_quarter_offset = (
        f"({tq('FiscalYear')} * 4 + {tq('FiscalQuarter')}) - "
        "(c.TodayFiscalYear * 4 + c.TodayFiscalQuarter)"
    )
    rolling_month_diff = f"(c.TodayYear * 12 + c.TodayMonth) - ({tq('Year')} * 12 + {tq('Month')})"

    last7 = cfg["add_days"]("c.TodayDate", -6)
    last30 = cfg["add_days"]("c.TodayDate", -29)
    last90 = cfg["add_days"]("c.TodayDate", -89)

    bw = cfg["bool_wrap"]
    select_cols = [
        "t.*",
        f"{day_offset} AS {q('DayOffset')}",
        f"{week_offset} AS {q('WeekOffset')}",
        f"{month_offset} AS {q('MonthOffset')}",
        f"{quarter_offset} AS {q('QuarterOffset')}",
        f"{year_offset} AS {q('YearOffset')}",
        f"{fiscal_year_offset} AS {q('FiscalYearOffset')}",
        f"{fiscal_quarter_offset} AS {q('FiscalQuarterOffset')}",
        f"{bw(f'{t_date} = c.TodayDate')} AS {q('IsToday')}",
        f"{bw(f'({week_offset}) = 0')} AS {q('IsCurrentWeek')}",
        f"{bw(f'({month_offset}) = 0')} AS {q('IsCurrentMonth')}",
        f"{bw(f'({quarter_offset}) = 0')} AS {q('IsCurrentQuarter')}",
        f"{bw(f'({year_offset}) = 0')} AS {q('IsCurrentYear')}",
        f"{bw(f'({fiscal_year_offset}) = 0')} AS {q('IsCurrentFiscalYear')}",
        f"{bw(f'(({year_offset}) = 0) AND ({t_date} <= c.TodayDate)')} AS {q('IsCalendarYTD')}",
        f"{bw(f'(({fiscal_year_offset}) = 0) AND ({t_date} <= c.TodayDate)')} AS {q('IsFiscalYTD')}",
        f"{bw(f'(({month_offset}) = 0) AND ({t_date} <= c.TodayDate)')} AS {q('IsMonthToDate')}",
        f"{bw(f'(({quarter_offset}) = 0) AND ({t_date} <= c.TodayDate)')} AS {q('IsQuarterToDate')}",
        f"{bw(f'{t_date} >= {last7} AND {t_date} <= c.TodayDate')} AS {q('IsLast7Days')}",
        f"{bw(f'{t_date} >= {last30} AND {t_date} <= c.TodayDate')} AS {q('IsLast30Days')}",
        f"{bw(f'{t_date} >= {last90} AND {t_date} <= c.TodayDate')} AS {q('IsLast90Days')}",
        f"{bw(f'({month_offset}) = -1')} AS {q('IsPriorMonth')}",
        f"{bw(f'({year_offset}) = -1')} AS {q('IsPriorYear')}",
        f"{bw(f'(({rolling_month_diff}) BETWEEN 0 AND 11) AND ({t_date} <= c.TodayDate)')} AS {q('IsRolling12Months')}",
    ]

    return (
        f"{cte_sql}\n"
        "SELECT\n    " + ",\n    ".join(select_cols) + "\n"
        f"FROM {q(table_name)} AS t\n"
        "CROSS JOIN today_attrs AS c"
    )

def relative_view_sql(table_name: str, view_name: str, dialect: str, fiscal_start_month: int = 4) -> str:
    """CREATE VIEW wrapping relative_select_sql() — see that function for
    the actual relative-column logic (spec §7, §8).
    """
    q = DIALECTS[dialect]["quote"]
    return f"CREATE VIEW {q(view_name)} AS\n{relative_select_sql(table_name, dialect, fiscal_start_month)};"
