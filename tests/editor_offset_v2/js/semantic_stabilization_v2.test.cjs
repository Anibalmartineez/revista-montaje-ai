"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const EditPolicy = require(path.join(repoRoot, "static/js/editor_offset_v2/edit_policy.js"));
const SourceSemantics = require(path.join(repoRoot, "static/js/editor_offset_v2/source_semantics.js"));
const LayoutMetrics = require(path.join(repoRoot, "static/js/editor_offset_v2/layout_metrics.js"));
const Geometry = require(path.join(repoRoot, "static/js/editor_offset_v2/geometry_view.js"));
const CanvasRenderer = require(path.join(repoRoot, "static/js/editor_offset_v2/canvas_renderer.js"));
const OutputPanel = require(path.join(repoRoot, "static/js/editor_offset_v2/output_panel.js"));
const RepeatPanel = require(path.join(repoRoot, "static/js/editor_offset_v2/repeat_panel.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const { SaveCoordinator } = require(path.join(repoRoot, "static/js/editor_offset_v2/autosave.js"));

function fixture() {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
    "utf8",
  ));
}

function unlockedFrontSlot(layout, id = "slot_editable") {
  const slot = structuredClone(layout.slots.find((item) => item.face === "front"));
  slot.id = id;
  slot.locks = { geometry: [], content: [], production: [], delete: [] };
  return slot;
}

function positions(slots, delta = 0) {
  return Object.fromEntries(slots.map((slot) => [slot.id, {
    x_mm: slot.geometry.position_mm.x_mm + delta,
    y_mm: slot.geometry.position_mm.y_mm + delta,
  }]));
}

function repeatResult(slot) {
  const proposed = structuredClone(slot);
  proposed.id = "slot_repeat_editable";
  proposed.locks.geometry = [];
  proposed.generated_by = {
    type: "engine",
    engine: "repeat",
    operation_id: "repeat_semantic",
  };
  return {
    success: true,
    operation_id: "repeat_semantic",
    generated_at: "2026-07-19T12:00:00Z",
    slots: [proposed],
    requested: 1,
    placed: 1,
    unplaced: 0,
    overproduced: 0,
    warnings: [],
    metrics: {
      utilization_percent: 5,
      proposal_utilization_pct: 5,
      projected_total_utilization_pct: 10,
    },
    issues: [],
  };
}

function repeatOptions(mode = "add") {
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

test("central policy treats every valid lock source as a real geometry lock", () => {
  for (const source of ["user", "engine", "ctp", "system"]) {
    const layout = fixture();
    const slot = unlockedFrontSlot(layout, `slot_${source}`);
    slot.locks.geometry = [source];
    layout.slots = [slot];

    assert.deepEqual(EditPolicy.blockedSlotIds(layout, [slot.id], "move"), [slot.id]);
    assert.throws(
      () => new Commands.MoveSlotsCommand(positions([slot]), positions([slot], 5)).execute(layout),
      (error) => error.code === "SLOT_EDIT_LOCKED"
        && error.blockedIds.includes(slot.id),
    );
  }
});

test("multi-slot movement is atomic when one selected slot is locked", () => {
  const layout = fixture();
  const editable = unlockedFrontSlot(layout, "slot_editable");
  const locked = unlockedFrontSlot(layout, "slot_locked");
  locked.geometry.position_mm.x_mm += 100;
  locked.locks.geometry = ["system"];
  layout.slots = [editable, locked];
  const before = structuredClone(layout.slots);

  const command = new Commands.MoveSlotsCommand(
    positions(layout.slots),
    positions(layout.slots, 12),
  );
  assert.throws(() => command.execute(layout), /slot_locked/);
  assert.deepEqual(layout.slots, before);
});

test("delete, content and Repeat replace locks reject their whole operation", () => {
  const layout = fixture();
  const editable = unlockedFrontSlot(layout, "slot_editable");
  const lockedDelete = unlockedFrontSlot(layout, "slot_delete_locked");
  lockedDelete.geometry.position_mm.x_mm += 100;
  lockedDelete.locks.delete = ["user"];
  layout.slots = [editable, lockedDelete];
  const before = structuredClone(layout.slots);

  assert.throws(
    () => new Commands.DeleteSlotsCommand(layout, [editable.id, lockedDelete.id]),
    /slot_delete_locked/,
  );
  assert.deepEqual(layout.slots, before);
  assert.throws(
    () => new Commands.ApplyRepeatCommand(
      layout,
      repeatResult(editable),
      repeatOptions("replace_work_face"),
    ),
    /slot_delete_locked/,
  );
  assert.deepEqual(layout.slots, before);

  editable.locks.content = ["ctp"];
  const replacement = {
    asset_id: layout.assets[1].id,
    page: 1,
    pdf_box: "trim",
  };
  assert.throws(
    () => new Commands.ReplaceSlotSourceCommand(layout, editable.id, replacement),
    /slot_editable/,
  );
  assert.deepEqual(layout.slots, before.map((slot, index) => (
    index === 0 ? { ...slot, locks: { ...slot.locks, content: ["ctp"] } } : slot
  )));
});

test("Repeat provenance remains historical while its normal slot stays editable", async () => {
  const layout = fixture();
  const base = unlockedFrontSlot(layout);
  layout.slots = [];
  layout.imposition.last_result = null;
  const store = new EditorStore(layout);
  const result = repeatResult(base);
  store.executeCommand(new Commands.ApplyRepeatCommand(store.layout, result, repeatOptions()));
  const slot = store.layout.slots[0];
  assert.deepEqual(slot.locks.geometry, []);
  assert.deepEqual(slot.generated_by, result.slots[0].generated_by);

  const saved = [];
  const saver = new SaveCoordinator(store, {
    async saveLayout(_url, revision, submitted) {
      const canonical = structuredClone(submitted);
      canonical.job.revision = revision + 1;
      saved.push(canonical);
      return { layout: canonical };
    },
  }, "/save", { debounceMs: 1 });
  const before = positions([slot]);
  const after = positions([slot], 7);
  store.executeCommand(new Commands.MoveSlotsCommand(before, after));
  store.undo();
  store.redo();
  await new Promise((resolve) => setTimeout(resolve, 25));

  assert.deepEqual(store.layout.slots[0].geometry.position_mm.x_mm, after[slot.id].x_mm);
  assert.equal(store.layout.slots[0].generated_by.operation_id, "repeat_semantic");
  assert.equal(store.saveState.status, "clean");
  assert.ok(saved.length >= 1);
  saver.dispose();
});

test("slot source override is derived and undo restores it without changing work defaults", () => {
  const layout = fixture();
  const slot = unlockedFrontSlot(layout);
  layout.slots = [slot];
  const workBefore = structuredClone(layout.works[0]);
  assert.equal(SourceSemantics.hasSourceOverride(layout, slot), false);
  const replacement = { asset_id: layout.assets[1].id, page: 1, pdf_box: "trim" };
  const command = new Commands.ReplaceSlotSourceCommand(layout, slot.id, replacement);

  command.execute(layout);
  assert.equal(SourceSemantics.hasSourceOverride(layout, slot), true);
  assert.deepEqual(layout.works[0], workBefore);
  command.undo(layout);
  assert.equal(SourceSemantics.hasSourceOverride(layout, slot), false);
  command.redo(layout);
  assert.equal(SourceSemantics.hasSourceOverride(layout, slot), true);
});

test("saving and reloading preserves the effective slot source override", async () => {
  const layout = fixture();
  layout.slots = [unlockedFrontSlot(layout)];
  const workBefore = structuredClone(layout.works[0]);
  const store = new EditorStore(layout);
  let persisted = null;
  const saver = new SaveCoordinator(store, {
    async saveLayout(_url, revision, submitted) {
      persisted = structuredClone(submitted);
      persisted.job.revision = revision + 1;
      return { layout: persisted };
    },
  }, "/save", { debounceMs: 1 });
  const replacement = { asset_id: layout.assets[1].id, page: 1, pdf_box: "trim" };

  store.executeCommand(new Commands.ReplaceSlotSourceCommand(
    store.layout,
    store.layout.slots[0].id,
    replacement,
  ));
  await new Promise((resolve) => setTimeout(resolve, 20));
  const reloaded = new EditorStore(persisted);

  assert.deepEqual(reloaded.layout.slots[0].source, replacement);
  assert.deepEqual(reloaded.layout.works[0], workBefore);
  assert.equal(SourceSemantics.hasSourceOverride(
    reloaded.layout,
    reloaded.layout.slots[0],
  ), true);
  saver.dispose();
});

test("historical Repeat result remains unchanged while current counts follow real slots", () => {
  const layout = fixture();
  const first = unlockedFrontSlot(layout, "slot_last_1");
  const second = unlockedFrontSlot(layout, "slot_last_2");
  second.geometry.position_mm.x_mm += 100;
  for (const slot of [first, second]) {
    slot.generated_by = { type: "engine", engine: "repeat", operation_id: "repeat_old" };
  }
  layout.slots = [first, second];
  layout.imposition.last_result = {
    operation_id: "repeat_old",
    status: "complete",
    requested: 2,
    placed: 2,
    unplaced: 0,
    overproduced: 0,
    generated_at: "2026-07-19T12:00:00Z",
    warnings: [],
  };
  const historical = structuredClone(layout.imposition.last_result);

  layout.slots.pop();
  const current = LayoutMetrics.currentSlotMetrics(layout, "front");
  assert.deepEqual(layout.imposition.last_result, historical);
  assert.equal(current.total, 1);
  assert.equal(current.byWork.work_card, 1);
  assert.equal(current.lastOperationPresent, 1);
});

test("printable area distinguishes sheet and printable boundary with bleed and rotation", () => {
  const layout = fixture();
  const slot = unlockedFrontSlot(layout);
  const sheet = {
    size_mm: { width: 200, height: 120 },
    printable_margins_mm: { left: 10, right: 20, bottom: 5, top: 15 },
  };
  assert.deepEqual(Geometry.printableBounds(sheet), {
    left: 10,
    right: 180,
    bottom: 5,
    top: 105,
    width: 170,
    height: 100,
  });
  assert.deepEqual(Geometry.printableBounds({
    size_mm: { width: 200, height: 120 },
    printable_margins_mm: { left: 0, right: 0, bottom: 0, top: 0 },
  }), { left: 0, right: 200, bottom: 0, top: 120, width: 200, height: 120 });

  slot.geometry.trim_size_mm = { width: 40, height: 20 };
  slot.geometry.bleed_mm = 3;
  slot.geometry.rotation_deg = 90;
  slot.geometry.position_mm = { x_mm: 30, y_mm: 30, anchor: "trim_center" };
  assert.equal(Geometry.classifySlotPlacement(slot, sheet), "inside");
  slot.geometry.position_mm.x_mm = 14;
  assert.equal(Geometry.classifySlotPlacement(slot, sheet), "outside_printable");
  assert.equal(CanvasRenderer.slotPlacementClasses(slot, sheet, Geometry).message, "Fuera del área imprimible");
  slot.geometry.position_mm.x_mm = -5;
  assert.equal(Geometry.classifySlotPlacement(slot, sheet), "outside_sheet");
  assert.equal(CanvasRenderer.slotPlacementClasses(slot, sheet, Geometry).className, "is-outside-sheet");
});

test("approximate artwork, output labels and exact quantity default are explicit", () => {
  const layout = fixture();
  const real = unlockedFrontSlot(layout);
  assert.equal(CanvasRenderer.artworkIsApproximate(real, layout, "/assets"), true);
  const withoutArtwork = structuredClone(real);
  withoutArtwork.source.asset_id = "missing";
  assert.equal(CanvasRenderer.artworkIsApproximate(withoutArtwork, layout, "/assets"), false);
  assert.equal(
    OutputPanel.issueLabel({ code: "UNSUPPORTED_SOURCE_PAGE", message: "fallback" }),
    "Página distinta de 1 no soportada",
  );
  assert.deepEqual(RepeatPanel.readSettings({
    repeatGapX: { value: "4" },
    repeatGapY: { value: "3" },
    repeatFill: { checked: true },
    repeatPartial: { checked: false },
  }), {
    horizontal_gap_mm: 4,
    vertical_gap_mm: 3,
    exact_quantity: true,
    fill_remaining_space: true,
    allow_partial: false,
  });
});

test("thirty identical slot issues are grouped by code, asset and work", () => {
  const layout = fixture();
  const base = unlockedFrontSlot(layout);
  layout.slots = Array.from({ length: 30 }, (_, index) => {
    const slot = structuredClone(base);
    slot.id = `slot_repeat_operation_${String(index + 1).padStart(4, "0")}`;
    return slot;
  });
  const issues = layout.slots.map((slot, index) => ({
    code: "SOURCE_TRIM_SIZE_MISMATCH",
    level: "error",
    message: "mismatch",
    path: `$.slots[${index}].geometry.trim_size_mm`,
    slot_id: slot.id,
    asset_id: slot.source.asset_id,
  }));

  const groups = OutputPanel.groupIssues(issues, layout);

  assert.equal(groups.length, 1);
  assert.equal(groups[0].code, "SOURCE_TRIM_SIZE_MISMATCH");
  assert.equal(groups[0].assetId, base.source.asset_id);
  assert.equal(groups[0].workId, base.work_id);
  assert.equal(groups[0].count, 30);
  assert.equal(groups[0].slotIds.length, 30);
  assert.equal(groups[0].slotIds[0], "slot_repeat_operation_0001");
  assert.equal(groups[0].slotIds[29], "slot_repeat_operation_0030");
});

test("slot labels stay short, adapt to zoom and hide on physically tiny slots", () => {
  const layout = fixture();
  const slot = unlockedFrontSlot(layout, "slot_repeat_operation_0030");
  const presentations = [0.35, 1, 4].map((zoom) => (
    CanvasRenderer.slotLabelPresentation(slot, 30, zoom, true)
  ));

  assert.deepEqual(presentations.map((item) => item.text), ["#30", "#30", "#30"]);
  assert.ok(presentations.every((item) => item.visible));
  assert.ok(presentations[0].fontSizeMm > presentations[1].fontSizeMm);
  assert.ok(presentations[1].fontSizeMm > presentations[2].fontSizeMm);

  slot.geometry.trim_size_mm = { width: 5, height: 5 };
  assert.equal(
    CanvasRenderer.slotLabelPresentation(slot, 30, 4, true).visible,
    false,
  );
  assert.equal(
    CanvasRenderer.slotLabelPresentation(slot, 30, 1, false).visible,
    false,
  );
});

test("slot label visibility is temporary and never dirties or changes the layout", () => {
  const store = new EditorStore(fixture());
  const before = structuredClone(store.layout);
  const revision = store.revision;

  store.setSlotLabelsVisible(false);
  assert.equal(store.showSlotLabels, false);
  assert.equal(store.hasUnsavedChanges(), false);
  assert.equal(store.saveState.status, "clean");
  assert.equal(store.changeVersion, 0);
  assert.equal(store.revision, revision);
  assert.deepEqual(store.layout, before);

  store.setSlotLabelsVisible(true);
  assert.equal(store.hasUnsavedChanges(), false);
  assert.deepEqual(store.layout, before);
});
