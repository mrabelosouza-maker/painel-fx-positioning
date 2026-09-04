"""Monta templates/dashboard.html: casca editorial JGP + corpo do painel.

templates/dashboard.html e um arquivo GERADO — nao edite ele a mao. Edite
tools/corpo.html (abas, secoes, notas) ou o SHIM_CSS/PANEL_JS aqui embaixo, e
rode:

    python tools/montar_casca.py && python src/build.py

A casca (dashboard.css + chrome.js) vem do skill jgp-html-report, entao rodar de
novo tambem traz as atualizacoes dela. Sem o skill instalado o script para no
read_text — nesse caso o dashboard.html ja versionado continua valendo.
"""
from pathlib import Path

SKILL = Path.home() / ".claude" / "skills" / "jgp-html-report" / "references"
SCRATCH = Path(__file__).resolve().parent
ROOT = SCRATCH.parent

css = SKILL.joinpath("dashboard.css").read_text(encoding="utf-8")
chrome = SKILL.joinpath("chrome.js").read_text(encoding="utf-8")
body = SCRATCH.joinpath("corpo.html").read_text(encoding="utf-8")

# A casca original nao dispara resize ao colapsar o sumario; os graficos deste
# painel sao pre-renderizados e nao reflowam sozinhos. Ver applyNav no SKILL.md.
old = """        updateProgress();
      };"""
new = """        updateProgress();
        window.dispatchEvent(new Event('resize'));
      };"""
assert old in chrome
chrome = chrome.replace(old, new)

# ── Extensoes de CSS: grids deste painel + classes legadas do table_builder ──
SHIM_CSS = """
  /* ==== Extensoes do painel FX Positioning ==== */
  /* Grid 2:1 (grafico grande + tabela) e grid de 3 (tenores do swap). */
  .grid-wide{display:grid;grid-template-columns:2fr 1fr;gap:14px}
  .grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
  .grid-wide > .card:last-child{align-self:start}
  @media (max-width:1200px){.grid-wide,.grid3{grid-template-columns:1fr}}
  @media (max-width:820px){.grid-wide,.grid3{grid-template-columns:1fr}}

  /* Os graficos vem prontos do Python (plotly to_html); o card e a moldura. */
  .card .js-plotly-plot{width:100%!important}
  .card > .plotly-graph-div{margin:0 auto}
  /* Card cuja figura ainda nao nasceu, por causa do render preguicoso (LAZY_JS):
     sem o retangulo branco. O --bg-content e #FFFFFF sobre um papel creme, e a
     aba de setores tem cinco figuras de 560px — quase tres mil pixels de branco
     enquanto elas desenham.

     O Plotly poe .js-plotly-plot na propria div quando desenha, entao a AUSENCIA
     dela e o sinal de pendente. Some so o fundo e a borda; a altura fica, senao
     o layout salta quando a figura aparece. */
  .card:has(> div > .plotly-graph-div:not(.js-plotly-plot)),
  .card:has(> .plotly-graph-div:not(.js-plotly-plot)){
    background:transparent;border-color:transparent
  }

  /* Tabelas emitidas pelo table_builder.py (.data-table) na moldura JGP:
     cabecalho verde, numeros tabulares, agregados com risco em cima. */
  table.data-table{border-collapse:collapse;font-size:12px;width:100%;min-width:0;max-width:none}
  table.data-table th,table.data-table td{border:1px solid var(--line);padding:5px 10px;white-space:nowrap}
  table.data-table thead th{background:var(--green);color:#fff;font-weight:700;text-align:center;
    border-color:var(--green-dark)}
  table.data-table thead th:first-child{text-align:left}
  table.data-table td.num{text-align:right;font-variant-numeric:tabular-nums}
  table.data-table td.row-label{text-align:left;font-weight:600}
  /* A formatacao condicional das tabelas de setores sai como background inline,
     que vence esta regra por especificidade. !important devolve o hover: a tinta
     serve para varrer a coluna com o olho, e ao passar o mouse a linha inteira
     se destaca limpa, para ler os numeros. */
  table.data-table tbody tr:hover td{background:var(--jgp-green-tint) !important}
  /* Amostras de cor na legenda da tinta, no subtitulo da tabela. */
  .heat-key{padding:0 5px;border-radius:3px;font-weight:600;color:var(--ink-primary)}
  .heat-key-compra{background:rgba(0,176,80,.34)}
  .heat-key-venda{background:rgba(230,57,70,.34)}
  table.data-table tr.row-agg td{background:var(--sec);font-weight:700;
    border-top:2px solid var(--rule-strong)}
  .table-title{font-size:14px;font-weight:700;color:var(--chart-title);margin:0 0 2px;letter-spacing:-.01em}
  .table-subtitle{font-size:11px;color:var(--chart-sub);margin:0 0 10px;line-height:1.4}

  /* Notas de leitura dentro de um card. */
  .note{font-size:11.5px;line-height:1.6;color:var(--ink-secondary);
    border-top:1px solid var(--rule-faint);margin-top:14px;padding-top:12px}
  .note-flush{border-top:none;margin-top:0;padding-top:0}

  /* ==== Respiro ====
     A casca e desenhada para texto corrido; aqui cada card carrega um grafico
     ou uma tabela densa, entao o padrao ficava apertado. */
  /* O card do skill tem .5rem .6rem: pouco para uma moldura de figura. */
  .card{padding:.75rem .9rem .65rem}
  /* Cabecalho verde com um pouco mais de ar que as linhas de dado. */
  table.data-table thead th{padding:6px 10px}
  /* Entre o texto de apoio da secao e o primeiro card. */
  .lead,.sub{margin-bottom:12px;line-height:1.6}
  /* h2 tem regua tracejada logo abaixo: afasta do texto que vem depois. */
  h2{margin:2rem 0 .9rem;padding-bottom:.5rem}
  /* Sem page-header o primeiro h2 encosta na tabbar, e nao ha nada acima dele
     dentro do painel para separar. */
  .tab > h2:first-child{margin-top:.2rem}
"""
css = css.rstrip() + "\n" + SHIM_CSS

# O painel nao usa o page-header da casca (titulo + lead + meta): ele repetia em
# toda aba e comia ~230px de altura. A data do build vive na pill da topnav e no
# rodape. Sem ele o respiro de 2rem do topo vira 1rem.
for antes, depois in [
    ("  .main-content{padding:2rem 1.8rem 4rem;min-width:0;position:relative}",
     "  .main-content{padding:1rem 1.8rem 4rem;min-width:0;position:relative}"),
    ("    .main-content{padding:2rem 1.4rem 4rem}",
     "    .main-content{padding:1rem 1.4rem 4rem}"),
]:
    assert antes in css
    css = css.replace(antes, depois)

# Sumario fechado por padrao neste painel: sao 43 graficos e a largura vale mais
# que a lista de secoes. Quem abrir uma vez continua com ele aberto (o '0' fica
# no localStorage); a casca vinha com o padrao inverso.
old = "      let col = false; try { col = localStorage.getItem(key) === '1'; } catch (e) {}"
new = (
    "      let col = true;\n"
    "      try { const v = localStorage.getItem(key); if (v !== null) col = v === '1'; } catch (e) {}"
)
assert old in chrome
chrome = chrome.replace(old, new)

# O showTab da casca nao sabe da renderizacao preguicosa (LAZY_JS): as figuras da
# aba que acabou de abrir precisam nascer depois do toggle do .on e antes do
# onTab, para o reflow/retema dele as pegar ja desenhadas.
old = """    document.querySelectorAll('.tab').forEach(p => p.classList.toggle('on', p.id === 'tab-' + id));
    buildSidebar();"""
new = """    document.querySelectorAll('.tab').forEach(p => p.classList.toggle('on', p.id === 'tab-' + id));
    // Depois de trocar o .on e antes do onTab: as figuras que estavam
    // enfileiradas nesta aba nascem agora, com largura de verdade, e o
    // reflow/retema do onTab as pega ja desenhadas.
    if (window.JGPLazy) window.JGPLazy.flush();
    buildSidebar();"""
assert old in chrome
chrome = chrome.replace(old, new)

# ── Renderizacao preguicosa: entra no head, antes de qualquer figura ──
LAZY_JS = """<script>
/* =====================================================================
   Renderizacao preguicosa por aba.

   As figuras chegam do Python (plotly to_html) como chamadas inline de
   Plotly.newPlot, que rodam no parse do HTML. Sem isto, abrir o painel desenha
   as 46 de uma vez — dezenas de milhares de nos SVG, a grande maioria em aba
   escondida. Pior: aba escondida tem largura zero, entao a figura sai medida
   errada e so se corrige no reflow seguinte.

   O shim troca Plotly.newPlot por uma versao que enfileira a chamada quando a
   div nao esta na aba visivel, e a solta quando a aba abre (showTab chama
   flush). Como o script vem depois do plotly.min.js e antes de qualquer figura,
   toda chamada passa por aqui.
   ===================================================================== */
window.JGPLazy = (function () {
  var fila = {};   // id da div -> arguments do newPlot que ficou pendente
  var real = null;

  function visivel(id) {
    var el = document.getElementById(id);
    var pane = el && el.closest ? el.closest('.tab') : null;
    // Fora de qualquer aba (ou sem closest): desenha na hora, e o seguro.
    return !pane || pane.classList.contains('on');
  }

  if (typeof Plotly !== 'undefined') {
    real = Plotly.newPlot;
    Plotly.newPlot = function (div) {
      var id = typeof div === 'string' ? div : (div && div.id);
      if (id && !visivel(id)) {
        fila[id] = arguments;
        // to_html nao encadeia .then, mas devolver promessa mantem o contrato.
        return Promise.resolve();
      }
      return real.apply(Plotly, arguments);
    };
  }

  function solta(id) {
    var args = fila[id];
    delete fila[id];
    try { real.apply(Plotly, args); } catch (e) {}
  }

  // Chamado pelo showTab: as figuras da aba que abriu, agora, de uma vez.
  function flush() {
    if (!real) return 0;
    var soltar = Object.keys(fila).filter(visivel);
    soltar.forEach(solta);
    return soltar.length;
  }

  // E o resto vai desenhando em tempo ocioso, uma figura por vez, ANTES de
  // alguem clicar na aba. Sem isto o adiamento so muda o lugar da espera: a aba
  // de setores abria com cinco cards vazios de 560px, quase tres mil pixels de
  // branco, ate as figuras nascerem. Uma por callback para nao segurar o thread
  // e nao competir com o scroll.
  //
  // A figura nasce em aba escondida, que tem display:none e portanto largura
  // zero, entao sai medida errada — e o reflow do onTab a corrige quando a aba
  // aparece, que e o que a camada do painel ja fazia antes de existir fila.
  function ocioso() {
    var ids = Object.keys(fila);
    if (!ids.length) return;
    solta(ids[0]);
    agenda();
  }

  function agenda() {
    if (!real || !Object.keys(fila).length) return;
    if (window.requestIdleCallback) {
      window.requestIdleCallback(ocioso, { timeout: 600 });
    } else {
      setTimeout(ocioso, 120);
    }
  }

  // Depois do load: primeiro a aba aberta fica pronta e interativa, e so entao
  // as escondidas consomem o tempo que sobra.
  if (typeof window !== 'undefined' && window.addEventListener) {
    window.addEventListener('load', function () { setTimeout(agenda, 200); });
  }

  return {
    flush: flush,
    agenda: agenda,
    pendentes: function () { return Object.keys(fila).length; },
  };
})();
</script>"""


# ── JS do painel: retema os graficos ja renderizados e cuida do reflow ──
PANEL_JS = """
/* =====================================================================
   Camada do painel sobre a casca.

   Os graficos sao renderizados no build, pelo Python (plotly to_html), e nao
   pelo JS: eles chegam com as cores do template "jgp" do chart_builder.py, que
   sao as do modo claro. Duas consequencias tratadas aqui:

   Dark mode — a casca troca os tokens CSS sozinha, mas o SVG ja desenhado nao.
   `retema()` le os tokens --chart-* e faz um Plotly.relayout em cada figura,
   incluindo as anotacoes de convencao de sinal e as linhas de zero (add_hline
   vira shape com cor preta fixa).

   A altura fica como veio do Python. Escalar por innerHeight foi testado e
   descartado: o relayout muda o SVG mas nao o .card, e o eixo X vazava por cima
   da secao seguinte. A largura, que era o ganho de tela que importava, ja vem
   do container de 1840px da casca.
   ===================================================================== */
(function () {
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  var tok = function (n) { return getComputedStyle(document.body).getPropertyValue(n).trim(); };
  // So as figuras da aba VISIVEL. Era document.querySelectorAll, e cada troca de
  // aba e cada resize rodava resize+relayout nas figuras todas da pagina,
  // inclusive nas das abas escondidas — que tem largura zero, entao o relayout
  // nem serve para nada la. Relayout de barra empilhada repinta um retangulo por
  // ponto por serie, e era isso que travava a aba de setores.
  var plots = function () {
    var pane = document.querySelector('.tab.on');
    return [].slice.call((pane || document).querySelectorAll('.js-plotly-plot'));
  };

  function retema() {
    if (typeof Plotly === 'undefined') return;
    var ink = tok('--chart-title'), tick = tok('--chart-legend'),
        grid = tok('--chart-grid'), axis = tok('--chart-axis'),
        fundo = mq.matches ? 'rgba(26,26,25,.82)' : 'rgba(255,255,255,.78)';

    plots().forEach(function (gd) {
      var L = gd.layout || {};
      var up = {
        'font.color': ink, 'title.font.color': ink,
        'xaxis.linecolor': axis, 'xaxis.tickcolor': axis, 'xaxis.tickfont.color': tick,
        'yaxis.linecolor': axis, 'yaxis.tickcolor': axis, 'yaxis.tickfont.color': tick,
        'yaxis.gridcolor': grid, 'legend.font.color': tick
      };
      if (L.yaxis2) {
        up['yaxis2.linecolor'] = axis; up['yaxis2.tickcolor'] = axis;
        up['yaxis2.tickfont.color'] = tick; up['yaxis2.gridcolor'] = grid;
      }
      (L.annotations || []).forEach(function (a, i) {
        if (a.bgcolor) up['annotations[' + i + '].bgcolor'] = fundo;
      });
      (L.shapes || []).forEach(function (s, i) {
        var c = s.line && s.line.color;
        if (c === 'black' || c === '#000' || c === '#000000') up['shapes[' + i + '].line.color'] = axis;
      });
      try { Plotly.relayout(gd, up); } catch (e) {}
    });
  }

  // O to_html ja emite config.responsive, entao o Plotly redimensiona sozinho.
  // Este reflow existe para o caso que o dele nao cobre: a figura que nasceu com
  // largura zero em aba escondida. Com a renderizacao preguicosa isso quase nao
  // acontece mais, mas custa pouco e cobre a aba que ja estava aberta no load.
  function reflow() {
    if (typeof Plotly === 'undefined') return;
    plots().forEach(function (gd) { try { Plotly.Plots.resize(gd); } catch (e) {} });
  }

  var pend;
  function agenda() { clearTimeout(pend); pend = setTimeout(function () { reflow(); retema(); }, 80); }

  window.addEventListener('resize', agenda, { passive: true });
  if (mq.addEventListener) mq.addEventListener('change', retema);
  else if (mq.addListener) mq.addListener(retema);

  JGPChrome.init({
    // Abas escondidas tem largura zero: a figura so mede certo quando aparece.
    onTab: function () { setTimeout(function () { reflow(); retema(); }, 30); }
  });

  reflow();
  retema();
})();
"""

html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel FX Positioning &mdash; JGP Macro</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="plotly.min.js"></script>
{LAZY_JS}
<style>
{css}
</style>
</head>
{body}
<script>
{chrome}
{PANEL_JS}
</script>
</body>
</html>
"""

out = ROOT / "templates" / "dashboard.html"
out.write_text(html, encoding="utf-8")
print(f"escrito {out} — {len(html):,} bytes")
