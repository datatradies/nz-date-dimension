# Column dictionary

One row per column in the emitted CSV, in output order. Dates are ISO
`YYYY-MM-DD`. Booleans are the literal strings `true` / `false`. Empty
string means "no value" (currently only possible for `HolidayName` on a
non-holiday date).

## Calendar (core)

| Column | Type | Description |
|---|---|---|
| `Date` | date | The calendar date for this row, ISO `YYYY-MM-DD`. |
| `DateKey` | integer | Numeric surrogate key, `YYYYMMDD` (e.g. `20250723`). |
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

## Fiscal (NZ tax year, 1 Apr – 31 Mar)

| Column | Type | Description |
|---|---|---|
| `FiscalYear` | integer | NZ fiscal year, labelled by the year it **ends** in (FY2026 = 1 Apr 2025 – 31 Mar 2026). |
| `FiscalYearLabel` | string | Fiscal year label, e.g. `FY2026`. |
| `FiscalQuarter` | integer | Fiscal quarter, `1`–`4` (Q1 starts on `fiscal_start_month`). |
| `FiscalMonth` | integer | Month number within the fiscal year, `1`–`12` (month 1 = `fiscal_start_month`). |
| `FiscalDayOfYear` | integer | Day number within the fiscal year, `1`–`366`. |
| `FiscalStartOfYear` | date | First day of this date's fiscal year. |
| `FiscalEndOfYear` | date | Last day of this date's fiscal year. |

## National holidays

| Column | Type | Description |
|---|---|---|
| `IsHoliday` | boolean | `true` if this date is a New Zealand national public holiday (including Mondayised observed days). |
| `HolidayName` | string | Holiday name verbatim from `python-holidays` (empty if not a holiday). **Not a stable filter key across years or library versions** — use `IsHoliday` / `IsObserved`, not name matching. |
| `IsObserved` | boolean | `true` if this date is a Mondayised "observed" day (python-holidays appends `(observed)` to `HolidayName`). |
| `IsBusinessDay` | boolean | `true` unless this date is a weekend, a national public holiday, or a Mondayised observed day. |

## Regional (provincial anniversary flags)

One `IsHoliday_<CODE>` boolean column per NZ subdivision (17 total): `AUK`,
`BOP`, `CAN`, `CIT`, `GIS`, `HKB`, `MBH`, `MWT`, `NSN`, `NTL`, `OTA`, `STL`,
`TAS`, `TKI`, `WGN`, `WKO`, `WTC`.

| Column | Type | Description |
|---|---|---|
| `IsHoliday_<CODE>` | boolean | `true` if this date is a public holiday in that subdivision — i.e. a national holiday **or** that region's provincial anniversary day. |

## Metadata

| Column | Type | Description |
|---|---|---|
| `GeneratedOn` | date | The date this CSV was generated (run date), ISO `YYYY-MM-DD`. Appended as the trailing column by the CSV emitter; not part of `STABLE_COLUMNS`. |
