"""Clientes para buscar dados da API do Banco Central de Chile e fontes colombianas."""
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    AFP_ALLOC_XLSX,
    AFP_FLOW_CACHE,
    AFP_FLOWS_XLSX,
    AFP_FUND_TYPES,
    AFP_HISTORY_START,
    AFP_STALE_TOL,
    BCENTRAL_CORE,
    BCENTRAL_FIRSTDATE,
    BCENTRAL_PASS,
    BCENTRAL_USER,
    BBG_TICKER_USDCLP,
    BBG_TICKER_USDCOP,
    COLOMBIA_API_URL,
    COLOMBIA_BANREP_URL,
    COLOMBIA_LOCAL_FALLBACK,
    ORACLE_CONN_STR,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Session com retry
# ──────────────────────────────────────────────────────────────────────
def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s

_session = _make_session()

# ──────────────────────────────────────────────────────────────────────
# Banco Central de Chile
# ──────────────────────────────────────────────────────────────────────
def fetch_bcentral_series(
    series_code: str,
    core: str = BCENTRAL_CORE,
    user: str = BCENTRAL_USER,
    password: str = BCENTRAL_PASS,
    firstdate: str = BCENTRAL_FIRSTDATE,
) -> pd.DataFrame:
    """Busca uma serie temporal da API BCCh. Retorna DataFrame [date_str, value]."""
    url = (
        f"{core}user={user}&pass={password}&firstdate={firstdate}"
        f"&timeseries={series_code}&function=GetSeries"
    )
    resp = _session.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    obs = data.get("Series", {}).get("Obs", [])
    if not obs:
        logger.warning("Serie %s retornou vazia", series_code)
        return pd.DataFrame(columns=["date_str", "value"])
    rows = [
        {"date_str": o.get("indexDateString", ""), "value": o.get("value")}
        for o in obs
    ]
    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def fetch_bcentral_matrix(
    series_codes: list[str], **kwargs
) -> pd.DataFrame:
    """Busca multiplas series em paralelo e retorna DataFrame wide (date_str, V1, V2, ...)."""
    results: dict[int, pd.DataFrame] = {}

    def _fetch(idx_code):
        idx, code = idx_code
        return idx, fetch_bcentral_series(code, **kwargs)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch, (i, c)): i for i, c in enumerate(series_codes)}
        for fut in as_completed(futures):
            idx, df = fut.result()
            results[idx] = df

    # merge sequencial por date_str (inner join)
    base = results[0].rename(columns={"value": "V0"})
    for i in range(1, len(series_codes)):
        right = results[i].rename(columns={"value": f"V{i}"})
        base = base.merge(right, on="date_str", how="inner")
    return base


# ──────────────────────────────────────────────────────────────────────
# Oracle DB (Bloomberg data)
# ──────────────────────────────────────────────────────────────────────
_oracle_engine = None

def _get_oracle_engine():
    """Cria (ou reutiliza) engine SQLAlchemy para o Oracle."""
    global _oracle_engine
    if _oracle_engine is None:
        from sqlalchemy import create_engine
        _oracle_engine = create_engine(
            ORACLE_CONN_STR,
            max_identifier_length=128,
            pool_recycle=3600,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _oracle_engine


def fetch_bbg_closing(ticker: str, col_name: str, start: str = "2022-06-01") -> pd.DataFrame:
    """Busca preco de fechamento (PX_LAST) via Oracle DB (Bloomberg).

    Retorna DataFrame com colunas [Data, col_name].
    """
    try:
        from sqlalchemy import text
        engine = _get_oracle_engine()
        query = text("""
            SELECT DATUM_DATE, NUMBER_VALUE
            FROM (
                SELECT BBG_SUBQUERY.*,
                    RANK() OVER (
                        PARTITION BY BBG_SUBQUERY.SERIES_CODE,
                                     BBG_SUBQUERY.RELEASE_STAGE_OVERRIDE,
                                     BBG_SUBQUERY.DATUM_DATE
                        ORDER BY BBG_SUBQUERY.UPDATED_AT DESC
                    ) DEST_RANK
                FROM (
                    SELECT * FROM ODS.MACRO_BBG
                    WHERE field = :field
                      AND ticker = :ticker
                      AND DATUM_DATE >= TO_DATE(:start_date, 'YYYY-MM-DD')
                ) BBG_SUBQUERY
            )
            WHERE DEST_RANK = 1
            ORDER BY DATUM_DATE
        """)
        params = {"field": "PX_LAST", "ticker": ticker, "start_date": start}
        df = pd.read_sql_query(query, engine, params=params)
        df.columns = df.columns.str.upper()
        df["Data"] = pd.to_datetime(df["DATUM_DATE"])
        df[col_name] = pd.to_numeric(df["NUMBER_VALUE"], errors="coerce")
        df = df[["Data", col_name]].dropna()
        logger.info("%s closing via Oracle DB: %d linhas", ticker, len(df))
        return df
    except Exception as e:
        logger.warning("Oracle DB %s falhou: %s", ticker, e)
        return pd.DataFrame(columns=["Data", col_name])


# ──────────────────────────────────────────────────────────────────────
# USDCLP / USDCOP Closing (Yahoo Finance fallback)
# ──────────────────────────────────────────────────────────────────────
def fetch_yfinance_closing(ticker_str: str, col_name: str, start: str = "2022-06-01") -> pd.DataFrame:
    """Busca preco de fechamento via Yahoo Finance.

    Retorna DataFrame com colunas [Data, col_name].
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(ticker_str)
        hist = ticker.history(start=start)
        if hist.empty:
            raise ValueError(f"Yahoo Finance retornou vazio para {ticker_str}")
        df = hist[["Close"]].reset_index()
        df = df.rename(columns={"Date": "Data", "Close": col_name})
        df["Data"] = pd.to_datetime(df["Data"]).dt.tz_localize(None)
        logger.info("%s closing via Yahoo Finance: %d linhas", ticker_str, len(df))
        return df[["Data", col_name]]
    except Exception as e:
        logger.warning("Yahoo Finance %s falhou: %s", ticker_str, e)
        return pd.DataFrame(columns=["Data", col_name])


def fetch_usdclp_closing(start: str = "2022-06-01") -> pd.DataFrame:
    """Busca USDCLP fechamento via Oracle DB. Fallback: Yahoo Finance, depois BCCh."""
    df = fetch_bbg_closing(BBG_TICKER_USDCLP, "USDCLP", start)
    if not df.empty:
        return df
    logger.warning("Fallback para Yahoo Finance para USDCLP...")
    df = fetch_yfinance_closing("USDCLP=X", "USDCLP", start)
    if not df.empty:
        return df
    logger.warning("Fallback para BCCh (media) para USDCLP...")
    from config import CODIGO_CAMBIO
    raw = fetch_bcentral_series(CODIGO_CAMBIO)
    raw["Data"] = pd.to_datetime(raw["date_str"], dayfirst=True, errors="coerce")
    raw = raw.rename(columns={"value": "USDCLP"})
    return raw[["Data", "USDCLP"]].dropna()


def fetch_usdcop_closing(start: str = "2016-01-01") -> pd.DataFrame:
    """Busca USDCOP fechamento via Oracle DB. Fallback: Yahoo Finance, depois datos.gov.co."""
    df = fetch_bbg_closing(BBG_TICKER_USDCOP, "USDCOP", start)
    if not df.empty:
        return df
    logger.warning("Fallback para Yahoo Finance para USDCOP...")
    df = fetch_yfinance_closing("USDCOP=X", "USDCOP", start)
    if not df.empty:
        return df
    logger.warning("Fallback para datos.gov.co para USDCOP...")
    return fetch_colombia_cop()


# ──────────────────────────────────────────────────────────────────────
# Colombia
# ──────────────────────────────────────────────────────────────────────
def fetch_colombia_cop() -> pd.DataFrame:
    """Busca taxa USDCOP da API datos.gov.co."""
    try:
        resp = _session.get(COLOMBIA_API_URL, timeout=30)
        resp.raise_for_status()
        records = resp.json()
        df = pd.DataFrame(records)
        df["Fecha"] = pd.to_datetime(df["vigenciahasta"])
        df["USDCOP"] = pd.to_numeric(df["valor"], errors="coerce")
        df = df[["Fecha", "USDCOP"]].sort_values("Fecha").reset_index(drop=True)
        return df
    except Exception as e:
        logger.error("Erro ao buscar USDCOP: %s", e)
        return pd.DataFrame(columns=["Fecha", "USDCOP"])


def fetch_colombia_forwards() -> pd.DataFrame:
    """Baixa Excel de forwards da Banrep. Fallback para arquivo local."""
    try:
        resp = _session.get(COLOMBIA_BANREP_URL, timeout=60)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "spreadsheet" in content_type or "excel" in content_type or "octet" in content_type:
            buf = io.BytesIO(resp.content)
            df = pd.read_excel(buf, sheet_name="4. SaldoDiario", skiprows=6, engine="openpyxl")
            return df
    except Exception as e:
        logger.warning("Download Banrep falhou (%s), tentando arquivo local...", e)

    try:
        df = pd.read_excel(
            COLOMBIA_LOCAL_FALLBACK,
            sheet_name="4. SaldoDiario",
            skiprows=6,
            engine="openpyxl",
        )
        return df
    except Exception as e2:
        logger.error("Fallback local tambem falhou: %s", e2)
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────
# Fundos de pensao: fluxo diario por tipo de fundo e fatia offshore
# ──────────────────────────────────────────────────────────────────────
def _afp_flows_from_xlsx() -> pd.DataFrame:
    """Fluxo diario (dinheiro novo) por tipo de fundo, em MM CLP.

    Le as abas `Fundo A`..`Fundo E` de DadosDiarios.xlsx. Cada aba traz, para as
    seis AFPs, o valor cuota (colunas E,G,I,K,M,O) e o patrimonio do fundo
    (F,H,J,L,N,P), ambos da Bloomberg. O fluxo limpo de retorno de cada AFP e

        q_{t-1} * NAV_t / q_t - NAV_{t-1}

    e o fluxo do tipo de fundo e a soma sobre as seis AFPs.

    Reproduz a aba `Consolidado` da propria planilha (diferenca maxima 0,0) mas
    dois dias mais fresco, porque o `Consolidado` tem range fixo de formulas.
    """
    out = {}
    for fund in AFP_FUND_TYPES:
        raw = pd.read_excel(
            AFP_FLOWS_XLSX, sheet_name=f"Fundo {fund}",
            skiprows=8, usecols="D:P", header=None,
        )
        raw.columns = ["Data"] + [f"c{i}" for i in range(12)]
        raw["Data"] = pd.to_datetime(raw["Data"], errors="coerce")
        raw = raw.dropna(subset=["Data"]).set_index("Data").sort_index()
        raw = raw.apply(pd.to_numeric, errors="coerce")

        total = pd.Series(0.0, index=raw.index)
        has_data = pd.Series(False, index=raw.index)
        for k in range(6):  # seis AFPs, pares (cuota, patrimonio)
            quota = raw[f"c{2 * k}"]
            nav = raw[f"c{2 * k + 1}"]
            flow = (quota.shift(1) * nav / quota) - nav.shift(1)
            total = total.add(flow.fillna(0.0))
            has_data = has_data | flow.notna()
        out[fund] = total.where(has_data)

    flows = pd.DataFrame(out)

    # Dias em que os cinco fundos nao se movem sao Bloomberg estagnado (cuota e
    # patrimonio nao atualizaram), nao ausencia de fluxo.
    stale = flows.abs().max(axis=1).fillna(0) < AFP_STALE_TOL
    flows = flows[~stale]
    flows = flows[flows.index >= AFP_HISTORY_START]

    logger.info(
        "AFP fluxos via xlsx: %d dias, ate %s",
        len(flows), flows.index.max().date(),
    )
    return flows


def _afp_weights_from_xlsx() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fatia offshore e AUM por tipo de fundo, mensal.

    Le o bloco `% Portfolio` das abas `Fundo A`..`Fundo E` de
    Fundos de Pensao.xlsx. Retorna (fatia offshore total, AUM em MM USD).
    """
    weights, aum = {}, {}
    for fund in AFP_FUND_TYPES:
        raw = pd.read_excel(
            AFP_ALLOC_XLSX, sheet_name=f"Fundo {fund}",
            skiprows=1, usecols="A:P",
        )
        raw.columns = [
            "Data", "n_tot", "n_rv", "n_rf", "off_tot", "off_rv", "off_rf",
            "total", "_gap", "p_ntot", "p_nrv", "p_nrf", "p_offtot",
            "p_offrv", "p_offrf", "p_tot",
        ]
        raw["Data"] = pd.to_datetime(raw["Data"], errors="coerce")
        raw = raw.dropna(subset=["Data"]).set_index("Data").sort_index()
        weights[fund] = pd.to_numeric(raw["p_offtot"], errors="coerce")
        aum[fund] = pd.to_numeric(raw["total"], errors="coerce")

    w_df = pd.DataFrame(weights).dropna(how="all")
    aum_df = pd.DataFrame(aum).dropna(how="all")
    logger.info("AFP pesos offshore via xlsx: ate %s", w_df.index.max().date())
    return w_df, aum_df


def _cache_path() -> Path:
    return Path(__file__).resolve().parent.parent / AFP_FLOW_CACHE


def _write_afp_cache(flows: pd.DataFrame, weights: pd.DataFrame, aum: pd.DataFrame) -> None:
    """Grava o CSV versionado que serve de fonte quando o R: nao esta acessivel."""
    wide = flows.add_prefix("flow_")
    for src, prefix in ((weights, "woff_"), (aum, "aum_")):
        daily = src.reindex(src.index.union(flows.index)).ffill().reindex(flows.index)
        wide = wide.join(daily.add_prefix(prefix))
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    wide.rename_axis("Data").to_csv(path, float_format="%.6f")
    logger.info("AFP cache gravado: %s (%d linhas)", path, len(wide))


def _read_afp_cache() -> pd.DataFrame:
    path = _cache_path()
    df = pd.read_csv(path, parse_dates=["Data"]).set_index("Data").sort_index()
    logger.info("AFP via cache CSV: %d dias, ate %s", len(df), df.index.max().date())
    return df


def fetch_afp_flows_and_weights() -> pd.DataFrame:
    """Fluxo diario por tipo de fundo, fatia offshore e AUM, tudo em base diaria.

    Fonte primaria: as planilhas no R:. Quando elas nao estao acessiveis (ex.:
    GitHub Actions), cai para o CSV versionado gravado pelo ultimo build local.
    Retorna DataFrame indexado por Data com colunas flow_A..E (MM CLP),
    woff_A..E (fracao) e aum_A..E (MM USD), ou vazio se nenhuma fonte servir.
    """
    try:
        flows = _afp_flows_from_xlsx()
        weights, aum = _afp_weights_from_xlsx()
        _write_afp_cache(flows, weights, aum)
        return _read_afp_cache()
    except Exception as e:
        logger.warning("Planilhas AFP no R: indisponiveis (%s), tentando cache...", e)

    try:
        return _read_afp_cache()
    except Exception as e2:
        logger.error("Cache AFP tambem falhou: %s", e2)
        return pd.DataFrame()
