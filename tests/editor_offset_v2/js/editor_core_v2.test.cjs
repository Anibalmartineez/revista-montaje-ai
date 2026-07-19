"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const geometry = require(path.join(repoRoot, "static/js/editor_offset_v2/geometry_view.js"));
const commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const { SaveCoordinator } = require(path.join(repoRoot, "static/js/editor_offset_v2/autosave.js"));

function fixture(name) {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2", name),
    "utf8",
  ));
}

function newStore() {
  return new EditorStore(fixture("layout_v2_minimal.json"));
}

function createPlaceholder(store, token = "unit") {
  const bundle = commands.createDevelopmentPlaceholderBundle(
    store.layout,
    token,
    "2026-07-19T00:00:00Z",
  );
  store.executeCommand(new commands.CreateSlotCommand(bundle));
  return bundle;
}

function canonicalResponse(layout, revision) {
  const result = structuredClone(layout);
  result.job.revision = revision;
  result.job.updated_at = `2026-07-19T00:00:0${revision}Z`;
  return { layout: result, revision };
}

test("geometry view matches reusable cardinal fixtures and inverts only SVG Y", () => {
  const cases = fixture("geometry_cases.json");
  for (const item of cases.slot_cases) {
    const slot = {
      geometry: {
        position_mm: { x_mm: item.center.x, y_mm: item.center.y },
        trim_size_mm: item.trim_size,
        bleed_mm: item.bleed,
        rotation_deg: item.rotation_deg,
      },
    };
    assert.deepEqual(
      geometry.orientedSize(item.trim_size, item.rotation_deg),
      item.expected.oriented_trim_size,
      item.id,
    );
    assert.deepEqual(geometry.productiveSize(item.trim_size, item.bleed), item.expected.productive_size);
    assert.deepEqual(geometry.trimBounds(slot), {
      ...item.expected.trim_bounds,
      width: item.expected.trim_bounds.right - item.expected.trim_bounds.left,
      height: item.expected.trim_bounds.top - item.expected.trim_bounds.bottom,
    });
    assert.deepEqual(geometry.bleedBounds(slot), {
      ...item.expected.bleed_bounds,
      width: item.expected.bleed_bounds.right - item.expected.bleed_bounds.left,
      height: item.expected.bleed_bounds.top - item.expected.bleed_bounds.bottom,
    });
  }
  assert.equal(geometry.mmToSvgY(125, 500), 375);
  assert.equal(geometry.svgToMmY(375, 500), 125);
  assert.equal(geometry.svgToMmX(17.25), 17.25);
});

test("store keeps persistent and temporary state separate", () => {
  const store = newStore();
  const original = structuredClone(store.layout);

  store.setSelection([], "replace");
  store.setZoom(2);
  store.setPan({ x: 12, y: -7 });
  store.setCursor({ x: 5, y: 9 });

  assert.deepEqual(store.layout, original);
  assert.equal(store.getState().zoom, 2);
  assert.deepEqual(store.getState().pan, { x: 12, y: -7 });
  assert.equal(Object.hasOwn(store.layout, "selection"), false);
  assert.equal(Object.hasOwn(store.layout, "zoom"), false);
});

test("create, move and delete commands undo and redo without layout snapshots", () => {
  const store = newStore();
  const bundle = createPlaceholder(store);
  assert.equal(store.layout.slots.length, 1);
  assert.equal(store.saveState.status, "dirty");
  assert.deepEqual(store.undoStack[0].affectedIds, [bundle.slot.id]);

  const before = { [bundle.slot.id]: { ...bundle.slot.geometry.position_mm } };
  const after = { [bundle.slot.id]: { x_mm: 411.25, y_mm: 277.5 } };
  store.executeCommand(new commands.MoveSlotsCommand(before, after));
  assert.deepEqual(store.layout.slots[0].geometry.position_mm, {
    x_mm: 411.25,
    y_mm: 277.5,
    anchor: "trim_center",
  });
  store.undo();
  assert.deepEqual(store.layout.slots[0].geometry.position_mm, bundle.slot.geometry.position_mm);
  store.redo();
  assert.equal(store.layout.slots[0].geometry.position_mm.x_mm, 411.25);

  store.executeCommand(new commands.DeleteSlotsCommand(store.layout, [bundle.slot.id]));
  assert.equal(store.layout.slots.length, 0);
  store.undo();
  assert.equal(store.layout.slots[0].id, bundle.slot.id);
});

test("move command rejects non-finite coordinates", () => {
  assert.throws(
    () => new commands.MoveSlotsCommand(
      { slot_a: { x_mm: 1, y_mm: 2 } },
      { slot_a: { x_mm: Number.NaN, y_mm: 3 } },
    ),
    /finite millimetres/,
  );
});

test("pointer preview never mutates persisted slot geometry", () => {
  const store = newStore();
  const bundle = createPlaceholder(store, "preview");
  const persisted = structuredClone(store.layout.slots[0].geometry.position_mm);
  store.beginPointerSession({ type: "move", pointerId: 1, beforePositions: {} });
  store.updatePointerPreview({
    [bundle.slot.id]: { x_mm: persisted.x_mm + 20, y_mm: persisted.y_mm - 10 },
  });

  assert.deepEqual(store.layout.slots[0].geometry.position_mm, persisted);
  assert.notDeepEqual(store.effectivePosition(store.layout.slots[0]), persisted);
  store.endPointerSession();
  assert.deepEqual(store.effectivePosition(store.layout.slots[0]), persisted);
});

test("selection supports replace, add, toggle and filters deleted ids", () => {
  const store = newStore();
  const first = createPlaceholder(store, "select_a");
  const second = commands.createDevelopmentPlaceholderBundle(
    store.layout,
    "select_b",
    "2026-07-19T00:00:00Z",
  );
  store.executeCommand(new commands.CreateSlotCommand(second));

  store.setSelection([first.slot.id], "replace");
  store.setSelection([second.slot.id], "add");
  assert.deepEqual(new Set(store.getState().selection), new Set([first.slot.id, second.slot.id]));
  store.setSelection([first.slot.id], "toggle");
  assert.deepEqual(store.getState().selection, [second.slot.id]);
  store.executeCommand(new commands.DeleteSlotsCommand(store.layout, [second.slot.id]));
  assert.deepEqual(store.getState().selection, []);
});

test("undo and redo remain dirty even when visual state returns", () => {
  const store = newStore();
  createPlaceholder(store, "dirty");
  store.undo();
  assert.equal(store.layout.slots.length, 0);
  assert.equal(store.saveState.status, "dirty");
  assert.equal(store.hasUnsavedChanges(), true);
  store.redo();
  assert.equal(store.layout.slots.length, 1);
  assert.equal(store.saveState.status, "dirty");
});

test("save coordinator serializes saves and preserves edits made in flight", async () => {
  const store = newStore();
  const bundle = createPlaceholder(store, "serial");
  let firstResolve;
  let calls = 0;
  const api = {
    async saveLayout(_url, baseRevision, layout) {
      calls += 1;
      if (calls === 1) {
        await new Promise((resolve) => { firstResolve = resolve; });
      }
      return canonicalResponse(layout, baseRevision + 1);
    },
  };
  const saver = new SaveCoordinator(store, api, "/save", { debounceMs: 2 });
  const firstSave = saver.performSave();
  await new Promise((resolve) => setImmediate(resolve));
  const position = { ...store.layout.slots[0].geometry.position_mm };
  store.executeCommand(new commands.MoveSlotsCommand(
    { [bundle.slot.id]: { ...position } },
    { [bundle.slot.id]: { x_mm: position.x_mm + 5, y_mm: position.y_mm + 4 } },
  ));
  assert.equal(calls, 1);
  firstResolve();
  await firstSave;
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.equal(calls, 2);
  assert.equal(store.revision, 2);
  assert.equal(store.saveState.status, "clean");
  assert.equal(store.layout.slots[0].geometry.position_mm.x_mm, position.x_mm + 5);
  saver.dispose();
});

test("409 marks conflict and never replaces local layout", async () => {
  const store = newStore();
  createPlaceholder(store, "conflict");
  const local = structuredClone(store.layout);
  const api = {
    async saveLayout() {
      const error = new Error("La revisión remota cambió.");
      error.status = 409;
      throw error;
    },
  };
  const saver = new SaveCoordinator(store, api, "/save", { debounceMs: 1000 });

  assert.equal(await saver.manualSave(), false);
  assert.equal(store.saveState.status, "conflict");
  assert.deepEqual(store.layout, local);
  assert.equal(store.revision, local.job.revision);
  saver.dispose();
});

test("save coordinator never saves during an active pointer session", async () => {
  const store = newStore();
  createPlaceholder(store, "pointer_save");
  let calls = 0;
  const api = {
    async saveLayout() {
      calls += 1;
      throw new Error("must not run");
    },
  };
  const saver = new SaveCoordinator(store, api, "/save", { debounceMs: 1000 });
  store.beginPointerSession({ type: "move", pointerId: 1, beforePositions: {} });

  assert.equal(await saver.manualSave(), false);
  assert.equal(calls, 0);
  assert.equal(store.saveState.status, "dirty");
  saver.dispose();
});
