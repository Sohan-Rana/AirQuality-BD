import numpy as np
import pandas as pd

from airquality.aqi import add_aqi_columns, aqi_category, aqi_pm10, aqi_pm25


def test_pm25_breakpoints():
    assert aqi_pm25(0.0) == 0
    assert aqi_pm25(9.0) == 50
    assert aqi_pm25(35.4) == 100
    assert aqi_pm25(55.4) == 150
    assert aqi_pm25(12.0) == 56


def test_pm25_cap_and_invalid():
    assert aqi_pm25(900.0) == 500
    assert np.isnan(aqi_pm25(-1.0))
    assert np.isnan(aqi_pm25(float("nan")))


def test_pm10():
    assert aqi_pm10(54) == 50
    assert aqi_pm10(100) == 73
    assert aqi_pm10(700) == 500


def test_series_and_category():
    s = pd.Series([5.0, 20.0, 60.0, np.nan])
    a = aqi_pm25(s)
    assert list(a.iloc[:3]) == sorted(a.iloc[:3])
    cats = aqi_category(a)
    assert cats.iloc[0] == "Good"
    assert cats.iloc[3] is None or pd.isna(cats.iloc[3])


def test_add_columns_takes_worst_pollutant():
    df = pd.DataFrame({"pm25": [10.0], "pm10": [300.0]})
    out = add_aqi_columns(df)
    assert out["aqi"].iloc[0] == max(out["aqi_pm25"].iloc[0], out["aqi_pm10"].iloc[0])
    assert out["dominant"].iloc[0] == "PM10"
