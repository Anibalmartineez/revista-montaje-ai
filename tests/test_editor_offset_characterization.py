import io
import json
import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

sys.path.append(str(Path(__file__).resolve().parents[1]))

import montaje_offset_inteligente
from ai_agent.tools_repeat import generar_repeat
from app import app
from engines.step_repeat_pro_engine import build_step_repeat_slots
from routes import (
    _constructor_job_dir,
    _load_constructor_layout,
    _save_constructor_layout,
)
from services.editor_offset_output_service import montar_offset_desde_layout as montar_constructor_layout


@pytest.fixture()
def work_dir(request):
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)
    path = Path("tests") / "_tmp_editor_offset_characterization" / safe_name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    yield path
    if path.exists():
        shutil.rmtree(path)


@pytest.fixture()
def editor_app(work_dir, monkeypatch):
    static_root = work_dir / "static"
    static_root.mkdir()
    monkeypatch.setattr(app, "static_folder", str(static_root))
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(editor_app):
    with editor_app.test_client() as test_client:
        yield test_client


def _pdf_bytes(width_mm=40, height_mm=20):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width_mm * mm, height_mm * mm))
    c.rect(2 * mm, 2 * mm, max(1, width_mm - 4) * mm, max(1, height_mm - 4) * mm)
    c.drawString(5 * mm, 5 * mm, "editor")
    c.save()
    buffer.seek(0)
    return buffer


def _repeat_layout(*, face="front"):
    return {
        "sheet_mm": [200, 160],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 0,
        "gap_default_mm": 5,
        "works": [],
        "slots": [],
        "designs": [
            {
                "ref": "file0",
                "filename": "pieza.pdf",
                "width_mm": 30,
                "height_mm": 20,
                "bleed_mm": 0,
                "allow_rotation": False,
                "forms_per_plate": 3,
                "priority": 100,
                "preferred_zone": "auto",
                "preferred_flow": "auto",
                "repeat_role": "secondary",
                "repeat_manual_overrides": {
                    "priority": False,
                    "preferred_flow": False,
                    "repeat_role": True,
                },
            }
        ],
        "faces": [face],
        "active_face": face,
        "imposition_engine": "repeat",
        "allowed_engines": ["repeat", "nesting", "hybrid"],
        "spacingSettings": {"spacingX_mm": 7, "spacingY_mm": 11, "live": True},
        "export_settings": {"bleed_mm": 0, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
    }


def test_editor_offset_save_persists_constructor_defaults(client, editor_app):
    job_id = "charsave"
    layout = {"sheet_mm": [300, 400], "margins_mm": [10, 10, 10, 10]}

    response = client.post(
        "/editor_offset/save",
        data={"job_id": job_id, "layout_json": json.dumps(layout)},
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    with editor_app.app_context():
        stored = _load_constructor_layout(_constructor_job_dir(job_id))
    assert stored["faces"] == ["front"]
    assert stored["active_face"] == "front"
    assert stored["imposition_engine"] == "repeat"
    assert stored["allowed_engines"] == ["repeat", "nesting", "hybrid"]
    assert stored["export_settings"]["crop_marks"] is True
    assert stored["export_settings"]["output_mode"] == "raster"


def test_editor_offset_upload_appends_design_from_work_contract(client, editor_app):
    job_id = "charupload"
    initial_layout = {
        "sheet_mm": [300, 400],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 3,
        "works": [
            {
                "id": "work0",
                "name": "Trabajo",
                "final_size_mm": [50, 30],
                "forms_per_plate": 4,
                "default_bleed_mm": 2,
                "allow_rotation": False,
                "has_bleed": False,
            }
        ],
        "designs": [],
        "slots": [],
    }
    with editor_app.app_context():
        _save_constructor_layout(_constructor_job_dir(job_id), deepcopy(initial_layout))

    response = client.post(
        f"/editor_offset/upload/{job_id}",
        data={
            "work_id": "work0",
            "files": (_pdf_bytes(), "pieza.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert len(data["designs"]) == 1
    design = data["designs"][0]
    assert design["ref"] == "file0"
    assert design["work_id"] == "work0"
    assert design["forms_per_plate"] == 4
    assert design["allow_rotation"] is False
    assert design["width_mm"] == pytest.approx(54)
    assert design["height_mm"] == pytest.approx(34)
    assert design["bleed_mm"] == pytest.approx(2)


def test_apply_imposition_endpoint_generates_and_persists_repeat_slots(client, editor_app):
    job_id = "charrepeat"
    layout = _repeat_layout(face="back")
    with editor_app.app_context():
        _save_constructor_layout(_constructor_job_dir(job_id), deepcopy(layout))

    response = client.post(
        "/editor_offset_visual/apply_imposition",
        data={
            "job_id": job_id,
            "selected_engine": "repeat",
            "layout_json": json.dumps(layout),
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    slots = data["layout"]["slots"]
    assert len(slots) == 3
    assert {slot["design_ref"] for slot in slots} == {"file0"}
    assert {slot["face"] for slot in slots} == {"back"}
    assert slots[1]["x_mm"] - (slots[0]["x_mm"] + slots[0]["w_mm"]) == pytest.approx(7)
    for slot in slots:
        assert {
            "id",
            "design_ref",
            "x_mm",
            "y_mm",
            "w_mm",
            "h_mm",
            "bleed_mm",
            "rotation_deg",
            "face",
        } <= set(slot)

    with editor_app.app_context():
        persisted = _load_constructor_layout(_constructor_job_dir(job_id))
    assert persisted["slots"] == slots


@pytest.mark.parametrize(
    "endpoint,error_text",
    [
        ("/editor_offset/preview/{job_id}", "preview"),
        ("/editor_offset/generar_pdf/{job_id}", "PDF final"),
    ],
)
def test_preview_and_pdf_endpoints_block_invalid_layout_contract(
    client, editor_app, endpoint, error_text
):
    job_id = f"charinvalid{error_text.split()[0].lower()}"
    layout = _repeat_layout()
    layout["slots"] = [
        {
            "id": "slot0",
            "x_mm": 10,
            "y_mm": 10,
            "w_mm": 30,
            "h_mm": 20,
            "bleed_mm": 0,
            "rotation_deg": 0,
            "design_ref": "missing",
            "face": "front",
        }
    ]
    with editor_app.app_context():
        _save_constructor_layout(_constructor_job_dir(job_id), layout)

    response = client.post(endpoint.format(job_id=job_id))
    data = response.get_json()

    assert response.status_code == 422
    assert data["ok"] is False
    assert error_text in data["error"]
    assert any(issue["code"] == "slot_design_ref_invalid" for issue in data["errors"])


def test_repeat_ai_tool_matches_canonical_engine_and_marks_change_type():
    layout = _repeat_layout()

    generated = generar_repeat(layout, {})
    engine_slots = build_step_repeat_slots(layout)

    assert generated["imposition_engine"] == "repeat"
    assert generated["slots"] == engine_slots
    assert generated["ai_agent"]["layout_change_type"] == "layout_with_slots"
    assert generated["ai_agent"]["last_repeat_slot_count"] == len(engine_slots)


def test_repeat_ai_tool_does_not_depend_on_routes_wrapper(monkeypatch):
    layout = _repeat_layout()

    def fail_if_routes_wrapper_is_used(_layout):
        raise AssertionError("generar_repeat no debe depender de routes._build_step_repeat_slots")

    monkeypatch.setattr("routes._build_step_repeat_slots", fail_if_routes_wrapper_is_used)

    generated = generar_repeat(layout, {})

    assert generated["slots"] == build_step_repeat_slots(layout)


def test_montar_offset_desde_layout_splits_front_back_and_applies_ctp_pinza(
    work_dir, monkeypatch
):
    job_dir = work_dir / "job"
    job_dir.mkdir()
    pdf_path = job_dir / "pieza.pdf"
    pdf_path.write_bytes(_pdf_bytes().getvalue())
    captured = []

    def fake_realizar_montaje(disenos, config):
        captured.append(config)
        out = Path(config.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(out), pagesize=(config.tamano_pliego[0] * mm, config.tamano_pliego[1] * mm))
        c.drawString(10, 10, "ok")
        c.save()
        return str(out)

    monkeypatch.setattr(montaje_offset_inteligente, "realizar_montaje_inteligente", fake_realizar_montaje)

    layout = {
        "sheet_mm": [200, 160],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 0,
        "gap_default_mm": 5,
        "designs": [{"ref": "file0", "filename": "pieza.pdf", "forms_per_plate": 1}],
        "works": [],
        "faces": ["front", "back"],
        "active_face": "front",
        "imposition_engine": "repeat",
        "export_settings": {"bleed_mm": 0, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
        "ctp": {"enabled": True, "gripper_mm": 42, "show_guide": True, "lock_after": True},
        "slots": [
            {
                "id": "front0",
                "design_ref": "file0",
                "x_mm": 10,
                "y_mm": 20,
                "w_mm": 40,
                "h_mm": 20,
                "bleed_mm": 0,
                "rotation_deg": 0,
                "face": "front",
                "crop_marks": True,
            },
            {
                "id": "back0",
                "design_ref": "file0",
                "x_mm": 12,
                "y_mm": 22,
                "w_mm": 40,
                "h_mm": 20,
                "bleed_mm": 0,
                "rotation_deg": 180,
                "face": "back",
                "crop_marks": True,
            },
        ],
    }

    output = montaje_offset_inteligente.montar_offset_desde_layout(layout, str(job_dir), preview=False)

    assert Path(output).exists()
    assert len(captured) == 2
    assert [Path(config.output_path).name for config in captured] == ["montaje_front.pdf", "montaje_back.pdf"]
    assert all(config.pinza_mm == 42 for config in captured)
    assert all(config.ctp_config == layout["ctp"] for config in captured)
    assert captured[0].posiciones_manual[0]["rot_deg"] == 0
    assert captured[1].posiciones_manual[0]["rot_deg"] == 180


def test_repeat_manual_rotation_preserves_source_aspect_in_output_positions(work_dir):
    job_dir = work_dir / "job_manual_rotation"
    job_dir.mkdir()
    pdf_path = job_dir / "pieza.pdf"
    pdf_path.write_bytes(_pdf_bytes(width_mm=210.058, height_mm=297.18).getvalue())
    captured = []

    def fake_render(_disenos, config):
        captured.append(config)
        out = Path(config.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"%PDF-1.4\n%%EOF\n")
        return str(out)

    layout = {
        "sheet_mm": [640, 880],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 3,
        "gap_default_mm": 5,
        "designs": [
            {
                "ref": "file0",
                "filename": "pieza.pdf",
                "width_mm": 210.058,
                "height_mm": 297.18,
                "bleed_mm": 3,
                "forms_per_plate": 1,
            }
        ],
        "works": [],
        "faces": ["front"],
        "active_face": "front",
        "imposition_engine": "repeat",
        "export_settings": {"bleed_mm": 3, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
        "slots": [
            {
                "id": "sr_1",
                "design_ref": "file0",
                "x_mm": 315,
                "y_mm": 125,
                "w_mm": 216.058,
                "h_mm": 303.18,
                "bleed_mm": 3,
                "rotation_deg": 90,
                "face": "front",
                "crop_marks": True,
            }
        ],
    }

    montar_constructor_layout(
        layout,
        str(job_dir),
        preview=False,
        diseno_cls=montaje_offset_inteligente.Diseno,
        config_cls=montaje_offset_inteligente.MontajeConfig,
        render_fn=fake_render,
    )

    pos = captured[0].posiciones_manual[0]
    assert pos["slot_box_final"] is False
    assert pos["rot_deg"] == 90
    assert pos["source_w_mm"] == pytest.approx(210.058)
    assert pos["source_h_mm"] == pytest.approx(297.18)
    assert pos["w_mm"] == pytest.approx(297.18)
    assert pos["h_mm"] == pytest.approx(210.058)
    assert pos["x_mm"] == pytest.approx(315 + 216.058 / 2 - 303.18 / 2)
    assert pos["y_mm"] == pytest.approx(125 + 303.18 / 2 - 216.058 / 2)


def test_repeat_auto_rotated_slot_keeps_final_footprint_semantics(work_dir):
    job_dir = work_dir / "job_auto_rotation"
    job_dir.mkdir()
    pdf_path = job_dir / "pieza.pdf"
    pdf_path.write_bytes(_pdf_bytes(width_mm=70, height_mm=20).getvalue())
    captured = []

    def fake_render(_disenos, config):
        captured.append(config)
        out = Path(config.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"%PDF-1.4\n%%EOF\n")
        return str(out)

    layout = {
        "sheet_mm": [120, 95],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 0,
        "gap_default_mm": 2,
        "designs": [
            {
                "ref": "file0",
                "filename": "pieza.pdf",
                "width_mm": 70,
                "height_mm": 20,
                "bleed_mm": 0,
                "forms_per_plate": 1,
            }
        ],
        "works": [],
        "faces": ["front"],
        "active_face": "front",
        "imposition_engine": "repeat",
        "export_settings": {"bleed_mm": 0, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
        "slots": [
            {
                "id": "sr_0",
                "design_ref": "file0",
                "x_mm": 10,
                "y_mm": 10,
                "w_mm": 20,
                "h_mm": 70,
                "bleed_mm": 0,
                "rotation_deg": 90,
                "face": "front",
                "crop_marks": True,
            }
        ],
    }

    montar_constructor_layout(
        layout,
        str(job_dir),
        preview=False,
        diseno_cls=montaje_offset_inteligente.Diseno,
        config_cls=montaje_offset_inteligente.MontajeConfig,
        render_fn=fake_render,
    )

    pos = captured[0].posiciones_manual[0]
    assert pos["slot_box_final"] is True
    assert pos["w_mm"] == pytest.approx(20)
    assert pos["h_mm"] == pytest.approx(70)
    assert pos["source_w_mm"] == pytest.approx(70)
    assert pos["source_h_mm"] == pytest.approx(20)


def test_explicit_slot_box_final_is_respected_for_repeat_slots(work_dir):
    job_dir = work_dir / "job_explicit_slot_box"
    job_dir.mkdir()
    pdf_path = job_dir / "pieza.pdf"
    pdf_path.write_bytes(_pdf_bytes(width_mm=210.058, height_mm=297.18).getvalue())
    captured = []

    def fake_render(_disenos, config):
        captured.append(config)
        out = Path(config.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"%PDF-1.4\n%%EOF\n")
        return str(out)

    layout = {
        "sheet_mm": [640, 880],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 3,
        "gap_default_mm": 5,
        "designs": [
            {
                "ref": "file0",
                "filename": "pieza.pdf",
                "width_mm": 210.058,
                "height_mm": 297.18,
                "bleed_mm": 3,
                "forms_per_plate": 1,
            }
        ],
        "works": [],
        "faces": ["front"],
        "active_face": "front",
        "imposition_engine": "repeat",
        "export_settings": {"bleed_mm": 3, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
        "slots": [
            {
                "id": "sr_1",
                "design_ref": "file0",
                "x_mm": 315,
                "y_mm": 125,
                "w_mm": 216.058,
                "h_mm": 303.18,
                "bleed_mm": 3,
                "rotation_deg": 90,
                "slot_box_final": True,
                "face": "front",
                "crop_marks": True,
            }
        ],
    }

    montar_constructor_layout(
        layout,
        str(job_dir),
        preview=False,
        diseno_cls=montaje_offset_inteligente.Diseno,
        config_cls=montaje_offset_inteligente.MontajeConfig,
        render_fn=fake_render,
    )

    assert captured[0].posiciones_manual[0]["slot_box_final"] is True
