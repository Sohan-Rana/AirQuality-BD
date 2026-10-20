"""End-to-end pipeline: load -> clean -> analyse -> charts -> forecast -> report.

Examples (run from the project root):
    python scripts/run_pipeline.py --demo
    python scripts/run_pipeline.py --csv data/raw/my_data.csv
    python scripts/run_pipeline.py --openaq --from 2024-01-01 --to 2025-12-31
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from airquality import analysis, charts, collect, forecast  # noqa: E402
from airquality.clean import clean  # noqa: E402
from airquality.config import DATA_PROCESSED, DATA_RAW, FIG_DIR, OUT_DIR  # noqa: E402
from airquality.sample_data import generate_demo  # noqa: E402


def load(args):
    if args.demo:
        df = generate_demo()
        DATA_RAW.parent.joinpath("sample").mkdir(parents=True, exist_ok=True)
        df.to_csv(DATA_RAW.parent / "sample" / "demo_synthetic.csv", index=False)
        return df
    if args.csv:
        return collect.load_csv(args.csv)
    df = collect.collect_openaq(args.date_from, args.date_to)
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_RAW / "openaq_bd_daily.csv", index=False)
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--demo", action="store_true", help="use SYNTHETIC demo data")
    src.add_argument("--csv", help="path to your own CSV (date, city, pm25, pm10)")
    src.add_argument("--openaq", action="store_true", help="download real data (needs OPENAQ_API_KEY)")
    p.add_argument("--from", dest="date_from", default="2024-01-01")
    p.add_argument("--to", dest="date_to", default="2025-12-31")
    p.add_argument("--horizon", type=int, default=14, help="forecast days")
    args = p.parse_args()

    raw = load(args)
    df, report = clean(raw)
    synthetic = report["any_synthetic"]
    print("Cleaning report:", json.dumps(report, indent=2))

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PROCESSED / "clean_daily.csv", index=False)

    summary = analysis.city_summary(df)
    summary.to_csv(OUT_DIR / "city_summary.csv", index=False)

    charts.timeseries(df, FIG_DIR / "01_pm25_trend.png")
    charts.city_ranking(summary, FIG_DIR / "02_city_ranking.png", synthetic)
    charts.monthly_heatmap(analysis.monthly_pivot(df), FIG_DIR / "03_monthly_heatmap.png", synthetic)
    charts.aqi_distribution(analysis.aqi_category_share(df), FIG_DIR / "04_aqi_distribution.png", synthetic)
    charts.seasonal_boxplot(df, FIG_DIR / "05_seasonal_boxplot.png")

    # Forecast for the most polluted city that has enough data.
    fc_note = "Forecast skipped: not enough data."
    for city in summary["city"]:
        try:
            series = forecast.prepare_series(df, city)
        except ValueError:
            continue
        ev = forecast.evaluate(series)
        future = forecast.forecast_future(series, args.horizon)
        charts.forecast_chart(series, ev["test_predictions"], future, city,
                              FIG_DIR / "06_forecast.png", synthetic)
        charts.model_comparison(ev["metrics"], city, FIG_DIR / "07_model_comparison.png", synthetic)
        fc_note = (f"Forecast city: {city}. Best model on the {ev['test_days']}-day hold-out: "
                   f"{ev['best_model']}. MAE (ug/m3): "
                   + ", ".join(f"{k}={v['MAE']:.1f}" for k, v in ev["metrics"].items()))
        break
    print(fc_note)

    lines = ["# AirQuality BD - run report", ""]
    if synthetic:
        lines += ["> **SYNTHETIC DEMO DATA** - simulated numbers, not real measurements.", ""]
    lines += [f"- Rows in/out: {report['rows_in']} / {report['rows_out']}",
              f"- Cities: {report['cities']}, period: {report['date_min']} to {report['date_max']}",
              f"- {fc_note}", "", "## City summary", "", summary.to_markdown(index=False)
              if _has_tabulate() else summary.to_string(index=False)]
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Done. Figures in {FIG_DIR}, report in {OUT_DIR / 'report.md'}")


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
