"""Application service for Editor Offset V2 job lifecycle and revisions."""

from __future__ import annotations

import copy
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from editor_offset_v2.domain.layout_v2 import EXPECTED_COORDINATE_SYSTEM
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.job_repository import (
    JobRepository,
    JobRepositoryError,
)


INITIAL_REVISION = 1
DEFAULT_JOB_NAME = "Nuevo montaje offset V2"


@dataclass(frozen=True)
class JobServiceError(Exception):
    code: str
    message: str
    status_code: int
    issues: tuple[dict[str, str], ...] = ()

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class JobResult:
    job_id: str
    revision: int
    layout: dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def create_initial_layout_v2(
    job_id: str,
    name: str | None = None,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Build a new, empty and valid Layout V2 from explicit V2 defaults."""

    timestamp = now or utc_now_iso()
    layout: dict[str, Any] = {
        "layout_schema_version": 2,
        "job": {
            "id": job_id,
            "name": name or DEFAULT_JOB_NAME,
            "revision": INITIAL_REVISION,
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "coordinate_system": dict(EXPECTED_COORDINATE_SYSTEM),
        "sheet": {
            "size_mm": {"width": 700.0, "height": 500.0},
            "printable_margins_mm": {
                "left": 0.0,
                "right": 0.0,
                "bottom": 0.0,
                "top": 0.0,
            },
        },
        "faces": {
            "enabled": ["front"],
            "duplex": {"enabled": False, "flip": "none"},
        },
        "assets": [],
        "works": [],
        "slots": [],
        "imposition": {
            "engine": "manual",
            "engine_version": "2.0.0",
            "settings": {
                "horizontal_gap_mm": 0.0,
                "vertical_gap_mm": 0.0,
                "exact_quantity": True,
                "fill_remaining_space": False,
                "respect_priority": True,
                "respect_preferred_zones": True,
            },
            "last_result": None,
        },
        "export": {
            "profile": "offset_production",
            "render_mode": "vector_hybrid",
            "dpi": 300,
            "faces": {
                "front": True,
                "back": False,
                "combine_in_single_pdf": False,
                "order": ["front"],
            },
            "marks_profiles": [
                {
                    "id": "standard_offset",
                    "crop_marks": True,
                    "registration_marks": False,
                    "technical_text": False,
                    "color_bar": False,
                }
            ],
            "default_marks_profile_id": "standard_offset",
            "bleed_policy": "slot_geometry",
            "crop_to_content": False,
            "preserve_vector_content": True,
        },
        "ctp": {
            "enabled": False,
            "face": "front",
            "gripper": {"edge": "bottom", "depth_mm": 0.0},
            "plate": {"offset_x_mm": 0.0, "offset_y_mm": 0.0},
            "color_bar": {
                "enabled": False,
                "height_mm": 0.0,
                "position": "opposite_gripper",
            },
            "technical_text": {
                "enabled": False,
                "job_name": False,
                "date": False,
                "plate_name": False,
            },
            "registration_marks": {"enabled": False},
        },
    }
    issues = validate_layout_v2(layout)
    if issues:
        raise RuntimeError("Initial Layout V2 defaults violate the canonical contract")
    return layout


class JobService:
    def __init__(
        self,
        repository: JobRepository,
        *,
        clock: Callable[[], str] = utc_now_iso,
        id_factory: Callable[[], str] | None = None,
    ):
        self._repository = repository
        self._clock = clock
        self._id_factory = id_factory or (lambda: f"ev2_{secrets.token_hex(12)}")

    def create_job(self, name: str | None = None) -> JobResult:
        normalized_name = self._validate_name(name)
        for _ in range(5):
            job_id = self._id_factory()
            try:
                if self._repository.job_exists(job_id):
                    continue
                layout = create_initial_layout_v2(
                    job_id,
                    normalized_name,
                    now=self._clock(),
                )
                self._repository.create_job(job_id, layout)
                return JobResult(job_id, INITIAL_REVISION, layout)
            except JobRepositoryError as exc:
                if exc.code == "PERSISTENCE_ERROR" and self._repository.job_exists(
                    job_id
                ):
                    continue
                raise self._map_repository_error(exc) from exc
        raise JobServiceError(
            "PERSISTENCE_ERROR",
            "A unique V2 job identifier could not be allocated",
            500,
        )

    def get_job(self, job_id: object) -> JobResult:
        layout = self._read_valid_layout(job_id)
        return JobResult(job_id, layout["job"]["revision"], layout)

    def save_layout(
        self,
        job_id: object,
        base_revision: object,
        layout: object,
    ) -> JobResult:
        persisted = self._read_valid_layout(job_id)
        persisted_revision = persisted["job"]["revision"]
        if (
            isinstance(base_revision, bool)
            or not isinstance(base_revision, int)
            or base_revision < 0
        ):
            raise JobServiceError(
                "INVALID_LAYOUT",
                "base_revision must be a non-negative integer",
                400,
                ({"code": "TYPE_INTEGER", "path": "$.base_revision", "message": "must be a non-negative integer"},),
            )
        if base_revision != persisted_revision:
            raise JobServiceError(
                "REVISION_CONFLICT",
                "The submitted base revision does not match the persisted layout",
                409,
            )
        if not isinstance(layout, Mapping):
            raise JobServiceError(
                "INVALID_LAYOUT",
                "layout must be a JSON object",
                400,
                ({"code": "TYPE_OBJECT", "path": "$.layout", "message": "must be an object"},),
            )
        submitted = copy.deepcopy(dict(layout))
        submitted_job = submitted.get("job")
        if not isinstance(submitted_job, dict):
            self._raise_validation_issues(submitted)
        if submitted_job.get("id") != job_id:
            raise JobServiceError(
                "INVALID_LAYOUT",
                "layout.job.id must match the job_id in the URL",
                400,
                ({"code": "JOB_ID_MISMATCH", "path": "$.layout.job.id", "message": "must match the URL job_id"},),
            )
        if submitted_job.get("revision") != base_revision:
            raise JobServiceError(
                "REVISION_CONFLICT",
                "layout.job.revision must equal base_revision",
                409,
            )
        self._raise_validation_issues(submitted)

        saved = copy.deepcopy(submitted)
        saved["job"]["revision"] = persisted_revision + 1
        saved["job"]["created_at"] = persisted["job"]["created_at"]
        saved["job"]["updated_at"] = self._clock()
        self._raise_validation_issues(saved)
        try:
            self._repository.replace_layout_if_revision(
                job_id,
                persisted_revision,
                saved,
            )
        except JobRepositoryError as exc:
            raise self._map_repository_error(exc) from exc
        return JobResult(job_id, saved["job"]["revision"], saved)

    def _read_valid_layout(self, job_id: object) -> dict[str, Any]:
        try:
            layout = self._repository.read_layout(job_id)
        except JobRepositoryError as exc:
            raise self._map_repository_error(exc) from exc
        issues = validate_layout_v2(layout)
        if issues:
            raise JobServiceError(
                "INVALID_LAYOUT",
                "The persisted job does not contain a valid Layout V2",
                500,
                tuple(issue.as_dict() for issue in issues),
            )
        if layout["job"]["id"] != job_id:
            raise JobServiceError(
                "INVALID_LAYOUT",
                "The persisted layout job id does not match its directory",
                500,
                ({"code": "JOB_ID_MISMATCH", "path": "$.job.id", "message": "does not match the job directory"},),
            )
        return layout

    @staticmethod
    def _validate_name(name: object) -> str | None:
        if name is None:
            return None
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 160:
            raise JobServiceError(
                "INVALID_LAYOUT",
                "name must be a non-empty string with at most 160 characters",
                400,
            )
        return name.strip()

    @staticmethod
    def _raise_validation_issues(layout: object) -> None:
        issues = validate_layout_v2(layout)
        if issues:
            raise JobServiceError(
                "INVALID_LAYOUT",
                "The submitted document is not a valid Layout V2",
                400,
                tuple(issue.as_dict() for issue in issues),
            )

    @staticmethod
    def _map_repository_error(error: JobRepositoryError) -> JobServiceError:
        status_codes = {
            "INVALID_JOB_ID": 400,
            "JOB_NOT_FOUND": 404,
            "REVISION_CONFLICT": 409,
            "PERSISTENCE_ERROR": 500,
        }
        return JobServiceError(
            error.code,
            error.message,
            status_codes.get(error.code, 500),
        )


__all__ = [
    "DEFAULT_JOB_NAME",
    "INITIAL_REVISION",
    "JobResult",
    "JobService",
    "JobServiceError",
    "create_initial_layout_v2",
    "utc_now_iso",
]
