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
