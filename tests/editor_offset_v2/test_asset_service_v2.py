from __future__ import annotations

import hashlib
import io
import json

import pytest
from werkzeug.datastructures import FileStorage

from editor_offset_v2.application.asset_service import (
    AssetService,
    AssetServiceError,
)
from editor_offset_v2.application.job_service import JobService, JobServiceError
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.asset_repository import AssetRepository
from editor_offset_v2.infrastructure.job_repository import JobRepository


JOB_ID = "ev2_abcdef0123456789abcdef01"
ASSET_A = "asset_111111111111111111111111"
ASSET_B = "asset_222222222222222222222222"
TIMESTAMP = "2026-07-19T12:00:00Z"


def uploaded_file(data: bytes, filename: str = "diseño.pdf", mime: str = "application/pdf"):
    return FileStorage(
        stream=io.BytesIO(data),
        filename=filename,
        content_type=mime,
    )


def make_services(tmp_path, *, ids=(ASSET_A, ASSET_B), max_bytes=2_000_000):
    repository = JobRepository(tmp_path / "jobs")
    job_service = JobService(
        repository,
        clock=lambda: TIMESTAMP,
        id_factory=lambda: JOB_ID,
    )
    job_service.create_job("Assets V2")
    id_values = iter(ids)
    asset_repository = AssetRepository(repository)
    asset_service = AssetService(
        job_service,
        asset_repository,
        max_upload_bytes=max_bytes,
        clock=lambda: TIMESTAMP,
        id_factory=lambda: next(id_values),
    )
    return job_service, asset_service, asset_repository


def test_upload_persists_immutable_source_metadata_hash_thumbnails_and_layout(
    tmp_path,
    pdf_bytes_factory,
):
    data = pdf_bytes_factory(page_sizes=((288, 144), (200, 100)), trim=True, bleed=True)
    job_service, service, repository = make_services(tmp_path)

    result = service.upload_pdf(JOB_ID, 1, uploaded_file(data, "Catálogo ñ.pdf"))

    assert result.asset_id == ASSET_A
    assert result.revision == 2
    assert result.asset["original_filename"] == "Catálogo ñ.pdf"
    assert result.asset["storage_key"] == f"assets/{ASSET_A}/source.pdf"
    assert result.asset["sha256"] == hashlib.sha256(data).hexdigest()
    assert result.asset["page_count"] == 2
    assert result.asset["status"] == "ready"
    assert result.asset["preflight_status"] == "not_run"
    assert result.asset["preflight_report_id"] is None
    assert validate_layout_v2(result.layout) == []
    assert job_service.get_job(JOB_ID).layout == result.layout

    asset_path = repository.asset_path(JOB_ID, ASSET_A)
    assert (asset_path / "source.pdf").read_bytes() == data
    assert (asset_path / "thumbnails" / "page_1.png").is_file()
    assert (asset_path / "thumbnails" / "page_2.png").is_file()
    metadata = json.loads((asset_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["asset"] == result.asset
    assert metadata["size_bytes"] == len(data)
    assert metadata["suggested_boxes"] == {"1": "trim", "2": "trim"}


def test_duplicate_unicode_filename_allocates_distinct_physical_assets(
    tmp_path,
    pdf_bytes_factory,
):
    data = pdf_bytes_factory()
    _, service, repository = make_services(tmp_path)

    first = service.upload_pdf(JOB_ID, 1, uploaded_file(data, "Único.pdf"))
    second = service.upload_pdf(JOB_ID, 2, uploaded_file(data, "Único.pdf"))

    assert first.asset_id == ASSET_A
    assert second.asset_id == ASSET_B
    assert repository.asset_path(JOB_ID, ASSET_A).is_dir()
    assert repository.asset_path(JOB_ID, ASSET_B).is_dir()
    assert first.asset["original_filename"] == second.asset["original_filename"]


@pytest.mark.parametrize(
    ("data", "max_bytes", "expected_code"),
    [
        (b"", 1000, "EMPTY_FILE"),
        (b"not-pdf", 1000, "INVALID_PDF_SIGNATURE"),
        (b"%PDF-corrupt", 1000, "INVALID_PDF"),
        (b"%PDF-" + b"x" * 50, 10, "FILE_TOO_LARGE"),
    ],
)
def test_invalid_uploads_are_controlled_and_cleaned(
    tmp_path,
    data,
    max_bytes,
    expected_code,
):
    _, service, repository = make_services(tmp_path, max_bytes=max_bytes)

    with pytest.raises((AssetServiceError,)) as caught:
        service.upload_pdf(JOB_ID, 1, uploaded_file(data))

    assert caught.value.code == expected_code
    assert list(repository.assets_root(JOB_ID).iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "mime", "expected_code"),
    [
        ("", "application/pdf", "INVALID_FILENAME"),
        ("image.png", "image/png", "UNSUPPORTED_FILE_TYPE"),
        ("fake.pdf", "image/png", "UNSUPPORTED_FILE_TYPE"),
    ],
)
def test_filename_extension_and_mime_are_validated_before_storage(
    tmp_path,
    filename,
    mime,
    expected_code,
):
    _, service, repository = make_services(tmp_path)

    with pytest.raises(AssetServiceError) as caught:
        service.upload_pdf(JOB_ID, 1, uploaded_file(b"%PDF-x", filename, mime))

    assert caught.value.code == expected_code
    assert list(repository.assets_root(JOB_ID).iterdir()) == []


def test_revision_conflict_and_missing_job_do_not_read_or_store_upload(
    tmp_path,
    pdf_bytes_factory,
):
    _, service, repository = make_services(tmp_path)
    data = pdf_bytes_factory()

    with pytest.raises(AssetServiceError) as conflict:
        service.upload_pdf(JOB_ID, 0, uploaded_file(data))
    assert conflict.value.code == "REVISION_CONFLICT"
    assert list(repository.assets_root(JOB_ID).iterdir()) == []

    with pytest.raises(JobServiceError) as missing:
        service.upload_pdf(
            "ev2_999999999999999999999999",
            1,
            uploaded_file(data),
        )
    assert missing.value.code == "JOB_NOT_FOUND"


def test_layout_failure_after_finalization_removes_invisible_asset(
    tmp_path,
    pdf_bytes_factory,
    monkeypatch,
):
    job_service, service, repository = make_services(tmp_path)

    def fail_save(*_args, **_kwargs):
        raise JobServiceError("PERSISTENCE_ERROR", "forced failure", 500)

    monkeypatch.setattr(job_service, "save_layout", fail_save)

    with pytest.raises(JobServiceError, match="forced failure"):
        service.upload_pdf(JOB_ID, 1, uploaded_file(pdf_bytes_factory()))

    assert list(repository.assets_root(JOB_ID).iterdir()) == []
    assert job_service.get_job(JOB_ID).layout["assets"] == []


def test_thumbnail_requires_asset_and_page_registered_in_layout(
    tmp_path,
    pdf_bytes_factory,
):
    _, service, _ = make_services(tmp_path)
    service.upload_pdf(JOB_ID, 1, uploaded_file(pdf_bytes_factory()))

    assert service.thumbnail_path(JOB_ID, ASSET_A, 1).name == "page_1.png"
    with pytest.raises(AssetServiceError) as missing_page:
        service.thumbnail_path(JOB_ID, ASSET_A, 2)
    assert missing_page.value.code == "THUMBNAIL_NOT_FOUND"
    with pytest.raises(AssetServiceError) as missing_asset:
        service.thumbnail_path(JOB_ID, ASSET_B, 1)
    assert missing_asset.value.code == "ASSET_NOT_FOUND"
