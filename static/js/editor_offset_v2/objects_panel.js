(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ObjectsPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const LOCK_LABELS = Object.freeze({
    geometry: "Geometría",
    content: "Contenido",
    delete: "Eliminación",
  });

  class Panel {
    constructor(store, refs, registry, contextProvider, actionIds, operations, runAction) {
      this.store = store;
      this.refs = refs;
      this.registry = registry;
      this.contextProvider = contextProvider;
      this.actionIds = actionIds;
      this.operations = operations;
      this.runAction = runAction;
      this.bind();
      this.unsubscribe = store.subscribe(() => this.render());
      this.render();
    }

    bind() {
      this.refs.objectRotatePositive.addEventListener("click", () => (
        this.runAction(this.actionIds.ROTATE_CLOCKWISE)
      ));
      this.refs.objectRotateNegative.addEventListener("click", () => (
        this.runAction(this.actionIds.ROTATE_COUNTERCLOCKWISE)
      ));
      this.refs.objectRotation.addEventListener("change", () => {
        if (this.refs.objectRotation.value !== "") {
          this.runAction(this.actionIds.ROTATE_SET, {
            rotation: Number(this.refs.objectRotation.value),
          });
        }
      });
      for (const [refName, actionId] of [
        ["objectDuplicate", this.actionIds.DUPLICATE],
        ["objectCopy", this.actionIds.COPY],
        ["objectCut", this.actionIds.CUT],
        ["objectPaste", this.actionIds.PASTE],
        ["objectDelete", this.actionIds.DELETE],
        ["objectSelectAll", this.actionIds.SELECT_ALL_FACE],
        ["objectSelectWork", this.actionIds.SELECT_SAME_WORK],
        ["objectSelectAsset", this.actionIds.SELECT_SAME_ASSET],
      ]) {
        this.refs[refName].addEventListener("click", () => this.runAction(actionId));
      }
      for (const button of this.refs.objectLockButtons) {
        button.addEventListener("click", () => this.runAction(
          this.actionIds.USER_LOCKS_SET,
          {
            surface: button.dataset.lockSurface,
            locked: button.dataset.lockAction === "lock",
          },
        ));
      }
    }

    enabled(actionId) {
      return this.registry.isEnabled(actionId, this.contextProvider());
    }

    render() {
      const slots = this.operations.selectedSlots(this.store);
      const rotation = this.operations.selectionRotation(slots);
      this.refs.objectSelection.textContent = slots.length
        ? `${slots.length} slot${slots.length === 1 ? "" : "s"} seleccionado${slots.length === 1 ? "" : "s"}`
        : "Sin selección";
      this.refs.objectRotation.value = rotation.state === "mixed"
        ? ""
        : rotation.value === null ? "" : String(rotation.value);
      this.refs.objectRotation.setAttribute(
        "aria-label",
        rotation.state === "mixed"
          ? "Rotación cardinal mixta"
          : `Rotación cardinal ${rotation.value ?? "sin selección"}`,
      );

      this.refs.objectRotatePositive.disabled = !this.enabled(this.actionIds.ROTATE_CLOCKWISE);
      this.refs.objectRotateNegative.disabled = !this.enabled(this.actionIds.ROTATE_COUNTERCLOCKWISE);
      this.refs.objectRotation.disabled = !this.enabled(this.actionIds.ROTATE_SET);
      for (const [refName, actionId] of [
        ["objectDuplicate", this.actionIds.DUPLICATE],
        ["objectCopy", this.actionIds.COPY],
        ["objectCut", this.actionIds.CUT],
        ["objectPaste", this.actionIds.PASTE],
        ["objectDelete", this.actionIds.DELETE],
        ["objectSelectAll", this.actionIds.SELECT_ALL_FACE],
        ["objectSelectWork", this.actionIds.SELECT_SAME_WORK],
        ["objectSelectAsset", this.actionIds.SELECT_SAME_ASSET],
      ]) {
        this.refs[refName].disabled = !this.enabled(actionId);
      }

      const clipboard = this.store.clipboard;
      const validation = this.operations.validateClipboard(
        this.store.layout,
        clipboard,
        this.store.activeFace,
      );
      this.refs.objectClipboard.textContent = !clipboard
        ? "Clipboard interno vacío."
        : validation.ok
          ? clipboard.pasteCount > 0
            ? `${clipboard.slots.length} slot(s) · ${clipboard.pasteCount} pegado(s) en este job.`
            : `${clipboard.slots.length} slot(s) · listo para pegar.`
          : validation.reason;
      this.refs.objectClipboard.dataset.state = validation.ok ? "ready" : "warning";

      for (const surface of this.operations.USER_LOCK_SURFACES) {
        const state = this.operations.userLockState(slots, surface);
        const status = this.refs.objectLockStatuses.find(
          (element) => element.dataset.lockStatus === surface,
        );
        const remaining = this.operations.remainingLockSources(slots, surface);
        const stateLabel = { none: "ninguno", all: "todos", mixed: "mixto" }[state];
        status.textContent = `${LOCK_LABELS[surface]}: ${stateLabel}${
          remaining.length ? ` · otras fuentes: ${remaining.join(", ")}` : ""
        }`;
        status.dataset.state = state;
        status.setAttribute("aria-label", `${LOCK_LABELS[surface]}, estado ${stateLabel}`);
        const lock = this.refs.objectLockButtons.find(
          (button) => button.dataset.lockSurface === surface
            && button.dataset.lockAction === "lock",
        );
        const unlock = this.refs.objectLockButtons.find(
          (button) => button.dataset.lockSurface === surface
            && button.dataset.lockAction === "unlock",
        );
        const actionEnabled = this.enabled(this.actionIds.USER_LOCKS_SET);
        lock.disabled = !actionEnabled || state === "all";
        unlock.disabled = !actionEnabled || state === "none";
      }
    }

    dispose() {
      this.unsubscribe();
    }
  }

  return Object.freeze({ LOCK_LABELS, Panel });
});
