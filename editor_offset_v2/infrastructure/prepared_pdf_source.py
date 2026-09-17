"""V2-owned source preparation: page, PDF box, orientation and explicit bleed.

Produces an in-memory, single-page carrier for the temporary renderer. Original
PDF bytes are never saved or modified. The carrier's full page is its TrimBox;
the real piece trim and bleed remain defined by Layout V2, not by this carrier.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import fitz

from editor_offset_v2.domain.geometry import Size, oriented_size, productive_size
from editor_offset_v2.infrastructure.pdf_inspector import PdfBox, inspect_pdf


class SourcePreparationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PreparedSource:
    data: bytes
    trim_size: Size
    size: Size
    bleed_origin: str


def _contains(outer: PdfBox, inner: PdfBox) -> bool:
    # PDF writers round box coordinates independently. This is a physical
    # containment tolerance (1 micron), not the kernel's numerical epsilon.
    epsilon = 0.001
    return (outer.x - epsilon <= inner.x and outer.y - epsilon <= inner.y
            and outer.x + outer.width + epsilon >= inner.x + inner.width
            and outer.y + outer.height + epsilon >= inner.y + inner.height)


def prepare_source(
    pdf_data: bytes,
    *,
    page_number: int,
    pdf_box: str,
    bleed_mm: float = 0,
    clip_to: str = "trim_box",
    allow_mirror_bleed: bool = False,
) -> PreparedSource:
    """Normalize selected visible artwork and preserve real bleed when possible.

    A positive bleed with trim clipping needs explicit mirror permission. With
    bleed clipping, preserve the source's declared coverage; if insufficient,
    only the explicit mirror option permits synthesis. No partial bleed fallback.
    """
    inspection = inspect_pdf(pdf_data)
    if isinstance(page_number, bool) or not isinstance(page_number, int) or not 1 <= page_number <= inspection.page_count:
        raise SourcePreparationError("INVALID_SOURCE_PAGE", "Selected PDF page does not exist")
    if pdf_box not in {"media", "crop", "trim", "bleed"}:
        raise SourcePreparationError("INVALID_SOURCE_BOX", "Unknown PDF source box")
    if clip_to not in {"trim_box", "bleed_box"}:
        raise SourcePreparationError("UNSUPPORTED_CONTENT_CLIP", "Explicit trim or bleed clipping is required")
    info = inspection.pages[page_number - 1]
    selected = getattr(info, pdf_box)
    if selected is None:
        raise SourcePreparationError("MISSING_SOURCE_BOX", "The selected physical PDF box is absent")
    if not _contains(info.media, selected):
        raise SourcePreparationError("SOURCE_BOX_OUTSIDE_MEDIA", "Selected PDF box exceeds MediaBox")
    trim_size = oriented_size(Size(selected.width, selected.height), info.intrinsic_rotation_deg)
    full_size = productive_size(trim_size, bleed_mm)
    if max(full_size.width, full_size.height) > 1400:
        raise SourcePreparationError("SOURCE_RESOURCE_LIMIT", "Prepared source exceeds the trial size limit")
    expanded = PdfBox(selected.x - bleed_mm, selected.y - bleed_mm,
                      selected.width + 2 * bleed_mm, selected.height + 2 * bleed_mm)
    preserve = (bleed_mm > 0 and clip_to == "bleed_box" and info.bleed is not None
                and _contains(info.bleed, expanded) and _contains(info.media, expanded))
    if bleed_mm > 0 and not preserve and not allow_mirror_bleed:
        raise SourcePreparationError("BLEED_REQUIRES_EXPLICIT_MIRROR", "No usable source bleed; mirror generation needs explicit permission")
    if bleed_mm > min(trim_size.width, trim_size.height) and not preserve:
        raise SourcePreparationError("MIRROR_BLEED_EXCEEDS_TRIM", "Mirror strips cannot exceed the source dimensions")
    source_box = expanded if preserve else selected
    content_size = full_size if preserve else trim_size
    points_per_mm = 72 / 25.4

    with fitz.open(stream=pdf_data, filetype="pdf") as source, fitz.open() as normalized:
        page = source.load_page(page_number - 1)
        kind, unit = source.xref_get_key(page.xref, "UserUnit")
        if kind != "null" and float(unit) != 1:
            raise SourcePreparationError("UNSUPPORTED_USER_UNIT", "Non-default UserUnit is not supported")
        if page.first_annot is not None or page.first_widget is not None:
            raise SourcePreparationError("UNSUPPORTED_PDF_ANNOTATIONS", "Annotations require an explicit flattening policy")
        # Reset only the in-memory source view. Raw PDF boxes use bottom-left;
        # MuPDF's transformation matrix maps them into its top-left coordinates.
        page.set_rotation(0)
        media = info.media
        raw_media = [media.x, media.y, media.x + media.width, media.y + media.height]
        source.xref_set_key(page.xref, "CropBox", "[" + " ".join(str(v * points_per_mm) for v in raw_media) + "]")
        page = source.reload_page(page)
        raw_clip = fitz.Rect(source_box.x * points_per_mm, source_box.y * points_per_mm,
                             (source_box.x + source_box.width) * points_per_mm,
                             (source_box.y + source_box.height) * points_per_mm)
        clip = raw_clip * page.transformation_matrix
        target = normalized.new_page(width=content_size.width * points_per_mm,
                                     height=content_size.height * points_per_mm)
        if page.get_contents():
            target.show_pdf_page(target.rect, source, page_number - 1,
                                 clip=clip, rotate=(-info.intrinsic_rotation_deg) % 360,
                                 keep_proportion=False)
        normalized_data = normalized.tobytes(garbage=3, deflate=True)

    if bleed_mm <= 0 or preserve:
        return PreparedSource(normalized_data, trim_size, full_size, "source" if preserve else "none")

    return _compose_mirror(normalized_data, trim_size, full_size, bleed_mm)


def _compose_mirror(normalized_data, trim_size, full_size, bleed_mm):
    """V2 adaptation of V1's eight mirrored strips, with exact physical joins.

    V1's single transparent frame rounds trim and bleed pixels independently;
    scaling that frame around an exact vector trim can leave white seams. Render
    an integer-sized trim and place its eight strips in explicit millimetre
    rectangles instead. Only the strips are RGB raster; the center stays vector.
    """
    import math
    from PIL import Image

    points_per_mm = 72 / 25.4
    with fitz.open(stream=normalized_data, filetype="pdf") as trim_doc, fitz.open() as output:
        source_page = trim_doc[0]
        width = max(1, math.ceil(trim_size.width * 300 / 25.4))
        height = max(1, math.ceil(trim_size.height * 300 / 25.4))
        if width * height > 24_000_000:
            raise SourcePreparationError('SOURCE_RESOURCE_LIMIT', 'Mirror preparation exceeds the 24 megapixel budget')
        pix = source_page.get_pixmap(matrix=fitz.Matrix(
            width / source_page.rect.width, height / source_page.rect.height,
        ), alpha=False, colorspace=fitz.csRGB)
        trim_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        # Floating point page bounds may allocate one extra pixmap edge pixel.
        trim_image = trim_image.crop((0, 0, width, height))
        bx = max(1, min(width, round(bleed_mm * width / trim_size.width)))
        by = max(1, min(height, round(bleed_mm * height / trim_size.height)))
        page = output.new_page(width=full_size.width * points_per_mm,
                               height=full_size.height * points_per_mm)
        b, w, h = bleed_mm, trim_size.width, trim_size.height
        # Source pixel crop, destination mm (top-left), reflection axes.
        strips = [
            ((0, 0, bx, height), (0, b, b, b+h), True, False),
            ((width-bx, 0, width, height), (b+w, b, 2*b+w, b+h), True, False),
            ((0, 0, width, by), (b, 0, b+w, b), False, True),
            ((0, height-by, width, height), (b, b+h, b+w, 2*b+h), False, True),
            ((0, 0, bx, by), (0, 0, b, b), True, True),
            ((width-bx, 0, width, by), (b+w, 0, 2*b+w, b), True, True),
            ((0, height-by, bx, height), (0, b+h, b, 2*b+h), True, True),
            ((width-bx, height-by, width, height), (b+w, b+h, 2*b+w, 2*b+h), True, True),
        ]
        for crop, bounds, horizontal, vertical in strips:
            tile = trim_image.crop(crop)
            if horizontal:
                tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if vertical:
                tile = tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            png = io.BytesIO()
            tile.save(png, format="PNG")
            tile.close()
            page.insert_image(fitz.Rect(*(v * points_per_mm for v in bounds)),
                              stream=png.getvalue(), keep_proportion=False)
        trim_image.close()
        target = fitz.Rect(b * points_per_mm, b * points_per_mm,
                           (b+w) * points_per_mm, (b+h) * points_per_mm)
        if source_page.get_contents():
            page.show_pdf_page(target, trim_doc, 0, keep_proportion=False)
        return PreparedSource(output.tobytes(garbage=3, deflate=True), trim_size, full_size, "mirror")
