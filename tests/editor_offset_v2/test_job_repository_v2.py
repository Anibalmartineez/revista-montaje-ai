from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from editor_offset_v2.application.job_service import create_initial_layout_v2
from editor_offset_v2.infrastructure.job_repository import (
    JOB_DIRECTORIES,
    LAYOUT_FILENAME,
    JobRepository,
    JobRepositoryError,
    validate_job_id,
)


JOB_ID = "ev2_0123456789abcdef01234567"


def make_layout(revision: int = 1) -> dict:
    layout = create_initial_layout_v2(
        JOB_ID,
        "Repositorio V2",
        now="2026-07-18T12:00:00Z",
    )
    layout["job"]["revision"] = revision
    return layout


def test_create_job_builds_isolated_directory_tree_and_layout(tmp_path):
    repository = JobRepository(tmp_path / "jobs")
    layout = make_layout()

    job_path = repository.create_job(JOB_ID, layout)

    assert job_path == (tmp_path / "jobs" / JOB_ID).resolve()
    assert (job_path / LAYOUT_FILENAME).is_file()
    assert all((job_path / name).is_dir() for name in JOB_DIRECTORIES)
    assert repository.read_layout(JOB_ID) == layout


def test_json_is_utf8_deterministic_strict_and_ends_with_newline(tmp_path):
    repository = JobRepository(tmp_path / "jobs")
    layout = make_layout()
    repository.create_job(JOB_ID, layout)
    raw = repository.layout_path(JOB_ID).read_bytes()

    assert raw.endswith(b"\n")
    decoded = raw.decode("utf-8")
    assert '"assets": []' in decoded
    assert decoded.index('"assets"') < decoded.index('"coordinate_system"')
    assert json.loads(decoded) == layout


@pytest.mark.parametrize(
    "job_id",
    [
        "../outside",
        "ev2_../outside",
        "ev2_bad/name",
        "ev2_bad\\name",
        "C:\\absolute\\job",
        "/absolute/job",
        "ev2_short",
        "EV2_0123456789abcdef01234567",
        "ev2_0123456789abcdef0123456g",
        "ev2_" + "a" * 100,
        "",
        None,
    ],
)
def test_invalid_job_ids_are_rejected_before_path_resolution(tmp_path, job_id):
    repository = JobRepository(tmp_path / "jobs")

    with pytest.raises(JobRepositoryError) as exc_info:
        repository.job_path(job_id)

    assert exc_info.value.code == "INVALID_JOB_ID"


def test_valid_server_id_is_accepted():
    assert validate_job_id(JOB_ID) == JOB_ID


def test_missing_job_and_missing_layout_are_distinct_controlled_failures(tmp_path):
    repository = JobRepository(tmp_path / "jobs")
    with pytest.raises(JobRepositoryError) as missing_job:
        repository.read_layout(JOB_ID)
    assert missing_job.value.code == "JOB_NOT_FOUND"

    repository.job_path(JOB_ID).mkdir(parents=True)
    with pytest.raises(JobRepositoryError) as missing_layout:
        repository.read_layout(JOB_ID)
    assert missing_layout.value.code == "PERSISTENCE_ERROR"


@pytest.mark.parametrize("raw", ["{broken", "NaN", "[]", '"text"'])
def test_corrupt_or_non_object_json_is_rejected(tmp_path, raw):
    repository = JobRepository(tmp_path / "jobs")
    job_path = repository.job_path(JOB_ID)
    job_path.mkdir(parents=True)
    (job_path / LAYOUT_FILENAME).write_text(raw, encoding="utf-8")

    with pytest.raises(JobRepositoryError) as exc_info:
        repository.read_layout(JOB_ID)

    assert exc_info.value.code == "PERSISTENCE_ERROR"


def test_compare_and_swap_replaces_only_the_expected_revision(tmp_path):
    repository = JobRepository(tmp_path / "jobs")
    repository.create_job(JOB_ID, make_layout(1))
    revision_two = make_layout(2)

    repository.replace_layout_if_revision(JOB_ID, 1, revision_two)
    assert repository.read_layout(JOB_ID)["job"]["revision"] == 2

    with pytest.raises(JobRepositoryError) as conflict:
        repository.replace_layout_if_revision(JOB_ID, 1, make_layout(3))
    assert conflict.value.code == "REVISION_CONFLICT"
    assert repository.read_layout(JOB_ID)["job"]["revision"] == 2


def test_atomic_replace_failure_preserves_previous_layout_and_cleans_temp(
    tmp_path, monkeypatch
):
    repository = JobRepository(tmp_path / "jobs")
    original = make_layout(1)
    repository.create_job(JOB_ID, original)

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(
        "editor_offset_v2.infrastructure.job_repository.os.replace",
        fail_replace,
    )
    with pytest.raises(JobRepositoryError) as exc_info:
        repository.replace_layout_if_revision(JOB_ID, 1, make_layout(2))

    assert exc_info.value.code == "PERSISTENCE_ERROR"
    assert repository.read_layout(JOB_ID) == original
    assert list(repository.job_path(JOB_ID).glob(".layout_v2.*.tmp")) == []


def test_non_finite_json_does_not_modify_persisted_layout(tmp_path):
    repository = JobRepository(tmp_path / "jobs")
    original = make_layout(1)
    repository.create_job(JOB_ID, original)
    invalid = copy.deepcopy(original)
    invalid["sheet"]["size_mm"]["width"] = float("nan")

    with pytest.raises(JobRepositoryError) as exc_info:
        repository.replace_layout_if_revision(JOB_ID, 1, invalid)

    assert exc_info.value.code == "PERSISTENCE_ERROR"
    assert repository.read_layout(JOB_ID) == original


def test_repository_never_uses_static_constructor_jobs(tmp_path):
    repository = JobRepository(tmp_path / "instance" / "editor_offset_v2_jobs")

    assert "static" not in repository.jobs_root.parts
    assert repository.jobs_root.name == "editor_offset_v2_jobs"
