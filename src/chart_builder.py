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
