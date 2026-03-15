"""
Valuation Model: XGBoost predicting median_sale_price (predicted resale price).
Features: mortgage_rate, inventory, seasonality, lagged prices.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add seasonality and lagged price features."""
    df = df.copy()
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    # Cyclical seasonality
    df["season_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["season_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    # Lagged prices (by metro)
    df = df.sort_values(["metro", "date"])
    df["price_lag_1"] = df.groupby("metro")["median_sale_price"].shift(1)
    df["price_lag_2"] = df.groupby("metro")["median_sale_price"].shift(2)
    df["price_lag_3"] = df.groupby("metro")["median_sale_price"].shift(3)
    return df


class ValuationModel:
    """XGBoost model for predicting median resale price by metro."""

    FEATURES = ["mortgage_rate", "inventory", "season_sin", "season_cos", "price_lag_1", "price_lag_2", "price_lag_3"]
    TARGET = "median_sale_price"

    def __init__(self):
        self.model = None
        self.metro_encoder = None  # map metro -> index for last-known values
        self.last_prices = {}  # metro -> last 3 prices for inference

    def fit(self, df: pd.DataFrame) -> "ValuationModel":
        df = _add_features(df)
        df = df.dropna(subset=self.FEATURES + [self.TARGET])
        X = df[self.FEATURES]
        y = df[self.TARGET]
        self.model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
        self.model.fit(X, y)
        # Store last prices per metro for inference
        for metro in df["metro"].unique():
            metro_df = df[df["metro"] == metro].sort_values("date", ascending=False).head(3)
            self.last_prices[metro] = metro_df["median_sale_price"].tolist()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        df = _add_features(df)
        X = df[self.FEATURES]
        return self.model.predict(X)

    def predict_for_metro(self, metro: str, date: pd.Timestamp, mortgage_rate: float, inventory: float) -> float:
        """Predict resale price for a single metro at a given date."""
        month = date.month
        season_sin = np.sin(2 * np.pi * month / 12)
        season_cos = np.cos(2 * np.pi * month / 12)
        lags = self.last_prices.get(metro, self.last_prices.get(str(metro), []))
        if not lags:
            all_prices = [p for prices in self.last_prices.values() for p in (prices if isinstance(prices, list) else [])]
            fallback = all_prices[0] if all_prices else 300000
            lags = [fallback, fallback, fallback]
        p1 = lags[0] if len(lags) > 0 else lags[-1]
        p2 = lags[1] if len(lags) > 1 else p1
        p3 = lags[2] if len(lags) > 2 else p2
        X = pd.DataFrame([{
            "mortgage_rate": mortgage_rate,
            "inventory": inventory,
            "season_sin": season_sin,
            "season_cos": season_cos,
            "price_lag_1": p1,
            "price_lag_2": p2,
            "price_lag_3": p3,
        }])
        return float(self.model.predict(X)[0])

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path.with_suffix(".json")))
        import json
        meta = {"last_prices": self.last_prices}
        (path.parent / f"{path.stem}_meta.json").write_text(json.dumps(meta, default=str))

    def load(self, path: str | Path) -> "ValuationModel":
        path = Path(path)
        self.model = xgb.XGBRegressor()
        self.model.load_model(str(path.with_suffix(".json")))
        import json
        meta_path = path.parent / f"{path.stem}_meta.json"
        if meta_path.exists():
            self.last_prices = json.loads(meta_path.read_text())
        return self
