"""Strict, dependency-free validation for persisted Layout V2 documents."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .layout_v2 import (
    EXPECTED_COORDINATE_SYSTEM,
    LAYOUT_SCHEMA_VERSION,
    LEGACY_FIELD_NAMES,
    VALID_ASSET_STATUSES,
    VALID_BLEED_POLICIES,
    VALID_CLIP_TARGETS,
    VALID_DUPLEX_FLIPS,
    VALID_ENGINES,
    VALID_FACES,
    VALID_FIT_MODES,
    VALID_GENERATOR_TYPES,
    VALID_IMPOSITION_STATUSES,
    VALID_ISSUE_LEVELS,
    VALID_LOCK_SOURCES,
    VALID_PDF_BOXES,
    VALID_PREFLIGHT_STATUSES,
    VALID_RENDER_MODES,
)


@dataclass(frozen=True)
class ValidationIssue:
    """A stable machine-readable contract validation issue."""

    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class LayoutV2ValidationError(ValueError):
    """Raised when a Layout V2 document violates the persisted contract."""

    def __init__(self, issues: Sequence[ValidationIssue]):
        self.issues = tuple(issues)
        summary = "; ".join(f"{item.path}: {item.message}" for item in self.issues[:5])
        if len(self.issues) > 5:
            summary += f"; and {len(self.issues) - 5} more issue(s)"
        super().__init__(summary or "Invalid Layout V2 document")


class _Validator:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def issue(self, code: str, path: str, message: str) -> None:
        self.issues.append(ValidationIssue(code=code, path=path, message=message))

    def object(
        self,
        value: Any,
        path: str,
        *,
        required: Iterable[str],
        optional: Iterable[str] = (),
    ) -> Mapping[str, Any] | None:
        if not isinstance(value, dict):
            self.issue("TYPE_OBJECT", path, "must be an object")
            return None
        required_set = set(required)
        allowed = required_set | set(optional)
        for key in sorted(required_set - set(value)):
            self.issue("REQUIRED_FIELD", f"{path}.{key}", "is required")
        for key in sorted(set(value) - allowed):
            self.issue("UNKNOWN_FIELD", f"{path}.{key}", "is not allowed")
        return value

    def array(self, value: Any, path: str) -> list[Any] | None:
        if not isinstance(value, list):
            self.issue("TYPE_ARRAY", path, "must be an array")
            return None
        return value

    def string(self, value: Any, path: str, *, nonempty: bool = True) -> str | None:
        if not isinstance(value, str):
            self.issue("TYPE_STRING", path, "must be a string")
            return None
        if nonempty and not value.strip():
            self.issue("EMPTY_STRING", path, "must not be empty")
            return None
        return value

    def boolean(self, value: Any, path: str) -> bool | None:
        if not isinstance(value, bool):
            self.issue("TYPE_BOOLEAN", path, "must be a boolean")
            return None
        return value

    def number(
        self,
        value: Any,
        path: str,
        *,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.issue("TYPE_NUMBER", path, "must be a finite number")
            return None
        result = float(value)
        if not math.isfinite(result):
            self.issue("NON_FINITE_NUMBER", path, "must be finite")
            return None
        if positive and result <= 0:
            self.issue("NON_POSITIVE_NUMBER", path, "must be greater than zero")
        if nonnegative and result < 0:
            self.issue("NEGATIVE_NUMBER", path, "must be zero or greater")
        return result

    def integer(
        self,
        value: Any,
        path: str,
        *,
        minimum: int | None = None,
    ) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            self.issue("TYPE_INTEGER", path, "must be an integer")
            return None
        if minimum is not None and value < minimum:
            self.issue("INTEGER_RANGE", path, f"must be at least {minimum}")
        return value

    def enum(self, value: Any, path: str, allowed: Iterable[Any]) -> Any:
        allowed_set = set(allowed)
        if value not in allowed_set:
            self.issue(
                "INVALID_ENUM",
                path,
                f"must be one of {sorted(allowed_set, key=str)}",
            )
            return None
        return value


def _scan_legacy_fields(value: Any, validator: _Validator, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in LEGACY_FIELD_NAMES:
                validator.issue(
                    "LEGACY_FIELD",
                    child_path,
                    "legacy fields are forbidden in Layout V2",
                )
            _scan_legacy_fields(child, validator, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_legacy_fields(child, validator, f"{path}[{index}]")


def _validate_size(value: Any, validator: _Validator, path: str) -> None:
    obj = validator.object(value, path, required={"width", "height"})
    if obj is None:
        return
    validator.number(obj.get("width"), f"{path}.width", positive=True)
    validator.number(obj.get("height"), f"{path}.height", positive=True)


def _validate_rect(value: Any, validator: _Validator, path: str) -> None:
    obj = validator.object(value, path, required={"x", "y", "width", "height"})
    if obj is None:
        return
    validator.number(obj.get("x"), f"{path}.x")
    validator.number(obj.get("y"), f"{path}.y")
    validator.number(obj.get("width"), f"{path}.width", positive=True)
    validator.number(obj.get("height"), f"{path}.height", positive=True)


def _validate_source_ref(
    value: Any,
    validator: _Validator,
    path: str,
    *,
    allow_null: bool,
) -> dict[str, Any] | None:
    if value is None and allow_null:
        return None
    obj = validator.object(value, path, required={"asset_id", "page", "pdf_box"})
    if obj is None:
        return None
    validator.string(obj.get("asset_id"), f"{path}.asset_id")
    validator.integer(obj.get("page"), f"{path}.page", minimum=1)
    validator.enum(obj.get("pdf_box"), f"{path}.pdf_box", VALID_PDF_BOXES)
    return dict(obj)


def _validate_issue(value: Any, validator: _Validator, path: str) -> None:
    obj = validator.object(value, path, required={"code", "level", "message"})
    if obj is None:
        return
    validator.string(obj.get("code"), f"{path}.code")
    validator.enum(obj.get("level"), f"{path}.level", VALID_ISSUE_LEVELS)
    validator.string(obj.get("message"), f"{path}.message")


def _validate_preflight(value: Any, validator: _Validator, path: str) -> None:
    obj = validator.object(
        value,
        path,
        required={
            "status",
            "color_spaces",
            "minimum_effective_dpi",
            "has_transparency",
            "has_overprint",
            "issues",
        },
    )
    if obj is None:
        return
    validator.enum(obj.get("status"), f"{path}.status", VALID_PREFLIGHT_STATUSES)
    color_spaces = validator.array(obj.get("color_spaces"), f"{path}.color_spaces")
    if color_spaces is not None:
        for index, color_space in enumerate(color_spaces):
            validator.string(color_space, f"{path}.color_spaces[{index}]")
    dpi = obj.get("minimum_effective_dpi")
    if dpi is not None:
        validator.number(dpi, f"{path}.minimum_effective_dpi", positive=True)
    transparency = obj.get("has_transparency")
    if transparency is not None:
        validator.boolean(transparency, f"{path}.has_transparency")
    overprint = obj.get("has_overprint")
    if overprint is not None:
        validator.boolean(overprint, f"{path}.has_overprint")
    issues = validator.array(obj.get("issues"), f"{path}.issues")
    if issues is not None:
        for index, issue in enumerate(issues):
            _validate_issue(issue, validator, f"{path}.issues[{index}]")


def _validate_assets(
    value: Any, validator: _Validator
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[int, set[str]]]]:
    assets = validator.array(value, "$.assets")
    by_id: dict[str, dict[str, Any]] = {}
    page_boxes: dict[str, dict[int, set[str]]] = {}
    if assets is None:
        return by_id, page_boxes

    for index, asset_value in enumerate(assets):
        path = f"$.assets[{index}]"
        asset = validator.object(
            asset_value,
            path,
            required={
                "id",
                "original_filename",
                "storage_key",
                "mime_type",
                "sha256",
                "page_count",
                "status",
                "created_at",
                "pages",
            },
        )
        if asset is None:
            continue
        asset_id = validator.string(asset.get("id"), f"{path}.id")
        if asset_id:
            if asset_id in by_id:
                validator.issue("DUPLICATE_ID", f"{path}.id", f"duplicate asset id {asset_id!r}")
            else:
                by_id[asset_id] = dict(asset)
        validator.string(asset.get("original_filename"), f"{path}.original_filename")
        validator.string(asset.get("storage_key"), f"{path}.storage_key")
        mime_type = validator.string(asset.get("mime_type"), f"{path}.mime_type")
        if mime_type is not None and mime_type != "application/pdf":
            validator.issue("INVALID_MIME_TYPE", f"{path}.mime_type", "must be application/pdf")
        sha256 = validator.string(asset.get("sha256"), f"{path}.sha256")
        if sha256 is not None and (
            len(sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha256)
        ):
            validator.issue("INVALID_SHA256", f"{path}.sha256", "must contain 64 hexadecimal characters")
        page_count = validator.integer(asset.get("page_count"), f"{path}.page_count", minimum=1)
        validator.enum(asset.get("status"), f"{path}.status", VALID_ASSET_STATUSES)
        validator.string(asset.get("created_at"), f"{path}.created_at")

        pages = validator.array(asset.get("pages"), f"{path}.pages")
        known_pages: dict[int, set[str]] = {}
        if pages is not None:
            for page_index, page_value in enumerate(pages):
                page_path = f"{path}.pages[{page_index}]"
                page = validator.object(
                    page_value,
                    page_path,
                    required={
                        "number",
                        "intrinsic_rotation_deg",
                        "boxes_mm",
                        "preview_key",
                        "preflight",
                    },
                )
                if page is None:
                    continue
                number = validator.integer(page.get("number"), f"{page_path}.number", minimum=1)
                if number is not None:
                    if number in known_pages:
                        validator.issue("DUPLICATE_PAGE", f"{page_path}.number", "page number is duplicated")
                    else:
                        known_pages[number] = set()
                rotation = validator.number(
                    page.get("intrinsic_rotation_deg"),
                    f"{page_path}.intrinsic_rotation_deg",
                )
                if rotation is not None and rotation not in {0.0, 90.0, 180.0, 270.0}:
                    validator.issue(
                        "INVALID_ROTATION",
                        f"{page_path}.intrinsic_rotation_deg",
                        "intrinsic PDF rotation must be 0, 90, 180 or 270",
                    )
                boxes = validator.object(
                    page.get("boxes_mm"),
                    f"{page_path}.boxes_mm",
                    required={"media", "trim", "bleed", "crop"},
                )
                if boxes is not None:
                    for box_name in ("media", "trim", "bleed", "crop"):
                        box_value = boxes.get(box_name)
                        if box_name == "media" and box_value is None:
                            validator.issue(
                                "MISSING_MEDIA_BOX",
                                f"{page_path}.boxes_mm.media",
                                "MediaBox must be present",
                            )
                        elif box_value is not None:
                            _validate_rect(box_value, validator, f"{page_path}.boxes_mm.{box_name}")
                            if number is not None:
                                known_pages[number].add(box_name)
                preview_key = page.get("preview_key")
                if preview_key is not None:
                    validator.string(preview_key, f"{page_path}.preview_key")
                _validate_preflight(page.get("preflight"), validator, f"{page_path}.preflight")

        if page_count is not None and pages is not None and page_count != len(pages):
            validator.issue(
                "PAGE_COUNT_MISMATCH",
                f"{path}.page_count",
                "must equal the number of page metadata entries",
            )
        if asset_id:
            page_boxes[asset_id] = known_pages
    return by_id, page_boxes


def _validate_works(
    value: Any,
    validator: _Validator,
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
    works = validator.array(value, "$.works")
    by_id: dict[str, dict[str, Any]] = {}
    sources: list[tuple[str, dict[str, Any]]] = []
    if works is None:
        return by_id, sources

    for index, work_value in enumerate(works):
        path = f"$.works[{index}]"
        work = validator.object(
            work_value,
            path,
            required={
                "id",
                "name",
                "trim_size_mm",
                "bleed_mm",
                "requested_forms",
                "allowed_rotations_deg",
                "priority",
                "preferred_zone",
                "preferred_flow",
                "front_source",
                "back_source",
            },
        )
        if work is None:
            continue
        work_id = validator.string(work.get("id"), f"{path}.id")
        if work_id:
            if work_id in by_id:
                validator.issue("DUPLICATE_ID", f"{path}.id", f"duplicate work id {work_id!r}")
            else:
                by_id[work_id] = dict(work)
        validator.string(work.get("name"), f"{path}.name")
        _validate_size(work.get("trim_size_mm"), validator, f"{path}.trim_size_mm")
        validator.number(work.get("bleed_mm"), f"{path}.bleed_mm", nonnegative=True)
        validator.integer(work.get("requested_forms"), f"{path}.requested_forms", minimum=1)
        rotations = validator.array(work.get("allowed_rotations_deg"), f"{path}.allowed_rotations_deg")
        if rotations is not None:
            if not rotations:
                validator.issue("EMPTY_ROTATIONS", f"{path}.allowed_rotations_deg", "must not be empty")
            seen_rotations: set[float] = set()
            for rotation_index, rotation_value in enumerate(rotations):
                rotation_path = f"{path}.allowed_rotations_deg[{rotation_index}]"
                rotation = validator.number(rotation_value, rotation_path)
                if rotation is not None:
                    if not 0 <= rotation < 360:
                        validator.issue("INVALID_ROTATION", rotation_path, "must be in [0, 360)")
                    if rotation in seen_rotations:
                        validator.issue("DUPLICATE_ROTATION", rotation_path, "rotation is duplicated")
                    seen_rotations.add(rotation)
        validator.integer(work.get("priority"), f"{path}.priority", minimum=0)
        validator.string(work.get("preferred_zone"), f"{path}.preferred_zone")
        validator.string(work.get("preferred_flow"), f"{path}.preferred_flow")
        for source_name in ("front_source", "back_source"):
            source = _validate_source_ref(
                work.get(source_name),
                validator,
                f"{path}.{source_name}",
                allow_null=True,
            )
            if source is not None:
                sources.append((f"{path}.{source_name}", source))
    return by_id, sources


def _validate_content_transform(value: Any, validator: _Validator, path: str) -> None:
    transform = validator.object(
        value,
        path,
        required={
            "fit_mode",
            "scale_x",
            "scale_y",
            "offset_mm",
            "rotation_deg",
            "mirror_x",
            "mirror_y",
            "clip_to",
        },
    )
    if transform is None:
        return
    validator.enum(transform.get("fit_mode"), f"{path}.fit_mode", VALID_FIT_MODES)
    validator.number(transform.get("scale_x"), f"{path}.scale_x", positive=True)
    validator.number(transform.get("scale_y"), f"{path}.scale_y", positive=True)
    offset = validator.object(transform.get("offset_mm"), f"{path}.offset_mm", required={"x", "y"})
    if offset is not None:
        validator.number(offset.get("x"), f"{path}.offset_mm.x")
        validator.number(offset.get("y"), f"{path}.offset_mm.y")
    rotation = validator.number(transform.get("rotation_deg"), f"{path}.rotation_deg")
    if rotation is not None and not 0 <= rotation < 360:
        validator.issue("INVALID_ROTATION", f"{path}.rotation_deg", "must be in [0, 360)")
    validator.boolean(transform.get("mirror_x"), f"{path}.mirror_x")
    validator.boolean(transform.get("mirror_y"), f"{path}.mirror_y")
    validator.enum(transform.get("clip_to"), f"{path}.clip_to", VALID_CLIP_TARGETS)


def _validate_slots(
    value: Any,
    validator: _Validator,
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
    slots = validator.array(value, "$.slots")
    by_id: dict[str, dict[str, Any]] = {}
    sources: list[tuple[str, dict[str, Any]]] = []
    if slots is None:
        return by_id, sources

    for index, slot_value in enumerate(slots):
        path = f"$.slots[{index}]"
        slot = validator.object(
            slot_value,
            path,
            required={
                "id",
                "face",
                "work_id",
                "source",
                "geometry",
                "content_transform",
                "locks",
                "production",
                "generated_by",
            },
        )
        if slot is None:
            continue
        slot_id = validator.string(slot.get("id"), f"{path}.id")
        if slot_id:
            if slot_id in by_id:
                validator.issue("DUPLICATE_ID", f"{path}.id", f"duplicate slot id {slot_id!r}")
            else:
                by_id[slot_id] = dict(slot)
        validator.enum(slot.get("face"), f"{path}.face", VALID_FACES)
        validator.string(slot.get("work_id"), f"{path}.work_id")
        source = _validate_source_ref(slot.get("source"), validator, f"{path}.source", allow_null=False)
        if source is not None:
            sources.append((f"{path}.source", source))

        geometry = validator.object(
            slot.get("geometry"),
            f"{path}.geometry",
            required={"position_mm", "trim_size_mm", "bleed_mm", "rotation_deg"},
        )
        if geometry is not None:
            position = validator.object(
                geometry.get("position_mm"),
                f"{path}.geometry.position_mm",
                required={"x_mm", "y_mm", "anchor"},
            )
            if position is not None:
                validator.number(position.get("x_mm"), f"{path}.geometry.position_mm.x_mm")
                validator.number(position.get("y_mm"), f"{path}.geometry.position_mm.y_mm")
                if position.get("anchor") != "trim_center":
                    validator.issue(
                        "INVALID_ANCHOR",
                        f"{path}.geometry.position_mm.anchor",
                        "must be trim_center",
                    )
            _validate_size(geometry.get("trim_size_mm"), validator, f"{path}.geometry.trim_size_mm")
            validator.number(geometry.get("bleed_mm"), f"{path}.geometry.bleed_mm", nonnegative=True)
            rotation = validator.number(geometry.get("rotation_deg"), f"{path}.geometry.rotation_deg")
            if rotation is not None and not 0 <= rotation < 360:
                validator.issue("INVALID_ROTATION", f"{path}.geometry.rotation_deg", "must be in [0, 360)")

        _validate_content_transform(slot.get("content_transform"), validator, f"{path}.content_transform")

        locks = validator.object(
            slot.get("locks"),
            f"{path}.locks",
            required={"geometry", "content", "production", "delete"},
        )
        if locks is not None:
            for lock_name in ("geometry", "content", "production", "delete"):
                lock_sources = validator.array(locks.get(lock_name), f"{path}.locks.{lock_name}")
                if lock_sources is not None:
                    seen_sources: set[str] = set()
                    for source_index, lock_source in enumerate(lock_sources):
                        source_path = f"{path}.locks.{lock_name}[{source_index}]"
                        validator.enum(lock_source, source_path, VALID_LOCK_SOURCES)
                        if isinstance(lock_source, str) and lock_source in seen_sources:
                            validator.issue("DUPLICATE_LOCK_SOURCE", source_path, "lock source is duplicated")
                        if isinstance(lock_source, str):
                            seen_sources.add(lock_source)

        production = validator.object(
            slot.get("production"),
            f"{path}.production",
            required={"marks_profile_id"},
        )
        if production is not None:
            validator.string(production.get("marks_profile_id"), f"{path}.production.marks_profile_id")

        generated_by = validator.object(
            slot.get("generated_by"),
            f"{path}.generated_by",
            required={"type"},
            optional={"engine", "operation_id", "source_slot_id"},
        )
        if generated_by is not None:
            validator.enum(generated_by.get("type"), f"{path}.generated_by.type", VALID_GENERATOR_TYPES)
            for optional_string in ("engine", "operation_id", "source_slot_id"):
                if optional_string in generated_by:
                    validator.string(generated_by.get(optional_string), f"{path}.generated_by.{optional_string}")
    return by_id, sources


def _validate_imposition(value: Any, validator: _Validator) -> None:
    path = "$.imposition"
    imposition = validator.object(
        value,
        path,
        required={"engine", "engine_version", "settings", "last_result"},
    )
    if imposition is None:
        return
    validator.enum(imposition.get("engine"), f"{path}.engine", VALID_ENGINES)
    validator.string(imposition.get("engine_version"), f"{path}.engine_version")
    settings = validator.object(
        imposition.get("settings"),
        f"{path}.settings",
        required={
            "horizontal_gap_mm",
            "vertical_gap_mm",
            "exact_quantity",
            "fill_remaining_space",
            "respect_priority",
            "respect_preferred_zones",
        },
    )
    if settings is not None:
        validator.number(settings.get("horizontal_gap_mm"), f"{path}.settings.horizontal_gap_mm", nonnegative=True)
        validator.number(settings.get("vertical_gap_mm"), f"{path}.settings.vertical_gap_mm", nonnegative=True)
        for key in ("exact_quantity", "fill_remaining_space", "respect_priority", "respect_preferred_zones"):
            validator.boolean(settings.get(key), f"{path}.settings.{key}")

    result = imposition.get("last_result")
    if result is None:
        return
    result_obj = validator.object(
        result,
        f"{path}.last_result",
        required={
            "operation_id",
            "status",
            "requested",
            "placed",
            "unplaced",
            "overproduced",
            "generated_at",
            "warnings",
        },
    )
    if result_obj is None:
        return
    validator.string(result_obj.get("operation_id"), f"{path}.last_result.operation_id")
    validator.enum(result_obj.get("status"), f"{path}.last_result.status", VALID_IMPOSITION_STATUSES)
    for key in ("requested", "placed", "unplaced", "overproduced"):
        validator.integer(result_obj.get(key), f"{path}.last_result.{key}", minimum=0)
    validator.string(result_obj.get("generated_at"), f"{path}.last_result.generated_at")
    warnings = validator.array(result_obj.get("warnings"), f"{path}.last_result.warnings")
    if warnings is not None:
        for index, warning in enumerate(warnings):
            validator.string(warning, f"{path}.last_result.warnings[{index}]")


def _validate_export(value: Any, validator: _Validator) -> set[str]:
    path = "$.export"
    export = validator.object(
        value,
        path,
        required={
            "profile",
            "render_mode",
            "dpi",
            "faces",
            "marks_profiles",
            "default_marks_profile_id",
            "bleed_policy",
            "crop_to_content",
            "preserve_vector_content",
        },
    )
    profile_ids: set[str] = set()
    if export is None:
        return profile_ids
    validator.string(export.get("profile"), f"{path}.profile")
    validator.enum(export.get("render_mode"), f"{path}.render_mode", VALID_RENDER_MODES)
    validator.integer(export.get("dpi"), f"{path}.dpi", minimum=1)
    faces = validator.object(
        export.get("faces"),
        f"{path}.faces",
        required={"front", "back", "combine_in_single_pdf", "order"},
    )
    if faces is not None:
        for key in ("front", "back", "combine_in_single_pdf"):
            validator.boolean(faces.get(key), f"{path}.faces.{key}")
        order = validator.array(faces.get("order"), f"{path}.faces.order")
        if order is not None:
            seen: set[str] = set()
            for index, face in enumerate(order):
                face_path = f"{path}.faces.order[{index}]"
                validator.enum(face, face_path, VALID_FACES)
                if isinstance(face, str) and face in seen:
                    validator.issue("DUPLICATE_FACE", face_path, "face is duplicated")
                if isinstance(face, str):
                    seen.add(face)

    profiles = validator.array(export.get("marks_profiles"), f"{path}.marks_profiles")
    if profiles is not None:
        for index, profile_value in enumerate(profiles):
            profile_path = f"{path}.marks_profiles[{index}]"
            profile = validator.object(
                profile_value,
                profile_path,
                required={"id", "crop_marks", "registration_marks", "technical_text", "color_bar"},
            )
            if profile is None:
                continue
            profile_id = validator.string(profile.get("id"), f"{profile_path}.id")
            if profile_id:
                if profile_id in profile_ids:
                    validator.issue("DUPLICATE_ID", f"{profile_path}.id", "marks profile id is duplicated")
                profile_ids.add(profile_id)
            for key in ("crop_marks", "registration_marks", "technical_text", "color_bar"):
                validator.boolean(profile.get(key), f"{profile_path}.{key}")
    default_profile = validator.string(export.get("default_marks_profile_id"), f"{path}.default_marks_profile_id")
    if default_profile and default_profile not in profile_ids:
        validator.issue(
            "BROKEN_REFERENCE",
            f"{path}.default_marks_profile_id",
            "references an unknown marks profile",
        )
    validator.enum(export.get("bleed_policy"), f"{path}.bleed_policy", VALID_BLEED_POLICIES)
    validator.boolean(export.get("crop_to_content"), f"{path}.crop_to_content")
    validator.boolean(export.get("preserve_vector_content"), f"{path}.preserve_vector_content")
    return profile_ids


def _validate_ctp(value: Any, validator: _Validator) -> None:
    path = "$.ctp"
    ctp = validator.object(
        value,
        path,
        required={"enabled", "face", "gripper", "plate", "color_bar", "technical_text", "registration_marks"},
    )
    if ctp is None:
        return
    validator.boolean(ctp.get("enabled"), f"{path}.enabled")
    validator.enum(ctp.get("face"), f"{path}.face", VALID_FACES)
    gripper = validator.object(ctp.get("gripper"), f"{path}.gripper", required={"edge", "depth_mm"})
    if gripper is not None:
        validator.enum(gripper.get("edge"), f"{path}.gripper.edge", {"top", "right", "bottom", "left"})
        validator.number(gripper.get("depth_mm"), f"{path}.gripper.depth_mm", nonnegative=True)
    plate = validator.object(ctp.get("plate"), f"{path}.plate", required={"offset_x_mm", "offset_y_mm"})
    if plate is not None:
        validator.number(plate.get("offset_x_mm"), f"{path}.plate.offset_x_mm")
        validator.number(plate.get("offset_y_mm"), f"{path}.plate.offset_y_mm")
    color_bar = validator.object(
        ctp.get("color_bar"),
        f"{path}.color_bar",
        required={"enabled", "height_mm", "position"},
    )
    if color_bar is not None:
        validator.boolean(color_bar.get("enabled"), f"{path}.color_bar.enabled")
        validator.number(color_bar.get("height_mm"), f"{path}.color_bar.height_mm", nonnegative=True)
        validator.enum(
            color_bar.get("position"),
            f"{path}.color_bar.position",
            {"opposite_gripper", "gripper", "top", "right", "bottom", "left"},
        )
    technical = validator.object(
        ctp.get("technical_text"),
        f"{path}.technical_text",
        required={"enabled", "job_name", "date", "plate_name"},
    )
    if technical is not None:
        for key in ("enabled", "job_name", "date", "plate_name"):
            validator.boolean(technical.get(key), f"{path}.technical_text.{key}")
    registration = validator.object(
        ctp.get("registration_marks"),
        f"{path}.registration_marks",
        required={"enabled"},
    )
    if registration is not None:
        validator.boolean(registration.get("enabled"), f"{path}.registration_marks.enabled")


def _validate_reference(
    path: str,
    source: Mapping[str, Any],
    validator: _Validator,
    assets: Mapping[str, Any],
    page_boxes: Mapping[str, Mapping[int, set[str]]],
) -> None:
    asset_id = source.get("asset_id")
    page = source.get("page")
    pdf_box = source.get("pdf_box")
    if not isinstance(asset_id, str) or asset_id not in assets:
        validator.issue("BROKEN_REFERENCE", f"{path}.asset_id", "references an unknown asset")
        return
    if not isinstance(page, int) or isinstance(page, bool) or page not in page_boxes.get(asset_id, {}):
        validator.issue("BROKEN_REFERENCE", f"{path}.page", "references an unknown asset page")
        return
    if isinstance(pdf_box, str) and pdf_box not in page_boxes[asset_id][page]:
        validator.issue(
            "MISSING_PDF_BOX",
            f"{path}.pdf_box",
            "the selected PDF box is not present on the referenced page",
        )


def validate_layout_v2(layout: Any) -> list[ValidationIssue]:
    """Return all detected Layout V2 contract violations.

    The function is strict by design: it does not add defaults, coerce values or
    interpret legacy fields.
    """

    validator = _Validator()
    root = validator.object(
        layout,
        "$",
        required={
            "layout_schema_version",
            "job",
            "coordinate_system",
            "sheet",
            "faces",
            "assets",
            "works",
            "slots",
            "imposition",
            "export",
            "ctp",
        },
    )
    if root is None:
        return validator.issues

    _scan_legacy_fields(root, validator)
    if root.get("layout_schema_version") != LAYOUT_SCHEMA_VERSION:
        validator.issue(
            "INVALID_SCHEMA_VERSION",
            "$.layout_schema_version",
            f"must be exactly {LAYOUT_SCHEMA_VERSION}",
        )

    job = validator.object(
        root.get("job"),
        "$.job",
        required={"id", "name", "revision", "created_at", "updated_at"},
    )
    if job is not None:
        validator.string(job.get("id"), "$.job.id")
        validator.string(job.get("name"), "$.job.name")
        validator.integer(job.get("revision"), "$.job.revision", minimum=0)
        validator.string(job.get("created_at"), "$.job.created_at")
        validator.string(job.get("updated_at"), "$.job.updated_at")

    coordinate_system = validator.object(
        root.get("coordinate_system"),
        "$.coordinate_system",
        required=set(EXPECTED_COORDINATE_SYSTEM),
    )
    if coordinate_system is not None:
        for key, expected in EXPECTED_COORDINATE_SYSTEM.items():
            if coordinate_system.get(key) != expected:
                validator.issue(
                    "INVALID_COORDINATE_SYSTEM",
                    f"$.coordinate_system.{key}",
                    f"must be {expected!r}",
                )

    sheet = validator.object(
        root.get("sheet"),
        "$.sheet",
        required={"size_mm", "printable_margins_mm"},
        optional={"background"},
    )
    if sheet is not None:
        _validate_size(sheet.get("size_mm"), validator, "$.sheet.size_mm")
        margins = validator.object(
            sheet.get("printable_margins_mm"),
            "$.sheet.printable_margins_mm",
            required={"left", "right", "bottom", "top"},
        )
        if margins is not None:
            for key in ("left", "right", "bottom", "top"):
                validator.number(margins.get(key), f"$.sheet.printable_margins_mm.{key}", nonnegative=True)
        if "background" in sheet:
            background = validator.object(sheet.get("background"), "$.sheet.background", required={"color"})
            if background is not None:
                validator.string(background.get("color"), "$.sheet.background.color")

    faces = validator.object(root.get("faces"), "$.faces", required={"enabled", "duplex"})
    enabled_faces: set[str] = set()
    if faces is not None:
        enabled = validator.array(faces.get("enabled"), "$.faces.enabled")
        if enabled is not None:
            if not enabled:
                validator.issue("EMPTY_FACES", "$.faces.enabled", "must enable at least one face")
            for index, face in enumerate(enabled):
                validator.enum(face, f"$.faces.enabled[{index}]", VALID_FACES)
                if isinstance(face, str) and face in enabled_faces:
                    validator.issue("DUPLICATE_FACE", f"$.faces.enabled[{index}]", "face is duplicated")
                if isinstance(face, str):
                    enabled_faces.add(face)
        duplex = validator.object(faces.get("duplex"), "$.faces.duplex", required={"enabled", "flip"})
        if duplex is not None:
            duplex_enabled = validator.boolean(duplex.get("enabled"), "$.faces.duplex.enabled")
            flip = validator.enum(duplex.get("flip"), "$.faces.duplex.flip", VALID_DUPLEX_FLIPS)
            if duplex_enabled is False and flip not in (None, "none"):
                validator.issue("INVALID_DUPLEX", "$.faces.duplex.flip", "must be none when duplex is disabled")

    assets, page_boxes = _validate_assets(root.get("assets"), validator)
    works, work_sources = _validate_works(root.get("works"), validator)
    slots, slot_sources = _validate_slots(root.get("slots"), validator)
    _validate_imposition(root.get("imposition"), validator)
    marks_profiles = _validate_export(root.get("export"), validator)
    _validate_ctp(root.get("ctp"), validator)

    for source_path, source in [*work_sources, *slot_sources]:
        _validate_reference(source_path, source, validator, assets, page_boxes)

    for index, slot_value in enumerate(root.get("slots", []) if isinstance(root.get("slots"), list) else []):
        if not isinstance(slot_value, dict):
            continue
        path = f"$.slots[{index}]"
        work_id = slot_value.get("work_id")
        if not isinstance(work_id, str) or work_id not in works:
            validator.issue("BROKEN_REFERENCE", f"{path}.work_id", "references an unknown work")
        face = slot_value.get("face")
        if isinstance(face, str) and face not in enabled_faces:
            validator.issue("DISABLED_FACE", f"{path}.face", "slot face is not enabled by the layout")
        production = slot_value.get("production")
        if isinstance(production, dict):
            marks_profile_id = production.get("marks_profile_id")
            if isinstance(marks_profile_id, str) and marks_profile_id not in marks_profiles:
                validator.issue(
                    "BROKEN_REFERENCE",
                    f"{path}.production.marks_profile_id",
                    "references an unknown marks profile",
                )

    for slot_id, slot in slots.items():
        generated_by = slot.get("generated_by")
        if isinstance(generated_by, dict) and "source_slot_id" in generated_by:
            source_slot_id = generated_by.get("source_slot_id")
            if source_slot_id not in slots:
                validator.issue(
                    "BROKEN_REFERENCE",
                    f"$.slots[{slot_id}].generated_by.source_slot_id",
                    "references an unknown source slot",
                )

    return validator.issues


def assert_valid_layout_v2(layout: Any) -> None:
    """Raise :class:`LayoutV2ValidationError` if *layout* is invalid."""

    issues = validate_layout_v2(layout)
    if issues:
        raise LayoutV2ValidationError(issues)
