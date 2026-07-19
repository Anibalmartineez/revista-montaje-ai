"""Typed temporary output contract for Editor Offset Visual V2.

The models in this module are immutable.  Legacy dictionaries are deliberately
not the internal representation; they are produced only by the infrastructure
adapter immediately before the future connection to the productive renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .geometry import Bounds, Point, Size


OUTPUT_CONTRACT_VERSION: Final = 1
OUTPUT_ISSUE_LEVELS: Final = frozenset({"error", "warning"})
OUTPUT_FACE_NAMES: Final = frozenset({"front", "back"})


@dataclass(frozen=True)
class OutputIssue:
    code: str
    level: str
    message: str
    path: str | None = None
    slot_id: str | None = None
    asset_id: str | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("OutputIssue.code cannot be empty")
        if self.level not in OUTPUT_ISSUE_LEVELS:
            raise ValueError(f"Unsupported output issue level: {self.level!r}")
        if not self.message:
            raise ValueError("OutputIssue.message cannot be empty")

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "level": self.level,
            "message": self.message,
        }
        for key in ("path", "slot_id", "asset_id"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        return result


@dataclass(frozen=True)
class OutputSourceBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class OutputDesign:
    id: str
    asset_id: str
    source_path: Path
    original_filename: str
    page: int
    pdf_box: str
    source_box_mm: OutputSourceBox
    intrinsic_rotation_deg: int


@dataclass(frozen=True)
class OutputMarksProfile:
    id: str
    crop_marks: bool
    registration_marks: bool
    technical_text: bool
    color_bar: bool


@dataclass(frozen=True)
class OutputPosition:
    slot_id: str
    face: str
    design_id: str
    design_index: int
    source_page: int
    pdf_box: str
    trim_size: Size
    productive_size: Size
    rotation_deg: int
    bleed_mm: float
    trim_bounds: Bounds
    productive_bounds: Bounds
    lower_left: Point
    marks_profile_id: str
    crop_marks: bool
    slot_box_final: bool = True

    def __post_init__(self) -> None:
        if self.face not in OUTPUT_FACE_NAMES:
            raise ValueError(f"Unsupported output face: {self.face!r}")
        if not self.slot_box_final:
            raise ValueError("V2 output positions must declare slot_box_final")


@dataclass(frozen=True)
class OutputFace:
    name: str
    enabled: bool
    positions: tuple[OutputPosition, ...]

    def __post_init__(self) -> None:
        if self.name not in OUTPUT_FACE_NAMES:
            raise ValueError(f"Unsupported output face: {self.name!r}")
        if any(position.face != self.name for position in self.positions):
            raise ValueError("Every position must belong to its OutputFace")


@dataclass(frozen=True)
class OutputMargins:
    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class OutputExportConfig:
    profile: str
    render_mode: str
    dpi: int
    front_enabled: bool
    back_enabled: bool
    combine_in_single_pdf: bool
    face_order: tuple[str, ...]
    bleed_policy: str
    crop_to_content: bool
    preserve_vector_content: bool
    default_marks_profile_id: str


@dataclass(frozen=True)
class OutputCtpConfig:
    enabled: bool
    face: str
    gripper_edge: str
    gripper_depth_mm: float
    plate_offset_x_mm: float
    plate_offset_y_mm: float
    color_bar_enabled: bool
    color_bar_height_mm: float
    color_bar_position: str
    technical_text_enabled: bool
    technical_text_job_name: bool
    technical_text_date: bool
    technical_text_plate_name: bool
    registration_marks_enabled: bool


@dataclass(frozen=True)
class OutputJob:
    id: str
    name: str
    revision: int
    sheet_size: Size
    margins: OutputMargins
    imposition_engine: str
    designs: tuple[OutputDesign, ...]
    faces: tuple[OutputFace, ...]
    marks_profiles: tuple[OutputMarksProfile, ...]
    export: OutputExportConfig
    ctp: OutputCtpConfig

    def face(self, name: str) -> OutputFace:
        for face in self.faces:
            if face.name == name:
                return face
        raise KeyError(name)


@dataclass(frozen=True)
class OutputAdapterResult:
    success: bool
    job: OutputJob | None
    issues: tuple[OutputIssue, ...]

    def __post_init__(self) -> None:
        has_errors = any(issue.level == "error" for issue in self.issues)
        if self.success and (has_errors or self.job is None):
            raise ValueError("Successful adapter results require a job and no errors")
        if not self.success and self.job is not None:
            raise ValueError("Failed adapter results cannot expose a partial output job")


__all__ = [
    "OUTPUT_CONTRACT_VERSION",
    "OutputAdapterResult",
    "OutputCtpConfig",
    "OutputDesign",
    "OutputExportConfig",
    "OutputFace",
    "OutputIssue",
    "OutputJob",
    "OutputMargins",
    "OutputMarksProfile",
    "OutputPosition",
    "OutputSourceBox",
]
