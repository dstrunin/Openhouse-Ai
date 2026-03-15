"""
Train Valuation and Liquidity models, save to data/processed.
Run once to build models before using the app.
"""

from pathlib import Path

from src.data_pipeline import build_training_table
from src.models import LiquidityModel, ValuationModel


def main():
    project_root = Path(__file__).parent
    data_dir = project_root / "data"
    processed_dir = data_dir / "processed"
    models_dir = processed_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print("Building training table...")
    df = build_training_table(data_dir)
    print(f"  Rows: {len(df)}, Metros: {df['metro'].nunique()}")

    print("Training Valuation Model...")
    valuation = ValuationModel().fit(df)
    valuation.save(models_dir / "valuation")
    print("  Saved.")

    print("Training Liquidity Model...")
    liquidity = LiquidityModel().fit(df)
    liquidity.save(models_dir / "liquidity")
    print("  Saved.")

    # Save latest metro data for inference (use data directly, not model predictions)
    latest = df.sort_values("date", ascending=False).groupby("metro").first().reset_index()
    # Add National fallback (average across metros) for ZIPs without metro data
    national_row = pd.DataFrame([{
        "metro": "National",
        "date": latest["date"].iloc[0],
        "mortgage_rate": latest["mortgage_rate"].mean(),
        "inventory": latest["inventory"].mean(),
        "median_sale_price": latest["median_sale_price"].mean(),
        "days_on_market": latest["days_on_market"].mean(),
    }])
    latest = pd.concat([latest, national_row], ignore_index=True)
    latest[["metro", "date", "mortgage_rate", "inventory", "median_sale_price", "days_on_market"]].to_parquet(
        processed_dir / "latest_by_metro.parquet", index=False
    )
    print("Saved latest_by_metro.parquet (with National fallback).")

    print("\nDone. Run: streamlit run app.py")
