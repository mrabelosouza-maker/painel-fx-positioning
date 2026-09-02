"""Metricas fora de amostra e teste de plateau."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from estudos.afp_leading.modelo import Spec
from estudos.afp_leading.avaliacao import (
    previsao_oos, r2_oos, avaliar, tem_plateau,
)
from tests.afp_leading.test_modelo import painel_sintetico


def test_r2_oos_zero_quando_modelo_iguala_a_media():
    """Previsao identica a media expansivel nao ganha nada da referencia.

    Com y = [1,2,3,4] a media expansivel defasada e [nan, 1, 1.5, 2]. A primeira
    linha nao tem referencia e sai da conta, entao o 99 abaixo e ignorado de
    proposito — se ele influenciasse o resultado, a referencia estaria sendo
    zerada em vez de descartada.
    """
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2_oos(y, np.array([99.0, 1.0, 1.5, 2.0])) == pytest.approx(0.0)


def test_r2_oos_positivo_quando_modelo_acerta_mais():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2_oos(y, y) == pytest.approx(1.0)


def test_r2_oos_negativo_quando_modelo_erra_mais_que_a_media():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2_oos(y, np.array([50.0, 50.0, 50.0, 50.0])) < 0


def test_r2_oos_com_referencia_externa_difere_da_recalculada():
    """Recalcular a referencia sobre amostra ja truncada infla o R2 OOS.

    Simula o que avaliar() fazia antes da correcao: corta as primeiras k
    observacoes (como um dropna que descarta linhas sem previsao por falta de
    treino) e so entao forma a media expansivel, que comeca com 1 observacao
    ruidosissima em vez de ja ter k de historia. A versao correta forma a
    media expansivel sobre a serie COMPLETA (antes do corte) e so depois
    fatia — essa e a que deve ser passada como "referencia".

    O resultado tem que ser diferente, e a versao com referencia externa
    (correta) tem que ser a MENOR das duas: recalcular do zero infla o SSE de
    referencia, e portanto infla o R2 OOS a favor do modelo.
    """
    rng = np.random.default_rng(42)
    n, k = 300, 250
    realizado_full = rng.normal(50.0, 5.0, n)
    previsto_full = np.full(n, np.nan)
    previsto_full[k:] = realizado_full[k:] + rng.normal(0, 3.0, n - k)

    realizado_trunc = realizado_full[k:]
    previsto_trunc = previsto_full[k:]

    r2_recalculado = r2_oos(realizado_trunc, previsto_trunc)

    referencia_completa = (
        pd.Series(realizado_full).expanding().mean().shift(1).to_numpy()
    )
    r2_com_referencia_externa = r2_oos(
        realizado_trunc, previsto_trunc, referencia=referencia_completa[k:]
    )

    assert r2_com_referencia_externa != pytest.approx(r2_recalculado)
    assert r2_com_referencia_externa < r2_recalculado


def test_previsao_oos_nao_usa_o_futuro():
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    p1 = previsao_oos(painel, spec)

    corrompido = painel.copy()
    corrompido.loc[600:, "net_1d"] = corrompido.loc[600:, "net_1d"] * -5.0
    p2 = previsao_oos(corrompido, spec)

    corte = 500
    np.testing.assert_allclose(
        p1.iloc[:corte]["previsto"].to_numpy(),
        p2.iloc[:corte]["previsto"].to_numpy(),
        equal_nan=True,
    )

    # controle positivo: a corrupcao precisa ter mudado alguma coisa depois
    # do ponto 600. sem isso, uma implementacao quebrada (que devolvesse so
    # NaN, ou que ignorasse o painel de entrada) passaria no assert acima.
    depois1 = p1.iloc[600:]["previsto"].to_numpy()
    depois2 = p2.iloc[600:]["previsto"].to_numpy()
    ambos_validos = ~(np.isnan(depois1) | np.isnan(depois2))
    assert ambos_validos.sum() > 0, "nenhuma previsao valida apos a corrupcao"
    diferenca = np.abs(depois1[ambos_validos] - depois2[ambos_validos])
    assert (diferenca > 1.0).any(), "corrupcao nao mudou nenhuma previsao depois de 600"


def test_previsao_oos_nao_usa_a_propria_observacao():
    """Ataca a fronteira exata: previsto em c nao pode ver a linha c.

    Corrompendo o painel so na linha c, o treino da linha c usa indices < c
    (nao muda, ja que sel[i:] = False exclui a propria observacao), enquanto
    o treino da linha c+1 usa indices < c+1, que ja inclui a linha c
    corrompida (muda). Esse par distingue sel[i:] (correto) de um vazamento
    estreito como sel[i+1:], que vazaria so a propria observacao e nao seria
    detectado pelo teste que corrompe a partir de 600 e compara ate 500 (o
    efeito apareceria perto de 600, onde aquele teste nunca olha).
    """
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    p1 = previsao_oos(painel, spec)

    c = 600  # bem depois do min_treino=252
    corrompido = painel.copy()
    corrompido.loc[c, "net_1d"] = corrompido.loc[c, "net_1d"] * -5.0
    p2 = previsao_oos(corrompido, spec)

    previsto_c_original = p1.iloc[c]["previsto"]
    previsto_c_corrompido = p2.iloc[c]["previsto"]
    previsto_c1_original = p1.iloc[c + 1]["previsto"]
    previsto_c1_corrompido = p2.iloc[c + 1]["previsto"]

    assert not np.isnan(previsto_c_original)
    assert not np.isnan(previsto_c_corrompido)
    assert not np.isnan(previsto_c1_original)
    assert not np.isnan(previsto_c1_corrompido)

    # linha c: treino vai so ate c-1, entao a corrupcao na propria linha c
    # nao pode ter mudado nada.
    assert previsto_c_original == pytest.approx(previsto_c_corrompido, abs=1e-6)

    # linha c+1: treino ja inclui a linha c, que esta corrompida, entao a
    # previsao tem que ter mudado de forma material.
    assert abs(previsto_c1_original - previsto_c1_corrompido) > 0.5


def test_avaliar_recupera_relacao_forte():
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0, ruido=40.0)
    a = avaliar(painel, Spec("net_1d", "r_MXWO", "pontual", 3))

    assert a["r2_oos"] > 0.10
    assert a["corr"] > 0.5
    assert a["mae_usd_mm"] > 0
    assert set(a["metades"]) == {"primeira", "segunda"}
    assert a["metades"]["primeira"]["beta"] < 0
    assert a["metades"]["segunda"]["beta"] < 0


def test_avaliar_nao_encontra_relacao_em_ruido_puro():
    painel = painel_sintetico(n=900, beta_verdadeiro=0.0, ruido=40.0)
    a = avaliar(painel, Spec("net_1d", "r_MXWO", "pontual", 3))
    assert a["r2_oos"] < 0.05


def _tabela(betas_r2):
    """betas_r2: lista de (n, beta, r2_oos) para a familia pontual."""
    return pd.DataFrame([
        {"tipo": "pontual", "n": n, "beta": b, "r2_oos": r}
        for n, b, r in betas_r2
    ])


def test_plateau_aceita_vizinhos_vivos():
    tab = _tabela([(2, -25000, 0.12), (3, -30000, 0.20), (4, -22000, 0.11)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert ok, msg


def test_plateau_rejeita_pico_isolado():
    tab = _tabela([(2, -1000, 0.01), (3, -30000, 0.20), (4, 500, 0.00)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert not ok
    assert "vizinho" in msg.lower()


def test_plateau_rejeita_vizinho_de_sinal_trocado():
    tab = _tabela([(2, 26000, 0.15), (3, -30000, 0.20), (4, -28000, 0.18)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert not ok


def test_plateau_rejeita_vencedor_com_r2_negativo():
    """r2_alvo <= 0 nao tem o que sustentar como plateau, mesmo com vizinhos vivos.

    O criterio a["r2_oos"] < r2_alvo / 2 so faz sentido com r2_alvo positivo.
    Com o vencedor negativo, vizinhos tambem negativos (mas "menos negativos")
    passariam nesse criterio sem que nenhuma das especificacoes tenha poder
    preditivo algum — a guarda tem que barrar isso antes de olhar vizinhos.
    """
    tab = _tabela([(2, -25000, -0.05), (3, -30000, -0.02), (4, -22000, -0.01)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert not ok
    assert "preditivo" in msg.lower()
