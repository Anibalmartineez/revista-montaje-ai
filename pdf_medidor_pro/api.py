"""Flask blueprint for the isolated PDF Medidor Pro module."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from .config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_RENDER_DPI,
    EXPORT_DIR,
    PREVIEW_DIR,
    STATIC_DIR,
    UPLOAD_DIR,
    ensure_runtime_dirs,
)
from .services.export_json import build_export_payload
from .services.ai_measure_engine import count_label_candidates, detect_measurement_near, detect_printed_measurement
from .services.pdf_analyzer import analyze_pdf_boxes
from .services.pdf_renderer import render_first_page


def create_pdf_medidor_pro_blueprint() -> Blueprint:
    """Create the isolated PDF Medidor Pro blueprint."""

    bp = Blueprint(
        "pdf_medidor_pro",
        __name__,
        template_folder="templates",
    )

    @bp.get("/pdf-medidor-pro")
    def ui():
        return render_template("pdf_medidor_pro.html")

    @bp.get("/pdf-medidor-pro/static/<path:filename>")
    def static_file(filename: str):
        return send_from_directory(STATIC_DIR, filename)

    @bp.get("/pdf-medidor-pro/previews/<path:filename>")
    def preview_file(filename: str):
        return send_from_directory(PREVIEW_DIR, filename)

    @bp.get("/api/pdf-medidor-pro/health")
    def health():
        return jsonify({"ok": True, "service": "pdf_medidor_pro", "status": "ready"})

    @bp.post("/api/pdf-medidor-pro/upload")
    def upload_pdf():
        ensure_runtime_dirs()
        file = request.files.get("pdf")
        if file is None or not file.filename:
            return _error("PDF_REQUIRED", "Debes subir un archivo PDF.", 400)

        safe_name = secure_filename(file.filename) or "trabajo.pdf"
        if Path(safe_name).suffix.lower() not in ALLOWED_EXTENSIONS:
            return _error("INVALID_EXTENSION", "Solo se permiten archivos PDF.", 400)

        upload_id = uuid4().hex
        stored_filename = f"{upload_id}_{safe_name}"
        pdf_path = UPLOAD_DIR / stored_filename
        file.save(pdf_path)

        try:
            analysis = analyze_pdf_boxes(pdf_path)
            dpi = int(current_app.config.get("PDF_MEDIDOR_PRO_DPI", DEFAULT_RENDER_DPI))
            preview_filename = f"{Path(stored_filename).stem}.png"
            preview_info = render_first_page(pdf_path, PREVIEW_DIR / preview_filename, dpi=dpi)
        except Exception as exc:
            pdf_path.unlink(missing_ok=True)
            return _error("PDF_ANALYSIS_FAILED", str(exc), 400)

        preview_url = url_for("pdf_medidor_pro.preview_file", filename=preview_filename)
        return jsonify(
            {
                "ok": True,
                "upload_id": upload_id,
                "archivo": safe_name,
                "stored_filename": stored_filename,
                "pagina": analysis["pagina"],
                "page_count": analysis["page_count"],
                "medidas_auto": analysis["medidas_auto"],
                "render_mm": analysis["render_mm"],
                "preview": {**preview_info, "url": preview_url},
                "preview_url": preview_url,
            }
        )

    @bp.post("/api/pdf-medidor-pro/ai/detect")
    def ai_detect():
        payload = request.get_json(silent=True) or {}
        preview_path = _preview_path_from_payload(payload)
        if preview_path is None:
            return _error("PREVIEW_REQUIRED", "Preview no encontrado.", 400)
        try:
            measurement = detect_measurement_near(
                preview_path,
                x_mm=float(payload.get("x_mm") or 0),
                y_mm=float(payload.get("y_mm") or 0),
                render_mm=_render_mm(payload),
                name=str(payload.get("nombre") or "Objeto detectado (IA)"),
            )
        except Exception as exc:
            return _error("AI_DETECT_FAILED", str(exc), 400)
        if measurement is None:
            return _error("AI_OBJECT_NOT_FOUND", "No se detecto un objeto cerca del clic.", 404)
        return jsonify({"ok": True, "measurement": measurement})

    @bp.post("/api/pdf-medidor-pro/ai/printed-area")
    def ai_printed_area():
        payload = request.get_json(silent=True) or {}
        preview_path = _preview_path_from_payload(payload)
        if preview_path is None:
            return _error("PREVIEW_REQUIRED", "Preview no encontrado.", 400)
        measurement = detect_printed_measurement(preview_path, render_mm=_render_mm(payload))
        if measurement is None:
            return _error("AI_OBJECT_NOT_FOUND", "No se detecto area impresa.", 404)
        return jsonify({"ok": True, "measurement": measurement})

    @bp.post("/api/pdf-medidor-pro/ai/count")
    def ai_count():
        payload = request.get_json(silent=True) or {}
        preview_path = _preview_path_from_payload(payload)
        if preview_path is None:
            return _error("PREVIEW_REQUIRED", "Preview no encontrado.", 400)
        return jsonify({"ok": True, **count_label_candidates(preview_path)})

    @bp.post("/api/pdf-medidor-pro/export")
    def export_json():
        ensure_runtime_dirs()
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return _error("INVALID_JSON", "El cuerpo debe ser un objeto JSON.", 400)

        export_payload = build_export_payload(
            archivo=str(payload.get("archivo") or "trabajo.pdf"),
            pagina=int(payload.get("pagina") or 1),
            medidas_auto=payload.get("medidas_auto"),
            medidas_manual=payload.get("medidas_manual"),
            calibracion=payload.get("calibracion"),
            mediciones=payload.get("mediciones"),
            origen_medida_final=str(payload.get("origen_medida_final") or "manual"),
            confianza=str(payload.get("confianza") or "alta"),
        )

        export_filename = f"pdf_medidor_pro_{uuid4().hex}.json"
        export_path = EXPORT_DIR / export_filename
        export_path.write_text(
            json.dumps(export_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return jsonify(
            {
                "ok": True,
                "export": export_payload,
                "filename": export_filename,
                "url": url_for("pdf_medidor_pro.export_file", filename=export_filename),
            }
        )

    @bp.get("/api/pdf-medidor-pro/exports/<path:filename>")
    def export_file(filename: str):
        return send_from_directory(EXPORT_DIR, filename, as_attachment=False)

    return bp


def _error(code: str, message: str, status: int):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def _preview_path_from_payload(payload: dict) -> Path | None:
    raw = str(payload.get("preview_filename") or payload.get("preview") or "")
    filename = secure_filename(Path(raw).name)
    if not filename:
        return None
    path = PREVIEW_DIR / filename
    return path if path.exists() else None


def _render_mm(payload: dict) -> dict[str, float]:
    render_mm = payload.get("render_mm") if isinstance(payload.get("render_mm"), dict) else {}
    return {
        "ancho": float(render_mm.get("ancho") or payload.get("ancho_mm") or 0),
        "alto": float(render_mm.get("alto") or payload.get("alto_mm") or 0),
    }


pdf_medidor_pro_bp = create_pdf_medidor_pro_blueprint()
