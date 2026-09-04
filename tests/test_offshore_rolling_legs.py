"""build_offshore_rolling_legs: janelas rolantes das pernas do offshore.

O que pode dar errado em silencio aqui e o sinal (as series do BCCh vem na otica
do banco residente e tem de entrar invertidas) e a janela (soma de variacoes
diarias tem de fechar o delta do saldo de ponta a ponta). Os testes cobrem isso.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_processor import build_offshore_rolling_legs  # noqa: E402


def _adj(ndf, spot):
    """adj_df minimo, em pregoes consecutivos, no sinal cru do BCCh."""
    return pd.DataFrame({
        "Data": pd.bdate_range("2025-01-01", periods=len(ndf)),
        "No residentes": ndf,
        "spot_neto": spot,
    })


def test_janela_de_ndf_fecha_o_delta_do_saldo_ponta_a_ponta():
    # Saldo cru sobe 10 por dia => em compra-de-USD cai 10 por dia, e a janela
    # de 3 pregoes tem de dar exatamente -30, nao a soma de tres niveis.
    df = _adj([0, 10, 20, 30, 40, 50], [0.0] * 6)
    out = build_offshore_rolling_legs(df, 3)
    assert (out["ndf_wk"] == -30).all()


def test_as_duas_pernas_entram_invertidas_e_o_net_e_a_soma():
    # O primeiro pregao sai (nao tem variacao de saldo), sobram dois: a janela
    # de 2 pega o saldo cru de 0 a 10 e o spot cru de 2+2+2 nesses dois dias.
    df = _adj([0, 5, 10], [2.0, 2.0, 2.0])
    out = build_offshore_rolling_legs(df, 2)
    assert len(out) == 1
    linha = out.iloc[0]
    assert linha["ndf_wk"] == -10  # saldo cru +10 na janela -> -10 comprando USD
    assert linha["bcch_wk"] == -4  # spot cru +2+2 -> -4
    assert linha["net_wk"] == -14


def test_a_barra_mais_antiga_nao_soma_spot_de_n_dias_contra_ndf_de_n_menos_1():
    # Sem o corte do primeiro pregao a janela mais antiga teria NDF em NaN e uma
    # barra de spot sozinha, empilhada contra nada.
    df = _adj([0, 10, 20, 30, 40], [1.0] * 5)
    out = build_offshore_rolling_legs(df, 2)
    assert out[["ndf_wk", "bcch_wk", "net_wk"]].notna().all().all()
    assert (out["bcch_wk"] == -2).all()  # sempre 2 dias de spot, nunca 3


def test_media_movel_suaviza_sem_deslocar_o_nivel():
    # Janela constante: a media movel por cima nao pode mudar o valor.
    df = _adj(list(range(0, 100, 10)), [1.0] * 10)
    crua = build_offshore_rolling_legs(df, 3)
    suave = build_offshore_rolling_legs(df, 3, media=5)
    assert (suave["ndf_wk"] == crua["ndf_wk"].iloc[0]).all()
    # A suavizacao custa os 4 primeiros pontos da janela crua.
    assert len(suave) == len(crua) - 4


def test_janela_incompleta_nao_vira_barra_parcial():
    df = _adj([0, 10, 20], [0.0] * 3)
    # 3 pregoes rendem 2 variacoes diarias: janela de 5 nao fecha nenhuma vez.
    assert build_offshore_rolling_legs(df, 5).empty


def test_dias_sem_saldo_de_ndf_saem_antes_da_janela():
    # A linha com saldo NaN nao pode consumir um dos N pregoes da janela.
    df = _adj([0, 10, None, 20, 30, 40], [0.0] * 6)
    out = build_offshore_rolling_legs(df, 2)
    assert out["ndf_wk"].notna().all()
    assert (out["ndf_wk"] == -20).all()


def test_entrada_vazia_devolve_vazio_em_vez_de_levantar():
    assert build_offshore_rolling_legs(pd.DataFrame(), 5).empty
