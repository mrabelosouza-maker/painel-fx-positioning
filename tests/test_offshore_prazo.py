"""Offshore por prazo: sinal, total, agregacao e janela rolante.

O que pode dar errado em silencio nesta aba:

  - o SINAL. As series do BCCh vem na otica do banco residente e tem de entrar
    invertidas, senao a aba diz o contrario do que quer dizer e nada quebra;
  - o TOTAL. A linha preta e a soma das fatias desenhadas; se sair de outra
    conta, o grafico mostra uma linha que nao fecha as barras;
  - a AGREGACAO. Os tres grupos tem de ser uma particao dos seis baldes, senao
    o grafico agregado e o detalhado contam coisas diferentes;
  - a JANELA rolante, que conta pregao e nao dia corrido.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import (  # noqa: E402
    OFFSHORE_PRAZO_BALDES, OFFSHORE_PRAZO_GRUPOS, OFFSHORE_PRAZO_NOMES,
    OFFSHORE_PRAZO_TOTAL, SERIES_OFFSHORE_PRAZO,
)
from data_processor import (  # noqa: E402
    _com_total, agrega_prazo, build_prazo_rolling,
    build_prazo_tabela_estoque, build_prazo_tabela_fluxo,
)

NOMES = [OFFSHORE_PRAZO_NOMES[b] for b in OFFSHORE_PRAZO_BALDES]


def _largo(n=10, passo=1.0):
    """Seis baldes, ja em compra-de-USD, em pregoes consecutivos."""
    idx = pd.bdate_range("2025-01-01", periods=n, name="Data")
    return pd.DataFrame(
        {nome: [passo * (i + 1) * (j + 1) for j in range(n)] for i, nome in enumerate(NOMES)},
        index=idx,
    )


# ── ids das series ────────────────────────────────────────────────────
def test_os_ids_sao_ndf_usdclp_do_offshore_em_prazo_contratual():
    # O par e CLPUSD e o instrumento e NDF: a aba Offshore usa a serie ampla
    # (Z, MLME), que e outra coisa. E o slot de prazo e "C", contratual — se
    # virar "R" a serie nao existe e o build volta vazio.
    for tipo, esperado in (("estoque", "STO"), ("fluxo", "FLU")):
        for balde, sid in SERIES_OFFSHORE_PRAZO[tipo].items():
            p = sid.split(".")
            assert p[2] == esperado, sid
            assert p[6] == "NR" and p[8] == "NDF" and p[10] == "CLPUSD", sid
            assert p[11] == "C", f"{sid}: prazo tem de ser contratual"
            assert p[12] == balde, sid


def test_estoque_e_fluxo_cobrem_os_mesmos_baldes():
    assert set(SERIES_OFFSHORE_PRAZO["estoque"]) == set(SERIES_OFFSHORE_PRAZO["fluxo"])
    assert set(SERIES_OFFSHORE_PRAZO["estoque"]) == set(OFFSHORE_PRAZO_BALDES)


# ── total ─────────────────────────────────────────────────────────────
def test_o_total_e_a_soma_das_fatias_desenhadas():
    df = _com_total(_largo())
    fatias = [c for c in df.columns if c != OFFSHORE_PRAZO_TOTAL]
    assert (df[OFFSHORE_PRAZO_TOTAL] == df[fatias].sum(axis=1)).all()


def test_o_nome_do_total_comeca_com_TOTAL():
    # make_sector_weekly_stacked separa a linha preta das barras por este prefixo.
    # Se o nome mudar, o total vira mais uma fatia empilhada e o grafico mente.
    assert OFFSHORE_PRAZO_TOTAL.startswith("TOTAL")


def test_linha_com_balde_faltando_nao_vira_total_menor_sem_aviso():
    df = _largo(4)
    df.iloc[2, 0] = None
    assert pd.isna(_com_total(df)[OFFSHORE_PRAZO_TOTAL].iloc[2])


# ── agregacao ─────────────────────────────────────────────────────────
def test_os_tres_grupos_sao_uma_particao_dos_seis_baldes():
    juntos = [b for baldes in OFFSHORE_PRAZO_GRUPOS.values() for b in baldes]
    assert sorted(juntos) == sorted(OFFSHORE_PRAZO_BALDES)
    assert len(juntos) == len(set(juntos)), "algum balde entra em dois grupos"


def test_agregar_preserva_o_total():
    # Se o agregado nao der o mesmo total do detalhado, os dois graficos de
    # estoque mostram niveis diferentes para a mesma posicao.
    det = _com_total(_largo())
    agg = agrega_prazo(det)
    assert (agg[OFFSHORE_PRAZO_TOTAL] - det[OFFSHORE_PRAZO_TOTAL]).abs().max() < 1e-9


def test_agregar_soma_os_baldes_certos():
    df = _com_total(_largo(3))
    agg = agrega_prazo(df)
    for grupo, baldes in OFFSHORE_PRAZO_GRUPOS.items():
        esperado = df[[OFFSHORE_PRAZO_NOMES[b] for b in baldes]].sum(axis=1)
        assert (agg[grupo] - esperado).abs().max() < 1e-9


# ── janela rolante ────────────────────────────────────────────────────
def test_a_janela_rolante_soma_exatamente_n_pregoes():
    fluxo = _com_total(pd.DataFrame(
        {n: [1.0] * 10 for n in NOMES}, index=pd.bdate_range("2025-01-01", periods=10),
    ))
    roll = build_prazo_rolling(fluxo, 5)
    assert (roll[NOMES[0]] == 5.0).all()
    assert (roll[OFFSHORE_PRAZO_TOTAL] == 5.0 * len(NOMES)).all()


def test_janela_incompleta_nao_vira_barra_parcial():
    fluxo = _com_total(_largo(3))
    assert build_prazo_rolling(fluxo, 5).empty


def test_o_total_do_rolante_sai_das_fatias_e_nao_da_coluna_ja_existente():
    # Se _com_total somasse a coluna de total antiga junto, o total dobraria.
    fluxo = _com_total(_largo(8))
    roll = build_prazo_rolling(fluxo, 3)
    fatias = [c for c in roll.columns if c != OFFSHORE_PRAZO_TOTAL]
    assert set(fatias) == set(NOMES)
    assert (roll[OFFSHORE_PRAZO_TOTAL] == roll[fatias].sum(axis=1)).all()


# ── tabelas ───────────────────────────────────────────────────────────
def test_o_delta_da_tabela_de_estoque_e_ponta_a_ponta_e_nao_soma_de_niveis():
    est = _com_total(_largo(10))
    tab, fim = build_prazo_tabela_estoque(est)
    n = 5
    esperado = est.iloc[-1] - est.iloc[-1 - n]
    assert (tab["delta"] - esperado).abs().max() < 1e-9
    assert (tab["nivel"] - est.iloc[-1]).abs().max() < 1e-9
    assert fim == est.index[-1]


def test_tabela_de_fluxo_compara_a_janela_com_a_anterior_do_mesmo_tamanho():
    idx = pd.bdate_range("2025-01-01", periods=10)
    fluxo = _com_total(pd.DataFrame({n: [1.0] * 5 + [3.0] * 5 for n in NOMES}, index=idx))
    tab, inicio, fim = build_prazo_tabela_fluxo(fluxo, 5)
    assert (tab["fluxo"].loc[NOMES] == 15.0).all()     # 5 pregoes a 3
    assert (tab["anterior"].loc[NOMES] == 5.0).all()   # os 5 antes, a 1
    assert inicio == idx[5] and fim == idx[-1]


def test_sem_historico_para_a_janela_anterior_a_coluna_fica_vazia():
    fluxo = _com_total(_largo(6))
    tab, _, _ = build_prazo_tabela_fluxo(fluxo, 5)
    assert tab["anterior"].isna().all()


# ── vazios ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fn,args", [
    (agrega_prazo, ()), (build_prazo_rolling, (5,)),
])
def test_entrada_vazia_devolve_vazio_em_vez_de_levantar(fn, args):
    assert fn(pd.DataFrame(), *args).empty


def test_tabelas_com_entrada_vazia_devolvem_vazio():
    assert build_prazo_tabela_estoque(pd.DataFrame())[0].empty
    assert build_prazo_tabela_fluxo(pd.DataFrame(), 5)[0].empty


# ── sinal ─────────────────────────────────────────────────────────────
def test_a_serie_crua_do_bcch_entra_invertida(monkeypatch):
    """O BCCh publica na otica do BANCO residente; a aba fala do OFFSHORE.

    Saldo cru positivo = banco comprou USD do offshore = offshore VENDEU USD.
    Na convencao da aba (+ = compra de USD pelo offshore) isso tem de sair
    negativo. E o erro que nao quebra nada: o painel desenha igual e diz o
    contrario.
    """
    import data_processor as dp

    n = len(OFFSHORE_PRAZO_BALDES)
    cru = pd.DataFrame({
        "date_str": ["01-09-2026", "02-09-2026"],
        **{f"V{i}": [100.0 * (i + 1)] * 2 for i in range(n)},
    })
    monkeypatch.setattr(dp, "fetch_bcentral_matrix", lambda codes: cru)

    out = dp._fetch_prazo("estoque")
    assert list(out.columns) == NOMES
    assert (out.iloc[0].values == [-100.0 * (i + 1) for i in range(n)]).all()


def test_dia_sem_dado_sai_antes_de_virar_pregao(monkeypatch):
    # A serie do BCCh vem em dia CORRIDO, com NaN no fim de semana e feriado.
    # Se a linha vazia ficar, ela consome uma sessao da janela rolante.
    import data_processor as dp

    n = len(OFFSHORE_PRAZO_BALDES)
    cru = pd.DataFrame({
        "date_str": ["04-09-2026", "05-09-2026", "07-09-2026"],
        **{f"V{i}": [1.0, None, 2.0] for i in range(n)},
    })
    monkeypatch.setattr(dp, "fetch_bcentral_matrix", lambda codes: cru)

    out = dp._fetch_prazo("fluxo")
    assert len(out) == 2
    assert out.notna().all().all()
