"""Prepared-source trial boundary. The public legacy capabilities stay unchanged."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import fitz

from editor_offset_v2.application.output_service import validate_output_capabilities
from editor_offset_v2.domain.output_contract import OutputAdapterResult, OutputIssue
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.editor_output_adapter import (
    _build_output_job, _resolve_asset_path, serialize_output_job,
)
from editor_offset_v2.infrastructure.prepared_pdf_source import prepare_source


# These four OLD bridge restrictions are replaced by mandatory physical source
# preparation. A failure in preparation aborts the trial, never falls back to V1.
PREPARATION_REPLACES = frozenset({
    "UNSUPPORTED_SOURCE_PAGE", "UNSUPPORTED_PDF_BOX",
    "UNSUPPORTED_INTRINSIC_ROTATION", "UNSUPPORTED_CONTENT_CLIP",
})


def adapt_prepared_trial(layout: dict, root: Path) -> OutputAdapterResult:
    structural = validate_layout_v2(layout)
    if structural:
        return OutputAdapterResult(False, None, tuple(
            OutputIssue(issue.code, "error", issue.message, issue.path) for issue in structural
        ))
    issues = [issue for issue in validate_output_capabilities(layout)
              if issue.code not in PREPARATION_REPLACES]
    paths = {}
    assets = {asset["id"]: asset for asset in layout["assets"]}
    for slot in layout["slots"]:
        asset_id = slot["source"]["asset_id"]
        if asset_id in paths:
            continue
        path, issue = _resolve_asset_path(root, assets[asset_id]["storage_key"],
                                          path=f"assets.{asset_id}.storage_key",
                                          slot_id=slot["id"], asset_id=asset_id)
        if issue:
            issues.append(issue)
        else:
            paths[asset_id] = path
    if any(issue.level == "error" for issue in issues):
        return OutputAdapterResult(False, None, tuple(issues))
    return OutputAdapterResult(True, _build_output_job(layout, paths), tuple(issues))


def prepare_renderer_inputs(job, layout, snapshots, stage, *, allow_mirror_bleed):
    payload = serialize_output_job(job)
    slots = {slot["id"]: slot for slot in layout["slots"]}
    folder = stage / "prepared"
    folder.mkdir()
    paths, evidence, cache = [], [], {}
    for face in job.export.face_order:
        for position in payload["faces"][face]["posiciones_manual"]:
            slot = slots[position["slot_id"]]
            source = slot["source"]
            bleed = slot["geometry"]["bleed_mm"]
            clip = slot["content_transform"]["clip_to"]
            key = (source["asset_id"], source["page"], source["pdf_box"], bleed, clip)
            if key not in cache:
                prepared = prepare_source(
                    snapshots[source["asset_id"]].read_bytes(),
                    page_number=source["page"], pdf_box=source["pdf_box"],
                    bleed_mm=bleed, clip_to=clip, allow_mirror_bleed=allow_mirror_bleed,
                )
                index = len(paths)
                path = folder / f"source_{index}.pdf"
                path.write_bytes(prepared.data)
                paths.append(path)
                cache[key] = (index, prepared.size)
                evidence.append({
                    **source, "bleed_mm": bleed, "clip_to": clip,
                    "bleed_origin": prepared.bleed_origin,
                    "prepared_path": path.relative_to(stage).as_posix(),
                    "sha256": hashlib.sha256(prepared.data).hexdigest(),
                })
            index, size = cache[key]
            # Keep the original V2 center and rotated footprint. Feed the entire
            # precomposed carrier to V1 as artwork with zero additional bleed.
            position.update(file_idx=index, source_page=1, pdf_box="trim",
                            source_w_mm=size.width, source_h_mm=size.height,
                            bleed_mm=0, crop_marks=False)
    return paths, payload, evidence


def overlay_slot_crop_marks(pdf_path: Path, job, face: str) -> None:
    positions = [position for position in job.face(face).positions if position.crop_marks]
    if not positions:
        return
    from reportlab.pdfgen import canvas
    from montaje_offset_inteligente import draw_cutmarks_around_form_reportlab

    points = 72 / 25.4
    stream = io.BytesIO()
    drawing = canvas.Canvas(stream, pagesize=(job.sheet_size.width * points, job.sheet_size.height * points))
    for position in positions:
        trim = position.trim_bounds
        # Reuse V1's eight ticks per trim. For zero bleed the trial explicitly
        # uses 3 mm ticks instead of silently omitting requested crop marks.
        draw_cutmarks_around_form_reportlab(
            drawing, trim.left * points, trim.bottom * points,
            (trim.right - trim.left) * points, (trim.top - trim.bottom) * points,
            bleed_mm=position.bleed_mm if position.bleed_mm > 0 else 3,
        )
    drawing.save()
    with fitz.open(pdf_path) as output, fitz.open(stream=stream.getvalue(), filetype="pdf") as marks:
        output[0].show_pdf_page(output[0].rect, marks, 0)
        data = output.tobytes(garbage=3, deflate=True)
    pdf_path.write_bytes(data)  # Only unpublished trial staging is modified.
