# AU + Combined ANZ build report

**Date:** 2026-07-22
**Baseline:** Plan A + Plan B complete, 84 tests passing (main @ `01d8987`).
**Design:** `anz-date-dimension-au-combined-design.md` §1–6 (design) + §7 (pre-build QA resolutions, authoritative).
**Result:** 166 tests passing (84 baseline + 82 net-new). NZ CSV output confirmed byte-identical against the shipped `outputs/nz-date-dimension.csv` (sha256 `40e97e5bad70da7adbad9e43c1556c14c99bdaa8401e7f9ac100d3b5f386c973`, matched exactly, and now a permanent regression test). `holidays` pinned at `0.101` (was installed at `0.100`, diverging from the existing pin — reconciled). Strict TDD throughout: every new/changed behaviour had a failing test confirmed before the corresponding implementation.

## Refactor approach

Rather than bolting AU onto the existing NZ-hardcoded modules, this build introduced two new foundation modules everything else derives from:

- **`countries.py`** — a `CountryConfig` dataclass (python-holidays class, subdivision codes, fiscal start month, observed-detection strategy, table/output naming, gazetting cap) with `NZ` and `AU` instances and a `get_country()` lookup. Adding a future Pacific country is "add one `CountryConfig`", not a rewrite.
- **`columns.py`** — `stable_columns(country_codes)` / `seed_columns(country_codes)`, replacing the hardcoded `STABLE_COLUMNS`/`SEED_COLUMNS` lists. Single-country output keeps bare `IsHoliday_<code>` flags (NZ stays byte-identical); Combined mode inserts a `Country` column after `DateKey` and country-prefixes every regional flag (`IsHoliday_NZ_<code>` / `IsHoliday_AU_<code>`).

Everything downstream (`holidays_engine.py` — replacing `holidays_nz.py`; `regional.py`; `build.py`; all six emitters; `cli.py`) was then re-parameterised to take a `CountryConfig`/column list instead of importing NZ specifics, with every existing call site keeping its NZ-default behaviour via default-`None`-falls-back-to-NZ parameters. Nine logical commits on `main`, each with its own passing test suite at that point (see `git log`).

## Per-resolution outcome (design doc §7)

| # | Resolution | Outcome |
|---|---|---|
| 1 | Dynamic columns, not hardcoded `NZ_SUBDIVISIONS` | Done — `columns.py`; every emitter (CSV, T-SQL, Snowflake, Databricks, Power Query, dbt) takes an optional `columns` argument. |
| 2 | Country abstraction (holidays class, subdivisions, fiscal month, observed strategy, notes) | Done — `countries.py`. |
| 3 | AU: national+state holidays, 8 state flags, Jul-start fiscal, per-AU `IsBusinessDay` | Done — see AU national/regional split below. |
| 4 | AU observed detection: diff (`observed=True` minus `observed=False`), NZ stays suffix-based and byte-identical | Done — `holidays_engine.NationalHolidays`, two strategies, verified live against holidays==0.101. NZ regression test confirms zero behavioural drift. |
| 5 | Combined: `Country` column, country-prefixed regional flags, composite PK `(Date, Country)` | Done — `build.py`, `sql_common.create_table_sql(..., primary_key=[...])`. |
| 6 | CLI `--country`, `--fiscal-start-month` default `None`, country-parameterised paths/table names | Done — `cli.py`. |
| 7 | `holidays` version reconciliation, pin 0.101, re-confirm AU behaviour on pinned version | Done — installed 0.101, full NZ suite green, AU observed/state behaviour re-verified live on 0.101 (see below). |

## A design gap found during implementation (not in §7, resolved here)

The design doc assumed AU's national (no-subdivision) `python-holidays` calendar would Mondayise the same way NZ's does. Reading `holidays/countries/australia.py` directly and verifying live showed this is **not the case**: `Australia()` with no subdivision only adds the raw, unshifted common holidays (New Year's, Australia Day's nominal date, Good Friday, Easter Monday, ANZAC Day, Christmas, Boxing Day) — `observed=True` and `observed=False` produce **identical** output for the no-subdiv case, because Australia has no single nationally-legislated weekend-shift rule, only state-level ones (confirmed in the library source: the observed-shift calls only appear inside the per-state `_populate_subdiv_*_public_holidays()` methods). The design's illustrative "national holidays" list also included Sovereign's/King's Birthday, which is actually state-only in the modern (2015+) calendar for the same reason.

**Decision made:** keep AU's architecture a strict 1:1 parallel to NZ's already-shipped, already-tested pattern — main `IsHoliday`/`HolidayName`/`IsObserved`/`IsBusinessDay` come from the no-subdiv national layer (a state-only holiday like WA's Labour Day does **not** flip these, exactly like NZ's provincial anniversaries don't); the 8 `IsHoliday_<STATE>` flags come from the full per-state calendars (all state-specific days, correctly Mondayised). This is the minimal-diff, most defensible reading of design §1's own framing ("country-parameterise the generator... exactly as the NZ spec anticipated") and is documented in the README's "Observed-day detection" section. The AU "diff" observed-detection strategy is real and tested (verified against AU's real per-state make-up Mondays); it simply never fires at the national level for AU specifically, which is an accurate reflection of Australian public holiday law, not a bug.

## Known limitations (flagged, not silently shipped)

1. **Combined SQL relative-view fiscal columns.** The T-SQL/Snowflake/Databricks companion "relative columns" VIEW computes one `TodayFiscalYear`/`TodayFiscalQuarter` reference point for the whole view (NZ's convention by default, or whatever `--fiscal-start-month` is given). The static base table's per-row `FiscalYear`/`FiscalQuarter` are always correct per-country; every non-fiscal relative column (`DayOffset`, `IsCurrentMonth`, `IsToday`, ...) is unaffected. But `FiscalYearOffset`/`IsCurrentFiscalYear`/`IsFiscalYTD`/`FiscalQuarterOffset` in that view are only fiscal-calendar-correct for NZ rows, not AU rows, in Combined mode. Fixing this properly needs a per-`Country` `CASE` in `relative_select_sql`, which I scoped out given the task's own Combined test list didn't call for it. Documented in README and column-dictionary.
2. **Combined dbt is unsupported by design**, not by oversight — `build_dbt_model_sql(country="combined")` raises `NotImplementedError` with a clear message, and the CLI's `--format all --country combined` skips dbt with a printed note rather than crashing the run. The underlying reason is the same as #1: the hand-authored model applies one `fiscal_start_month` to its whole `dbt_utils.date_spine`, which can't represent a per-row country-dependent fiscal year without a materially larger rewrite (a per-country CTE branch). `--country nz --format dbt` and `--country au --format dbt` both work fully.

Neither limitation affects any of the task's explicit test requirements (NZ regression, AU sample assertions, Combined `Country`/prefixed-flags/isolation/composite-key). Both are called out prominently in the README (`Combined ANZ mode` section) and column dictionary so a future implementer — human or agent — doesn't have to rediscover them.

## Test suite

**166 passed, 0 failed** (`python -m pytest -v`), up from the 84-test baseline:

- 82 net-new tests across 6 new files (`test_countries.py`, `test_columns.py`, `test_holidays_engine.py`, `test_nz_regression.py`) and additions to the 10 pre-existing test files that imported NZ constants or exercised the emitters/CLI (`test_build.py`, `test_regional.py`, `test_cli.py`, `test_emit_csv.py`, `test_sql_common.py`, `test_emit_tsql.py`, `test_emit_snowflake.py`, `test_emit_databricks.py`, `test_emit_powerquery.py`, `test_emit_dbt.py`).
- `test_holidays_nz.py` deleted, fully superseded by `test_holidays_engine.py` (same NZ assertions carried forward unchanged, plus AU/diff-strategy coverage).
- **NZ regression:** `tests/test_nz_regression.py` regenerates the default-args CLI CSV and `filecmp.cmp()`s it byte-for-byte against the committed `outputs/nz-date-dimension.csv` — this is now a permanent, automatic guard, not just the one-off manual sha256 check performed during this build.
- **AU:** Australia Day 26 Jan (national nominal date + all 8 states' Mondayised observance verified live); Melbourne Cup 1st Tue Nov VIC-only (verified live against all 8 states); WA Labour Day (verified live, no other state collides on that date); the AU "diff" observed strategy directly against real per-state make-up Mondays; July fiscal start (`1 Aug 2025 → FY2026`, ends `30 Jun 2026`) at both the `fiscal.py` and dataset/CLI levels; `IsBusinessDay` around a state holiday (state-only holiday does not flip the national flag, matching the NZ precedent).
- **Combined:** `Country` column and position; country-prefixed flags only (no bare form leaks in); structural no-cross-country-bleed check across every row of a full year; per-row-country fiscal columns; per-row-country national holidays; composite-key SQL emission (T-SQL/Snowflake/Databricks); Combined dbt's explicit `NotImplementedError`.

## End-to-end verification (scratch dirs, outside the test suite)

- `--country au --format all` (2024–2027): all 7 outputs written (CSV, T-SQL, Snowflake, Databricks, Power Query, dbt model + seed) with `au-date-dimension.*`/`AUDateDimension`/`au_date_dimension` naming throughout. Spot-checked: 26 Jan 2025 (Sunday) shows `IsHoliday=true, HolidayName=Australia Day, IsObserved=false`, all 8 state flags false (the make-up Monday carries them instead); 3 Mar 2025 (WA Labour Day) shows `IsHoliday=false, IsBusinessDay=true, IsHoliday_WA=true`; 1 Aug 2025 shows `FiscalYear=2026, FiscalStartOfYear=2025-07-01`.
- `--country combined --format csv` (2024–2027): 2,922 data rows (both countries' full range), `Country` column at position 3, 17 `IsHoliday_NZ_*` + 8 `IsHoliday_AU_*` columns. Spot-checked 6 Feb 2025 (Waitangi Day): the NZ row shows `IsHoliday=true, HolidayName=Waitangi Day, FiscalYear=2025` (Apr-start) with every NZ regional flag true and every AU flag false; the AU row on the same date shows `IsHoliday=false, FiscalYear=2025` (Jul-start, different fiscal boundary) with every flag false.

## Deviations / decisions requiring your attention

1. The AU national/state architecture decision above (main columns = national-only, matching NZ's own precedent) — a real, load-bearing design call the original design doc didn't fully specify, made because empirical testing against the library contradicted its assumption.
2. Scoped Combined dbt support out entirely (clear error, not silent wrong output) rather than attempting a per-country-branching dbt model rewrite.
3. Scoped the Combined SQL relative-view's fiscal-offset columns to "NZ reference calendar, documented limitation" rather than a per-`Country` CASE rewrite of `relative_select_sql`.
4. `holidays_nz.py` was deleted outright (not kept as a backward-compat shim) and replaced by `holidays_engine.py` — the task explicitly permitted updating the ~10 dependent test files' imports, and a shim would have meant maintaining two parallel implementations of the same logic.

None of these were pushed anywhere — all nine commits are local-only on `main`, as instructed.

## Concerns

- The Combined SQL relative-view and Combined dbt limitations (above) are real functionality gaps, not just documentation notes. If Combined SQL/dbt consumers are expected soon, both are natural next increments (a per-`Country` CASE in `relative_select_sql`; a per-country CTE branch in the dbt model) — flagging now so they're a deliberate backlog item rather than a surprise.
- `outputs/nz-date-dimension.csv` (the shipped download) was **not** regenerated/re-committed as part of this build — it's still the pre-refactor file, now proven byte-identical to what the refactored generator produces. No AU or Combined CSV was added to `outputs/` (out of scope; the task's own scratch-dir verification instruction implied these are demonstration runs, not repo artifacts to ship).
