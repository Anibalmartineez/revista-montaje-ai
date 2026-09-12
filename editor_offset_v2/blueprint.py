"""Flask blueprint for the isolated Editor Offset Visual V2 shell."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
)

from editor_offset_v2.application.asset_service import (
    AssetService,
    AssetServiceError,
)
from editor_offset_v2.application.job_service import JobService, JobServiceError
from editor_offset_v2.application.output_service import validate_output_capabilities
from editor_offset_v2.application.pdf_final_service import PdfFinalService, PdfFinalServiceError
from editor_offset_v2.application.derived_asset_service import DerivedAssetService, DerivedAssetServiceError
from editor_offset_v2.application.preflight_service import PreflightService, PreflightServiceError
from editor_offset_v2.application.preview_service import (
    PREVIEW_DEFAULT_DPI,
    PreviewService,
    PreviewServiceError,
)
from editor_offset_v2.application.repeat_service import RepeatService, RepeatServiceError
from editor_offset_v2.config import (
    EDITOR_OFFSET_V2_ENABLED,
    EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED,
    EDITOR_OFFSET_V2_PREVIEW_ENABLED,
    EDITOR_OFFSET_V2_PDF_FINAL_ENABLED,
    EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED,
    EDITOR_OFFSET_V2_JOBS_ROOT,
    EDITOR_OFFSET_V2_MAX_UPLOAD_BYTES,
    configure_editor_offset_v2,
)
from editor_offset_v2.infrastructure.asset_repository import AssetRepository
from editor_offset_v2.infrastructure.job_repository import JobRepository


editor_offset_v2_bp = Blueprint("editor_offset_v2", __name__)


def _is_enabled() -> bool:
    return current_app.config.get(EDITOR_OFFSET_V2_ENABLED) is True


def _job_service() -> JobService:
    jobs_root = Path(current_app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
    return JobService(JobRepository(jobs_root))


def _job_repository() -> JobRepository:
    return JobRepository(Path(current_app.config[EDITOR_OFFSET_V2_JOBS_ROOT]))


def _asset_service() -> AssetService:
    jobs_root = Path(current_app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
    repository = JobRepository(jobs_root)
    return AssetService(
        JobService(repository),
        AssetRepository(repository),
        max_upload_bytes=current_app.config[EDITOR_OFFSET_V2_MAX_UPLOAD_BYTES],
    )


def _repeat_service() -> RepeatService:
    return RepeatService(_job_service())


def _derived_asset_service() -> DerivedAssetService:
    repository = _job_repository()
    return DerivedAssetService(_job_service(), AssetRepository(repository), repository)


def _error_payload(error: JobServiceError | AssetServiceError | RepeatServiceError | PreflightServiceError | PreviewServiceError):
    payload: dict[str, Any] = {
        "ok": False,
        "error": {
            "code": error.code,
            "message": error.message,
        },
    }
    if error.issues:
        payload["error"]["issues"] = list(error.issues)
    return jsonify(payload), error.status_code


@editor_offset_v2_bp.before_request
def require_editor_offset_v2_enabled():
    if _is_enabled():
        return None
    if request.path.startswith("/api/editor-offset-v2/"):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": {
                        "code": "V2_DISABLED",
                        "message": "Editor Offset Visual V2 is disabled",
                    },
                }
            ),
            404,
        )
    abort(404)


@editor_offset_v2_bp.get("/editor_offset_visual_v2")
def editor_shell():
    context = {
        "job_id": None,
        "revision": None,
        "job_name": None,
        "layout": None,
        "create_job_url": url_for("editor_offset_v2.create_job"),
        "job_api_url": None,
        "save_layout_url": None,
        "assets_api_url": None,
        "repeat_api_url": None,
        "output_capabilities_api_url": None,
        "preflight_api_url": None,
        "preview_api_url": None,
        "pdf_final_api_url": None,
        "derived_assets_enabled": False,
        "dev_tools_enabled": current_app.config.get(
            EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED
        ) is True,
    }
    return render_template("editor_offset_visual_v2.html", editor_context=context)


@editor_offset_v2_bp.get("/editor_offset_visual_v2/<job_id>")
def editor_with_job(job_id: str):
    try:
        result = _job_service().get_job(job_id)
    except JobServiceError as error:
        abort(404 if error.code in {"JOB_NOT_FOUND", "INVALID_JOB_ID"} else 500)
    context = {
        "job_id": result.job_id,
        "revision": result.revision,
        "job_name": result.layout["job"]["name"],
        "layout": result.layout,
        "create_job_url": url_for("editor_offset_v2.create_job"),
        "job_api_url": url_for(
            "editor_offset_v2.get_job",
            job_id=result.job_id,
        ),
        "save_layout_url": url_for(
            "editor_offset_v2.save_job_layout",
            job_id=result.job_id,
        ),
        "assets_api_url": url_for(
            "editor_offset_v2.upload_asset",
            job_id=result.job_id,
        ),
        "repeat_api_url": url_for(
            "editor_offset_v2.propose_repeat",
            job_id=result.job_id,
        ),
        "output_capabilities_api_url": url_for(
            "editor_offset_v2.output_capabilities",
            job_id=result.job_id,
        ),
        "preflight_api_url": url_for(
            "editor_offset_v2.preflight",
            job_id=result.job_id,
        ),
        "preview_api_url": url_for(
            "editor_offset_v2.preview",
            job_id=result.job_id,
        ) if current_app.config.get(EDITOR_OFFSET_V2_PREVIEW_ENABLED) is True else None,
        "pdf_final_api_url": url_for(
            "editor_offset_v2.pdf_final",
            job_id=result.job_id,
        ) if current_app.config.get(EDITOR_OFFSET_V2_PDF_FINAL_ENABLED) is True else None,
        "derived_assets_enabled": current_app.config.get(EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED) is True,
        "dev_tools_enabled": current_app.config.get(
            EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED
        ) is True,
    }
    return render_template("editor_offset_visual_v2.html", editor_context=context)


@editor_offset_v2_bp.post("/api/editor-offset-v2/jobs")
def create_job():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _error_payload(
            JobServiceError(
                "INVALID_LAYOUT",
                "Request body must be a JSON object",
                400,
            )
        )
    if "job_id" in payload:
        return _error_payload(
            JobServiceError(
                "INVALID_JOB_ID",
                "job_id is generated exclusively by the server",
                400,
            )
        )
    unexpected = set(payload) - {"name"}
    if unexpected:
        return _error_payload(
            JobServiceError(
                "INVALID_LAYOUT",
                "Request body contains unsupported fields",
                400,
            )
        )
    try:
        result = _job_service().create_job(payload.get("name"))
    except JobServiceError as error:
        return _error_payload(error)
    open_url = url_for("editor_offset_v2.editor_with_job", job_id=result.job_id)
    return (
        jsonify(
            {
                "ok": True,
                "job_id": result.job_id,
                "revision": result.revision,
                "open_url": open_url,
                "layout": result.layout,
            }
        ),
        201,
    )


@editor_offset_v2_bp.get("/api/editor-offset-v2/jobs/<job_id>")
def get_job(job_id: str):
    try:
        result = _job_service().get_job(job_id)
    except JobServiceError as error:
        return _error_payload(error)
    return jsonify(
        {
            "ok": True,
            "job_id": result.job_id,
            "revision": result.revision,
            "open_url": url_for(
                "editor_offset_v2.editor_with_job",
                job_id=result.job_id,
            ),
            "layout": result.layout,
        }
    )


@editor_offset_v2_bp.post("/api/editor-offset-v2/jobs/<job_id>/assets")
def upload_asset(job_id: str):
    raw_revision = request.form.get("base_revision")
    base_revision: object = (
        int(raw_revision)
        if isinstance(raw_revision, str) and raw_revision.isdecimal()
        else raw_revision
    )
    try:
        result = _asset_service().upload_pdf(
            job_id,
            base_revision,
            request.files.get("file"),
        )
    except (AssetServiceError, JobServiceError) as error:
        return _error_payload(error)
    return (
        jsonify(
            {
                "ok": True,
                "job_id": result.job_id,
                "asset_id": result.asset_id,
                "revision": result.revision,
                "asset": result.asset,
                "layout": result.layout,
            }
        ),
        201,
    )


@editor_offset_v2_bp.get(
    "/api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/thumbnails/<page>"
)
def asset_thumbnail(job_id: str, asset_id: str, page: str):
    page_number: object = int(page) if page.isdecimal() else page
    try:
        if "box" in request.args:
            data = _asset_service().box_thumbnail(job_id, asset_id, page_number, request.args["box"])
            return send_file(io.BytesIO(data), mimetype="image/png", conditional=True,
                             etag=hashlib.sha256(data).hexdigest(), max_age=3600)
        path = _asset_service().thumbnail_path(job_id, asset_id, page_number)
    except (AssetServiceError, JobServiceError) as error:
        return _error_payload(error)
    return send_file(
        path,
        mimetype="image/png",
        conditional=True,
        max_age=3600,
    )


@editor_offset_v2_bp.post(
    "/api/editor-offset-v2/jobs/<job_id>/imposition/repeat"
)
def propose_repeat(job_id: str):
    payload = request.get_json(silent=True)
    try:
        result = _repeat_service().propose(job_id, payload)
    except (RepeatServiceError, JobServiceError) as error:
        return _error_payload(error)
    return jsonify({"ok": True, "result": result.as_dict()})


@editor_offset_v2_bp.get(
    "/api/editor-offset-v2/jobs/<job_id>/output-capabilities"
)
def output_capabilities(job_id: str):
    try:
        result = _job_service().get_job(job_id)
    except JobServiceError as error:
        return _error_payload(error)
    issues = tuple(validate_output_capabilities(result.layout))
    errors = [issue.as_dict() for issue in issues if issue.level == "error"]
    warnings = [issue.as_dict() for issue in issues if issue.level == "warning"]
    return jsonify(
        {
            "ok": True,
            "job_id": result.job_id,
            "revision": result.revision,
            "compatible": not errors,
            "errors": errors,
            "warnings": warnings,
            "issues": [issue.as_dict() for issue in issues],
        }
    )


@editor_offset_v2_bp.post(
    "/api/editor-offset-v2/jobs/<job_id>/preflight"
)
def preflight(job_id: str):
    payload = request.get_json(silent=True)
    if payload is not None and not isinstance(payload, dict):
        return _error_payload(
            PreflightServiceError(
                "INVALID_PREFLIGHT_REQUEST",
                "Request body must be a JSON object",
                400,
            )
        )
    if isinstance(payload, dict) and payload:
        return _error_payload(
            PreflightServiceError(
                "INVALID_PREFLIGHT_REQUEST",
                "Preflight does not accept options in this phase",
                400,
            )
        )
    try:
        report = PreflightService(_job_repository()).run(
            job_id,
            enabled_operations={
                "preview": current_app.config.get(EDITOR_OFFSET_V2_PREVIEW_ENABLED) is True,
                "pdf_final": current_app.config.get(EDITOR_OFFSET_V2_PDF_FINAL_ENABLED) is True,
                "ctp": False,
            },
        )
    except PreflightServiceError as error:
        return _error_payload(error)
    return jsonify({"ok": True, "report": report}), 201


@editor_offset_v2_bp.post("/api/editor-offset-v2/jobs/<job_id>/preview")
def preview(job_id: str):
    if current_app.config.get(EDITOR_OFFSET_V2_PREVIEW_ENABLED) is not True:
        return _error_payload(
            PreviewServiceError(
                "PREVIEW_DISABLED",
                "Editor Offset Visual V2 Preview is disabled",
                404,
            )
        )
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _error_payload(
            PreviewServiceError(
                "INVALID_PREVIEW_REQUEST",
                "Request body must be a JSON object",
                400,
            )
        )
    unexpected = set(payload) - {"face", "dpi", "allow_mirror_bleed"}
    if unexpected:
        return _error_payload(
            PreviewServiceError(
                "INVALID_PREVIEW_REQUEST",
                "Request body contains unsupported fields",
                400,
            )
        )
    try:
        result = PreviewService(_job_repository()).render(
            job_id,
            face=payload.get("face", "front"),
            dpi=payload.get("dpi", PREVIEW_DEFAULT_DPI),
            allow_mirror_bleed=payload.get("allow_mirror_bleed", False),
        )
    except PreviewServiceError as error:
        return _error_payload(error)
    return send_file(
        result.path,
        mimetype="image/png",
        conditional=True,
        etag=result.sha256,
        max_age=3600,
    )


@editor_offset_v2_bp.post(
    "/api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/derived-page"
)
def derived_page(job_id: str, asset_id: str):
    if current_app.config.get(EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED) is not True:
        return _error_payload(
            DerivedAssetServiceError(
                "DERIVED_ASSETS_DISABLED",
                "Derived V2 asset pages are disabled",
                404,
            )
        )
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _error_payload(DerivedAssetServiceError(
            "INVALID_DERIVED_REQUEST", "Request body must be a JSON object", 400,
        ))
    unexpected = set(payload) - {"page", "pdf_box", "bleed_mm", "allow_mirror_bleed", "content_transform"}
    if unexpected:
        return _error_payload(DerivedAssetServiceError(
            "INVALID_DERIVED_REQUEST", "Request body contains unsupported fields", 400,
        ))
    try:
        result = _derived_asset_service().materialize_page(
            job_id,
            asset_id,
            payload.get("page"),
            pdf_box=payload.get("pdf_box", "trim"),
            bleed_mm=payload.get("bleed_mm", 0),
            allow_mirror_bleed=payload.get("allow_mirror_bleed", False),
            content_transform=payload.get("content_transform"),
        )
    except DerivedAssetServiceError as error:
        return _error_payload(error)
    return jsonify({"ok": True, "result": {
        "asset_id": result.asset_id,
        "page": result.page_number,
        "derived_key": result.derived_key,
        "sha256": result.sha256,
        "manifest": result.manifest,
    }}), 201


@editor_offset_v2_bp.post("/api/editor-offset-v2/jobs/<job_id>/pdf-final")
def pdf_final(job_id: str):
    if current_app.config.get(EDITOR_OFFSET_V2_PDF_FINAL_ENABLED) is not True:
        return _error_payload(
            PdfFinalServiceError(
                "PDF_FINAL_DISABLED",
                "Editor Offset Visual V2 PDF final is disabled",
                404,
            )
        )
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _error_payload(
            PdfFinalServiceError(
                "INVALID_PDF_FINAL_REQUEST",
                "Request body must be a JSON object",
                400,
            )
        )
    unexpected = set(payload) - {"face", "dpi", "allow_mirror_bleed"}
    if unexpected:
        return _error_payload(
            PdfFinalServiceError(
                "INVALID_PDF_FINAL_REQUEST",
                "Request body contains unsupported fields",
                400,
            )
        )
    try:
        result = PdfFinalService(_job_repository()).render(
            job_id,
            face=payload.get("face", "front"),
            dpi=payload.get("dpi", PREVIEW_DEFAULT_DPI),
            allow_mirror_bleed=payload.get("allow_mirror_bleed", False),
        )
    except PdfFinalServiceError as error:
        return _error_payload(error)
    return send_file(
        result.path,
        mimetype="application/pdf",
        conditional=True,
        etag=result.sha256,
        max_age=3600,
    )


@editor_offset_v2_bp.put("/api/editor-offset-v2/jobs/<job_id>/layout")
def save_job_layout(job_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _error_payload(
            JobServiceError(
                "INVALID_LAYOUT",
                "Request body must be a JSON object",
                400,
            )
        )
    if set(payload) != {"base_revision", "layout"}:
        return _error_payload(
            JobServiceError(
                "INVALID_LAYOUT",
                "Request body must contain only base_revision and layout",
                400,
            )
        )
    try:
        result = _job_service().save_layout(
            job_id,
            payload["base_revision"],
            payload["layout"],
        )
    except JobServiceError as error:
        return _error_payload(error)
    return jsonify(
        {
            "ok": True,
            "job_id": result.job_id,
            "revision": result.revision,
            "layout": result.layout,
        }
    )


def init_editor_offset_v2(app: Flask) -> None:
    """Configure and register the V2 blueprint exactly once."""

    configure_editor_offset_v2(app)
    if editor_offset_v2_bp.name not in app.blueprints:
        app.register_blueprint(editor_offset_v2_bp)


__all__ = [
    "editor_offset_v2_bp",
    "init_editor_offset_v2",
]
