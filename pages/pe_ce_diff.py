"""
PE-CE OI Diff Tab — matches iCharts TotalPECEOIDiff_Beta.php
Layout: 4 charts in 2x2 grid
  Top-left:    Total Unwinding (CE+PE cumulative line + fair price)
  Top-right:   Unwinding 15-min (CE+PE bar chart + fair price line)
  Bottom-left: Total Buildup (CE+PE cumulative line + fair price)
  Bottom-right:Buildup 15-min (CE+PE bar chart + fair price line)
Sub-tabs: Stats | OI Diff | %OI Chg
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from utils.data_fetcher import fetch_option_chain, get_intraday_oi_history
from utils.chart_theme import *
from utils.chart_theme import show_sim_banner


def render(symbol: str, symbol_type: str, expiry: str, candle_size: int):
    data = fetch_option_chain(symbol, symbol_type)
    df_oc = data["df"]
    spot = data["spot"]
    simulated = data["simulated"]

    if simulated:
        reason = data.get("sim_reason", "NSE API unavailable")
        show_sim_banner(reason)

    # Sub-tabs matching iCharts
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Stats", "OI Diff", "%OI Chg"])

    with sub_tab1:
        _render_stats(symbol, symbol_type, df_oc, spot, candle_size)

    with sub_tab2:
        _render_oi_diff(symbol, df_oc, spot, candle_size)

    with sub_tab3:
        _render_pct_oi_chg(symbol, df_oc, spot, candle_size)


def _render_stats(symbol, symbol_type, df_oc, spot, candle_size):
    """4-panel buildup/unwinding charts matching iCharts Image 1."""
    history = get_intraday_oi_history(symbol, candle_size)

    times = history["time"].dt.strftime("%H:%M").tolist()
    ce_bu = history["ce_buildup"].tolist()
    pe_bu = history["pe_buildup"].tolist()
    ce_uw = history["ce_unwind"].tolist()
    pe_uw = history["pe_unwind"].tolist()
    fair_price = history["fair_price"].tolist()

    # 15-min deltas for bar charts
    def deltas(series):
        arr = np.array(series)
        d = np.diff(arr, prepend=arr[0])
        return d.tolist()

    ce_bu_d = deltas(ce_bu)
    pe_bu_d = deltas(pe_bu)
    ce_uw_d = deltas(ce_uw)
    pe_uw_d = deltas(pe_uw)

    col1, col2 = st.columns(2)

    # ── Top-left: Total Unwinding ─────────────────────────────────────────────
    with col1:
        fig_uw = make_subplots(specs=[[{"secondary_y": True}]])

        fig_uw.add_trace(go.Scatter(
            x=times, y=ce_uw, name="CE Unwinding",
            line=dict(color=CE_COLOR, width=2),
            hovertemplate="CE Unwd: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_uw.add_trace(go.Scatter(
            x=times, y=pe_uw, name="PE Unwinding",
            line=dict(color=PE_COLOR, width=2),
            hovertemplate="PE Unwd: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_uw.add_trace(go.Scatter(
            x=times, y=fair_price, name="Fair Price",
            line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
            hovertemplate="Fair Price: %{y:,.1f}<extra></extra>",
        ), secondary_y=True)

        # Annotation for last values
        if times:
            _add_end_annotation(fig_uw, times[-1], ce_uw[-1], f"{ce_uw[-1]:,.0f}", CE_COLOR)
            _add_end_annotation(fig_uw, times[-1], pe_uw[-1], f"{pe_uw[-1]:,.0f}", PE_COLOR)
            _add_end_annotation_y2(fig_uw, times[-1], fair_price[-1], f"{fair_price[-1]:,.1f}", FAIR_PRICE_COLOR)

        layout = dual_axis_layout("Total Unwinding", height=340)
        layout["yaxis"]["title"] = dict(text="OI", font=dict(size=10))
        layout["yaxis2"]["title"] = dict(text="Price", font=dict(size=10))
        layout["legend"]["x"] = 0
        fig_uw.update_layout(layout)
        st.plotly_chart(fig_uw, use_container_width=True, config={"displayModeBar": False})

    # ── Top-right: Unwinding 15-min bars ──────────────────────────────────────
    with col2:
        fig_uw15 = make_subplots(specs=[[{"secondary_y": True}]])

        fig_uw15.add_trace(go.Bar(
            x=times, y=ce_uw_d, name="CE Unwd 15",
            marker_color=[CE_COLOR if v >= 0 else "#a371f7" for v in ce_uw_d],
            opacity=0.85,
            hovertemplate="CE Δ15: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_uw15.add_trace(go.Bar(
            x=times, y=pe_uw_d, name="PE Unwd 15",
            marker_color=[PE_COLOR if v >= 0 else "#d29922" for v in pe_uw_d],
            opacity=0.85,
            hovertemplate="PE Δ15: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_uw15.add_trace(go.Scatter(
            x=times, y=fair_price, name="Fair Price",
            line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
        ), secondary_y=True)

        if times:
            _add_end_annotation_y2(fig_uw15, times[-1], fair_price[-1], f"{fair_price[-1]:,.1f}", FAIR_PRICE_COLOR)
            _add_end_annotation(fig_uw15, times[-1], ce_uw_d[-1], f"{int(ce_uw_d[-1]):,}", CE_COLOR)
            _add_end_annotation(fig_uw15, times[-1], pe_uw_d[-1], f"{int(pe_uw_d[-1]):,}", PE_COLOR)

        layout = dual_axis_layout(f"Unwinding ({candle_size} Min)", height=340)
        layout["barmode"] = "group"
        fig_uw15.update_layout(layout)
        st.plotly_chart(fig_uw15, use_container_width=True, config={"displayModeBar": False})

    # ── Bottom-left: Total Buildup ────────────────────────────────────────────
    with col1:
        fig_bu = make_subplots(specs=[[{"secondary_y": True}]])

        fig_bu.add_trace(go.Scatter(
            x=times, y=ce_bu, name="CE Buildup",
            line=dict(color=CE_COLOR, width=2),
            hovertemplate="CE Buildup: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_bu.add_trace(go.Scatter(
            x=times, y=pe_bu, name="PE Buildup",
            line=dict(color=PE_COLOR, width=2),
            hovertemplate="PE Buildup: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_bu.add_trace(go.Scatter(
            x=times, y=fair_price, name="Fair Price",
            line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
        ), secondary_y=True)

        if times:
            _add_end_annotation(fig_bu, times[-1], ce_bu[-1], f"{ce_bu[-1]:,.0f}", CE_COLOR)
            _add_end_annotation(fig_bu, times[-1], pe_bu[-1], f"{pe_bu[-1]:,.0f}", PE_COLOR)
            _add_end_annotation_y2(fig_bu, times[-1], fair_price[-1], f"{fair_price[-1]:,.1f}", FAIR_PRICE_COLOR)

        layout = dual_axis_layout("Total Buildup", height=340)
        layout["yaxis"]["title"] = dict(text="OI", font=dict(size=10))
        layout["yaxis2"]["title"] = dict(text="Price", font=dict(size=10))
        fig_bu.update_layout(layout)
        st.plotly_chart(fig_bu, use_container_width=True, config={"displayModeBar": False})

    # ── Bottom-right: Buildup 15-min bars ────────────────────────────────────
    with col2:
        fig_bu15 = make_subplots(specs=[[{"secondary_y": True}]])

        fig_bu15.add_trace(go.Bar(
            x=times, y=ce_bu_d, name="CE Buildup 15",
            marker_color=[CE_COLOR if v >= 0 else "#a371f7" for v in ce_bu_d],
            opacity=0.85,
            hovertemplate="CE Δ15: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_bu15.add_trace(go.Bar(
            x=times, y=pe_bu_d, name="PE Buildup 15",
            marker_color=[PE_COLOR if v >= 0 else "#d29922" for v in pe_bu_d],
            opacity=0.85,
            hovertemplate="PE Δ15: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_bu15.add_trace(go.Scatter(
            x=times, y=fair_price, name="Fair Price",
            line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
        ), secondary_y=True)

        if times:
            _add_end_annotation_y2(fig_bu15, times[-1], fair_price[-1], f"{fair_price[-1]:,.1f}", FAIR_PRICE_COLOR)

        layout = dual_axis_layout(f"Buildup ({candle_size} Min)", height=340)
        layout["barmode"] = "group"
        fig_bu15.update_layout(layout)
        st.plotly_chart(fig_bu15, use_container_width=True, config={"displayModeBar": False})


def _render_oi_diff(symbol, df_oc, spot, candle_size):
    """PE - CE OI Difference chart over time."""
    history = get_intraday_oi_history(symbol, candle_size)
    times = history["time"].dt.strftime("%H:%M").tolist()
    oi_diff = (history["pe_buildup"] - history["ce_buildup"]).tolist()
    fair_price = history["fair_price"].tolist()

    col1, col2 = st.columns(2)
    with col1:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        colors = [GREEN if v >= 0 else RED for v in oi_diff]
        fig.add_trace(go.Bar(
            x=times, y=oi_diff, name="PE-CE OI Diff",
            marker_color=colors, opacity=0.85,
            hovertemplate="PE-CE Diff: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=times, y=fair_price, name="Fair Price",
            line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
        ), secondary_y=True)
        fig.add_hline(y=0, line_color=BORDER_COLOR, line_width=1)
        layout = dual_axis_layout("PE - CE OI Difference (Cumulative)", height=380)
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        # OI diff delta (15-min slices)
        oi_diff_arr = np.array(oi_diff)
        oi_diff_delta = np.diff(oi_diff_arr, prepend=oi_diff_arr[0]).tolist()
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(
            x=times, y=oi_diff_delta, name=f"PE-CE OI Diff {candle_size}min",
            marker_color=[GREEN if v >= 0 else RED for v in oi_diff_delta],
            opacity=0.85,
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            x=times, y=fair_price, name="Fair Price",
            line=dict(color=FAIR_PRICE_COLOR, width=1.5, dash="dash"),
        ), secondary_y=True)
        layout2 = dual_axis_layout(f"PE-CE OI Diff ({candle_size} Min)", height=380)
        fig2.update_layout(layout2)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})


def _render_pct_oi_chg(symbol, df_oc, spot, candle_size):
    """% OI Change for CE and PE."""
    df = df_oc.copy()
    df["ce_pct"] = (df["ce_coi"] / df["ce_oi"].replace(0, 1) * 100).round(2)
    df["pe_pct"] = (df["pe_coi"] / df["pe_oi"].replace(0, 1) * 100).round(2)

    # Filter near ATM
    strikes = sorted(df["strike"].unique())
    step = strikes[1] - strikes[0] if len(strikes) > 1 else 50
    atm = round(spot / step) * step
    df_f = df[df["strike"].apply(lambda s: abs(s - atm) <= 10 * step)].sort_values("strike")
    labels = [str(int(s)) for s in df_f["strike"]]

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=df_f["ce_pct"],
            name="CE %OI Chg",
            marker_color=[CE_COLOR if v >= 0 else RED for v in df_f["ce_pct"]],
            opacity=0.85,
            hovertemplate="Strike: %{x}<br>CE %Chg: %{y:.2f}%<extra></extra>",
        ))
        fig.add_hline(y=0, line_color=BORDER_COLOR, line_width=1, line_dash="dot")
        layout = base_layout("CE % OI Change by Strike", height=350)
        layout["xaxis"]["tickangle"] = -45
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=labels, y=df_f["pe_pct"],
            name="PE %OI Chg",
            marker_color=[PE_COLOR if v >= 0 else GREEN for v in df_f["pe_pct"]],
            opacity=0.85,
            hovertemplate="Strike: %{x}<br>PE %Chg: %{y:.2f}%<extra></extra>",
        ))
        fig2.add_hline(y=0, line_color=BORDER_COLOR, line_width=1, line_dash="dot")
        layout2 = base_layout("PE % OI Change by Strike", height=350)
        layout2["xaxis"]["tickangle"] = -45
        fig2.update_layout(layout2)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})


def _add_end_annotation(fig, x, y, text, color, xref="x", yref="y"):
    fig.add_annotation(
        x=x, y=y, text=f"  {text}",
        showarrow=False,
        font=dict(size=10, color="white"),
        bgcolor=color,
        borderpad=2,
        xanchor="left",
    )


def _add_end_annotation_y2(fig, x, y, text, color):
    fig.add_annotation(
        x=x, y=y, text=f"  {text}",
        showarrow=False,
        font=dict(size=10, color="white"),
        bgcolor=color,
        borderpad=2,
        xanchor="left",
        yref="y2",
    )
