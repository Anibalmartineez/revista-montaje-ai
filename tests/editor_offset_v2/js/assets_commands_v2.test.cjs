"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));
const { thumbnailUrl } = require(path.join(repoRoot, "static/js/editor_offset_v2/assets_panel.js"));
const { isMaterializationCompatible } = require(path.join(repoRoot, "static/js/editor_offset_v2/content_transform_inspector.js"));

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

test("CreateWorksCommand creates one independent work per selected PDF page and undoes atomically", () => {
  const layout = fixture("layout_v2_complete.json");
  const asset = layout.assets[0];
  const page1 = structuredClone(asset.pages[0]);
  asset.pages = [
    page1,
    { ...structuredClone(page1), number: 2, preview_key: "assets/asset_card_front/thumbnails/page_2.png" },
    { ...structuredClone(page1), number: 3, preview_key: "assets/asset_card_front/thumbnails/page_3.png" },
  ];
  asset.page_count = asset.pages.length;
  const entries = asset.pages.map((page, index) => ({
    source: { asset_id: asset.id, page: page.number, pdf_box: "trim" },
    values: { name: `Revista · pág. ${page.number}`, requestedForms: index + 1 },
  }));
  const works = commands.createWorksFromSources(
    layout,
    entries,
    { width: 90, height: 50, bleed: 3, allowedRotations: [0], useSameSourceForBack: false },
    (entry) => `multi_${entry.source.page}`,
  );
  const command = new commands.CreateWorksCommand(works);
  const initialCount = layout.works.length;
  command.execute(layout);
  assert.equal(layout.works.length, initialCount + 3);
  assert.deepEqual(layout.works.slice(-3).map((work) => work.front_source.page), [1, 2, 3]);
  assert.deepEqual(layout.works.slice(-3).map((work) => work.requested_forms), [1, 2, 3]);
  command.undo(layout);
  assert.equal(layout.works.length, initialCount);
  command.redo(layout);
  assert.deepEqual(layout.works.slice(-3).map((work) => work.id), [
    "work_multi_1", "work_multi_2", "work_multi_3",
  ]);
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

test("SetContentTransformCommand applies graphic corrections atomically and respects content locks", () => {
  const layout = fixture("layout_v2_complete.json");
  const target = layout.slots[0];
  const before = structuredClone(target.content_transform);
  const patch = {
    fit_mode: "cover",
    scale_x: 1.25,
    scale_y: 0.8,
    offset_mm: { x: 2.5, y: -1.5 },
    rotation_deg: 90,
    mirror_x: true,
    mirror_y: false,
    clip_to: "bleed_box",
  };
  const command = new commands.SetContentTransformCommand(layout, [target.id], patch);
  command.execute(layout);
  assert.deepEqual(target.content_transform, patch);
  command.undo(layout);
  assert.deepEqual(target.content_transform, before);
  command.redo(layout);
  assert.deepEqual(target.content_transform, patch);

  target.locks.content = ["user"];
  assert.throws(
    () => new commands.SetContentTransformCommand(layout, [target.id], { scale_x: 2 }),
    /slots bloqueados/,
  );
});

test("SetSlotDerivedSourceCommand connects and clears a versioned page without changing the original asset", () => {
  const layout = fixture("layout_v2_complete.json");
  const target = layout.slots[0];
  const original = structuredClone(target.source);
  const originalAssetHash = layout.assets[0].sha256;
  const derived = {
    derived_key: "derived/assets/asset_card_front/page_1/r8_deadbeef.pdf",
    derived_sha256: "a".repeat(64),
    source_sha256: layout.assets[0].sha256,
  };
  const command = new commands.SetSlotDerivedSourceCommand(layout, [target.id], derived);
  command.execute(layout);
  assert.deepEqual(target.source.derived, derived);
  assert.equal(layout.assets[0].sha256, originalAssetHash);
  command.undo(layout);
  assert.deepEqual(target.source, original);
  command.redo(layout);
  assert.deepEqual(target.source.derived, derived);
  const clear = new commands.SetSlotDerivedSourceCommand(layout, [target.id], null);
  clear.execute(layout);
  assert.deepEqual(target.source, original);
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

test("derived materialization only enables for the identity transform matching the source box", () => {
  const slot = {
    source: { pdf_box: "trim" },
    content_transform: {
      fit_mode: "actual_size",
      scale_x: 1,
      scale_y: 1,
      offset_mm: { x: 0, y: 0 },
      rotation_deg: 0,
      mirror_x: false,
      mirror_y: false,
      clip_to: "trim_box",
    },
  };
  assert.equal(isMaterializationCompatible(slot), true);
  slot.content_transform.offset_mm.x = 0.01;
  assert.equal(isMaterializationCompatible(slot), false);
  slot.content_transform.offset_mm.x = 0;
  slot.content_transform.clip_to = "bleed_box";
  assert.equal(isMaterializationCompatible(slot), true);
  slot.content_transform.clip_to = "none";
  assert.equal(isMaterializationCompatible(slot), false);
});
