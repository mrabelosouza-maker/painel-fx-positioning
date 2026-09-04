"""O shim de renderizacao preguicosa, executado de verdade em Node.

O shim vive no template como JS, entao afirmar sobre o texto dele nao prova
nada: um `!` a menos inverteria a logica e o teste de texto continuaria verde.
Aqui o codigo real e extraido da pagina publicada e executado contra um DOM e um
Plotly falsos, para checar o comportamento que importa:

  - figura da aba visivel desenha na hora;
  - figura de aba escondida NAO desenha, fica na fila;
  - quando a aba abre, o flush solta so as dela;
  - figura fora de qualquer aba desenha na hora (o seguro).
"""
import io
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PAGINA = RAIZ / "docs" / "index.html"

# Fake DOM minimo: tres divs, uma na aba visivel, uma na escondida, uma solta.
CENARIO = r"""
var desenhadas = [];
function Pane(nome, ligada) {
  this.classList = {
    _on: ligada,
    contains: function (c) { return c === 'on' && this._on; },
  };
  this.nome = nome;
}
var visivelPane = new Pane('tab-visivel', true);
var escondidaPane = new Pane('tab-escondida', false);

function Div(id, pane) {
  this.id = id;
  this._pane = pane;
  this.closest = function (sel) { return sel === '.tab' ? this._pane : null; };
}
var divs = {
  naVisivel: new Div('naVisivel', visivelPane),
  naEscondida: new Div('naEscondida', escondidaPane),
  solta: new Div('solta', null),
};
global.document = {
  getElementById: function (id) { return divs[id] || null; },
};
global.Plotly = {
  newPlot: function (id) { desenhadas.push(id); return Promise.resolve(); },
};
global.window = {};
global.Promise = Promise;
"""

VERIFICACAO = r"""
var L = window.JGPLazy;
L.flush();  // nada pendente ainda
Plotly.newPlot('naVisivel', [], {});
Plotly.newPlot('naEscondida', [], {});
Plotly.newPlot('solta', [], {});

var resultado = {
  depoisDoLoad: desenhadas.slice(),
  pendentesDepoisDoLoad: L.pendentes(),
};

// A aba escondida abre: o showTab liga o .on e chama flush.
escondidaPane.classList._on = true;
resultado.soltasNoFlush = L.flush();
resultado.depoisDoFlush = desenhadas.slice();
resultado.pendentesDepoisDoFlush = L.pendentes();

// Flush de novo nao pode desenhar a mesma figura outra vez.
L.flush();
resultado.depoisDoSegundoFlush = desenhadas.slice();

console.log(JSON.stringify(resultado));
"""


def _shim_da_pagina() -> str:
    """Extrai o IIFE do window.JGPLazy da pagina publicada."""
    h = io.open(PAGINA, encoding="utf-8").read()
    m = re.search(r"window\.JGPLazy = \(function \(\) \{", h)
    assert m, "shim window.JGPLazy nao encontrado na pagina"
    # Fecha no '})();' que casa com a abertura, contando chaves.
    i = h.index("{", m.start())
    dep = 0
    while i < len(h):
        if h[i] == "{":
            dep += 1
        elif h[i] == "}":
            dep -= 1
            if dep == 0:
                fim = h.index(";", i)
                return h[m.start():fim + 1]
        i += 1
    pytest.fail("nao consegui delimitar o shim")


@pytest.fixture(scope="module")
def resultado():
    if not PAGINA.exists():
        pytest.skip("docs/index.html ainda nao foi gerado")
    if not shutil.which("node"):
        pytest.skip("node nao disponivel para executar o shim")
    script = CENARIO + _shim_da_pagina() + VERIFICACAO
    proc = subprocess.run(
        ["node", "--input-type=commonjs", "-e", script],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"node falhou:\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_aba_visivel_desenha_no_load(resultado):
    assert "naVisivel" in resultado["depoisDoLoad"]


def test_aba_escondida_nao_desenha_no_load(resultado):
    assert "naEscondida" not in resultado["depoisDoLoad"]
    assert resultado["pendentesDepoisDoLoad"] == 1


def test_figura_fora_de_aba_desenha_no_load(resultado):
    # O seguro: se um grafico for para fora da estrutura de abas, ele nao pode
    # ficar preso numa fila que ninguem solta.
    assert "solta" in resultado["depoisDoLoad"]


def test_abrir_a_aba_solta_a_figura(resultado):
    assert resultado["soltasNoFlush"] == 1
    assert "naEscondida" in resultado["depoisDoFlush"]
    assert resultado["pendentesDepoisDoFlush"] == 0


def test_flush_repetido_nao_redesenha(resultado):
    assert resultado["depoisDoSegundoFlush"] == resultado["depoisDoFlush"]
