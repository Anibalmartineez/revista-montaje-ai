"""Flask configuration helpers for the isolated Editor Offset V2 surface."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


EDITOR_OFFSET_V2_ENABLED = "EDITOR_OFFSET_V2_ENABLED"
EDITOR_OFFSET_V2_JOBS_ROOT = "EDITOR_OFFSET_V2_JOBS_ROOT"


def _environment_flag(name: str, default: bool = False) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def configure_editor_offset_v2(app: Any) -> None:
    """Install V2 defaults without overriding explicit app/test settings."""

    app.config.setdefault(
        EDITOR_OFFSET_V2_ENABLED,
        _environment_flag(EDITOR_OFFSET_V2_ENABLED),
    )
    app.config.setdefault(
        EDITOR_OFFSET_V2_JOBS_ROOT,
        str(Path(app.instance_path) / "editor_offset_v2_jobs"),
    )


__all__ = [
    "EDITOR_OFFSET_V2_ENABLED",
    "EDITOR_OFFSET_V2_JOBS_ROOT",
    "configure_editor_offset_v2",
]
