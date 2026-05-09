import os
from typing import Dict, Iterable

from PyPDF2 import PdfReader
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services.editor_offset_layout_defaults import (
    REPEAT_DESIGN_DEFAULT_PRIORITY,
    first_numeric,
)


def pdf_page_size_mm(path: str) -> tuple[float, float]:
    try:
        reader = PdfReader(path)
        page = reader.pages[0]
        w_pt = float(page.mediabox.width)
        h_pt = float(page.mediabox.height)
        return (w_pt * 25.4 / 72.0, h_pt * 25.4 / 72.0)
    except Exception:
        return 0.0, 0.0


def _next_design_ref(designs: list[Dict]) -> str:
    prefix = "file"
    max_idx = -1
    for design in designs:
        ref = str(design.get("ref", ""))
        if ref.startswith(prefix):
            try:
                idx = int(ref[len(prefix) :])
                max_idx = max(max_idx, idx)
            except ValueError:
                continue
    return f"{prefix}{max_idx + 1}"


def append_uploaded_designs(
    *,
    job_dir: str,
    layout: Dict,
    files: Iterable[FileStorage],
    work_id_form: str | None = None,
) -> list[Dict]:
    designs = layout.get("designs", [])
    if not isinstance(designs, list):
        designs = []

    if not work_id_form and layout.get("works"):
        if len(layout["works"]) == 1:
            work_id_form = layout["works"][0].get("id")

    for file_storage in files:
        filename = secure_filename(file_storage.filename)
        if not filename:
            continue
        os.makedirs(job_dir, exist_ok=True)
        dest = os.path.join(job_dir, filename)
        file_storage.save(dest)
        new_ref = _next_design_ref(designs)
        width_mm, height_mm = pdf_page_size_mm(dest)
        bleed_mm = first_numeric(layout.get("bleed_default_mm"), default=0.0)
        allow_rotation = True
        forms_per_plate = 1
        if work_id_form:
            related_work = next((w for w in layout.get("works", []) if w.get("id") == work_id_form), None)
            if related_work:
                bleed_mm = first_numeric(related_work.get("default_bleed_mm"), bleed_mm, default=0.0)
                allow_rotation = bool(related_work.get("allow_rotation", True))
                forms_per_plate = int(related_work.get("forms_per_plate") or forms_per_plate)
                final_size = related_work.get("final_size_mm") or []
                if len(final_size) == 2:
                    width_mm = first_numeric(final_size[0], width_mm, default=0.0)
                    height_mm = first_numeric(final_size[1], height_mm, default=0.0)
                    if not related_work.get("has_bleed"):
                        width_mm += 2 * bleed_mm
                        height_mm += 2 * bleed_mm
        designs.append(
            {
                "ref": new_ref,
                "filename": filename,
                "work_id": work_id_form,
                "width_mm": round(first_numeric(width_mm, default=0.0), 3),
                "height_mm": round(first_numeric(height_mm, default=0.0), 3),
                "bleed_mm": round(first_numeric(bleed_mm, default=0.0), 3),
                "allow_rotation": allow_rotation,
                "forms_per_plate": max(1, forms_per_plate),
                "priority": REPEAT_DESIGN_DEFAULT_PRIORITY,
                "preferred_zone": "auto",
                "preferred_flow": "auto",
                "repeat_role": "secondary",
                "repeat_manual_overrides": {
                    "priority": False,
                    "preferred_flow": False,
                    "repeat_role": False,
                },
            }
        )

    layout["designs"] = designs
    return designs
