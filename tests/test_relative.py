from datetime import date, timedelta
from nz_date_dimension.relative import relative_columns, RELATIVE_COLUMNS

TODAY = date(2026, 7, 22)  # a Wednesday; FY2027 Q2 (fiscal_start_month=4)

def rc(d, today=TODAY, fiscal_start_month=4):
    return relative_columns(d, today, fiscal_start_month)

def test_today_is_all_zero_offsets_and_all_current():
    c = rc(TODAY)
    assert c["DayOffset"] == 0 and c["WeekOffset"] == 0 and c["MonthOffset"] == 0
    assert c["QuarterOffset"] == 0 and c["YearOffset"] == 0
    assert c["FiscalYearOffset"] == 0 and c["FiscalQuarterOffset"] == 0
    assert c["IsToday"] is True
    assert c["IsCurrentWeek"] is True and c["IsCurrentMonth"] is True
    assert c["IsCurrentQuarter"] is True and c["IsCurrentYear"] is True
    assert c["IsCurrentFiscalYear"] is True
    assert c["IsCalendarYTD"] is True and c["IsFiscalYTD"] is True
    assert c["IsMonthToDate"] is True and c["IsQuarterToDate"] is True
    assert c["IsLast7Days"] is True and c["IsLast30Days"] is True and c["IsLast90Days"] is True
    assert c["IsPriorMonth"] is False and c["IsPriorYear"] is False
    assert c["IsRolling12Months"] is True

def test_rows_carry_every_relative_column():
    c = rc(TODAY)
    for col in RELATIVE_COLUMNS:
        assert col in c, f"missing {col}"

def test_all_relative_columns_are_booleans_or_ints():
    c = rc(TODAY)
    for col in RELATIVE_COLUMNS:
        assert isinstance(c[col], (bool, int)), f"{col} is {type(c[col])}"

def test_week_offset_exact_multiple_of_seven_days_back():
    # today - 21 days is exactly 3 Mondays earlier, regardless of weekday
    # alignment, so WeekOffset must be exactly -3.
    d = TODAY - timedelta(days=21)
    c = rc(d)
    assert c["WeekOffset"] == -3
    assert c["IsCurrentWeek"] is False

def test_monday_of_current_week_is_still_current_week():
    d = date(2026, 7, 20)  # Monday of today's ISO week
    c = rc(d)
    assert c["WeekOffset"] == 0 and c["IsCurrentWeek"] is True
    assert c["DayOffset"] == -2

def test_sunday_of_prior_week_is_not_current_week():
    d = date(2026, 7, 19)  # Sunday, one day before this week's Monday
    c = rc(d)
    assert c["WeekOffset"] == -1 and c["IsCurrentWeek"] is False
    assert c["DayOffset"] == -3

def test_start_of_year_same_calendar_year_but_different_fiscal_year():
    # 2026-01-01 is same calendar year as TODAY (2026) but FY2026
    # (1 Apr 2025 - 31 Mar 2026), while TODAY is in FY2027.
    d = date(2026, 1, 1)
    c = rc(d)
    assert c["YearOffset"] == 0 and c["IsCurrentYear"] is True
    assert c["IsCalendarYTD"] is True  # same year, d <= today
    assert c["MonthOffset"] == -6 and c["IsCurrentMonth"] is False
    assert c["QuarterOffset"] == -2 and c["IsCurrentQuarter"] is False
    assert c["FiscalYearOffset"] == -1 and c["IsCurrentFiscalYear"] is False
    assert c["FiscalQuarterOffset"] == -2
    assert c["IsFiscalYTD"] is False  # different fiscal year entirely
    assert c["IsMonthToDate"] is False and c["IsQuarterToDate"] is False

def test_future_date_in_same_year_is_not_calendar_ytd():
    d = date(2026, 12, 31)
    c = rc(d)
    assert c["YearOffset"] == 0
    assert c["IsCalendarYTD"] is False  # in the future relative to today

def test_start_of_current_fiscal_year_is_current_fiscal_year():
    d = date(2026, 4, 1)  # start of FY2027
    c = rc(d)
    assert c["FiscalYearOffset"] == 0 and c["IsCurrentFiscalYear"] is True
    assert c["IsFiscalYTD"] is True  # d <= today, same fiscal year

def test_last_7_days_boundary():
    assert rc(TODAY - timedelta(days=6))["IsLast7Days"] is True
    assert rc(TODAY - timedelta(days=7))["IsLast7Days"] is False
    assert rc(TODAY + timedelta(days=1))["IsLast7Days"] is False  # future excluded

def test_last_30_days_boundary():
    assert rc(TODAY - timedelta(days=29))["IsLast30Days"] is True
    assert rc(TODAY - timedelta(days=30))["IsLast30Days"] is False

def test_last_90_days_boundary():
    assert rc(TODAY - timedelta(days=89))["IsLast90Days"] is True
    assert rc(TODAY - timedelta(days=90))["IsLast90Days"] is False

def test_is_prior_month_flags_the_whole_previous_calendar_month():
    assert rc(date(2026, 6, 1))["IsPriorMonth"] is True
    assert rc(date(2026, 6, 15))["IsPriorMonth"] is True
    assert rc(date(2026, 6, 30))["IsPriorMonth"] is True
    assert rc(date(2026, 5, 30))["IsPriorMonth"] is False
    assert rc(date(2026, 7, 1))["IsPriorMonth"] is False  # current month, not prior

def test_is_prior_year_flags_the_whole_previous_calendar_year():
    assert rc(date(2025, 1, 1))["IsPriorYear"] is True
    assert rc(date(2025, 12, 31))["IsPriorYear"] is True
    assert rc(date(2024, 12, 31))["IsPriorYear"] is False
    assert rc(date(2026, 1, 1))["IsPriorYear"] is False  # current year, not prior

def test_rolling_12_months_window():
    assert rc(date(2025, 8, 1))["IsRolling12Months"] is True   # 11 months back: included
    assert rc(date(2025, 7, 31))["IsRolling12Months"] is False  # 12 months back: excluded
    assert rc(date(2025, 7, 1))["IsRolling12Months"] is False
    assert rc(date(2026, 8, 1))["IsRolling12Months"] is False  # future month excluded

def test_rolling_12_months_excludes_future_days_in_current_month():
    d = TODAY + timedelta(days=3)
    assert d.year == TODAY.year and d.month == TODAY.month
    assert rc(d)["IsRolling12Months"] is False

def test_fiscal_start_month_parameter_is_honoured():
    # start_month=1 (plain calendar year): fiscal year == calendar year,
    # so a January 2026 date shares TODAY's fiscal year (2026).
    c = rc(date(2026, 1, 15), fiscal_start_month=1)
    assert c["FiscalYearOffset"] == 0
    assert c["IsCurrentFiscalYear"] is True
