"""
NSE Option Chain Data Fetcher
Pulls real data from NSE India public API.
Falls back to simulated data during non-market hours or on error.
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import time
import json
from datetime import datetime, date
import pytz

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
}

SESSION_URL = "https://www.nseindia.com"
OC_INDEX_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={}"
OC_EQUITY_URL = "https://www.nseindia.com/api/option-chain-equities?symbol={}"


@st.cache_resource(ttl=300)
def get_nse_session():
    """Create and cache an NSE session with proper cookies."""
    try:
        session = requests.Session()
        session.headers.update(NSE_HEADERS)
        resp = session.get(SESSION_URL, timeout=5)
        resp.raise_for_status()
        time.sleep(0.5)
        return session
    except Exception as e:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_option_chain(symbol: str, symbol_type: str) -> dict:
    """Fetch option chain from NSE. Returns parsed dict or simulated data."""
    try:
        session = get_nse_session()
        if session is None:
            return _simulate_option_chain(symbol)

        url = OC_INDEX_URL.format(symbol) if symbol_type == "Index" else OC_EQUITY_URL.format(symbol)
        resp = session.get(url, timeout=8)

        if resp.status_code == 401:
            # Re-initialize session by clearing cache and retrying
            get_nse_session.clear()
            session = get_nse_session()
            if session is None:
                return _simulate_option_chain(symbol)
            resp = session.get(url, timeout=8)

        resp.raise_for_status()
        raw = resp.json()
        return _parse_option_chain(raw, symbol)

    except Exception as e:
        # Silently fall back to simulation — real data unavailable
        return _simulate_option_chain(symbol)


def _parse_option_chain(raw: dict, symbol: str) -> dict:
    """Parse NSE raw option chain JSON into a clean DataFrame."""
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
    }


def _simulate_option_chain(symbol: str) -> dict:
    """Generate realistic simulated option chain data for demo/non-market hours."""
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

    # Determine step size
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

    np.random.seed(int(time.time() / 300))  # Stable for 5 min windows

    rows = []
    for s in strikes:
        dist = (s - atm) / step
        # OI distribution: higher near ATM, decaying away
        ce_base = max(10, 200 * np.exp(-0.08 * max(dist, 0) ** 2) + np.random.normal(0, 20))
        pe_base = max(10, 200 * np.exp(-0.08 * max(-dist, 0) ** 2) + np.random.normal(0, 20))

        # OTM strikes have more OI (selling pressure)
        ce_oi = abs(ce_base * (1.5 if dist > 2 else 1.0)) * 1000
        pe_oi = abs(pe_base * (1.5 if dist < -2 else 1.0)) * 1000

        ce_coi = np.random.normal(ce_oi * 0.05, ce_oi * 0.03)
        pe_coi = np.random.normal(pe_oi * 0.03, pe_oi * 0.04)

        # LTP from Black-Scholes approximation
        ce_ltp = max(0.5, spot - s + max(0, spot * 0.015 - abs(dist) * step * 0.3))
        pe_ltp = max(0.5, s - spot + max(0, spot * 0.015 - abs(dist) * step * 0.3))

        rows.append({
            "strike": s,
            "expiry": "Current",
            "ce_oi": round(ce_oi),
            "ce_coi": round(ce_coi),
            "ce_volume": round(abs(np.random.normal(ce_oi * 0.3, ce_oi * 0.1))),
            "ce_iv": round(abs(np.random.normal(15 + abs(dist) * 0.5, 2)), 2),
            "ce_ltp": round(ce_ltp, 2),
            "ce_bid": round(ce_ltp * 0.99, 2),
            "ce_ask": round(ce_ltp * 1.01, 2),
            "pe_oi": round(pe_oi),
            "pe_coi": round(pe_coi),
            "pe_volume": round(abs(np.random.normal(pe_oi * 0.3, pe_oi * 0.1))),
            "pe_iv": round(abs(np.random.normal(15 + abs(dist) * 0.5, 2)), 2),
            "pe_ltp": round(pe_ltp, 2),
            "pe_bid": round(pe_ltp * 0.99, 2),
            "pe_ask": round(pe_ltp * 1.01, 2),
        })

    df = pd.DataFrame(rows)

    # Generate fake expiry dates
    from datetime import timedelta
    today = date.today()
    # Next few Thursdays
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
        "df": df,
        "expiry_dates": expiry_dates,
        "spot": spot,
        "symbol": symbol,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "simulated": True,
    }


@st.cache_data(ttl=60, show_spinner=False)
def get_intraday_oi_history(symbol: str, candle_size: int = 15) -> pd.DataFrame:
    """
    Generate intraday OI history (time-series) for buildup/unwinding charts.
    In production: replace with your own stored snapshots from DB.
    """
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if now < market_open:
        current = market_open
    elif now > market_close:
        current = market_close
    else:
        current = now

    times = []
    t = market_open
    while t <= current:
        times.append(t)
        t = t + pd.Timedelta(minutes=candle_size)

    if not times:
        times = [market_open]

    n = len(times)
    np.random.seed(42)

    # Simulate cumulative buildup / unwinding with drift
    ce_buildup = np.cumsum(np.random.normal(3000, 8000, n))
    pe_buildup = np.cumsum(np.random.normal(5000, 7000, n))
    ce_unwind = np.cumsum(np.random.normal(-2000, 6000, n))
    pe_unwind = np.cumsum(np.random.normal(-3000, 5000, n))

    spot_prices = {
        "NIFTY": 22400, "BANKNIFTY": 48200, "FINNIFTY": 23800,
    }
    base_spot = spot_prices.get(symbol, 22400)
    fair_price = base_spot + np.cumsum(np.random.normal(0, 20, n))

    df = pd.DataFrame({
        "time": times,
        "ce_buildup": ce_buildup,
        "pe_buildup": pe_buildup,
        "ce_unwind": ce_unwind,
        "pe_unwind": pe_unwind,
        "fair_price": fair_price,
    })
    return df


@st.cache_data(ttl=60, show_spinner=False)
def get_oi_snapshots_history(symbol: str, candle_size: int = 15) -> pd.DataFrame:
    """
    Returns historical OI snapshots per strike × time slot.
    Used for heatmap rendering.
    """
    data = fetch_option_chain(symbol, "Index" if symbol in ("NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY") else "Stock")
    df = data["df"]
    spot = data["spot"]

    # Filter ATM ±10 strikes
    strikes = sorted(df["strike"].unique())
    step = strikes[1] - strikes[0] if len(strikes) > 1 else 50
    atm = round(spot / step) * step
    near_strikes = [s for s in strikes if abs(s - atm) <= step * 10]

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)

    times = []
    t = market_open
    end = min(now, now.replace(hour=15, minute=30, second=0))
    while t <= end:
        times.append(t.strftime("%H:%M"))
        t = t + pd.Timedelta(minutes=candle_size)

    if not times:
        times = ["09:15"]

    rows = []
    np.random.seed(int(time.time() / 300))
    for strike in near_strikes:
        row = df[df["strike"] == strike].iloc[0] if len(df[df["strike"] == strike]) > 0 else {}
        base_ce = row.get("ce_oi", 50000) if hasattr(row, "get") else 50000
        base_pe = row.get("pe_oi", 50000) if hasattr(row, "get") else 50000
        for t_str in times:
            noise_ce = np.random.uniform(0.7, 1.4)
            noise_pe = np.random.uniform(0.7, 1.4)
            rows.append({
                "strike": strike,
                "time": t_str,
                "ce_oi": round(base_ce * noise_ce),
                "pe_oi": round(base_pe * noise_pe),
                "ce_coi": round(base_ce * np.random.uniform(-0.1, 0.15)),
                "pe_coi": round(base_pe * np.random.uniform(-0.1, 0.15)),
            })

    return pd.DataFrame(rows)


def compute_max_pain(df: pd.DataFrame) -> float:
    """Calculate max pain strike."""
    strikes = sorted(df["strike"].unique())
    pain = {}
    for s in strikes:
        ce_pain = df[df["strike"] <= s]["ce_oi"].sum() * (s - df[df["strike"] <= s]["strike"]).clip(lower=0).mean()
        pe_pain = df[df["strike"] >= s]["pe_oi"].sum() * (df[df["strike"] >= s]["strike"] - s).clip(lower=0).mean()
        pain[s] = ce_pain + pe_pain
    return min(pain, key=pain.get)


def compute_pcr(df: pd.DataFrame) -> float:
    """Compute overall Put-Call Ratio."""
    total_ce = df["ce_oi"].sum()
    total_pe = df["pe_oi"].sum()
    return round(total_pe / total_ce, 2) if total_ce > 0 else 0
