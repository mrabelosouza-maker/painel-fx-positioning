"""Painel diario do estudo: fluxo AFP + indices de bolsa global.

Unico modulo do estudo que toca a rede. Os demais recebem DataFrames prontos,
para poderem ser testados sem Bloomberg nem BCCh.
"""
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

logger = logging.getLogger(__name__)

# Nome da coluna de retorno -> ticker Bloomberg no Oracle (ODS.MACRO_BBG).
INDICES = {
    "MXWO": "MXWO Index",   # MSCI World, preditor principal
    "MXWD": "MXWD Index",   # MSCI ACWI, cobertura mais ampla
    "SPX": "SPX Index",     # S&P 500, proxy mais liquida
    "MXEF": "MXEF Index",   # MSCI EM, a carteira externa do AFP nao e so DM
}

COLS_FLUXO = ["ndf_1d", "spot_bcch", "net_1d"]
INICIO_PADRAO = "2022-06-01"


def alinhar(afp: pd.DataFrame, precos: pd.DataFrame) -> pd.DataFrame:
    """Casa o fluxo AFP com os indices, no calendario do AFP.

    O retorno de um dia util chileno t e o acumulado do indice desde o dia util
    chileno anterior. Para isso o preco e reindexado nas datas do painel com
    ffill (ultimo fechamento conhecido) e so entao vira log-retorno: um feriado
    la fora sai como retorno zero e o movimento inteiro aparece no dia seguinte,
    sem sumir do acumulado.

    O ffill e no NIVEL DE PRECO, para casar calendario. O fluxo nunca e
    preenchido: dia sem fluxo publicado e linha fora do painel.
    """
    afp = afp.sort_values("Data").reset_index(drop=True)
    precos = precos.sort_values("Data").reset_index(drop=True)

    out = afp.copy()
    datas = pd.DatetimeIndex(out["Data"])
    cols_indice = [c for c in precos.columns if c != "Data"]

    for col in cols_indice:
        serie = precos.set_index("Data")[col].dropna()
        # ffill so propaga para a frente: data do painel anterior ao primeiro
        # fechamento fica NaN, e a linha cai no dropna abaixo.
        nivel = serie.reindex(serie.index.union(datas)).ffill().reindex(datas)
        out[f"r_{col}"] = np.log(nivel.to_numpy() / np.roll(nivel.to_numpy(), 1))
        out.loc[0, f"r_{col}"] = np.nan  # sem dia anterior no painel

    usadas = COLS_FLUXO + [f"r_{c}" for c in cols_indice]
    usadas = [c for c in usadas if c in out.columns]
    out = out.dropna(subset=usadas).reset_index(drop=True)
    return out[["Data"] + usadas]


def montar_painel(inicio: str = INICIO_PADRAO) -> pd.DataFrame:
    """Busca tudo e devolve o painel diario pronto para o modelo.

    Toca a rede: BCCh (via build_fx_dados) e Oracle/Bloomberg (fetch_bbg_closing).
    """
    from data_processor import build_fx_dados, build_afp_spot_flow
    from data_fetcher import fetch_bbg_closing

    dados = build_fx_dados()
    afp = build_afp_spot_flow(dados)[["Data"] + COLS_FLUXO]
    logger.info("Fluxo AFP: %d linhas (%s a %s)", len(afp),
                afp["Data"].min().date(), afp["Data"].max().date())

    precos = None
    for nome, ticker in INDICES.items():
        df = fetch_bbg_closing(ticker, nome, start=inicio)
        if df.empty:
            raise RuntimeError(f"Indice {ticker} voltou vazio do Oracle")
        precos = df if precos is None else precos.merge(df, on="Data", how="outer")

    painel = alinhar(afp, precos)
    logger.info("Painel: %d linhas (%s a %s)", len(painel),
                painel["Data"].min().date(), painel["Data"].max().date())
    return painel
