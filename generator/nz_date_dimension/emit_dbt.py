"""dbt model + seed emitter (spec §8). Split per spec's own design:

- The **seed** (`build_dbt_seed_csv`) carries only what needs Python's
  holiday logic — Mondayisation, Matariki, one-off holidays, the 17
  provincial-anniversary flags. That's the genuinely complex thinking
  (spec §8's "materialisation, not computation" principle) — dbt just
  looks it up.
- The **model** (`build_dbt_model_sql`) generates the calendar spine via
  `dbt_utils.date_spine` and derives calendar/fiscal columns and the
  relative/time-intelligence columns natively in SQL from `current_date()`
  (spec §7) — recomputed on every dbt run, so they never go stale.

Deliberately Snowflake-flavoured SQL (date_part/dateadd/datediff,
DAYOFWEEKISO) for internal consistency with emit_snowflake.py — noted
here and in the model's own header comment. Swap the date functions if
compiling against a different warehouse.
"""
from .holidays_nz import NZ_SUBDIVISIONS
from .sql_common import relative_select_sql

DBT_UTILS_VERSION_PIN = ">=1.1.0, <2.0.0"  # date_spine's end_date inclusivity confirmed at this pin

SEED_COLUMNS = (
    ["Date", "IsHoliday", "HolidayName", "IsObserved"]
    + [f"IsHoliday_{code}" for code in NZ_SUBDIVISIONS]
)

def build_dbt_seed_csv(rows: list) -> str:
    """CSV for seeds/nz_date_dimension_holidays.csv — the holiday/Matariki/
    provincial-anniversary lookup the dbt model left-joins against its
    date_spine-generated calendar. Deliberately excludes calendar/fiscal
    columns (Year, FiscalYear, ...): the model derives those itself from
    the spine date, so they're not duplicated into the seed.
    """
    lines = [",".join(SEED_COLUMNS)]
    for row in rows:
        values = []
        for col in SEED_COLUMNS:
            v = row[col]
            if v is None:
                values.append("")
            elif isinstance(v, bool):
                values.append("true" if v else "false")
            elif hasattr(v, "isoformat"):
                values.append(v.isoformat())
            else:
                values.append(str(v))
        lines.append(",".join(values))
    return "\n".join(lines) + "\n"

def write_dbt_seed(rows: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_dbt_seed_csv(rows))

# ---------------------------------------------------------------------------
# Model SQL. Hand-written Snowflake-flavoured date functions
# (year/month/quarter/dayofweekiso/date_trunc-style boundaries), kept
# internally consistent with emit_snowflake.py's own choices. The
# relative-column tail below reuses relative_select_sql() verbatim rather
# than re-deriving that logic a third time.
# ---------------------------------------------------------------------------

_MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]
_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _case_map(expr: str, names: list, start_index: int = 1) -> str:
    """CASE expression mapping an integer expr (start_index..start_index+len-1)
    to a literal name, matching calendar_core.py's MONTH_NAMES/DAY_NAMES
    exactly rather than relying on locale-dependent SQL date-format strings.
    """
    whens = "\n        ".join(
        f"WHEN {i + start_index} THEN '{name}'" for i, name in enumerate(names)
    )
    return f"CASE {expr}\n        {whens}\n    END"

def build_dbt_model_sql(start_year: int = 2015, end_year: int = 2050,
                         fiscal_start_month: int = 4,
                         holiday_seed_ref: str = "nz_date_dimension_holidays") -> str:
    fsm = fiscal_start_month
    start_date_lit = f"cast('{start_year}-01-01' as date)"
    end_date_lit = f"cast('{end_year}-12-31' as date)"

    month_name_case = _case_map("date_part(month, date_day)", _MONTH_NAMES[1:])
    month_short_case = _case_map("date_part(month, date_day)", [m[:3] for m in _MONTH_NAMES[1:]])
    day_name_case = _case_map("dayofweekiso(date_day)", _DAY_NAMES)
    day_short_case = _case_map("dayofweekiso(date_day)", [d[:3] for d in _DAY_NAMES])

    calendar_core = f"""calendar_core as (
    select
        cast(date_day as date) as "Date",
        date_part(year, date_day) * 10000 + date_part(month, date_day) * 100
            + date_part(day, date_day) as "DateKey",
        date_part(year, date_day) as "Year",
        date_part(quarter, date_day) as "Quarter",
        'Q' || date_part(quarter, date_day)::varchar as "QuarterName",
        date_part(month, date_day) as "Month",
        {month_name_case} as "MonthName",
        {month_short_case} as "MonthShort",
        date_part(day, date_day) as "Day",
        date_part(dayofyear, date_day) as "DayOfYear",
        dayofweekiso(date_day) as "DayOfWeek",
        {day_name_case} as "DayName",
        {day_short_case} as "DayShort",
        weekiso(date_day) as "ISOWeek",
        yearofweekiso(date_day) as "ISOWeekYear",
        (dayofweekiso(date_day) >= 6) as "IsWeekend",
        (dayofweekiso(date_day) < 6) as "IsWeekday",
        date_trunc('month', date_day)::date as "StartOfMonth",
        dateadd(day, -1, dateadd(month, 1, date_trunc('month', date_day)))::date as "EndOfMonth",
        date_trunc('quarter', date_day)::date as "StartOfQuarter",
        dateadd(day, -1, dateadd(quarter, 1, date_trunc('quarter', date_day)))::date as "EndOfQuarter",
        date_trunc('year', date_day)::date as "StartOfYear",
        dateadd(day, -1, dateadd(year, 1, date_trunc('year', date_day)))::date as "EndOfYear"
    from spine
)"""

    fiscal_stage1 = f"""fiscal_stage1 as (
    select
        calendar_core.*,
        case when "Month" >= {fsm}
            then date_from_parts("Year", {fsm}, 1)
            else date_from_parts("Year" - 1, {fsm}, 1)
        end as "FiscalStartOfYear"
    from calendar_core
)"""

    fiscal_stage2 = f"""fiscal_stage2 as (
    select
        fiscal_stage1.*,
        dateadd(day, -1, dateadd(year, 1, "FiscalStartOfYear"))::date as "FiscalEndOfYear",
        mod(mod("Month" - {fsm}, 12) + 12, 12) + 1 as "FiscalMonth"
    from fiscal_stage1
)"""

    fiscal_final = """fiscal_final as (
    select
        fiscal_stage2.*,
        date_part(year, "FiscalEndOfYear") as "FiscalYear",
        'FY' || date_part(year, "FiscalEndOfYear")::varchar as "FiscalYearLabel",
        floor(("FiscalMonth" - 1) / 3) + 1 as "FiscalQuarter",
        datediff(day, "FiscalStartOfYear", "Date") + 1 as "FiscalDayOfYear"
    from fiscal_stage2
)"""

    regional_cols = ",\n        ".join(
        f'coalesce(holidays."IsHoliday_{code}", false) as "IsHoliday_{code}"'
        for code in NZ_SUBDIVISIONS
    )
    with_holidays = f"""holidays as (
    select * from {{{{ ref('{holiday_seed_ref}') }}}}
),

with_holidays as (
    select
        fiscal_final.*,
        coalesce(holidays."IsHoliday", false) as "IsHoliday",
        holidays."HolidayName" as "HolidayName",
        coalesce(holidays."IsObserved", false) as "IsObserved",
        (fiscal_final."IsWeekday" and not coalesce(holidays."IsHoliday", false)) as "IsBusinessDay",
        {regional_cols}
    from fiscal_final
    left join holidays on fiscal_final."Date" = holidays."Date"
)"""

    relative_fragment = relative_select_sql("with_holidays", "snowflake", fsm)

    header = f'''-- models/nz_date_dimension.sql
--
-- NZ date dimension -- dbt model (Plan B, spec section 8). Calendar spine
-- generated via dbt_utils.date_spine; holiday/Matariki/provincial-
-- anniversary logic is looked up from the nz_date_dimension_holidays seed
-- rather than recomputed here -- Python already did that thinking (spec
-- section 8's "materialisation, not computation" principle).
--
-- Pin dbt_utils in packages.yml:
--   packages:
--     - package: dbt-labs/dbt_utils
--       version: [{DBT_UTILS_VERSION_PIN!r}]
--
-- BOUNDARY NOTE (spec sections 8, 11): dbt_utils.date_spine's end_date
-- inclusivity has varied across versions -- as of the {DBT_UTILS_VERSION_PIN}
-- pin above it is INCLUSIVE of end_date (the last spine row equals
-- end_date). tests/test_emit_dbt.py documents this; if a future dbt_utils
-- version reverts to exclusive semantics, adjust end_date below by one day
-- and re-verify the spine's last row against the intended end date.
--
-- Deliberately Snowflake-flavoured SQL (date_part/dateadd/datediff,
-- dayofweekiso/weekiso/yearofweekiso) for consistency with
-- emit_snowflake.py -- adjust date functions if compiling against a
-- different warehouse.
--
-- Relative/time-intelligence columns (DayOffset..IsRolling12Months) are
-- derived from current_date() and therefore recomputed fresh on every
-- dbt run (spec section 7) -- never baked into the seed or a static file.

{{% set start_date = "{start_date_lit}" %}}
{{% set end_date = "{end_date_lit}" %}}

with spine as (
    {{{{ dbt_utils.date_spine(
        datepart="day",
        start_date=start_date,
        end_date=end_date
    ) }}}}
),

{calendar_core},

{fiscal_stage1},

{fiscal_stage2},

{fiscal_final},

{with_holidays},

relative as (
    {relative_fragment}
)

select * from relative
'''
    return header

def write_dbt_model(path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_dbt_model_sql(**kwargs))
