from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from editor_offset_v2.infrastructure.pdf_inspector import inspect_pdf
from editor_offset_v2.domain.output_parity_contract import PDF_BOX_TOLERANCE_MM


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "editor_offset_v2"
MANIFEST_PATH = FIXTURE_ROOT / "pdf_fixture_manifest.json"
BOX_TOLERANCE_MM = PDF_BOX_TOLERANCE_MM


def _assert_box(actual: dict[str, float] | None, expected: dict[str, float] | None) -> None:
    if expected is None:
        assert actual is None
        return
    assert actual is not None
    for key in ("x", "y", "width", "height"):
        assert actual[key] == pytest.approx(expected[key], abs=BOX_TOLERANCE_MM)


def _expected_suggested_box(page: dict[str, object]) -> str:
    boxes = page["boxes"]
    if boxes["trim"] is not None:
        return "trim"
    if boxes["crop"] is not None:
        return "crop"
    return "media"


def test_canonical_pdf_fixtures_match_inspector_contract() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["unit"] == "mm"
    assert len(manifest["cases"]) >= 6

    for case in manifest["cases"]:
        fixture_path = FIXTURE_ROOT / case["file"]
        assert fixture_path.is_file(), case["file"]
        inspection = inspect_pdf(fixture_path)
        expected_pages = case["pages"]
        assert inspection.page_count == len(expected_pages)

        for inspected, expected in zip(inspection.pages, expected_pages, strict=True):
            assert inspected.intrinsic_rotation_deg == expected["rotation"]
            expected_boxes = expected["boxes"]
            actual_boxes = inspected.boxes_as_layout()
            for name in ("media", "crop", "trim", "bleed"):
                _assert_box(actual_boxes[name], expected_boxes[name])

            expected_suggested = _expected_suggested_box(expected)
            assert inspected.suggested_box == expected_suggested
            suggested = expected_boxes[expected_suggested]
            expected_size = (suggested["width"], suggested["height"])
            if expected["rotation"] in (90, 270):
                expected_size = (expected_size[1], expected_size[0])
            assert inspected.suggested_size_mm == pytest.approx(expected_size, abs=BOX_TOLERANCE_MM)


def test_missing_bleed_and_mirror_candidate_are_never_synthesized() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for case in manifest["cases"]:
        for expected in case["pages"]:
            if expected.get("bleed_policy") != "mirror_explicit_option":
                continue
            page = inspect_pdf(FIXTURE_ROOT / case["file"]).pages[0]
            assert expected["requires_future_stage"] is True
            assert page.trim is None
            assert page.bleed is None
            assert page.suggested_box == "crop"


def test_marks_and_clipping_fixture_contains_asymmetric_renderable_artwork() -> None:
    fixture_path = FIXTURE_ROOT / "marks-clipping.pdf"
    with fitz.open(fixture_path) as document:
        page = document[0]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixels = pixmap.samples
        colors = {
            tuple(pixels[index : index + 3])
            for index in range(0, len(pixels), pixmap.n)
        }
        assert pixmap.width > 0 and pixmap.height > 0
        assert len(colors) >= 20
        assert any(red > blue + 40 for red, green, blue in colors)
        assert any(blue > red + 40 for red, green, blue in colors)


def test_front_back_fixture_keeps_face_and_transform_expectations_explicit() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["file"] == "front-back-flip.pdf")
    assert [page["face"] for page in case["pages"]] == ["front", "back"]
    assert [page["flip"] for page in case["pages"]] == ["none", "horizontal"]
    assert case["pages"][1]["content_transform"] == {
        "rotation_deg": 90,
        "offset_mm": {"x": 1.5, "y": -2.0},
        "clip_to": "trim",
    }
