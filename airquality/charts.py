"""Static charts (matplotlib). Each function saves a PNG and returns its path.

Design rules: one axis per chart, thin marks, recessive grid, text in ink
colors (never series colors), a legend whenever there are 2+ series, and a
visible watermark whenever the data is synthetic.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from .aqi import AQI_CATEGORIES, AQI_COLORS
from .config import (BD_PM25_24H, SYNTHETIC_LABEL, WHO_PM25_24H)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
SEQ_CMAP = LinearSegmentedColormap.from_list("bd_blue", BLUE_RAMP)

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": AXIS,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 1,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "legend.frameon": False,
})

PM25_LABEL = "PM2.5 (µg/m³)"


def _finish(fig, ax_title, subtitle, path, synthetic):
    fig.suptitle(ax_title, x=0.01, y=0.99, ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.01, 0.912, subtitle, ha="left", va="top", fontsize=9.5, color=INK2)
    if synthetic:
        fig.text(0.5, 0.5, SYNTHETIC_LABEL, fontsize=42, color=INK, alpha=0.07,
                 ha="center", va="center", rotation=25, fontweight="bold")
        fig.text(0.99, 0.01, "Simulated data - not real measurements", ha="right",
                 fontsize=8, color=INK2)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _is_synth(df) -> bool:
    return bool("is_synthetic" in df.columns and df["is_synthetic"].any())


def _ref_lines(ax, x_start, x_end, x_text):
    """Reference lines stop at the data edge; labels sit in the right margin."""
    for val, label in ((WHO_PM25_24H, f"WHO 24h ({WHO_PM25_24H:g})"),
                       (BD_PM25_24H, f"BD std 24h ({BD_PM25_24H:g})")):
        ax.hlines(val, x_start, x_end, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(x_text, val, label, fontsize=8, color=INK2, va="center", ha="left")


def _date_axis(ax, locator=None):
    import matplotlib.dates as mdates
    loc = locator or mdates.AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))


def timeseries(df: pd.DataFrame, path, cities: list[str] | None = None, window: int = 30):
    """Rolling-mean PM2.5 for up to 4 cities."""
    order = df.groupby("city")["pm25"].mean().sort_values(ascending=False).index
    cities = (cities or list(order))[:4]
    fig, ax = plt.subplots(figsize=(10, 5))
    last_x = df["date"].max()
    for i, city in enumerate(cities):
        s = (df[df["city"] == city].set_index("date")["pm25"].asfreq("D")
             .rolling(window, min_periods=max(5, window // 3)).mean())
        ax.plot(s.index, s.values, color=SERIES[i], linewidth=2, label=city)
        end = s.dropna()
        if len(end):
            ax.text(end.index[-1], end.iloc[-1], f"  {city}", fontsize=8.5, color=INK2, va="center")
    import matplotlib.dates as mdates
    _ref_lines(ax, df["date"].min(), last_x, last_x + pd.Timedelta(days=12))
    ax.set_ylabel(PM25_LABEL)
    ax.set_xlim(right=last_x + pd.Timedelta(days=190))
    _date_axis(ax, mdates.MonthLocator(bymonth=(1, 7)))
    ax.legend(loc="upper left", ncol=len(cities), fontsize=9)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, "PM2.5 trend by city", f"{window}-day rolling mean of daily PM2.5",
                   path, _is_synth(df))


def city_ranking(summary: pd.DataFrame, path, synthetic: bool = False):
    s = summary.sort_values("pm25_mean")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.barh(s["city"], s["pm25_mean"], color=SERIES[0], height=0.6)
    for b, v in zip(bars, s["pm25_mean"]):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.0f}", va="center",
                fontsize=9, color=INK)
    ax.axvline(WHO_PM25_24H, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(WHO_PM25_24H + 0.5, -0.65, "WHO 24h guideline", fontsize=8, color=INK2)
    ax.set_xlabel("Mean PM2.5 (µg/m³)")
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, "Cities ranked by mean PM2.5", "Average over the whole period",
                   path, synthetic)


def monthly_heatmap(pivot: pd.DataFrame, path, synthetic: bool = False):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    data = pivot.to_numpy(float)
    vmin, vmax = np.nanmin(data), np.nanmax(data)
    ax.pcolormesh(data, cmap=SEQ_CMAP, vmin=vmin, vmax=vmax, edgecolors=SURFACE, linewidth=2)
    ax.set_xticks(np.arange(12) + 0.5, months)
    ax.set_yticks(np.arange(len(pivot)) + 0.5, pivot.index)
    ax.invert_yaxis()
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    for (r, c), v in np.ndenumerate(data):
        if np.isnan(v):
            continue
        dark = (v - vmin) / (vmax - vmin + 1e-9) > 0.5
        ax.text(c + 0.5, r + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=8.5,
                color="#ffffff" if dark else INK)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, "Seasonality: monthly mean PM2.5 (µg/m³)",
                   "Darker = more polluted. Rows sorted by overall mean.", path, synthetic)


def aqi_distribution(share: pd.DataFrame, path, synthetic: bool = False):
    fig, ax = plt.subplots(figsize=(10, 4.8))
    left = np.zeros(len(share))
    y = np.arange(len(share))
    for cat in AQI_CATEGORIES:
        vals = share[cat].to_numpy()
        ax.barh(y, vals, left=left, color=AQI_COLORS[cat], height=0.62,
                edgecolor=SURFACE, linewidth=1.5, label=cat)
        for yi, (l, v) in enumerate(zip(left, vals)):
            if v >= 8:
                light_fill = cat in ("Moderate", "Unhealthy for Sensitive Groups")
                ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color=INK if light_fill else "#ffffff")
        left += vals
    ax.set_yticks(y, share.index)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of days (%)")
    ax.grid(visible=False)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8.5)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, "Share of days by AQI category (US EPA scale)",
                   "Each bar sums to 100% of valid days", path, synthetic)


def seasonal_boxplot(df: pd.DataFrame, path):
    from .analysis import add_time_columns
    from .config import SEASON_ORDER
    d = add_time_columns(df).dropna(subset=["pm25"])
    data = [d.loc[d["season"] == s, "pm25"] for s in SEASON_ORDER]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bp = ax.boxplot(data, tick_labels=SEASON_ORDER, patch_artist=True, widths=0.55,
                    showfliers=False, medianprops={"color": INK, "linewidth": 1.5},
                    whiskerprops={"color": AXIS}, capprops={"color": AXIS},
                    boxprops={"edgecolor": SERIES[0]})
    for patch in bp["boxes"]:
        patch.set_facecolor("#cde2fb")
    ax.axhline(WHO_PM25_24H, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.55, WHO_PM25_24H, "WHO 24h guideline", fontsize=8, color=INK2, va="bottom")
    ax.set_ylabel(PM25_LABEL)
    ax.grid(axis="x", visible=False)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, "PM2.5 by season (all cities)", "Box = middle 50% of days, line = median",
                   path, _is_synth(df))


def forecast_chart(history: pd.Series, test_pred: pd.DataFrame, future: pd.DataFrame,
                   city: str, path, synthetic: bool = False, history_days: int = 120):
    h = history.iloc[-history_days:]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(h.index, h.values, color=SERIES[0], linewidth=2, label="Observed")
    if test_pred is not None and len(test_pred):
        ax.plot(test_pred.index, test_pred["gradient_boosting"], color=SERIES[1], linewidth=2,
                label="Model, 1-day-ahead on hold-out")
    ax.fill_between(future.index, future["low"], future["high"], color=SERIES[2], alpha=0.18,
                    linewidth=0)
    ax.plot(future.index, future["forecast"], color=SERIES[2], linewidth=2, linestyle="--",
            label="Forecast (rough band)")
    ax.set_ylabel(PM25_LABEL)
    _date_axis(ax)
    ax.legend(loc="upper left", ncol=3, fontsize=9)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, f"{city}: PM2.5 forecast",
                   "Recursive forecast; band is a rough residual-based range, not a true interval",
                   path, synthetic)


def model_comparison(metrics: dict, city: str, path, synthetic: bool = False):
    names = {"persistence": "Persistence", "seasonal_naive_7d": "Same day last week",
             "gradient_boosting": "Gradient boosting"}
    keys = list(names)
    vals = [metrics[k]["MAE"] for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar([names[k] for k in keys], vals, color=SERIES[0], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_ylabel("Mean absolute error (µg/m³)")
    ax.grid(axis="x", visible=False)
    fig.subplots_adjust(top=0.84)
    return _finish(fig, f"{city}: forecast error on hold-out", "Lower is better",
                   path, synthetic)
