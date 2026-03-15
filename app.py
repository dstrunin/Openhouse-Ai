"""
Openhouse-Ai: iBuyer profitability checker.
Enter a property (city, beds, baths, sqft) → get full iBuyer decision.
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


def resolve_metro(city: str, config: dict, available_metros: list[str]) -> str | None:
    """Map user city input to metro. Returns None if not found."""
    city_lower = city.strip().lower()
    # Config mapping
    mapping = config.get("city_to_metro", {})
    if city_lower in mapping:
        metro = mapping[city_lower]
        if metro in available_metros:
            return metro
    # Fuzzy: find metro containing city name
    for m in available_metros:
        if city_lower in m.lower():
            return m
    return None


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

    # Check if models exist
    if not (MODELS_DIR / "valuation.json").exists():
        st.error(
            "Models not trained yet. Run: `python train.py` first.\n\n"
            "You'll need a free FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html\n"
            "Set it: `export FRED_API_KEY=your_key`"
        )
        return

    valuation, liquidity, engine = load_models()
    config = load_config()

    # Load latest metro data
    latest_path = PROCESSED_DIR / "latest_by_metro.parquet"
    if not latest_path.exists():
        st.error("Run `python train.py` first to generate latest_by_metro.parquet")
        return
    latest = pd.read_parquet(latest_path)
    available_metros = latest["metro"].tolist()

    # Inputs
    st.sidebar.header("Property Inputs")
    city = st.sidebar.text_input("City", placeholder="e.g. Austin, Chicago")
    beds = st.sidebar.number_input("Beds", min_value=1, max_value=10, value=3)
    baths = st.sidebar.number_input("Baths", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
    sqft = st.sidebar.number_input("Sqft", min_value=100, max_value=20000, value=1800)

    if st.sidebar.button("Get iBuyer Decision"):
        if not city:
            st.warning("Enter a city.")
        else:
            metro = resolve_metro(city, config, available_metros)
            if not metro:
                st.error(
                    f"City '{city}' not found. Try: {', '.join(available_metros[:10])}..."
                )
            else:
                row = latest[latest["metro"] == metro].iloc[0]
                date = pd.to_datetime(row["date"])
                mortgage_rate = float(row["mortgage_rate"])
                inventory = float(row["inventory"])

                # Valuation: metro median scaled by property size (baseline 2000 sqft = typical US home)
                metro_median = valuation.predict_for_metro(metro, date, mortgage_rate, inventory)
                sqft_factor = sqft / 2000  # 2000 sqft = 1.0x (US median home size)
                predicted_resale = metro_median * sqft_factor
                # Liquidity: larger homes may sit longer; slight adjustment by size
                base_hold_days = liquidity.predict_for_metro(
                    metro, date, mortgage_rate, inventory, price_relative_to_median=1.0
                )
                # Larger homes typically take longer to sell (~5% per 1000 sqft above 2000)
                size_hold_factor = 1 + 0.05 * ((sqft - 2000) / 1000)
                expected_hold_days = max(1, base_hold_days * size_hold_factor)
                # Offer Engine
                result = engine.compute(predicted_resale, expected_hold_days)

                # Display property inputs
                st.write("**Property**")
                st.write(f"{metro} · {int(beds)} beds · {baths} baths · {sqft:,} sqft")
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

    st.sidebar.caption("Valuation scales by sqft (2000 sqft = metro median). Beds/baths reserved for future.")


if __name__ == "__main__":
    main()
