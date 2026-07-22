import holidays
import pytest
from nz_date_dimension.countries import (
    NZ, AU, COUNTRIES, get_country, NZ_SUBDIVISIONS, AU_SUBDIVISIONS,
    MATARIKI_LAST_YEAR, COMBINED_TABLE_NAME, COMBINED_OUTPUT_STEM,
    COMBINED_COUNTRY_ORDER,
)

def test_nz_config_values():
    assert NZ.code == "NZ"
    assert NZ.holidays_class is holidays.NewZealand
    assert NZ.fiscal_start_month == 4
    assert NZ.observed_strategy == "suffix"
    assert NZ.table_name == "NZDateDimension"
    assert NZ.output_stem == "nz-date-dimension"
    assert NZ.max_year == MATARIKI_LAST_YEAR == 2052
    assert NZ.subdivisions == NZ_SUBDIVISIONS
    assert len(NZ.subdivisions) == 17

def test_au_config_values():
    assert AU.code == "AU"
    assert AU.holidays_class is holidays.Australia
    assert AU.fiscal_start_month == 7
    assert AU.observed_strategy == "diff"
    assert AU.table_name == "AUDateDimension"
    assert AU.output_stem == "au-date-dimension"
    assert AU.max_year is None
    assert AU.subdivisions == AU_SUBDIVISIONS
    assert AU.subdivisions == ("ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA")

def test_get_country_is_case_insensitive():
    assert get_country("nz") is NZ
    assert get_country("AU") is AU
    assert get_country("Au") is AU

def test_get_country_unknown_raises_value_error():
    with pytest.raises(ValueError):
        get_country("US")

def test_countries_registry_has_both():
    assert COUNTRIES == {"NZ": NZ, "AU": AU}

def test_combined_naming_constants():
    assert COMBINED_TABLE_NAME == "ANZDateDimension"
    assert COMBINED_OUTPUT_STEM == "anz-date-dimension"
    assert COMBINED_COUNTRY_ORDER == ("NZ", "AU")
