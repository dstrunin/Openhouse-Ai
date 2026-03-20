# Openhouse-Ai

**Live app:** [Streamlit (deployed)](https://openhouse-ai-2hmegkbyadye8uab8l3iua.streamlit.app/)

**MVP:** If an iBuyer bought this house today, would they make money?

**Important:** Dollar amounts are built from **Zillow ZHVI** (typical home value for the metro), scaled by your sqft — **not** median sale price or a Zestimate for one address.

*Inspired by Opendoor's iBuying model and the challenge of profitable instant home buying*

**GitHub “About”** (description, website, topics): copy-paste / `gh` commands in [`.github/GITHUB_ABOUT.md`](.github/GITHUB_ABOUT.md).

[![Smoke tests](https://github.com/dstrunin/Openhouse-Ai/actions/workflows/smoke.yml/badge.svg)](https://github.com/dstrunin/Openhouse-Ai/actions/workflows/smoke.yml)

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
Latest metro ZHVI (Streamlit) → resale-style estimate scaled by sqft; hold time from Zillow days-on-market data
  ↓
Valuation & Liquidity models (XGBoost) — trained for future use / research
  ↓
Offer Engine → offer price, expected profit
  ↓
Streamlit UI
```

## Key Features

- **Market data**: Latest Zillow ZHVI and days on market per metro (plus national fallback)
- **Offer math**: Transaction cost, holding cost, and risk margin on the ZHVI-based resale estimate — **sidebar sliders** (defaults from `configs/settings.yaml`) plus a one-line **assumptions** summary on each result
- **ZIP or metro**: county FIPS + Census CBSA (2020) + pgeocode, or pick from 660+ metros; the UI notes when the ZIP’s postal city differs from the Zillow metro used for stats (e.g. Round Rock → Austin, TX)

## Data Sources

- **ZHVI, days on market, inventory:** Zillow Research (auto-downloaded)
- **Mortgage rate:** FRED (MORTGAGE30US) or Freddie Mac PMMS CSV fallback
- **ZIP → CBSA:** U.S. Census Bureau 2020 CBSA county delineation (`data/geo/fips_to_cbsa.parquet`). Regenerate with `python scripts/build_fips_cbsa_crosswalk.py` (needs `xlrd` for the `.xls` file).

## Deploy to Streamlit Cloud

**Pre-flight (local):**

```bash
.venv/bin/python scripts/smoke_zip_resolution.py   # ZIP → metro sanity check
.venv/bin/streamlit run app.py                     # click through one ZIP + one metro
```

**Commit everything the app needs** (Streamlit Cloud does not run `train.py` for you):

- `data/processed/latest_by_metro.parquet` and model dirs under `data/processed/models/`
- `data/geo/fips_to_cbsa.parquet` (Census crosswalk; do **not** commit `data/geo/_list1_2020.xls`)

**Push to GitHub**

```bash
git add -A
git status    # confirm no secrets / huge raw files
git commit -m "Your message"
git push origin main
```

*(New repo? `git init`, `git remote add origin …`, then push as above.)*

**Streamlit Cloud**

1. [share.streamlit.io](https://share.streamlit.io) → **New app** → your repo
2. Main file: `app.py` → **Deploy**
3. Python version: match `runtime.txt` if present

No API secrets are required for the deployed app (prebuilt data + models in the repo). You still need `FRED_API_KEY` locally if you run `train.py` to refresh data.

## Reliability & refreshing data

**CI (GitHub Actions):** On every push and pull request to `main`, [`.github/workflows/smoke.yml`](.github/workflows/smoke.yml) installs deps and runs `scripts/smoke_zip_resolution.py` (ZIP → metro checks; uses network for pgeocode). You can also run it manually: **Actions → Smoke tests → Run workflow**.

**Refreshing Zillow/mortgage data (local):**

1. `export FRED_API_KEY=...` (see Quick Start).
2. `.venv/bin/python train.py` — downloads Zillow series, refreshes `data/processed/latest_by_metro.parquet`, retrains models under `data/processed/models/`.
3. Run `scripts/smoke_zip_resolution.py` after changes to geo or resolution logic.
4. Commit the updated parquet(s) / model artifacts you want the **deployed** app to use, then `git push`.
5. Streamlit Cloud redeploys from `main` (or trigger a redeploy in the dashboard).

**ZIP → CBSA crosswalk only** (Census file changed / rebuild): `pip install xlrd` then `python scripts/build_fips_cbsa_crosswalk.py`, commit `data/geo/fips_to_cbsa.parquet` (not the cached `.xls`).

## Data Coverage

- **660+ metros** from Zillow Research: ZHVI (typical home value), days on market, inventory
- **Direct data** — latest ZHVI + days on market (no model for the live number shown in the app)
- **ZIP lookup**: pgeocode → county FIPS → [Census CBSA delineation](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html) → Zillow metro name; fallback to city substring match
- **National fallback** when ZIP has no metro data
- **Metro selector** — pick from 660+ metros directly

## MVP Success Criteria

✅ Run `app.py`, enter a property, get a full iBuyer decision.
