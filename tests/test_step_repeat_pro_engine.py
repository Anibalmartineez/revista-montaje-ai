import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import app
from routes import (
    IncompleteImpositionError,
    _build_step_repeat_slots,
    _constructor_job_dir,
    _load_constructor_layout,
    _save_constructor_layout,
)


def _design(
    ref,
    *,
    width=20,
    height=10,
    forms=1,
    bleed=0,
    zone="auto",
    role="secondary",
    allow_rotation=False,
):
    return {
        "ref": ref,
        "filename": f"{ref}.pdf",
        "work_id": None,
        "width_mm": width,
        "height_mm": height,
        "bleed_mm": bleed,
        "forms_per_plate": forms,
        "allow_rotation": allow_rotation,
        "preferred_zone": zone,
        "preferred_flow": "auto",
        "repeat_role": role,
        "priority": 100,
        "repeat_manual_overrides": {
            "priority": False,
            "preferred_flow": False,
            "repeat_role": True,
        },
    }


def _layout(*designs, sheet=(200, 200), margins=(10, 10, 10, 10), spacing=(4, 3), face="front"):
    return {
        "sheet_mm": list(sheet),
        "margins_mm": list(margins),
        "bleed_default_mm": 3,
        "gap_default_mm": 5,
        "works": [],
        "slots": [],
        "designs": list(designs),
        "faces": [face],
        "active_face": face,
        "imposition_engine": "repeat",
        "allowed_engines": ["repeat", "nesting", "hybrid"],
        "spacingSettings": {
            "spacingX_mm": spacing[0],
            "spacingY_mm": spacing[1],
            "live": True,
        },
        "export_settings": {"bleed_mm": 3, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
    }


def _overlaps(a, b):
    return (
        a["x_mm"] < b["x_mm"] + b["w_mm"]
        and a["x_mm"] + a["w_mm"] > b["x_mm"]
        and a["y_mm"] < b["y_mm"] + b["h_mm"]
        and a["y_mm"] + a["h_mm"] > b["y_mm"]
    )


def _assert_no_collisions(slots):
    for idx, slot in enumerate(slots):
        for other in slots[idx + 1 :]:
            assert not _overlaps(slot, other)


def test_repeat_simple_auto_places_all_requested_forms():
    layout = _layout(_design("a", forms=6, width=20, height=10), spacing=(2, 2))

    slots = _build_step_repeat_slots(layout)

    assert len(slots) == 6
    assert {slot["design_ref"] for slot in slots} == {"a"}
    _assert_no_collisions(slots)


def test_repeat_respects_forms_per_plate_per_design():
    layout = _layout(
        _design("a", forms=3, width=20, height=10),
        _design("b", forms=2, width=15, height=10),
        spacing=(2, 2),
    )

    slots = _build_step_repeat_slots(layout)

    counts = {}
    for slot in slots:
        counts[slot["design_ref"]] = counts.get(slot["design_ref"], 0) + 1
    assert counts == {"a": 3, "b": 2}


def test_repeat_raises_incomplete_when_requested_forms_do_not_fit():
    layout = _layout(_design("huge", forms=4, width=90, height=90), sheet=(100, 100), margins=(5, 5, 5, 5))

    with pytest.raises(IncompleteImpositionError) as exc:
        _build_step_repeat_slots(layout)

    assert exc.value.details
    assert exc.value.details[0]["requested_forms"] == 4
    assert exc.value.details[0]["missing_forms"] > 0


def test_repeat_respects_explicit_zero_bleed():
    layout = _layout(_design("zero", width=30, height=20, forms=2, bleed=0), spacing=(2, 2))

    slots = _build_step_repeat_slots(layout)

    assert all(slot["bleed_mm"] == 0 for slot in slots)
    assert {(slot["w_mm"], slot["h_mm"]) for slot in slots} == {(30.0, 20.0)}


def test_repeat_uses_spacing_settings_between_slots():
    layout = _layout(_design("spaced", width=20, height=10, forms=2, bleed=0), spacing=(7, 11))

    slots = sorted(_build_step_repeat_slots(layout), key=lambda slot: slot["x_mm"])

    assert len(slots) == 2
    assert slots[1]["x_mm"] - (slots[0]["x_mm"] + slots[0]["w_mm"]) == pytest.approx(7)


@pytest.mark.parametrize(
    ("zone", "predicate"),
    [
        ("bottom", lambda slot, usable_bottom, usable_top: slot["y_mm"] < usable_bottom + (usable_top - usable_bottom) * 0.25 + 1e-6),
        ("center", lambda slot, usable_bottom, usable_top: usable_bottom + (usable_top - usable_bottom) * 0.25 - 1e-6 <= slot["y_mm"] <= usable_bottom + (usable_top - usable_bottom) * 0.75 + 1e-6),
        ("top", lambda slot, usable_bottom, usable_top: slot["y_mm"] >= usable_bottom + (usable_top - usable_bottom) * 0.75 - 1e-6),
    ],
)
def test_repeat_vertical_zones_place_slots_in_initial_zone_when_used_alone(zone, predicate):
    layout = _layout(
        _design(zone, width=20, height=10, forms=1, zone=zone),
        sheet=(200, 200),
        margins=(10, 10, 10, 10),
    )

    slots = _build_step_repeat_slots(layout)

    assert len(slots) == 1
    usable_bottom = 10
    usable_top = 190
    assert predicate(slots[0], usable_bottom, usable_top)


def test_repeat_vertical_zones_compact_without_collisions():
    layout = _layout(
        _design("top", width=30, height=15, forms=2, zone="top"),
        _design("bottom", width=30, height=15, forms=2, zone="bottom"),
        sheet=(220, 220),
        margins=(10, 10, 10, 10),
        spacing=(4, 6),
    )

    slots = _build_step_repeat_slots(layout)

    assert len(slots) == 4
    _assert_no_collisions(slots)


def test_repeat_auto_avoids_collisions_with_zonal_slots():
    layout = _layout(
        _design("top", width=30, height=15, forms=2, zone="top"),
        _design("auto", width=25, height=15, forms=2, zone="auto"),
        sheet=(220, 220),
        margins=(10, 10, 10, 10),
        spacing=(4, 6),
    )

    slots = _build_step_repeat_slots(layout)

    assert len(slots) == 4
    _assert_no_collisions(slots)


def test_repeat_fill_does_not_collide_with_existing_zonal_slots():
    layout = _layout(
        _design("top", width=30, height=15, forms=2, zone="top"),
        _design("fill", width=20, height=12, forms=2, zone="auto", role="fill"),
        sheet=(220, 220),
        margins=(10, 10, 10, 10),
        spacing=(4, 6),
    )

    slots = _build_step_repeat_slots(layout)

    assert len(slots) == 4
    _assert_no_collisions(slots)


def test_repeat_rotation_keeps_slot_dimensions_as_final_footprint():
    layout = _layout(
        _design("rot", width=70, height=20, forms=4, bleed=0, allow_rotation=True),
        sheet=(120, 95),
        margins=(10, 10, 10, 10),
        spacing=(2, 2),
    )

    slots = _build_step_repeat_slots(layout)

    assert len(slots) == 4
    assert {slot["rotation_deg"] for slot in slots} == {90}
    assert {(slot["w_mm"], slot["h_mm"]) for slot in slots} == {(20.0, 70.0)}


def test_failed_apply_imposition_does_not_persist_partial_slots():
    job_id = "srtestpersist"
    stored_layout = _layout(_design("old", width=10, height=10, forms=1))
    stored_layout["slots"] = [
        {
            "id": "existing",
            "design_ref": "old",
            "x_mm": 1,
            "y_mm": 1,
            "w_mm": 10,
            "h_mm": 10,
            "bleed_mm": 0,
            "rotation_deg": 0,
            "face": "front",
        }
    ]
    failing_layout = _layout(_design("huge", width=90, height=90, forms=4), sheet=(100, 100), margins=(5, 5, 5, 5))

    with app.app_context():
        job_dir = Path(_constructor_job_dir(job_id))
        if job_dir.exists():
            shutil.rmtree(job_dir)
        _save_constructor_layout(str(job_dir), deepcopy(stored_layout))

    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post(
            "/editor_offset_visual/apply_imposition",
            data={
                "job_id": job_id,
                "selected_engine": "repeat",
                "layout_json": json.dumps(failing_layout),
            },
        )

    assert response.status_code == 422
    with app.app_context():
        persisted = _load_constructor_layout(str(_constructor_job_dir(job_id)))
    assert persisted["slots"] == stored_layout["slots"]


def test_all_generated_slots_include_required_contract_fields():
    required = {
        "id",
        "design_ref",
        "x_mm",
        "y_mm",
        "w_mm",
        "h_mm",
        "bleed_mm",
        "rotation_deg",
        "face",
    }
    layout = _layout(_design("contract", width=20, height=10, forms=3, bleed=1), face="back")

    slots = _build_step_repeat_slots(layout)

    assert slots
    for slot in slots:
        assert required <= set(slot)
        assert slot["face"] == "back"
