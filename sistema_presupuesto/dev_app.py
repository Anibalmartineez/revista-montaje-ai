"""App de desarrollo aislada para previsualizar la UI del Sistema Presupuesto."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, send_from_directory

from .api import presupuesto_api_bp

MODULE_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = MODULE_ROOT / "frontend"
TEMPLATE_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"


def create_dev_app() -> Flask:
    app = Flask(__name__)
    app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = os.environ.get(
        "SISTEMA_PRESUPUESTO_DATA_DIR",
        str(MODULE_ROOT / "data"),
    )
    app.register_blueprint(presupuesto_api_bp)

    @app.get("/")
    @app.get("/sistema-presupuesto-ui")
    def presupuesto_ui():
        html = (TEMPLATE_DIR / "presupuesto_offset_app.html").read_text(encoding="utf-8")
        return Response(html, mimetype="text/html")

    @app.get("/sistema-presupuesto-ui/static/<path:filename>")
    def presupuesto_static(filename: str):
        return send_from_directory(STATIC_DIR, filename)

    return app


if __name__ == "__main__":
    create_dev_app().run(debug=True, port=5057)
