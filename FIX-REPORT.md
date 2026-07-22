# Fix Wave — Response to REVIEW-REPORT.md

**Scope:** the non-blocking follow-ups from the independent code review
(`REVIEW-REPORT.md`), applied on top of the READY-TO-SHIP Plan A build.
Followed TDD for the one behaviour change (M-1); the two test-coverage
findings (I-1, M-4) added tests against already-correct production code.

---

## I-1 (Important) — Complete the observed-day test coverage

**Where:** `tests/test_holidays_nz.py`

Queried the pinned library first, as instructed:

```
python -c "import holidays; nz=holidays.NewZealand(years=[2021,2022], observed=True); ..."
```

Confirmed real observed dates:

- **New Year 2022:** `2022-01-01` (Sat) `New Year's Day` → observed
  `2022-01-03` (Mon) `New Year's Day (observed)`; `2022-01-02` (Sun)
  `Day after New Year's Day` → observed `2022-01-04` (Tue) `Day after New
  Year's Day (observed)`.
- **Christmas/Boxing 2021:** `2021-12-25` (Sat) `Christmas Day` → observed
  `2021-12-27` (Mon) `Christmas Day (observed)`; `2021-12-26` (Sun)
  `Boxing Day` → observed `2021-12-28` (Tue) `Boxing Day (observed)`.

Added `test_new_year_mondayisation_2022` and
`test_christmas_boxing_mondayisation_2021`, asserting
`IsHoliday=True, IsObserved=True, IsBusinessDay=False` on the transferred
days, matching the pattern already used for Waitangi Day. Both passed
immediately — the generic `(observed)`-suffix detection in
`holidays_nz.py` was already correct; it just wasn't pinned by a test for
these two spec-named cases.

## M-4 (Minor) — "Not observed on the actual date" test

**Where:** `tests/test_holidays_nz.py`

Added `test_waitangi_actual_weekend_date_is_not_observed`
(`2021-02-06`, a Saturday: `IsHoliday=True`, `IsObserved=False`,
`IsBusinessDay=False` because it's still a weekend) and folded the same
check into the Christmas/Boxing test for `2021-12-25` / `2021-12-26`.
Confirms `IsObserved` is only ever `True` on the transferred day, never on
the actual weekend occurrence.

## M-1 (Minor) — Fiscal year-ending logic for any `fiscal_start_month`

**Where:** `generator/nz_date_dimension/fiscal.py`

TDD: added two failing-first tests to `tests/test_fiscal.py`
(`test_calendar_year_fiscal_start_month_1`,
`test_australian_fiscal_start_month_7`), confirmed
`test_calendar_year_fiscal_start_month_1` failed against the old code
(`FiscalYear` came back `2026` instead of `2025` for `start_month=1`),
then refactored:

- `_fiscal_start_of_year(d, start_month)` — the most recent
  `(start_month, 1)` on or before `d`.
- `_fiscal_end_of_year(start)` — `start` + 1 year − 1 day.
- `FiscalYear` = `fiscal_end_of_year.year` (derived, so label and
  boundary dates can never disagree).
- `FiscalYearLabel` = `f"FY{FiscalYear}"`.
- `FiscalQuarter`/`FiscalMonth`/`FiscalDayOfYear` unchanged, still
  derived from `fiscal_start_of_year`.

**Verified dates (all against the new code):**

- `start_month=1` (calendar year), `d=2025-06-01` → `FiscalYear=2025`,
  `FiscalStartOfYear=2025-01-01`, `FiscalEndOfYear=2025-12-31` (was
  `FiscalYear=2026` before the fix — the bug the review flagged).
- `start_month=7` (AU), `d=2025-08-01` → `FiscalYear=2026`,
  `FiscalStartOfYear=2025-07-01`, `FiscalEndOfYear=2026-06-30`.
- **NZ default unchanged:** `start_month=4`, `d=2025-04-01` →
  `FiscalYear=2026`, `FiscalStartOfYear=2025-04-01`,
  `FiscalEndOfYear=2026-03-31` (existing tests
  `test_april_is_start_of_fiscal_year`, `test_march_is_end_of_fiscal_year`,
  `test_fiscal_year_helper` all still pass unmodified).
- Re-ran the review's own baseline checks against the fixed code:
  `build_dataset(2015, 2050)` → **13,149** rows (unchanged);
  `build_dataset(2024, 2024)` → **366** rows, and
  `2024-03-31` → `FiscalDayOfYear=366`, `FiscalYear=2024` (both unchanged)
  — the NZ leap-fiscal-year output is byte-for-byte identical to before
  the refactor.

## M-2 (Minor) — Windows-friendly README quick-start

**Where:** `README.md`

Reordered the quick-start so the portable `cd generator` +
`python -m nz_date_dimension.cli --out ../outputs/nz-date-dimension.csv`
form is the sole primary command (works unmodified on PowerShell, cmd.exe,
and bash/zsh). The repo-root `PYTHONPATH=...` variant is now secondary and
given as an explicit per-shell table (bash/zsh, PowerShell, cmd.exe)
instead of a single bash-only line.

## M-3 (Minor) — Split dev dependency

**Where:** `requirements.txt`, `requirements-dev.txt` (new), `README.md`

`requirements.txt` now contains only the runtime dependency
(`holidays==0.101`). Added `requirements-dev.txt` (`-r requirements.txt` +
`pytest`) and updated the README's "Running the tests" section to install
from `requirements-dev.txt`. Verified `pip install -r requirements-dev.txt`
resolves both files correctly in the repo's `.venv`.

## Skipped (per instructions)

- **M-5 / `HolidayCode`:** not added — spec marks it explicitly optional.
- **`DATA-LICENSE`:** left as-is — acceptable per the review.

---

## Final verification

```
python -m pytest -v
```

**27 passed** in `0.58s` (22 original + 5 new: 3 in `test_holidays_nz.py`
for I-1/M-4, 2 in `test_fiscal.py` for M-1). Full run in the repo's
`.venv` (Python 3.13.5, `holidays==0.101`, `pytest==9.1.1`).
