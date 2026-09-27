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
  unrelated.generated_by = { type: "manual" };
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


test("Repeat records the actual native engine version and undo restores historical metadata", () => {
  const layout = fixture(); layout.slots = [];
  const before = structuredClone(layout.imposition);
  const result = { ...proposal(layout), engine_version: "v2-repeat-1.0.0" };
  const command = new Commands.ApplyRepeatCommand(layout, result, options());
  command.execute(layout);
  assert.equal(layout.imposition.engine_version, result.engine_version);
  command.undo(layout);
  assert.deepEqual(layout.imposition, before);
  command.redo(layout);
  assert.equal(layout.imposition.engine_version, result.engine_version);
  const old = new Commands.ApplyRepeatCommand(fixture(), proposal(fixture()), options());
  assert.equal(old.afterImposition.engine_version, "2.0.0-adapter");
});


test("replacement collision leaves layout, selection and both history stacks untouched", () => {
  const store = new Store.EditorStore(fixture());
  const result = proposal(store.layout);
  result.slots[0].id = store.layout.slots[1].id;
  const before = structuredClone(store.layout);
  const selection = [...store.selection];
  assert.throws(() => store.executeCommand(new Commands.ApplyRepeatCommand(
    store.layout, result, options("replace_work_face"))), /collides/);
  assert.deepEqual(store.layout, before);
  assert.deepEqual([...store.selection], selection);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.redoStack.length, 0);
  assert.equal(store.changeVersion, 0);
});

test("replacement blocks a retained duplicate whose source would disappear", () => {
  const layout = fixture(), before = structuredClone(layout);
  assert.throws(() => new Commands.ApplyRepeatCommand(layout, proposal(layout), options("replace_work_face")), /origen/);
  assert.deepEqual(layout, before);
});

test("invalid proposal scope, source, geometry or transform cannot partially replace", () => {
  for (const mutate of [s => s.face = "back", s => s.work_id = "missing",
    s => s.source.page = 999, s => s.geometry.position_mm.x_mm = NaN,
    s => s.geometry.rotation_deg = 45, s => s.content_transform.scale_x = 0,
    s => s.production.marks_profile_id = "missing"]) {
    const layout = fixture(); layout.slots = layout.slots.slice(0, 1);
    const before = structuredClone(layout), result = proposal(layout);
    mutate(result.slots[0]);
    assert.throws(() => new Commands.ApplyRepeatCommand(layout, result, options("replace_work_face")));
    assert.deepEqual(layout, before);
  }
});

test("execute rechecks collisions and locks after construction; failed redo retains history", () => {
  const layout = fixture(); layout.slots = layout.slots.slice(0, 1);
  const store = new Store.EditorStore(layout);
  const command = new Commands.ApplyRepeatCommand(store.layout, proposal(layout), options("replace_work_face"));
  store.executeCommand(command); store.undo();
  store.layout.slots[0].locks.delete = ["user"];
  const before = structuredClone(store.layout), version = store.changeVersion;
  assert.throws(() => store.redo());
  assert.deepEqual(store.layout, before);
  assert.equal(store.changeVersion, version);
  assert.equal(store.redoStack.length, 1);
  assert.equal(store.undoStack.length, 0);
  store.layout.slots[0].locks.delete = [];
  const collision = structuredClone(command.proposed[0]); collision.face = "back";
  store.layout.slots.push(collision);
  const unchanged = structuredClone(store.layout);
  assert.throws(() => command.execute(store.layout), /collides/);
  assert.deepEqual(store.layout, unchanged);
});

test("proposal preview and projected work counts stay outside layout/history/save tickets", () => {
  const store = new Store.EditorStore(fixture());
  const result = proposal(store.layout, 2);
  const context = { ...options(), jobId: store.layout.job.id, revision: store.revision, changeVersion: store.changeVersion };
  const before = structuredClone(store.layout);
  store.setRepeatState("ready", result, null, context);
  assert.equal(store.getState().repeatPreview.proposal.slots.length, 2);
  assert.equal(store.beginSave(), null);
  assert.equal(store.undoStack.length, 0);
  assert.deepEqual(store.layout, before);
  const added = RepeatPanel.proposalWorkRows(store.layout, result, context)[0];
  const replaced = RepeatPanel.proposalWorkRows(store.layout, result, { ...context, mode: "replace_work_face" })[0];
  assert.equal(added.projected, 3); assert.equal(added.retained, 1);
  assert.equal(replaced.projected, 2); assert.equal(replaced.removed, 1);
  store.changeVersion++;
  assert.equal(store.getState().repeatPreview, null);
});
