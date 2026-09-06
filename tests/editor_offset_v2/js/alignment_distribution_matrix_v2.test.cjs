"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Alignment = require(path.join(repoRoot, "static/js/editor_offset_v2/alignment_operations.js"));
const Commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const EditPolicy = require(path.join(repoRoot, "static/js/editor_offset_v2/edit_policy.js"));
const Geometry = require(path.join(repoRoot, "static/js/editor_offset_v2/geometry_view.js"));
const RegistryModule = require(path.join(repoRoot, "static/js/editor_offset_v2/command_registry.js"));
const ArrangementPanel = require(path.join(repoRoot, "static/js/editor_offset_v2/arrangement_panel.js"));
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
  base.locks = { geometry: [], content: [], production: [], delete: [] };
  layout.sheet.size_mm = { width: 300, height: 200 };
  layout.sheet.printable_margins_mm = { left: 20, right: 30, bottom: 15, top: 25 };
  layout.slots = specifications.map((specification, index) => {
    const slot = structuredClone(base);
    slot.id = specification.id || `slot_arrange_${index + 1}`;
    slot.geometry.position_mm = {
      x_mm: specification.x,
      y_mm: specification.y,
      anchor: "trim_center",
    };
    slot.geometry.trim_size_mm = {
      width: specification.width || 20,
      height: specification.height || 10,
    };
    slot.geometry.bleed_mm = specification.bleed ?? 2;
    slot.geometry.rotation_deg = specification.rotation || 0;
    return slot;
  });
  return layout;
}

function options(extra = {}) {
  return {
    geometryReference: "trim",
    target: "selection",
    activeFace: "front",
    keySlotId: null,
    ...extra,
  };
}

function positions(layout) {
  return Object.fromEntries(layout.slots.map((slot) => [slot.id, {
    x_mm: slot.geometry.position_mm.x_mm,
    y_mm: slot.geometry.position_mm.y_mm,
  }]));
}

function executePlan(store, plan) {
  if (!plan.changed) return false;
  const selection = [...store.selection];
  store.executeCommand(new Commands.MoveSlotsCommand(
    plan.beforePositions,
    plan.afterPositions,
    { selectionBefore: selection, selectionAfter: selection },
  ));
  return true;
}

function actionContext(store) {
  return {
    store,
    commands: Commands,
    editPolicy: EditPolicy,
    alignmentOperations: Alignment,
    geometry: Geometry,
    interactions: { hasPanSession: () => false },
    nudgeController: null,
  };
}

test("trim and productive bounds cover cardinal rotations without DOM geometry", () => {
  const layout = layoutWithSlots([
    { id: "r0", x: 60, y: 60, width: 30, height: 10, rotation: 0, bleed: 3 },
    { id: "r90", x: 100, y: 60, width: 30, height: 10, rotation: 90, bleed: 3 },
    { id: "r180", x: 140, y: 60, width: 30, height: 10, rotation: 180, bleed: 3 },
    { id: "r270", x: 180, y: 60, width: 30, height: 10, rotation: 270, bleed: 3 },
  ]);
  assert.deepEqual(Alignment.slotBounds(layout.slots[0], Geometry, "trim"), {
    left: 45, right: 75, bottom: 55, top: 65, width: 30, height: 10,
  });
  assert.deepEqual(Alignment.slotBounds(layout.slots[1], Geometry, "trim"), {
    left: 95, right: 105, bottom: 45, top: 75, width: 10, height: 30,
  });
  assert.deepEqual(Alignment.slotBounds(layout.slots[2], Geometry, "trim"), {
    left: 125, right: 155, bottom: 55, top: 65, width: 30, height: 10,
  });
  assert.deepEqual(Alignment.slotBounds(layout.slots[3], Geometry, "trim"), {
    left: 175, right: 185, bottom: 45, top: 75, width: 10, height: 30,
  });
  assert.deepEqual(Alignment.slotBounds(layout.slots[1], Geometry, "productive"), {
    left: 92, right: 108, bottom: 42, top: 78, width: 16, height: 36,
  });
  assert.deepEqual(
    Alignment.aggregateBounds(layout.slots, Geometry, "trim"),
    { left: 45, right: 185, bottom: 45, top: 75, width: 140, height: 30 },
  );
  const source = fs.readFileSync(
    path.join(repoRoot, "static/js/editor_offset_v2/alignment_operations.js"),
    "utf8",
  );
  assert.doesNotMatch(source, /getBoundingClientRect/);
});

test("slot key is temporary, selection-bound, face-bound and never dirties history", () => {
  const store = new EditorStore(layoutWithSlots([
    { id: "a", x: 30, y: 30 },
    { id: "b", x: 70, y: 30 },
  ]));
  store.setSelection(["a", "b"], "replace");
  store.setKeySlot("a");
  assert.equal(store.arrangement.keySlotId, "a");
  store.setKeySlot("b");
  assert.equal(store.arrangement.keySlotId, "b");
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.hasUnsavedChanges(), false);
  assert.throws(() => store.setKeySlot("missing"), /selección/);
  store.setSelection(["a"], "replace");
  assert.equal(store.arrangement.keySlotId, null);
  store.setSelection(["a", "b"], "replace");
  store.setKeySlot("a");
  store.layout.slots = store.layout.slots.filter((slot) => slot.id !== "a");
  store.filterSelection();
  assert.equal(store.arrangement.keySlotId, null);
  store.setArrangementGeometryReference("productive");
  store.setArrangementTarget("sheet");
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
});

test("selection alignment covers six axes, mixed sizes, rotations, no-op and undo/redo", () => {
  for (const [alignment, edge] of [
    ["left", "left"], ["right", "right"], ["top", "top"], ["bottom", "bottom"],
  ]) {
    const store = new EditorStore(layoutWithSlots([
      { id: "a", x: 60, y: 80, width: 20, height: 10 },
      { id: "b", x: 120, y: 110, width: 40, height: 20, rotation: 90 },
      { id: "c", x: 180, y: 55, width: 30, height: 15, rotation: 180 },
    ]));
    store.setSelection(["a", "b", "c"], "replace");
    const before = positions(store.layout);
    const plan = Alignment.buildAlignmentPlan(
      store.layout,
      [...store.selection],
      Geometry,
      options({ alignment }),
    );
    assert.equal(executePlan(store, plan), true);
    const values = store.layout.slots.map((slot) => Alignment.slotBounds(slot, Geometry, "trim")[edge]);
    assert.ok(values.every((value) => Math.abs(value - values[0]) < 1e-9));
    assert.deepEqual([...store.selection], ["a", "b", "c"]);
    store.undo();
    assert.deepEqual(positions(store.layout), before);
    store.redo();
    assert.ok(store.layout.slots.map(
      (slot) => Alignment.slotBounds(slot, Geometry, "trim")[edge],
    ).every((value) => Math.abs(value - values[0]) < 1e-9));
  }

  for (const alignment of ["horizontal_center", "vertical_center"]) {
    const layout = layoutWithSlots([
      { id: "a", x: 30, y: 40 },
      { id: "b", x: 80, y: 90, rotation: 270 },
    ]);
    const plan = Alignment.buildAlignmentPlan(layout, ["a", "b"], Geometry, options({ alignment }));
    const coordinate = alignment === "horizontal_center" ? "x_mm" : "y_mm";
    assert.equal(plan.afterPositions.a[coordinate], plan.afterPositions.b[coordinate]);
  }
  const one = layoutWithSlots([{ id: "one", x: 30, y: 30 }]);
  assert.throws(
    () => Alignment.buildAlignmentPlan(one, ["one"], Geometry, options({ alignment: "left" })),
    /al menos dos/,
  );
  const noOp = layoutWithSlots([
    { id: "a", x: 30, y: 30 }, { id: "b", x: 30, y: 70 },
  ]);
  assert.equal(Alignment.buildAlignmentPlan(
    noOp, ["a", "b"], Geometry, options({ alignment: "horizontal_center" }),
  ).changed, false);
});

test("key alignment keeps key fixed, permits a locked key and rejects a moving lock atomically", () => {
  const layout = layoutWithSlots([
    { id: "key", x: 60, y: 60, width: 30 },
    { id: "move", x: 130, y: 100, width: 20 },
  ]);
  layout.slots[0].locks.geometry = ["user"];
  const store = new EditorStore(layout);
  store.setSelection(["key", "move"], "replace");
  const plan = Alignment.buildAlignmentPlan(
    store.layout,
    [...store.selection],
    Geometry,
    options({ target: "key", keySlotId: "key", alignment: "left" }),
  );
  assert.deepEqual(plan.affectedIds, ["move"]);
  const keyBefore = structuredClone(store.layout.slots[0].geometry.position_mm);
  executePlan(store, plan);
  assert.deepEqual(store.layout.slots[0].geometry.position_mm, keyBefore);

  store.undo();
  store.layout.slots[1].locks.geometry = ["ctp"];
  const lockedPlan = Alignment.buildAlignmentPlan(
    store.layout,
    [...store.selection],
    Geometry,
    options({ target: "key", keySlotId: "key", alignment: "right" }),
  );
  const before = positions(store.layout);
  assert.throws(() => executePlan(store, lockedPlan), /move \[ctp\]/);
  assert.deepEqual(positions(store.layout), before);
});

test("sheet and printable alignment move groups while preserving relative distances", () => {
  for (const target of ["sheet", "printable"]) {
    for (const alignment of ["left", "right", "top", "bottom", "horizontal_center", "vertical_center", "both"]) {
      const layout = layoutWithSlots([
        { id: "a", x: 80, y: 80, width: 20, height: 10 },
        { id: "b", x: 140, y: 110, width: 40, height: 20, rotation: 90 },
      ]);
      const relative = { x: 60, y: 30 };
      const plan = Alignment.buildAlignmentPlan(
        layout,
        ["a", "b"],
        Geometry,
        options({ target, alignment, geometryReference: "productive" }),
      );
      for (const slot of layout.slots) {
        if (plan.afterPositions[slot.id]) slot.geometry.position_mm = { ...slot.geometry.position_mm, ...plan.afterPositions[slot.id] };
      }
      assert.equal(layout.slots[1].geometry.position_mm.x_mm - layout.slots[0].geometry.position_mm.x_mm, relative.x);
      assert.equal(layout.slots[1].geometry.position_mm.y_mm - layout.slots[0].geometry.position_mm.y_mm, relative.y);
      const aggregate = Alignment.aggregateBounds(layout.slots, Geometry, "productive");
      const container = Alignment.targetBounds(layout, Geometry, target);
      if (alignment === "left") assert.ok(Math.abs(aggregate.left - container.left) < 1e-9);
      if (alignment === "right") assert.ok(Math.abs(aggregate.right - container.right) < 1e-9);
      if (alignment === "top") assert.ok(Math.abs(aggregate.top - container.top) < 1e-9);
      if (alignment === "bottom") assert.ok(Math.abs(aggregate.bottom - container.bottom) < 1e-9);
      if (["horizontal_center", "both"].includes(alignment)) {
        assert.ok(Math.abs((aggregate.left + aggregate.right) - (container.left + container.right)) < 1e-9);
      }
      if (["vertical_center", "both"].includes(alignment)) {
        assert.ok(Math.abs((aggregate.bottom + aggregate.top) - (container.bottom + container.top)) < 1e-9);
      }
    }
  }
});

test("horizontal and vertical distribution use stable order, fixed selection endpoints and signed gaps", () => {
  const layout = layoutWithSlots([
    { id: "left", x: 20, y: 150, width: 40, height: 20 },
    { id: "middle", x: 55, y: 100, width: 50, height: 30, rotation: 90 },
    { id: "right", x: 80, y: 45, width: 60, height: 40 },
  ]);
  const horizontal = Alignment.buildDistributionPlan(
    layout,
    ["right", "middle", "left"],
    Geometry,
    options({ axis: "horizontal" }),
  );
  assert.deepEqual(horizontal.orderedIds, ["left", "middle", "right"]);
  assert.equal(horizontal.overlap, true);
  assert.equal(horizontal.beforePositions.left, undefined);
  assert.equal(horizontal.beforePositions.right, undefined);
  assert.ok(horizontal.affectedIds.includes("middle"));

  const vertical = Alignment.buildDistributionPlan(
    layout,
    ["right", "middle", "left"],
    Geometry,
    options({ axis: "vertical" }),
  );
  assert.deepEqual(vertical.orderedIds, ["left", "middle", "right"]);
  assert.equal(vertical.beforePositions.left, undefined);
  assert.equal(vertical.beforePositions.right, undefined);

  for (const target of ["sheet", "printable"]) {
    const plan = Alignment.buildDistributionPlan(
      layout,
      layout.slots.map((slot) => slot.id),
      Geometry,
      options({ axis: "horizontal", target }),
    );
    const container = Alignment.targetBounds(layout, Geometry, target);
    const leftX = plan.afterPositions.left?.x_mm ?? layout.slots[0].geometry.position_mm.x_mm;
    const rightX = plan.afterPositions.right?.x_mm ?? layout.slots[2].geometry.position_mm.x_mm;
    assert.ok(Math.abs(leftX - 20 - container.left) < 1e-9);
    assert.ok(Math.abs(rightX + 30 - container.right) < 1e-9);
  }
  assert.throws(
    () => Alignment.buildDistributionPlan(layout, ["left", "right"], Geometry, options({ axis: "horizontal" })),
    /al menos tres/,
  );
  assert.throws(
    () => Alignment.buildDistributionPlan(layout, ["left", "middle", "right"], Geometry, options({ axis: "horizontal", target: "key" })),
    /Destino/,
  );
});

test("exact horizontal and vertical gaps parse point/comma and honor start, end and key anchors", () => {
  for (const [raw, expected] of [[" 2.5 ", 2.5], ["3,75", 3.75], ["0", 0]]) {
    assert.deepEqual(Alignment.parseNonNegativeMillimetres(raw), { ok: true, value: expected, error: null });
  }
  for (const raw of ["", "-1", "NaN", "Infinity", "1,2.3", "texto"]) {
    assert.equal(Alignment.parseNonNegativeMillimetres(raw).ok, false);
  }
  for (const axis of ["horizontal", "vertical"]) {
    for (const anchor of ["start", "end", "key"]) {
      const layout = layoutWithSlots([
        { id: "first", x: 40, y: 150, width: 20, height: 10 },
        { id: "key", x: 90, y: 100, width: 30, height: 20, rotation: 90 },
        { id: "last", x: 160, y: 45, width: 40, height: 30 },
      ]);
      const before = positions(layout);
      const plan = Alignment.buildExactGapPlan(
        layout,
        ["last", "first", "key"],
        Geometry,
        options({ axis, anchor, keySlotId: "key", gapMm: 7, geometryReference: "productive" }),
      );
      assert.equal(plan.fixedId, anchor === "start" ? "first" : anchor === "end" ? "last" : "key");
      assert.equal(plan.beforePositions[plan.fixedId], undefined);
      const fixed = layout.slots.find((slot) => slot.id === plan.fixedId);
      assert.deepEqual(fixed.geometry.position_mm, { ...fixed.geometry.position_mm, ...before[plan.fixedId] });
      for (const slot of layout.slots) {
        if (plan.afterPositions[slot.id]) slot.geometry.position_mm = { ...slot.geometry.position_mm, ...plan.afterPositions[slot.id] };
      }
      const ordered = Alignment.stableOrder(layout, layout.slots, Geometry, "productive", axis);
      for (let index = 1; index < ordered.length; index += 1) {
        const previous = Alignment.slotBounds(ordered[index - 1], Geometry, "productive");
        const current = Alignment.slotBounds(ordered[index], Geometry, "productive");
        const gap = axis === "horizontal" ? current.left - previous.right : previous.bottom - current.top;
        assert.ok(Math.abs(gap - 7) < 1e-9);
      }
    }
  }
});

test("matrix duplicates one or several sources in +X/-Y with stable IDs, provenance and one undo", () => {
  const layout = layoutWithSlots([
    { id: "source_a", x: 40, y: 160, width: 20, height: 10, rotation: 90 },
    { id: "source_b", x: 70, y: 140, width: 30, height: 20, bleed: 3 },
  ]);
  layout.slots[0].locks.geometry = ["system"];
  layout.slots[0].content_transform.offset_mm = { x: 1.5, y: -2 };
  const ids = Array.from({ length: 20 }, (_, index) => `matrix_id_${index + 1}`);
  let idIndex = 0;
  const prepared = Alignment.prepareMatrixCopies(
    layout,
    ["source_a", "source_b"],
    Geometry,
    Commands,
    options({
      rows: 2,
      columns: 3,
      gapX: 5,
      gapY: 7,
      geometryReference: "productive",
      idFactory: () => ids[idIndex++],
    }),
  );
  assert.equal(prepared.newSlots, 10);
  assert.equal(prepared.copies.length, 10);
  assert.equal(new Set(prepared.copies.map((slot) => slot.id)).size, 10);
  assert.ok(prepared.copies.some((slot) => slot.geometry.position_mm.x_mm > 70));
  assert.ok(prepared.copies.some((slot) => slot.geometry.position_mm.y_mm < 140));
  for (const copy of prepared.copies) {
    const source = layout.slots.find((slot) => slot.id === copy.generated_by.source_slot_id);
    assert.equal(copy.generated_by.type, "duplicate");
    assert.equal(copy.work_id, source.work_id);
    assert.equal(copy.face, source.face);
    assert.deepEqual(copy.source, source.source);
    assert.deepEqual(copy.content_transform, source.content_transform);
    assert.deepEqual(copy.locks, source.locks);
    assert.equal(copy.generated_by.operation_id, undefined);
  }
  const originals = structuredClone(layout.slots);
  const store = new EditorStore(layout);
  store.setSelection(["source_a", "source_b"], "replace");
  const command = new Commands.DuplicateSlotsCommand(store.layout, prepared.sourceIds, {
    preparedSlots: prepared.copies,
    selectionBefore: [...store.selection],
  });
  store.executeCommand(command);
  assert.deepEqual(store.layout.slots.slice(0, 2), originals);
  assert.deepEqual([...store.selection], command.affectedIds);
  const createdIds = [...command.affectedIds];
  store.undo();
  assert.equal(store.layout.slots.length, 2);
  assert.deepEqual([...store.selection], ["source_a", "source_b"]);
  store.redo();
  assert.deepEqual(command.affectedIds, createdIds);
  assert.deepEqual([...store.selection], createdIds);
  assert.throws(() => Alignment.matrixSummary(1, 1, 1), /más de una/);
  assert.throws(() => Alignment.matrixSummary(100, 3, 3), /500/);
  assert.equal(Alignment.parsePositiveInteger("2.5", "Filas").ok, false);
  assert.equal(Alignment.parsePositiveInteger("0", "Filas").ok, false);
});

test("matrix repeat guard blocks only the unchanged generated selection", () => {
  const payload = { rows: 2, columns: 2, gapX: 10, gapY: 10 };
  const guard = ArrangementPanel.createMatrixRepeatGuard(
    ["generated_a", "generated_b", "generated_c"],
    payload,
  );

  assert.equal(ArrangementPanel.shouldBlockMatrixRepeat(
    guard,
    ["generated_c", "generated_a", "generated_b"],
    payload,
  ), true);
  assert.equal(ArrangementPanel.shouldBlockMatrixRepeat(
    guard,
    ["source_a"],
    payload,
  ), false);
  assert.equal(ArrangementPanel.shouldBlockMatrixRepeat(
    guard,
    ["generated_a", "generated_b", "generated_c"],
    { ...payload, gapX: 11 },
  ), false);
});

test("8C actions are unique, buttons can share them and commands alone trigger dirty", () => {
  const registry = new RegistryModule.ActionRegistry();
  RegistryModule.registerEditorActions(registry);
  const ids = Object.values(RegistryModule.ACTION_IDS);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of [
    "selection.key_slot.set", "selection.key_slot.clear", "selection.align.left",
    "selection.align.right", "selection.align.top", "selection.align.bottom",
    "selection.align.horizontal_center", "selection.align.vertical_center",
    "selection.center.horizontal", "selection.center.vertical", "selection.center.both",
    "selection.distribute.horizontal", "selection.distribute.vertical",
    "selection.gap.horizontal", "selection.gap.vertical", "selection.matrix.create",
  ]) assert.ok(registry.get(id), id);

  const store = new EditorStore(layoutWithSlots([
    { id: "a", x: 30, y: 40 },
    { id: "b", x: 90, y: 80 },
    { id: "c", x: 150, y: 120 },
  ]));
  store.setSelection(["a", "b", "c"], "replace");
  const context = actionContext(store);
  registry.execute(RegistryModule.ACTION_IDS.KEY_SLOT_SET, context, { slotId: "b" });
  store.setArrangementGeometryReference("productive");
  store.setArrangementTarget("selection");
  assert.equal(store.changeVersion, 0);
  assert.equal(store.undoStack.length, 0);
  registry.execute(RegistryModule.ACTION_IDS.ALIGN_LEFT, context);
  assert.equal(store.changeVersion, 1);
  assert.equal(store.undoStack.length, 1);
  store.undo();
  store.redo();
  assert.equal(store.undoStack.length, 1);

  const rendererSource = fs.readFileSync(
    path.join(repoRoot, "static/js/editor_offset_v2/canvas_renderer.js"),
    "utf8",
  );
  assert.match(rendererSource, /data-key-slot-badge/);
  const template = fs.readFileSync(
    path.join(repoRoot, "templates/editor_offset_visual_v2.html"),
    "utf8",
  );
  assert.match(template, /data-arrangement-action="selection\.align\.left"/);
  assert.doesNotMatch(template, /Ctrl\+Shift\+P/);
});
