"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Advanced = require(path.join(repoRoot, "static/js/editor_offset_v2/advanced_selection.js"));
const Geometry = require(path.join(repoRoot, "static/js/editor_offset_v2/geometry_view.js"));
const ObjectOperations = require(path.join(repoRoot, "static/js/editor_offset_v2/object_operations.js"));
const ObjectTree = require(path.join(repoRoot, "static/js/editor_offset_v2/object_tree.js"));
const RegistryModule = require(path.join(repoRoot, "static/js/editor_offset_v2/command_registry.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));

function fixture() {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
    "utf8",
  ));
}

function layoutWithSlots(specifications) {
  const layout = fixture();
  const base = structuredClone(layout.slots.find((slot) => slot.face === "front"));
  layout.sheet.size_mm = { width: 300, height: 200 };
  layout.sheet.printable_margins_mm = { left: 20, right: 30, bottom: 15, top: 25 };
  const baseWork = structuredClone(layout.works[0]);
  const secondWork = structuredClone(baseWork);
  secondWork.id = "work_second";
  secondWork.name = "Segundo work";
  layout.works = [baseWork, secondWork];
  layout.faces.enabled = ["front", "back"];
  layout.faces.duplex = { enabled: true, flip: "long_edge" };
  layout.slots = specifications.map((specification, index) => {
    const slot = structuredClone(base);
    slot.id = specification.id || `slot_8d_${index + 1}`;
    slot.face = specification.face || "front";
    slot.work_id = specification.workId || baseWork.id;
    slot.source.asset_id = specification.assetId || base.source.asset_id;
    slot.geometry.position_mm = {
      x_mm: specification.x,
      y_mm: specification.y,
      anchor: "trim_center",
    };
    slot.geometry.trim_size_mm = {
      width: specification.width || 20,
      height: specification.height || 10,
    };
    slot.geometry.bleed_mm = specification.bleed ?? 0;
    slot.geometry.rotation_deg = specification.rotation || 0;
    slot.generated_by = specification.generatedBy || { type: "manual" };
    slot.locks = specification.locks || {
      geometry: [], content: [], production: [], delete: [],
    };
    return slot;
  });
  return layout;
}

function context(store) {
  return {
    store,
    objectOperations: ObjectOperations,
    advancedSelection: Advanced,
    geometry: Geometry,
    editPolicy: require(path.join(repoRoot, "static/js/editor_offset_v2/edit_policy.js")),
    alignmentOperations: require(path.join(repoRoot, "static/js/editor_offset_v2/alignment_operations.js")),
    commands: require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js")),
    interactions: {
      hasPanSession: () => false,
      hasPointerActivity: () => false,
      cancelPointer: () => {},
    },
  };
}

test("temporary selection, marquee, tree and visibility state never dirty layout or history", () => {
  const layout = layoutWithSlots([
    { id: "a", x: 40, y: 40 }, { id: "b", x: 80, y: 40 },
  ]);
  const persisted = structuredClone(layout);
  const store = new EditorStore(layout);
  const revision = store.revision;
  store.setSelection(["a"], "replace");
  store.setMarqueeMode("intersect");
  store.setMarqueeRect({ left: 0, right: 10, bottom: 0, top: 10, width: 10, height: 10 });
  store.setTreeExpanded("work", layout.works[0].id, false);
  store.setTreeAnchor("a");
  store.setSelectionCycle({ point: { x: 40, y: 40 }, candidateIds: ["a"], index: 0 });
  store.hideSlots(["a"], { capturePrevious: true });
  assert.deepEqual(store.layout, persisted);
  assert.equal(store.revision, revision);
  assert.equal(store.changeVersion, 0);
  assert.equal(store.hasUnsavedChanges(), false);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.redoStack.length, 0);
  assert.equal(store.selection.size, 0);
  assert.equal(store.isSlotHidden("a"), true);
  assert.equal(store.advancedSelection.cycle, null);
});

test("marquee inclusion and intersection share trim/productive cardinal bounds and modifiers", () => {
  const layout = layoutWithSlots([
    { id: "r0", x: 30, y: 30, width: 20, height: 10, bleed: 3 },
    { id: "r90", x: 65, y: 30, width: 20, height: 10, rotation: 90, bleed: 3 },
    { id: "back", x: 30, y: 30, face: "back" },
  ]);
  const trimCandidates = Advanced.captureMarqueeCandidates(
    layout, "front", [], Geometry, "trim",
  );
  const productiveCandidates = Advanced.captureMarqueeCandidates(
    layout, "front", [], Geometry, "productive",
  );
  const rectangle = Advanced.rectangleFromPoints({ x: 20, y: 24 }, { x: 40, y: 36 });
  assert.deepEqual(Advanced.matchingMarqueeIds(trimCandidates, rectangle, "contain"), ["r0"]);
  assert.deepEqual(Advanced.matchingMarqueeIds(productiveCandidates, rectangle, "contain"), []);
  assert.deepEqual(Advanced.matchingMarqueeIds(productiveCandidates, rectangle, "intersect"), ["r0"]);
  assert.deepEqual(
    Advanced.captureMarqueeCandidates(layout, "front", ["r0"], Geometry, "trim").map((item) => item.id),
    ["r90"],
  );
  assert.equal(Advanced.selectionModeFromModifiers({}, false), "replace");
  assert.equal(Advanced.selectionModeFromModifiers({ shiftKey: true }, false), "add");
  assert.equal(Advanced.selectionModeFromModifiers({ ctrlKey: true }, false), "toggle");
  assert.equal(Advanced.selectionModeFromModifiers({ metaKey: true }, false), "toggle");
  assert.equal(Advanced.selectionModeFromModifiers({ altKey: true }, false), "subtract");
  assert.equal(Advanced.selectionModeFromModifiers({ altKey: true }, true), "replace");
  assert.deepEqual(Advanced.applySelectionMode(["r0"], ["r90"], "add"), ["r0", "r90"]);
  assert.deepEqual(Advanced.applySelectionMode(["r0", "r90"], ["r0"], "toggle"), ["r90"]);
  assert.deepEqual(Advanced.applySelectionMode(["r0", "r90"], ["r0"], "subtract"), ["r90"]);
});

test("cycle follows top-to-bottom render order and resets by point, layout or visibility", () => {
  const layout = layoutWithSlots([
    { id: "bottom", x: 50, y: 50 },
    { id: "middle", x: 50, y: 50 },
    { id: "top", x: 50, y: 50 },
    { id: "back", x: 50, y: 50, face: "back" },
  ]);
  const base = {
    layout, activeFace: "front", hiddenSlotIds: [], geometry: Geometry,
    reference: "trim", point: { x: 50, y: 50 }, currentSlotId: "top",
    layoutVersion: 0, visibilityVersion: 0,
  };
  const first = Advanced.cycleAtPoint(base);
  assert.equal(first.selectedId, "middle");
  assert.deepEqual(first.cycle.candidateIds, ["top", "middle", "bottom"]);
  const second = Advanced.cycleAtPoint({ ...base, previousCycle: first.cycle });
  const third = Advanced.cycleAtPoint({ ...base, previousCycle: second.cycle });
  assert.equal(second.selectedId, "bottom");
  assert.equal(third.selectedId, "top");
  assert.equal(Advanced.cycleAtPoint({ ...base, previousCycle: third.cycle, point: { x: 55, y: 50 } }).selectedId, "middle");
  assert.equal(Advanced.cycleAtPoint({ ...base, previousCycle: first.cycle, layoutVersion: 1 }).selectedId, "middle");
  assert.equal(Advanced.cycleAtPoint({ ...base, previousCycle: first.cycle, visibilityVersion: 1 }).selectedId, "middle");
  assert.deepEqual(Advanced.hitTestSlots(layout, "front", ["top"], Geometry, "trim", base.point), ["middle", "bottom"]);
});

test("similar selections use unions, effective asset, persisted trim, cardinal rotation and provenance", () => {
  const layout = layoutWithSlots([
    { id: "a", x: 20, y: 20, width: 20, height: 10, workId: layoutWorkId(0), generatedBy: { type: "manual" } },
    { id: "b", x: 50, y: 20, width: 20 + 5e-10, height: 10, workId: "work_second", rotation: 90, generatedBy: { type: "engine", engine: "repeat" } },
    { id: "c", x: 80, y: 20, width: 30, height: 10, workId: "work_second", rotation: 90, generatedBy: { type: "duplicate", source_slot_id: "b" } },
    { id: "back", x: 20, y: 20, face: "back", width: 20, height: 10 },
  ]);
  layout.slots[1].source.asset_id = "asset_override";
  layout.assets.push({ ...structuredClone(layout.assets[0]), id: "asset_override" });
  assert.deepEqual(Advanced.selectSimilar(layout, ["a", "b"], "front", [], "work"), ["a", "b", "c"]);
  assert.deepEqual(Advanced.selectSimilar(layout, ["b"], "front", [], "asset"), ["b"]);
  assert.deepEqual(Advanced.selectSimilar(layout, ["a"], "front", [], "size"), ["a", "b"]);
  assert.deepEqual(Advanced.selectSimilar(layout, ["b"], "front", ["c"], "rotation"), ["b"]);
  assert.deepEqual(Advanced.selectSimilar(layout, ["a", "c"], "front", [], "provenance"), ["a", "c"]);
});

function layoutWorkId() {
  return fixture().works[0].id;
}

test("effective lock selection accepts user, engine, ctp and system without duplicates", () => {
  const surfaces = ["geometry", "content", "delete"];
  const sources = ["user", "engine", "ctp", "system"];
  const specs = sources.map((source, index) => ({
    id: source,
    x: 20 + index * 30,
    y: 30,
    locks: {
      geometry: [source], content: index % 2 ? [source] : [], production: [], delete: [source],
    },
  }));
  const layout = layoutWithSlots(specs);
  assert.deepEqual(Advanced.selectLocked(layout, "front", [], "geometry"), sources);
  assert.deepEqual(Advanced.selectLocked(layout, "front", [], "content"), ["engine", "system"]);
  assert.deepEqual(Advanced.selectLocked(layout, "front", ["ctp"], "delete"), ["user", "engine", "system"]);
  assert.deepEqual(surfaces, ["geometry", "content", "delete"]);
});

test("current geometry issues select both overlap participants and distinguish sheet/printable", () => {
  const layout = layoutWithSlots([
    { id: "overlap_a", x: 60, y: 60, width: 30, height: 20 },
    { id: "overlap_b", x: 70, y: 60, width: 30, height: 20 },
    { id: "outside_printable", x: 10, y: 100, width: 10, height: 10 },
    { id: "outside_sheet", x: 302, y: 100, width: 10, height: 10 },
    { id: "touch", x: 90, y: 60, width: 10, height: 20 },
  ]);
  const index = Advanced.geometryIssueIndex(layout, "front", [], Geometry, "trim");
  assert.deepEqual(Advanced.selectGeometryIssues(index, "overlap"), ["overlap_a", "overlap_b"]);
  assert.deepEqual(Advanced.selectGeometryIssues(index, "outside_sheet"), ["outside_sheet"]);
  assert.deepEqual(Advanced.selectGeometryIssues(index, "outside_printable"), ["outside_printable"]);
  assert.deepEqual(
    new Set(Advanced.selectGeometryIssues(index, "any")),
    new Set(["overlap_a", "overlap_b", "outside_printable", "outside_sheet"]),
  );
  const hiddenIndex = Advanced.geometryIssueIndex(layout, "front", ["overlap_b"], Geometry, "trim");
  assert.deepEqual(Advanced.selectGeometryIssues(hiddenIndex, "overlap"), []);
});

test("tree hierarchy and ranges preserve layout order and never cross works", () => {
  const layout = layoutWithSlots([
    { id: "a", x: 20, y: 20 },
    { id: "b", x: 50, y: 20 },
    { id: "c", x: 80, y: 20, workId: "work_second" },
    { id: "d", x: 110, y: 20, workId: "work_second" },
  ]);
  const groups = ObjectTree.workGroups(layout, "front");
  assert.deepEqual(groups.map((group) => group.slots.map((slot) => slot.id)), [["a", "b"], ["c", "d"]]);
  assert.deepEqual(ObjectTree.rangeSelection(layout, "front", [], "a", "b"), ["a", "b"]);
  assert.deepEqual(ObjectTree.rangeSelection(layout, "front", [], "a", "d"), ["d"]);
  assert.deepEqual(ObjectTree.rangeSelection(layout, "front", ["b"], "a", "b"), ["b"]);
  assert.equal(ObjectTree.workVisibilityState(groups[0].slots, []), "visible");
  assert.equal(ObjectTree.workVisibilityState(groups[0].slots, ["a"]), "mixed");
  assert.equal(ObjectTree.workVisibilityState(groups[0].slots, ["a", "b"]), "hidden");
});

test("visibility actions hide, isolate, show, restore, toggle slot/work and clean key selection", () => {
  const layout = layoutWithSlots([
    { id: "a", x: 20, y: 20 },
    { id: "b", x: 50, y: 20 },
    { id: "c", x: 80, y: 20, workId: "work_second" },
  ]);
  const store = new EditorStore(layout);
  const registry = new RegistryModule.ActionRegistry();
  RegistryModule.registerEditorActions(registry);
  const ctx = context(store);
  let nudgeCancelled = 0;
  ctx.nudgeController = { cancel: () => { nudgeCancelled += 1; } };
  store.setSelection(["a"], "replace");
  store.setKeySlot("a");
  registry.execute(RegistryModule.ACTION_IDS.VISIBILITY_HIDE_SELECTION, ctx);
  assert.deepEqual([...store.advancedSelection.hiddenSlotIds], ["a"]);
  assert.equal(store.selection.size, 0);
  assert.equal(store.arrangement.keySlotId, null);
  assert.equal(nudgeCancelled, 1);
  store.setSelection(["b"], "replace");
  registry.execute(RegistryModule.ACTION_IDS.VISIBILITY_ISOLATE_SELECTION, ctx);
  assert.deepEqual(new Set(store.advancedSelection.hiddenSlotIds), new Set(["a", "c"]));
  registry.execute(RegistryModule.ACTION_IDS.VISIBILITY_SHOW_ALL, ctx);
  assert.equal(store.advancedSelection.hiddenSlotIds.size, 0);
  registry.execute(RegistryModule.ACTION_IDS.VISIBILITY_RESTORE_PREVIOUS, ctx);
  assert.deepEqual(new Set(store.advancedSelection.hiddenSlotIds), new Set(["a", "c"]));
  registry.execute(RegistryModule.ACTION_IDS.VISIBILITY_SLOT_TOGGLE, ctx, { slotId: "a" });
  assert.equal(store.isSlotHidden("a"), false);
  registry.execute(RegistryModule.ACTION_IDS.VISIBILITY_WORK_TOGGLE, ctx, { workId: "work_second" });
  assert.equal(store.isSlotHidden("c"), false);
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
});

test("8D actions are unique, registered and selection actions remain temporary", () => {
  const layout = layoutWithSlots([
    { id: "a", x: 20, y: 20 }, { id: "b", x: 20, y: 20 },
  ]);
  const store = new EditorStore(layout);
  const registry = new RegistryModule.ActionRegistry();
  RegistryModule.registerEditorActions(registry);
  const ids = registry.list().map((action) => action.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of [
    RegistryModule.ACTION_IDS.MARQUEE_MODE_SET,
    RegistryModule.ACTION_IDS.CYCLE_AT_POINT,
    RegistryModule.ACTION_IDS.SELECT_SAME_SIZE,
    RegistryModule.ACTION_IDS.SELECT_LOCKED_GEOMETRY,
    RegistryModule.ACTION_IDS.SELECT_OVERLAPS,
    RegistryModule.ACTION_IDS.VISIBILITY_HIDE_SELECTION,
    RegistryModule.ACTION_IDS.VISIBILITY_WORK_TOGGLE,
  ]) assert.ok(registry.get(id), id);
  const ctx = context(store);
  store.setSelection(["a"], "replace");
  registry.execute(RegistryModule.ACTION_IDS.CYCLE_AT_POINT, ctx, {
    point: { x: 20, y: 20 }, currentSlotId: "a", additive: true,
  });
  assert.deepEqual([...store.selection], ["a", "b"]);
  store.setSelection(["a"], "replace");
  registry.execute(RegistryModule.ACTION_IDS.SELECT_SAME_SIZE, ctx);
  registry.execute(RegistryModule.ACTION_IDS.MARQUEE_MODE_SET, ctx, { mode: "intersect" });
  assert.deepEqual([...store.selection], ["a", "b"]);
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
});

test("five hundred slots remain deterministic without document mutations or listener state", () => {
  const specifications = Array.from({ length: 500 }, (_, index) => ({
    id: `many_${String(index + 1).padStart(3, "0")}`,
    x: 5 + (index % 25) * 11,
    y: 5 + Math.floor(index / 25) * 9,
    width: 8,
    height: 6,
  }));
  const layout = layoutWithSlots(specifications);
  const store = new EditorStore(layout);
  const candidates = Advanced.captureMarqueeCandidates(layout, "front", [], Geometry, "trim");
  const rectangle = Advanced.rectangleFromPoints({ x: 0, y: 0 }, { x: 300, y: 200 });
  const selected = Advanced.matchingMarqueeIds(candidates, rectangle, "contain");
  const groups = ObjectTree.workGroups(layout, "front");
  assert.equal(candidates.length, 500);
  assert.equal(selected.length, 500);
  assert.equal(groups.reduce((total, group) => total + group.slots.length, 0), 500);
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
  assert.equal(new EditorStore(structuredClone(store.layout)).advancedSelection.hiddenSlotIds.size, 0);
});
