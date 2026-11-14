"""Contract 0.1.1: the NOT_HARMONIZED reason code and the 0.1.1 version string (T-039).

All data are SYNTHETIC test products built here."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fire_api.main import app
from fire_api.models import Metadata, ReasonCode
from tests.conftest import METADATA, build_products


def test_not_harmonized_is_a_known_reason_code() -> None:
    assert ReasonCode("NOT_HARMONIZED") is ReasonCode.NOT_HARMONIZED


def test_meta_with_contract_version_0_1_1_is_served(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_products(tmp_path)
    meta = {**METADATA, "contract_version": "0.1.1", "method_version": "0.1.0-raw-only"}
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
    body = TestClient(app).get("/api/meta").json()
    Metadata.model_validate(body)
    assert body["contract_version"] == "0.1.1"
