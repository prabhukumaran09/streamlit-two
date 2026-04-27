"""OI Table — Full strike-wise option chain table with color coding."""

import streamlit as st
import pandas as pd
import numpy as np
from utils.data_fetcher import fetch_option_chain, compute_max_pain, compute_pcr
from utils.chart_theme import *
import plotly.graph_objects as go


def _color_pct(val):
    if val > 0:
        intensity = min(int(val / 50 * 255), 200)
        return f"background-color: rgba(63,185,80,{intensity/255:.2f}); color: #e6edf3"
    elif val < 0:
        intensity = min(int(abs(val) / 50 * 255), 200)
        return f"background-color: rgba(248,81,73,{intensity/255:.2f}); color: #e6edf3"
    return ""


def render(symbol: str, symbol_type: str, expiry: str):
    data = fetch_option_chain(symbol, symbol_type)
    df = data["df"].copy()
    spot = data["spot"]
    ts = data["timestamp"]
    simulated = data["simulated"]

    if simulated:
        st.caption("⚠️ Simulated data — real NSE API unavailable right now.")

    # Compute derived columns
    df["pcr"] = (df["pe_oi"] / df["ce_oi"].replace(0, 1)).round(2)
    df["ce_pct"] = (df["ce_coi"] / df["ce_oi"].replace(0, 1) * 100).round(2)
    df["pe_pct"] = (df["pe_coi"] / df["pe_oi"].replace(0, 1) * 100).round(2)
    max_pain = compute_max_pain(df)

    strikes = sorted(df["strike"].unique())
    step = strikes[1] - strikes[0] if len(strikes) > 1 else 50
    atm = round(spot / step) * step
    df["is_atm"] = df["strike"] == atm
    df["is_max_pain"] = df["strike"] == max_pain

    # Controls
    col_c1, col_c2, col_c3 = st.columns([2, 2, 2])
    with col_c1:
        strike_range = st.slider("Strikes ±ATM", 5, 20, 12, key="oi_tbl_range")
    with col_c2:
        sort_by = st.selectbox("Sort by", ["Strike (ASC)", "Strike (DESC)", "CE OI ↓", "PE OI ↓", "PCR ↓"], key="oi_tbl_sort")
    with col_c3:
        show_iv = st.checkbox("Show IV", value=True, key="oi_tbl_iv")

    # Filter
    df_f = df[df["strike"].apply(lambda s: abs(s - atm) <= strike_range * step)].copy()

    # Sort
    sort_map = {
        "Strike (ASC)": ("strike", True),
        "Strike (DESC)": ("strike", False),
        "CE OI ↓": ("ce_oi", False),
        "PE OI ↓": ("pe_oi", False),
        "PCR ↓": ("pcr", False),
    }
    sort_col, sort_asc = sort_map[sort_by]
    df_f = df_f.sort_values(sort_col, ascending=sort_asc)

    # Build HTML table
    rows_html = ""
    for _, row in df_f.iterrows():
        atm_class = "atm" if row["is_atm"] else ""
        mp_marker = " 🎯" if row["is_max_pain"] else ""
        ce_chg_color = "green" if row["ce_pct"] >= 0 else "red"
        pe_chg_color = "green" if row["pe_pct"] >= 0 else "red"
        pcr_color = "green" if row["pcr"] >= 1 else "red"

        iv_cols = f"""<td>{row['ce_iv']:.1f}%</td><td>{row['pe_iv']:.1f}%</td>""" if show_iv else ""

        rows_html += f"""
        <tr class="{atm_class}">
            <td>{int(row['ce_oi']/1000):.0f}K</td>
            <td class="{ce_chg_color}">{row['ce_pct']:+.1f}%</td>
            <td>{int(row['ce_coi']/1000):.0f}K</td>
            <td>₹{row['ce_ltp']:.1f}</td>
            {"<td>"+str(row['ce_iv'])+"</td>" if show_iv else ""}
            <td style="font-weight:700;text-align:center;color:{'#d29922' if row['is_atm'] else '#58a6ff'}">
                {int(row['strike'])}{mp_marker}{"★" if row['is_atm'] else ""}
            </td>
            {"<td>"+str(row['pe_iv'])+"</td>" if show_iv else ""}
            <td>₹{row['pe_ltp']:.1f}</td>
            <td>{int(row['pe_coi']/1000):.0f}K</td>
            <td class="{pe_chg_color}">{row['pe_pct']:+.1f}%</td>
            <td>{int(row['pe_oi']/1000):.0f}K</td>
            <td class="{pcr_color}">{row['pcr']:.2f}</td>
        </tr>
        """

    iv_headers = "<th>CE IV</th><th>PE IV</th>" if show_iv else ""

    table_html = f"""
    <style>
    .oi-wrap {{ overflow-x: auto; }}
    .oi-table {{ width: 100%; border-collapse: collapse; font-size: 12px; font-family: monospace; }}
    .oi-table th {{ background: #21262d; color: #8b949e; padding: 7px 8px; text-align: center;
                   border-bottom: 1px solid #30363d; font-size: 11px; white-space: nowrap; position: sticky; top: 0; }}
    .oi-table td {{ padding: 5px 8px; text-align: center; border-bottom: 1px solid #21262d; color: #e6edf3; }}
    .oi-table tr.atm td {{ background: #1f2a1f !important; border-top: 1px solid #3fb950; border-bottom: 1px solid #3fb950; }}
    .oi-table tr:hover td {{ background: #21262d; }}
    .oi-table .green {{ color: #3fb950; font-weight: 600; }}
    .oi-table .red {{ color: #f85149; font-weight: 600; }}
    .oi-table .ce-side {{ border-right: 2px solid #30363d; }}
    </style>
    <div class="oi-wrap">
    <table class="oi-table">
    <thead><tr>
        <th colspan="4" style="background:#0f2318;color:#3fb950">— CALLS (CE) —</th>
        {"<th colspan='1' style='background:#0f2318;color:#3fb950'>IV</th>" if show_iv else ""}
        <th style="background:#21262d;color:#d29922">STRIKE</th>
        {"<th colspan='1' style='background:#2a1f1f;color:#f85149'>IV</th>" if show_iv else ""}
        <th colspan="4" style="background:#2a1f1f;color:#f85149">— PUTS (PE) —</th>
        <th style="background:#21262d;color:#8b949e">PCR</th>
    </tr>
    <tr>
        <th>OI</th><th>%Chg</th><th>OI Chg</th><th>LTP</th>
        {"<th>IV</th>" if show_iv else ""}
        <th>Strike</th>
        {"<th>IV</th>" if show_iv else ""}
        <th>LTP</th><th>OI Chg</th><th>%Chg</th><th>OI</th>
        <th>PCR</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── OI Bar Summary below table ─────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[str(int(s)) for s in df_f["strike"]],
            y=df_f["ce_oi"] / 1000,
            name="CE OI", marker_color=CE_COLOR, opacity=0.8,
        ))
        fig.add_trace(go.Bar(
            x=[str(int(s)) for s in df_f["strike"]],
            y=df_f["pe_oi"] / 1000,
            name="PE OI", marker_color=PE_COLOR, opacity=0.8,
        ))
        layout = base_layout("OI by Strike", height=220)
        layout["barmode"] = "group"
        layout["xaxis"]["tickangle"] = -45
        layout["xaxis"]["tickfont"] = dict(size=9)
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=[str(int(s)) for s in df_f["strike"]],
            y=df_f["ce_coi"] / 1000,
            name="CE OI Chg",
            marker_color=[CE_COLOR if v >= 0 else RED for v in df_f["ce_coi"]],
            opacity=0.8,
        ))
        fig2.add_trace(go.Bar(
            x=[str(int(s)) for s in df_f["strike"]],
            y=df_f["pe_coi"] / 1000,
            name="PE OI Chg",
            marker_color=[PE_COLOR if v >= 0 else GREEN for v in df_f["pe_coi"]],
            opacity=0.8,
        ))
        fig2.add_hline(y=0, line_color=BORDER_COLOR, line_width=1, line_dash="dot")
        layout2 = base_layout("OI Change by Strike", height=220)
        layout2["barmode"] = "group"
        layout2["xaxis"]["tickangle"] = -45
        layout2["xaxis"]["tickfont"] = dict(size=9)
        fig2.update_layout(layout2)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
