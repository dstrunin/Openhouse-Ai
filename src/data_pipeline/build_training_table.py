"""
Build the single training table from Zillow + FRED data.
Output: date, metro, median_sale_price, days_on_market, inventory, mortgage_rate
"""

import os
from pathlib import Path

import pandas as pd
import requests


def _melt_zillow_wide(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
    """Melt Zillow wide-format (date columns) to long format."""
    id_cols = ["RegionID", "RegionName", "RegionType", "StateName"]
    id_cols = [c for c in id_cols if c in df.columns]
    date_cols = [c for c in df.columns if c not in id_cols and "-" in str(c)]
    melted = df.melt(
        id_vars=id_cols,
        value_vars=date_cols,
        var_name="date",
        value_name=value_name,
    )
    melted["date"] = pd.to_datetime(melted["date"])
    return melted


def _download_zillow_csv(url: str, cache_path: Path) -> pd.DataFrame:
    """Download Zillow CSV, cache locally."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return pd.read_csv(cache_path)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    cache_path.write_bytes(resp.content)
    return pd.read_csv(cache_path)


def _get_mortgage_rate(data_dir: Path) -> pd.DataFrame:
    """Fetch mortgage rate from FRED or Freddie Mac CSV."""
    api_key = os.environ.get("FRED_API_KEY")
    if api_key:
        try:
            from fredapi import Fred
            fred = Fred(api_key=api_key)
            s = fred.get_series("MORTGAGE30US")
            df = s.reset_index()
            df.columns = ["date", "mortgage_rate"]
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").resample("ME").last().reset_index()
            return df
        except Exception as e:
            print(f"FRED fetch failed: {e}, trying Freddie Mac...")

    # Fallback: Freddie Mac CSV (local or download)
    freddie_path = data_dir / "raw" / "PMMS_history.csv"
    if not freddie_path.exists():
        try:
            raw_dir = data_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            url = "https://www.freddiemac.com/pmms/docs/PMMS_history.csv"
            resp = requests.get(url, timeout=30)
            if resp.ok:
                freddie_path.write_bytes(resp.content)
        except Exception as e:
            print(f"Freddie Mac download failed: {e}")
    if freddie_path.exists():
        df = pd.read_csv(freddie_path)
        # Freddie format: date, pmms30 (30yr), pmms15, etc.
        date_col = df.columns[0]
        rate_col = "pmms30" if "pmms30" in df.columns else df.columns[1]
        df = df[[date_col, rate_col]].copy()
        df.columns = ["date", "mortgage_rate"]
        df["date"] = pd.to_datetime(df["date"])
        df["mortgage_rate"] = pd.to_numeric(df["mortgage_rate"], errors="coerce")
        df = df.dropna()
        df = df.set_index("date").resample("ME").last().reset_index()
        return df

    raise ValueError(
        "Set FRED_API_KEY (free at https://fred.stlouisfed.org/docs/api/api_key.html) "
        "or download PMMS_history.csv from https://freddiemac.com/pmms/pmms_archives to data/raw/"
    )


def build_training_table(
    data_dir: str | Path,
    zhvi_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Build single training table: date, metro, median_sale_price, days_on_market, inventory, mortgage_rate.
    """
    data_dir = Path(data_dir)
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. ZHVI (median_sale_price proxy)
    zhvi_path = zhvi_path or data_dir / "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    zhvi = pd.read_csv(zhvi_path)
    zhvi = zhvi[zhvi["RegionType"] == "msa"].copy()
    zhvi_long = _melt_zillow_wide(zhvi, "median_sale_price")
    zhvi_long = zhvi_long[["RegionName", "date", "median_sale_price"]].rename(
        columns={"RegionName": "metro"}
    )

    # 2. Days on market
    dom_url = "https://files.zillowstatic.com/research/public_csvs/mean_doz_pending/Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv"
    dom_path = raw_dir / "Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv"
    dom = _download_zillow_csv(dom_url, dom_path)
    dom = dom[dom["RegionType"] == "msa"].copy()
    dom_long = _melt_zillow_wide(dom, "days_on_market")
    dom_long = dom_long[["RegionName", "date", "days_on_market"]].rename(
        columns={"RegionName": "metro"}
    )

    # 3. Inventory
    inv_url = "https://files.zillowstatic.com/research/public_csvs/invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv"
    inv_path = raw_dir / "Metro_invt_fs_uc_sfrcondo_sm_month.csv"
    inv = _download_zillow_csv(inv_url, inv_path)
    inv = inv[inv["RegionType"] == "msa"].copy()
    inv_long = _melt_zillow_wide(inv, "inventory")
    inv_long = inv_long[["RegionName", "date", "inventory"]].rename(
        columns={"RegionName": "metro"}
    )

    # 4. Mortgage rate
    mortgage = _get_mortgage_rate(data_dir)
    mortgage["date"] = mortgage["date"].dt.normalize()

    # 5. Merge
    df = zhvi_long.merge(dom_long, on=["metro", "date"], how="inner")
    df = df.merge(inv_long, on=["metro", "date"], how="inner")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    mortgage["date"] = pd.to_datetime(mortgage["date"]).dt.normalize()
    df = df.merge(mortgage, on="date", how="left")

    # Drop rows with missing values
    df = df.dropna()

    # Sort
    df = df.sort_values(["metro", "date"]).reset_index(drop=True)

    out_path = processed_dir / "training_table.parquet"
    df.to_parquet(out_path, index=False)
    return df
