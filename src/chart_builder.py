"""Construcao de graficos Plotly. Cada funcao retorna HTML embeddable."""
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import pandas as pd


# ──────────────────────────────────────────────────────────────────────
# Tema JGP (casca editorial analise_html)
# ──────────────────────────────────────────────────────────────────────
# PALETTE_JGP na ordem canonica, igual aos tokens --s1..--d3 do dashboard.css.
# Semantica: verde = serie principal · preto = secundaria · cinza = neutro ·
# azul = alternativa · verde-claro = projecao · azul-claro = ano anterior ·
# laranja = alerta moderado · vermelho = alerta forte. Cor por SIGNIFICADO,
# nao por ordem de indice.
JGP_VERDE = "#00B050"
JGP_PRETO = "#1F1F1F"
JGP_CINZA = "#7F7F7F"
JGP_AZUL = "#0070C0"
JGP_VERDE_CLARO = "#92D050"
JGP_AZUL_CLARO = "#00B0F0"
JGP_LARANJA = "#FFA500"
JGP_VERMELHO = "#E63946"

PALETTE_JGP = [
    JGP_VERDE, JGP_PRETO, JGP_CINZA, JGP_AZUL,
    JGP_VERDE_CLARO, JGP_AZUL_CLARO, JGP_LARANJA, JGP_VERMELHO,
]

JGP_FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# Fundo transparente: quem pinta e o .card da casca, entao o grafico acompanha
# o papel creme no claro e a superficie escura no dark sem precisar redesenhar.
# Grade so na horizontal, espinhas pretas, titulo 14 bold — o mesmo desenho do
# funcoes_graficas_jgp/tema.py, portado para o Plotly.
pio.templates["jgp"] = go.layout.Template(layout=dict(
    font=dict(family=JGP_FONT, size=12, color=JGP_PRETO),
    title=dict(font=dict(family=JGP_FONT, size=14, color=JGP_PRETO),
               x=0.005, xanchor="left", xref="container", yref="container",
               y=0.985, yanchor="top", pad=dict(t=4, l=4)),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=PALETTE_JGP,
    xaxis=dict(
        showgrid=False, zeroline=False,
        linecolor="#000000", linewidth=1, showline=True, mirror=False,
        ticks="outside", tickcolor="#000000", ticklen=6,
        tickfont=dict(family=JGP_FONT, size=10, color="#4D4D4D"),
        title=dict(standoff=12), automargin=True,
    ),
    yaxis=dict(
        showgrid=True, gridcolor="#EBEBEB", gridwidth=1, zeroline=False,
        linecolor="#000000", linewidth=1, showline=True, mirror=False,
        ticks="outside", tickcolor="#000000", ticklen=6,
        tickfont=dict(family=JGP_FONT, size=10, color="#4D4D4D"),
        title=dict(standoff=14), automargin=True,
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                font=dict(family=JGP_FONT, size=11, color="#4D4D4D")),
    hoverlabel=dict(font=dict(family=JGP_FONT, size=11)),
))


def _to_html(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _date_strings(series: pd.Series) -> list[str]:
    """Converte Series de datas para strings formatadas (para eixo categorico)."""
    return series.dt.strftime("%Y-%m-%d").tolist()


def _apply_category_xaxis(fig: go.Figure, nticks: int = 15) -> None:
    """Configura eixo X como categorico para eliminar gaps de weekends/feriados."""
    fig.update_xaxes(
        type="category",
        nticks=nticks,
        tickangle=-45,
    )


# ──────────────────────────────────────────────────────────────────────
# Charts padrao (Pensao, Offshore, Corporate, Bancos)
# ──────────────────────────────────────────────────────────────────────
def make_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str = JGP_VERDE,
    usd_labels: bool = False,
) -> str:
    plot_df = df.dropna(subset=[x, y]).copy()
    x_str = _date_strings(plot_df[x])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_str, y=plot_df[y], mode="lines",
        line=dict(color=color, width=1.5),
        name=y,
    ))
    fig.update_layout(
        title=title, xaxis_title="", yaxis_title="USD million",
        template="jgp", height=400, margin=dict(l=50, r=20, t=64, b=60),
        showlegend=False,
    )
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=0.5)
    if usd_labels:
        _usd_side_labels(fig)
    _apply_category_xaxis(fig)
    return _to_html(fig)


def make_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str = JGP_VERDE,
    date_filter: str = "2024-01-01",
    usd_labels: bool = False,
) -> str:
    filtered = df[df[x] >= date_filter].copy() if date_filter else df.copy()
    filtered = filtered.dropna(subset=[x, y])
    x_str = _date_strings(filtered[x])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_str, y=filtered[y],
        marker_color=color, name=y,
    ))
    fig.update_layout(
        title=title, xaxis_title="", yaxis_title="USD million",
        template="jgp", height=350, margin=dict(l=50, r=20, t=64, b=60),
        showlegend=False,
    )
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=0.5)
    if usd_labels:
        _usd_side_labels(fig)
    _apply_category_xaxis(fig, nticks=12)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Dual-axis charts
# ──────────────────────────────────────────────────────────────────────
def _ranges_padronizados(y1: pd.Series, y2: pd.Series, folga: float = 1.08):
    """Um range por serie, na mesma escala padronizada: media +/- k*sigma.

    E a transformacao que faz duas series de escalas diferentes andarem "um pra
    um" no painel. O `k` e COMUM as duas e sai do maior desvio relativo
    observado, entao: as duas ficam contidas, a mais esticada toca a borda, e a
    posicao vertical de cada uma passa a ser desvio padronizado — a distancia
    entre as linhas vira diferenca de z-score, nao diferenca de unidade.

    Padronizar por sigma, e nao por max|desvio| de cada serie, evita que um
    unico spike de uma das pernas defina sozinho a escala dela e desalinhe as
    duas (na amostra inteira isso fecha ~1,7pp da distancia media).

    Simetrico em torno da media de proposito: assimetrico deslocaria as duas por
    fatores diferentes e a leitura de co-movimento se perderia. Nao ha ajuste
    melhor que este para o segundo eixo — o OLS, que minimiza a distancia
    vertical, so ganha encolhendo a segunda serie ate ela virar reta (com
    rho=0,88 empata; com rho~0 ele reduz o span dela a 2% do painel e inverte o
    eixo em cima de ruido).
    """
    a, b = y1.dropna(), y2.dropna()
    if len(a) < 2 or len(b) < 2:
        return None, None
    c1, c2 = float(a.mean()), float(b.mean())
    s1, s2 = float(a.std()), float(b.std())
    if not (s1 > 0 and s2 > 0):
        return None, None
    k = max((a - c1).abs().max() / s1, (b - c2).abs().max() / s2) * folga
    if not k > 0:
        return None, None
    return ([c1 - k * s1, c1 + k * s1], [c2 - k * s2, c2 + k * s2])


def _js_fit_1a1(
    div_id: str, y1: pd.Series, y2: pd.Series,
    rev2: bool = False, folga: float = 1.08,
) -> str:
    """Refaz os dois ranges do jeito acima a cada mudanca de janela no eixo X.

    Sem isso, os ranges cravados na montagem so servem a janela default: assim
    que o usuario expande para a amostra toda, as linhas ou achatam ou saem do
    painel. O guarda de recursao e olhar so para eventos que mexem no eixo X —
    o proprio relayout de Y dispara o evento de novo, mas com chaves de Y.
    """
    import json

    def arr(v):
        return json.dumps([None if pd.isna(z) else round(float(z), 6) for z in v])

    return f"""
<script>
(function() {{
  var alvo = {json.dumps(div_id)}, folga = {folga}, rev = {json.dumps(bool(rev2))};
  var Y = [{arr(y1)}, {arr(y2)}], EIXO = ["yaxis", "yaxis2"], n = Y[0].length;
  function ajusta(lo, hi) {{
    var i0 = Math.max(0, Math.ceil(lo)), i1 = Math.min(n - 1, Math.floor(hi));
    var est = [];
    for (var k = 0; k < 2; k++) {{
      var v = [], a = Y[k];
      for (var i = i0; i <= i1; i++) {{
        if (a[i] !== null && isFinite(a[i])) v.push(a[i]);
      }}
      if (v.length < 2) return {{}};
      var m = 0;
      v.forEach(function(z) {{ m += z; }});
      m /= v.length;
      var ss = 0, dv = 0;
      v.forEach(function(z) {{ ss += (z - m) * (z - m); dv = Math.max(dv, Math.abs(z - m)); }});
      var sd = Math.sqrt(ss / (v.length - 1));
      if (!(sd > 0)) return {{}};
      est.push({{m: m, sd: sd, dv: dv}});
    }}
    // k comum as duas series: o maior desvio relativo observado na janela
    var kk = Math.max(est[0].dv / est[0].sd, est[1].dv / est[1].sd) * folga;
    if (!(kk > 0)) return {{}};
    var up = {{}};
    for (var j = 0; j < 2; j++) {{
      var lo2 = est[j].m - kk * est[j].sd, hi2 = est[j].m + kk * est[j].sd;
      up[EIXO[j] + ".range"] = (j === 1 && rev) ? [hi2, lo2] : [lo2, hi2];
    }}
    return up;
  }}
  function liga() {{
    var gd = document.getElementById(alvo);
    if (!gd || !window.Plotly || typeof gd.on !== "function") return setTimeout(liga, 120);
    gd.on("plotly_relayout", function(ev) {{
      var mexeuX = Object.keys(ev).some(function(k) {{ return k.indexOf("xaxis") === 0; }});
      if (!mexeuX) return;
      var xr = (gd.layout.xaxis && gd.layout.xaxis.range) || [0, n - 1];
      var up = ajusta(xr[0], xr[1]);
      if (Object.keys(up).length) window.Plotly.relayout(gd, up);
    }});
  }}
  liga();
}})();
</script>
"""


def make_dual_axis_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    title: str,
    y1_name: str = "Positioning",
    y2_name: str = "USDCLP",
    y1_color: str = JGP_VERDE,
    y2_color: str = JGP_PRETO,
    invert_y2: bool = True,
    annotations: list = None,
    default_start: str = None,
    usd_labels: bool = False,
    fit_1a1: bool = False,
) -> str:
    """Duas series de escalas diferentes, uma em cada eixo Y.

    - `default_start`: data em que o painel abre. A serie inteira continua no
      grafico; e so a janela inicial do eixo X. Duplo-clique ou zoom-out devolve
      a amostra toda.
    - `usd_labels`: escreve a convencao de sinal presa ao topo e ao pe do painel,
      igual as outras abas (+ = compra de USD).
    - `fit_1a1`: padroniza os dois eixos na janela visivel para as series andarem
      quase um pra um, e refaz essa conta em JS a cada mudanca de janela.
    """
    plot_df = df.dropna(subset=[x, y1, y2]).copy()
    x_str = _date_strings(plot_df[x])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=x_str, y=plot_df[y1], name=y1_name,
                   line=dict(color=y1_color, width=2)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=x_str, y=plot_df[y2], name=y2_name,
                   line=dict(color=y2_color, width=2)),
        secondary_y=True,
    )
    fig.update_layout(
        title=title, template="jgp", height=500,
        margin=dict(l=60, r=60, t=78, b=104),
        legend=dict(orientation="h", yanchor="top", y=-0.20, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text=y1_name, secondary_y=False)
    if invert_y2:
        fig.update_yaxes(title_text=y2_name, autorange="reversed", secondary_y=True)
    else:
        fig.update_yaxes(title_text=y2_name, secondary_y=True)

    # Anotacoes ancoradas no dado (legado). Os rotulos de convencao de sinal
    # ficam com usd_labels, que os prende ao painel e sobrevive ao zoom.
    if annotations:
        y1_vals = plot_df[y1].dropna()
        y1_min = y1_vals.min() if len(y1_vals) > 0 else 0
        y1_max = y1_vals.max() if len(y1_vals) > 0 else 0
        for ann in annotations:
            y_pos = y1_max * 0.95 if ann.get("y_pos") == "top" else y1_min * 0.95
            fig.add_annotation(
                x=x_str[0], y=y_pos, xshift=6,
                text=ann["text"], showarrow=False,
                font=dict(color=ann.get("color", JGP_PRETO), size=11, weight="bold"),
                xanchor="left", bgcolor="rgba(255,255,255,0.78)", borderpad=3,
            )
        fig.add_hline(y=0, line_color="black", line_width=0.5)

    if usd_labels:
        _usd_side_labels(fig)

    _apply_category_xaxis(fig)

    # Janela inicial: o indice da primeira data >= default_start no eixo
    # categorico. Fora do range da amostra, abre inteiro.
    i0 = 0
    if default_start:
        pos = plot_df[x] >= pd.Timestamp(default_start)
        if pos.any() and not pos.all():
            i0 = int(pos.values.argmax())
            fig.update_xaxes(range=[i0 - 0.5, len(x_str) - 0.5])

    if fit_1a1:
        # Ranges da montagem: a mesma conta do JS, para o primeiro paint ja sair
        # certo em vez de piscar na escala automatica.
        janela = plot_df.iloc[i0:]
        r1, r2 = _ranges_padronizados(janela[y1], janela[y2])
        if r1:
            fig.update_yaxes(range=r1, secondary_y=False)
        if r2:
            fig.update_yaxes(
                range=r2[::-1] if invert_y2 else r2, autorange=False, secondary_y=True,
            )
        div_id = f"dual-{y1}-{y2}".lower().replace(" ", "-").replace("_", "-")
        html = fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)
        return html + _js_fit_1a1(div_id, plot_df[y1], plot_df[y2], rev2=invert_y2)

    return _to_html(fig)


def make_dual_series_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    title: str,
    y1_name: str = "Fondos de Pensiones",
    y2_name: str = "No Residentes",
    y1_color: str = JGP_VERDE,
    y2_color: str = JGP_AZUL,
) -> str:
    plot_df = df.dropna(subset=[x, y1, y2]).copy()
    x_str = _date_strings(plot_df[x])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=x_str, y=plot_df[y1], name=y1_name,
                   line=dict(color=y1_color, width=1.5)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=x_str, y=plot_df[y2], name=y2_name,
                   line=dict(color=y2_color, width=1.5)),
        secondary_y=True,
    )
    fig.update_layout(
        title=title, template="jgp", height=500,
        margin=dict(l=60, r=60, t=64, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text=y1_name, secondary_y=False)
    fig.update_yaxes(title_text=y2_name, secondary_y=True)
    _apply_category_xaxis(fig)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Offshore: as duas pernas (spot vs NDF)
# ──────────────────────────────────────────────────────────────────────
def make_offshore_corr_chart(corr_df: pd.DataFrame, title: str) -> str:
    """Correlacao movel entre as pernas (15/30/90 dias). -1 = hedge puro."""
    if corr_df.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(corr_df["Data"])
    fig = go.Figure()
    # rampa ordinal: janela mais curta clara, mais longa escura
    for col, color, width in [
        ("corr_15d", JGP_AZUL_CLARO, 1.2),
        ("corr_30d", JGP_AZUL, 1.6),
        ("corr_90d", "#004A80", 2.2),
    ]:
        if col not in corr_df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=x_str, y=corr_df[col], mode="lines",
            name=f"{col.replace('corr_', '')} úteis",
            line=dict(color=color, width=width),
            hovertemplate="%{x}<br>%{y:+.2f}<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)
    fig.add_hline(y=-0.5, line_color="gray", line_width=1, line_dash="dot")

    # Presos ao topo e ao pe do painel (yref="paper"), como os rotulos de
    # convencao de sinal das outras abas: assim sobrevivem a qualquer zoom. Aqui
    # o eixo e correlacao, nao fluxo, entao o texto explica os extremos da
    # correlacao em vez de compra e venda de USD.
    for y, text, anchor, color in [
        (0.03, "−1: espelho perfeito, o forward é só hedge do spot", "bottom", JGP_CINZA),
        (0.97, "+1: mesma direção, as duas pernas somam risco", "top", JGP_CINZA),
    ]:
        fig.add_annotation(
            xref="paper", x=0.012, y=y, yref="paper", text=text, showarrow=False,
            font=dict(color=color, size=10), xanchor="left", yanchor=anchor,
            bgcolor="rgba(255,255,255,0.75)", borderpad=3,
        )

    fig.update_layout(
        title=title, template="jgp", height=420,
        margin=dict(l=60, r=20, t=64, b=70),
        yaxis_title="correlação entre as pernas",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
    )
    fig.update_yaxes(range=[-1.05, 1.05], dtick=0.5)
    _apply_category_xaxis(fig)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Swap Camara charts
# ──────────────────────────────────────────────────────────────────────
def make_swap_line_chart(
    df: pd.DataFrame,
    tenor: str,
    title: str,
) -> str:
    """3-line chart: offshore, localexbanks, localbanks(=-total)."""
    if df.empty or len(df) < 2:
        return f"<p>Dados indisponíveis para {tenor}</p>"

    col_off = f"total_{tenor}.offshore"
    col_loc = f"total_{tenor}.localexbanks"
    col_total = f"total_{tenor}"

    for c in [col_off, col_loc, col_total]:
        if c not in df.columns:
            return f"<p>Coluna {c} não encontrada</p>"

    plot_df = df.dropna(subset=["Data", col_off, col_loc, col_total]).copy()
    if plot_df.empty:
        return f"<p>Dados indisponíveis para {tenor}</p>"

    x_str = _date_strings(plot_df["Data"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_str, y=plot_df[col_off], name="Offshore",
        line=dict(width=2, color=JGP_VERDE),
    ))
    fig.add_trace(go.Scatter(
        x=x_str, y=plot_df[col_loc], name="Local Ex Banks",
        line=dict(width=2, color=JGP_AZUL),
    ))
    fig.add_trace(go.Scatter(
        x=x_str, y=-plot_df[col_total], name="Local Banks",
        line=dict(width=2, color=JGP_LARANJA),
    ))
    fig.add_hline(y=0, line_color="black", line_width=0.5)

    y_vals = pd.concat([plot_df[col_off], plot_df[col_loc], -plot_df[col_total]]).dropna()
    y_min = y_vals.min() if len(y_vals) > 0 else 0
    y_max = y_vals.max() if len(y_vals) > 0 else 0

    fig.add_annotation(
        x=x_str[0], y=y_min * 1.1 if y_min < 0 else y_min - abs(y_max) * 0.1,
        text="Tomado", showarrow=False, font=dict(color=JGP_VERMELHO, size=10),
    )
    fig.add_annotation(
        x=x_str[0], y=y_max * 1.1 if y_max > 0 else y_max + abs(y_min) * 0.1,
        text="Aplicado", showarrow=False, font=dict(color=JGP_AZUL, size=10),
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=12)),
        template="jgp",
        height=380,
        margin=dict(l=50, r=15, t=58, b=96),
        yaxis_title="DV01",
        legend=dict(
            orientation="h", yanchor="top", y=-0.30, xanchor="left", x=0,
            font=dict(size=9),
        ),
    )
    _apply_category_xaxis(fig, nticks=10)
    return _to_html(fig)


def make_swap_delta_bars(
    deltas: dict,
    title: str,
) -> str:
    """Horizontal bar chart: 1D/7D/30D/45D/90D changes."""
    labels = list(deltas.keys())
    values = list(deltas.values())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=values, orientation="h",
        marker_color=JGP_AZUL,
    ))
    fig.update_layout(
        title=title, template="jgp", height=280,
        margin=dict(l=100, r=20, t=52, b=44),
        xaxis_title="DV01", yaxis_title="",
        showlegend=False,
    )
    fig.add_vline(x=0, line_color="black", line_width=0.5)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Colombia charts
# ──────────────────────────────────────────────────────────────────────
def make_colombia_line_chart(
    df: pd.DataFrame,
    date_filter: str = "2017-01-01",
) -> str:
    filtered = df[df["Fecha"] >= date_filter].copy()
    cols_to_check = [c for c in ["Extranjero", "FPC", "RestoyReal"] if c in filtered.columns]
    filtered = filtered.dropna(subset=["Fecha"] + cols_to_check)
    x_str = _date_strings(filtered["Fecha"])

    fig = go.Figure()
    for col, color in [
        ("Extranjero", JGP_VERDE),
        ("FPC", JGP_AZUL),
        ("RestoyReal", JGP_LARANJA),
    ]:
        if col in filtered.columns:
            fig.add_trace(go.Scatter(
                x=x_str, y=filtered[col],
                name=col, line=dict(width=1.2, color=color),
            ))
    fig.add_hline(y=0, line_color="black", line_width=0.5)
    fig.update_layout(
        title="Saldos de compra e venda de contratos fwd (USD million)",
        template="jgp", height=400,
        margin=dict(l=50, r=20, t=64, b=60),
        yaxis_title="USD million",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _apply_category_xaxis(fig)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Fluxo AFP: NDF + spot
# ──────────────────────────────────────────────────────────────────────
# Cores fixas das duas pernas, usadas em todos os graficos da aba.
AFP_LEG_COLORS = {
    "ndf": JGP_VERDE,
    "bcch": JGP_AZUL,
}


def _side_labels(fig: go.Figure, topo: str, pe: str) -> None:
    """Escreve a convencao de sinal no topo e no pe do painel.

    Ancorado em `yref="paper"`, nao no eixo de dados: assim os rotulos ficam
    presos ao topo e ao pe do painel e sobrevivem a qualquer zoom manual. Com
    coordenada de dados eles ficavam parados no y em que foram desenhados e
    saiam de vista assim que a escala mudava.
    """
    for y, anchor, text, color in [
        (0.97, "top", topo, JGP_VERDE),
        (0.03, "bottom", pe, JGP_VERMELHO),
    ]:
        fig.add_annotation(
            xref="paper", x=0.012, y=y, yref="paper", text=text, showarrow=False,
            font=dict(color=color, size=11), xanchor="left", yanchor=anchor,
            bgcolor="rgba(255,255,255,0.75)", borderpad=3,
        )


def _clp_side_labels(fig: go.Figure) -> None:
    """Convencao das abas de fundos de pensao e offshore: + = compra de CLP."""
    _side_labels(
        fig,
        "▲ acima de zero: comprando CLP (vendendo USD)",
        "▼ abaixo de zero: vendendo CLP (comprando USD)",
    )


def _usd_side_labels(fig: go.Figure) -> None:
    """Convencao das abas de setores e de fundos de pensao: + = compra de USD."""
    _side_labels(
        fig,
        "▲ acima de zero: comprando USD (vendendo CLP)",
        "▼ abaixo de zero: vendendo USD (comprando CLP)",
    )


def make_afp_5d_bars(legs: dict) -> str:
    """Uma barra por perna com o acumulado dos ultimos 5 pregoes.

    A janela fecha na ancora comum as duas pernas, que pode ser anterior ao
    ultimo dado da aba de Fundos de Pensao: por isso a data entra no rotulo.
    """
    if not legs:
        return "<p>Dados do fluxo AFP indisponíveis</p>"

    ancora = legs["anchor"].strftime("%d/%m")
    items = [
        (f"NDF<br><span style='font-size:11px'>Δ saldo BCCh até {ancora}</span>",
         legs["ndf"], AFP_LEG_COLORS["ndf"]),
        (f"SPOT (observado)<br><span style='font-size:11px'>BCCh setor 42 até {ancora}</span>",
         legs["spot_bcch"], AFP_LEG_COLORS["bcch"]),
    ]
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = [i[2] for i in items]

    janela = (
        f"{legs['start'].strftime('%d/%m')} a "
        f"{legs['anchor'].strftime('%d/%m/%Y')}"
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v:+,.0f}" for v in values],
        textposition="outside",
        textfont=dict(size=15),
        hovertemplate="%{x}<br>%{y:+,.0f} mm USD<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="black", line_width=1)

    lim = max(abs(v) for v in values) * 1.45 if any(values) else 1.0
    fig.update_layout(
        title=(
            "FUNDOS DE PENSÃO: 5 PREGÕES — NDF vs SPOT "
            f"<span style='font-size:13px;color:#666'>({janela})</span>"
        ),
        template="jgp", height=460,
        margin=dict(l=60, r=20, t=84, b=80),
        yaxis_title="USD million acumulado",
        showlegend=False, bargap=0.45,
    )
    fig.update_yaxes(range=[-lim, lim])
    _usd_side_labels(fig)
    return _to_html(fig)


def make_weekly_legs_bars(
    wk: pd.DataFrame, title: str, weeks_default: int = 12,
    stacked: bool = False, usd: bool = False, date_col: str = "Semana",
) -> str:
    """Barras por semana com as duas pernas e a linha do net.

    Serve as duas abas que tem pernas de NDF e spot, mas elas divergem em duas
    coisas, daí os parametros:

    - `stacked`: empilhado (aba dos AFPs) ou agrupado (offshore ajustado). No
      empilhado as barras ficam translucidas, para a linha do net atras nao
      sumir e para as duas pernas se lerem sobrepostas quando tem sinais iguais.
    - `usd`: convencao de compra-de-USD (aba dos AFPs) ou de compra-de-CLP
      (offshore ajustado).
    - `date_col`: "Semana" para o agregado semanal, "Data" para as versoes
      diarias rolantes. `weeks_default` passa a contar observacoes, nao semanas.
    """
    if wk.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(wk[date_col])
    series = [
        ("ndf_wk", "NDF (Δ saldo na semana)", AFP_LEG_COLORS["ndf"]),
        ("bcch_wk", "Spot observado (BCCh)", AFP_LEG_COLORS["bcch"]),
    ]

    fig = go.Figure()
    for col, name, color in series:
        fig.add_trace(go.Bar(
            x=x_str, y=wk[col], name=name,
            marker=dict(color=color, opacity=0.62 if stacked else 1.0),
            hovertemplate=f"semana de %{{x}}<br>{name}: %{{y:+,.0f}} mm USD<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=x_str, y=wk["net_wk"], name="Net (NDF + spot)", mode="lines+markers",
        line=dict(color="black", width=1.5),
        marker=dict(color="black", size=5, symbol="diamond"),
        hovertemplate="semana de %{x}<br>net: %{y:+,.0f} mm USD<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    fig.update_layout(
        title=title,
        barmode="relative" if stacked else "group",
        bargap=0.2 if stacked else 0.25, bargroupgap=0.05,
        template="jgp", height=440,
        margin=dict(l=60, r=20, t=64, b=70),
        yaxis_title=f"USD million (+ compra de {'USD' if usd else 'CLP'})",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _apply_category_xaxis(fig, nticks=14)

    # Abre nas ultimas N semanas: com o historico inteiro visivel as barras
    # recentes ficam achatadas. Duplo-clique devolve a serie toda.
    n = len(x_str)
    visivel = wk.tail(weeks_default) if n > weeks_default else wk
    if stacked:
        v = visivel[[c for c, _, _ in series]]
        lim = max(
            v.clip(lower=0).sum(axis=1).max(),
            v.clip(upper=0).sum(axis=1).abs().max(),
            visivel["net_wk"].abs().max(),
        ) * 1.20
    else:
        vals = pd.concat(
            [visivel[c] for c, _, _ in series] + [visivel["net_wk"]]
        ).dropna()
        lim = vals.abs().max() * 1.30 if len(vals) else 1.0
    lim = lim if lim and lim > 0 else 1.0
    fig.update_yaxes(range=[-lim, lim])
    (_usd_side_labels if usd else _clp_side_labels)(fig)
    if n > weeks_default:
        fig.update_xaxes(range=[n - weeks_default - 0.5, n - 0.5])
    return _to_html(fig)


def make_afp_level_line(afp_df: pd.DataFrame, title: str) -> str:
    """Nivel do saldo forward do setor 42, diario.

    Sem os rotulos de compra/venda de USD: aqui acima de zero significa AFP net
    LONG USD, que e estoque e nao fluxo, e reaproveitar o rotulo de fluxo dos
    outros paineis confundiria. A leitura vai no titulo.
    """
    d = afp_df.dropna(subset=["ndf_level"])
    if d.empty:
        return "<p>Dados indisponíveis</p>"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=_date_strings(d["Data"]), y=d["ndf_level"], mode="lines",
        line=dict(color=AFP_LEG_COLORS["ndf"], width=1.5),
        hovertemplate="%{x}<br>%{y:+,.0f} mm USD<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="black", line_width=0.5)
    fig.update_layout(
        title=title, template="jgp", height=400,
        margin=dict(l=60, r=20, t=64, b=60),
        yaxis_title="USD million (+ AFP long USD)",
        showlegend=False,
    )
    _apply_category_xaxis(fig)
    return _to_html(fig)


def make_afp_daily_bars(afp_df: pd.DataFrame, col: str, title: str, color: str) -> str:
    """Fluxo diario de uma perna (ou do net), em compra-de-USD."""
    d = afp_df.dropna(subset=[col])
    if d.empty:
        return "<p>Dados indisponíveis</p>"

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=_date_strings(d["Data"]), y=d[col], marker_color=color,
        hovertemplate="%{x}<br>%{y:+,.0f} mm USD<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    lim = d[col].abs().max() * 1.25
    fig.update_layout(
        title=title, template="jgp", height=400,
        margin=dict(l=60, r=20, t=64, b=60),
        yaxis_title="USD million (+ compra de USD)",
        showlegend=False,
    )
    fig.update_yaxes(range=[-lim, lim])
    _usd_side_labels(fig)
    _apply_category_xaxis(fig)
    return _to_html(fig)


# Mesmas cores que a aba de setores da a esses dois: a cor segue a entidade, para
# o leitor reconhecer as series entre abas.
NET_SECTOR_COLORS = {"pension": "#377eb8", "offshore": "#ff7f00", "total": "#111827"}


def make_net_comparison_chart(df: pd.DataFrame, title: str) -> str:
    """Net semanal dos fundos de pensao, do offshore e a soma, em compra-de-USD."""
    if df.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(df["Semana"])
    fig = go.Figure()
    for col, name, color, dash, width in [
        ("net_pension", "Fundos de pensão (NDF + spot)",
         NET_SECTOR_COLORS["pension"], "solid", 1.8),
        ("net_offshore", "Offshore (NDF + spot)",
         NET_SECTOR_COLORS["offshore"], "solid", 1.8),
        # A soma vai tracejada e em preto para ler como serie derivada, nao como
        # um terceiro setor.
        ("net_total", "Soma dos dois", NET_SECTOR_COLORS["total"], "dash", 2.2),
    ]:
        fig.add_trace(go.Scatter(
            x=x_str, y=df[col], name=name, mode="lines",
            line=dict(color=color, width=width, dash=dash),
            hovertemplate=f"semana de %{{x}}<br>{name}: %{{y:+,.0f}} mm USD<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    fig.update_layout(
        title=title, template="jgp", height=440,
        margin=dict(l=60, r=20, t=64, b=70),
        yaxis_title="USD million (+ compra de USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    vals = pd.concat([df["net_pension"], df["net_offshore"], df["net_total"]]).dropna()
    lim = vals.abs().max() * 1.15 if len(vals) else 1.0
    fig.update_yaxes(range=[-lim, lim])
    _usd_side_labels(fig)
    _apply_category_xaxis(fig, nticks=14)
    return _to_html(fig)


# Paleta categorica dos setores: Set1 do ColorBrewer, na ordem em que empilham.
# A ordem importa tanto quanto as cores — num empilhado so os vizinhos se tocam,
# entao ela foi escolhida para maximizar a separacao entre pares adjacentes.
# Validado (dataviz/validate_palette.js, superficie clara): pior par adjacente
# com dE 17,2 em protanopia e 20,1 na visao normal, sem WARN.
#
# Em todos os pares, e nao so os adjacentes, nenhuma paleta de sete matizes
# passa: o pior par vira marrom x vermelho com dE 13,0. Isso e limite do numero
# de series, nao desta escolha — testados Okabe-Ito, Tableau10 e varias
# substituicoes, todos falham igual ou pior. O alivio e o previsto para o caso:
# as tres tabelas da mesma aba nomeiam cada setor com os seus numeros, entao a
# identidade nunca depende so da cor.
SECTOR_LINE_COLORS = {
    "Fondos de pensiones": "#377eb8",      # azul
    "Companias de seguros": "#4daf4a",     # verde
    "Empresas sector real": "#984ea3",     # roxo
    "Corredoras de bolsa": "#e41a1c",      # vermelho
    "Adm generales de fondos": "#f781bf",  # rosa
    "Otros sectores": "#a65628",           # marrom
    "No residentes": "#ff7f00",            # laranja
    "TOTAL (todos os setores)": "#111827",
}


def make_sector_weekly_stacked(
    wk: pd.DataFrame, title: str, weeks_default: int = 26,
) -> str:
    """Net semanal empilhado por setor, em compra-de-USD.

    Barras empilhadas em vez de linhas: a pergunta da aba e de composicao — quem
    compra e quem vende CLP na semana — e sete linhas cruzando zero nao mostram
    isso. Com barmode relative os compradores empilham para cima e os vendedores
    para baixo.

    O total vai como linha com marcadores e nao como barra: numa pilha com sinais
    dos dois lados a altura liquida nao e visivel, e a linha liga onde as duas
    pilhas se encontram em cada semana.
    """
    if wk.empty or len(wk.columns) < 2:
        return "<p>Dados indisponíveis</p>"

    # Data curta: com 26 barras e rotulo -45 graus, "2026-08-28" nao cabe.
    x_str = wk["Semana"].dt.strftime("%d/%m/%y").tolist()
    total_col = next((c for c in wk.columns if c.startswith("TOTAL")), None)
    setores = [c for c in wk.columns if c != "Semana" and c != total_col]

    fig = go.Figure()
    for col in setores:
        fig.add_trace(go.Bar(
            x=x_str, y=wk[col], name=col,
            marker=dict(
                color=SECTOR_LINE_COLORS.get(col),
                # Fio branco entre segmentos: separa as fatias sem depender do
                # contraste entre as cores vizinhas.
                line=dict(color="white", width=1),
            ),
            hovertemplate=f"{col}: %{{y:+,.0f}} mm USD<extra></extra>",
        ))
    if total_col:
        fig.add_trace(go.Scatter(
            x=x_str, y=wk[total_col], name=total_col, mode="lines+markers",
            line=dict(color="black", width=2),
            marker=dict(color="black", size=6, symbol="diamond",
                        line=dict(color="white", width=1)),
            hovertemplate=f"{total_col}: %{{y:+,.0f}} mm USD<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    fig.update_layout(
        title=title, barmode="relative", bargap=0.2,
        template="jgp", height=560,
        margin=dict(l=60, r=20, t=64, b=170),
        yaxis_title="USD million (+ compra de USD)",
        # A legenda tem oito entradas e quebra em duas linhas. Empurrada para
        # baixo dos rotulos de data, com margem inferior que cabe as duas coisas.
        legend=dict(orientation="h", yanchor="top", y=-0.30, xanchor="left", x=0),
        hovermode="x unified",
    )
    # nticks e nao dtick=1: com o historico todo aberto (222 semanas) forcar um
    # rotulo por barra vira borrao. O Plotly rareia sozinho conforme o zoom.
    fig.update_xaxes(type="category", tickangle=-45, nticks=14)

    n = len(x_str)
    visivel = wk.tail(weeks_default) if n > weeks_default else wk
    # Numa pilha o alcance e a soma dos positivos e a dos negativos da semana,
    # nao o maior setor isolado.
    v = visivel[setores]
    lim = max(
        v.clip(lower=0).sum(axis=1).max(),
        v.clip(upper=0).sum(axis=1).abs().max(),
    ) * 1.15
    lim = lim if lim and lim > 0 else 1.0
    fig.update_yaxes(range=[-lim, lim])
    _usd_side_labels(fig)
    if n > weeks_default:
        fig.update_xaxes(range=[n - weeks_default - 0.5, n - 0.5])
    return _to_html(fig)


def make_afp_levels_chart(
    df: pd.DataFrame, title: str, ancora=None, nivel_ancora: float = None,
) -> str:
    """Niveis rebaseados das duas pernas, com o residuo sombreado contra o zero.

    O sombreado e `ndf + spot`, e nao o vao entre as duas linhas: as pernas sao
    espelhos, entao o vao vale cerca do dobro de cada uma e nao corresponde a
    posicao nenhuma. O residuo e a parte comprada de USD que o forward nao
    cobriu — colado no zero quando o hedge esta apertado.

    `ancora` e `nivel_ancora` montam o subtitulo, que precisa dizer duas coisas:
    que o eixo e variacao e nao posicao, e qual era o saldo naquele dia, que e o
    tamanho que o rebasement esconde.
    """
    if df.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(df["Data"])
    fig = go.Figure()

    # Sombreado primeiro, para as linhas ficarem por cima.
    fig.add_trace(go.Scatter(
        x=x_str, y=df["residuo"], name="Resíduo (NDF + spot, não hedgeado)",
        mode="lines", line=dict(color="#111827", width=1.2),
        fill="tozeroy", fillcolor="rgba(17,24,39,0.22)",
        hovertemplate="resíduo: %{y:+,.0f} mm USD<extra></extra>",
    ))
    for col, name, color in [
        ("ndf", "Δ saldo NDF (rebaseado)", AFP_LEG_COLORS["ndf"]),
        ("spot", "Spot acumulado", AFP_LEG_COLORS["bcch"]),
    ]:
        fig.add_trace(go.Scatter(
            x=x_str, y=df[col], name=name, mode="lines",
            line=dict(color=color, width=1.8),
            hovertemplate=f"{name}: %{{y:+,.0f}} mm USD<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    vals = pd.concat([df["ndf"], df["spot"], df["residuo"]]).dropna()
    lim = vals.abs().max() * 1.12 if len(vals) else 1.0
    if ancora is not None:
        sub = (
            f"as duas séries partem de zero em "
            f"{pd.Timestamp(ancora).strftime('%d/%m/%Y')}: o eixo é "
            f"<b>variação desde então</b>, não posição"
        )
        if nivel_ancora is not None:
            sub += f" &mdash; o saldo de NDF naquele dia era {nivel_ancora:+,.0f} mm USD"
        title = (
            f"{title}<br><span style='font-size:12px;color:#666'>{sub}</span>"
        )

    fig.update_layout(
        title=title, template="jgp", height=470,
        margin=dict(l=70, r=20, t=96, b=70),
        yaxis_title="USD million desde a âncora (+ compra de USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_yaxes(range=[-lim, lim])
    _usd_side_labels(fig)
    _apply_category_xaxis(fig)
    return _to_html(fig)
