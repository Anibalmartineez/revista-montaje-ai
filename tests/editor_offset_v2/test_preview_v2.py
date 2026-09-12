from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import fitz
import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import EDITOR_OFFSET_V2_PREVIEW_ENABLED
from editor_offset_v2.infrastructure.pdf_inspector import POINT_TO_MM


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "layout_v2_complete.json"


@pytest.fixture
def preview_app_factory(tmp_path):
    def create(enabled: bool = True) -> Flask:
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
        )
        init_editor_offset_v2(app)
        return app

    return create


def create_job(client, name="Preview V2") -> dict:
    response = client.post("/api/editor-offset-v2/jobs", json={"name": name})
    assert response.status_code == 201
    return response.get_json()


def _source_pdf() -> bytes:
    points = 1 / POINT_TO_MM
    document = fitz.open()
    page = document.new_page(width=90 * points, height=50 * points)
    page.insert_text((18, 28), "PREVIEW-V2", fontsize=12, color=(0.1, 0.2, 0.8))
    document.xref_set_key(page.xref, "TrimBox", f"[0 0 {90 * points} {50 * points}]")
    data = document.tobytes(garbage=4, deflate=False, no_new_id=True)
    document.close()
    return data


def _asymmetric_parity_source_pdf() -> bytes:
    points = 1 / POINT_TO_MM
    width, height = 40 * points, 20 * points
    document = fitz.open()
    page = document.new_page(width=width, height=height)
    midpoint = width / 2
    page.draw_rect(fitz.Rect(0, 0, midpoint, height), color=(0.8, 0.05, 0.05), fill=(0.9, 0.1, 0.1), width=0.2)
    page.draw_rect(fitz.Rect(midpoint, 0, width, height), color=(0.05, 0.1, 0.8), fill=(0.1, 0.2, 0.9), width=0.2)
    document.xref_set_key(page.xref, "TrimBox", f"[0 0 {width} {height}]")
    data = document.tobytes(garbage=4, deflate=False, no_new_id=True)
    document.close()
    return data


def _preview_layout(base: dict, asset: dict) -> dict:
    complete = json.loads(COMPLETE_FIXTURE.read_text(encoding="utf-8"))
    layout = copy.deepcopy(base)
    work = copy.deepcopy(complete["works"][0])
    slot = copy.deepcopy(complete["slots"][0])
    work["id"] = "work_preview"
    work["front_source"] = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    work["back_source"] = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    slot["work_id"] = work["id"]
    slot["source"] = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    slot["geometry"]["bleed_mm"] = 0.0
    slot["content_transform"]["clip_to"] = "trim_box"
    layout["assets"] = [asset]
    layout["works"] = [work]
    layout["slots"] = [slot]
    layout["faces"] = {"enabled": ["front"], "duplex": {"enabled": False, "flip": "none"}}
    layout["export"]["faces"] = {
        "front": True,
        "back": False,
        "combine_in_single_pdf": False,
        "order": ["front"],
    }
    layout["export"]["marks_profiles"][0].update({
        "crop_marks": False,
        "registration_marks": False,
        "technical_text": False,
        "color_bar": False,
    })
    layout["ctp"]["enabled"] = False
    return layout


def _save_preview_layout(client, created: dict, layout: dict) -> dict:
    response = client.put(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
        json={"base_revision": created["revision"], "layout": layout},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_preview_endpoint_is_separately_gated_and_default_off(preview_app_factory):
    client = preview_app_factory().test_client()
    created = create_job(client)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PREVIEW_DISABLED"


def test_preview_request_rejects_non_object_and_invalid_face(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client)

    non_object = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json=[],
    )
    invalid_face = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": []},
    )

    assert non_object.status_code == 400
    assert non_object.get_json()["error"]["code"] == "INVALID_PREVIEW_REQUEST"
    assert invalid_face.status_code == 400
    assert invalid_face.get_json()["error"]["code"] == "INVALID_PREVIEW_FACE"


def test_gated_preview_renders_a_face_without_mutating_layout(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client)
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    saved = _save_preview_layout(client, upload.get_json(), layout)
    before = client.get(f"/api/editor-offset-v2/jobs/{created['job_id']}").get_json()

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": "front", "dpi": 36},
    )

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert response.content_length == len(response.data)
    assert client.get(f"/api/editor-offset-v2/jobs/{created['job_id']}").get_json() == before
    preview_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "previews"
    assert list(preview_dir.glob(f"preview_r{saved['revision']}_front_36.png"))


def test_preview_rejects_marks_and_supports_non_identity_internal_transforms(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client)
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    layout["export"]["marks_profiles"][0]["registration_marks"] = True
    saved = _save_preview_layout(client, upload.get_json(), layout)

    marked = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )
    assert marked.status_code == 422
    assert marked.get_json()["error"]["code"] == "PREVIEW_MARKS_UNSUPPORTED"

    layout["job"]["revision"] = saved["revision"]
    layout["export"]["marks_profiles"][0]["crop_marks"] = False
    layout["export"]["marks_profiles"][0]["registration_marks"] = False
    layout["slots"][0]["content_transform"]["offset_mm"]["x"] = 1.0
    updated = _save_preview_layout(client, saved, layout)
    transformed = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )
    assert updated["revision"] == saved["revision"] + 1
    assert transformed.status_code == 200
    assert transformed.mimetype == "image/png"


def test_preview_uses_a_verified_derived_source_reference(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    app.config["EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED"] = True
    client = app.test_client()
    created = create_job(client)
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "derived-preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    uploaded = upload.get_json()
    layout = _preview_layout(uploaded["layout"], uploaded["asset"])
    derived_response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets/{uploaded['asset_id']}/derived-page",
        json={"page": 1, "pdf_box": "trim", "bleed_mm": 3, "allow_mirror_bleed": True},
    )
    assert derived_response.status_code == 201
    derived = derived_response.get_json()["result"]
    layout["slots"][0]["source"]["derived"] = {
        "derived_key": derived["derived_key"],
        "derived_sha256": derived["sha256"],
        "source_sha256": uploaded["asset"]["sha256"],
    }
    layout["slots"][0]["geometry"]["bleed_mm"] = 3.0
    layout["slots"][0]["content_transform"]["clip_to"] = "bleed_box"
    saved = _save_preview_layout(client, uploaded, layout)
    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": "front", "dpi": 36},
    )
    assert saved["revision"] == uploaded["revision"] + 1
    assert response.status_code == 200
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_preview_raster_bounds_and_orientation_match_canvas_geometry(preview_app_factory):
    """The preview's visible artwork must occupy the saved slot footprint."""
    from PIL import Image

    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client, "Preview parity")
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_asymmetric_parity_source_pdf()), "parity.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    layout["sheet"]["size_mm"] = {"width": 120.0, "height": 80.0}
    layout["sheet"]["printable_margins_mm"] = {
        "left": 0.0,
        "right": 0.0,
        "bottom": 0.0,
        "top": 0.0,
    }
    layout["works"][0]["trim_size_mm"] = {"width": 40.0, "height": 20.0}
    layout["works"][0]["bleed_mm"] = 0.0
    slot = layout["slots"][0]
    slot["geometry"]["position_mm"] = {"anchor": "trim_center", "x_mm": 60.0, "y_mm": 40.0}
    slot["geometry"]["trim_size_mm"] = {"width": 40.0, "height": 20.0}
    slot["geometry"]["bleed_mm"] = 0.0
    saved = _save_preview_layout(client, upload.get_json(), layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": "front", "dpi": 36},
    )

    assert response.status_code == 200
    image = Image.open(io.BytesIO(response.data)).convert("RGB")
    expected_sheet_size = (round(120 * 36 / 25.4), round(80 * 36 / 25.4))
    assert all(abs(actual - expected) <= 1 for actual, expected in zip(image.size, expected_sheet_size))
    pixels = image.load()
    red = []
    blue = []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]
            if r > 170 and g < 130 and b < 130:
                red.append((x, y))
            if b > 170 and r < 130 and g < 150:
                blue.append((x, y))
    assert len(red) > 100
    assert len(blue) > 100

    scale_x = image.width / 120
    scale_y = image.height / 80
    expected = (
        round(40 * scale_x),
        round((80 - 50) * scale_y),
        round(80 * scale_x),
        round((80 - 30) * scale_y),
    )
    tolerance_px = 2
    for point in red + blue:
        assert expected[0] - tolerance_px <= point[0] <= expected[2] + tolerance_px
        assert expected[1] - tolerance_px <= point[1] <= expected[3] + tolerance_px
    assert sum(x for x, _ in red) / len(red) < sum(x for x, _ in blue) / len(blue)
    assert saved["revision"] == client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}"
    ).get_json()["revision"]


@pytest.mark.parametrize("fit_mode", ["contain", "cover", "stretch"])
def test_preview_supports_fit_modes_and_explicit_mirror_bleed(preview_app_factory, fit_mode):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client, f"Preview {fit_mode}")
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    slot = layout["slots"][0]
    slot["content_transform"].update(
        fit_mode=fit_mode,
        scale_x=0.8,
        scale_y=1.1,
        offset_mm={"x": 1.0, "y": -0.5},
        rotation_deg=90,
        mirror_x=True,
    )
    saved = _save_preview_layout(client, upload.get_json(), layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert saved["revision"] == client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}"
    ).get_json()["revision"]


def test_preview_requires_explicit_mirror_for_missing_source_bleed(preview_app_factory):
    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client, "Preview mirror bleed")
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "preview.pdf"),
        },
        content_type="multipart/form-data",
    )
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    layout["works"][0]["bleed_mm"] = 3.0
    layout["slots"][0]["geometry"]["bleed_mm"] = 3.0
    layout["slots"][0]["content_transform"]["clip_to"] = "bleed_box"
    _save_preview_layout(client, upload.get_json(), layout)

    blocked = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={},
    )
    assert blocked.status_code == 422
    assert blocked.get_json()["error"]["code"] == "BLEED_REQUIRES_EXPLICIT_MIRROR"

    mirrored = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"allow_mirror_bleed": True},
    )
    assert mirrored.status_code == 200
    assert mirrored.mimetype == "image/png"


def test_preview_draws_crop_marks_and_applies_back_long_edge_flip(preview_app_factory):
    from PIL import Image

    app = preview_app_factory()
    app.config[EDITOR_OFFSET_V2_PREVIEW_ENABLED] = True
    client = app.test_client()
    created = create_job(client, "Preview marks and duplex")
    upload = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_asymmetric_parity_source_pdf()), "parity.pdf"),
        },
        content_type="multipart/form-data",
    )
    asset = upload.get_json()["asset"]
    layout = _preview_layout(upload.get_json()["layout"], asset)
    layout["sheet"]["size_mm"] = {"width": 120.0, "height": 80.0}
    layout["sheet"]["printable_margins_mm"] = {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}
    layout["works"][0]["trim_size_mm"] = {"width": 40.0, "height": 20.0}
    slot = layout["slots"][0]
    slot["face"] = "back"
    slot["geometry"]["position_mm"] = {"anchor": "trim_center", "x_mm": 40.0, "y_mm": 40.0}
    slot["geometry"]["trim_size_mm"] = {"width": 40.0, "height": 20.0}
    layout["faces"] = {"enabled": ["back"], "duplex": {"enabled": True, "flip": "long_edge"}}
    layout["export"]["faces"] = {"front": False, "back": True, "combine_in_single_pdf": False, "order": ["back"]}
    layout["export"]["marks_profiles"][0]["crop_marks"] = True
    saved = _save_preview_layout(client, upload.get_json(), layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
        json={"face": "back", "dpi": 36},
    )
    assert response.status_code == 200
    image = Image.open(io.BytesIO(response.data)).convert("RGB")
    red, blue, black = [], [], []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = image.getpixel((x, y))
            if r > 170 and g < 130 and b < 130:
                red.append(x)
            if b > 170 and r < 130 and g < 150:
                blue.append(x)
            if r < 50 and g < 50 and b < 50:
                black.append((x, y))
    assert red and blue and black
    assert sum(red) / len(red) > sum(blue) / len(blue)
    assert saved["revision"] == client.get(
        f"/api/editor-offset-v2/jobs/{created['job_id']}"
    ).get_json()["revision"]
