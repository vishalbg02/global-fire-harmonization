"""Aqua drift diagnostic (T-012, part B).

Monthly ratio R(t) = Aqua / converted VIIRS (the T-011 ratios, nothing refitted), globally and per fire region, day and night
separately, from S-NPP and from NOAA-20 separately. Complete witness-months only (both witnesses).

PRE-REGISTERED change-point method (docs/task-prompts/T-012-holdout-drift.md section 9.4, fixed before any result was seen):
on y(t) = log R(t) of the GLOBAL DAY series from S-NPP, fit a model that is flat up to a break month b and linear afterwards,
continuous at b:  y = a + s x max(0, t - b), by least squares over the candidate months b from 2018-01 to 2025-06. The onset is
the b with the smallest residual sum of squares. Its 90% interval is the 5th to 95th percentile of b over 1,000 moving-block
bootstrap replicates of the residuals (blocks of 6 months, fixed seed; every replicate repeats the whole search over b). The
slope after b is reported with the 5th to 95th percentile of the replicate slopes. Drift is DETECTED only if the slope interval
excludes 0 AND the break model beats the flat model by BIC (BIC = n log(RSS / n) + k log n; flat: k = 2 (level, sigma); break:
k = 4 (level, slope, break month, sigma)). The same is repeated as confirmation, not selection, for the other series.

Deviations are written into the report (for example a later first candidate for a short series). The proposal is for the Lead's
approval (D-005); nothing here is applied anywhere.

    python pipeline/aqua_drift.py     # writes data/interim/qa/aqua_drift_report.json and docs/figures/aqua_drift.png
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

SEED = 2012                  # fixed seed of every bootstrap
N_BOOT = 1000
BLOCK = 6                    # months
FIRST_MONTH = (2012, 1)
CAND_FIRST = (2018, 1)       # candidate break months of the pre-registered method
CAND_LAST = (2025, 6)
MIN_UNITS = 20.0             # a month enters a regional series only if Aqua and converted VIIRS each have at least this many cell-days
MIN_POINTS = 60              # shortest series that is fitted
K_FLAT, K_BREAK = 2, 4       # BIC parameter counts
PRIMARY = ("GLOBAL", "D", "SNPP_VIIRS")
VIIRS = ("SNPP_VIIRS", "NOAA20_VIIRS")


def month_index(year: int, month: int) -> int:
    """Months since 2012-01."""
    return (year - FIRST_MONTH[0]) * 12 + (month - FIRST_MONTH[1])


def month_label(idx: int) -> str:
    y, m = divmod(int(idx) + FIRST_MONTH[1] - 1, 12)
    return f"{FIRST_MONTH[0] + y}-{m + 1:02d}"


# --------------------------------------------------------------------------------------------- the pure change-point code
def scan(t: np.ndarray, y: np.ndarray, cand: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares fit of y = a + s x max(0, t - b) for every candidate b.

    y: (n,) or (reps, n). Returns the residual sum of squares and the slope, shape (len(cand),) or (reps, len(cand)).
    """
    y2 = np.atleast_2d(y)
    yc = y2 - y2.mean(axis=1, keepdims=True)
    syy = (yc ** 2).sum(axis=1)
    rss = np.empty((y2.shape[0], len(cand)))
    slope = np.empty_like(rss)
    for j, b in enumerate(cand):
        x = np.maximum(0.0, t - b)
        xc = x - x.mean()
        sxx = float((xc ** 2).sum())
        if sxx <= 0:
            rss[:, j], slope[:, j] = syy, 0.0
            continue
        sxy = yc @ xc
        slope[:, j] = sxy / sxx
        rss[:, j] = syy - sxy ** 2 / sxx
    rss = np.maximum(rss, 0.0)
    return (rss[0], slope[0]) if y.ndim == 1 else (rss, slope)


def bic(rss: float, n: int, k: int) -> float:
    return n * np.log(max(rss, 1e-300) / n) + k * np.log(n)


def fit_break(t: np.ndarray, y: np.ndarray, cand: np.ndarray) -> dict:
    """The best break month, level, slope, the flat model and the two BIC values."""
    rss, slope = scan(t, y, cand)
    j = int(np.argmin(rss))
    b = int(cand[j])
    x = np.maximum(0.0, t - b)
    a = float(y.mean() - slope[j] * x.mean())
    n = len(y)
    rss_flat = float(((y - y.mean()) ** 2).sum())
    return {"b": b, "a": a, "slope": float(slope[j]), "rss": float(rss[j]), "rss_flat": rss_flat, "n": n,
            "bic_break": float(bic(rss[j], n, K_BREAK)), "bic_flat": float(bic(rss_flat, n, K_FLAT)),
            "fitted": a + slope[j] * x}


def block_indices(n: int, block: int, reps: int, rng: np.random.Generator) -> np.ndarray:
    """Moving-block bootstrap: overlapping blocks of `block` consecutive positions, concatenated and cut to length n."""
    block = max(1, min(block, n))
    nb = -(-n // block)
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, nb * block)
    return idx[:, :n]


def bootstrap_break(t: np.ndarray, y: np.ndarray, cand: np.ndarray, fit: dict | None = None, reps: int = N_BOOT, block: int = BLOCK,
                    seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    """Break months and slopes of `reps` moving-block bootstrap replicates of the residuals of the fitted break model."""
    fit = fit or fit_break(t, y, cand)
    resid = y - fit["fitted"]
    rng = np.random.default_rng(seed)
    ystar = fit["fitted"][None, :] + resid[block_indices(len(y), block, reps, rng)]
    rss, slope = scan(t, ystar, cand)
    j = np.argmin(rss, axis=1)
    return cand[j].astype(int), slope[np.arange(reps), j]


def detect(t: np.ndarray, y: np.ndarray, cand: np.ndarray, reps: int = N_BOOT, block: int = BLOCK, seed: int = SEED) -> dict:
    """The registered procedure: onset, its 90% interval, the slope and its interval, BIC comparison, detected yes/no."""
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    fit = fit_break(t, y, np.asarray(cand))
    bs, ss = bootstrap_break(t, y, np.asarray(cand), fit, reps, block, seed)
    b_lo, b_hi = (int(v) for v in np.percentile(bs, [5, 95]))
    s_lo, s_hi = (float(v) for v in np.percentile(ss, [5, 95]))
    excludes0 = bool(s_lo > 0 or s_hi < 0)
    beats = bool(fit["bic_break"] < fit["bic_flat"])
    return {"onset": fit["b"], "onset_lo": b_lo, "onset_hi": b_hi, "slope": fit["slope"], "slope_lo": s_lo, "slope_hi": s_hi,
            "bic_break": fit["bic_break"], "bic_flat": fit["bic_flat"], "delta_bic": fit["bic_flat"] - fit["bic_break"],
            "slope_interval_excludes_0": excludes0, "break_beats_flat_by_bic": beats, "detected": excludes0 and beats,
            "n": fit["n"], "level": fit["a"], "rss": fit["rss"], "rss_flat": fit["rss_flat"], "fitted": fit["fitted"]}


def null_pvalue(t: np.ndarray, y: np.ndarray, cand: np.ndarray, reps: int = N_BOOT, block: int = BLOCK, seed: int = SEED) -> dict:
    """SENSITIVITY (not part of the registered method): how often does a series with NO break, resampled in blocks, gain as much
    from the best break as the observed one? Searching over b always lowers the residual sum of squares a little; this puts the
    observed gain in that context. Gain = 1 - RSS(break) / RSS(flat)."""
    y = np.asarray(y, float)
    resid = y - y.mean()
    rng = np.random.default_rng(seed)
    ystar = y.mean() + resid[block_indices(len(y), block, reps, rng)]
    rss, _ = scan(np.asarray(t, float), ystar, np.asarray(cand))
    flat = ((ystar - ystar.mean(axis=1, keepdims=True)) ** 2).sum(axis=1)
    gain_null = 1 - rss.min(axis=1) / flat
    rss_o, _ = scan(np.asarray(t, float), y, np.asarray(cand))
    gain_obs = float(1 - rss_o.min() / ((y - y.mean()) ** 2).sum())
    return {"gain_observed": gain_obs, "gain_null_p95": float(np.percentile(gain_null, 95)), "p_value": float((gain_null >= gain_obs).mean())}


# ----------------------------------------------------------------------------------------------------- the series builder
def build_series(agg: pd.DataFrame, min_units: float = 0.0) -> pd.DataFrame:
    """Monthly R = Aqua / converted VIIRS from the harmonize.aggregate table.

    agg: entity_id, year, month, witness, daynight, e (converted estimate, Aqua ratio 1), complete. Returns one row per
    series key (GLOBAL and each entity_id), VIIRS witness, daynight and month, with the columns aqua, viirs, R, idx. Only months
    where Aqua and that VIIRS witness are both complete are kept (the global value needs every entity complete); a month with
    either side below `min_units` cell-days, or zero, is dropped.
    """
    a = agg[agg.witness.isin(("AQUA_MODIS",) + VIIRS)]
    g = a.groupby(["year", "month", "witness", "daynight"]).agg(e=("e", "sum"), complete=("complete", "all")).reset_index()
    g["entity_id"] = "GLOBAL"
    frames = [g, a[["entity_id", "year", "month", "witness", "daynight", "e", "complete"]]]
    both = pd.concat(frames, ignore_index=True)
    aq = both[both.witness == "AQUA_MODIS"].rename(columns={"e": "aqua", "complete": "c_aqua"}).drop(columns="witness")
    out = []
    for w in VIIRS:
        v = both[both.witness == w].rename(columns={"e": "viirs", "complete": "c_viirs"}).drop(columns="witness")
        j = aq.merge(v, on=["entity_id", "year", "month", "daynight"])
        j = j[j.c_aqua.astype(bool) & j.c_viirs.astype(bool)]
        j = j[(j.aqua > 0) & (j.viirs > 0) & (j.aqua >= min_units) & (j.viirs >= min_units)].copy()
        j["witness"] = w
        out.append(j)
    r = pd.concat(out, ignore_index=True)
    r["R"] = r.aqua / r.viirs
    r["idx"] = [month_index(y, m) for y, m in zip(r.year, r.month, strict=True)]
    return r.sort_values(["entity_id", "witness", "daynight", "idx"]).reset_index(drop=True)[
        ["entity_id", "witness", "daynight", "year", "month", "idx", "aqua", "viirs", "R"]]


def candidates(first_idx: int, min_after_first: int = 0, last: tuple[int, int] = CAND_LAST) -> np.ndarray:
    """Candidate break months: the registered range 2018-01 to 2025-06, started later if the series starts later
    (at least `min_after_first` months after the first observation)."""
    lo = max(month_index(*CAND_FIRST), first_idx + min_after_first)
    return np.arange(lo, month_index(*last) + 1)


def run_series(s: pd.DataFrame, min_after_first: int = 0, reps: int = N_BOOT, block: int = BLOCK, seed: int = SEED,
               last: tuple[int, int] = CAND_LAST) -> dict:
    t = s.idx.to_numpy(float)
    y = np.log(s.R.to_numpy(float))
    cand = candidates(int(t.min()), min_after_first, last)
    if len(s) < MIN_POINTS or len(cand) == 0:
        return {"status": "insufficient data", "n": len(s)}
    res = detect(t, y, cand, reps, block, seed)
    res.update({"status": "ok", "candidate_first": month_label(cand[0]), "candidate_last": month_label(cand[-1])})
    return res


def public(res: dict) -> dict:
    """The JSON-friendly result with month labels and percent per year."""
    if res.get("status") != "ok":
        return res
    out = {k: v for k, v in res.items() if k != "fitted"}
    for k in ("onset", "onset_lo", "onset_hi"):
        out[k + "_month"] = month_label(res[k])
    for k in ("slope", "slope_lo", "slope_hi"):
        out[k + "_pct_per_year"] = 100 * (np.exp(12 * res[k]) - 1)
    return {k: (float(v) if isinstance(v, np.floating) else v) for k, v in out.items()}


# ----------------------------------------------------------------------------------------------------- the DuckDB reading
def read_aggregates(paths=None) -> tuple[pd.DataFrame, dict]:
    """Thin reading: harmonize.aggregate over every cell, entity = fire region (UNASSIGNED kept, cells with no region as NONE)."""
    import duckdb
    import harmonize as hz
    paths = paths or hz.Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='4GB'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS SELECT 'REGION' AS entity_type, coalesce(fire_region, 'NONE') AS entity_id,
                    coalesce(fire_region, 'NONE') AS entity_name, cell_id FROM {cells}""")
    last = con.execute(f"SELECT max(year * 100 + month) FROM read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')").fetchone()[0]
    months = [(y, m) for y in range(2012, last // 100 + 1) for m in range(1, 13) if y * 100 + m <= last]
    agg = hz.aggregate(con, paths, "members", months)
    info = {"cells_by_region": dict(con.execute("SELECT entity_id, count(*) FROM members GROUP BY 1 ORDER BY 1").fetchall()),
            "missing_ratio_rows": int(agg["missing"].sum())}
    return agg, info


# ------------------------------------------------------------------------------------------------------------ the report
FIT_PERIODS = {"SNPP_VIIRS": (month_index(2012, 1), month_index(2016, 12)), "NOAA20_VIIRS": (month_index(2018, 4), month_index(2021, 12))}


@dataclass
class Outputs:
    report: Path = ROOT / "data" / "interim" / "qa" / "aqua_drift_report.json"
    figure: Path = ROOT / "docs" / "figures" / "aqua_drift.png"


def run(paths=None, outputs: Outputs | None = None) -> dict:
    outputs = outputs or Outputs()
    agg, info = read_aggregates(paths)
    glob = build_series(agg)                                   # global series: no minimum needed
    reg_all = build_series(agg, MIN_UNITS)
    regional = reg_all[reg_all.entity_id != "GLOBAL"]
    series = pd.concat([glob[glob.entity_id == "GLOBAL"], regional], ignore_index=True)

    report: dict = {"method": __doc__.split("\n\n")[1].replace("\n", " "), "seed": SEED, "bootstrap_replicates": N_BOOT, "block_months": BLOCK,
                    "registered_candidate_range": [month_label(month_index(*CAND_FIRST)), month_label(month_index(*CAND_LAST))],
                    "regional_min_cell_days": MIN_UNITS, "info": info, "deviations": []}
    last = {w: month_label(int(glob[(glob.entity_id == "GLOBAL") & (glob.witness == w)].idx.max())) for w in VIIRS}
    report["last_complete_month"] = last

    # R(t) in the fit years (near 1 by construction)
    fit_years = {}
    for w, (i0, i1) in FIT_PERIODS.items():
        for dn in ("D", "N"):
            s = glob[(glob.entity_id == "GLOBAL") & (glob.witness == w) & (glob.daynight == dn) & glob.idx.between(i0, i1)]
            fit_years[f"{w}_{dn}"] = {"months": len(s), "median_R": float(s.R.median()), "min_R": float(s.R.min()), "max_R": float(s.R.max())}
    report["R_in_fit_years"] = fit_years

    # primary (registered) and confirmations
    results: dict[str, dict] = {}
    fits: dict[str, dict] = {}
    for key, s in series.groupby(["entity_id", "daynight", "witness"]):
        eid, dn, w = key
        after = 12 if w == "NOAA20_VIIRS" else 0
        res = run_series(s, after)
        fits[f"{eid}|{dn}|{w}"] = res
        results[f"{eid}|{dn}|{w}"] = public(res)
    report["results"] = results
    report["deviations"] += ["NOAA-20 series (from 2018-04): candidate range starts 12 months after the first month (2019-04) and ends at the registered 2025-06",
                             "regional series: a month enters only with at least 20 cell-days on each side and both witnesses complete; series with fewer than 60 months are not fitted"]
    primary_key = "|".join(PRIMARY)
    prim = fits[primary_key]
    report["primary"] = results[primary_key]

    # sensitivity, labelled as such
    s = series[(series.entity_id == "GLOBAL") & (series.daynight == "D") & (series.witness == "SNPP_VIIRS")]
    t, y = s.idx.to_numpy(float), np.log(s.R.to_numpy(float))
    cand = candidates(int(t.min()))
    sens = {"null_bootstrap_of_the_break_search": null_pvalue(t, y, cand),
            "block_length": {str(bl): {k: v for k, v in public(run_series(s, 0, N_BOOT, bl)).items()
                                       if k in ("onset_month", "onset_lo_month", "onset_hi_month", "slope_pct_per_year", "detected")} for bl in (3, 12)}}
    keep = ("onset_month", "onset_lo_month", "onset_hi_month", "slope_pct_per_year", "slope_lo_pct_per_year", "slope_hi_pct_per_year", "delta_bic", "detected")
    sens["extended_candidate_range_to_2026-04"] = {
        dn: {k: v for k, v in public(run_series(series[(series.entity_id == "GLOBAL") & (series.daynight == dn) & (series.witness == "SNPP_VIIRS")],
                                                0, N_BOOT, BLOCK, SEED, (2026, 4))).items() if k in keep} for dn in ("D", "N")}
    resid = y - prim["fitted"]
    sens["primary_residual_lag1_autocorrelation"] = float(np.corrcoef(resid[:-1], resid[1:])[0, 1])
    sens["primary_residual_sd_log"] = float(resid.std(ddof=4))
    report["sensitivity"] = sens

    # the proposal
    if prim.get("status") == "ok" and prim["detected"]:
        conf = {k: v for k, v in results.items() if k != primary_key and v.get("status") == "ok"}
        report["proposal"] = {"aqua_cutoff": [int(prim["onset_month"][:4]), int(prim["onset_month"][5:])] if "onset_month" in prim else None,
                              "status": "PROPOSED for the Lead's approval (D-005); not applied anywhere",
                              "onset_month": public(prim)["onset_month"], "interval": [public(prim)["onset_lo_month"], public(prim)["onset_hi_month"]],
                              "confirmed_detected": sorted(k for k, v in conf.items() if v["detected"]),
                              "confirmed_not_detected": sorted(k for k, v in conf.items() if not v["detected"])}
    else:
        report["proposal"] = {"aqua_cutoff": None, "status": "no drift detected by the registered method; no cutoff proposed"}

    # monthly series
    report["series"] = {f"{eid}|{dn}|{w}": {"months": g.idx.map(month_label).tolist(), "R": g.R.round(5).tolist()}
                        for (eid, dn, w), g in series.groupby(["entity_id", "daynight", "witness"])}
    outputs.report.parent.mkdir(parents=True, exist_ok=True)
    outputs.report.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    plot(series, fits, outputs.figure)
    return report


def plot(series: pd.DataFrame, fits: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    g = series[series.entity_id == "GLOBAL"]
    t0 = pd.Timestamp(FIRST_MONTH[0], FIRST_MONTH[1], 1)

    def when(i):
        return t0 + pd.DateOffset(months=int(i))

    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="white")
    ax.set_facecolor("white")
    style = {("SNPP_VIIRS", "D"): ("#d55e00", "o", "S-NPP day"), ("SNPP_VIIRS", "N"): ("#0072b2", "s", "S-NPP night"),
             ("NOAA20_VIIRS", "D"): ("#e69f00", "^", "NOAA-20 day"), ("NOAA20_VIIRS", "N"): ("#009e73", "v", "NOAA-20 night")}
    for (w, dn), (col, mk, lab) in style.items():
        s = g[(g.witness == w) & (g.daynight == dn)]
        ax.plot([when(i) for i in s.idx], s.R, linestyle="none", marker=mk, ms=3.2, color=col, alpha=0.85, label=lab)
    key = "|".join(PRIMARY)
    p = fits[key]
    s = g[(g.witness == PRIMARY[2]) & (g.daynight == PRIMARY[1])]
    if p.get("status") == "ok":
        ax.plot([when(i) for i in s.idx], np.exp(p["fitted"]), color="black", lw=2.0, label="fitted model, S-NPP day (registered)")
        ax.axvspan(when(p["onset_lo"]), when(p["onset_hi"]), color="grey", alpha=0.25, lw=0)
        ax.axvline(when(p["onset"]), color="black", ls="--", lw=1.2)
        pp = public(p)
        txt = (f"onset {pp['onset_month']} (90% interval {pp['onset_lo_month']} to {pp['onset_hi_month']})\n"
               f"slope after onset {pp['slope_pct_per_year']:+.1f}% per year (90% {pp['slope_lo_pct_per_year']:+.1f} to {pp['slope_hi_pct_per_year']:+.1f})\n"
               f"drift detected: {'yes' if p['detected'] else 'no'}")
        ax.text(0.015, 0.03, txt, transform=ax.transAxes, fontsize=8.5, va="bottom", color="black",
                bbox={"facecolor": "white", "edgecolor": "#888888", "alpha": 0.92})
    ax.axhline(1.0, color="#666666", lw=0.8, ls=":")
    ax.axvspan(when(0), when(FIT_PERIODS["SNPP_VIIRS"][1]), color="#cfe8ff", alpha=0.35, lw=0)
    ax.set_xlabel("Month")
    ax.set_ylabel("R = Aqua / converted VIIRS, global (1 = agreement)")
    ax.set_title("Aqua against converted VIIRS, monthly, 2012 to 2026", fontsize=11)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Line2D([0], [0], color="#cfe8ff", lw=8))
    labels.append("S-NPP fit period 2012-2016 (R near 1 by construction)")
    handles.append(Line2D([0], [0], color="#bbbbbb", lw=8))
    labels.append("90% interval of the registered onset (dashed line)")
    ax.legend(handles, labels, loc="upper left", fontsize=8, framealpha=0.92, ncol=2)
    ax.set_ylim(0.38, 1.72)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def summary(rep: dict) -> str:
    p = rep["primary"]
    head = (f"PRIMARY (registered) global day, S-NPP: onset {p['onset_month']} ({p['onset_lo_month']} to {p['onset_hi_month']}), "
            f"slope {p['slope_pct_per_year']:+.2f}%/yr ({p['slope_lo_pct_per_year']:+.2f} to {p['slope_hi_pct_per_year']:+.2f}), "
            f"BIC break {p['bic_break']:.1f} vs flat {p['bic_flat']:.1f}, detected {p['detected']}")
    lines = [head, "confirmation:"]
    for k, v in sorted(rep["results"].items()):
        if v.get("status") != "ok":
            lines.append(f"  {k}: {v['status']} (n={v['n']})")
        else:
            lines.append(f"  {k}: onset {v['onset_month']} ({v['onset_lo_month']}..{v['onset_hi_month']}) slope {v['slope_pct_per_year']:+.1f}%/yr "
                         f"[{v['slope_lo_pct_per_year']:+.1f},{v['slope_hi_pct_per_year']:+.1f}] dBIC {v['delta_bic']:.1f} detected {v['detected']}")
    lines.append("proposal: " + json.dumps(rep["proposal"]))
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary(run()))
