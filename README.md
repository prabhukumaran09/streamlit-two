# 📊 OI Analytics Dashboard

A production-grade **Open Interest Analytics Dashboard** for NSE FNO stocks and indices.
Inspired by iCharts, built with Python + Streamlit + Plotly.

---

## Features

| Tab | Description |
|---|---|
| **OI Stats** | Strike-wise OI bars (CE+PE grouped), OI Change bars, PCR by strike, Max Pain, ATM marker — mirrors iCharts OptionOIStatsBeta |
| **PE-CE OI Diff** | 4-panel layout: Total Buildup, Buildup 15-min, Total Unwinding, Unwinding 15-min with Fair Price overlay — mirrors iCharts TotalPECEOIDiff_Beta |
| **OI Heatmap** | CE and PE OI intensity heatmap (Strike × Time), CE-PE difference heatmap |
| **Spike Detection** | Auto-detects OI spikes across all FNO stocks with severity classification |
| **OI Table** | Full color-coded option chain table with buildup/unwinding classification |

---

## Quick Start (Local)

```bash
git clone https://github.com/YOUR_USERNAME/oi-dashboard.git
cd oi-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Deploy to Streamlit Cloud (Free, Public URL)

1. **Push to GitHub:**
```bash
git init
git add .
git commit -m "Initial OI Dashboard"
git remote add origin https://github.com/YOUR_USERNAME/oi-dashboard.git
git push -u origin main
```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click **New app**
   - Select your GitHub repo → branch `main` → file `app.py`
   - Click **Deploy** → you get a public URL like `https://your-app.streamlit.app`

> Free tier runs 24/7 with 1 GB RAM. Sufficient for this dashboard.

---

## Deploy to Railway (Alternative — always-on)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Add this `Procfile`:
```
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

---

## Deploy to Render (Free tier)

1. Connect your GitHub repo at [render.com](https://render.com)
2. Create a **Web Service**
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

---

## Real NSE Data Notes

The app fetches live data from `https://www.nseindia.com` public API:
- **Index OI**: `/api/option-chain-indices?symbol=NIFTY`
- **Stock OI**: `/api/option-chain-equities?symbol=RELIANCE`

**During market hours (9:15–15:30 IST, Mon–Fri):** Real data is fetched and cached for 60 seconds.

**Outside market hours or on connection error:** The app automatically shows high-quality simulated data that mirrors real OI distributions.

**NSE Session:** The fetcher initializes a session by visiting `nseindia.com` first (to obtain cookies), then calls the API. This is the standard approach used by all NSE data tools.

---

## Architecture

```
oi-dashboard/
├── app.py                    # Main Streamlit entry, sidebar, tab routing
├── requirements.txt
├── .streamlit/
│   └── config.toml           # Dark theme configuration
├── pages/
│   ├── oi_stats.py           # Tab 1: Strike-wise OI stats
│   ├── pe_ce_diff.py         # Tab 2: Buildup/Unwinding 4-panel
│   ├── oi_heatmap.py         # Tab 3: Heatmap
│   ├── spike_detection.py    # Tab 4: Spike detection
│   └── oi_table_page.py      # Tab 5: Full OI table
└── utils/
    ├── data_fetcher.py        # NSE API + simulation fallback
    ├── chart_theme.py         # Plotly dark theme constants
    └── market_utils.py        # Market hours, IST timezone
```

---

## Enhancements Roadmap

- [ ] **PostgreSQL storage** — store OI snapshots every 5 min during market hours
- [ ] **Telegram alerts** — push spike notifications via bot
- [ ] **Gamma Exposure (GEX)** — dealer gamma positioning chart
- [ ] **IV Surface** — 3D implied volatility by strike + expiry
- [ ] **FII/DII OI** — participant-wise OI from NSE participant data
- [ ] **Expected Move** — ATM straddle-based ±1σ range
- [ ] **Long/Short buildup classifier** — price + OI delta classification
- [ ] **Historical OI** — compare today vs same expiry prior months
- [ ] **Multi-expiry comparison** — current vs next week OI

---

## License

MIT — free to use, modify, and deploy.
