# 🌍 AirQuality BD

**Bangladesh air quality analytics: data collection, cleaning, analysis, visualization, an interactive dashboard and short-term forecasting, all in Python.**

![CI](https://github.com/Sohan-Rana/AirQuality-BD/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> ⚠️ **Data honesty.** The charts below are built from **synthetic demo data** (clearly watermarked) so the project runs out of the box. They are **not** real measurements of Bangladesh air quality. To analyse real data, use the OpenAQ collector or your own CSV. Every row carries an `is_synthetic` flag and the dashboard shows a warning banner when synthetic data is loaded.

## What it does

| Stage | What you get |
|---|---|
| Collect | OpenAQ v3 collector for Bangladesh stations, or load your own CSV |
| Clean | Date/city validation, impossible values to missing, duplicate merge, PM2.5 > PM10 flag |
| AQI | US EPA AQI for PM2.5 and PM10, category and dominant pollutant |
| Analyse | City ranking, monthly/seasonal patterns, days above WHO guideline and Bangladesh standard |
| Visualize | 7 charts + interactive Streamlit dashboard |
| Forecast | Gradient boosting vs persistence vs same-day-last-week, time-ordered evaluation |

## Charts (synthetic demo data)

![Trend](outputs/figures/01_pm25_trend.png)
![Ranking](outputs/figures/02_city_ranking.png)
![Seasonality](outputs/figures/03_monthly_heatmap.png)
![AQI categories](outputs/figures/04_aqi_distribution.png)
![Seasons](outputs/figures/05_seasonal_boxplot.png)
![Forecast](outputs/figures/06_forecast.png)
![Model comparison](outputs/figures/07_model_comparison.png)

## Quick start

```bash
git clone https://github.com/Sohan-Rana/AirQuality-BD.git
cd AirQuality-BD
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

python scripts/run_pipeline.py --demo
streamlit run app/dashboard.py
pytest
```

## Using real data

**Option 1: OpenAQ (free API key)**

1. Create an account at https://explore.openaq.org and copy your API key.
2. Set `OPENAQ_API_KEY` (PowerShell: `$env:OPENAQ_API_KEY="your-key"`).
3. `python scripts/run_pipeline.py --openaq --from 2024-01-01 --to 2025-12-31`

Station coverage in Bangladesh is limited, so check how many days each city really has.

**Option 2: your own CSV** with columns `date,city,pm25,pm10`:

`python scripts/run_pipeline.py --csv data/raw/my_data.csv`

## Methods and limits

- AQI is the **US EPA** index, not the Bangladesh DoE index.
- Reference lines: WHO 2021 PM2.5 24-hour guideline (15 µg/m³) and the Bangladesh 24-hour standard (65 µg/m³). Check the latest DoE notification before quoting it in a paper.
- Forecasting is evaluated one day ahead on the last 60 days. The shaded band is a rough range, not a true prediction interval.
- Forecast accuracy on synthetic data says nothing about accuracy on real data.

## License

MIT © Sohan Rana
