"""Transformacoes de dados: deltas, DV01, joins."""
import numpy as np
import pandas as pd

from config import (
    CODIGO_CAMBIO,
    DURATIONS,
    SERIES_BANCOS,
    SERIES_FX_ALL,
    SERIES_NAMES_ALL,
    SERIES_SWAP_LOCAL,
    SERIES_SWAP_OFFSHORE,
    SERIES_SWAP_TOTAL,
    SWAP_TENOR_NAMES,
    TENOR_DURATION_MAP,
)
from data_fetcher import (
    fetch_bcentral_matrix,
    fetch_bcentral_series,
    fetch_colombia_cop,
    fetch_colombia_forwards,
)


# ──────────────────────────────────────────────────────────────────────
# FX Positioning
# ──────────────────────────────────────────────────────────────────────
def build_fx_dados() -> pd.DataFrame:
    """Replica build_dados() do R: busca series FX + cambio, join, parse datas."""
    matrix = fetch_bcentral_matrix(SERIES_FX_ALL)
    cambio = fetch_bcentral_series(CODIGO_CAMBIO)

    # rename columns
    col_map = {"date_str": "date_str"}
    for i, name in enumerate(SERIES_NAMES_ALL):
        col_map[f"V{i}"] = name
    matrix = matrix.rename(columns=col_map)

    # merge with cambio
    cambio = cambio.rename(columns={"value": "USDCLP"})
    dados = matrix.merge(cambio, on="date_str", how="inner")

    # parse date
    dados["Data"] = pd.to_datetime(dados["date_str"], dayfirst=True, errors="coerce")
    dados = dados.drop(columns=["date_str"]).dropna(subset=["Data"])
    dados = dados.sort_values("Data").reset_index(drop=True)
    return dados


def compute_deltas(
    df: pd.DataFrame, col: str, lags: list[int] = None
) -> pd.DataFrame:
    """Adiciona colunas de delta (col - lag) ao DataFrame."""
    if lags is None:
        lags = [1, 7, 28]
    result = df.copy()
    for lag in lags:
        result[f"delta_{lag}d"] = result[col] - result[col].shift(lag)
    return result


# ──────────────────────────────────────────────────────────────────────
# Swap Camara
# ──────────────────────────────────────────────────────────────────────
def _fetch_swap_group(series_codes: list[str]) -> pd.DataFrame:
    """Busca um grupo de 10 series swap e retorna com colunas nomeadas por tenor."""
    matrix = fetch_bcentral_matrix(series_codes)
    col_map = {"date_str": "date_str"}
    for i, name in enumerate(SWAP_TENOR_NAMES):
        col_map[f"V{i}"] = f"total_{name}"
    matrix = matrix.rename(columns=col_map)
    matrix["Data"] = pd.to_datetime(matrix["date_str"], dayfirst=True, errors="coerce")
    matrix = matrix.drop(columns=["date_str"]).dropna(subset=["Data"])
    return matrix.sort_values("Data").reset_index(drop=True)


def build_swap_data() -> dict:
    """Busca e processa todos os dados de Swap Camara.

    Retorna dict com:
        - 'cambio': DataFrame com Data e cambio
        - 'agregados': DataFrame consolidado (total + offshore + localexbanks)
        - 'dv01': dict[tenor -> DataFrame com DV01 por participante]
        - 'ate2y_dv01': DataFrame com DV01 agregado ate 2y
        - 'delta_tables': dict[tenor -> dict com deltas por participante]
    """
    # Fetch 3 groups
    total_df = _fetch_swap_group(SERIES_SWAP_TOTAL)
    offshore_df = _fetch_swap_group(SERIES_SWAP_OFFSHORE)
    local_df = _fetch_swap_group(SERIES_SWAP_LOCAL)

    # Fetch cambio
    cambio_raw = fetch_bcentral_series(CODIGO_CAMBIO)
    cambio_df = cambio_raw.rename(columns={"value": "cambio", "date_str": "ds"})
    cambio_df["Data"] = pd.to_datetime(cambio_df["ds"], dayfirst=True, errors="coerce")
    cambio_df = cambio_df[["Data", "cambio"]].dropna().sort_values("Data").reset_index(drop=True)

    # Rename offshore/local columns
    offshore_renamed = offshore_df.copy()
    for c in offshore_renamed.columns:
        if c != "Data":
            offshore_renamed = offshore_renamed.rename(columns={c: f"{c}.offshore"})

    local_renamed = local_df.copy()
    for c in local_renamed.columns:
        if c != "Data":
            local_renamed = local_renamed.rename(columns={c: f"{c}.localexbanks"})

    # Merge
    agregados = total_df.merge(offshore_renamed, on="Data", how="left")
    agregados = agregados.merge(local_renamed, on="Data", how="left")

    # DV01 by tenor
    dv01 = {}
    tenors_with_duration = ["3m", "6m", "9m", "12m", "18m", "2y", "5y", "10y"]

    for tenor in tenors_with_duration:
        dur = TENOR_DURATION_MAP[tenor]
        cols_total = f"total_{tenor}"
        cols_off = f"total_{tenor}.offshore"
        cols_loc = f"total_{tenor}.localexbanks"

        tenor_df = agregados[["Data", cols_total, cols_off, cols_loc]].copy()
        tenor_df = tenor_df.merge(cambio_df, on="Data", how="left")

        for c in [cols_total, cols_off, cols_loc]:
            tenor_df[c] = 1_000_000 * ((tenor_df[c] * dur) / 10_000) / tenor_df["cambio"]

        dv01[tenor] = tenor_df

    # ate2y DV01 = sum of 3m through 2y
    ate2y_tenors = ["3m", "6m", "9m", "12m", "18m", "2y"]
    ate2y_df = dv01["3m"][["Data"]].copy()

    for participant in ["total", "offshore", "localexbanks"]:
        suffix = "" if participant == "total" else f".{participant}"
        col_name = f"total_ate2y{suffix}"
        ate2y_df[col_name] = 0.0
        for t in ate2y_tenors:
            src_col = f"total_{t}{suffix}"
            ate2y_df[col_name] = ate2y_df[col_name] + dv01[t][src_col].values

    dv01["ate2y"] = ate2y_df

    # Delta tables for ate2y, 5y, 10y
    delta_tables = {}
    delta_lags = [1, 7, 30, 45, 90]

    for tenor_key in ["ate2y", "5y", "10y"]:
        df_t = dv01[tenor_key].copy()
        table_data = {}

        for participant, suffix in [
            ("Offshore", ".offshore"),
            ("Local Ex Banks", ".localexbanks"),
        ]:
            col = f"total_{tenor_key}{suffix}"
            deltas = {}
            for lag in delta_lags:
                val = df_t[col].iloc[-1] - df_t[col].iloc[-(lag + 1)] if len(df_t) > lag else np.nan
                deltas[f"{lag}D Change"] = val
            table_data[participant] = deltas

        # Local Banks = -total
        col_total = f"total_{tenor_key}"
        neg_total = -df_t[col_total]
        deltas_banks = {}
        for lag in delta_lags:
            val = neg_total.iloc[-1] - neg_total.iloc[-(lag + 1)] if len(df_t) > lag else np.nan
            deltas_banks[f"{lag}D Change"] = val
        table_data["Local Banks"] = deltas_banks

        delta_tables[tenor_key] = table_data

    return {
        "cambio": cambio_df,
        "agregados": agregados,
        "dv01": dv01,
        "ate2y_dv01": ate2y_df,
        "delta_tables": delta_tables,
    }


# ──────────────────────────────────────────────────────────────────────
# Colombia
# ──────────────────────────────────────────────────────────────────────
def build_colombia_data() -> dict:
    """Busca e processa dados de Colombia (USDCOP + forwards Banrep).

    Retorna dict com:
        - 'series': DataFrame com Fecha, Extranjero, FPC, RestoyReal, USDCOP
        - 'table_data': DataFrame com ultimas 5 linhas formatadas
    """
    cop_df = fetch_colombia_cop()
    fwd_df = fetch_colombia_forwards()

    if fwd_df.empty:
        return {"series": pd.DataFrame(), "table_data": pd.DataFrame()}

    fwd_df = fwd_df.sort_values("Fecha").copy()
    fwd_df["RestoyReal"] = fwd_df["Resto"] + fwd_df["Real"]
    series = fwd_df[["Fecha", "Extranjero", "FPC", "RestoyReal"]].copy()

    # Merge with COP
    if not cop_df.empty:
        series = series.merge(cop_df, on="Fecha", how="left")
    else:
        series["USDCOP"] = np.nan

    series = series.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)

    # Table: last 5 rows with delta and % USDCOP
    table_df = series[["Fecha", "Extranjero", "USDCOP"]].copy()
    table_df["USDCOP"] = pd.to_numeric(table_df["USDCOP"], errors="coerce")
    table_df["Delta"] = table_df["Extranjero"] - table_df["Extranjero"].shift(1)
    table_df["% USDCOP"] = 100 * (
        np.log(table_df["USDCOP"]) - np.log(table_df["USDCOP"].shift(1))
    )
    table_df = table_df.rename(columns={"Extranjero": "Nivel"})
    table_data = table_df[["Fecha", "Nivel", "Delta", "% USDCOP"]].tail(5)

    return {"series": series, "table_data": table_data}
