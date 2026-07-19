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
  });

  function issueLabel(issue) {
    return ISSUE_LABELS[issue.code] || issue.message || issue.code;
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

  class Panel {
    constructor(store, refs, api, saver, context) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.refs.outputCheck.addEventListener("click", () => this.check());
    }

    async check() {
      this.refs.outputCheck.disabled = true;
      this.refs.outputStatus.textContent = "Analizando la última revisión guardada…";
      this.refs.outputIssues.replaceChildren();
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de consultar la compatibilidad.");
        }
        const result = await this.api.getOutputCapabilities(
          this.context.output_capabilities_api_url,
        );
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
  }

  return Object.freeze({
    ISSUE_LABELS,
    Panel,
    groupIssues,
    issueLabel,
    renderIssueGroup,
  });
});
