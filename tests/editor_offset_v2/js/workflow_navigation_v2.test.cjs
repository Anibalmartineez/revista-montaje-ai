"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const Workflow = require(path.join(
  repoRoot,
  "static/js/editor_offset_v2/workflow_navigation.js",
));

test("Fase 19-D conserva un orden de etapas estable", () => {
  assert.deepEqual(Workflow.STAGES, [
    "prepare",
    "impose",
    "adjust",
    "validate",
    "output",
  ]);
  assert.equal(Workflow.normalizeStage("VALIDATE"), "validate");
  assert.equal(Workflow.normalizeStage("desconocida", "prepare"), "prepare");
});

test("la navegación por teclado omite etapas deshabilitadas y es circular", () => {
  const stages = [
    { stage: "prepare", enabled: true },
    { stage: "impose", enabled: false },
    { stage: "adjust", enabled: true },
  ];
  assert.equal(Workflow.nextEnabledStage(stages, "prepare", 1), "adjust");
  assert.equal(Workflow.nextEnabledStage(stages, "adjust", 1), "prepare");
  assert.equal(Workflow.nextEnabledStage(stages, "prepare", -1), "adjust");
});

test("el resumen del pliego solo lee Layout V2", () => {
  const layout = { sheet: { size_mm: { width: 700, height: 500.25 } } };
  const before = structuredClone(layout);
  assert.equal(Workflow.formatSheetSize(layout), "700 × 500,25 mm");
  assert.equal(Workflow.formatSheetSize(null), "Sin pliego");
  assert.deepEqual(layout, before);
});
