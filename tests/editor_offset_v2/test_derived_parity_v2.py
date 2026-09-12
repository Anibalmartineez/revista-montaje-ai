from __future__ import annotations

import copy
import io
from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageChops, ImageStat
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import (
    EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED,
    EDITOR_OFFSET_V2_PDF_FINAL_ENABLED,
    EDITOR_OFFSET_V2_PREVIEW_ENABLED,
)
from editor_offset_v2.domain.output_parity_contract import (
    DERIVED_PREVIEW_MAX_CHANGED_RATIO,
    DERIVED_PREVIEW_MAX_MEAN_CHANNEL_DELTA,
    PREVIEW_PDF_MAX_CHANGED_RATIO,
    PREVIEW_PDF_MAX_MEAN_CHANNEL_DELTA,
)
from test_preview_v2 import _preview_layout, _save_preview_layout, create_job


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "marks-clipping.pdf"


@pytest.fixture
def parity_app_factory(tmp_path: Path):
    def create() -> Flask:
        app = Flask(
            __name__,
            template_folder=str(REPO_ROOT / "templates"),
            static_folder=str(REPO_ROOT / "static"),
            instance_path=str(tmp_path / "instance"),
        )
        app.config.update(
            TESTING=True,
            EDITOR_OFFSET_V2_ENABLED=True,
            EDITOR_OFFSET_V2_PREVIEW_ENABLED=True,
            EDITOR_OFFSET_V2_PDF_FINAL_ENABLED=True,
            EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED=True,
            EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
        )
        init_editor_offset_v2(app)
        return app

    return create


def _upload_fixture(client, created: dict) -> dict:
    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(FIXTURE.read_bytes()), "marks-clipping.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _transform() -> dict:
    return {
        "fit_mode": "actual_size",
        "scale_x": 0.82,
        "scale_y": 1.08,
        "offset_mm": {"x": 3.0, "y": -2.0},
        "rotation_deg": 90,
        "mirror_x": True,
        "mirror_y": False,
        "clip_to": "trim_box",
    }


def _image_difference(left: Image.Image, right: Image.Image) -> tuple[float, float]:
    width = min(left.width, right.width)
    height = min(left.height, right.height)
    left = left.crop((0, 0, width, height)).convert("RGB")
    right = right.crop((0, 0, width, height)).convert("RGB")
    difference = ImageChops.difference(left, right)
    total = width * height
    changed = sum(1 for pixel in difference.getdata() if max(pixel) > 12)
    mean = sum(ImageStat.Stat(difference).mean) / 3
    return changed / max(1, total), mean


def test_transformed_derived_preview_and_pdf_share_one_representation(parity_app_factory):
    """A baked transform must not be applied a second time by Preview/PDF."""
    app = parity_app_factory()
    client = app.test_client()
    created = create_job(client, "Derived parity V2")
    uploaded = _upload_fixture(client, created)
    asset = uploaded["asset"]
    layout = _preview_layout(uploaded["layout"], asset)
    trim = asset["pages"][0]["boxes_mm"]["trim"]
    assert trim is not None
    layout["sheet"]["size_mm"] = {"width": 200.0, "height": 120.0}
    layout["sheet"]["printable_margins_mm"] = {
        "left": 0.0,
        "right": 0.0,
        "bottom": 0.0,
        "top": 0.0,
    }
    layout["works"][0]["trim_size_mm"] = {
        "width": trim["width"],
        "height": trim["height"],
    }
    layout["slots"][0]["geometry"].update(
        position_mm={"anchor": "trim_center", "x_mm": 100.0, "y_mm": 60.0},
        trim_size_mm={"width": trim["width"], "height": trim["height"]},
        bleed_mm=0.0,
    )
    transform = _transform()
    layout["slots"][0]["content_transform"] = copy.deepcopy(transform)
    saved = _save_preview_layout(client, uploaded, layout)

    derived_response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets/{asset['id']}/derived-page",
        json={"page": 1, "pdf_box": "trim", "content_transform": transform},
    )
    assert derived_response.status_code == 201, derived_response.get_json()
    derived = derived_response.get_json()["result"]

    linked_layout = copy.deepcopy(layout)
    linked_layout["job"]["revision"] = saved["revision"]
    slot = linked_layout["slots"][0]
    slot["source"]["derived"] = {
        "derived_key": derived["derived_key"],
        "derived_sha256": derived["sha256"],
        "source_sha256": asset["sha256"],
    }
    slot["content_transform"] = {
        **copy.deepcopy(transform),
        "fit_mode": "actual_size",
        "scale_x": 1.0,
        "scale_y": 1.0,
        "offset_mm": {"x": 0.0, "y": 0.0},
        "rotation_deg": 0,
        "mirror_x": False,
        "mirror_y": False,
    }
    linked = _save_preview_layout(client, saved, linked_layout)

    preview_response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": "front", "dpi": 36},
    )
    assert preview_response.status_code == 200, preview_response.get_json()
    with Image.open(io.BytesIO(preview_response.data)) as preview_file:
        preview_image = preview_file.convert("RGB")
    preview_response.close()

    output_response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",
        json={"face": "front", "dpi": 36},
    )
    assert output_response.status_code == 200, output_response.get_json()
    with fitz.open(stream=output_response.data, filetype="pdf") as output:
        pdf_pixmap = output[0].get_pixmap(dpi=36, colorspace=fitz.csRGB, alpha=False)
        pdf_image = Image.frombytes("RGB", (pdf_pixmap.width, pdf_pixmap.height), pdf_pixmap.samples)

    full_ratio, full_mean = _image_difference(preview_image, pdf_image)
    assert full_ratio <= PREVIEW_PDF_MAX_CHANGED_RATIO
    assert full_mean <= PREVIEW_PDF_MAX_MEAN_CHANNEL_DELTA

    with fitz.open(
        app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]
        + f"/{created['job_id']}/{derived['derived_key']}"
    ) as derived_document:
        derived_pixmap = derived_document[0].get_pixmap(dpi=36, colorspace=fitz.csRGB, alpha=False)
        derived_image = Image.frombytes(
            "RGB", (derived_pixmap.width, derived_pixmap.height), derived_pixmap.samples
        )
    sheet_scale = 36 / 25.4
    center_x = round(100.0 * sheet_scale)
    center_y = round((120.0 - 60.0) * sheet_scale)
    left = center_x - derived_image.width // 2
    top = center_y - derived_image.height // 2
    preview_crop = preview_image.crop((left, top, left + derived_image.width, top + derived_image.height))
    crop_ratio, crop_mean = _image_difference(preview_crop, derived_image)
    assert crop_ratio <= DERIVED_PREVIEW_MAX_CHANGED_RATIO
    assert crop_mean <= DERIVED_PREVIEW_MAX_MEAN_CHANNEL_DELTA
    assert linked["revision"] == saved["revision"] + 1
