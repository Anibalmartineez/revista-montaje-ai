"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const root = path.resolve(__dirname, "../../..");
const commands = require(path.join(root, "static/js/editor_offset_v2/commands.js"));
const { EditorStore } = require(path.join(root, "static/js/editor_offset_v2/store.js"));
const objects = require(path.join(root, "static/js/editor_offset_v2/object_operations.js"));

function layout() {
  const value = JSON.parse(fs.readFileSync(path.join(root, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"), "utf8"));
  value.faces = { enabled: ["front"], duplex: { enabled: false, flip: "none" } };
  value.export.faces = { front: true, back: false, combine_in_single_pdf: false, order: ["front"] };
  value.slots = value.slots.filter(slot => slot.face === "front");
  return value;
}

test("habilitar Dorso es reversible y navegar no cambia layout, dirty ni historial", () => {
  const store = new EditorStore(layout());
  const before = structuredClone(store.layout);
  const command = new commands.ConfigureBackFaceCommand(store.layout, "none");
  store.executeCommand(command);
  assert.deepEqual(store.layout.faces, { enabled: ["front", "back"], duplex: { enabled: true, flip: "none" } });
  assert.deepEqual(store.layout.export.faces, { front: true, back: true, combine_in_single_pdf: true, order: ["front", "back"] });
  assert.equal(store.undoStack.length, 1);
  store.setSelection([store.layout.slots[0].id], "replace");
  store.setKeySlot(store.layout.slots[0].id);
  const version = store.changeVersion;
  assert.equal(store.setActiveFace("back"), true);
  assert.deepEqual([...store.selection], []);
  assert.equal(store.arrangement.keySlotId, null);
  assert.equal(store.changeVersion, version);
  assert.equal(store.undoStack.length, 1);
  assert.equal(Object.hasOwn(store.layout, "activeFace"), false);
  store.undo();
  assert.deepEqual(store.layout, before);
  assert.equal(store.activeFace, "front");
});

test("un slot manual Dorso usa la fuente elegida, aislado de Frente y del work", () => {
  const store = new EditorStore(layout());
  const front = structuredClone(store.layout.slots[0]);
  store.executeCommand(new commands.ConfigureBackFaceCommand(store.layout, "none"));
  const asset = store.layout.assets[0];
  const second = structuredClone(asset.pages[0]);
  second.number = 2;
  asset.pages.push(second);
  asset.page_count = asset.pages.length;
  const chosen = { asset_id: asset.id, page: 2, pdf_box: "trim" };
  const work = store.layout.works[0];
  const originalWork = structuredClone(work);
  const back = commands.createSlotFromWork(store.layout, work.id, "back_manual", { x_mm: 100, y_mm: 100 }, "back", chosen);
  store.executeCommand(new commands.CreateSlotFromWorkCommand(back));
  assert.equal(back.face, "back");
  assert.deepEqual(back.source, chosen);
  assert.deepEqual(work, originalWork);
  assert.deepEqual(store.layout.slots.find(slot => slot.id === front.id), front);
  store.setActiveFace("back");
  store.setSelection([front.id], "replace");
  assert.deepEqual([...store.selection], []);
  store.setSelection([back.id], "replace");
  objects.copySelection(store);
  assert.equal(objects.validateClipboard(store.layout, store.clipboard, "back").ok, true);
  const prepared = objects.createPasteCommand(store, commands, { idFactory: () => "slot_back_paste" });
  store.executeCommand(prepared.command);
  assert.equal(store.layout.slots.find(slot => slot.id === "slot_back_paste").face, "back");
  store.undo();
  assert.equal(store.layout.slots.some(slot => slot.id === "slot_back_paste"), false);
  store.setActiveFace("front");
  assert.equal(objects.validateClipboard(store.layout, store.clipboard, "front").ok, false);
  store.undo();
  assert.equal(store.layout.slots.some(slot => slot.id === back.id), false);
  store.redo();
  assert.equal(store.layout.slots.some(slot => slot.id === back.id), true);
  assert.deepEqual([...store.selection], []);
  assert.deepEqual(store.layout.slots.find(slot => slot.id === front.id), front);
});

test("autosave guarda ambas caras por CAS sin persistir activeFace", async () => {
  const { SaveCoordinator } = require(path.join(root, "static/js/editor_offset_v2/autosave.js"));
  const store = new EditorStore(layout());
  store.executeCommand(new commands.ConfigureBackFaceCommand(store.layout, "short_edge"));
  const work = store.layout.works[0];
  const back = commands.createSlotFromWork(store.layout, work.id, "save_back", { x_mm: 120, y_mm: 110 }, "back", work.front_source);
  store.executeCommand(new commands.CreateSlotFromWorkCommand(back));
  store.setActiveFace("back");
  let submitted;
  const api = {
    async saveLayout(_url, baseRevision, value) {
      submitted = { baseRevision, layout: structuredClone(value) };
      const canonical = structuredClone(value);
      canonical.job.revision = baseRevision + 1;
      return { layout: canonical, revision: baseRevision + 1 };
    },
  };
  const saver = new SaveCoordinator(store, api, "/save", { debounceMs: 1000 });
  try {
    assert.equal(await saver.manualSave(), true);
    assert.equal(submitted.baseRevision, 4);
    assert.equal(submitted.layout.slots.some(slot => slot.face === "back"), true);
    assert.equal(submitted.layout.slots.some(slot => slot.face === "front"), true);
    assert.equal(submitted.layout.faces.duplex.flip, "short_edge");
    assert.equal(Object.hasOwn(submitted.layout, "activeFace"), false);
    assert.equal(store.saveState.status, "clean");
  } finally {
    saver.dispose();
  }
});

test("Dorso acepta otra fuente PDF sin modificar el work ya colocado", () => {
  const value = layout();
  const otherAsset = structuredClone(value.assets[0]);
  otherAsset.id = "asset_back_pdf";
  value.assets.push(otherAsset);
  const workBefore = structuredClone(value.works[0]);
  const frontBefore = structuredClone(value.slots[0]);
  const store = new EditorStore(value);
  store.executeCommand(new commands.ConfigureBackFaceCommand(store.layout, "none"));
  const source = { asset_id: otherAsset.id, page: 1, pdf_box: "trim" };
  const back = commands.createSlotFromWork(store.layout, workBefore.id, "other_pdf", { x_mm: 250, y_mm: 120 }, "back", source);
  store.executeCommand(new commands.CreateSlotFromWorkCommand(back));
  assert.deepEqual(back.source, source);
  assert.deepEqual(store.layout.works[0], workBefore);
  assert.deepEqual(store.layout.slots[0], frontBefore);
});
