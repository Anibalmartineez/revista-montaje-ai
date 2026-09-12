"""Versioned, opt-in materialization of edited V2 PDF pages.

The uploaded PDF remains immutable. This service creates a new one-page PDF under
the job's derived tree and records the operation and hashes in a manifest.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import fitz
from PIL import Image, ImageOps

from editor_offset_v2.application.job_service import JobService, JobServiceError
from editor_offset_v2.infrastructure.asset_repository import AssetRepository, AssetRepositoryError, SOURCE_FILENAME
from editor_offset_v2.infrastructure.job_repository import JobRepository
from editor_offset_v2.infrastructure.prepared_pdf_source import prepare_source, SourcePreparationError


DERIVED_RENDER_DPI = 300


@dataclass(frozen=True)
class DerivedAssetServiceError(Exception):
    code: str
    message: str
    status_code: int
    issues: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class DerivedPageResult:
    asset_id: str
    page_number: int
    derived_key: str
    sha256: str
    manifest: dict[str, object]


class DerivedAssetService:
    def __init__(self, jobs: JobService, repository: AssetRepository, job_repository: JobRepository):
        self._jobs = jobs
        self._assets = repository
        self._job_repository = job_repository

    def materialize_page(
        self,
        job_id: object,
        asset_id: object,
        page_number: object,
        *,
        pdf_box: str = "trim",
        bleed_mm: float = 0,
        allow_mirror_bleed: bool = False,
        content_transform: Mapping[str, object] | None = None,
    ) -> DerivedPageResult:
        try:
            job = self._jobs.get_job(job_id)
            asset_path = self._assets.asset_path(job.job_id, asset_id)
        except (JobServiceError, AssetRepositoryError) as exc:
            raise DerivedAssetServiceError(getattr(exc, "code", "ASSET_NOT_FOUND"), str(exc), 404) from exc
        asset = next((item for item in job.layout["assets"] if item["id"] == asset_id), None)
        if asset is None:
            raise DerivedAssetServiceError("ASSET_NOT_FOUND", "The V2 asset does not exist", 404)
        if isinstance(page_number, bool) or not isinstance(page_number, int) or not 1 <= page_number <= asset["page_count"]:
            raise DerivedAssetServiceError("INVALID_SOURCE_PAGE", "Selected PDF page does not exist", 400)
        if not isinstance(pdf_box, str) or pdf_box not in {"media", "crop", "trim", "bleed"}:
            raise DerivedAssetServiceError("INVALID_SOURCE_BOX", "Unknown PDF source box", 400)
        if isinstance(bleed_mm, bool) or not isinstance(bleed_mm, (int, float)) or bleed_mm < 0:
            raise DerivedAssetServiceError("INVALID_DERIVED_OPTION", "bleed_mm must be non-negative", 400)
        if not isinstance(allow_mirror_bleed, bool):
            raise DerivedAssetServiceError("INVALID_DERIVED_OPTION", "allow_mirror_bleed must be boolean", 400)
        transform = self._normalize_materialization_transform(content_transform, pdf_box)
        source = asset_path / SOURCE_FILENAME
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise DerivedAssetServiceError("ASSET_FILE_NOT_FOUND", "The source PDF is unavailable", 404) from exc
        if hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise DerivedAssetServiceError("ASSET_HASH_MISMATCH", "Source identity differs from the saved asset", 409)
        try:
            prepared = prepare_source(
                data,
                page_number=page_number,
                pdf_box=pdf_box,
                bleed_mm=float(bleed_mm),
                clip_to=transform["clip_to"],
                allow_mirror_bleed=allow_mirror_bleed,
            )
        except SourcePreparationError as exc:
            raise DerivedAssetServiceError(exc.code, str(exc), 422) from exc
        if content_transform is not None:
            try:
                prepared_data = self._bake_transform(
                    prepared.data,
                    transform,
                    trim_size=prepared.trim_size,
                    bleed_mm=float(bleed_mm),
                )
            except (OSError, RuntimeError, ValueError) as exc:
                raise DerivedAssetServiceError(
                    "DERIVED_TRANSFORM_FAILED",
                    "The content transform could not be baked into the derived PDF",
                    422,
                ) from exc
        else:
            prepared_data = prepared.data
        digest = hashlib.sha256(prepared_data).hexdigest()
        revision = int(job.revision)
        root = self._job_repository.job_path(job.job_id) / "derived" / "assets" / str(asset_id) / f"page_{page_number}"
        root.mkdir(parents=True, exist_ok=True)
        filename = f"r{revision}_{digest[:16]}.pdf"
        target = root / filename
        manifest_path = root / f"r{revision}_{digest[:16]}.json"
        self._atomic_write(target, prepared_data)
        output_width = prepared.trim_size.width + (2 * float(bleed_mm) if transform["clip_to"] == "bleed_box" else 0)
        output_height = prepared.trim_size.height + (2 * float(bleed_mm) if transform["clip_to"] == "bleed_box" else 0)
        manifest = {
            "schema_version": 1,
            "asset_id": asset_id,
            "page": page_number,
            "source_sha256": asset["sha256"],
            "derived_sha256": digest,
            "source_box": pdf_box,
            "bleed_mm": float(bleed_mm),
            "allow_mirror_bleed": allow_mirror_bleed,
            "content_transform": {
                **transform,
            },
            "trim_size_mm": {"width": prepared.trim_size.width, "height": prepared.trim_size.height},
            "size_mm": {"width": output_width if content_transform is not None else prepared.size.width,
                         "height": output_height if content_transform is not None else prepared.size.height},
            "layout_revision": revision,
            "derived_key": f"derived/assets/{asset_id}/page_{page_number}/{filename}",
        }
        self._atomic_write(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
        return DerivedPageResult(asset_id, page_number, manifest["derived_key"], digest, manifest)

    @staticmethod
    def _normalize_materialization_transform(
        transform: Mapping[str, object] | None,
        pdf_box: str,
    ) -> dict[str, object]:
        """Normalize the transform that will be baked into the derived page."""
        expected_clip = "bleed_box" if pdf_box == "bleed" else "trim_box"
        defaults: dict[str, object] = {
            "fit_mode": "actual_size",
            "scale_x": 1.0,
            "scale_y": 1.0,
            "offset_mm": {"x": 0.0, "y": 0.0},
            "rotation_deg": 0,
            "mirror_x": False,
            "mirror_y": False,
            "clip_to": expected_clip,
        }
        if transform is None:
            return defaults
        if not isinstance(transform, Mapping):
            raise DerivedAssetServiceError(
                "INVALID_DERIVED_TRANSFORM",
                "content_transform must be an object",
                400,
            )
        normalized = {**defaults, **dict(transform)}
        fit_mode = normalized["fit_mode"]
        scale_x = normalized["scale_x"]
        scale_y = normalized["scale_y"]
        offset = normalized["offset_mm"]
        rotation = normalized["rotation_deg"]
        mirror_x = normalized["mirror_x"]
        mirror_y = normalized["mirror_y"]
        clip_to = normalized["clip_to"]
        try:
            valid = (
                fit_mode in {"actual_size", "contain", "cover", "stretch"}
                and not isinstance(scale_x, bool) and float(scale_x) > 0
                and not isinstance(scale_y, bool) and float(scale_y) > 0
                and isinstance(offset, Mapping)
                and not isinstance(offset.get("x", 0.0), bool)
                and not isinstance(offset.get("y", 0.0), bool)
                and math.isfinite(float(offset.get("x", 0.0)))
                and math.isfinite(float(offset.get("y", 0.0)))
                and not isinstance(rotation, bool)
                and float(rotation) in {0.0, 90.0, 180.0, 270.0}
                and isinstance(mirror_x, bool)
                and isinstance(mirror_y, bool)
                and clip_to in {"trim_box", "bleed_box"}
            )
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            raise DerivedAssetServiceError(
                "INVALID_DERIVED_TRANSFORM",
                "content_transform contains unsupported values",
                400,
            )
        return {
            "fit_mode": str(fit_mode),
            "scale_x": float(scale_x),
            "scale_y": float(scale_y),
            "offset_mm": {"x": float(offset.get("x", 0.0)), "y": float(offset.get("y", 0.0))},
            "rotation_deg": int(float(rotation)),
            "mirror_x": mirror_x,
            "mirror_y": mirror_y,
            "clip_to": str(clip_to),
        }

    @staticmethod
    def _bake_transform(
        pdf_data: bytes,
        transform: Mapping[str, object],
        *,
        trim_size: object,
        bleed_mm: float,
    ) -> bytes:
        """Rasterize and bake the V2 content transform into a one-page PDF."""
        with fitz.open(stream=pdf_data, filetype="pdf") as source:
            page = source[0]
            pixmap = page.get_pixmap(dpi=DERIVED_RENDER_DPI, colorspace=fitz.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        points_per_mm = 72.0 / 25.4
        scale = DERIVED_RENDER_DPI / 25.4
        trim_width = float(trim_size.width)
        trim_height = float(trim_size.height)
        clip_width = trim_width + (2 * bleed_mm if transform["clip_to"] == "bleed_box" else 0)
        clip_height = trim_height + (2 * bleed_mm if transform["clip_to"] == "bleed_box" else 0)
        rotation = int(transform["rotation_deg"])
        oriented_width = image.height if rotation in (90, 270) else image.width
        oriented_height = image.width if rotation in (90, 270) else image.height
        clip_width_px = max(1, round(clip_width * scale))
        clip_height_px = max(1, round(clip_height * scale))
        if transform["fit_mode"] == "actual_size":
            fit_x = fit_y = 1.0
        elif transform["fit_mode"] == "contain":
            fit_x = fit_y = min(clip_width_px / oriented_width, clip_height_px / oriented_height)
        elif transform["fit_mode"] == "cover":
            fit_x = fit_y = max(clip_width_px / oriented_width, clip_height_px / oriented_height)
        else:
            fit_x = clip_width_px / oriented_width
            fit_y = clip_height_px / oriented_height
        image = image.resize(
            (max(1, round(image.width * fit_x * float(transform["scale_x"]))),
             max(1, round(image.height * fit_y * float(transform["scale_y"]))),
            ),
            Image.Resampling.LANCZOS,
        )
        if transform["mirror_x"]:
            image = ImageOps.mirror(image)
        if transform["mirror_y"]:
            image = ImageOps.flip(image)
        if rotation:
            image = image.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
        canvas = Image.new("RGB", (clip_width_px, clip_height_px), "white")
        offset_x = round(float(transform["offset_mm"]["x"]) * scale)
        offset_y = round(float(transform["offset_mm"]["y"]) * scale)
        left = (clip_width_px - image.width) // 2 + offset_x
        top = (clip_height_px - image.height) // 2 - offset_y
        canvas.paste(image, (left, top))
        output = io.BytesIO()
        canvas.save(output, format="PNG", optimize=False)
        with fitz.open() as document:
            target = document.new_page(width=clip_width * points_per_mm, height=clip_height * points_per_mm)
            target.insert_image(target.rect, stream=output.getvalue(), keep_proportion=False)
            return document.tobytes(garbage=4, deflate=True, no_new_id=True)

    @staticmethod
    def _atomic_write(target: Path, data: bytes) -> None:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".derived-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
        except OSError as exc:
            raise DerivedAssetServiceError("DERIVED_PUBLISH_FAILED", "The derived PDF could not be published", 500) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


__all__ = ["DerivedAssetService", "DerivedAssetServiceError", "DerivedPageResult"]
