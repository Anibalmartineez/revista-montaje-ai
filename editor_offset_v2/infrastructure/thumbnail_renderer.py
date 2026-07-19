"""PNG thumbnail generation for immutable Editor Offset V2 PDF assets."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import fitz

from .pdf_inspector import PdfInspection


THUMBNAIL_EXTENSION: Final = "png"
THUMBNAIL_MAX_EDGE_PX: Final = 900
THUMBNAIL_MAX_SCALE: Final = 2.0


class ThumbnailRenderError(RuntimeError):
    """Raised when a PDF page cannot be rasterized for UI use."""


def render_thumbnails(
    pdf_path: str | Path,
    output_directory: str | Path,
    inspection: PdfInspection,
) -> tuple[Path, ...]:
    """Render one bounded RGB PNG per page without saving changes to the PDF."""

    source = Path(pdf_path)
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=False)
    rendered: list[Path] = []
    try:
        with fitz.open(source) as document:
            if document.page_count != inspection.page_count:
                raise ThumbnailRenderError("PDF page count changed during thumbnail generation")
            for page_info in inspection.pages:
                page = document.load_page(page_info.number - 1)
                longest_edge = max(float(page.rect.width), float(page.rect.height))
                if longest_edge <= 0:
                    raise ThumbnailRenderError(
                        f"Page {page_info.number} has no renderable area"
                    )
                scale = min(
                    THUMBNAIL_MAX_SCALE,
                    THUMBNAIL_MAX_EDGE_PX / longest_edge,
                )
                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(scale, scale),
                    colorspace=fitz.csRGB,
                    alpha=False,
                )
                target = destination / f"page_{page_info.number}.{THUMBNAIL_EXTENSION}"
                pixmap.save(target)
                rendered.append(target)
    except ThumbnailRenderError:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError, OSError) as exc:
        raise ThumbnailRenderError("A PDF page could not be rendered safely") from exc
    return tuple(rendered)


__all__ = [
    "THUMBNAIL_EXTENSION",
    "THUMBNAIL_MAX_EDGE_PX",
    "ThumbnailRenderError",
    "render_thumbnails",
]
