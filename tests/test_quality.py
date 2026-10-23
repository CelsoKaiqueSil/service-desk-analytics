from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook
from service_desk_analytics.pipeline import build_report, calculate_kpis, load_tickets

SOURCE = Path(__file__).parents[1] / 'data/tickets.csv'


def save(tmp_path, frame):
    target = tmp_path / 'tickets.csv'
    frame.to_csv(target, index=False)
    return target


def test_identical_rows_removed(tmp_path):
    raw = pd.read_csv(SOURCE)
    frame = load_tickets(save(tmp_path, pd.concat([raw, raw.iloc[:1]])))
    assert len(frame) == 8
    assert frame.attrs['quality']['duplicates_removed'] == 1


def test_conflicting_id_is_not_silently_chosen(tmp_path):
    raw = pd.read_csv(SOURCE)
    changed = raw.iloc[:1].copy()
    changed['owner'] = 'Different synthetic owner'
    with pytest.raises(ValueError, match='Conflicting'):
        load_tickets(save(tmp_path, pd.concat([raw, changed])))


def test_negative_duration_quarantined(tmp_path):
    raw = pd.read_csv(SOURCE)
    raw.loc[0, 'first_response_at'] = '2026-06-01T00:00:00Z'
    frame = load_tickets(save(tmp_path, raw))
    assert frame.attrs['quality']['rejected_rows'] == 1
    assert len(frame.attrs['rejected']) == 1
    assert frame['response_hours'].min() >= 0


def test_missing_sla_is_unknown_not_failed():
    frame = load_tickets(SOURCE)
    assert frame.loc[frame['resolved_at'].isna(), 'sla_met'].isna().all()


def test_end_is_inclusive_and_future_resolution_excluded():
    frame = load_tickets(SOURCE, start='2026-07-01', end='2026-07-01')
    metrics = calculate_kpis(frame)
    assert metrics['opened'] == 2
    assert metrics['resolved'] == 1
    assert metrics['backlog'] == 1


def test_invalid_window_rejected():
    with pytest.raises(ValueError):
        load_tickets(SOURCE, start='2026-07-03', end='2026-07-01')


def test_report_has_actual_charts_and_print_area(tmp_path):
    path = build_report(SOURCE, tmp_path / 'report.xlsx')
    with pd.ExcelFile(path) as book:
        assert 'Qualidade' in book.sheet_names
    book = load_workbook(path)
    try:
        assert len(book['Dashboard']._charts) == 2
        assert book['Dashboard'].page_setup.fitToHeight == 1
    finally:
        book.close()
