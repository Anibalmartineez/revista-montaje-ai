"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const { thumbnailUrl } = require(path.join(repoRoot, "static/js/editor_offset_v2/assets_panel.js"));

function fixture(name) {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2", name),
    "utf8",
  ));
}

function realSource(layout, assetIndex = 0) {
  return {
    asset_id: layout.assets[assetIndex].id,
    page: 1,
    pdf_box: "trim",
  };
}

test("CreateWorkCommand builds a valid real-source work and reverses cleanly", () => {
  const layout = fixture("layout_v2_complete.json");
  const initialCount = layout.works.length;
  const work = commands.createWorkFromSource(
    layout,
    realSource(layout),
    {
      name: "Tarjeta adicional",
      width: 90,
      height: 50,
      bleed: 3,
      requestedForms: 12,
      allowedRotations: [0, 90],
      useSameSourceForBack: true,
    },
    "asset_work",
  );
  const command = new commands.CreateWorkCommand(work);

  command.execute(layout);
  assert.equal(layout.works.length, initialCount + 1);
  assert.deepEqual(layout.works.at(-1).front_source, realSource(layout));
  assert.deepEqual(layout.works.at(-1).back_source, realSource(layout));
  command.undo(layout);
  assert.equal(layout.works.length, initialCount);
  command.redo(layout);
  assert.equal(layout.works.at(-1).id, "work_asset_work");
});

test("CreateSlotFromWorkCommand creates a real cardinal slot at visible center", () => {
  const layout = fixture("layout_v2_complete.json");
  const workId = layout.works[0].id;
  const slot = commands.createSlotFromWork(
    layout,
    workId,
    "real_slot",
    { x_mm: 350.5, y_mm: 249.25 },
  );
  const command = new commands.CreateSlotFromWorkCommand(slot);

  command.execute(layout);
  assert.equal(layout.slots.at(-1).id, "slot_real_slot");
  assert.equal(layout.slots.at(-1).work_id, workId);
  assert.deepEqual(layout.slots.at(-1).source, layout.works[0].front_source);
  assert.deepEqual(layout.slots.at(-1).geometry.position_mm, {
    x_mm: 350.5,
    y_mm: 249.25,
    anchor: "trim_center",
  });
  assert.equal(layout.slots.at(-1).content_transform.fit_mode, "actual_size");
  assert.equal(layout.slots.at(-1).generated_by.type, "manual");
  command.undo(layout);
  assert.equal(layout.slots.some((item) => item.id === "slot_real_slot"), false);
});

test("ReplaceSlotSourceCommand changes only one slot and undo restores source", () => {
  const layout = fixture("layout_v2_complete.json");
  const target = layout.slots[0];
  const untouched = structuredClone(layout.slots[1]);
  const original = structuredClone(target.source);
  const replacement = realSource(layout, 1);
  const replacementBox = layout.assets[1].pages[0].boxes_mm.trim;
  replacementBox.width = 80;
  replacementBox.height = 40;
  const command = new commands.ReplaceSlotSourceCommand(layout, target.id, replacement);

  assert.match(command.dimensionWarning, /80\.00 × 40\.00/);
  command.execute(layout);
  assert.deepEqual(target.source, replacement);
  assert.deepEqual(layout.slots[1], untouched);
  command.undo(layout);
  assert.deepEqual(target.source, original);
  command.redo(layout);
  assert.deepEqual(target.source, replacement);
});

test("server asset incorporation updates revision only while store is clean", () => {
  const minimal = fixture("layout_v2_minimal.json");
  const complete = fixture("layout_v2_complete.json");
  const store = new EditorStore(minimal);
  const canonical = structuredClone(minimal);
  canonical.assets.push(complete.assets[0]);
  canonical.job.revision += 1;
  canonical.job.updated_at = "2026-07-19T12:00:00Z";

  store.applyServerLayout(canonical);
  assert.equal(store.revision, canonical.job.revision);
  assert.equal(store.layout.assets.length, 1);
  assert.equal(store.assetPanel.selectedAssetId, complete.assets[0].id);
  assert.equal(store.assetPanel.selectedPdfBox, "trim");
  assert.equal(store.saveState.status, "clean");

  const work = commands.createWorkFromSource(
    store.layout,
    realSource(store.layout),
    {
      name: "Dirty",
      width: 90,
      height: 50,
      bleed: 0,
      requestedForms: 1,
      allowedRotations: [0],
      useSameSourceForBack: false,
    },
    "dirty",
  );
  store.executeCommand(new commands.CreateWorkCommand(work));
  assert.throws(() => store.applyServerLayout(canonical), /local changes/);
});

test("thumbnail URL is derived from the server-owned asset API boundary", () => {
  assert.equal(
    thumbnailUrl("/api/editor-offset-v2/jobs/ev2_x/assets", "asset_a b", 3),
    "/api/editor-offset-v2/jobs/ev2_x/assets/asset_a%20b/thumbnails/3",
  );
});
