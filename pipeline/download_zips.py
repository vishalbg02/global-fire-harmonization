"""Download the FIRMS global yearly zips (T-001).

Standard library only. Resumable, idempotent, verifies each file against the
server's Content-Length and a zip CRC test, and writes a manifest next to the
zips (git-ignored, under data/raw/).

    python pipeline/download_zips.py            # download + verify everything
    python pipeline/download_zips.py --verify   # verify only, no network downloads
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://firms.modaps.eosdis.nasa.gov/data/country/zips"
# MODIS first (small, needed for everything), then S-NPP, then NOAA-20.
SENSORS: list[tuple[str, range]] = [
    ("modis", range(2002, 2026)),
    ("viirs-snpp", range(2012, 2026)),
    ("viirs-jpss1", range(2018, 2026)),
]
ROOT = Path(__file__).resolve().parents[1]
ZIP_DIR = ROOT / "data" / "raw" / "zips"
MANIFEST = ZIP_DIR / "MANIFEST.tsv"
CHUNK = 1 << 20
RETRIES = 5


def jobs() -> list[tuple[str, int, str]]:
    return [(s, y, f"{s}_{y}_all_countries.zip") for s, years in SENSORS for y in years]


def remote_size(url: str) -> int:
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch(url: str, dest: Path, expected: int) -> None:
    """Download to dest, resuming a partial file with an HTTP Range request."""
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, RETRIES + 1):
        have = part.stat().st_size if part.exists() else 0
        try:
            req = urllib.request.Request(url)
            if have:
                req.add_header("Range", f"bytes={have}-")
            with urllib.request.urlopen(req, timeout=60) as r:
                mode = "ab" if have and r.status == 206 else "wb"
                with open(part, mode) as f:
                    while chunk := r.read(CHUNK):
                        f.write(chunk)
            if part.stat().st_size == expected:
                part.replace(dest)
                return
            print(f"  size {part.stat().st_size} != {expected}, retrying", flush=True)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  attempt {attempt}/{RETRIES} failed: {e}", flush=True)
        time.sleep(min(60, 2**attempt))
    raise RuntimeError(f"gave up on {dest.name}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def zip_ok(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except zipfile.BadZipFile:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="verify existing files only")
    ap.add_argument("--workers", type=int, default=3, help="parallel sensors (default 3)")
    args = ap.parse_args()
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    if not args.verify:
        free = shutil.disk_usage(ZIP_DIR).free
        print(f"free disk: {free / 1e9:.1f} GB", flush=True)

    def run(job: tuple[str, int, str]) -> tuple[str, int, int, str, str]:
        _, _, name = job
        url, dest = f"{BASE}/{name}", ZIP_DIR / name
        try:
            expected = remote_size(url)
            if not (dest.exists() and dest.stat().st_size == expected):
                if args.verify:
                    raise RuntimeError("missing or wrong size")
                print(f"downloading {name} ({expected / 1e6:.1f} MB)", flush=True)
                fetch(url, dest, expected)
            if not zip_ok(dest):
                raise RuntimeError("zip integrity test failed")
            print(f"OK   {name}", flush=True)
            return (name, dest.stat().st_size, expected, sha256(dest), "OK")
        except Exception as e:  # noqa: BLE001  (record and continue; never substitute data)
            print(f"FAIL {name}: {e}", flush=True)
            size = dest.stat().st_size if dest.exists() else 0
            return (name, size, 0, "", f"FAIL: {e}")

    # One worker per sensor (the server appears to throttle each connection).
    by_sensor: dict[str, list] = {}
    for j in jobs():
        by_sensor.setdefault(j[0], []).append(j)

    def run_sensor(sensor_jobs: list) -> list:
        return [run(j) for j in sensor_jobs]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        groups = list(pool.map(run_sensor, by_sensor.values()))
    order = [n for _, _, n in jobs()]
    rows = sorted((r for g in groups for r in g), key=lambda r: order.index(r[0]))
    failed = [(r[0], r[4]) for r in rows if r[4] != "OK"]

    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write("file\tbytes\texpected_bytes\tsha256\tresult\n")
        f.writelines("\t".join(map(str, r)) + "\n" for r in rows)
    ok = [r for r in rows if r[4] == "OK"]
    print(f"\n{len(ok)}/{len(rows)} verified, {sum(r[1] for r in ok):,} bytes total")
    for name, why in failed:
        print(f"MISSING/FAILED: {name}: {why}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
