from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from editor_offset_v2.application.job_service import create_initial_layout_v2
from editor_offset_v2.domain.geometry import Bounds, bleed_bounds
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.repeat_engine_adapter import RepeatEngineAdapter


FIXTURE = Path("tests/fixtures/editor_offset_v2/repeat_cases.json")
OPERATION_ID = "repeat_test_operation"
GENERATED_AT = "2026-07-19T12:00:00Z"


def load_case(case_id: str) -> dict:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(item for item in fixture["cases"] if item["id"] == case_id)


def make_asset(asset_id: str = "asset_repeat") -> dict:
    return {
        "id": asset_id,
        "original_filename": f"{asset_id}.pdf",
        "storage_key": f"assets/{asset_id}/source.pdf",
        "mime_type": "application/pdf",
        "sha256": "a" * 64,
        "page_count": 1,
        "status": "ready",
        "created_at": GENERATED_AT,
        "pages": [
            {
                "number": 1,
                "intrinsic_rotation_deg": 0,
                "boxes_mm": {
                    "media": {"x": 0, "y": 0, "width": 100, "height": 60},
                    "trim": {"x": 3, "y": 3, "width": 94, "height": 54},
                    "bleed": {"x": 0, "y": 0, "width": 100, "height": 60},
                    "crop": None,
                },
                "preview_key": f"assets/{asset_id}/thumbnails/page_1.png",
                "preflight": {
                    "status": "not_run",
                    "color_spaces": [],
                    "minimum_effective_dpi": None,
                    "has_transparency": None,
                    "has_overprint": None,
                    "issues": [],
                },
            }
        ],
    }


def make_layout(case: dict, *, back: bool = False) -> dict:
    layout = create_initial_layout_v2("ev2_aaaaaaaaaaaaaaaaaaaaaaaa", now=GENERATED_AT)
    layout["sheet"]["size_mm"] = copy.deepcopy(case["sheet_mm"])
    layout["sheet"]["printable_margins_mm"] = copy.deepcopy(case["margins_mm"])
    if back:
        layout["faces"] = {
            "enabled": ["front", "back"],
            "duplex": {"enabled": True, "flip": "long_edge"},
        }
        layout["export"]["faces"].update({"back": True, "combine_in_single_pdf": True})
        layout["export"]["faces"]["order"] = ["front", "back"]
    asset = make_asset()
    source = {"asset_id": asset["id"], "page": 1, "pdf_box": "trim"}
    layout["assets"] = [asset]
    layout["works"] = [
        {
            "id": "work_repeat",
            "name": "Repeat work",
            "trim_size_mm": copy.deepcopy(case["trim_mm"]),
            "bleed_mm": case["bleed_mm"],
            "requested_forms": case["requested"],
            "allowed_rotations_deg": copy.deepcopy(case["allowed_rotations_deg"]),
            "priority": 100,
            "preferred_zone": "auto",
            "preferred_flow": "rows",
            "front_source": copy.deepcopy(source),
            "back_source": copy.deepcopy(source) if back else None,
        }
    ]
    assert validate_layout_v2(layout) == []
    return layout


def settings(case: dict, **overrides) -> dict:
    result = {
        "horizontal_gap_mm": case["gaps_mm"]["horizontal"],
        "vertical_gap_mm": case["gaps_mm"]["vertical"],
        "exact_quantity": True,
        "fill_remaining_space": False,
        "allow_partial": False,
        "respect_priority": True,
        "respect_preferred_zones": True,
    }
    result.update(overrides)
    return result


def propose(layout: dict, case: dict, **overrides):
    face = overrides.pop("face", "front")
    apply_mode = overrides.pop("apply_mode", "add")
    return RepeatEngineAdapter().propose(
        layout,
        ["work_repeat"],
        face,
        settings(case, **overrides),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode=apply_mode,
    )


def test_single_work_zero_bleed_exact_quantity_and_contract():
    case = load_case("single_zero_bleed")
    result = propose(make_layout(case), case)

    assert result.success is True
    assert (result.requested, result.placed, result.unplaced, result.overproduced) == (6, 6, 0, 0)
    assert all(slot["geometry"]["bleed_mm"] == 0 for slot in result.slots)
    assert all("w_mm" not in slot and "slot_box_final" not in slot for slot in result.slots)
    proposal = make_layout(case)
    proposal["slots"] = copy.deepcopy(list(result.slots))
    assert validate_layout_v2(proposal) == []


def test_rotation_90_preserves_unrotated_trim_and_converts_productive_corner_to_center():
    case = load_case("cardinal_90_only")
    result = propose(make_layout(case), case)

    assert result.success is True
    assert {slot["geometry"]["rotation_deg"] for slot in result.slots} == {90}
    assert {tuple(slot["geometry"]["trim_size_mm"].values()) for slot in result.slots} == {(70, 20)}
    first = result.slots[0]
    assert first["geometry"]["position_mm"]["x_mm"] == pytest.approx(20)
    assert first["geometry"]["position_mm"]["y_mm"] == pytest.approx(45)


def test_bleed_three_uses_productive_footprints_inside_printable_bounds():
    case = load_case("bleed_three")
    layout = make_layout(case)
    result = propose(layout, case)
    printable = Bounds(12, 208, 15, 145)

    assert result.success is True
    assert len(result.slots) == 4
    for slot in result.slots:
        geometry = RepeatEngineAdapter._slot_geometry(slot)
        assert geometry.bleed == 3
        bounds = bleed_bounds(geometry)
        assert bounds.left >= printable.left
        assert bounds.right <= printable.right
        assert bounds.bottom >= printable.bottom
        assert bounds.top <= printable.top


def test_multiple_works_are_not_omitted():
    case = load_case("single_zero_bleed")
    layout = make_layout(case)
    second_asset = make_asset("asset_second")
    second = copy.deepcopy(layout["works"][0])
    second.update({"id": "work_second", "name": "Second", "requested_forms": 2, "priority": 50})
    second["front_source"]["asset_id"] = second_asset["id"]
    layout["assets"].append(second_asset)
    layout["works"].append(second)
    assert validate_layout_v2(layout) == []

    result = RepeatEngineAdapter().propose(
        layout,
        ["work_repeat", "work_second"],
        "front",
        settings(case),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode="add",
    )

    assert result.success is True
    assert result.placed == 8
    assert {slot["work_id"] for slot in result.slots} == {"work_repeat", "work_second"}


def test_incomplete_is_blocked_or_returned_as_explicit_partial():
    case = load_case("partial_required")
    layout = make_layout(case)
    blocked = propose(layout, case)
    partial = propose(layout, case, allow_partial=True)

    assert blocked.success is False
    assert blocked.slots == ()
    assert blocked.issues[0].code == "INCOMPLETE_IMPOSITION"
    assert partial.success is True
    assert (partial.requested, partial.placed, partial.unplaced) == (4, 1, 3)
    assert partial.warnings


def test_fill_remaining_space_reports_overproduction_and_false_does_not_overproduce():
    case = load_case("fill_capacity")
    layout = make_layout(case)
    exact = propose(layout, case)
    filled = propose(layout, case, fill_remaining_space=True)

    assert exact.placed == exact.requested == 2
    assert exact.overproduced == 0
    assert filled.success is True
    assert filled.placed == 16
    assert filled.overproduced == 14


def test_front_and_back_use_the_corresponding_source_without_inventing_back():
    case = load_case("single_zero_bleed")
    front_only = make_layout(case)
    missing = propose(front_only, case, face="back")
    duplex = make_layout(case, back=True)
    back = propose(duplex, case, face="back")

    assert missing.success is False
    assert missing.issues[0].code == "SOURCE_NOT_FOUND"
    assert back.success is True
    assert {slot["face"] for slot in back.slots} == {"back"}


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda layout: layout.update({"works": []}), "WORK_NOT_FOUND"),
        (lambda layout: layout.update({"assets": []}), "ASSET_NOT_FOUND"),
        (lambda layout: layout["assets"][0].update({"pages": []}), "PAGE_NOT_FOUND"),
        (
            lambda layout: layout["assets"][0]["pages"][0]["boxes_mm"].update({"trim": None}),
            "PDF_BOX_NOT_FOUND",
        ),
        (lambda layout: layout["assets"][0].update({"status": "error"}), "NON_EXPORTABLE_ASSET"),
    ],
)
def test_invalid_work_sources_and_placeholders_are_explicit(mutation, code):
    case = load_case("single_zero_bleed")
    layout = make_layout(case)
    mutation(layout)

    result = propose(layout, case)

    assert result.success is False
    assert result.slots == ()
    assert result.issues[0].code == code


@pytest.mark.parametrize(
    ("legacy_slots", "expected_code"),
    [
        ([{"design_ref": "work_repeat", "x_mm": -50, "y_mm": 10, "rotation_deg": 0}], "ENGINE_SLOT_OUT_OF_BOUNDS"),
        (
            [
                {"design_ref": "work_repeat", "x_mm": 10, "y_mm": 10, "rotation_deg": 0},
                {"design_ref": "work_repeat", "x_mm": 10, "y_mm": 10, "rotation_deg": 0},
            ],
            "ENGINE_SLOT_OVERLAP",
        ),
    ],
)
def test_invalid_engine_positions_are_rejected(legacy_slots, expected_code):
    case = load_case("single_zero_bleed")
    layout = make_layout(case)
    adapter = RepeatEngineAdapter(engine=lambda _layout: legacy_slots)

    result = adapter.propose(
        layout,
        ["work_repeat"],
        "front",
        settings(case),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode="add",
    )

    assert result.success is False
    assert expected_code in {issue.code for issue in result.issues}


def test_add_checks_existing_overlap_while_replace_excludes_selected_work_face():
    case = load_case("single_zero_bleed")
    layout = make_layout(case)
    first = propose(layout, case)
    layout["slots"] = [copy.deepcopy(first.slots[0])]

    add = RepeatEngineAdapter().propose(
        layout,
        ["work_repeat"],
        "front",
        settings(case),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode="add",
    )
    replace = RepeatEngineAdapter().propose(
        layout,
        ["work_repeat"],
        "front",
        settings(case),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode="replace_work_face",
    )

    assert add.success is False
    assert "OVERLAP_EXISTING_SLOT" in {issue.code for issue in add.issues}
    assert replace.success is True


def test_adapter_is_pure_and_deterministic_for_same_arguments():
    case = load_case("realistic_offset_decimal")
    layout = make_layout(case)
    before = copy.deepcopy(layout)
    adapter = RepeatEngineAdapter()

    first = adapter.propose(
        layout,
        ["work_repeat"],
        "front",
        settings(case),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode="add",
    )
    second = adapter.propose(
        layout,
        ["work_repeat"],
        "front",
        settings(case),
        operation_id=OPERATION_ID,
        generated_at=GENERATED_AT,
        apply_mode="add",
    )

    assert layout == before
    assert first.as_dict() == second.as_dict()
