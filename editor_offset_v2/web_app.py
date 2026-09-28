"""Exclusive V2 host; never imports the coexistence application or V1 routes."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from flask import Flask, abort, jsonify, redirect, send_from_directory, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from editor_offset_v2.blueprint import init_editor_offset_v2


REPO_ROOT = Path(__file__).resolve().parents[1]


def create_app(config: dict | None = None) -> Flask:
    """Keep existing resources and jobs, with an exclusively V2 route table."""
    app = Flask(
        __name__,
        template_folder=str(REPO_ROOT / "templates"),
        static_folder=None,
        instance_path=str(REPO_ROOT / "instance"),
    )
    app.config.update(MAX_CONTENT_LENGTH=32 * 1024 * 1024)
    app.config["EDITOR_OFFSET_V2_ENABLED"] = True
    if os.environ.get("EDITOR_OFFSET_V2_JOBS_ROOT"):
        app.config["EDITOR_OFFSET_V2_JOBS_ROOT"] = os.environ["EDITOR_OFFSET_V2_JOBS_ROOT"]
    if config:
        app.config.update(config)
    init_editor_offset_v2(app)

    @app.get("/")
    def index():
        return redirect(url_for("editor_offset_v2.editor_shell"))

    @app.get("/health/editor-offset-v2")
    def health():
        return jsonify(application="editor-offset-v2", hosting="exclusive", layout_schema_version=2)

    @app.get("/static/<path:filename>", endpoint="static")
    def v2_static(filename):
        path = PurePosixPath(filename)
        allowed = filename in {
            "css/editor_offset_visual_v2.css", "js/editor_offset_visual_v2.js",
        } or (str(path.parent) == "js/editor_offset_v2" and path.suffix == ".js")
        if not allowed:
            abort(404)
        return send_from_directory(REPO_ROOT / "static", filename)

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(error):
        return jsonify(ok=False, error="Payload demasiado grande. El límite es de 32 MiB."), 413

    return app
