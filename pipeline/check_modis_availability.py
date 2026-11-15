"""Aqua / Terra 2026 availability check (T-008).

Standard library only. Read-only: it reads the files pulled by pull_api_2026.py
(data/raw/api_2026/MODIS_SP, MODIS_NRT) and the saved FIRMS missing_data response,
and prints a Markdown summary. It writes nothing.

    python -I pipeline/check_modis_availability.py
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
START = dt.date(2026, 1, 1)
SATELLITES = ("Aqua", "Terra")
MISSING_NAME = {"Aqua": "Aqua (MODIS)", "Terra": "Terra (MODIS)"}


def main() -> None:
    days: dict[str, set[str]] = collections.defaultdict(set)
    per_month: collections.Counter = collections.Counter()
    for f in sorted(glob.glob(str(RAW / "api_2026" / "MODIS_*" / "*.csv"))):
        with open(f, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sat, day = row["satellite"], row["acq_date"]
                days[sat].add(day)
                per_month[(sat, day[:7])] += 1
    if not days:
        raise SystemExit("no MODIS files in data/raw/api_2026 (run pipeline/pull_api_2026.py first)")

    last_pulled = max(max(d) for d in days.values())
    span = [(START + dt.timedelta(i)).isoformat() for i in range((dt.date.fromisoformat(last_pulled) - START).days + 1)]

    miss_file = max((RAW / "availability").glob("missing_data_*.json"))
    cells = re.findall(r"<td>([^<]*)</td>", json.loads(miss_file.read_text(encoding="utf-8"))["html"])
    listed = collections.defaultdict(set)  # satellite name -> dates FIRMS lists as missing
    for date, name in zip(cells[0::2], cells[1::2]):
        if name:
            listed[name].add(date)

    print(f"Window checked: {START} to {last_pulled} ({len(span)} days). Missing-data snapshot: {miss_file.name}\n")
    print("| Satellite | First detection | Last detection | Days with detections | Days without | Days without that FIRMS lists as missing |")
    print("|---|---|---|---|---|---|")
    for sat in SATELLITES:
        have = days[sat]
        without = [d for d in span if d not in have]
        listed_2026 = sorted(d for d in listed[MISSING_NAME[sat]] if d >= START.isoformat())
        print(f"| {sat} | {min(have)} | {max(have)} | {len(have)} | {len(without)} ({', '.join(without) or 'none'}) | {', '.join(listed_2026) or 'none'} |")

    print("\n| Month | Aqua rows | Terra rows |")
    print("|---|---|---|")
    for month in sorted({m for _, m in per_month}):
        print(f"| {month} | {per_month[('Aqua', month)]:,} | {per_month[('Terra', month)]:,} |")


if __name__ == "__main__":
    main()
