"""Short-term PM2.5 forecasting for a single city.

Models compared on a time-ordered hold-out (never shuffled):
  * persistence      - tomorrow = today
  * seasonal naive   - tomorrow = same weekday last week
  * gradient boosting on lag / rolling / calendar features

Evaluation is ONE-STEP-AHEAD (each test day is predicted from the real previous
days). Multi-day forecasts are made recursively and are naturally less accurate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

MIN_HISTORY = 14
MIN_DAYS = 120


def _features(hist: np.ndarray, date: pd.Timestamp) -> list[float]:
    doy = date.dayofyear
    return [
        hist[-1], hist[-2], hist[-3], hist[-7], hist[-14],
        hist[-7:].mean(), hist[-14:].mean(),
        np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25),
        date.dayofweek,
    ]


def prepare_series(df: pd.DataFrame, city: str, column: str = "pm25") -> pd.Series:
    """Daily, gap-filled series for one city (short gaps interpolated)."""
    s = df.loc[df["city"] == city].set_index("date")[column].sort_index()
    s = s[~s.index.duplicated()].asfreq("D")
    s = s.interpolate(limit=7, limit_direction="both").dropna()
    if len(s) < MIN_DAYS:
        raise ValueError(f"Need at least {MIN_DAYS} days of data for {city}; have {len(s)}.")
    return s


def _build_xy(values: np.ndarray, index: pd.DatetimeIndex):
    X, y, dates = [], [], []
    for i in range(MIN_HISTORY, len(values)):
        X.append(_features(values[:i], index[i]))
        y.append(values[i])
        dates.append(index[i])
    return np.array(X), np.array(y), pd.DatetimeIndex(dates)


def _model() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=42)


def _scores(y_true, y_pred) -> dict:
    err = y_true - y_pred
    return {"MAE": float(np.mean(np.abs(err))), "RMSE": float(np.sqrt(np.mean(err ** 2)))}


def evaluate(series: pd.Series, test_days: int = 60) -> dict:
    """Hold out the last `test_days`; returns metrics and test predictions."""
    values = series.to_numpy(float)
    X, y, dates = _build_xy(values, series.index)
    if len(y) <= test_days + 30:
        raise ValueError("Series too short for this hold-out size.")
    split = len(y) - test_days
    model = _model().fit(X[:split], y[:split])
    pred = np.clip(model.predict(X[split:]), 0, None)
    y_test = y[split:]
    persistence = X[split:, 0]   # lag-1
    seasonal = X[split:, 3]      # lag-7
    metrics = {
        "gradient_boosting": _scores(y_test, pred),
        "persistence": _scores(y_test, persistence),
        "seasonal_naive_7d": _scores(y_test, seasonal),
    }
    best = min(metrics, key=lambda k: metrics[k]["MAE"])
    preds = pd.DataFrame({"date": dates[split:], "actual": y_test,
                          "gradient_boosting": pred}).set_index("date")
    return {"metrics": metrics, "best_model": best, "test_predictions": preds,
            "test_days": test_days}


def forecast_future(series: pd.Series, horizon: int = 14) -> pd.DataFrame:
    """Recursive multi-day forecast from the full history."""
    values = series.to_numpy(float)
    X, y, _ = _build_xy(values, series.index)
    model = _model().fit(X, y)
    # Rough uncertainty band from in-sample residual spread (not a true interval).
    resid_sd = float(np.std(y - model.predict(X)))
    hist = list(values)
    out_dates, out_vals = [], []
    for step in range(1, horizon + 1):
        date = series.index[-1] + pd.Timedelta(days=step)
        val = float(max(model.predict([_features(np.array(hist), date)])[0], 0.0))
        hist.append(val)
        out_dates.append(date)
        out_vals.append(val)
    fc = pd.DataFrame({"date": out_dates, "forecast": out_vals}).set_index("date")
    spread = resid_sd * np.sqrt(np.arange(1, horizon + 1))
    fc["low"] = np.clip(fc["forecast"] - 1.28 * spread, 0, None)
    fc["high"] = fc["forecast"] + 1.28 * spread
    return fc
