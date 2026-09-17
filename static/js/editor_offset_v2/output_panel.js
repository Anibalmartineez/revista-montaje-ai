(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.OutputPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const ISSUE_LABELS = Object.freeze({
    UNSUPPORTED_SOURCE_PAGE: "Página distinta de 1 no soportada",
    UNSUPPORTED_PDF_BOX: "Caja PDF distinta de TrimBox no soportada",
    UNSUPPORTED_INTRINSIC_ROTATION: "Rotación intrínseca no soportada",
    UNSUPPORTED_CONTENT_FIT_MODE: "Modo de ajuste interno no soportado",
    UNSUPPORTED_CONTENT_SCALE: "Escala interna no soportada",
    UNSUPPORTED_CONTENT_OFFSET: "Desplazamiento interno no soportado",
    UNSUPPORTED_CONTENT_ROTATION: "Rotación interna no soportada",
    UNSUPPORTED_CONTENT_MIRROR: "Espejo interno no soportado",
    UNSUPPORTED_CONTENT_CLIP: "Recorte interno no soportado",
    SOURCE_TRIM_SIZE_MISMATCH: "Tamaño fuente/trim incompatible",
    ASSET_NOT_READY: "Asset no listo o placeholder",
    ASSET_IDENTITY_MISMATCH: "Identidad física del asset distinta",
    ASSET_MISSING: "Asset usado no encontrado",
    ASSET_UNSAFE_PATH: "Ruta física de asset no segura",
    PDF_UNREADABLE: "PDF físico no legible",
    PDF_METADATA_MISMATCH: "Metadata física del PDF distinta",
    PDF_SEMANTICS_UNSUPPORTED: "Página o caja PDF ausente",
    TRIM_OUTSIDE_SHEET: "Trim fuera del pliego",
    BLEED_OUTSIDE_PRINTABLE: "Bleed fuera del área imprimible",
    TRIM_OVERLAP: "Trim superpuesto",
    BLEED_OVERLAP: "Bleed superpuesto",
    OUTPUT_FEATURE_UNSUPPORTED: "Función de salida no soportada todavía",
  });

  const DIAGNOSIS_INVALIDATING_EVENTS = Object.freeze([
    "command",
    "undo",
    "redo",
    "external_update",
  ]);

  function issueLabel(issue) {
    return (issue.code === "OUTPUT_FEATURE_UNSUPPORTED" && issue.message) || ISSUE_LABELS[issue.code] || issue.message || issue.code;
  }

  function groupIssues(issues, layout) {
    const slots = new Map((layout?.slots || []).map((slot) => [slot.id, slot]));
    const groups = new Map();
    for (const issue of issues || []) {
      const slot = issue.slot_id ? slots.get(issue.slot_id) : null;
      const workId = slot?.work_id || issue.work_id || null;
      const assetId = issue.asset_id || slot?.source?.asset_id || null;
      const key = issue.slot_id
        ? [issue.level, issue.code, assetId || "", workId || ""].join("|")
        : [issue.level, issue.code, issue.path || ""].join("|");
      if (!groups.has(key)) {
        groups.set(key, {
          code: issue.code,
          level: issue.level,
          message: issue.message,
          path: issue.path || null,
          assetId,
          workId,
          slotIds: [],
          count: 0,
        });
      }
      const group = groups.get(key);
      group.count += 1;
      if (issue.slot_id && !group.slotIds.includes(issue.slot_id)) {
        group.slotIds.push(issue.slot_id);
      }
    }
    return [...groups.values()].map((group) => ({
      ...group,
      slotIds: [...group.slotIds].sort(),
    }));
  }

  function renderIssueGroup(group) {
    const item = document.createElement("li");
    item.dataset.code = group.code;
    item.dataset.level = group.level;
    item.dataset.affectedSlots = String(group.slotIds.length);

    const summary = document.createElement("span");
    const scope = [
      group.workId && `work ${group.workId}`,
      group.assetId && `asset ${group.assetId}`,
      group.slotIds.length && `${group.slotIds.length} slot${group.slotIds.length === 1 ? "" : "s"} afectado${group.slotIds.length === 1 ? "" : "s"}`,
      !group.slotIds.length && group.path,
    ].filter(Boolean);
    summary.textContent = `${issueLabel(group)}${scope.length ? ` · ${scope.join(" · ")}` : ""}`;
    item.append(summary);

    if (group.slotIds.length) {
      const details = document.createElement("details");
      const toggle = document.createElement("summary");
      toggle.textContent = group.slotIds.length === 1 ? "Ver ID completo" : "Ver IDs completos";
      const ids = document.createElement("ul");
      for (const slotId of group.slotIds) {
        const row = document.createElement("li");
        const code = document.createElement("code");
        code.textContent = slotId;
        row.append(code);
        ids.append(row);
      }
      details.append(toggle, ids);
      item.append(details);
    }
    return item;
  }

  function groupPreflightIssues(issues) {
    const groups = new Map();
    for (const issue of issues || []) {
      const refs = issue.references || {};
      const key = [issue.severity, issue.code, issue.message, refs.path || ""].join("|");
      if (!groups.has(key)) {
        groups.set(key, {
          code: issue.code,
          level: issue.severity,
          message: issue.message,
          path: refs.path || null,
          assetId: (refs.asset_ids || [])[0] || null,
          workId: (refs.work_ids || [])[0] || null,
          slotIds: [...(refs.slot_ids || [])],
          count: 0,
        });
      }
      const group = groups.get(key);
      group.count += 1;
      for (const slotId of refs.slot_ids || []) {
        if (!group.slotIds.includes(slotId)) group.slotIds.push(slotId);
      }
    }
    return [...groups.values()].map((group) => ({
      ...group,
      slotIds: [...group.slotIds].sort(),
    }));
  }

  class Panel {
    constructor(store, refs, api, saver, context) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.checkedRevision = null;
      this.diagnosisStale = false;
      this.preflightReport = null;
      this.preflightStale = false;
      this.unsubscribe = this.store.subscribe((event) => this.onStoreEvent(event));
      this.refs.outputCheck.addEventListener("click", () => this.check());
      this.refs.preflightRun?.addEventListener("click", () => this.runPreflight());
    }

    onStoreEvent(event) {
      if (DIAGNOSIS_INVALIDATING_EVENTS.includes(event.type)) {
        this.invalidate();
        this.invalidatePreflight();
        return;
      }
      if (event.type === "save_success"
          && this.checkedRevision !== null
          && (this.diagnosisStale || this.checkedRevision !== this.store.revision)) {
        this.invalidate();
      }
      if (event.type === "save_success" && this.preflightReport && this.preflightReport.subject.revision !== this.store.revision) {
        this.invalidatePreflight();
      }
    }

    staleMessage() {
      if (this.store.hasUnsavedChanges()) {
        return (
          `Diagnóstico desactualizado · la revisión ${this.checkedRevision} tiene cambios pendientes. `
          + "Guarda y vuelve a consultar compatibilidad."
        );
      }
      return (
        `Diagnóstico desactualizado · se comprobó la revisión ${this.checkedRevision}, `
        + `pero la revisión actual es ${this.store.revision}. `
        + "Vuelve a consultar compatibilidad."
      );
    }

    invalidate() {
      if (this.checkedRevision === null) return false;
      this.diagnosisStale = true;
      this.refs.outputStatus.textContent = this.staleMessage();
      this.refs.outputStatus.dataset.state = "warning";
      this.refs.outputIssues.replaceChildren();
      return true;
    }

    invalidatePreflight() {
      if (!this.preflightReport || !this.refs.preflightStatus) return false;
      this.preflightStale = true;
      this.refs.preflightStatus.textContent = "Preflight desactualizado · guarda y vuelve a ejecutarlo.";
      this.refs.preflightStatus.dataset.state = "warning";
      this.refs.preflightIssues?.replaceChildren();
      if (this.refs.preflightSummary) this.refs.preflightSummary.textContent = "El reporte corresponde a una revisión anterior.";
      return true;
    }

    async runPreflight() {
      if (!this.refs.preflightRun || !this.context.preflight_api_url) return;
      this.refs.preflightRun.disabled = true;
      this.refs.preflightStatus.textContent = "Analizando la revisión guardada y sus fuentes físicas…";
      this.refs.preflightStatus.dataset.state = "pending";
      this.refs.preflightIssues?.replaceChildren();
      if (this.refs.preflightSummary) this.refs.preflightSummary.textContent = "";
      this.preflightReport = null;
      this.preflightStale = false;
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de ejecutar el preflight.");
        }
        const result = await this.api.runPreflight(this.context.preflight_api_url);
        const report = result.report;
        this.preflightReport = report;
        if (this.store.hasUnsavedChanges() || this.store.revision !== report.subject.revision) {
          this.invalidatePreflight();
          return result;
        }
        const blocked = (report.decisions || []).filter((decision) => decision.status === "blocked").map((decision) => decision.operation);
        const errorCount = (report.issues || []).filter((issue) => issue.severity === "error").length;
        this.refs.preflightStatus.textContent = `Preflight completo · revisión ${report.subject.revision} · reporte ${report.report_id}`;
        this.refs.preflightStatus.dataset.state = errorCount ? "error" : "success";
        if (this.refs.preflightSummary) {
          this.refs.preflightSummary.textContent = blocked.length
            ? `Operaciones bloqueadas: ${blocked.join(", ")}. ${errorCount} error${errorCount === 1 ? "" : "es"} encontrado${errorCount === 1 ? "" : "s"}.`
            : "No hay operaciones bloqueadas.";
        }
        for (const group of groupPreflightIssues(report.issues)) {
          this.refs.preflightIssues?.append(renderIssueGroup(group));
        }
        return result;
      } catch (error) {
        this.refs.preflightStatus.textContent = error.message || "No se pudo ejecutar el preflight.";
        this.refs.preflightStatus.dataset.state = "error";
      } finally {
        this.refs.preflightRun.disabled = false;
      }
    }

    async check() {
      this.refs.outputCheck.disabled = true;
      this.refs.outputStatus.textContent = "Analizando la última revisión guardada…";
      this.refs.outputStatus.dataset.state = "pending";
      this.refs.outputIssues.replaceChildren();
      this.checkedRevision = null;
      this.diagnosisStale = false;
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de consultar la compatibilidad.");
        }
        const result = await this.api.getOutputCapabilities(
          this.context.output_capabilities_api_url,
        );
        this.checkedRevision = result.revision;
        if (this.store.hasUnsavedChanges() || this.store.revision !== result.revision) {
          this.invalidate();
          return result;
        }
        this.refs.outputStatus.textContent = result.compatible
          ? `Compatible con salida temporal · revisión ${result.revision}`
          : `No compatible con salida temporal · revisión ${result.revision}`;
        this.refs.outputStatus.dataset.state = result.compatible ? "success" : "error";
        for (const group of groupIssues(result.issues, this.store.layout)) {
          this.refs.outputIssues.append(renderIssueGroup(group));
        }
      } catch (error) {
        this.refs.outputStatus.textContent = error.message || "No se pudo consultar la compatibilidad.";
        this.refs.outputStatus.dataset.state = "error";
      } finally {
        this.refs.outputCheck.disabled = false;
      }
    }

    dispose() {
      this.unsubscribe?.();
      this.unsubscribe = null;
    }
  }

  return Object.freeze({
    ISSUE_LABELS,
    DIAGNOSIS_INVALIDATING_EVENTS,
    Panel,
    groupIssues,
    groupPreflightIssues,
    issueLabel,
    renderIssueGroup,
  });
});
