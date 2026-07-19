"""Strict Layout V2 to temporary productive-output adapter.

This is the only V2 component allowed to emit legacy renderer field names.
It does not invoke Flask, read V1 layouts or call the productive renderer.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from editor_offset_v2.application.output_service import (
    validate_output_capabilities,
)
from editor_offset_v2.domain.geometry import (
    Point,
    Size,
    SlotGeometry,
    bleed_bounds,
    oriented_size,
    productive_size,
    trim_bounds,
)
from editor_offset_v2.domain.output_contract import (
    OUTPUT_CONTRACT_VERSION,
    OutputAdapterResult,
    OutputCtpConfig,
    OutputDesign,
    OutputExportConfig,
    OutputFace,
    OutputIssue,
    OutputJob,
    OutputMargins,
    OutputMarksProfile,
    OutputPosition,
    OutputSourceBox,
)
from editor_offset_v2.domain.validation import validate_layout_v2


def _error(
    code: str,
    message: str,
    path: str,
    *,
    slot_id: str | None = None,
    asset_id: str | None = None,
) -> OutputIssue:
    return OutputIssue(
        code=code,
        level="error",
        message=message,
        path=path,
        slot_id=slot_id,
        asset_id=asset_id,
    )


def _safe_storage_parts(storage_key: str) -> tuple[str, ...] | None:
    windows_path = PureWindowsPath(storage_key)
    posix_path = PurePosixPath(storage_key)
    if (
        windows_path.is_absolute()
        or bool(windows_path.drive)
        or posix_path.is_absolute()
    ):
        return None
    parts = tuple(storage_key.replace("\\", "/").split("/"))
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    return parts


def _resolve_asset_path(
    root: Path,
    storage_key: str,
    *,
    path: str,
    slot_id: str,
    asset_id: str,
) -> tuple[Path | None, OutputIssue | None]:
    parts = _safe_storage_parts(storage_key)
    if parts is None:
        return None, _error(
            "UNSAFE_ASSET_STORAGE_KEY",
            "Asset storage_key must be a normalized relative path without traversal.",
            path,
            slot_id=slot_id,
            asset_id=asset_id,
        )

    candidate = root.joinpath(*parts).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, _error(
            "ASSET_PATH_OUTSIDE_JOB_ROOT",
            "Resolved asset path escapes the supplied V2 job root.",
            path,
            slot_id=slot_id,
            asset_id=asset_id,
        )
    if not candidate.is_file():
        return None, _error(
            "ASSET_FILE_NOT_FOUND",
            "The referenced physical PDF file does not exist.",
            path,
            slot_id=slot_id,
            asset_id=asset_id,
        )
    return candidate, None


def _find_page(asset: Mapping[str, Any], number: int) -> Mapping[str, Any]:
    for page in asset["pages"]:
        if page["number"] == number:
            return page
    raise KeyError(number)


def _source_key(source: Mapping[str, Any]) -> tuple[str, int, str]:
    return source["asset_id"], source["page"], source["pdf_box"]


def _design_id(source: Mapping[str, Any]) -> str:
    return f"{source['asset_id']}:page-{source['page']}:{source['pdf_box']}"


def _build_ctp_config(ctp: Mapping[str, Any]) -> OutputCtpConfig:
    technical = ctp["technical_text"]
    color_bar = ctp["color_bar"]
    return OutputCtpConfig(
        enabled=ctp["enabled"],
        face=ctp["face"],
        gripper_edge=ctp["gripper"]["edge"],
        gripper_depth_mm=ctp["gripper"]["depth_mm"],
        plate_offset_x_mm=ctp["plate"]["offset_x_mm"],
        plate_offset_y_mm=ctp["plate"]["offset_y_mm"],
        color_bar_enabled=color_bar["enabled"],
        color_bar_height_mm=color_bar["height_mm"],
        color_bar_position=color_bar["position"],
        technical_text_enabled=technical["enabled"],
        technical_text_job_name=technical["job_name"],
        technical_text_date=technical["date"],
        technical_text_plate_name=technical["plate_name"],
        registration_marks_enabled=ctp["registration_marks"]["enabled"],
    )


def adapt_layout_v2_to_output(
    layout: Mapping[str, object],
    job_root: Path,
) -> OutputAdapterResult:
    """Adapt a valid Layout V2 without mutating it or interpreting legacy data."""

    contract_issues = validate_layout_v2(layout)
    if contract_issues:
        return OutputAdapterResult(
            success=False,
            job=None,
            issues=tuple(
                OutputIssue(
                    code=issue.code,
                    level="error",
                    message=issue.message,
                    path=issue.path,
                )
                for issue in contract_issues
            ),
        )

    try:
        root = Path(job_root).resolve(strict=True)
    except (OSError, RuntimeError):
        return OutputAdapterResult(
            success=False,
            job=None,
            issues=(
                _error(
                    "INVALID_JOB_ROOT",
                    "The supplied V2 job root does not exist.",
                    "$job_root",
                ),
            ),
        )
    if not root.is_dir():
        return OutputAdapterResult(
            success=False,
            job=None,
            issues=(
                _error(
                    "INVALID_JOB_ROOT",
                    "The supplied V2 job root must be a directory.",
                    "$job_root",
                ),
            ),
        )

    typed_layout: Mapping[str, Any] = layout
    issues = list(validate_output_capabilities(typed_layout))
    assets = {asset["id"]: asset for asset in typed_layout["assets"]}
    asset_indexes = {
        asset["id"]: index for index, asset in enumerate(typed_layout["assets"])
    }

    resolved_paths: dict[str, Path] = {}
    for slot in typed_layout["slots"]:
        asset_id = slot["source"]["asset_id"]
        if asset_id in resolved_paths:
            continue
        asset = assets[asset_id]
        resolved, issue = _resolve_asset_path(
            root,
            asset["storage_key"],
            path=f"$.assets[{asset_indexes[asset_id]}].storage_key",
            slot_id=slot["id"],
            asset_id=asset_id,
        )
        if issue is not None:
            issues.append(issue)
        elif resolved is not None:
            resolved_paths[asset_id] = resolved

    if any(issue.level == "error" for issue in issues):
        return OutputAdapterResult(success=False, job=None, issues=tuple(issues))

    design_keys: list[tuple[str, int, str]] = []
    for slot in typed_layout["slots"]:
        key = _source_key(slot["source"])
        if key not in design_keys:
            design_keys.append(key)

    designs: list[OutputDesign] = []
    design_indexes: dict[tuple[str, int, str], int] = {}
    for index, key in enumerate(design_keys):
        asset_id, page_number, pdf_box = key
        asset = assets[asset_id]
        page = _find_page(asset, page_number)
        source_box = page["boxes_mm"][pdf_box]
        design_indexes[key] = index
        designs.append(
            OutputDesign(
                id=f"{asset_id}:page-{page_number}:{pdf_box}",
                asset_id=asset_id,
                source_path=resolved_paths[asset_id],
                original_filename=asset["original_filename"],
                page=page_number,
                pdf_box=pdf_box,
                source_box_mm=OutputSourceBox(
                    x=source_box["x"],
                    y=source_box["y"],
                    width=source_box["width"],
                    height=source_box["height"],
                ),
                intrinsic_rotation_deg=page["intrinsic_rotation_deg"],
            )
        )

    profiles = tuple(
        OutputMarksProfile(
            id=profile["id"],
            crop_marks=profile["crop_marks"],
            registration_marks=profile["registration_marks"],
            technical_text=profile["technical_text"],
            color_bar=profile["color_bar"],
        )
        for profile in typed_layout["export"]["marks_profiles"]
    )
    profiles_by_id = {profile.id: profile for profile in profiles}

    positions_by_face: dict[str, list[OutputPosition]] = {
        "front": [],
        "back": [],
    }
    for slot in typed_layout["slots"]:
        persisted = slot["geometry"]
        geometry = SlotGeometry(
            center=Point(
                persisted["position_mm"]["x_mm"],
                persisted["position_mm"]["y_mm"],
            ),
            trim_size=Size(
                persisted["trim_size_mm"]["width"],
                persisted["trim_size_mm"]["height"],
            ),
            bleed=persisted["bleed_mm"],
            rotation_deg=persisted["rotation_deg"],
        )
        derived_trim_bounds = trim_bounds(geometry)
        derived_productive_bounds = bleed_bounds(geometry)
        derived_productive_size = oriented_size(
            productive_size(geometry.trim_size, geometry.bleed),
            geometry.rotation_deg,
        )
        source = slot["source"]
        source_key = _source_key(source)
        marks_profile_id = slot["production"]["marks_profile_id"]
        positions_by_face[slot["face"]].append(
            OutputPosition(
                slot_id=slot["id"],
                face=slot["face"],
                design_id=_design_id(source),
                design_index=design_indexes[source_key],
                source_page=source["page"],
                pdf_box=source["pdf_box"],
                trim_size=geometry.trim_size,
                productive_size=derived_productive_size,
                rotation_deg=int(geometry.rotation_deg),
                bleed_mm=geometry.bleed,
                trim_bounds=derived_trim_bounds,
                productive_bounds=derived_productive_bounds,
                lower_left=Point(
                    derived_productive_bounds.left,
                    derived_productive_bounds.bottom,
                ),
                marks_profile_id=marks_profile_id,
                crop_marks=profiles_by_id[marks_profile_id].crop_marks,
            )
        )

    export = typed_layout["export"]
    export_faces = export["faces"]
    sheet = typed_layout["sheet"]
    margins = sheet["printable_margins_mm"]
    job_data = typed_layout["job"]
    job = OutputJob(
        id=job_data["id"],
        name=job_data["name"],
        revision=job_data["revision"],
        sheet_size=Size(sheet["size_mm"]["width"], sheet["size_mm"]["height"]),
        margins=OutputMargins(
            left=margins["left"],
            right=margins["right"],
            bottom=margins["bottom"],
            top=margins["top"],
        ),
        imposition_engine=typed_layout["imposition"]["engine"],
        designs=tuple(designs),
        faces=(
            OutputFace(
                name="front",
                enabled=export_faces["front"],
                positions=tuple(positions_by_face["front"]),
            ),
            OutputFace(
                name="back",
                enabled=export_faces["back"],
                positions=tuple(positions_by_face["back"]),
            ),
        ),
        marks_profiles=profiles,
        export=OutputExportConfig(
            profile=export["profile"],
            render_mode=export["render_mode"],
            dpi=export["dpi"],
            front_enabled=export_faces["front"],
            back_enabled=export_faces["back"],
            combine_in_single_pdf=export_faces["combine_in_single_pdf"],
            face_order=tuple(export_faces["order"]),
            bleed_policy=export["bleed_policy"],
            crop_to_content=export["crop_to_content"],
            preserve_vector_content=export["preserve_vector_content"],
            default_marks_profile_id=export["default_marks_profile_id"],
        ),
        ctp=_build_ctp_config(typed_layout["ctp"]),
    )
    return OutputAdapterResult(success=True, job=job, issues=tuple(issues))


def _serialize_position(position: OutputPosition) -> dict[str, object]:
    return {
        "slot_id": position.slot_id,
        "design_id": position.design_id,
        "file_idx": position.design_index,
        "source_page": position.source_page,
        "pdf_box": position.pdf_box,
        "x_mm": position.lower_left.x,
        "y_mm": position.lower_left.y,
        "w_mm": position.productive_size.width,
        "h_mm": position.productive_size.height,
        "rot_deg": position.rotation_deg,
        "bleed_mm": position.bleed_mm,
        "crop_marks": position.crop_marks,
        "marks_profile_id": position.marks_profile_id,
        "slot_box_final": position.slot_box_final,
        "source_w_mm": position.trim_size.width,
        "source_h_mm": position.trim_size.height,
    }


def serialize_output_job(job: OutputJob) -> dict[str, object]:
    """Serialize an OutputJob into the explicit temporary legacy boundary."""

    faces: dict[str, object] = {}
    for face in job.faces:
        positions = [_serialize_position(position) for position in face.positions]
        faces[face.name] = {
            "enabled": face.enabled,
            "modo_manual": bool(positions),
            "cutmarks_por_forma": any(
                position.crop_marks for position in face.positions
            ),
            "posiciones_manual": positions,
        }

    return {
        "output_contract_version": OUTPUT_CONTRACT_VERSION,
        "source_layout_schema_version": 2,
        "job": {
            "id": job.id,
            "name": job.name,
            "revision": job.revision,
        },
        "sheet_mm": [job.sheet_size.width, job.sheet_size.height],
        "margins_mm": [
            job.margins.left,
            job.margins.right,
            job.margins.top,
            job.margins.bottom,
        ],
        "imposition_engine": job.imposition_engine,
        "designs": [
            {
                "id": design.id,
                "asset_id": design.asset_id,
                "ruta": str(design.source_path),
                "cantidad": 1,
                "original_filename": design.original_filename,
                "source_page": design.page,
                "pdf_box": design.pdf_box,
                "source_box_mm": {
                    "x": design.source_box_mm.x,
                    "y": design.source_box_mm.y,
                    "width": design.source_box_mm.width,
                    "height": design.source_box_mm.height,
                },
                "intrinsic_rotation_deg": design.intrinsic_rotation_deg,
            }
            for design in job.designs
        ],
        "faces": faces,
        "marks_profiles": [
            {
                "id": profile.id,
                "crop_marks": profile.crop_marks,
                "registration_marks": profile.registration_marks,
                "technical_text": profile.technical_text,
                "color_bar": profile.color_bar,
            }
            for profile in job.marks_profiles
        ],
        "export_settings": {
            "profile": job.export.profile,
            "output_mode": job.export.render_mode,
            "dpi": job.export.dpi,
            "faces": {
                "front": job.export.front_enabled,
                "back": job.export.back_enabled,
                "combine_in_single_pdf": job.export.combine_in_single_pdf,
                "order": list(job.export.face_order),
            },
            "bleed_policy": job.export.bleed_policy,
            "crop_to_content": job.export.crop_to_content,
            "preserve_vector_content": job.export.preserve_vector_content,
            "default_marks_profile_id": job.export.default_marks_profile_id,
        },
        "ctp_config": {
            "enabled": job.ctp.enabled,
            "face": job.ctp.face,
            "gripper_mm": job.ctp.gripper_depth_mm,
            "marks": {
                "control_strip": job.ctp.color_bar_enabled,
                "registro": job.ctp.registration_marks_enabled,
            },
        },
    }


__all__ = ["adapt_layout_v2_to_output", "serialize_output_job"]
