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
    COLOMBIA_API_URL,
    COLOMBIA_BANREP_URL,
    COLOMBIA_LOCAL_FALLBACK,
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
