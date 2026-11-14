"""Tests for the SYNTHETIC fixtures and the contract checker (T-010).

    python -m pytest pipeline/tests -q
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import contract_check as cc
import make_fixtures as mf

FIXTURES = mf.DEFAULT_OUT
NAMES = ["cells", "cell_month_witness", "cell_month_harmonized", "entity_month", "calibration"]


@pytest.fixture(scope="module")
def harm() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "cell_month_harmonized.parquet")


@pytest.fixture(scope="module")
def cmw() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "cell_month_witness.parquet")


@pytest.fixture(scope="module")
def cells() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "cells.parquet")


@pytest.fixture(scope="module")
def entity() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "entity_month.parquet")


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("regen")
    mf.generate(out)
    return out


# ---------------------------------------------------------------- contract conformance
def test_committed_fixtures_conform_to_the_contract():
    assert cc.check_dir(FIXTURES) == []


def test_every_product_is_present():
    for n in NAMES:
        assert (FIXTURES / f"{n}.parquet").exists()
    for n in ("metadata.json", "validation_results.json", "README.md"):
        assert (FIXTURES / n).exists()


def test_synthetic_labelling():
    meta = json.loads((FIXTURES / "metadata.json").read_text(encoding="utf-8"))
    val = json.loads((FIXTURES / "validation_results.json").read_text(encoding="utf-8"))
    assert meta["synthetic"] is True and val["synthetic"] is True
    assert "SYNTHETIC" in meta["citation"]
    assert all(t["test_id"].startswith("SYNTHETIC-") for t in val["tests"])
    assert all(t["notes"] == "SYNTHETIC EXAMPLE — not a result" for t in val["tests"])
    assert {t["status"] for t in val["tests"]} == cc.ENUMS["test_status"]
    assert "SYNTHETIC" in (FIXTURES / "README.md").read_text(encoding="utf-8")


def test_total_size_under_5_mb():
    assert sum(f.stat().st_size for f in FIXTURES.iterdir()) < 5_000_000


def test_fixtures_are_reproducible(regenerated):
    for n in NAMES:
        a = pd.read_parquet(FIXTURES / f"{n}.parquet")
        b = pd.read_parquet(regenerated / f"{n}.parquet")
        pd.testing.assert_frame_equal(a, b)
    for n in ("metadata.json", "validation_results.json", "README.md"):
        assert (FIXTURES / n).read_text(encoding="utf-8") == (regenerated / n).read_text(encoding="utf-8")


# -------------------------------------------------------------------------- coverage
def test_grid_countries_and_continents(cells):
    assert 100 <= len(cells) <= 500
    assert cells.cell_id.str.startswith("g050_").all()
    assert 4 <= cells.country_iso3.nunique() <= 8
    assert cells.continent.nunique() >= 3


def test_months_and_witness_windows(cmw, harm):
    ym = harm.year * 100 + harm.month
    assert ym.min() == 200207 and ym.max() == 202611
    first = cmw.assign(ym=cmw.year * 100 + cmw.month).groupby("witness").ym.agg(["min", "max"])
    assert first.loc["AQUA_MODIS", "min"] == 200207
    assert first.loc["SNPP_VIIRS", "min"] == 201201
    assert first.loc["NOAA20_VIIRS", "min"] == 201804
    assert (first["max"] == 202611).all()


def test_terra_is_raw_only_and_aqua_leaves_after_drift_cutoff(harm):
    used = harm.witnesses_used.explode().dropna()
    assert "TERRA_MODIS" not in set(used)
    late = harm[(harm.year * 100 + harm.month) >= 202201]
    assert not late.witnesses_used.map(lambda w: "AQUA_MODIS" in w).any()
    assert late.reason_codes.map(lambda r: "AQUA_DRIFT_ERA" in r).all()


def test_entities(entity):
    assert {"COUNTRY", "CONTINENT", "GLOBAL"} <= set(entity.entity_type)
    assert entity[entity.entity_type == "GLOBAL"].entity_id.eq("GLOBAL").all()
    assert set(entity[entity.entity_type == "CONTINENT"].entity_id) <= {"AF", "AS", "EU", "NA", "OC", "SA"}


def test_entity_sums_match_their_cells(entity, harm, cells):
    row = entity[(entity.entity_id == "PRT") & (entity.year == 2019) & (entity.month == 8)].iloc[0]
    ids = set(cells[cells.country_iso3 == "PRT"].cell_id)
    sub = harm[harm.cell_id.isin(ids) & (harm.year == 2019) & (harm.month == 8)]
    assert row.n_cells == len(ids)
    assert row.estimate == pytest.approx(round(sub.estimate.sum(), 3))
    assert row.raw_combined_cell_days == sub.raw_combined_cell_days.sum()


# -------------------------------------------------------------------------- edge cases
def test_every_verdict_and_reason_code_present(harm):
    assert set(harm.verdict) == cc.ENUMS["verdict"]
    assert set(harm.reason_codes.explode().dropna()) == cc.ENUMS["reason_code"]


def test_outage_month(cmw, harm):
    s = cmw[(cmw.witness == "SNPP_VIIRS") & (cmw.year == 2016) & (cmw.month == 2)]
    assert (s.days_available == 21).all() and (s.days_in_month == 29).all()
    feb = harm[(harm.year == 2016) & (harm.month == 2)]
    assert feb.reason_codes.map(lambda r: "OUTAGE" in r).all()


def test_last_two_months_are_nrt_and_provisional(harm):
    last = harm[(harm.year == 2026) & (harm.month >= 10)]
    assert (last.data_level == "NRT").all()
    meta = json.loads((FIXTURES / "metadata.json").read_text(encoding="utf-8"))
    assert {"2026-10", "2026-11"} <= set(meta["provisional_months"])
    assert last.reason_codes.map(lambda r: "PROVISIONAL_NRT" in r).all()


def test_zero_baseline_median_gives_null_pct_of_normal(harm):
    z = harm[harm.baseline_median == 0]
    assert len(z) > 0 and z.pct_of_normal.isna().all()
    assert (z.estimate > 0).any()  # a real fire in a normally fire-free cell is included


def test_disagreement_scale_above_one(harm):
    assert (harm.disagreement_scale > 1).any()
    assert harm.disagreement_scale.dropna().ge(1).all()


def test_no_detected_activity_is_never_below_normal(harm):
    nd = harm[harm.verdict == "NO_DETECTED_ACTIVITY"]
    assert len(nd) > 0 and (nd.raw_combined_cell_days == 0).all()
    zero_cells = set(nd.cell_id)
    quiet = harm[harm.cell_id.isin(zero_cells) & (harm.raw_combined_cell_days == 0)]
    assert not (quiet.verdict == "BELOW_NORMAL").any()


def test_null_estimate_rows(harm):
    n = harm[harm.estimate.isna()]
    assert len(n) > 0
    assert (n.verdict == "CANNOT_DETERMINE").all() and (n.n_witnesses == 0).all()
    assert n.ci90_low.isna().all() and n.sd.isna().all()


def test_values_are_never_filled_with_zero_for_missing(harm):
    # a null estimate stays null; it is never written as 0
    assert harm.loc[harm.n_witnesses == 0, "estimate"].isna().all()
    assert (harm.loc[harm.estimate == 0, "n_witnesses"] > 0).all()


# --------------------------------------------------- the checker really catches problems
def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "copy"
    shutil.copytree(FIXTURES, dst)
    return dst


def _edit_parquet(folder: Path, name: str, fn) -> None:
    df = pd.read_parquet(folder / f"{name}.parquet")
    fn(df)
    df.to_parquet(folder / f"{name}.parquet", index=False)


def test_checker_flags_bad_enum(tmp_path):
    d = _copy(tmp_path)
    _edit_parquet(d, "cell_month_harmonized", lambda df: df.__setitem__("verdict", df.verdict.replace({"WITHIN_NORMAL": "FINE"})))
    assert any("verdict" in e for e in cc.check_dir(d))


def test_checker_flags_null_in_required_field(tmp_path):
    d = _copy(tmp_path)

    def f(df):
        df.loc[0, "cell_id"] = None

    _edit_parquet(d, "cell_month_harmonized", f)
    assert any("non-nullable" in e or "cell_id" in e for e in cc.check_dir(d))


def test_checker_flags_estimate_without_witness(tmp_path):
    d = _copy(tmp_path)

    def f(df):
        i = df.index[df.estimate.isna()][0]
        df.loc[i, "estimate"] = 0.0

    _edit_parquet(d, "cell_month_harmonized", f)
    assert any("estimate must be null" in e for e in cc.check_dir(d))


def test_checker_flags_probability_out_of_range(tmp_path):
    d = _copy(tmp_path)

    def f(df):
        i = df.index[df.p_above.notna()][0]
        df.loc[i, "p_above"] = 1.5

    _edit_parquet(d, "cell_month_harmonized", f)
    assert any("probability" in e for e in cc.check_dir(d))


def test_checker_flags_pct_of_normal_with_zero_median(tmp_path):
    d = _copy(tmp_path)

    def f(df):
        i = df.index[df.baseline_median == 0][0]
        df.loc[i, "pct_of_normal"] = 100.0

    _edit_parquet(d, "cell_month_harmonized", f)
    assert any("pct_of_normal" in e for e in cc.check_dir(d))


def test_checker_flags_missing_field_and_wrong_type(tmp_path):
    d = _copy(tmp_path)
    _edit_parquet(d, "cells", lambda df: df.drop(columns=["area_km2"], inplace=True))
    _edit_parquet(d, "calibration", lambda df: df.__setitem__("ratio", df.ratio.astype(str)))
    errs = cc.check_dir(d)
    assert any("area_km2" in e for e in errs) and any("calibration.ratio" in e for e in errs)


def test_checker_flags_duplicate_keys(tmp_path):
    d = _copy(tmp_path)
    _edit_parquet(d, "cells", lambda df: df.__setitem__("cell_id", df.cell_id.iloc[0]))
    assert any("duplicate" in e for e in cc.check_dir(d))


def test_checker_flags_non_synthetic_labels_and_missing_file(tmp_path):
    d = _copy(tmp_path)
    meta = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    meta["synthetic"] = False
    (d / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    val = json.loads((d / "validation_results.json").read_text(encoding="utf-8"))
    val["tests"][0]["test_id"] = "A1-REAL"
    (d / "validation_results.json").write_text(json.dumps(val), encoding="utf-8")
    (d / "calibration.parquet").unlink()
    errs = cc.check_dir(d)
    assert any("synthetic must be true" in e for e in errs)
    assert any("SYNTHETIC-" in e for e in errs)
    assert any("calibration" in e and "missing" in e for e in errs)
