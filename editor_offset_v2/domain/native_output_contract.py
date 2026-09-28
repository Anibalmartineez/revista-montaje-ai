"""Immutable findings owned by the native V2 renderer capability diagnosis.

This contract does not depend on historical output jobs or renderer adapters.
Operation blockers are supplied by native_output_capabilities and consumed by
preflight; a finding alone is not a physical source or output approval.
"""

from dataclasses import dataclass


NATIVE_DIAGNOSIS_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class NativeOutputIssue:
    code: str
    level: str
    message: str
    path: str | None = None
    slot_id: str | None = None
    asset_id: str | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("NativeOutputIssue.code cannot be empty")
        if self.level not in {"error", "warning"}:
            raise ValueError(f"Unsupported native output issue level: {self.level!r}")
        if not self.message:
            raise ValueError("NativeOutputIssue.message cannot be empty")

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"code": self.code, "level": self.level, "message": self.message}
        for key in ("path", "slot_id", "asset_id"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        return result
