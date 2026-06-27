"""Configuration for the isolated PDF Medidor Pro module."""

from __future__ import annotations

from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = MODULE_ROOT / "templates"
STATIC_DIR = MODULE_ROOT / "static"
UPLOAD_DIR = MODULE_ROOT / "uploads"
PREVIEW_DIR = MODULE_ROOT / "previews"
EXPORT_DIR = MODULE_ROOT / "exports"

ALLOWED_EXTENSIONS = {".pdf"}
DEFAULT_RENDER_DPI = 150


def ensure_runtime_dirs() -> None:
    """Create runtime folders used by the module."""

    for path in (UPLOAD_DIR, PREVIEW_DIR, EXPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)
