from datetime import date, timedelta
from .calendar_core import calendar_columns
from .fiscal import fiscal_columns
from .holidays_engine import build_national, national_holiday_columns, warn_if_beyond_cap
from .regional import build_regional, regional_columns
from .columns import stable_columns, regional_flag_columns
from .countries import get_country, COMBINED_COUNTRY_ORDER

# Backward-compat constant: the NZ-shaped STABLE_COLUMNS list, byte-identical
# in content and order to the pre-refactor hardcoded list (spec §7
# regression guard). AU/Combined callers should use stable_columns(...)
# directly (see columns.py) rather than this NZ-specific constant.
STABLE_COLUMNS = stable_columns(["NZ"])

def build_dataset(start_year: int, end_year: int, fiscal_start_month: int = None,
                   country: str = "NZ") -> list:
    """Build the full date-dimension dataset for one country ("NZ"/"AU") or
    "combined" (unions NZ + AU under a Country column).

    fiscal_start_month=None (the default) falls back to the country's own
    config (NZ=4, AU=7) -- passing it explicitly overrides that for every
    country in the dataset (spec §7: avoids AU silently getting an April
    fiscal year).
    """
    if country.upper() == "COMBINED":
        return _build_combined_dataset(start_year, end_year, fiscal_start_month)
    cfg = get_country(country)
    fsm = fiscal_start_month if fiscal_start_month is not None else cfg.fiscal_start_month
    warn_if_beyond_cap(cfg, end_year)
    national = build_national(cfg, start_year, end_year)
    regional = build_regional(cfg, start_year, end_year)
    rows = []
    d = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    while d <= end:
        cal = calendar_columns(d)
        row = {}
        row.update(cal)
        row.update(fiscal_columns(d, fsm))
        row.update(national_holiday_columns(d, national, is_weekend=cal["IsWeekend"]))
        row.update(regional_columns(d, regional))
        rows.append(row)
        d += timedelta(days=1)
    return rows

def _build_combined_dataset(start_year: int, end_year: int, fiscal_start_month: int = None) -> list:
    """Combined ANZ dataset: one table, a Country column, per-row fiscal
    year computed from THAT row's country FY, national holidays/
    IsBusinessDay from that row's country, and country-prefixed regional
    flags (spec §7 resolution: avoids the NZ Taranaki / AU Tasmania "TAS"
    collision). Rows are unioned across countries then sorted by
    (Date, Country) -- matching the Combined SQL composite PK.
    """
    flag_cols = regional_flag_columns(list(COMBINED_COUNTRY_ORDER))
    all_rows = []
    for cc in COMBINED_COUNTRY_ORDER:
        cfg = get_country(cc)
        fsm = fiscal_start_month if fiscal_start_month is not None else cfg.fiscal_start_month
        warn_if_beyond_cap(cfg, end_year)
        national = build_national(cfg, start_year, end_year)
        regional = build_regional(cfg, start_year, end_year)
        d = date(start_year, 1, 1)
        end = date(end_year, 12, 31)
        while d <= end:
            cal = calendar_columns(d)
            row = {"Country": cc}
            row.update(cal)
            row.update(fiscal_columns(d, fsm))
            row.update(national_holiday_columns(d, national, is_weekend=cal["IsWeekend"]))
            row.update({fc: False for fc in flag_cols})       # default every combined flag false
            row.update(regional_columns(d, regional, prefix=cc))  # overlay this country's true values
            all_rows.append(row)
            d += timedelta(days=1)
    all_rows.sort(key=lambda r: (r["Date"], r["Country"]))
    return all_rows
