"""Project-wide constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_SAMPLE = ROOT / "data" / "sample"
DATA_PROCESSED = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
FIG_DIR = OUT_DIR / "figures"

# 24-hour reference values in ug/m3.
# WHO 2021 global air quality guideline values.
WHO_PM25_24H = 15.0
WHO_PM10_24H = 45.0
# Bangladesh national ambient standard (24-hour). Verify against the latest
# Department of Environment notification before quoting it in a paper.
BD_PM25_24H = 65.0
BD_PM10_24H = 150.0

# Standard input schema for any dataset used by this project.
REQUIRED_COLUMNS = ["date", "city"]
POLLUTANT_COLUMNS = ["pm25", "pm10"]

SEASONS = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Pre-monsoon", 4: "Pre-monsoon", 5: "Pre-monsoon",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-monsoon", 11: "Post-monsoon",
}
SEASON_ORDER = ["Winter", "Pre-monsoon", "Monsoon", "Post-monsoon"]

SYNTHETIC_LABEL = "SYNTHETIC DEMO DATA"
