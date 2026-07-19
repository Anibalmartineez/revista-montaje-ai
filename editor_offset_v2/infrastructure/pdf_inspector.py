"""Strict PDF page and box inspection for physical Editor Offset V2 assets."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import fitz


POINT_TO_MM: Final = 25.4 / 72.0
DEFAULT_MAX_PAGES: Final = 250
_NUMBER_PATTERN = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)


class PdfInspectionError(ValueError):
    """Raised when an uploaded file is not a safely inspectable PDF."""


@dataclass(frozen=True)
class PdfBox:
    x: float
    y: float
    width: float
    height: float

    def as_layout(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class PdfPageInspection:
    number: int
    intrinsic_rotation_deg: int
    media: PdfBox
    crop: PdfBox | None
    trim: PdfBox | None
    bleed: PdfBox | None
    suggested_box: str

    @property
    def suggested_size_mm(self) -> tuple[float, float]:
        box = getattr(self, self.suggested_box)
        if box is None:  # pragma: no cover - protected by suggested-box policy
            raise PdfInspectionError("The suggested PDF box is absent")
        if self.intrinsic_rotation_deg in (90, 270):
            return box.height, box.width
        return box.width, box.height

    def boxes_as_layout(self) -> dict[str, dict[str, float] | None]:
        return {
            "media": self.media.as_layout(),
            "trim": self.trim.as_layout() if self.trim else None,
            "bleed": self.bleed.as_layout() if self.bleed else None,
            "crop": self.crop.as_layout() if self.crop else None,
        }


@dataclass(frozen=True)
class PdfInspection:
    page_count: int
    pages: tuple[PdfPageInspection, ...]


def _parent_xref(document: fitz.Document, xref: int) -> int | None:
    key_type, value = document.xref_get_key(xref, "Parent")
    if key_type != "xref":
        return None
    match = re.match(r"\s*(\d+)\s+\d+\s+R\s*$", value)
    return int(match.group(1)) if match else None


def _box_value(
    document: fitz.Document,
    page_xref: int,
    key: str,
    *,
    inherited: bool,
) -> str | None:
    current = page_xref
    visited: set[int] = set()
    while current not in visited:
        visited.add(current)
        key_type, value = document.xref_get_key(current, key)
        if key_type == "array":
            return value
        if not inherited:
            return None
        parent = _parent_xref(document, current)
        if parent is None:
            return None
        current = parent
    return None


def _parse_pdf_box(value: str | None, name: str) -> PdfBox | None:
    if value is None:
        return None
    numbers = [float(item) for item in _NUMBER_PATTERN.findall(value)]
    if len(numbers) != 4 or not all(math.isfinite(item) for item in numbers):
        raise PdfInspectionError(f"{name} is not a finite four-number PDF box")
    x0, y0, x1, y1 = numbers
    left, right = sorted((x0, x1))
    bottom, top = sorted((y0, y1))
    if right <= left or top <= bottom:
        raise PdfInspectionError(f"{name} must have positive dimensions")
    return PdfBox(
        x=left * POINT_TO_MM,
        y=bottom * POINT_TO_MM,
        width=(right - left) * POINT_TO_MM,
        height=(top - bottom) * POINT_TO_MM,
    )


def inspect_pdf(
    pdf_path: str | Path,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> PdfInspection:
    """Inspect page boxes without inventing absent TrimBox or BleedBox values."""

    path = Path(pdf_path)
    try:
        document = fitz.open(path)
    except (fitz.FileDataError, RuntimeError, ValueError, OSError) as exc:
        raise PdfInspectionError("The uploaded file is corrupt or is not a readable PDF") from exc

    try:
        if document.needs_pass:
            raise PdfInspectionError("Password-protected PDFs are not supported")
        if not document.is_pdf or document.page_count < 1:
            raise PdfInspectionError("The uploaded PDF contains no readable pages")
        if document.page_count > max_pages:
            raise PdfInspectionError(
                f"The PDF exceeds the supported limit of {max_pages} pages"
            )

        pages: list[PdfPageInspection] = []
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            media = _parse_pdf_box(
                _box_value(document, page.xref, "MediaBox", inherited=True),
                "MediaBox",
            )
            if media is None:
                raise PdfInspectionError(f"Page {page_index + 1} has no MediaBox")
            crop = _parse_pdf_box(
                _box_value(document, page.xref, "CropBox", inherited=True),
                "CropBox",
            )
            trim = _parse_pdf_box(
                _box_value(document, page.xref, "TrimBox", inherited=False),
                "TrimBox",
            )
            bleed = _parse_pdf_box(
                _box_value(document, page.xref, "BleedBox", inherited=False),
                "BleedBox",
            )
            suggested = "trim" if trim else "crop" if crop else "media"
            rotation = int(page.rotation)
            if rotation not in (0, 90, 180, 270):
                raise PdfInspectionError(
                    f"Page {page_index + 1} has a non-cardinal intrinsic rotation"
                )
            pages.append(
                PdfPageInspection(
                    number=page_index + 1,
                    intrinsic_rotation_deg=rotation,
                    media=media,
                    crop=crop,
                    trim=trim,
                    bleed=bleed,
                    suggested_box=suggested,
                )
            )
        return PdfInspection(page_count=document.page_count, pages=tuple(pages))
    finally:
        document.close()


__all__ = [
    "DEFAULT_MAX_PAGES",
    "POINT_TO_MM",
    "PdfBox",
    "PdfInspection",
    "PdfInspectionError",
    "PdfPageInspection",
    "inspect_pdf",
]
