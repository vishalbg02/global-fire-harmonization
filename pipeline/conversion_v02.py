"""Method 0.2: an activity-dependent factor on the T-011 conversion (T-020c, D-030 PROPOSED).

    ratio_v02(stratum, witness, daynight, season, month) = ratio_v01(stratum, witness, daynight, season) x f(witness, daynight, bin)

`bin` is the activity bin of the stratum-month, measured from the witness's own counts and converted to the Aqua-equivalent scale:

    x = ratio_v01 x (witness cell-days of the whole stratum-month) / (analysis cells of the stratum)      [cell-days per cell and month]

in the eight fixed bins of T-020b (`saturation.EDGES`). The factor is one global value per witness, day/night and bin, fitted on the
calibration fit periods only (S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12, complete months, exactly as T-011):

    f(bin) = sum(Aqua) / sum(ratio_v01 x witness)      over the stratum-months of the bin with witness cell-days above 0

Binning on the witness's own count makes f the conditional expectation of Aqua given the witness, which is what a prediction needs.
Bins with fewer than `MIN_UNITS` units take the factor (and its error) of the nearest bin with enough units: no extrapolation.
`f_sd` is the standard deviation of f over `BOOT` resamples of whole fit months. The design was fixed before any fit
(docs/task-prompts/T-020c-v02-conversion.md section 9).

    python pipeline/conversion_v02.py        # writes data/interim/v02/activity_factors.parquet and activity_factors_report.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibration as cal
import saturation as sat

ROOT = Path(__file__).resolve().parents[1]
EDGES = sat.EDGES
MIN_UNITS = sat.MIN_UNITS
BOOT = sat.BOOT
SEED = sat.SEED
METHOD_VERSION_V02 = "0.2.0-activity-factor"
V02_DIR = ROOT / "data" / "interim" / "v02"


def fit_bins(month: np.ndarray, x: np.ndarray, aqua: np.ndarray, conv: np.ndarray, n_months: int, boot: int = BOOT, seed: int = SEED,
             min_units: int = MIN_UNITS, edges: np.ndarray = EDGES) -> dict:
    """The factor per bin from units given as arrays (month index, activity x, Aqua cell-days, converted witness cell-days).

    Only units with `conv` above 0 enter. Returns arrays over the bins: f, f_sd, units, and `filled` (True where the value was
    copied from the nearest bin that has `min_units` units).
    """
    n_bins = len(edges) - 1
    keep = conv > 0
    month, x, aqua, conv = month[keep], x[keep], aqua[keep], conv[keep]
    bins = sat.bin_index(x, edges)
    sa, sc, n = sat.month_bin_sums(month, bins, aqua, conv, n_months, n_bins)
    tot_a, tot_c, tot_n = sa.sum(0), sc.sum(0), n.sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        f = np.where(tot_c > 0, tot_a / tot_c, np.nan)
    rng = np.random.default_rng(seed)
    counts = np.zeros((boot, n_months))
    for b in range(boot):
        counts[b] = np.bincount(rng.integers(0, n_months, n_months), minlength=n_months)
    ba, bc = counts @ sa, counts @ sc
    with np.errstate(divide="ignore", invalid="ignore"):
        rep = np.where(bc > 0, ba / bc, np.nan)
    ok = np.isfinite(rep).sum(axis=0) >= 20
    f_sd = np.full(n_bins, np.nan)
    for j in np.where(ok)[0]:
        f_sd[j] = float(np.nanstd(rep[:, j], ddof=1))
    eligible = (tot_n >= min_units) & np.isfinite(f) & np.isfinite(f_sd)
    filled = np.zeros(n_bins, dtype=bool)
    f_out, sd_out = f.copy(), f_sd.copy()
    if eligible.any():
        idx = np.where(eligible)[0]
        for j in range(n_bins):
            if not eligible[j]:
                near = idx[np.argmin(np.abs(idx - j))]       # the nearest eligible bin; a tie goes to the lower one (argmin takes the first)
                f_out[j], sd_out[j], filled[j] = f[near], f_sd[near], True
    return {"f": f_out, "f_sd": sd_out, "f_raw": f, "units": tot_n, "filled": filled, "aqua": tot_a, "converted": tot_c}


def factor_table(per: dict[tuple[str, str], dict], edges: np.ndarray = EDGES) -> pd.DataFrame:
    """The factors as a DataFrame (witness, daynight, bin, lo, hi, f, f_sd, units, filled) that `harmonize.aggregate(factors=...)` takes."""
    rows = []
    for (witness, dn), r in per.items():
        for b in range(len(edges) - 1):
            rows.append({"witness": witness, "daynight": dn, "bin": b, "lo": float(edges[b]),
                         "hi": float(edges[b + 1]) if np.isfinite(edges[b + 1]) else float("inf"),
                         "f": float(r["f"][b]), "f_sd": float(r["f_sd"][b]), "units": int(r["units"][b]), "filled": bool(r["filled"][b])})
    return pd.DataFrame(rows)


def season_of_month(months: list[tuple[int, int]], idx: np.ndarray) -> np.ndarray:
    return np.array([cal.SEASON_OF[months[i][1]] for i in idx])


def unit_arrays(u: dict, witness: str, dn: str, ratios: pd.DataFrame) -> dict:
    """Month index, activity x, Aqua and converted witness cell-days of the units of one witness and day/night.

    `ratios`: calibration.parquet rows (stratum_id, witness, daynight, season, ratio). u: one entry of `saturation.load_units`.
    """
    df = pd.DataFrame({"stratum_id": u["stratum"], "season": season_of_month(u["months"], u["month"])})
    r = ratios[(ratios.witness == witness) & (ratios.daynight == dn)][["stratum_id", "season", "ratio"]]
    df = df.merge(r, on=["stratum_id", "season"], how="left")
    if df["ratio"].isna().any():
        raise ValueError(f"{int(df['ratio'].isna().sum())} fit units have no calibration ratio ({witness} {dn})")
    ratio = df["ratio"].to_numpy(float)
    conv = ratio * u["w"]
    return {"month": u["month"], "x": conv / u["cells"], "aqua": u["a"], "conv": conv}


def fit_factors(paths: cal.Paths | None = None, boot: int = BOOT) -> tuple[pd.DataFrame, dict]:
    """Fit the activity factors on the fit periods of S-NPP and NOAA-20 and return (table, report)."""
    paths = paths or cal.Paths()
    units = sat.load_units(paths)
    ratios = pd.read_parquet(paths.products / "calibration.parquet", columns=["stratum_id", "witness", "daynight", "season", "ratio"])
    per: dict = {}
    for (witness, dn), u in units.items():
        arr = unit_arrays(u, witness, dn, ratios)
        per[(witness, dn)] = fit_bins(arr["month"], arr["x"], arr["aqua"], arr["conv"], len(u["months"]), boot)
    table = factor_table(per)
    report = {"method_version": METHOD_VERSION_V02, "bin_edges": [float(e) if np.isfinite(e) else None for e in EDGES], "min_units": MIN_UNITS,
              "bootstrap": boot, "seed": SEED, "fit_periods": {w: list(cal.FITS[w]) for w in sat.WITNESSES},
              "months": {w: len(units[(w, "D")]["months"]) for w in sat.WITNESSES}, "factors": table.to_dict(orient="records")}
    return table, report


def load_factors(directory: Path = V02_DIR) -> pd.DataFrame:
    return pd.read_parquet(directory / "activity_factors.parquet")


def main() -> int:
    table, report = fit_factors()
    V02_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(V02_DIR / "activity_factors.parquet", index=False)
    (V02_DIR / "activity_factors_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(table.assign(f=table.f.round(3), f_sd=table.f_sd.round(4))[["witness", "daynight", "lo", "units", "f", "f_sd", "filled"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
