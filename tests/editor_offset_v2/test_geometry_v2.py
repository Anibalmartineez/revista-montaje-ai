from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from editor_offset_v2.domain.geometry import (
    DEFAULT_TOLERANCE_MM,
    Bounds,
    GeometryValidationError,
    Point,
    Polygon,
    Size,
    SlotGeometry,
    bleed_bounds,
    bleed_polygon,
    center_to_bleed_bounds,
    center_to_trim_bounds,
    distance_between_bounds,
    horizontal_gap,
    is_finite_number,
    oriented_size,
    point_in_polygon,
    polygon_bounds,
    polygon_within_bounds,
    polygons_intersect,
    productive_size,
    rectangle_polygon,
    rotate_point,
    sheet_bounds,
    slot_within_sheet,
    slots_overlap,
    translate_polygon,
    trim_bounds,
    trim_polygon,
    validate_cardinal_rotation,
    validate_finite,
    validate_non_negative,
    validate_positive,
    vertical_gap,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "editor_offset_v2" / "geometry_cases.json"
)
LAYOUT_FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "editor_offset_v2"
    / "layout_v2_complete.json"
)


def load_cases() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def make_size(data: dict) -> Size:
    return Size(data["width"], data["height"])


def make_point(data: dict) -> Point:
    return Point(data["x"], data["y"])


def make_slot(data: dict) -> SlotGeometry:
    return SlotGeometry(
        center=make_point(data["center"]),
        trim_size=make_size(data["trim_size"]),
        bleed=data["bleed"],
        rotation_deg=data["rotation_deg"],
    )


def make_polygon(points: list[list[float]]) -> Polygon:
    return Polygon(tuple(Point(x, y) for x, y in points))


def assert_size(actual: Size, expected: dict) -> None:
    assert actual.width == pytest.approx(expected["width"])
    assert actual.height == pytest.approx(expected["height"])


def assert_bounds(actual: Bounds, expected: dict) -> None:
    assert actual.left == pytest.approx(expected["left"])
    assert actual.right == pytest.approx(expected["right"])
    assert actual.bottom == pytest.approx(expected["bottom"])
    assert actual.top == pytest.approx(expected["top"])
    assert actual.width == pytest.approx(expected["right"] - expected["left"])
    assert actual.height == pytest.approx(expected["top"] - expected["bottom"])


def assert_polygon(actual: Polygon, expected: list[list[float]]) -> None:
    assert len(actual.points) == len(expected)
    for point, (expected_x, expected_y) in zip(actual.points, expected):
        assert point.x == pytest.approx(expected_x)
        assert point.y == pytest.approx(expected_y)


@pytest.mark.parametrize("value", [0, 1, -1, 0.5, -3.25])
def test_is_finite_number_accepts_finite_ints_and_floats(value):
    assert is_finite_number(value)


@pytest.mark.parametrize(
    "value",
    [True, False, "1", None, math.nan, math.inf, -math.inf],
)
def test_is_finite_number_rejects_invalid_values(value):
    assert not is_finite_number(value)


@pytest.mark.parametrize(
    ("validator", "value"),
    [
        (validate_finite, True),
        (validate_finite, math.nan),
        (validate_finite, math.inf),
        (validate_positive, 0),
        (validate_positive, -1),
        (validate_non_negative, -0.001),
    ],
)
def test_numeric_validators_raise(validator, value):
    with pytest.raises(GeometryValidationError):
        validator(value)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270, 90.0])
def test_cardinal_rotations_are_valid(rotation):
    assert validate_cardinal_rotation(rotation) == float(rotation)


@pytest.mark.parametrize(
    "rotation",
    [89, 91, -90, 360, 450, True, math.nan, math.inf],
)
def test_non_cardinal_rotations_are_rejected_without_normalisation(rotation):
    with pytest.raises(GeometryValidationError):
        validate_cardinal_rotation(rotation)


@pytest.mark.parametrize(("width", "height"), [(0, 10), (-1, 10), (10, 0), (10, -1)])
def test_size_rejects_zero_and_negative_dimensions(width, height):
    with pytest.raises(GeometryValidationError):
        Size(width, height)


def test_slot_geometry_rejects_negative_bleed_and_non_cardinal_rotation():
    with pytest.raises(GeometryValidationError):
        SlotGeometry(Point(0, 0), Size(10, 10), -1, 0)
    with pytest.raises(GeometryValidationError):
        SlotGeometry(Point(0, 0), Size(10, 10), 0, 45)


def test_productive_size_keeps_trim_immutable_and_expands_uniformly():
    trim = Size(90, 50)

    assert productive_size(trim, 0) == Size(90, 50)
    assert productive_size(trim, 3) == Size(96, 56)
    assert trim == Size(90, 50)


@pytest.mark.parametrize(
    ("rotation", "expected"),
    [(0, Size(90, 50)), (90, Size(50, 90)), (180, Size(90, 50)), (270, Size(50, 90))],
)
def test_oriented_size_is_derived_without_changing_source(rotation, expected):
    source = Size(90, 50)

    assert oriented_size(source, rotation) == expected
    assert source == Size(90, 50)


@pytest.mark.parametrize("case", load_cases()["slot_cases"], ids=lambda case: case["id"])
def test_slot_fixture_sizes_polygons_and_bounds(case):
    slot = make_slot(case)
    expected = case["expected"]

    assert_size(oriented_size(slot.trim_size, slot.rotation_deg), expected["oriented_trim_size"])
    assert_size(productive_size(slot.trim_size, slot.bleed), expected["productive_size"])
    assert_polygon(trim_polygon(slot), expected["trim_polygon"])
    assert_bounds(trim_bounds(slot), expected["trim_bounds"])
    assert_bounds(bleed_bounds(slot), expected["bleed_bounds"])


def test_rectangle_vertices_have_stable_local_ccw_order_after_rotation():
    center = Point(10, 20)
    size = Size(4, 2)

    assert_polygon(
        rectangle_polygon(center, size, 0),
        [[8, 19], [12, 19], [12, 21], [8, 21]],
    )
    assert_polygon(
        rectangle_polygon(center, size, 90),
        [[11, 18], [11, 22], [9, 22], [9, 18]],
    )


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_rectangle_rotation_preserves_center(rotation):
    center = Point(12.75, 8.125)
    polygon = rectangle_polygon(center, Size(7.5, 2.25), rotation)

    average_x = sum(point.x for point in polygon) / len(polygon)
    average_y = sum(point.y for point in polygon) / len(polygon)
    assert average_x == pytest.approx(center.x)
    assert average_y == pytest.approx(center.y)


def test_rotate_point_is_counter_clockwise_and_cardinal():
    point = Point(2, 1)
    pivot = Point(1, 1)

    assert rotate_point(point, pivot, 0) == Point(2, 1)
    assert rotate_point(point, pivot, 90) == Point(1, 2)
    assert rotate_point(point, pivot, 180) == Point(0, 1)
    assert rotate_point(point, pivot, 270) == Point(1, 0)


def test_bleed_polygon_uses_same_center_and_rotation_as_trim():
    slot = SlotGeometry(Point(50, 40), Size(20, 10), 3, 90)

    trim = trim_bounds(slot)
    productive = bleed_bounds(slot)
    assert trim.center == slot.center
    assert productive.center == slot.center
    assert productive.width == pytest.approx(trim.width + 6)
    assert productive.height == pytest.approx(trim.height + 6)


def test_center_conversion_returns_trim_and_productive_lower_left_bounds():
    center = Point(60, 55)
    trim = Size(90, 50)

    assert center_to_trim_bounds(center, trim, 90) == Bounds(35, 85, 10, 100)
    assert center_to_bleed_bounds(center, trim, 3, 90) == Bounds(32, 88, 7, 103)
    assert center_to_trim_bounds(center, trim, 90).center == center


def test_polygon_bounds_handles_decimal_coordinates():
    polygon = rectangle_polygon(Point(12.75, 8.125), Size(7.5, 2.25), 270)

    assert polygon_bounds(polygon) == Bounds(11.625, 13.875, 4.375, 11.875)


def test_translate_polygon_does_not_modify_source():
    source = rectangle_polygon(Point(0, 0), Size(4, 2), 0)
    original_points = source.points

    translated = translate_polygon(source, 10.5, -2.25)

    assert source.points == original_points
    assert translated == rectangle_polygon(Point(10.5, -2.25), Size(4, 2), 0)


def test_point_in_polygon_includes_boundary_and_rejects_outside():
    polygon = rectangle_polygon(Point(5, 5), Size(10, 10), 0)

    assert point_in_polygon(Point(5, 5), polygon)
    assert point_in_polygon(Point(0, 5), polygon)
    assert point_in_polygon(Point(0, 0), polygon)
    assert not point_in_polygon(Point(-0.01, 5), polygon)


def test_polygon_within_bounds_accepts_edge_and_uses_only_numeric_tolerance():
    container = Bounds(0, 100, 0, 100)
    on_edge = rectangle_polygon(Point(10, 5), Size(20, 10), 0)
    tiny_outside = translate_polygon(on_edge, -DEFAULT_TOLERANCE_MM / 2.0, 0)

    assert polygon_within_bounds(on_edge, container)
    assert polygon_within_bounds(tiny_outside, container)
    assert not polygon_within_bounds(tiny_outside, container, tolerance_mm=0)


@pytest.mark.parametrize("case", load_cases()["sheet_cases"], ids=lambda case: case["id"])
def test_sheet_containment_fixture_cases(case):
    slot = make_slot(case["slot"])
    sheet_size_value = make_size(case["sheet_size"])

    assert slot_within_sheet(
        slot,
        sheet_size_value,
        use_bleed=case["use_bleed"],
    ) is case["expected"]
    if "expected_with_bleed" in case:
        assert slot_within_sheet(slot, sheet_size_value, use_bleed=True) is case[
            "expected_with_bleed"
        ]


def test_sheet_bounds_uses_bottom_left_origin():
    assert sheet_bounds(Size(700, 500)) == Bounds(0, 700, 0, 500)


@pytest.mark.parametrize("case", load_cases()["overlap_cases"], ids=lambda case: case["id"])
def test_slot_overlap_fixture_cases(case):
    first = make_slot(case["slot_a"])
    second = make_slot(case["slot_b"])

    assert slots_overlap(
        first,
        second,
        use_bleed=case["use_bleed"],
    ) is case["expected"]
    if "expected_without_bleed" in case:
        assert slots_overlap(first, second, use_bleed=False) is case[
            "expected_without_bleed"
        ]


def test_sat_rejects_aabb_false_positive_for_rotated_rectangles():
    case = load_cases()["polygon_cases"][0]
    first = make_polygon(case["polygon_a"])
    second = make_polygon(case["polygon_b"])
    first_bounds = polygon_bounds(first)
    second_bounds = polygon_bounds(second)
    bounds_overlap = horizontal_gap(first_bounds, second_bounds) < 0 and vertical_gap(
        first_bounds, second_bounds
    ) < 0

    assert bounds_overlap is case["expected_bounds_overlap"]
    assert polygons_intersect(first, second) is case["expected_polygon_overlap"]


def test_sat_treats_touch_and_tiny_penetration_as_numeric_contact():
    first = rectangle_polygon(Point(10, 10), Size(10, 10), 0)
    touching = rectangle_polygon(Point(20, 10), Size(10, 10), 0)
    tiny_penetration = rectangle_polygon(
        Point(20 - DEFAULT_TOLERANCE_MM / 2.0, 10),
        Size(10, 10),
        0,
    )

    assert not polygons_intersect(first, touching)
    assert not polygons_intersect(first, tiny_penetration)
    assert polygons_intersect(first, tiny_penetration, tolerance_mm=0)


def test_signed_horizontal_and_vertical_gaps_distinguish_states():
    base = Bounds(0, 10, 0, 10)

    assert horizontal_gap(base, Bounds(15, 25, 2, 8)) == pytest.approx(5)
    assert horizontal_gap(base, Bounds(10, 20, 2, 8)) == pytest.approx(0)
    assert horizontal_gap(base, Bounds(8, 20, 2, 8)) == pytest.approx(-2)
    assert vertical_gap(base, Bounds(2, 8, 15, 25)) == pytest.approx(5)
    assert vertical_gap(base, Bounds(2, 8, 10, 20)) == pytest.approx(0)
    assert vertical_gap(base, Bounds(2, 8, 8, 20)) == pytest.approx(-2)


def test_distance_between_bounds_is_minimum_euclidean_distance():
    base = Bounds(0, 10, 0, 10)

    assert distance_between_bounds(base, Bounds(13, 20, 14, 20)) == pytest.approx(5)
    assert distance_between_bounds(base, Bounds(5, 15, 5, 15)) == 0
    assert distance_between_bounds(base, Bounds(10, 20, 10, 20)) == 0


def test_models_are_immutable():
    point = Point(1, 2)
    size = Size(3, 4)
    bounds = Bounds(0, 3, 0, 4)
    polygon = rectangle_polygon(point, size, 0)
    slot = SlotGeometry(point, size, 0, 0)

    for model, attribute, value in [
        (point, "x", 10),
        (size, "width", 10),
        (bounds, "left", 10),
        (polygon, "points", ()),
        (slot, "bleed", 3),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(model, attribute, value)


def test_same_arguments_produce_equal_results_without_mutation():
    slot = SlotGeometry(Point(60, 55), Size(90, 50), 3, 90)
    before = (slot.center, slot.trim_size, slot.bleed, slot.rotation_deg)

    first = bleed_polygon(slot)
    second = bleed_polygon(slot)

    assert first == second
    assert (slot.center, slot.trim_size, slot.bleed, slot.rotation_deg) == before


def test_fixture_is_language_neutral_and_declares_tolerance():
    fixture = load_cases()

    assert fixture["fixture_schema_version"] == 1
    assert fixture["unit"] == "mm"
    assert fixture["default_tolerance_mm"] == DEFAULT_TOLERANCE_MM


def test_slot_geometry_maps_directly_from_layout_v2_geometry_contract():
    layout = json.loads(LAYOUT_FIXTURE_PATH.read_text(encoding="utf-8"))
    persisted = layout["slots"][0]["geometry"]
    slot = SlotGeometry(
        center=Point(
            persisted["position_mm"]["x_mm"],
            persisted["position_mm"]["y_mm"],
        ),
        trim_size=Size(
            persisted["trim_size_mm"]["width"],
            persisted["trim_size_mm"]["height"],
        ),
        bleed=persisted["bleed_mm"],
        rotation_deg=persisted["rotation_deg"],
    )

    assert slot == SlotGeometry(Point(60, 55), Size(90, 50), 3, 0)
