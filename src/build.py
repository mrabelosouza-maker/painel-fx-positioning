"""Orquestrador principal: busca dados, processa, gera HTML estatico."""
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import numpy as np

# Adiciona src/ ao path para imports relativos
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from data_processor import build_fx_dados, compute_deltas, build_swap_data, build_colombia_data, build_offshore_adjusted
from chart_builder import (
    make_line_chart,
    make_bar_chart,
    make_dual_axis_chart,
    make_dual_series_chart,
    make_swap_line_chart,
    make_swap_delta_bars,
    make_colombia_line_chart,
)
from table_builder import make_summary_table, make_swap_delta_table

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

    # ── FUNDOS DE PENSÃO ──
    col = "Fondos de pensiones"
    df_pension = compute_deltas(dados, col, [1, 7, 28])
    ctx["pension_line"] = make_line_chart(dados, "Data", col, "Fondos de Pensiones: Net Short (USD million)")
    ctx["pension_table"] = make_summary_table(
        df_pension, [col, "delta_1d", "delta_7d", "delta_28d"],
        col_labels={col: "Nivel", **fx_labels},
    )
    ctx["pension_delta7"] = make_bar_chart(df_pension, "Data", "delta_7d", "DELTA 7 DIAS: Fondos de Pensiones (USD million)")
    ctx["pension_delta28"] = make_bar_chart(df_pension, "Data", "delta_28d", "DELTA 28 DIAS: Fondos de Pensiones (USD million)")

    # ── OFFSHORE ──
    col = "No residentes"
    df_off = compute_deltas(dados, col, [1, 7, 28])
    df_off["pct_usdclp"] = 100 * (np.log(df_off["USDCLP"]) - np.log(df_off["USDCLP"].shift(1)))
    ctx["offshore_line"] = make_line_chart(dados, "Data", col, "No Residentes (Offshore): Net Short (USD million)")
    ctx["offshore_table"] = make_summary_table(
        df_off, [col, "delta_1d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )
    ctx["offshore_delta7"] = make_bar_chart(df_off, "Data", "delta_7d", "DELTA 7 DIAS: No Residentes (USD million)")
    ctx["offshore_delta28"] = make_bar_chart(df_off, "Data", "delta_28d", "DELTA 28 DIAS: No Residentes (USD million)")

    # ── CORPORATE ──
    col = "Empresas sector real"
    df_corp = compute_deltas(dados, col, [1, 7, 28])
    ctx["corporate_line"] = make_line_chart(dados, "Data", col, "Empresas Sector Real: Net Short (USD million)")
    ctx["corporate_table"] = make_summary_table(
        df_corp, [col, "delta_1d", "delta_7d", "delta_28d"],
        col_labels={col: "Nivel", **fx_labels},
    )
    ctx["corporate_delta7"] = make_bar_chart(df_corp, "Data", "delta_7d", "DELTA 7 DIAS: Empresas Sector Real (USD million)")
    ctx["corporate_delta28"] = make_bar_chart(df_corp, "Data", "delta_28d", "DELTA 28 DIAS: Empresas Sector Real (USD million)")

    # ── BANCOS ──
    col = "PosicaoBancos"
    df_banks = compute_deltas(dados, col, [1, 7, 28])
    ctx["banks_line"] = make_line_chart(dados, "Data", col, "Posição dos Bancos: Net Spot (USD million)")
    ctx["banks_table"] = make_summary_table(
        df_banks, [col, "delta_1d", "delta_7d", "delta_28d"],
        col_labels={col: "Nivel", **fx_labels},
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


def build_offshore_adj_section(dados):
    """Gera charts e tables para a aba Offshore Ajustado."""
    ctx = {}
    adj_df = build_offshore_adjusted(dados)

    fx_labels = {
        "delta_1d": "Delta 1D",
        "delta_7d": "Delta 7D",
        "delta_28d": "Delta 28D",
    }

    # Dual-axis: Offshore Ajustado vs USDCLP
    ctx["offadj_chart"] = make_dual_axis_chart(
        adj_df, "Data", "Offshore_Adj", "USDCLP",
        title="Offshore Ajustado (NDF + Spot Acum.) vs USDCLP",
        y1_name="Offshore Adj (USD mm)", y2_name="USDCLP",
        y1_color="dodgerblue", y2_color="red",
        invert_y2=True,
    )

    # Tabela: ultimas 5 linhas com deltas
    col = "Offshore_Adj"
    df_deltas = compute_deltas(adj_df, col, [1, 7, 28])
    ctx["offadj_table"] = make_summary_table(
        df_deltas, [col, "delta_1d", "delta_7d", "delta_28d"],
        col_labels={col: "Nivel", **fx_labels},
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
    context["build_timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    context.update(build_fx_section(dados))
    context.update(build_offshore_adj_section(dados))
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
