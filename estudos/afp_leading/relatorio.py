"""Relatorio HTML do estudo, no tema do painel."""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from chart_builder import JGP_VERDE, JGP_PRETO, JGP_AZUL  # noqa: E402


def _fig_estrutura(tab: pd.DataFrame, tipo: str, titulo: str) -> str:
    d = tab[tab["tipo"] == tipo].sort_values("n")
    cores = [JGP_AZUL if u else "#C9C9C4" for u in d["utilizavel"]]
    fig = go.Figure(go.Bar(
        x=d["n"], y=d["r2"], marker_color=cores,
        hovertemplate="n=%{x}<br>R2=%{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=titulo, template="jgp", height=340,
        margin=dict(l=60, r=20, t=64, b=60),
        xaxis_title="defasagem (pregoes)", yaxis_title="R2 dentro de amostra",
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _fig_beta(bm: pd.DataFrame, bm_janela: pd.DataFrame) -> str:
    d = bm.dropna(subset=["beta"])
    d_j = bm_janela.dropna(subset=["beta"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["Data"], y=d["beta"], mode="lines", name="expansivel",
        line=dict(color=JGP_VERDE, width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=d_j["Data"], y=d_j["beta"], mode="lines", name="movel 252 dias",
        line=dict(color=JGP_AZUL, width=1.2),
    ))
    fig.add_hline(y=0, line=dict(color=JGP_PRETO, width=1, dash="dot"))
    fig.update_layout(
        title="Beta em janela expansivel e movel",
        template="jgp", height=360, margin=dict(l=60, r=20, t=64, b=96),
        yaxis_title="USD milhoes por unidade de retorno",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _fig_previsto(p: pd.DataFrame) -> str:
    d = p.dropna(subset=["realizado", "previsto"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["Data"], y=d["realizado"], mode="lines",
                             name="realizado", line=dict(color=JGP_PRETO, width=1)))
    fig.add_trace(go.Scatter(x=d["Data"], y=d["previsto"], mode="lines",
                             name="previsto", line=dict(color=JGP_VERDE, width=1.5)))
    fig.update_layout(
        title="Fluxo AFP: previsto fora de amostra vs realizado",
        template="jgp", height=400, margin=dict(l=60, r=20, t=64, b=96),
        yaxis_title="USD milhoes (+ compra de USD)",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _tabela_decisao(criterios: list[tuple[str, bool, str]]) -> str:
    linhas = []
    for nome, ok, detalhe in criterios:
        marca = "PASSOU" if ok else "FALHOU"
        cor = JGP_VERDE if ok else "#E63946"
        linhas.append(
            f"<tr><td>{nome}</td>"
            f"<td style='color:{cor};font-weight:700'>{marca}</td>"
            f"<td>{detalhe}</td></tr>"
        )
    return (
        "<table class='data-table'><thead><tr>"
        "<th>Criterio</th><th>Resultado</th><th>Detalhe</th>"
        "</tr></thead><tbody>" + "".join(linhas) + "</tbody></table>"
    )


def gerar(
    caminho: Path,
    spec,
    tab: pd.DataFrame,
    bm: pd.DataFrame,
    bm_janela: pd.DataFrame,
    prev: pd.DataFrame,
    aval: dict,
    criterios: list[tuple[str, bool, str]],
    veredito: bool,
    n_painel: int,
    beta_vencedora: float,
) -> Path:
    """Escreve o HTML. Nao decide nada: so mostra o que as outras pecas mediram."""
    titulo_veredito = (
        "RESULTADO POSITIVO: a hipotese sobreviveu"
        if veredito else
        "RESULTADO NEGATIVO: a hipotese nao passou"
    )
    m = aval["metades"]
    if beta_vencedora < 0:
        texto_beta = (
            "O beta so se traduz em exposicao hedgeada implicita "
            "(h*A = -beta/1000, em USD bilhoes) quando e negativo, conforme a convencao de "
            "sinal descrita acima. Como o beta da especificacao vencedora e negativo, o "
            "grafico acima poderia ser lido como h*A; ele mostra o beta diretamente para "
            "manter a mesma escala das outras especificacoes da tabela."
        )
    else:
        texto_beta = (
            "O beta so se traduz em exposicao hedgeada implicita "
            "(h*A = -beta/1000, em USD bilhoes) quando e negativo, conforme a convencao de "
            "sinal descrita acima. Com beta positivo, como na especificacao vencedora, essa "
            "traducao nao tem sentido economico: e por isso que o grafico acima mostra o "
            "beta diretamente, e nao um h*A."
        )
    corpo = f"""
<h2>Veredito</h2>
<p class="lead"><b>{titulo_veredito}</b></p>
<p class="sub">Especificacao vencedora: alvo <code>{spec.alvo}</code>,
preditor <code>{spec.preditor}</code>, {spec.tipo} n={spec.n}.
R2 fora de amostra {aval['r2_oos']:.3f} em {aval['nobs']} observacoes,
correlacao {aval['corr']:.3f}, erro absoluto medio de
USD {aval['mae_usd_mm']:,.0f} mm.</p>
<div class="card">{_tabela_decisao(criterios)}</div>

<h2>Estrutura de defasagem</h2>
<p class="sub">Cinza = nao utilizavel. O MXWO fecha depois do mercado cambial
chileno, entao o retorno do mesmo dia (k=0) nao estaria disponivel a tempo.</p>
<div class="card">{_fig_estrutura(tab, 'pontual', 'Defasagem pontual: R2 por k')}</div>
<div class="card">{_fig_estrutura(tab, 'acumulada', 'Janela acumulada: R2 por w')}</div>

<h2>Estabilidade do beta</h2>
<div class="card">{_fig_beta(bm, bm_janela)}</div>
<p class="sub">{texto_beta}</p>

<h2>Previsto vs realizado</h2>
<p class="sub">Previsao em cada dia usa coeficientes ajustados apenas com dado
anterior aquele dia.</p>
<div class="card">{_fig_previsto(prev)}</div>

<h2>Split de amostra</h2>
<div class="card"><table class="data-table">
<thead><tr><th>Metade</th><th>beta</th><th>t-stat</th><th>R2</th><th>n</th></tr></thead>
<tbody>
<tr><td>Primeira</td><td class="num">{m['primeira']['beta']:,.0f}</td>
<td class="num">{m['primeira']['tstat']:.2f}</td>
<td class="num">{m['primeira']['r2']:.3f}</td>
<td class="num">{m['primeira']['nobs']}</td></tr>
<tr><td>Segunda</td><td class="num">{m['segunda']['beta']:,.0f}</td>
<td class="num">{m['segunda']['tstat']:.2f}</td>
<td class="num">{m['segunda']['r2']:.3f}</td>
<td class="num">{m['segunda']['nobs']}</td></tr>
</tbody></table></div>

<h2>Limitacoes</h2>
<p class="sub">{n_painel:,} observacoes no painel, e nao ha mais: e o limite do
dado do BCCh ({aval['nobs']:,} entraram na regressao vencedora fora de
amostra, apos o treino minimo). Cada metade do split cobre ~2 anos, entao o
teste de estabilidade e tambem um teste de regime e os dois nao dao para
separar. A vencedora foi escolhida entre ~32 especificacoes; o criterio de
plateau mitiga a busca, nao a elimina. Nada aqui tem custo de transacao: e
medida de relacao estatistica, nao de P&amp;L.</p>
"""

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fluxo AFP previsto &mdash; JGP Macro</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
:root{{--bg:#F6F4EE;--card:#fff;--ink:#0A0A0A;--ink2:#4A4A48;--ink3:#8C8C88;
--verde:#00B050;--rule:#DDD9CE;--faint:#ECE8DC;--sec:#E4E0D3;--line:#DDD9CE;
--green:#00B050;--green-dark:#008A3F;--chart-title:#1F1F1F;--chart-sub:#666}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--ink);
font-size:15px;line-height:1.55;padding:2rem clamp(1rem,4vw,4rem) 4rem;max-width:1500px;margin:0 auto}}
h1{{font-size:2.2rem;font-weight:700;letter-spacing:-.028em;margin-bottom:.4rem}}
h2{{counter-increment:s;display:flex;gap:.7rem;align-items:baseline;font-size:1.02rem;
font-weight:600;margin:2rem 0 .9rem;padding-bottom:.5rem;border-bottom:1px dashed var(--rule)}}
h2::before{{content:counter(s,decimal-leading-zero);font-size:.78rem;color:var(--verde);font-weight:600}}
body{{counter-reset:s}}
.lead{{font-size:1rem;color:var(--ink2);margin-bottom:12px}}
.sub{{font-size:12.5px;color:var(--ink3);margin-bottom:12px;line-height:1.6}}
.card{{background:var(--card);border:1px solid var(--faint);padding:.75rem .9rem;margin-bottom:14px}}
table.data-table{{border-collapse:collapse;font-size:12px;width:100%}}
table.data-table th,table.data-table td{{border:1px solid var(--line);padding:5px 10px}}
table.data-table thead th{{background:var(--green);color:#fff;font-weight:700;border-color:var(--green-dark)}}
table.data-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
code{{background:rgba(0,176,80,.08);padding:1px 4px;font-size:.92em}}
.meta{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink3);margin-bottom:2rem}}
</style></head><body>
<h1>Fluxo AFP previsto a partir de bolsa global</h1>
<div class="meta">JGP Emerging Markets &middot; Chile &middot; gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}</div>
{corpo}
</body></html>"""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(html, encoding="utf-8")
    return caminho
