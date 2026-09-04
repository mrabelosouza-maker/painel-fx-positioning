"""Orcamento de peso da pagina publicada.

Plotly em SVG desenha TODOS os pontos de uma trace, inclusive os que caem fora
da janela inicial do eixo x: o `range` recorta a vista, nao o DOM. Logo o custo
de pintura, de hover e de relayout e proporcional ao total de pontos da serie, e
nao ao pedaco que aparece.

Uma serie diaria de varios anos como barras empilhadas por setor estoura isso
sem nenhum aviso no build: o HTML fica valido, os testes de dado passam e a aba
trava no navegador. Estes limites sao a guarda que faltava. Se um grafico novo
os romper, escolha uma marca mais barata (linha/area em vez de barra) ou corte o
historico da serie -- nao afrouxe o numero.
"""
import base64
import io
import json
import math
import re
import struct
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PAGINA = RAIZ / "docs" / "index.html"

# Tetos com folga sobre o medido (pior figura ~2.100, pagina ~24.000), para nao
# quebrar a cada rebuild de dado mas ainda pegar um grafico novo que estoure.
MAX_RECTS_POR_FIGURA = 3_000
MAX_RECTS_NA_PAGINA = 28_000
BARRA = chr(92)


def _bloco(h: str, start: int) -> str | None:
    """Recorta o array JSON que comeca em `start`, contando profundidade."""
    dep, i, dentro, esc = 0, start, False, False
    while i < len(h):
        c = h[i]
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
                return h[start:i + 1]
        i += 1
    return None


def _valores(y) -> list:
    """Numeros de um campo y, que o Plotly 6 serializa como base64 binario."""
    if isinstance(y, list):
        return y
    if isinstance(y, dict) and "bdata" in y:
        crus = base64.b64decode(y["bdata"])
        fmt = {"f8": "d", "f4": "f", "i4": "i", "i8": "q"}.get(y.get("dtype"), "d")
        n = len(crus) // struct.calcsize(fmt)
        return list(struct.unpack("<" + fmt * n, crus))
    return []


def _figuras() -> list[tuple[str, int]]:
    """(id da div, retangulos de barra) para cada figura da pagina."""
    h = io.open(PAGINA, encoding="utf-8").read()
    fora = []
    for m in re.finditer(r'Plotly\.newPlot\(\s*"([^"]+)"\s*,\s*(\[)', h):
        txt = _bloco(h, m.start(2))
        if not txt:
            continue
        rects = 0
        for t in json.loads(txt):
            if t.get("type") != "bar":
                continue
            rects += sum(
                1 for v in _valores(t.get("y"))
                if isinstance(v, (int, float)) and not math.isnan(v)
            )
        fora.append((m.group(1), rects))
    return fora


@pytest.fixture(scope="module")
def figuras():
    if not PAGINA.exists():
        pytest.skip("docs/index.html ainda nao foi gerado")
    fig = _figuras()
    if not fig:
        pytest.skip("nenhuma figura Plotly na pagina")
    return fig


def test_nenhuma_figura_sozinha_estoura_o_orcamento(figuras):
    piores = sorted(figuras, key=lambda f: -f[1])[:3]
    assert piores[0][1] <= MAX_RECTS_POR_FIGURA, (
        f"figura {piores[0][0]} emite {piores[0][1]:,} retangulos de barra "
        f"(teto {MAX_RECTS_POR_FIGURA:,}). Tres piores: {piores}"
    )


def test_a_pagina_toda_cabe_no_orcamento(figuras):
    total = sum(r for _, r in figuras)
    assert total <= MAX_RECTS_NA_PAGINA, (
        f"a pagina emite {total:,} retangulos de barra "
        f"(teto {MAX_RECTS_NA_PAGINA:,})"
    )


def test_o_contador_enxerga_as_barras(figuras):
    # Guarda do proprio teste: se o parser parar de decodificar o bdata, os
    # dois testes acima passariam com zero e a guarda viraria decorativa.
    assert sum(r for _, r in figuras) > 1_000
