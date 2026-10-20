"""Validation and cleaning for daily air quality data."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .aqi import add_aqi_columns
from .config import REQUIRED_COLUMNS

MAX_PM25 = 1000.0
MAX_PM10 = 2000.0


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean a raw daily table. Returns (clean_df, report).

    Input columns: date, city, pm25 and/or pm10 (ug/m3). Optional: source,
    is_synthetic. Output has one row per (city, date) plus AQI columns.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {missing}")
    if not ({"pm25", "pm10"} & set(df.columns)):
        raise ValueError("Need at least one of the columns: pm25, pm10")

    report = {"rows_in": int(len(df))}
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    out["city"] = out["city"].astype(str).str.strip()
    for col in ("pm25", "pm10"):
        if col not in out:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")

    bad_date = out["date"].isna() | out["city"].eq("") | out["city"].eq("nan")
    report["dropped_bad_date_or_city"] = int(bad_date.sum())
    out = out[~bad_date]

    # Physically impossible readings become missing, not zero.
    invalid25 = (out["pm25"] < 0) | (out["pm25"] > MAX_PM25)
    invalid10 = (out["pm10"] < 0) | (out["pm10"] > MAX_PM10)
    report["invalid_values_set_nan"] = int(invalid25.sum() + invalid10.sum())
    out.loc[invalid25, "pm25"] = np.nan
    out.loc[invalid10, "pm10"] = np.nan

    empty = out["pm25"].isna() & out["pm10"].isna()
    report["dropped_no_pollutant"] = int(empty.sum())
    out = out[~empty]

    # PM2.5 is a subset of PM10, so pm25 > pm10 signals a sensor problem.
    out["pm_inconsistent"] = out["pm25"] > out["pm10"]
    report["pm25_gt_pm10_flagged"] = int(out["pm_inconsistent"].sum())

    meta = {c: "first" for c in ("source", "is_synthetic") if c in out.columns}
    agg = {"pm25": "mean", "pm10": "mean", "pm_inconsistent": "max", **meta}
    before = len(out)
    out = out.groupby(["city", "date"], as_index=False).agg(agg)
    report["duplicates_merged"] = int(before - len(out))

    if "is_synthetic" not in out:
        out["is_synthetic"] = False
    out["is_synthetic"] = out["is_synthetic"].astype(bool)
    out = add_aqi_columns(out).sort_values(["city", "date"]).reset_index(drop=True)
    report["rows_out"] = int(len(out))
    report["cities"] = int(out["city"].nunique())
    report["date_min"] = str(out["date"].min().date()) if len(out) else None
    report["date_max"] = str(out["date"].max().date()) if len(out) else None
    report["any_synthetic"] = bool(out["is_synthetic"].any())
    return out, report
