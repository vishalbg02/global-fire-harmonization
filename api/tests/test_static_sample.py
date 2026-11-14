"""The sample that the app's tests decode (T-043): the exporter's compact map files for four
SYNTHETIC fixture months, next to the API's own /api/map answers for the same months. The app test
(app/src/api/staticData.test.ts) checks that decoding the first gives exactly the second; this test
checks that the committed sample is what the exporter writes now.

Rewrite the sample after a change of the layout:
WRITE_STATIC_SAMPLE=1 pytest tests/test_static_sample.py
"""

import json
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fire_api.main import app
from fire_api.static_export import export_static

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures" / "v0.1.0"
SAMPLE = ROOT / "app" / "src" / "api" / "__fixtures__" / "static"
# An outage month (null estimates), a witness-disagreement month, a MIXED month and an NRT month.
MONTHS = ["2004-07", "2013-07", "2026-09", "2026-10"]

pytestmark = pytest.mark.skipif(not FIXTURES.is_dir(), reason="data/fixtures/v0.1.0 not present")


def _build(out: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRODUCTS_DIR", str(FIXTURES))
    full = out / "_full"
    export_static(full, only_months=MONTHS)
    client = TestClient(app)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(full / "cells.json", out / "cells.json")
    (out / "map").mkdir(exist_ok=True)
    (out / "api-map").mkdir(exist_ok=True)
    for label in MONTHS:
        year, month = label.split("-")
        shutil.copy(full / "map" / f"{label}.json", out / "map" / f"{label}.json")
        api = client.get(f"/api/map?year={year}&month={int(month)}&layer=raw").json()
        (out / "api-map" / f"{label}.json").write_text(
            json.dumps(api, separators=(",", ":")), encoding="utf-8"
        )
    shutil.rmtree(full)


def test_the_committed_sample_is_what_the_exporter_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.environ.get("WRITE_STATIC_SAMPLE") == "1":
        shutil.rmtree(SAMPLE, ignore_errors=True)
        _build(SAMPLE, monkeypatch)
    fresh = tmp_path / "sample"
    _build(fresh, monkeypatch)
    names = sorted(p.relative_to(fresh).as_posix() for p in fresh.rglob("*.json"))
    assert names == sorted(p.relative_to(SAMPLE).as_posix() for p in SAMPLE.rglob("*.json"))
    for name in names:
        assert json.loads((fresh / name).read_text()) == json.loads((SAMPLE / name).read_text()), (
            name
        )


def test_the_sample_is_labelled_synthetic() -> None:
    text = " ".join((SAMPLE / "README.md").read_text(encoding="utf-8").split())
    assert text.startswith("# SYNTHETIC test sample")
    assert "not NASA observations" in text
