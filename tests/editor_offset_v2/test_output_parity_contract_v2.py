from __future__ import annotations

import json
from pathlib import Path

import pytest

from editor_offset_v2.domain.output_parity_contract import (
    CANVAS_GEOMETRY_TOLERANCE_MM,
    DERIVED_PREVIEW_MAX_CHANGED_RATIO,
    DERIVED_PREVIEW_MAX_MEAN_CHANNEL_DELTA,
    OUTPUT_PARITY_SCHEMA_VERSION,
    PAGE_ORDER_EXACT,
    PDF_BOX_TOLERANCE_MM,
    PREVIEW_PDF_MAX_CHANGED_RATIO,
    PREVIEW_PDF_MAX_MEAN_CHANNEL_DELTA,
    ROTATION_AND_FLIP_EXACT,
)


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "editor_offset_v2"


def test_output_parity_contract_is_explicit_and_bounded() -> None:
    assert OUTPUT_PARITY_SCHEMA_VERSION == 1
    assert PDF_BOX_TOLERANCE_MM == pytest.approx(0.01)
    assert CANVAS_GEOMETRY_TOLERANCE_MM == pytest.approx(0.01)
    assert PAGE_ORDER_EXACT is True
    assert ROTATION_AND_FLIP_EXACT is True
    assert 0 < PREVIEW_PDF_MAX_CHANGED_RATIO < 1
    assert 0 < DERIVED_PREVIEW_MAX_CHANGED_RATIO < 1
    assert 0 < PREVIEW_PDF_MAX_MEAN_CHANNEL_DELTA < 255
    assert 0 < DERIVED_PREVIEW_MAX_MEAN_CHANNEL_DELTA < 255


def test_fixture_manifest_contains_the_full_output_risk_matrix() -> None:
    manifest = json.loads((FIXTURE_ROOT / "pdf_fixture_manifest.json").read_text(encoding="utf-8"))
    files = {case["file"] for case in manifest["cases"]}
    assert {
        "boxes-offset.pdf",
        "boxes-missing.pdf",
        "multipage-rotations.pdf",
        "marks-clipping.pdf",
        "mirror-bleed-candidate.pdf",
        "front-back-flip.pdf",
    } <= files
    multipage = next(case for case in manifest["cases"] if case["file"] == "multipage-rotations.pdf")
    assert [page["rotation"] for page in multipage["pages"]] == [0, 90, 180]
    mirror = next(case for case in manifest["cases"] if case["file"] == "mirror-bleed-candidate.pdf")
    assert mirror["pages"][0]["bleed_policy"] == "mirror_explicit_option"


def test_front_back_fixture_declares_exact_flip_and_transform_expectations() -> None:
    manifest = json.loads((FIXTURE_ROOT / "pdf_fixture_manifest.json").read_text(encoding="utf-8"))
    case = next(case for case in manifest["cases"] if case["file"] == "front-back-flip.pdf")
    front, back = case["pages"]
    assert front["face"] == "front" and front["flip"] == "none"
    assert back["face"] == "back" and back["flip"] == "horizontal"
    assert back["content_transform"] == {
        "rotation_deg": 90,
        "offset_mm": {"x": 1.5, "y": -2.0},
        "clip_to": "trim",
    }
