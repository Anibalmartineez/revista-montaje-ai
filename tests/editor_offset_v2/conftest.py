from __future__ import annotations

import io

import fitz
import pytest


@pytest.fixture
def pdf_bytes_factory():
    def build(
        *,
        page_sizes: tuple[tuple[float, float], ...] = ((288.0, 144.0),),
        trim: bool = False,
        bleed: bool = False,
        crop: bool = False,
        rotation: int = 0,
        text: str = "Editor Offset V2",
    ) -> bytes:
        document = fitz.open()
        for index, (width, height) in enumerate(page_sizes, start=1):
            page = document.new_page(width=width, height=height)
            page.insert_text((18, 28), f"{text} - {index}", fontsize=12)
            if crop:
                document.xref_set_key(
                    page.xref,
                    "CropBox",
                    f"[4 4 {width - 4} {height - 4}]",
                )
            if trim:
                document.xref_set_key(
                    page.xref,
                    "TrimBox",
                    f"[8 8 {width - 8} {height - 8}]",
                )
            if bleed:
                document.xref_set_key(
                    page.xref,
                    "BleedBox",
                    f"[4 4 {width - 4} {height - 4}]",
                )
            if rotation:
                page.set_rotation(rotation)
        output = io.BytesIO()
        document.save(output)
        document.close()
        return output.getvalue()

    return build
