"""Geracao de tabelas HTML formatadas."""
import pandas as pd
import numpy as np


def _fmt(val, decimals: int = 1) -> str:
    if pd.isna(val) or val is None:
        return "—"
    try:
        return f"{float(val):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)


def make_summary_table(
    df: pd.DataFrame,
    columns: list[str],
    col_labels: dict[str, str] = None,
    date_col: str = "Data",
    decimals: int = 1,
    n_rows: int = 5,
) -> str:
    """Gera tabela HTML das ultimas n_rows linhas.

    col_labels: dict mapping internal column names to display names.
    """
    if col_labels is None:
        col_labels = {}

    # Remove rows where the main data columns are all NaN
    clean = df.dropna(subset=columns, how="all") if columns else df
    tail = clean.tail(n_rows).copy()

    # Build header
    all_cols = [date_col] + columns
    header_cells = []
    for c in all_cols:
        label = col_labels.get(c, c)
        header_cells.append(f"<th>{label}</th>")

    # Build rows
    rows_html = []
    for _, row in tail.iterrows():
        cells = []
        for c in all_cols:
            val = row.get(c)
            if c == date_col:
                if isinstance(val, pd.Timestamp):
                    cells.append(f"<td>{val.strftime('%d/%m/%Y')}</td>")
                else:
                    cells.append(f"<td>{val}</td>")
            else:
                cells.append(f"<td class='num'>{_fmt(val, decimals)}</td>")
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    return f"""
    <table class="data-table">
        <thead><tr>{"".join(header_cells)}</tr></thead>
        <tbody>{"".join(rows_html)}</tbody>
    </table>
    """


def make_swap_delta_table(
    delta_data: dict,
    title: str,
    subtitle: str = "k DV01",
) -> str:
    """Tabela de deltas Swap Camara: 5 rows x 3 cols (Offshore/Local Ex Banks/Local Banks).

    delta_data: {participant_name: {period_label: value, ...}}
    """
    participants = ["Offshore", "Local Ex Banks", "Local Banks"]
    periods = ["1D Change", "7D Change", "30D Change", "45D Change", "90D Change"]

    header = "<tr><th></th>" + "".join(f"<th>{p}</th>" for p in participants) + "</tr>"

    rows = []
    for period in periods:
        cells = [f"<td class='row-label'>{period}</td>"]
        for p in participants:
            val = delta_data.get(p, {}).get(period, np.nan)
            cells.append(f"<td class='num'>{_fmt(val, 0)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return f"""
    <div class="table-title">{title}</div>
    <div class="table-subtitle">{subtitle}</div>
    <table class="data-table swap-table">
        <thead>{header}</thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """
