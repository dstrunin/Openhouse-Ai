#!/usr/bin/env python3
"""
Download Census 2020 CBSA delineation (list1_2020.xls) and build
data/geo/fips_to_cbsa.parquet for ZIP→metro via county FIPS.

Requires: pandas, pyarrow, requests, xlrd (for .xls)
  pip install xlrd requests
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

CENSUS_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2020/delineation-files/list1_2020.xls"
)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "data" / "geo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "fips_to_cbsa.parquet"

    xls_path = root / "data" / "geo" / "_list1_2020.xls"
    print(f"Downloading {CENSUS_URL} ...")
    r = requests.get(CENSUS_URL, timeout=120)
    r.raise_for_status()
    xls_path.write_bytes(r.content)
    print(f"  Saved {xls_path.stat().st_size} bytes")

    try:
        df = pd.read_excel(xls_path, header=2, engine="xlrd")
    except ImportError:
        print("Install xlrd to read .xls: pip install xlrd", file=sys.stderr)
        return 1

    df = df.dropna(subset=["FIPS State Code", "FIPS County Code"])
    df["fips"] = df["FIPS State Code"].astype(int) * 1000 + df["FIPS County Code"].astype(int)
    out = df[["fips", "CBSA Code", "CBSA Title"]].copy()
    out = out.rename(columns={"CBSA Code": "cbsa_code"})
    out["cbsa_code"] = pd.to_numeric(out["cbsa_code"], errors="coerce").astype("Int64")
    out.to_parquet(out_path, index=False)
    print(f"Wrote {out_path} ({len(out)} counties, unique fips: {out['fips'].nunique()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
