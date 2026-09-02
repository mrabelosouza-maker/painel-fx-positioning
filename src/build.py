"""Orquestrador principal: busca dados, processa, gera HTML estatico."""
import os
import sys
import time
import logging
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

# Adiciona src/ ao path para imports relativos
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from config import SECTOR_WINDOWS, OFFSHORE_ADJ_DEFAULT_START
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
    JGP_AZUL,
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
    # Unica aba das quatro em compra-de-USD: positivo = compra de USD, negativo
    # = venda de USD. A serie crua do BCCh vem na otica do banco residente
    # (positivo = AFP net short USD = AFP vendendo USD), entao entra invertida.
    # Inverte-se o nivel junto com os deltas, senao tabela e grafico discordam.
    # As abas de offshore, corporate e bancos seguem no sinal cru.
    # Deltas em PREGOES (5 e 21), como a aba de fluxo AFP — nao em dias corridos.
    col = "Fondos de pensiones"
    dados_pension = dados.copy()
    dados_pension[col] = -dados_pension[col]
    df_pension = _add_pct_usdclp(
        compute_deltas(dados_pension, col, [1, 5, 21], sessions=True)
    )
    pension_labels = {
        "delta_1d": "Delta 1D",
        "delta_5d": "Delta 5D",
        "delta_21d": "Delta 21D",
        "pct_usdclp": "% USDCLP",
    }
    ctx["pension_line"] = make_line_chart(
        dados_pension, "Data", col,
        "Fondos de Pensiones: Posição em USD (USD million)",
        usd_labels=True,
    )
    ctx["pension_table"] = make_summary_table(
        df_pension, [col, "delta_1d", "delta_5d", "pct_usdclp"],
        col_labels={col: "Nivel", **pension_labels}, decimals=1,
    )
    ctx["pension_delta5"] = make_bar_chart(
        df_pension, "Data", "delta_5d",
        "DELTA 5 PREGÕES: Fondos de Pensiones (USD million)",
        usd_labels=True,
    )
    ctx["pension_delta21"] = make_bar_chart(
        df_pension, "Data", "delta_21d",
        "DELTA 21 PREGÕES: Fondos de Pensiones (USD million)",
        usd_labels=True,
    )

    # ── OFFSHORE ──
    # Mesma convencao compra-de-USD das abas de Fundos de Pensao, Fluxo AFP e
    # Todos os Setores: positivo = compra de USD. A serie crua do BCCh vem na
    # otica do banco residente (positivo = offshore net short USD = offshore
    # vendendo USD), entao entra invertida — nivel e deltas juntos, senao tabela
    # e grafico discordam. Deltas em PREGOES (5 e 21), nao em dias corridos.
    col = "No residentes"
    dados_off = dados.copy()
    dados_off[col] = -dados_off[col]
    df_off = _add_pct_usdclp(
        compute_deltas(dados_off, col, [1, 5, 21], sessions=True)
    )
    offshore_labels = {
        "delta_1d": "Delta 1D",
        "delta_5d": "Delta 5D",
        "delta_21d": "Delta 21D",
        "pct_usdclp": "% USDCLP",
    }
    ctx["offshore_line"] = make_line_chart(
        dados_off, "Data", col,
        "No Residentes (Offshore): Posição em USD (USD million)",
        usd_labels=True,
    )
    ctx["offshore_table"] = make_summary_table(
        df_off, [col, "delta_1d", "delta_5d", "pct_usdclp"],
        col_labels={col: "Nivel", **offshore_labels}, decimals=1,
    )
    ctx["offshore_delta5"] = make_bar_chart(
        df_off, "Data", "delta_5d",
        "DELTA 5 PREGÕES: No Residentes (USD million)",
        usd_labels=True,
    )
    ctx["offshore_delta21"] = make_bar_chart(
        df_off, "Data", "delta_21d",
        "DELTA 21 PREGÕES: No Residentes (USD million)",
        usd_labels=True,
    )

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

    Toda a aba na convencao compra-de-USD: positivo = compra de USD (venda de
    CLP), negativo = venda de USD. Vale para o nivel, para os deltas e para as
    duas pernas semanais — as series cruas do BCCh vem na otica do banco
    residente e entram invertidas.

    `afp_wk` e o semanal dos fundos de pensao, calculado uma vez no main e
    reaproveitado aqui para o comparativo de net entre os dois setores.
    """
    ctx = {}
    adj_df = build_offshore_adjusted(dados)

    # As duas pernas por semana e a correlacao entre elas. build_weekly_legs ja
    # devolve em compra-de-USD; build_offshore_corr le as colunas cruas e a
    # correlacao e invariante a inversao conjunta das duas pernas.
    wk = build_weekly_legs(adj_df)
    ctx["offadj_weekly_bars"] = make_weekly_legs_bars(
        wk, "SEMANAL: as duas pernas do fluxo do offshore", usd=True,
    )
    ctx["offadj_net_vs_afp"] = make_net_comparison_chart(
        build_net_comparison(afp_wk if afp_wk is not None else pd.DataFrame(), wk),
        "SEMANAL: net dos fundos de pensão vs net do offshore",
    )
    ctx["offadj_corr"] = make_offshore_corr_chart(
        build_offshore_corr(adj_df),
        "Correlação móvel entre as pernas: NDF (saldo) vs spot acumulado",
    )

    # Inverter sinal: positivo = compra de USD, negativo = venda de USD
    adj_df["Offshore_Adj"] = -adj_df["Offshore_Adj"]

    # Deltas em PREGOES (5 e 21), como as abas de Fundos de Pensao, Offshore e
    # Fluxo AFP — nao em dias corridos, que dariam janela erratica (5 dias
    # corridos cobrem 3 pregoes na segunda e 5 so na sexta).
    fx_labels = {
        "delta_1d": "Delta 1D",
        "delta_5d": "Delta 5D",
        "delta_21d": "Delta 21D",
        "pct_usdclp": "% USDCLP",
    }

    # Dual-axis: Offshore Ajustado vs USDCLP (eixo direito NAO invertido, porque
    # na convencao compra-de-USD as duas series andam no mesmo sentido). Abre em
    # jan/2025 com os dois eixos padronizados na janela visivel, o que faz as
    # linhas andarem quase um pra um; o JS refaz essa conta quando o usuario
    # expande a janela, ate a amostra toda.
    ctx["offadj_chart"] = make_dual_axis_chart(
        adj_df, "Data", "Offshore_Adj", "USDCLP",
        title="Offshore Ajustado (NDF + Spot Acum.) vs USDCLP",
        y1_name="Offshore Adj (USD mm)", y2_name="USDCLP",
        y2_color=JGP_AZUL,
        invert_y2=False,
        default_start=OFFSHORE_ADJ_DEFAULT_START,
        usd_labels=True,
        fit_1a1=True,
    )

    # Tabela: ultimas 5 linhas com deltas + % USDCLP
    col = "Offshore_Adj"
    df_deltas = compute_deltas(adj_df, col, [1, 5, 21], sessions=True)
    df_deltas["pct_usdclp"] = 100 * (np.log(df_deltas["USDCLP"]) - np.log(df_deltas["USDCLP"].shift(1)))
    ctx["offadj_table"] = make_summary_table(
        df_deltas, [col, "delta_1d", "delta_5d", "pct_usdclp"],
        col_labels={col: "Nivel", **fx_labels}, decimals=1,
    )

    # Bar charts de delta
    ctx["offadj_delta5"] = make_bar_chart(
        df_deltas, "Data", "delta_5d",
        "DELTA 5 PREGÕES: Offshore Ajustado (USD million)",
        usd_labels=True,
    )
    ctx["offadj_delta21"] = make_bar_chart(
        df_deltas, "Data", "delta_21d",
        "DELTA 21 PREGÕES: Offshore Ajustado (USD million)",
        usd_labels=True,
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
    # A ancora e o primeiro dia com saldo de NDF; o nivel daquele dia vai no
    # subtitulo, porque e o tamanho que o rebasement esconde.
    ancora = afp_df.dropna(subset=["ndf_level"]).iloc[0]
    ctx["afp_levels"] = make_afp_levels_chart(
        build_afp_levels(afp_df),
        "NÍVEIS REBASEADOS: Δ saldo NDF vs spot acumulado — sombreado = resíduo",
        ancora=ancora["Data"], nivel_ancora=ancora["ndf_level"],
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


def _copiar_plotly() -> None:
    """Coloca o plotly.min.js do pacote instalado ao lado do index.html.

    A casca JGP pede a lib local, nao de CDN. E aqui isso tambem corrige um
    descasamento: as figuras sao serializadas pelo plotly.py instalado, e a
    versao do CDN que o painel usava era outra. Copia so quando muda de
    tamanho — sao ~5 MB e o commit diario nao precisa reescrever isso.
    """
    import plotly
    origem = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    destino = OUTPUT_DIR / "plotly.min.js"
    if not origem.exists():
        logger.warning("plotly.min.js nao encontrado em %s", origem)
        return
    if destino.exists() and destino.stat().st_size == origem.stat().st_size:
        return
    shutil.copyfile(origem, destino)
    logger.info("plotly.min.js copiado (%s, %.1f MB)",
                plotly.__version__, origem.stat().st_size / 1e6)


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
    _copiar_plotly()
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")

    logger.info("Dashboard salvo em %s (%.1fs total)", output_path, time.time() - t0)
    logger.info("Tamanho: %.1f MB", output_path.stat().st_size / 1_000_000)


if __name__ == "__main__":
    main()
