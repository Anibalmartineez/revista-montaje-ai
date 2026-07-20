"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const EditPolicy = require(path.join(repoRoot, "static/js/editor_offset_v2/edit_policy.js"));
const Positioning = require(path.join(repoRoot, "static/js/editor_offset_v2/position_inspector.js"));
const RegistryModule = require(path.join(repoRoot, "static/js/editor_offset_v2/command_registry.js"));
const Shortcuts = require(path.join(repoRoot, "static/js/editor_offset_v2/shortcut_manager.js"));
const Nudge = require(path.join(repoRoot, "static/js/editor_offset_v2/nudge_controller.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const { SaveCoordinator } = require(path.join(repoRoot, "static/js/editor_offset_v2/autosave.js"));

function fixture() {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
    "utf8",
  ));
}

function editableLayout(count = 2) {
  const layout = fixture();
  const base = structuredClone(layout.slots.find((slot) => slot.face === "front"));
  base.locks = { geometry: [], content: [], production: [], delete: [] };
  layout.slots = Array.from({ length: count }, (_, index) => {
    const slot = structuredClone(base);
    slot.id = `slot_position_${index + 1}`;
    slot.geometry.position_mm.x_mm = 100 + index * 50;
    slot.geometry.position_mm.y_mm = 120 + index * 25;
    return slot;
  });
  return layout;
}

function fakeElement(tagName, attributes = {}, parentElement = null) {
  return {
    tagName,
    parentElement,
    isContentEditable: attributes.isContentEditable === true,
    dataset: attributes.dataset || {},
    getAttribute(name) {
      return Object.hasOwn(attributes, name) ? attributes[name] : null;
    },
    closest(selector) {
      if (selector === "#ev2-position-form" && attributes.positionForm) return this;
      return parentElement?.closest?.(selector) || null;
    },
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
    repeat: Boolean(options.repeat),
    target: options.target || fakeElement("DIV"),
    prevented: 0,
    preventDefault() { this.prevented += 1; },
  };
}

function interactionStub() {
  return {
    pan: false,
    pointer: false,
    hasPanSession() { return this.pan; },
    hasPointerActivity() { return this.pointer; },
    cancelPointer() { this.pointer = false; },
  };
}

function fullContext(store, nudgeController, overrides = {}) {
  const interactions = overrides.interactions || interactionStub();
  return {
    store,
    commands: Commands,
    positioning: Positioning,
    editPolicy: EditPolicy,
    interactions,
    nudgeController,
    saveCoordinator: overrides.saveCoordinator || { manualSave: async () => true },
    positionInspector: overrides.positionInspector || {
      hasPendingDraft: () => false,
      hasInvalidDraft: () => false,
      cancelPending: () => false,
      confirmPending: () => true,
    },
    shortcutHelp: overrides.shortcutHelp || {
      opened: false,
      isOpen() { return this.opened; },
      toggle() { this.opened = !this.opened; return true; },
      close() { this.opened = false; return true; },
    },
  };
}

function editorRegistry() {
  const registry = new RegistryModule.ActionRegistry();
  RegistryModule.registerEditorActions(registry);
  return registry;
}

test("action registry enforces stable unique ids and executes enabled actions with payload", () => {
  const registry = new RegistryModule.ActionRegistry();
  let received = null;
  const action = registry.register({
    id: "test.action",
    label: "Acción",
    category: "testing",
    description: "test",
    shortcuts: ["Ctrl+K"],
    enabled: (context) => context.enabled,
    execute: (_context, payload) => { received = payload; return "ok"; },
  });
  assert.equal(registry.get("test.action"), action);
  assert.equal(action.category, "testing");
  assert.equal(registry.isEnabled("test.action", { enabled: true }), true);
  assert.equal(registry.isEnabled("test.action", { enabled: false }), false);
  assert.equal(registry.execute("test.action", { enabled: true }, { value: 7 }), "ok");
  assert.deepEqual(received, { value: 7 });
  assert.throws(() => registry.register({ id: "test.action", execute() {} }), /Duplicate/);
  assert.throws(
    () => registry.execute("test.action", { enabled: false }),
    (error) => error.code === "EDITOR_ACTION_DISABLED",
  );
  assert.throws(
    () => registry.execute("unknown.action", {}),
    (error) => error.code === "UNKNOWN_EDITOR_ACTION",
  );
});

test("shortcut normalization covers Ctrl, Meta, Shift, help and nudge combinations", () => {
  assert.equal(Shortcuts.normalizeKeyboardEvent(keyEvent("s", { ctrlKey: true })), "Ctrl+S");
  assert.equal(Shortcuts.normalizeKeyboardEvent(keyEvent("s", { metaKey: true })), "Meta+S");
  assert.equal(
    Shortcuts.normalizeKeyboardEvent(keyEvent("z", { ctrlKey: true, shiftKey: true })),
    "Ctrl+Shift+Z",
  );
  assert.equal(Shortcuts.normalizeKeyboardEvent(keyEvent("?", { shiftKey: true })), "?");
  assert.equal(Shortcuts.normalizeKeyboardEvent(keyEvent("/", { shiftKey: true })), "?");
  assert.equal(
    Shortcuts.normalizeKeyboardEvent(keyEvent("ArrowLeft", { metaKey: true, shiftKey: true })),
    "Meta+Shift+ArrowLeft",
  );
  assert.deepEqual(Shortcuts.expandShortcutDefinition("Mod+S"), ["Ctrl+S", "Meta+S"]);
});

test("shortcut manager resolves implemented bindings and rejects conflicts", () => {
  const registry = editorRegistry();
  const store = new EditorStore(editableLayout(1));
  store.setSelection([store.layout.slots[0].id], "replace");
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, { timeoutMs: 10_000 });
  const context = fullContext(store, nudge);
  const manager = new Shortcuts.Manager(registry, () => context);
  assert.equal(manager.resolve(keyEvent("s", { ctrlKey: true }), context).action.id, "editor.save");
  assert.equal(manager.resolve(keyEvent("z", { ctrlKey: true }), context).action.id, "history.undo");
  assert.equal(
    manager.resolve(keyEvent("z", { ctrlKey: true, shiftKey: true }), context).action.id,
    "history.redo",
  );
  assert.equal(manager.resolve(keyEvent("y", { ctrlKey: true }), context).action.id, "history.redo");
  assert.equal(manager.resolve(keyEvent("?", { shiftKey: true }), context).action.id, "shortcuts.help.toggle");
  assert.equal(manager.resolve(keyEvent("ArrowUp"), context).action.id, "selection.nudge");
  manager.dispose();
  nudge.dispose();

  const conflicts = new RegistryModule.ActionRegistry();
  conflicts.register({ id: "first.action", shortcuts: ["Mod+K"], execute() {} });
  conflicts.register({ id: "second.action", shortcuts: ["Ctrl+K"], execute() {} });
  assert.throws(
    () => new Shortcuts.Manager(conflicts, () => ({})),
    (error) => error.code === "SHORTCUT_CONFLICT" && error.shortcut === "Ctrl+K",
  );
});

test("editable scope covers native fields, nested contenteditable, roles and explicit capture", () => {
  for (const tag of ["INPUT", "TEXTAREA", "SELECT"]) {
    assert.equal(Shortcuts.isEditableTarget(fakeElement(tag)), true);
  }
  const editable = fakeElement("DIV", { contenteditable: "true" });
  assert.equal(Shortcuts.isEditableTarget(editable), true);
  assert.equal(Shortcuts.isEditableTarget(fakeElement("SPAN", {}, editable)), true);
  assert.equal(Shortcuts.isEditableTarget(fakeElement("DIV", { role: "textbox" })), true);
  assert.equal(
    Shortcuts.isEditableTarget(fakeElement("DIV", { "data-editor-captures-keyboard": "true" })),
    true,
  );
  assert.equal(Shortcuts.isEditableTarget(fakeElement("DIV")), false);
});

test("keyboard scopes protect inputs, help, drag and pan while controlled exceptions remain", () => {
  const registry = editorRegistry();
  const store = new EditorStore(editableLayout(1));
  store.setSelection([store.layout.slots[0].id], "replace");
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, { timeoutMs: 10_000 });
  const context = fullContext(store, nudge);
  const manager = new Shortcuts.Manager(registry, () => context);
  const input = fakeElement("INPUT");
  assert.equal(manager.resolve(keyEvent("ArrowRight", { target: input }), context), null);
  assert.equal(manager.resolve(keyEvent("z", { ctrlKey: true, target: input }), context), null);
  assert.equal(manager.resolve(keyEvent("s", { ctrlKey: true, target: input }), context).action.id, "editor.save");
  context.shortcutHelp.opened = true;
  assert.equal(manager.resolve(keyEvent("ArrowRight"), context), null);
  assert.equal(manager.resolve(keyEvent("Escape"), context).action.id, "editor.cancel");
  context.shortcutHelp.opened = false;
  store.beginPointerSession({ type: "move", pointerId: 1, beforePositions: {} });
  assert.equal(manager.resolve(keyEvent("ArrowRight"), context), null);
  store.endPointerSession();
  context.interactions.pan = true;
  assert.equal(manager.resolve(keyEvent("ArrowRight"), context), null);
  context.interactions.pan = false;
  manager.dispose();
  nudge.dispose();
});

test("millimetre parser accepts point/comma and rejects unsafe numeric text", () => {
  for (const [raw, expected] of [
    ["10", 10], ["10.5", 10.5], ["10,5", 10.5],
    ["-10.5", -10.5], ["-10,5", -10.5], [" 10,5 ", 10.5],
  ]) {
    assert.deepEqual(Positioning.parseMillimetres(raw), { ok: true, value: expected, error: null });
  }
  for (const raw of ["", "NaN", "Infinity", "-Infinity", "10mm", "1.2.3", "1,2,3", "1,2.3"]) {
    assert.equal(Positioning.parseMillimetres(raw).ok, false, raw);
  }
});

test("absolute positioning changes one or both axes, preserves exact untouched data and no-op stays clean", () => {
  const store = new EditorStore(editableLayout(1));
  const slot = store.layout.slots[0];
  store.setSelection([slot.id], "replace");
  const registry = editorRegistry();
  const context = fullContext(store, null);
  registry.execute(RegistryModule.ACTION_IDS.MOVE_ABSOLUTE, context, {
    x_mm: 123.456,
    y_mm: slot.geometry.position_mm.y_mm,
  });
  assert.equal(slot.geometry.position_mm.x_mm, 123.456);
  assert.equal(slot.geometry.position_mm.y_mm, 120);
  assert.equal(store.undoStack.length, 1);
  store.undo();
  assert.deepEqual(slot.geometry.position_mm, { x_mm: 100, y_mm: 120, anchor: "trim_center" });
  store.redo();
  assert.equal(slot.geometry.position_mm.x_mm, 123.456);
  const version = store.changeVersion;
  const result = registry.execute(RegistryModule.ACTION_IDS.MOVE_ABSOLUTE, context, {
    x_mm: 123.456,
    y_mm: 120,
  });
  assert.equal(result.changed, false);
  assert.equal(store.changeVersion, version);
});

test("absolute positioning rejects missing slots and MoveSlotsCommand defends a late lock", () => {
  const layout = editableLayout(1);
  assert.throws(
    () => Positioning.buildMovePlan(layout, ["missing"], "absolute", { x_mm: 1, y_mm: 2 }),
    /No existen/,
  );
  const store = new EditorStore(layout);
  const slot = store.layout.slots[0];
  const plan = Positioning.buildMovePlan(
    store.layout,
    [slot.id],
    "absolute",
    { x_mm: 20, y_mm: 30 },
  );
  slot.locks.geometry = ["system"];
  assert.throws(
    () => store.executeCommand(new Commands.MoveSlotsCommand(plan.beforePositions, plan.afterPositions)),
    (error) => error.code === "SLOT_EDIT_LOCKED",
  );
  assert.deepEqual(slot.geometry.position_mm, { x_mm: 100, y_mm: 120, anchor: "trim_center" });
  assert.equal(store.undoStack.length, 0);
});

test("multi-selection delta is atomic, supports signs and preserves relative distances", () => {
  const store = new EditorStore(editableLayout(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  const before = structuredClone(store.layout.slots.map((slot) => slot.geometry.position_mm));
  const registry = editorRegistry();
  const context = fullContext(store, null);
  registry.execute(RegistryModule.ACTION_IDS.MOVE_DELTA, context, { dx_mm: 10.5, dy_mm: -4.25 });
  assert.equal(store.layout.slots[0].geometry.position_mm.x_mm, before[0].x_mm + 10.5);
  assert.equal(store.layout.slots[1].geometry.position_mm.y_mm, before[1].y_mm - 4.25);
  assert.equal(
    store.layout.slots[1].geometry.position_mm.x_mm - store.layout.slots[0].geometry.position_mm.x_mm,
    before[1].x_mm - before[0].x_mm,
  );
  assert.equal(store.undoStack.length, 1);
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.geometry.position_mm), before);
  store.redo();
  const version = store.changeVersion;
  assert.equal(
    registry.execute(RegistryModule.ACTION_IDS.MOVE_DELTA, context, { dx_mm: 0, dy_mm: 0 }).changed,
    false,
  );
  assert.equal(store.changeVersion, version);
});

test("every geometry lock source blocks an entire multi-selection and reports blocked ids", () => {
  for (const source of ["user", "engine", "ctp", "system"]) {
    const store = new EditorStore(editableLayout(2));
    const ids = store.layout.slots.map((slot) => slot.id);
    store.setSelection(ids, "replace");
    store.layout.slots[1].locks.geometry = [source];
    const before = structuredClone(store.layout.slots);
    const context = fullContext(store, null);
    const registry = editorRegistry();
    assert.equal(registry.isEnabled(RegistryModule.ACTION_IDS.MOVE_DELTA, context), false);
    assert.throws(
      () => registry.execute(RegistryModule.ACTION_IDS.MOVE_DELTA, context, { dx_mm: 1, dy_mm: 1 }),
      (error) => error.code === "EDITOR_ACTION_DISABLED" && error.message.includes(ids[1]),
    );
    assert.deepEqual(store.layout.slots, before);
  }
});

test("nudge maps canonical domain directions and three requested step scales", () => {
  assert.deepEqual(RegistryModule.nudgePayload("ArrowLeft"), {
    direction: "ArrowLeft", step: 0.1, dx: -0.1, dy: 0,
  });
  assert.equal(RegistryModule.nudgePayload("ArrowRight").dx, 0.1);
  assert.equal(RegistryModule.nudgePayload("ArrowUp").dy, 0.1);
  assert.equal(RegistryModule.nudgePayload("ArrowDown").dy, -0.1);
  assert.equal(RegistryModule.nudgePayload("Shift+ArrowRight").step, 1);
  assert.equal(RegistryModule.nudgePayload("Ctrl+Shift+ArrowRight").step, 10);
  assert.equal(RegistryModule.nudgePayload("Meta+Shift+ArrowRight").step, 10);
});

test("keydown autorepeat previews without dirty and keyup commits one command and one undo", () => {
  const store = new EditorStore(editableLayout(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  const before = structuredClone(store.layout.slots.map((slot) => slot.geometry.position_mm));
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, { timeoutMs: 10_000 });
  nudge.handleKeyDown({ direction: "ArrowRight", step: 0.1, dx: 0.1, dy: 0 });
  nudge.handleKeyDown({ direction: "ArrowRight", step: 0.1, dx: 0.1, dy: 0, repeat: true });
  assert.deepEqual(store.layout.slots.map((slot) => slot.geometry.position_mm), before);
  assert.equal(store.undoStack.length, 0);
  assert.equal(store.hasUnsavedChanges(), false);
  assert.equal(store.previewPositions[ids[0]].x_mm, before[0].x_mm + 0.2);
  nudge.handleKeyUp("ArrowRight");
  assert.equal(store.layout.slots[0].geometry.position_mm.x_mm, before[0].x_mm + 0.2);
  assert.equal(store.layout.slots[1].geometry.position_mm.x_mm, before[1].x_mm + 0.2);
  assert.equal(store.undoStack.length, 1);
  assert.equal(store.hasUnsavedChanges(), true);
  store.undo();
  assert.deepEqual(store.layout.slots.map((slot) => slot.geometry.position_mm), before);
  nudge.dispose();
});

test("nudge rejects no selection and locks without creating preview or history", () => {
  const store = new EditorStore(editableLayout(1));
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, { timeoutMs: 10_000 });
  assert.equal(nudge.handleKeyDown({ direction: "ArrowLeft", step: 0.1, dx: -0.1, dy: 0 }), false);
  store.setSelection([store.layout.slots[0].id], "replace");
  store.layout.slots[0].locks.geometry = ["ctp"];
  assert.throws(
    () => nudge.handleKeyDown({ direction: "ArrowLeft", step: 0.1, dx: -0.1, dy: 0 }),
    (error) => error.code === "SLOT_EDIT_LOCKED",
  );
  assert.equal(store.pointerSession, null);
  assert.equal(store.undoStack.length, 0);
  nudge.dispose();
});

test("direction, modifier and selection changes split batches deterministically", () => {
  const store = new EditorStore(editableLayout(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, { timeoutMs: 10_000 });
  nudge.handleKeyDown({ direction: "ArrowRight", step: 0.1, dx: 0.1, dy: 0 });
  nudge.handleKeyDown({ direction: "ArrowUp", step: 0.1, dx: 0, dy: 0.1 });
  assert.equal(store.undoStack.length, 1, "direction change commits the first batch");
  nudge.handleKeyDown({ direction: "ArrowUp", step: 1, dx: 0, dy: 1 });
  assert.equal(store.undoStack.length, 2, "step change commits the second batch");
  store.setSelection([ids[0]], "replace");
  assert.equal(store.undoStack.length, 3, "selection change commits only original ids");
  assert.equal(nudge.isActive(), false);
  nudge.dispose();
});

test("timeout and blur safely finalize a batch, while Escape cancels it without dirty", () => {
  const store = new EditorStore(editableLayout(1));
  store.setSelection([store.layout.slots[0].id], "replace");
  let timeoutCallback = null;
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, {
    timeoutMs: 5,
    setTimeout(callback) { timeoutCallback = callback; return 1; },
    clearTimeout() {},
  });
  nudge.handleKeyDown({ direction: "ArrowUp", step: 0.1, dx: 0, dy: 0.1 });
  timeoutCallback();
  assert.equal(store.undoStack.length, 1);
  nudge.handleKeyDown({ direction: "ArrowDown", step: 0.1, dx: 0, dy: -0.1 });
  nudge.finish();
  assert.equal(store.undoStack.length, 2, "blur/finalize commits one more batch");

  const cleanStore = new EditorStore(editableLayout(1));
  cleanStore.setSelection([cleanStore.layout.slots[0].id], "replace");
  const cleanNudge = new Nudge.Controller(cleanStore, Commands, EditPolicy, { timeoutMs: 10_000 });
  const before = structuredClone(cleanStore.layout.slots[0].geometry.position_mm);
  cleanNudge.handleKeyDown({ direction: "ArrowRight", step: 0.1, dx: 0.1, dy: 0 });
  const registry = editorRegistry();
  registry.execute(RegistryModule.ACTION_IDS.CANCEL, fullContext(cleanStore, cleanNudge));
  assert.deepEqual(cleanStore.layout.slots[0].geometry.position_mm, before);
  assert.equal(cleanStore.undoStack.length, 0);
  assert.equal(cleanStore.hasUnsavedChanges(), false);
  cleanNudge.dispose();
  nudge.dispose();
});

test("another document command finalizes nudge first and autosave starts only after confirmation", async () => {
  const store = new EditorStore(editableLayout(2));
  const ids = store.layout.slots.map((slot) => slot.id);
  store.setSelection(ids, "replace");
  let saves = 0;
  const saver = new SaveCoordinator(store, {
    async saveLayout(_url, revision, submitted) {
      saves += 1;
      const canonical = structuredClone(submitted);
      canonical.job.revision = revision + 1;
      return { layout: canonical };
    },
  }, "/save", { debounceMs: 1 });
  const nudge = new Nudge.Controller(store, Commands, EditPolicy, { timeoutMs: 10_000 });
  nudge.handleKeyDown({ direction: "ArrowRight", step: 1, dx: 1, dy: 0 });
  await new Promise((resolve) => setTimeout(resolve, 5));
  assert.equal(saves, 0, "preview never schedules autosave");
  store.executeCommand(new Commands.DeleteSlotsCommand(store.layout, [ids[1]]));
  assert.equal(store.undoStack.length, 2);
  assert.equal(store.undoStack[0].description, "Mover slots");
  assert.equal(store.undoStack[1].description, "Eliminar slots");
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(saves, 1, "both confirmed commands share the debounced save");
  nudge.dispose();
  saver.dispose();
});

test("Ctrl+S, undo, redo and help delegate through registered actions without extra layout commands", async () => {
  const store = new EditorStore(editableLayout(1));
  const slot = store.layout.slots[0];
  store.setSelection([slot.id], "replace");
  store.executeCommand(new Commands.MoveSlotsCommand(
    { [slot.id]: { x_mm: 100, y_mm: 120 } },
    { [slot.id]: { x_mm: 101, y_mm: 120 } },
  ));
  let saveCalls = 0;
  const context = fullContext(store, null, {
    saveCoordinator: { manualSave: async () => { saveCalls += 1; return true; } },
  });
  const registry = editorRegistry();
  const manager = new Shortcuts.Manager(registry, () => context);
  const saveEvent = keyEvent("s", { ctrlKey: true });
  manager.handleKeyDown(saveEvent);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(saveEvent.prevented, 1);
  assert.equal(saveCalls, 1);
  manager.handleKeyDown(keyEvent("z", { ctrlKey: true }));
  assert.equal(store.layout.slots[0].geometry.position_mm.x_mm, 100);
  manager.handleKeyDown(keyEvent("y", { ctrlKey: true }));
  assert.equal(store.layout.slots[0].geometry.position_mm.x_mm, 101);
  const beforeVersion = store.changeVersion;
  const beforeRevision = store.revision;
  manager.handleKeyDown(keyEvent("?", { shiftKey: true }));
  assert.equal(context.shortcutHelp.opened, true);
  assert.equal(store.changeVersion, beforeVersion);
  assert.equal(store.revision, beforeRevision);
  assert.equal(store.undoStack.length, 1);
  manager.handleKeyDown(keyEvent("Escape"));
  assert.equal(context.shortcutHelp.opened, false);
  assert.equal(store.changeVersion, beforeVersion);
  manager.dispose();
});

test("invalid pending inspector blocks save while a valid pending edit confirms before one save", async () => {
  const store = new EditorStore(editableLayout(1));
  const registry = editorRegistry();
  let saveCalls = 0;
  const invalidInspector = {
    hasPendingDraft: () => true,
    hasInvalidDraft: () => true,
    confirmPending: () => false,
    cancelPending: () => false,
  };
  let context = fullContext(store, null, {
    positionInspector: invalidInspector,
    saveCoordinator: { manualSave: async () => { saveCalls += 1; return true; } },
  });
  assert.equal(await registry.execute(RegistryModule.ACTION_IDS.SAVE, context), false);
  assert.equal(saveCalls, 0);

  let confirms = 0;
  context = fullContext(store, null, {
    positionInspector: {
      hasPendingDraft: () => true,
      hasInvalidDraft: () => false,
      confirmPending: () => { confirms += 1; return true; },
      cancelPending: () => false,
    },
    saveCoordinator: { manualSave: async () => { saveCalls += 1; return true; } },
  });
  assert.equal(await registry.execute(RegistryModule.ACTION_IDS.SAVE, context), true);
  assert.equal(confirms, 1);
  assert.equal(saveCalls, 1);
});
