"""
Openhouse-Ai: iBuyer profitability checker.
Enter a property (ZIP code, beds, baths, sqft) → get full iBuyer decision.
"""

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.models import LiquidityModel, ValuationModel
from src.simulation import OfferEngine

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PROCESSED_DIR / "models"
CONFIG_PATH = PROJECT_ROOT / "configs" / "settings.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@st.cache_resource
def _get_zip_lookup():
    import pgeocode
    return pgeocode.Nominatim("us")


def resolve_metro_from_zip(zip_code: str, available_metros: list[str]) -> tuple[str | None, str | None]:
    """
    Look up ZIP code and return (metro, location_display) or (None, None) if not found.
    location_display is e.g. "ZIP 78701 (Austin, TX)" for the output.
    """
    zip_code = zip_code.strip().replace("-", "").replace(" ", "")
    if len(zip_code) != 5 or not zip_code.isdigit():
        return None, None
    try:
        nomi = _get_zip_lookup()
        result = nomi.query_postal_code(zip_code)
        if result is None or pd.isna(result.get("place_name")):
            return None, None
        place = str(result["place_name"]).strip()
        state = str(result["state_code"]).strip() if "state_code" in result else ""
        if not place or not state:
            return None, None
        city_state = f"{place}, {state}"
        # Try exact match first
        for m in available_metros:
            if city_state == m:
                return m, f"ZIP {zip_code} ({city_state})"
        # Fuzzy: metro contains city name
        place_lower = place.lower()
        for m in available_metros:
            if place_lower in m.lower():
                return m, f"ZIP {zip_code} ({city_state})"
        return None, f"ZIP {zip_code} ({city_state})"
    except Exception:
        return None, None


def validate_property(beds: int, baths: float, sqft: int) -> list[str]:
    """Return list of validation errors. Empty if valid."""
    errors = []
    # Baths vs beds: typically 0.5-1.5 baths per bedroom
    if baths < beds * 0.3:
        errors.append(f"Too few bathrooms ({baths}) for {beds} bedrooms. Expect at least {beds * 0.5:.1f} baths.")
    if baths > beds + 2:
        errors.append(f"Too many bathrooms ({baths}) for {beds} bedrooms. Unusual for a single-family home.")
    # Sqft per bedroom: typically 150-600 sqft
    sqft_per_bed = sqft / beds
    if sqft_per_bed < 120:
        errors.append(f"Only {sqft_per_bed:.0f} sqft per bedroom — unusually small. Check your numbers.")
    if sqft_per_bed > 800:
        errors.append(f"{sqft_per_bed:.0f} sqft per bedroom — unusually large. Check your numbers.")
    return errors


@st.cache_resource
def load_models():
    """Load trained models (cached)."""
    valuation = ValuationModel().load(MODELS_DIR / "valuation")
    liquidity = LiquidityModel().load(MODELS_DIR / "liquidity")
    config = load_config()
    engine = OfferEngine(
        transaction_cost_pct=config.get("transaction_cost_pct", 0.08),
        holding_cost_per_day=config.get("holding_cost_per_day", 150),
        risk_margin_pct=config.get("risk_margin_pct", 0.05),
    )
    return valuation, liquidity, engine


def main():
    st.set_page_config(page_title="Openhouse-Ai | iBuyer Decision", layout="centered")
    st.title("Openhouse-Ai")
    st.subheader("If an iBuyer bought this house today, would they make money?")

    # Check if data exists (we use latest data directly; models reserved for future forecasting)
    latest_path = PROCESSED_DIR / "latest_by_metro.parquet"
    if not latest_path.exists():
        st.error("Run `python train.py` first to generate data.")
        return

    _, _, engine = load_models()
    config = load_config()

    # Load latest metro data (must have days_on_market — re-run train.py if missing)
    latest = pd.read_parquet(latest_path)
    if "days_on_market" not in latest.columns:
        st.error("Re-run `python train.py` to regenerate data with days_on_market.")
        return
    available_metros = latest["metro"].tolist()
    data_as_of = pd.to_datetime(latest["date"]).max()
    st.caption(f"Data as of {data_as_of.strftime('%B %Y')} · Zillow Research")

    # Inputs
    st.sidebar.header("Property Inputs")
    input_mode = st.sidebar.radio("Location", ["ZIP Code", "Select Metro"], horizontal=True)
    if input_mode == "ZIP Code":
        zip_code = st.sidebar.text_input("ZIP Code", placeholder="e.g. 78701, 10001", max_chars=10)
        metro_override = None
    else:
        metro_options = ["— Select metro —"] + sorted([m for m in available_metros if m != "National"])
        metro_override = st.sidebar.selectbox("Metro Area", metro_options)
        metro_override = None if metro_override == "— Select metro —" else metro_override
        zip_code = ""
    beds = st.sidebar.number_input("Beds", min_value=1, max_value=8, value=3, help="1–8 bedrooms")
    baths = st.sidebar.number_input("Baths", min_value=0.5, max_value=8.0, value=2.0, step=0.5, help="0.5–8 bathrooms")
    sqft = st.sidebar.number_input("Sqft", min_value=400, max_value=15000, value=1800, step=100, help="400–15,000 sqft")

    if st.sidebar.button("Get iBuyer Decision"):
        if input_mode == "Select Metro" and not metro_override:
            st.warning("Select a metro area.")
        elif input_mode == "ZIP Code" and (not zip_code or not zip_code.strip()):
            st.warning("Enter a ZIP code.")
        else:
            validation_errors = validate_property(int(beds), baths, sqft)
            if validation_errors:
                for err in validation_errors:
                    st.error(err)
            else:
                if metro_override:
                    metro, location_display = metro_override, metro_override
                    use_national_fallback = False
                else:
                    metro, location_display = resolve_metro_from_zip(zip_code, available_metros)
                    if not metro:
                        if location_display:
                            metro, location_display = "National", f"{location_display} (national average)"
                            use_national_fallback = True
                        else:
                            st.error("Invalid or unknown ZIP code. Enter a valid 5-digit US ZIP.")
                            metro = None
                    else:
                        use_national_fallback = False
                if metro:
                    row = latest[latest["metro"] == metro].iloc[0]
                    # Use latest data directly (Zillow ZHVI + days on market) — models were under-predicting
                    metro_median = float(row["median_sale_price"])
                    base_hold_days = float(row["days_on_market"])
                    sqft_factor = sqft / 2000  # 2000 sqft = 1.0x (US median home size)
                    predicted_resale = metro_median * sqft_factor
                    # Larger homes typically take longer to sell (~5% per 1000 sqft above 2000)
                    size_hold_factor = 1 + 0.05 * ((sqft - 2000) / 1000)
                    expected_hold_days = max(1, base_hold_days * size_hold_factor)
                    # Offer Engine
                    result = engine.compute(predicted_resale, expected_hold_days)

                    # Display property inputs
                    st.write("**Property**")
                    st.write(f"{location_display or metro} · {int(beds)} beds · {baths} baths · {sqft:,} sqft")
                    if use_national_fallback:
                        st.info("Metro-level data not available for this ZIP. Using national average — results are approximate.")
                    st.divider()

                    # Display
                    st.success("**iBuyer Decision**" if result.is_profitable else "**iBuyer Decision**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Offer Price", f"${result.offer_price:,.0f}")
                        st.caption("Max iBuyer would pay")
                    with col2:
                        st.metric("Expected Profit", f"${result.expected_profit:,.0f}")
                        st.caption("Target margin (5%)")
                    with col3:
                        st.metric("Expected Hold", f"{result.expected_hold_days:.0f} days")
                        st.caption("Time to sell")

                    st.divider()
                    st.write("**Breakdown**")
                    st.write(f"- Predicted resale: ${result.predicted_resale:,.0f}")
                    st.write(f"- Transaction cost (8%): ${result.transaction_cost:,.0f}")
                    st.write(f"- Holding cost ({result.expected_hold_days:.0f} × $150): ${result.holding_cost:,.0f}")
                    st.write(f"- Risk margin (5%): ${result.risk_margin:,.0f}")

                    if result.is_profitable:
                        st.success("Yes — iBuyer would make money.")
                    else:
                        st.warning("No — offer would be negative or unprofitable.")

    st.sidebar.caption(
        "Data: Zillow ZHVI (typical home value) + days on market. "
        "ZIP → metro via pgeocode; or select metro for 660+ areas."
    )


if __name__ == "__main__":
    main()
