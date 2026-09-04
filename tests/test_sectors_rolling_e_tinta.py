"""Aba Todos os Setores: janela rolante por setor e a tinta das tabelas.

Cobre o que erra em silencio: a janela (soma movel por setor, sem barra
parcial), o total (somado das proprias fatias, e nao mudo quando falta setor) e
a escala da tinta (tirada so das folhas, senao o agregado achata todo o resto).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from config import SECTOR_CHART_LINES, SECTOR_NET_LINE  # noqa: E402
from data_processor import build_sector_rolling  # noqa: E402
from table_builder import _heat_style, make_sector_flow_table  # noqa: E402

SETORES = list(SECTOR_CHART_LINES)


def _longo(n_dias: int, valor_por_setor: dict = None) -> pd.DataFrame:
    """long_df minimo: uma linha por (Data, setor), com net_1d constante."""
    datas = pd.bdate_range("2025-01-01", periods=n_dias)
    valor_por_setor = valor_por_setor or {s: 1.0 for s in SETORES}
    return pd.DataFrame([
        {"Data": d, "setor": s, "net_1d": v}
        for d in datas for s, v in valor_por_setor.items()
    ])


# ── janela rolante ────────────────────────────────────────────────────
def test_soma_a_janela_de_cada_setor_e_nao_o_dia():
    out = build_sector_rolling(_longo(10), 5)
    assert (out["Fondos de pensiones"] == 5.0).all()


def test_janela_incompleta_nao_vira_barra_parcial():
    # 4 pregoes nao fecham janela de 5 nenhuma vez.
    assert build_sector_rolling(_longo(4), 5).empty


def test_primeira_barra_e_a_quinta_data_nao_a_primeira():
    out = build_sector_rolling(_longo(10), 5)
    assert len(out) == 6  # 10 - 5 + 1
    assert out["Data"].iloc[0] == pd.bdate_range("2025-01-01", periods=5)[-1]


def test_total_e_a_soma_das_fatias_desenhadas():
    valores = {s: float(i + 1) for i, s in enumerate(SETORES)}
    out = build_sector_rolling(_longo(8, valores), 3)
    esperado = 3 * sum(valores.values())
    assert out[SECTOR_NET_LINE].tolist() == pytest.approx([esperado] * len(out))
    assert out[SECTOR_NET_LINE].iloc[0] == pytest.approx(
        out[SETORES].iloc[0].sum()
    )


def test_setor_faltando_na_janela_deixa_o_total_nulo_em_vez_de_menor():
    # Sem o min_count o total viria menor, sem aviso, e pareceria fluxo de
    # verdade: um setor a menos e um total incomparavel, nao um total pequeno.
    longo = _longo(6)
    longo = longo[~(
        (longo["setor"] == SETORES[0])
        & (longo["Data"] == longo["Data"].max())
    )]
    out = build_sector_rolling(longo, 3)
    assert pd.isna(out[SECTOR_NET_LINE].iloc[-1])


def test_entrada_vazia_devolve_vazio_em_vez_de_levantar():
    assert build_sector_rolling(pd.DataFrame(), 5).empty


def test_coluna_escolhe_a_perna():
    longo = _longo(6)
    longo["spot"] = 2.0
    fora = build_sector_rolling(longo, 3, "spot")
    assert (fora["Fondos de pensiones"] == 6.0).all()


# ── tinta condicional das tabelas ─────────────────────────────────────
def test_tinta_verde_para_compra_e_vermelha_para_venda():
    assert "rgba(0,176,80" in _heat_style(100, 100)
    assert "rgba(230,57,70" in _heat_style(-100, 100)


def test_intensidade_acompanha_o_valor_relativo():
    forte = _heat_style(100, 100)
    fraco = _heat_style(30, 100)
    alpha = lambda st: float(st.rsplit(",", 1)[1].rstrip(")'"))
    assert alpha(forte) > alpha(fraco) > 0


def test_alpha_tem_teto_para_o_numero_seguir_legivel():
    alpha = float(_heat_style(1e9, 1).rsplit(",", 1)[1].rstrip(")'"))
    assert alpha <= 0.42


def test_valor_nulo_ou_escala_nula_nao_tinge():
    assert _heat_style(None, 100) == ""
    assert _heat_style(float("nan"), 100) == ""
    assert _heat_style(100, 0) == ""
    assert _heat_style(100, None) == ""


def test_agregado_nao_define_a_escala_nem_recebe_tinta():
    # O agregado e a soma das folhas. Se entrasse na escala, a folha de 900
    # sairia quase branca; e se recebesse tinta, apagaria a faixa cinza dele.
    tab = pd.DataFrame(
        {"ndf": [900.0, 100.0, 1000.0], "spot": [0.0, 0.0, 0.0],
         "net": [900.0, 100.0, 1000.0], "ndf_level": [0.0, 0.0, 0.0]},
        index=["Fondos de pensiones", "Otros sectores", "Monto vigente neto"],
    )
    html = make_sector_flow_table(tab, 5, "2025-01-01", "2025-01-07")
    linhas = html.split("<tr")
    folha = next(l for l in linhas if "Fondos de pensiones" in l)
    agg = next(l for l in linhas if "monto vigente neto" in l.lower())
    # A folha maxima entre as folhas leva o alpha cheio.
    assert "rgba(0,176,80,0.420)" in folha
    assert "background:rgba" not in agg


def test_saldo_ndf_fica_sem_tinta_porque_e_estoque_e_nao_movimento():
    tab = pd.DataFrame(
        {"ndf": [0.0], "spot": [0.0], "net": [0.0], "ndf_level": [-5000.0]},
        index=["Fondos de pensiones"],
    )
    html = make_sector_flow_table(tab, 5, "2025-01-01", "2025-01-07")
    assert "background:rgba" not in html
