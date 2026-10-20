import pytest

from airquality.clean import clean
from airquality.collect import parse_daily
from airquality.forecast import evaluate, forecast_future, prepare_series
from airquality.sample_data import generate_demo


@pytest.fixture(scope="module")
def series():
    df, _ = clean(generate_demo(end="2024-06-30"))
    return prepare_series(df, "Dhaka")


def test_evaluate_returns_metrics(series):
    ev = evaluate(series, test_days=45)
    assert set(ev["metrics"]) == {"gradient_boosting", "persistence", "seasonal_naive_7d"}
    assert ev["metrics"]["gradient_boosting"]["MAE"] > 0
    assert len(ev["test_predictions"]) == 45


def test_forecast_shape_and_non_negative(series):
    fc = forecast_future(series, horizon=10)
    assert len(fc) == 10
    assert (fc["forecast"] >= 0).all()
    assert (fc["low"] <= fc["high"]).all()
    assert fc.index[0] == series.index[-1] + (fc.index[1] - fc.index[0])


def test_too_short_series_rejected():
    df, _ = clean(generate_demo(end="2023-02-15"))
    with pytest.raises(ValueError):
        prepare_series(df, "Dhaka")


def test_parse_openaq_payload():
    payload = [
        {"value": 55.2, "period": {"datetimeFrom": {"local": "2024-01-05T00:00:00+06:00"}}},
        {"value": None, "period": {"datetimeFrom": {"local": "2024-01-06T00:00:00+06:00"}}},
    ]
    out = parse_daily(payload, "Dhaka", "pm25")
    assert len(out) == 1
    assert out["date"].iloc[0] == "2024-01-05"
