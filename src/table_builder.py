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
    from data_processor import SWAP_DELTA_SESSIONS, swap_delta_label

    periods = [swap_delta_label(n) for n in SWAP_DELTA_SESSIONS]

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
    """Tabela das duas pernas do fluxo AFP, em compra-de-USD, mais net e % USDCLP.

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
    <div class="table-title">Fluxo AFP por dia (mm USD, + compra de USD)</div>
    {rodape}
    <table class="data-table">
        <thead>{header}</thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


# Verde = compra de USD, vermelho = venda. Nao e juizo de bom/ruim: e a mesma
# convencao que as etiquetas de sinal dos graficos da aba ja usam (_usd_side_labels),
# entao a tabela e o grafico se leem com o mesmo codigo de cor.
_HEAT_COMPRA = (0, 176, 80)     # JGP_VERDE
_HEAT_VENDA = (230, 57, 70)     # JGP_VERMELHO
# Teto de alpha baixo de proposito: a tinta serve para varrer a coluna com o
# olho, e o numero tem de continuar legivel por cima dela nos dois modos.
_HEAT_ALPHA_MAX = 0.42


def _heat_style(val, escala: float) -> str:
    """Fundo da celula proporcional a |val| dentro da coluna, divergente no sinal.

    `escala` e o |valor| de referencia da coluna. Devolve string vazia quando nao
    ha o que tingir, para a celula cair na regra CSS normal.
    """
    if val is None or pd.isna(val) or not escala or escala <= 0:
        return ""
    intensidade = min(abs(float(val)) / escala, 1.0)
    if intensidade < 0.02:
        return ""
    r, g, b = _HEAT_COMPRA if float(val) > 0 else _HEAT_VENDA
    return f" style='background:rgba({r},{g},{b},{intensidade * _HEAT_ALPHA_MAX:.3f})'"


def make_sector_flow_table(
    tab: pd.DataFrame, sessoes: int, inicio, fim,
) -> str:
    """Tabela de um horizonte (em pregoes): setor x NDF, spot, net e nivel do saldo, em compra-de-USD.

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
    rotulo = "1 PREGÃO" if sessoes == 1 else f"{sessoes} PREGÕES"

    # Escala da tinta por coluna, tirada SO das folhas: um agregado e a soma
    # delas, entao entraria como o maximo e achataria todas as folhas em quase
    # branco. Por isso os agregados tambem nao recebem tinta — ja se destacam
    # pela faixa cinza e pelo negrito, e a faixa e o que a tinta apagaria.
    flows = ("ndf", "spot", "net")
    folhas = tab[~tab.index.isin(SECTOR_AGGREGATES)]
    escalas = {
        c: (folhas[c].abs().max() if c in folhas.columns else None) for c in flows
    }

    linhas = []
    for setor, row in tab.iterrows():
        agg = setor in SECTOR_AGGREGATES
        nome = "TOTAL (monto vigente neto)" if setor == SECTOR_GRAND_TOTAL else setor
        cls = " class='row-agg'" if agg else ""
        recuo = "" if agg else "style='padding-left:22px'"
        cells = [f"<td {recuo}>{nome}</td>"]
        for c in ("ndf", "spot", "net", "ndf_level"):
            # Saldo NDF fica sem tinta: e estoque, nao movimento da janela, e na
            # mesma escala de cor competiria com as tres pernas de fluxo, que sao
            # o que a tabela existe para mostrar.
            tinta = "" if (agg or c not in flows) else _heat_style(row.get(c), escalas[c])
            cells.append(f"<td class='num'{tinta}>{_fmt(row.get(c), 0)}</td>")
        linhas.append(f"<tr{cls}>" + "".join(cells) + "</tr>")

    return f"""
    <div class="table-title">{rotulo} &mdash; NDF + spot por setor (mm USD, + compra de USD)</div>
    <div class="table-subtitle">Janela {janela} &middot; as seis folhas somam Residentes no bancos; este mais No residentes soma o total
    <br>Fundo <span class="heat-key heat-key-compra">verde</span> = compra de USD, <span class="heat-key heat-key-venda">vermelho</span> = venda; intensidade proporcional ao maior |valor| entre as folhas da coluna</div>
    <table class="data-table">
        <thead><tr>
            <th>Setor</th><th>&Delta; NDF</th><th>Spot</th><th>Net</th><th>Saldo NDF</th>
        </tr></thead>
        <tbody>{"".join(linhas)}</tbody>
    </table>
    """
