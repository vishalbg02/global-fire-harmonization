"""Generate the SYNTHETIC contract fixtures (T-010).

Every value produced here is synthetic. Geography is real (real ISO3 codes and cell
positions); activity levels, calibration ratios, the Aqua drift cutoff, verdict
thresholds and validation results are PLACEHOLDERS for exercising the app. They are
not NASA observations and not results.

    python pipeline/make_fixtures.py                 # writes data/fixtures/v0.1.0/
    python pipeline/make_fixtures.py --out some/dir  # writes elsewhere (used by tests)

The random seed is fixed, so the output is reproducible.
"""
from __future__ import annotations

import argparse
import calendar
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "fixtures" / "v0.1.0"

SEED = 20261114
CONTRACT_VERSION = "0.1.0"
METHOD_VERSION = "SYNTHETIC-0.0.0"
GENERATED_AT = "2026-11-14T00:00:00Z"  # fixed so the output is reproducible
RES = 0.5  # analysis grid (grid code g050)
FIRST_MONTH, LAST_MONTH = (2002, 7), (2026, 11)
BASELINE_YEARS = (2003, 2022)
MIN_BASELINE_VALUES = 10
DRIFT_CUTOFF = (2022, 1)  # PLACEHOLDER: Aqua leaves witnesses_used from this month
OUTAGE_MONTH = (2016, 2)  # PLACEHOLDER outage month (S-NPP)
NRT_FROM = {"AQUA_MODIS": (2026, 10), "TERRA_MODIS": (2026, 10), "SNPP_VIIRS": (2026, 8), "NOAA20_VIIRS": (2026, 8)}
START = {"AQUA_MODIS": FIRST_MONTH, "TERRA_MODIS": FIRST_MONTH, "SNPP_VIIRS": (2012, 1), "NOAA20_VIIRS": (2018, 4)}
WITNESSES = ["AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"]
DAY_FRACTION = {"AQUA_MODIS": 0.62, "TERRA_MODIS": 0.60, "SNPP_VIIRS": 0.52, "NOAA20_VIIRS": 0.52}
VERDICTS = ["ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL", "CANNOT_DETERMINE", "NO_DETECTED_ACTIVITY"]
REASONS = ["OUTAGE", "INSUFFICIENT_BASELINE", "INSUFFICIENT_OVERLAP", "WITNESS_DISAGREEMENT", "WIDE_INTERVAL",
           "PROVISIONAL_NRT", "AQUA_DRIFT_ERA", "SINGLE_WITNESS", "POOLED_CALIBRATION", "DIURNAL_CAVEAT"]
# Placeholder verdict thresholds (the real ones are locked at G1).
P_ABOVE, P_BELOW, P_WITHIN, DISAGREE_FLAG = 0.8, 0.8, 0.5, 1.25

# (iso3, continent, name, GFED-style region code, lat_min start, rows, lon_min start, cols, peak month, amplitude)
BLOCKS = [
    ("IDN", "AS", "Indonesia", "EQAS", -3.0, 5, 111.0, 6, 9, 60.0),
    ("AUS", "OC", "Australia", "AUST", -15.0, 5, 130.0, 6, 8, 80.0),
    ("AUS", "OC", "Australia", "AUST", -25.0, 3, 130.0, 3, 8, 0.0),  # desert block: no activity
    ("BRA", "SA", "Brazil", "SHSA", -12.0, 5, -56.0, 6, 8, 90.0),
    ("COD", "AF", "Democratic Republic of the Congo", "SHAF", -10.5, 5, 25.0, 6, 7, 70.0),
    ("USA", "NA", "United States", "TENA", 38.0, 5, -122.0, 6, 8, 35.0),
    ("PRT", "EU", "Portugal", "EURO", 39.5, 5, -8.5, 3, 8, 25.0),
    ("ESP", "EU", "Spain", "EURO", 39.5, 5, -5.5, 5, 8, 20.0),
]
CONTINENT_NAMES = {"AF": "Africa", "AS": "Asia", "EU": "Europe", "NA": "North America", "OC": "Oceania", "SA": "South America"}
POOLING = {"COD": "REGION", "ESP": "GLOBAL"}  # all other strata: LOCAL
SEASONS = ["DJF", "MAM", "JJA", "SON"]


def season_of(month: int) -> str:
    return SEASONS[(month % 12) // 3]


def month_list() -> list[tuple[int, int]]:
    out, (y, m) = [], FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        out.append((y, m))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# --------------------------------------------------------------------------- cells
def build_cells() -> pd.DataFrame:
    rows = []
    for b, (iso, cont, _, region, lat0, nr, lon0, nc, _, _) in enumerate(BLOCKS):
        for i in range(nr):
            for j in range(nc):
                lat_min, lon_min = lat0 + i * RES, lon0 + j * RES
                r, c = round((lat_min + 90) / RES), round((lon_min + 180) / RES)
                lat_max, lon_max = lat_min + RES, lon_min + RES
                area = 6371.0088**2 * math.radians(RES) * (math.sin(math.radians(lat_max)) - math.sin(math.radians(lat_min)))
                rows.append({
                    "cell_id": f"g{int(RES * 100):03d}_r{r:04d}_c{c:04d}",
                    "lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max,
                    "lat_c": lat_min + RES / 2, "lon_c": lon_min + RES / 2,
                    "area_km2": round(area, 2), "country_iso3": iso, "continent": cont,
                    "fire_region": region, "stratum_id": f"{region}_{iso}" + ("_DESERT" if BLOCKS[b][9] == 0 else ""),
                    "_block": b,
                })
    return pd.DataFrame(rows).sort_values("cell_id").reset_index(drop=True)


# ------------------------------------------------------------------------ calibration
def build_calibration(cells: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for stratum in sorted(cells["stratum_id"].unique()):
        iso = stratum.split("_")[1]
        for witness, period, overlap in (("SNPP_VIIRS", "2012-01/2016-12", 14), ("NOAA20_VIIRS", "2018-04/2021-12", 8)):
            for season in SEASONS:
                base = round(0.625 * (1 + 0.06 * rng.standard_normal()), 4)
                for dn, mult in (("ALL", 1.0), ("D", 1.03), ("N", 0.96)):
                    n_ov = 4 if (iso == "COD" and witness == "NOAA20_VIIRS") else overlap + int(rng.integers(-1, 2))
                    rows.append({
                        "stratum_id": stratum, "witness": witness, "daynight": dn, "season": season,
                        "ratio": round(base * mult, 4), "ratio_sd": round(0.02 + 0.05 * float(rng.random()), 4),
                        "n_overlap_months": n_ov, "fit_period": period, "pooling_level": POOLING.get(iso, "LOCAL"),
                    })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- core
def percentile_baseline(values: np.ndarray, years: np.ndarray, month_idx: np.ndarray) -> np.ndarray:
    """Per (row, month index): same-calendar-month baseline over BASELINE_YEARS.

    values: (n, T) with NaN for null. Returns (n, T, 3) of median, p25, p75 (NaN if too few values).
    """
    n, T = values.shape
    out = np.full((n, T, 3), np.nan)
    in_base = (years >= BASELINE_YEARS[0]) & (years <= BASELINE_YEARS[1])
    for m in range(1, 13):
        cols = np.where(in_base & (month_idx == m))[0]
        sub = values[:, cols]
        cnt = np.sum(~np.isnan(sub), axis=1)
        with np.errstate(all="ignore"):
            q = np.nanpercentile(sub, [50, 25, 75], axis=1)  # (3, n)
        q[:, cnt < MIN_BASELINE_VALUES] = np.nan
        for t in np.where(month_idx == m)[0]:
            out[:, t, :] = q.T
    return out


def verdict_for(est, sd, raw_sum, med, p25, p75):
    """Placeholder verdict rule. Returns (verdict, p_above, p_below, p_within, pct_of_normal, wide)."""
    if est is None or math.isnan(est):
        return "CANNOT_DETERMINE", None, None, None, None, False
    wide = (est + 1.645 * sd - max(est - 1.645 * sd, 0.0)) > max(est, 3.0) * 1.5
    if math.isnan(med):
        return "CANNOT_DETERMINE", None, None, None, None, wide
    pct = None if med == 0 else est / med * 100.0
    if raw_sum == 0 and p75 < 1.0:
        return "NO_DETECTED_ACTIVITY", None, None, None, pct, wide
    sd = max(sd, 0.5)
    pa_ = 1.0 - norm_cdf((p75 - est) / sd)
    pb_ = norm_cdf((p25 - est) / sd)
    pw_ = max(0.0, 1.0 - pa_ - pb_)
    if pa_ >= P_ABOVE:
        v = "ABOVE_NORMAL"
    elif pb_ >= P_BELOW:
        v = "BELOW_NORMAL"
    elif wide and pw_ < P_WITHIN:
        v = "CANNOT_DETERMINE"
    else:
        v = "WITHIN_NORMAL"
    return v, round(pa_, 4), round(pb_, 4), round(pw_, 4), pct, wide


def generate(out: Path) -> dict:
    rng = np.random.default_rng(SEED)
    months = month_list()
    T = len(months)
    years = np.array([y for y, _ in months])
    mon = np.array([m for _, m in months])
    dim = np.array([calendar.monthrange(y, m)[1] for y, m in months])
    t_index = {ym: i for i, ym in enumerate(months)}

    cells = build_cells()
    N = len(cells)
    calib = build_calibration(cells, rng)
    ratio = {(r.stratum_id, r.witness, r.season): r.ratio for r in calib[calib.daynight == "ALL"].itertuples()}

    # ---- latent Aqua-equivalent activity (cell-days) per cell and month --------------------
    block = cells["_block"].to_numpy()
    amp = np.array([BLOCKS[b][9] for b in block])
    peak = np.array([BLOCKS[b][8] for b in block])
    season_f = np.exp(1.6 * (np.cos(2 * np.pi * (mon[None, :] - peak[:, None]) / 12.0) - 1.0))
    cell_factor = rng.lognormal(0, 0.35, N)
    year_factor = {(b, y): float(rng.lognormal(0, 0.30)) for b in range(len(BLOCKS)) for y in range(2002, 2027)}
    yf = np.array([[year_factor[(block[i], years[t])] for t in range(T)] for i in range(N)])
    noise = rng.lognormal(0, 0.25, (N, T))
    latent = amp[:, None] * cell_factor[:, None] * season_f * yf * noise
    iso = cells["country_iso3"].to_numpy()
    for t in range(T):  # planted anomalies (synthetic)
        y, m = years[t], mon[t]
        if y == 2015 and m in (9, 10):
            latent[iso == "IDN", t] *= 4.0
        if y == 2009 and m in (7, 8, 9):
            latent[iso == "BRA", t] *= 0.25
        if y == 2011 and m in (8, 9, 10):
            latent[(iso == "AUS") & (amp > 0), t] *= 0.2
        if y == 2024 and m in (7, 8, 9):
            latent[iso == "USA", t] *= 3.0
    desert = np.where(amp == 0)[0]
    sudden_cell = desert[0]
    latent[desert, :] = 0.0
    latent[sudden_cell, t_index[(2020, 8)]] = 8.0  # a fire in a normally fire-free cell: zero baseline median

    # ---- no-usable-data cell-months (null estimate + INSUFFICIENT_BASELINE) -------------------
    cod = np.where(iso == "COD")[0]
    null_cell = cod[len(cod) // 2]
    no_data = np.zeros((N, T), bool)
    for t in range(T):
        if mon[t] == 7 and 2004 <= years[t] <= 2015:
            no_data[null_cell, t] = True

    # ---- witnesses: availability, raw counts ---------------------------------------------
    stratum = cells["stratum_id"].to_numpy()
    seasons = np.array([season_of(m) for m in mon])
    raw_all = {w: np.zeros((N, T), np.int64) for w in WITNESSES}
    avail = {w: np.zeros(T, int) for w in WITNESSES}
    operating = {w: np.array([ym >= START[w] for ym in months]) for w in WITNESSES}
    level = {w: np.array(["NRT" if ym >= NRT_FROM[w] else "SP" for ym in months]) for w in WITNESSES}
    for w in WITNESSES:
        for t, ym in enumerate(months):
            if not operating[w][t]:
                continue
            avail[w][t] = dim[t]
            if ym == LAST_MONTH:
                avail[w][t] = 2 if w == "SNPP_VIIRS" else 14  # S-NPP ends 2 Nov; others partial month
            if w == "SNPP_VIIRS" and ym == OUTAGE_MONTH:
                avail[w][t] = 21
    for w in WITNESSES:
        for i in range(N):
            for t in range(T):
                if not operating[w][t] or no_data[i, t]:
                    continue
                frac = avail[w][t] / dim[t]
                if w in ("AQUA_MODIS", "TERRA_MODIS"):
                    r = 1.0 if w == "AQUA_MODIS" else 0.87  # Terra raw ~1.15x Aqua
                else:
                    r = ratio[(stratum[i], w, seasons[t])]
                exp = latent[i, t] / r * frac * float(rng.lognormal(0, 0.10))
                if w == "SNPP_VIIRS" and iso[i] == "BRA" and (years[t], mon[t]) in ((2019, 8), (2019, 9)):
                    exp *= 1.8  # planted witness bias -> disagreement
                raw_all[w][i, t] = round(exp) if latent[i, t] > 0 else 0
    wit_records = []
    for w in WITNESSES:
        for i in range(N):
            for t in range(T):
                if not operating[w][t] or no_data[i, t]:
                    continue
                all_cd = int(raw_all[w][i, t])
                d_cd = round(all_cd * min(0.95, max(0.05, DAY_FRACTION[w] + 0.03 * math.sin(i))))
                for dn, cd in (("ALL", all_cd), ("D", d_cd), ("N", all_cd - d_cd)):
                    det = round(cd * 1.8 * (1 + 0.1 * math.sin(i + t)))
                    wit_records.append((cells.cell_id[i], int(years[t]), int(mon[t]), w, dn, det, cd,
                                        round(det * (11.0 if w.startswith(("AQUA", "TERRA")) else 7.5), 1),
                                        int(avail[w][t]), int(dim[t]), str(level[w][t])))
    cmw = pd.DataFrame(wit_records, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days",
                                             "frp_sum_mw", "days_available", "days_in_month", "data_level"])
    cmw = cmw.sort_values(["cell_id", "witness", "daynight", "year", "month"]).reset_index(drop=True)

    # ---- harmonization (placeholder method) ------------------------------------------------
    drift_t = t_index[DRIFT_CUTOFF]
    est = np.full((N, T), np.nan)
    sd = np.full((N, T), np.nan)
    scale = np.full((N, T), np.nan)
    used = [[[] for _ in range(T)] for _ in range(N)]
    raw_sum = np.zeros((N, T), np.int64)
    overlap_bad = np.zeros((N, T), bool)
    for i in range(N):
        for t in range(T):
            if no_data[i, t]:
                continue
            raw_sum[i, t] = sum(int(raw_all[w][i, t]) for w in WITNESSES if operating[w][t])
            cand = []
            if operating["AQUA_MODIS"][t] and t < drift_t:
                cand.append("AQUA_MODIS")
            if operating["SNPP_VIIRS"][t]:
                cand.append("SNPP_VIIRS")
            if operating["NOAA20_VIIRS"][t]:
                if iso[i] == "COD" and (2018, 4) <= months[t] <= (2018, 6):
                    overlap_bad[i, t] = True  # too little calibration overlap: witness not used
                else:
                    cand.append("NOAA20_VIIRS")
            conv, sds = [], []
            for w in cand:
                frac = avail[w][t] / dim[t]
                r = 1.0 if w == "AQUA_MODIS" else ratio[(stratum[i], w, seasons[t])]
                c = raw_all[w][i, t] * r / frac
                conv.append(c)
                sds.append(math.sqrt((0.15 * c) ** 2 + max(c, 1.0)) / math.sqrt(frac))
            wts = [1.0 / (s * s) for s in sds]
            mean = sum(w_ * c for w_, c in zip(wts, conv)) / sum(wts)
            s_comb = math.sqrt(1.0 / sum(wts))
            sc = 1.0
            if len(cand) >= 2:
                chi2 = sum(w_ * (c - mean) ** 2 for w_, c in zip(wts, conv))
                sc = max(1.0, math.sqrt(chi2 / (len(cand) - 1)))
                scale[i, t] = round(sc, 4)
            if months[t] == OUTAGE_MONTH:
                s_comb *= 1.5
            est[i, t], sd[i, t], used[i][t] = round(mean, 3), round(s_comb * sc, 3), cand
    base = percentile_baseline(est, years, mon)

    recs = []
    for i in range(N):
        pooled = POOLING.get(iso[i]) is not None
        for t in range(T):
            e = est[i, t]
            nw = len(used[i][t])
            med, p25, p75 = base[i, t]
            level_set = {str(level[w][t]) for w in WITNESSES if operating[w][t] and not no_data[i, t]}
            dl = "MIXED" if len(level_set) > 1 else (level_set.pop() if level_set else "SP")
            v, pa_, pb_, pw_, pct, wide = verdict_for(None if np.isnan(e) else float(e), float(sd[i, t]) if nw else 0.0,
                                                      int(raw_sum[i, t]), med, p25, p75)
            r: set[str] = set()
            if no_data[i, t]:
                r.add("OUTAGE")
            if np.isnan(med):
                r.add("INSUFFICIENT_BASELINE")
            if overlap_bad[i, t]:
                r.add("INSUFFICIENT_OVERLAP")
            if months[t] == OUTAGE_MONTH and not no_data[i, t]:
                r.add("OUTAGE")
            if not np.isnan(scale[i, t]) and scale[i, t] > DISAGREE_FLAG:
                r.add("WITNESS_DISAGREEMENT")
            if wide and nw:
                r.add("WIDE_INTERVAL")
            if dl in ("NRT", "MIXED") and nw:
                r.add("PROVISIONAL_NRT")
            if t >= drift_t and operating["AQUA_MODIS"][t]:
                r.add("AQUA_DRIFT_ERA")
                if iso[i] in ("IDN", "BRA"):
                    r.add("DIURNAL_CAVEAT")
            if nw == 1:
                r.add("SINGLE_WITNESS")
            if pooled and any(w != "AQUA_MODIS" for w in used[i][t]):
                r.add("POOLED_CALIBRATION")
            recs.append({
                "cell_id": cells.cell_id[i], "year": int(years[t]), "month": int(mon[t]),
                "estimate": None if np.isnan(e) else float(e),
                "ci90_low": None if np.isnan(e) else round(max(0.0, float(e) - 1.645 * float(sd[i, t])), 3),
                "ci90_high": None if np.isnan(e) else round(float(e) + 1.645 * float(sd[i, t]), 3),
                "sd": None if np.isnan(e) else float(sd[i, t]),
                "raw_combined_cell_days": int(raw_sum[i, t]),
                "witnesses_used": list(used[i][t]), "n_witnesses": nw,
                "disagreement_scale": None if np.isnan(scale[i, t]) else float(scale[i, t]),
                "baseline_median": None if np.isnan(med) else round(float(med), 3),
                "baseline_p25": None if np.isnan(p25) else round(float(p25), 3),
                "baseline_p75": None if np.isnan(p75) else round(float(p75), 3),
                "pct_of_normal": None if pct is None else round(pct, 2),
                "p_above": pa_, "p_below": pb_, "p_within": pw_,
                "verdict": v, "reason_codes": [c for c in REASONS if c in r],
                "data_level": dl, "method_version": METHOD_VERSION,
            })
    harm = pd.DataFrame(recs)

    entity = build_entities(cells, harm, cmw, months, years, mon)

    out.mkdir(parents=True, exist_ok=True)
    write_tables(out, cells.drop(columns="_block"), cmw, harm, entity, calib)
    meta = write_json(out, months)
    info = edge_case_report(cells, harm, cmw, entity, calib, null_cell, sudden_cell, desert)
    write_readme(out, info)
    return {"cells": cells, "cmw": cmw, "harm": harm, "entity": entity, "calib": calib, "metadata": meta, "info": info}


# ------------------------------------------------------------------------------ entities
def build_entities(cells, harm, cmw, months, years, mon) -> pd.DataFrame:
    T = len(months)
    idx_of = {c: i for i, c in enumerate(cells.cell_id)}
    h = harm.copy()
    h["ci"] = h.cell_id.map(idx_of)
    h["t"] = (h.year - FIRST_MONTH[0]) * 12 + h.month - FIRST_MONTH[1]
    est = np.full((len(cells), T), np.nan)
    var = np.full((len(cells), T), np.nan)
    ok = h.estimate.notna()
    est[h.ci[ok], h.t[ok]] = h.estimate[ok]
    var[h.ci[ok], h.t[ok]] = h.sd[ok] ** 2
    raw = np.zeros((len(cells), T))
    raw[h.ci, h.t] = h.raw_combined_cell_days
    all_rows = cmw[cmw.daynight == "ALL"].copy()
    all_rows["ci"] = all_rows.cell_id.map(idx_of)
    all_rows["t"] = (all_rows.year - FIRST_MONTH[0]) * 12 + all_rows.month - FIRST_MONTH[1]

    names = {c.country_iso3: n for c, n in ((cells[cells.country_iso3 == b[0]].iloc[0], b[2]) for b in BLOCKS)}
    entities = [("COUNTRY", i, names[i], cells.country_iso3 == i) for i in sorted(names)]
    entities += [("CONTINENT", c, CONTINENT_NAMES[c], cells.continent == c) for c in sorted(cells.continent.unique())]
    entities += [("GLOBAL", "GLOBAL", "Global (fixture cells)", np.ones(len(cells), bool))]

    rows = []
    hidx = h.set_index(["ci", "t"])
    for etype, eid, ename, mask in entities:
        ci = np.where(np.asarray(mask))[0]
        e_est = np.where(np.all(np.isnan(est[ci]), axis=0), np.nan, np.nansum(est[ci], axis=0))
        e_sd = np.sqrt(np.nansum(var[ci], axis=0))
        base = percentile_baseline(e_est[None, :], years, mon)[0]
        sub = all_rows[all_rows.ci.isin(ci)]
        by_w = sub.groupby(["t", "witness"]).cell_days.sum()
        for t in range(T):
            e = e_est[t]
            cells_t = [hidx.loc[(c, t)] for c in ci]
            used_w = sorted({w for r in cells_t for w in r.witnesses_used}, key=WITNESSES.index)
            levels = {r.data_level for r in cells_t}
            counts = defaultdict(int)
            for r in cells_t:
                for c in r.reason_codes:
                    counts[c] += 1
            codes = [c for c in REASONS if counts[c] * 2 >= len(ci)]
            scales = [r.disagreement_scale for r in cells_t if r.disagreement_scale is not None]
            med, p25, p75 = base[t]
            v, pa_, pb_, pw_, pct, wide = verdict_for(None if np.isnan(e) else float(e), float(e_sd[t]),
                                                      int(raw[ci, t].sum()), med, p25, p75)
            if wide and "WIDE_INTERVAL" not in codes:
                codes = [c for c in REASONS if c in set(codes) | {"WIDE_INTERVAL"}]
            rbw = {w: int(by_w.get((t, w), 0)) for w in WITNESSES if (t, w) in by_w.index}
            rows.append({
                "entity_type": etype, "entity_id": eid, "entity_name": ename,
                "year": int(years[t]), "month": int(mon[t]),
                "estimate": None if np.isnan(e) else round(float(e), 3),
                "ci90_low": None if np.isnan(e) else round(max(0.0, float(e) - 1.645 * float(e_sd[t])), 3),
                "ci90_high": None if np.isnan(e) else round(float(e) + 1.645 * float(e_sd[t]), 3),
                "sd": None if np.isnan(e) else round(float(e_sd[t]), 3),
                "raw_combined_cell_days": int(raw[ci, t].sum()),
                "witnesses_used": used_w, "n_witnesses": len(used_w),
                "disagreement_scale": max(scales) if scales else None,
                "baseline_median": None if np.isnan(med) else round(float(med), 3),
                "baseline_p25": None if np.isnan(p25) else round(float(p25), 3),
                "baseline_p75": None if np.isnan(p75) else round(float(p75), 3),
                "pct_of_normal": None if pct is None else round(pct, 2),
                "p_above": pa_, "p_below": pb_, "p_within": pw_,
                "verdict": v, "reason_codes": codes,
                "data_level": levels.pop() if len(levels) == 1 else "MIXED",
                "method_version": METHOD_VERSION, "n_cells": len(ci),
                "raw_by_witness": json.dumps(rbw, sort_keys=True),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------- output
STR, I32, F64 = pa.string(), pa.int32(), pa.float64()
LIST_STR = pa.list_(pa.string())
SCHEMAS = {
    "cells": pa.schema([("cell_id", STR), ("lat_min", F64), ("lat_max", F64), ("lon_min", F64), ("lon_max", F64),
                        ("lat_c", F64), ("lon_c", F64), ("area_km2", F64), ("country_iso3", STR), ("continent", STR),
                        ("fire_region", STR), ("stratum_id", STR)]),
    "cell_month_witness": pa.schema([("cell_id", STR), ("year", I32), ("month", I32), ("witness", STR), ("daynight", STR),
                                     ("detections", I32), ("cell_days", I32), ("frp_sum_mw", F64),
                                     ("days_available", I32), ("days_in_month", I32), ("data_level", STR)]),
    "cell_month_harmonized": pa.schema([("cell_id", STR), ("year", I32), ("month", I32), ("estimate", F64), ("ci90_low", F64),
                                        ("ci90_high", F64), ("sd", F64), ("raw_combined_cell_days", I32),
                                        ("witnesses_used", LIST_STR), ("n_witnesses", I32), ("disagreement_scale", F64),
                                        ("baseline_median", F64), ("baseline_p25", F64), ("baseline_p75", F64),
                                        ("pct_of_normal", F64), ("p_above", F64), ("p_below", F64), ("p_within", F64),
                                        ("verdict", STR), ("reason_codes", LIST_STR), ("data_level", STR),
                                        ("method_version", STR)]),
    "entity_month": pa.schema([("entity_type", STR), ("entity_id", STR), ("entity_name", STR), ("year", I32), ("month", I32),
                               ("estimate", F64), ("ci90_low", F64), ("ci90_high", F64), ("sd", F64),
                               ("raw_combined_cell_days", I32), ("witnesses_used", LIST_STR), ("n_witnesses", I32),
                               ("disagreement_scale", F64), ("baseline_median", F64), ("baseline_p25", F64),
                               ("baseline_p75", F64), ("pct_of_normal", F64), ("p_above", F64), ("p_below", F64),
                               ("p_within", F64), ("verdict", STR), ("reason_codes", LIST_STR), ("data_level", STR),
                               ("method_version", STR), ("n_cells", I32), ("raw_by_witness", STR)]),
    "calibration": pa.schema([("stratum_id", STR), ("witness", STR), ("daynight", STR), ("season", STR), ("ratio", F64),
                              ("ratio_sd", F64), ("n_overlap_months", I32), ("fit_period", STR), ("pooling_level", STR)]),
}


def write_tables(out: Path, cells, cmw, harm, entity, calib) -> None:
    for name, df in (("cells", cells), ("cell_month_witness", cmw), ("cell_month_harmonized", harm),
                     ("entity_month", entity), ("calibration", calib)):
        schema = SCHEMAS[name]
        df = df[[f.name for f in schema]]
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        pq.write_table(table, out / f"{name}.parquet", compression="zstd", compression_level=19)


def write_json(out: Path, months) -> dict:
    meta = {
        "contract_version": CONTRACT_VERSION, "method_version": METHOD_VERSION, "synthetic": True,
        "generated_at": GENERATED_AT, "grid": {"analysis_deg": RES, "fine_deg": None},
        "baseline_years": list(BASELINE_YEARS), "first_month": "2002-07", "latest_month": "2026-11",
        "provisional_months": ["2026-08", "2026-09", "2026-10", "2026-11"],
        "witnesses": ["AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"],
        "data_snapshot": {"zips_downloaded": None, "api_pulled": None},
        "citation": "SYNTHETIC DATA, not NASA observations. Real products will cite NASA FIRMS (LANCE, ESDIS).",
    }
    tests = [
        ("SYNTHETIC-A1-INDONESIA-2015", "A", "Real anomaly preserved (two independent paths)", "Indonesia Sep-Oct 2015",
         "Same direction; peak month +-1; magnitudes overlap within 90% intervals", {"aqua_only_pct_of_normal": 410.0, "snpp_only_pct_of_normal": 380.0}, "PASS"),
        ("SYNTHETIC-B1-SNPP-START", "B", "No spurious step when a satellite starts", "S-NPP start 2012-01",
         "No step larger than the placeholder tolerance", {"step_pct": 31.0}, "FAIL"),
        ("SYNTHETIC-B3-AQUA-DRIFT", "B", "Known artifact handled", "Aqua drift era from 2022-01",
         "Drift flagged; Aqua excluded from witnesses_used", {"months_flagged": 59}, "PASS"),
        ("SYNTHETIC-D1-COVERAGE", "D", "Interval coverage on holdout", "Holdout 2017-2021",
         "Nominal 90% coverage within tolerance", {"coverage": None}, "INCONCLUSIVE"),
        ("SYNTHETIC-D2-GAPS", "D", "Gaps shown as gaps", "Outage month 2016-02",
         "Outage months flagged, never filled", {}, "NOT_RUN"),
        ("SYNTHETIC-CTRL-QUIET", "CTRL", "Quiet months stay quiet", "Fire-free desert cells",
         "NO_DETECTED_ACTIVITY, never BELOW_NORMAL", {"cells_checked": 8}, "PASS"),
    ]
    val = {
        "contract_version": CONTRACT_VERSION, "method_version": METHOD_VERSION, "generated_at": GENERATED_AT, "synthetic": True,
        "tests": [{
            "test_id": tid, "family": fam, "title": title, "case": case, "criterion": crit,
            "threshold": "SYNTHETIC placeholder (real thresholds are pre-registered at G1)",
            "measured": measured, "status": status, "notes": "SYNTHETIC EXAMPLE — not a result",
        } for tid, fam, title, case, crit, measured, status in tests],
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "validation_results.json").write_text(json.dumps(val, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


def edge_case_report(cells, harm, cmw, entity, calib, null_cell, sudden_cell, desert) -> dict:
    cid = cells.cell_id
    info = {"counts": {"cells": len(cells), "cell_month_witness": len(cmw), "cell_month_harmonized": len(harm),
                       "entity_month": len(entity), "calibration": len(calib)}}
    info["verdict_counts"] = harm.verdict.value_counts().to_dict()
    codes = harm.reason_codes.explode().value_counts().to_dict()
    info["reason_counts"] = {k: int(codes.get(k, 0)) for k in REASONS}
    info["null_cell"] = cid[null_cell]
    info["sudden_cell"] = cid[sudden_cell]
    info["desert_cells"] = [cid[i] for i in desert if i != sudden_cell]
    z = harm[(harm.baseline_median == 0) & harm.estimate.notna() & (harm.estimate > 0)]
    info["zero_median_example"] = None if z.empty else (z.iloc[0].cell_id, int(z.iloc[0].year), int(z.iloc[0].month))
    d = harm[harm.disagreement_scale.fillna(0) > 1.0]
    info["disagreement_rows"] = len(d)
    info["disagreement_example"] = None if d.empty else (d.sort_values("disagreement_scale").iloc[-1].cell_id,
                                                        int(d.sort_values("disagreement_scale").iloc[-1].year),
                                                        int(d.sort_values("disagreement_scale").iloc[-1].month))
    info["null_estimate_rows"] = int(harm.estimate.isna().sum())
    return info


def write_readme(out: Path, info: dict) -> None:
    c, v, r = info["counts"], info["verdict_counts"], info["reason_counts"]
    z, d = info["zero_median_example"], info["disagreement_example"]
    text = f"""# SYNTHETIC fixtures, contract v{CONTRACT_VERSION}

**SYNTHETIC DATA. Not NASA observations. Not results.** Values are made up to test the application. Geography is real
(real ISO3 codes and real cell positions). Every file here is generated by `pipeline/make_fixtures.py` with a fixed random
seed; regenerate with `python pipeline/make_fixtures.py`. Check against the contract with `python pipeline/contract_check.py`.

## Files

| File | Rows |
|---|---|
| `cells.parquet` | {c['cells']} |
| `cell_month_witness.parquet` | {c['cell_month_witness']:,} |
| `cell_month_harmonized.parquet` | {c['cell_month_harmonized']:,} |
| `entity_month.parquet` | {c['entity_month']:,} |
| `calibration.parquet` | {c['calibration']} |
| `metadata.json` | `"synthetic": true` |
| `validation_results.json` | `"synthetic": true`; every `test_id` starts with `SYNTHETIC-` |

## Coverage

- Grid `g050` (0.5 degrees), {c['cells']} cells in 8 blocks over 7 countries on 6 continents: IDN (AS), AUS (OC, two blocks), BRA (SA), COD (AF), USA (NA), PRT and ESP (EU).
- Months 2002-07 to 2026-11. Witness windows: `AQUA_MODIS` from 2002-07; `TERRA_MODIS` in raw rows only; `SNPP_VIIRS` 2012-01 to 2026-11; `NOAA20_VIIRS` from 2018-04.
- Entities in `entity_month`: 7 `COUNTRY`, 6 `CONTINENT`, 1 `GLOBAL`. The `GLOBAL` entity covers only the fixture cells.
- The app must show a persistent "SYNTHETIC DATA — not NASA observations" banner while `metadata.synthetic` is `true`.

## Edge cases (all present)

| Case | Where |
|---|---|
| Every `verdict` | counts in `cell_month_harmonized`: {', '.join(f'{k} {n:,}' for k, n in sorted(v.items()))} |
| Every `reason_code` | counts: {', '.join(f'{k} {n:,}' for k, n in r.items())} |
| Outage month | 2016-02: S-NPP `days_available` = 21 of 29 (placeholder), reason `OUTAGE` on every cell |
| Last months provisional | 2026-08 to 2026-09 `data_level = MIXED`; 2026-10 and 2026-11 `data_level = NRT`; `metadata.provisional_months` lists 2026-08 to 2026-11 |
| Zero baseline median (`pct_of_normal` null) | all rows of the desert cells, and e.g. `{z[0] if z else ''}` {f'{z[1]}-{z[2]:02d}' if z else ''} (a fire in a normally fire-free cell) |
| `disagreement_scale` > 1 | {info['disagreement_rows']:,} rows; strongest example `{d[0] if d else ''}` {f'{d[1]}-{d[2]:02d}' if d else ''} (planted S-NPP bias in Brazil, 2019-08 and 2019-09) |
| `NO_DETECTED_ACTIVITY` | the desert cells in Australia, e.g. `{info['desert_cells'][0]}` |
| Null `estimate` | {info['null_estimate_rows']} rows: cell `{info['null_cell']}`, every July 2004-2015 (no witness had usable data) |
| `INSUFFICIENT_BASELINE` | the same cell, every July (baseline has fewer than {MIN_BASELINE_VALUES} values) |
| `INSUFFICIENT_OVERLAP` | COD cells, 2018-04 to 2018-06 (NOAA-20 not used) |
| `AQUA_DRIFT_ERA` | all cells from 2022-01 (placeholder cutoff); Aqua leaves `witnesses_used` |
| Planted anomalies | Indonesia 2015-09/10 high; Brazil 2009 and Australia 2011 low; USA 2024 high (all synthetic) |

## Placeholders (not decisions)

Calibration ratios, the Aqua drift cutoff, the outage month, verdict thresholds (p ≥ {P_ABOVE} / {P_BELOW} / {P_WITHIN}),
the disagreement flag ({DISAGREE_FLAG}), baseline rule (same calendar month, 2003 to 2022, at least {MIN_BASELINE_VALUES} values),
fire-region codes, strata and the day/night split are all placeholders. The grid decision (D-009) and `fine_deg` are open, so
`metadata.grid.fine_deg` is `null`. `data_snapshot` dates are `null` because no real snapshot exists for synthetic data.
Probabilities are `null` for `NO_DETECTED_ACTIVITY`, `CANNOT_DETERMINE` without a baseline, and null estimates.
Entity values add the cell estimates and combine their standard deviations as if independent (placeholder).

## Conventions used (still PROPOSED, D-022)

`cell_id` = `g050_r{{row:04d}}_c{{col:04d}}` (row from the south, column from -180); entity IDs are ISO3 codes, `AF/AS/EU/NA/OC/SA`
and `GLOBAL`; each product is one `<name>.parquet` file.
"""
    (out / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    res = generate(args.out)
    size = sum(f.stat().st_size for f in args.out.iterdir())
    print(f"wrote {args.out} ({size / 1e6:.2f} MB)")
    print(res["info"]["counts"])


if __name__ == "__main__":
    main()
