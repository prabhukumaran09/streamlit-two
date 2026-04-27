"""
OI Stats Tab — matches iCharts OptionOIStatsBeta.php
Layout:
  Left column:  Total OI bar (CE vs PE) + Total OI Change bar
  Right column: Strike-wise OI bars (CE+PE grouped) + Strike-wise OI Change bars
  Bottom:       Time range slider + Intraday/EOD toggle
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.data_fetcher import fetch_option_chain, compute_max_pain, compute_pcr
from utils.chart_theme import *


def render(symbol: str, symbol_type: str, expiry: str, candle_size: int):
    data = fetch_option_chain(symbol, symbol_type)
    df = data["df"]
    spot = data["spot"]
    ts = data["timestamp"]
    simulated = data["simulated"]

    if simulated:
        st.caption("⚠️ Showing simulated data — NSE API unavailable outside market hours or connection issue.")

    # ── KPI Row ───────────────────────────────────────────────────────────────
    total_ce_oi = df["ce_oi"].sum()
    total_pe_oi = df["pe_oi"].sum()
    total_ce_coi = df["ce_coi"].sum()
    total_pe_coi = df["pe_coi"].sum()
    pcr = compute_pcr(df)
    max_pain = compute_max_pain(df)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Spot Price", f"₹{spot:,.0f}")
    k2.metric("Total CE OI", f"{total_ce_oi/100000:.1f}L", f"{total_ce_coi/1000:+.0f}K")
    k3.metric("Total PE OI", f"{total_pe_oi/100000:.1f}L", f"{total_pe_coi/1000:+.0f}K")
    k4.metric("PCR", f"{pcr}", "Bullish" if pcr > 1 else "Bearish")
    k5.metric("Max Pain", f"₹{max_pain:,.0f}")
    k6.metric("Updated", ts)

    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

    # ── Strike range filter ───────────────────────────────────────────────────
    strikes = sorted(df["strike"].unique())
    step = strikes[1] - strikes[0] if len(strikes) > 1 else 50
    atm = round(spot / step) * step

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    with col_ctrl1:
        strike_range = st.slider(
            "Strike Range (±ATM)",
            min_value=3, max_value=15, value=8,
            key="oi_stats_strike_range"
        )
    with col_ctrl2:
        view_mode = st.radio("View", ["Intraday", "EOD"], horizontal=True, key="oi_stats_view")
    with col_ctrl3:
        show_max_markers = st.checkbox("Show Max OI", value=True, key="oi_stats_max")

    # Filter strikes
    filtered_strikes = [s for s in strikes if abs(s - atm) <= strike_range * step]
    df_f = df[df["strike"].isin(filtered_strikes)].sort_values("strike")

    # ── Main layout: Left summary + Right detail ──────────────────────────────
    col_left, col_right = st.columns([1, 4])

    # ── LEFT: Total OI bar + Total OI Change bar ──────────────────────────────
    with col_left:
        # Total OI
        fig_total = go.Figure()
        fig_total.add_trace(go.Bar(
            x=["CE", "PE"],
            y=[total_ce_oi / 100000, total_pe_oi / 100000],
            marker_color=[CE_COLOR, PE_COLOR],
            text=[f"{total_ce_oi/100000:.1f}L", f"{total_pe_oi/100000:.1f}L"],
            textposition="outside",
            textfont=dict(size=10, color=TEXT_COLOR),
            width=0.5,
        ))
        layout_total = base_layout(f"{symbol} Total OI", height=200, show_legend=False)
        layout_total["margin"] = dict(l=20, r=10, t=40, b=30)
        layout_total["yaxis"]["title"] = dict(text="Lakhs", font=dict(size=10))
        fig_total.update_layout(layout_total)
        st.plotly_chart(fig_total, use_container_width=True, config={"displayModeBar": False})

        # Total OI Change
        fig_coi = go.Figure()
        fig_coi.add_trace(go.Bar(
            x=["CE Chg", "PE Chg"],
            y=[total_ce_coi / 1000, total_pe_coi / 1000],
            marker_color=[
                CE_COLOR if total_ce_coi >= 0 else RED,
                PE_COLOR if total_pe_coi >= 0 else RED
            ],
            text=[f"{total_ce_coi/1000:+.0f}K", f"{total_pe_coi/1000:+.0f}K"],
            textposition="outside",
            textfont=dict(size=10, color=TEXT_COLOR),
            width=0.5,
        ))
        layout_coi = base_layout(f"Total OI Chg", height=200, show_legend=False)
        layout_coi["margin"] = dict(l=20, r=10, t=40, b=30)
        layout_coi["yaxis"]["title"] = dict(text="K contracts", font=dict(size=10))
        fig_coi.update_layout(layout_coi)
        st.plotly_chart(fig_coi, use_container_width=True, config={"displayModeBar": False})

    # ── RIGHT: Strike-wise OI + OI Change ────────────────────────────────────
    with col_right:
        strike_labels = [str(int(s)) for s in df_f["strike"]]
        atm_idx = strike_labels.index(str(int(atm))) if str(int(atm)) in strike_labels else -1

        # ── Chart 1: Strike-wise OI (CE + PE grouped bars) ───────────────────
        fig_oi = go.Figure()

        # Max CE and Max PE markers (hollow circles like iCharts)
        max_ce_strike = df_f.loc[df_f["ce_oi"].idxmax(), "strike"] if len(df_f) > 0 else None
        max_pe_strike = df_f.loc[df_f["pe_oi"].idxmax(), "strike"] if len(df_f) > 0 else None

        if show_max_markers and max_ce_strike:
            max_ce_val = df_f.loc[df_f["strike"] == max_ce_strike, "ce_oi"].values[0] / 100000
            fig_oi.add_trace(go.Scatter(
                x=[str(int(max_ce_strike))], y=[max_ce_val],
                mode="markers+text",
                marker=dict(symbol="circle-open", size=14, color=CE_COLOR, line=dict(width=2)),
                text=[f"Max CE<br>{str(int(max_ce_strike))}"],
                textposition="top center",
                textfont=dict(size=9, color=CE_COLOR),
                name="Max CE OI",
                showlegend=True,
            ))

        if show_max_markers and max_pe_strike:
            max_pe_val = df_f.loc[df_f["strike"] == max_pe_strike, "pe_oi"].values[0] / 100000
            fig_oi.add_trace(go.Scatter(
                x=[str(int(max_pe_strike))], y=[max_pe_val],
                mode="markers+text",
                marker=dict(symbol="circle-open", size=14, color=PE_COLOR, line=dict(width=2)),
                text=[f"Max PE<br>{str(int(max_pe_strike))}"],
                textposition="top center",
                textfont=dict(size=9, color=PE_COLOR),
                name="Max PE OI",
                showlegend=True,
            ))

        fig_oi.add_trace(go.Bar(
            x=strike_labels, y=df_f["ce_oi"] / 100000,
            name="CE OI", marker_color=CE_COLOR,
            opacity=0.85,
            hovertemplate="Strike: %{x}<br>CE OI: %{y:.2f}L<extra></extra>",
        ))
        fig_oi.add_trace(go.Bar(
            x=strike_labels, y=df_f["pe_oi"] / 100000,
            name="PE OI", marker_color=PE_COLOR,
            opacity=0.85,
            hovertemplate="Strike: %{x}<br>PE OI: %{y:.2f}L<extra></extra>",
        ))

        # ATM vertical line
        if atm_idx >= 0:
            fig_oi.add_vline(
                x=atm_idx, line_dash="dot", line_color=AMBER, line_width=1.5,
                annotation_text=f"ATM {int(atm)}", annotation_font_color=AMBER,
                annotation_font_size=10,
            )

        layout_oi = base_layout(f"{symbol} — Strike-wise OI", height=280)
        layout_oi["barmode"] = "group"
        layout_oi["bargap"] = 0.1
        layout_oi["bargroupgap"] = 0.05
        layout_oi["yaxis"]["title"] = dict(text="OI (Lakhs)", font=dict(size=10))
        layout_oi["xaxis"]["title"] = dict(text="Strike", font=dict(size=10))
        layout_oi["xaxis"]["tickangle"] = -45
        layout_oi["xaxis"]["tickfont"] = dict(size=9)
        fig_oi.update_layout(layout_oi)
        st.plotly_chart(fig_oi, use_container_width=True, config={"displayModeBar": False})

        # ── Chart 2: Strike-wise OI Change ───────────────────────────────────
        fig_coi2 = go.Figure()

        # Max CE/PE OI change markers
        if show_max_markers and len(df_f) > 0:
            max_ce_coi_s = df_f.loc[df_f["ce_coi"].abs().idxmax(), "strike"]
            max_pe_coi_s = df_f.loc[df_f["pe_coi"].abs().idxmax(), "strike"]
            for s, color, label in [(max_ce_coi_s, CE_COLOR, "Max CE Chg"), (max_pe_coi_s, PE_COLOR, "Max PE Chg")]:
                col_val = "ce_coi" if label.startswith("Max CE") else "pe_coi"
                y_val = df_f.loc[df_f["strike"] == s, col_val].values[0] / 1000
                fig_coi2.add_trace(go.Scatter(
                    x=[str(int(s))], y=[y_val],
                    mode="markers",
                    marker=dict(symbol="circle-open", size=12, color=color, line=dict(width=2)),
                    name=label, showlegend=True,
                ))

        # CE OI change bars — color by positive/negative
        fig_coi2.add_trace(go.Bar(
            x=strike_labels,
            y=df_f["ce_coi"] / 1000,
            name="CE OI Chg",
            marker_color=[CE_COLOR if v >= 0 else "#f85149" for v in df_f["ce_coi"]],
            opacity=0.85,
            hovertemplate="Strike: %{x}<br>CE Chg: %{y:+.1f}K<extra></extra>",
        ))
        fig_coi2.add_trace(go.Bar(
            x=strike_labels,
            y=df_f["pe_coi"] / 1000,
            name="PE OI Chg",
            marker_color=[PE_COLOR if v >= 0 else "#3fb950" for v in df_f["pe_coi"]],
            opacity=0.85,
            hovertemplate="Strike: %{x}<br>PE Chg: %{y:+.1f}K<extra></extra>",
        ))

        # Zero line
        fig_coi2.add_hline(y=0, line_color=BORDER_COLOR, line_width=1, line_dash="dot")

        if atm_idx >= 0:
            fig_coi2.add_vline(
                x=atm_idx, line_dash="dot", line_color=AMBER, line_width=1.5,
                annotation_text=f"ATM {int(atm)}", annotation_font_color=AMBER,
                annotation_font_size=10, annotation_position="bottom right",
            )

        layout_coi2 = base_layout(f"{symbol} — Strike-wise OI Change", height=260)
        layout_coi2["barmode"] = "group"
        layout_coi2["bargap"] = 0.1
        layout_coi2["bargroupgap"] = 0.05
        layout_coi2["yaxis"]["title"] = dict(text="OI Change (K)", font=dict(size=10))
        layout_coi2["xaxis"]["title"] = dict(text="Strike", font=dict(size=10))
        layout_coi2["xaxis"]["tickangle"] = -45
        layout_coi2["xaxis"]["tickfont"] = dict(size=9)
        fig_coi2.update_layout(layout_coi2)
        st.plotly_chart(fig_coi2, use_container_width=True, config={"displayModeBar": False})

    # ── PCR chart by strike ───────────────────────────────────────────────────
    df_f2 = df_f.copy()
    df_f2["pcr"] = (df_f2["pe_oi"] / df_f2["ce_oi"].replace(0, 1)).round(2)

    fig_pcr = go.Figure()
    fig_pcr.add_trace(go.Bar(
        x=strike_labels,
        y=df_f2["pcr"],
        marker_color=[GREEN if v >= 1 else RED for v in df_f2["pcr"]],
        name="PCR",
        hovertemplate="Strike: %{x}<br>PCR: %{y:.2f}<extra></extra>",
    ))
    fig_pcr.add_hline(y=1, line_color=AMBER, line_dash="dot", line_width=1.5,
                      annotation_text="PCR=1 (Neutral)", annotation_font_color=AMBER, annotation_font_size=10)
    layout_pcr = base_layout("Put-Call Ratio by Strike", height=220, show_legend=False)
    layout_pcr["xaxis"]["tickangle"] = -45
    layout_pcr["xaxis"]["tickfont"] = dict(size=9)
    fig_pcr.update_layout(layout_pcr)
    st.plotly_chart(fig_pcr, use_container_width=True, config={"displayModeBar": False})
