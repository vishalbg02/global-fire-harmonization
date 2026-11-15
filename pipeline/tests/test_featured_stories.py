"""Tests for pipeline/featured_stories.py (T-079). Rules on SYNTHETIC values; the generated files are compared with the real products when present.

    python -m pytest pipeline/tests/test_featured_stories.py -q
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import featured_stories as fs

PRODUCTS_PRESENT = (fs.PRODUCTS / "entity_month.parquet").exists() and (fs.PRODUCTS / "entity_month.parquet").stat().st_size > 10_000


def test_percentages_and_probabilities_follow_the_displayed_precision():
    assert fs.pct_text(264.5) == "265%" and fs.pct_text(99.49) == "99%" and fs.pct_text(None) == "no data"
    assert fs.prob_text(0.995) == "more than 99%" and fs.prob_text(0.9999) == "more than 99%"
    assert fs.prob_text(0.994) == "99%" and fs.prob_text(0.005) == "less than 1%" and fs.prob_text(0.006) == "1%"
    assert fs.prob_text(0.7051) == "71%" and fs.prob_text(None) == "no data"
    assert fs.cd_text(19068.709) == "19,069" and fs.cd_text(0.5) == "1" and fs.cd_text(None) == "no data"


def row(i, verdict, pa, pb, pct):
    return {"entity_id": i, "entity_type": "COUNTRY", "verdict": verdict, "p_above": pa, "p_below": pb, "pct_of_normal": pct}


def test_rank_uses_the_displayed_precision_then_the_distance_from_normal_then_the_id():
    rows = [row("AAA", "ABOVE_NORMAL", 0.9999, 0.0, 150.0),        # equal certainty ("more than 99%")
            row("BBB", "ABOVE_NORMAL", 0.9951, 0.0, 400.0),        # farther from normal: first
            row("CCC", "ABOVE_NORMAL", 0.99, 0.0, 900.0),          # 99%, below the equal group
            row("DDD", "BELOW_NORMAL", 0.0, 0.999, 10.0),          # in the list, but not an above entry
            row("EEE", "WITHIN_NORMAL", 0.0, 0.0, 100.0),          # never ranked
            row("FFF", "ABOVE_NORMAL", 0.9999, 0.0, None)]         # missing pct: last among equals
    order = [r for r in rows if r["verdict"] == "ABOVE_NORMAL"]
    ranks = {r["entity_id"]: fs.rank_of(rows, r["entity_id"], "ABOVE_NORMAL")[0] for r in order}
    assert ranks == {"BBB": 1, "AAA": 2, "FFF": 3, "CCC": 4}
    assert fs.rank_of(rows, "DDD", "BELOW_NORMAL") == (1, 1)
    assert fs.rank_of(rows, "EEE", "WITHIN_NORMAL") is None and fs.rank_of(rows, "ZZZ", "ABOVE_NORMAL") is None


def test_a_caption_contains_only_numbers_that_are_in_the_facts():
    r = {"entity_type": "COUNTRY", "entity_id": "XXX", "entity_name": "Testland", "year": 2020, "month": 3, "verdict": "ABOVE_NORMAL",
         "pct_of_normal": 250.4, "estimate": 5000.2, "ci90_low": 4000.0, "ci90_high": 6000.0, "baseline_median": 2000.0,
         "baseline_p25": 1500.0, "baseline_p75": 2500.0, "p_above": 1.0, "p_below": 0.0, "p_within": 0.0, "reason_codes": [],
         "data_level": "SP", "n_witnesses": 3, "disagreement_scale": 1.0, "raw_combined_cell_days": 1}
    case = {"id": "canada-2023-08", "context": "x", "row": r, "rank": (3, 7), "entities_of_type": 100, "above": 7, "below": 2}
    c = fs.caption(case, {})["caption"]
    assert "250% of normal" in c and "5,000" in c and "4,000 to 6,000" in c and "1,500 to 2,500" in c and "median 2,000" in c
    assert "ranks 3 of 7" in c
    numbers = set(re.findall(r"\d[\d,]*", c))
    assert numbers <= {"250", "5,000", "4,000", "6,000", "1,500", "2,500", "2,000", "3", "7", "90", "99"}  # 99 is the wording "more than 99%"


def test_the_typescript_file_is_plain_data_with_every_case():
    stories = [{"id": "a", "headline": 'He said "hi"', "caption": "line", "notes": [], "facts": {}}]
    src = fs.ts_source(stories)
    assert src.startswith("// Featured stories") and "export const FEATURED_STORIES" in src and '\\"hi\\"' in src


@pytest.mark.skipif(not PRODUCTS_PRESENT, reason="products not available (git lfs pull)")
def test_the_committed_files_equal_what_the_products_give():
    facts = fs.gather()
    stories = fs.build(facts)
    assert fs.TS_FILE.read_text(encoding="utf-8") == fs.ts_source(stories)
    assert fs.DOC_FILE.read_text(encoding="utf-8") == fs.doc_source(facts, stories)


@pytest.mark.skipif(not PRODUCTS_PRESENT, reason="products not available (git lfs pull)")
def test_the_statements_the_lead_asked_for_hold_on_the_real_products():
    facts = fs.gather()
    by = {c["id"]: c for c in facts["cases"]}
    assert by["indonesia-2015-09"]["rank"] == (9, 21) and by["canada-2023-08"]["rank"][0] == 1
    assert by["australia-2019-12"]["row"]["verdict"] == "ABOVE_NORMAL" and round(by["australia-2019-12"]["row"]["pct_of_normal"]) == 328
    assert facts["aus_cells_d031"] == {"ABOVE_NORMAL": 4, "CANNOT_DETERMINE": 105}           # D-031
    assert by["brazil-2019-08"]["row"]["verdict"] == "WITHIN_NORMAL" and by["world-2026-10"]["row"]["verdict"] == "CANNOT_DETERMINE"
    assert by["world-2026-10"]["rank"] is None
