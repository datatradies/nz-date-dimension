# Build report — NZ Date Dimension (Plan A)

Built strictly TDD, task-by-task, from
`C:\Projects\datatradies-website\.claude\analysis\nz-date-dimension-plan.md`.
Repo: `C:\Projects\nz-date-dimension\` (new, standalone; `datatradies-website`
was not modified). Default branch `master`, no worktrees used.

**Environment:** Python 3.13.5 (`python`), Windows 11, Git Bash. Venv at
`.venv/` (gitignored). `holidays==0.101`, `pytest==9.1.1`.

## Overall status: DONE

All 9 tasks implemented in order, TDD followed on every task (failing test
confirmed → minimal implementation → passing test confirmed → commit).
9 commits total. Full suite: **22 passed, 0 failed**.

## Per-task outcome

| Task | Outcome | Commit |
|---|---|---|
| 1. Repo scaffold, pinned dependency, licences | PASS (smoke test) | `3adea0f` |
| 2. Calendar core columns | PASS (2/2 tests) | `83a1c8b` |
| 3. NZ fiscal-year columns | PASS (3/3 tests) | `aa3f834` |
| 4. National holiday columns (Mondayisation, Matariki, one-offs) | PASS (7/7 tests) | `25bea2d` |
| 5. Regional provincial-anniversary flags | PASS (3/3 tests) | `bb58014` |
| 6. Assemble full dataset | PASS (4/4 tests) | `df3f77d` |
| 7. CSV emitter | PASS (1/1 test) | `58970cc` |
| 8. CLI entry point | PASS (1/1 test) + real CSV generated | `d180809` |
| 9. README, column dictionary, attribution | Docs written, full suite green | `d29c24e` |

Every task followed the RED → GREEN cycle exactly as specified: each new
test module was run first and confirmed to fail with `ModuleNotFoundError`
(module/function not yet defined) before the corresponding implementation
file was written, then re-run and confirmed to pass.

## Final `pytest -v` summary

```
22 passed in 0.45s
```

Breakdown: `test_build.py` (4), `test_calendar_core.py` (2), `test_cli.py`
(1), `test_emit_csv.py` (1), `test_fiscal.py` (3), `test_holidays_nz.py`
(7), `test_regional.py` (3), `test_smoke.py` (1) = 22.

## The two execution-time verifications

### 1. `IsObserved` marker (Task 4)

```
python -c "import holidays; from datetime import date; print(holidays.NewZealand(years=2021, observed=True).get(date(2021,2,8)))"
```

Result: **`'Waitangi Day (observed)'`**

This matches the plan's assumption exactly — python-holidays does append
the literal suffix `(observed)` to Mondayised days. No adjustment to the
`is_observed` detection logic in `holidays_nz.py` was needed; the plan's
code was used verbatim. `test_waitangi_mondayisation_2021` passed on the
first run.

### 2. Auckland Anniversary 2025 date + subdivision codes (Task 5)

```
python -c "import holidays; nz=holidays.NewZealand(subdiv='AUK', years=2025); print({d:n for d,n in nz.items() if 'Anniversary' in n})"
```

Result: **`{date(2025, 1, 27): 'Auckland Anniversary Day'}`** — Monday 27
January 2025, exactly as the plan assumed. No test-date adjustment needed;
`test_auckland_anniversary_flags_auckland_only` passed on the first run.

**Subdivision code check** — all 17 codes in the plan's `NZ_SUBDIVISIONS`
list were constructed and iterated (`holidays.NewZealand(subdiv=code,
years=2025)`) with zero errors. Separately, `holidays.NewZealand.subdivisions`
on the installed version (0.101) reports **18** entries, not 17 — the extra
one is the string `'South Canterbury'` (a full name, not a 3-letter code,
unlike every other entry). This is exactly the case the plan's own code
comment flagged for confirmation ("NOTE: confirm South Canterbury handling
during execution — may be a subregion"). Resolution: `NZ_SUBDIVISIONS`
deliberately excludes it, per the plan's design and its own test asserting
`len(NZ_SUBDIVISIONS) == 17`. This is documented in a code comment in
`holidays_nz.py`. No plan code changes were required.

## Pinned dependency

`requirements.txt`:
```
holidays==0.101
pytest
```

`holidays==0.101` is the exact version installed via `pip install holidays
pytest` at scaffold time (Task 1). This is newer than the plan's example
figure ("e.g. `holidays==0.62`") — that was only an illustrative example in
the plan, not a version requirement, so no deviation.

## Generated output

Ran the CLI to produce the real default dataset:
```
outputs/nz-date-dimension.csv   (2015-01-01 .. 2050-12-31)
```
- **13,149 rows** — verified correct: 36 years × 365 days + 9 leap days
  (2016, 2020, 2024, 2028, 2032, 2036, 2040, 2044, 2048) = 13,149.
- First row `Date` = `2015-01-01`, last row `Date` = `2050-12-31`.
- Spot-checked holidays in the generated file:
  - `2025-12-25` → `HolidayName = Christmas Day`, `IsBusinessDay = false`.
  - `2021-02-08` → `HolidayName = Waitangi Day (observed)`, `IsObserved = true`.
  - `2022-06-24` → `HolidayName = Matariki`.
  - `2025-01-27` → `IsHoliday_AUK = true`, `IsHoliday_WGN = false`.
  - `GeneratedOn` on every row = the run date.
- This file is **not committed** (gitignored via `outputs/*.csv` per Task 1)
  — regenerate locally with the Quick start command in `README.md`.

## Deviations from the plan (with reasons)

1. **Added `pyproject.toml`** with:
   ```toml
   [tool.pytest.ini_options]
   pythonpath = ["generator"]
   testpaths = ["tests"]
   ```
   Not in Task 1's file list, but the outer task brief explicitly asked for
   *"a conftest.py/pyproject.toml that puts generator/ on the path — pick
   whichever is cleanest and note what you did."* Chose `pyproject.toml`'s
   built-in `pythonpath` option over a `conftest.py` sys.path hack because
   it's declarative, doesn't touch `sys.path` imperatively, and is
   respected by both `pytest` and IDEs. This is why `pytest -v` (or
   `python -m pytest`) works unmodified from the repo root without needing
   `cd generator` first.

2. **README quick-start command differs from the plan's literal Task 8
   Step 4 instruction.** The plan says: *"Run `python -m
   nz_date_dimension.cli` (from `generator/`) → writes
   `outputs/nz-date-dimension.csv`."* But the plan's own File Structure
   diagram places `outputs/` as a **sibling** of `generator/` at the repo
   root, not nested inside it — so running from `generator/` with the
   default relative `--out outputs/nz-date-dimension.csv` would actually
   create a new `generator/outputs/` directory rather than writing to the
   real one. This is a small internal inconsistency in the plan. Resolved
   by running `PYTHONPATH=generator python -m nz_date_dimension.cli` from
   the **repo root** instead (verified working — produced the correct
   13,149-row file at `outputs/nz-date-dimension.csv`), and documented
   both that form and the `cd generator && ... --out
   ../outputs/nz-date-dimension.csv` alternative in `README.md`. No code
   or test changes were needed — `cli.py` and `test_cli.py` are exactly as
   specified in the plan.

No other deviations. All file paths, module names, function signatures,
column names/order, test cases, and commit messages match the plan
verbatim.

## Concerns / known limitations (not gaps against Plan A's scope)

- **Not pip-installable as a package** — there's no `[build-system]` /
  `setuptools` config, only the pytest `pythonpath` setting. Fine for
  Plan A (a generator run via `PYTHONPATH` or from `generator/`), but a
  future consumer wanting `pip install nz-date-dimension` would need a
  proper `pyproject.toml` `[build-system]` + package metadata — explicitly
  out of scope here and not requested by the plan.
- **South Canterbury** is not one of the 17 regional flag columns (see
  verification #2 above) — intentional per the plan's own design, but
  worth knowing if a consumer specifically needs that subregion's
  anniversary date; it would need to be added as an 18th column in a
  future revision using the subdivision key `'South Canterbury'`.
- **Git line-ending warnings** (`LF will be replaced by CRLF`) appeared on
  every commit — cosmetic only (no `.gitattributes` was specified by the
  plan), doesn't affect test behaviour or file contents.
- Deferred to Plan B, as the plan itself specifies: relative/time-
  intelligence columns, SQL/M/dbt emitters + cross-format consistency
  test, and a Power BI `.pbit`/`.pbix` fast-follow.
