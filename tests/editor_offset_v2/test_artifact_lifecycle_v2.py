from __future__ import annotations

import threading
import subprocess
import sys
import time
from pathlib import Path

import pytest

from editor_offset_v2.application.job_service import create_initial_layout_v2
from editor_offset_v2.infrastructure.artifact_lifecycle import ArtifactLifecycleService
from editor_offset_v2.infrastructure.job_repository import JobRepository
from editor_offset_v2.infrastructure.process_lock import exclusive_file_lock


JOB_ID = "ev2_aaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture
def repository(tmp_path: Path) -> JobRepository:
    repository = JobRepository(tmp_path / "jobs")
    repository.create_job(JOB_ID, create_initial_layout_v2(JOB_ID, now="2026-09-16T00:00:00Z"))
    return repository


def test_recovery_removes_only_known_interrupted_temporaries(repository: JobRepository) -> None:
    job = repository.job_path(JOB_ID)
    (job / "previews" / ".preview-interrupted.tmp").write_bytes(b"partial")
    (job / "outputs" / ".pdf-final-interrupted.tmp").write_bytes(b"partial")
    (job / "reports" / "operator-notes.tmp").write_bytes(b"keep")
    (job / "outputs" / "pdf_final_r1_front_36.pdf").write_bytes(b"keep")

    recovered = ArtifactLifecycleService(repository).recover_temporaries(JOB_ID)

    assert recovered == (
        "outputs/.pdf-final-interrupted.tmp",
        "previews/.preview-interrupted.tmp",
    )
    assert (job / "reports" / "operator-notes.tmp").exists()
    assert (job / "outputs" / "pdf_final_r1_front_36.pdf").exists()


def test_retention_keeps_newest_managed_outputs_and_never_touches_sources(repository: JobRepository) -> None:
    job = repository.job_path(JOB_ID)
    outputs = job / "outputs"
    for revision in range(1, 6):
        path = outputs / f"pdf_final_r{revision}_front_36.pdf"
        path.write_bytes(str(revision).encode())
        path.touch()
        time.sleep(0.002)
    source = job / "assets" / "source.pdf"
    source.write_bytes(b"source")

    removed = ArtifactLifecycleService(repository).retain(JOB_ID, keep_latest=2)

    assert len(removed) == 3
    assert (outputs / "pdf_final_r5_front_36.pdf").exists()
    assert (outputs / "pdf_final_r4_front_36.pdf").exists()
    assert source.exists()


def test_retention_covers_preflight_reports_but_preserves_unmanaged_notes(repository: JobRepository) -> None:
    job = repository.job_path(JOB_ID)
    reports = job / "reports"
    for revision in range(1, 5):
        path = reports / f"pfr_{revision:02d}.json"
        path.write_text(str(revision), encoding="utf-8")
        path.touch()
        time.sleep(0.002)
    note = reports / "operator-notes.json"
    note.write_text("keep", encoding="utf-8")

    removed = ArtifactLifecycleService(repository).retain(JOB_ID, keep_latest=2)

    assert len(removed) == 2
    assert (reports / "pfr_04.json").exists()
    assert (reports / "pfr_03.json").exists()
    assert note.exists()


def test_file_lock_serializes_threads_and_releases_after_scope(tmp_path: Path) -> None:
    lock_path = tmp_path / "job" / ".job.lock"
    events: list[str] = []
    entered = threading.Event()

    def holder() -> None:
        with exclusive_file_lock(lock_path):
            events.append("holder-enter")
            entered.set()
            time.sleep(0.05)
            events.append("holder-exit")

    first = threading.Thread(target=holder)
    first.start()
    assert entered.wait(1)
    with exclusive_file_lock(lock_path):
        events.append("waiter-enter")
    first.join(timeout=1)

    assert events == ["holder-enter", "holder-exit", "waiter-enter"]


def test_file_lock_serializes_two_python_processes(tmp_path: Path) -> None:
    lock_path = tmp_path / "job" / ".job.lock"
    events_path = tmp_path / "events.log"
    script = (
        "import sys, time\n"
        "from pathlib import Path\n"
        "from editor_offset_v2.infrastructure.process_lock import exclusive_file_lock\n"
        "lock = Path(sys.argv[1]); events = Path(sys.argv[2]); name = sys.argv[3]\n"
        "with exclusive_file_lock(lock):\n"
        "    with events.open('a', encoding='utf-8') as stream: stream.write(name + '-enter\\n')\n"
        "    time.sleep(0.08)\n"
        "    with events.open('a', encoding='utf-8') as stream: stream.write(name + '-exit\\n')\n"
    )
    first = subprocess.Popen([sys.executable, "-c", script, str(lock_path), str(events_path), "first"])
    time.sleep(0.01)
    second = subprocess.Popen([sys.executable, "-c", script, str(lock_path), str(events_path), "second"])
    assert first.wait(timeout=3) == 0
    assert second.wait(timeout=3) == 0

    events = events_path.read_text(encoding="utf-8").splitlines()
    assert events in [
        ["first-enter", "first-exit", "second-enter", "second-exit"],
        ["second-enter", "second-exit", "first-enter", "first-exit"],
    ]
