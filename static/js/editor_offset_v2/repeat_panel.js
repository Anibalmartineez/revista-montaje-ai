(function (root, factory) {
  "use strict";
  const layoutMetrics = typeof module === "object" && module.exports
    ? require("./layout_metrics.js")
    : root.EditorOffsetV2?.LayoutMetrics;
  const preparation = typeof module === "object" && module.exports
    ? require("./preparation.js")
    : root.EditorOffsetV2?.Preparation;
  const api = factory(layoutMetrics, preparation);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.RepeatPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (LayoutMetrics, Preparation) {
  "use strict";

  if (!LayoutMetrics || !Preparation) throw new Error("Editor V2 layout metrics and PDF preparation are required");

  function selectedWorkIds(container) {
    return [...container.querySelectorAll('input[type="checkbox"]:checked')]
      .map((input) => input.value);
  }

  function readSettings(refs) {
    return {
      horizontal_gap_mm: Number(refs.repeatGapX.value),
      vertical_gap_mm: Number(refs.repeatGapY.value),
      exact_quantity: true,
      fill_remaining_space: refs.repeatFill.checked,
      allow_partial: refs.repeatPartial.checked,
    };
  }

  function proposalSignature(proposal) {
    return JSON.stringify((proposal?.slots || []).map((slot) =>
      [slot.work_id, slot.face, slot.source, slot.geometry]).map(JSON.stringify).sort());
  }

  function renderIssueList(container, issues, warnings) {
    container.replaceChildren();
    const issueMessages = new Set((issues || []).map((issue) => issue.message));
    const messages = [...new Set([
      ...(issues || []).map((issue) => `${issue.code}: ${issue.message}`),
      ...(warnings || []).filter((message) => !issueMessages.has(message)),
    ])];
    for (const message of messages) {
      const item = document.createElement("li");
      item.textContent = message;
      container.append(item);
    }
  }

  function proposalWorkRows(layout, proposal, context) {
    if (!context || !proposal) return [];
    return context.workIds.map((id) => {
      const work = layout.works.find((item) => item.id === id);
      const count = proposal.work_counts?.find((item) => item.work_id === id);
      const placed = proposal.slots.filter((slot) => slot.work_id === id).length;
      const existing = layout.slots.filter((slot) => slot.work_id === id && slot.face === context.face).length;
      const retained = context.mode === "add" ? existing : 0;
      const requested = count?.requested ?? work?.requested_forms ?? 0;
      const source = context.sourceOverrides?.[id]
        || work?.[context.face === "front" ? "front_source" : "back_source"];
      const asset = layout.assets.find((item) => item.id === source?.asset_id);
      return { id, name: work?.name || id, page: source?.page,
        sourceLabel: source ? `${asset?.original_filename || source.asset_id} · página ${source.page}` : "Sin fuente",
        requested, placed, unplaced: Math.max(0, requested - placed), overproduced: Math.max(0, placed - requested),
        retained, removed: existing - retained, projected: retained + placed };
    });
  }

  class Panel {
    constructor(store, refs, api, saver, context, commands, editPolicy, runAction) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.runAction = runAction;
      this.proposalContext = null;
      this.applied = false;
      this.requestSequence = 0;
      this.sourceChoices = new Map();
      this.bind();
      this.renderWorks();
      this.renderState();
      this.renderHistory();
    }

    bind() {
      this.refs.repeatCalculate.addEventListener("click", () => this.runAction("repeat.calculate"));
      this.refs.repeatApply.addEventListener("click", () => this.runAction("repeat.apply"));
      this.refs.repeatDiscard?.addEventListener("click", () => this.runAction("repeat.discard"));
      this.refs.repeatAlternative?.addEventListener("click", () => this.runAction("repeat.alternative"));
      this.refs.repeatDistribution?.addEventListener("change", () => this.invalidateProposal());
      for (const control of [
        this.refs.repeatGapX,
        this.refs.repeatGapY,
        this.refs.repeatPartial,
        this.refs.repeatFill,
        ...this.refs.repeatModes,
      ]) {
        control.addEventListener("change", () => this.invalidateProposal());
      }
      for (const control of [this.refs.repeatGapX, this.refs.repeatGapY]) {
        control.addEventListener("input", () => this.invalidateProposal());
      }
      this.refs.repeatWorks.addEventListener("change", (event) => {
        if (event.target?.dataset?.repeatSource) {
          this.sourceChoices.set(event.target.dataset.repeatSource, event.target.value);
        }
        this.invalidateProposal();
        this.renderState();
      });
      this.unsubscribe = this.store.subscribe((event) => {
        if (["command", "undo", "redo", "external_update", "active_face"].includes(event.type)) {
          this.invalidateProposal();
          this.renderWorks();
          this.renderHistory();
        }
        if (["save_conflict", "save_error"].includes(event.type)
            || (event.type === "save_success" && this.proposalContext
              && this.proposalContext.revision !== this.store.revision)) this.invalidateProposal();
        if (event.type === "repeat_state") this.renderState();
      });
    }

    renderWorks() {
      const checked = new Set(selectedWorkIds(this.refs.repeatWorks));
      this.refs.repeatWorks.replaceChildren();
      if (!this.store.layout.works.length) {
        const empty = document.createElement("p");
        empty.className = "ev2-list-empty";
        empty.textContent = "Crea un work real antes de calcular Repeat.";
        this.refs.repeatWorks.append(empty);
        this.refs.repeatCalculate.disabled = true;
        return;
      }
      for (const work of this.store.layout.works) {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = work.id;
        input.checked = checked.size ? checked.has(work.id) : work.front_source !== null;
        const text = document.createElement("span");
        text.textContent = `${work.name} · ${work.requested_forms} por Repeat · ${work.allowed_rotations_deg.join("° / ")}°`;
        label.append(input, text);
        this.refs.repeatWorks.append(label);
        if (this.store.activeFace === "back") {
          const sourceLabel = document.createElement("label");
          sourceLabel.className = "ev2-repeat-source-label";
          sourceLabel.textContent = `Fuente Dorso · ${work.name}`;
          const select = document.createElement("select");
          select.dataset.repeatSource = work.id;
          select.setAttribute("aria-label", `Fuente Dorso para ${work.name}`);
          const defaultOption = document.createElement("option");
          defaultOption.value = "";
          defaultOption.textContent = work.back_source
            ? `Fuente del work · página ${work.back_source.page}`
            : "Elegí PDF y página";
          select.append(defaultOption);
          for (const asset of this.store.layout.assets.filter((item) => item.status === "ready")) {
            for (const page of asset.pages) {
              const box = Preparation.detectedBox(page, work.bleed_mm);
              if (!box) continue;
              const option = document.createElement("option");
              option.value = JSON.stringify({ asset_id: asset.id, page: page.number, pdf_box: box });
              option.textContent = `${asset.original_filename} · página ${page.number}`;
              select.append(option);
            }
          }
          const choice = this.sourceChoices?.get(work.id) || "";
          select.value = [...select.options].some((option) => option.value === choice) ? choice : "";
          sourceLabel.append(select);
          this.refs.repeatWorks.append(sourceLabel);
        }
      }
      this.renderState();
    }

    sourceOverrides(workIds, face) {
      const overrides = {};
      if (face !== "back") return overrides;
      for (const id of workIds) {
        const work = this.store.layout.works.find((item) => item.id === id);
        if (!work) throw new Error(`El work ${id} ya no existe.`);
        const choice = this.sourceChoices?.get(id);
        const source = choice ? JSON.parse(choice) : work.back_source;
        if (!source) throw new Error(`Elegí PDF, página y caja para el Dorso de ${work.name}.`);
        const asset = this.store.layout.assets.find((item) => item.id === source.asset_id && item.status === "ready");
        const page = asset?.pages.find((item) => item.number === source.page);
        if (!page?.boxes_mm?.[source.pdf_box]) throw new Error(`La fuente Dorso de ${work.name} ya no está disponible.`);
        if (choice) overrides[id] = source;
      }
      return overrides;
    }

    invalidateProposal() {
      this.requestSequence += 1;
      this.proposalContext = null;
      this.applied = false;
      this.store.setRepeatState("idle", null, null);
      this.renderHistory();
    }

    selectedMode() {
      return [...this.refs.repeatModes].find((input) => input.checked)?.value || "add";
    }

    async alternative() {
      if (!this.refs.repeatDistribution || this.store.repeatPanel.status === "calculating") return;
      const previous = this.store.repeatPanel.proposal;
      const choices = ["auto", "rows", "columns", "rotated"];
      this.refs.repeatDistribution.value = choices[(choices.indexOf(this.refs.repeatDistribution.value) + 1) % choices.length];
      return this.calculate(previous);
    }

    async calculate(previous = null) {
      this.invalidateProposal();
      const workIds = selectedWorkIds(this.refs.repeatWorks);
      const settings = readSettings(this.refs);
      if (!workIds.length) {
        this.store.setRepeatState("error", null, "Selecciona al menos un work.");
        return;
      }
      const face = this.store.activeFace;
      let sourceOverrides;
      try {
        sourceOverrides = this.sourceOverrides(workIds, face);
      } catch (error) {
        this.store.setRepeatState("error", null, error.message);
        return;
      }
      if (![settings.horizontal_gap_mm, settings.vertical_gap_mm].every(
        (value) => Number.isFinite(value) && value >= 0,
      )) {
        this.store.setRepeatState("error", null, "Los gaps deben ser números no negativos.");
        return;
      }
      this.store.setRepeatState("calculating", null, null);
      const sequence = ++this.requestSequence;
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de calcular Repeat.");
        }
        if (sequence !== this.requestSequence || face !== this.store.activeFace) return;
        const changeVersion = this.store.changeVersion;
        const request = {
          base_revision: this.store.revision,
          work_ids: workIds,
          face,
          settings,
          source_overrides: sourceOverrides,
          apply_mode: this.selectedMode(),
          distribution: this.refs.repeatDistribution?.value || "auto",
        };
        const jobId = this.store.layout.job.id;
        const response = await this.api.proposeRepeat(this.context.repeat_api_url, request);
        if (sequence !== this.requestSequence || request.face !== this.store.activeFace) return;
        if (JSON.stringify(sourceOverrides) !== JSON.stringify(this.sourceOverrides(workIds, face))) {
          this.invalidateProposal();
          return;
        }
        if (jobId !== this.store.layout.job.id || changeVersion !== this.store.changeVersion
            || request.base_revision !== this.store.revision || this.store.saveState.status !== "clean") {
          this.invalidateProposal();
          return;
        }
        this.proposalContext = {
          jobId,
          revision: request.base_revision,
          changeVersion,
          workIds: [...workIds],
          face: request.face,
          settings: { ...settings },
          sourceOverrides: structuredClone(sourceOverrides),
          mode: request.apply_mode,
          distribution: request.distribution,
        };
        this.applied = false;
        if (!response.result.success) {
          this.store.setRepeatState("error", response.result, "La propuesta Repeat no es aplicable.");
          return;
        }
        if (previous?.success && proposalSignature(previous) === proposalSignature(response.result)) {
          response.result.warnings = [...(response.result.warnings || []),
            "Esta distribución produce el mismo montaje que la anterior con las condiciones actuales."];
        }
        this.store.setRepeatState("ready", response.result, null, this.proposalContext);
      } catch (error) {
        if (sequence !== this.requestSequence) return;
        if (error && error.status === 409) this.store.failSave(error, true);
        this.store.setRepeatState("error", null, error.message || "No se pudo calcular Repeat.");
      }
    }

    apply() {
      const result = this.store.repeatPanel.proposal;
      if (!result || !result.success || !this.proposalContext || this.applied) return;
      if (this.store.pointerSession) return;
      let currentSources;
      try {
        currentSources = this.sourceOverrides(this.proposalContext.workIds, this.store.activeFace);
      } catch (error) {
        this.invalidateProposal();
        this.store.setRepeatState("error", null, error.message);
        return;
      }
      if (this.proposalContext.jobId !== this.store.layout.job.id
          || this.proposalContext.revision !== this.store.revision
          || this.proposalContext.changeVersion !== this.store.changeVersion
          || this.store.saveState.status !== "clean"
          || this.proposalContext.face !== this.store.activeFace
          || this.proposalContext.mode !== this.selectedMode()
          || this.proposalContext.distribution !== (this.refs.repeatDistribution?.value || "auto")
          || JSON.stringify(this.proposalContext.settings) !== JSON.stringify(readSettings(this.refs))
          || JSON.stringify(this.proposalContext.sourceOverrides) !== JSON.stringify(currentSources)
          || JSON.stringify(this.proposalContext.workIds) !== JSON.stringify(selectedWorkIds(this.refs.repeatWorks))) {
        this.invalidateProposal();
        this.store.setRepeatState("error", null, "El montaje cambió. Vuelve a calcular Repeat.");
        return;
      }
      try {
        const command = new this.commands.ApplyRepeatCommand(
          this.store.layout,
          result,
          this.proposalContext,
        );
        command.selectionBefore = [...this.store.selection];
        command.selectionAfter = result.slots.map((slot) => slot.id);
        this.store.executeCommand(command);
        this.store.setSelection(result.slots.map((slot) => slot.id), "replace");
        this.applied = true;
        this.store.setRepeatState("applied", result, null);
      } catch (error) {
        this.store.setRepeatState("error", result, error.message);
      }
    }

    renderState() {
      if (this.refs.repeatHeading) this.refs.repeatHeading.textContent = `Repeat — ${this.store.activeFace === "back" ? "Dorso" : "Frente"}`;
      const state = this.store.repeatPanel;
      const proposal = state.proposal;
      if (this.refs.repeatAlternative) this.refs.repeatAlternative.disabled = !["ready", "error"].includes(state.status);
      let sourceError = null;
      try { this.sourceOverrides(selectedWorkIds(this.refs.repeatWorks), this.store.activeFace); }
      catch (error) { sourceError = error.message; }
      this.refs.repeatCalculate.disabled = state.status === "calculating" || !this.store.layout.works.length || Boolean(sourceError);
      this.refs.repeatStatus.textContent = state.error
        || (state.status === "idle" ? sourceError : null)
        || ({ idle: "Configura y calcula una propuesta.", calculating: "Calculando…", ready: "Propuesta lista para aplicar.", applied: "Propuesta aplicada al layout." }[state.status] || "");
      this.refs.repeatStatus.dataset.state = state.status;
      const replaceIds = this.proposalContext?.mode === "replace_work_face"
        ? this.store.layout.slots
          .filter((slot) => slot.face === this.proposalContext.face
            && this.proposalContext.workIds.includes(slot.work_id))
          .map((slot) => slot.id)
        : [];
      const blocked = this.editPolicy.blockedSlotIds(
        this.store.layout,
        replaceIds,
        "replace_by_repeat",
      );
      this.refs.repeatApply.disabled = state.status !== "ready"
        || !proposal?.success
        || blocked.length > 0;
      if (blocked.length && state.status === "ready") {
        this.refs.repeatStatus.textContent = `Repeat no puede reemplazar slots bloqueados: ${blocked.join(", ")}.`;
        this.refs.repeatStatus.dataset.state = "error";
      }
      this.refs.repeatSummary.hidden = !proposal;
      this.renderWorkDetails(state);
      if (!proposal) {
        renderIssueList(this.refs.repeatIssues, [], []);
        return;
      }
      this.refs.repeatRequested.textContent = String(proposal.requested);
      this.refs.repeatPlaced.textContent = String(proposal.placed);
      this.refs.repeatUnplaced.textContent = String(proposal.unplaced);
      this.refs.repeatOverproduced.textContent = String(proposal.overproduced);
      const proposalPct = proposal.metrics.proposal_utilization_pct
        ?? proposal.metrics.utilization_percent;
      const projectedPct = proposal.metrics.projected_total_utilization_pct
        ?? proposalPct;
      this.refs.repeatProposalUtilization.textContent = `${proposalPct.toFixed(2)}%`;
      this.refs.repeatProjectedUtilization.textContent = `${projectedPct.toFixed(2)}%`;
      renderIssueList(this.refs.repeatIssues, proposal.issues, proposal.warnings);
    }

    renderWorkDetails(state) {
      const container = this.refs.repeatWorkDetails;
      if (!container) return;
      container.replaceChildren();
      const reviewing = state.status === "ready" && this.proposalContext;
      this.refs.repeatDiscard.disabled = !["ready", "calculating", "error"].includes(state.status);
      this.refs.repeatReviewNote.hidden = !reviewing;
      if (!reviewing) return;
      const rows = proposalWorkRows(this.store.layout, state.proposal, this.proposalContext);
      const removed = rows.reduce((sum, row) => sum + row.removed, 0);
      const total = this.store.layout.slots.filter((slot) => slot.face === this.proposalContext.face).length;
      this.refs.repeatReviewNote.textContent = this.proposalContext.mode === "add"
        ? `Añadir: se conservan ${total} piezas y se añaden ${state.proposal.placed}. Total en la cara: ${total + state.proposal.placed}.`
        : `Reemplazar: se retiran ${removed} piezas de los works elegidos en ${this.proposalContext.face === "back" ? "Dorso" : "Frente"}, incluidos slots manuales; se conservan ${total - removed} y se colocan ${state.proposal.placed}. Total en la cara: ${total - removed + state.proposal.placed}. IDs retirados: ${this.store.layout.slots.filter((slot) => slot.face === this.proposalContext.face && this.proposalContext.workIds.includes(slot.work_id)).map((slot) => slot.id).join(", ") || "ninguno"}.`;
      for (const row of rows) {
        const card = document.createElement("article");
        card.className = "ev2-repeat-work-detail";
        card.dataset.workId = row.id;
        const title = document.createElement("strong");
        title.textContent = `${row.name} · ${row.sourceLabel}`;
        const values = document.createElement("dl");
        for (const [label, value] of [["Solicitadas", row.requested], ["Propuestas", row.placed],
          ["Faltantes", row.unplaced], ["Extras", row.overproduced], ["Conservadas", row.retained], ["Total al aplicar", row.projected]]) {
          const cell = document.createElement("div");
          const term = document.createElement("dt"); term.textContent = label;
          const number = document.createElement("dd"); number.textContent = String(value);
          cell.append(term, number); values.append(cell);
        }
        card.append(title, values); container.append(card);
      }
    }

    renderHistory() {
      const historical = this.store.layout.imposition.last_result;
      this.refs.repeatHistory.textContent = historical
        ? `Resultado al aplicar la última imposición · ${historical.operation_id} · solicitadas ${historical.requested}, colocadas ${historical.placed}, no colocadas ${historical.unplaced}.`
        : "Resultado al aplicar la última imposición · todavía no existe.";
      const current = LayoutMetrics.currentSlotMetrics(
        this.store.layout,
        this.store.activeFace,
      );
      this.refs.repeatCurrentFace.textContent = String(current.total);
      this.refs.repeatCurrentWorks.textContent = LayoutMetrics.workCountsLabel(
        this.store.layout,
        current.byWork,
      );
      this.refs.repeatCurrentOperation.textContent = current.operationId
        ? String(current.lastOperationPresent)
        : "—";
    }
  }

  return Object.freeze({ Panel, readSettings, selectedWorkIds, proposalWorkRows });
});
