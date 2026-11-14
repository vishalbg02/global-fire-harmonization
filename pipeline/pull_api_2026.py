"""Pull 2026 FIRMS detections through the area API (T-002).

Standard library only. Reads FIRMS_MAP_KEY (and optionally FIRMS_MAP_KEY_2, _3, ...) from the environment or .env.
With several keys, each request uses whichever key has quota left. Keys are never printed, logged or used in a file name.

    python pipeline/pull_api_2026.py             # pull everything missing
    python pipeline/pull_api_2026.py --force     # re-pull existing segments
    python pipeline/pull_api_2026.py --check     # coverage check only, no network
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOST = "https://firms.modaps.eosdis.nasa.gov"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "api_2026"
AVAIL = ROOT / "data" / "raw" / "availability"
LOG = OUT / "pull_log.tsv"
START = dt.date(2026, 1, 1)
WINDOW = 5
RETRIES = 6
# family -> (SP source, NRT source, expected first CSV column)
FAMILIES = {
    "MODIS": ("MODIS_SP", "MODIS_NRT"),
    "VIIRS_SNPP": ("VIIRS_SNPP_SP", "VIIRS_SNPP_NRT"),
    "VIIRS_NOAA20": ("VIIRS_NOAA20_SP", "VIIRS_NOAA20_NRT"),
}
LOG_COLUMNS = ["source", "start", "days", "level", "rows", "attempts", "status"]


def load_keys() -> list[str]:
    """FIRMS_MAP_KEY, FIRMS_MAP_KEY_2, FIRMS_MAP_KEY_3, ... from the environment and .env."""
    found: dict[str, str] = {k: v for k, v in os.environ.items() if re.fullmatch(r"FIRMS_MAP_KEY(_\d+)?", k) and v}
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            m = re.fullmatch(r"(FIRMS_MAP_KEY(?:_\d+)?)=(.*)", line.strip())
            if m and m.group(2).strip():
                found.setdefault(m.group(1), m.group(2).strip())
    keys = [v for _, v in sorted(found.items(), key=lambda kv: int(kv[0].rsplit("_", 1)[-1]) if kv[0] != "FIRMS_MAP_KEY" and kv[0].rsplit("_", 1)[-1].isdigit() else 1)]
    if not keys:
        sys.exit("FIRMS_MAP_KEY is not set (put it in .env)")
    return list(dict.fromkeys(keys))  # drop duplicates, keep order


KEYS: list[str] = []
KEY = ""  # first key: used for availability and for the first status line


def redact(text: str) -> str:
    for k in KEYS:
        text = text.replace(k, "[KEY]")
    return text


def get(url: str) -> tuple[str, int]:
    """GET with retry/backoff on 429, 5xx and network errors. Returns (body, attempts)."""
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read().decode("utf-8"), attempt
        except urllib.error.HTTPError as e:
            quota = e.code == 400 and b"transaction limit" in e.read()
            if e.code != 429 and e.code < 500 and not quota:
                raise RuntimeError(f"HTTP {e.code}") from None
            why = "quota exceeded" if quota else f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            why = redact(str(e))
        wait = min(120, 5 * 2**attempt)
        print(f"  attempt {attempt}/{RETRIES} failed ({why}); waiting {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"gave up after {RETRIES} attempts")


def used_transactions(key: str) -> tuple[int, int]:
    """(current_transactions, transaction_limit) for one key's current 10-minute window."""
    body, _ = get(f"{HOST}/mapserver/mapkey_status/?MAP_KEY={key}")
    d = json.loads(body)
    return int(d["current_transactions"]), int(d["transaction_limit"])


LOCK = threading.Lock()
PENDING: dict[str, int] = {}  # transactions reserved by in-flight requests, per key
COST = 200  # assumed transactions per world request (measured 180 in this run); the 90% cap absorbs the rest


def acquire_key() -> str:
    """Block until some key can take one more request; reserve it. Picks the least-loaded key."""
    while True:
        with LOCK:
            KEYS[:] = load_keys()  # pick up keys added to .env while running
            keys = list(KEYS)
        usage = {k: used_transactions(k) for k in keys}
        with LOCK:
            fits = [(cur + PENDING.get(k, 0), k) for k, (cur, limit) in usage.items()
                    if cur + PENDING.get(k, 0) + COST <= 0.9 * limit]
            if fits:
                _, k = min(fits)
                PENDING[k] = PENDING.get(k, 0) + COST
                return k
        print("  all keys near quota: " + ", ".join(f"{c}/{l}" for c, l in usage.values()) + "; waiting", flush=True)
        time.sleep(20)


def release_key(key: str) -> None:
    with LOCK:
        PENDING[key] = max(0, PENDING.get(key, 0) - COST)


def fetch_availability(today: str) -> dict[str, tuple[dt.date, dt.date]]:
    AVAIL.mkdir(parents=True, exist_ok=True)
    body, _ = get(f"{HOST}/api/data_availability/csv/{KEY}/ALL")
    (AVAIL / f"data_availability_{today}.csv").write_text(body, encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(body)))
    if not rows or "data_id" not in rows[0]:
        sys.exit("unexpected data_availability response")
    out = {r["data_id"]: (dt.date.fromisoformat(r["min_date"]), dt.date.fromisoformat(r["max_date"])) for r in rows}
    miss, _ = get(f"{HOST}/api/missing_data/?action=fetch_data")
    json.loads(miss)  # fail loudly if the response is not JSON
    (AVAIL / f"missing_data_{today}.json").write_text(miss, encoding="utf-8")
    return out


def segments(family: str, avail: dict[str, tuple[dt.date, dt.date]]) -> list[tuple[str, dt.date, int, str]]:
    """(source, start, days, level) covering START..latest date, no date requested twice."""
    sp, nrt = FAMILIES[family]
    sp_max = avail[sp][1]
    last = avail[nrt][1]
    segs = []
    d = START
    while d <= last:
        end = min(d + dt.timedelta(days=WINDOW - 1), last)
        if end <= sp_max:
            segs.append((sp, d, (end - d).days + 1, "SP"))
        elif d > sp_max:
            segs.append((nrt, d, (end - d).days + 1, "NRT"))
        else:  # window crosses the SP/NRT boundary: split it
            segs.append((sp, d, (sp_max - d).days + 1, "SP"))
            segs.append((nrt, sp_max + dt.timedelta(days=1), (end - sp_max).days, "NRT"))
        d = end + dt.timedelta(days=1)
    return segs


def seg_path(source: str, start: dt.date, days: int) -> Path:
    return OUT / source / f"{start.isoformat()}_{days}.csv"


def check_coverage(avail: dict[str, tuple[dt.date, dt.date]]) -> bool:
    ok = True
    for fam in FAMILIES:
        dates: set[dt.date] = set()
        for source, start, days, _ in segments(fam, avail):
            p = seg_path(source, start, days)
            if not p.exists():
                print(f"MISSING {p.relative_to(ROOT)}")
                ok = False
                continue
            with open(p, encoding="utf-8") as f:
                header = f.readline()
            if not header.startswith("latitude,longitude"):
                print(f"BAD HEADER {p.name}")
                ok = False
            dates.update(start + dt.timedelta(days=i) for i in range(days))
        last = avail[FAMILIES[fam][1]][1]
        gaps = [START + dt.timedelta(days=i) for i in range((last - START).days + 1) if START + dt.timedelta(days=i) not in dates]
        print(f"{fam}: {len(dates)} days present, {len(gaps)} gaps, {START}..{last}")
        ok = ok and not gaps
    return ok


def main() -> int:
    global KEY, KEYS
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--workers", type=int, default=6, help="parallel requests (default 6)")
    args = ap.parse_args()
    KEYS = load_keys()
    KEY = KEYS[0]
    today = dt.date.today().isoformat()

    if args.check:
        avail_file = sorted(AVAIL.glob("data_availability_*.csv"))[-1]
        rows = csv.DictReader(open(avail_file, encoding="utf-8"))
        avail = {r["data_id"]: (dt.date.fromisoformat(r["min_date"]), dt.date.fromisoformat(r["max_date"])) for r in rows}
        return 0 if check_coverage(avail) else 1

    print(f"keys in use: {len(KEYS)}", flush=True)
    avail = fetch_availability(today)
    OUT.mkdir(parents=True, exist_ok=True)
    new_log = not LOG.exists()
    log = open(LOG, "a", encoding="utf-8", newline="")
    w = csv.writer(log, delimiter="\t")
    if new_log:
        w.writerow(LOG_COLUMNS)

    todo = [seg for fam in FAMILIES for seg in segments(fam, avail)
            if args.force or not seg_path(seg[0], seg[1], seg[2]).exists()]
    print(f"{len(todo)} segments to pull with {args.workers} workers", flush=True)
    log_lock = threading.Lock()

    def pull(seg: tuple[str, dt.date, int, str]) -> bool:
        source, start, days, level = seg
        print(f"{source} {start} +{days}d ({level})", flush=True)
        key = ""
        try:
            key = acquire_key()
            body, attempts = get(f"{HOST}/api/area/csv/{key}/{source}/world/{days}/{start.isoformat()}")
            if not body.startswith("latitude,longitude"):
                raise RuntimeError("response is not CSV: " + redact(" ".join(body[:80].split())))
            path = seg_path(source, start, days)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            tmp.write_text(body, encoding="utf-8", newline="")
            tmp.replace(path)  # atomic: a stopped run never leaves a half-written .csv
            row = [source, start, days, level, len(body.splitlines()) - 1, attempts, "OK"]
            ok = True
        except Exception as e:  # log and continue; never fill gaps
            row = [source, start, days, level, "", RETRIES, "FAIL: " + redact(str(e))]
            print("  FAIL:", redact(str(e)), flush=True)
            ok = False
        finally:
            if key:
                release_key(key)
        with log_lock:
            w.writerow(row)
            log.flush()
        return ok

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        failed = sum(not r for r in pool.map(pull, todo))
    log.close()
    print("transactions after:", [used_transactions(k)[0] for k in KEYS])
    print(f"failed segments: {failed}")
    return 0 if check_coverage(avail) and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
