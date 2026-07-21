from datetime import date
from nz_date_dimension.holidays_nz import build_national, national_holiday_columns, NZ_SUBDIVISIONS

def cols(d, y0, y1):
    nat = build_national(y0, y1)
    return national_holiday_columns(d, nat, is_weekend=d.isoweekday() >= 6)

def test_christmas_is_holiday_and_not_business_day():
    c = cols(date(2025, 12, 25), 2025, 2025)
    assert c["IsHoliday"] is True and c["IsBusinessDay"] is False
    assert "Christmas" in c["HolidayName"]

def test_waitangi_mondayisation_2021():
    # 6 Feb 2021 was a Saturday -> observed Monday 8 Feb 2021
    observed = cols(date(2021, 2, 8), 2021, 2021)
    assert observed["IsHoliday"] is True
    assert observed["IsObserved"] is True
    assert observed["IsBusinessDay"] is False

def test_matariki_2022():
    assert cols(date(2022, 6, 24), 2022, 2022)["IsHoliday"] is True

def test_matariki_not_before_2022():
    assert cols(date(2021, 6, 24), 2021, 2021)["IsHoliday"] is False

def test_qe2_memorial_one_off_2022():
    assert cols(date(2022, 9, 26), 2022, 2022)["IsHoliday"] is True

def test_ordinary_weekday_is_business_day():
    c = cols(date(2025, 7, 23), 2025, 2025)
    assert c["IsHoliday"] is False and c["IsBusinessDay"] is True

def test_there_are_17_subdivisions():
    assert len(NZ_SUBDIVISIONS) == 17
