from __future__ import annotations

import copy
import io
from pathlib import Path

import fitz
import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import EDITOR_OFFSET_V2_PDF_FINAL_ENABLED
from test_preview_v2 import _preview_layout, _save_preview_layout, _source_pdf, create_job


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "layout_v2_complete.json"


def app_factory(tmp_path: Path, *, enabled: bool) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(REPO_ROOT / "templates"),
        static_folder=str(REPO_ROOT / "static"),
        instance_path=str(tmp_path / "instance"),
    )
    app.config.update(
        TESTING=True,
        EDITOR_OFFSET_V2_ENABLED=True,
        EDITOR_OFFSET_V2_PDF_FINAL_ENABLED=enabled,
        EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
    )
    init_editor_offset_v2(app)
    return app


def _ready_layout(base: dict, asset: dict) -> dict:
    layout = _preview_layout(base, asset)
    layout['export'].update(render_mode='vector_hybrid', preserve_vector_content=True)
    layout["export"]["marks_profiles"][0].update(
        crop_marks=False,
        registration_marks=False,
        technical_text=False,
        color_bar=False,
    )
    return layout


def _upload_source(client, created: dict) -> dict:
    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "source.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.get_json()


def test_pdf_final_is_separately_gated(tmp_path):
    app = app_factory(tmp_path, enabled=False)
    client = app.test_client()
    created = create_job(client)
    response = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final", json={})
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PDF_FINAL_DISABLED"


def test_gated_pdf_final_writes_one_sheet_page_with_physical_size(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, "PDF final V2")
    uploaded = _upload_source(client, created)
    layout = _ready_layout(uploaded["layout"], uploaded["asset"])
    saved = _save_preview_layout(client, uploaded, layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",
        json={"dpi": 36},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    with fitz.open(stream=response.data, filetype="pdf") as document:
        assert document.page_count == 1
        page = document[0]
        assert page.rect.width == pytest.approx(700 * 72 / 25.4, abs=0.01)
        assert page.rect.height == pytest.approx(500 * 72 / 25.4, abs=0.01)
        assert 'PREVIEW-V2' in page.get_text()
        assert not page.get_images(full=True)  # A vector source must remain vector.
    output_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "outputs"
    assert list(output_dir.glob(f"pdf_final_r{saved['revision']}_front_36_*.pdf"))


def test_pdf_final_regeneration_replaces_same_artifact_deterministically(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, "PDF regeneration V2")
    uploaded = _upload_source(client, created)
    saved = _save_preview_layout(client, uploaded, _ready_layout(uploaded["layout"], uploaded["asset"]))

    first = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final", json={"dpi": 36})
    first_data = first.data
    first.close()
    second = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final", json={"dpi": 36})

    assert first.status_code == second.status_code == 200
    assert first_data == second.data
    output_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "outputs"
    assert len(list(output_dir.glob(f"pdf_final_r{saved['revision']}_front_36_*.pdf"))) == 1
    assert not list(output_dir.glob(".pdf-final-*.tmp"))


def test_gated_pdf_final_combines_front_and_back_in_layout_order(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, "PDF duplex V2")
    uploaded = _upload_source(client, created)
    layout = _ready_layout(uploaded["layout"], uploaded["asset"])
    front = copy.deepcopy(layout["slots"][0])
    back = copy.deepcopy(front)
    back["id"] = "slot_back"
    back["face"] = "back"
    layout["slots"] = [front, back]
    layout["faces"] = {"enabled": ["front", "back"], "duplex": {"enabled": True, "flip": "long_edge"}}
    layout["export"]["faces"] = {
        "front": True,
        "back": True,
        "combine_in_single_pdf": True,
        "order": ["front", "back"],
    }
    saved = _save_preview_layout(client, uploaded, layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",
        json={"face": "both", "dpi": 36},
    )

    assert response.status_code == 200
    with fitz.open(stream=response.data, filetype="pdf") as document:
        assert document.page_count == 2
        assert all(page.rect.width == pytest.approx(700 * 72 / 25.4, abs=0.01) for page in document)
    output_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "outputs"
    assert list(output_dir.glob(f"pdf_final_r{saved['revision']}_both_36_*.pdf"))
