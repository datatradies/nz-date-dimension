# Plan B report — NZ Date Dimension

Built strictly TDD, task-by-task, from `datatradies-website`'s
`nz-date-dimension-spec.md` (§4.5 relative columns, §7 dynamic-vs-static
handling, §8 output formats). Extends the completed, reviewed **Plan A**
(calendar + fiscal + national holidays + 17 regional flags + CSV emitter +
CLI, 27 tests) in place, in this repo (`C:\Projects\nz-date-dimension`),
on `main`. `datatradies-website` was not touched.

**Environment:** Python 3.13.5 (`python`), Windows 11, Git Bash.
`holidays==0.101`, `pytest==9.0.2` (per repo's `.venv`).

## Overall status: DONE

Every RED → GREEN → commit cycle was followed: each new test module (or
new test in an existing module) was run and confirmed to fail first
(`ModuleNotFoundError` or `SystemExit`/argparse error for missing CLI
flags), then the minimal implementation was added and re-run to confirm
green, then committed. One genuine bug was caught this way (see
"Deviations" below) — TDD did its job.

**Final `python -m pytest -v`: 74 passed, 0 failed** (27 Plan A + 47 Plan
B). No skips, no xfails.

## Commits (9, all on `main`, none pushed)

| Commit | Summary |
|---|---|
| `672bae7` | `relative.py` — relative/time-intelligence columns against an injectable `today` |
| `0d7737e` | T-SQL, Snowflake, and Databricks SQL emitters (+ shared `sql_common.py`) |
| `39b2cd0` | Power Query (M) emitter with live relative columns |
| `f91c33f` | refactor: extract `relative_select_sql()` as a reusable fragment |
| `7e4bc66` | dbt model + seed emitter using `date_spine` and a holiday seed |
| `57da392` | test: cross-format consistency guard (CSV / T-SQL / Power Query) |
| `be9c748` | CLI `--format` flag wiring every Plan B emitter |
| `6894b5f` | docs: README Formats section + column-dictionary relative columns |

Git identity was already `Data Tradies <238778164+datatradies-admin@users.noreply.github.com>`
on this repo (checked before starting — no change needed).

## Per-task / per-format outcome

| Task | Outcome | Tests |
|---|---|---|
| 1. `relative.py` (offsets + booleans vs. injectable `today`) | DONE | 17/17 (`tests/test_relative.py`) |
| 2a. `sql_common.py` (shared dialect config, typing, literal formatting, view SQL) | DONE | 5/5 (`tests/test_sql_common.py`) |
| 2b. `emit_tsql.py` | DONE | 3/3 |
| 2c. `emit_snowflake.py` | DONE | 2/2 |
| 2d. `emit_databricks.py` | DONE | 2/2 |
| 3. `emit_powerquery.py` | DONE | 4/4 |
| 4. `emit_dbt.py` (model + seed) | DONE | 8/8 (incl. a regression test for a bug found during TDD) |
| 5. Cross-format consistency test | DONE | 1/1, round-trips CSV/T-SQL/M on 5 representative dates × all 33 stable columns |
| 6. CLI `--format` wiring | DONE | 6/6 (1 pre-existing + 5 new), default CSV behaviour explicitly regression-tested |
| 7. Docs (README, column-dictionary) | DONE | — |

All six v1 formats (CSV, T-SQL, Snowflake, Databricks, Power Query, dbt)
are implemented, tested, and wired into the CLI. Verified end-to-end
outside the test suite too: ran `python -m nz_date_dimension.cli
--start-year 2024 --end-year 2025 --format all` in a scratch directory —
produced all 7 files (dbt emits 2) with real, well-formed content
(spot-checked CSV header/row, the T-SQL relative view's full `CASE
WHEN`/`DATEDIFF` logic, and the dbt seed's holiday rows).

## Architecture decisions (beyond the literal file list)

1. **`sql_common.py`** — a shared, dialect-parameterised module backing
   `emit_tsql.py`/`emit_snowflake.py`/`emit_databricks.py`. Not named in
   the brief, but matches this repo's existing pattern of small modules
   importing shared logic (e.g. `regional.py` importing `NZ_SUBDIVISIONS`
   from `holidays_nz.py`). Each dialect is a small config dict of
   functions/strings (quote style, type map, date functions); the three
   `emit_*.py` files are thin ~20-line wrappers. Without this, the
   CREATE TABLE / INSERT / relative-view logic would have been
   copy-pasted three times with three chances to drift.

2. **`relative_select_sql()` extraction** (commit `f91c33f`) — mid-course
   refactor splitting `relative_view_sql()`'s `CREATE VIEW` wrapper from
   its reusable `WITH ... SELECT ... FROM ... CROSS JOIN` core, so
   `emit_dbt.py` could reuse the *exact same* relative-column formulas
   against its own staged CTE instead of re-deriving them a third time.
   Verified no behaviour change (full suite green before and after) before
   building on it.

3. **Relative-view SQL layers on the base table's own materialized
   columns** (`t.Year`, `t.Month`, `t.Quarter`, `t.DayOfWeek`,
   `t.FiscalYear`, `t.FiscalQuarter`) rather than re-deriving calendar
   attributes from `t.Date` — only the small "today" CTE needs real date
   functions. Deliberately did **not** self-join the view back into the
   same table to look up "today"'s row (tempting, since the table already
   has every date 2015–2050) — that pattern silently returns zero rows if
   `CURRENT_DATE` ever falls outside the generated range (e.g. year 2051+,
   or a narrower custom-range generation). Computing "today" independently
   via date functions is slightly more verbose but doesn't have that
   failure mode.

4. **WeekOffset via a DATEFIRST-independent / native ISO-weekday formula**
   in every dialect (T-SQL: the `(DATEPART(WEEKDAY,x) + @@DATEFIRST - 2) %
   7 + 1` idiom; Snowflake: native `DAYOFWEEKISO()`; Databricks: converts
   Spark's fixed Sun=1..Sat=7 `dayofweek()` to ISO). Verified by hand for
   every input 1–7 against each formula (worked through in the build
   session) rather than trusting an untested guess — T-SQL's `DATEDIFF(week,
   ...)` was deliberately avoided because its result depends on the
   session's `@@DATEFIRST` setting.

5. **T-SQL boolean handling**: T-SQL doesn't allow a bare comparison
   expression in a `SELECT` list (`SELECT (a = b)` is a syntax error), so
   every boolean relative column is `CASE WHEN <cond> THEN 1 ELSE 0 END`
   for T-SQL specifically; Snowflake/Databricks return native `BOOLEAN`
   from a bare condition. Handled via a per-dialect `bool_wrap` config
   entry rather than a single shared branch, to keep it visible and
   correct per dialect.

6. **dbt model targets Snowflake-flavoured SQL** (`date_part`, `dateadd`,
   `dayofweekiso`/`weekiso`/`yearofweekiso`) rather than being warehouse-
   agnostic. The spec doesn't pin a warehouse for the dbt fast-follow;
   Snowflake keeps the model internally consistent with `emit_snowflake.py`
   and is dbt's most common OSS-adjacent pairing. Documented in the
   model's own header comment ("adjust date functions if compiling
   against a different warehouse") and here.

7. **Batched `INSERT`, 1000 rows/statement** (all three SQL dialects) —
   1000 is SQL Server's hard limit for a multi-row `VALUES` constructor;
   used uniformly rather than a different limit per dialect for
   simplicity, since it's well under Snowflake/Databricks' much higher
   limits too.

8. **Relative-column semantics I had to define** (not pinned exactly by
   the spec, which lists column names but not boundary formulas):
   - `IsLast7Days`/`30`/`90` = inclusive trailing N-day windows ending
     today (`today - (N-1)` .. `today`).
   - `IsPriorMonth`/`IsPriorYear` = the *entire* previous calendar
     month/year (every day in it), not "to date".
   - `IsRolling12Months` = the current (possibly partial) calendar month
     plus the 11 preceding full months, excluding future days within the
     current month.
   All documented in `docs/column-dictionary.md`'s new section and backed
   by explicit boundary tests in `tests/test_relative.py` (e.g.
   `test_last_7_days_boundary`, `test_rolling_12_months_excludes_future_
   days_in_current_month`).

## Cross-format consistency test — design note

Per the brief: "assert CSV vs SQL vs M produce identical stable columns."
A full byte-for-byte round-trip of all 731+ rows across all formats would
need a real SQL and M parser, which doesn't exist in this stdlib-only
project. Instead, `tests/test_cross_format_consistency.py` round-trip
*decodes* (small hand-rolled tokenizers respecting SQL `''` / M `""`
quote-escaping and paren/brace nesting) a representative 5-date sample —
a national holiday (New Year's), a regional-only holiday (Auckland
Anniversary), an ordinary weekday, a weekend, and Christmas — covering
every stable-column category (calendar, fiscal, national holiday,
regional), and asserts all 33 stable columns agree between the original
computed row, the re-read CSV, the extracted T-SQL `INSERT` row, and the
extracted Power Query `#table` row. Manually verified during the build
session that the test is genuinely discriminating (not vacuously true) by
spot-checking that `IsHoliday_AUK=True` vs `IsHoliday_WGN=False` and
`HolidayName=None` decode correctly and distinctly through all three
extraction paths.

## Bug caught and fixed via TDD

While building `emit_dbt.py`, the generated `with_holidays` CTE initially
had a **trailing comma before `FROM`** in its column list (a syntax
error in Snowflake SQL) — the 17 regional-flag columns were built with a
comma embedded in *every* line including the last, then inserted right
before the final explicit column. Caught by manually printing the
generated SQL and reading it (not by a test — the structural tests didn't
happen to check for this). Fixed the join logic and added
`test_dbt_model_has_no_dangling_trailing_commas` as a permanent regression
guard for the general bug class (trailing comma before `FROM` or a
closing CTE paren), verified it passes against the fix.

## Concerns / known limitations

- **No live SQL/Power BI/dbt engine available in this environment** — the
  T-SQL, Snowflake, Databricks, Power Query, and dbt output has been
  verified for structural correctness (right columns, right row counts,
  well-formed syntax by inspection, no dangling commas) and reasoned
  through by hand (e.g. manually verifying the DATEFIRST-independent ISO
  weekday formula against every input 1–7), but **has not been executed
  against a real SQL Server / Snowflake / Databricks / Power BI / dbt
  instance**. This exact caveat is already flagged as non-blocking in the
  spec itself (§12: "Confirm at implementation... test on those engines").
  Recommend running each output against a real (or trial/free-tier)
  instance of each engine before treating this as fully verified,
  particularly the dbt model's Snowflake-specific function names
  (`dayofweekiso`, `weekiso`, `yearofweekiso`, `date_from_parts`) and the
  Power Query M syntax (best exercised by pasting into Power BI Desktop's
  Advanced Editor).
- **dbt model is Snowflake-flavoured only** — not warehouse-agnostic. A
  BigQuery/Postgres/Redshift target would need different date functions;
  documented as a deliberate scope decision, not an oversight.
- **Relative-column boundary semantics** (last-N-days inclusivity, prior-
  period = whole period vs. to-date, rolling-12-months definition) were
  not pinned by the spec and had to be defined during implementation —
  documented explicitly in `docs/column-dictionary.md` and backed by
  tests, but worth a second look if the eventual Power BI consumer
  expects a different convention (e.g. some BI tools define "rolling 12
  months" as a trailing 365-day window rather than 12 calendar months).
- **CSV stable-column output is unchanged** from Plan A — verified via
  `test_cli_default_format_is_still_csv_when_format_omitted` and the
  pre-existing `test_cli_writes_csv`/`test_write_csv_roundtrip` all still
  passing unmodified.
- Did not regenerate/commit a new `outputs/nz-date-dimension.csv` (Plan
  A's committed 2015–2050 CSV is untouched) — the end-to-end `--format
  all` smoke test was run in an isolated scratch directory outside this
  repo specifically to avoid disturbing it.

## Not pushed

Per instructions, nothing was pushed — `main` is 9 commits ahead of
`origin/main`, awaiting review.
