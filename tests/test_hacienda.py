"""Aba Vendas Hacienda: o que nao pode quebrar calado.

  - zero da planilha depois de HACIENDA_ULTIMO_DIVULGADO e "nao sabemos", nao
    "nao vendeu": se entrar como zero, a calibracao aprende que o neto alto de
    junho veio sem venda e a regua sem Hacienda ganha meses com venda;
  - a planilha anota 2026 em mil USD e o resto em mm USD;
  - os dois estimadores fecham a conta que dizem fazer.

Tudo com dado sintetico: nada aqui toca a API do BCCh nem o drive R:.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import data_processor as dp  # noqa: E402
from config import HACIENDA_ULTIMO_DIVULGADO  # noqa: E402


def _diario(inicio="2024-01-01", fim="2026-10-07", seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(inicio, fim)
    compras = 150 + rng.normal(0, 20, len(idx))
    ventas = 150 + rng.normal(0, 20, len(idx))
    return pd.DataFrame(
        {"compras": compras, "ventas": ventas, "neto": compras - ventas}, index=idx,
    )


@pytest.fixture
def hacienda(monkeypatch):
    d = _diario()
    meses = pd.date_range("2024-01-01", HACIENDA_ULTIMO_DIVULGADO + "-01", freq="MS")
    efetivo = pd.Series(500.0, index=meses, name="efetivo")
    efetivo[["2024-04-01", "2024-05-01"]] = 0.0
    monkeypatch.setattr(dp, "fetch_otros_spot", lambda: d)
    monkeypatch.setattr(dp, "load_hacienda_mensal", lambda: efetivo)
    return dp.build_hacienda(), d, efetivo


def test_apagao_nao_vira_zero(hacienda):
    h, _, _ = hacienda
    m = h["mensal"]
    depois = m.index > pd.Timestamp(HACIENDA_ULTIMO_DIVULGADO + "-01")
    assert depois.any()
    assert m.loc[depois, "efetivo"].isna().all()
    # ... e por isso nenhum mes do apagao entra na regua sem Hacienda.
    assert all(t <= pd.Timestamp(HACIENDA_ULTIMO_DIVULGADO + "-01") for t in h["regua"]["meses"])


def test_regua_so_com_meses_de_venda_zero(hacienda):
    h, _, _ = hacienda
    assert [t.strftime("%Y-%m") for t in h["regua"]["meses"]] == ["2024-04", "2024-05"]


def test_estimador_fecha_a_conta_e_sinal_compra_usd(hacienda):
    h, d, efetivo = hacienda
    m, c = h["mensal"], h["calib"]
    cal = m.loc[c["inicio"]:c["fim"]].dropna(subset=["efetivo"])
    # Razao: na janela de calibracao, a soma estimada bate a soma divulgada.
    assert cal["est"].sum() == pytest.approx(cal["efetivo"].sum())
    # Convencao do painel: venda de USD e negativa, razao positiva.
    assert (m["efetivo"].dropna() <= 0).all()
    assert (h["diario"]["venda"] <= 0).all()
    assert c["razao"] > 0
    # neto em compra-de-USD = o oposto do neto cru do banco.
    assert h["diario"]["neto"].iloc[0] == pytest.approx(-d["neto"].iloc[0])


def test_semana_parcial_so_na_ultima(hacienda):
    h, _, _ = hacienda
    sem = h["semanal"]
    assert bool(sem["parcial"].iloc[-1])            # 07/10/2026 e uma quarta
    assert int(sem["pregoes"].iloc[-1]) == 3
    assert not sem["parcial"].iloc[:-1].any()


def test_planilha_em_mil_usd_a_partir_de_2026(monkeypatch, tmp_path):
    raw = pd.DataFrame({
        0: [None, None, pd.Timestamp("2025-12-01"), pd.Timestamp("2026-01-01"),
            pd.Timestamp("2026-05-01"), pd.Timestamp("2026-06-01")],
        1: [None, "Vendas Mensais USD", 900, 550_000, 1_944_000, 0],
    })
    monkeypatch.setattr(dp.pd, "read_excel", lambda *a, **k: raw)
    monkeypatch.setattr(dp, "HACIENDA_CACHE", str(tmp_path / "c.csv"))
    s = dp.load_hacienda_mensal()
    assert s["2025-12-01"] == 900
    assert s["2026-01-01"] == 550
    assert s["2026-05-01"] == 1944
    # junho/2026 em diante nao existe: e o apagao.
    assert pd.Timestamp("2026-06-01") not in s.index
    # e o cache foi regravado, para o build sem drive R:.
    assert (tmp_path / "c.csv").exists()
