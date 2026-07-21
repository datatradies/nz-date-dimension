import csv
from nz_date_dimension.cli import main

def test_cli_writes_csv(tmp_path):
    out = tmp_path / "d.csv"
    rc = main(["--start-year", "2025", "--end-year", "2025", "--out", str(out)])
    assert rc == 0
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 365
