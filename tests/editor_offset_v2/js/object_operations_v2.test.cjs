"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const EditPolicy = require(path.join(repoRoot, "static/js/editor_offset_v2/edit_policy.js"));
const Objects = require(path.join(repoRoot, "static/js/editor_offset_v2/object_operations.js"));
const RegistryModule = require(path.join(repoRoot, "static/js/editor_offset_v2/command_registry.js"));
const Shortcuts = require(path.join(repoRoot, "static/js/editor_offset_v2/shortcut_manager.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const { SaveCoordinator } = require(path.join(repoRoot, "static/js/editor_offset_v2/autosave.js"));

function fixture() {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
    "utf8",
  ));
}

function layoutWithSlots(count = 2) {
  const layout = fixture();
  const base = structuredClone(layout.slots.find((slot) => slot.face === "front"));
  base.locks = { geometry: [], content: [], production: [], delete: [] };
  layout.slots = Array.from({ length: count }, (_, index) => {
    const slot = structuredClone(base);
    slot.id = `slot_object_${index + 1}`;
    slot.geometry.position_mm.x_mm = 100 + index * 40;
    slot.geometry.position_mm.y_mm = 140 + index * 20;
    slot.geometry.rotation_deg = [0, 90, 180, 270][index % 4];
    return slot;
  });
  return layout;
}

function registry() {
  const result = new RegistryModule.ActionRegistry();
  RegistryModule.registerEditorActions(result);
  return result;
}

function context(store, overrides = {}) {
  return {
    store,
    commands: Commands,
    objectOperations: Objects,
    editPolicy: EditPolicy,
    interactions: {
      hasPanSession: () => false,
      hasPointerActivity: () => Boolean(store.pointerSession),
      cancelPointer: () => store.endPointerSession(),
      ...(overrides.interactions || {}),
    },
    nudgeController: overrides.nudgeController || null,
    saveCoordinator: overrides.saveCoordinator || { manualSave: async () => true },
    positionInspector: {
      hasPendingDraft: () => false,
      hasInvalidDraft: () => false,
      cancelPending: () => false,
      confirmPending: () => true,
    },
    shortcutHelp: {
      opened: false,
      isOpen() { return this.opened; },
      toggle() { this.opened = !this.opened; return true; },
      close() { this.opened = false; return true; },
    },
  };
}

function fakeElement(tagName = "DIV") {
  return {
    tagName,
    parentElement: null,
    isContentEditable: false,
    dataset: {},
    getAttribute: () => null,
    closest: () => null,
  };
}

function keyEvent(key, options = {}) {
  return {
    key,
    code: options.code || key,
    ctrlKey: Boolean(options.ctrlKey),
    metaKey: Boolean(options.metaKey),
    altKey: Boolean(options.altKey),
    shiftKey: Boolean(options.shiftKey),
    repeat: false,
    target: options.target || fakeElement(),
    prevented: 0,
    preventDefault() { this.prevented += 1; },
  };
}

test("cardinal rotation changes only rotation, keeps center/trim/bleed/content/source and is reversible", () => {
  const store = new EditorStore(layoutWithSlots(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  const before = structuredClone(store.layout.slots);
  const actionRegistry = registry();
  const ctx = context(store);

  actionRegistry.execute(RegistryModule.ACTION_IDS.ROTATE_CLOCKWISE, ctx);
  assert.deepEqual(
    store.layout.slots.map((slot) => slot.geometry.rotation_deg),
    [90, 180],
  );
  for (let index = 0; index < before.length; index += 1) {
    const after = structuredClone(store.layout.slots[index]);
    after.geometry.rotation_deg = before[index].geometry.rotation_deg;
    assert.deepEqual(after, before[index]);
  }
  assert.equal(store.undoStack.length, 1);
  store.undo();
  assert.deepEqual(store.layout.slots, before);
  store.redo();
  assert.deepEqual([...store.selection], ids);

  actionRegistry.execute(RegistryModule.ACTION_IDS.ROTATE_COUNTERCLOCKWISE, ctx);
  assert.deepEqual(
    store.layout.slots.map((slot) => slot.geometry.rotation_deg),
    [0, 90],
  );
});

test("set rotation supports 0/90/180/270, normalizes command input and no-op stays clean", () => {
  for (const rotation of [0, 90, 180, 270]) {
    const store = new EditorStore(layoutWithSlots(2));
    const ids = store.layout.slots.map((slot) => slot.id);
    store.setSelection(ids, "replace");
    const actionRegistry = registry();
    const result = actionRegistry.execute(
      RegistryModule.ACTION_IDS.ROTATE_SET,
      context(store),
      { rotation },
    );
    assert.ok(store.layout.slots.every((slot) => slot.geometry.rotation_deg === rotation));
    assert.equal(result.changed, true);
  }
  assert.equal(Commands.normalizeCardinalRotation(-90), 270);
  assert.equal(Commands.normalizeCardinalRotation(360), 0);
  assert.equal(Commands.normalizeCardinalRotation(450), 90);
  assert.throws(() => Commands.normalizeCardinalRotation(89), /cardinal/);

  const store = new EditorStore(layoutWithSlots(1));
  store.setSelection([store.layout.slots[0].id], "replace");
  const result = registry().execute(
    RegistryModule.ACTION_IDS.ROTATE_SET,
    context(store),
    { rotation: 0 },
  );
  assert.equal(result.changed, false);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.hasUnsavedChanges(), false);
});

test("manual cardinal rotation is independent of work allowed rotations and every geometry lock blocks atomically", () => {
  const freeStore = new EditorStore(layoutWithSlots(1));
  freeStore.layout.works[0].allowed_rotations_deg = [0];
  freeStore.setSelection([freeStore.layout.slots[0].id], "replace");
  registry().execute(RegistryModule.ACTION_IDS.ROTATE_SET, context(freeStore), { rotation: 270 });
  assert.equal(freeStore.layout.slots[0].geometry.rotation_deg, 270);

  for (const source of ["user", "engine", "ctp", "system"]) {
    const store = new EditorStore(layoutWithSlots(2));
    const ids = store.layout.slots.map((slot) => slot.id);
    store.layout.slots[1].locks.geometry = [source];
    store.setSelection(ids, "replace");
    const before = structuredClone(store.layout.slots);
    const actionRegistry = registry();
    assert.equal(actionRegistry.isEnabled(
      RegistryModule.ACTION_IDS.ROTATE_CLOCKWISE,
      context(store),
    ), false);
    assert.throws(
      () => new Commands.RotateSlotsCommand(store.layout, ids, 90),
      (error) => error.code === "SLOT_EDIT_LOCKED" && error.blockedIds.includes(ids[1]),
    );
    assert.deepEqual(store.layout.slots, before);
  }
});

test("duplicate preserves slot data and locks, replaces provenance, offsets selection and reuses IDs on redo", () => {
  const store = new EditorStore(layoutWithSlots(2));
  const originals = structuredClone(store.layout.slots);
  originals[0].locks.geometry = ["system"];
  store.layout.slots[0].locks.geometry = ["system"];
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  let counter = 0;
  const command = new Commands.DuplicateSlotsCommand(store.layout, ids, {
    offset: Objects.DUPLICATE_OFFSET_MM,
    idFactory: () => `slot_copy_${++counter}`,
    selectionBefore: ids,
  });
  store.executeCommand(command);

  assert.deepEqual(command.affectedIds, ["slot_copy_1", "slot_copy_2"]);
  assert.deepEqual([...store.selection], command.affectedIds);
  assert.equal(store.layout.slots.length, 4);
  for (let index = 0; index < 2; index += 1) {
    const copy = store.layout.slots[index + 2];
    const original = originals[index];
    assert.equal(copy.geometry.position_mm.x_mm, original.geometry.position_mm.x_mm + 5);
    assert.equal(copy.geometry.position_mm.y_mm, original.geometry.position_mm.y_mm - 5);
    const normalizedCopy = structuredClone(copy);
    normalizedCopy.id = original.id;
    normalizedCopy.geometry.position_mm = structuredClone(original.geometry.position_mm);
    normalizedCopy.generated_by = structuredClone(original.generated_by);
    assert.deepEqual(normalizedCopy, original);
    assert.deepEqual(copy.generated_by, {
      type: "duplicate",
      source_slot_id: original.id,
    });
  }
  const relativeBefore = originals[1].geometry.position_mm.x_mm
    - originals[0].geometry.position_mm.x_mm;
  const relativeAfter = store.layout.slots[3].geometry.position_mm.x_mm
    - store.layout.slots[2].geometry.position_mm.x_mm;
  assert.equal(relativeAfter, relativeBefore);

  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.id), ids);
  assert.deepEqual([...store.selection], ids);
  store.redo();
  assert.deepEqual(store.layout.slots.slice(-2).map((slot) => slot.id), command.affectedIds);
  assert.deepEqual([...store.selection], command.affectedIds);
});

test("copy is deep, immutable, resets paste count and never changes history, dirty or revision", () => {
  const store = new EditorStore(layoutWithSlots(1));
  const slot = store.layout.slots[0];
  store.setSelection([slot.id], "replace");
  const revision = store.revision;
  const clipboard = Objects.copySelection(store, "2026-07-26T00:00:00Z");
  store.layout.slots[0].geometry.position_mm.x_mm += 99;
  store.layout.slots[0].source.asset_id = store.layout.assets[1].id;

  assert.equal(clipboard.pasteCount, 0);
  assert.equal(store.clipboard.pasteCount, 0);
  assert.notEqual(
    store.clipboard.slots[0].geometry.position_mm.x_mm,
    store.layout.slots[0].geometry.position_mm.x_mm,
  );
  assert.notEqual(store.clipboard.slots[0].source.asset_id, store.layout.slots[0].source.asset_id);
  assert.equal(Object.isFrozen(store.clipboard), true);
  assert.equal(Object.isFrozen(store.clipboard.slots[0]), true);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.changeVersion, 0);
  assert.equal(store.hasUnsavedChanges(), false);
  assert.equal(store.revision, revision);

  store.setClipboardPasteCount(3);
  Objects.copySelection(store, "2026-07-26T00:01:00Z");
  assert.equal(store.clipboard.pasteCount, 0);
});

test("paste is same-job only, validates references and accumulates offset from clipboard originals", () => {
  const store = new EditorStore(layoutWithSlots(1));
  const original = structuredClone(store.layout.slots[0]);
  store.setSelection([original.id], "replace");
  Objects.copySelection(store);

  let counter = 0;
  const first = Objects.createPasteCommand(store, Commands, {
    idFactory: () => `slot_paste_${++counter}`,
  });
  store.executeCommand(first.command);
  store.setClipboardPasteCount(first.pasteCount);
  const firstCopy = structuredClone(store.layout.slots.at(-1));
  assert.equal(firstCopy.geometry.position_mm.x_mm, original.geometry.position_mm.x_mm + 5);
  assert.equal(firstCopy.geometry.position_mm.y_mm, original.geometry.position_mm.y_mm - 5);

  const second = Objects.createPasteCommand(store, Commands, {
    idFactory: () => `slot_paste_${++counter}`,
  });
  store.executeCommand(second.command);
  store.setClipboardPasteCount(second.pasteCount);
  const secondCopy = store.layout.slots.at(-1);
  assert.equal(secondCopy.geometry.position_mm.x_mm, original.geometry.position_mm.x_mm + 10);
  assert.equal(secondCopy.geometry.position_mm.y_mm, original.geometry.position_mm.y_mm - 10);
  assert.notEqual(firstCopy.id, secondCopy.id);
  assert.equal(store.clipboard.pasteCount, 2);

  const secondId = secondCopy.id;
  store.undo();
  assert.equal(store.layout.slots.some((slot) => slot.id === secondId), false);
  assert.equal(store.clipboard.pasteCount, 2, "undo does not rewind temporary clipboard");
  store.redo();
  assert.equal(store.layout.slots.at(-1).id, secondId);

  store.setClipboard({ ...store.clipboard, jobId: "ev2_other_job" });
  assert.match(
    Objects.validateClipboard(store.layout, store.clipboard, "front").reason,
    /otro job/,
  );
  store.setClipboard({
    ...store.clipboard,
    jobId: store.layout.job.id,
    slots: [{ ...store.clipboard.slots[0], work_id: "missing_work" }],
  });
  assert.match(
    Objects.validateClipboard(store.layout, store.clipboard, "front").reason,
    /work inexistente/,
  );
});

test("paste action synchronizes its temporary counter through undo and redo", () => {
  const store = new EditorStore(layoutWithSlots(1));
  const sourceId = store.layout.slots[0].id;
  store.setSelection([sourceId], "replace");
  const actionRegistry = registry();
  const ctx = context(store);

  actionRegistry.execute(RegistryModule.ACTION_IDS.COPY, ctx);
  const clipboardVersion = store.clipboardVersion;
  actionRegistry.execute(RegistryModule.ACTION_IDS.PASTE, ctx);
  const firstPasteId = [...store.selection][0];
  actionRegistry.execute(RegistryModule.ACTION_IDS.PASTE, ctx);
  const secondPasteId = [...store.selection][0];
  assert.equal(store.clipboard.pasteCount, 2);

  actionRegistry.execute(RegistryModule.ACTION_IDS.UNDO, ctx);
  assert.equal(store.layout.slots.some((slot) => slot.id === secondPasteId), false);
  assert.equal(store.clipboard.pasteCount, 1);
  actionRegistry.execute(RegistryModule.ACTION_IDS.UNDO, ctx);
  assert.equal(store.layout.slots.some((slot) => slot.id === firstPasteId), false);
  assert.equal(store.clipboard.pasteCount, 0);
  actionRegistry.execute(RegistryModule.ACTION_IDS.REDO, ctx);
  assert.equal(store.layout.slots.some((slot) => slot.id === firstPasteId), true);
  assert.equal(store.clipboard.pasteCount, 1);

  actionRegistry.execute(RegistryModule.ACTION_IDS.COPY, ctx);
  assert.ok(store.clipboardVersion > clipboardVersion);
  assert.equal(store.clipboard.pasteCount, 0);
  actionRegistry.execute(RegistryModule.ACTION_IDS.UNDO, ctx);
  assert.equal(
    store.clipboard.pasteCount,
    0,
    "undo from an older paste must not alter a newer clipboard capture",
  );
});

test("cut rejects mixed delete locks without replacing clipboard and successful undo keeps clipboard", () => {
  const store = new EditorStore(layoutWithSlots(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection([ids[0]], "replace");
  Objects.copySelection(store);
  const previousClipboard = structuredClone(store.clipboard);
  store.layout.slots[1].locks.delete = ["system"];
  store.setSelection(ids, "replace");
  const actionRegistry = registry();
  const ctx = context(store);
  assert.equal(actionRegistry.isEnabled(RegistryModule.ACTION_IDS.CUT, ctx), false);
  assert.deepEqual(store.clipboard, previousClipboard);
  assert.equal(store.layout.slots.length, 2);

  store.layout.slots[1].locks.delete = [];
  actionRegistry.execute(RegistryModule.ACTION_IDS.CUT, ctx);
  assert.equal(store.layout.slots.length, 0);
  assert.deepEqual(store.clipboard.order, ids);
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.id), ids);
  assert.deepEqual([...store.selection], ids);
  assert.deepEqual(store.clipboard.order, ids);
});

test("delete action is shared by keyboard, atomic, reversible and protected in editable controls", () => {
  const store = new EditorStore(layoutWithSlots(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  const actionRegistry = registry();
  const ctx = context(store);
  const manager = new Shortcuts.Manager(actionRegistry, () => ctx);
  const event = keyEvent("Delete");
  assert.equal(manager.handleKeyDown(event), true);
  assert.equal(event.prevented, 1);
  assert.equal(store.layout.slots.length, 0);
  assert.equal(store.undoStack.length, 1);
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.id), ids);

  const inputEvent = keyEvent("Delete", { target: fakeElement("INPUT") });
  assert.equal(manager.handleKeyDown(inputEvent), false);
  assert.equal(inputEvent.prevented, 0);
  assert.equal(store.layout.slots.length, 2);
  manager.dispose();
});

test("delete and cut block unselected dependents while collective delete stays atomic", () => {
  const store = new EditorStore(layoutWithSlots(1));
  const sourceId = store.layout.slots[0].id;
  store.setSelection([sourceId], "replace");
  store.executeCommand(new Commands.DuplicateSlotsCommand(
    store.layout,
    [sourceId],
    { idFactory: () => "slot_dependent" },
  ));
  const dependentId = store.layout.slots.at(-1).id;
  Objects.copySelection(store);
  const clipboardBefore = structuredClone(store.clipboard);
  store.setSelection([sourceId], "replace");
  const layoutBefore = structuredClone(store.layout);
  const historyBefore = store.undoStack.length;
  const actionRegistry = registry();
  const ctx = context(store);

  assert.deepEqual(
    Commands.unselectedDeleteDependents(store.layout, [sourceId]).map((slot) => slot.id),
    [dependentId],
  );
  assert.throws(
    () => new Commands.DeleteSlotsCommand(store.layout, [sourceId]),
    /1 slot dependiente quedaría sin origen.*Selecciona también ese dependiente/,
  );
  assert.equal(actionRegistry.execute(RegistryModule.ACTION_IDS.DELETE, ctx), false);
  assert.match(
    store.feedback,
    /1 slot dependiente quedaría sin origen.*Selecciona también ese dependiente/,
  );
  assert.equal(actionRegistry.execute(RegistryModule.ACTION_IDS.CUT, ctx), false);
  assert.match(store.feedback, /1 slot dependiente quedaría sin origen/);
  assert.deepEqual(store.layout, layoutBefore);
  assert.deepEqual(store.clipboard, clipboardBefore);
  assert.equal(store.undoStack.length, historyBefore);

  store.setSelection([sourceId, dependentId], "replace");
  actionRegistry.execute(RegistryModule.ACTION_IDS.DELETE, ctx);
  assert.equal(store.layout.slots.length, 0);
  assert.equal(store.undoStack.length, historyBefore + 1);
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.id), [sourceId, dependentId]);
  assert.deepEqual([...store.selection], [sourceId, dependentId]);
  store.redo();
  assert.equal(store.layout.slots.length, 0);

  store.undo();
  store.setSelection([sourceId, dependentId], "replace");
  actionRegistry.execute(RegistryModule.ACTION_IDS.CUT, ctx);
  assert.equal(store.layout.slots.length, 0);
  assert.deepEqual(store.clipboard.slots.map((slot) => slot.id), [sourceId, dependentId]);
  assert.equal(store.undoStack.length, historyBefore + 1);
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.id), [sourceId, dependentId]);
});

test("delete rechecks dependencies at execution time before mutating layout", () => {
  const layout = layoutWithSlots(2);
  const [source, dependent] = layout.slots;
  const command = new Commands.DeleteSlotsCommand(layout, [source.id]);
  dependent.generated_by = { type: "duplicate", source_slot_id: source.id };
  const before = structuredClone(layout.slots);

  assert.throws(
    () => command.execute(layout),
    /1 slot dependiente quedaría sin origen/,
  );
  assert.deepEqual(layout.slots, before);
});

test("basic selections use active face, union works and effective asset without history or dirty", () => {
  const layout = layoutWithSlots(3);
  const secondWork = structuredClone(layout.works[0]);
  secondWork.id = "work_second";
  secondWork.name = "Second";
  secondWork.front_source = {
    asset_id: layout.assets[1].id,
    page: 1,
    pdf_box: "trim",
  };
  layout.works.push(secondWork);
  layout.slots[1].work_id = secondWork.id;
  layout.slots[1].source = structuredClone(secondWork.front_source);
  layout.slots[2].source = structuredClone(secondWork.front_source);
  const back = structuredClone(layout.slots[0]);
  back.id = "slot_back_excluded";
  back.face = "back";
  layout.slots.push(back);
  const store = new EditorStore(layout);
  const actionRegistry = registry();
  const ctx = context(store);

  actionRegistry.execute(RegistryModule.ACTION_IDS.SELECT_ALL_FACE, ctx);
  assert.deepEqual([...store.selection], ["slot_object_1", "slot_object_2", "slot_object_3"]);
  store.setSelection(["slot_object_1", "slot_object_2"], "replace");
  actionRegistry.execute(RegistryModule.ACTION_IDS.SELECT_SAME_WORK, ctx);
  assert.deepEqual(new Set(store.selection), new Set([
    "slot_object_1", "slot_object_2", "slot_object_3",
  ]));
  store.setSelection(["slot_object_2"], "replace");
  actionRegistry.execute(RegistryModule.ACTION_IDS.SELECT_SAME_ASSET, ctx);
  assert.deepEqual(new Set(store.selection), new Set(["slot_object_2", "slot_object_3"]));
  assert.equal(store.selection.has("slot_back_excluded"), false);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.changeVersion, 0);
  assert.equal(store.hasUnsavedChanges(), false);
});

test("user locks expose none/all/mixed, preserve other sources, no-op and undo/redo exactly", () => {
  const store = new EditorStore(layoutWithSlots(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.layout.slots[0].locks.geometry = ["engine"];
  store.layout.slots[1].locks.geometry = ["ctp", "user"];
  store.setSelection(ids, "replace");
  assert.equal(Objects.userLockState(Objects.selectedSlots(store), "geometry"), "mixed");
  const before = structuredClone(store.layout.slots.map((slot) => slot.locks.geometry));
  const actionRegistry = registry();
  const ctx = context(store);

  actionRegistry.execute(
    RegistryModule.ACTION_IDS.USER_LOCKS_SET,
    ctx,
    { surface: "geometry", locked: true },
  );
  assert.deepEqual(store.layout.slots[0].locks.geometry, ["engine", "user"]);
  assert.deepEqual(store.layout.slots[1].locks.geometry, ["ctp", "user"]);
  assert.equal(Objects.userLockState(Objects.selectedSlots(store), "geometry"), "all");
  const version = store.changeVersion;
  const noOp = actionRegistry.execute(
    RegistryModule.ACTION_IDS.USER_LOCKS_SET,
    ctx,
    { surface: "geometry", locked: true },
  );
  assert.equal(noOp.changed, false);
  assert.equal(store.changeVersion, version);

  actionRegistry.execute(
    RegistryModule.ACTION_IDS.USER_LOCKS_SET,
    ctx,
    { surface: "geometry", locked: false },
  );
  assert.deepEqual(store.layout.slots[0].locks.geometry, ["engine"]);
  assert.deepEqual(store.layout.slots[1].locks.geometry, ["ctp"]);
  store.undo();
  assert.ok(store.layout.slots.every((slot) => slot.locks.geometry.includes("user")));
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.locks.geometry), before);
  store.redo();
  store.redo();
  assert.deepEqual(store.layout.slots[0].locks.geometry, ["engine"]);
  assert.deepEqual(store.layout.slots[1].locks.geometry, ["ctp"]);
});

test("geometry/content/delete user locks immediately govern existing edit policy", () => {
  const store = new EditorStore(layoutWithSlots(1));
  const slot = store.layout.slots[0];
  store.setSelection([slot.id], "replace");
  const actionRegistry = registry();
  const ctx = context(store);
  for (const [surface, capabilities] of [
    ["geometry", ["move", "rotate"]],
    ["content", ["replace_content"]],
    ["delete", ["delete", "replace_by_repeat"]],
  ]) {
    actionRegistry.execute(
      RegistryModule.ACTION_IDS.USER_LOCKS_SET,
      ctx,
      { surface, locked: true },
    );
    for (const capability of capabilities) {
      assert.equal(EditPolicy.can(store.layout, [slot.id], capability), false);
    }
  }
  assert.equal(actionRegistry.isEnabled(RegistryModule.ACTION_IDS.ROTATE_CLOCKWISE, ctx), false);
  assert.equal(actionRegistry.isEnabled(RegistryModule.ACTION_IDS.CUT, ctx), false);
  assert.equal(actionRegistry.isEnabled(RegistryModule.ACTION_IDS.DELETE, ctx), false);
});

test("move then user lock preserves deterministic undo/redo order", () => {
  const store = new EditorStore(layoutWithSlots(1));
  const slot = store.layout.slots[0];
  store.setSelection([slot.id], "replace");
  const before = structuredClone(slot.geometry.position_mm);
  store.executeCommand(new Commands.MoveSlotsCommand(
    { [slot.id]: before },
    { [slot.id]: { x_mm: before.x_mm + 7, y_mm: before.y_mm - 2 } },
  ));
  store.executeCommand(new Commands.SetSlotUserLocksCommand(
    store.layout,
    [slot.id],
    "geometry",
    true,
  ));
  store.undo();
  assert.deepEqual(slot.locks.geometry, []);
  assert.equal(slot.geometry.position_mm.x_mm, before.x_mm + 7);
  store.undo();
  assert.deepEqual(slot.geometry.position_mm, before);
  store.redo();
  store.redo();
  assert.equal(slot.geometry.position_mm.x_mm, before.x_mm + 7);
  assert.deepEqual(slot.locks.geometry, ["user"]);
});

test("registered 8B shortcuts share actions and editable scopes protect R/A/C/X/V/Delete", () => {
  const actionRegistry = registry();
  const ids = actionRegistry.list().map((action) => action.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of [
    RegistryModule.ACTION_IDS.ROTATE_CLOCKWISE,
    RegistryModule.ACTION_IDS.ROTATE_COUNTERCLOCKWISE,
    RegistryModule.ACTION_IDS.DUPLICATE,
    RegistryModule.ACTION_IDS.COPY,
    RegistryModule.ACTION_IDS.CUT,
    RegistryModule.ACTION_IDS.PASTE,
    RegistryModule.ACTION_IDS.DELETE,
    RegistryModule.ACTION_IDS.SELECT_ALL_FACE,
    RegistryModule.ACTION_IDS.SELECT_SAME_WORK,
    RegistryModule.ACTION_IDS.SELECT_SAME_ASSET,
    RegistryModule.ACTION_IDS.USER_LOCKS_SET,
  ]) assert.ok(actionRegistry.get(id), id);

  const store = new EditorStore(layoutWithSlots(1));
  store.setSelection([store.layout.slots[0].id], "replace");
  Objects.copySelection(store);
  const ctx = context(store);
  const manager = new Shortcuts.Manager(actionRegistry, () => ctx);
  assert.equal(manager.resolve(keyEvent("r"), ctx).action.id, RegistryModule.ACTION_IDS.ROTATE_CLOCKWISE);
  assert.equal(
    manager.resolve(keyEvent("r", { shiftKey: true }), ctx).action.id,
    RegistryModule.ACTION_IDS.ROTATE_COUNTERCLOCKWISE,
  );
  assert.equal(manager.resolve(keyEvent("d", { ctrlKey: true }), ctx).action.id, RegistryModule.ACTION_IDS.DUPLICATE);
  assert.equal(manager.resolve(keyEvent("c", { ctrlKey: true }), ctx).action.id, RegistryModule.ACTION_IDS.COPY);
  assert.equal(manager.resolve(keyEvent("x", { ctrlKey: true }), ctx).action.id, RegistryModule.ACTION_IDS.CUT);
  assert.equal(manager.resolve(keyEvent("v", { ctrlKey: true }), ctx).action.id, RegistryModule.ACTION_IDS.PASTE);
  assert.equal(manager.resolve(keyEvent("a", { ctrlKey: true }), ctx).action.id, RegistryModule.ACTION_IDS.SELECT_ALL_FACE);
  assert.equal(manager.resolve(keyEvent("Delete"), ctx).action.id, RegistryModule.ACTION_IDS.DELETE);

  const input = fakeElement("INPUT");
  for (const event of [
    keyEvent("r", { target: input }),
    keyEvent("Delete", { target: input }),
    keyEvent("a", { ctrlKey: true, target: input }),
    keyEvent("c", { ctrlKey: true, target: input }),
    keyEvent("x", { ctrlKey: true, target: input }),
    keyEvent("v", { ctrlKey: true, target: input }),
  ]) {
    assert.equal(manager.handleKeyDown(event), false);
    assert.equal(event.prevented, 0);
  }
  manager.dispose();
});

test("duplicate preview slots and clipboard are temporary; autosave starts only after command", async () => {
  const store = new EditorStore(layoutWithSlots(1));
  const slot = store.layout.slots[0];
  store.setSelection([slot.id], "replace");
  let saves = 0;
  const saver = new SaveCoordinator(store, {
    async saveLayout(_url, revision, submitted) {
      saves += 1;
      const canonical = structuredClone(submitted);
      canonical.job.revision = revision + 1;
      return { layout: canonical };
    },
  }, "/save", { debounceMs: 1 });
  const prepared = Commands.prepareDuplicateSlots(
    store.layout,
    [slot.id],
    { x_mm: 0, y_mm: 0 },
    { idFactory: () => "slot_alt_preview" },
  );
  store.beginPointerSession({
    type: "duplicate_move",
    previewSlots: prepared,
    beforePositions: {
      slot_alt_preview: structuredClone(prepared[0].geometry.position_mm),
    },
  });
  store.updatePointerPreviewSlots(prepared.map((copy) => ({
    ...copy,
    geometry: {
      ...copy.geometry,
      position_mm: {
        ...copy.geometry.position_mm,
        x_mm: copy.geometry.position_mm.x_mm + 10,
      },
    },
  })));
  Objects.copySelection(store);
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.equal(saves, 0);
  assert.equal(store.layout.slots.length, 1);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.hasUnsavedChanges(), false);
  const finalCopies = structuredClone(store.previewSlots);
  store.endPointerSession();
  store.executeCommand(new Commands.DuplicateSlotsCommand(
    store.layout,
    [slot.id],
    { preparedSlots: finalCopies, selectionBefore: [slot.id] },
  ));
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(saves, 1);
  assert.equal(store.layout.slots.length, 2);
  assert.equal(store.undoStack.length, 1);
  saver.dispose();
});

test("Escape cancels an active Alt-drag before an older inspector draft", () => {
  const store = new EditorStore(layoutWithSlots(1));
  store.beginPointerSession({
    type: "duplicate_move",
    pointerId: 7,
    beforePositions: {},
    previewSlots: [],
  });
  let pointerCancelled = 0;
  let inspectorCancelled = 0;
  const ctx = context(store, {
    interactions: {
      hasPointerActivity: () => Boolean(store.pointerSession),
      cancelPointer: () => {
        pointerCancelled += 1;
        store.endPointerSession();
      },
    },
  });
  ctx.positionInspector = {
    hasPendingDraft: () => true,
    hasInvalidDraft: () => true,
    cancelPending: () => {
      inspectorCancelled += 1;
      return true;
    },
  };

  const actionRegistry = registry();
  const manager = new Shortcuts.Manager(actionRegistry, () => ctx);
  const escape = keyEvent("Escape", { altKey: true });
  assert.equal(Shortcuts.normalizeKeyboardEvent(escape), "Escape");
  assert.equal(manager.handleKeyDown(escape), true);
  assert.equal(pointerCancelled, 1);
  assert.equal(inspectorCancelled, 0);
  assert.equal(store.pointerSession, null);
  assert.equal(store.hasUnsavedChanges(), false);
  manager.dispose();
});
