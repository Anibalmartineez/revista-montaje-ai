import json
import os
from typing import Dict

from flask import current_app

from services.editor_offset_layout_defaults import (
    default_constructor_layout,
    ensure_constructor_layout_defaults,
)


POST_EDITOR_DIR = "ia_jobs"
LAYOUT_FILENAME = "layout.json"
META_FILENAME = "meta.json"
ASSETS_DIRNAME = "assets"
ORIGINAL_PDF_NAME = "pliego.pdf"
EDITED_PDF_NAME = "pliego_edit.pdf"
EDITED_PREVIEW_NAME = "preview_edit.png"
CONSTRUCTOR_DIRNAME = "constructor_offset_jobs"
CONSTRUCTOR_LAYOUT_NAME = "layout_constructor.json"


def safe_job_id(job_id: str | None) -> str | None:
    if not job_id:
        return None
    token = job_id.strip()
    if not token or not token.isalnum():
        return None
    return token


def jobs_root() -> str:
    root = os.path.join(current_app.static_folder, POST_EDITOR_DIR)
    os.makedirs(root, exist_ok=True)
    return root


def job_dir(job_id: str | None) -> str | None:
    token = safe_job_id(job_id)
    if not token:
        return None
    path = os.path.join(jobs_root(), token)
    return path


def job_relpath(job_id: str, *parts: str) -> str:
    return os.path.join(POST_EDITOR_DIR, job_id, *parts).replace("\\", "/")


def static_web_relpath(abs_path: str) -> str:
    return os.path.relpath(abs_path, current_app.static_folder).replace("\\", "/")


def layout_path(job_dir: str) -> str:
    return os.path.join(job_dir, LAYOUT_FILENAME)


def meta_path(job_dir: str) -> str:
    return os.path.join(job_dir, META_FILENAME)


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def constructor_root() -> str:
    root = os.path.join(current_app.static_folder, CONSTRUCTOR_DIRNAME)
    os.makedirs(root, exist_ok=True)
    return root


def constructor_job_dir(job_id: str) -> str:
    return os.path.join(constructor_root(), job_id)


def constructor_layout_path(job_dir: str) -> str:
    return os.path.join(job_dir, CONSTRUCTOR_LAYOUT_NAME)


def load_constructor_layout(job_dir: str) -> Dict | None:
    path = constructor_layout_path(job_dir)
    if not os.path.exists(path):
        return None
    return load_json(path)


def save_constructor_layout(job_dir: str, layout: Dict) -> str:
    os.makedirs(job_dir, exist_ok=True)
    path = constructor_layout_path(job_dir)
    save_json(path, layout)
    return path


def load_or_init_constructor_layout(job_id: str) -> tuple[str, Dict]:
    job_dir_path = constructor_job_dir(job_id)
    layout = load_constructor_layout(job_dir_path)
    if layout is None:
        layout = default_constructor_layout()
        save_constructor_layout(job_dir_path, layout)
    else:
        layout, changed = ensure_constructor_layout_defaults(layout)
        if changed:
            save_constructor_layout(job_dir_path, layout)
    return job_dir_path, layout
