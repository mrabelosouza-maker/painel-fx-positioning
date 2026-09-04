"""Estrutura das abas no corpo do painel: divs balanceadas e panes irmaos.

Escrito depois de um estrago real. Ao remover a aba "Total vs USDCLP" ficou um
`</div>` orfao no lugar dela. O navegador nao reclama de div sobrando: ele fecha
o `main-content` ali e reparenta o resto, entao as quatro ultimas abas viraram
filhas diretas do `<body>`, fora do `.page-wrapper`. O efeito visivel era um vao
branco de quase mil pixels no topo da aba.

Nada disso quebrou: o build passou, o HTML saiu valido, os graficos desenharam e
os 33 testes de entao ficaram verdes. Só se vê abrindo no navegador. Daí estes
testes, que sao de forma e nao de conteudo:

  - as divs do corpo fecham exatamente;
  - todo pane de aba abre na mesma profundidade (sao irmaos dentro do main);
  - ha um pane para cada botao da tabbar, e vice-versa.
"""
import io
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / "tools" / "corpo.html"

TAG_DIV = re.compile(r"<div\b[^>]*>|</div\s*>", re.I)
ID_ABA = re.compile(r'<div\b[^>]*id="tab-([\w-]+)"', re.I)
BOTAO_ABA = re.compile(r'<button\b[^>]*data-tab="([\w-]+)"', re.I)


def _limpo() -> str:
    """Corpo sem comentarios: um <div> comentado nao conta na arvore."""
    s = io.open(FONTE, encoding="utf-8").read()
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


@pytest.fixture(scope="module")
def corpo():
    if not FONTE.exists():
        pytest.skip("tools/corpo.html nao existe")
    return _limpo()


def _profundidades(corpo: str):
    """(profundidade final, {id da aba: profundidade em que abriu})."""
    prof = 0
    abas = {}
    for m in TAG_DIV.finditer(corpo):
        tag = m.group(0)
        if tag.startswith("</"):
            prof -= 1
        else:
            nome = ID_ABA.match(tag)
            if nome:
                abas[nome.group(1)] = prof
            prof += 1
    return prof, abas


def test_as_divs_do_corpo_fecham_exatamente(corpo):
    prof, _ = _profundidades(corpo)
    assert prof == 0, (
        f"o corpo termina com profundidade {prof}: "
        + ("falta fechar div" if prof > 0 else "ha </div> sobrando")
    )


def test_toda_aba_abre_na_mesma_profundidade(corpo):
    _, abas = _profundidades(corpo)
    assert abas, "nenhum pane de aba encontrado"
    niveis = sorted(set(abas.values()))
    assert len(niveis) == 1, (
        "panes de aba em profundidades diferentes — algum </div> sobrando ou "
        f"faltando entre eles: { {k: v for k, v in abas.items()} }"
    )


def test_cada_botao_da_tabbar_tem_o_seu_pane(corpo):
    _, abas = _profundidades(corpo)
    botoes = set(BOTAO_ABA.findall(corpo))
    # O bloco de exemplo do comentario da casca usa data-tab="X"; ja saiu no
    # _limpo(), mas se voltar nao deve reprovar o teste por si.
    botoes.discard("X")
    assert botoes == set(abas), (
        f"botao sem pane: {sorted(botoes - set(abas))} | "
        f"pane sem botao: {sorted(set(abas) - botoes)}"
    )
