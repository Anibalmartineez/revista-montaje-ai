from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path

import fitz
import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.domain.preflight_contract import validate_preflight_report

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "editor_offset_v2" / "layout_v2_complete.json"


@pytest.fixture
def app_factory(tmp_path):
    def create():
        app = Flask(__name__, instance_path=str(tmp_path / "instance"))
        app.config.update(
            TESTING=True,
            EDITOR_OFFSET_V2_ENABLED=True,
            EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
        )
        init_editor_offset_v2(app)
        return app

    return create


def _pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page(width=288, height=144)
    page.insert_text((18, 28), "Preflight V2", fontsize=12)
    output = io.BytesIO()
    document.save(output)
    document.close()
    return output.getvalue()


def _upload(client, job_id: str, data: bytes, revision: int = 1):
    return client.post(
        f"/api/editor-offset-v2/jobs/{job_id}/assets",
        data={
            "base_revision": str(revision),
            "file": (io.BytesIO(data), "preflight.pdf", "application/pdf"),
        },
        content_type="multipart/form-data",
    )


def _layout_with_real_slot(layout: dict, asset: dict) -> dict:
    result = copy.deepcopy(layout)
    asset_id = asset["id"]
    complete = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result["assets"] = [copy.deepcopy(asset)]
    work = copy.deepcopy(complete["works"][0])
    work["trim_size_mm"] = {"width": 101.6, "height": 50.8}
    work["bleed_mm"] = 0.0
    work["front_source"] = {"asset_id": asset_id, "page": 1, "pdf_box": "media"}
    work["back_source"] = {"asset_id": asset_id, "page": 1, "pdf_box": "media"}
    result["works"] = [work]
    slot = copy.deepcopy(complete["slots"][0])
    slot["source"] = {"asset_id": asset_id, "page": 1, "pdf_box": "media"}
    slot["geometry"]["trim_size_mm"] = {"width": 101.6, "height": 50.8}
    slot["geometry"]["bleed_mm"] = 0.0
    slot["geometry"]["position_mm"] = {"x_mm": 80.0, "y_mm": 80.0, "anchor": "trim_center"}
    result["slots"] = [slot]
    return result


def test_preflight_publishes_immutable_report_and_blocks_output_gate(app_factory):
    app = app_factory()
    client = app.test_client()
    created = client.post("/api/editor-offset-v2/jobs", json={}).get_json()
    uploaded = _upload(client, created["job_id"], _pdf_bytes()).get_json()
    layout = _layout_with_real_slot(uploaded["layout"], uploaded["asset"])
    saved = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": uploaded["revision"], "layout": layout},
    )
    assert saved.status_code == 200
    response = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/preflight", json={})

    assert response.status_code == 201
    report = response.get_json()["report"]
    validate_preflight_report({key: value for key, value in report.items() if key != "report_path"})
    assert report["subject"]["revision"] == saved.get_json()["revision"]
    assert report["execution"] == "complete"
    assert all(decision["status"] == "blocked" for decision in report["decisions"])
    assert all("CAPABILITY_GATE_NOT_ENABLED" in decision["reason_codes"] for decision in report["decisions"])
    assert report["report_path"].startswith("reports/")
    report_path = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / report["report_path"]
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert "report_path" not in persisted
    assert persisted["report_id"] == report["report_id"]


def test_preflight_detects_physical_asset_identity_change_without_mutating_layout(app_factory):
    app = app_factory()
    client = app.test_client()
    created = client.post("/api/editor-offset-v2/jobs", json={}).get_json()
    data = _pdf_bytes()
    uploaded = _upload(client, created["job_id"], data).get_json()
    layout = _layout_with_real_slot(uploaded["layout"], uploaded["asset"])
    saved = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": uploaded["revision"], "layout": layout},
    ).get_json()
    source = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / uploaded["asset"]["storage_key"]
    source.write_bytes(data + b"changed")

    response = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/preflight", json={})
    assert response.status_code == 201
    report = response.get_json()["report"]
    assert any(issue["code"] == "ASSET_IDENTITY_MISMATCH" for issue in report["issues"])
    assert report["subject"]["revision"] == saved["revision"]
    assert client.get(f"/api/editor-offset-v2/jobs/{created['job_id']}").get_json()["revision"] == saved["revision"]


def test_preflight_rejects_options_until_policy_is_explicit(app_factory):
    client = app_factory().test_client()
    created = client.post("/api/editor-offset-v2/jobs", json={}).get_json()

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preflight",
        json={"operation": "pdf_final"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PREFLIGHT_REQUEST"


def test_preflight_missing_job_is_a_controlled_not_found(app_factory):
    client = app_factory().test_client()

    response = client.post("/api/editor-offset-v2/jobs/ev2_000000000000000000000000/preflight", json={})

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "JOB_NOT_FOUND"
