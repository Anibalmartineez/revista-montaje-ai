(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.PrecisionPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  class Panel {
    constructor(store, refs, registry, contextProvider, actionIds, tools, geometry, runAction) {
      this.store = store;
      this.refs = refs;
      this.registry = registry;
      this.contextProvider = contextProvider;
      this.actionIds = actionIds;
      this.tools = tools;
      this.geometry = geometry;
      this.runAction = runAction;
      this.guideToken = 0;
      this.guidesKey = null;
      this.metricsKey = null;
      this.boundGuideListClick = (event) => this.onGuideListClick(event);
      this.boundGuideListKeyDown = (event) => this.onGuideListKeyDown(event);
      this.boundGuideListFocusOut = (event) => this.onGuideListFocusOut(event);
      this.unsubscribe = store.subscribe(() => this.render());
      this.bind();
      this.render();
    }

    bind() {
      const toggles = [
        [this.refs.precisionRulers, this.actionIds.PRECISION_RULERS_TOGGLE],
        [this.refs.precisionGuidesVisible, this.actionIds.PRECISION_GUIDES_TOGGLE],
        [this.refs.precisionSmartGuides, this.actionIds.PRECISION_SMART_GUIDES_TOGGLE],
        [this.refs.precisionSnapEnabled, this.actionIds.PRECISION_SNAP_TOGGLE],
      ];
      toggles.forEach(([element, actionId]) => element.addEventListener("change", () => {
        this.runAction(actionId, { enabled: element.checked });
      }));
      for (const [element, source] of [
        [this.refs.precisionSnapGuides, "guides"],
        [this.refs.precisionSnapSlots, "slots"],
        [this.refs.precisionSnapSheet, "sheet"],
        [this.refs.precisionSnapPrintable, "printable"],
      ]) {
        element.addEventListener("change", () => this.runAction(
          this.actionIds.PRECISION_SNAP_SOURCE_SET,
          { source, enabled: element.checked },
        ));
      }
      this.refs.precisionSnapReference.addEventListener("change", () => this.runAction(
        this.actionIds.PRECISION_SNAP_REFERENCE_SET,
        { reference: this.refs.precisionSnapReference.value },
      ));
      this.refs.precisionSnapThreshold.addEventListener("change", () => this.runAction(
        this.actionIds.PRECISION_SNAP_THRESHOLD_SET,
        { pixels: Number(this.refs.precisionSnapThreshold.value) },
      ));
      this.refs.precisionGuideForm.addEventListener("submit", (event) => {
        event.preventDefault();
        this.createGuide();
      });
      this.refs.precisionGuidesClear.addEventListener("click", () => {
        this.runAction(this.actionIds.PRECISION_GUIDES_CLEAR);
      });
      this.refs.precisionGuidesList.addEventListener("click", this.boundGuideListClick);
      this.refs.precisionGuidesList.addEventListener("keydown", this.boundGuideListKeyDown);
      this.refs.precisionGuidesList.addEventListener("focusout", this.boundGuideListFocusOut);
      this.refs.precisionMeasureToggle.addEventListener("click", () => this.runAction(
        this.actionIds.PRECISION_MEASURE_TOGGLE,
        { enabled: !this.store.precisionTools.measurementMode },
      ));
      this.refs.precisionMeasureClear.addEventListener("click", () => this.runAction(
        this.actionIds.PRECISION_MEASURE_CLEAR,
      ));
    }

    createGuide() {
      const parsed = this.tools.parseMillimetres(this.refs.precisionGuidePosition.value);
      if (!parsed.ok) {
        this.setGuideError(parsed.error);
        return false;
      }
      this.guideToken += 1;
      const result = this.runAction(this.actionIds.PRECISION_GUIDE_CREATE, {
        axis: this.refs.precisionGuideAxis.value,
        position_mm: parsed.value,
        token: `${Date.now().toString(36)}_${this.guideToken}`,
      });
      if (result === false) return false;
      this.refs.precisionGuidePosition.value = "";
      this.setGuideError("");
      return true;
    }

    onGuideListClick(event) {
      const row = event.target.closest("[data-guide-id]");
      if (!row) return;
      const id = row.dataset.guideId;
      this.store.setActiveGuide(id);
      const action = event.target.closest("button")?.dataset.guideAction;
      if (action === "delete") {
        this.runAction(this.actionIds.PRECISION_GUIDE_DELETE, { id });
      } else if (action === "update") {
        this.updateGuideFromRow(row);
      }
    }

    onGuideListKeyDown(event) {
      const row = event.target.closest("[data-guide-id]");
      if (!row) return;
      if (event.key === "Enter" && event.target.matches("input")) {
        event.preventDefault();
        event.stopPropagation();
        this.updateGuideFromRow(row);
      }
      if (event.key === "Escape" && event.target.matches("input")) {
        event.preventDefault();
        event.stopPropagation();
        this.restoreGuideInput(row);
        event.target.blur();
      }
      if (event.key === "Delete" && !event.target.matches("input")) {
        event.preventDefault();
        event.stopPropagation();
        this.runAction(this.actionIds.PRECISION_GUIDE_DELETE, { id: row.dataset.guideId });
      }
    }

    onGuideListFocusOut(event) {
      if (!event.target.matches("input")) return;
      const row = event.target.closest("[data-guide-id]");
      if (!row) return;
      const next = event.relatedTarget;
      if (next?.closest?.("[data-guide-id]") === row
          && next?.dataset?.guideAction === "update") return;
      this.restoreGuideInput(row);
    }

    restoreGuideInput(row) {
      const item = this.store.precisionTools.guides.find(
        (guide) => guide.id === row.dataset.guideId,
      );
      const input = row.querySelector("input");
      if (item && input) input.value = this.tools.formatMillimetres(item.position_mm);
      this.setGuideError("");
    }

    updateGuideFromRow(row) {
      const parsed = this.tools.parseMillimetres(row.querySelector("input")?.value);
      if (!parsed.ok) {
        this.setGuideError(parsed.error);
        return false;
      }
      const result = this.runAction(this.actionIds.PRECISION_GUIDE_UPDATE, {
        id: row.dataset.guideId,
        position_mm: parsed.value,
      });
      if (result !== false) this.setGuideError("");
      return result;
    }

    setGuideError(message) {
      this.refs.precisionGuideError.textContent = message || "";
      this.refs.precisionGuidePosition.setAttribute("aria-invalid", String(Boolean(message)));
    }

    renderGuides(state) {
      const nextKey = JSON.stringify({
        guides: state.precisionTools.guides,
        activeGuideId: state.precisionTools.activeGuideId,
      });
      if (nextKey === this.guidesKey) return;
      this.guidesKey = nextKey;
      this.refs.precisionGuidesList.replaceChildren();
      for (const item of state.precisionTools.guides) {
        const row = document.createElement("li");
        row.dataset.guideId = item.id;
        row.className = state.precisionTools.activeGuideId === item.id ? "is-active" : "";
        row.tabIndex = 0;
        row.setAttribute("aria-label", `${item.axis === "x" ? "Guía vertical" : "Guía horizontal"} ${item.position_mm} milímetros`);
        const label = document.createElement("span");
        label.textContent = item.axis === "x" ? "Vertical X" : "Horizontal Y";
        const input = document.createElement("input");
        input.type = "text";
        input.inputMode = "decimal";
        input.value = this.tools.formatMillimetres(item.position_mm);
        input.setAttribute("aria-label", `Posición de ${label.textContent} en milímetros`);
        const unit = document.createElement("span");
        unit.textContent = "mm";
        const update = document.createElement("button");
        update.type = "button";
        update.dataset.guideAction = "update";
        update.textContent = "Aplicar";
        const remove = document.createElement("button");
        remove.type = "button";
        remove.dataset.guideAction = "delete";
        remove.textContent = "Eliminar";
        row.append(label, input, unit, update, remove);
        this.refs.precisionGuidesList.append(row);
      }
      if (!state.precisionTools.guides.length) {
        const empty = document.createElement("li");
        empty.className = "is-empty";
        empty.textContent = "Sin guías temporales.";
        this.refs.precisionGuidesList.append(empty);
      }
      this.refs.precisionGuidesClear.disabled = !state.precisionTools.guides.length;
    }

    renderMeasurement(state) {
      const precision = state.precisionTools;
      this.refs.precisionMeasureToggle.textContent = precision.measurementMode
        ? "Salir de medición" : "Activar medición";
      this.refs.precisionMeasureToggle.setAttribute("aria-pressed", String(precision.measurementMode));
      this.refs.precisionMeasureClear.disabled = !precision.measurementDraft
        && !precision.lastMeasurement;
      const raw = precision.lastMeasurement || (precision.measurementDraft
        ? this.tools.measurement(
          precision.measurementDraft.start,
          precision.measurementDraft.current,
        ) : null);
      if (!raw) {
        this.refs.precisionMeasurementResult.textContent = precision.measurementMode
          ? "Haz click para fijar el primer punto." : "Sin medición.";
        return;
      }
      this.refs.precisionMeasurementResult.textContent = [
        `X1 ${this.tools.formatMillimetres(raw.start.x)} · Y1 ${this.tools.formatMillimetres(raw.start.y)} mm`,
        `X2 ${this.tools.formatMillimetres(raw.end.x)} · Y2 ${this.tools.formatMillimetres(raw.end.y)} mm`,
        `ΔX ${this.tools.formatMillimetres(raw.deltaX)} · ΔY ${this.tools.formatMillimetres(raw.deltaY)} mm`,
        `Distancia ${this.tools.formatMillimetres(raw.distance)} mm`,
      ].join("\n");
    }

    renderMetrics(state) {
      const key = [
        this.store.changeVersion,
        state.selection.join("|"),
        state.arrangement.geometryReference,
        state.advancedSelection.visibilityVersion,
        state.activeFace,
      ].join(":");
      if (key === this.metricsKey) return;
      this.metricsKey = key;
      const metrics = this.tools.selectionMetrics(
        state.layout,
        state.selection,
        this.geometry,
        {
          reference: state.arrangement.geometryReference,
          activeFace: state.activeFace,
          hiddenSlotIds: state.advancedSelection.hiddenSlotIds,
        },
      );
      if (!metrics.count) {
        this.refs.precisionSelectionMetrics.textContent = "Sin selección visible.";
        return;
      }
      const f = (value) => this.tools.formatMillimetres(value);
      if (metrics.count === 1) {
        this.refs.precisionSelectionMetrics.textContent = [
          `1 slot · referencia ${metrics.reference === "trim" ? "Trim" : "Footprint"}`,
          `Centro X ${f(metrics.center.x)} · Y ${f(metrics.center.y)} mm`,
          `Trim ${f(metrics.trimBounds.width)} × ${f(metrics.trimBounds.height)} mm`,
          `Footprint ${f(metrics.productiveBounds.width)} × ${f(metrics.productiveBounds.height)} mm`,
          `Rotación ${metrics.rotationDeg}°`,
        ].join("\n");
      } else if (metrics.count === 2) {
        const pair = metrics.pair;
        this.refs.precisionSelectionMetrics.textContent = [
          `2 slots · referencia ${metrics.reference === "trim" ? "Trim" : "Footprint"}`,
          `IDs ${pair.ids.join(" ↔ ")}`,
          `Gap X ${f(pair.gapX)} · Gap Y ${f(pair.gapY)} mm`,
          `Δ centros X ${f(pair.deltaX)} · Y ${f(pair.deltaY)} mm`,
          `Distancia entre centros ${f(pair.centerDistance)} mm`,
          pair.overlaps
            ? `Overlap sí · X ${f(pair.overlapX)} · Y ${f(pair.overlapY)} · área ${f(pair.overlapArea)} mm²`
            : "Overlap no",
        ].join("\n");
      } else {
        this.refs.precisionSelectionMetrics.textContent = [
          `${metrics.count} slots · referencia ${metrics.reference === "trim" ? "Trim" : "Footprint"}`,
          `Aggregate ${f(metrics.aggregate.width)} × ${f(metrics.aggregate.height)} mm`,
          `Gap H mín ${f(metrics.horizontalGapMin)} · máx ${f(metrics.horizontalGapMax)} mm`,
          `Gap V mín ${f(metrics.verticalGapMin)} · máx ${f(metrics.verticalGapMax)} mm`,
          `Pares con overlap: ${metrics.overlapPairs}`,
        ].join("\n");
      }
    }

    render() {
      const state = this.store.getState();
      const precision = state.precisionTools;
      this.refs.precisionRulers.checked = precision.rulersVisible;
      this.refs.precisionGuidesVisible.checked = precision.guidesVisible;
      this.refs.precisionSmartGuides.checked = precision.smartGuidesVisible;
      this.refs.precisionSnapEnabled.checked = precision.snapEnabled;
      this.refs.precisionSnapGuides.checked = precision.snapToGuides;
      this.refs.precisionSnapSlots.checked = precision.snapToSlots;
      this.refs.precisionSnapSheet.checked = precision.snapToSheet;
      this.refs.precisionSnapPrintable.checked = precision.snapToPrintable;
      this.refs.precisionSnapReference.value = state.arrangement.geometryReference;
      this.refs.precisionSnapThreshold.value = String(precision.snapThresholdPx);
      this.renderGuides(state);
      this.renderMeasurement(state);
      this.renderMetrics(state);
      this.refs.precisionLive.textContent = precision.activeGuideId
        ? `Guía seleccionada ${precision.activeGuideId}.`
        : precision.snapEnabled ? "Snap activo para arrastre." : "Snap desactivado.";
    }

    cancelActiveDraft() {
      if (this.store.precisionTools.measurementDraft) {
        return this.store.cancelMeasurementDraft();
      }
      if (this.refs.precisionGuidePosition.value) {
        this.refs.precisionGuidePosition.value = "";
        this.setGuideError("");
        return true;
      }
      return false;
    }

    dispose() {
      this.unsubscribe();
      this.refs.precisionGuidesList.removeEventListener("click", this.boundGuideListClick);
      this.refs.precisionGuidesList.removeEventListener("keydown", this.boundGuideListKeyDown);
      this.refs.precisionGuidesList.removeEventListener("focusout", this.boundGuideListFocusOut);
    }
  }

  return Object.freeze({ Panel });
});
