"""Application service for non-persistent Editor Offset V2 Repeat proposals."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from editor_offset_v2.application.job_service import JobService, utc_now_iso
from editor_offset_v2.domain.repeat_contract import RepeatResultV2
from editor_offset_v2.infrastructure.repeat_engine_adapter import RepeatEngineAdapter


@dataclass(frozen=True)
class RepeatServiceError(Exception):
    code: str
    message: str
    status_code: int
    issues: tuple[dict[str, object], ...] = ()

    def __str__(self) -> str:
        return self.message


class RepeatService:
    def __init__(
        self,
        jobs: JobService,
        adapter: RepeatEngineAdapter | None = None,
        *,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self._jobs = jobs
        self._adapter = adapter or RepeatEngineAdapter()
        self._clock = clock

    def propose(self, job_id: object, payload: object) -> RepeatResultV2:
        request = self._validate_request(payload)
        current = self._jobs.get_job(job_id)
        if request["base_revision"] != current.revision:
            raise RepeatServiceError(
                "REVISION_CONFLICT",
                "La revisión base no coincide con el Layout V2 persistido.",
                409,
            )
        face = request["face"]
        if face not in current.layout["faces"]["enabled"]:
            raise RepeatServiceError(
                "INVALID_FACE",
                "La cara solicitada no está habilitada en el Layout V2.",
                400,
            )
        settings = {
            **request["settings"],
            "respect_priority": current.layout["imposition"]["settings"]["respect_priority"],
            "respect_preferred_zones": current.layout["imposition"]["settings"]["respect_preferred_zones"],
        }
        operation_payload = {
            "job_id": current.job_id,
            "revision": current.revision,
            "work_ids": request["work_ids"],
            "face": face,
            "settings": settings,
            "apply_mode": request["apply_mode"],
        }
        digest = hashlib.sha256(
            json.dumps(
                operation_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]
        return self._adapter.propose(
            current.layout,
            request["work_ids"],
            face,
            settings,
            operation_id=f"repeat_{digest}",
            generated_at=self._clock(),
            apply_mode=request["apply_mode"],
        )

    @staticmethod
    def _validate_request(payload: object) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise RepeatServiceError(
                "INVALID_REPEAT_REQUEST",
                "La petición Repeat debe ser un objeto JSON.",
                400,
            )
        request = dict(payload)
        allowed = {"base_revision", "work_ids", "face", "settings", "apply_mode"}
        required = {"base_revision", "work_ids", "face", "settings"}
        if not required <= set(request) or set(request) - allowed:
            raise RepeatServiceError(
                "INVALID_REPEAT_REQUEST",
                "La petición Repeat contiene campos ausentes o no soportados.",
                400,
            )
        revision = request["base_revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise RepeatServiceError(
                "INVALID_REPEAT_REQUEST",
                "base_revision debe ser un entero no negativo.",
                400,
            )
        work_ids = request["work_ids"]
        if (
            not isinstance(work_ids, list)
            or not work_ids
            or any(not isinstance(item, str) or not item for item in work_ids)
            or len(set(work_ids)) != len(work_ids)
        ):
            raise RepeatServiceError(
                "INVALID_REPEAT_REQUEST",
                "work_ids debe ser una lista no vacía de IDs únicos.",
                400,
            )
        if request["face"] not in {"front", "back"}:
            raise RepeatServiceError(
                "INVALID_FACE",
                "face debe ser front o back.",
                400,
            )
        settings = request["settings"]
        expected_settings = {
            "horizontal_gap_mm",
            "vertical_gap_mm",
            "exact_quantity",
            "fill_remaining_space",
            "allow_partial",
        }
        if not isinstance(settings, Mapping) or set(settings) != expected_settings:
            raise RepeatServiceError(
                "INVALID_REPEAT_SETTINGS",
                "settings debe contener únicamente la configuración Repeat V2 requerida.",
                400,
            )
        normalized_settings = dict(settings)
        for key in ("horizontal_gap_mm", "vertical_gap_mm"):
            value = normalized_settings[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise RepeatServiceError(
                    "INVALID_REPEAT_SETTINGS",
                    f"{key} debe ser un número finito no negativo.",
                    400,
                )
            normalized_settings[key] = float(value)
        for key in ("exact_quantity", "fill_remaining_space", "allow_partial"):
            if not isinstance(normalized_settings[key], bool):
                raise RepeatServiceError(
                    "INVALID_REPEAT_SETTINGS",
                    f"{key} debe ser booleano.",
                    400,
                )
        apply_mode = request.get("apply_mode", "add")
        if apply_mode not in {"add", "replace_work_face"}:
            raise RepeatServiceError(
                "INVALID_REPEAT_REQUEST",
                "apply_mode debe ser add o replace_work_face.",
                400,
            )
        return {
            "base_revision": revision,
            "work_ids": list(work_ids),
            "face": request["face"],
            "settings": normalized_settings,
            "apply_mode": apply_mode,
        }


__all__ = ["RepeatService", "RepeatServiceError"]
