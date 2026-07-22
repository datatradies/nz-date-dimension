import re
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.relative import RELATIVE_COLUMNS
from nz_date_dimension.emit_powerquery import emit_powerquery

def test_emit_powerquery_has_let_in_and_source_table():
    rows = build_dataset(2025, 2025)  # 365 rows
    m = emit_powerquery(rows, fiscal_start_month=4)
    assert m.strip().startswith("let")
    assert "#table(" in m
    assert "DateTime.LocalNow()" in m

def test_emit_powerquery_includes_every_stable_and_relative_column():
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows)
    for col in STABLE_COLUMNS:
        assert f'"{col}"' in m, f"missing stable column header {col}"
    for col in RELATIVE_COLUMNS:
        assert f'"{col}"' in m, f"missing relative column {col}"
        assert f'Table.AddColumn(' in m

def test_emit_powerquery_row_count_matches_dataset():
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows)
    date_keys = set(re.findall(r"\b\d{8}\b", m))
    assert len(date_keys) == 365

def test_emit_powerquery_last_step_is_the_final_relative_column():
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows)
    last_line = m.strip().splitlines()[-1].strip()
    assert last_line == f"Add{RELATIVE_COLUMNS[-1]}"

def test_today_fiscal_month_uses_positive_modulo_guard():
    """Regression for review finding I2: M's Number.Mod follows the
    dividend's sign (Number.Mod(x, n) = x - n * IntegerDivide(x, n), which
    truncates toward zero), so a bare
    Number.Mod(Date.Month(Today) - FiscalStartMonth, 12) goes NEGATIVE for
    Jan/Feb/Mar under the default April fiscal start -- e.g. January:
    Number.Mod(-3, 12) = -3 -> TodayFiscalMonth = -2 ->
    TodayFiscalQuarter = IntegerDivide(-3, 3) + 1 = 0 (should be 4). That
    corrupts FiscalQuarterOffset by 4 for every row during a refresh in
    those months. Must use the positive-modulo idiom
    Number.Mod(Number.Mod(x, n) + n, n).
    """
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows, fiscal_start_month=4)
    assert (
        "TodayFiscalMonth = Number.Mod(Number.Mod(Date.Month(Today) - "
        "FiscalStartMonth, 12) + 12, 12) + 1"
    ) in m
    # guard against a naive fix that forgot to remove the old bare call --
    # anchored on "= Number.Mod(Date...." (immediately after the binding
    # name) so it doesn't false-match the nested Number.Mod(...) + 12 inside
    # the corrected positive-modulo expression above.
    assert "TodayFiscalMonth = Number.Mod(Date.Month(Today) - FiscalStartMonth, 12) + 1" not in m
