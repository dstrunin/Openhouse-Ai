# Openhouse-Ai

**MVP:** If an iBuyer bought this house today, would they make money?

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

Enter a city (e.g. Austin, Chicago), beds, baths, sqft → get full iBuyer decision.

## Architecture

```
Data (Zillow ZHVI, days on market, inventory + FRED mortgage rate)
  ↓
Valuation Model (XGBoost) → predicted resale price
  ↓
Liquidity Model (XGBoost) → expected hold time
  ↓
Offer Engine → offer price, expected profit
  ↓
Streamlit UI
```

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

- **660+ metros** from Zillow Research (ZHVI, days on market, inventory)
- **ZIP lookup** via pgeocode → city/state → metro match
- **National fallback** when ZIP has no metro data (uses US average)
- **Metro selector** — pick from 660+ metros directly for guaranteed coverage

## MVP Success Criteria

✅ Run `app.py`, enter a property, get a full iBuyer decision.
