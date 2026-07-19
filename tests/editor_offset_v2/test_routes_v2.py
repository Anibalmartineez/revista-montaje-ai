from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import (
    EDITOR_OFFSET_V2_ENABLED,
    EDITOR_OFFSET_V2_JOBS_ROOT,
)
from editor_offset_v2.domain.validation import validate_layout_v2


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "layout_v2_complete.json"
)


@pytest.fixture
def app_factory(tmp_path):
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

        @app.get("/editor_offset_visual")
        def legacy_editor_probe():
            return "Editor V1 intacto"

        init_editor_offset_v2(app)
        return app

    return create


def create_job(client, name="Job desde API") -> dict:
    response = client.post(
        "/api/editor-offset-v2/jobs",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.get_json()


def with_fixture_slot(layout: dict) -> dict:
    complete = json.loads(COMPLETE_FIXTURE.read_text(encoding="utf-8"))
    result = copy.deepcopy(layout)
    result["assets"] = copy.deepcopy(complete["assets"])
    result["works"] = copy.deepcopy(complete["works"])
    result["slots"] = [copy.deepcopy(complete["slots"][0])]
    return result


def test_feature_flag_disabled_returns_404_without_affecting_v1(app_factory):
    app = app_factory(enabled=False)
    client = app.test_client()

    shell = client.get("/editor_offset_visual_v2")
    api = client.post("/api/editor-offset-v2/jobs", json={})
    legacy = client.get("/editor_offset_visual")

    assert shell.status_code == 404
    assert api.status_code == 404
    assert api.get_json()["error"]["code"] == "V2_DISABLED"
    assert legacy.status_code == 200
    assert legacy.get_data(as_text=True) == "Editor V1 intacto"


def test_feature_flag_can_be_enabled_per_app_without_global_state(app_factory):
    disabled = app_factory(enabled=False)
    enabled = app_factory(enabled=True)

    assert disabled.test_client().get("/editor_offset_visual_v2").status_code == 404
    assert enabled.test_client().get("/editor_offset_visual_v2").status_code == 200


def test_shell_without_job_has_v2_assets_and_never_loads_v1_script(app_factory):
    client = app_factory().test_client()

    response = client.get("/editor_offset_visual_v2")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Editor Offset Visual V2" in html
    assert "Crea un job para comenzar" in html
    assert "Sin documento abierto" in html
    assert "/static/css/editor_offset_visual_v2.css" in html
    assert "/static/js/editor_offset_visual_v2.js" in html
    assert "/static/js/editor_offset_v2/store.js" in html
    assert "/static/js/editor_offset_v2/commands.js" in html
    assert "/static/js/editor_offset_v2/canvas_renderer.js" in html
    assert "static/js/editor_offset_visual.js" not in html
    assert "data-editor-tab" not in html


def test_post_creates_server_id_valid_layout_directories_and_open_url(app_factory):
    app = app_factory()
    client = app.test_client()

    payload = create_job(client)

    assert payload["ok"] is True
    assert payload["job_id"].startswith("ev2_")
    assert len(payload["job_id"]) == 28
    assert payload["revision"] == 1
    assert payload["open_url"] == f"/editor_offset_visual_v2/{payload['job_id']}"
    assert validate_layout_v2(payload["layout"]) == []
    job_path = Path(app.config[EDITOR_OFFSET_V2_JOBS_ROOT]) / payload["job_id"]
    assert (job_path / "layout_v2.json").is_file()
    assert all(
        (job_path / name).is_dir()
        for name in ("assets", "derived", "previews", "outputs", "reports")
    )


def test_client_supplied_job_id_is_rejected(app_factory):
    client = app_factory().test_client()

    response = client.post(
        "/api/editor-offset-v2/jobs",
        json={"job_id": "ev2_aaaaaaaaaaaaaaaaaaaaaaaa"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JOB_ID"


def test_get_existing_job_and_shell_context(app_factory):
    client = app_factory().test_client()
    created = create_job(client, "Documento abierto")
    job_id = created["job_id"]

    api_response = client.get(f"/api/editor-offset-v2/jobs/{job_id}")
    shell_response = client.get(f"/editor_offset_visual_v2/{job_id}")
    html = shell_response.get_data(as_text=True)

    assert api_response.status_code == 200
    assert api_response.get_json()["layout"] == created["layout"]
    assert shell_response.status_code == 200
    assert job_id in html
    assert "Documento abierto" in html
    assert '<strong id="ev2-revision">1</strong>' in html
    assert 'id="ev2-canvas"' in html
    assert 'id="ev2-save"' in html


def test_canvas_placeholder_can_be_saved_moved_and_conflict_preserves_it(app_factory):
    client = app_factory().test_client()
    created = create_job(client)
    layout = with_fixture_slot(created["layout"])
    slot_id = layout["slots"][0]["id"]

    first = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 1, "layout": layout},
    )
    assert first.status_code == 200
    assert first.get_json()["revision"] == 2

    moved = copy.deepcopy(first.get_json()["layout"])
    moved["slots"][0]["geometry"]["position_mm"]["x_mm"] = 144.25
    moved["slots"][0]["geometry"]["position_mm"]["y_mm"] = 98.75
    second = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 2, "layout": moved},
    )
    assert second.status_code == 200
    assert second.get_json()["revision"] == 3
    assert second.get_json()["layout"]["slots"][0]["id"] == slot_id

    stale = copy.deepcopy(second.get_json()["layout"])
    stale["slots"][0]["geometry"]["position_mm"]["x_mm"] = 999.0
    conflict = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 2, "layout": stale},
    )
    persisted = client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}"
    ).get_json()["layout"]

    assert conflict.status_code == 409
    assert persisted == second.get_json()["layout"]


def test_get_missing_invalid_and_traversal_ids_are_controlled(app_factory):
    client = app_factory().test_client()
    missing_id = "ev2_aaaaaaaaaaaaaaaaaaaaaaaa"

    missing = client.get(f"/api/editor-offset-v2/jobs/{missing_id}")
    invalid = client.get("/api/editor-offset-v2/jobs/not-valid")
    traversal = client.get("/api/editor-offset-v2/jobs/..%5Coutside")

    assert (missing.status_code, missing.get_json()["error"]["code"]) == (
        404,
        "JOB_NOT_FOUND",
    )
    assert (invalid.status_code, invalid.get_json()["error"]["code"]) == (
        400,
        "INVALID_JOB_ID",
    )
    assert traversal.status_code == 400
    assert traversal.get_json()["error"]["code"] == "INVALID_JOB_ID"


def test_put_saves_valid_layout_with_server_revision(app_factory):
    client = app_factory().test_client()
    created = create_job(client)
    layout = copy.deepcopy(created["layout"])
    layout["job"]["name"] = "Guardado por PUT"

    response = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 1, "layout": layout},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["revision"] == 2
    assert payload["layout"]["job"]["revision"] == 2
    assert payload["layout"]["job"]["name"] == "Guardado por PUT"
    assert validate_layout_v2(payload["layout"]) == []


def test_put_revision_conflict_returns_409_and_preserves_layout(app_factory):
    client = app_factory().test_client()
    created = create_job(client)

    conflict = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 0, "layout": created["layout"]},
    )
    loaded = client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}"
    ).get_json()

    assert conflict.status_code == 409
    assert conflict.get_json()["error"]["code"] == "REVISION_CONFLICT"
    assert loaded["revision"] == 1
    assert loaded["layout"] == created["layout"]


def test_put_invalid_layout_and_job_id_mismatch_return_400(app_factory):
    client = app_factory().test_client()
    created = create_job(client)
    invalid_layout = copy.deepcopy(created["layout"])
    invalid_layout["layout_schema_version"] = 1

    invalid = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 1, "layout": invalid_layout},
    )
    mismatch_layout = copy.deepcopy(created["layout"])
    mismatch_layout["job"]["id"] = "ev2_bbbbbbbbbbbbbbbbbbbbbbbb"
    mismatch = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 1, "layout": mismatch_layout},
    )

    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "INVALID_LAYOUT"
    assert mismatch.status_code == 400
    assert mismatch.get_json()["error"]["code"] == "INVALID_LAYOUT"


def test_corrupt_physical_layout_returns_controlled_api_error(app_factory):
    app = app_factory()
    client = app.test_client()
    created = create_job(client)
    layout_path = (
        Path(app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
        / created["job_id"]
        / "layout_v2.json"
    )
    layout_path.write_text("{broken", encoding="utf-8")

    response = client.get(f"/api/editor-offset-v2/jobs/{created['job_id']}")

    assert response.status_code == 500
    assert response.get_json() == {
        "ok": False,
        "error": {
            "code": "PERSISTENCE_ERROR",
            "message": "The persisted V2 layout cannot be read as strict UTF-8 JSON",
        },
    }


def test_blueprint_registration_is_idempotent(app_factory):
    app = app_factory()
    rules_before = [rule.rule for rule in app.url_map.iter_rules()]

    init_editor_offset_v2(app)

    assert [rule.rule for rule in app.url_map.iter_rules()] == rules_before
    assert "editor_offset_v2" in app.blueprints


def test_production_app_registers_v2_blueprint_without_replacing_v1():
    from app import app as production_app

    endpoints = {rule.endpoint for rule in production_app.url_map.iter_rules()}

    assert "editor_offset_v2" in production_app.blueprints
    assert "editor_offset_v2.editor_shell" in endpoints
    assert "routes.editor_offset_visual" in endpoints


def test_template_embeds_parseable_context_json(app_factory):
    client = app_factory().test_client()
    response = client.get("/editor_offset_visual_v2")
    html = response.get_data(as_text=True)
    start = html.index('<script id="editor-offset-v2-context" type="application/json">')
    start = html.index(">", start) + 1
    end = html.index("</script>", start)

    context = json.loads(html[start:end])

    assert context["job_id"] is None
    assert context["revision"] is None
    assert context["create_job_url"] == "/api/editor-offset-v2/jobs"
    assert context["job_api_url"] is None
    assert context["save_layout_url"] is None


def test_template_context_has_canonical_get_and_save_urls(app_factory):
    client = app_factory().test_client()
    created = create_job(client)
    response = client.get(created["open_url"])
    html = response.get_data(as_text=True)
    start = html.index('<script id="editor-offset-v2-context" type="application/json">')
    start = html.index(">", start) + 1
    end = html.index("</script>", start)
    context = json.loads(html[start:end])

    job_id = created["job_id"]
    assert context["job_api_url"] == f"/api/editor-offset-v2/jobs/{job_id}"
    assert context["save_layout_url"] == f"/api/editor-offset-v2/jobs/{job_id}/layout"
