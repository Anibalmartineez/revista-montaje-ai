"""Versioned, opt-in materialization of edited V2 PDF pages.

The uploaded PDF remains immutable. This service creates a new one-page PDF under
the job's derived tree and records the operation and hashes in a manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from editor_offset_v2.application.job_service import JobService, JobServiceError
from editor_offset_v2.infrastructure.asset_repository import AssetRepository, AssetRepositoryError, SOURCE_FILENAME
from editor_offset_v2.infrastructure.job_repository import JobRepository
from editor_offset_v2.infrastructure.prepared_pdf_source import prepare_source, SourcePreparationError


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
                clip_to="bleed_box" if pdf_box == "bleed" else "trim_box",
                allow_mirror_bleed=allow_mirror_bleed,
            )
        except SourcePreparationError as exc:
            raise DerivedAssetServiceError(exc.code, str(exc), 422) from exc
        digest = hashlib.sha256(prepared.data).hexdigest()
        revision = int(job.revision)
        root = self._job_repository.job_path(job.job_id) / "derived" / "assets" / str(asset_id) / f"page_{page_number}"
        root.mkdir(parents=True, exist_ok=True)
        filename = f"r{revision}_{digest[:16]}.pdf"
        target = root / filename
        manifest_path = root / f"r{revision}_{digest[:16]}.json"
        self._atomic_write(target, prepared.data)
        manifest = {
            "schema_version": 1,
            "asset_id": asset_id,
            "page": page_number,
            "source_sha256": asset["sha256"],
            "derived_sha256": digest,
            "source_box": pdf_box,
            "bleed_mm": float(bleed_mm),
            "allow_mirror_bleed": allow_mirror_bleed,
            "trim_size_mm": {"width": prepared.trim_size.width, "height": prepared.trim_size.height},
            "size_mm": {"width": prepared.size.width, "height": prepared.size.height},
            "layout_revision": revision,
            "derived_key": f"derived/assets/{asset_id}/page_{page_number}/{filename}",
        }
        self._atomic_write(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
        return DerivedPageResult(asset_id, page_number, manifest["derived_key"], digest, manifest)

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
