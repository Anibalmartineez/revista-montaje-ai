from __future__ import annotations

import copy
import io
from pathlib import Path

import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import (
    EDITOR_OFFSET_V2_JOBS_ROOT,
    EDITOR_OFFSET_V2_MAX_UPLOAD_BYTES,
)
from editor_offset_v2.domain.validation import validate_layout_v2


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def assets_app_factory(tmp_path):
    def create(*, enabled=True, max_bytes=2_000_000):
        app = Flask(
            __name__,
            template_folder=str(REPO_ROOT / "templates"),
            static_folder=str(REPO_ROOT / "static"),
            instance_path=str(tmp_path / "instance"),
        )
        app.config.update(
            TESTING=True,
            EDITOR_OFFSET_V2_ENABLED=enabled,
            EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
            EDITOR_OFFSET_V2_MAX_UPLOAD_BYTES=max_bytes,
        )
        init_editor_offset_v2(app)
        return app

    return create


def create_job(client):
    response = client.post("/api/editor-offset-v2/jobs", json={})
    assert response.status_code == 201
    return response.get_json()


def upload(client, job_id, data, *, revision=1, filename="diseño.pdf", mime="application/pdf"):
    return client.post(
        f"/api/editor-offset-v2/jobs/{job_id}/assets",
        data={
            "base_revision": str(revision),
            "file": (io.BytesIO(data), filename, mime),
        },
        content_type="multipart/form-data",
    )


def test_valid_upload_increments_revision_persists_layout_and_serves_thumbnail(
    assets_app_factory,
    pdf_bytes_factory,
):
    app = assets_app_factory()
    client = app.test_client()
    created = create_job(client)
    data = pdf_bytes_factory(page_sizes=((288, 144), (200, 100)), trim=True)

    response = upload(client, created["job_id"], data)
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["revision"] == 2
    assert payload["asset_id"].startswith("asset_")
    assert len(payload["asset_id"]) == 30
    assert validate_layout_v2(payload["layout"]) == []
    assert payload["layout"]["assets"] == [payload["asset"]]
    asset_id = payload["asset_id"]
    asset_root = (
        Path(app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
        / created["job_id"]
        / "assets"
        / asset_id
    )
    assert (asset_root / "source.pdf").read_bytes() == data
    assert (asset_root / "metadata.json").is_file()

    thumbnail = client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets/{asset_id}/thumbnails/1"
    )
    assert thumbnail.status_code == 200
    assert thumbnail.mimetype == "image/png"
    assert thumbnail.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_duplicate_filename_creates_distinct_assets(assets_app_factory, pdf_bytes_factory):
    client = assets_app_factory().test_client()
    created = create_job(client)
    data = pdf_bytes_factory()

    first = upload(client, created["job_id"], data, filename="igual.pdf")
    second = upload(
        client,
        created["job_id"],
        data,
        revision=2,
        filename="igual.pdf",
    )

    assert first.status_code == second.status_code == 201
    assert first.get_json()["asset_id"] != second.get_json()["asset_id"]
    assert len(second.get_json()["layout"]["assets"]) == 2


@pytest.mark.parametrize(
    ("data", "filename", "expected_status", "expected_code"),
    [
        (b"", "empty.pdf", 400, "EMPTY_FILE"),
        (b"not-pdf", "fake.pdf", 400, "INVALID_PDF_SIGNATURE"),
        (b"%PDF-corrupt", "corrupt.pdf", 400, "INVALID_PDF"),
        (b"%PDF-test", "image.png", 415, "UNSUPPORTED_FILE_TYPE"),
    ],
)
def test_invalid_upload_errors_are_structured_and_leave_layout_unchanged(
    assets_app_factory,
    data,
    filename,
    expected_status,
    expected_code,
):
    client = assets_app_factory().test_client()
    created = create_job(client)

    response = upload(client, created["job_id"], data, filename=filename)
    loaded = client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}"
    ).get_json()

    assert response.status_code == expected_status
    assert response.get_json()["error"]["code"] == expected_code
    assert loaded["revision"] == 1
    assert loaded["layout"]["assets"] == []


def test_oversized_file_is_413_and_cleaned(assets_app_factory):
    app = assets_app_factory(max_bytes=10)
    client = app.test_client()
    created = create_job(client)

    response = upload(client, created["job_id"], b"%PDF-" + b"x" * 100)

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "FILE_TOO_LARGE"
    assets_root = (
        Path(app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
        / created["job_id"]
        / "assets"
    )
    assert list(assets_root.iterdir()) == []


def test_feature_flag_missing_job_and_revision_conflict_are_controlled(
    assets_app_factory,
    pdf_bytes_factory,
):
    data = pdf_bytes_factory()
    disabled = assets_app_factory(enabled=False).test_client()
    disabled_response = upload(
        disabled,
        "ev2_aaaaaaaaaaaaaaaaaaaaaaaa",
        data,
    )
    assert disabled_response.status_code == 404
    assert disabled_response.get_json()["error"]["code"] == "V2_DISABLED"

    client = assets_app_factory().test_client()
    created = create_job(client)
    missing = upload(client, "ev2_999999999999999999999999", data)
    conflict = upload(client, created["job_id"], data, revision=0)
    assert (missing.status_code, missing.get_json()["error"]["code"]) == (
        404,
        "JOB_NOT_FOUND",
    )
    assert (conflict.status_code, conflict.get_json()["error"]["code"]) == (
        409,
        "REVISION_CONFLICT",
    )


def test_thumbnail_rejects_invalid_ids_pages_traversal_and_missing_files(
    assets_app_factory,
    pdf_bytes_factory,
):
    app = assets_app_factory()
    client = app.test_client()
    created = create_job(client)
    uploaded = upload(client, created["job_id"], pdf_bytes_factory()).get_json()
    base = f"/api/editor-offset-v2/jobs/{created['job_id']}/assets"

    invalid_id = client.get(f"{base}/not-an-asset/thumbnails/1")
    traversal = client.get(f"{base}/..%5Coutside/thumbnails/1")
    missing_page = client.get(f"{base}/{uploaded['asset_id']}/thumbnails/2")
    missing_file_path = (
        Path(app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
        / created["job_id"]
        / "assets"
        / uploaded["asset_id"]
        / "thumbnails"
        / "page_1.png"
    )
    missing_file_path.unlink()
    missing_file = client.get(f"{base}/{uploaded['asset_id']}/thumbnails/1")

    assert invalid_id.status_code == 400
    assert invalid_id.get_json()["error"]["code"] == "INVALID_ASSET_ID"
    assert traversal.status_code == 400
    assert traversal.get_json()["error"]["code"] == "INVALID_ASSET_ID"
    assert missing_page.status_code == 404
    assert missing_page.get_json()["error"]["code"] == "THUMBNAIL_NOT_FOUND"
    assert missing_file.status_code == 404
    assert missing_file.get_json()["error"]["code"] == "THUMBNAIL_NOT_FOUND"


def test_thumbnail_rejects_layout_storage_key_outside_job(
    assets_app_factory,
    pdf_bytes_factory,
):
    client = assets_app_factory().test_client()
    created = create_job(client)
    uploaded = upload(client, created["job_id"], pdf_bytes_factory()).get_json()
    layout = copy.deepcopy(uploaded["layout"])
    layout["assets"][0]["storage_key"] = "../outside.pdf"
    saved = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": 2, "layout": layout},
    )
    assert saved.status_code == 200

    response = client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets/"
        f"{uploaded['asset_id']}/thumbnails/1"
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "UNSAFE_ASSET_PATH"


def test_thumbnail_rejects_symlinked_file(
    assets_app_factory,
    pdf_bytes_factory,
    tmp_path,
):
    app = assets_app_factory()
    client = app.test_client()
    created = create_job(client)
    uploaded = upload(client, created["job_id"], pdf_bytes_factory()).get_json()
    thumbnail = (
        Path(app.config[EDITOR_OFFSET_V2_JOBS_ROOT])
        / created["job_id"]
        / "assets"
        / uploaded["asset_id"]
        / "thumbnails"
        / "page_1.png"
    )
    outside = tmp_path / "outside.png"
    outside.write_bytes(thumbnail.read_bytes())
    thumbnail.unlink()
    try:
        thumbnail.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"The platform cannot create test symlinks: {exc}")

    response = client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets/"
        f"{uploaded['asset_id']}/thumbnails/1"
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "UNSAFE_ASSET_PATH"
