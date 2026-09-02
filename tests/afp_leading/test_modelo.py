"""Recuperacao de beta conhecido e portao de sanidade."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from estudos.afp_leading.modelo import Spec, serie_preditora, estrutura_defasagem


def painel_sintetico(n=800, k_verdadeiro=3, beta_verdadeiro=-30000.0, ruido=40.0, seed=7):
    """Fluxo gerado por beta * retorno defasado de k dias, mais ruido branco.

    beta = -30000 significa que 1% de bolsa move 300 USD mm de hedge, e uma
    exposicao hedgeada implicita de USD 30 bi -- dentro da faixa plausivel.
    """
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 0.01, n)
    fluxo = beta_verdadeiro * np.roll(r, k_verdadeiro) + rng.normal(0, ruido, n)
    fluxo[:k_verdadeiro] = np.nan
    return pd.DataFrame({
        "Data": pd.bdate_range("2022-06-01", periods=n),
        "net_1d": fluxo,
        "ndf_1d": fluxo,
        "r_MXWO": r,
    }).dropna().reset_index(drop=True)


def test_serie_preditora_pontual_desloca_k_dias():
    painel = pd.DataFrame({
        "Data": pd.bdate_range("2024-01-01", periods=5),
        "r_MXWO": [0.01, 0.02, 0.03, 0.04, 0.05],
    })
    s = serie_preditora(painel, Spec("net_1d", "r_MXWO", "pontual", 2))
    assert np.isnan(s.iloc[0]) and np.isnan(s.iloc[1])
    assert s.iloc[2] == pytest.approx(0.01)
    assert s.iloc[4] == pytest.approx(0.03)


def test_serie_preditora_acumulada_nunca_inclui_o_dia():
    """Janela w=2 em t soma r(t-2) e r(t-1); r(t) fica de fora."""
    painel = pd.DataFrame({
        "Data": pd.bdate_range("2024-01-01", periods=5),
        "r_MXWO": [0.01, 0.02, 0.03, 0.04, 0.05],
    })
    s = serie_preditora(painel, Spec("net_1d", "r_MXWO", "acumulada", 2))
    assert s.iloc[2] == pytest.approx(0.01 + 0.02)
    assert s.iloc[4] == pytest.approx(0.03 + 0.04)


def test_estrutura_encontra_a_defasagem_verdadeira():
    painel = painel_sintetico(k_verdadeiro=3, beta_verdadeiro=-30000.0)
    tab = estrutura_defasagem(painel, "net_1d", "r_MXWO")

    pontuais = tab[tab["tipo"] == "pontual"]
    vencedor = pontuais.loc[pontuais["r2"].idxmax()]
    assert vencedor["n"] == 3
    assert vencedor["beta"] == pytest.approx(-30000.0, rel=0.15)
    assert vencedor["tstat"] < -5


def test_h_a_implicito_em_bilhoes():
    painel = painel_sintetico(k_verdadeiro=3, beta_verdadeiro=-30000.0)
    tab = estrutura_defasagem(painel, "net_1d", "r_MXWO")
    linha = tab[(tab["tipo"] == "pontual") & (tab["n"] == 3)].iloc[0]
    # beta -30000 USD mm por unidade de retorno -> h*A = USD 30 bi
    assert linha["h_a_bi"] == pytest.approx(30.0, rel=0.15)


def test_k_zero_marcado_nao_utilizavel():
    painel = painel_sintetico()
    tab = estrutura_defasagem(painel, "net_1d", "r_MXWO")
    k0 = tab[(tab["tipo"] == "pontual") & (tab["n"] == 0)].iloc[0]
    assert not k0["utilizavel"]
    assert tab[tab["tipo"] == "acumulada"]["utilizavel"].all()


from estudos.afp_leading.modelo import beta_movel, portao_sanidade, FAIXA_H_A_BI


def test_beta_movel_converge_para_o_verdadeiro():
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    bm = beta_movel(painel, Spec("net_1d", "r_MXWO", "pontual", 3))

    assert list(bm.columns) == ["Data", "beta"]
    assert bm["beta"].notna().sum() > 500
    assert bm["beta"].dropna().iloc[-1] == pytest.approx(-30000.0, rel=0.15)


def test_beta_movel_nao_usa_o_futuro():
    """Trocar o dado depois de uma data nao pode mudar o beta naquela data."""
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    bm1 = beta_movel(painel, spec)

    corrompido = painel.copy()
    corrompido.loc[600:, "net_1d"] = corrompido.loc[600:, "net_1d"] * -5.0
    bm2 = beta_movel(corrompido, spec)

    corte = 500
    a = bm1.iloc[:corte]["beta"].to_numpy()
    b = bm2.iloc[:corte]["beta"].to_numpy()
    np.testing.assert_allclose(a, b, equal_nan=True)

    # controle positivo: a corrupcao precisa ter mudado alguma coisa depois
    # do ponto 600. sem isso, uma implementacao quebrada (que devolvesse so
    # NaN, ou que ignorasse o painel de entrada) passaria no assert acima.
    depois1 = bm1.iloc[600:]["beta"].to_numpy()
    depois2 = bm2.iloc[600:]["beta"].to_numpy()
    ambos_validos = ~(np.isnan(depois1) | np.isnan(depois2))
    assert ambos_validos.sum() > 0, "nenhuma estimativa valida apos a corrupcao"
    diferenca = np.abs(depois1[ambos_validos] - depois2[ambos_validos])
    assert (diferenca > 1.0).any(), "corrupcao nao mudou nenhuma estimativa depois de 600"


def test_beta_movel_nao_usa_a_propria_observacao():
    """Ataca a fronteira exata: beta em c nao pode ver a linha c.

    Corrompendo o painel a partir da linha c, o treino da linha c usa so
    indices < c (nao muda), enquanto o treino da linha c+1 usa indices < c+1,
    que ja inclui a linha c corrompida (muda). Esse par distingue sel[i:]
    (correto) de um vazamento estreito como sel[i+1:] (que vazaria so a
    propria observacao).
    """
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    bm1 = beta_movel(painel, spec)

    c = 600
    corrompido = painel.copy()
    corrompido.loc[c:, "net_1d"] = corrompido.loc[c:, "net_1d"] * -5.0
    bm2 = beta_movel(corrompido, spec)

    beta_c_original = bm1.iloc[c]["beta"]
    beta_c_corrompido = bm2.iloc[c]["beta"]
    beta_c1_original = bm1.iloc[c + 1]["beta"]
    beta_c1_corrompido = bm2.iloc[c + 1]["beta"]

    assert not np.isnan(beta_c_original)
    assert not np.isnan(beta_c_corrompido)
    assert not np.isnan(beta_c1_original)
    assert not np.isnan(beta_c1_corrompido)

    # linha c: treino vai so ate c-1, entao a corrupcao a partir de c nao
    # pode ter mudado nada.
    assert beta_c_original == pytest.approx(beta_c_corrompido, abs=1e-6)

    # linha c+1: treino ja inclui a linha c, que esta corrompida, entao o
    # beta tem que ter mudado de forma material.
    assert abs(beta_c1_original - beta_c1_corrompido) > 1.0


def test_beta_movel_janela_movel_nao_usa_o_futuro():
    """Mesma garantia da janela expansivel, mas para a janela movel (janela=252)."""
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    bm1 = beta_movel(painel, spec, janela=252)

    corrompido = painel.copy()
    corrompido.loc[600:, "net_1d"] = corrompido.loc[600:, "net_1d"] * -5.0
    bm2 = beta_movel(corrompido, spec, janela=252)

    corte = 500
    a = bm1.iloc[:corte]["beta"].to_numpy()
    b = bm2.iloc[:corte]["beta"].to_numpy()
    np.testing.assert_allclose(a, b, equal_nan=True)

    # controle positivo, igual ao caso expansivel: prova que o teste tem
    # poder de detectar uma implementacao que ignore o painel ou so devolva NaN.
    depois1 = bm1.iloc[600:]["beta"].to_numpy()
    depois2 = bm2.iloc[600:]["beta"].to_numpy()
    ambos_validos = ~(np.isnan(depois1) | np.isnan(depois2))
    assert ambos_validos.sum() > 0, "nenhuma estimativa valida apos a corrupcao"
    diferenca = np.abs(depois1[ambos_validos] - depois2[ambos_validos])
    assert (diferenca > 1.0).any(), "corrupcao nao mudou nenhuma estimativa depois de 600"


def test_portao_aceita_magnitude_plausivel():
    ok, msg = portao_sanidade(-30000.0)
    assert ok, msg


def test_portao_rejeita_beta_positivo():
    ok, msg = portao_sanidade(30000.0)
    assert not ok
    assert "positivo" in msg.lower()


def test_portao_rejeita_magnitude_absurda():
    ok, msg = portao_sanidade(-500000.0)  # h*A = USD 500 bi
    assert not ok
    assert "500" in msg
