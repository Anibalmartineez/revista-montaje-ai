const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const Commands = require(path.resolve("static/js/editor_offset_v2/commands.js"));
const Store = require(path.resolve("static/js/editor_offset_v2/store.js"));
const Autosave = require(path.resolve("static/js/editor_offset_v2/autosave.js"));
const RepeatPanel = require(path.resolve("static/js/editor_offset_v2/repeat_panel.js"));

function fixture() {
  return JSON.parse(fs.readFileSync(
    path.resolve("tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
    "utf8",
  ));
}

function proposal(layout, count = 2) {
  const base = structuredClone(layout.slots[0] || fixture().slots[0]);
  const slots = Array.from({ length: count }, (_, index) => ({
    ...structuredClone(base),
    id: `slot_repeat_test_${index + 1}`,
    geometry: {
      ...structuredClone(base.geometry),
      position_mm: {
        ...structuredClone(base.geometry.position_mm),
        x_mm: 150 + index * 100,
      },
    },
    generated_by: {
      type: "engine",
      engine: "repeat",
      operation_id: "repeat_test",
    },
  }));
  return {
    success: true,
    operation_id: "repeat_test",
    generated_at: "2026-07-19T12:00:00Z",
    slots,
    requested: count,
    placed: count,
    unplaced: 0,
    overproduced: 0,
    warnings: [],
    metrics: { utilization_percent: 10 },
    issues: [],
  };
}

function options(mode = "add") {
  return {
    mode,
    workIds: ["work_card"],
    face: "front",
    settings: {
      horizontal_gap_mm: 4,
      vertical_gap_mm: 3,
      exact_quantity: true,
      fill_remaining_space: false,
      allow_partial: false,
    },
  };
}

test("ApplyRepeatCommand adds one atomic proposal and undo/redo restores imposition", () => {
  const layout = fixture();
  layout.slots = [];
  layout.imposition.last_result = null;
  const beforeImposition = structuredClone(layout.imposition);
  const store = new Store.EditorStore(layout);
  const result = proposal(layout);

  store.executeCommand(new Commands.ApplyRepeatCommand(store.layout, result, options()));

  assert.equal(store.layout.slots.length, 2);
  assert.equal(store.layout.imposition.last_result.operation_id, "repeat_test");
  assert.equal(store.saveState.status, "dirty");
  assert.equal(store.undoStack.length, 1);
  store.undo();
  assert.deepEqual(store.layout.slots, []);
  assert.deepEqual(store.layout.imposition, beforeImposition);
  store.redo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.id), result.slots.map((slot) => slot.id));
});

test("replace mode preserves unrelated slots and restores replaced entries on undo", () => {
  const layout = fixture();
  const replaced = structuredClone(layout.slots[0]);
  const unrelated = structuredClone(layout.slots[1]);
  layout.slots = [replaced, unrelated];
  const store = new Store.EditorStore(layout);
  const result = proposal(layout, 3);

  store.executeCommand(new Commands.ApplyRepeatCommand(
    store.layout,
    result,
    options("replace_work_face"),
  ));

  assert.equal(store.layout.slots.length, 4);
  assert.ok(store.layout.slots.some((slot) => slot.id === unrelated.id));
  assert.ok(!store.layout.slots.some((slot) => slot.id === replaced.id));
  store.undo();
  assert.deepEqual(store.layout.slots, [replaced, unrelated]);
  store.redo();
  assert.equal(store.layout.slots.filter((slot) => slot.face === "front").length, 3);
});

test("failed or empty Repeat results cannot mutate the layout", () => {
  const layout = fixture();
  const before = structuredClone(layout);

  assert.throws(
    () => new Commands.ApplyRepeatCommand(layout, { success: false, slots: [] }, options()),
    /successful non-empty proposal/,
  );
  assert.deepEqual(layout, before);
});

test("partial successful proposal is applied with incomplete trace and remains reversible", () => {
  const layout = fixture();
  layout.slots = [];
  const result = proposal(layout, 1);
  Object.assign(result, {
    requested: 4,
    placed: 1,
    unplaced: 3,
    warnings: ["Propuesta parcial"],
  });
  const command = new Commands.ApplyRepeatCommand(layout, result, options());

  command.execute(layout);
  assert.equal(layout.imposition.last_result.status, "incomplete");
  assert.equal(layout.imposition.last_result.unplaced, 3);
  command.undo(layout);
  assert.equal(layout.slots.length, 0);
});

test("Repeat temporary state is outside layout and ApplyRepeatCommand triggers autosave", async () => {
  const layout = fixture();
  layout.slots = [];
  const store = new Store.EditorStore(layout);
  const saved = [];
  const api = {
    async saveLayout(_url, revision, submitted) {
      saved.push(structuredClone(submitted));
      const canonical = structuredClone(submitted);
      canonical.job.revision = revision + 1;
      return { layout: canonical };
    },
  };
  const saver = new Autosave.SaveCoordinator(store, api, "/save", { debounceMs: 1 });
  const result = proposal(layout, 1);

  store.setRepeatState("ready", result, null);
  assert.equal(Object.hasOwn(store.layout, "repeatPanel"), false);
  store.executeCommand(new Commands.ApplyRepeatCommand(store.layout, result, options()));
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.equal(saved.length, 1);
  assert.equal(saved[0].slots.length, 1);
  assert.equal(store.saveState.status, "clean");
  saver.dispose();
});

test("Repeat panel helpers read configuration and selected works deterministically", () => {
  const refs = {
    repeatGapX: { value: "4.5" },
    repeatGapY: { value: "3" },
    repeatExact: { checked: true },
    repeatFill: { checked: false },
    repeatPartial: { checked: true },
  };
  const container = {
    querySelectorAll() {
      return [{ checked: true, value: "work_a" }, { checked: true, value: "work_b" }];
    },
  };

  assert.deepEqual(RepeatPanel.readSettings(refs), {
    horizontal_gap_mm: 4.5,
    vertical_gap_mm: 3,
    exact_quantity: true,
    fill_remaining_space: false,
    allow_partial: true,
  });
  assert.deepEqual(RepeatPanel.selectedWorkIds(container), ["work_a", "work_b"]);
});
