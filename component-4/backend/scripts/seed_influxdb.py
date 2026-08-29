"""
scripts/seed_influxdb.py
---------------------------
One-off backfill: loads the cleaned historical CSV series (via
data_loader.load_metal_series) for every supported metal and writes each
point into InfluxDB, so the bucket isn't empty on day one.

Run once, after InfluxDB is actually up and the bucket in your .env
exists:

    python scripts/seed_influxdb.py

Also doubles as the template for a daily cron/scheduled job: in
production you'd replace the CSV read with a call to whatever live price
source you settle on (a paid metals API, a scraped exchange page, etc.)
and run just the last block (today's point) once a day, instead of the
full historical backfill.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_metal_series, SUPPORTED_METALS
from services.influx_client import write_price_point


def backfill_all(max_points_per_metal: int = 2000) -> None:
    for metal in SUPPORTED_METALS:
        series = load_metal_series(metal)
        # Influx writes are one HTTP call each in this simple wrapper --
        # cap how far back we backfill so a first run doesn't take forever.
        series = series.tail(max_points_per_metal)
        written = 0
        for date, price in series.items():
            ok = write_price_point(metal, float(price), when=date.to_pydatetime())
            written += int(ok)
        print(f"{metal}: wrote {written}/{len(series)} points")


if __name__ == "__main__":
    backfill_all()
