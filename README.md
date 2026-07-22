# NZ Date Dimension

A parameterised Python generator that produces a correct, tested New Zealand
date dimension (calendar table) and emits it to CSV — the kind of "done
properly" date dimension every NZ data warehouse eventually needs, built
once and open-sourced instead of rebuilt badly by every team.

## Why this is "done properly"

Most home-grown NZ date dimensions get the easy 80% right and quietly get
the rest wrong. This one doesn't cut those corners:

- **Matariki**, New Zealand's newest public holiday, correctly present from
  its first observance in **2022** through to **2052** (the last year the
  date is currently gazetted) — and correctly *absent* before 2022.
- **Mondayisation** handled properly: when Waitangi Day or ANZAC Day falls
  on a weekend, the Monday "observed" holiday is flagged via `IsObserved`,
  and `IsBusinessDay` accounts for it.
- **NZ fiscal year**, 1 April – 31 March, labelled by the year it **ends**
  (`FY2026` = 1 Apr 2025 – 31 Mar 2026) — not the US/calendar convention.
- **17 regional public holiday flags** — one `IsHoliday_<CODE>` column per
  NZ subdivision, so "is this a public holiday in Auckland vs. Wellington"
  is a single boolean lookup, not a lookup table you have to build yourself.
- All holiday logic comes from [`python-holidays`](https://github.com/vacanza/holidays)
  (actively maintained, MIT licensed) rather than a hand-rolled and
  inevitably-stale holiday table.

## Download

Just want the data? Grab the ready-made **2015–2050** CSV directly — no Python required:

**⬇ [`outputs/nz-date-dimension.csv`](outputs/nz-date-dimension.csv)** — 13,149 rows, one per day.

Or generate a custom date range yourself with the quick start below.

## Quick start

Works the same on Windows (PowerShell/cmd) and bash/zsh — run from inside
`generator/`, writing back out to the repo-root `outputs/` folder:

```bash
pip install -r requirements.txt

cd generator
python -m nz_date_dimension.cli --out ../outputs/nz-date-dimension.csv
```

This writes the full 2015–2050 date dimension to
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
| `--start-year` | `2015` | First calendar year included (inclusive). |
| `--end-year` | `2050` | Last calendar year included (inclusive). Values beyond `2052` emit a warning that Matariki is not gazetted that far out. |
| `--out` | `outputs/nz-date-dimension.csv` | Output CSV path. |
| `--fiscal-start-month` | `4` | First month of the NZ fiscal year (1 = January … 12 = December). |

## Columns

Every row is one calendar date. See
[`docs/column-dictionary.md`](docs/column-dictionary.md) for the full list —
calendar columns, fiscal-year columns, national holiday columns, and the 17
per-region `IsHoliday_<CODE>` flags — with type and description for each.

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
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Holiday
computation via [`python-holidays`](https://github.com/vacanza/holidays)
(MIT licence).

## Licences

- **Code**: MIT — see [`LICENSE`](LICENSE).
- **Generated data files**: CC BY 4.0 — see [`DATA-LICENSE`](DATA-LICENSE).

## Roadmap

This repo is **Plan A**: the core generator and CSV emitter. Deliberately
deferred to a later **Plan B**:

- Relative / time-intelligence columns (e.g. `IsToday`, `DaysFromToday`,
  rolling period flags).
- Additional emitters — SQL (DDL + `INSERT`s), Power Query (M), dbt seed —
  plus a cross-format consistency test so every emitter agrees with the CSV.
- A Power BI template (`.pbit`)/`.pbix` fast-follow.
- Expanding beyond Aotearoa New Zealand to the wider Pacific.
