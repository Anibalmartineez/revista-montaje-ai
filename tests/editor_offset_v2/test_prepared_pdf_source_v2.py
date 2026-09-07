from __future__ import annotations

import fitz
import pytest

from editor_offset_v2.infrastructure.prepared_pdf_source import SourcePreparationError, prepare_source
from editor_offset_v2.infrastructure.pdf_inspector import inspect_pdf
from test_legacy_output_probe_v2 import COLOR_TOLERANCE, make_job, rgb_at


@pytest.mark.parametrize("box", ["media", "crop", "trim", "bleed"])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_page_box_and_intrinsic_rotation_preserve_artwork(tmp_path, box, rotation):
    _, path = make_job(tmp_path / "job", pages=2, rotation=rotation)
    original = path.read_bytes()
    prepared = prepare_source(original, page_number=2, pdf_box=box)
    assert path.read_bytes() == original
    assert prepared.size.width == pytest.approx(20 if rotation in (90, 270) else 40, abs=0.01)
    assert prepared.size.height == pytest.approx(40 if rotation in (90, 270) else 20, abs=0.01)
    red = {0: (-10, 5), 90: (5, 10), 180: (10, -5), 270: (-5, -10)}[rotation]
    with fitz.open(stream=prepared.data, filetype="pdf") as document:
        assert len(document) == 1
        assert document[0].rotation == 0
        assert "PAGE 2" in document[0].get_text()
        assert "PAGE 1" not in document[0].get_text()
        assert rgb_at(document[0], prepared.size.width / 2 + red[0], prepared.size.height / 2 + red[1]) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)


@pytest.mark.parametrize("box", ["trim", "crop"])
def test_shifted_pdf_boxes_have_no_hidden_offset_or_scaling(tmp_path, box):
    _, path = make_job(tmp_path / "job", shifted=True)
    with fitz.open(path) as document:
        page = document[0]
        if box == "crop":
            document.xref_set_key(page.xref, "CropBox", document.xref_get_key(page.xref, "TrimBox")[1])
        data = document.tobytes()
    prepared = prepare_source(data, page_number=1, pdf_box=box)
    with fitz.open(stream=prepared.data, filetype="pdf") as document:
        assert rgb_at(document[0], 10, 15) == pytest.approx((255, 0, 0), abs=COLOR_TOLERANCE)
        assert rgb_at(document[0], 10, 5) == pytest.approx((0, 0, 255), abs=COLOR_TOLERANCE)
        assert prepared.size.width == pytest.approx(40, abs=0.01)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_original_bleed_is_preserved_even_when_mirror_is_permitted(tmp_path, rotation):
    _, path = make_job(tmp_path / "job", bleed=3, rotation=rotation)
    prepared = prepare_source(path.read_bytes(), page_number=1, pdf_box="trim",
                              bleed_mm=3, clip_to="bleed_box", allow_mirror_bleed=True)
    assert prepared.bleed_origin == "source"
    with fitz.open(stream=prepared.data, filetype="pdf") as document:
        assert rgb_at(document[0], 1.5, 5) == pytest.approx((255, 0, 255), abs=COLOR_TOLERANCE)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_missing_bleed_requires_explicit_option_and_frame_matches_trim(tmp_path, rotation):
    _, path = make_job(tmp_path / "job", selected_box="crop", rotation=rotation)
    data = path.read_bytes()
    assert inspect_pdf(data).pages[0].trim is None
    with pytest.raises(SourcePreparationError) as caught:
        prepare_source(data, page_number=1, pdf_box="crop", bleed_mm=3)
    assert caught.value.code == "BLEED_REQUIRES_EXPLICIT_MIRROR"
    prepared = prepare_source(data, page_number=1, pdf_box="crop", bleed_mm=3, allow_mirror_bleed=True)
    assert prepared.bleed_origin == "mirror"
    # Same strip and inner edge must have matching colors after intrinsic rotation.
    with fitz.open(stream=prepared.data, filetype="pdf") as document:
        page = document[0]
        assert rgb_at(page, 1.5, prepared.size.height - 8) == pytest.approx(
            rgb_at(page, 5, prepared.size.height - 8), abs=COLOR_TOLERANCE)


@pytest.mark.parametrize("option,value,code", [
    ("page_number", 3, "INVALID_SOURCE_PAGE"),
    ("pdf_box", "unknown", "INVALID_SOURCE_BOX"),
    ("clip_to", "none", "UNSUPPORTED_CONTENT_CLIP"),
])
def test_invalid_source_options_are_rejected(tmp_path, option, value, code):
    _, path = make_job(tmp_path / "job")
    options = dict(page_number=1, pdf_box="trim")
    options[option] = value
    with pytest.raises(SourcePreparationError) as caught:
        prepare_source(path.read_bytes(), **options)
    assert caught.value.code == code


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_mirror_joins_do_not_expose_white_gaps(tmp_path, rotation):
    _, path = make_job(tmp_path / "job", selected_box="crop", rotation=rotation)
    prepared = prepare_source(path.read_bytes(), page_number=1, pdf_box="crop",
                              bleed_mm=3, allow_mirror_bleed=True)
    with fitz.open(stream=prepared.data, filetype="pdf") as document:
        pix = document[0].get_pixmap(dpi=600, alpha=False)
        scale = 600 / 25.4
        w, h = prepared.trim_size.width, prepared.trim_size.height

        def pixel(x, y):
            return pix.pixel(int(x * scale), int(y * scale))

        joins = [
            ((3, 3 + h / 4), (3.5, 3 + h / 4), True),
            ((3 + w, 3 + h / 4), (2.5 + w, 3 + h / 4), True),
            ((3 + w / 4, 3), (3 + w / 4, 3.5), False),
            ((3 + w / 4, 3 + h), (3 + w / 4, 2.5 + h), False),
        ]
        for (x, y), inner, horizontal in joins:
            expected = pixel(*inner)
            for delta in range(-4, 5):
                observed = pixel(x + delta / scale if horizontal else x,
                                 y if horizontal else y + delta / scale)
                # Allow subpixel antialiasing at a join; the former white gaps
                # exceeded this by > 150 RGB levels at 600 dpi.
                assert observed == pytest.approx(expected, abs=80)
