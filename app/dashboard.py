"""AirQuality BD - interactive dashboard.

Run:  streamlit run app/dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from airquality import analysis, collect, forecast  # noqa: E402
from airquality.aqi import AQI_CATEGORIES, AQI_COLORS  # noqa: E402
from airquality.clean import clean  # noqa: E402
from airquality.config import (BD_PM25_24H, DATA_RAW, SYNTHETIC_LABEL,  # noqa: E402
                               WHO_PM25_24H)
from airquality.sample_data import generate_demo  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUES = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]

st.set_page_config(page_title="AirQuality BD", page_icon="🌍", layout="wide")


@st.cache_data(show_spinner=False)
def load_demo():
    return clean(generate_demo())


@st.cache_data(show_spinner=False)
def load_file(path_or_bytes):
    df = collect.load_csv(path_or_bytes)
    return clean(df)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🌍 AirQuality BD")
source = st.sidebar.radio("Data source", ["Demo (synthetic)", "Upload CSV", "File in data/raw"])

data = None
if source == "Demo (synthetic)":
    data = load_demo()
elif source == "Upload CSV":
    up = st.sidebar.file_uploader("CSV with columns: date, city, pm25, pm10", type="csv")
    if up is not None:
        try:
            data = load_file(up)
        except ValueError as exc:
            st.sidebar.error(str(exc))
else:
    files = sorted(p.name for p in DATA_RAW.glob("*.csv")) if DATA_RAW.exists() else []
    if not files:
        st.sidebar.info("No CSV files in data/raw yet. Run the OpenAQ collector first.")
    else:
        choice = st.sidebar.selectbox("File", files)
        data = load_file(str(DATA_RAW / choice))

st.title("AirQuality BD")
st.caption("Bangladesh air quality analytics: PM2.5, PM10 and AQI trends, city comparison, "
           "seasonality and short-term forecasting.")

if data is None:
    st.info("Choose a data source in the sidebar to begin.")
    st.stop()

df_all, report = data
if report["any_synthetic"]:
    st.warning(f"**{SYNTHETIC_LABEL}** - these numbers are simulated to demonstrate the "
               "dashboard. They are NOT real measurements of Bangladesh air quality.")

cities_all = sorted(df_all["city"].unique())
cities = st.sidebar.multiselect("Cities", cities_all, default=cities_all[:4])
dmin, dmax = df_all["date"].min().date(), df_all["date"].max().date()
dr = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
if isinstance(dr, tuple) and len(dr) == 2:
    start, end = dr
else:
    start, end = dmin, dmax

df = df_all[df_all["city"].isin(cities)
            & (df_all["date"] >= pd.Timestamp(start)) & (df_all["date"] <= pd.Timestamp(end))]
if df.empty:
    st.warning("No data for this selection.")
    st.stop()

color_map = {c: SERIES[i % len(SERIES)] for i, c in enumerate(cities_all)}  # color follows the city

# ---------------------------------------------------------------- KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Mean PM2.5", f"{df['pm25'].mean():.1f} µg/m³")
k2.metric("Mean AQI (US EPA)", f"{df['aqi'].mean():.0f}")
k3.metric("Days above WHO guideline", f"{100 * (df['pm25'].dropna() > WHO_PM25_24H).mean():.0f}%")
k4.metric("Days above BD standard", f"{100 * (df['pm25'].dropna() > BD_PM25_24H).mean():.0f}%")

tabs = st.tabs(["Trends", "Cities", "Seasonality", "AQI categories", "Forecast", "Data"])

# ---------------------------------------------------------------- trends
with tabs[0]:
    window = st.slider("Rolling average (days)", 1, 90, 30)
    pollutant = st.radio("Pollutant", ["pm25", "pm10"], horizontal=True,
                         format_func=lambda x: "PM2.5" if x == "pm25" else "PM10")
    rolled = (df.set_index("date").groupby("city")[pollutant]
                .apply(lambda s: s.asfreq("D").rolling(window, min_periods=1).mean())
                .reset_index())
    fig = px.line(rolled, x="date", y=pollutant, color="city", color_discrete_map=color_map,
                  labels={pollutant: "µg/m³", "date": ""})
    fig.update_traces(line_width=2)
    if pollutant == "pm25":
        fig.add_hline(y=WHO_PM25_24H, line_dash="dash", line_color="#898781",
                      annotation_text="WHO 24h guideline", annotation_position="bottom right")
        fig.add_hline(y=BD_PM25_24H, line_dash="dash", line_color="#898781",
                      annotation_text="BD 24h standard", annotation_position="top right")
    fig.update_layout(hovermode="x unified", legend_title_text="", height=480)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- cities
with tabs[1]:
    summ = analysis.city_summary(df)
    fig = px.bar(summ.sort_values("pm25_mean"), x="pm25_mean", y="city", orientation="h",
                 text="pm25_mean", labels={"pm25_mean": "Mean PM2.5 (µg/m³)", "city": ""})
    fig.update_traces(marker_color=SERIES[0], texttemplate="%{text:.0f}", textposition="outside")
    fig.add_vline(x=WHO_PM25_24H, line_dash="dash", line_color="#898781",
                  annotation_text="WHO guideline")
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(summ, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- seasonality
with tabs[2]:
    pv = analysis.monthly_pivot(df)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = px.imshow(pv.values, x=months, y=list(pv.index), text_auto=".0f", aspect="auto",
                    color_continuous_scale=BLUES, labels={"color": "PM2.5"})
    fig.update_layout(height=120 + 60 * len(pv), coloraxis_colorbar_title="µg/m³")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(analysis.seasonal_summary(df), hide_index=True)

# ---------------------------------------------------------------- AQI categories
with tabs[3]:
    share = analysis.aqi_category_share(df).reset_index().melt(
        id_vars="city", var_name="Category", value_name="Share of days (%)")
    fig = px.bar(share, x="Share of days (%)", y="city", color="Category", orientation="h",
                 color_discrete_map=AQI_COLORS, category_orders={"Category": AQI_CATEGORIES})
    fig.update_layout(height=420, legend_title_text="", barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("AQI here is the US EPA scale, not the Bangladesh DoE index.")

# ---------------------------------------------------------------- forecast
with tabs[4]:
    c1, c2 = st.columns(2)
    fc_city = c1.selectbox("City", cities)
    horizon = c2.slider("Forecast horizon (days)", 3, 30, 14)
    try:
        series = forecast.prepare_series(df_all, fc_city)
        with st.spinner("Training model..."):
            ev = forecast.evaluate(series)
            future = forecast.forecast_future(series, horizon)
    except ValueError as exc:
        st.info(str(exc))
    else:
        hist = series.iloc[-120:]
        fig = go.Figure()
        fig.add_scatter(x=hist.index, y=hist.values, name="Observed",
                        line=dict(color=SERIES[0], width=2))
        fig.add_scatter(x=ev["test_predictions"].index, y=ev["test_predictions"]["gradient_boosting"],
                        name="Model (1-day-ahead, hold-out)", line=dict(color=SERIES[1], width=2))
        fig.add_scatter(x=future.index.tolist() + future.index[::-1].tolist(),
                        y=future["high"].tolist() + future["low"][::-1].tolist(), fill="toself",
                        fillcolor="rgba(27,175,122,0.18)", line=dict(width=0),
                        hoverinfo="skip", name="Rough range", showlegend=True)
        fig.add_scatter(x=future.index, y=future["forecast"], name="Forecast",
                        line=dict(color=SERIES[2], width=2, dash="dash"))
        fig.update_layout(height=450, hovermode="x unified", legend_title_text="",
                          yaxis_title="PM2.5 (µg/m³)")
        st.plotly_chart(fig, use_container_width=True)
        m = pd.DataFrame(ev["metrics"]).T.round(1)
        st.write(f"Error on the last {ev['test_days']} days (lower is better). "
                 f"Best: **{ev['best_model']}**.")
        st.dataframe(m)
        st.caption("Evaluation is one day ahead. The shaded range is a rough residual-based band, "
                   "not a statistical prediction interval.")

# ---------------------------------------------------------------- data
with tabs[5]:
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "airquality_bd_filtered.csv", "text/csv")
    st.json(report, expanded=False)
