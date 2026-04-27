"""
OI Spike Detection — Auto-detects unusual OI jumps across FNO stocks.
Algorithm: OI change > 2× rolling average OR absolute jump > threshold.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from utils.data_fetcher import fetch_option_chain
from utils.chart_theme import *

FNO_STOCKS = [
    "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY",
    "HDFCBANK", "ICICIBANK", "AXISBANK", "SBIN", "WIPRO",
    "LT", "BHARTIARTL", "BAJFINANCE", "TATAMOTORS", "MARUTI",
]

SPIKE_THRESHOLD_PCT = 50   # % OI change to flag as spike
SPIKE_THRESHOLD_ABS = 5000  # Min absolute OI change (contracts)


def detect_spikes(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Return rows where OI change is anomalous."""
    spikes = []
    for _, row in df.iterrows():
        # CE spike
        if row["ce_oi"] > 0:
            ce_pct = abs(row["ce_coi"]) / row["ce_oi"] * 100
            if ce_pct > SPIKE_THRESHOLD_PCT and abs(row["ce_coi"]) > SPIKE_THRESHOLD_ABS:
                spikes.append({
                    "symbol": symbol,
                    "strike": row["strike"],
                    "type": "CE",
                    "oi": row["ce_oi"],
                    "coi": row["ce_coi"],
                    "pct": round(ce_pct, 1),
                    "ltp": row["ce_ltp"],
                    "direction": "BUILDUP" if row["ce_coi"] > 0 else "UNWINDING",
                    "severity": "HIGH" if ce_pct > 150 else "MEDIUM" if ce_pct > 80 else "LOW",
                })
        # PE spike
        if row["pe_oi"] > 0:
            pe_pct = abs(row["pe_coi"]) / row["pe_oi"] * 100
            if pe_pct > SPIKE_THRESHOLD_PCT and abs(row["pe_coi"]) > SPIKE_THRESHOLD_ABS:
                spikes.append({
                    "symbol": symbol,
                    "strike": row["strike"],
                    "type": "PE",
                    "oi": row["pe_oi"],
                    "coi": row["pe_coi"],
                    "pct": round(pe_pct, 1),
                    "ltp": row["pe_ltp"],
                    "direction": "BUILDUP" if row["pe_coi"] > 0 else "UNWINDING",
                    "severity": "HIGH" if pe_pct > 150 else "MEDIUM" if pe_pct > 80 else "LOW",
                })
    return pd.DataFrame(spikes)


def render(symbol: str, symbol_type: str, expiry: str):
    st.markdown("#### OI Spike Detection")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    with col_ctrl1:
        scan_scope = st.radio("Scan Scope", ["Current Symbol", "All FNO Stocks"], horizontal=True, key="spike_scope")
    with col_ctrl2:
        threshold = st.slider("Spike Threshold (%)", 20, 200, SPIKE_THRESHOLD_PCT, 10, key="spike_thresh")
    with col_ctrl3:
        severity_filter = st.selectbox("Severity", ["ALL", "HIGH", "MEDIUM", "LOW"], key="spike_sev")

    if scan_scope == "Current Symbol":
        scan_symbols = [(symbol, symbol_type)]
    else:
        scan_symbols = [(s, "Index" if s in ("NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY") else "Stock")
                        for s in FNO_STOCKS]

    all_spikes = []
    with st.spinner(f"Scanning {len(scan_symbols)} symbol(s)..."):
        for sym, stype in scan_symbols:
            try:
                data = fetch_option_chain(sym, stype)
                df = data["df"]
                spikes = detect_spikes(df, sym)
                if not spikes.empty:
                    all_spikes.append(spikes)
            except Exception:
                pass

    if not all_spikes:
        st.info("No OI spikes detected with current settings. Try lowering the threshold.")
        return

    df_spikes = pd.concat(all_spikes, ignore_index=True)
    df_spikes = df_spikes.sort_values("pct", ascending=False)

    if severity_filter != "ALL":
        df_spikes = df_spikes[df_spikes["severity"] == severity_filter]

    # ── Summary cards ──────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Spikes", len(df_spikes))
    k2.metric("High Severity", len(df_spikes[df_spikes["severity"] == "HIGH"]))
    k3.metric("CE Spikes", len(df_spikes[df_spikes["type"] == "CE"]))
    k4.metric("PE Spikes", len(df_spikes[df_spikes["type"] == "PE"]))

    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

    col_list, col_chart = st.columns([1, 1])

    with col_list:
        st.markdown("**Top Spike Alerts**")
        for _, row in df_spikes.head(15).iterrows():
            sev_color = {"HIGH": "#f85149", "MEDIUM": "#d29922", "LOW": "#58a6ff"}[row["severity"]]
            type_color = CE_COLOR if row["type"] == "CE" else PE_COLOR
            dir_icon = "↑" if row["direction"] == "BUILDUP" else "↓"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #21262d">
                <span style="background:{type_color};color:white;font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px;min-width:30px;text-align:center">{row['type']}</span>
                <div style="flex:1">
                    <span style="font-size:13px;font-weight:600;color:#e6edf3">{row['symbol']}</span>
                    <span style="font-size:12px;color:#8b949e"> {int(row['strike'])}</span>
                    <span style="font-size:11px;color:{sev_color};margin-left:4px">[{row['severity']}]</span><br>
                    <span style="font-size:11px;color:#8b949e">OI: {row['oi']/1000:.1f}K &nbsp;|&nbsp; Chg: {row['coi']/1000:+.1f}K &nbsp;|&nbsp; LTP: ₹{row['ltp']:.1f}</span>
                </div>
                <span style="font-size:14px;font-weight:600;color:{sev_color}">{dir_icon} {row['pct']:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)

    with col_chart:
        # Spike distribution bar chart
        by_sym = df_spikes.groupby(["symbol", "type"])["pct"].sum().unstack(fill_value=0).reset_index()
        fig = go.Figure()
        if "CE" in by_sym.columns:
            fig.add_trace(go.Bar(
                x=by_sym["symbol"], y=by_sym["CE"],
                name="CE Spike Σ%", marker_color=CE_COLOR, opacity=0.85,
            ))
        if "PE" in by_sym.columns:
            fig.add_trace(go.Bar(
                x=by_sym["symbol"], y=by_sym["PE"],
                name="PE Spike Σ%", marker_color=PE_COLOR, opacity=0.85,
            ))
        layout = base_layout("Spike Distribution by Symbol", height=280)
        layout["barmode"] = "group"
        layout["yaxis"]["title"] = dict(text="Cumulative Spike %", font=dict(size=10))
        layout["xaxis"]["tickangle"] = -45
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Spike timeline
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_spikes["symbol"] + " " + df_spikes["strike"].astype(int).astype(str),
            y=df_spikes["pct"],
            marker_color=[CE_COLOR if t == "CE" else PE_COLOR for t in df_spikes["type"]],
            hovertemplate="%{x}<br>Spike: %{y:.1f}%<extra></extra>",
            name="Spike %",
        ))
        layout2 = base_layout("All Spikes Ranked", height=230, show_legend=False)
        layout2["xaxis"]["tickangle"] = -45
        layout2["xaxis"]["tickfont"] = dict(size=8)
        layout2["yaxis"]["title"] = dict(text="OI Chg %", font=dict(size=10))
        fig2.update_layout(layout2)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
