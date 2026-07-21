from datetime import date
import holidays

# 17 python-holidays NZ subdivisions (verified against installed holidays==0.101).
# NOTE: the installed library also exposes an 18th subdivision key, the string
# "South Canterbury" (not a 3-letter code like the others) — deliberately
# excluded here to keep NZ_SUBDIVISIONS at the 17 short codes per spec.
NZ_SUBDIVISIONS = ["AUK", "BOP", "CAN", "CIT", "GIS", "HKB", "MBH", "MWT",
                   "NSN", "NTL", "OTA", "STL", "TAS", "TKI", "WGN", "WKO", "WTC"]

MATARIKI_LAST_YEAR = 2052

def build_national(start_year: int, end_year: int):
    return holidays.NewZealand(years=range(start_year, end_year + 1), observed=True)

def national_holiday_columns(d: date, national, is_weekend: bool) -> dict:
    name = national.get(d)
    is_holiday = name is not None
    # python-holidays appends "(observed)" to Mondayised observed days.
    # Verified against actual output (holidays==0.101): NewZealand(years=2021,
    # observed=True).get(date(2021, 2, 8)) == "Waitangi Day (observed)".
    is_observed = bool(name) and "(observed)" in name.lower()
    return {
        "IsHoliday": is_holiday,
        "HolidayName": name,
        "IsObserved": is_observed,
        "IsBusinessDay": (not is_weekend) and (not is_holiday),
    }

def warn_if_beyond_matariki(end_year: int) -> None:
    if end_year > MATARIKI_LAST_YEAR:
        import warnings
        warnings.warn(
            f"end_year={end_year} exceeds {MATARIKI_LAST_YEAR}; Matariki is not "
            f"gazetted beyond {MATARIKI_LAST_YEAR} and will be absent for later years.",
            stacklevel=2,
        )
