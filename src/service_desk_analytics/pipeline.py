"""Build Service Desk KPIs and an executive Excel workbook."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DATE_COLUMNS = [
    "opened_at",
    "first_response_at",
    "resolved_at",
    "closed_at",
    "sla_due_at",
]
REQUIRED_COLUMNS = {
    "ticket_id",
    "opened_at",
    "first_response_at",
    "resolved_at",
    "closed_at",
    "sla_due_at",
    "category",
    "urgency",
    "owner",
    "status",
}


def load_tickets(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"ticket_id": "string"})
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    frame = frame.copy()
    for column in DATE_COLUMNS:
        frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True)
    frame["response_hours"] = (
        frame["first_response_at"] - frame["opened_at"]
    ).dt.total_seconds() / 3600
    frame["solution_hours"] = (
        frame["resolved_at"] - frame["opened_at"]
    ).dt.total_seconds() / 3600
    frame["sla_met"] = (
        frame["resolved_at"].notna()
        & frame["sla_due_at"].notna()
        & frame["resolved_at"].le(frame["sla_due_at"])
    )
    return frame


def _distribution(series: pd.Series, prefix: str) -> dict[str, float]:
    values = series.dropna()
    if values.empty:
        return {
            f"{prefix}_mean_hours": float("nan"),
            f"{prefix}_median_hours": float("nan"),
            f"{prefix}_p90_hours": float("nan"),
        }
    return {
        f"{prefix}_mean_hours": float(values.mean()),
        f"{prefix}_median_hours": float(values.median()),
        f"{prefix}_p90_hours": float(values.quantile(0.90)),
    }


def calculate_kpis(frame: pd.DataFrame) -> dict[str, float | int]:
    resolved = frame["resolved_at"].notna()
    closed = frame["closed_at"].notna()
    backlog = frame["status"].str.casefold().isin({"aberto", "em andamento"})
    eligible_sla = resolved & frame["sla_due_at"].notna()
    sla_rate = float(frame.loc[eligible_sla, "sla_met"].mean() * 100) if eligible_sla.any() else float("nan")

    metrics: dict[str, float | int] = {
        "opened": int(len(frame)),
        "resolved": int(resolved.sum()),
        "closed": int(closed.sum()),
        "backlog": int(backlog.sum()),
        "sla_met_percent": sla_rate,
    }
    metrics.update(_distribution(frame["response_hours"], "response"))
    metrics.update(_distribution(frame["solution_hours"], "solution"))
    return metrics


def _segment(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        frame.groupby(column, dropna=False)
        .agg(
            tickets=("ticket_id", "size"),
            resolved=("resolved_at", lambda values: int(values.notna().sum())),
            response_median_hours=("response_hours", "median"),
            solution_p90_hours=("solution_hours", lambda values: values.dropna().quantile(0.90)),
        )
        .reset_index()
        .sort_values("tickets", ascending=False)
    )


def _excel_safe(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy whose datetime columns are compatible with Excel."""
    result = frame.copy()
    for column in result.columns:
        if isinstance(result[column].dtype, pd.DatetimeTZDtype):
            result[column] = result[column].dt.tz_convert("UTC").dt.tz_localize(None)
    return result


def build_report(input_path: str | Path, output_path: str | Path) -> Path:
    frame = load_tickets(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    dashboard = pd.DataFrame(
        [{"indicator": key, "value": value} for key, value in calculate_kpis(frame).items()]
    )
    methodology = pd.DataFrame(
        [
            {"indicator": "backlog", "definition": "Tickets com status Aberto ou Em andamento."},
            {"indicator": "response_hours", "definition": "Primeira resposta menos abertura, em horas."},
            {"indicator": "solution_hours", "definition": "Resolução menos abertura, em horas."},
            {"indicator": "sla_met", "definition": "Resolvido até o prazo, somente quando ambas as datas existem."},
            {"indicator": "p90", "definition": "Valor abaixo do qual ficam 90% dos tempos observados."},
        ]
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dashboard.to_excel(writer, sheet_name="Dashboard", index=False)
        _excel_safe(frame).to_excel(writer, sheet_name="Tickets", index=False)
        _segment(frame, "category").to_excel(writer, sheet_name="Categorias", index=False)
        _segment(frame, "owner").to_excel(writer, sheet_name="Responsáveis", index=False)
        methodology.to_excel(writer, sheet_name="Metodologia", index=False)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/tickets.csv")
    parser.add_argument("--output", default="output/service_desk.xlsx")
    args = parser.parse_args()
    print(build_report(args.input, args.output))


if __name__ == "__main__":
    main()
