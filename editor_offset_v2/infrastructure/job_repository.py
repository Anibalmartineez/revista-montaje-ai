"""Filesystem repository for isolated Editor Offset V2 jobs."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final


LAYOUT_FILENAME: Final = "layout_v2.json"
JOB_DIRECTORIES: Final = ("assets", "derived", "previews", "outputs", "reports")
JOB_ID_PATTERN: Final = re.compile(r"^ev2_[a-f0-9]{24}$")
MAX_JOB_ID_LENGTH: Final = 64


class JobRepositoryError(Exception):
    """Controlled infrastructure failure with a stable application code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


_LOCKS_GUARD = threading.Lock()
_JOB_LOCKS: dict[tuple[str, str], threading.Lock] = {}


def _job_lock(root: Path, job_id: str) -> threading.Lock:
    key = (str(root), job_id)
    with _LOCKS_GUARD:
        return _JOB_LOCKS.setdefault(key, threading.Lock())


def validate_job_id(job_id: object) -> str:
    if not isinstance(job_id, str):
        raise JobRepositoryError("INVALID_JOB_ID", "job_id must be a string")
    if len(job_id) > MAX_JOB_ID_LENGTH or not JOB_ID_PATTERN.fullmatch(job_id):
        raise JobRepositoryError(
            "INVALID_JOB_ID",
            "job_id must match the server-generated ev2_ identifier format",
        )
    return job_id


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is forbidden: {value}")


class JobRepository:
    """Persist Layout V2 documents beneath one explicitly supplied root."""

    def __init__(self, jobs_root: Path):
        self._root = Path(jobs_root).resolve(strict=False)

    @property
    def jobs_root(self) -> Path:
        return self._root

    def job_path(self, job_id: object) -> Path:
        safe_id = validate_job_id(job_id)
        candidate = (self._root / safe_id).resolve(strict=False)
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise JobRepositoryError(
                "INVALID_JOB_ID",
                "job_id resolves outside the configured V2 jobs root",
            ) from exc
        return candidate

    def layout_path(self, job_id: object) -> Path:
        return self.job_path(job_id) / LAYOUT_FILENAME

    def job_exists(self, job_id: object) -> bool:
        return self.job_path(job_id).is_dir()

    def create_job(self, job_id: object, layout: Mapping[str, Any]) -> Path:
        job_dir = self.job_path(job_id)
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            job_dir.mkdir(parents=False, exist_ok=False)
            for directory_name in JOB_DIRECTORIES:
                (job_dir / directory_name).mkdir()
            self._write_layout_atomic(job_dir / LAYOUT_FILENAME, layout)
        except FileExistsError as exc:
            raise JobRepositoryError(
                "PERSISTENCE_ERROR",
                "The generated V2 job identifier already exists",
            ) from exc
        except JobRepositoryError:
            raise
        except (OSError, TypeError, ValueError) as exc:
            raise JobRepositoryError(
                "PERSISTENCE_ERROR",
                "The V2 job could not be created",
            ) from exc
        return job_dir

    def read_layout(self, job_id: object) -> dict[str, Any]:
        job_dir = self.job_path(job_id)
        if not job_dir.is_dir():
            raise JobRepositoryError("JOB_NOT_FOUND", "The V2 job does not exist")
        layout_path = job_dir / LAYOUT_FILENAME
        if not layout_path.is_file():
            raise JobRepositoryError(
                "PERSISTENCE_ERROR",
                "The V2 job exists but layout_v2.json is missing",
            )
        try:
            with layout_path.open("r", encoding="utf-8") as stream:
                value = json.load(stream, parse_constant=_reject_json_constant)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise JobRepositoryError(
                "PERSISTENCE_ERROR",
                "The persisted V2 layout cannot be read as strict UTF-8 JSON",
            ) from exc
        if not isinstance(value, dict):
            raise JobRepositoryError(
                "PERSISTENCE_ERROR",
                "The persisted V2 layout root must be a JSON object",
            )
        return value

    def replace_layout_if_revision(
        self,
        job_id: object,
        expected_revision: int,
        layout: Mapping[str, Any],
    ) -> None:
        safe_id = validate_job_id(job_id)
        with _job_lock(self._root, safe_id):
            persisted = self.read_layout(safe_id)
            revision = (persisted.get("job") or {}).get("revision")
            if revision != expected_revision:
                raise JobRepositoryError(
                    "REVISION_CONFLICT",
                    "The persisted revision changed before the save completed",
                )
            self._write_layout_atomic(self.layout_path(safe_id), layout)

    def _write_layout_atomic(
        self,
        layout_path: Path,
        layout: Mapping[str, Any],
    ) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".layout_v2.",
                suffix=".tmp",
                dir=layout_path.parent,
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(
                    layout,
                    stream,
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=2,
                    sort_keys=True,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, layout_path)
            temporary_path = None
        except (OSError, TypeError, ValueError) as exc:
            raise JobRepositoryError(
                "PERSISTENCE_ERROR",
                "The V2 layout could not be written atomically",
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass


__all__ = [
    "JOB_DIRECTORIES",
    "JOB_ID_PATTERN",
    "LAYOUT_FILENAME",
    "MAX_JOB_ID_LENGTH",
    "JobRepository",
    "JobRepositoryError",
    "validate_job_id",
]
