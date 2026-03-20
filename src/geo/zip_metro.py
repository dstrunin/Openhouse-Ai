"""
Map ZIP → Zillow metro using pgeocode county FIPS + Census CBSA delineation.

CBSA titles (e.g. "Austin-Round Rock-Georgetown, TX") are reduced to the
principal city + lead state ("Austin, TX") and matched to Zillow RegionName.
"""

from __future__ import annotations

import pandas as pd

# US state / territory FIPS used with pgeocode county_code (3-digit county within state)
STATE_FIPS: dict[str, int] = {
    "AL": 1,
    "AK": 2,
    "AZ": 4,
    "AR": 5,
    "CA": 6,
    "CO": 8,
    "CT": 9,
    "DE": 10,
    "DC": 11,
    "FL": 12,
    "GA": 13,
    "HI": 15,
    "ID": 16,
    "IL": 17,
    "IN": 18,
    "IA": 19,
    "KS": 20,
    "KY": 21,
    "LA": 22,
    "ME": 23,
    "MD": 24,
    "MA": 25,
    "MI": 26,
    "MN": 27,
    "MS": 28,
    "MO": 29,
    "MT": 30,
    "NE": 31,
    "NV": 32,
    "NH": 33,
    "NJ": 34,
    "NM": 35,
    "NY": 36,
    "NC": 37,
    "ND": 38,
    "OH": 39,
    "OK": 40,
    "OR": 41,
    "PA": 42,
    "RI": 44,
    "SC": 45,
    "SD": 46,
    "TN": 47,
    "TX": 48,
    "UT": 49,
    "VT": 50,
    "VA": 51,
    "WA": 53,
    "WV": 54,
    "WI": 55,
    "WY": 56,
    "PR": 72,
}


def county_fips_from_pgeocode(state_code: str, county_code: float | int | None) -> int | None:
    """Combine Census state FIPS + county code from pgeocode into 5-digit county FIPS."""
    if not state_code or county_code is None or (isinstance(county_code, float) and pd.isna(county_code)):
        return None
    st = str(state_code).strip().upper()
    sf = STATE_FIPS.get(st)
    if sf is None:
        return None
    try:
        cc = int(float(county_code))
    except (TypeError, ValueError):
        return None
    return sf * 1000 + cc


def _principal_metro_candidate(cbsa_title: str) -> str:
    """CBSA title → 'City, ST' using OMB naming (first hyphen segment + lead state)."""
    t = (cbsa_title or "").strip()
    if ", " not in t:
        return ""
    left, states_part = t.rsplit(", ", 1)
    state_abbr = states_part.split("-")[0].strip()
    principal_city = left.split("-")[0].strip()
    if not principal_city or not state_abbr:
        return ""
    return f"{principal_city}, {state_abbr}"


def _normalize_candidate(candidate: str) -> str:
    """Fix known mismatches between OMB titles and Zillow RegionName."""
    c = candidate
    # OMB lists consolidated city/county this way; Zillow uses "Louisville, KY"
    c = c.replace("Louisville/Jefferson County", "Louisville")
    return c


def _metro_variants(metro: str) -> list[str]:
    """St. ↔ Saint for Zillow/Census spelling differences."""
    out = [metro]
    if ", " not in metro:
        return out
    city, st = metro.rsplit(", ", 1)
    if city.startswith("St. "):
        out.append(f"Saint {city[4:]}, {st}")
    elif city.startswith("Saint "):
        out.append(f"St. {city[6:]}, {st}")
    return out


def cbsa_title_to_zillow_metro(cbsa_title: str, available_metros: set[str]) -> str | None:
    """
    Map a CBSA Title from Census delineation to a Zillow metro name in our dataset.
    Returns None if no match.
    """
    candidate = _normalize_candidate(_principal_metro_candidate(cbsa_title))
    if not candidate:
        return None
    for m in _metro_variants(candidate):
        if m in available_metros:
            return m
    return None


def resolve_metro_for_zip(
    zip_code: str,
    place: str,
    state: str,
    county_code: float | int | None,
    available_metros: list[str],
    fips_to_cbsa: dict[int, str],
) -> tuple[str | None, str]:
    """
    Pure resolution: geocode fields + crosswalk → Zillow metro name.

    Returns (metro_or_none, location_display) where location_display is always
    ``ZIP {zip} ({place}, {state})`` when inputs are valid.
    """
    city_state = f"{place}, {state}"
    display = f"ZIP {zip_code} ({city_state})"
    metro_set = {m for m in available_metros if m != "National"}

    fips = county_fips_from_pgeocode(state, county_code)
    if fips is not None and fips_to_cbsa:
        cbsa_title = fips_to_cbsa.get(fips)
        if cbsa_title:
            via_cbsa = cbsa_title_to_zillow_metro(cbsa_title, metro_set)
            if via_cbsa:
                return via_cbsa, display

    for m in available_metros:
        if city_state == m:
            return m, display

    place_lower = place.lower()
    for m in available_metros:
        if place_lower in m.lower():
            return m, display

    return None, display
