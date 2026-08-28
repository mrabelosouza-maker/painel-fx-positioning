"""Construcao de graficos Plotly. Cada funcao retorna HTML embeddable."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


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
    color: str = "dodgerblue",
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
        template="plotly_white", height=400, margin=dict(l=50, r=20, t=50, b=60),
        showlegend=False,
    )
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=0.5)
    _apply_category_xaxis(fig)
    return _to_html(fig)


def make_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str = "dodgerblue",
    date_filter: str = "2024-01-01",
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
        template="plotly_white", height=350, margin=dict(l=50, r=20, t=50, b=60),
        showlegend=False,
    )
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=0.5)
    _apply_category_xaxis(fig, nticks=12)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Dual-axis charts
# ──────────────────────────────────────────────────────────────────────
def make_dual_axis_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    title: str,
    y1_name: str = "Positioning",
    y2_name: str = "USDCLP",
    y1_color: str = "dodgerblue",
    y2_color: str = "red",
    invert_y2: bool = True,
    annotations: list = None,
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
        title=title, template="plotly_white", height=500,
        margin=dict(l=60, r=60, t=50, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text=y1_name, secondary_y=False)
    if invert_y2:
        fig.update_yaxes(title_text=y2_name, autorange="reversed", secondary_y=True)
    else:
        fig.update_yaxes(title_text=y2_name, secondary_y=True)

    # Anotacoes (ex: "Long USD" / "Short USD")
    if annotations:
        y1_vals = plot_df[y1].dropna()
        y1_min = y1_vals.min() if len(y1_vals) > 0 else 0
        y1_max = y1_vals.max() if len(y1_vals) > 0 else 0
        for ann in annotations:
            y_pos = y1_max * 0.95 if ann.get("y_pos") == "top" else y1_min * 0.95
            fig.add_annotation(
                x=x_str[0], y=y_pos,
                text=ann["text"], showarrow=False,
                font=dict(color=ann.get("color", "black"), size=11, weight="bold"),
                xanchor="left",
            )
        fig.add_hline(y=0, line_color="black", line_width=0.5)

    _apply_category_xaxis(fig)
    return _to_html(fig)


def make_dual_series_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    title: str,
    y1_name: str = "Fondos de Pensiones",
    y2_name: str = "No Residentes",
    y1_color: str = "dodgerblue",
    y2_color: str = "darkorange",
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
        title=title, template="plotly_white", height=500,
        margin=dict(l=60, r=60, t=50, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text=y1_name, secondary_y=False)
    fig.update_yaxes(title_text=y2_name, secondary_y=True)
    _apply_category_xaxis(fig)
    return _to_html(fig)


# ──────────────────────────────────────────────────────────────────────
# Offshore: as duas pernas (spot vs NDF)
# ──────────────────────────────────────────────────────────────────────
def _long_short_labels(fig: go.Figure, ymax: float, ymin: float) -> None:
    """Marca no grafico que acima de zero e long USD e abaixo e short USD."""
    for y, text, color in [
        (ymax * 0.88, "▲ acima de zero: comprando USD (long USD)", "green"),
        (ymin * 0.88, "▼ abaixo de zero: vendendo USD (short USD)", "red"),
    ]:
        fig.add_annotation(
            xref="paper", x=0.01, y=y, yref="y", text=text, showarrow=False,
            font=dict(color=color, size=11), xanchor="left",
            bgcolor="rgba(255,255,255,0.75)",
        )


def make_weekly_legs_bars(
    wk: pd.DataFrame,
    title: str,
    weeks_default: int = 12,
) -> str:
    """Barras agrupadas por semana: perna spot e variacao do NDF, em long USD.

    Abre mostrando as ultimas `weeks_default` semanas; duplo-clique no grafico
    devolve a serie inteira (autoscale nativo do Plotly).
    """
    if wk.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(wk["Semana"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_str, y=wk["spot_wk"], name="Spot (fluxo da semana)",
        marker_color="darkorange",
        hovertemplate="semana de %{x}<br>spot: %{y:+,.0f} mm USD<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=x_str, y=wk["dndf_wk"], name="NDF (Δ saldo na semana)",
        marker_color="dodgerblue",
        hovertemplate="semana de %{x}<br>Δ NDF: %{y:+,.0f} mm USD<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    fig.update_layout(
        title=title, barmode="group", bargap=0.25, bargroupgap=0.05,
        template="plotly_white", height=420,
        margin=dict(l=60, r=20, t=50, b=70),
        yaxis_title="USD million (+ long USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _apply_category_xaxis(fig, nticks=14)

    # Janela inicial: ultimas N semanas (eixo categorico -> range por indice).
    # O eixo y escala para essa janela, senao as barras ficam achatadas contra
    # os extremos do historico. Duplo-clique faz autoscale dos dois eixos.
    n = len(x_str)
    visivel = wk.tail(weeks_default) if n > weeks_default else wk
    vals = pd.concat([visivel["spot_wk"], visivel["dndf_wk"]]).dropna()
    lim = vals.abs().max() * 1.30 if len(vals) else 1.0
    fig.update_yaxes(range=[-lim, lim])
    _long_short_labels(fig, lim, -lim)
    if n > weeks_default:
        fig.update_xaxes(range=[n - weeks_default - 0.5, n - 0.5])
    return _to_html(fig)


def make_weekly_legs_scatter(wk: pd.DataFrame, title: str) -> str:
    """Scatter semanal: spot no x, Δ NDF no y, cor = tempo.

    Pontos sobre a diagonal y = -x significam hedge perfeito na semana.
    """
    if wk.empty:
        return "<p>Dados indisponíveis</p>"

    t = wk["Semana"]
    tnum = (t - t.min()).dt.days
    # ticks da colorbar em datas legiveis
    idx = [0, len(t) // 3, 2 * len(t) // 3, len(t) - 1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=wk["spot_wk"], y=wk["dndf_wk"], mode="markers",
        marker=dict(
            size=9, color=tnum, colorscale="Viridis",
            showscale=True, line=dict(width=1, color="white"),
            colorbar=dict(
                title=dict(text="semana", side="right"), thickness=12,
                tickvals=[tnum.iloc[i] for i in idx],
                ticktext=[t.iloc[i].strftime("%b-%y") for i in idx],
            ),
        ),
        customdata=_date_strings(t),
        hovertemplate=("semana de %{customdata}<br>spot: %{x:+,.0f}"
                       "<br>Δ NDF: %{y:+,.0f}<extra></extra>"),
    ))

    # Escalas independentes: o Δ NDF tem varias vezes a dispersao do spot, e
    # forcar escala igual colapsa a nuvem numa faixa. A reta y = -x continua
    # correta em coordenadas de dado, so nao aparece a 45 graus -- por isso o
    # rotulo diz a relacao em vez de depender da inclinacao.
    xlim = wk["spot_wk"].abs().max() * 1.15
    ylim = wk["dndf_wk"].abs().max() * 1.15
    fig.add_shape(type="line", x0=-xlim, y0=xlim, x1=xlim, y1=-xlim,
                  line=dict(color="gray", width=1, dash="dash"))
    fig.add_annotation(
        x=-xlim * 0.80, y=xlim * 0.80, text="hedge perfeito (y = −x)",
        showarrow=False, font=dict(color="gray", size=10),
        yanchor="bottom", bgcolor="rgba(255,255,255,0.75)",
    )
    fig.add_hline(y=0, line_color="black", line_width=0.5)
    fig.add_vline(x=0, line_color="black", line_width=0.5)
    fig.update_layout(
        title=title, template="plotly_white", height=420,
        margin=dict(l=60, r=20, t=50, b=60),
        xaxis_title="Spot na semana (USD mm, + long USD)",
        yaxis_title="Δ NDF na semana (USD mm, + long USD)",
        showlegend=False,
    )
    fig.update_xaxes(range=[-xlim, xlim], zeroline=False)
    fig.update_yaxes(range=[-ylim, ylim], zeroline=False)
    return _to_html(fig)


def make_offshore_corr_chart(corr_df: pd.DataFrame, title: str) -> str:
    """Correlacao movel entre as pernas (15/30/90 dias). -1 = hedge puro."""
    if corr_df.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(corr_df["Data"])
    fig = go.Figure()
    # rampa ordinal: janela mais curta clara, mais longa escura
    for col, color, width in [
        ("corr_15d", "#86b6ef", 1.2),
        ("corr_30d", "#2a78d6", 1.6),
        ("corr_90d", "#104281", 2.2),
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

    for y, text, anchor in [
        (-0.93, "−1: espelho perfeito, o forward é só hedge do spot", "bottom"),
        (0.93, "+1: mesma direção, as duas pernas somam risco", "top"),
    ]:
        fig.add_annotation(
            xref="paper", x=0.01, y=y, yref="y", text=text, showarrow=False,
            font=dict(color="dimgray", size=10), xanchor="left", yanchor=anchor,
            bgcolor="rgba(255,255,255,0.75)",
        )

    fig.update_layout(
        title=title, template="plotly_white", height=420,
        margin=dict(l=60, r=20, t=50, b=70),
        yaxis_title="correlação entre as pernas",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
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
        line=dict(width=2, color="#1f77b4"),
    ))
    fig.add_trace(go.Scatter(
        x=x_str, y=plot_df[col_loc], name="Local Ex Banks",
        line=dict(width=2, color="#ff7f0e"),
    ))
    fig.add_trace(go.Scatter(
        x=x_str, y=-plot_df[col_total], name="Local Banks",
        line=dict(width=2, color="#2ca02c"),
    ))
    fig.add_hline(y=0, line_color="black", line_width=0.5)

    y_vals = pd.concat([plot_df[col_off], plot_df[col_loc], -plot_df[col_total]]).dropna()
    y_min = y_vals.min() if len(y_vals) > 0 else 0
    y_max = y_vals.max() if len(y_vals) > 0 else 0

    fig.add_annotation(
        x=x_str[0], y=y_min * 1.1 if y_min < 0 else y_min - abs(y_max) * 0.1,
        text="Tomado", showarrow=False, font=dict(color="red", size=10),
    )
    fig.add_annotation(
        x=x_str[0], y=y_max * 1.1 if y_max > 0 else y_max + abs(y_min) * 0.1,
        text="Aplicado", showarrow=False, font=dict(color="blue", size=10),
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=12)),
        template="plotly_white",
        height=380,
        margin=dict(l=50, r=15, t=40, b=55),
        yaxis_title="DV01",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5,
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
        marker_color="darkblue",
    ))
    fig.update_layout(
        title=title, template="plotly_white", height=280,
        margin=dict(l=100, r=20, t=50, b=40),
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
        ("Extranjero", "dodgerblue"),
        ("FPC", "darkorange"),
        ("RestoyReal", "green"),
    ]:
        if col in filtered.columns:
            fig.add_trace(go.Scatter(
                x=x_str, y=filtered[col],
                name=col, line=dict(width=1.2, color=color),
            ))
    fig.add_hline(y=0, line_color="black", line_width=0.5)
    fig.update_layout(
        title="Saldos de compra e venda de contratos fwd (USD million)",
        template="plotly_white", height=400,
        margin=dict(l=50, r=20, t=50, b=60),
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
    "ndf": "dodgerblue",
    "bcch": "#6b7280",
}


def _clp_side_labels(fig: go.Figure, ymax: float, ymin: float) -> None:
    """Marca que acima de zero e compra de CLP e abaixo e venda de CLP."""
    for y, text, color in [
        (ymax * 0.88, "▲ acima de zero: comprando CLP (vendendo USD)", "green"),
        (ymin * 0.88, "▼ abaixo de zero: vendendo CLP (comprando USD)", "red"),
    ]:
        fig.add_annotation(
            xref="paper", x=0.01, y=y, yref="y", text=text, showarrow=False,
            font=dict(color=color, size=11), xanchor="left",
            bgcolor="rgba(255,255,255,0.75)",
        )


def make_afp_7d_bars(legs: dict) -> str:
    """Uma barra por perna com o acumulado dos ultimos 7 dias corridos.

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
            "FUNDOS DE PENSÃO: 7 DIAS — NDF vs SPOT "
            f"<span style='font-size:13px;color:#666'>({janela})</span>"
        ),
        template="plotly_white", height=460,
        margin=dict(l=60, r=20, t=70, b=80),
        yaxis_title="USD million acumulado",
        showlegend=False, bargap=0.45,
    )
    fig.update_yaxes(range=[-lim, lim])
    _clp_side_labels(fig, lim, -lim)
    return _to_html(fig)


def make_afp_weekly_bars(wk: pd.DataFrame, title: str, weeks_default: int = 12) -> str:
    """Barras agrupadas por semana com as duas pernas, em compra-de-CLP."""
    if wk.empty:
        return "<p>Dados indisponíveis</p>"

    x_str = _date_strings(wk["Semana"])
    series = [
        ("ndf_wk", "NDF (Δ saldo na semana)", AFP_LEG_COLORS["ndf"]),
        ("bcch_wk", "Spot observado (BCCh)", AFP_LEG_COLORS["bcch"]),
    ]

    fig = go.Figure()
    for col, name, color in series:
        fig.add_trace(go.Bar(
            x=x_str, y=wk[col], name=name, marker_color=color,
            hovertemplate=f"semana de %{{x}}<br>{name}: %{{y:+,.0f}} mm USD<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="black", line_width=0.8)

    fig.update_layout(
        title=title, barmode="group", bargap=0.25, bargroupgap=0.05,
        template="plotly_white", height=440,
        margin=dict(l=60, r=20, t=50, b=70),
        yaxis_title="USD million (+ compra de CLP)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _apply_category_xaxis(fig, nticks=14)

    # Abre nas ultimas N semanas: com o historico inteiro visivel as barras
    # recentes ficam achatadas. Duplo-clique devolve a serie toda.
    n = len(x_str)
    visivel = wk.tail(weeks_default) if n > weeks_default else wk
    vals = pd.concat([visivel[c] for c, _, _ in series]).dropna()
    lim = vals.abs().max() * 1.30 if len(vals) else 1.0
    fig.update_yaxes(range=[-lim, lim])
    _clp_side_labels(fig, lim, -lim)
    if n > weeks_default:
        fig.update_xaxes(range=[n - weeks_default - 0.5, n - 0.5])
    return _to_html(fig)
