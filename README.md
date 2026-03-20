# Openhouse-Ai

**MVP:** If an iBuyer bought this house today, would they make money?

*Inspired by Opendoor's iBuying model and the challenge of profitable instant home buying*

## Quick Start

```bash
# 1. Create venv and install deps
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Set FRED API key (free: https://fred.stlouisfed.org/docs/api/api_key.html)
export FRED_API_KEY=your_key

# 3. Train models (downloads Zillow data, fetches mortgage rates)
.venv/bin/python train.py

# 4. Run app
.venv/bin/streamlit run app.py
```

Enter a ZIP or metro, beds, baths, sqft → get full iBuyer decision.

## Architecture

```
Data (Zillow ZHVI, days on market, inventory + FRED mortgage rate)
  ↓
Latest metro row (Streamlit) → resale estimate scaled by sqft, hold time from data
  ↓
Valuation & Liquidity models (XGBoost) — trained for future use / research
  ↓
Offer Engine → offer price, expected profit
  ↓
Streamlit UI
```

## Key Features

- **Market data**: Latest Zillow ZHVI and days on market per metro (plus national fallback)
- **Offer math**: Transaction cost, holding cost, and risk margin on predicted resale
- **ZIP or metro**: pgeocode lookup or pick from 660+ metros

## Data Sources

- **ZHVI, days on market, inventory:** Zillow Research (auto-downloaded)
- **Mortgage rate:** FRED (MORTGAGE30US) or Freddie Mac PMMS CSV fallback

## Deploy to Streamlit Cloud

1. **Push to GitHub** (models must be committed):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/Openhouse-Ai.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app" → select `Openhouse-Ai` repo
   - Main file: `app.py`
   - Click "Deploy"

No secrets needed — the app uses pre-trained models in the repo.

## Data Coverage

- **660+ metros** from Zillow Research: ZHVI (typical home value), days on market, inventory
- **Direct data** — uses latest Zillow values (no model prediction for current valuation)
- **ZIP lookup** via pgeocode → city/state → metro match
- **National fallback** when ZIP has no metro data
- **Metro selector** — pick from 660+ metros directly

## MVP Success Criteria

✅ Run `app.py`, enter a property, get a full iBuyer decision.
