"""Artifact-level characterization; does not exercise Flask or real user jobs."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

import fitz
import numpy as np
import pytest
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure import legacy_output_probe as probe
from editor_offset_v2.infrastructure.pdf_inspector import inspect_pdf


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "editor_offset_v2"
MM_PER_PIXEL = 25.4 / 150
COLOR_TOLERANCE = 35
RASTER_BOUNDS_TOLERANCE_MM = 0.35


@pytest.fixture
def trial_root(tmp_path):
    # Optional retained artifacts for human review, always in a fresh directory.
    retained = os.environ.get("EDITOR_V2_PROBE_ARTIFACT_ROOT")
    if retained:
        parent = Path(retained).resolve()
        parent.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="trial-", dir=parent))
    return tmp_path


def make_job(root, *, bleed=0, pages=1, rotation=0, shifted=False, mode="vector_hybrid", selected_box="trim"):
    root.mkdir()
    layout = json.loads((FIXTURES / "layout_v2_complete.json").read_text(encoding="utf-8"))
    layout["sheet"]["size_mm"] = {"width": 200, "height": 160}
    layout["faces"] = {"enabled": ["front"], "duplex": {"enabled": False, "flip": "none"}}
    layout["ctp"]["enabled"] = False
    layout["export"].update(render_mode=mode, preserve_vector_content=mode == "vector_hybrid")
    layout["export"]["faces"].update(back=False, combine_in_single_pdf=False, order=["front"])
    for profile in layout["export"]["marks_profiles"]:
        profile.update(crop_marks=False, registration_marks=False, technical_text=False, color_bar=False)
    asset = layout["assets"][0]
    layout["assets"] = [asset]
    source = root / asset["storage_key"]
    source.parent.mkdir(parents=True)
    left, bottom = (11, 17) if shifted else (bleed, bleed)
    width, height = (84, 62) if shifted else (40 + 2 * bleed, 20 + 2 * bleed)
    raw = root / "fixture-drawing.pdf"
    drawing = canvas.Canvas(str(raw), pagesize=(width * mm, height * mm), invariant=1)
    for number in range(1, pages + 1):
        # Native bleed is magenta; mirrored artwork has a different color.
        drawing.setFillColorRGB(1, 0, 1)
        drawing.rect(0, 0, width * mm, height * mm, fill=1, stroke=0)
        for x, y, color in ((0, 10, (1, 0, 0)), (20, 10, (0, 1, 0)),
                            (0, 0, (0, 0, 1)), (20, 0, (1, 1, 0))):
            drawing.setFillColorRGB(*color)
            drawing.rect((left + x) * mm, (bottom + y) * mm, 20 * mm, 10 * mm, fill=1, stroke=0)
        drawing.setFillColorRGB(0, 0, 0)
        drawing.setFont("Helvetica", 6)
        drawing.drawString((left + 15) * mm, (bottom + 9) * mm, f"PAGE {number}")
        drawing.showPage()
    drawing.save()
    reader, writer = PdfReader(str(raw)), PdfWriter()
    for page in reader.pages:
        page.cropbox = RectangleObject(page.mediabox)
        if selected_box == "trim":
            page.trimbox = RectangleObject([v * mm for v in (left, bottom, left + 40, bottom + 20)])
            page.bleedbox = RectangleObject([v * mm for v in (
                left - bleed, bottom - bleed, left + 40 + bleed, bottom + 20 + bleed,
            )])
        if rotation:
            page.rotate(rotation)
        writer.add_page(page)
    with source.open("wb") as stream:
        writer.write(stream)
    inspection = inspect_pdf(source)
    template_page = copy.deepcopy(asset["pages"][0])
    template_page["preflight"].update(status="not_run", issues=[])
    asset.update(sha256=hashlib.sha256(source.read_bytes()).hexdigest(), page_count=pages)
    asset["pages"] = [dict(copy.deepcopy(template_page), number=page.number,
                           intrinsic_rotation_deg=page.intrinsic_rotation_deg,
                           boxes_mm=page.boxes_as_layout()) for page in inspection.pages]
    work = layout["works"][0]
    work.update(trim_size_mm={"width": 40, "height": 20}, bleed_mm=bleed, back_source=None)
    work["front_source"]["pdf_box"] = selected_box
    slot = layout["slots"][0]
    slot["source"]["pdf_box"] = selected_box
    layout["slots"] = [slot]
    slot["geometry"].update(trim_size_mm={"width": 40, "height": 20}, bleed_mm=bleed, rotation_deg=0)
    slot["geometry"]["position_mm"].update(x_mm=37, y_mm=34)
    slot["content_transform"]["clip_to"] = "bleed_box" if bleed else "trim_box"
    save_job(root, layout)
    return layout, source


def save_job(root, layout):
    issues = validate_layout_v2(layout)
    assert not issues, issues
    (root / "layout_v2.json").write_text(json.dumps(layout, indent=2), encoding="utf-8")


def run(root, destination, **kwargs):
    return probe.run_legacy_output_probe(root, destination, expected_revision=4, **kwargs)


def rgb_at(page, x, y):
    pix = page.get_pixmap(dpi=150, alpha=False, colorspace=fitz.csRGB)
    pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return pixels[int((page.rect.height * 25.4 / 72 - y) / MM_PER_PIXEL), int(x / MM_PER_PIXEL)]


@pytest.mark.parametrize("mode", ["raster", "vector_hybrid"])
def test_four_rotations_match_v2_positions_and_asymmetric_artwork(trial_root, mode):
    root = trial_root / "job"
    layout, source = make_job(root, mode=mode)
    original = source.read_bytes()
    layout["slots"] = [copy.deepcopy(layout["slots"][0]) for _ in range(4)]
    # Deliberately off-center: a centering default would fail these checks.
    centers = [(37, 34), (93, 38), (40, 103), (112, 99)]
    red_offsets = [(-10, 5), (-5, -10), (10, -5), (5, 10)]
    blue_offsets = [(-10, -5), (5, -10), (10, 5), (-5, 10)]
    for index, slot in enumerate(layout["slots"]):
        slot["id"] = f"slot_{index}"
        slot["geometry"]["rotation_deg"] = index * 90
        slot["geometry"]["position_mm"].update(x_mm=centers[index][0], y_mm=centers[index][1])
    save_job(root, layout)
    stored = (root / "layout_v2.json").read_bytes()
    artifacts = run(root, trial_root / "artifacts")
    report = json.loads(artifacts.report.read_text(encoding="utf-8"))
    assert report["production_ready"] is False
    with fitz.open(artifacts.pdf) as document:
        assert len(document) == 1
        page = document[0]
        assert tuple(page.mediabox)[2:] == pytest.approx((200 * mm, 160 * mm), abs=0.01 * mm)
        for index, ((cx, cy), red, blue) in enumerate(zip(centers, red_offsets, blue_offsets)):
            assert rgb_at(page, cx + red[0], cy + red[1]) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
            assert rgb_at(page, cx + blue[0], cy + blue[1]) == pytest.approx((0, 0, 255), abs=COLOR_TOLERANCE)
            w, h = (40, 20) if index % 2 == 0 else (20, 40)
            applied = report["positions"]["front"][index]
            assert (applied["x_mm"], applied["y_mm"]) == pytest.approx((cx - w / 2, cy - h / 2), abs=0.01)
            # Pixel footprint, independent of renderer-returned positions.
            crop = fitz.Rect((cx - w / 2 - 2) * mm, (160 - cy - h / 2 - 2) * mm,
                             (cx + w / 2 + 2) * mm, (160 - cy + h / 2 + 2) * mm)
            pix = page.get_pixmap(dpi=150, clip=crop, alpha=False)
            pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            mask = np.max(pixels, axis=2).astype(int) - np.min(pixels, axis=2).astype(int) > 100
            ys, xs = np.where(mask)
            assert (xs.max() - xs.min() + 1) * MM_PER_PIXEL == pytest.approx(w, abs=RASTER_BOUNDS_TOLERANCE_MM)
            assert (ys.max() - ys.min() + 1) * MM_PER_PIXEL == pytest.approx(h, abs=RASTER_BOUNDS_TOLERANCE_MM)
        assert ("PAGE 1" in page.get_text()) == (mode == "vector_hybrid")
        expected_preview = page.get_pixmap(dpi=150, alpha=False)
        with Image.open(artifacts.previews[0]) as preview:
            assert preview.tobytes() == expected_preview.samples
    assert source.read_bytes() == original
    assert (root / "layout_v2.json").read_bytes() == stored


@pytest.mark.parametrize("mode", ["raster", "vector_hybrid"])
def test_shifted_trim_box_clips_original_artwork(trial_root, mode):
    root = trial_root / "job"
    make_job(root, shifted=True, mode=mode)
    artifacts = run(root, trial_root / "artifacts")
    with fitz.open(artifacts.pdf) as document:
        assert rgb_at(document[0], 27, 39) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
        assert rgb_at(document[0], 27, 29) == pytest.approx((0, 0, 255), abs=COLOR_TOLERANCE)
        assert rgb_at(document[0], 15, 34) == pytest.approx((255, 255, 255), abs=COLOR_TOLERANCE)


def test_two_explicit_faces_keep_order_and_page_content(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root)
    layout["faces"]["enabled"].append("back")
    layout["export"]["faces"].update(back=True, combine_in_single_pdf=True, order=["front", "back"])
    back = copy.deepcopy(layout["slots"][0])
    back.update(id="back_slot", face="back")
    back["geometry"]["position_mm"].update(x_mm=137, y_mm=104)
    layout["slots"].append(back)
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts")
    assert len(artifacts.previews) == 2
    with fitz.open(artifacts.pdf) as document:
        assert len(document) == 2
        assert rgb_at(document[0], 27, 39) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
        assert rgb_at(document[1], 127, 109) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
        assert rgb_at(document[1], 27, 39) == pytest.approx((255, 255, 255), abs=COLOR_TOLERANCE)


@pytest.mark.parametrize("mode", ["raster", "vector_hybrid"])
def test_explicit_bleed_observation_proves_original_bleed_is_replaced(trial_root, mode):
    root = trial_root / "job"
    make_job(root, bleed=3, mode=mode)
    with pytest.raises(probe.ProbeRejected, match="Explicit observation"):
        run(root, trial_root / "blocked")
    artifacts = run(root, trial_root / "artifacts", observe_legacy_bleed=True)
    with fitz.open(artifacts.pdf) as document:
        # Outside trim: source was magenta; V1's mirrored left/top quadrant is red.
        assert rgb_at(document[0], 15.5, 39) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
    assert "mirrored" in artifacts.report.read_text(encoding="utf-8")
    assert not (trial_root / "blocked").exists()


@pytest.mark.parametrize("case,code", [
    ("crop_current", "UNSUPPORTED_PDF_BOX"),
    ("page_two", "UNSUPPORTED_SOURCE_PAGE"),
    ("intrinsic_rotation", "UNSUPPORTED_INTRINSIC_ROTATION"),
    ("internal_scale", "UNSUPPORTED_CONTENT_SCALE"),
    ("ctp", "UNSUPPORTED_CTP_CONFIGURATION"),
])
def test_unadapted_features_are_rejected_without_partial_output(trial_root, case, code):
    root = trial_root / "job"
    layout, _ = make_job(root, pages=2, rotation=90 if case == "intrinsic_rotation" else 0,
                         selected_box="crop" if case == "crop_current" else "trim")
    if case == "crop_current":
        layout["slots"][0]["source"]["pdf_box"] = "crop"
        layout["slots"][0]["geometry"]["bleed_mm"] = 3
    elif case == "page_two":
        layout["slots"][0]["source"]["page"] = 2
    elif case == "internal_scale":
        layout["slots"][0]["content_transform"]["scale_x"] = 2
    elif case == "ctp":
        layout["ctp"]["enabled"] = True
    save_job(root, layout)
    with pytest.raises(probe.ProbeRejected) as caught:
        run(root, trial_root / "artifacts")
    assert code in {issue.code for issue in caught.value.issues}
    assert not (trial_root / "artifacts").exists()


@pytest.mark.parametrize("change,code", [("hash", "ASSET_HASH_MISMATCH"),
                                          ("metadata", "PHYSICAL_METADATA_MISMATCH"),
                                          ("missing", "ADAPTER_REJECTED"),
                                          ("revision", "STALE_REVISION")])
def test_physical_identity_and_saved_revision_are_checked(trial_root, change, code):
    root = trial_root / "job"
    layout, source = make_job(root)
    if change == "hash":
        source.write_bytes(source.read_bytes() + b"\n%changed\n")
    elif change == "metadata":
        layout["assets"][0]["pages"][0]["boxes_mm"]["media"]["width"] += 1
    elif change == "missing":
        source.rename(source.with_name("missing.pdf"))
    else:
        layout["job"]["revision"] += 1
    save_job(root, layout)
    with pytest.raises(probe.ProbeRejected) as caught:
        run(root, trial_root / "artifacts")
    assert caught.value.code == code
    assert not (trial_root / "artifacts").exists()
    assert not list(trial_root.glob(".v2-output-probe-*"))


@pytest.mark.parametrize("failure", ["renderer", "stale_during_render"])
def test_failed_trial_publishes_no_partial_artifacts(trial_root, monkeypatch, failure):
    root = trial_root / "job"
    layout, source = make_job(root)
    original = source.read_bytes()
    real_render = probe._render_face
    def interrupted(designs, config):
        assert Path(designs[0].ruta) != source
        if failure == "renderer":
            Path(config.output_path).write_bytes(b"partial")
            raise RuntimeError("simulated renderer failure")
        result = real_render(designs, config)
        layout["job"]["revision"] += 1
        save_job(root, layout)
        return result
    monkeypatch.setattr(probe, "_render_face", interrupted)
    with pytest.raises((RuntimeError, probe.ProbeRejected)):
        run(root, trial_root / "artifacts")
    assert source.read_bytes() == original
    assert not (trial_root / "artifacts").exists()
    assert not list(trial_root.glob(".v2-output-probe-*"))


def test_trial_cannot_write_into_job_or_replace_existing_artifacts(trial_root):
    root = trial_root / "job"
    make_job(root)
    for path in (root / "outputs" / "trial", root, trial_root):
        with pytest.raises(probe.ProbeRejected) as caught:
            run(root, path)
        assert caught.value.code == "UNSAFE_OUTPUT_DIRECTORY"
    destination = trial_root / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_text("keep")
    with pytest.raises(probe.ProbeRejected) as caught:
        run(root, destination)
    assert caught.value.code == "OUTPUT_ALREADY_EXISTS"
    assert marker.read_text() == "keep"


def test_zero_bleed_crop_marks_are_not_drawn_by_legacy(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root)
    layout["export"]["marks_profiles"][0]["crop_marks"] = True
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts")
    with fitz.open(artifacts.pdf) as document:
        strokes = [drawing for drawing in document[0].get_drawings() if drawing["type"] == "s"]
        assert len(strokes) == 0  # Observed limitation, not desired V2 behavior.


def test_mixed_crop_profiles_are_lost_by_legacy_normalization(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root, bleed=3)
    profile = layout["export"]["marks_profiles"][0]
    profile["crop_marks"] = True
    no_marks = dict(profile, id="no_marks", crop_marks=False)
    layout["export"]["marks_profiles"].append(no_marks)
    second = copy.deepcopy(layout["slots"][0])
    second["id"] = "second"
    second["production"]["marks_profile_id"] = "no_marks"
    second["geometry"]["position_mm"]["x_mm"] = 110
    layout["slots"].append(second)
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts", observe_legacy_bleed=True)
    with fitz.open(artifacts.pdf) as document:
        strokes = [drawing for drawing in document[0].get_drawings() if drawing["type"] == "s"]
        assert len(strokes) == 16  # Eight lines on BOTH slots, despite the second profile.


def test_rotated_hybrid_bleed_frame_disagrees_with_vector_center(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root, bleed=3)
    layout["slots"][0]["geometry"]["rotation_deg"] = 90
    save_job(root, layout)
    artifacts = run(root, trial_root / "artifacts", observe_legacy_bleed=True)
    with fitz.open(artifacts.pdf) as document:
        # CCW vector center is red on the lower left. Legacy's clockwise bleed
        # frame mirrors yellow there: this explicitly characterizes the defect.
        assert rgb_at(document[0], 32, 24) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
        assert rgb_at(document[0], 25.5, 24) == pytest.approx((255, 255, 0), abs=COLOR_TOLERANCE)


def test_duplex_flip_requires_a_separate_contract(trial_root):
    root = trial_root / "job"
    layout, _ = make_job(root)
    layout["faces"]["duplex"].update(enabled=True, flip="long_edge")
    save_job(root, layout)
    with pytest.raises(probe.ProbeRejected) as caught:
        run(root, trial_root / "artifacts")
    assert caught.value.code == "DUPLEX_NOT_CHARACTERIZED"
