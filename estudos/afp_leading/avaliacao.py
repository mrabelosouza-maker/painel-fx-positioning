"""Metricas fora de amostra e a defesa contra a busca por especificacao."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from .modelo import Spec, serie_preditora


def r2_oos(
    realizado: np.ndarray,
    previsto: np.ndarray,
    referencia: np.ndarray | None = None,
) -> float:
    """R2 fora de amostra a la Campbell-Thompson.

    1 - SSE_modelo / SSE_referencia, com a referencia sendo a media EXPANSIVEL
    do proprio fluxo — o chute honesto de quem so conhece o passado. Nao e a
    media da amostra cheia, que ja seria look-ahead. Pode ser negativo: e o que
    acontece quando o modelo erra mais do que o chute da media.

    referencia: media expansivel defasada ja pronta, opcional. Quando None
    (comportamento padrao), e recalculada aqui em cima do proprio "realizado"
    recebido. Isso so e seguro se "realizado" for a serie completa do fluxo:
    se ja chegou truncada (por exemplo depois de um dropna que descartou as
    observacoes iniciais sem previsao por falta de treino), recalcular do zero
    perde a historia real do fluxo — a referencia comeca com 1 observacao
    ruidosissima em vez de ja ter, digamos, 252 de historia — o que infla o
    SSE de referencia e portanto infla o R2 OOS a favor do modelo. Nesse caso
    quem chama deve calcular a referencia sobre a serie completa, antes do
    corte, e passar pronta aqui.
    """
    y = np.asarray(realizado, dtype=float)
    p = np.asarray(previsto, dtype=float)

    if referencia is None:
        ok = ~(np.isnan(y) | np.isnan(p))
        y, p = y[ok], p[ok]
        if len(y) < 2:
            return float("nan")
        ref = pd.Series(y).expanding().mean().shift(1).to_numpy()
    else:
        ref = np.asarray(referencia, dtype=float)
        ok = ~(np.isnan(y) | np.isnan(p))
        y, p, ref = y[ok], p[ok], ref[ok]
        if len(y) < 2:
            return float("nan")

    # A referencia nao existe na primeira observacao: nao ha historia para formar
    # media. A linha sai das duas somas, em vez de virar zero — zero inflaria o
    # SSE de referencia e faria o R2 OOS parecer melhor do que e.
    com_ref = ~np.isnan(ref)
    y, p, ref = y[com_ref], p[com_ref], ref[com_ref]
    if len(y) < 1:
        return float("nan")

    sse_modelo = np.nansum((y - p) ** 2)
    sse_ref = np.nansum((y - ref) ** 2)
    if sse_ref == 0:
        return float("nan")
    return float(1 - sse_modelo / sse_ref)


def previsao_oos(painel: pd.DataFrame, spec: Spec, min_treino: int = 252) -> pd.DataFrame:
    """Previsao em t com coeficientes ajustados so ate t-1.

    Reajusta intercepto e beta a cada passo, em janela expansivel. E lento (uma
    OLS por dia), mas a amostra tem ~1.000 linhas e a clareza vale mais que o
    tempo aqui.
    """
    x = serie_preditora(painel, spec).to_numpy()
    y = painel[spec.alvo].to_numpy()
    valido = ~(np.isnan(x) | np.isnan(y))

    previsto = np.full(len(painel), np.nan)
    for i in range(len(painel)):
        if not valido[i]:
            continue
        sel = valido.copy()
        sel[i:] = False  # so o passado estrito
        if sel.sum() < min_treino:
            continue
        m = sm.OLS(y[sel], sm.add_constant(x[sel])).fit()
        previsto[i] = float(m.params[0] + m.params[1] * x[i])

    return pd.DataFrame({
        "Data": painel["Data"].to_numpy(),
        "realizado": np.where(valido, y, np.nan),
        "previsto": previsto,
    })


def _ols_simples(painel: pd.DataFrame, spec: Spec) -> dict:
    x = serie_preditora(painel, spec)
    d = pd.DataFrame({"y": painel[spec.alvo], "x": x}).dropna()
    if len(d) < 30:
        return {"beta": float("nan"), "tstat": float("nan"), "r2": float("nan"), "nobs": len(d)}
    m = sm.OLS(d["y"], sm.add_constant(d["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    return {
        "beta": float(m.params.iloc[1]),
        "tstat": float(m.tvalues.iloc[1]),
        "r2": float(m.rsquared),
        "nobs": len(d),
    }


def avaliar(painel: pd.DataFrame, spec: Spec, min_treino: int = 252) -> dict:
    """R2 fora de amostra, correlacao, erro em USD mm e split de amostra.

    O erro em USD mm esta aqui de proposito ao lado do R2: o R2 diz se ha
    relacao, o erro em USD mm diz se ela e grande o bastante para significar
    alguma coisa numa mesa.
    """
    p_full = previsao_oos(painel, spec, min_treino=min_treino)

    # Referencia expansivel calculada sobre o historico REAL completo do fluxo,
    # antes do dropna abaixo. O dropna remove as primeiras ~min_treino linhas
    # (onde "previsto" ainda e NaN por falta de treino), mas essas linhas tem
    # fluxo realizado de verdade — descarta-las antes de formar a media
    # expansivel jogaria fora justamente a historia que torna a referencia
    # honesta. Ver docstring de r2_oos.
    ref_full = pd.Series(p_full["realizado"]).expanding().mean().shift(1).to_numpy()

    p = p_full.dropna(subset=["realizado", "previsto"])
    ref = ref_full[p.index.to_numpy()]

    meio = len(painel) // 2
    metades = {
        "primeira": _ols_simples(painel.iloc[:meio], spec),
        "segunda": _ols_simples(painel.iloc[meio:], spec),
    }

    if p.empty:
        return {"r2_oos": float("nan"), "corr": float("nan"),
                "mae_usd_mm": float("nan"), "nobs": 0, "metades": metades}

    return {
        "r2_oos": r2_oos(p["realizado"].to_numpy(), p["previsto"].to_numpy(), referencia=ref),
        "corr": float(p["realizado"].corr(p["previsto"])),
        "mae_usd_mm": float((p["realizado"] - p["previsto"]).abs().mean()),
        "nobs": len(p),
        "metades": metades,
    }


def tem_plateau(tabela: pd.DataFrame, tipo: str, n: int, aval_por_spec: dict) -> tuple[bool, str]:
    """A vencedora nao pode ser um pico isolado na grade.

    Um rebalanceamento real produz estrutura de defasagem suave: se o AFP ajusta
    o hedge ao longo de alguns dias, k=3 funcionar implica k=2 e k=4 funcionarem.
    Vencedor cercado de vizinhos mortos e a assinatura do ruido, e e exatamente o
    que a busca por especificacao produz numa amostra de 1.054 observacoes.

    Criterio: cada vizinho que existe na grade precisa ter beta do mesmo sinal e
    r2_oos de pelo menos metade do vencedor.
    """
    alvo = aval_por_spec.get((tipo, n))
    if alvo is None:
        return False, f"especificacao ({tipo}, {n}) sem avaliacao"

    r2_alvo = alvo["r2_oos"]
    if r2_alvo <= 0:
        return False, (
            f"({tipo}, {n}) tem R2 OOS do vencedor de {r2_alvo:.3f} (<= 0) — "
            "sem poder preditivo positivo nao ha o que a estrutura de plateau "
            "possa sustentar. Isso nao e falha de plateau, e ausencia de sinal."
        )
    sinal = np.sign(alvo["beta"])
    existentes = set(tabela[tabela["tipo"] == tipo]["n"].tolist())

    vizinhos = [v for v in (n - 1, n + 1) if v in existentes]
    if not vizinhos:
        return False, f"({tipo}, {n}) nao tem vizinho na grade para sustentar plateau"

    for v in vizinhos:
        a = aval_por_spec.get((tipo, v))
        if a is None:
            return False, f"vizinho ({tipo}, {v}) sem avaliacao"
        if np.sign(a["beta"]) != sinal:
            return False, (
                f"vizinho ({tipo}, {v}) tem beta de sinal oposto "
                f"({a['beta']:,.0f} vs {alvo['beta']:,.0f})"
            )
        if a["r2_oos"] < r2_alvo / 2:
            return False, (
                f"vizinho ({tipo}, {v}) tem R2 OOS {a['r2_oos']:.3f}, "
                f"menos da metade do vencedor ({r2_alvo:.3f}) — pico isolado"
            )

    return True, f"plateau confirmado com os vizinhos {vizinhos}"
