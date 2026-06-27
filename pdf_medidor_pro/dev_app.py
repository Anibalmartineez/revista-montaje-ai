"""Development app for running PDF Medidor Pro in isolation."""

from __future__ import annotations

from flask import Flask

from .api import pdf_medidor_pro_bp
from .config import ensure_runtime_dirs


def create_dev_app() -> Flask:
    ensure_runtime_dirs()
    app = Flask(__name__)
    app.config.setdefault("MAX_CONTENT_LENGTH", 32 * 1024 * 1024)
    app.register_blueprint(pdf_medidor_pro_bp)
    return app


if __name__ == "__main__":
    create_dev_app().run(debug=True, port=5058)
