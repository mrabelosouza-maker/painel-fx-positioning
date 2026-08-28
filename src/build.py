"""Orquestrador principal: busca dados, processa, gera HTML estatico."""
import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

# Adiciona src/ ao path para imports relativos
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from config import SECTOR_WINDOWS, OFFSHORE_ADJ_CUTOVER
from data_processor import (
    build_fx_dados, compute_deltas, build_swap_data, build_colombia_data,
    build_offshore_adjusted, build_weekly_legs, build_offshore_corr,
    build_net_comparison,
    build_all_sectors_flow, build_sector_window_table, build_sector_weekly,
    build_afp_spot_flow, build_afp_5d_legs, build_afp_weekly_legs,
    build_afp_rolling_legs, build_afp_levels,
)
from chart_builder import (
    make_line_chart,
    make_bar_chart,
    make_dual_axis_chart,
    make_dual_series_chart,
    make_swap_line_chart,
    make_swap_delta_bars,
    make_colombia_line_chart,
    make_weekly_legs_bars,
    make_net_comparison_chart,
    make_sector_weekly_stacked,
    make_offshore_corr_chart,
    AFP_LEG_COLORS,
    make_afp_5d_bars,
    make_afp_daily_bars,
    make_afp_level_line,
    make_afp_levels_chart,
)
from table_builder import (
    make_summary_table, make_swap_delta_table, make_afp_legs_table,
    make_sector_flow_table,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "docs"


def build_fx_section(dados):
    """Gera charts e tables para as 4 secoes FX padrao + dual-axis."""
    ctx = {}

    fx_labels = {
        "delta_1d": "Delta 1D",
        "delta_7d": "Delta 7D",
        "delta_28d": "Delta 28D",
        "pct_usdclp": "% USDCLP",
    }

    # Helper: adicionar % USDCLP a qualquer df
    def _add_pct_usdclp(df):
        df["pct_usdclp"] = 100 * (np.log(df["USDCLP"]) - np.log(df["USDCLP"].shift(1)))
        return df

    # ── FUNDOS DE PENSÃO ──
    col = "Fondos de pensiones"
    df_pension = _add_pct_usdclp(compute_deltas(dados, col, [1, 7, 28]))
    ctx["pension_line"] = make_line_chart(dados, "Data", col, "Fondos de Pensiones: Net Short (USD million)")
    ctx["pension_table"] = make_summary_table(
        df_pension, [col, "delta_1d", "delta_7d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )
    ctx["pension_delta7"] = make_bar_chart(df_pension, "Data", "delta_7d", "DELTA 7 DIAS: Fondos de Pensiones (USD million)")
    ctx["pension_delta28"] = make_bar_chart(df_pension, "Data", "delta_28d", "DELTA 28 DIAS: Fondos de Pensiones (USD million)")

    # ── OFFSHORE ──
    col = "No residentes"
    df_off = _add_pct_usdclp(compute_deltas(dados, col, [1, 7, 28]))
    ctx["offshore_line"] = make_line_chart(dados, "Data", col, "No Residentes (Offshore): Net Short (USD million)")
    ctx["offshore_table"] = make_summary_table(
        df_off, [col, "delta_1d", "delta_7d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )
    ctx["offshore_delta7"] = make_bar_chart(df_off, "Data", "delta_7d", "DELTA 7 DIAS: No Residentes (USD million)")
    ctx["offshore_delta28"] = make_bar_chart(df_off, "Data", "delta_28d", "DELTA 28 DIAS: No Residentes (USD million)")

    # ── CORPORATE ──
    col = "Empresas sector real"
    df_corp = _add_pct_usdclp(compute_deltas(dados, col, [1, 7, 28]))
    ctx["corporate_line"] = make_line_chart(dados, "Data", col, "Empresas Sector Real: Net Short (USD million)")
    ctx["corporate_table"] = make_summary_table(
        df_corp, [col, "delta_1d", "delta_7d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )
    ctx["corporate_delta7"] = make_bar_chart(df_corp, "Data", "delta_7d", "DELTA 7 DIAS: Empresas Sector Real (USD million)")
    ctx["corporate_delta28"] = make_bar_chart(df_corp, "Data", "delta_28d", "DELTA 28 DIAS: Empresas Sector Real (USD million)")

    # ── BANCOS ──
    col = "PosicaoBancos"
    df_banks = _add_pct_usdclp(compute_deltas(dados, col, [1, 7, 28]))
    ctx["banks_line"] = make_line_chart(dados, "Data", col, "Posição dos Bancos: Net Spot (USD million)")
    ctx["banks_table"] = make_summary_table(
        df_banks, [col, "delta_1d", "delta_7d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )
    ctx["banks_delta7"] = make_bar_chart(df_banks, "Data", "delta_7d", "DELTA 7 DIAS: Posição dos Bancos (USD million)")
    ctx["banks_delta28"] = make_bar_chart(df_banks, "Data", "delta_28d", "DELTA 28 DIAS: Posição dos Bancos (USD million)")

    # ── TOTAL VS USDCLP ──
    dados_total = dados.copy()
    dados_total["Total_Positioning"] = dados_total["Fondos de pensiones"] + dados_total["No residentes"]
    ctx["total_vs_usdclp"] = make_dual_axis_chart(
        dados_total, "Data", "Total_Positioning", "USDCLP",
        title="Positioning (Pensiones + Offshore) vs USDCLP",
        y1_name="Positioning (USD mm)", y2_name="USDCLP",
        invert_y2=True,
    )

    # ── FUNDOS + OFFSHORE ──
    ctx["pension_offshore_dual"] = make_dual_series_chart(
        dados, "Data", "Fondos de pensiones", "No residentes",
        title="Fondos de Pensiones vs No Residentes (Offshore)",
        y1_name="Fondos de Pensiones", y2_name="No Residentes",
    )

    return ctx


def build_swap_section(swap_data):
    """Gera charts e tables para a secao Swap Camara."""
    ctx = {}

    # Delta tables
    for tenor_key, title in [("ate2y", "Até 2y"), ("5y", "5y"), ("10y", "10y ou mais")]:
        ctx[f"swap_table_{tenor_key}"] = make_swap_delta_table(
            swap_data["delta_tables"][tenor_key], title, "k DV01"
        )

    # Line charts por tenor
    dv01 = swap_data["dv01"]

    for tenor, title in [
        ("ate2y", "Net Aplicado / Tomado Swap Camara: Até 2y"),
        ("5y", "Net Aplicado / Tomado Swap Camara: 5y"),
        ("10y", "Net Aplicado / Tomado Swap Camara: 10y ou mais"),
        ("3m", "Net Aplicado / Tomado Swap Camara: 3M"),
        ("6m", "Net Aplicado / Tomado Swap Camara: 6M"),
        ("9m", "Net Aplicado / Tomado Swap Camara: 9M"),
        ("12m", "Net Aplicado / Tomado Swap Camara: 12M"),
        ("18m", "Net Aplicado / Tomado Swap Camara: 18M"),
        ("2y", "Net Aplicado / Tomado Swap Camara: 2Y"),
    ]:
        ctx[f"swap_chart_{tenor}"] = make_swap_line_chart(dv01[tenor], tenor, title)

    return ctx


def build_offshore_adj_section(dados, afp_wk=None):
    """Gera charts e tables para a aba Offshore Ajustado.

    `afp_wk` e o semanal dos fundos de pensao, calculado uma vez no main e
    reaproveitado aqui para o comparativo de net entre os dois setores.
    """
    ctx = {}
    adj_df = build_offshore_adjusted(dados)

    # As duas pernas por semana e a correlacao entre elas (antes de inverter o sinal
    # de Offshore_Adj: essas funcoes leem as colunas cruas "No residentes"/"spot_neto")
    wk = build_weekly_legs(adj_df)
    ctx["offadj_weekly_bars"] = make_weekly_legs_bars(
        wk, "SEMANAL: as duas pernas do fluxo do offshore",
    )
    ctx["offadj_net_vs_afp"] = make_net_comparison_chart(
        build_net_comparison(afp_wk if afp_wk is not None else pd.DataFrame(), wk),
        "SEMANAL: net dos fundos de pensão vs net do offshore",
    )
    ctx["offadj_corr"] = make_offshore_corr_chart(
        build_offshore_corr(adj_df),
        "Correlação móvel entre as pernas: NDF (saldo) vs spot acumulado",
    )

    # Inverter sinal: positivo = long USD, negativo = short USD
    adj_df["Offshore_Adj"] = -adj_df["Offshore_Adj"]

    fx_labels = {
        "delta_1d": "Delta 1D",
        "delta_7d": "Delta 7D",
        "pct_usdclp": "% USDCLP",
    }

    # Dual-axis: Offshore Ajustado vs USDCLP (eixo direito NAO invertido)
    ctx["offadj_chart"] = make_dual_axis_chart(
        adj_df, "Data", "Offshore_Adj", "USDCLP",
        title="Offshore Ajustado (NDF + Spot Acum.) vs USDCLP",
        y1_name="Offshore Adj (USD mm)", y2_name="USDCLP",
        y1_color="dodgerblue", y2_color="red",
        invert_y2=False,
        annotations=[
            dict(text="Long USD", y_pos="top", color="green"),
            dict(text="Short USD", y_pos="bottom", color="red"),
        ],
    )

    # Tabela: ultimas 5 linhas com deltas + % USDCLP
    col = "Offshore_Adj"
    df_deltas = compute_deltas(adj_df, col, [1, 7, 28])
    df_deltas["pct_usdclp"] = 100 * (np.log(df_deltas["USDCLP"]) - np.log(df_deltas["USDCLP"].shift(1)))
    ctx["offadj_table"] = make_summary_table(
        df_deltas, [col, "delta_1d", "delta_7d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )

    # Bar charts de delta
    ctx["offadj_delta7"] = make_bar_chart(
        df_deltas, "Data", "delta_7d",
        "DELTA 7 DIAS: Offshore Ajustado (USD million)",
    )
    ctx["offadj_delta28"] = make_bar_chart(
        df_deltas, "Data", "delta_28d",
        "DELTA 28 DIAS: Offshore Ajustado (USD million)",
    )

    return ctx


def build_afp_flow_section(afp_df, wk):
    """Gera charts e table da aba Fluxo AFP: NDF + Spot.

    Complementa a perna de NDF que o painel ja tinha com o fluxo spot que o BCCh
    observa no setor 42, as duas em convencao compra-de-USD.
    """
    ctx = {}
    if afp_df.empty:
        indisp = "<p>Fluxo AFP indisponível: planilhas do R: e cache CSV inacessíveis</p>"
        return {
            "afp_5d": indisp, "afp_weekly": indisp,
            "afp_roll5": indisp, "afp_roll21": indisp, "afp_levels": indisp,
            "afp_ndf_level": indisp, "afp_spot_daily": indisp,
            "afp_net_daily": indisp,
            "afp_table": "<p>—</p>",
        }

    legs = build_afp_5d_legs(afp_df)

    ctx["afp_5d"] = make_afp_5d_bars(legs)
    ctx["afp_weekly"] = make_weekly_legs_bars(
        wk, "SEMANAL: as duas pernas do fluxo dos fundos de pensão — empilhado",
        stacked=True, usd=True,
    )
    # Duas versoes rolantes do mesmo painel: a curta suavizada e a de um mes.
    # Barras consecutivas compartilham dias, entao leem-se como nivel de fluxo,
    # nao como barras independentes — para isso serve o semanal acima.
    ctx["afp_roll5"] = make_weekly_legs_bars(
        build_afp_rolling_legs(afp_df, 5, media=5),
        "ROLANTE: delta de 5 pregões, média móvel de 5 dias — empilhado",
        weeks_default=120, stacked=True, usd=True, date_col="Data",
    )
    ctx["afp_roll21"] = make_weekly_legs_bars(
        build_afp_rolling_legs(afp_df, 21),
        "ROLANTE: delta de 21 pregões — empilhado",
        weeks_default=120, stacked=True, usd=True, date_col="Data",
    )
    # Os dois niveis na mesma base, com o residuo sombreado: e a leitura de
    # estoque contra estoque do hedge, que a razao removida tentava dar por
    # divisao e nao conseguia.
    ctx["afp_levels"] = make_afp_levels_chart(
        build_afp_levels(afp_df),
        "NÍVEIS REBASEADOS: Δ saldo NDF vs spot acumulado — sombreado = resíduo",
        marca=OFFSHORE_ADJ_CUTOVER,
    )
    ctx["afp_ndf_level"] = make_afp_level_line(
        afp_df, "NDF: nível do saldo forward do setor 42 (USD million)",
    )
    ctx["afp_spot_daily"] = make_afp_daily_bars(
        afp_df, "spot_bcch",
        "SPOT: fluxo diário observado pelo BCCh (USD million)",
        AFP_LEG_COLORS["bcch"],
    )
    ctx["afp_net_daily"] = make_afp_daily_bars(
        afp_df, "net_1d",
        "NET DIÁRIO: Δ NDF + spot (USD million)", "#0f766e",
    )
    ctx["afp_table"] = make_afp_legs_table(afp_df, legs.get("last_dates"))
    return ctx


def build_sectors_section(dados):
    """Gera a aba Todos os Setores: NDF + spot de cada setor, em compra-de-CLP.

    Uma tabela por horizonte (1, 7 e 28 dias) mais tres graficos empilhados
    semanais: net, a perna de NDF e a perna de spot. As tabelas fecham por construcao: as seis folhas residentes somam
    Residentes no bancos, e este mais No residentes soma o monto vigente neto.
    """
    ctx = {}
    long_df = build_all_sectors_flow(dados)

    if long_df.empty:
        indisp = "<p>Dados por setor indisponíveis</p>"
        return {
            "sectors_net": indisp, "sectors_ndf": indisp, "sectors_spot": indisp,
            **{f"sectors_table_{d}": "<p>—</p>" for d in SECTOR_WINDOWS},
        }

    for dias in SECTOR_WINDOWS:
        tab, inicio, fim = build_sector_window_table(long_df, dias)
        ctx[f"sectors_table_{dias}"] = make_sector_flow_table(tab, dias, inicio, fim)

    # Os tres saem da mesma funcao e do mesmo desenho, para dar para comparar
    # barra a barra: de onde veio o net daquela semana, do forward ou do spot.
    for chave, col, titulo in [
        ("sectors_net", "net_1d", "SEMANAL: net (Δ NDF + spot) por setor"),
        ("sectors_ndf", "ndf_1d", "SEMANAL: Δ NDF por setor"),
        ("sectors_spot", "spot", "SEMANAL: fluxo spot por setor"),
    ]:
        ctx[chave] = make_sector_weekly_stacked(
            build_sector_weekly(long_df, col),
            f"{titulo} — empilhado, linha = total",
        )
    return ctx


def build_colombia_section(col_data):
    """Gera charts e tables para Colombia."""
    ctx = {}
    series = col_data["series"]
    table_data = col_data["table_data"]

    if series.empty:
        ctx["colombia_line"] = "<p>Dados Colombia indisponíveis</p>"
        ctx["colombia_table"] = "<p>—</p>"
        ctx["colombia_delta7"] = "<p>—</p>"
        ctx["colombia_delta28"] = "<p>—</p>"
        return ctx

    ctx["colombia_line"] = make_colombia_line_chart(series)
    ctx["colombia_table"] = make_summary_table(
        table_data, ["Nivel", "Delta", "% USDCOP"], date_col="Fecha", decimals=1
    )

    # Deltas (dias corridos)
    series_deltas = compute_deltas(series, "Extranjero", [7, 28], date_col="Fecha")

    ctx["colombia_delta7"] = make_bar_chart(
        series_deltas, "Fecha", "delta_7d",
        "COLOMBIA: DELTA 7 DIAS SALDO FWD OFFSHORE (USD million)",
        date_filter="2024-01-01",
    )
    ctx["colombia_delta28"] = make_bar_chart(
        series_deltas, "Fecha", "delta_28d",
        "COLOMBIA: DELTA 28 DIAS SALDO FWD OFFSHORE (USD million)",
        date_filter="2024-01-01",
    )

    return ctx


def main():
    t0 = time.time()

    # ── 1. Fetch & Process FX Data ──
    logger.info("Buscando dados FX...")
    dados = build_fx_dados()
    logger.info("FX: %d linhas carregadas (%.1fs)", len(dados), time.time() - t0)

    # ── 2. Fetch & Process Swap Data ──
    t1 = time.time()
    logger.info("Buscando dados Swap Camara...")
    swap_data = build_swap_data()
    logger.info("Swap: carregado (%.1fs)", time.time() - t1)

    # ── 3. Fetch & Process Colombia Data ──
    t2 = time.time()
    logger.info("Buscando dados Colombia...")
    col_data = build_colombia_data()
    logger.info("Colombia: carregado (%.1fs)", time.time() - t2)

    # ── 4. Build all charts and tables ──
    logger.info("Gerando charts e tables...")
    context = {}
    brt = timezone(timedelta(hours=-3))
    context["build_timestamp"] = datetime.now(brt).strftime("%Y-%m-%d %H:%M BRT")

    # O semanal dos AFPs serve as duas abas: a propria e o comparativo de net na
    # de Offshore Ajustado. Calcular uma vez evita refazer o fetch da serie spot.
    afp_df = build_afp_spot_flow(dados)
    afp_wk = build_afp_weekly_legs(afp_df)

    context.update(build_fx_section(dados))
    context.update(build_afp_flow_section(afp_df, afp_wk))
    context.update(build_offshore_adj_section(dados, afp_wk))
    context.update(build_sectors_section(dados))
    context.update(build_swap_section(swap_data))
    context.update(build_colombia_section(col_data))

    # ── 5. Render template ──
    logger.info("Renderizando HTML...")
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("dashboard.html")
    html = template.render(**context)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")

    logger.info("Dashboard salvo em %s (%.1fs total)", output_path, time.time() - t0)
    logger.info("Tamanho: %.1f MB", output_path.stat().st_size / 1_000_000)


if __name__ == "__main__":
    main()
