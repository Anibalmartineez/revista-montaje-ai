from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from editor_offset_v2.domain.layout_v2 import (
    CARDINAL_ROTATIONS_DEG,
    LEGACY_FIELD_NAMES,
)
from editor_offset_v2.domain.validation import (
    LayoutV2ValidationError,
    assert_valid_layout_v2,
    validate_layout_v2,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2"
SCHEMA_PATH = REPO_ROOT / "editor_offset_v2" / "schemas" / "layout-v2.schema.json"


def load_fixture(name: str = "layout_v2_complete.json") -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def codes(layout: object) -> set[str]:
    return {issue.code for issue in validate_layout_v2(layout)}


def set_rotation(layout: dict, target: str, value: object) -> None:
    if target == "slot":
        layout["slots"][0]["geometry"]["rotation_deg"] = value
    elif target == "work":
        layout["works"][0]["allowed_rotations_deg"] = [value]
    elif target == "content":
        layout["slots"][0]["content_transform"]["rotation_deg"] = value
    elif target == "page":
        layout["assets"][0]["pages"][0]["intrinsic_rotation_deg"] = value
    else:
        raise AssertionError(f"Unknown rotation target: {target}")


@pytest.mark.parametrize(
    "fixture_name",
    ["layout_v2_minimal.json", "layout_v2_complete.json"],
)
def test_v2_fixtures_are_valid(fixture_name):
    assert validate_layout_v2(load_fixture(fixture_name)) == []


def test_json_schema_is_valid_json_and_declares_v2():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["layout_schema_version"]["const"] == 2
    assert schema["additionalProperties"] is False


def test_json_schema_rotation_enums_match_python_canonical_rotations():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    definitions = schema["$defs"]
    expected = set(CARDINAL_ROTATIONS_DEG)

    schema_enums = {
        "work": definitions["work"]["properties"]["allowed_rotations_deg"][
            "items"
        ]["enum"],
        "content": definitions["contentTransform"]["properties"]["rotation_deg"][
            "enum"
        ],
        "slot": definitions["slot"]["properties"]["geometry"]["properties"][
            "rotation_deg"
        ]["enum"],
        "page": definitions["page"]["properties"]["intrinsic_rotation_deg"][
            "enum"
        ],
    }

    for values in schema_enums.values():
        assert set(values) == expected
        assert values == [0, 90, 180, 270]


def test_schema_and_fixtures_do_not_contain_legacy_field_names():
    documents = [
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
        load_fixture("layout_v2_minimal.json"),
        load_fixture("layout_v2_complete.json"),
    ]

    def collect_keys(value):
        if isinstance(value, dict):
            result = set(value)
            for child in value.values():
                result.update(collect_keys(child))
            return result
        if isinstance(value, list):
            result = set()
            for child in value:
                result.update(collect_keys(child))
            return result
        return set()

    for document in documents:
        assert collect_keys(document).isdisjoint(LEGACY_FIELD_NAMES)


def test_rejects_wrong_schema_version():
    layout = load_fixture()
    layout["layout_schema_version"] = 1

    assert "INVALID_SCHEMA_VERSION" in codes(layout)


def test_rejects_legacy_field_at_any_depth():
    layout = load_fixture()
    layout["slots"][0]["geometry"]["w_mm"] = 90

    assert "LEGACY_FIELD" in codes(layout)


def test_rejects_unknown_field_in_critical_structure():
    layout = load_fixture()
    layout["slots"][0]["geometry"]["cached_footprint"] = {}

    assert "UNKNOWN_FIELD" in codes(layout)


def test_rejects_unknown_asset_reference():
    layout = load_fixture()
    layout["slots"][0]["source"]["asset_id"] = "missing_asset"

    assert "BROKEN_REFERENCE" in codes(layout)


def test_rejects_unknown_work_reference():
    layout = load_fixture()
    layout["slots"][0]["work_id"] = "missing_work"

    assert "BROKEN_REFERENCE" in codes(layout)


def test_rejects_unknown_page_reference():
    layout = load_fixture()
    layout["slots"][0]["source"]["page"] = 99

    assert "BROKEN_REFERENCE" in codes(layout)


def test_rejects_pdf_box_that_is_explicitly_absent():
    layout = load_fixture()
    layout["slots"][0]["source"]["pdf_box"] = "crop"

    assert "MISSING_PDF_BOX" in codes(layout)


def test_rejects_invalid_or_disabled_face():
    layout = load_fixture()
    layout["slots"][0]["face"] = "inside"

    assert "INVALID_ENUM" in codes(layout)

    layout = load_fixture()
    layout["faces"]["enabled"] = ["front"]
    assert "DISABLED_FACE" in codes(layout)


@pytest.mark.parametrize("value", [0, -1])
def test_rejects_non_positive_trim_dimensions(value):
    layout = load_fixture()
    layout["slots"][0]["geometry"]["trim_size_mm"]["width"] = value

    assert "NON_POSITIVE_NUMBER" in codes(layout)


def test_rejects_negative_bleed():
    layout = load_fixture()
    layout["slots"][0]["geometry"]["bleed_mm"] = -0.1

    assert "NEGATIVE_NUMBER" in codes(layout)


@pytest.mark.parametrize("target", ["slot", "work", "content", "page"])
@pytest.mark.parametrize("value", [0, 90, 180, 270])
def test_accepts_only_canonical_rotations_for_v2_rotation_fields(target, value):
    layout = load_fixture()
    set_rotation(layout, target, value)

    assert validate_layout_v2(layout) == []


@pytest.mark.parametrize("target", ["slot", "work", "content", "page"])
@pytest.mark.parametrize(
    "value",
    [-90, 45, 89, 90.0001, 360, 450, math.nan, math.inf],
)
def test_rejects_non_cardinal_rotations_for_v2_rotation_fields(target, value):
    layout = load_fixture()
    set_rotation(layout, target, value)

    issue_codes = codes(layout)
    assert issue_codes & {"NON_FINITE_NUMBER", "INVALID_ROTATION"}


@pytest.mark.parametrize("collection", ["assets", "works", "slots"])
def test_rejects_duplicate_ids(collection):
    layout = load_fixture()
    layout[collection].append(copy.deepcopy(layout[collection][0]))

    assert "DUPLICATE_ID" in codes(layout)


def test_rejects_invalid_lock_source():
    layout = load_fixture()
    layout["slots"][0]["locks"]["geometry"] = ["legacy"]

    assert "INVALID_ENUM" in codes(layout)


def test_rejects_invalid_engine():
    layout = load_fixture()
    layout["imposition"]["engine"] = "legacy_auto"

    assert "INVALID_ENUM" in codes(layout)


@pytest.mark.parametrize("section", ["export", "ctp"])
def test_rejects_incomplete_export_or_ctp(section):
    layout = load_fixture()
    first_key = next(iter(layout[section]))
    del layout[section][first_key]

    assert "REQUIRED_FIELD" in codes(layout)


def test_rejects_invalid_revision():
    layout = load_fixture()
    layout["job"]["revision"] = -1

    assert "INTEGER_RANGE" in codes(layout)


def test_assert_valid_layout_raises_with_structured_issues():
    layout = load_fixture()
    layout["layout_schema_version"] = 1

    with pytest.raises(LayoutV2ValidationError) as exc_info:
        assert_valid_layout_v2(layout)

    assert exc_info.value.issues
    assert exc_info.value.issues[0].as_dict().keys() == {"code", "path", "message"}
