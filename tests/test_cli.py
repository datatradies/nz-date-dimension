import csv
from nz_date_dimension.cli import main

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

def test_cli_format_tsql_writes_sql(tmp_path):
    out = tmp_path / "d.tsql.sql"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--format", "tsql", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "CREATE TABLE" in text and "CREATE VIEW" in text

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
