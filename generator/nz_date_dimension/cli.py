import argparse
import os
from datetime import date
from .build import build_dataset
from .emit_csv import write_csv
from .emit_tsql import write_tsql
from .emit_snowflake import write_snowflake
from .emit_databricks import write_databricks
from .emit_powerquery import write_powerquery
from .emit_dbt import write_dbt_model, write_dbt_seed

FORMAT_CHOICES = ["csv", "tsql", "snowflake", "databricks", "powerquery", "dbt", "all"]

_DEFAULT_PATHS = {
    "csv": "outputs/nz-date-dimension.csv",
    "tsql": "outputs/nz-date-dimension.tsql.sql",
    "snowflake": "outputs/nz-date-dimension.snowflake.sql",
    "databricks": "outputs/nz-date-dimension.databricks.sql",
    "powerquery": "outputs/nz-date-dimension.pq",
}
_DBT_MODEL_PATH = "outputs/dbt/models/nz_date_dimension.sql"
_DBT_SEED_PATH = "outputs/dbt/seeds/nz_date_dimension_holidays.csv"

_SQL_WRITERS = {
    "tsql": write_tsql,
    "snowflake": write_snowflake,
    "databricks": write_databricks,
}

def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

def _write_one_format(fmt: str, rows: list, out: str, fiscal_start_month: int,
                       generated_on: date) -> list:
    """Write a single format and return the list of paths written."""
    if fmt == "csv":
        _ensure_parent_dir(out)
        write_csv(rows, out, generated_on=generated_on)
        return [out]
    if fmt == "dbt":
        _ensure_parent_dir(_DBT_MODEL_PATH)
        _ensure_parent_dir(_DBT_SEED_PATH)
        write_dbt_model(_DBT_MODEL_PATH, fiscal_start_month=fiscal_start_month)
        write_dbt_seed(rows, _DBT_SEED_PATH)
        return [_DBT_MODEL_PATH, _DBT_SEED_PATH]
    # tsql / snowflake / databricks / powerquery
    _ensure_parent_dir(out)
    if fmt == "powerquery":
        write_powerquery(rows, out, fiscal_start_month=fiscal_start_month)
    else:
        _SQL_WRITERS[fmt](rows, out, fiscal_start_month=fiscal_start_month)
    return [out]

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate the NZ date dimension.")
    p.add_argument("--start-year", type=int, default=2015)
    p.add_argument("--end-year", type=int, default=2050)
    p.add_argument("--out", default=None,
                    help="Output path. Defaults per --format (unchanged CSV "
                         "default: outputs/nz-date-dimension.csv). Ignored "
                         "when --format all (every format uses its own default path).")
    p.add_argument("--fiscal-start-month", type=int, default=4)
    p.add_argument("--format", choices=FORMAT_CHOICES, default="csv",
                    help="Output format. 'all' writes every format (spec section 8).")
    a = p.parse_args(argv)

    rows = build_dataset(a.start_year, a.end_year, a.fiscal_start_month)
    generated_on = date.today()

    formats = [f for f in FORMAT_CHOICES if f != "all"] if a.format == "all" else [a.format]
    written = []
    for fmt in formats:
        # --out only applies to a single explicit non-'all' format; 'all'
        # and multi-file formats (dbt) always use their own default paths.
        out = a.out if (a.out and a.format != "all" and fmt not in ("dbt",)) else _DEFAULT_PATHS.get(fmt)
        written.extend(_write_one_format(fmt, rows, out, a.fiscal_start_month, generated_on))

    for path in written:
        print(f"Wrote {len(rows)} rows to {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
