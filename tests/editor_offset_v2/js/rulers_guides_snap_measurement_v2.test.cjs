const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Geometry = require(path.join(repoRoot, "static/js/editor_offset_v2/geometry_view.js"));
const Precision = require(path.join(repoRoot, "static/js/editor_offset_v2/precision_tools.js"));
const Snap = require(path.join(repoRoot, "static/js/editor_offset_v2/snap_engine.js"));
const Store = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const Registry = require(path.join(repoRoot, "static/js/editor_offset_v2/command_registry.js"));
const Interactions = require(path.join(repoRoot, "static/js/editor_offset_v2/interactions.js"));

const layoutFixture = JSON.parse(fs.readFileSync(
  path.join(repoRoot, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
  "utf8",
));

function clone(value) {
  return structuredClone(value);
}

function slot(id, x, y, options = {}) {
  const source = clone(layoutFixture.slots[0]);
  source.id = id;
  source.face = options.face || "front";
  source.geometry.position_mm = { x_mm: x, y_mm: y };
  source.geometry.trim_size_mm = options.size || { width: 20, height: 10 };
  source.geometry.bleed_mm = options.bleed ?? 0;
  source.geometry.rotation_deg = options.rotation ?? 0;
  return source;
}

function layoutWith(slots) {
  const layout = clone(layoutFixture);
  layout.slots = slots;
  layout.faces.enabled = ["front", "back"];
  return layout;
}

function targets(layout, options = {}) {
  return Snap.captureTargets({
    layout,
    activeFace: "front",
    hiddenSlotIds: options.hidden || [],
    movingIds: options.moving || [],
    guides: options.guides || [],
    geometry: Geometry,
    reference: options.reference || "trim",
    sources: options.sources || { guides: true, sheet: true, printable: true, slots: true },
  });
}

test("ruler ticks adapt to zoom and pan, preserve canonical values and stay bounded", () => {
  const low = Precision.rulerTicks({ start: -620, end: 820, pixelsPerMm: 0.2 });
  const high = Precision.rulerTicks({ start: 12.25, end: 22.25, pixelsPerMm: 40 });
  assert.ok(low.majorStep > high.majorStep);
  assert.ok(low.ticks.length <= Precision.MAX_RULER_TICKS);
  assert.ok(high.ticks.length <= Precision.MAX_RULER_TICKS);
  assert.ok(low.ticks.some((item) => item.value < 0 && item.label !== null));
  assert.ok(high.ticks.some((item) => item.value >= 12.25 && item.label !== null));
  assert.equal(Precision.chooseRulerStep(0.1, 64), 500);
  assert.equal(Precision.chooseRulerStep(1000, 64), 0.1);
});

test("screen pixel threshold converts through the live SVG transform", () => {
  const svg = {
    getScreenCTM: () => ({ inverse: () => ({ scale: 0.25 }) }),
    createSVGPoint: () => ({
      x: 0,
      y: 0,
      matrixTransform(matrix) { return { x: this.x * matrix.scale, y: this.y * matrix.scale }; },
    }),
  };
  assert.deepEqual(Interactions.screenPixelsToDomain(svg, 6), { x: 1.5, y: 1.5 });
});

test("guide parsing and CRUD accept point, comma, sign and remain wholly temporary", () => {
  assert.deepEqual(Precision.parseMillimetres(" -12,50 "), { ok: true, value: -12.5, error: null });
  assert.deepEqual(Precision.parseMillimetres("+3.25"), { ok: true, value: 3.25, error: null });
  assert.equal(Precision.parseMillimetres("3 mm").ok, false);
  const store = new Store.EditorStore(layoutWith([slot("a", 20, 20)]));
  const baseline = {
    version: store.changeVersion,
    revision: store.revision,
    dirty: store.hasUnsavedChanges(),
    undo: store.undoStack.length,
    redo: store.redoStack.length,
  };
  store.setPrecisionOption("rulersVisible", true);
  store.setPrecisionOption("guidesVisible", false);
  store.setPrecisionOption("snapEnabled", true);
  store.createGuide({ id: "gx", axis: "x", position_mm: -12.5 });
  store.createGuide({ id: "gy", axis: "y", position_mm: 30.25 });
  store.updateGuide("gx", 4.75);
  store.deleteGuide("gy");
  store.clearGuides();
  store.setMeasurementMode(true);
  store.startMeasurement({ x: 0, y: 0 });
  store.updateMeasurement({ x: 3, y: 4 });
  store.finishMeasurement(Precision.measurement({ x: 0, y: 0 }, { x: 3, y: 4 }));
  store.clearMeasurement();
  assert.deepEqual({
    version: store.changeVersion,
    revision: store.revision,
    dirty: store.hasUnsavedChanges(),
    undo: store.undoStack.length,
    redo: store.redoStack.length,
  }, baseline);
  assert.equal(store.precisionTools.guides.length, 0);
});

test("precision actions are unique, centralized and never documentary", () => {
  const registry = new Registry.ActionRegistry();
  Registry.registerEditorActions(registry);
  const ids = Object.values(Registry.ACTION_IDS).filter((id) => id.startsWith("precision."));
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ids) assert.equal(registry.get(id).modifiesLayout, false, id);
  const store = new Store.EditorStore(layoutWith([slot("a", 20, 20)]));
  const context = { store, precisionTools: Precision };
  registry.execute(Registry.ACTION_IDS.PRECISION_GUIDE_CREATE, context,
    { axis: "x", position_mm: -2.5, token: "stable" });
  registry.execute(Registry.ACTION_IDS.PRECISION_GUIDE_UPDATE, context,
    { id: store.precisionTools.guides[0].id, position_mm: 7.5 });
  registry.execute(Registry.ACTION_IDS.PRECISION_GUIDE_DELETE, context,
    { id: store.precisionTools.guides[0].id });
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
});

test("snap sources cover guide, printable, sheet and visible same-face slots only", () => {
  const layout = layoutWith([
    slot("moving", 20, 20),
    slot("visible", 80, 50),
    slot("hidden", 100, 50),
    slot("back", 120, 50, { face: "back" }),
  ]);
  const captured = targets(layout, {
    moving: ["moving"],
    hidden: ["hidden"],
    guides: [{ id: "guide-x", axis: "x", position_mm: 42 }],
  });
  assert.equal(captured.capturedSlotCount, 1);
  assert.ok(captured.x.some((item) => item.source === "guide" && item.value === 42));
  assert.ok(captured.x.some((item) => item.source === "printable"));
  assert.ok(captured.x.some((item) => item.source === "sheet"));
  assert.ok(captured.x.some((item) => item.source === "slot" && item.id.startsWith("visible:")));
  assert.ok(!captured.x.some((item) => item.id.startsWith("moving:")
    || item.id.startsWith("hidden:") || item.id.startsWith("back:")));
});

test("snap is deterministic, thresholded, simultaneous and prioritizes guide, printable, sheet, slot", () => {
  const sourceBounds = Geometry.bounds({ left: 0, right: 10, bottom: 0, top: 10 });
  const target = (axis, value, source, kind, id, order = 0) => ({
    axis, value, source, kind, id, order, label: `${source}-${kind}`,
  });
  const snapTargets = {
    x: [
      target("x", 20, "slot", "edge", "d", 0),
      target("x", 20, "sheet", "edge", "c", 0),
      target("x", 20, "printable", "edge", "b", 0),
      target("x", 20, "guide", "edge", "a", 0),
    ],
    y: [target("y", 30, "sheet", "center", "sheet:center-y", 0)],
  };
  const disabled = Snap.snapTranslation({ sourceBounds, rawDx: 9, rawDy: 19,
    targets: snapTargets, thresholdMm: 2, enabled: false });
  assert.deepEqual({ dx: disabled.dx, dy: disabled.dy }, { dx: 9, dy: 19 });
  const snapped = Snap.snapTranslation({ sourceBounds, rawDx: 9.5, rawDy: 19.5,
    targets: snapTargets, thresholdMm: { x: 1, y: 1 }, enabled: true });
  assert.equal(snapped.dx, 10);
  assert.equal(snapped.dy, 20);
  assert.equal(snapped.x.target.source, "guide");
  assert.equal(snapped.guides.length, 2);
  const outside = Snap.snapTranslation({ sourceBounds, rawDx: 7, rawDy: 17,
    targets: snapTargets, thresholdMm: 1, enabled: true });
  assert.deepEqual({ dx: outside.dx, dy: outside.dy }, { dx: 7, dy: 17 });
});

test("Trim and productive reference change group anchors without breaking multi-slot distances", () => {
  const moving = [slot("a", 20, 20, { bleed: 3 }), slot("b", 60, 20, { bleed: 3 })];
  const trim = Snap.groupBounds(moving, Geometry, "trim");
  const productive = Snap.groupBounds(moving, Geometry, "productive");
  assert.equal(productive.left, trim.left - 3);
  assert.equal(productive.right, trim.right + 3);
  const result = Snap.snapTranslation({
    sourceBounds: trim,
    rawDx: 4.8,
    rawDy: 0,
    targets: { x: [{ axis: "x", value: trim.right + 5, source: "guide", kind: "edge",
      id: "g", order: 0, label: "guide" }], y: [] },
    thresholdMm: 1,
    enabled: true,
  });
  assert.ok(Math.abs(result.dx - 5) <= Geometry.DEFAULT_TOLERANCE_MM);
  assert.equal((moving[1].geometry.position_mm.x_mm + result.dx)
    - (moving[0].geometry.position_mm.x_mm + result.dx), 40);
});

test("measurement keeps canonical positive Y and optional point snap", () => {
  const measurement = Precision.measurement({ x: -1, y: -2 }, { x: 2, y: 2 });
  assert.deepEqual({ dx: measurement.deltaX, dy: measurement.deltaY, distance: measurement.distance },
    { dx: 3, dy: 4, distance: 5 });
  const snapped = Snap.snapPoint({
    point: { x: 9.8, y: 20.2 },
    targets: {
      x: [{ axis: "x", value: 10, source: "guide", kind: "edge", id: "gx", order: 0, label: "guide" }],
      y: [{ axis: "y", value: 20, source: "guide", kind: "edge", id: "gy", order: 1, label: "guide" }],
    },
    thresholdMm: 0.5,
    enabled: true,
  });
  assert.deepEqual(snapped.point, { x: 10, y: 20 });
  assert.equal(snapped.guides.length, 2);
});

test("selection metrics cover one, two, contact, overlap, rotation, references and aggregate", () => {
  const slots = [
    slot("a", 10, 10, { bleed: 2, rotation: 90, size: { width: 20, height: 10 } }),
    slot("b", 25, 10, { bleed: 2, size: { width: 10, height: 10 } }),
    slot("c", 50, 30, { size: { width: 10, height: 10 } }),
    slot("hidden", 10, 10),
    slot("back", 10, 10, { face: "back" }),
  ];
  const layout = layoutWith(slots);
  const one = Precision.selectionMetrics(layout, ["a"], Geometry,
    { reference: "trim", activeFace: "front", hiddenSlotIds: [] });
  assert.equal(one.count, 1);
  assert.equal(one.trimBounds.width, 10);
  assert.equal(one.trimBounds.height, 20);
  assert.equal(one.productiveBounds.width, 14);
  const twoTrim = Precision.selectionMetrics(layout, ["a", "b"], Geometry,
    { reference: "trim", activeFace: "front", hiddenSlotIds: [] });
  assert.equal(twoTrim.pair.gapX, 5);
  assert.equal(twoTrim.pair.overlaps, false);
  const twoProductive = Precision.selectionMetrics(layout, ["a", "b"], Geometry,
    { reference: "productive", activeFace: "front", hiddenSlotIds: [] });
  assert.equal(twoProductive.pair.gapX, 1);
  const many = Precision.selectionMetrics(layout, ["a", "b", "c", "hidden", "back"], Geometry,
    { reference: "trim", activeFace: "front", hiddenSlotIds: ["hidden"] });
  assert.equal(many.count, 3);
  assert.equal(many.aggregate.left, 5);
  assert.equal(many.aggregate.right, 55);
  assert.equal(many.overlapPairs, 0);
  const overlapLayout = layoutWith([slot("x", 10, 10), slot("y", 18, 10)]);
  const overlap = Precision.selectionMetrics(overlapLayout, ["x", "y"], Geometry,
    { reference: "trim", activeFace: "front", hiddenSlotIds: [] });
  assert.equal(overlap.pair.gapX, -12);
  assert.equal(overlap.pair.overlaps, true);
  assert.equal(overlap.pair.overlapArea, 120);
});

test("capturing snap targets for 500 slots is linear, stable and done once per gesture", () => {
  const many = Array.from({ length: 500 }, (_, index) => slot(
    `slot_${index}`,
    10 + (index % 25) * 24,
    10 + Math.floor(index / 25) * 14,
  ));
  const layout = layoutWith(many);
  const started = performance.now();
  const captured = targets(layout, { moving: ["slot_0"], hidden: ["slot_1"] });
  const elapsed = performance.now() - started;
  assert.equal(captured.capturedSlotCount, 498);
  assert.equal(captured.x.filter((item) => item.source === "slot").length, 498 * 3);
  assert.ok(elapsed < 1000, `target capture took ${elapsed.toFixed(1)}ms`);
  const first = Snap.snapTranslation({
    sourceBounds: Geometry.trimBounds(many[0]), rawDx: 1, rawDy: 1,
    targets: captured, thresholdMm: 2, enabled: true,
  });
  const second = Snap.snapTranslation({
    sourceBounds: Geometry.trimBounds(many[0]), rawDx: 1, rawDy: 1,
    targets: captured, thresholdMm: 2, enabled: true,
  });
  assert.deepEqual(first, second);
});
