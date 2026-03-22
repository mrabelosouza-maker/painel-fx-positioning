"""Transformacoes de dados: deltas, DV01, joins."""
import numpy as np
import pandas as pd

from config import (
    CODIGO_CAMBIO,
    DURATIONS,
    OFFSHORE_ADJ_CUTOVER,
    SERIES_BANCOS,
    SERIES_FX_ALL,
    SERIES_NAMES_ALL,
    SERIES_SPOT_NR_NETO,
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

    # Remover fins de semana e feriados (linhas onde todos os valores sao NaN)
    value_cols = [c for c in dados.columns if c not in ("Data", "USDCLP")]
    dados = dados.dropna(subset=value_cols, how="all")

    dados = dados.sort_values("Data").reset_index(drop=True)
    return dados


def compute_deltas(
    df: pd.DataFrame, col: str, lags: list[int] = None,
    date_col: str = "Data",
) -> pd.DataFrame:
    """Adiciona colunas de delta baseadas em dias corridos.

    Para cada lag N, busca o valor do dia util mais proximo a (data - N dias).
    Assim, delta_1d na segunda-feira compara com sexta-feira,
    delta_7d compara com 7 dias corridos atras (dia util mais proximo), etc.
    """
    if lags is None:
        lags = [1, 7, 28]
    result = df.copy()
    result = result.sort_values(date_col).reset_index(drop=True)

    # Indexar por data para lookup rapido
    date_series = result[date_col]
    val_series = result[col]

    # Criar mapa data -> valor (usando o ultimo valor disponivel para cada data)
    date_to_val = dict(zip(date_series, val_series))
    sorted_dates = date_series.sort_values().values

    for lag in lags:
        deltas = []
        for i, row_date in enumerate(date_series):
            target_date = row_date - pd.Timedelta(days=lag)
            # Buscar o dia util mais proximo <= target_date
            candidates = sorted_dates[sorted_dates <= target_date]
            if len(candidates) > 0:
                closest_date = candidates[-1]
                prev_val = date_to_val.get(pd.Timestamp(closest_date))
                if prev_val is not None and not pd.isna(prev_val):
                    deltas.append(val_series.iloc[i] - prev_val)
                else:
                    deltas.append(np.nan)
            else:
                deltas.append(np.nan)
        result[f"delta_{lag}d"] = deltas

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

    # Remover fins de semana/feriados (linhas com todos os valores NaN)
    value_cols = [c for c in matrix.columns if c != "Data"]
    matrix = matrix.dropna(subset=value_cols, how="all")

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
    cambio_df = cambio_df[["Data", "cambio"]].dropna(subset=["Data", "cambio"]).sort_values("Data").reset_index(drop=True)

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

    # Delta tables for ate2y, 5y, 10y (dias corridos)
    delta_tables = {}
    delta_lags = [1, 7, 30, 45, 90]

    for tenor_key in ["ate2y", "5y", "10y"]:
        df_t = dv01[tenor_key].copy().dropna(subset=["Data"])
        df_t = df_t.sort_values("Data").reset_index(drop=True)
        table_data = {}

        last_date = df_t["Data"].iloc[-1] if len(df_t) > 0 else None

        for participant, suffix in [
            ("Offshore", ".offshore"),
            ("Local Ex Banks", ".localexbanks"),
        ]:
            col = f"total_{tenor_key}{suffix}"
            if col not in df_t.columns or df_t[col].dropna().empty or last_date is None:
                table_data[participant] = {f"{lag}D Change": np.nan for lag in delta_lags}
                continue
            last_val = df_t[col].iloc[-1]
            date_to_val = dict(zip(df_t["Data"], df_t[col]))
            sorted_dates = df_t["Data"].sort_values().values
            deltas = {}
            for lag in delta_lags:
                target = last_date - pd.Timedelta(days=lag)
                candidates = sorted_dates[sorted_dates <= target]
                if len(candidates) > 0:
                    prev_val = date_to_val.get(pd.Timestamp(candidates[-1]))
                    if prev_val is not None and not pd.isna(prev_val):
                        deltas[f"{lag}D Change"] = float(last_val - prev_val)
                    else:
                        deltas[f"{lag}D Change"] = np.nan
                else:
                    deltas[f"{lag}D Change"] = np.nan
            table_data[participant] = deltas

        # Local Banks = -total
        col_total = f"total_{tenor_key}"
        if col_total in df_t.columns and not df_t[col_total].dropna().empty and last_date is not None:
            last_val = -df_t[col_total].iloc[-1]
            date_to_val = dict(zip(df_t["Data"], -df_t[col_total]))
            sorted_dates = df_t["Data"].sort_values().values
            deltas_banks = {}
            for lag in delta_lags:
                target = last_date - pd.Timedelta(days=lag)
                candidates = sorted_dates[sorted_dates <= target]
                if len(candidates) > 0:
                    prev_val = date_to_val.get(pd.Timestamp(candidates[-1]))
                    if prev_val is not None and not pd.isna(prev_val):
                        deltas_banks[f"{lag}D Change"] = float(last_val - prev_val)
                    else:
                        deltas_banks[f"{lag}D Change"] = np.nan
                else:
                    deltas_banks[f"{lag}D Change"] = np.nan
            table_data["Local Banks"] = deltas_banks
        else:
            table_data["Local Banks"] = {f"{lag}D Change": np.nan for lag in delta_lags}

        delta_tables[tenor_key] = table_data

    return {
        "cambio": cambio_df,
        "agregados": agregados,
        "dv01": dv01,
        "ate2y_dv01": ate2y_df,
        "delta_tables": delta_tables,
    }


# ──────────────────────────────────────────────────────────────────────
# Offshore Ajustado
# ──────────────────────────────────────────────────────────────────────
def build_offshore_adjusted(dados: pd.DataFrame) -> pd.DataFrame:
    """Constroi serie de offshore ajustado.

    Ate 21-nov-2025: posicao offshore original (No residentes).
    A partir de 24-nov-2025: offshore original + soma acumulada do spot
    (spot comeca a acumular em 24-nov-2025).

    Retorna DataFrame com Data, Offshore_Adj, USDCLP.
    """
    cutover = pd.Timestamp(OFFSHORE_ADJ_CUTOVER)

    # Buscar spot No Residentes Neto (fluxo diario)
    spot_raw = fetch_bcentral_series(SERIES_SPOT_NR_NETO)
    spot_raw["Data"] = pd.to_datetime(spot_raw["date_str"], dayfirst=True, errors="coerce")
    spot_raw = spot_raw.dropna(subset=["Data", "value"])
    spot_raw = spot_raw[spot_raw["Data"].dt.dayofweek < 5]  # remove weekends
    spot_df = spot_raw[["Data", "value"]].rename(columns={"value": "spot_neto"})
    spot_df = spot_df.sort_values("Data").reset_index(drop=True)

    # Merge com dados FX
    result = dados[["Data", "No residentes", "USDCLP"]].copy()
    result = result.merge(spot_df, on="Data", how="left")
    result["spot_neto"] = result["spot_neto"].fillna(0.0)

    # Soma acumulada do spot a partir do cutover
    result["spot_cumsum"] = 0.0
    mask = result["Data"] >= cutover
    result.loc[mask, "spot_cumsum"] = result.loc[mask, "spot_neto"].cumsum()

    # Offshore ajustado
    result["Offshore_Adj"] = result["No residentes"].copy()
    result.loc[mask, "Offshore_Adj"] = (
        result.loc[mask, "No residentes"] + result.loc[mask, "spot_cumsum"]
    )

    return result[["Data", "Offshore_Adj", "USDCLP"]].dropna(subset=["Offshore_Adj"])


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

    # Table: last 5 rows with delta (dias corridos) and % USDCOP
    table_df = series[["Fecha", "Extranjero", "USDCOP"]].copy()
    table_df = table_df.sort_values("Fecha").reset_index(drop=True)
    table_df["USDCOP"] = pd.to_numeric(table_df["USDCOP"], errors="coerce")

    # Delta 1D em dias corridos: buscar dia util anterior
    sorted_dates = table_df["Fecha"].values
    date_to_ext = dict(zip(table_df["Fecha"], table_df["Extranjero"]))
    date_to_cop = dict(zip(table_df["Fecha"], table_df["USDCOP"]))
    deltas = []
    pct_cop = []
    for _, row in table_df.iterrows():
        target = row["Fecha"] - pd.Timedelta(days=1)
        candidates = sorted_dates[sorted_dates <= target]
        if len(candidates) > 0:
            prev_date = pd.Timestamp(candidates[-1])
            prev_ext = date_to_ext.get(prev_date)
            prev_cop = date_to_cop.get(prev_date)
            deltas.append(row["Extranjero"] - prev_ext if prev_ext is not None else np.nan)
            if prev_cop is not None and prev_cop > 0 and row["USDCOP"] > 0:
                pct_cop.append(100 * (np.log(row["USDCOP"]) - np.log(prev_cop)))
            else:
                pct_cop.append(np.nan)
        else:
            deltas.append(np.nan)
            pct_cop.append(np.nan)
    table_df["Delta"] = deltas
    table_df["% USDCOP"] = pct_cop

    table_df = table_df.rename(columns={"Extranjero": "Nivel"})
    table_data = table_df[["Fecha", "Nivel", "Delta", "% USDCOP"]].tail(5)

    return {"series": series, "table_data": table_data}
