"""Report which Intervals.icu wellness fields are populated for recent days.

Reads API_KEY and ATHLETE_ID from the environment (or a .env file in the repo),
fetches raw wellness rows with a single GET, and prints, for each field, how
many of the days have a value. The API key is never printed.

Usage:
    uv run python scripts/wellness_field_report.py [DAYS]   # default 14
"""

import asyncio
import datetime as dt
import sys

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config

# Fields worth calling out for a Garmin-sourced account, in display order.
HEADLINE = [
    ("hrv", "HRV (overnight rMSSD)"),
    ("restingHR", "Resting HR"),
    ("sleepSecs", "Sleep duration"),
    ("sleepScore", "Sleep score"),
    ("sleepQuality", "Sleep quality"),
    ("spO2", "SpO2"),
    ("weight", "Weight"),
    ("bodyFat", "Body fat"),
    ("steps", "Steps"),
    ("vo2max", "VO2max"),
    ("avgSleepingHR", "Avg sleeping HR"),
    ("respiration", "Respiration"),
    ("readiness", "Readiness"),
    ("stress", "Stress (Intervals.icu subjective 1-4)"),
    ("BodyBatteryMax", "Body Battery max (custom field)"),
    ("BodyBatteryMin", "Body Battery min (custom field)"),
]


async def main(days: int) -> int:
    config = get_config()
    if not config.api_key or not config.athlete_id:
        print("API_KEY and ATHLETE_ID must be set (environment or .env).", file=sys.stderr)
        return 2

    newest = dt.date.today()
    oldest = newest - dt.timedelta(days=days - 1)
    rows = await make_intervals_request(
        url=f"/athlete/{config.athlete_id}/wellness",
        params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
    )
    if isinstance(rows, dict):
        print(f"Error: {rows.get('message', rows)}", file=sys.stderr)
        return 1

    print(f"{len(rows)} wellness rows from {oldest} to {newest}\n")
    keys = sorted({k for row in rows for k in row})
    counts = {k: sum(1 for row in rows if row.get(k) not in (None, "", [], {})) for k in keys}

    print(f"{'field':40} days with a value")
    for key, label in HEADLINE:
        shown = f"{label} [{key}]"
        if key not in counts:
            print(f"{shown:40} absent (key not returned)")
        else:
            print(f"{shown:40} {counts[key]}/{len(rows)}")

    headline_keys = {k for k, _ in HEADLINE}
    others = [k for k in keys if k not in headline_keys]
    print(
        "\nOther populated keys:",
        ", ".join(f"{k} {counts[k]}/{len(rows)}" for k in others if counts[k]) or "none",
    )
    print("Other keys always null:", ", ".join(k for k in others if not counts[k]) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)))
