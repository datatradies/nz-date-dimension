import csv
from datetime import date
from nz_date_dimension.build import build_dataset
from nz_date_dimension.emit_csv import write_csv

def test_write_csv_roundtrip(tmp_path):
    rows = build_dataset(2025, 2025)
    out = tmp_path / "nz.csv"
    write_csv(rows, str(out), generated_on=date(2026, 7, 22))
    with open(out, newline="", encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert len(read) == 365
    assert read[0]["Date"] == "2025-01-01"
    assert read[0]["GeneratedOn"] == "2026-07-22"
    xmas = next(r for r in read if r["Date"] == "2025-12-25")
    assert xmas["IsBusinessDay"] == "false" and xmas["IsHoliday"] == "true"
