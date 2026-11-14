"""Tests for the FIRMS country name -> ISO3 / continent mapping (T-009).

    python -m pytest pipeline/tests/test_country_mapping.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import country_mapping as cm

ROWS = cm.read_map()
BY_NAME = {r["firms_name"]: r for r in ROWS}


def ne_row(name, adm0, iso, continent, **extra):
    base = {"NAME": name, "NAME_LONG": name, "NAME_EN": name, "BRK_NAME": name, "ADMIN": name, "FORMAL_EN": "",
            "SOVEREIGNT": name, "ADM0_A3": adm0, "ISO_A3": iso, "ISO_A3_EH": iso, "CONTINENT": continent}
    base.update(extra)
    return base


# ----------------------------------------------------------------- the committed table
def test_table_is_structurally_valid():
    assert cm.validate_rows(ROWS) == []
    assert len(ROWS) == 238
    assert list(ROWS[0].keys()) == cm.COLUMNS


def test_every_iso3_is_unique_and_continents_are_known():
    assert len({r["iso3"] for r in ROWS}) == len(ROWS)
    assert {r["continent"] for r in ROWS} <= cm.CONTINENTS
    assert BY_NAME["Antarctica"]["continent"] == "AN"


@pytest.mark.parametrize("name, iso3, continent", [
    ("Cote d Ivoire", "CIV", "AF"),
    ("Republic of Congo", "COG", "AF"),
    ("Democratic Republic of the Congo", "COD", "AF"),
    ("Dem Rep Korea", "PRK", "AS"),
    ("Republic of Korea", "KOR", "AS"),
    ("Swaziland", "SWZ", "AF"),
    ("Macedonia Former Yugoslav Republic of", "MKD", "EU"),
    ("Kosovo", "XKX", "EU"),
    ("Russian Federation", "RUS", "EU"),
    ("Turkey", "TUR", "AS"),
    ("Brazil", "BRA", "SA"),
    ("Indonesia", "IDN", "AS"),
    ("Australia", "AUS", "OC"),
    ("United States", "USA", "NA"),
    ("United States Virgin Islands", "VIR", "NA"),
    ("The Gambia", "GMB", "AF"),
    ("Lao PDR", "LAO", "AS"),
    ("Palestine", "PSE", "AS"),
    ("Saint-Martin", "MAF", "NA"),
    ("Sint Maarten", "SXM", "NA"),
    ("Mauritius", "MUS", "AF"),
])
def test_known_cases(name, iso3, continent):
    assert (BY_NAME[name]["iso3"], BY_NAME[name]["continent"]) == (iso3, continent)


def test_territories_are_not_mapped_to_their_sovereign():
    assert BY_NAME["Greenland"]["iso3"] == "GRL" and BY_NAME["Denmark"]["iso3"] == "DNK"
    assert BY_NAME["Hong Kong"]["iso3"] == "HKG" and BY_NAME["China"]["iso3"] == "CHN"
    assert BY_NAME["Norfolk Island"]["iso3"] == "NFK" and BY_NAME["Australia"]["iso3"] == "AUS"


def test_manual_rows_have_notes_and_approved_ones_say_so():
    manual = [r for r in ROWS if r["method"] == "MANUAL"]
    assert len(manual) == len(cm.MANUAL) and all(r["note"] for r in manual)
    assert "approved by the Lead 2026-11-14" in BY_NAME["Kosovo"]["note"]


# ------------------------------------------------------------- builder logic (synthetic reference)
def test_exact_match_and_normalization():
    ne = [ne_row("Côte d'Ivoire", "CIV", "CIV", "Africa"), ne_row("Guinea-Bissau", "GNB", "GNB", "Africa")]
    rows, problems = cm.build_rows(["Guinea Bissau"], ne)
    assert problems == [] and rows[0]["iso3"] == "GNB" and rows[0]["method"] == "NATURAL_EARTH"


def test_unmatched_name_is_reported_not_guessed():
    rows, problems = cm.build_rows(["Atlantis"], [ne_row("Chile", "CHL", "CHL", "South America")])
    assert rows == [] and any("Atlantis" in p and "no match" in p for p in problems)


def test_conflict_is_reported():
    ne = [ne_row("Twin", "AAA", "AAA", "Asia"), ne_row("Twin", "BBB", "BBB", "Asia")]
    rows, problems = cm.build_rows(["Twin"], ne)
    assert rows == [] and any("conflict" in p for p in problems)


def test_sovereignty_is_not_used_for_matching():
    ne = [ne_row("Islandia", "ISL", "ISL", "Europe", SOVEREIGNT="Denmark"),
          ne_row("Denmark", "DNK", "DNK", "Europe")]
    rows, problems = cm.build_rows(["Denmark"], ne)
    assert problems == [] and rows[0]["iso3"] == "DNK"


def test_undefined_code_or_ocean_continent_must_be_manual():
    ne = [ne_row("Nocode", "NOC", "-99", "Europe", ISO_A3_EH="-99"), ne_row("Seaville", "SEA", "SEA", "Seven seas (open ocean)")]
    rows, problems = cm.build_rows(["Nocode", "Seaville"], ne)
    assert rows == [] and len(problems) == 2


def test_eh_code_is_used_when_iso_a3_is_undefined():
    ne = [ne_row("Frostland", "FRO", "-99", "Europe", ISO_A3_EH="FRL")]
    rows, problems = cm.build_rows(["Frostland"], ne)
    assert problems == [] and rows[0]["iso3"] == "FRL"


def test_validate_catches_bad_rows():
    bad = [
        {"firms_name": "A", "iso3": "ab", "continent": "AF", "method": "MANUAL", "note": ""},
        {"firms_name": "B", "iso3": "XYZ", "continent": "ZZ", "method": "OTHER", "note": "x"},
        {"firms_name": "C", "iso3": "XYZ", "continent": "AF", "method": "MANUAL", "note": "x"},
        {"firms_name": "C", "iso3": "QQQ", "continent": "AF", "method": "MANUAL", "note": "x"},
    ]
    text = " | ".join(cm.validate_rows(bad))
    for part in ("bad iso3", "bad continent", "bad method", "without a note", "used by both", "duplicate"):
        assert part in text


def test_check_reports_unmapped_and_extra_names():
    rows = [{"firms_name": "Chile", "iso3": "CHL", "continent": "SA", "method": "MANUAL", "note": "x"}]
    problems = cm.check(["Chile", "Peru"], rows)
    assert problems == ["unmapped name in the data: Peru"]
    assert cm.check([], rows) == ["table name not in the data: Chile"]


# ------------------------------------------------------------ 100% of the real data (needs local data)
@pytest.mark.skipif(not (cm.DETECTIONS / "row_counts.tsv").exists(), reason="normalized detections not on this machine")
def test_every_country_in_the_detections_is_mapped():
    names = cm.names_in_detections()
    assert len(names) == 238
    assert cm.check(names, ROWS) == []
