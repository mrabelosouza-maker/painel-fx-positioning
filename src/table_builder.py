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


def make_afp_legs_table(
    afp_df: pd.DataFrame,
    last_dates: dict = None,
    n_rows: int = 5,
) -> str:
    """Tabela das duas pernas do fluxo AFP, em compra-de-CLP, mais net e % USDCLP.

    O rodape traz a ultima data de cada fonte: elas tem defasagem diferente e o
    leitor precisa ver isso antes de comparar as pernas.
    """
    if afp_df.empty:
        return "<p>—</p>"

    df = afp_df.copy()
    df["net"] = df[["ndf_1d", "spot_bcch"]].sum(axis=1, min_count=1)
    df["pct_usdclp"] = 100 * (np.log(df["USDCLP"]) - np.log(df["USDCLP"].shift(1)))

    cols = [
        ("ndf_1d", "NDF 1D"),
        ("spot_bcch", "Spot BCCh"),
        ("net", "Net (NDF+spot)"),
        ("pct_usdclp", "% USDCLP"),
    ]

    tail = df.dropna(subset=[c for c, _ in cols], how="all").tail(n_rows)

    header = "<tr><th>Data</th>" + "".join(f"<th>{lab}</th>" for _, lab in cols) + "</tr>"
    rows = []
    for _, row in tail.iterrows():
        cells = [f"<td>{row['Data'].strftime('%d/%m/%Y')}</td>"]
        for c, _ in cols:
            cells.append(f"<td class='num'>{_fmt(row.get(c), 1)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    rodape = ""
    if last_dates:
        partes = " · ".join(
            f"{k}: {v.strftime('%d/%m')}" if v is not None else f"{k}: —"
            for k, v in last_dates.items()
        )
        rodape = f"<div class='table-subtitle'>Último dado — {partes}</div>"

    return f"""
    <div class="table-title">Fluxo AFP por dia (mm USD, + compra de CLP)</div>
    {rodape}
    <table class="data-table">
        <thead>{header}</thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def make_sector_flow_table(
    tab: pd.DataFrame, dias: int, inicio, fim,
) -> str:
    """Tabela de um horizonte: setor x NDF, spot, net e nivel do saldo, em compra-de-USD.

    As folhas vao indentadas e os agregados em negrito com risco em cima, para a
    conta ficar visivel na propria tabela: as seis folhas somam Residentes no
    bancos, e este mais No residentes soma o total.
    """
    if tab.empty:
        return "<p>—</p>"

    from config import SECTOR_AGGREGATES, SECTOR_GRAND_TOTAL

    janela = (
        f"{pd.Timestamp(inicio).strftime('%d/%m')} a "
        f"{pd.Timestamp(fim).strftime('%d/%m/%Y')}"
    )
    rotulo = {1: "1 DIA", 7: "7 DIAS", 28: "28 DIAS"}.get(dias, f"{dias} DIAS")

    linhas = []
    for setor, row in tab.iterrows():
        agg = setor in SECTOR_AGGREGATES
        nome = "TOTAL (monto vigente neto)" if setor == SECTOR_GRAND_TOTAL else setor
        cls = " class='row-agg'" if agg else ""
        recuo = "" if agg else "style='padding-left:22px'"
        cells = [f"<td {recuo}>{nome}</td>"]
        for c in ("ndf", "spot", "net", "ndf_level"):
            cells.append(f"<td class='num'>{_fmt(row.get(c), 0)}</td>")
        linhas.append(f"<tr{cls}>" + "".join(cells) + "</tr>")

    return f"""
    <div class="table-title">{rotulo} &mdash; NDF + spot por setor (mm USD, + compra de USD)</div>
    <div class="table-subtitle">Janela {janela} &middot; as seis folhas somam Residentes no bancos; este mais No residentes soma o total</div>
    <table class="data-table">
        <thead><tr>
            <th>Setor</th><th>&Delta; NDF</th><th>Spot</th><th>Net</th><th>Saldo NDF</th>
        </tr></thead>
        <tbody>{"".join(linhas)}</tbody>
    </table>
    """
