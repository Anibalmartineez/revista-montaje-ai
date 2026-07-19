"""Safe filesystem storage for immutable physical Editor Offset V2 assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final, Mapping

from .job_repository import JobRepository, JobRepositoryError, validate_job_id


ASSET_ID_PATTERN: Final = re.compile(r"^asset_[a-f0-9]{24}$")
MAX_ASSET_ID_LENGTH: Final = 64
SOURCE_FILENAME: Final = "source.pdf"
METADATA_FILENAME: Final = "metadata.json"
THUMBNAILS_DIRECTORY: Final = "thumbnails"
UPLOAD_CHUNK_BYTES: Final = 64 * 1024


class AssetRepositoryError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class StoredUpload:
    size_bytes: int
    sha256: str


def validate_asset_id(asset_id: object) -> str:
    if not isinstance(asset_id, str):
        raise AssetRepositoryError("INVALID_ASSET_ID", "asset_id must be a string")
    if len(asset_id) > MAX_ASSET_ID_LENGTH or not ASSET_ID_PATTERN.fullmatch(asset_id):
        raise AssetRepositoryError(
            "INVALID_ASSET_ID",
            "asset_id must match the server-generated asset identifier format",
        )
    return asset_id


class AssetRepository:
    def __init__(self, job_repository: JobRepository):
        self._jobs = job_repository

    def assets_root(self, job_id: object) -> Path:
        safe_job_id = validate_job_id(job_id)
        job_path = self._jobs.job_path(safe_job_id)
        if not job_path.is_dir():
            raise AssetRepositoryError("JOB_NOT_FOUND", "The V2 job does not exist")
        root = job_path / "assets"
        if root.is_symlink() or not root.is_dir():
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "The V2 asset root is missing or unsafe",
            )
        return root.resolve(strict=True)

    def asset_path(self, job_id: object, asset_id: object) -> Path:
        safe_asset_id = validate_asset_id(asset_id)
        root = self.assets_root(job_id)
        candidate = root / safe_asset_id
        self._assert_direct_child(root, candidate)
        return candidate

    def begin_staging(self, job_id: object, asset_id: object) -> Path:
        safe_asset_id = validate_asset_id(asset_id)
        root = self.assets_root(job_id)
        final = self.asset_path(job_id, safe_asset_id)
        if final.exists() or final.is_symlink():
            raise AssetRepositoryError(
                "ASSET_ALREADY_EXISTS",
                "The generated asset identifier already exists",
            )
        try:
            staging = Path(tempfile.mkdtemp(prefix=f".{safe_asset_id}.", suffix=".upload", dir=root))
        except OSError as exc:
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "The asset staging directory could not be created",
            ) from exc
        self._assert_direct_child(root, staging)
        return staging

    def write_source(
        self,
        staging: Path,
        stream: BinaryIO,
        *,
        max_bytes: int,
    ) -> StoredUpload:
        target = staging / SOURCE_FILENAME
        digest = hashlib.sha256()
        size = 0
        signature = b""
        try:
            with target.open("xb") as output:
                while True:
                    chunk = stream.read(UPLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise AssetRepositoryError(
                            "INVALID_UPLOAD",
                            "The uploaded stream did not return bytes",
                        )
                    size += len(chunk)
                    if size > max_bytes:
                        raise AssetRepositoryError(
                            "FILE_TOO_LARGE",
                            f"The PDF exceeds the configured limit of {max_bytes} bytes",
                        )
                    if len(signature) < 5:
                        signature += chunk[: 5 - len(signature)]
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except AssetRepositoryError:
            raise
        except OSError as exc:
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "The uploaded PDF could not be stored",
            ) from exc
        if size == 0:
            raise AssetRepositoryError("EMPTY_FILE", "The uploaded PDF is empty")
        if signature != b"%PDF-":
            raise AssetRepositoryError(
                "INVALID_PDF_SIGNATURE",
                "The uploaded file does not begin with a PDF signature",
            )
        return StoredUpload(size_bytes=size, sha256=digest.hexdigest())

    def write_metadata(self, staging: Path, metadata: Mapping[str, object]) -> None:
        target = staging / METADATA_FILENAME
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".metadata.",
                suffix=".tmp",
                dir=staging,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                json.dump(
                    metadata,
                    stream,
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=2,
                    sort_keys=True,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
        except (OSError, TypeError, ValueError) as exc:
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "Asset metadata could not be written atomically",
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def finalize(self, job_id: object, asset_id: object, staging: Path) -> Path:
        root = self.assets_root(job_id)
        final = self.asset_path(job_id, asset_id)
        self._assert_direct_child(root, staging)
        if staging.is_symlink() or not staging.is_dir():
            raise AssetRepositoryError("PERSISTENCE_ERROR", "Asset staging is unsafe")
        if final.exists() or final.is_symlink():
            raise AssetRepositoryError("ASSET_ALREADY_EXISTS", "Asset already exists")
        try:
            os.rename(staging, final)
        except OSError as exc:
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "The immutable asset could not be finalized",
            ) from exc
        return final

    def thumbnail_path(self, job_id: object, asset_id: object, page: object) -> Path:
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise AssetRepositoryError("INVALID_PAGE", "page must be a positive integer")
        asset = self.asset_path(job_id, asset_id)
        root = self.assets_root(job_id)
        if asset.is_symlink() or not asset.is_dir():
            raise AssetRepositoryError("ASSET_NOT_FOUND", "The V2 asset does not exist")
        thumbnails = asset / THUMBNAILS_DIRECTORY
        target = thumbnails / f"page_{page}.png"
        for component in (thumbnails, target):
            if component.is_symlink():
                raise AssetRepositoryError(
                    "UNSAFE_ASSET_PATH",
                    "Symlinked asset files are not allowed",
                )
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(root)
        except FileNotFoundError as exc:
            raise AssetRepositoryError(
                "THUMBNAIL_NOT_FOUND",
                "The requested asset thumbnail does not exist",
            ) from exc
        except (OSError, ValueError) as exc:
            raise AssetRepositoryError(
                "UNSAFE_ASSET_PATH",
                "The thumbnail resolves outside the V2 job",
            ) from exc
        if not resolved.is_file():
            raise AssetRepositoryError(
                "THUMBNAIL_NOT_FOUND",
                "The requested asset thumbnail does not exist",
            )
        return resolved

    def cleanup(self, job_id: object, path: Path | None) -> None:
        if path is None or not path.exists():
            return
        root = self.assets_root(job_id)
        self._assert_direct_child(root, path)
        if path.is_symlink():
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "Refusing to clean a symlinked asset path",
            )
        try:
            shutil.rmtree(path)
        except OSError as exc:
            raise AssetRepositoryError(
                "PERSISTENCE_ERROR",
                "An incomplete asset could not be cleaned up",
            ) from exc

    @staticmethod
    def _assert_direct_child(root: Path, candidate: Path) -> None:
        try:
            parent = candidate.parent.resolve(strict=True)
        except OSError as exc:
            raise AssetRepositoryError(
                "UNSAFE_ASSET_PATH",
                "The asset parent path cannot be resolved safely",
            ) from exc
        if parent != root:
            raise AssetRepositoryError(
                "UNSAFE_ASSET_PATH",
                "The asset path must remain directly beneath the job asset root",
            )


__all__ = [
    "ASSET_ID_PATTERN",
    "METADATA_FILENAME",
    "SOURCE_FILENAME",
    "THUMBNAILS_DIRECTORY",
    "AssetRepository",
    "AssetRepositoryError",
    "StoredUpload",
    "validate_asset_id",
]
