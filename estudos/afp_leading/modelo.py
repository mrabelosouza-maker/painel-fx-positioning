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


# Faixa de exposicao hedgeada implicita (h*A) aceitavel, em USD bilhoes.
# Checagem de ordem de grandeza, nao de precisao: a carteira externa do AFP e da
# ordem de dezenas de bilhoes e a razao de hedge historicamente varia numa faixa
# larga. Se h*A cair perto de qualquer borda, confrontar com o ativo externo
# publicado pela Superintendencia de Pensiones antes de seguir.
FAIXA_H_A_BI = (5.0, 90.0)


def beta_movel(
    painel: pd.DataFrame,
    spec: Spec,
    janela: int | None = None,
    min_treino: int = 252,
) -> pd.DataFrame:
    """Beta estimado so com dado anterior a cada data.

    janela=None  -> expansivel (toda a historia ate t-1)
    janela=252   -> movel de 252 observacoes terminando em t-1

    O beta na linha i NUNCA usa a observacao i nem nenhuma posterior: e esse
    beta que a fase 2 usaria para prever, e um beta contaminado pelo futuro
    inventaria performance.
    """
    x = serie_preditora(painel, spec).to_numpy()
    y = painel[spec.alvo].to_numpy()
    valido = ~(np.isnan(x) | np.isnan(y))

    betas = np.full(len(painel), np.nan)
    for i in range(len(painel)):
        ini = 0 if janela is None else max(0, i - janela)
        sel = valido.copy()
        sel[:ini] = False
        sel[i:] = False  # exclui a propria observacao e todo o futuro
        if sel.sum() < min_treino:
            continue
        xi, yi = x[sel], y[sel]
        m = sm.OLS(yi, sm.add_constant(xi)).fit()
        betas[i] = float(m.params[1])

    return pd.DataFrame({"Data": painel["Data"].to_numpy(), "beta": betas})


def portao_sanidade(beta: float, faixa=FAIXA_H_A_BI) -> tuple[bool, str]:
    """Checa se o beta e compativel com o mecanismo antes de gastar o resto.

    Duas condicoes: sinal negativo (bolsa sobe -> AFP vende USD a termo) e
    exposicao hedgeada implicita de ordem de grandeza plausivel.
    """
    if not np.isfinite(beta):
        return False, "beta nao finito"
    if beta >= 0:
        return False, (
            f"beta positivo ({beta:,.0f}): bolsa subindo com o AFP comprando USD "
            "contraria o mecanismo de hedge. A hipotese esta errada, nao o ajuste."
        )
    h_a = -beta / 1000.0
    lo, hi = faixa
    if not (lo <= h_a <= hi):
        return False, (
            f"exposicao hedgeada implicita de USD {h_a:,.1f} bi fora da faixa "
            f"[{lo:,.0f}, {hi:,.0f}] bi"
        )
    return True, f"beta {beta:,.0f} -> h*A implicito de USD {h_a:,.1f} bi"
