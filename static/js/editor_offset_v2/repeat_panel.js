(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.RepeatPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function selectedWorkIds(container) {
    return [...container.querySelectorAll('input[type="checkbox"]:checked')]
      .map((input) => input.value);
  }

  function readSettings(refs) {
    return {
      horizontal_gap_mm: Number(refs.repeatGapX.value),
      vertical_gap_mm: Number(refs.repeatGapY.value),
      exact_quantity: refs.repeatExact.checked,
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
    constructor(store, refs, api, saver, context, commands) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.commands = commands;
      this.proposalContext = null;
      this.applied = false;
      for (const option of this.refs.repeatFace.options) {
        option.disabled = !this.store.layout.faces.enabled.includes(option.value);
      }
      if (!this.store.layout.faces.enabled.includes(this.refs.repeatFace.value)) {
        this.refs.repeatFace.value = this.store.layout.faces.enabled[0];
      }
      this.bind();
      this.renderWorks();
      this.renderState();
    }

    bind() {
      this.refs.repeatCalculate.addEventListener("click", () => this.calculate());
      this.refs.repeatApply.addEventListener("click", () => this.apply());
      for (const control of [
        this.refs.repeatFace,
        this.refs.repeatGapX,
        this.refs.repeatGapY,
        this.refs.repeatExact,
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
      this.refs.repeatApply.disabled = state.status !== "ready" || !proposal?.success;
      this.refs.repeatSummary.hidden = !proposal;
      if (!proposal) {
        renderIssueList(this.refs.repeatIssues, [], []);
        return;
      }
      this.refs.repeatRequested.textContent = String(proposal.requested);
      this.refs.repeatPlaced.textContent = String(proposal.placed);
      this.refs.repeatUnplaced.textContent = String(proposal.unplaced);
      this.refs.repeatOverproduced.textContent = String(proposal.overproduced);
      this.refs.repeatUtilization.textContent = `${proposal.metrics.utilization_percent.toFixed(2)}%`;
      renderIssueList(this.refs.repeatIssues, proposal.issues, proposal.warnings);
    }
  }

  return Object.freeze({ Panel, readSettings, selectedWorkIds });
});
