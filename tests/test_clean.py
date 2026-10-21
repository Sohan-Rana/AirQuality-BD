import pandas as pd
import pytest

from airquality.clean import clean
from airquality.sample_data import generate_demo


def test_clean_handles_bad_rows():
    raw = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-01", "2024-01-02", "not-a-date", "2024-01-03"],
        "city": ["Dhaka", "Dhaka", "Dhaka", "Dhaka", "Dhaka"],
        "pm25": [50, 70, -5, 40, None],
        "pm10": [90, 100, 80, 70, None],
    })
    out, rep = clean(raw)
    assert rep["dropped_bad_date_or_city"] == 1
    assert rep["duplicates_merged"] == 1
    assert rep["invalid_values_set_nan"] == 1
    assert rep["dropped_no_pollutant"] == 1
    assert out.loc[out["date"] == "2024-01-01", "pm25"].iloc[0] == 60
    assert not out["is_synthetic"].any()
    assert "aqi" in out.columns


def test_clean_requires_columns():
    with pytest.raises(ValueError):
        clean(pd.DataFrame({"city": ["x"], "pm25": [1]}))


def test_demo_is_flagged_synthetic():
    out, rep = clean(generate_demo(end="2023-03-31"))
    assert rep["any_synthetic"] is True
    assert out["is_synthetic"].all()
    assert (out["pm25"].dropna() > 0).all()
