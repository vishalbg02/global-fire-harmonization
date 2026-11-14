"""Custom areas against the real contract products in data/products/ (Git LFS, T-035).

Skipped with a reason when the files are only LFS pointer files (`git lfs pull` fetches them).
The import test needs no products."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fire_api import custom, products
from fire_api.main import app
from fire_api.models import EntityMonth

REAL = Path(__file__).resolve().parents[2] / "data" / "products"
NEEDED = ("cells.parquet", "cell_month_witness.parquet", "calibration.parquet")
# Roughly Uruguay: a country-sized box.
URUGUAY = [-58.5, -35.0, -53.0, -30.0]


def _is_real(name: str) -> bool:
    path = REAL / name
    return path.is_file() and path.stat().st_size > 1024  # an LFS pointer is about 130 bytes


needs_real = pytest.mark.skipif(
    not all(_is_real(n) for n in NEEDED),
    reason="data/products/*.parquet are Git LFS pointers: run `git lfs pull`",
)


@pytest.fixture
def real_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PRODUCTS_DIR", str(REAL))
    return TestClient(app)


def test_harmonize_area_imports_from_any_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert callable(custom.load_harmonize_area())
    assert str(custom.PIPELINE_DIR) in sys.path


@needs_real
def test_country_sized_box_returns_the_real_series(
    real_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    west, south, east, north = URUGUAY
    n_cells = len(products.cells_with_centre_in(west, south, east, north))
    assert n_cells > 0
    response = real_client.post("/api/series/custom", json={"bbox": URUGUAY})
    assert response.status_code == 200
    records = [EntityMonth.model_validate(r) for r in response.json()]
    assert len(records) > 200  # monthly, 2002-07 onwards
    assert {r.entity_type for r in records} == {"CUSTOM"}
    assert {r.n_cells for r in records} == {n_cells}
    assert any(r.estimate is not None for r in records)
    # Baseline, probabilities and verdicts belong to T-014: null and CANNOT_DETERMINE.
    assert all(r.baseline_median is None and r.p_above is None for r in records)
    assert {r.verdict for r in records} == {"CANNOT_DETERMINE"}
    assert all(r.method_version.startswith("0.1.0-combined") for r in records)
    assert [(r.year, r.month) for r in records] == sorted((r.year, r.month) for r in records)


@needs_real
def test_the_api_writes_nothing_into_the_repository(real_client: TestClient) -> None:
    root = REAL.parents[1]
    before = {p for p in (root / "data").rglob("*") if p.is_file()}
    real_client.post("/api/series/custom", json={"bbox": [-58.0, -34.0, -57.0, -33.0]})
    after = {p for p in (root / "data").rglob("*") if p.is_file()}
    assert after == before


@needs_real
def test_export_csv_of_a_real_box(real_client: TestClient) -> None:
    response = real_client.get("/api/export.csv", params={"bbox": "-58,-34,-57,-33"})
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment; filename=")
    assert "SYNTHETIC" not in response.headers["content-disposition"]
    assert "# data_status: REAL" in response.text
