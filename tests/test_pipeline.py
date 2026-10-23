from pathlib import Path

import pandas as pd

from service_desk_analytics.pipeline import build_report, calculate_kpis, load_tickets


ROOT = Path(__file__).resolve().parents[1]


def test_kpis_keep_statuses_distinct() -> None:
    frame = load_tickets(ROOT / "data" / "tickets.csv")
    metrics = calculate_kpis(frame)
    assert metrics["opened"] == 8
    assert metrics["resolved"] == 6
    assert metrics["closed"] == 4
    assert metrics["backlog"] == 2


def test_distribution_includes_median_and_p90() -> None:
    metrics = calculate_kpis(load_tickets(ROOT / "data" / "tickets.csv"))
    assert metrics["response_median_hours"] > 0
    assert metrics["response_p90_hours"] >= metrics["response_median_hours"]
    assert metrics["solution_p90_hours"] >= metrics["solution_median_hours"]


def test_report_contains_methodology(tmp_path: Path) -> None:
    output = build_report(ROOT / "data" / "tickets.csv", tmp_path / "service_desk.xlsx")
    assert set(pd.ExcelFile(output).sheet_names) == {
        "Dashboard",
        "Tickets",
        "Categorias",
        "Responsáveis",
        "Metodologia",
        "Qualidade",
    }
