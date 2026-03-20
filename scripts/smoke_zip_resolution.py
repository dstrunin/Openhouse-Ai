#!/usr/bin/env python3
"""
Smoke-test ZIP → metro resolution (pgeocode + fips_to_cbsa.parquet).
Run before deploy: .venv/bin/python scripts/smoke_zip_resolution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pgeocode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.geo.zip_metro import resolve_metro_for_zip  # noqa: E402

# (zip, expected_metro substring or exact name — we use exact for stability)
CASES: list[tuple[str, str]] = [
    ("78664", "Austin, TX"),  # Round Rock suburb → CBSA
    ("78701", "Austin, TX"),
    ("10001", "New York, NY"),
    ("40202", "Louisville, KY"),  # Louisville/Jefferson CBSA normalization
    ("60614", "Chicago, IL"),
    ("90210", "Los Angeles, CA"),  # Beverly Hills → LA CBSA principal
]


def load_fips_map() -> dict[int, str]:
    path = ROOT / "data" / "geo" / "fips_to_cbsa.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path} — run scripts/build_fips_cbsa_crosswalk.py")
    df = pd.read_parquet(path)
    return dict(zip(df["fips"].astype(int), df["CBSA Title"].astype(str)))


def main() -> int:
    latest = ROOT / "data" / "processed" / "latest_by_metro.parquet"
    if not latest.exists():
        print(f"Missing {latest} — run train.py first.", file=sys.stderr)
        return 1

    metros = pd.read_parquet(latest)["metro"].tolist()
    fips_map = load_fips_map()
    nomi = pgeocode.Nominatim("us")

    failed = 0
    for z, expected in CASES:
        r = nomi.query_postal_code(z)
        if r is None or pd.isna(r.get("place_name")):
            print(f"FAIL {z}: no geocode result")
            failed += 1
            continue
        place = str(r["place_name"]).strip()
        state = str(r["state_code"]).strip()
        county_code = r.get("county_code")
        metro, display = resolve_metro_for_zip(z, place, state, county_code, metros, fips_map)
        if metro != expected:
            print(f"FAIL {z}: got {metro!r}, expected {expected!r} | {display}")
            failed += 1
        else:
            print(f"OK   {z} → {metro} | {display}")

    if failed:
        print(f"\n{failed} case(s) failed.", file=sys.stderr)
        return 1
    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
