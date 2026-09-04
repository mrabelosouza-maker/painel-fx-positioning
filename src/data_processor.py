"""Transformacoes de dados: deltas, DV01, joins."""
import numpy as np
import pandas as pd

from config import (
    SECTOR_CHART_LINES,
    SECTOR_NET_LINE,
    SECTOR_SPOT_SERIES,
    SECTOR_TABLE_ORDER,
    SECTOR_WINDOWS,
    CODIGO_CAMBIO,
    DURATIONS,
    OFFSHORE_ADJ_CUTOVER,
    OFFSHORE_WEEKLY_SESSIONS,
    SERIES_BANCOS,
    SERIES_FX_ALL,
    SERIES_NAMES_ALL,
    SERIES_NDF_PENSION_NAME,
    SERIES_SPOT_NR_NETO,
    SERIES_SPOT_PENSION,
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
    fetch_usdclp_closing,
    fetch_usdcop_closing,
)


# ──────────────────────────────────────────────────────────────────────
# FX Positioning
# ──────────────────────────────────────────────────────────────────────
def build_fx_dados() -> pd.DataFrame:
    """Busca series FX + USDCLP closing (Yahoo Finance), join, parse datas."""
    matrix = fetch_bcentral_matrix(SERIES_FX_ALL)

    # rename columns
    col_map = {"date_str": "date_str"}
    for i, name in enumerate(SERIES_NAMES_ALL):
        col_map[f"V{i}"] = name
    matrix = matrix.rename(columns=col_map)

    # parse date
    matrix["Data"] = pd.to_datetime(matrix["date_str"], dayfirst=True, errors="coerce")
    matrix = matrix.drop(columns=["date_str"]).dropna(subset=["Data"])

    # merge with USDCLP closing (Yahoo Finance)
    cambio = fetch_usdclp_closing()
    dados = matrix.merge(cambio, on="Data", how="left")

    # Remover fins de semana e feriados (linhas onde todos os valores sao NaN)
    value_cols = [c for c in dados.columns if c not in ("Data", "USDCLP")]
    dados = dados.dropna(subset=value_cols, how="all")

    dados = dados.sort_values("Data").reset_index(drop=True)
    return dados


def compute_deltas(
    df: pd.DataFrame, col: str, lags: list[int] = None,
    date_col: str = "Data", sessions: bool = False,
) -> pd.DataFrame:
    """Adiciona colunas de delta baseadas em dias corridos.

    Para cada lag N, busca o valor do dia util mais proximo a (data - N dias).
    Assim, delta_1d na segunda-feira compara com sexta-feira,
    delta_7d compara com 7 dias corridos atras (dia util mais proximo), etc.

    Com `sessions=True` o lag conta PREGOES, nao dias corridos: como o df ja vem
    so com dia util (fim de semana e feriado caem no dropna de build_fx_data),
    diff(N) anda exatamente N sessoes. Mesma convencao de AFP_DELTA_SESSIONS na
    aba de fluxo AFP. Dias corridos dariam janela erratica: 5 dias corridos
    cobrem 3 pregoes na segunda e 5 so na sexta.
    """
    if lags is None:
        lags = [1, 7, 28]
    result = df.copy()
    result = result.sort_values(date_col).reset_index(drop=True)

    if sessions:
        for lag in lags:
            result[f"delta_{lag}d"] = result[col].diff(lag)
        return result

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


# Horizontes da tabela de swap em PREGOES: 1, 5, 21, 32 e 63 sessoes valem os
# antigos 1, 7, 30, 45 e 90 dias corridos (calendario x 5/7).
SWAP_DELTA_SESSIONS = [1, 5, 21, 32, 63]


def swap_delta_label(sessoes: int) -> str:
    """Rotulo da linha da tabela de swap: 1 Pregao / N Pregoes."""
    return "1 Pregão" if sessoes == 1 else f"{sessoes} Pregões"


def _deltas_por_pregao(serie: pd.Series, lags: list[int]) -> dict:
    """Variacao do ultimo valor contra o de N pregoes atras, para cada N.

    A serie ja vem so com pregao, entao andar N linhas anda N sessoes.
    """
    valores = serie.reset_index(drop=True)
    ultimo = valores.iloc[-1] if len(valores) else np.nan
    saida = {}
    for lag in lags:
        pos = len(valores) - 1 - lag
        anterior = valores.iloc[pos] if pos >= 0 else np.nan
        saida[swap_delta_label(lag)] = (
            np.nan if pd.isna(ultimo) or pd.isna(anterior) else float(ultimo - anterior)
        )
    return saida


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

    # Fetch cambio (Yahoo Finance closing)
    cambio_yf = fetch_usdclp_closing()
    cambio_df = cambio_yf.rename(columns={"USDCLP": "cambio"})
    cambio_df = cambio_df.dropna(subset=["Data", "cambio"]).sort_values("Data").reset_index(drop=True)

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

    # Delta tables for ate2y, 5y, 10y, em PREGOES (nao dias corridos).
    # Os horizontes sao os mesmos de antes, so contados em sessao: 1, 5, 21, 32 e
    # 63 pregoes valem 1, 7, 30, 45 e 90 dias corridos. Como o df ja vem so com
    # dia util (o dropna de _fetch_swap_group derruba fim de semana e feriado),
    # andar N linhas anda exatamente N sessoes.
    delta_tables = {}
    delta_lags = SWAP_DELTA_SESSIONS

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
                table_data[participant] = {swap_delta_label(lag): np.nan for lag in delta_lags}
                continue
            table_data[participant] = _deltas_por_pregao(df_t[col], delta_lags)

        # Local Banks = -total
        col_total = f"total_{tenor_key}"
        if col_total in df_t.columns and not df_t[col_total].dropna().empty and last_date is not None:
            table_data["Local Banks"] = _deltas_por_pregao(-df_t[col_total], delta_lags)
        else:
            table_data["Local Banks"] = {swap_delta_label(lag): np.nan for lag in delta_lags}

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

    Antes do cutover (OFFSHORE_ADJ_CUTOVER): posicao offshore original
    (No residentes). A partir do cutover: offshore original + soma acumulada
    do spot liquido de nao residentes, que comeca a acumular na data do cutover.

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

    return result[
        ["Data", "Offshore_Adj", "USDCLP", "No residentes", "spot_neto"]
    ].dropna(subset=["Offshore_Adj"])


def build_weekly_legs(
    adj_df: pd.DataFrame, sessoes: int = OFFSHORE_WEEKLY_SESSIONS,
) -> pd.DataFrame:
    """Agrega as duas pernas do offshore por bloco de pregoes, em compra-de-USD.

    Blocos NAO sobrepostos de `sessoes` pregoes, ancorados no fim: o mais
    recente fecha no ultimo dado e o mais antigo cai se estiver incompleto.
    Blocos de pregao, e nao semana de calendario (W-FRI), porque a semana civil
    tem 3, 4 ou 5 pregoes dependendo de feriado, e uma barra de 3 dias ao lado
    de outra de 5 nao se compara — mesma convencao de AFP_DELTA_SESSIONS.

    Acima de zero = compra de USD. As series cruas do BCCh vem na otica do banco
    residente (positivo = cliente comprando CLP), entao as duas entram com o
    sinal invertido.

      ndf_wk  : variacao do saldo de NDF de ponta a ponta do bloco
      bcch_wk : soma do fluxo spot liquido no bloco
      net_wk  : soma das duas = variacao da posicao ajustada no bloco
    """
    d = adj_df.dropna(subset=["No residentes"]).set_index("Data").sort_index()
    n = len(d)
    if n < 2 * sessoes:
        return pd.DataFrame(columns=["Semana", "ndf_wk", "bcch_wk", "net_wk"])

    ndf, spot = -d["No residentes"], -d["spot_neto"]

    # bloco 0 = os `sessoes` pregoes mais recentes, 1 = os 5 anteriores, etc.
    bloco = pd.Series((n - 1 - np.arange(n)) // sessoes, index=d.index)
    completos = bloco.value_counts()
    bloco = bloco[bloco.map(completos) == sessoes]
    if bloco.empty:
        return pd.DataFrame(columns=["Semana", "ndf_wk", "bcch_wk", "net_wk"])

    # bloco decrescente = data crescente, para o diff andar no sentido do tempo
    ordem = sorted(bloco.unique(), reverse=True)
    fecha = ndf.loc[bloco.index].groupby(bloco).last().reindex(ordem)
    wk = pd.DataFrame({
        "Semana": pd.Series(bloco.index, index=bloco.index)
                    .groupby(bloco).last().reindex(ordem).values,
        # Ponta a ponta: o nivel no fim do bloco menos o nivel no fim do bloco
        # anterior. Por isso o bloco mais antigo sai (nao tem anterior).
        "ndf_wk": fecha.diff().values,
        "bcch_wk": spot.loc[bloco.index].groupby(bloco).sum().reindex(ordem).values,
    }).dropna(subset=["ndf_wk"])
    wk["net_wk"] = wk["ndf_wk"] + wk["bcch_wk"]
    return wk.reset_index(drop=True)


def build_offshore_corr(
    adj_df: pd.DataFrame, windows: tuple = (15, 30, 90)
) -> pd.DataFrame:
    """Correlacao movel entre as duas pernas do offshore, em nivel.

    NDF (saldo) contra spot acumulado, ambos em convencao long USD: logo
    -1 = espelho perfeito (o forward e so o hedge do spot) e +1 = as duas
    pernas somam risco. O acumulado usa a amostra inteira de proposito --
    correlacao e invariante a deslocamento constante, entao nao depende da
    ancora do ajuste e assim tem historia antes dela.
    """
    d = adj_df.set_index("Data").sort_index()
    ndf_long = -d["No residentes"]
    spot_cum = (-d["spot_neto"]).cumsum()
    out = pd.DataFrame({
        f"corr_{w}d": ndf_long.rolling(w).corr(spot_cum) for w in windows
    })
    return out.dropna(how="all").rename_axis("Data").reset_index()


def build_offshore_rolling_legs(
    adj_df: pd.DataFrame, sessoes: int, media: int = None,
) -> pd.DataFrame:
    """Janelas rolantes das duas pernas do offshore, em compra-de-USD.

    A versao rolante do `build_weekly_legs`: em vez de blocos de pregao que nao
    se sobrepoem, cada dia carrega a janela de `sessoes` pregoes que termina
    nele. Mesma leitura da aba de Fluxo AFP, e por isso delega a conta da janela
    para `build_afp_rolling_legs` — so monta antes o frame diario que ela espera.

    As series cruas do BCCh vem na otica do banco residente (positivo = cliente
    comprando CLP), entao as duas entram invertidas, como no resto da aba.

      ndf_1d    : variacao diaria do saldo de NDF (a soma na janela e o delta
                  do saldo de ponta a ponta)
      spot_bcch : fluxo spot liquido de nao residentes no dia
    """
    if adj_df.empty:
        return pd.DataFrame()

    d = adj_df.dropna(subset=["No residentes"]).set_index("Data").sort_index()
    diario = pd.DataFrame({
        "Data": d.index,
        "ndf_1d": (-d["No residentes"]).diff().values,
        "spot_bcch": (-d["spot_neto"]).values,
    })
    # O primeiro pregao nao tem dia anterior, logo nao tem variacao de saldo. Sai
    # antes da janela: se ficasse, a barra mais antiga somaria N dias de spot
    # contra N-1 de NDF, e o empilhado compararia pernas de tamanho diferente.
    return build_afp_rolling_legs(diario.iloc[1:], sessoes, media=media)


# ──────────────────────────────────────────────────────────────────────
# Colombia
# ──────────────────────────────────────────────────────────────────────
def build_colombia_data() -> dict:
    """Busca e processa dados de Colombia (USDCOP + forwards Banrep).

    Retorna dict com:
        - 'series': DataFrame com Fecha, Extranjero, FPC, RestoyReal, USDCOP
        - 'table_data': DataFrame com ultimas 5 linhas formatadas
    """
    cop_df = fetch_usdcop_closing()
    fwd_df = fetch_colombia_forwards()

    if fwd_df.empty:
        return {"series": pd.DataFrame(), "table_data": pd.DataFrame()}

    fwd_df = fwd_df.sort_values("Fecha").copy()
    fwd_df["RestoyReal"] = fwd_df["Resto"] + fwd_df["Real"]
    series = fwd_df[["Fecha", "Extranjero", "FPC", "RestoyReal"]].copy()

    # Merge with COP (Yahoo Finance closing)
    if not cop_df.empty:
        # cop_df vem com coluna "Data" do yfinance ou "Fecha" do fallback
        if "Data" in cop_df.columns and "Fecha" not in cop_df.columns:
            cop_df = cop_df.rename(columns={"Data": "Fecha"})
        series = series.merge(cop_df[["Fecha", "USDCOP"]], on="Fecha", how="left")
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


# ──────────────────────────────────────────────────────────────────────
# Fluxo AFP: NDF + spot
# ──────────────────────────────────────────────────────────────────────
# Convencao unica desta secao: acima de zero = compra de USD, abaixo de zero =
# venda de USD. Unidade MM USD. Igual a aba de setores e INVERTIDA em relacao a
# aba de offshore ajustado, que segue em compra-de-CLP.
#
#   NDF            a serie crua do BCCh e o nivel visto pelo banco residente:
#                  positivo = AFP net short USD. Aumentar o short e vender mais
#                  USD a termo, ou seja comprar CLP -> +delta do nivel.
#   spot observado a serie crua do BCCh e fluxo visto pelo banco residente:
#                  positivo = banco compra USD do AFP = AFP vende USD -> -valor.


# Janela curta da aba: cinco pregoes, nao cinco dias corridos.
AFP_DELTA_SESSIONS = 5


def build_afp_spot_flow(dados: pd.DataFrame) -> pd.DataFrame:
    """Monta as duas pernas do fluxo dos fundos de pensao, em compra-de-USD.

    NDF e a variacao do saldo forward do setor 42; spot e o fluxo spot que o
    BCCh observa no mesmo setor. As duas series cruas do BCCh vem na otica do
    banco residente, em que positivo = o AFP compra CLP, entao entram com o
    sinal invertido. O nivel do saldo tambem inverte, e nao so os fluxos, para a
    aba inteira ter uma convencao so: o saldo aparece aqui como -33.498 (net
    short USD) e na aba Fundos de Pensao como +33.498, o sinal cru do BCCh.
    """
    # Perna de spot observado pelo BCCh.
    spot_raw = fetch_bcentral_series(SERIES_SPOT_PENSION)
    spot_raw["Data"] = pd.to_datetime(spot_raw["date_str"], dayfirst=True, errors="coerce")
    spot_raw = spot_raw.dropna(subset=["Data", "value"])
    if spot_raw.empty:
        return pd.DataFrame()
    spot_bcch = -spot_raw.set_index("Data")["value"]

    ndf = dados[["Data", SERIES_NDF_PENSION_NAME, "USDCLP"]].dropna(
        subset=[SERIES_NDF_PENSION_NAME]
    ).set_index("Data").sort_index()
    nivel = -ndf[SERIES_NDF_PENSION_NAME]

    # Delta de 5 PREGOES, nao de 5 dias corridos. A serie so tem dia util, entao
    # diff(5) anda exatamente cinco sessoes. Com 5 dias corridos a janela seria
    # erratica: cobriria 3 pregoes na segunda, terca e quarta, 4 na quinta e 5 so
    # na sexta. (7 dias corridos davam 5 pregoes em 869 dos 1046 dias, mas o
    # deslocamento por sessao e exato em todos.)
    idx_ndf = pd.DataFrame({
        "ndf_level": nivel,
        "ndf_1d": nivel.diff(),
        "ndf_5d": nivel.diff(AFP_DELTA_SESSIONS),
        "USDCLP": ndf["USDCLP"],
    })

    # Indice uniao: as duas fontes tem defasagem diferente e o painel precisa
    # mostrar o dado mais fresco de cada uma, nao truncar as duas na mais atrasada.
    ilist = idx_ndf.index.union(spot_bcch.index).sort_values()
    ilist = ilist[ilist >= spot_bcch.index.min()]

    out = idx_ndf.reindex(ilist)
    out["spot_bcch"] = spot_bcch.reindex(ilist)
    # Mesma regra da coluna Net da tabela (min_count=1), para grafico e tabela
    # nao discordarem em dia que so uma das pernas publicou.
    out["net_1d"] = out[["ndf_1d", "spot_bcch"]].sum(axis=1, min_count=1)
    return out.rename_axis("Data").reset_index()


def build_afp_5d_legs(afp_df: pd.DataFrame) -> dict:
    """Acumulado dos ultimos 5 pregoes de cada perna.

    A janela termina na ultima data em que as duas pernas existem, porque as
    fontes tem defasagem diferente (o BCCh publica o spot e o saldo de NDF em
    dias diferentes). Essa ancora pode ser anterior ao ultimo dado da aba de
    Fundos de Pensao, entao o grafico imprime a data ao lado da barra de NDF.
    """
    if afp_df.empty:
        return {}

    legs = ["ndf_5d", "spot_bcch"]
    d = afp_df.set_index("Data").sort_index()

    common = d[legs].dropna()
    if common.empty:
        return {}
    anchor = common.index.max()

    # As cinco ultimas sessoes ate a ancora. Bate com ndf_5d por construcao: a
    # variacao de nivel em cinco sessoes e a soma das cinco variacoes diarias.
    window = d.loc[:anchor].tail(AFP_DELTA_SESSIONS)
    return {
        # ndf_5d ja e a variacao acumulada nas cinco sessoes: pegar o ponto da
        # ancora, nao somar, senao conta o mesmo movimento cinco vezes.
        "ndf": d.loc[anchor, "ndf_5d"],
        "spot_bcch": window["spot_bcch"].sum(),
        "anchor": anchor,
        "start": window.index.min() if len(window) else anchor,
        "last_dates": {
            "NDF": d["ndf_5d"].last_valid_index(),
            "Spot BCCh": d["spot_bcch"].last_valid_index(),
        },
    }


def build_afp_levels(afp_df: pd.DataFrame) -> pd.DataFrame:
    """Os dois niveis rebaseados na primeira data, e o residuo entre eles.

    Ja em compra-de-USD, como o resto da aba.

    O saldo de NDF e um estoque de verdade, mas o spot so existe como fluxo e
    vira nivel por soma acumulada, cujo zero e a data em que a serie do BCCh
    comeca — arbitrario. Somar um com o outro cru misturaria uma escala absoluta
    com uma relativa, entao o NDF tambem entra rebaseado: as duas passam a
    compartilhar o mesmo zero explicito e o painel le "variacao da posicao desde
    a ancora", nao "posicao".

    Rebasear e deslocamento aditivo puro, entao trocar a ancora muda o nivel das
    tres series por uma constante e nao muda a forma de nenhuma.

    `residuo` = ndf + spot, a parte comprada de USD que o forward nao cobriu.
    Colado no zero = hedge apertado.
    """
    if afp_df.empty:
        return pd.DataFrame()

    d = afp_df.set_index("Data").sort_index()
    nivel = d["ndf_level"].dropna()
    if nivel.empty:
        return pd.DataFrame()

    out = pd.DataFrame({
        "ndf": nivel - nivel.iloc[0],
        "spot": d["spot_bcch"].fillna(0.0).cumsum(),
    })
    out["residuo"] = out["ndf"] + out["spot"]
    return out.dropna(how="all").rename_axis("Data").reset_index()


def build_afp_rolling_legs(
    afp_df: pd.DataFrame, sessoes: int, media: int = None,
) -> pd.DataFrame:
    """Soma movel de `sessoes` pregoes de cada perna, opcionalmente suavizada.

    Versao diaria e rolante do semanal: em vez de fechar a semana na sexta, cada
    dia carrega a janela que termina nele. Some o mesmo movimento em dias
    consecutivos, entao le-se como nivel de fluxo e nao como barras
    independentes — o semanal continua sendo o de barras que nao se sobrepoem.

    Para a perna de NDF a soma das variacoes diarias na janela e exatamente a
    variacao do nivel na janela, entao "soma movel" e "delta rolante" sao a mesma
    coisa aqui.

    `media` aplica ainda uma media movel de N dias por cima, para tirar o ruido.

    Devolve os mesmos nomes de coluna do semanal (ndf_wk, bcch_wk, net_wk) para
    reaproveitar o mesmo grafico.
    """
    if afp_df.empty:
        return pd.DataFrame()

    d = afp_df.set_index("Data").sort_index()
    out = pd.DataFrame({
        "ndf_wk": d["ndf_1d"].rolling(sessoes, min_periods=sessoes).sum(),
        "bcch_wk": d["spot_bcch"].rolling(sessoes, min_periods=sessoes).sum(),
    })
    if media:
        out = out.rolling(media, min_periods=media).mean()
    out["net_wk"] = out[["ndf_wk", "bcch_wk"]].sum(axis=1, min_count=2)
    return out.dropna(how="all").rename_axis("Data").reset_index()


def build_afp_weekly_legs(afp_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega as duas pernas por semana (sexta a sexta), em compra-de-USD."""
    if afp_df.empty:
        return pd.DataFrame()

    d = afp_df.set_index("Data").sort_index()
    # ndf_1d e variacao de nivel dia a dia, entao somar a semana devolve a
    # variacao de ponta a ponta do saldo.
    wk = pd.DataFrame({
        "ndf_wk": d["ndf_1d"].resample("W-FRI").sum(min_count=1),
        "bcch_wk": d["spot_bcch"].resample("W-FRI").sum(min_count=1),
    })
    wk["net_wk"] = wk[["ndf_wk", "bcch_wk"]].sum(axis=1, min_count=1)

    return wk.dropna(how="all").rename_axis("Semana").reset_index()


# ──────────────────────────────────────────────────────────────────────
# Todos os setores: NDF + spot
# ──────────────────────────────────────────────────────────────────────
# ATENCAO: esta aba usa a convencao INVERTIDA em relacao as outras. Aqui acima de
# zero = compra de USD (venda de CLP); nas abas de fundos de pensao e offshore
# ajustado, acima de zero = compra de CLP.
#
# As series cruas do BCCh vem na otica do banco residente, em que positivo =
# cliente comprando CLP, entao tudo aqui entra com o sinal invertido. Inverte-se
# tambem o nivel do saldo, e nao so os fluxos: uma tabela com o fluxo num sinal e
# o estoque no outro seria pior que a diferenca entre abas, que a nota da aba
# explica. Logo o saldo de NDF dos fundos de pensao aparece aqui como -33.498
# (net short USD) e na aba deles como +33.498.
def build_all_sectors_flow(dados: pd.DataFrame) -> pd.DataFrame:
    """Diario, por setor: nivel de NDF, variacao do NDF, spot e net, em compra-de-USD.

    Retorna formato longo, uma linha por (Data, setor), para as tabelas e o
    grafico agruparem por setor sem precisar decorar nomes de coluna.
    """
    nomes = list(SECTOR_SPOT_SERIES)
    spot_matrix = fetch_bcentral_matrix([SECTOR_SPOT_SERIES[n] for n in nomes])
    if spot_matrix.empty:
        return pd.DataFrame()

    spot_matrix["Data"] = pd.to_datetime(
        spot_matrix["date_str"], dayfirst=True, errors="coerce"
    )
    spot = spot_matrix.dropna(subset=["Data"]).set_index("Data").sort_index()
    spot = spot[[f"V{i}" for i in range(len(nomes))]]
    spot.columns = nomes

    ndf = dados.set_index("Data").sort_index()

    partes = []
    for nome in nomes:
        if nome not in ndf.columns:
            logger.warning("Setor %s sem coluna de NDF, pulando", nome)
            continue
        nivel = ndf[nome].dropna()
        # Variacao dia a dia do saldo: somar a janela devolve a variacao de ponta
        # a ponta, do mesmo jeito que as outras abas fazem.
        parte = pd.DataFrame({
            "ndf_level": -nivel,
            "ndf_1d": -nivel.diff(),
            "spot": -spot[nome],
        })
        parte["net_1d"] = parte[["ndf_1d", "spot"]].sum(axis=1, min_count=1)
        parte["setor"] = nome
        partes.append(parte.rename_axis("Data").reset_index())

    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True).sort_values(["setor", "Data"])


def build_sector_window_table(
    long_df: pd.DataFrame, sessoes: int
) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Acumulado dos ultimos `sessoes` pregoes por setor: NDF, spot e net.

    A janela conta PREGOES, nao dias corridos: pega as N ultimas datas com dado.
    Assim tem sempre o mesmo numero de sessoes, independente de feriado ou de em
    que dia da semana o build roda. Mesma convencao de AFP_DELTA_SESSIONS e dos
    deltas de 5/21 pregoes das outras abas.

    A janela fecha na ultima data com dado e vale para todos os setores, senao a
    tabela somaria periodos diferentes e a linha de total nao fecharia.
    Retorna (tabela indexada por setor, inicio, fim).
    """
    if long_df.empty:
        return pd.DataFrame(), None, None

    datas = (
        long_df.dropna(subset=["net_1d"])["Data"].drop_duplicates().sort_values()
    )
    if datas.empty:
        return pd.DataFrame(), None, None
    janela_datas = datas.tail(sessoes)
    fim = janela_datas.iloc[-1]
    janela = long_df[long_df["Data"].isin(set(janela_datas))]

    tab = janela.groupby("setor")[["ndf_1d", "spot"]].sum(min_count=1)
    tab["net"] = tab[["ndf_1d", "spot"]].sum(axis=1, min_count=1)
    tab = tab.rename(columns={"ndf_1d": "ndf", "spot": "spot"})

    # Nivel de NDF do fim da janela, para a tabela dar o contexto do estoque.
    nivel = (
        long_df[long_df["Data"] == fim].set_index("setor")["ndf_level"]
    )
    tab["ndf_level"] = nivel

    ordem = [s for s in SECTOR_TABLE_ORDER if s in tab.index]
    primeira = janela["Data"].min() if len(janela) else fim
    return tab.loc[ordem], primeira, fim


def build_sector_weekly(long_df: pd.DataFrame, col: str = "net_1d") -> pd.DataFrame:
    """Agregado semanal (sexta a sexta) de uma perna por setor, mais o total.

    `col` escolhe a perna: "ndf_1d", "spot" ou "net_1d". Os tres graficos
    empilhados da aba saem desta funcao com a mesma forma, entao o de NDF, o de
    spot e o de net sao comparaveis barra a barra.

    Como setores entram so as folhas e o offshore: os agregados intermediarios
    sao soma delas e virariam barra duplicada. O total entra como serie propria.
    """
    if long_df.empty:
        return pd.DataFrame()

    d = long_df[long_df["setor"].isin(SECTOR_CHART_LINES)]
    wk = (
        d.set_index("Data")
        .groupby("setor")[col]
        .resample("W-FRI")
        .sum(min_count=1)
        .unstack("setor")
    )
    cols = [c for c in SECTOR_CHART_LINES if c in wk.columns]
    wk = wk[cols].copy()
    # O total sai da soma das proprias barras do grafico, nao da serie de total
    # publicada: assim a linha preta e por construcao o que se ve somando as
    # outras. As duas batem (diferenca 0,00), entao nao se perde nada.
    # min_count=len(cols): so existe na semana em que todos os setores existem.
    wk[SECTOR_NET_LINE] = wk.sum(axis=1, min_count=len(cols))
    return wk.dropna(how="all").rename_axis("Semana").reset_index()
