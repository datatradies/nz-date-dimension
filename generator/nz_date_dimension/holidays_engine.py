"""Country-driven national-holiday building and observed-day detection.

Refactored from the original holidays_nz.py (spec §7): the generator now
supports NZ and AU (and, via countries.py, future countries) from one
codebase instead of hardcoding NewZealand()/the "(observed)" suffix
heuristic. NZ behaviour is unchanged -- build_national(NZ, ...) and
national_holiday_columns() against it produce byte-identical results to
the pre-refactor holidays_nz.py.

Observed-day detection is country-configurable (spec §7 resolution 4):
- NZ ("suffix" strategy): python-holidays appends "(observed)" to the
  Mondayised day's name and keeps the original weekend date in the
  calendar too (both dates present, differentiated by the suffix).
  Verified against holidays==0.101: NewZealand(years=2021,
  observed=True).get(date(2021, 2, 8)) == "Waitangi Day (observed)".
- AU ("diff" strategy): the make-up Monday carries NO "(observed)" suffix
  and the original weekend date is REMOVED from the observed=True
  calendar entirely -- the suffix heuristic silently fails (never detects
  anything). Instead: a date is observed if it's a holiday under
  observed=True but NOT under observed=False (i.e. it only exists because
  of the weekend-shift rule). Verified live against holidays==0.101:
  Australia(subdiv="NSW", years=2025, observed=True).get(date(2025, 1, 27))
  == "Australia Day" (no suffix), and date(2025, 1, 26) (the actual
  Sunday) is entirely absent from the observed=True calendar.
"""
from datetime import date
import warnings
from .countries import CountryConfig

class NationalHolidays:
    """Wraps a python-holidays calendar (observed=True) plus, for
    "diff"-strategy countries, its observed=False twin, and exposes a
    single country-agnostic is_observed() alongside the usual dict-like
    .get(d).
    """
    def __init__(self, observed_true, observed_false, strategy: str):
        self.observed_true = observed_true
        self.observed_false = observed_false
        self.strategy = strategy

    def get(self, d: date):
        return self.observed_true.get(d)

    def is_observed(self, d: date) -> bool:
        name = self.observed_true.get(d)
        if not name:
            return False
        if self.strategy == "suffix":
            return "(observed)" in name.lower()
        if self.strategy == "diff":
            return d not in self.observed_false
        raise ValueError(f"Unknown observed_strategy: {self.strategy!r}")

def build_national(country: CountryConfig, start_year: int, end_year: int) -> NationalHolidays:
    """Build the country's NATIONAL (no-subdivision) holiday calendar --
    the common holidays observed across the whole country, excluding
    region/state-specific days (those are regional.py's concern). This is
    what drives the main IsHoliday/HolidayName/IsObserved/IsBusinessDay
    columns.
    """
    years = range(start_year, end_year + 1)
    observed_true = country.holidays_class(years=years, observed=True)
    observed_false = (
        country.holidays_class(years=years, observed=False)
        if country.observed_strategy == "diff"
        else None
    )
    return NationalHolidays(observed_true, observed_false, country.observed_strategy)

def national_holiday_columns(d: date, national: NationalHolidays, is_weekend: bool) -> dict:
    name = national.get(d)
    is_holiday = name is not None
    is_observed = national.is_observed(d)
    return {
        "IsHoliday": is_holiday,
        "HolidayName": name,
        "IsObserved": is_observed,
        "IsBusinessDay": (not is_weekend) and (not is_holiday),
    }

def warn_if_beyond_cap(country: CountryConfig, end_year: int) -> None:
    """Warn if end_year exceeds the country's gazetting cap (NZ's Matariki,
    gazetted only through 2052). Countries with no cap (max_year=None, e.g.
    AU) never warn.
    """
    if country.max_year is not None and end_year > country.max_year:
        warnings.warn(
            f"end_year={end_year} exceeds {country.max_year}; {country.cap_note}",
            stacklevel=2,
        )
