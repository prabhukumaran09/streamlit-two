import streamlit as st

st.set_page_config(
    page_title="OI Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS matching iCharts style
st.markdown("""
<style>
    /* Main layout */
    .block-container { padding: 0.5rem 1rem 1rem 1rem; max-width: 100%; }
    .stApp { background-color: #0e1117; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label { color: #c9d1d9 !important; font-size: 13px; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px 14px;
    }
    [data-testid="metric-container"] label { color: #8b949e !important; font-size: 12px !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 20px !important; }
    [data-testid="stMetricDelta"] { font-size: 12px !important; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: #8b949e; border-radius: 6px; font-size: 13px; padding: 6px 16px; }
    .stTabs [aria-selected="true"] { background: #21262d !important; color: #e6edf3 !important; }

    /* Headers */
    h1, h2, h3 { color: #e6edf3 !important; }

    /* General text */
    p, li, span, label { color: #c9d1d9; }

    /* Dataframe */
    [data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }

    /* Buttons */
    .stButton button {
        background: #21262d;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-size: 13px;
    }
    .stButton button:hover { background: #30363d; border-color: #58a6ff; }

    /* Select boxes */
    .stSelectbox [data-baseweb="select"] > div { background: #21262d; border-color: #30363d; color: #e6edf3; }

    /* Live badge */
    .live-badge {
        display: inline-block;
        background: #da3633;
        color: white;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 12px;
        animation: blink 2s infinite;
        margin-left: 8px;
        vertical-align: middle;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.5} }

    /* Chart containers */
    .chart-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .chart-title {
        font-size: 13px;
        font-weight: 600;
        color: #8b949e;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Divider */
    hr { border-color: #30363d; }

    /* Positive / negative colors */
    .up { color: #3fb950 !important; }
    .dn { color: #f85149 !important; }

    /* Table */
    .oi-table { width: 100%; border-collapse: collapse; font-size: 12px; }
    .oi-table th { background: #21262d; color: #8b949e; padding: 6px 8px; text-align: right; border-bottom: 1px solid #30363d; font-size: 11px; font-weight: 500; }
    .oi-table th:first-child { text-align: left; }
    .oi-table td { padding: 5px 8px; text-align: right; border-bottom: 1px solid #21262d; color: #e6edf3; font-size: 12px; }
    .oi-table td:first-child { text-align: left; font-weight: 600; }
    .oi-table tr.atm { background: #1f2a1f; }
    .oi-table tr:hover td { background: #21262d; }
    .green { color: #3fb950; font-weight: 500; }
    .red { color: #f85149; font-weight: 500; }
    .blue { color: #58a6ff; }
    .amber { color: #d29922; }
</style>
""", unsafe_allow_html=True)

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from pages import oi_stats, pe_ce_diff, oi_heatmap, spike_detection, oi_table_page
from utils.data_fetcher import get_nse_session
from utils.market_utils import is_market_open, get_market_status
import time

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 OI Analytics")
    st.markdown("---")

    symbol_type = st.radio("Symbol Type", ["Index", "Stock"], horizontal=True)

    if symbol_type == "Index":
        symbol = st.selectbox("Index", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"])
    else:
        symbol = st.selectbox("FNO Stock", [
            "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK",
            "AXISBANK","SBIN","WIPRO","LT","BHARTIARTL",
            "ADANIENT","BAJFINANCE","MARUTI","TATAMOTORS","SUNPHARMA",
            "HINDUNILVR","KOTAKBANK","NTPC","POWERGRID","ONGC"
        ])

    st.markdown("---")

    expiry_options = ["Current Week", "Next Week", "Monthly", "Far Month"]
    expiry = st.selectbox("Expiry", expiry_options)

    st.markdown("---")

    candle_size = st.selectbox("Candle Size (min)", [3, 5, 10, 15, 30, 60], index=3)

    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Refresh every (sec)", 30, 300, 60, 15)

    st.markdown("---")

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Market status
    status, color = get_market_status()
    st.markdown(f"""
    <div style="text-align:center;margin-top:8px">
        <span style="font-size:12px;color:#8b949e">Market: </span>
        <span style="font-size:12px;color:{color};font-weight:600">{status}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center;margin-top:4px">
        <span style="font-size:11px;color:#484f58">{time.strftime('%d-%b-%Y %H:%M:%S')}</span>
    </div>
    """, unsafe_allow_html=True)

# ── Store in session state ────────────────────────────────────────────────────
st.session_state["symbol"] = symbol
st.session_state["symbol_type"] = symbol_type
st.session_state["expiry"] = expiry
st.session_state["candle_size"] = candle_size

# ── Top header ────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"""
    <h2 style="margin:0;padding:4px 0 0 0">
        {symbol} Option OI Dashboard
        <span class="live-badge">LIVE</span>
    </h2>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:8px;font-size:12px;color:#8b949e">
        Expiry: {expiry} &nbsp;|&nbsp; Candle: {candle_size}min
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin:6px 0 12px 0'>", unsafe_allow_html=True)

# ── Main tabs (matching iCharts layout) ──────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 OI Stats",
    "📈 PE-CE OI Diff",
    "🔥 OI Heatmap",
    "⚡ Spike Detection",
    "📋 OI Table",
])

with tab1:
    oi_stats.render(symbol, symbol_type, expiry, candle_size)

with tab2:
    pe_ce_diff.render(symbol, symbol_type, expiry, candle_size)

with tab3:
    oi_heatmap.render(symbol, symbol_type, expiry)

with tab4:
    spike_detection.render(symbol, symbol_type, expiry)

with tab5:
    oi_table_page.render(symbol, symbol_type, expiry)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh and is_market_open():
    st.markdown(
        f'<meta http-equiv="refresh" content="{refresh_interval}">',
        unsafe_allow_html=True
    )
