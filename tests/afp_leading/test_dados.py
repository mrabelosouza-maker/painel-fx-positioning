"""Alinhamento de calendario entre o fluxo AFP e os indices de bolsa."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from estudos.afp_leading.dados import alinhar


def _afp(datas, net=None):
    n = len(datas)
    return pd.DataFrame({
        "Data": pd.to_datetime(datas),
        "ndf_1d": np.arange(n, dtype=float),
        "spot_bcch": np.zeros(n),
        "net_1d": np.arange(n, dtype=float) if net is None else net,
    })


def test_retorno_acumula_sobre_dia_sem_indice():
    """Feriado no indice: retorno zero no dia, movimento inteiro no seguinte.

    O painel tem 3 dias uteis chilenos; o indice nao negociou no dia 2. O
    retorno do dia 2 tem que ser zero e o do dia 3 tem que carregar o caminho
    inteiro de 100 para 110, nao so o ultimo trecho.
    """
    afp = _afp(["2024-01-02", "2024-01-03", "2024-01-04"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-04"]),
        "MXWO": [100.0, 110.0],
    })

    out = alinhar(afp, precos)

    assert list(out.columns) == ["Data", "ndf_1d", "spot_bcch", "net_1d", "r_MXWO"]
    # primeira linha nao tem retorno definido e sai do painel
    assert len(out) == 2
    assert out["Data"].tolist() == pd.to_datetime(["2024-01-03", "2024-01-04"]).tolist()
    assert out["r_MXWO"].iloc[0] == pytest.approx(0.0)
    assert out["r_MXWO"].iloc[1] == pytest.approx(np.log(110 / 100))


def test_dia_do_afp_sem_preco_anterior_sai_do_painel():
    """Sem fechamento anterior ao inicio, nao ha retorno: a linha nao entra."""
    afp = _afp(["2024-01-02", "2024-01-03"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-03"]),
        "MXWO": [100.0],
    })

    out = alinhar(afp, precos)

    assert out.empty


def test_dia_do_indice_sem_afp_nao_vira_linha():
    """O painel segue o calendario do AFP; dia extra do indice e ignorado."""
    afp = _afp(["2024-01-02", "2024-01-04"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        "MXWO": [100.0, 105.0, 110.0],
    })

    out = alinhar(afp, precos)

    assert out["Data"].tolist() == pd.to_datetime(["2024-01-04"]).tolist()
    # acumula 100 -> 110, passando por 105 sem criar linha
    assert out["r_MXWO"].iloc[0] == pytest.approx(np.log(110 / 100))


def test_fluxo_nao_e_preenchido():
    """NaN no fluxo derruba a linha; nunca vira zero nem ffill."""
    afp = _afp(["2024-01-02", "2024-01-03", "2024-01-04"])
    afp.loc[1, "net_1d"] = np.nan
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        "MXWO": [100.0, 105.0, 110.0],
    })

    out = alinhar(afp, precos)

    assert out["Data"].tolist() == pd.to_datetime(["2024-01-04"]).tolist()


def test_painel_vazio_nao_quebra_com_varios_indices():
    """Painel AFP vazio com 2+ colunas de indice nao pode quebrar via enlargement.

    Com 0 linhas em `out`, um `out.loc[0, col] = valor` cria uma linha
    fantasma (setting with enlargement); a segunda coluna de indice entao
    falha porque o tamanho dos valores nao bate mais com o indice. O
    resultado esperado e simplesmente um DataFrame vazio, sem excecao.
    """
    afp = _afp([])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "MXWO": [100.0, 101.0],
        "MXWD": [200.0, 202.0],
    })

    out = alinhar(afp, precos)

    assert out.empty
    assert list(out.columns) == [
        "Data", "ndf_1d", "spot_bcch", "net_1d", "r_MXWO", "r_MXWD",
    ]


def test_indice_todo_nan_levanta_erro():
    """Coluna de indice sem nenhum valor nao pode esvaziar o painel em silencio."""
    afp = _afp(["2024-01-02", "2024-01-03"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "MXWO": [100.0, 101.0],
        "MXWD": [np.nan, np.nan],
    })

    with pytest.raises(ValueError, match="MXWD"):
        alinhar(afp, precos)


def test_amostra_e_intersecao_de_todos_os_indices():
    """A amostra final e a intersecao de todos os indices, nao a uniao.

    MXWD so comeca em 2024-01-03 (um dia a menos de historico que MXWO).
    Isolado, o MXWO teria retorno valido em 2024-01-03; mas como o MXWD
    ainda nao tem fechamento anterior nessa data, a linha sai do painel.
    """
    afp = _afp(["2024-01-02", "2024-01-03", "2024-01-04"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        "MXWO": [100.0, 101.0, 102.0],
        "MXWD": [np.nan, 150.0, 151.0],
    })

    out = alinhar(afp, precos)

    assert pd.to_datetime("2024-01-03") not in out["Data"].tolist()
    assert out["Data"].tolist() == pd.to_datetime(["2024-01-04"]).tolist()
