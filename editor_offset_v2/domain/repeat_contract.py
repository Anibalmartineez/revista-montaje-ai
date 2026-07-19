"""Explicit immutable result models for Editor Offset V2 Repeat proposals."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal


IssueLevel = Literal["error", "warning"]


@dataclass(frozen=True)
class RepeatIssueV2:
    code: str
    level: IssueLevel
    message: str
    path: str | None = None
    work_id: str | None = None
    slot_id: str | None = None
    asset_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "level": self.level,
            "message": self.message,
            "path": self.path,
            "work_id": self.work_id,
            "slot_id": self.slot_id,
            "asset_id": self.asset_id,
        }


@dataclass(frozen=True)
class RepeatMetricsV2:
    printable_width_mm: float
    printable_height_mm: float
    printable_area_mm2: float
    occupied_productive_area_mm2: float
    utilization_percent: float

    def as_dict(self) -> dict[str, float]:
        return {
            "printable_width_mm": self.printable_width_mm,
            "printable_height_mm": self.printable_height_mm,
            "printable_area_mm2": self.printable_area_mm2,
            "occupied_productive_area_mm2": self.occupied_productive_area_mm2,
            "utilization_percent": self.utilization_percent,
        }


@dataclass(frozen=True)
class RepeatResultV2:
    success: bool
    operation_id: str
    generated_at: str
    slots: tuple[dict[str, Any], ...]
    requested: int
    placed: int
    unplaced: int
    overproduced: int
    warnings: tuple[str, ...]
    metrics: RepeatMetricsV2
    issues: tuple[RepeatIssueV2, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "operation_id": self.operation_id,
            "generated_at": self.generated_at,
            "slots": copy.deepcopy(list(self.slots)),
            "requested": self.requested,
            "placed": self.placed,
            "unplaced": self.unplaced,
            "overproduced": self.overproduced,
            "warnings": list(self.warnings),
            "metrics": self.metrics.as_dict(),
            "issues": [issue.as_dict() for issue in self.issues],
        }


__all__ = [
    "RepeatIssueV2",
    "RepeatMetricsV2",
    "RepeatResultV2",
]
