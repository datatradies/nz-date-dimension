from datetime import date, timedelta
from .fiscal import fiscal_columns

# Relative / time-intelligence columns (spec §4.5). These are DYNAMIC —
# always computed against an injectable "today", never baked into the
# static CSV (a frozen IsCalendarYTD would be wrong the next day). This
# module is the single reference implementation of the logic; the SQL
# views, Power Query script and dbt model each re-express it natively in
# their own engine so it stays live on refresh (spec §7).
RELATIVE_COLUMNS = [
    "DayOffset", "WeekOffset", "MonthOffset", "QuarterOffset", "YearOffset",
    "FiscalYearOffset", "FiscalQuarterOffset",
    "IsToday", "IsCurrentWeek", "IsCurrentMonth", "IsCurrentQuarter",
    "IsCurrentYear", "IsCurrentFiscalYear",
    "IsCalendarYTD", "IsFiscalYTD", "IsMonthToDate", "IsQuarterToDate",
    "IsLast7Days", "IsLast30Days", "IsLast90Days",
    "IsPriorMonth", "IsPriorYear", "IsRolling12Months",
]

def _week_start(d: date) -> date:
    """Monday of the ISO week containing d."""
    return d - timedelta(days=d.isoweekday() - 1)

def _quarter(d: date) -> int:
    return (d.month - 1) // 3 + 1

def _month_index(d: date) -> int:
    """Absolute month index (year*12+month) so month offsets are plain subtraction."""
    return d.year * 12 + d.month

def _quarter_index(d: date) -> int:
    """Absolute calendar-quarter index (year*4+quarter)."""
    return d.year * 4 + _quarter(d)

def relative_columns(d: date, today: date, fiscal_start_month: int = 4) -> dict:
    day_offset = (d - today).days
    week_offset = (_week_start(d) - _week_start(today)).days // 7
    month_offset = _month_index(d) - _month_index(today)
    quarter_offset = _quarter_index(d) - _quarter_index(today)
    year_offset = d.year - today.year

    fy_d = fiscal_columns(d, fiscal_start_month)
    fy_today = fiscal_columns(today, fiscal_start_month)
    fiscal_year_offset = fy_d["FiscalYear"] - fy_today["FiscalYear"]
    fiscal_quarter_index_d = fy_d["FiscalYear"] * 4 + fy_d["FiscalQuarter"]
    fiscal_quarter_index_today = fy_today["FiscalYear"] * 4 + fy_today["FiscalQuarter"]
    fiscal_quarter_offset = fiscal_quarter_index_d - fiscal_quarter_index_today

    is_current_year = year_offset == 0
    is_current_fiscal_year = fiscal_year_offset == 0

    # Rolling 12 months = the current (possibly partial) calendar month plus
    # the 11 preceding full months, up to and including today (future days
    # within the current month are excluded).
    rolling_month_diff = _month_index(today) - _month_index(d)
    is_rolling_12_months = 0 <= rolling_month_diff <= 11 and d <= today

    return {
        "DayOffset": day_offset,
        "WeekOffset": week_offset,
        "MonthOffset": month_offset,
        "QuarterOffset": quarter_offset,
        "YearOffset": year_offset,
        "FiscalYearOffset": fiscal_year_offset,
        "FiscalQuarterOffset": fiscal_quarter_offset,
        "IsToday": d == today,
        "IsCurrentWeek": week_offset == 0,
        "IsCurrentMonth": month_offset == 0,
        "IsCurrentQuarter": quarter_offset == 0,
        "IsCurrentYear": is_current_year,
        "IsCurrentFiscalYear": is_current_fiscal_year,
        "IsCalendarYTD": is_current_year and d <= today,
        "IsFiscalYTD": is_current_fiscal_year and d <= today,
        "IsMonthToDate": month_offset == 0 and d <= today,
        "IsQuarterToDate": quarter_offset == 0 and d <= today,
        "IsLast7Days": today - timedelta(days=6) <= d <= today,
        "IsLast30Days": today - timedelta(days=29) <= d <= today,
        "IsLast90Days": today - timedelta(days=89) <= d <= today,
        "IsPriorMonth": month_offset == -1,
        "IsPriorYear": year_offset == -1,
        "IsRolling12Months": is_rolling_12_months,
    }
