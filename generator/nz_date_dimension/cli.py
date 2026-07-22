import argparse
import os
from datetime import date
from .build import build_dataset
from .columns import stable_columns, seed_columns
from .countries import get_country, COMBINED_TABLE_NAME, COMBINED_OUTPUT_STEM, COMBINED_COUNTRY_ORDER
from .emit_csv import write_csv
from .emit_tsql import write_tsql
from .emit_snowflake import write_snowflake
from .emit_databricks import write_databricks
from .emit_powerquery import write_powerquery
from .emit_dbt import write_dbt_model, write_dbt_seed

FORMAT_CHOICES = ["csv", "tsql", "snowflake", "databricks", "powerquery", "dbt", "all"]
COUNTRY_CHOICES = ["nz", "au", "combined"]

_SQL_WRITERS = {
    "tsql": write_tsql,
    "snowflake": write_snowflake,
    "databricks": write_databricks,
}

def _is_combined(country: str) -> bool:
    return country.upper() == "COMBINED"

def _country_codes(country: str) -> list:
    """The country code(s) in a dataset for this --country value -- used to
    derive its dynamic column list (spec §7)."""
    return list(COMBINED_COUNTRY_ORDER) if _is_combined(country) else [country.upper()]

def _output_stem(country: str) -> str:
    return COMBINED_OUTPUT_STEM if _is_combined(country) else get_country(country).output_stem

def _table_name(country: str) -> str:
    return COMBINED_TABLE_NAME if _is_combined(country) else get_country(country).table_name

def _default_paths(country: str) -> dict:
    stem = _output_stem(country)
    return {
        "csv": f"outputs/{stem}.csv",
        "tsql": f"outputs/{stem}.tsql.sql",
        "snowflake": f"outputs/{stem}.snowflake.sql",
        "databricks": f"outputs/{stem}.databricks.sql",
        "powerquery": f"outputs/{stem}.pq",
    }

def _dbt_paths(country: str) -> tuple:
    stem = _output_stem(country).replace("-", "_")
    return (f"outputs/dbt/models/{stem}.sql", f"outputs/dbt/seeds/{stem}_holidays.csv")

def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

def _write_one_format(fmt: str, rows: list, out: str, fiscal_start_month: int,
                       generated_on: date, country: str, table_name: str,
                       columns: list, seed_cols: list, primary_key: list) -> list:
    """Write a single format and return the list of paths written."""
    if fmt == "csv":
        _ensure_parent_dir(out)
        write_csv(rows, out, generated_on=generated_on, columns=columns)
        return [out]
    if fmt == "dbt":
        if _is_combined(country):
            # Combined rows need a per-row country-dependent fiscal year --
            # not expressible in this hand-authored single dbt model (see
            # emit_dbt.build_dbt_model_sql's own NotImplementedError).
            # --format all must not crash the whole run over this -- skip
            # with a clear note instead.
            print("Skipping dbt: not supported for --country combined "
                  "(generate NZ and AU dbt models separately instead).")
            return []
        model_path, seed_path = _dbt_paths(country)
        _ensure_parent_dir(model_path)
        _ensure_parent_dir(seed_path)
        write_dbt_model(model_path, fiscal_start_month=fiscal_start_month, country=country)
        write_dbt_seed(rows, seed_path, columns=seed_cols)
        return [model_path, seed_path]
    # tsql / snowflake / databricks / powerquery
    _ensure_parent_dir(out)
    if fmt == "powerquery":
        write_powerquery(rows, out, fiscal_start_month=fiscal_start_month, columns=columns)
    else:
        _SQL_WRITERS[fmt](rows, out, table_name=table_name, fiscal_start_month=fiscal_start_month,
                           columns=columns, primary_key=primary_key)
    return [out]

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate the NZ / AU / Combined ANZ date dimension.")
    p.add_argument("--start-year", type=int, default=2015)
    p.add_argument("--end-year", type=int, default=2050)
    p.add_argument("--country", choices=COUNTRY_CHOICES, default="nz",
                    help="Which calendar to generate: nz, au, or combined "
                         "(unions both under a Country column). Default: nz.")
    p.add_argument("--out", default=None,
                    help="Output path. Defaults per --format and --country "
                         "(unchanged NZ CSV default: outputs/nz-date-dimension.csv). "
                         "Ignored when --format all (every format uses its own default path).")
    p.add_argument("--fiscal-start-month", type=int, default=None,
                    help="First month of the fiscal year (1=January .. 12=December). "
                         "Default: the country's own convention (NZ=4, AU=7). An "
                         "explicit value overrides that for every country in the dataset.")
    p.add_argument("--format", choices=FORMAT_CHOICES, default="csv",
                    help="Output format. 'all' writes every format (spec section 8). "
                         "'dbt' is not supported for --country combined.")
    a = p.parse_args(argv)

    country = a.country
    if _is_combined(country) and a.format == "dbt":
        raise NotImplementedError(
            "dbt is not supported for --country combined: this model applies one "
            "fiscal_start_month to the whole date spine, but Combined rows need a "
            "per-row country-dependent fiscal year (NZ Apr-start vs AU Jul-start). "
            "Generate the NZ and AU dbt models separately instead."
        )

    rows = build_dataset(a.start_year, a.end_year, a.fiscal_start_month, country=country)
    generated_on = date.today()

    # Resolve fiscal_start_month to a concrete int for the emitters' LIVE
    # "relative columns" view/query (they each default to 4 in their own
    # signature, so passing bare None through would embed the literal
    # string "None" into generated SQL/M). build_dataset() above already
    # resolved it per-row for the STATIC FiscalYear/etc. columns
    # internally -- this is a separate resolution for the dynamic view.
    # KNOWN LIMITATION: Combined mode's relative view has one "Today"
    # fiscal reference point for the whole view (NZ's Apr-start convention
    # unless overridden), so FiscalYearOffset/IsCurrentFiscalYear/
    # IsFiscalYTD/FiscalQuarterOffset in that companion view are correct
    # for NZ rows but not fiscal-calendar-correct for AU rows -- the
    # static base table (every row's own FiscalYear/FiscalQuarter) is
    # unaffected and always correct per-row per-country.
    if a.fiscal_start_month is not None:
        resolved_fsm = a.fiscal_start_month
    elif _is_combined(country):
        resolved_fsm = get_country("NZ").fiscal_start_month
    else:
        resolved_fsm = get_country(country).fiscal_start_month

    country_codes = _country_codes(country)
    columns = stable_columns(country_codes)
    seed_cols = seed_columns(country_codes)
    table_name = _table_name(country)
    primary_key = ["Date", "Country"] if _is_combined(country) else ["Date"]
    default_paths = _default_paths(country)

    formats = [f for f in FORMAT_CHOICES if f != "all"] if a.format == "all" else [a.format]
    written = []
    for fmt in formats:
        # --out only applies to a single explicit non-'all' format; 'all'
        # and multi-file formats (dbt) always use their own default paths.
        out = a.out if (a.out and a.format != "all" and fmt not in ("dbt",)) else default_paths.get(fmt)
        written.extend(_write_one_format(fmt, rows, out, resolved_fsm, generated_on,
                                          country, table_name, columns, seed_cols, primary_key))

    for path in written:
        print(f"Wrote {len(rows)} rows to {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
