import csv
from datetime import date
from .build import STABLE_COLUMNS

def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, date):
        return v.isoformat()
    return v

def write_csv(rows: list, path: str, generated_on: date) -> None:
    header = STABLE_COLUMNS + ["GeneratedOn"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([_fmt(r[c]) for c in STABLE_COLUMNS] + [generated_on.isoformat()])
