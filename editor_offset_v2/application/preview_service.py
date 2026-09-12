"""Strict, gated sheet preview owned by Editor Offset V2."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import fitz

from editor_offset_v2.domain.geometry import (
    Point,
    Size,
    SlotGeometry,
    bleed_bounds,
)
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.asset_repository import (
    AssetRepository,
    AssetRepositoryError,
    SOURCE_FILENAME,
)
from editor_offset_v2.infrastructure.job_repository import JobRepository, JobRepositoryError
from editor_offset_v2.infrastructure.pdf_inspector import PdfInspectionError, inspect_pdf
from editor_offset_v2.infrastructure.prepared_pdf_source import (
    SourcePreparationError,
    prepare_source,
)


PREVIEW_DEFAULT_DPI = 150
PREVIEW_MIN_DPI = 36
PREVIEW_MAX_DPI = 300
PREVIEW_MAX_PIXELS = 24_000_000
PREVIEW_METADATA_TOLERANCE_MM = 0.01
POINTS_PER_MM = 72.0 / 25.4


class PreviewServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.issues: tuple[object, ...] = ()
        super().__init__(message)


@dataclass(frozen=True)
class PreviewResult:
    path: Path
    job_id: str
    revision: int
    face: str
    dpi: int
    sha256: str


def _same_number(left: object, right: object) -> bool:
    return abs(float(left) - float(right)) <= PREVIEW_METADATA_TOLERANCE_MM


def _same_box(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(_same_number(actual[key], expected[key]) for key in ("x", "y", "width", "height"))


class PreviewService:
    """Render a single-face PNG without changing Layout V2 or invoking V1."""

    def __init__(self, jobs: JobRepository):
        self._jobs = jobs
        self._assets = AssetRepository(jobs)

    def render(
        self,
        job_id: str,
        *,
        face: str = "front",
        dpi: int = PREVIEW_DEFAULT_DPI,
        allow_mirror_bleed: bool = False,
    ) -> PreviewResult:
        try:
            layout = self._jobs.read_layout(job_id)
        except JobRepositoryError as exc:
            status = 404 if exc.code == "JOB_NOT_FOUND" else 400 if exc.code == "INVALID_JOB_ID" else 500
            raise PreviewServiceError(exc.code, exc.message, status) from exc

        contract_issues = validate_layout_v2(layout)
        if contract_issues:
            raise PreviewServiceError("INVALID_LAYOUT", "The saved Layout V2 is invalid", 500)
        if not isinstance(face, str) or face not in {"front", "back"}:
            raise PreviewServiceError("INVALID_PREVIEW_FACE", "face must be front or back", 400)
        if face not in layout["faces"]["enabled"] or not layout["export"]["faces"].get(face):
            raise PreviewServiceError("PREVIEW_FACE_DISABLED", "The requested face is not enabled", 422)
        if isinstance(dpi, bool) or not isinstance(dpi, int) or not PREVIEW_MIN_DPI <= dpi <= PREVIEW_MAX_DPI:
            raise PreviewServiceError(
                "INVALID_PREVIEW_DPI",
                f"dpi must be an integer between {PREVIEW_MIN_DPI} and {PREVIEW_MAX_DPI}",
                400,
            )
        if not isinstance(allow_mirror_bleed, bool):
            raise PreviewServiceError("INVALID_PREVIEW_OPTION", "allow_mirror_bleed must be boolean", 400)

        slots = [slot for slot in layout["slots"] if slot["face"] == face]
        if not slots:
            raise PreviewServiceError("PREVIEW_NO_SLOTS", "The requested face has no slots", 422)
        if layout["faces"]["duplex"]["enabled"] and face == "back" and layout["faces"]["duplex"]["flip"] != "none":
            raise PreviewServiceError(
                "PREVIEW_DUPLEX_FLIP_UNSUPPORTED",
                "Back-face duplex flip requires its own approved preview contract",
            )
        used_profile_ids = {slot["production"]["marks_profile_id"] for slot in slots}
        profiles = {
            profile["id"]: profile
            for profile in layout["export"]["marks_profiles"]
            if profile["id"] in used_profile_ids
        }
        for profile in profiles.values():
            if any(profile[name] for name in ("crop_marks", "registration_marks", "technical_text", "color_bar")):
                raise PreviewServiceError(
                    "PREVIEW_MARKS_UNSUPPORTED",
                    "Preview is blocked while output marks are requested; marks require a dedicated contract",
                )

        sheet = layout["sheet"]["size_mm"]
        sheet_width_px = round(float(sheet["width"]) * dpi / 25.4)
        sheet_height_px = round(float(sheet["height"]) * dpi / 25.4)
        if sheet_width_px * sheet_height_px > PREVIEW_MAX_PIXELS:
            raise PreviewServiceError("PREVIEW_RESOURCE_LIMIT", "The requested preview exceeds the pixel limit")

        assets = {asset["id"]: asset for asset in layout["assets"]}
        with fitz.open() as output:
            output_page = output.new_page(
                width=float(sheet["width"]) * POINTS_PER_MM,
                height=float(sheet["height"]) * POINTS_PER_MM,
            )
            for slot in slots:
                prepared_data = self._prepared_slot(slot, assets, job_id, allow_mirror_bleed)
                geometry = slot["geometry"]
                slot_geometry = SlotGeometry(
                    center=Point(
                        geometry["position_mm"]["x_mm"],
                        geometry["position_mm"]["y_mm"],
                    ),
                    trim_size=Size(
                        geometry["trim_size_mm"]["width"],
                        geometry["trim_size_mm"]["height"],
                    ),
                    bleed=geometry["bleed_mm"],
                    rotation_deg=geometry["rotation_deg"],
                )
                bounds = bleed_bounds(slot_geometry)
                target = fitz.Rect(
                    bounds.left * POINTS_PER_MM,
                    (float(sheet["height"]) - bounds.top) * POINTS_PER_MM,
                    bounds.right * POINTS_PER_MM,
                    (float(sheet["height"]) - bounds.bottom) * POINTS_PER_MM,
                )
                with fitz.open(stream=prepared_data, filetype="pdf") as prepared:
                    output_page.show_pdf_page(
                        target,
                        prepared,
                        0,
                        rotate=int(slot_geometry.rotation_deg),
                        keep_proportion=False,
                    )
            png_data = output_page.get_pixmap(
                dpi=dpi,
                colorspace=fitz.csRGB,
                alpha=False,
            ).tobytes("png")

        previews = self._jobs.job_path(job_id) / "previews"
        previews.mkdir(exist_ok=True)
        target = previews / f"preview_r{layout['job']['revision']}_{face}_{dpi}.png"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=previews, prefix=".preview-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(png_data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
        except OSError as exc:
            raise PreviewServiceError("PREVIEW_PUBLISH_FAILED", "The preview could not be published", 500) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return PreviewResult(
            path=target,
            job_id=job_id,
            revision=layout["job"]["revision"],
            face=face,
            dpi=dpi,
            sha256=hashlib.sha256(png_data).hexdigest(),
        )

    def _prepared_slot(
        self,
        slot: Mapping[str, Any],
        assets: Mapping[str, Mapping[str, Any]],
        job_id: str,
        allow_mirror_bleed: bool,
    ) -> bytes:
        transform = slot["content_transform"]
        if (
            transform["fit_mode"] != "actual_size"
            or transform["scale_x"] != 1.0
            or transform["scale_y"] != 1.0
            or transform["offset_mm"]["x"] != 0.0
            or transform["offset_mm"]["y"] != 0.0
            or transform["rotation_deg"] != 0.0
            or transform["mirror_x"]
            or transform["mirror_y"]
        ):
            raise PreviewServiceError(
                "PREVIEW_TRANSFORM_UNSUPPORTED",
                "Preview baseline requires identity internal content transform",
            )
        asset_id = slot["source"]["asset_id"]
        asset = assets.get(asset_id)
        if asset is None or asset["status"] != "ready":
            raise PreviewServiceError("ASSET_NOT_READY", "The selected source asset is not ready")
        try:
            asset_dir = self._assets.asset_path(job_id, asset_id)
            source_path = asset_dir / SOURCE_FILENAME
            if source_path.is_symlink() or not source_path.resolve().is_relative_to(asset_dir.resolve()):
                raise AssetRepositoryError("ASSET_UNSAFE_PATH", "The source PDF path is unsafe")
            source_data = source_path.read_bytes()
        except (AssetRepositoryError, OSError) as exc:
            code = exc.code if isinstance(exc, AssetRepositoryError) else "ASSET_MISSING"
            raise PreviewServiceError(code, "The selected source PDF is unavailable") from exc
        if hashlib.sha256(source_data).hexdigest() != asset["sha256"]:
            raise PreviewServiceError("ASSET_IDENTITY_MISMATCH", "The source PDF hash differs from saved metadata")
        try:
            inspection = inspect_pdf(source_data)
        except PdfInspectionError as exc:
            raise PreviewServiceError("PDF_UNREADABLE", "The selected source PDF cannot be inspected") from exc
        page_number = slot["source"]["page"]
        if not isinstance(page_number, int) or not 1 <= page_number <= inspection.page_count:
            raise PreviewServiceError("INVALID_SOURCE_PAGE", "The selected PDF page does not exist")
        declared_page = next((page for page in asset["pages"] if page["number"] == page_number), None)
        if declared_page is None:
            raise PreviewServiceError("PDF_METADATA_MISMATCH", "The selected page is absent from asset metadata")
        physical_page = inspection.pages[page_number - 1]
        if physical_page.intrinsic_rotation_deg != declared_page["intrinsic_rotation_deg"]:
            raise PreviewServiceError("PDF_METADATA_MISMATCH", "PDF page rotation differs from saved metadata")
        for name, actual in physical_page.boxes_as_layout().items():
            expected = declared_page["boxes_mm"][name]
            if (actual is None) != (expected is None) or (
                actual is not None and expected is not None and not _same_box(actual, expected)
            ):
                raise PreviewServiceError("PDF_METADATA_MISMATCH", f"PDF {name} differs from saved metadata")
        pdf_box = slot["source"]["pdf_box"]
        selected = declared_page["boxes_mm"].get(pdf_box)
        if selected is None:
            raise PreviewServiceError("MISSING_SOURCE_BOX", "The selected physical PDF box is absent")
        trim = slot["geometry"]["trim_size_mm"]
        source_width = selected["width"]
        source_height = selected["height"]
        if physical_page.intrinsic_rotation_deg in (90, 270):
            source_width, source_height = source_height, source_width
        if not _same_number(source_width, trim["width"]) or not _same_number(source_height, trim["height"]):
            raise PreviewServiceError("PREVIEW_SOURCE_SIZE_MISMATCH", "Source box size differs from slot trim size")
        try:
            prepared = prepare_source(
                source_data,
                page_number=page_number,
                pdf_box=pdf_box,
                bleed_mm=slot["geometry"]["bleed_mm"],
                clip_to=transform["clip_to"],
                allow_mirror_bleed=allow_mirror_bleed,
            )
        except SourcePreparationError as exc:
            raise PreviewServiceError(exc.code, str(exc)) from exc
        return prepared.data


__all__ = [
    "PREVIEW_DEFAULT_DPI",
    "PREVIEW_MAX_DPI",
    "PREVIEW_MIN_DPI",
    "PreviewResult",
    "PreviewService",
    "PreviewServiceError",
]
