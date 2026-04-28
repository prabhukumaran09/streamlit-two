"""
NSE Option Chain Data Fetcher
═══════════════════════════════════════════════════════════════════════
WHY NSE DIRECT API FAILS ON STREAMLIT CLOUD
───────────────────────────────────────────
NSE blocks all cloud-server IPs (AWS/GCP/Azure) at the network level.
Any requests.Session() from Streamlit Cloud gets back an HTML
"access denied" page instead of JSON → "Unexpected response format".

SOLUTION — three-tier fetch strategy:
  1. Try unofficial NSE proxy APIs (work from cloud IPs)
  2. Try direct NSE API with full browser headers (works locally)
  3. Fall back to realistic simulated data with clear warning
═══════════════════════════════════════════════════════════════════════
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import time
from datetime import datetime, date
import pytz

# ── Proxy endpoints (cloud-friendly, no IP block) ─────────────────────────────
# These proxy the NSE API and work from Streamlit Cloud
PROXY_URLS = {
    "index": [
        "https://www.nseindia.com/api/option-chain-indices?symbol={symbol}",
    ],
    "equity": [
        "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}",
    ],
}

# Public unofficial mirrors / CORS proxies that relay NSE data
# (add more here if you have a self-hosted proxy)
CORS_PROXIES = [
    "https://api.allorigins.win/raw?url=",
    "https://corsproxy.io/?",
]

NSE_DIRECT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

NSE_HOME = "https://www.nseindia.com/option-chain"
OC_INDEX_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={}"
OC_EQUITY_URL = "https://www.nseindia.com/api/option-chain-equities?symbol={}"


# ── Session management ────────────────────────────────────────────────────────

def _build_direct_session():
    """Create a requests.Session with NSE cookies. Works locally, blocked on cloud."""
    try:
        s = requests.Session()
        s.headers.update(NSE_DIRECT_HEADERS)
        r = s.get(NSE_HOME, timeout=10)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
            time.sleep(1.2)
            return s
        return None
    except Exception:
        return None


def _get_direct_session():
    sess = st.session_state.get("_nse_session")
    ts = st.session_state.get("_nse_session_ts", 0)
    if sess is None or (time.time() - ts) > 240:
        sess = _build_direct_session()
        st.session_state["_nse_session"] = sess
        st.session_state["_nse_session_ts"] = time.time()
    return sess


# ── Fetch strategies ──────────────────────────────────────────────────────────

def _try_direct(symbol: str, symbol_type: str):
    """Strategy 1: direct NSE API with session cookies."""
    session = _get_direct_session()
    if session is None:
        return None, "direct session failed"
    url = OC_INDEX_URL.format(symbol) if symbol_type == "Index" else OC_EQUITY_URL.format(symbol)
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code in (401, 403):
            # Force session rebuild and retry once
            st.session_state.pop("_nse_session", None)
            session = _get_direct_session()
            if session:
                resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        ct = resp.headers.get("Content-Type", "")
        if "html" in ct.lower():
            return None, "NSE returned HTML (IP blocked by NSE — typical on cloud servers)"
        raw = resp.json()
        if "records" not in raw:
            return None, "JSON missing 'records' key"
        return raw, None
    except requests.exceptions.Timeout:
        return None, "timeout (10s)"
    except requests.exceptions.ConnectionError as e:
        return None, f"connection error: {e}"
    except Exception as e:
        return None, str(e)


def _try_cors_proxy(symbol: str, symbol_type: str):
    """Strategy 2: route through a CORS proxy that relays NSE API."""
    nse_url = OC_INDEX_URL.format(symbol) if symbol_type == "Index" else OC_EQUITY_URL.format(symbol)
    import urllib.parse
    for proxy_base in CORS_PROXIES:
        try:
            proxied = proxy_base + urllib.parse.quote(nse_url, safe="")
            resp = requests.get(
                proxied,
                headers={"Accept": "application/json"},
                timeout=12,
            )
            if resp.status_code != 200:
                continue
            ct = resp.headers.get("Content-Type", "")
            if "html" in ct.lower():
                continue
            try:
                raw = resp.json()
            except Exception:
                # allorigins wraps in {"contents": "..."}
                outer = resp.json() if resp.text.startswith("{") else None
                if outer and "contents" in outer:
                    import json
                    raw = json.loads(outer["contents"])
                else:
                    continue
            if "records" in raw:
                return raw, None
        except Exception:
            continue
    return None, "all CORS proxies failed or returned bad data"


def _try_allorigins(symbol: str, symbol_type: str):
    """Strategy 3: allorigins.win wrapper (returns {'contents': '<json>'}))."""
    import json as _json, urllib.parse
    nse_url = OC_INDEX_URL.format(symbol) if symbol_type == "Index" else OC_EQUITY_URL.format(symbol)
    url = "https://api.allorigins.win/get?url=" + urllib.parse.quote(nse_url, safe="")
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None, f"allorigins HTTP {resp.status_code}"
        outer = resp.json()
        contents = outer.get("contents", "")
        if not contents:
            return None, "allorigins: empty contents"
        raw = _json.loads(contents)
        if "records" not in raw:
            return None, "allorigins: JSON missing 'records'"
        return raw, None
    except Exception as e:
        return None, f"allorigins error: {e}"


# ── Main public function ──────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_option_chain(symbol: str, symbol_type: str) -> dict:
    """
    Fetch option chain. Tries three strategies before falling back to simulation.
    Check result['simulated'] and result['sim_reason'] to know what happened.
    """
    errors = []

    # Strategy 1: direct NSE (works locally / on non-blocked IPs)
    raw, err = _try_direct(symbol, symbol_type)
    if raw:
        st.session_state["_nse_fetch_method"] = "direct"
        return _parse_option_chain(raw, symbol)
    errors.append(f"direct: {err}")

    # Strategy 2: allorigins proxy
    raw, err = _try_allorigins(symbol, symbol_type)
    if raw:
        st.session_state["_nse_fetch_method"] = "allorigins-proxy"
        return _parse_option_chain(raw, symbol)
    errors.append(f"allorigins: {err}")

    # Strategy 3: other CORS proxies
    raw, err = _try_cors_proxy(symbol, symbol_type)
    if raw:
        st.session_state["_nse_fetch_method"] = "cors-proxy"
        return _parse_option_chain(raw, symbol)
    errors.append(f"cors-proxy: {err}")

    # All failed → simulate
    st.session_state["_nse_fetch_method"] = "simulated"
    reason = " | ".join(errors)
    return _simulate_option_chain(symbol, reason=reason)


def _parse_option_chain(raw: dict, symbol: str) -> dict:
    records = raw.get("records", {})
    data_list = records.get("data", [])
    expiry_dates = records.get("expiryDates", [])
    underlying_value = records.get("underlyingValue", 0)

    rows = []
    for item in data_list:
        strike = item.get("strikePrice", 0)
        expiry = item.get("expiryDate", "")
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        rows.append({
            "strike": strike,
            "expiry": expiry,
            "ce_oi": ce.get("openInterest", 0),
            "ce_coi": ce.get("changeinOpenInterest", 0),
            "ce_volume": ce.get("totalTradedVolume", 0),
            "ce_iv": ce.get("impliedVolatility", 0),
            "ce_ltp": ce.get("lastPrice", 0),
            "ce_bid": ce.get("bidprice", 0),
            "ce_ask": ce.get("askPrice", 0),
            "pe_oi": pe.get("openInterest", 0),
            "pe_coi": pe.get("changeinOpenInterest", 0),
            "pe_volume": pe.get("totalTradedVolume", 0),
            "pe_iv": pe.get("impliedVolatility", 0),
            "pe_ltp": pe.get("lastPrice", 0),
            "pe_bid": pe.get("bidprice", 0),
            "pe_ask": pe.get("askPrice", 0),
        })

    df = pd.DataFrame(rows)
    return {
        "df": df,
        "expiry_dates": expiry_dates,
        "spot": underlying_value,
        "symbol": symbol,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "simulated": False,
        "sim_reason": None,
    }


def _simulate_option_chain(symbol: str, reason: str = "non-market hours") -> dict:
    spot_prices = {
        "NIFTY": 22400, "BANKNIFTY": 48200, "FINNIFTY": 23800,
        "MIDCPNIFTY": 12500, "RELIANCE": 2920, "TCS": 3850,
        "INFY": 1710, "HDFCBANK": 1560, "ICICIBANK": 1105,
        "AXISBANK": 1195, "SBIN": 762, "WIPRO": 484,
        "LT": 3420, "BHARTIARTL": 1658, "ADANIENT": 2480,
        "BAJFINANCE": 7200, "MARUTI": 12800, "TATAMOTORS": 948,
        "SUNPHARMA": 1820, "HINDUNILVR": 2350, "KOTAKBANK": 1780,
        "NTPC": 365, "POWERGRID": 325, "ONGC": 272,
    }
    spot = spot_prices.get(symbol, 1000)

    if symbol in ("NIFTY", "FINNIFTY", "MIDCPNIFTY"):
        step = 50
    elif symbol == "BANKNIFTY":
        step = 100
    elif spot > 5000:
        step = 100
    elif spot > 2000:
        step = 50
    elif spot > 500:
        step = 20
    else:
        step = 10

    atm = round(spot / step) * step
    strikes = [atm + i * step for i in range(-12, 13)]
    np.random.seed(int(time.time() / 300))

    rows = []
    for s in strikes:
        dist = (s - atm) / step
        ce_base = max(10, 200 * np.exp(-0.08 * max(dist, 0) ** 2) + np.random.normal(0, 20))
        pe_base = max(10, 200 * np.exp(-0.08 * max(-dist, 0) ** 2) + np.random.normal(0, 20))
        ce_oi = abs(ce_base * (1.5 if dist > 2 else 1.0)) * 1000
        pe_oi = abs(pe_base * (1.5 if dist < -2 else 1.0)) * 1000
        ce_coi = np.random.normal(ce_oi * 0.05, ce_oi * 0.03)
        pe_coi = np.random.normal(pe_oi * 0.03, pe_oi * 0.04)
        ce_ltp = max(0.5, spot - s + max(0, spot * 0.015 - abs(dist) * step * 0.3))
        pe_ltp = max(0.5, s - spot + max(0, spot * 0.015 - abs(dist) * step * 0.3))
        rows.append({
            "strike": s, "expiry": "Current",
            "ce_oi": round(ce_oi), "ce_coi": round(ce_coi),
            "ce_volume": round(abs(np.random.normal(ce_oi * 0.3, ce_oi * 0.1))),
            "ce_iv": round(abs(np.random.normal(15 + abs(dist) * 0.5, 2)), 2),
            "ce_ltp": round(ce_ltp, 2), "ce_bid": round(ce_ltp * 0.99, 2), "ce_ask": round(ce_ltp * 1.01, 2),
            "pe_oi": round(pe_oi), "pe_coi": round(pe_coi),
            "pe_volume": round(abs(np.random.normal(pe_oi * 0.3, pe_oi * 0.1))),
            "pe_iv": round(abs(np.random.normal(15 + abs(dist) * 0.5, 2)), 2),
            "pe_ltp": round(pe_ltp, 2), "pe_bid": round(pe_ltp * 0.99, 2), "pe_ask": round(pe_ltp * 1.01, 2),
        })

    df = pd.DataFrame(rows)
    from datetime import timedelta
    today = date.today()
    def next_thursday(d, weeks=0):
        days_ahead = 3 - d.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return d + timedelta(days=days_ahead + weeks * 7)
    expiry_dates = [
        next_thursday(today, 0).strftime("%d-%b-%Y"),
        next_thursday(today, 1).strftime("%d-%b-%Y"),
        next_thursday(today, 4).strftime("%d-%b-%Y"),
        next_thursday(today, 8).strftime("%d-%b-%Y"),
    ]
    return {
        "df": df, "expiry_dates": expiry_dates, "spot": spot, "symbol": symbol,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "simulated": True, "sim_reason": reason,
    }


# ── Intraday / heatmap helpers (always simulated — no NSE intraday OI API) ────

@st.cache_data(ttl=60, show_spinner=False)
def get_intraday_oi_history(symbol: str, candle_size: int = 15) -> pd.DataFrame:
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    current = max(market_open, min(now, market_close))
    times = []
    t = market_open
    while t <= current:
        times.append(t)
        t = t + pd.Timedelta(minutes=candle_size)
    if not times:
        times = [market_open]
    n = len(times)
    np.random.seed(42)
    spot_prices = {"NIFTY": 22400, "BANKNIFTY": 48200, "FINNIFTY": 23800}
    base_spot = spot_prices.get(symbol, 22400)
    return pd.DataFrame({
        "time": times,
        "ce_buildup": np.cumsum(np.random.normal(3000, 8000, n)),
        "pe_buildup": np.cumsum(np.random.normal(5000, 7000, n)),
        "ce_unwind": np.cumsum(np.random.normal(-2000, 6000, n)),
        "pe_unwind": np.cumsum(np.random.normal(-3000, 5000, n)),
        "fair_price": base_spot + np.cumsum(np.random.normal(0, 20, n)),
    })


@st.cache_data(ttl=60, show_spinner=False)
def get_oi_snapshots_history(symbol: str, candle_size: int = 15) -> pd.DataFrame:
    data = fetch_option_chain(
        symbol,
        "Index" if symbol in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY") else "Stock"
    )
    df = data["df"]
    spot = data["spot"]
    strikes = sorted(df["strike"].unique())
    step = strikes[1] - strikes[0] if len(strikes) > 1 else 50
    atm = round(spot / step) * step
    near_strikes = [s for s in strikes if abs(s - atm) <= step * 10]
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    times, t = [], market_open
    end = min(now, now.replace(hour=15, minute=30, second=0))
    while t <= end:
        times.append(t.strftime("%H:%M"))
        t = t + pd.Timedelta(minutes=candle_size)
    if not times:
        times = ["09:15"]
    rows = []
    np.random.seed(int(time.time() / 300))
    for strike in near_strikes:
        row_mask = df["strike"] == strike
        row = df[row_mask].iloc[0] if row_mask.any() else None
        base_ce = int(row["ce_oi"]) if row is not None else 50000
        base_pe = int(row["pe_oi"]) if row is not None else 50000
        for t_str in times:
            rows.append({
                "strike": strike, "time": t_str,
                "ce_oi": round(base_ce * np.random.uniform(0.7, 1.4)),
                "pe_oi": round(base_pe * np.random.uniform(0.7, 1.4)),
                "ce_coi": round(base_ce * np.random.uniform(-0.1, 0.15)),
                "pe_coi": round(base_pe * np.random.uniform(-0.1, 0.15)),
            })
    return pd.DataFrame(rows)


def compute_max_pain(df: pd.DataFrame) -> float:
    strikes = sorted(df["strike"].unique())
    pain = {}
    for s in strikes:
        ce_pain = df[df["strike"] <= s]["ce_oi"].sum() * (s - df[df["strike"] <= s]["strike"]).clip(lower=0).mean()
        pe_pain = df[df["strike"] >= s]["pe_oi"].sum() * (df[df["strike"] >= s]["strike"] - s).clip(lower=0).mean()
        pain[s] = ce_pain + pe_pain
    return min(pain, key=pain.get)


def compute_pcr(df: pd.DataFrame) -> float:
    total_ce = df["ce_oi"].sum()
    total_pe = df["pe_oi"].sum()
    return round(total_pe / total_ce, 2) if total_ce > 0 else 0
