"""Strict, gated sheet preview owned by Editor Offset V2."""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import fitz
from PIL import Image, ImageChops, ImageDraw, ImageOps

from editor_offset_v2.domain.geometry import (
    Point,
    Size,
    SlotGeometry,
    bleed_bounds,
    bleed_polygon,
    productive_size,
    trim_polygon,
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
        duplex_flip = "none"
        if face == "back" and layout["faces"]["duplex"]["enabled"]:
            duplex_flip = layout["faces"]["duplex"]["flip"]
        used_profile_ids = {slot["production"]["marks_profile_id"] for slot in slots}
        profiles = {
            profile["id"]: profile
            for profile in layout["export"]["marks_profiles"]
            if profile["id"] in used_profile_ids
        }
        for profile in profiles.values():
            if any(profile[name] for name in ("registration_marks", "technical_text", "color_bar")):
                raise PreviewServiceError(
                    "PREVIEW_MARKS_UNSUPPORTED",
                    "Preview is blocked while registration, technical or color marks are requested",
                )

        sheet = layout["sheet"]["size_mm"]
        sheet_width_px = round(float(sheet["width"]) * dpi / 25.4)
        sheet_height_px = round(float(sheet["height"]) * dpi / 25.4)
        if sheet_width_px * sheet_height_px > PREVIEW_MAX_PIXELS:
            raise PreviewServiceError("PREVIEW_RESOURCE_LIMIT", "The requested preview exceeds the pixel limit")

        assets = {asset["id"]: asset for asset in layout["assets"]}
        sheet_scale = dpi / 25.4
        sheet_size_px = (
            round(float(sheet["width"]) * sheet_scale),
            round(float(sheet["height"]) * sheet_scale),
        )
        sheet_image = Image.new("RGB", sheet_size_px, (255, 255, 255))
        for slot in slots:
            prepared_data = self._prepared_slot(slot, assets, job_id, allow_mirror_bleed)
            self._paint_slot(
                sheet_image,
                slot,
                prepared_data,
                sheet_size_mm=sheet,
                dpi=dpi,
                duplex_flip=duplex_flip,
            )
        if any(profiles[slot["production"]["marks_profile_id"]]["crop_marks"] for slot in slots):
            self._paint_crop_marks(sheet_image, slots, profiles, sheet_size_mm=sheet, dpi=dpi, duplex_flip=duplex_flip)
        output = io.BytesIO()
        sheet_image.save(output, format="PNG", optimize=False)
        png_data = output.getvalue()

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

    def _paint_slot(
        self,
        sheet_image: Image.Image,
        slot: Mapping[str, Any],
        prepared_data: bytes,
        *,
        sheet_size_mm: Mapping[str, Any],
        dpi: int,
        duplex_flip: str,
    ) -> None:
        """Paint one transformed source and clip it to its V2 slot polygon.

        The preview is raster output, so applying the content transform to an
        in-memory image keeps the persisted Layout untouched while preserving
        the order: source orientation, fit, scale, internal rotation/mirror,
        slot rotation, then placement and clipping.
        """
        transform = slot["content_transform"]
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
        sheet_width_mm = float(sheet_size_mm["width"])
        sheet_height_mm = float(sheet_size_mm["height"])
        if duplex_flip == "long_edge":
            slot_geometry = SlotGeometry(
                center=Point(sheet_width_mm - slot_geometry.center.x, slot_geometry.center.y),
                trim_size=slot_geometry.trim_size,
                bleed=slot_geometry.bleed,
                rotation_deg=(-slot_geometry.rotation_deg) % 360,
            )
        elif duplex_flip == "short_edge":
            slot_geometry = SlotGeometry(
                center=Point(slot_geometry.center.x, sheet_height_mm - slot_geometry.center.y),
                trim_size=slot_geometry.trim_size,
                bleed=slot_geometry.bleed,
                rotation_deg=(-slot_geometry.rotation_deg) % 360,
            )
        with fitz.open(stream=prepared_data, filetype="pdf") as prepared:
            page = prepared[0]
            pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
            source = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

        source_size = Size(
            float(source.width) / (dpi / 25.4),
            float(source.height) / (dpi / 25.4),
        )
        internal_rotation = int(transform["rotation_deg"])
        oriented = Size(
            source_size.height if internal_rotation in (90, 270) else source_size.width,
            source_size.width if internal_rotation in (90, 270) else source_size.height,
        )
        clip_size = (
            slot_geometry.trim_size
            if transform["clip_to"] == "trim_box"
            else productive_size(slot_geometry.trim_size, slot_geometry.bleed)
        )
        fit_mode = transform["fit_mode"]
        if fit_mode == "actual_size":
            fit_scale_x = fit_scale_y = 1.0
        elif fit_mode == "contain":
            fit_scale_x = fit_scale_y = min(
                clip_size.width / oriented.width,
                clip_size.height / oriented.height,
            )
        elif fit_mode == "cover":
            fit_scale_x = fit_scale_y = max(
                clip_size.width / oriented.width,
                clip_size.height / oriented.height,
            )
        elif fit_mode == "stretch":
            fit_scale_x = clip_size.width / oriented.width
            fit_scale_y = clip_size.height / oriented.height
        else:  # pragma: no cover - contract validation owns this enum
            raise PreviewServiceError("PREVIEW_TRANSFORM_UNSUPPORTED", "Unknown content fit mode")

        resize_x = fit_scale_x * float(transform["scale_x"])
        resize_y = fit_scale_y * float(transform["scale_y"])
        resized = source.resize(
            (
                max(1, round(source.width * resize_x)),
                max(1, round(source.height * resize_y)),
            ),
            Image.Resampling.LANCZOS,
        )
        if transform["mirror_x"]:
            resized = ImageOps.mirror(resized)
        if transform["mirror_y"]:
            resized = ImageOps.flip(resized)
        if internal_rotation:
            resized = resized.rotate(internal_rotation, expand=True, resample=Image.Resampling.BICUBIC)
        slot_rotation = int(slot_geometry.rotation_deg)
        if slot_rotation:
            resized = resized.rotate(slot_rotation, expand=True, resample=Image.Resampling.BICUBIC)
        if duplex_flip == "long_edge":
            resized = ImageOps.mirror(resized)
        elif duplex_flip == "short_edge":
            resized = ImageOps.flip(resized)
        sheet_scale = dpi / 25.4
        center = Point(
            slot_geometry.center.x + (float(transform["offset_mm"]["x"]) if duplex_flip != "long_edge" else -float(transform["offset_mm"]["x"])),
            slot_geometry.center.y + (float(transform["offset_mm"]["y"]) if duplex_flip != "short_edge" else -float(transform["offset_mm"]["y"])),
        )
        center_px = (
            round(center.x * sheet_scale),
            round((sheet_height_mm - center.y) * sheet_scale),
        )
        left = center_px[0] - resized.width // 2
        top = center_px[1] - resized.height // 2
        layer = Image.new("RGBA", sheet_image.size, (0, 0, 0, 0))
        layer.paste(resized, (left, top))

        clip_polygon = (
            trim_polygon(slot_geometry)
            if transform["clip_to"] == "trim_box"
            else bleed_polygon(slot_geometry)
        )
        clip_mask = Image.new("L", sheet_image.size, 0)
        draw = ImageDraw.Draw(clip_mask)
        draw.polygon(
            [
                (
                    round(point.x * sheet_scale),
                    round((sheet_height_mm - point.y) * sheet_scale),
                )
                for point in clip_polygon.points
            ],
            fill=255,
        )
        alpha = ImageChops.multiply(layer.getchannel("A"), clip_mask)
        layer.putalpha(alpha)
        sheet_image.paste(layer.convert("RGB"), (0, 0), alpha)

    def _paint_crop_marks(
        self,
        sheet_image: Image.Image,
        slots: list[Mapping[str, Any]],
        profiles: Mapping[str, Mapping[str, Any]],
        *,
        sheet_size_mm: Mapping[str, Any],
        dpi: int,
        duplex_flip: str,
    ) -> None:
        """Draw deterministic four-corner crop ticks outside each trim."""
        sheet_width_mm = float(sheet_size_mm["width"])
        sheet_height_mm = float(sheet_size_mm["height"])
        sheet_scale = dpi / 25.4
        drawing = ImageDraw.Draw(sheet_image)
        length_mm = 3.0
        gap_mm = 1.0
        width_px = max(1, round(0.2 * sheet_scale))
        for slot in slots:
            profile = profiles[slot["production"]["marks_profile_id"]]
            if not profile["crop_marks"]:
                continue
            geometry = slot["geometry"]
            slot_geometry = SlotGeometry(
                center=Point(geometry["position_mm"]["x_mm"], geometry["position_mm"]["y_mm"]),
                trim_size=Size(geometry["trim_size_mm"]["width"], geometry["trim_size_mm"]["height"]),
                bleed=geometry["bleed_mm"],
                rotation_deg=geometry["rotation_deg"],
            )
            if duplex_flip == "long_edge":
                slot_geometry = SlotGeometry(
                    center=Point(sheet_width_mm - slot_geometry.center.x, slot_geometry.center.y),
                    trim_size=slot_geometry.trim_size,
                    bleed=slot_geometry.bleed,
                    rotation_deg=(-slot_geometry.rotation_deg) % 360,
                )
            elif duplex_flip == "short_edge":
                slot_geometry = SlotGeometry(
                    center=Point(slot_geometry.center.x, sheet_height_mm - slot_geometry.center.y),
                    trim_size=slot_geometry.trim_size,
                    bleed=slot_geometry.bleed,
                    rotation_deg=(-slot_geometry.rotation_deg) % 360,
                )
            polygon = trim_polygon(slot_geometry)
            for index, point in enumerate(polygon.points):
                previous = polygon.points[index - 1]
                following = polygon.points[(index + 1) % len(polygon.points)]
                for other in (previous, following):
                    dx = point.x - other.x
                    dy = point.y - other.y
                    norm = (dx * dx + dy * dy) ** 0.5
                    if norm == 0:
                        continue
                    start = (point.x + dx / norm * gap_mm, point.y + dy / norm * gap_mm)
                    end = (point.x + dx / norm * (gap_mm + length_mm), point.y + dy / norm * (gap_mm + length_mm))
                    drawing.line(
                        (
                            round(start[0] * sheet_scale),
                            round((sheet_height_mm - start[1]) * sheet_scale),
                            round(end[0] * sheet_scale),
                            round((sheet_height_mm - end[1]) * sheet_scale),
                        ),
                        fill=(0, 0, 0),
                        width=width_px,
                    )


__all__ = [
    "PREVIEW_DEFAULT_DPI",
    "PREVIEW_MAX_DPI",
    "PREVIEW_MIN_DPI",
    "PreviewResult",
    "PreviewService",
    "PreviewServiceError",
]
