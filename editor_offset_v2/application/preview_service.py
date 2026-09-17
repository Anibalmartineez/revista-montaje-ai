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

from editor_offset_v2.application.preflight_service import PreflightService, PreflightServiceError
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
from editor_offset_v2.infrastructure.process_lock import exclusive_file_lock
from editor_offset_v2.infrastructure.output_snapshot import OutputSnapshot, snapshot_operation
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
    data: bytes = b""


def _same_number(left: object, right: object) -> bool:
    return abs(float(left) - float(right)) <= PREVIEW_METADATA_TOLERANCE_MM


def _same_box(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(_same_number(actual[key], expected[key]) for key in ("x", "y", "width", "height"))


class PreviewService:
    """Render a single-face PNG without changing Layout V2 or invoking V1."""

    def __init__(self, jobs: JobRepository):
        self._jobs = jobs
        self._assets = AssetRepository(jobs)

    @snapshot_operation(PreviewServiceError)
    def render(
        self,
        job_id: str,
        *,
        face: str = "front",
        dpi: int = PREVIEW_DEFAULT_DPI,
        allow_mirror_bleed: bool = False,
        require_preflight: bool = True,
    ) -> PreviewResult:
        if require_preflight:
            try:
                preflight = PreflightService(self._jobs).run(
                    job_id,
                    enabled_operations={"preview": True},
                )
                PreflightService(self._jobs).consume(job_id, preflight, "preview")
            except PreflightServiceError as exc:
                error = PreviewServiceError(exc.code, exc.message, exc.status_code)
                error.issues = exc.issues
                raise error from exc
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
        from editor_offset_v2.infrastructure.pdf_compositor import compose_pdf
        pdf_data = compose_pdf(layout, (face,), lambda slot:self._prepared_slot(slot,assets,job_id,allow_mirror_bleed))
        with fitz.open(stream=pdf_data,filetype='pdf') as document:
            # Exact requested raster size; physical PDF remains independent of DPI.
            matrix=fitz.Matrix(sheet_width_px/document[0].rect.width,sheet_height_px/document[0].rect.height)
            pix=document[0].get_pixmap(matrix=matrix,colorspace=fitz.csRGB,alpha=False)
            image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples).crop((0,0,sheet_width_px,sheet_height_px))
            output=io.BytesIO(); image.save(output,format='PNG'); png_data=output.getvalue()

        previews = self._jobs.job_path(job_id) / "previews"
        previews.mkdir(exist_ok=True)
        target = previews / f"preview_r{layout['job']['revision']}_{face}_{dpi}_{self._jobs.request_key}.png"
        temporary: Path | None = None
        try:
            with self._jobs.publication(previews):
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
            data=png_data,
        )

    def _prepared_slot(
        self,
        slot: Mapping[str, Any],
        assets: Mapping[str, Mapping[str, Any]],
        job_id: str,
        allow_mirror_bleed: bool,
    ) -> bytes:
        if isinstance(self._jobs,OutputSnapshot) and slot['id'] in self._jobs.prepared:
            return self._jobs.prepared[slot['id']]
        cache_key = __import__('json').dumps([slot['source'],slot['geometry']['trim_size_mm'],slot['geometry']['bleed_mm'],slot['content_transform']['clip_to'],allow_mirror_bleed],sort_keys=True)
        if isinstance(self._jobs,OutputSnapshot) and cache_key in self._jobs.prepared_by_source:
            return self._jobs.prepared_by_source[cache_key]
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
            source_data = self._jobs.read_source(source_path) if isinstance(self._jobs,OutputSnapshot) else source_path.read_bytes()
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
        derived = slot["source"].get("derived")
        if derived is not None:
            data = self._read_derived_source(job_id, asset, derived)
            with fitz.open(stream=data,filetype='pdf') as document:
                bleed = slot['geometry']['bleed_mm'] if transform['clip_to']=='bleed_box' else 0
                expected = (trim['width']+2*bleed, trim['height']+2*bleed)
                actual = (document[0].rect.width / POINTS_PER_MM, document[0].rect.height / POINTS_PER_MM)
                if any(abs(a-b)>0.01 for a,b in zip(actual,expected)):
                    raise PreviewServiceError('DERIVED_SIZE_MISMATCH','Derived page dimensions do not match the selected trim and clipping')
            return data
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
        if isinstance(self._jobs,OutputSnapshot): self._jobs.prepared_by_source[cache_key]=prepared.data
        return prepared.data

    def _read_derived_source(
        self,
        job_id: str,
        asset: Mapping[str, Any],
        derived: Mapping[str, Any],
    ) -> bytes:
        if not isinstance(derived, Mapping):
            raise PreviewServiceError("INVALID_DERIVED_SOURCE", "The derived source reference is invalid")
        key = derived.get("derived_key")
        expected_sha = derived.get("derived_sha256")
        source_sha = derived.get("source_sha256")
        if not isinstance(key, str) or not key.startswith("derived/") or "\\" in key:
            raise PreviewServiceError("UNSAFE_DERIVED_PATH", "The derived source path is unsafe")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise PreviewServiceError("INVALID_DERIVED_SOURCE", "The derived source hash is invalid")
        if source_sha != asset.get("sha256"):
            raise PreviewServiceError("DERIVED_SOURCE_MISMATCH", "The derived source belongs to another asset")
        try:
            root = self._jobs.job_path(job_id).resolve(strict=True)
            candidate = root / Path(*key.split('/'))
            if any(p.is_symlink() for p in (candidate, *candidate.parents)):
                raise PreviewServiceError('UNSAFE_DERIVED_PATH','Symlinks are not valid derived sources')
            target = candidate.resolve(strict=True)
            target.relative_to((root / "derived").resolve(strict=True))
            if target.is_symlink() or not target.is_file():
                raise PreviewServiceError("UNSAFE_DERIVED_PATH", "The derived source path is unsafe")
            data = self._jobs.read_source(target) if isinstance(self._jobs,OutputSnapshot) else target.read_bytes()
        except PreviewServiceError:
            raise
        except (OSError, ValueError, JobRepositoryError) as exc:
            raise PreviewServiceError("DERIVED_SOURCE_MISSING", "The derived source PDF is unavailable") from exc
        if hashlib.sha256(data).hexdigest().lower() != expected_sha.lower():
            raise PreviewServiceError("DERIVED_IDENTITY_MISMATCH", "The derived source hash differs from its reference")
        try:
            with fitz.open(stream=data, filetype="pdf") as document:
                if document.needs_pass or document.page_count != 1:
                    raise PreviewServiceError("INVALID_DERIVED_SOURCE", "The derived source must be one readable PDF page")
        except PreviewServiceError:
            raise
        except (fitz.FileDataError, RuntimeError, ValueError) as exc:
            raise PreviewServiceError("INVALID_DERIVED_SOURCE", "The derived source PDF is unreadable") from exc
        return data



__all__ = [
    "PREVIEW_DEFAULT_DPI",
    "PREVIEW_MAX_DPI",
    "PREVIEW_MIN_DPI",
    "PreviewResult",
    "PreviewService",
    "PreviewServiceError",
]
