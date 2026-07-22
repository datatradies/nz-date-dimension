# ANZ Date Dimension

A parameterised Python generator that produces a correct, tested date
dimension (calendar table) for **New Zealand**, **Australia**, or a
**Combined ANZ** table unioning both — and emits it to **six formats** —
the kind of "done properly" date dimension every ANZ data warehouse
eventually needs, built once and open-sourced instead of rebuilt badly by
every team.

**Coverage today: NZ + AU (ANZ). The wider Pacific is next** — see
[Roadmap](#roadmap).

## Why this is "done properly"

Most home-grown date dimensions get the easy 80% right and quietly get the
rest wrong. This one doesn't cut those corners:

- **Matariki**, New Zealand's newest public holiday, correctly present from
  its first observance in **2022** through to **2052** (the last year the
  date is currently gazetted) — and correctly *absent* before 2022.
- **Mondayisation handled properly, per country**: NZ's Waitangi Day/ANZAC
  Day observed-Monday is flagged via the `(observed)` suffix
  `python-holidays` gives it; AU's per-state make-up Mondays (which carry
  **no** suffix and instead *replace* the original weekend date) are
  detected with a country-agnostic diff check instead — see
  [Observed-day detection](#observed-day-detection). `IsBusinessDay`
  accounts for both correctly.
- **Correct fiscal years, per country**: NZ's 1 April – 31 March and AU's
  1 July – 30 June, both labelled by the year they **end** (`FY2026`) —
  not the US/calendar convention. Combined mode computes each row's fiscal
  columns from **that row's own country's** fiscal year.
- **Regional/state public holiday flags** — one `IsHoliday_<CODE>` column
  per NZ subdivision (17) or AU state/territory (8), so "is this a public
  holiday in Auckland vs. Wellington" or "in VIC vs. NSW" is a single
  boolean lookup, not a lookup table you have to build yourself.
- **Relative / time-intelligence columns** (`IsToday`, `IsCalendarYTD`,
  `IsRolling12Months`, offsets, ...) — always computed *live* against the
  query engine's clock in every dynamic format, never frozen into a stale
  static file. See [Relative columns](#relative--time-intelligence-columns)
  below.
- All holiday logic comes from [`python-holidays`](https://github.com/vacanza/holidays)
  (actively maintained, MIT licensed) rather than a hand-rolled and
  inevitably-stale holiday table.

## Download

Just want the data? Grab the ready-made **2015–2050** NZ CSV directly — no
Python required:

**⬇ [`outputs/nz-date-dimension.csv`](outputs/nz-date-dimension.csv)** — 13,149 rows, one per day.

Or generate NZ, AU, or a Combined ANZ table yourself with the quick start below.

## Quick start

Works the same on Windows (PowerShell/cmd) and bash/zsh — run from inside
`generator/`, writing back out to the repo-root `outputs/` folder:

```bash
pip install -r requirements.txt

cd generator
python -m nz_date_dimension.cli --out ../outputs/nz-date-dimension.csv
```

This writes the full 2015–2050 **NZ** date dimension to
[`outputs/nz-date-dimension.csv`](outputs/nz-date-dimension.csv) — the same
ready-made file that's committed to this repo (see [Download](#download)).

Prefer running from the repo root instead? Point `PYTHONPATH` at the
`generator/` package for your shell:

| Shell | Command |
|---|---|
| bash / zsh | `PYTHONPATH=generator python -m nz_date_dimension.cli` |
| PowerShell | `$env:PYTHONPATH="generator"; python -m nz_date_dimension.cli` |
| cmd.exe | `set PYTHONPATH=generator && python -m nz_date_dimension.cli` |

CLI flags:

| Flag | Default | Description |
|---|---|---|
| `--country` | `nz` | Which calendar to generate: `nz`, `au`, or `combined` (unions both under a `Country` column — see [Combined ANZ mode](#combined-anz-mode)). |
| `--start-year` | `2015` | First calendar year included (inclusive). |
| `--end-year` | `2050` | Last calendar year included (inclusive). For `--country nz` (or `combined`), values beyond `2052` emit a warning that Matariki is not gazetted that far out. AU has no such cap. |
| `--out` | per-format, per-country (see [Formats](#formats)) | Output path. Ignored when `--format all` or `--format dbt` (they always write to their fixed default paths since they produce more than one file). |
| `--fiscal-start-month` | the country's own convention (NZ=`4`, AU=`7`) | First month of the fiscal year (1 = January … 12 = December). An explicit value overrides the default for every country in the dataset. Not meaningful to override per-row in `--country combined` — see the note in [Combined ANZ mode](#combined-anz-mode). |
| `--format` | `csv` | One of `csv`, `tsql`, `snowflake`, `databricks`, `powerquery`, `dbt`, `all`. `all` writes every format in one run. `dbt` is **not supported** for `--country combined` (see below). |

Examples:

```bash
# Australia, Snowflake SQL (CREATE TABLE + INSERT + a relative-columns VIEW)
python -m nz_date_dimension.cli --country au --format snowflake --out ../outputs/au-date-dimension.snowflake.sql

# Combined ANZ, CSV -- one table, a Country column, NZ + AU unioned
python -m nz_date_dimension.cli --country combined --format csv --out ../outputs/anz-date-dimension.csv

# Everything at once for NZ, into outputs/ (and outputs/dbt/ for the dbt model + seed)
python -m nz_date_dimension.cli --format all
```

## Countries

| Country | `--country` value | Subdivisions | Fiscal year | Default table name | Default output stem |
|---|---|---|---|---|---|
| New Zealand | `nz` (default) | 17 regions: `AUK, BOP, CAN, CIT, GIS, HKB, MBH, MWT, NSN, NTL, OTA, STL, TAS, TKI, WGN, WKO, WTC` | 1 Apr – 31 Mar | `NZDateDimension` | `nz-date-dimension` |
| Australia | `au` | 8 states/territories: `ACT, NSW, NT, QLD, SA, TAS, VIC, WA` | 1 Jul – 30 Jun | `AUDateDimension` | `au-date-dimension` |
| Combined ANZ | `combined` | Both, country-prefixed (see below) | Per-row, per-country | `ANZDateDimension` | `anz-date-dimension` |

Single-country output keeps bare `IsHoliday_<CODE>` flags (NZ's `IsHoliday_TAS`
is Taranaki, AU's `IsHoliday_TAS` is Tasmania — no collision because
they're never in the same table).

### Observed-day detection

`IsObserved` is computed differently per country because `python-holidays`
represents "Mondayised" days differently for NZ and AU:

- **NZ**: the make-up Monday keeps the original weekend date in the
  calendar too and appends `" (observed)"` to its name (e.g. `"Waitangi
  Day (observed)"`). `IsObserved` = the name contains that suffix.
- **AU**: the make-up Monday carries **no suffix** at all (just
  `"Australia Day"`) and the original weekend date is **removed** from the
  `observed=True` calendar entirely — the NZ suffix check would never fire.
  Instead: a date is observed if it's a holiday under `observed=True` but
  **not** under `observed=False` (i.e. it only exists because of the
  weekend-shift rule).

Both strategies are driven by a per-country config (`countries.py`) and
verified live against the pinned `python-holidays==0.101` — see
`generator/nz_date_dimension/holidays_engine.py`.

AU's national-level calendar (no subdivision) only carries the handful of
truly nation-wide fixed holidays (New Year's, Australia Day's nominal
date, Good Friday, Easter Monday, ANZAC Day, Christmas, Boxing Day) and
**never Mondayises them** — Australia has no single national
weekend-shift law, only state ones. So, mirroring NZ's own national-vs-
regional split (a region's provincial anniversary doesn't flip NZ's main
`IsBusinessDay`), an AU state-only holiday (e.g. WA's Labour Day) does
**not** flip AU's main `IsHoliday`/`IsBusinessDay` either — it only shows
up in that state's own `IsHoliday_<STATE>` flag. Use the per-state flag if
your business calendar needs a specific state's observance.

### Combined ANZ mode

`--country combined` produces **one table** with:

- A `Country` column (`"NZ"` or `"AU"`), positioned right after `DateKey`.
- Fiscal columns (`FiscalYear`, `FiscalQuarter`, ...) computed from
  **that row's own country's** fiscal year (NZ Apr-start, AU Jul-start) —
  not a single global fiscal calendar.
- `IsHoliday`/`HolidayName`/`IsObserved`/`IsBusinessDay` from that row's
  own country's national holidays.
- The **union** of both countries' regional flags, **country-prefixed**
  to avoid NZ Taranaki / AU Tasmania both being `TAS`:
  `IsHoliday_NZ_<code>` (17) and `IsHoliday_AU_<code>` (8). A row's
  non-applicable country's flags are always `false`.
- SQL emitters use a **composite primary key** `(Date, Country)` instead
  of the single-country `(Date)` — `Date` alone isn't unique once NZ and
  AU rows share a table. `DateKey` (`yyyymmdd`) is therefore non-unique
  across countries in Combined mode by design; it is not the Combined PK.

**Known limitation:** the SQL emitters' companion "relative columns" VIEW
(T-SQL/Snowflake/Databricks) computes its live `TodayFiscalYear`/
`TodayFiscalQuarter` reference point from a **single** fiscal_start_month
for the whole view (NZ's, unless `--fiscal-start-month` is given). The
static base table's per-row `FiscalYear`/`FiscalQuarter` are always
correct per-country, and every non-fiscal relative column (`DayOffset`,
`IsCurrentMonth`, `IsToday`, ...) is unaffected — but `FiscalYearOffset`,
`IsCurrentFiscalYear`, `IsFiscalYTD`, and `FiscalQuarterOffset` in that
companion view are only fiscal-calendar-correct for NZ rows, not AU rows,
in Combined mode. A future enhancement could make the view branch per row
via the `Country` column; out of scope for this refactor.

**`dbt` is not supported for `--country combined`** and raises a clear
error rather than silently emitting wrong SQL: the dbt model applies one
`fiscal_start_month` to its whole `dbt_utils.date_spine`, which can't
represent a per-row country-dependent fiscal year either. Generate the NZ
and AU dbt models separately (`--country nz --format dbt` and
`--country au --format dbt`) instead. `--format all --country combined`
skips dbt with a printed note rather than failing the whole run.

## Formats

Every format is emitted from the **same** Python-computed dataset — one
generator, per-format emitters, no per-format drift — guarded by a
cross-format consistency test in `tests/test_cross_format_consistency.py`.
Every emitter derives its columns from the dataset's own country config
(`columns.py`) rather than a hardcoded NZ column list, so CSV, SQL, Power
Query, and dbt all work unchanged for NZ, AU, or Combined.

| Format | Status | Emitter | Notes |
|---|---|---|---|
| CSV | ✅ Available | `emit_csv.py` | Stable columns only + a `GeneratedOn` stamp. The ready-made NZ download above. |
| T-SQL (SQL Server) | ✅ Available | `emit_tsql.py` | `CREATE TABLE` + batched `INSERT`s of the stable rows, plus a `CREATE VIEW` deriving the relative columns from `GETDATE()`. |
| Snowflake SQL | ✅ Available | `emit_snowflake.py` | Same shape as T-SQL, Snowflake-native types/functions (`BOOLEAN`, `CURRENT_DATE()`, `DAYOFWEEKISO`). |
| Databricks SQL | ✅ Available | `emit_databricks.py` | Same shape again, Spark SQL functions (`current_date()`, `dayofweek()`-derived ISO weekday). |
| Power Query (M) | ✅ Available | `emit_powerquery.py` | A single `let...in` query: the stable rows as a `#table` literal, plus the relative columns computed live via `DateTime.LocalNow()` on every refresh — no separate view needed. |
| dbt model | ✅ Available (NZ, AU) | `emit_dbt.py` | `dbt_utils.date_spine` generates the calendar spine; a seed (`<country>_date_dimension_holidays.csv`) carries the holiday/regional-anniversary lookup; relative columns via `current_date()`. Snowflake-flavoured SQL — see the model's own header comment. **Not supported for Combined** — see above. |
| Power BI (`.pbit`/`.pbix`) | 🔜 Fast-follow | — | Not in this repo yet — see [Roadmap](#roadmap). |

### Relative / time-intelligence columns

`DayOffset`, `WeekOffset`, `MonthOffset`, `QuarterOffset`, `YearOffset`,
`FiscalYearOffset`, `FiscalQuarterOffset`, `IsToday`, `IsCurrentWeek`,
`IsCurrentMonth`, `IsCurrentQuarter`, `IsCurrentYear`,
`IsCurrentFiscalYear`, `IsCalendarYTD`, `IsFiscalYTD`, `IsMonthToDate`,
`IsQuarterToDate`, `IsLast7Days`, `IsLast30Days`, `IsLast90Days`,
`IsPriorMonth`, `IsPriorYear`, `IsRolling12Months`.

These are **dynamic** — always "as of today" — so they are **deliberately
not in the static CSV** (a frozen `IsCalendarYTD` would be wrong the next
day). They live in:

- `generator/nz_date_dimension/relative.py` — the reference Python
  implementation (tested against an injectable `today` so results are
  deterministic).
- The **Power Query** output directly (computed via `DateTime.LocalNow()`).
- A companion **`CREATE VIEW`** in each SQL format (derived from
  `CURRENT_DATE`/`GETDATE()`/`current_date()`) — see the Combined-mode
  known limitation above.
- The **dbt model** (derived from `current_date()`, recomputed every run;
  NZ and AU only).

**Timezone caveat:** "today" resolves via the query engine's clock — the
session/warehouse timezone, not necessarily NZ or AU time. For `IsToday` /
`IsCalendarYTD` to align to local midnight, run the dynamic formats in a
same-timezone session/context.

## Columns

Every row is one calendar date (plus, in Combined mode, a country). See
[`docs/column-dictionary.md`](docs/column-dictionary.md) for the full list —
calendar columns, fiscal-year columns, national holiday columns, the
regional/state `IsHoliday_<CODE>` flags, the `Country` column, and the
relative/time-intelligence columns — with type and description for each,
across NZ, AU, and Combined.

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

`requirements-dev.txt` pulls in the runtime dependency (`holidays==0.101`)
plus `pytest`; `requirements.txt` alone (used by the quick start above) is
runtime-only.

## Attribution

Public-holiday and Matariki dates are © New Zealand Government, reused
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Australian
public-holiday dates are sourced via `python-holidays` from the relevant
state/territory legislation (see `holidays.countries.australia` for
references). Holiday computation via
[`python-holidays`](https://github.com/vacanza/holidays) (MIT licence).

## Licences

- **Code**: MIT — see [`LICENSE`](LICENSE).
- **Generated data files**: CC BY 4.0 — see [`DATA-LICENSE`](DATA-LICENSE).

## Roadmap

**Plan A** (core generator + CSV), **Plan B** (relative/time-intelligence
columns, T-SQL/Snowflake/Databricks/Power Query/dbt emitters, and the
cross-format consistency test), and the **AU + Combined ANZ** country
parameterisation are all done — see [Formats](#formats) and
[Countries](#countries).

Still ahead:

- A Power BI template (`.pbit`)/`.pbix` fast-follow with DAX measures
  (gated / email-capture piece).
- A `dbt` Combined model (per-row country-dependent fiscal year in a
  single dbt model) — currently out of scope; generate NZ and AU dbt
  models separately in the meantime.
- Expanding beyond Aotearoa New Zealand and Australia to the wider
  Pacific — the generator's country config (`countries.py`) is built so
  adding a country is "add one `CountryConfig`", not a rewrite.
