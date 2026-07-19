from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from editor_offset_v2.application.output_service import (
    validate_output_capabilities,
)
from editor_offset_v2.domain.geometry import (
    Point,
    Size,
    SlotGeometry,
    bleed_bounds,
    oriented_size,
    productive_size,
)
from editor_offset_v2.infrastructure.editor_output_adapter import (
    adapt_layout_v2_to_output,
    serialize_output_job,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2"


def load_layout() -> dict:
    return json.loads(
        (FIXTURES / "layout_v2_complete.json").read_text(encoding="utf-8")
    )


def load_cases() -> dict:
    return json.loads(
        (FIXTURES / "output_adapter_cases.json").read_text(encoding="utf-8")
    )


def make_supported_layout(*, front_and_back: bool = True) -> dict:
    layout = load_layout()
    layout["ctp"]["enabled"] = False
    for profile in layout["export"]["marks_profiles"]:
        profile["registration_marks"] = False
        profile["technical_text"] = False
        profile["color_bar"] = False
    if not front_and_back:
        layout["slots"] = [slot for slot in layout["slots"] if slot["face"] == "front"]
        layout["export"]["faces"].update(
            {
                "back": False,
                "combine_in_single_pdf": False,
                "order": ["front"],
            }
        )
    return layout


def create_asset_files(layout: dict, job_root: Path) -> None:
    for asset in layout["assets"]:
        target = job_root / asset["storage_key"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"%PDF-simulated\n")


def replace_pointer(document: dict, pointer: str, value: object) -> None:
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
    target: object = document
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    if isinstance(target, list):
        target[int(parts[-1])] = value
    else:
        target[parts[-1]] = value


def result_codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


def test_rejects_layout_without_v2_version_before_touching_assets(tmp_path):
    layout = make_supported_layout()
    layout["layout_schema_version"] = 1

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert result.job is None
    assert "INVALID_SCHEMA_VERSION" in result_codes(result)


def test_rejects_non_mapping_and_invalid_references(tmp_path):
    invalid = adapt_layout_v2_to_output([], tmp_path)
    assert not invalid.success
    assert "TYPE_OBJECT" in result_codes(invalid)

    layout = make_supported_layout()
    layout["slots"][0]["source"]["asset_id"] = "missing"
    broken = adapt_layout_v2_to_output(layout, tmp_path)
    assert not broken.success
    assert "BROKEN_REFERENCE" in result_codes(broken)


def test_successful_front_adaptation_resolves_asset_inside_job_root(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert result.success
    assert result.job is not None
    assert len(result.job.designs) == 1
    design = result.job.designs[0]
    assert design.source_path.is_file()
    assert design.source_path.is_relative_to(tmp_path.resolve())
    assert design.page == 1
    assert design.pdf_box == "trim"
    assert result.job.face("front").enabled
    assert not result.job.face("back").enabled
    assert result.job.face("back").positions == ()


def test_missing_physical_file_is_a_blocking_error(tmp_path):
    layout = make_supported_layout(front_and_back=False)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert result.job is None
    assert "ASSET_FILE_NOT_FOUND" in result_codes(result)


@pytest.mark.parametrize(
    ("storage_key", "expected_code"),
    [
        ("../outside.pdf", "UNSAFE_ASSET_STORAGE_KEY"),
        ("assets/../../outside.pdf", "UNSAFE_ASSET_STORAGE_KEY"),
        ("C:\\outside\\source.pdf", "UNSAFE_ASSET_STORAGE_KEY"),
        ("/outside/source.pdf", "UNSAFE_ASSET_STORAGE_KEY"),
    ],
)
def test_rejects_traversal_and_absolute_storage_keys(
    tmp_path, storage_key, expected_code
):
    layout = make_supported_layout(front_and_back=False)
    layout["assets"][0]["storage_key"] = storage_key

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert expected_code in result_codes(result)


def test_job_root_must_exist_and_be_a_directory(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    missing = tmp_path / "missing"
    file_root = tmp_path / "root.pdf"
    file_root.write_bytes(b"x")

    assert "INVALID_JOB_ROOT" in result_codes(
        adapt_layout_v2_to_output(layout, missing)
    )
    assert "INVALID_JOB_ROOT" in result_codes(
        adapt_layout_v2_to_output(layout, file_root)
    )


def test_valid_second_page_is_explicitly_unsupported_by_current_boundary(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    second_page = copy.deepcopy(layout["assets"][0]["pages"][0])
    second_page["number"] = 2
    layout["assets"][0]["pages"].append(second_page)
    layout["assets"][0]["page_count"] = 2
    layout["slots"][0]["source"]["page"] = 2
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert "UNSUPPORTED_SOURCE_PAGE" in result_codes(result)


def test_existing_non_trim_pdf_box_is_not_silently_exported(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    layout["slots"][0]["source"]["pdf_box"] = "media"
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert "UNSUPPORTED_PDF_BOX" in result_codes(result)


@pytest.mark.parametrize(
    "case",
    load_cases()["geometry_cases"],
    ids=lambda case: case["id"],
)
def test_center_to_productive_lower_left_uses_kernel_for_cardinal_rotations(
    tmp_path, case
):
    layout = make_supported_layout(front_and_back=False)
    slot = layout["slots"][0]
    slot["geometry"]["rotation_deg"] = case["rotation_deg"]
    slot["geometry"]["bleed_mm"] = case["bleed_mm"]
    if "clip_to" in case:
        slot["content_transform"]["clip_to"] = case["clip_to"]
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert result.success
    position = result.job.face("front").positions[0]
    assert (position.lower_left.x, position.lower_left.y) == pytest.approx(
        case["expected_lower_left_mm"]
    )
    assert (position.productive_size.width, position.productive_size.height) == pytest.approx(
        case["expected_productive_size_mm"]
    )
    assert position.trim_size == Size(90, 50)
    assert position.slot_box_final is True


def test_position_derivatives_equal_direct_geometry_kernel_results(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    layout["slots"][0]["geometry"]["rotation_deg"] = 90
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)
    position = result.job.face("front").positions[0]
    geometry = SlotGeometry(Point(60, 55), Size(90, 50), 3, 90)

    assert position.productive_bounds == bleed_bounds(geometry)
    assert position.productive_size == oriented_size(
        productive_size(geometry.trim_size, geometry.bleed),
        geometry.rotation_deg,
    )


def test_front_and_back_remain_distinct_without_implicit_duplication(tmp_path):
    layout = make_supported_layout(front_and_back=True)
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert result.success
    front = result.job.face("front")
    back = result.job.face("back")
    assert [position.slot_id for position in front.positions] == ["slot_front_001"]
    assert [position.slot_id for position in back.positions] == ["slot_back_001"]
    assert front.positions[0].design_id != back.positions[0].design_id
    assert front.positions[0].rotation_deg == 0
    assert back.positions[0].rotation_deg == 180


@pytest.mark.parametrize(
    "case",
    load_cases()["error_cases"],
    ids=lambda case: case["id"],
)
def test_language_neutral_error_cases_are_blocked(tmp_path, case):
    layout = make_supported_layout(front_and_back=False)
    create_asset_files(layout, tmp_path)
    replace_pointer(layout, case["pointer"], case["value"])

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert result.job is None
    assert case["expected_code"] in result_codes(result)


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("fit_mode", "contain", "UNSUPPORTED_CONTENT_FIT_MODE"),
        ("mirror_y", True, "UNSUPPORTED_CONTENT_MIRROR"),
        ("clip_to", "none", "UNSUPPORTED_CONTENT_CLIP"),
    ],
)
def test_unsupported_content_transform_never_degrades_silently(
    tmp_path, field, value, expected_code
):
    layout = make_supported_layout(front_and_back=False)
    layout["slots"][0]["content_transform"][field] = value
    create_asset_files(layout, tmp_path)

    issues = validate_output_capabilities(layout)

    assert expected_code in {issue.code for issue in issues}


def test_ctp_disabled_is_supported_but_active_ctp_is_blocked(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    create_asset_files(layout, tmp_path)

    disabled = adapt_layout_v2_to_output(layout, tmp_path)
    assert disabled.success
    assert disabled.job.ctp.enabled is False

    layout["ctp"]["enabled"] = True
    active = adapt_layout_v2_to_output(layout, tmp_path)
    assert not active.success
    assert "UNSUPPORTED_CTP_CONFIGURATION" in result_codes(active)


def test_advanced_per_slot_marks_are_blocked_until_safe_mapping_exists(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    layout["export"]["marks_profiles"][0]["registration_marks"] = True
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert "UNSUPPORTED_MARKS_PROFILE_FEATURE" in result_codes(result)


def test_export_face_order_combination_and_vector_policy_are_preflighted(tmp_path):
    layout = make_supported_layout(front_and_back=True)
    create_asset_files(layout, tmp_path)
    layout["export"]["faces"]["order"] = ["back", "front"]
    layout["export"]["faces"]["combine_in_single_pdf"] = False
    layout["export"]["preserve_vector_content"] = False

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert not result.success
    assert {
        "UNSUPPORTED_FACE_ORDER",
        "UNSUPPORTED_SEPARATE_FACE_PDFS",
        "UNSUPPORTED_VECTOR_POLICY",
    }.issubset(result_codes(result))


def test_preflight_warning_is_structured_and_does_not_make_success_false(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    create_asset_files(layout, tmp_path)

    result = adapt_layout_v2_to_output(layout, tmp_path)

    assert result.success
    warning = next(issue for issue in result.issues if issue.level == "warning")
    assert warning.code == "ASSET_PREFLIGHT_WARNING"
    assert warning.path
    assert warning.slot_id == "slot_front_001"
    assert warning.asset_id == "asset_card_front"
    assert set(warning.as_dict()).issuperset(
        {"code", "level", "message", "path", "slot_id", "asset_id"}
    )


def test_serialization_is_deterministic_and_matches_manual_output_contract(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    create_asset_files(layout, tmp_path)
    result = adapt_layout_v2_to_output(layout, tmp_path)

    first = serialize_output_job(result.job)
    second = serialize_output_job(result.job)

    assert first == second
    assert first is not second
    assert first["source_layout_schema_version"] == 2
    assert first["faces"]["front"]["modo_manual"] is True
    position = first["faces"]["front"]["posiciones_manual"][0]
    assert position == {
        "slot_id": "slot_front_001",
        "design_id": "asset_card_front:page-1:trim",
        "file_idx": 0,
        "source_page": 1,
        "pdf_box": "trim",
        "x_mm": 12.0,
        "y_mm": 27.0,
        "w_mm": 96.0,
        "h_mm": 56.0,
        "rot_deg": 0,
        "bleed_mm": 3.0,
        "crop_marks": True,
        "marks_profile_id": "standard_offset",
        "slot_box_final": True,
        "source_w_mm": 90.0,
        "source_h_mm": 50.0,
    }


def test_adapter_is_pure_idempotent_and_output_models_are_immutable(tmp_path):
    layout = make_supported_layout(front_and_back=False)
    original = copy.deepcopy(layout)
    create_asset_files(layout, tmp_path)

    first = adapt_layout_v2_to_output(layout, tmp_path)
    second = adapt_layout_v2_to_output(layout, tmp_path)

    assert first == second
    assert layout == original
    with pytest.raises(FrozenInstanceError):
        first.job.revision = 99
    with pytest.raises(FrozenInstanceError):
        first.job.face("front").positions[0].bleed_mm = 0


def test_fixture_is_language_neutral_and_covers_required_categories():
    fixture = load_cases()
    case_ids = {case["id"] for case in fixture["error_cases"]}

    assert fixture["fixture_schema_version"] == 1
    assert fixture["unit"] == "mm"
    assert {case["rotation_deg"] for case in fixture["geometry_cases"]} == {
        0,
        90,
        180,
        270,
    }
    assert {
        "asset_reference_missing",
        "page_reference_missing",
        "pdf_box_missing",
        "storage_traversal",
        "storage_absolute_windows",
        "content_scale",
        "content_offset",
        "content_rotation",
        "content_mirror",
        "content_clip",
        "ctp_active",
        "marks_profile_missing",
    }.issubset(case_ids)
