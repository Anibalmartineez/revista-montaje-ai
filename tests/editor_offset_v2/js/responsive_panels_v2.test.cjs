"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "../../..");
const ResponsivePanels = require(path.join(
  repoRoot,
  "static/js/editor_offset_v2/responsive_panels.js",
));

class FakeElement {
  constructor() {
    this.attributes = new Map();
    this.classes = new Set();
    this.listeners = new Map();
    this.hidden = true;
    this.inert = false;
    this.focused = false;
    this.classList = {
      toggle: (name, force) => {
        if (force) this.classes.add(name);
        else this.classes.delete(name);
      },
    };
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  removeEventListener(type) {
    this.listeners.delete(type);
  }

  dispatch(type) {
    this.listeners.get(type)?.({ currentTarget: this });
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }

  focus() {
    this.focused = true;
  }
}

function fixture(matches = true) {
  const listeners = new Set();
  const mediaQuery = {
    matches,
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
    change(next) {
      this.matches = next;
      for (const listener of listeners) listener({ matches: next });
    },
  };
  const refs = {
    objectsRegion: new FakeElement(),
    inspectorRegion: new FakeElement(),
    responsiveSourcesToggle: new FakeElement(),
    responsiveInspectorToggle: new FakeElement(),
    responsiveSourcesClose: new FakeElement(),
    responsiveInspectorClose: new FakeElement(),
    responsivePanelBackdrop: new FakeElement(),
  };
  return { mediaQuery, refs };
}

test("Fase 19-F deriva el panel temporal desde la etapa sin tocar Layout V2", () => {
  assert.equal(ResponsivePanels.panelForStage("prepare"), "sources");
  assert.equal(ResponsivePanels.panelForStage("impose"), "inspector");
  assert.equal(ResponsivePanels.panelForStage("adjust"), "inspector");
  assert.equal(ResponsivePanels.panelForStage("validate"), "inspector");
  assert.equal(ResponsivePanels.panelForStage("output"), "inspector");
  assert.equal(ResponsivePanels.validPanelName("desconocido"), null);
});

test("los cajones compactos son exclusivos, restauran foco y se desactivan en escritorio", () => {
  const { mediaQuery, refs } = fixture(true);
  const controller = new ResponsivePanels.Controller(refs, { mediaQuery });

  assert.equal(refs.objectsRegion.inert, true);
  assert.equal(refs.inspectorRegion.inert, true);
  assert.equal(refs.responsivePanelBackdrop.hidden, true);

  refs.responsiveSourcesToggle.dispatch("click");
  assert.equal(controller.isOpen("sources"), true);
  assert.equal(refs.objectsRegion.classes.has("is-responsive-open"), true);
  assert.equal(refs.inspectorRegion.classes.has("is-responsive-open"), false);
  assert.equal(refs.responsiveSourcesToggle.attributes.get("aria-expanded"), "true");
  assert.equal(refs.responsiveInspectorToggle.attributes.get("aria-expanded"), "false");
  assert.equal(refs.responsivePanelBackdrop.hidden, false);
  assert.equal(refs.responsiveSourcesClose.focused, true);

  refs.responsiveSourcesClose.dispatch("click");
  assert.equal(controller.isOpen(), false);
  assert.equal(refs.responsiveSourcesToggle.focused, true);
  assert.equal(refs.responsivePanelBackdrop.hidden, true);

  mediaQuery.change(false);
  assert.equal(refs.objectsRegion.inert, false);
  assert.equal(refs.inspectorRegion.inert, false);
  assert.equal(refs.objectsRegion.attributes.has("aria-hidden"), false);
  assert.equal(refs.inspectorRegion.attributes.has("aria-hidden"), false);
  controller.destroy();
});
