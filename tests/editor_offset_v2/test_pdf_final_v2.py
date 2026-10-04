from __future__ import annotations

import copy
import io
from pathlib import Path

import fitz
import pytest
from flask import Flask

from editor_offset_v2.blueprint import init_editor_offset_v2
from editor_offset_v2.config import EDITOR_OFFSET_V2_PDF_FINAL_ENABLED
from test_preview_v2 import _preview_layout, _save_preview_layout, _source_pdf, create_job


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "layout_v2_complete.json"


def app_factory(tmp_path: Path, *, enabled: bool) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(REPO_ROOT / "templates"),
        static_folder=str(REPO_ROOT / "static"),
        instance_path=str(tmp_path / "instance"),
    )
    app.config.update(
        TESTING=True,
        EDITOR_OFFSET_V2_ENABLED=True,
        EDITOR_OFFSET_V2_PDF_FINAL_ENABLED=enabled,
        EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
    )
    init_editor_offset_v2(app)
    return app


def _ready_layout(base: dict, asset: dict) -> dict:
    layout = _preview_layout(base, asset)
    layout['export'].update(render_mode='vector_hybrid', preserve_vector_content=True)
    layout["export"]["marks_profiles"][0].update(
        crop_marks=False,
        registration_marks=False,
        technical_text=False,
        color_bar=False,
    )
    return layout


def _upload_source(client, created: dict) -> dict:
    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={
            "base_revision": str(created["revision"]),
            "file": (io.BytesIO(_source_pdf()), "source.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.get_json()


def test_pdf_final_is_separately_gated(tmp_path):
    app = app_factory(tmp_path, enabled=False)
    client = app.test_client()
    created = create_job(client)
    response = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final", json={})
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PDF_FINAL_DISABLED"


def test_gated_pdf_final_writes_one_sheet_page_with_physical_size(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, "PDF final V2")
    uploaded = _upload_source(client, created)
    layout = _ready_layout(uploaded["layout"], uploaded["asset"])
    saved = _save_preview_layout(client, uploaded, layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",
        json={"dpi": 36},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    with fitz.open(stream=response.data, filetype="pdf") as document:
        assert document.page_count == 1
        page = document[0]
        assert page.rect.width == pytest.approx(700 * 72 / 25.4, abs=0.01)
        assert page.rect.height == pytest.approx(500 * 72 / 25.4, abs=0.01)
        assert 'PREVIEW-V2' in page.get_text()
        assert not page.get_images(full=True)  # A vector source must remain vector.
    output_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "outputs"
    assert list(output_dir.glob(f"pdf_final_r{saved['revision']}_front_36_*.pdf"))


def test_pdf_final_regeneration_replaces_same_artifact_deterministically(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, "PDF regeneration V2")
    uploaded = _upload_source(client, created)
    saved = _save_preview_layout(client, uploaded, _ready_layout(uploaded["layout"], uploaded["asset"]))

    first = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final", json={"dpi": 36})
    first_data = first.data
    first.close()
    second = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final", json={"dpi": 36})

    assert first.status_code == second.status_code == 200
    assert first_data == second.data
    output_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "outputs"
    assert len(list(output_dir.glob(f"pdf_final_r{saved['revision']}_front_36_*.pdf"))) == 1
    assert not list(output_dir.glob(".pdf-final-*.tmp"))


def test_gated_pdf_final_combines_front_and_back_in_layout_order(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, "PDF duplex V2")
    uploaded = _upload_source(client, created)
    layout = _ready_layout(uploaded["layout"], uploaded["asset"])
    front = copy.deepcopy(layout["slots"][0])
    back = copy.deepcopy(front)
    back["id"] = "slot_back"
    back["face"] = "back"
    layout["slots"] = [front, back]
    layout["faces"] = {"enabled": ["front", "back"], "duplex": {"enabled": True, "flip": "long_edge"}}
    layout["export"]["faces"] = {
        "front": True,
        "back": True,
        "combine_in_single_pdf": True,
        "order": ["front", "back"],
    }
    saved = _save_preview_layout(client, uploaded, layout)

    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",
        json={"face": "both", "dpi": 36},
    )

    assert response.status_code == 200
    with fitz.open(stream=response.data, filetype="pdf") as document:
        assert document.page_count == 2
        assert all(page.rect.width == pytest.approx(700 * 72 / 25.4, abs=0.01) for page in document)
    output_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "outputs"
    assert list(output_dir.glob(f"pdf_final_r{saved['revision']}_both_36_*.pdf"))

def _two_page_asymmetric_pdf() -> bytes:
    points = 72 / 25.4
    document = fitz.open()
    for label, color in (("FRONT-ASYM", (0, 0, 1)), ("BACK-ASYM", (1, 0, 0))):
        page = document.new_page(width=90 * points, height=50 * points)
        page.draw_rect(fitz.Rect(10, 10, 35, 35), color=color, fill=color)
        page.insert_text((40, 25), label, fontsize=12, color=color)
        document.xref_set_key(page.xref, "TrimBox", f"[0 0 {90 * points} {50 * points}]")
    data = document.tobytes(garbage=4, deflate=False, no_new_id=True)
    document.close()
    return data


def _color_centroid(page, channel: str) -> tuple[float, float]:
    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5), alpha=False)
    samples = pix.samples
    xs, ys = [], []
    red = channel == "red"
    for y in range(pix.height):
        for x in range(pix.width):
            index = (y * pix.width + x) * pix.n
            r, g, b = samples[index:index + 3]
            if (r > 180 and g < 70 and b < 70) if red else (b > 180 and r < 70 and g < 100):
                xs.append(x)
                ys.append(y)
    assert xs, f"No {channel} artwork pixels found"
    return sum(xs) / len(xs) / pix.width, sum(ys) / len(ys) / pix.height


@pytest.mark.parametrize("flip", ["none", "long_edge", "short_edge"])
def test_duplex_pdf_has_distinct_physical_artwork_order_and_flip(tmp_path, flip):
    app = app_factory(tmp_path, enabled=True)
    client = app.test_client()
    created = create_job(client, f"Duplex {flip}")
    response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={"base_revision": str(created["revision"]),
              "file": (io.BytesIO(_two_page_asymmetric_pdf()), "two-pages.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    uploaded = response.get_json()
    layout = _ready_layout(uploaded["layout"], uploaded["asset"])
    front = copy.deepcopy(layout["slots"][0])
    back = copy.deepcopy(front)
    back["id"] = "slot_back_distinct"
    back["face"] = "back"
    back["source"]["page"] = 2
    layout["slots"] = [front, back]
    layout["faces"] = {"enabled": ["front", "back"], "duplex": {"enabled": True, "flip": flip}}
    layout["export"]["faces"] = {"front": True, "back": True, "combine_in_single_pdf": True,
                                   "order": ["back", "front"]}
    saved = _save_preview_layout(client, uploaded, layout)
    assert saved["layout"]["slots"][1]["source"]["page"] == 2
    stale = client.put(f"/api/editor-offset-v2/jobs/{created['job_id']}/layout",
                       json={"base_revision": uploaded["revision"], "layout": layout})
    assert stale.status_code == 409
    pdf = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",
                      json={"face": "both", "dpi": 36})
    assert pdf.status_code == 200, pdf.get_json() if pdf.is_json else ""
    with fitz.open(stream=pdf.data, filetype="pdf") as document:
        assert document.page_count == 2
        assert "BACK-ASYM" in document[0].get_text()
        assert "FRONT-ASYM" in document[1].get_text()
        for page in document:
            assert page.rect.width == pytest.approx(700 * 72 / 25.4, abs=0.01)
            assert page.rect.height == pytest.approx(500 * 72 / 25.4, abs=0.01)
        back_center = _color_centroid(document[0], "red")
        front_center = _color_centroid(document[1], "blue")
        if flip == "none":
            assert back_center[0] == pytest.approx(front_center[0], abs=0.005)
            assert back_center[1] == pytest.approx(front_center[1], abs=0.005)
        elif flip == "long_edge":
            assert back_center[0] == pytest.approx(1 - front_center[0], abs=0.005)
            assert back_center[1] == pytest.approx(front_center[1], abs=0.005)
        else:
            assert back_center[0] == pytest.approx(front_center[0], abs=0.005)
            assert back_center[1] == pytest.approx(1 - front_center[1], abs=0.005)


def test_duplex_preview_each_face_and_back_only_preflight_issue(tmp_path):
    from PIL import Image
    app = app_factory(tmp_path, enabled=True)
    app.config["EDITOR_OFFSET_V2_PREVIEW_ENABLED"] = True
    client = app.test_client()
    created = create_job(client, "Duplex preview")
    uploaded_response = client.post(
        f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",
        data={"base_revision": str(created["revision"]),
              "file": (io.BytesIO(_two_page_asymmetric_pdf()), "two-pages.pdf")},
        content_type="multipart/form-data",
    )
    assert uploaded_response.status_code == 201
    uploaded = uploaded_response.get_json()
    layout = _ready_layout(uploaded["layout"], uploaded["asset"])
    front = copy.deepcopy(layout["slots"][0])
    back = copy.deepcopy(front)
    back["id"] = "slot_back_preview"
    back["face"] = "back"
    back["source"]["page"] = 2
    back["geometry"]["position_mm"]["x_mm"] += 20
    layout["slots"] = [front, back]
    layout["faces"] = {"enabled": ["front", "back"], "duplex": {"enabled": True, "flip": "none"}}
    layout["export"]["faces"] = {"front": True, "back": True, "combine_in_single_pdf": True,
                                   "order": ["front", "back"]}
    saved = _save_preview_layout(client, uploaded, layout)
    previews = {}
    for face in ("front", "back"):
        response = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/preview",
                               json={"face": face, "dpi": 36})
        assert response.status_code == 200
        image = Image.open(io.BytesIO(response.data)).convert("RGB")
        assert image.width > 0 and image.height > 0
        previews[face] = response.data
        preview_dir = Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) / created["job_id"] / "previews"
        assert list(preview_dir.glob(f"preview_r{saved['revision']}_{face}_36_*.png"))
    assert previews["front"] != previews["back"]
    changed = copy.deepcopy(saved["layout"])
    changed["slots"][1]["geometry"]["position_mm"]["x_mm"] = 900
    changed_saved = _save_preview_layout(client, saved, changed)
    report_response = client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/preflight",
                                  json={"face": "front", "dpi": 36})
    assert report_response.status_code == 201
    report = report_response.get_json()["report"]
    back_issues = [issue for issue in report["issues"]
                   if "back" in issue["references"].get("faces", [])
                   and "front" not in issue["references"].get("faces", [])]
    assert back_issues
    assert any("slot_back_preview" in issue["references"].get("slot_ids", []) for issue in back_issues)
    assert changed_saved["revision"] == report["subject"]["revision"]
    assert any(decision["status"] == "blocked" for decision in report["decisions"]
               if decision["operation"] in ("preview", "pdf_final"))
