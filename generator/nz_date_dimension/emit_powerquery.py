"""Power Query (M) emitter (spec §8). Unlike the SQL emitters, the M
script does NOT need a companion object for relative columns — M is
inherently live-on-refresh, so a single query returns the full table
including the dynamic relative/time-intelligence columns computed via
DateTime.LocalNow() (spec §7).

The static rows are materialised the same way as the SQL INSERTs (an
embedded #table literal built from the Python-computed dataset); the
relative columns are then added as a chain of Table.AddColumn steps
mirroring the same logic as relative.py / sql_common.relative_view_sql,
re-expressed in M.
"""
from .build import STABLE_COLUMNS
from .relative import RELATIVE_COLUMNS
from .sql_common import column_kind

def _m_literal(value, kind: str) -> str:
    if value is None:
        return "null"
    if kind == "bool":
        return "true" if value else "false"
    if kind == "date":
        return f"#date({value.year}, {value.month}, {value.day})"
    if kind == "int":
        return str(int(value))
    escaped = str(value).replace('"', '""')
    return f'"{escaped}"'

def _m_row(row: dict) -> str:
    values = ", ".join(_m_literal(row[c], column_kind(c)) for c in STABLE_COLUMNS)
    return "{" + values + "}"

def _source_table_m(rows: list) -> str:
    headers = ", ".join(f'"{c}"' for c in STABLE_COLUMNS)
    row_lines = ",\n        ".join(_m_row(r) for r in rows)
    return (
        "#table(\n"
        f"        {{{headers}}},\n"
        "        {\n"
        f"        {row_lines}\n"
        "        }\n"
        "    )"
    )

# Each relative column's M expression (row context via [ColumnName]) and
# its M type, keyed by name so RELATIVE_COLUMNS stays the single ordering
# source of truth (a KeyError here means relative.py gained a column this
# emitter hasn't caught up to yet).
_RELATIVE_STEP_EXPRESSIONS = {
    "DayOffset": ("Duration.Days([Date] - Today)", "Int64.Type"),
    "WeekOffset": (
        "Int64.From(Duration.Days(Date.StartOfWeek([Date], Day.Monday) - "
        "Date.StartOfWeek(Today, Day.Monday)) / 7)",
        "Int64.Type",
    ),
    "MonthOffset": (
        "(Date.Year([Date]) - Date.Year(Today)) * 12 + (Date.Month([Date]) - Date.Month(Today))",
        "Int64.Type",
    ),
    "QuarterOffset": (
        "(Date.Year([Date]) * 4 + Date.QuarterOfYear([Date])) - "
        "(Date.Year(Today) * 4 + Date.QuarterOfYear(Today))",
        "Int64.Type",
    ),
    "YearOffset": ("Date.Year([Date]) - Date.Year(Today)", "Int64.Type"),
    "FiscalYearOffset": ("[FiscalYear] - TodayFiscalYear", "Int64.Type"),
    "FiscalQuarterOffset": (
        "([FiscalYear] * 4 + [FiscalQuarter]) - (TodayFiscalYear * 4 + TodayFiscalQuarter)",
        "Int64.Type",
    ),
    "IsToday": ("[Date] = Today", "type logical"),
    "IsCurrentWeek": (
        "Date.StartOfWeek([Date], Day.Monday) = Date.StartOfWeek(Today, Day.Monday)",
        "type logical",
    ),
    "IsCurrentMonth": (
        "Date.Year([Date]) = Date.Year(Today) and Date.Month([Date]) = Date.Month(Today)",
        "type logical",
    ),
    "IsCurrentQuarter": (
        "Date.Year([Date]) = Date.Year(Today) and "
        "Date.QuarterOfYear([Date]) = Date.QuarterOfYear(Today)",
        "type logical",
    ),
    "IsCurrentYear": ("Date.Year([Date]) = Date.Year(Today)", "type logical"),
    "IsCurrentFiscalYear": ("[FiscalYear] = TodayFiscalYear", "type logical"),
    "IsCalendarYTD": (
        "Date.Year([Date]) = Date.Year(Today) and [Date] <= Today", "type logical"
    ),
    "IsFiscalYTD": (
        "[FiscalYear] = TodayFiscalYear and [Date] <= Today", "type logical"
    ),
    "IsMonthToDate": (
        "Date.Year([Date]) = Date.Year(Today) and Date.Month([Date]) = Date.Month(Today) "
        "and [Date] <= Today",
        "type logical",
    ),
    "IsQuarterToDate": (
        "Date.Year([Date]) = Date.Year(Today) and "
        "Date.QuarterOfYear([Date]) = Date.QuarterOfYear(Today) and [Date] <= Today",
        "type logical",
    ),
    "IsLast7Days": ("[Date] >= Date.AddDays(Today, -6) and [Date] <= Today", "type logical"),
    "IsLast30Days": ("[Date] >= Date.AddDays(Today, -29) and [Date] <= Today", "type logical"),
    "IsLast90Days": ("[Date] >= Date.AddDays(Today, -89) and [Date] <= Today", "type logical"),
    "IsPriorMonth": (
        "(Date.Year([Date]) - Date.Year(Today)) * 12 + (Date.Month([Date]) - Date.Month(Today)) = -1",
        "type logical",
    ),
    "IsPriorYear": ("Date.Year([Date]) = Date.Year(Today) - 1", "type logical"),
    "IsRolling12Months": (
        "let DiffMonths = (Date.Year(Today) * 12 + Date.Month(Today)) - "
        "(Date.Year([Date]) * 12 + Date.Month([Date])) in "
        "DiffMonths >= 0 and DiffMonths <= 11 and [Date] <= Today",
        "type logical",
    ),
}

def emit_powerquery(rows: list, fiscal_start_month: int = 4) -> str:
    fsm = fiscal_start_month
    bindings = [
        "Today = DateTime.Date(DateTime.LocalNow())",
        f"FiscalStartMonth = {fsm}",
        "TodayFiscalStart = if Date.Month(Today) >= FiscalStartMonth "
        "then #date(Date.Year(Today), FiscalStartMonth, 1) "
        "else #date(Date.Year(Today) - 1, FiscalStartMonth, 1)",
        "TodayFiscalEnd = Date.AddDays(Date.AddYears(TodayFiscalStart, 1), -1)",
        "TodayFiscalYear = Date.Year(TodayFiscalEnd)",
        # M's Number.Mod follows the dividend's sign (unlike Python's %), so
        # a bare Number.Mod(x, 12) goes negative for Jan/Feb/Mar under an
        # April fiscal start -- wrap in the positive-modulo idiom (I2).
        "TodayFiscalMonth = Number.Mod(Number.Mod(Date.Month(Today) - FiscalStartMonth, 12) + 12, 12) + 1",
        "TodayFiscalQuarter = Number.IntegerDivide(TodayFiscalMonth - 1, 3) + 1",
        f"Source = {_source_table_m(rows)}",
    ]

    prev = "Source"
    for col in RELATIVE_COLUMNS:
        expr, m_type = _RELATIVE_STEP_EXPRESSIONS[col]
        step_name = f"Add{col}"
        bindings.append(f'{step_name} = Table.AddColumn({prev}, "{col}", each {expr}, {m_type})')
        prev = step_name

    body = ",\n    ".join(bindings)
    return f"let\n    {body}\nin\n    {prev}\n"

def write_powerquery(rows: list, path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(emit_powerquery(rows, **kwargs))
