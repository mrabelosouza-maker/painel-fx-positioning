"""Clientes para buscar dados da API do Banco Central de Chile e fontes colombianas."""
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
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
