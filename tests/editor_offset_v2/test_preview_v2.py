from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import fitz
import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import EDITOR_OFFSET_V2_PREVIEW_ENABLED
from editor_offset_v2.infrastructure.pdf_inspector import POINT_TO_MM


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "layout_v2_complete.json"


@pytest.fixture
def preview_app_factory(tmp_path):
    def create(enabled: bool = True) -> Flask:
        app = Flask(
            __name__,
            template_folder=str(REPO_ROOT / "templates"),
            static_folder=str(REPO_ROOT / "static"),
            instance_path=str(tmp_path / "instance"),
        )
        app.config.update(
            TESTING=True,
            EDITOR_OFFSET_V2_ENABLED=enabled,
            EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
        )
        init_editor_offset_v2(app)
        return app

    return create


def create_job(client, name="Preview V2") -> dict:
    response = client.post("/api/editor-offset-v2/jobs", json={"name": name})
    assert response.status_code == 201
    return response.get_json()


def _source_pdf() -> bytes:
    points = 1 / POINT_TO_MM
    document = fitz.open()
    page = document.new_page(width=90 * points, height=50 * points)
    page.insert_text((18, 28), "PREVIEW-V2", fontsize=12, color=(0.1, 0.2, 0.8))
    document.xref_set_key(page.xref, "TrimBox", f"[0 0 {90 * points} {50 * points}]")
    data = document.tobytes(garbage=4, deflate=False, no_new_id=True)
    document.close()
    return data


def _preview_layout(base: dict, asset: dict) -> dict:
    complete = json.loads(COMPLETE_FIXTURE.read_text(encoding="utf-8"))
    layout = copy.deepcopy(base)
    work = copy.deepcopy(complete["works"][0])
    slot = copy.deepcopy(complete["slots"][0])
    work["id"] = "work_preview"
    work["front_source"] = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    work["back_source"] = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    slot["work_id"] = work["id"]
    slot["source"] = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    slot["geometry"]["bleed_mm"] = 0.0
    slot["content_transform"]["clip_to"] = "trim_box"
    layout["assets"] = [asset]
    layout["works"] = [work]
    layout["slots"] = [slot]
    layout["faces"] = {"enabled": ["front"], "duplex": {"enabled": False, "flip": "none"}}
    layout["export"]["faces"] = {
        "front": True,
        "back": False,
        "combine_in_single_pdf": False,
        "order": ["front"],
    }
    layout["export"]["marks_profiles"][0].update({
        "crop_marks": False,
        "registration_marks": False,
        "technical_text": False,
        "color_bar": False,
    })
    layout["ctp"]["enabled"] = False
    return layout


def _save_preview_layout(client, created: dict, layout: dict) -> dict:
    response = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": created["revision"], "layout": layout},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_preview_endpoint_is_separately_gated_and_default_off(preview_app_factory):
    client = preview_app_factory().test_client()
    created = create_job(client)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PREVIEW_DISABLED"


def test_preview_request_rejects_non_object_and_invalid_face(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client)

    non_object = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json=[],
    )
    invalid_face = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": []},
    )

    assert non_object.status_code == 400
    assert non_object.get_json()["error"]["code"] == "INVALID_PREVIEW_REQUEST"
    assert invalid_face.status_code == 400
    assert invalid_face.get_json()["error"]["code"] == "INVALID_PREVIEW_FACE"


def test_gated_preview_renders_a_face_without_mutating_layout(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client)
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    saved = _save_preview_layout(client, upload.get_json(), layout)
    before = client.get(f"/api/editor-offset-v2/jobs/{created['job_id']}").get_json()

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": "front", "dpi": 36},
    )

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert response.content_length == len(response.data)
    assert client.get(f"/api/editor-offset-v2/jobs/{created['job_id']}").get_json() == before
    preview_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "previews"
    assert list(preview_dir.glob(f"preview_r{saved['revision']}_front_36.png"))


def test_preview_rejects_marks_and_non_identity_internal_transforms(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client)
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    layout["export"]["marks_profiles"][0]["crop_marks"] = True
    saved = _save_preview_layout(client, upload.get_json(), layout)

    marked = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )
    assert marked.status_code == 422
    assert marked.get_json()["error"]["code"] == "PREVIEW_MARKS_UNSUPPORTED"

    layout["job"]["revision"] = saved["revision"]
    layout["export"]["marks_profiles"][0]["crop_marks"] = False
    layout["slots"][0]["content_transform"]["offset_mm"]["x"] = 1.0
    updated = _save_preview_layout(client, saved, layout)
    transformed = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )
    assert updated["revision"] == saved["revision"] + 1
    assert transformed.status_code == 422
    assert transformed.get_json()["error"]["code"] == "PREVIEW_TRANSFORM_UNSUPPORTED"
