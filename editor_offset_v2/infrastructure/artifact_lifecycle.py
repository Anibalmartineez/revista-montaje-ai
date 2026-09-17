"""Recovery and bounded retention for derived V2 output artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from editor_offset_v2.infrastructure.job_repository import JobRepository, JobRepositoryError
from editor_offset_v2.infrastructure.process_lock import exclusive_file_lock


MANAGED_DIRECTORIES = ("reports", "previews", "outputs")
TEMP_PREFIXES = (".preflight-", ".preview-", ".pdf-final-", ".derived-")
MANAGED_PREFIXES = ("pfr_", "preview_r", "pdf_final_r")


@dataclass(frozen=True)
class ArtifactCleanupResult:
    recovered_temporaries: tuple[str, ...]
    removed_artifacts: tuple[str, ...]


class ArtifactLifecycleService:
    """Perform explicit, conservative cleanup under one V2 job directory."""

    def __init__(self, jobs: JobRepository):
        self._jobs = jobs

    def recover_temporaries(self, job_id: str) -> tuple[str, ...]:
        with exclusive_file_lock(self._job_path(job_id) / '.job.lock'):
            return self._recover_temporaries(job_id)

    def _recover_temporaries(self, job_id: str) -> tuple[str, ...]:
        job_path = self._job_path(job_id)
        recovered: list[str] = []
        for directory in MANAGED_DIRECTORIES:
            root = job_path / directory
            if root.is_symlink() or not root.is_dir():
                continue
            with exclusive_file_lock(root / '.publish.lock'):
                for path in root.iterdir():
                    if not path.is_symlink() and path.is_file() and path.suffix == ".tmp" and path.name.startswith(TEMP_PREFIXES):
                        path.unlink()
                        recovered.append(path.relative_to(job_path).as_posix())
        return tuple(sorted(recovered))

    def retain(self, job_id: str, *, keep_latest: int = 3) -> tuple[str, ...]:
        with exclusive_file_lock(self._job_path(job_id) / '.job.lock'):
            return self._retain(job_id, keep_latest=keep_latest)

    def _retain(self, job_id: str, *, keep_latest: int = 3) -> tuple[str, ...]:
        if isinstance(keep_latest, bool) or not isinstance(keep_latest, int) or keep_latest < 1:
            raise ValueError("keep_latest must be a positive integer")
        job_path = self._job_path(job_id)
        removed: list[str] = []
        for directory in ("reports", "previews", "outputs"):
            root = job_path / directory
            if root.is_symlink() or not root.is_dir():
                continue
            with exclusive_file_lock(root / '.publish.lock'):
                candidates = [
                    path for path in root.iterdir()
                    if not path.is_symlink() and path.is_file() and path.suffix in ('.json','.png','.pdf') and path.name.startswith(MANAGED_PREFIXES)
                ]
                candidates.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
                for path in candidates[keep_latest:]:
                    path.unlink()
                    removed.append(path.relative_to(job_path).as_posix())
        return tuple(sorted(removed))

    def recover_and_retain(self, job_id: str, *, keep_latest: int = 3) -> ArtifactCleanupResult:
        recovered = self.recover_temporaries(job_id)
        removed = self.retain(job_id, keep_latest=keep_latest)
        return ArtifactCleanupResult(recovered, removed)

    def _job_path(self, job_id: str) -> Path:
        try:
            path = self._jobs.job_path(job_id)
        except JobRepositoryError:
            raise
        if not path.is_dir():
            raise JobRepositoryError("JOB_NOT_FOUND", "The V2 job does not exist")
        return path


__all__ = [
    "ArtifactCleanupResult",
    "ArtifactLifecycleService",
    "MANAGED_DIRECTORIES",
    "MANAGED_PREFIXES",
    "TEMP_PREFIXES",
]
