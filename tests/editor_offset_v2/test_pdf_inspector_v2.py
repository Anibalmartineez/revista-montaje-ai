from __future__ import annotations

import math

import pytest

from editor_offset_v2.infrastructure.pdf_inspector import (
    POINT_TO_MM,
    PdfInspectionError,
    inspect_pdf,
)
from editor_offset_v2.infrastructure.thumbnail_renderer import render_thumbnails


def test_inspects_multipage_boxes_rotation_and_suggested_policy(
    tmp_path,
    pdf_bytes_factory,
):
    path = tmp_path / "multipage.pdf"
    path.write_bytes(
        pdf_bytes_factory(
            page_sizes=((288, 144), (200, 100)),
            trim=True,
            bleed=True,
            crop=True,
            rotation=90,
        )
    )

    inspection = inspect_pdf(path)

    assert inspection.page_count == 2
    assert [page.number for page in inspection.pages] == [1, 2]
    assert all(page.intrinsic_rotation_deg == 90 for page in inspection.pages)
    first = inspection.pages[0]
    assert first.suggested_box == "trim"
    assert first.trim is not None
    assert first.bleed is not None
    assert first.crop is not None
    assert math.isclose(first.media.width, 288 * POINT_TO_MM)
    assert math.isclose(first.trim.x, 8 * POINT_TO_MM)
    assert first.suggested_size_mm == (first.trim.height, first.trim.width)


def test_absent_optional_boxes_remain_none_and_media_is_suggested(
    tmp_path,
    pdf_bytes_factory,
):
    path = tmp_path / "media-only.pdf"
    path.write_bytes(pdf_bytes_factory())

    page = inspect_pdf(path).pages[0]

    assert page.crop is None
    assert page.trim is None
    assert page.bleed is None
    assert page.suggested_box == "media"
    assert page.boxes_as_layout()["trim"] is None


def test_crop_is_suggested_only_when_trim_is_absent(tmp_path, pdf_bytes_factory):
    path = tmp_path / "crop.pdf"
    path.write_bytes(pdf_bytes_factory(crop=True))

    page = inspect_pdf(path).pages[0]

    assert page.suggested_box == "crop"
    assert page.crop is not None
    assert page.trim is None


def test_corrupt_pdf_and_page_limit_are_controlled(tmp_path, pdf_bytes_factory):
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-not-a-real-document")
    with pytest.raises(PdfInspectionError, match="corrupt"):
        inspect_pdf(corrupt)

    multipage = tmp_path / "too-many.pdf"
    multipage.write_bytes(pdf_bytes_factory(page_sizes=((100, 100), (100, 100))))
    with pytest.raises(PdfInspectionError, match="limit"):
        inspect_pdf(multipage, max_pages=1)


def test_thumbnail_renderer_creates_bounded_pngs(tmp_path, pdf_bytes_factory):
    path = tmp_path / "thumbs.pdf"
    path.write_bytes(pdf_bytes_factory(page_sizes=((288, 144), (144, 288))))
    inspection = inspect_pdf(path)

    outputs = render_thumbnails(path, tmp_path / "thumbnails", inspection)

    assert [item.name for item in outputs] == ["page_1.png", "page_2.png"]
    assert all(item.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for item in outputs)
