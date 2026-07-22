# Column dictionary

The generator supports three outputs — `--country nz` (default), `--country
au`, and `--country combined` (unions both) — via the same code, columns
derived dynamically from each dataset's country config
(`generator/nz_date_dimension/columns.py`, `countries.py`). This dictionary
covers all three; where a column differs between them, that's called out
explicitly.

The **Calendar**, **Fiscal**, **National holidays**, **Regional**,
**Country** (Combined only), and **Metadata** sections below are the
static/stable columns, one row per column in the emitted CSV, in output
order. Dates are ISO `YYYY-MM-DD`. Booleans are the literal strings `true`
/ `false`. Empty string means "no value" (currently only possible for
`HolidayName` on a non-holiday date).

The **Relative / time-intelligence columns** section is different: those
columns are dynamic (computed "as of today") and are **not** part of the
static CSV — see that section for where they actually live.

## Calendar (core)

Identical for every country and Combined — computed purely from the date
itself.

| Column | Type | Description |
|---|---|---|
| `Date` | date | The calendar date for this row, ISO `YYYY-MM-DD`. |
| `DateKey` | integer | Numeric surrogate key, `YYYYMMDD` (e.g. `20250723`). In Combined mode, `DateKey` is **not unique** on its own (an NZ row and an AU row share the same `DateKey` on the same calendar date) — the Combined primary key is the composite `(Date, Country)`, not `DateKey`. |
| `Country` | string | **Combined mode only** — `"NZ"` or `"AU"`. Positioned right after `DateKey`. Absent entirely from single-country NZ/AU output. |
| `Year` | integer | Calendar year, e.g. `2025`. |
| `Quarter` | integer | Calendar quarter, `1`–`4`. |
| `QuarterName` | string | Calendar quarter label, e.g. `Q3`. |
| `Month` | integer | Calendar month, `1`–`12`. |
| `MonthName` | string | Full month name, e.g. `July`. |
| `MonthShort` | string | Three-letter month abbreviation, e.g. `Jul`. |
| `Day` | integer | Day of month, `1`–`31`. |
| `DayOfYear` | integer | Day of calendar year, `1`–`366`. |
| `DayOfWeek` | integer | ISO day of week, `1` (Monday) – `7` (Sunday). |
| `DayName` | string | Full weekday name, e.g. `Wednesday`. |
| `DayShort` | string | Three-letter weekday abbreviation, e.g. `Wed`. |
| `ISOWeek` | integer | ISO-8601 week number, `1`–`53`. |
| `ISOWeekYear` | integer | ISO-8601 week-numbering year (can differ from `Year` near year boundaries). |
| `IsWeekend` | boolean | `true` if Saturday or Sunday. |
| `IsWeekday` | boolean | `true` if Monday–Friday (note: independent of public holidays). |
| `StartOfMonth` | date | First day of this date's month. |
| `EndOfMonth` | date | Last day of this date's month. |
| `StartOfQuarter` | date | First day of this date's calendar quarter. |
| `EndOfQuarter` | date | Last day of this date's calendar quarter. |
| `StartOfYear` | date | 1 January of this date's calendar year. |
| `EndOfYear` | date | 31 December of this date's calendar year. |

## Fiscal (per-country tax year)

- **NZ**: 1 Apr – 31 Mar (`--fiscal-start-month` default `4`).
- **AU**: 1 Jul – 30 Jun (`--fiscal-start-month` default `7`).
- **Combined**: each row's fiscal columns are computed from **that row's
  own country's** fiscal year, not a single shared calendar — an NZ row on
  1 Aug 2025 and an AU row on the same date can (and do) show different
  `FiscalYear`/`FiscalStartOfYear` values.

Both conventions label the fiscal year by the year it **ends** in
(`FY2026`), not the US/calendar convention.

| Column | Type | Description |
|---|---|---|
| `FiscalYear` | integer | Fiscal year, labelled by the year it **ends** in (FY2026 = 1 Apr 2025 – 31 Mar 2026 for NZ, or 1 Jul 2025 – 30 Jun 2026 for AU). |
| `FiscalYearLabel` | string | Fiscal year label, e.g. `FY2026`. |
| `FiscalQuarter` | integer | Fiscal quarter, `1`–`4` (Q1 starts on `fiscal_start_month`). |
| `FiscalMonth` | integer | Month number within the fiscal year, `1`–`12` (month 1 = `fiscal_start_month`). |
| `FiscalDayOfYear` | integer | Day number within the fiscal year, `1`–`366`. |
| `FiscalStartOfYear` | date | First day of this date's fiscal year. |
| `FiscalEndOfYear` | date | Last day of this date's fiscal year. |

## National holidays

`IsHoliday`/`HolidayName`/`IsObserved`/`IsBusinessDay` reflect each
country's **national-only** calendar (the holidays observed everywhere in
that country) — a region/state-only day (e.g. NZ's Auckland Anniversary,
AU's WA Labour Day) does **not** flip these; it only shows up in that
region/state's own `IsHoliday_<CODE>` flag (see Regional, below). In
Combined mode, these four columns reflect **that row's own country's**
national calendar.

`IsObserved` detection is country-specific (see the README's [Observed-day
detection](../README.md#observed-day-detection) section for why):

- **NZ**: `true` if `python-holidays` appended `" (observed)"` to the
  name (NZ keeps both the original weekend date and the shifted Monday in
  its calendar, differentiated by that suffix).
- **AU**: `true` if the date is a holiday under `observed=True` but
  **not** under `observed=False` — AU's make-up Monday carries no suffix
  and instead *replaces* the original weekend date entirely, so the NZ
  suffix check would never fire for it.

| Column | Type | Description |
|---|---|---|
| `IsHoliday` | boolean | `true` if this date is a national public holiday for this row's country (including Mondayised/observed days). |
| `HolidayName` | string | Holiday name verbatim from `python-holidays` (empty if not a holiday). **Not a stable filter key across years or library versions** — use `IsHoliday` / `IsObserved`, not name matching. |
| `IsObserved` | boolean | `true` if this date is a Mondayised "observed" day — see the country-specific detection above. |
| `IsBusinessDay` | boolean | `true` unless this date is a weekend or this row's country's national public holiday (region/state-only holidays don't affect this — see their own `IsHoliday_<CODE>` flag). |

## Regional (provincial/state holiday flags)

One `IsHoliday_<CODE>` boolean column per subdivision — `true` if that
date is a public holiday in that subdivision (its country's national
holidays **or** that specific region/state's own day).

**Single-country output (NZ or AU) uses bare `IsHoliday_<CODE>` columns.**
**Combined output country-prefixes every flag** (`IsHoliday_NZ_<CODE>` /
`IsHoliday_AU_<CODE>`) to avoid a collision: NZ's Taranaki and AU's
Tasmania both use the code `TAS`, so they can only safely share a table
once prefixed. A row's non-applicable country's flags are always `false`
in Combined mode (an NZ row's `IsHoliday_AU_*` columns, and vice versa).

**NZ — 17 subdivisions:** `AUK`, `BOP`, `CAN`, `CIT`, `GIS`, `HKB`, `MBH`,
`MWT`, `NSN`, `NTL`, `OTA`, `STL`, `TAS`, `TKI`, `WGN`, `WKO`, `WTC`.

**AU — 8 states/territories:** `ACT`, `NSW`, `NT`, `QLD`, `SA`, `TAS`,
`VIC`, `WA`.

| Column | Type | Description |
|---|---|---|
| `IsHoliday_<CODE>` (NZ or AU) | boolean | `true` if this date is a public holiday in that subdivision — a national holiday **or** that region/state's own day. |
| `IsHoliday_NZ_<CODE>` (Combined only) | boolean | Same, for NZ's 17 regions. `false` on every AU row. |
| `IsHoliday_AU_<CODE>` (Combined only) | boolean | Same, for AU's 8 states/territories. `false` on every NZ row. |

## Relative / time-intelligence columns (DYNAMIC — not in the static CSV)

**These columns are always computed "as of today" and are deliberately
absent from the static CSV** — a frozen `IsCalendarYTD` in a CSV would be
wrong the very next day (spec §4.5, §7). They exist only in the *dynamic*
formats, where "today" is resolved live by the query engine's clock each
time the query/model runs:

| Format | Where | "Today" source |
|---|---|---|
| Power Query (M) | Directly in the emitted query | `DateTime.LocalNow()` |
| T-SQL | Companion `CREATE VIEW` (not the base table) | `GETDATE()` |
| Snowflake SQL | Companion `CREATE VIEW` (not the base table) | `CURRENT_DATE()` |
| Databricks SQL | Companion `CREATE VIEW` (not the base table) | `current_date()` |
| dbt model (NZ, AU only — not Combined) | The model itself (there is no static dbt seed for these) | `current_date()` |
| Python generator | `nz_date_dimension.relative.relative_columns(d, today, ...)` | an injected `today` parameter (deterministic for tests) |

**Timezone caveat:** "today" resolves in the query engine's/session's
timezone, not necessarily NZ or AU time — for `IsToday` / `IsCalendarYTD`
to align to local midnight, run the dynamic formats in a matching-timezone
session.

**Combined-mode fiscal caveat:** the SQL companion VIEW's live
`TodayFiscalYear`/`TodayFiscalQuarter` reference point uses a single
`fiscal_start_month` for the whole view (NZ's, unless overridden via
`--fiscal-start-month`) — so `FiscalYearOffset`, `IsCurrentFiscalYear`,
`IsFiscalYTD`, and `FiscalQuarterOffset` in that view are fiscal-calendar-
correct for NZ rows but not AU rows. Every other relative column
(`DayOffset`, `IsCurrentMonth`, `IsToday`, ...) is unaffected. See the
README's [Combined ANZ mode](../README.md#combined-anz-mode) section.

| Column | Type | Description |
|---|---|---|
| `DayOffset` | integer | Days from today to this date (`0` = today, negative = past, positive = future). |
| `WeekOffset` | integer | Whole ISO weeks (Monday-start) from today's week to this date's week. |
| `MonthOffset` | integer | Whole calendar months from today's month to this date's month. |
| `QuarterOffset` | integer | Whole calendar quarters from today's quarter to this date's quarter. |
| `YearOffset` | integer | Whole calendar years from today's year to this date's year. |
| `FiscalYearOffset` | integer | Whole fiscal years from today's fiscal year to this date's fiscal year. |
| `FiscalQuarterOffset` | integer | Whole fiscal quarters from today's fiscal quarter to this date's fiscal quarter. |
| `IsToday` | boolean | `true` if this date is today. |
| `IsCurrentWeek` | boolean | `true` if this date falls in today's ISO week (Monday–Sunday). |
| `IsCurrentMonth` | boolean | `true` if this date falls in today's calendar month. |
| `IsCurrentQuarter` | boolean | `true` if this date falls in today's calendar quarter. |
| `IsCurrentYear` | boolean | `true` if this date falls in today's calendar year. |
| `IsCurrentFiscalYear` | boolean | `true` if this date falls in today's fiscal year. |
| `IsCalendarYTD` | boolean | `true` if this date is in today's calendar year **and** on or before today. |
| `IsFiscalYTD` | boolean | `true` if this date is in today's fiscal year **and** on or before today. |
| `IsMonthToDate` | boolean | `true` if this date is in today's calendar month **and** on or before today. |
| `IsQuarterToDate` | boolean | `true` if this date is in today's calendar quarter **and** on or before today. |
| `IsLast7Days` | boolean | `true` if this date is within the 7-day window ending today, inclusive (today − 6 days .. today). |
| `IsLast30Days` | boolean | `true` if this date is within the 30-day window ending today, inclusive. |
| `IsLast90Days` | boolean | `true` if this date is within the 90-day window ending today, inclusive. |
| `IsPriorMonth` | boolean | `true` for every date in the calendar month immediately before today's month (the whole month, not "to date"). |
| `IsPriorYear` | boolean | `true` for every date in the calendar year immediately before today's year (the whole year, not "to date"). |
| `IsRolling12Months` | boolean | `true` if this date falls in today's (possibly partial) month or one of the 11 preceding full calendar months, and is on or before today. |

## Metadata

| Column | Type | Description |
|---|---|---|
| `GeneratedOn` | date | The date this CSV was generated (run date), ISO `YYYY-MM-DD`. Appended as the trailing column by the CSV emitter; not part of the stable columns list. |
