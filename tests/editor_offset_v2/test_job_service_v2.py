from __future__ import annotations

import copy
from datetime import datetime

import pytest

from editor_offset_v2.application.job_service import (
    INITIAL_REVISION,
    JobService,
    JobServiceError,
    create_initial_layout_v2,
)
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.job_repository import (
    JOB_DIRECTORIES,
    LAYOUT_FILENAME,
    JobRepository,
)


JOB_ID = "ev2_abcdef0123456789abcdef01"
CREATED_AT = "2026-07-18T13:00:00Z"
UPDATED_AT = "2026-07-18T13:05:00Z"


def make_service(tmp_path, *, clock_values=(CREATED_AT, UPDATED_AT)):
    values = iter(clock_values)
    repository = JobRepository(tmp_path / "jobs")
    service = JobService(
        repository,
        clock=lambda: next(values),
        id_factory=lambda: JOB_ID,
    )
    return service, repository


def test_initial_layout_is_empty_explicit_and_valid():
    layout = create_initial_layout_v2(JOB_ID, "Trabajo nuevo", now=CREATED_AT)

    assert validate_layout_v2(layout) == []
    assert layout["layout_schema_version"] == 2
    assert layout["job"] == {
        "id": JOB_ID,
        "name": "Trabajo nuevo",
        "revision": INITIAL_REVISION,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    assert layout["assets"] == []
    assert layout["works"] == []
    assert layout["slots"] == []
    assert layout["sheet"]["size_mm"] == {"width": 700.0, "height": 500.0}
    assert layout["faces"]["enabled"] == ["front"]
    assert layout["ctp"]["enabled"] is False


def test_create_job_uses_server_id_and_creates_all_directories(tmp_path):
    service, repository = make_service(tmp_path)

    result = service.create_job("Mi montaje")

    assert result.job_id == JOB_ID
    assert result.revision == INITIAL_REVISION
    assert result.layout["job"]["name"] == "Mi montaje"
    job_path = repository.job_path(JOB_ID)
    assert (job_path / LAYOUT_FILENAME).is_file()
    assert all((job_path / name).is_dir() for name in JOB_DIRECTORIES)


def test_dates_are_utc_iso_8601():
    layout = create_initial_layout_v2(JOB_ID, now=CREATED_AT)

    for field in ("created_at", "updated_at"):
        value = layout["job"][field]
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert value.endswith("Z")


def test_read_existing_job_returns_valid_layout(tmp_path):
    service, _ = make_service(tmp_path)
    created = service.create_job()

    loaded = service.get_job(JOB_ID)

    assert loaded == created
    assert validate_layout_v2(loaded.layout) == []


def test_missing_and_invalid_job_ids_are_typed_errors(tmp_path):
    service, _ = make_service(tmp_path)

    with pytest.raises(JobServiceError) as missing:
        service.get_job(JOB_ID)
    assert (missing.value.code, missing.value.status_code) == ("JOB_NOT_FOUND", 404)

    with pytest.raises(JobServiceError) as invalid:
        service.get_job("../bad")
    assert (invalid.value.code, invalid.value.status_code) == ("INVALID_JOB_ID", 400)


def test_save_increments_revision_updates_timestamp_and_preserves_created_at(tmp_path):
    service, repository = make_service(tmp_path)
    created = service.create_job()
    submitted = copy.deepcopy(created.layout)
    submitted["job"]["name"] = "Nombre actualizado"

    saved = service.save_layout(JOB_ID, INITIAL_REVISION, submitted)

    assert saved.revision == INITIAL_REVISION + 1
    assert saved.layout["job"]["revision"] == INITIAL_REVISION + 1
    assert saved.layout["job"]["updated_at"] == UPDATED_AT
    assert saved.layout["job"]["created_at"] == CREATED_AT
    assert repository.read_layout(JOB_ID) == saved.layout
    assert submitted["job"]["revision"] == INITIAL_REVISION
    assert submitted["job"]["updated_at"] == CREATED_AT


def test_revision_conflict_does_not_modify_file(tmp_path):
    service, repository = make_service(tmp_path)
    created = service.create_job()
    before = repository.layout_path(JOB_ID).read_bytes()

    with pytest.raises(JobServiceError) as conflict:
        service.save_layout(JOB_ID, 0, created.layout)

    assert (conflict.value.code, conflict.value.status_code) == (
        "REVISION_CONFLICT",
        409,
    )
    assert repository.layout_path(JOB_ID).read_bytes() == before


@pytest.mark.parametrize(
    "mutator",
    [
        lambda layout: layout.update(layout_schema_version=1),
        lambda layout: layout.pop("sheet"),
        lambda layout: layout["sheet"]["size_mm"].update(width=0),
    ],
)
def test_invalid_submitted_layout_is_rejected_without_writing(tmp_path, mutator):
    service, repository = make_service(tmp_path)
    created = service.create_job()
    submitted = copy.deepcopy(created.layout)
    mutator(submitted)
    before = repository.layout_path(JOB_ID).read_bytes()

    with pytest.raises(JobServiceError) as invalid:
        service.save_layout(JOB_ID, INITIAL_REVISION, submitted)

    assert (invalid.value.code, invalid.value.status_code) == ("INVALID_LAYOUT", 400)
    assert repository.layout_path(JOB_ID).read_bytes() == before


def test_layout_job_id_mismatch_is_rejected_without_writing(tmp_path):
    service, repository = make_service(tmp_path)
    created = service.create_job()
    submitted = copy.deepcopy(created.layout)
    submitted["job"]["id"] = "ev2_111111111111111111111111"
    before = repository.layout_path(JOB_ID).read_bytes()

    with pytest.raises(JobServiceError) as invalid:
        service.save_layout(JOB_ID, INITIAL_REVISION, submitted)

    assert invalid.value.code == "INVALID_LAYOUT"
    assert repository.layout_path(JOB_ID).read_bytes() == before


def test_client_cannot_choose_a_different_layout_revision(tmp_path):
    service, repository = make_service(tmp_path)
    created = service.create_job()
    submitted = copy.deepcopy(created.layout)
    submitted["job"]["revision"] = 99
    before = repository.layout_path(JOB_ID).read_bytes()

    with pytest.raises(JobServiceError) as conflict:
        service.save_layout(JOB_ID, INITIAL_REVISION, submitted)

    assert conflict.value.code == "REVISION_CONFLICT"
    assert repository.layout_path(JOB_ID).read_bytes() == before


def test_missing_corrupt_and_wrong_version_persisted_layouts_are_controlled(tmp_path):
    service, repository = make_service(tmp_path)
    job_path = repository.job_path(JOB_ID)
    job_path.mkdir(parents=True)

    with pytest.raises(JobServiceError) as missing:
        service.get_job(JOB_ID)
    assert missing.value.code == "PERSISTENCE_ERROR"

    repository.layout_path(JOB_ID).write_text("{bad", encoding="utf-8")
    with pytest.raises(JobServiceError) as corrupt:
        service.get_job(JOB_ID)
    assert corrupt.value.code == "PERSISTENCE_ERROR"

    wrong_version = create_initial_layout_v2(JOB_ID, now=CREATED_AT)
    wrong_version["layout_schema_version"] = 1
    repository.layout_path(JOB_ID).write_text(
        __import__("json").dumps(wrong_version),
        encoding="utf-8",
    )
    with pytest.raises(JobServiceError) as invalid:
        service.get_job(JOB_ID)
    assert invalid.value.code == "INVALID_LAYOUT"
    assert invalid.value.status_code == 500


@pytest.mark.parametrize("name", ["", "   ", 42, "x" * 161])
def test_invalid_job_name_is_rejected(tmp_path, name):
    service, _ = make_service(tmp_path)

    with pytest.raises(JobServiceError) as invalid:
        service.create_job(name)

    assert invalid.value.code == "INVALID_LAYOUT"
    assert invalid.value.status_code == 400
