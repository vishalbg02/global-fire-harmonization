"""'MODIS blindness' indicator per fire region (T-016, feature F13).

B = (sum of VIIRS cell-days) / (sum of Aqua cell-days) over the calibration fit months of a fire region, day and night apart, for each
VIIRS witness, for all fit months and for each season. It is the inverse of the T-011 ratio at fire-region level. The definition,
thresholds and caveats were fixed in docs/task-prompts/T-016-blindness.md before any real run.

B is not a fire count, not burned area and not a detection probability. Uncertainty: a 90% interval from a bootstrap over whole fit months
(sampling over months only).

    python pipeline/blindness.py      # writes data/interim/blindness/blindness_by_region.csv and .json
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibration as cal

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "interim" / "blindness"
BOOT = 1000
SEED = 20261115
MIN_CELL_DAYS = 100        # both the Aqua and the VIIRS sum (fixed before the run)
MIN_OVERLAP_MONTHS = 6     # months with both Aqua and VIIRS cell-days
MAX_MONTH_SHARE = 0.5      # as in T-011: one month holding more than half of the cell-days flags BURST
GLOBAL = "GLOBAL"
WITNESSES = ("SNPP_VIIRS", "NOAA20_VIIRS")
DAYNIGHT = ("D", "N")
CAVEAT = (
    "B is VIIRS cell-days per Aqua cell-day in the fit period. It is not a fire count, not burned area and not a detection probability. "
    "It mixes the 375 m versus 1 km sensitivity with overpass times (Aqua about 13:30 and 01:30, S-NPP about 13:30, NOAA-20 about 12:40), "
    "thresholds and cell-day saturation (the Aqua/VIIRS ratio rises with activity, T-020b), so it is lower in very active regions for that "
    "reason alone. It describes the fit months only. The interval is the spread over months and excludes model error. "
    "That MODIS misses small fires is a hypothesis here, not shown by this number."
)


def extra_share(b: float) -> float:
    """1 - 1/B: the share of VIIRS cell-days without an Aqua counterpart, as a sum (negative when B is below 1)."""
    return float(1.0 - 1.0 / b) if np.isfinite(b) and b > 0 else float("nan")


def _status(a: np.ndarray, w: np.ndarray) -> str:
    """a, w: (months,) cell-days of one region within a month set."""
    overlap = (a > 0) & (w > 0)
    if a.sum() < MIN_CELL_DAYS or w.sum() < MIN_CELL_DAYS or overlap.sum() < MIN_OVERLAP_MONTHS:
        return "CANNOT_DETERMINE"
    for x in (np.where(overlap, a, 0.0), np.where(overlap, w, 0.0)):
        if x.sum() > 0 and x.max() / x.sum() > MAX_MONTH_SHARE:
            return "BURST"
    return "OK"


def indicator_rows(a_m: np.ndarray, w_m: np.ndarray, regions: list[str], season_of_month: np.ndarray, boot: int = BOOT,
                   seed: int = SEED) -> list[dict]:
    """One row per region (plus GLOBAL, the sum over all regions) and month set (ALL and each season present).

    a_m, w_m: (months, regions) Aqua and VIIRS cell-days of the fit months of one witness and day/night.
    The same bootstrap draws of months are used for every region of a month set, so intervals are comparable.
    """
    rows: list[dict] = []
    names = list(regions) + [GLOBAL]
    a_all = np.column_stack([a_m, a_m.sum(axis=1)])
    w_all = np.column_stack([w_m, w_m.sum(axis=1)])
    sets = [("ALL", np.ones(len(season_of_month), dtype=bool))] + [(s, season_of_month == s) for s in cal.SEASONS if (season_of_month == s).any()]
    for season, sel in sets:
        a, w = a_all[sel], w_all[sel]
        n = a.shape[0]
        rng = np.random.default_rng(seed)
        counts = np.zeros((boot, n))
        for b in range(boot):
            counts[b] = np.bincount(rng.integers(0, n, n), minlength=n)
        ta, tw = counts @ a, counts @ w
        with np.errstate(divide="ignore", invalid="ignore"):
            bb = np.where(ta > 0, tw / np.where(ta > 0, ta, 1), np.nan)
        set_rows = []
        for j, name in enumerate(names):
            status = _status(a[:, j], w[:, j])
            sa, sw = float(a[:, j].sum()), float(w[:, j].sum())
            row = {"region": name, "season": season, "status": status, "B": float("nan"), "B_lo90": float("nan"), "B_hi90": float("nan"),
                   "extra_share": float("nan"), "extra_share_lo90": float("nan"), "extra_share_hi90": float("nan"),
                   "sum_aqua": sa, "sum_viirs": sw, "n_months": int(n), "n_overlap_months": int(((a[:, j] > 0) & (w[:, j] > 0)).sum()),
                   "vs_global": "", "caveat": CAVEAT}
            if status != "CANNOT_DETERMINE":
                col = bb[:, j][np.isfinite(bb[:, j])]
                row["B"] = sw / sa
                if col.size > 20:
                    row["B_lo90"], row["B_hi90"] = float(np.percentile(col, 5)), float(np.percentile(col, 95))
                row["extra_share"] = extra_share(row["B"])
                row["extra_share_lo90"], row["extra_share_hi90"] = extra_share(row["B_lo90"]), extra_share(row["B_hi90"])
            set_rows.append(row)
        g = set_rows[-1]["B"]
        for row in set_rows[:-1]:
            if row["status"] != "CANNOT_DETERMINE" and np.isfinite(g) and np.isfinite(row["B_lo90"]):
                row["vs_global"] = "higher" if row["B_lo90"] > g else "lower" if row["B_hi90"] < g else "not distinguishable"
        rows.extend(set_rows)
    return rows


# --------------------------------------------------------------------------------- real data
def load_matrices(con, paths: cal.Paths, witness: str, region_of_cell: dict[str, str], regions: list[str]):
    """Cell-days per fit month and region for Aqua and the witness, complete months only (calibration.monthly_sums with a region as stratum)."""
    months, sums, excluded = cal.monthly_sums(con, paths, witness, region_of_cell)
    r_idx = {r: i for i, r in enumerate(regions)}
    mats = {}
    for dn in DAYNIGHT:
        a = np.zeros((len(months), len(regions)))
        w = np.zeros((len(months), len(regions)))
        for (mi, r), n in sums.get(("AQUA_MODIS", dn), {}).items():
            a[mi, r_idx[r]] = n
        for (mi, r), n in sums.get((witness, dn), {}).items():
            w[mi, r_idx[r]] = n
        mats[dn] = (a, w)
    return months, mats, excluded


def calibration_crosscheck(paths: cal.Paths) -> dict:
    """Per (witness, daynight, season, region): inverse of the median T-011 stratum ratio and the median ratio_sd / ratio."""
    df = pd.read_parquet(paths.products / "calibration.parquet", columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd"])
    df = df[df.daynight.isin(DAYNIGHT)].copy()
    df["region"] = df.stratum_id.str.split("_b").str[0]
    df["rel_sd"] = df.ratio_sd / df.ratio
    g = df.groupby(["witness", "daynight", "season", "region"]).agg(med=("ratio", "median"), rsd=("rel_sd", "median"))
    return {k: (float(1.0 / v.med), float(v.rsd)) for k, v in g.iterrows()}


def run(paths: cal.Paths | None = None, boot: int = BOOT, out: Path = OUT) -> dict:
    paths = paths or cal.Paths()
    t0 = time.time()
    cells = cal.load_cells(paths)
    region_of_cell = dict(zip(cells["cell_id"], cells["fire_region"], strict=True))
    regions = sorted(set(region_of_cell.values()))
    tmp = ROOT / "data" / "interim" / "_tmp_T-016"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    for s in ("memory_limit='5GB'", "max_temp_directory_size='20GiB'", "preserve_insertion_order=false", "threads=4"):
        con.execute(f"SET {s}")
    check = calibration_crosscheck(paths)
    table: list[dict] = []
    meta: dict = {"regions": regions, "months": {}, "excluded": {}, "boot": boot, "seed": SEED}
    try:
        for witness in WITNESSES:
            months, mats, excluded = load_matrices(con, paths, witness, region_of_cell, regions)
            meta["months"][witness], meta["excluded"][witness] = len(months), [list(e) for e in excluded]
            seasons = np.array([cal.SEASON_OF[m] for _, m in months])
            (y0, m0), (y1, m1) = cal.FITS[witness]
            for dn in DAYNIGHT:
                a, w = mats[dn]
                for row in indicator_rows(a, w, regions, seasons, boot=boot):
                    row.update(witness=witness, daynight=dn, fit_period=f"{y0}-{m0:02d}/{y1}-{m1:02d}",
                               is_fire_region=row["region"] not in (cal.UNASSIGNED, GLOBAL))
                    c = check.get((witness, dn, row["season"], row["region"])) if row["season"] != "ALL" else None
                    row["calib_inverse_median"], row["calib_median_rel_sd"] = c if c else (float("nan"), float("nan"))
                    table.append(row)
            print(f"{witness} done ({time.time() - t0:.0f}s)", flush=True)
    finally:
        con.close()
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    cols = ["witness", "daynight", "region", "is_fire_region", "season", "status", "B", "B_lo90", "B_hi90", "extra_share", "extra_share_lo90",
            "extra_share_hi90", "vs_global", "sum_aqua", "sum_viirs", "n_months", "n_overlap_months", "calib_inverse_median",
            "calib_median_rel_sd", "fit_period", "caveat"]
    with open(out / "blindness_by_region.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        for r in table:
            wr.writerow({k: ("" if isinstance(r[k], float) and np.isnan(r[k]) else r[k]) for k in cols})
    meta["rows"], meta["seconds"] = len(table), round(time.time() - t0)
    (out / "blindness_by_region.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


if __name__ == "__main__":
    print(json.dumps(run(), indent=1)[:600])
