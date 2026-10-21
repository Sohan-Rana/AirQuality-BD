"""Descriptive analysis functions. All take the cleaned table from clean.clean()."""
from __future__ import annotations

import pandas as pd

from .aqi import AQI_CATEGORIES
from .config import (BD_PM25_24H, SEASON_ORDER, SEASONS, WHO_PM25_24H)


def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["year"] = out["date"].dt.year
    out["month"] = out["date"].dt.month
    out["season"] = pd.Categorical(out["month"].map(SEASONS), categories=SEASON_ORDER, ordered=True)
    return out


def city_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per city, sorted by mean PM2.5 (worst first)."""
    g = df.groupby("city")
    out = pd.DataFrame({
        "days": g["date"].nunique(),
        "pm25_mean": g["pm25"].mean(),
        "pm25_median": g["pm25"].median(),
        "pm25_max": g["pm25"].max(),
        "pm10_mean": g["pm10"].mean(),
        "aqi_mean": g["aqi"].mean(),
        "pct_days_above_who": g["pm25"].apply(lambda s: 100 * (s.dropna() > WHO_PM25_24H).mean()),
        "pct_days_above_bd_std": g["pm25"].apply(lambda s: 100 * (s.dropna() > BD_PM25_24H).mean()),
    })
    return out.sort_values("pm25_mean", ascending=False).round(1).reset_index()


def monthly_pivot(df: pd.DataFrame, value: str = "pm25") -> pd.DataFrame:
    """City x month-of-year matrix of mean values."""
    d = add_time_columns(df)
    pv = d.pivot_table(index="city", columns="month", values=value, aggfunc="mean")
    return pv.reindex(columns=range(1, 13)).loc[
        df.groupby("city")[value].mean().sort_values(ascending=False).index]


def seasonal_summary(df: pd.DataFrame) -> pd.DataFrame:
    d = add_time_columns(df)
    return (d.groupby("season", observed=True)["pm25"]
              .agg(["mean", "median", "max"]).round(1).reset_index())


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    d = add_time_columns(df)
    return d.pivot_table(index="year", columns="city", values="pm25", aggfunc="mean").round(1)


def aqi_category_share(df: pd.DataFrame) -> pd.DataFrame:
    """Percent of days in each AQI category per city (rows sum to 100)."""
    d = df.dropna(subset=["aqi_category"])
    ct = pd.crosstab(d["city"], d["aqi_category"], normalize="index") * 100
    ct = ct.reindex(columns=AQI_CATEGORIES, fill_value=0.0)
    order = df.groupby("city")["pm25"].mean().sort_values(ascending=False).index
    return ct.reindex(order).round(1)


def worst_days(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    cols = ["date", "city", "pm25", "pm10", "aqi", "aqi_category"]
    return df.dropna(subset=["pm25"]).nlargest(n, "pm25")[cols].reset_index(drop=True)
