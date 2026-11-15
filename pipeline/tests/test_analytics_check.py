"""T-083: the analytics panel's numbers equal an independent recomputation from the real products (skipped without them or without Node 22.6+)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analytics_check as ac


def node_ok() -> bool:
    node = shutil.which("node")
    if node is None:
        return False
    v = subprocess.run([node, "--version"], capture_output=True, text=True, check=False).stdout.strip().lstrip("v").split(".")
    return (int(v[0]), int(v[1])) >= (22, 6)


PRODUCTS_OK = all((ac.PRODUCTS / f).exists() and (ac.PRODUCTS / f).stat().st_size > 10_000 for f in ("entity_month.parquet", "cells.parquet", "cell_month_harmonized.parquet"))
needs_all = pytest.mark.skipif(not (PRODUCTS_OK and node_ok()), reason="real products (git lfs pull) and Node 22.6+ are needed")


def test_close_compares_numbers_and_nulls():
    assert ac.close(1.0, 1.0 + 1e-12) and not ac.close(1.0, 1.1) and ac.close(None, None) and not ac.close(None, 0.0)


def test_nan_becomes_none():
    assert ac.nan_to_none(float("nan")) is None and ac.nan_to_none(2.0) == 2.0


@needs_all
def test_the_panels_functions_agree_with_the_products_for_two_areas():
    report = ac.compare()
    assert report["mismatches"] == []
    assert set(report["areas"]) == {"COUNTRY:IDN", "GLOBAL:GLOBAL"}
    assert report["areas"]["COUNTRY:IDN"]["rank"]["rank"] >= 1
