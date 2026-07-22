"""Durable regression guard for spec §7's central requirement: "NZ CSV
output byte-identical to before the refactor." Rather than relying on a
one-off manual diff, this compares a freshly generated default-args CSV
against the actual `outputs/nz-date-dimension.csv` file committed to the
repo (2015-2050) -- every column EXCEPT `GeneratedOn` is compared exactly,
field-for-field. `GeneratedOn` is excluded deliberately: it legitimately
holds the date the fresh run happened, which is not the date the golden
file was committed, so including it would make this guard flake on any day
that doesn't match the golden file's stamp (M-1: the previous version of
this test skipped entirely on any day other than the golden file's
generation date, silently giving no protection in CI on later days). This
version is durable regardless of what day it runs on, and does not weaken
the check for any other column -- a regression in any stable column still
fails the test.
"""
import csv
from pathlib import Path
from nz_date_dimension.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_CSV = REPO_ROOT / "outputs" / "nz-date-dimension.csv"

def _read_rows_excluding_generated_on(path) -> list:
    """Parse a CSV into rows (list of field-value lists) with the trailing
    GeneratedOn column stripped from the header and every data row -- the
    one column that legitimately differs by run date.
    """
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows, f"{path} is empty"
    assert rows[0][-1] == "GeneratedOn", (
        f"expected last column to be GeneratedOn, got {rows[0][-1]!r}"
    )
    return [row[:-1] for row in rows]

def test_default_cli_csv_output_is_byte_identical_to_shipped_csv(tmp_path):
    if not GOLDEN_CSV.exists():
        import pytest
        pytest.skip("outputs/nz-date-dimension.csv not present in this checkout")

    out = tmp_path / "nz-date-dimension.csv"
    rc = main(["--out", str(out)])  # every default: 2015-2050, country=nz, csv
    assert rc == 0

    fresh_rows = _read_rows_excluding_generated_on(out)
    golden_rows = _read_rows_excluding_generated_on(GOLDEN_CSV)
    assert fresh_rows == golden_rows, (
        "Default CLI CSV output is no longer identical (ignoring the "
        "run-date-dependent GeneratedOn column) to the shipped "
        "outputs/nz-date-dimension.csv -- the country-parameterisation "
        "refactor must not change NZ's output."
    )
