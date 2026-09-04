"""templates/dashboard.html e GERADO; tools/corpo.html e a fonte.

O cabecalho do tools/montar_casca.py diz isso, mas nada verificava, e o arquivo
gerado foi editado a mao mais de uma vez. O custo nao aparece na hora: aparece na
proxima vez que alguem roda o gerador e o painel volta no tempo, perdendo
secoes, notas de convencao de sinal e abas — silenciosamente, porque o HTML
continua valido e o build passa.

Esta guarda compara o corpo do arquivo gerado com a fonte. Se falhar, NAO edite o
corpo.html para calar o teste sem antes olhar qual dos dois esta mais novo: se o
dashboard.html tem a mudanca boa, porte para o corpo.html; se o corpo.html tem,
rode `python tools/montar_casca.py`.
"""
import io
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
GERADO = RAIZ / "templates" / "dashboard.html"
FONTE = RAIZ / "tools" / "corpo.html"

# Como o montar_casca.py monta: </head>\n{body}\n<script>\n{chrome}...
ABRE = "</head>\n"
FECHA = "\n<script>\n"


def _corpo_do_gerado() -> str:
    # Leitura com newline universal nos dois lados: no Windows o git normaliza
    # CRLF na copia de trabalho, e a comparacao aqui e de conteudo, nao de
    # terminador de linha.
    h = io.open(GERADO, encoding="utf-8").read()
    ini = h.index(ABRE) + len(ABRE)
    return h[ini:h.index(FECHA, ini)]


@pytest.fixture(scope="module")
def par():
    for f in (GERADO, FONTE):
        if not f.exists():
            pytest.skip(f"{f.name} nao existe")
    return _corpo_do_gerado(), io.open(FONTE, encoding="utf-8").read()


def test_o_corpo_do_gerado_e_igual_a_fonte(par):
    corpo, fonte = par
    if corpo == fonte:
        return
    # Diferenca legivel: as linhas que existem so em um dos lados.
    so_no_gerado = [l for l in corpo.splitlines() if l not in fonte.splitlines()]
    so_na_fonte = [l for l in fonte.splitlines() if l not in corpo.splitlines()]
    pytest.fail(
        "templates/dashboard.html divergiu de tools/corpo.html.\n"
        f"So no gerado ({len(so_no_gerado)} linhas): {so_no_gerado[:6]}\n"
        f"So na fonte ({len(so_na_fonte)} linhas): {so_na_fonte[:6]}"
    )


def test_a_fonte_nao_referencia_grafico_que_o_build_nao_gera(par):
    """Placeholder orfao vira card vazio na pagina, sem erro no build.

    Ja aconteceu: o corpo.html ficou com offadj_net_vs_afp depois que o grafico
    saiu do build.py, e ninguem viu porque o gerador nao rodava.
    """
    import re
    import sys

    sys.path.insert(0, str(RAIZ / "src"))
    fonte = par[1]
    placeholders = set(re.findall(r"\{\{\s*(\w+)\s*\|\s*safe\s*\}\}", fonte))

    build_py = io.open(RAIZ / "src" / "build.py", encoding="utf-8").read()
    faltando = sorted(
        p for p in placeholders
        if f'"{p}"' not in build_py and f"'{p}'" not in build_py
        and f'ctx[f"{p[:p.rindex("_") + 1] if "_" in p else p}' not in build_py
    )
    # Chaves montadas por f-string (sectors_table_5, sectors_roll21, ...) nao
    # aparecem literais: exige que o prefixo apareca em algum ctx[f"...
    faltando = [
        p for p in faltando
        if not any(
            f'ctx[f"{p[:i]}' in build_py for i in range(len(p), 3, -1)
        )
    ]
    assert not faltando, (
        f"tools/corpo.html usa placeholders que o build.py nao preenche: {faltando}"
    )
