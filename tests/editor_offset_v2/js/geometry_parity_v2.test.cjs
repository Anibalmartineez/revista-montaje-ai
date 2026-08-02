const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Geometry = require(path.join(repoRoot, "static/js/editor_offset_v2/geometry_kernel.js"));
const fixture = JSON.parse(fs.readFileSync(
  path.join(repoRoot, "tests/fixtures/editor_offset_v2/geometry_cases.json"),
  "utf8",
));

function geometry(caseData) {
  return {
    position_mm: { x_mm: caseData.center.x, y_mm: caseData.center.y },
    trim_size_mm: { ...caseData.trim_size },
    bleed_mm: caseData.bleed,
    rotation_deg: caseData.rotation_deg,
  };
}

function close(actual, expected, tolerance = fixture.default_tolerance_mm) {
  assert.ok(Math.abs(actual - expected) <= tolerance * 4,
    `expected ${actual} to equal ${expected} within ${tolerance * 4}`);
}

function closeObject(actual, expected) {
  for (const [key, value] of Object.entries(expected)) close(actual[key], value);
}

test("frontend kernel consumes the same cardinal, bleed, decimal and negative fixtures as Python", () => {
  assert.equal(fixture.unit, "mm");
  assert.equal(fixture.default_tolerance_mm, Geometry.DEFAULT_TOLERANCE_MM);
  for (const item of fixture.slot_cases) {
    const source = geometry(item);
    closeObject(Geometry.orientedSize(item.trim_size, item.rotation_deg), item.expected.oriented_trim_size);
    closeObject(Geometry.productiveSize(item.trim_size, item.bleed), item.expected.productive_size);
    closeObject(Geometry.trimBounds(source), item.expected.trim_bounds);
    closeObject(Geometry.bleedBounds(source), item.expected.bleed_bounds);
    const polygon = Geometry.trimPolygon(source);
    item.expected.trim_polygon.forEach(([x, y], index) => {
      close(polygon[index].x, x);
      close(polygon[index].y, y);
    });
  }
});

test("frontend containment and SAT reproduce shared Python sheet and overlap cases", () => {
  for (const item of fixture.sheet_cases) {
    const sheet = Geometry.bounds({
      left: 0,
      right: item.sheet_size.width,
      bottom: 0,
      top: item.sheet_size.height,
    });
    const slot = geometry(item.slot);
    const polygon = item.use_bleed ? Geometry.bleedPolygon(slot) : Geometry.trimPolygon(slot);
    assert.equal(Geometry.polygonWithinBounds(polygon, sheet), item.expected, item.id);
    if (Object.hasOwn(item, "expected_with_bleed")) {
      assert.equal(Geometry.polygonWithinBounds(Geometry.bleedPolygon(slot), sheet),
        item.expected_with_bleed, `${item.id}:with_bleed`);
    }
  }
  for (const item of fixture.overlap_cases) {
    assert.equal(Geometry.slotsOverlap(geometry(item.slot_a), geometry(item.slot_b), item.use_bleed),
      item.expected, item.id);
    if (Object.hasOwn(item, "expected_without_bleed")) {
      assert.equal(Geometry.slotsOverlap(geometry(item.slot_a), geometry(item.slot_b), false),
        item.expected_without_bleed, `${item.id}:without_bleed`);
    }
  }
});

test("bounds, signed gaps, distance, contains and aggregate semantics are explicit", () => {
  for (const item of fixture.bounds_cases) {
    close(Geometry.horizontalGap(item.bounds_a, item.bounds_b), item.expected.gap_x);
    close(Geometry.verticalGap(item.bounds_a, item.bounds_b), item.expected.gap_y);
    close(Geometry.distanceBetweenBounds(item.bounds_a, item.bounds_b), item.expected.distance);
    assert.equal(Geometry.intersectsBounds(item.bounds_a, item.bounds_b, false), item.expected.intersects);
  }
  const aggregate = Geometry.aggregateBounds([
    { left: -4, right: 2, bottom: -3, top: 5 },
    { left: 1, right: 12, bottom: -8, top: 4 },
  ]);
  closeObject(aggregate, { left: -4, right: 12, bottom: -8, top: 5 });
  assert.equal(Geometry.containsPoint(aggregate, { x: -4, y: 5 }), true);
  assert.equal(Geometry.containsBounds(aggregate, { left: 0, right: 1, bottom: 0, top: 1 }), true);
  assert.equal(Geometry.intersectsBounds(
    { left: 0, right: 1, bottom: 0, top: 1 },
    { left: 1, right: 2, bottom: 0, top: 1 },
    true,
  ), true);
});

test("finite validation, exact cardinals and numerical tolerance match the Python contract", () => {
  for (const rotation of [0, 90, 180, 270]) assert.equal(Geometry.cardinalRotation(rotation), rotation);
  for (const rotation of [-90, 45, 360, Number.NaN]) {
    assert.throws(() => Geometry.cardinalRotation(rotation));
  }
  for (const value of [Number.NaN, Number.POSITIVE_INFINITY, "1", true]) {
    assert.throws(() => Geometry.finiteNumber(value));
  }
  assert.equal(Geometry.approximatelyEqual(10, 10 + Geometry.DEFAULT_TOLERANCE_MM / 2), true);
  assert.equal(Geometry.approximatelyEqual(10, 10 + Geometry.DEFAULT_TOLERANCE_MM * 2), false);
  const first = Geometry.rectanglePolygon({ x: 10, y: 10 }, { width: 10, height: 10 }, 0);
  const contact = Geometry.rectanglePolygon(
    { x: 20 - Geometry.DEFAULT_TOLERANCE_MM / 2, y: 10 },
    { width: 10, height: 10 },
    0,
  );
  assert.equal(Geometry.polygonsIntersect(first, contact), false);
  assert.equal(Geometry.polygonsIntersect(first, contact, 0), true);
});

test("shared SAT fixture preserves polygon precision beyond cardinal AABB helpers", () => {
  const item = fixture.polygon_cases[0];
  const first = item.polygon_a.map(([x, y]) => ({ x, y }));
  const second = item.polygon_b.map(([x, y]) => ({ x, y }));
  assert.equal(Geometry.intersectsBounds(
    Geometry.polygonBounds(first),
    Geometry.polygonBounds(second),
    false,
  ), item.expected_bounds_overlap);
  assert.equal(Geometry.polygonsIntersect(first, second),
    item.expected_polygon_overlap);
});
