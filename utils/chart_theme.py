"""Shared Plotly chart theme matching iCharts dark style."""

import plotly.graph_objects as go
import plotly.express as px

DARK_BG = "#0e1117"
CARD_BG = "#161b22"
GRID_COLOR = "#21262d"
BORDER_COLOR = "#30363d"
TEXT_COLOR = "#c9d1d9"
MUTED_COLOR = "#8b949e"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
AMBER = "#d29922"
PURPLE = "#a371f7"
TEAL = "#39d353"

CE_COLOR = "#3fb950"      # Green for CE buildup
PE_COLOR = "#f85149"      # Red for PE buildup
CE_UNWIND = "#f85149"     # Red for CE unwinding
PE_UNWIND = "#3fb950"     # Green for PE unwinding
FAIR_PRICE_COLOR = "#8b949e"


def base_layout(title="", height=350, show_legend=True):
    return dict(
        title=dict(text=title, font=dict(size=13, color=MUTED_COLOR), x=0.5, xanchor="center"),
        height=height,
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(family="Inter, sans-serif", color=TEXT_COLOR, size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
        ) if show_legend else dict(visible=False),
        margin=dict(l=50, r=50, t=40, b=40),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            zerolinecolor=GRID_COLOR,
            linecolor=BORDER_COLOR,
            tickfont=dict(size=10, color=MUTED_COLOR),
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            zerolinecolor=GRID_COLOR,
            linecolor=BORDER_COLOR,
            tickfont=dict(size=10, color=MUTED_COLOR),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#21262d", bordercolor=BORDER_COLOR, font=dict(size=11)),
    )


def dual_axis_layout(title="", height=380):
    """Layout for charts with price on left axis and OI on right axis."""
    layout = base_layout(title, height)
    layout["yaxis2"] = dict(
        overlaying="y",
        side="right",
        gridcolor="rgba(0,0,0,0)",
        linecolor=BORDER_COLOR,
        tickfont=dict(size=10, color=MUTED_COLOR),
        showgrid=False,
    )
    return layout


def add_fair_price_line(fig, x, y, name="Fair Price", yaxis="y"):
    fig.add_trace(go.Scatter(
        x=x, y=y,
        name=name,
        line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
        yaxis=yaxis,
        hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
    ))


def show_sim_banner(reason: str):
    """Shared banner shown when NSE real data is unavailable."""
    import streamlit as st
    st.warning(
        f"⚠️ **Simulated data** — NSE data could not be fetched from this server.  \n"
        f"**Reason:** `{reason}`  \n"
        f"**Fix:** Run locally with `streamlit run app.py`, or deploy a self-hosted NSE proxy.  \n"
        f"NSE blocks all major cloud provider IPs (AWS/GCP/Azure/Streamlit Cloud) by default.",
        icon="🚫",
    )
