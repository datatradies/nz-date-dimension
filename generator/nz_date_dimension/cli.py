import argparse
from datetime import date
from .build import build_dataset
from .emit_csv import write_csv

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate the NZ date dimension.")
    p.add_argument("--start-year", type=int, default=2015)
    p.add_argument("--end-year", type=int, default=2050)
    p.add_argument("--out", default="outputs/nz-date-dimension.csv")
    p.add_argument("--fiscal-start-month", type=int, default=4)
    a = p.parse_args(argv)
    rows = build_dataset(a.start_year, a.end_year, a.fiscal_start_month)
    write_csv(rows, a.out, generated_on=date.today())
    print(f"Wrote {len(rows)} rows to {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
