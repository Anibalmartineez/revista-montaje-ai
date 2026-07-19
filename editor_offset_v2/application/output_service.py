"""Capability preflight for the temporary V2 output boundary."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from editor_offset_v2.domain.output_contract import OutputIssue
from editor_offset_v2.domain.validation import validate_layout_v2


# PDF boxes originate in points and are persisted as millimetres, while work
# trim values are entered at millimetre precision in the UI.  This tolerance is
# deliberately separate from the geometry kernel epsilon: it represents safe
# compatibility of two physical measurements, not floating-point noise.
PDF_BOX_TRIM_COMPATIBILITY_TOLERANCE_MM = 0.01


def _issue(
    code: str,
    message: str,
    path: str,
    *,
    slot_id: str | None = None,
    asset_id: str | None = None,
    level: str = "error",
) -> OutputIssue:
    return OutputIssue(
        code=code,
        level=level,
        message=message,
        path=path,
        slot_id=slot_id,
        asset_id=asset_id,
    )


def _pdf_measure_close(left: object, right: object) -> bool:
    left_value = float(left)
    right_value = float(right)
    floating_margin = 4 * max(
        math.ulp(left_value),
        math.ulp(right_value),
        math.ulp(PDF_BOX_TRIM_COMPATIBILITY_TOLERANCE_MM),
    )
    return (
        abs(left_value - right_value)
        <= PDF_BOX_TRIM_COMPATIBILITY_TOLERANCE_MM + floating_margin
    )


def _oriented_source_box_size(
    page: Mapping[str, Any],
    source_box: Mapping[str, Any],
) -> tuple[float, float]:
    """Return the source size in the page's visible intrinsic orientation.

    PDF boxes remain persisted in their native, unrotated page coordinates.
    A page rotation of 90/270 changes the visible source orientation, so only
    the comparison view swaps axes.  Slot trim stays persisted before the
    slot's own geometric rotation and is never rewritten here.
    """

    width = float(source_box["width"])
    height = float(source_box["height"])
    if page["intrinsic_rotation_deg"] in (90, 270):
        return height, width
    return width, height


def _page_for(asset: Mapping[str, Any], number: int) -> Mapping[str, Any] | None:
    for page in asset["pages"]:
        if page["number"] == number:
            return page
    return None


def _validate_export_capabilities(
    layout: Mapping[str, Any],
    issues: list[OutputIssue],
) -> None:
    export = layout["export"]
    export_faces = export["faces"]
    layout_faces = set(layout["faces"]["enabled"])
    enabled = tuple(
        face for face in ("front", "back") if export_faces[face]
    )

    if not enabled:
        issues.append(
            _issue(
                "NO_EXPORT_FACE",
                "At least one output face must be enabled.",
                "$.export.faces",
            )
        )

    for face in enabled:
        if face not in layout_faces:
            issues.append(
                _issue(
                    "EXPORT_FACE_NOT_ENABLED",
                    f"Output face {face!r} is not enabled by the layout.",
                    f"$.export.faces.{face}",
                )
            )
        if not any(slot["face"] == face for slot in layout["slots"]):
            issues.append(
                _issue(
                    "EXPORT_FACE_HAS_NO_SLOTS",
                    f"Output face {face!r} has no slots to render.",
                    f"$.export.faces.{face}",
                )
            )

    order = tuple(export_faces["order"])
    if order != enabled:
        issues.append(
            _issue(
                "UNSUPPORTED_FACE_ORDER",
                "The current output boundary requires enabled faces in front/back order.",
                "$.export.faces.order",
            )
        )
    if len(enabled) == 2 and not export_faces["combine_in_single_pdf"]:
        issues.append(
            _issue(
                "UNSUPPORTED_SEPARATE_FACE_PDFS",
                "The current connection can only deliver front and back combined in one PDF.",
                "$.export.faces.combine_in_single_pdf",
            )
        )

    if export["dpi"] != 300:
        issues.append(
            _issue(
                "UNSUPPORTED_EXPORT_DPI",
                "The current raster output is fixed at 300 dpi.",
                "$.export.dpi",
            )
        )
    if export["crop_to_content"]:
        issues.append(
            _issue(
                "UNSUPPORTED_CROP_TO_CONTENT",
                "Cropping the sheet to used content is not supported by this boundary.",
                "$.export.crop_to_content",
            )
        )

    vector_expected = export["render_mode"] == "vector_hybrid"
    if export["preserve_vector_content"] is not vector_expected:
        issues.append(
            _issue(
                "UNSUPPORTED_VECTOR_POLICY",
                "Vector preservation must be enabled only for vector_hybrid output.",
                "$.export.preserve_vector_content",
            )
        )


def _validate_marks_capabilities(
    layout: Mapping[str, Any],
    issues: list[OutputIssue],
) -> None:
    used_profiles = {
        slot["production"]["marks_profile_id"] for slot in layout["slots"]
    }
    for index, profile in enumerate(layout["export"]["marks_profiles"]):
        if profile["id"] not in used_profiles:
            continue
        unsupported = [
            name
            for name in ("registration_marks", "technical_text", "color_bar")
            if profile[name]
        ]
        if unsupported:
            issues.append(
                _issue(
                    "UNSUPPORTED_MARKS_PROFILE_FEATURE",
                    "The current output boundary cannot safely render per-slot "
                    f"features: {', '.join(unsupported)}.",
                    f"$.export.marks_profiles[{index}]",
                )
            )


def _validate_slot_capabilities(
    layout: Mapping[str, Any],
    issues: list[OutputIssue],
) -> None:
    assets = {asset["id"]: asset for asset in layout["assets"]}

    for index, slot in enumerate(layout["slots"]):
        slot_path = f"$.slots[{index}]"
        slot_id = slot["id"]
        source = slot["source"]
        asset_id = source["asset_id"]
        asset = assets[asset_id]
        page = _page_for(asset, source["page"])
        assert page is not None

        if asset["status"] != "ready":
            issues.append(
                _issue(
                    "ASSET_NOT_READY",
                    "The source asset must be ready before output adaptation.",
                    f"$.assets[{layout['assets'].index(asset)}].status",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        if source["page"] != 1:
            issues.append(
                _issue(
                    "UNSUPPORTED_SOURCE_PAGE",
                    "The current renderer boundary can only address PDF page 1.",
                    f"{slot_path}.source.page",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        if source["pdf_box"] != "trim":
            issues.append(
                _issue(
                    "UNSUPPORTED_PDF_BOX",
                    "The current renderer boundary can only address the PDF trim box.",
                    f"{slot_path}.source.pdf_box",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        if page["intrinsic_rotation_deg"] != 0:
            issues.append(
                _issue(
                    "UNSUPPORTED_INTRINSIC_ROTATION",
                    "Prepared page rotation is required before output adaptation.",
                    f"{slot_path}.source.page",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )

        selected_box = page["boxes_mm"][source["pdf_box"]]
        source_width, source_height = _oriented_source_box_size(
            page,
            selected_box,
        )
        trim_size = slot["geometry"]["trim_size_mm"]
        if not (
            _pdf_measure_close(source_width, trim_size["width"])
            and _pdf_measure_close(source_height, trim_size["height"])
        ):
            issues.append(
                _issue(
                    "SOURCE_TRIM_SIZE_MISMATCH",
                    "At actual size, the selected source box must match the slot "
                    f"trim size within {PDF_BOX_TRIM_COMPATIBILITY_TOLERANCE_MM:g} mm.",
                    f"{slot_path}.geometry.trim_size_mm",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )

        transform = slot["content_transform"]
        if transform["fit_mode"] != "actual_size":
            issues.append(
                _issue(
                    "UNSUPPORTED_CONTENT_FIT_MODE",
                    "Only actual_size content fitting is supported in Phase 3.",
                    f"{slot_path}.content_transform.fit_mode",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        if transform["scale_x"] != 1.0 or transform["scale_y"] != 1.0:
            issues.append(
                _issue(
                    "UNSUPPORTED_CONTENT_SCALE",
                    "Content scale must remain 1.0 on both axes.",
                    f"{slot_path}.content_transform",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        offset = transform["offset_mm"]
        if offset["x"] != 0.0 or offset["y"] != 0.0:
            issues.append(
                _issue(
                    "UNSUPPORTED_CONTENT_OFFSET",
                    "Content offsets are not supported by the current renderer boundary.",
                    f"{slot_path}.content_transform.offset_mm",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        if transform["rotation_deg"] != 0:
            issues.append(
                _issue(
                    "UNSUPPORTED_CONTENT_ROTATION",
                    "Internal content rotation is not supported in Phase 3.",
                    f"{slot_path}.content_transform.rotation_deg",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        if transform["mirror_x"] or transform["mirror_y"]:
            issues.append(
                _issue(
                    "UNSUPPORTED_CONTENT_MIRROR",
                    "Mirrored content requires a prepared asset.",
                    f"{slot_path}.content_transform",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )

        clip_to = transform["clip_to"]
        bleed = slot["geometry"]["bleed_mm"]
        clip_supported = False
        if clip_to == "trim_box" and bleed == 0:
            clip_supported = True
        elif clip_to == "bleed_box":
            bleed_box = page["boxes_mm"]["bleed"]
            trim_box = page["boxes_mm"]["trim"]
            if bleed_box is not None and trim_box is not None:
                clip_supported = all(
                    (
                        _pdf_measure_close(bleed_box["x"], trim_box["x"] - bleed),
                        _pdf_measure_close(bleed_box["y"], trim_box["y"] - bleed),
                        _pdf_measure_close(
                            bleed_box["width"],
                            trim_box["width"] + 2 * bleed,
                        ),
                        _pdf_measure_close(
                            bleed_box["height"],
                            trim_box["height"] + 2 * bleed,
                        ),
                    )
                )
        if not clip_supported:
            issues.append(
                _issue(
                    "UNSUPPORTED_CONTENT_CLIP",
                    "The requested clipping cannot be represented without changing the artwork.",
                    f"{slot_path}.content_transform.clip_to",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )

        preflight = page["preflight"]
        if preflight["status"] == "error":
            issues.append(
                _issue(
                    "ASSET_PREFLIGHT_FAILED",
                    "The selected PDF page has blocking preflight errors.",
                    f"{slot_path}.source",
                    slot_id=slot_id,
                    asset_id=asset_id,
                )
            )
        elif preflight["status"] == "warning":
            issues.append(
                _issue(
                    "ASSET_PREFLIGHT_WARNING",
                    "The selected PDF page has preflight warnings.",
                    f"{slot_path}.source",
                    slot_id=slot_id,
                    asset_id=asset_id,
                    level="warning",
                )
            )


def validate_output_capabilities(
    layout: Mapping[str, object],
) -> tuple[OutputIssue, ...]:
    """Validate Layout V2 and the narrower capabilities of the current output.

    This function never coerces or normalizes input.  Contract errors are
    returned first and capability checks only run for a valid Layout V2.
    """

    contract_issues = validate_layout_v2(layout)
    if contract_issues:
        return tuple(
            OutputIssue(
                code=issue.code,
                level="error",
                message=issue.message,
                path=issue.path,
            )
            for issue in contract_issues
        )

    typed_layout = layout
    issues: list[OutputIssue] = []
    _validate_export_capabilities(typed_layout, issues)
    _validate_marks_capabilities(typed_layout, issues)
    _validate_slot_capabilities(typed_layout, issues)

    if typed_layout["ctp"]["enabled"]:
        issues.append(
            _issue(
                "UNSUPPORTED_CTP_CONFIGURATION",
                "Active CTP output remains blocked until the production mapping is complete.",
                "$.ctp.enabled",
            )
        )

    return tuple(issues)


__all__ = [
    "PDF_BOX_TRIM_COMPATIBILITY_TOLERANCE_MM",
    "validate_output_capabilities",
]
