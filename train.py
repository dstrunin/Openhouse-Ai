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

    # Save latest metro data for inference (mortgage_rate, inventory per metro)
    latest = df.sort_values("date", ascending=False).groupby("metro").first().reset_index()
    latest[["metro", "date", "mortgage_rate", "inventory", "median_sale_price"]].to_parquet(
        processed_dir / "latest_by_metro.parquet", index=False
    )
    print("Saved latest_by_metro.parquet for inference.")

    print("\nDone. Run: streamlit run app.py")
