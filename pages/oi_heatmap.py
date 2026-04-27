"""OI Heatmap — Strike × Time intensity map for CE and PE."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.data_fetcher import get_oi_snapshots_history, fetch_option_chain
from utils.chart_theme import *


def render(symbol: str, symbol_type: str, expiry: str):
    data = fetch_option_chain(symbol, symbol_type)
    spot = data["spot"]
    candle_size = st.session_state.get("candle_size", 15)

    history = get_oi_snapshots_history(symbol, candle_size)

    col_ctrl1, col_ctrl2 = st.columns([2, 2])
    with col_ctrl1:
        hm_type = st.selectbox("Heatmap Data", ["OI (Absolute)", "OI Change", "% OI Change"], key="hm_type")
    with col_ctrl2:
        color_scale_ce = st.selectbox("CE Color Scale", ["Blues", "Greens", "YlGn", "Teal"], key="hm_cs_ce")

    strikes = sorted(history["strike"].unique())
    times = sorted(history["time"].unique())

    value_col = {
        "OI (Absolute)": ("ce_oi", "pe_oi"),
        "OI Change": ("ce_coi", "pe_coi"),
        "% OI Change": ("ce_coi", "pe_coi"),
    }[hm_type]

    # Build pivot matrices
    def build_matrix(col):
        pivot = history.pivot_table(index="strike", columns="time", values=col, aggfunc="mean")
        pivot = pivot.reindex(index=sorted(pivot.index, reverse=True))
        if "%" in hm_type:
            oi_col = "ce_oi" if col == "ce_coi" else "pe_oi"
            oi_piv = history.pivot_table(index="strike", columns="time", values=oi_col, aggfunc="mean")
            oi_piv = oi_piv.reindex(index=sorted(oi_piv.index, reverse=True))
            pivot = (pivot / oi_piv.replace(0, 1) * 100).round(2)
        return pivot

    ce_matrix = build_matrix(value_col[0])
    pe_matrix = build_matrix(value_col[1])

    # CE Heatmap
    st.markdown("**CE OI Heatmap**")
    fig_ce = go.Figure(go.Heatmap(
        z=ce_matrix.values,
        x=ce_matrix.columns.tolist(),
        y=[str(int(s)) for s in ce_matrix.index.tolist()],
        colorscale=color_scale_ce,
        colorbar=dict(
            title=dict(text="OI (L)" if "%" not in hm_type else "% Chg", font=dict(size=10)),
            thickness=12, len=0.8,
            tickfont=dict(size=9, color=TEXT_COLOR),
        ),
        hovertemplate="Time: %{x}<br>Strike: %{y}<br>Value: %{z:,.0f}<extra></extra>",
    ))
    layout_ce = base_layout("", height=320, show_legend=False)
    layout_ce["xaxis"]["title"] = dict(text="Time", font=dict(size=10))
    layout_ce["yaxis"]["title"] = dict(text="Strike", font=dict(size=10))
    layout_ce["xaxis"]["tickangle"] = -45
    layout_ce["xaxis"]["tickfont"] = dict(size=9)
    layout_ce["margin"] = dict(l=60, r=60, t=20, b=50)
    fig_ce.update_layout(layout_ce)
    st.plotly_chart(fig_ce, use_container_width=True, config={"displayModeBar": False})

    # PE Heatmap
    st.markdown("**PE OI Heatmap**")
    fig_pe = go.Figure(go.Heatmap(
        z=pe_matrix.values,
        x=pe_matrix.columns.tolist(),
        y=[str(int(s)) for s in pe_matrix.index.tolist()],
        colorscale="Reds",
        colorbar=dict(
            title=dict(text="OI (L)" if "%" not in hm_type else "% Chg", font=dict(size=10)),
            thickness=12, len=0.8,
            tickfont=dict(size=9, color=TEXT_COLOR),
        ),
        hovertemplate="Time: %{x}<br>Strike: %{y}<br>Value: %{z:,.0f}<extra></extra>",
    ))
    layout_pe = base_layout("", height=320, show_legend=False)
    layout_pe["xaxis"]["title"] = dict(text="Time", font=dict(size=10))
    layout_pe["yaxis"]["title"] = dict(text="Strike", font=dict(size=10))
    layout_pe["xaxis"]["tickangle"] = -45
    layout_pe["xaxis"]["tickfont"] = dict(size=9)
    layout_pe["margin"] = dict(l=60, r=60, t=20, b=50)
    fig_pe.update_layout(layout_pe)
    st.plotly_chart(fig_pe, use_container_width=True, config={"displayModeBar": False})

    # Combined CE-PE difference heatmap
    st.markdown("**CE vs PE OI Difference Heatmap**")
    if ce_matrix.shape == pe_matrix.shape:
        diff_matrix = pe_matrix.values - ce_matrix.values
        fig_diff = go.Figure(go.Heatmap(
            z=diff_matrix,
            x=ce_matrix.columns.tolist(),
            y=[str(int(s)) for s in ce_matrix.index.tolist()],
            colorscale="RdYlGn",
            zmid=0,
            colorbar=dict(
                title=dict(text="PE-CE OI", font=dict(size=10)),
                thickness=12, len=0.8,
                tickfont=dict(size=9, color=TEXT_COLOR),
            ),
            hovertemplate="Time: %{x}<br>Strike: %{y}<br>PE-CE: %{z:,.0f}<extra></extra>",
        ))
        layout_diff = base_layout("", height=320, show_legend=False)
        layout_diff["xaxis"]["tickangle"] = -45
        layout_diff["xaxis"]["tickfont"] = dict(size=9)
        layout_diff["margin"] = dict(l=60, r=60, t=20, b=50)
        fig_diff.update_layout(layout_diff)
        st.plotly_chart(fig_diff, use_container_width=True, config={"displayModeBar": False})
