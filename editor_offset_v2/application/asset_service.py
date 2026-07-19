"""Transactional application service for physical Editor Offset V2 PDF assets."""

from __future__ import annotations

import copy
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final

from werkzeug.datastructures import FileStorage

from editor_offset_v2.application.job_service import (
    JobResult,
    JobService,
    JobServiceError,
    utc_now_iso,
)
from editor_offset_v2.infrastructure.asset_repository import (
    SOURCE_FILENAME,
    THUMBNAILS_DIRECTORY,
    AssetRepository,
    AssetRepositoryError,
)
from editor_offset_v2.infrastructure.pdf_inspector import (
    PdfInspection,
    PdfInspectionError,
    inspect_pdf,
)
from editor_offset_v2.infrastructure.thumbnail_renderer import (
    ThumbnailRenderError,
    render_thumbnails,
)


ASSET_METADATA_SCHEMA_VERSION: Final = 1
ACCEPTED_PDF_MIME_TYPES: Final = frozenset(
    {"application/pdf", "application/x-pdf", "application/octet-stream", ""}
)


@dataclass(frozen=True)
class AssetServiceError(Exception):
    code: str
    message: str
    status_code: int
    issues: tuple[dict[str, str], ...] = ()

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class AssetUploadResult:
    job_id: str
    asset_id: str
    revision: int
    asset: dict[str, object]
    layout: dict[str, object]


class AssetService:
    def __init__(
        self,
        job_service: JobService,
        repository: AssetRepository,
        *,
        max_upload_bytes: int,
        clock: Callable[[], str] = utc_now_iso,
        id_factory: Callable[[], str] | None = None,
    ):
        if isinstance(max_upload_bytes, bool) or not isinstance(max_upload_bytes, int):
            raise ValueError("max_upload_bytes must be a positive integer")
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes must be a positive integer")
        self._jobs = job_service
        self._repository = repository
        self._max_upload_bytes = max_upload_bytes
        self._clock = clock
        self._id_factory = id_factory or (lambda: f"asset_{secrets.token_hex(12)}")

    def upload_pdf(
        self,
        job_id: object,
        base_revision: object,
        file_storage: FileStorage | None,
    ) -> AssetUploadResult:
        current = self._jobs.get_job(job_id)
        self._validate_base_revision(base_revision, current)
        original_filename, mime_type = self._validate_file(file_storage)
        assert file_storage is not None

        staging: Path | None = None
        finalized: Path | None = None
        try:
            asset_id, staging = self._allocate_staging(current.job_id)
            stored = self._repository.write_source(
                staging,
                file_storage.stream,
                max_bytes=self._max_upload_bytes,
            )
            source_path = staging / SOURCE_FILENAME
            try:
                inspection = inspect_pdf(source_path)
            except PdfInspectionError as exc:
                raise AssetServiceError("INVALID_PDF", str(exc), 400) from exc
            try:
                render_thumbnails(
                    source_path,
                    staging / THUMBNAILS_DIRECTORY,
                    inspection,
                )
            except ThumbnailRenderError as exc:
                raise AssetServiceError("THUMBNAIL_RENDER_FAILED", str(exc), 422) from exc

            timestamp = self._clock()
            asset = self._build_layout_asset(
                asset_id=asset_id,
                original_filename=original_filename,
                mime_type=mime_type,
                sha256=stored.sha256,
                timestamp=timestamp,
                inspection=inspection,
            )
            metadata = {
                "metadata_schema_version": ASSET_METADATA_SCHEMA_VERSION,
                "asset": asset,
                "size_bytes": stored.size_bytes,
                "suggested_boxes": {
                    str(page.number): page.suggested_box for page in inspection.pages
                },
                "suggested_sizes_mm": {
                    str(page.number): {
                        "width": page.suggested_size_mm[0],
                        "height": page.suggested_size_mm[1],
                    }
                    for page in inspection.pages
                },
            }
            self._repository.write_metadata(staging, metadata)
            finalized = self._repository.finalize(current.job_id, asset_id, staging)
            staging = None

            submitted = copy.deepcopy(current.layout)
            submitted["assets"].append(copy.deepcopy(asset))
            saved = self._jobs.save_layout(
                current.job_id,
                base_revision,
                submitted,
            )
            return AssetUploadResult(
                job_id=current.job_id,
                asset_id=asset_id,
                revision=saved.revision,
                asset=copy.deepcopy(asset),
                layout=copy.deepcopy(saved.layout),
            )
        except (AssetServiceError, JobServiceError, AssetRepositoryError) as exc:
            target = finalized or staging
            try:
                self._repository.cleanup(current.job_id, target)
            except AssetRepositoryError as cleanup_error:
                raise AssetServiceError(
                    "PERSISTENCE_ERROR",
                    "Asset incorporation failed and its incomplete files could not be cleaned",
                    500,
                ) from cleanup_error
            if isinstance(exc, AssetRepositoryError):
                raise self._map_repository_error(exc) from exc
            raise

    def thumbnail_path(
        self,
        job_id: object,
        asset_id: object,
        page_number: object,
    ) -> Path:
        current = self._jobs.get_job(job_id)
        try:
            safe_asset_id = self._repository.asset_path(
                current.job_id,
                asset_id,
            ).name
        except AssetRepositoryError as exc:
            raise self._map_repository_error(exc) from exc
        asset = next(
            (item for item in current.layout["assets"] if item["id"] == safe_asset_id),
            None,
        )
        if asset is None:
            raise AssetServiceError("ASSET_NOT_FOUND", "The V2 asset does not exist", 404)
        expected_storage_key = f"assets/{safe_asset_id}/{SOURCE_FILENAME}"
        if asset.get("storage_key") != expected_storage_key:
            raise AssetServiceError(
                "UNSAFE_ASSET_PATH",
                "The asset storage_key does not match its server-managed location",
                400,
            )
        if isinstance(page_number, bool) or not isinstance(page_number, int):
            raise AssetServiceError("INVALID_PAGE", "page must be a positive integer", 400)
        page = next(
            (item for item in asset["pages"] if item["number"] == page_number),
            None,
        )
        if page is None:
            raise AssetServiceError("THUMBNAIL_NOT_FOUND", "The asset page does not exist", 404)
        expected_preview_key = (
            f"assets/{safe_asset_id}/thumbnails/page_{page_number}.png"
        )
        if page.get("preview_key") != expected_preview_key:
            raise AssetServiceError(
                "UNSAFE_ASSET_PATH",
                "The page preview_key does not match its server-managed location",
                400,
            )
        try:
            return self._repository.thumbnail_path(
                current.job_id,
                safe_asset_id,
                page_number,
            )
        except AssetRepositoryError as exc:
            raise self._map_repository_error(exc) from exc

    def _allocate_staging(self, job_id: str) -> tuple[str, Path]:
        for _ in range(5):
            asset_id = self._id_factory()
            try:
                return asset_id, self._repository.begin_staging(job_id, asset_id)
            except AssetRepositoryError as exc:
                if exc.code == "ASSET_ALREADY_EXISTS":
                    continue
                raise
        raise AssetServiceError(
            "PERSISTENCE_ERROR",
            "A unique V2 asset identifier could not be allocated",
            500,
        )

    @staticmethod
    def _validate_base_revision(base_revision: object, current: JobResult) -> None:
        if (
            isinstance(base_revision, bool)
            or not isinstance(base_revision, int)
            or base_revision < 0
        ):
            raise AssetServiceError(
                "INVALID_LAYOUT",
                "base_revision must be a non-negative integer",
                400,
            )
        if base_revision != current.revision:
            raise AssetServiceError(
                "REVISION_CONFLICT",
                "The upload base revision does not match the persisted layout",
                409,
            )

    @staticmethod
    def _validate_file(file_storage: FileStorage | None) -> tuple[str, str]:
        if file_storage is None:
            raise AssetServiceError("FILE_REQUIRED", "A multipart PDF file is required", 400)
        raw_name = file_storage.filename
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise AssetServiceError("INVALID_FILENAME", "The uploaded filename is empty", 400)
        normalized = raw_name.strip().replace("\\", "/")
        original_filename = PurePosixPath(normalized).name
        original_filename = PureWindowsPath(original_filename).name
        if not original_filename or len(original_filename) > 255:
            raise AssetServiceError(
                "INVALID_FILENAME",
                "The uploaded filename must contain at most 255 characters",
                400,
            )
        if Path(original_filename).suffix.lower() != ".pdf":
            raise AssetServiceError(
                "UNSUPPORTED_FILE_TYPE",
                "Only files with a .pdf extension are accepted",
                415,
            )
        mime_type = (file_storage.mimetype or "").split(";", 1)[0].strip().lower()
        if mime_type not in ACCEPTED_PDF_MIME_TYPES:
            raise AssetServiceError(
                "UNSUPPORTED_FILE_TYPE",
                "The uploaded MIME type is not compatible with PDF",
                415,
            )
        return original_filename, "application/pdf"

    @staticmethod
    def _build_layout_asset(
        *,
        asset_id: str,
        original_filename: str,
        mime_type: str,
        sha256: str,
        timestamp: str,
        inspection: PdfInspection,
    ) -> dict[str, object]:
        pages: list[dict[str, object]] = []
        for page in inspection.pages:
            pages.append(
                {
                    "number": page.number,
                    "intrinsic_rotation_deg": page.intrinsic_rotation_deg,
                    "boxes_mm": page.boxes_as_layout(),
                    "preview_key": (
                        f"assets/{asset_id}/thumbnails/page_{page.number}.png"
                    ),
                    "preflight": {
                        "status": "not_run",
                        "color_spaces": [],
                        "minimum_effective_dpi": None,
                        "has_transparency": None,
                        "has_overprint": None,
                        "issues": [],
                    },
                }
            )
        return {
            "id": asset_id,
            "original_filename": original_filename,
            "storage_key": f"assets/{asset_id}/{SOURCE_FILENAME}",
            "mime_type": mime_type,
            "sha256": sha256,
            "page_count": inspection.page_count,
            "status": "ready",
            "created_at": timestamp,
            "preflight_status": "not_run",
            "preflight_report_id": None,
            "preflight_updated_at": None,
            "pages": pages,
        }

    @staticmethod
    def _map_repository_error(error: AssetRepositoryError) -> AssetServiceError:
        status_codes = {
            "INVALID_ASSET_ID": 400,
            "INVALID_PAGE": 400,
            "JOB_NOT_FOUND": 404,
            "ASSET_NOT_FOUND": 404,
            "THUMBNAIL_NOT_FOUND": 404,
            "EMPTY_FILE": 400,
            "INVALID_PDF_SIGNATURE": 400,
            "FILE_TOO_LARGE": 413,
            "ASSET_ALREADY_EXISTS": 409,
            "UNSAFE_ASSET_PATH": 400,
            "INVALID_UPLOAD": 400,
            "PERSISTENCE_ERROR": 500,
        }
        return AssetServiceError(
            error.code,
            error.message,
            status_codes.get(error.code, 500),
        )


__all__ = [
    "ACCEPTED_PDF_MIME_TYPES",
    "ASSET_METADATA_SCHEMA_VERSION",
    "AssetService",
    "AssetServiceError",
    "AssetUploadResult",
]
