"""Country configuration — the single source of truth for everything that
varies between NZ, AU (and future countries): which python-holidays class
to build from, the subdivision/flag codes, the fiscal year start month, how
to detect a Mondayised "observed" day, and per-country output naming.

Adding a country (e.g. a future Pacific nation) means adding one
CountryConfig here — the generator, emitters and CLI all derive their
behaviour from this config rather than hardcoding NZ specifics (spec §7
resolution: "the refactor must derive columns dynamically from the
dataset/country config").
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import holidays

@dataclass(frozen=True)
class CountryConfig:
    code: str                      # "NZ" | "AU" -- also the Combined-mode Country column value
    name: str                      # "New Zealand" | "Australia"
    holidays_class: type           # holidays.NewZealand | holidays.Australia
    subdivisions: Tuple[str, ...]  # regional/state codes -> IsHoliday_<code> flags
    fiscal_start_month: int        # 4 (NZ) | 7 (AU)
    observed_strategy: str         # "suffix" (NZ: "(observed)" in HolidayName) |
                                    # "diff" (AU: observed=True holiday not present under observed=False)
    table_name: str                # single-country SQL table name
    output_stem: str               # single-country default output filename stem
    max_year: Optional[int] = None       # e.g. NZ's Matariki gazetting cap (2052); None = no cap
    cap_note: Optional[str] = None       # human note used in the beyond-cap warning

# 17 python-holidays NZ subdivisions (verified against holidays==0.101).
# NOTE: the installed library also exposes an 18th subdivision key, the string
# "South Canterbury" (not a 3-letter code like the others) -- deliberately
# excluded here to keep NZ_SUBDIVISIONS at the 17 short codes per spec.
NZ_SUBDIVISIONS: Tuple[str, ...] = (
    "AUK", "BOP", "CAN", "CIT", "GIS", "HKB", "MBH", "MWT",
    "NSN", "NTL", "OTA", "STL", "TAS", "TKI", "WGN", "WKO", "WTC",
)

# 8 python-holidays AU subdivisions (states/territories), verified against
# holidays==0.101 (holidays.Australia.subdivisions).
AU_SUBDIVISIONS: Tuple[str, ...] = ("ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA")

MATARIKI_LAST_YEAR = 2052

NZ = CountryConfig(
    code="NZ",
    name="New Zealand",
    holidays_class=holidays.NewZealand,
    subdivisions=NZ_SUBDIVISIONS,
    fiscal_start_month=4,
    observed_strategy="suffix",
    table_name="NZDateDimension",
    output_stem="nz-date-dimension",
    max_year=MATARIKI_LAST_YEAR,
    cap_note=(
        f"Matariki is not gazetted beyond {MATARIKI_LAST_YEAR} and will be "
        "absent for later years."
    ),
)

AU = CountryConfig(
    code="AU",
    name="Australia",
    holidays_class=holidays.Australia,
    subdivisions=AU_SUBDIVISIONS,
    fiscal_start_month=7,
    observed_strategy="diff",
    table_name="AUDateDimension",
    output_stem="au-date-dimension",
    max_year=None,
    cap_note=None,
)

COUNTRIES = {"NZ": NZ, "AU": AU}

# Combined ("ANZ") mode isn't a single python-holidays country -- it unions
# NZ + AU rows under a Country column -- so it gets its own naming constants
# rather than a CountryConfig of its own.
COMBINED_TABLE_NAME = "ANZDateDimension"
COMBINED_OUTPUT_STEM = "anz-date-dimension"
COMBINED_COUNTRY_ORDER: Tuple[str, ...] = ("NZ", "AU")

def get_country(code: str) -> CountryConfig:
    """Look up a CountryConfig by code, case-insensitively."""
    key = code.upper()
    if key not in COUNTRIES:
        raise ValueError(f"Unknown country code: {code!r}. Supported: {sorted(COUNTRIES)}")
    return COUNTRIES[key]
