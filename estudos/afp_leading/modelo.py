"""Estrutura de defasagem entre bolsa global e fluxo AFP.

Convencao de unidades, que faz o beta significar alguma coisa: fluxo em USD
milhoes, retorno logaritmico FRACIONARIO (0,01 = 1%). Com isso o modelo
    fluxo = a + beta * r
tem beta = -h*A, onde h e a razao de hedge e A a carteira externa em USD mm.
Bolsa sobe -> carteira externa vale mais -> o AFP vende USD a termo -> fluxo
negativo na convencao de compra-de-USD, logo beta negativo.
"""
from collections import namedtuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

Spec = namedtuple("Spec", ["alvo", "preditor", "tipo", "n"])

KS_PADRAO = range(0, 11)
WS_PADRAO = range(1, 22)


def serie_preditora(painel: pd.DataFrame, spec: Spec) -> pd.Series:
    """O X de uma especificacao, sempre so com informacao anterior a t.

    pontual k   -> r(t-k)
    acumulada w -> soma de r(t-w) ate r(t-1); o shift(1) antes do rolling
                   garante que r(t) nunca entra.
    """
    r = painel[spec.preditor]
    if spec.tipo == "pontual":
        return r.shift(spec.n)
    if spec.tipo == "acumulada":
        return r.shift(1).rolling(spec.n).sum()
    raise ValueError(f"tipo desconhecido: {spec.tipo}")


def _ajustar(painel: pd.DataFrame, spec: Spec):
    """OLS com erro-padrao Newey-West. Devolve (resultado, n_obs) ou (None, 0).

    A defasagem do Newey-West acompanha a janela: nas acumuladas as observacoes
    se sobrepoem e os residuos sao autocorrelacionados por construcao.
    """
    x = serie_preditora(painel, spec)
    y = painel[spec.alvo]
    d = pd.DataFrame({"y": y, "x": x}).dropna()
    if len(d) < 30:
        return None, len(d)
    maxlags = max(1, spec.n if spec.tipo == "acumulada" else 1)
    m = sm.OLS(d["y"], sm.add_constant(d["x"])).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags}
    )
    return m, len(d)


def estrutura_defasagem(
    painel: pd.DataFrame,
    alvo: str,
    preditor: str,
    ks=KS_PADRAO,
    ws=WS_PADRAO,
) -> pd.DataFrame:
    """Varre as duas familias de especificacao. Uma linha por especificacao.

    k = 0 entra na tabela mas sai marcado como nao utilizavel: o MXWO fecha
    depois do mercado cambial chileno, entao o retorno do mesmo dia nao estaria
    disponivel a tempo. Serve so como referencia de quanto do fluxo e
    contemporaneo.
    """
    linhas = []
    grade = [("pontual", k) for k in ks] + [("acumulada", w) for w in ws]

    for tipo, n in grade:
        spec = Spec(alvo, preditor, tipo, n)
        m, nobs = _ajustar(painel, spec)
        if m is None:
            continue
        beta = float(m.params.iloc[1])
        se = float(m.bse.iloc[1])
        linhas.append({
            "tipo": tipo,
            "n": n,
            "beta": beta,
            "se": se,
            "tstat": float(m.tvalues.iloc[1]),
            "r2": float(m.rsquared),
            "nobs": nobs,
            "utilizavel": tipo == "acumulada" or n >= 1,
            "h_a_bi": -beta / 1000.0,
        })

    return pd.DataFrame(linhas)
