"""Flask blueprint for the isolated Editor Offset Visual V2 shell."""

from __future__ import annotations

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
    url_for,
)

from editor_offset_v2.application.job_service import JobService, JobServiceError
from editor_offset_v2.config import (
    EDITOR_OFFSET_V2_ENABLED,
    EDITOR_OFFSET_V2_JOBS_ROOT,
    configure_editor_offset_v2,
)
from editor_offset_v2.infrastructure.job_repository import JobRepository


editor_offset_v2_bp = Blueprint("editor_offset_v2", __name__)


def _is_enabled() -> bool:
    return current_app.config.get(EDITOR_OFFSET_V2_ENABLED) is True


def _job_service() -> JobService:
    jobs_root = Path(current_app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
    return JobService(JobRepository(jobs_root))


def _error_payload(error: JobServiceError):
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
