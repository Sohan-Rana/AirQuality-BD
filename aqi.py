"""US EPA style AQI calculation for PM2.5 and PM10.

Breakpoints: PM2.5 uses the 2024 US EPA revision, PM10 the long-standing table.
Note: this is the US EPA AQI, not the Bangladesh DoE AQI. Always say which
index you are reporting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# (conc_low, conc_high, aqi_low, aqi_high)
PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]
PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 604, 301, 500),
]

AQI_CATEGORIES = [
    "Good",
    "Moderate",
    "Unhealthy for Sensitive Groups",
    "Unhealthy",
    "Very Unhealthy",
    "Hazardous",
]
AQI_BINS = [-1, 50, 100, 150, 200, 300, 10_000]
# Conventional AQI hues, slightly muted so they sit well on a light surface.
AQI_COLORS = {
    "Good": "#2e9e5b",
    "Moderate": "#e0b422",
    "Unhealthy for Sensitive Groups": "#ee8a2c",
    "Unhealthy": "#d64545",
    "Very Unhealthy": "#8a3f9e",
    "Hazardous": "#7e0023",
}


def _aqi_array(conc, table, decimals: int) -> np.ndarray:
    c = np.asarray(conc, dtype=float)
    scale = 10 ** decimals
    # EPA truncates (not rounds) concentrations; epsilon guards float error.
    c = np.floor(c * scale + 1e-9) / scale
    out = np.full(c.shape, np.nan)
    prev_hi = -np.inf
    for lo, hi, ilo, ihi in table:
        mask = (c >= 0) & (c > prev_hi) & (c <= hi)
        out[mask] = (ihi - ilo) / (hi - lo) * (c[mask] - lo) + ilo
        prev_hi = hi
    out[c > table[-1][1]] = 500.0  # cap beyond the table
    return np.round(out)


def aqi_pm25(conc):
    """AQI sub-index for PM2.5 (ug/m3). Accepts scalar, list or Series."""
    res = _aqi_array(conc, PM25_BREAKPOINTS, 1)
    return pd.Series(res, index=conc.index) if isinstance(conc, pd.Series) else (
        res if res.ndim else float(res))


def aqi_pm10(conc):
    """AQI sub-index for PM10 (ug/m3). Accepts scalar, list or Series."""
    res = _aqi_array(conc, PM10_BREAKPOINTS, 0)
    return pd.Series(res, index=conc.index) if isinstance(conc, pd.Series) else (
        res if res.ndim else float(res))


def aqi_category(aqi) -> pd.Series:
    """Map AQI numbers to category names."""
    s = pd.Series(aqi)
    return pd.cut(s, bins=AQI_BINS, labels=AQI_CATEGORIES).astype("object").where(s.notna())


def add_aqi_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add aqi_pm25, aqi_pm10, aqi, aqi_category, dominant columns."""
    out = df.copy()
    out["aqi_pm25"] = aqi_pm25(out["pm25"]) if "pm25" in out else np.nan
    out["aqi_pm10"] = aqi_pm10(out["pm10"]) if "pm10" in out else np.nan
    out["aqi"] = out[["aqi_pm25", "aqi_pm10"]].max(axis=1, skipna=True)
    out["aqi_category"] = aqi_category(out["aqi"]).values
    dom = np.where(out["aqi_pm25"] >= out["aqi_pm10"].fillna(-1), "PM2.5", "PM10")
    out["dominant"] = np.where(out["aqi"].isna(), None, dom)
    return out
