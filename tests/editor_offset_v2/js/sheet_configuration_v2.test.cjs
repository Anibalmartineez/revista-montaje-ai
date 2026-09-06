"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Commands = require(path.join(repoRoot, "static/js/editor_offset_v2/commands.js"));
const RegistryModule = require(path.join(
  repoRoot,
  "static/js/editor_offset_v2/command_registry.js",
));
const SheetPanel = require(path.join(repoRoot, "static/js/editor_offset_v2/sheet_panel.js"));
const { EditorStore } = require(path.join(repoRoot, "static/js/editor_offset_v2/store.js"));

function fixture() {
  return JSON.parse(fs.readFileSync(
    path.join(repoRoot, "tests/fixtures/editor_offset_v2/layout_v2_complete.json"),
    "utf8",
  ));
}

function sheet(width, height, margins = {}) {
  return {
    size_mm: { width, height },
    printable_margins_mm: {
      left: margins.left ?? 0,
      right: margins.right ?? 0,
      bottom: margins.bottom ?? 0,
      top: margins.top ?? 0,
    },
  };
}

function actionContext(store, overrides = {}) {
  return {
    store,
    commands: Commands,
    interactions: {
      hasPanSession: () => false,
      ...(overrides.interactions || {}),
    },
    nudgeController: overrides.nudgeController || null,
    positionInspector: overrides.positionInspector || {
      hasPendingDraft: () => false,
    },
    arrangementPanel: overrides.arrangementPanel || {
      hasPendingDraft: () => false,
    },
  };
}

test("Fase 19-E acepta milímetros con punto o coma y valida el área útil", () => {
  assert.equal(SheetPanel.parseMillimetres(" 700,5 "), 700.5);
  assert.equal(SheetPanel.parseMillimetres("500.25"), 500.25);
  assert.equal(SheetPanel.parseMillimetres(""), null);
  assert.equal(SheetPanel.parseMillimetres("10 mm"), null);

  const valid = SheetPanel.validateSheetDraft({
    width: "700",
    height: "500",
    left: "10",
    right: "15",
    bottom: "20",
    top: "25",
  });
  assert.equal(valid.valid, true);
  assert.deepEqual(SheetPanel.usefulArea(valid.sheet), { width: 675, height: 455 });

  const invalid = SheetPanel.validateSheetDraft({
    width: "100",
    height: "50",
    left: "60",
    right: "40",
    bottom: "-1",
    top: "0",
  });
  assert.equal(invalid.valid, false);
  assert.match(invalid.errors.left, /menor que el ancho/);
  assert.match(invalid.errors.bottom, /cero o mayor/);
});

test("el impacto diferencia slots dentro, fuera del imprimible y fuera del pliego", () => {
  const layout = {
    slots: [
      {
        geometry: {
          position_mm: { x_mm: 50, y_mm: 50 },
          trim_size_mm: { width: 20, height: 20 },
          bleed_mm: 0,
          rotation_deg: 0,
        },
      },
      {
        geometry: {
          position_mm: { x_mm: 5, y_mm: 50 },
          trim_size_mm: { width: 10, height: 10 },
          bleed_mm: 0,
          rotation_deg: 0,
        },
      },
      {
        geometry: {
          position_mm: { x_mm: 210, y_mm: 50 },
          trim_size_mm: { width: 20, height: 20 },
          bleed_mm: 0,
          rotation_deg: 0,
        },
      },
    ],
  };
  assert.deepEqual(
    SheetPanel.placementImpact(layout, sheet(200, 100, {
      left: 10, right: 10, bottom: 10, top: 10,
    })),
    {
      total: 3,
      inside: 1,
      outsideSheet: 1,
      outsidePrintable: 1,
      warningCount: 2,
    },
  );
});

test("UpdateSheetCommand cambia solo el pliego y conserva slots exactos en undo/redo", () => {
  const layout = fixture();
  const beforeSheet = structuredClone(layout.sheet);
  const beforeSlots = structuredClone(layout.slots);
  const command = new Commands.UpdateSheetCommand(
    layout,
    sheet(640, 460, { left: 12, right: 13, bottom: 14, top: 15 }),
  );

  command.execute(layout);
  assert.deepEqual(layout.sheet.size_mm, { width: 640, height: 460 });
  assert.deepEqual(layout.sheet.printable_margins_mm, {
    left: 12, right: 13, bottom: 14, top: 15,
  });
  assert.deepEqual(layout.slots, beforeSlots);
  command.undo(layout);
  assert.deepEqual(layout.sheet, beforeSheet);
  assert.deepEqual(layout.slots, beforeSlots);
  command.redo(layout);
  assert.deepEqual(layout.slots, beforeSlots);
  assert.throws(
    () => new Commands.UpdateSheetCommand(layout, sheet(0, 500)),
    /mayores que cero/,
  );
  assert.throws(
    () => new Commands.UpdateSheetCommand(layout, sheet(100, 100, { left: 50, right: 50 })),
    /ancho imprimible/,
  );
  assert.throws(
    () => new Commands.UpdateSheetCommand(layout, structuredClone(layout.sheet)),
    /no contiene cambios/,
  );
});

test("sheet.update entra una sola vez al historial y se bloquea con drafts pendientes", () => {
  const store = new EditorStore(fixture());
  const beforeSlots = structuredClone(store.layout.slots);
  const registry = new RegistryModule.ActionRegistry();
  RegistryModule.registerEditorActions(registry);
  const context = actionContext(store);

  assert.equal(RegistryModule.ACTION_IDS.SHEET_UPDATE, "sheet.update");
  assert.equal(registry.isEnabled(RegistryModule.ACTION_IDS.SHEET_UPDATE, context), true);
  const result = registry.execute(
    RegistryModule.ACTION_IDS.SHEET_UPDATE,
    context,
    { sheet: sheet(610, 430, { left: 5, right: 5, bottom: 8, top: 8 }) },
  );
  assert.equal(result.changed, true);
  assert.equal(store.undoStack.length, 1);
  assert.equal(store.saveState.status, "dirty");
  assert.deepEqual(store.layout.slots, beforeSlots);
  store.undo();
  assert.deepEqual(store.layout.slots, beforeSlots);

  const pending = actionContext(store, {
    positionInspector: { hasPendingDraft: () => true },
  });
  assert.equal(registry.isEnabled(RegistryModule.ACTION_IDS.SHEET_UPDATE, pending), false);
});
