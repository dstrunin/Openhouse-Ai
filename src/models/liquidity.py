"""
Liquidity Model: XGBoost predicting days_on_market (expected hold time).
Features: price_relative_to_median, inventory, season, mortgage_rate.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add liquidity model features."""
    df = df.copy()
    df["month"] = df["date"].dt.month
    df["season_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["season_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    # price_relative_to_median: listing_price / median_sale_price
    # For training we use 1.0 (at median) as proxy when we don't have listing price
    if "price_relative_to_median" not in df.columns:
        df["price_relative_to_median"] = 1.0
    return df


class LiquidityModel:
    """XGBoost model for predicting days on market (expected hold time)."""

    FEATURES = ["price_relative_to_median", "inventory", "season_sin", "season_cos", "mortgage_rate"]
    TARGET = "days_on_market"

    def __init__(self):
        self.model = None

    def fit(self, df: pd.DataFrame, median_prices: pd.DataFrame | None = None) -> "LiquidityModel":
        """
        Fit on training data. If median_prices provided, use for price_relative_to_median.
        Otherwise assume 1.0 (priced at median).
        """
        df = _add_features(df)
        if "price_relative_to_median" not in df.columns or df["price_relative_to_median"].isna().all():
            df["price_relative_to_median"] = 1.0
        df = df.dropna(subset=self.FEATURES + [self.TARGET])
        X = df[self.FEATURES]
        y = df[self.TARGET]
        self.model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
        self.model.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        df = _add_features(df)
        X = df[self.FEATURES]
        return self.model.predict(X)

    def predict_for_metro(
        self,
        metro: str,
        date: pd.Timestamp,
        mortgage_rate: float,
        inventory: float,
        price_relative_to_median: float = 1.0,
    ) -> float:
        """Predict expected hold time (days) for a metro."""
        month = date.month
        season_sin = np.sin(2 * np.pi * month / 12)
        season_cos = np.cos(2 * np.pi * month / 12)
        X = pd.DataFrame([{
            "price_relative_to_median": price_relative_to_median,
            "inventory": inventory,
            "season_sin": season_sin,
            "season_cos": season_cos,
            "mortgage_rate": mortgage_rate,
        }])
        return max(1, float(self.model.predict(X)[0]))  # min 1 day

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path.with_suffix(".json")))

    def load(self, path: str | Path) -> "LiquidityModel":
        path = Path(path)
        self.model = xgb.XGBRegressor()
        self.model.load_model(str(path.with_suffix(".json")))
        return self
