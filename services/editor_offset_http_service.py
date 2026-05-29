import json
import os
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Dict, Iterable

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage

from cuadernillos.simulator import CuadernilloSimulationError, simular_cuadernillo
from services import editor_offset_imposition_service as editor_imposition
from services import editor_offset_jobs as editor_jobs
from services import editor_offset_layout_defaults as editor_layout_defaults
from services import editor_offset_uploads as editor_uploads
from services.editor_offset_output_service import montar_offset_desde_layout
from services.editor_offset_output_contract import validate_constructor_output_layout


@dataclass
class EditorHttpResult:
    payload: Dict
    status: int = 200


def _error_result(msg: str, code: int = 422, **payload) -> EditorHttpResult:
    body = {"ok": False, "error": msg}
    body.update(payload)
    return EditorHttpResult(body, code)


def editor_visual_context(job_id_param: str | None) -> tuple[str, Dict]:
    job_id = editor_jobs.safe_job_id(job_id_param) or uuid.uuid4().hex[:12]
    _job_dir, layout = editor_jobs.load_or_init_constructor_layout(job_id)
    return (
        "editor_offset_visual.html",
        {
            "job_id": job_id,
            "layout_json": json.dumps(layout),
        },
    )


def save_constructor_layout_from_payload(job_id_raw: str | None, layout: Dict | None) -> EditorHttpResult:
    job_id = editor_jobs.safe_job_id(job_id_raw)
    if not job_id:
        return _error_result("job_id invÃ¡lido")
    if layout is None:
        return _error_result("layout_json faltante")

    layout, _ = editor_layout_defaults.ensure_faces_fields(layout)
    layout, _ = editor_layout_defaults.ensure_imposition_fields(layout)
    layout, _ = editor_layout_defaults.ensure_export_fields(layout)
    job_dir = editor_jobs.constructor_job_dir(job_id)
    editor_jobs.save_constructor_layout(job_dir, layout)
    return EditorHttpResult({"ok": True, "job_id": job_id})


def simulate_cuadernillo(payload: Dict) -> EditorHttpResult:
    try:
        resultado = simular_cuadernillo(payload)
    except CuadernilloSimulationError as exc:
        return _error_result(str(exc), 422)
    return EditorHttpResult({"ok": True, "simulacion": resultado})


def upload_editor_designs(
    job_id: str,
    files: Iterable[FileStorage],
    work_id_form: str | None = None,
) -> EditorHttpResult:
    safe_job_id = editor_jobs.safe_job_id(job_id)
    if not safe_job_id:
        return _error_result("job_id invÃ¡lido")
    job_dir, layout = editor_jobs.load_or_init_constructor_layout(safe_job_id)
    files = list(files)
    if not files:
        return _error_result("No se enviaron PDFs")

    designs = editor_uploads.append_uploaded_designs(
        job_dir=job_dir,
        layout=layout,
        files=files,
        work_id_form=work_id_form,
    )
    editor_jobs.save_constructor_layout(job_dir, layout)
    return EditorHttpResult({"designs": designs})


def generate_auto_layout(
    job_id: str,
    payload_layout: Dict | None,
    generate_slots_with_ai: Callable[[Dict, str], Dict],
) -> EditorHttpResult:
    safe_job_id = editor_jobs.safe_job_id(job_id)
    if not safe_job_id:
        return _error_result("job_id invÃ¡lido")
    job_dir = editor_jobs.constructor_job_dir(safe_job_id)
    layout = (
        payload_layout
        or editor_jobs.load_constructor_layout(job_dir)
        or editor_layout_defaults.default_constructor_layout()
    )
    updated = generate_slots_with_ai(layout, job_dir)
    return EditorHttpResult({"ok": True, "layout": updated})


def apply_imposition(
    job_id_raw: str | None,
    payload_layout: Dict | None,
    selected_engine: str | None = None,
) -> EditorHttpResult:
    job_id = editor_jobs.safe_job_id(job_id_raw)
    if not job_id:
        return _error_result("job_id invÃ¡lido")

    job_dir, stored_layout = editor_jobs.load_or_init_constructor_layout(job_id)
    layout = payload_layout or stored_layout or editor_layout_defaults.default_constructor_layout()
    layout, _ = editor_layout_defaults.ensure_faces_fields(layout)
    layout, _ = editor_layout_defaults.ensure_imposition_fields(layout)

    if not layout.get("designs"):
        return _error_result("ConfigurÃ¡ al menos un diseÃ±o con sus formas por pliego antes de aplicar la imposiciÃ³n.")

    engine = editor_imposition.select_imposition_engine(layout, payload_layout, selected_engine)
    layout["imposition_engine"] = engine

    try:
        layout_for_engine = deepcopy(layout)
        layout_for_engine["slots"] = []
        slots = editor_imposition.apply_imposition_engine(layout_for_engine, engine)
    except editor_imposition.IncompleteImpositionError as exc:
        current_app.logger.warning(
            "Imposicion incompleta en Step & Repeat PRO para job %s: %s | details=%s",
            job_id,
            str(exc),
            exc.details,
        )
        return _error_result(str(exc), details=exc.details)
    except ValueError as exc:
        return _error_result(str(exc))

    layout["slots"] = slots
    editor_jobs.save_constructor_layout(job_dir, layout)
    return EditorHttpResult({"ok": True, "layout": layout})


def generate_preview(job_id: str) -> EditorHttpResult:
    safe_job_id = editor_jobs.safe_job_id(job_id)
    if not safe_job_id:
        return _error_result("job_id invÃ¡lido")
    job_dir, layout = editor_jobs.load_or_init_constructor_layout(safe_job_id)
    errors, warnings = validate_constructor_output_layout(layout)
    if errors:
        return _error_result(
            "El layout contiene errores de contrato y no se puede generar la preview.",
            422,
            errors=errors,
            warnings=warnings,
        )
    preview_path = montar_offset_desde_layout(layout, job_dir, preview=True)
    rel = os.path.relpath(preview_path, current_app.static_folder).replace("\\", "/")
    return EditorHttpResult({"ok": True, "url": url_for("static", filename=rel), "warnings": warnings})


def generate_pdf(job_id: str) -> EditorHttpResult:
    safe_job_id = editor_jobs.safe_job_id(job_id)
    if not safe_job_id:
        return _error_result("job_id invÃ¡lido")
    job_dir, layout = editor_jobs.load_or_init_constructor_layout(safe_job_id)
    errors, warnings = validate_constructor_output_layout(layout)
    if errors:
        return _error_result(
            "El layout contiene errores de contrato y no se puede generar el PDF final.",
            422,
            errors=errors,
            warnings=warnings,
        )
    pdf_path = montar_offset_desde_layout(layout, job_dir, preview=False)
    rel = os.path.relpath(pdf_path, current_app.static_folder).replace("\\", "/")
    return EditorHttpResult({"ok": True, "url": url_for("static", filename=rel), "warnings": warnings})
