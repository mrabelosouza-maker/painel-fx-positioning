"""A area empilhada divergente dos rolantes por setor.

O empilhamento divergente do Plotly nao existe pronto para area: `barmode
="relative"` resolve isso na barra, mas `stackgroup` so soma. A figura contorna
isso partindo cada setor em duas traces -- a parte positiva num stackgroup e a
negativa no outro. E uma construcao que erra em silencio: um clip trocado
empilharia o setor no lado errado do zero, e o grafico continuaria bonito.

Estes testes leem a figura como ela e emitida na pagina, e nao o objeto Python,
porque e o JSON emitido que o navegador desenha.
"""
import base64
import json
import math
import re
import struct
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from chart_builder import make_sector_rolling_area  # noqa: E402
from config import SECTOR_CHART_LINES, SECTOR_NET_LINE  # noqa: E402

SETORES = list(SECTOR_CHART_LINES)
BARRA = chr(92)


def _numeros(y) -> list:
    """y do Plotly 6: lista, ou dict base64 binario."""
    if isinstance(y, list):
        return [float("nan") if v is None else v for v in y]
    if isinstance(y, dict) and "bdata" in y:
        crus = base64.b64decode(y["bdata"])
        fmt = {"f8": "d", "f4": "f", "i4": "i", "i8": "q"}[y["dtype"]]
        n = len(crus) // struct.calcsize(fmt)
        return list(struct.unpack("<" + fmt * n, crus))
    return []


def _traces(html: str) -> list[dict]:
    m = re.search(r'Plotly\.newPlot\(\s*"[^"]+"\s*,\s*(\[)', html)
    assert m, "nenhuma chamada de newPlot no fragmento"
    dep, i, dentro, esc = 0, m.start(1), False, False
    while i < len(html):
        c = html[i]
        if dentro:
            if esc:
                esc = False
            elif c == BARRA:
                esc = True
            elif c == '"':
                dentro = False
        elif c == '"':
            dentro = True
        elif c in "[{":
            dep += 1
        elif c in "]}":
            dep -= 1
            if dep == 0:
                return json.loads(html[m.start(1):i + 1])
        i += 1
    pytest.fail("nao consegui delimitar o array de traces")


@pytest.fixture(scope="module")
def figura():
    """Um setor sempre positivo, um sempre negativo, um que troca de sinal."""
    datas = pd.bdate_range("2025-01-01", periods=6)
    dados = {"Data": datas}
    for i, s in enumerate(SETORES):
        if i == 0:
            dados[s] = [100.0] * 6                      # sempre compra
        elif i == 1:
            dados[s] = [-60.0] * 6                      # sempre venda
        elif i == 2:
            dados[s] = [40.0, -40.0, 40.0, -40.0, 40.0, -40.0]   # troca
        else:
            dados[s] = [0.0] * 6
    roll = pd.DataFrame(dados)
    roll[SECTOR_NET_LINE] = roll[SETORES].sum(axis=1)
    return _traces(make_sector_rolling_area(roll, "teste", obs_default=3)), roll


def _par(traces, setor):
    """As duas metades de um setor: (positiva, negativa)."""
    metades = [t for t in traces if t.get("name") == setor]
    assert len(metades) == 2, f"{setor} deveria ter duas metades"
    pos = next(t for t in metades if t["stackgroup"] == "pos")
    neg = next(t for t in metades if t["stackgroup"] == "neg")
    return pos, neg


def test_nao_emite_nenhuma_barra(figura):
    # E a razao de existir desta figura: barra custava um retangulo por setor
    # por pregao e travava a aba.
    traces, _ = figura
    assert not [t for t in traces if t.get("type") == "bar"]


def test_um_par_por_setor_mais_a_linha_do_total(figura):
    traces, _ = figura
    assert len(traces) == 2 * len(SETORES) + 1
    assert sum(1 for t in traces if t.get("name") == SECTOR_NET_LINE) == 1


def test_metade_positiva_leva_so_o_que_esta_acima_do_zero(figura):
    traces, roll = figura
    pos, _ = _par(traces, SETORES[2])          # o que troca de sinal
    assert _numeros(pos["y"]) == pytest.approx(
        roll[SETORES[2]].clip(lower=0).tolist()
    )


def test_metade_negativa_leva_so_o_que_esta_abaixo_do_zero(figura):
    traces, roll = figura
    _, neg = _par(traces, SETORES[2])
    assert _numeros(neg["y"]) == pytest.approx(
        roll[SETORES[2]].clip(upper=0).tolist()
    )


def test_as_duas_metades_recompoem_o_valor_original(figura):
    # A guarda contra clip trocado: se as duas metades nao somam o dado, a pilha
    # esta contando outra coisa.
    traces, roll = figura
    for setor in SETORES:
        pos, neg = _par(traces, setor)
        soma = [a + b for a, b in zip(_numeros(pos["y"]), _numeros(neg["y"]))]
        assert soma == pytest.approx(roll[setor].tolist()), setor


def test_o_hover_mostra_o_valor_com_sinal_uma_vez_por_setor(figura):
    traces, roll = figura
    pos, neg = _par(traces, SETORES[1])        # sempre negativo
    # A metade negativa nao entra no hover, senao cada setor apareceria duas
    # vezes, uma delas como +0.
    assert neg.get("hoverinfo") == "skip"
    # E a positiva carrega o valor verdadeiro, nao o seu proprio y (que e 0 aqui).
    assert _numeros(pos["customdata"]) == pytest.approx(roll[SETORES[1]].tolist())
    assert "customdata" in pos["hovertemplate"]


def test_so_uma_metade_por_setor_vai_a_legenda(figura):
    traces, _ = figura
    na_legenda = [
        t for t in traces
        if t.get("showlegend") is not False and t.get("name") in SETORES
    ]
    assert len(na_legenda) == len(SETORES)


def test_as_metades_de_um_setor_ligam_na_legenda(figura):
    # legendgroup comum: clicar no setor apaga as duas metades, nao meia pilha.
    traces, _ = figura
    pos, neg = _par(traces, SETORES[0])
    assert pos["legendgroup"] == neg["legendgroup"] == SETORES[0]


def test_numeros_vao_em_float32(figura):
    # Metade dos bytes no transporte; base64 binario nao comprime no gzip.
    traces, _ = figura
    pos, _ = _par(traces, SETORES[0])
    assert pos["y"]["dtype"] == "f4"
    assert pos["customdata"]["dtype"] == "f4"


def test_entrada_vazia_devolve_aviso_em_vez_de_figura(figura):
    assert "indispon" in make_sector_rolling_area(pd.DataFrame(), "x").lower()
