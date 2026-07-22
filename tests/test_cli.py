import csv
from nz_date_dimension.cli import main

# --- NZ (unchanged defaults) ---

def test_cli_writes_csv(tmp_path):
    out = tmp_path / "d.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 365

def test_cli_default_format_is_still_csv_when_format_omitted(tmp_path):
    # Explicitly guards spec: "keep the CSV default working unchanged."
    out = tmp_path / "default.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header[0] == "Date" and header[-1] == "GeneratedOn"
    assert "Country" not in header

def test_cli_format_tsql_writes_sql(tmp_path):
    out = tmp_path / "d.tsql.sql"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--format", "tsql", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "CREATE TABLE" in text and "CREATE VIEW" in text
    assert "[NZDateDimension]" in text

def test_cli_format_powerquery_writes_m(tmp_path):
    out = tmp_path / "d.pq"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--format", "powerquery", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.strip().startswith("let") and "DateTime.LocalNow()" in text

def test_cli_format_dbt_writes_model_and_seed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--start-year", "2025", "--end-year", "2025", "--format", "dbt"])
    assert rc == 0
    model_path = tmp_path / "outputs" / "dbt" / "models" / "nz_date_dimension.sql"
    seed_path = tmp_path / "outputs" / "dbt" / "seeds" / "nz_date_dimension_holidays.csv"
    assert model_path.exists() and "dbt_utils.date_spine" in model_path.read_text(encoding="utf-8")
    assert seed_path.exists()
    with open(seed_path, newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 365

def test_cli_format_all_writes_every_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--start-year", "2025", "--end-year", "2025", "--format", "all"])
    assert rc == 0
    outputs = tmp_path / "outputs"
    assert (outputs / "nz-date-dimension.csv").exists()
    assert (outputs / "nz-date-dimension.tsql.sql").exists()
    assert (outputs / "nz-date-dimension.snowflake.sql").exists()
    assert (outputs / "nz-date-dimension.databricks.sql").exists()
    assert (outputs / "nz-date-dimension.pq").exists()
    assert (outputs / "dbt" / "models" / "nz_date_dimension.sql").exists()
    assert (outputs / "dbt" / "seeds" / "nz_date_dimension_holidays.csv").exists()

def test_cli_default_country_is_nz_and_fiscal_start_month_stays_april(tmp_path):
    out = tmp_path / "d.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = next(r for r in rows if r["Date"] == "2025-04-01")
    assert row["FiscalMonth"] == "1"  # April is fiscal month 1 for NZ

# --- AU ---

def test_cli_country_au_writes_au_csv_with_state_flags(tmp_path):
    out = tmp_path / "au.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "au", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 365
    assert "IsHoliday_WA" in rows[0]
    assert "IsHoliday_AUK" not in rows[0]

def test_cli_country_au_fiscal_start_month_defaults_to_july_not_april(tmp_path):
    # Regression for spec §7: --country au must not silently inherit an
    # April fiscal year just because --fiscal-start-month wasn't passed.
    out = tmp_path / "au.csv"
    rc = main(["--start-year", "2025", "--end-year", "2026", "--country", "au", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = next(r for r in rows if r["Date"] == "2025-08-01")
    assert row["FiscalYear"] == "2026"
    assert row["FiscalStartOfYear"] == "2025-07-01"

def test_cli_country_au_explicit_fiscal_start_month_overrides_default(tmp_path):
    out = tmp_path / "au.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "au",
               "--fiscal-start-month", "1", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = next(r for r in rows if r["Date"] == "2025-06-01")
    assert row["FiscalMonth"] == "6"  # calendar-year fiscal (start_month=1)

def test_cli_country_au_tsql_uses_au_table_name(tmp_path):
    out = tmp_path / "au.tsql.sql"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "au",
               "--format", "tsql", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "[AUDateDimension]" in text
    assert "[NZDateDimension]" not in text

def test_cli_country_au_default_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "au", "--format", "csv"])
    assert rc == 0
    assert (tmp_path / "outputs" / "au-date-dimension.csv").exists()

def test_cli_country_au_dbt_uses_au_seed_ref_and_default_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "au", "--format", "dbt"])
    assert rc == 0
    model_path = tmp_path / "outputs" / "dbt" / "models" / "au_date_dimension.sql"
    seed_path = tmp_path / "outputs" / "dbt" / "seeds" / "au_date_dimension_holidays.csv"
    assert model_path.exists()
    assert "ref('au_date_dimension_holidays')" in model_path.read_text(encoding="utf-8")
    assert seed_path.exists()

# --- Combined ---

def test_cli_country_combined_writes_csv_with_country_column(tmp_path):
    out = tmp_path / "anz.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "combined", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 730
    assert {r["Country"] for r in rows} == {"NZ", "AU"}
    assert "IsHoliday_NZ_AUK" in rows[0] and "IsHoliday_AU_WA" in rows[0]

def test_cli_country_combined_default_paths_and_table_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "combined", "--format", "tsql"])
    assert rc == 0
    out_path = tmp_path / "outputs" / "anz-date-dimension.tsql.sql"
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "[ANZDateDimension]" in text

def test_cli_country_combined_tsql_has_composite_primary_key(tmp_path):
    out = tmp_path / "anz.tsql.sql"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "combined",
               "--format", "tsql", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    pk_line = next(line for line in text.splitlines() if "PRIMARY KEY" in line)
    assert "[Date]" in pk_line and "[Country]" in pk_line

def test_cli_country_combined_format_all_skips_dbt_gracefully(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["--start-year", "2025", "--end-year", "2025", "--country", "combined", "--format", "all"])
    assert rc == 0  # must not crash the whole run
    outputs = tmp_path / "outputs"
    assert (outputs / "anz-date-dimension.csv").exists()
    assert (outputs / "anz-date-dimension.tsql.sql").exists()
    assert not (outputs / "dbt").exists()

def test_cli_country_combined_format_dbt_explicitly_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import pytest
    with pytest.raises((NotImplementedError, ValueError, SystemExit)):
        main(["--start-year", "2025", "--end-year", "2025", "--country", "combined", "--format", "dbt"])
