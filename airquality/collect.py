"""Collect REAL air quality data for Bangladesh from the OpenAQ v3 API.

You need a free API key: create an account at https://explore.openaq.org,
then set it as an environment variable:

    export OPENAQ_API_KEY="your-key"

The output follows the project's standard schema (date, city, pm25, pm10,
source, is_synthetic=False). Coverage in Bangladesh is limited and uneven
(a handful of stations), so always check how many days each city really has.

NOTE: this module was written against the OpenAQ v3 documentation. Run it once
with your own key and inspect the CSV before trusting it.
"""
from __future__ import annotations

import os
import time

import pandas as pd
import requests

BASE_URL = "https://api.openaq.org/v3"
PARAMETERS = {"pm25", "pm10"}


def _get(path: str, params: dict, api_key: str, retries: int = 3) -> dict:
    headers = {"X-API-Key": api_key}
    for attempt in range(retries):
        resp = requests.get(f"{BASE_URL}{path}", params=params, headers=headers, timeout=30)
        if resp.status_code == 429:  # rate limited
            time.sleep(2 ** attempt * 5)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("OpenAQ rate limit: retries exhausted")


def list_locations(api_key: str, iso: str = "BD") -> list[dict]:
    """All monitoring locations in a country that report PM2.5 or PM10."""
    found, page = [], 1
    while True:
        data = _get("/locations", {"iso": iso, "limit": 100, "page": page}, api_key)
        results = data.get("results", [])
        found.extend(results)
        if len(results) < 100:
            break
        page += 1
    return found


def pm_sensors(location: dict) -> list[tuple[int, str]]:
    """(sensor_id, parameter_name) for the PM sensors of one location."""
    out = []
    for s in location.get("sensors", []):
        name = (s.get("parameter") or {}).get("name", "").lower()
        if name in PARAMETERS:
            out.append((s["id"], name))
    return out


def parse_daily(results: list[dict], city: str, parameter: str) -> pd.DataFrame:
    """Turn OpenAQ /sensors/{id}/days results into rows (pure function, testable)."""
    rows = []
    for r in results:
        period = (r.get("period") or {}).get("datetimeFrom") or {}
        stamp = period.get("local") or period.get("utc")
        if stamp is None or r.get("value") is None:
            continue
        rows.append({"date": stamp[:10], "city": city, parameter: r["value"]})
    return pd.DataFrame(rows, columns=["date", "city", parameter])


def collect_openaq(date_from: str, date_to: str, api_key: str | None = None,
                   iso: str = "BD") -> pd.DataFrame:
    """Download daily PM2.5 / PM10 for every Bangladesh location."""
    api_key = api_key or os.environ.get("OPENAQ_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAQ_API_KEY (free key from explore.openaq.org).")
    frames: dict[str, list[pd.DataFrame]] = {"pm25": [], "pm10": []}
    for loc in list_locations(api_key, iso):
        city = loc.get("locality") or loc.get("name") or f"location-{loc['id']}"
        for sensor_id, parameter in pm_sensors(loc):
            data = _get(f"/sensors/{sensor_id}/days",
                        {"datetime_from": date_from, "datetime_to": date_to, "limit": 1000},
                        api_key)
            frames[parameter].append(parse_daily(data.get("results", []), city, parameter))
            time.sleep(0.5)  # be polite to the API

    def merge(parts, col):
        if not parts:
            return pd.DataFrame(columns=["date", "city", col])
        return pd.concat(parts).groupby(["date", "city"], as_index=False)[col].mean()

    out = pd.merge(merge(frames["pm25"], "pm25"), merge(frames["pm10"], "pm10"),
                   on=["date", "city"], how="outer")
    out["source"] = "OpenAQ"
    out["is_synthetic"] = False
    return out.sort_values(["city", "date"]).reset_index(drop=True)


def load_csv(path: str) -> pd.DataFrame:
    """Load your own CSV (columns: date, city, pm25, pm10). Treated as real data."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "is_synthetic" not in df.columns:
        df["is_synthetic"] = False
    return df
