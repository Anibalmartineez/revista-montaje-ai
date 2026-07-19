from __future__ import annotations

import copy

import pytest
from flask import Flask

from editor_offset_v2.application.job_service import JobService, create_initial_layout_v2
from editor_offset_v2.application.repeat_service import RepeatService, RepeatServiceError
from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import EDITOR_OFFSET_V2_JOBS_ROOT
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.job_repository import JobRepository


JOB_ID = "ev2_aaaaaaaaaaaaaaaaaaaaaaaa"
NOW = "2026-07-19T12:00:00Z"


def repeat_layout() -> dict:
    layout = create_initial_layout_v2(JOB_ID, now=NOW)
    asset = {
        "id": "asset_repeat",
        "original_filename": "repeat.pdf",
        "storage_key": "assets/asset_repeat/source.pdf",
        "mime_type": "application/pdf",
        "sha256": "b" * 64,
        "page_count": 1,
        "status": "ready",
        "created_at": NOW,
        "pages": [
            {
                "number": 1,
                "intrinsic_rotation_deg": 0,
                "boxes_mm": {
                    "media": {"x": 0, "y": 0, "width": 46, "height": 26},
                    "trim": {"x": 3, "y": 3, "width": 40, "height": 20},
                    "bleed": {"x": 0, "y": 0, "width": 46, "height": 26},
                    "crop": None,
                },
                "preview_key": "assets/asset_repeat/thumbnails/page_1.png",
                "preflight": {
                    "status": "not_run",
                    "color_spaces": [],
                    "minimum_effective_dpi": None,
                    "has_transparency": None,
                    "has_overprint": None,
                    "issues": [],
                },
            }
        ],
    }
    source = {"asset_id": "asset_repeat", "page": 1, "pdf_box": "trim"}
    layout["assets"] = [asset]
    layout["works"] = [
        {
            "id": "work_repeat",
            "name": "Repeat",
            "trim_size_mm": {"width": 40, "height": 20},
            "bleed_mm": 3,
            "requested_forms": 4,
            "allowed_rotations_deg": [0, 90],
            "priority": 100,
            "preferred_zone": "auto",
            "preferred_flow": "rows",
            "front_source": source,
            "back_source": None,
        }
    ]
    layout["sheet"]["size_mm"] = {"width": 200, "height": 140}
    layout["sheet"]["printable_margins_mm"] = {
        "left": 10,
        "right": 10,
        "bottom": 10,
        "top": 10,
    }
    assert validate_layout_v2(layout) == []
    return layout


def payload(**overrides) -> dict:
    result = {
        "base_revision": 1,
        "work_ids": ["work_repeat"],
        "face": "front",
        "settings": {
            "horizontal_gap_mm": 4,
            "vertical_gap_mm": 3,
            "exact_quantity": True,
            "fill_remaining_space": False,
            "allow_partial": False,
        },
        "apply_mode": "add",
    }
    result.update(overrides)
    return result


def make_service(tmp_path) -> tuple[RepeatService, JobRepository]:
    repository = JobRepository(tmp_path / "jobs")
    repository.create_job(JOB_ID, repeat_layout())
    service = RepeatService(
        JobService(repository),
        clock=lambda: NOW,
    )
    return service, repository


def test_service_returns_proposal_without_persisting_and_is_deterministic(tmp_path):
    service, repository = make_service(tmp_path)
    before = repository.read_layout(JOB_ID)

    first = service.propose(JOB_ID, payload())
    second = service.propose(JOB_ID, payload())

    assert first.success is True
    assert first.operation_id.startswith("repeat_")
    assert first.as_dict() == second.as_dict()
    assert repository.read_layout(JOB_ID) == before
    assert repository.read_layout(JOB_ID)["job"]["revision"] == 1


def test_service_rejects_revision_conflict_and_disabled_face(tmp_path):
    service, _ = make_service(tmp_path)

    with pytest.raises(RepeatServiceError) as conflict:
        service.propose(JOB_ID, payload(base_revision=0))
    with pytest.raises(RepeatServiceError) as face:
        service.propose(JOB_ID, payload(face="back"))

    assert (conflict.value.code, conflict.value.status_code) == ("REVISION_CONFLICT", 409)
    assert (face.value.code, face.value.status_code) == ("INVALID_FACE", 400)


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {},
        {**payload(), "unexpected": True},
        payload(work_ids=[]),
        payload(work_ids=["work_repeat", "work_repeat"]),
        payload(apply_mode="replace_all"),
        payload(settings={}),
        payload(settings={**payload()["settings"], "horizontal_gap_mm": -1}),
        payload(settings={**payload()["settings"], "allow_partial": 1}),
    ],
)
def test_service_rejects_invalid_requests_without_mutation(tmp_path, invalid):
    service, repository = make_service(tmp_path)
    before = repository.read_layout(JOB_ID)

    with pytest.raises(RepeatServiceError):
        service.propose(JOB_ID, invalid)

    assert repository.read_layout(JOB_ID) == before


def test_service_returns_structured_failure_for_unknown_work(tmp_path):
    service, _ = make_service(tmp_path)

    result = service.propose(JOB_ID, payload(work_ids=["work_missing"]))

    assert result.success is False
    assert result.slots == ()
    assert result.issues[0].code == "WORK_NOT_FOUND"


def test_legacy_exact_quantity_setting_remains_accepted_but_is_not_a_third_policy(tmp_path):
    service, _ = make_service(tmp_path)
    exact = service.propose(JOB_ID, payload())
    legacy_false = service.propose(
        JOB_ID,
        payload(settings={**payload()["settings"], "exact_quantity": False}),
    )

    assert exact.success is True
    assert legacy_false.success is True
    assert [slot["geometry"] for slot in exact.slots] == [
        slot["geometry"] for slot in legacy_false.slots
    ]


def test_repeat_endpoint_returns_proposal_and_never_persists_it(tmp_path):
    jobs_root = tmp_path / "jobs"
    repository = JobRepository(jobs_root)
    repository.create_job(JOB_ID, repeat_layout())
    app = Flask(
        __name__,
        template_folder=str(tmp_path),
        instance_path=str(tmp_path / "instance"),
    )
    app.config.update(
        TESTING=True,
        EDITOR_OFFSET_V2_ENABLED=True,
        EDITOR_OFFSET_V2_JOBS_ROOT=str(jobs_root),
    )
    init_editor_offset_v2(app)
    client = app.test_client()

    response = client.post(
        f"/api/editor-offset-v2/jobs/{JOB_ID}/imposition/repeat",
        json=payload(),
    )
    loaded = client.get(f"/api/editor-offset-v2/jobs/{JOB_ID}").get_json()

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["result"]["success"] is True
    assert body["result"]["slots"]
    assert loaded["revision"] == 1
    assert loaded["layout"]["slots"] == []


def test_repeat_endpoint_feature_flag_and_conflict_are_controlled(tmp_path):
    jobs_root = tmp_path / "jobs"
    repository = JobRepository(jobs_root)
    repository.create_job(JOB_ID, repeat_layout())
    app = Flask(__name__, instance_path=str(tmp_path / "instance"))
    app.config.update(
        TESTING=True,
        EDITOR_OFFSET_V2_ENABLED=False,
        EDITOR_OFFSET_V2_JOBS_ROOT=str(jobs_root),
    )
    init_editor_offset_v2(app)
    client = app.test_client()

    disabled = client.post(
        f"/api/editor-offset-v2/jobs/{JOB_ID}/imposition/repeat",
        json=payload(),
    )
    app.config["EDITOR_OFFSET_V2_ENABLED"] = True
    conflict = client.post(
        f"/api/editor-offset-v2/jobs/{JOB_ID}/imposition/repeat",
        json=payload(base_revision=0),
    )

    assert disabled.status_code == 404
    assert disabled.get_json()["error"]["code"] == "V2_DISABLED"
    assert conflict.status_code == 409
    assert conflict.get_json()["error"]["code"] == "REVISION_CONFLICT"
