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

  /* Tabelas emitidas pelo table_builder.py (.data-table) na moldura JGP:
     cabecalho verde, numeros tabulares, agregados com risco em cima. */
  table.data-table{border-collapse:collapse;font-size:12px;width:100%;min-width:0;max-width:none}
  table.data-table th,table.data-table td{border:1px solid var(--line);padding:3px 8px;white-space:nowrap}
  table.data-table thead th{background:var(--green);color:#fff;font-weight:700;text-align:center;
    border-color:var(--green-dark)}
  table.data-table thead th:first-child{text-align:left}
  table.data-table td.num{text-align:right;font-variant-numeric:tabular-nums}
  table.data-table td.row-label{text-align:left;font-weight:600}
  table.data-table tbody tr:hover td{background:var(--jgp-green-tint)}
  table.data-table tr.row-agg td{background:var(--sec);font-weight:700;
    border-top:2px solid var(--rule-strong)}
  .table-title{font-size:14px;font-weight:700;color:var(--chart-title);margin:0 0 1px;letter-spacing:-.01em}
  .table-subtitle{font-size:11px;color:var(--chart-sub);margin:0 0 6px;line-height:1.35}

  /* Notas de leitura dentro de um card. */
  .note{font-size:11.5px;line-height:1.55;color:var(--ink-secondary);
    border-top:1px solid var(--rule-faint);margin-top:12px;padding-top:10px}
  .note-flush{border-top:none;margin-top:0;padding-top:0}
"""
css = css.rstrip() + "\n" + SHIM_CSS

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
  var plots = function () { return [].slice.call(document.querySelectorAll('.js-plotly-plot')); };

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

  // As figuras vem sem config.responsive, entao o reflow e explicito.
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
