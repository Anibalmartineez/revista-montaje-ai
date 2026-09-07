from __future__ import annotations

import copy
import json

import fitz
import pytest

from editor_offset_v2.infrastructure.legacy_output_probe import run_prepared_output_probe
from editor_offset_v2.infrastructure.prepared_pdf_source import SourcePreparationError
from test_legacy_output_probe_v2 import COLOR_TOLERANCE, make_job, rgb_at, save_job, trial_root


def run(root, destination, **options):
    return run_prepared_output_probe(root, destination, expected_revision=4, **options)


@pytest.mark.parametrize("mode", ["raster", "vector_hybrid"])
@pytest.mark.parametrize("native_bleed", [False, True])
def test_full_montage_preserves_rotations_bleed_and_positions(trial_root, mode, native_bleed):
    root = trial_root / "job"
    layout, source = make_job(root, mode=mode, bleed=3 if native_bleed else 0,
                              selected_box="trim" if native_bleed else "crop")
    original = source.read_bytes()
    layout["slots"] = [copy.deepcopy(layout["slots"][0]) for _ in range(4)]
    centers = [(37, 34), (93, 38), (40, 103), (112, 99)]
    red_offsets = [(-10, 5), (-5, -10), (10, -5), (5, 10)]
    outer_red = [(-21.5, 5), (-5, -21.5), (21.5, -5), (5, 21.5)]
    for index, slot in enumerate(layout["slots"]):
        slot["id"] = f"slot_{index}"
        slot["geometry"].update(rotation_deg=90 * index, bleed_mm=3)
        slot["geometry"]["position_mm"].update(x_mm=centers[index][0], y_mm=centers[index][1])
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts", allow_mirror_bleed=not native_bleed)
    report = json.loads(artifacts.report.read_text(encoding="utf-8"))
    assert {item["bleed_origin"] for item in report["preparation"]} == {"source" if native_bleed else "mirror"}
    with fitz.open(artifacts.pdf) as document:
        for index, (cx, cy) in enumerate(centers):
            red, outer = red_offsets[index], outer_red[index]
            assert rgb_at(document[0], cx + red[0], cy + red[1]) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
            assert rgb_at(document[0], cx + outer[0], cy + outer[1]) == pytest.approx(
                (255, 0, 255) if native_bleed else (255, 0, 0), abs=COLOR_TOLERANCE)
            pos = report["positions"]["front"][index]
            w, h = (46, 26) if index % 2 == 0 else (26, 46)
            assert (pos["x_mm"], pos["y_mm"]) == pytest.approx((cx - w / 2, cy - h / 2), abs=0.01)
    assert source.read_bytes() == original


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_selected_page_and_intrinsic_rotation_compose_with_slot_rotation(trial_root, rotation):
    root = trial_root / "job"
    layout, _ = make_job(root, pages=2, rotation=rotation)
    slot = layout["slots"][0]
    slot["source"]["page"] = 2
    slot["geometry"]["rotation_deg"] = rotation
    if rotation in (90, 270):
        slot["geometry"]["trim_size_mm"].update(width=20, height=40)
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts")
    with fitz.open(artifacts.pdf) as document:
        assert "PAGE 2" in document[0].get_text()
        assert "PAGE 1" not in document[0].get_text()
        # Intrinsic clockwise + slot counterclockwise cancel.
        assert rgb_at(document[0], 27, 39) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)


@pytest.mark.parametrize("bleed", [0, 3])
def test_crop_marks_follow_each_slot_even_with_zero_bleed(trial_root, bleed):
    root = trial_root / "job"
    layout, _ = make_job(root, bleed=bleed)
    profile = layout["export"]["marks_profiles"][0]
    profile["crop_marks"] = True
    layout["export"]["marks_profiles"].append(dict(profile, id="without_marks", crop_marks=False))
    second = copy.deepcopy(layout["slots"][0])
    second["id"] = "second"
    second["production"]["marks_profile_id"] = "without_marks"
    second["geometry"]["position_mm"]["x_mm"] = 110
    layout["slots"].append(second)
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts")
    with fitz.open(artifacts.pdf) as document:
        strokes = [drawing for drawing in document[0].get_drawings() if drawing["type"] == "s"]
        assert len(strokes) == 8
        assert all(drawing["rect"].x1 < 65 * 72 / 25.4 for drawing in strokes)


def test_current_crop_and_bleed_case_requires_explicit_mirror(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root, selected_box="crop")
    layout["slots"][0]["geometry"]["bleed_mm"] = 3
    save_job(root, layout)
    with pytest.raises(SourcePreparationError) as caught:
        run(root, trial_root / "blocked")
    assert caught.value.code == "BLEED_REQUIRES_EXPLICIT_MIRROR"
    assert not (trial_root / "blocked").exists()
    assert not list(trial_root.glob(".v2-output-probe-*"))
    assert run(root, trial_root / "artifacts", allow_mirror_bleed=True).pdf.is_file()


def test_unsupported_clip_cannot_bypass_preparation(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root)
    layout["slots"][0]["content_transform"]["clip_to"] = "none"
    save_job(root, layout)
    with pytest.raises(SourcePreparationError) as caught:
        run(root, trial_root / "artifacts")
    assert caught.value.code == "UNSUPPORTED_CONTENT_CLIP"
    assert not (trial_root / "artifacts").exists()
