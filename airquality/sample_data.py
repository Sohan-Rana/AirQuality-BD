"""Synthetic demo data generator.

IMPORTANT: everything produced here is SIMULATED. It only imitates the broad
shape of South Asian PM2.5 (winter peak, monsoon trough) so the pipeline,
charts and dashboard can be demonstrated without an API key. The city baselines
are illustrative guesses, NOT measurements, and must never be presented as
real Bangladesh air quality. Every row carries is_synthetic=True.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Illustrative annual-mean PM2.5 guess (ug/m3) and seasonal amplitude.
CITY_PROFILES = {
    "Dhaka": (80.0, 0.55),
    "Gazipur": (82.0, 0.55),
    "Rajshahi": (62.0, 0.50),
    "Khulna": (58.0, 0.50),
    "Chattogram": (50.0, 0.45),
    "Sylhet": (38.0, 0.40),
}


def generate_demo(start: str = "2023-01-01", end: str = "2025-12-31",
                  seed: int = 42, missing_rate: float = 0.02) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="D")
    doy = dates.dayofyear.to_numpy()
    rows = []
    for city, (base, amp) in CITY_PROFILES.items():
        seasonal = 1 + amp * np.cos(2 * np.pi * (doy - 15) / 365.25)  # peak mid-Jan
        # AR(1) noise in log space gives realistic day-to-day persistence.
        noise = np.zeros(len(dates))
        for t in range(1, len(dates)):
            noise[t] = 0.75 * noise[t - 1] + rng.normal(0, 0.18)
        pm25 = base * seasonal * np.exp(noise - noise.var() / 2)
        pm10 = pm25 * rng.uniform(1.5, 2.1, len(dates)) + rng.normal(0, 5, len(dates))
        pm10 = np.maximum(pm10, pm25 * 1.05)
        frame = pd.DataFrame({
            "date": dates, "city": city,
            "pm25": pm25.round(1), "pm10": pm10.round(1),
            "source": "SYNTHETIC_DEMO", "is_synthetic": True,
        })
        drop = rng.random(len(frame)) < missing_rate
        frame.loc[drop, ["pm25", "pm10"]] = np.nan
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)
