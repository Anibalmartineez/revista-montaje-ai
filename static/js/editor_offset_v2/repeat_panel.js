(function (root, factory) {
  "use strict";
  const layoutMetrics = typeof module === "object" && module.exports
    ? require("./layout_metrics.js")
    : root.EditorOffsetV2?.LayoutMetrics;
  const api = factory(layoutMetrics);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.RepeatPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (LayoutMetrics) {
  "use strict";

  if (!LayoutMetrics) throw new Error("Editor V2 layout metrics are required");

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

  function renderIssueList(container, issues, warnings) {
    container.replaceChildren();
    const messages = [...new Set([
      ...(issues || []).map((issue) => `${issue.code}: ${issue.message}`),
      ...(warnings || []),
    ])];
    for (const message of messages) {
      const item = document.createElement("li");
      item.textContent = message;
      container.append(item);
    }
  }

  class Panel {
    constructor(store, refs, api, saver, context, commands, editPolicy) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.proposalContext = null;
      this.applied = false;
      for (const option of this.refs.repeatFace.options) {
        option.disabled = option.value === "back"
          || !this.store.layout.faces.enabled.includes(option.value);
      }
      this.refs.repeatFace.value = "front";
      this.bind();
      this.renderWorks();
      this.renderState();
      this.renderHistory();
    }

    bind() {
      this.refs.repeatCalculate.addEventListener("click", () => this.calculate());
      this.refs.repeatApply.addEventListener("click", () => this.apply());
      for (const control of [
        this.refs.repeatFace,
        this.refs.repeatGapX,
        this.refs.repeatGapY,
        this.refs.repeatPartial,
        this.refs.repeatFill,
        ...this.refs.repeatModes,
      ]) {
        control.addEventListener("change", () => this.invalidateProposal());
      }
      this.refs.repeatWorks.addEventListener("change", () => this.invalidateProposal());
      this.unsubscribe = this.store.subscribe((event) => {
        if (["command", "undo", "redo", "external_update"].includes(event.type)) {
          this.renderWorks();
          this.renderHistory();
        }
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
        text.textContent = `${work.name} · ${work.requested_forms} formas · ${work.allowed_rotations_deg.join("° / ")}°`;
        label.append(input, text);
        this.refs.repeatWorks.append(label);
      }
      this.refs.repeatCalculate.disabled = false;
    }

    invalidateProposal() {
      this.proposalContext = null;
      this.applied = false;
      this.store.setRepeatState("idle", null, null);
      this.renderHistory();
    }

    selectedMode() {
      return [...this.refs.repeatModes].find((input) => input.checked)?.value || "add";
    }

    async calculate() {
      const workIds = selectedWorkIds(this.refs.repeatWorks);
      const settings = readSettings(this.refs);
      if (!workIds.length) {
        this.store.setRepeatState("error", null, "Selecciona al menos un work.");
        return;
      }
      if (this.refs.repeatFace.value !== "front") {
        this.store.setRepeatState("error", null, "La interfaz Repeat solo permite frente por ahora.");
        return;
      }
      if (![settings.horizontal_gap_mm, settings.vertical_gap_mm].every(
        (value) => Number.isFinite(value) && value >= 0,
      )) {
        this.store.setRepeatState("error", null, "Los gaps deben ser números no negativos.");
        return;
      }
      this.store.setRepeatState("calculating", null, null);
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de calcular Repeat.");
        }
        const request = {
          base_revision: this.store.revision,
          work_ids: workIds,
          face: this.refs.repeatFace.value,
          settings,
          apply_mode: this.selectedMode(),
        };
        const response = await this.api.proposeRepeat(this.context.repeat_api_url, request);
        this.proposalContext = {
          workIds: [...workIds],
          face: request.face,
          settings: { ...settings },
          mode: request.apply_mode,
        };
        this.applied = false;
        if (!response.result.success) {
          this.store.setRepeatState("error", response.result, "La propuesta Repeat no es aplicable.");
          return;
        }
        this.store.setRepeatState("ready", response.result, null);
      } catch (error) {
        if (error && error.status === 409) this.store.failSave(error, true);
        this.store.setRepeatState("error", null, error.message || "No se pudo calcular Repeat.");
      }
    }

    apply() {
      const result = this.store.repeatPanel.proposal;
      if (!result || !result.success || !this.proposalContext || this.applied) return;
      try {
        const command = new this.commands.ApplyRepeatCommand(
          this.store.layout,
          result,
          this.proposalContext,
        );
        this.store.executeCommand(command);
        this.store.setSelection(result.slots.map((slot) => slot.id), "replace");
        this.applied = true;
        this.store.setRepeatState("applied", result, null);
      } catch (error) {
        this.store.setRepeatState("error", result, error.message);
      }
    }

    renderState() {
      const state = this.store.repeatPanel;
      const proposal = state.proposal;
      this.refs.repeatStatus.textContent = state.error
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

    renderHistory() {
      const historical = this.store.layout.imposition.last_result;
      this.refs.repeatHistory.textContent = historical
        ? `Resultado al aplicar la última imposición · ${historical.operation_id} · solicitadas ${historical.requested}, colocadas ${historical.placed}, no colocadas ${historical.unplaced}.`
        : "Resultado al aplicar la última imposición · todavía no existe.";
      const current = LayoutMetrics.currentSlotMetrics(
        this.store.layout,
        this.refs.repeatFace.value,
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

  return Object.freeze({ Panel, readSettings, selectedWorkIds });
});
