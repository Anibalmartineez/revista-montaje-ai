(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.WorkflowNavigation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STAGES = Object.freeze(["prepare", "impose", "adjust", "validate", "output"]);
  const STAGE_META = Object.freeze({
    prepare: Object.freeze({ title: "Preparar", description: "PDF y origen" }),
    impose: Object.freeze({ title: "Imponer", description: "Pliego y repetición" }),
    adjust: Object.freeze({ title: "Ajustar", description: "Posición y alineación" }),
    validate: Object.freeze({ title: "Validar", description: "Comprobaciones" }),
    output: Object.freeze({ title: "Salida · pendiente", description: "PDF y CTP" }),
  });

  function normalizeStage(value, fallback) {
    const candidate = String(value || "").trim().toLowerCase();
    if (STAGES.includes(candidate)) return candidate;
    return STAGES.includes(fallback) ? fallback : "adjust";
  }

  function nextEnabledStage(stages, currentStage, direction) {
    const enabled = stages.filter((entry) => entry && entry.enabled !== false);
    if (!enabled.length) return null;
    const currentIndex = Math.max(
      0,
      enabled.findIndex((entry) => entry.stage === currentStage),
    );
    const step = direction < 0 ? -1 : 1;
    return enabled[(currentIndex + step + enabled.length) % enabled.length].stage;
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === "") return null;
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return null;
    return String(Math.round(numeric * 1000) / 1000).replace(".", ",");
  }

  function formatSheetSize(layout) {
    const size = layout && layout.sheet && layout.sheet.size_mm;
    const width = formatNumber(size && size.width);
    const height = formatNumber(size && size.height);
    return width && height ? `${width} × ${height} mm` : "Sin pliego";
  }

  class Controller {
    constructor(store, refs, options) {
      this.store = store || null;
      this.refs = refs;
      this.options = options || {};
      this.hasJob = this.options.hasJob !== false && Boolean(this.store);
      this.runAction = typeof this.options.runAction === "function"
        ? this.options.runAction
        : null;
      this.isActionEnabled = typeof this.options.isActionEnabled === "function"
        ? this.options.isActionEnabled
        : () => false;
      this.duplicateActionId = this.options.duplicateActionId || null;
      this.activeStage = normalizeStage(
        this.options.initialStage || refs.workflow.dataset.initialStage,
        this.hasJob ? "adjust" : "prepare",
      );
      if (!this.hasJob) this.activeStage = "prepare";
      this.listeners = [];
      this.unsubscribe = null;
      this.bind();
      if (this.store) {
        this.unsubscribe = this.store.subscribe(() => this.renderContext());
      }
      this.selectStage(this.activeStage);
      this.renderContext();
    }

    listen(element, type, listener) {
      if (!element) return;
      element.addEventListener(type, listener);
      this.listeners.push(() => element.removeEventListener(type, listener));
    }

    stageEntries() {
      return this.refs.workflowTabs.map((tab) => ({
        stage: normalizeStage(tab.dataset.ev2StageTarget),
        enabled: !tab.disabled,
        tab,
      }));
    }

    bind() {
      for (const entry of this.stageEntries()) {
        this.listen(entry.tab, "click", () => this.selectStage(entry.stage));
        this.listen(entry.tab, "keydown", (event) => this.onTabKeydown(event, entry.stage));
      }
      this.listen(this.refs.workspaceDuplicate, "click", () => {
        if (this.runAction && this.duplicateActionId) {
          this.runAction(this.duplicateActionId);
        }
      });
      this.listen(this.refs.workspaceConfigureSheet, "click", () => {
        this.selectStage("impose", { focusSelector: "#ev2-sheet-width" });
      });
      this.listen(this.refs.workspaceOpenAlign, "click", () => {
        this.selectStage("adjust", { focusSelector: '[data-ev2-tool-anchor="align"]' });
      });
      this.listen(this.refs.workspaceOpenDistribute, "click", () => {
        this.selectStage("adjust", { focusSelector: '[data-ev2-tool-anchor="distribute"]' });
      });
      this.listen(this.refs.workspaceOpenRepeat, "click", () => {
        this.selectStage("impose", { focusSelector: "#ev2-stage-impose" });
      });
    }

    onTabKeydown(event, currentStage) {
      let stage = null;
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        stage = nextEnabledStage(this.stageEntries(), currentStage, -1);
      } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        stage = nextEnabledStage(this.stageEntries(), currentStage, 1);
      } else if (event.key === "Home") {
        stage = this.stageEntries().find((entry) => entry.enabled)?.stage || null;
      } else if (event.key === "End") {
        stage = [...this.stageEntries()].reverse().find((entry) => entry.enabled)?.stage || null;
      }
      if (!stage) return;
      event.preventDefault();
      this.selectStage(stage, { focusTab: true });
    }

    selectStage(stage, options) {
      const normalized = normalizeStage(stage, this.activeStage);
      const targetTab = this.stageEntries().find((entry) => entry.stage === normalized);
      if (!targetTab || !targetTab.enabled) return false;
      this.activeStage = normalized;
      this.refs.workflow.dataset.activeStage = normalized;
      for (const entry of this.stageEntries()) {
        const selected = entry.stage === normalized;
        entry.tab.setAttribute("aria-selected", String(selected));
        entry.tab.tabIndex = selected ? 0 : -1;
        entry.tab.classList.toggle("is-active", selected);
      }
      for (const panel of this.refs.workflowPanels) {
        panel.hidden = panel.dataset.ev2StagePanel !== normalized;
      }
      const meta = STAGE_META[normalized];
      this.refs.inspectorModeTitle.textContent = meta.title;
      this.refs.inspectorModeDescription.textContent = meta.description;

      const settings = options || {};
      if (settings.focusTab) targetTab.tab.focus();
      if (settings.focusSelector) {
        const target = document.querySelector(settings.focusSelector);
        if (target) {
          target.focus({ preventScroll: true });
          target.scrollIntoView({ block: "nearest" });
        }
      }
      return true;
    }

    renderContext() {
      const layout = this.store ? this.store.layout : null;
      this.refs.sheetSizeSummary.textContent = formatSheetSize(layout);
      this.refs.workspaceDuplicate.disabled = !(
        this.hasJob
        && this.duplicateActionId
        && this.isActionEnabled(this.duplicateActionId)
      );
    }

    destroy() {
      for (const remove of this.listeners.splice(0)) remove();
      if (this.unsubscribe) this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  return Object.freeze({
    Controller,
    STAGES,
    STAGE_META,
    normalizeStage,
    nextEnabledStage,
    formatSheetSize,
  });
});
