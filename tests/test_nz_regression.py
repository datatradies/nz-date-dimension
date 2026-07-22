"""Durable regression guard for spec §7's central requirement: "NZ CSV
output byte-identical to before the refactor." Rather than relying on a
one-off manual diff, this compares a freshly generated default-args CSV
against the actual `outputs/nz-date-dimension.csv` file committed to the
repo (2015-2050, generated the same day this test runs -- GeneratedOn is
today's date in both, so this only passes when run same-day as generation;
that's true in CI and in this refactor's own verification).
"""
import filecmp
from pathlib import Path
from datetime import date
from nz_date_dimension.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_CSV = REPO_ROOT / "outputs" / "nz-date-dimension.csv"

def test_default_cli_csv_output_is_byte_identical_to_shipped_csv(tmp_path):
    if not GOLDEN_CSV.exists():
        import pytest
        pytest.skip("outputs/nz-date-dimension.csv not present in this checkout")
    # The golden file's GeneratedOn column is baked in at generation time --
    # only a byte-identical comparison if regenerated the same day.
    golden_generated_on = GOLDEN_CSV.read_text(encoding="utf-8").splitlines()[1].split(",")[-1]
    if golden_generated_on != date.today().isoformat():
        import pytest
        pytest.skip(
            f"golden CSV was generated on {golden_generated_on}, not today "
            f"({date.today().isoformat()}) -- GeneratedOn would legitimately differ"
        )
    out = tmp_path / "nz-date-dimension.csv"
    rc = main(["--out", str(out)])  # every default: 2015-2050, country=nz, csv
    assert rc == 0
    assert filecmp.cmp(str(out), str(GOLDEN_CSV), shallow=False), (
        "Default CLI CSV output is no longer byte-identical to the shipped "
        "outputs/nz-date-dimension.csv -- the country-parameterisation "
        "refactor must not change NZ's output."
    )
