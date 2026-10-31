(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ObjectsPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

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
        ["objectPaste", this.actionIds.PASTE],
        ["objectDelete", this.actionIds.DELETE],
      ]) {
        this.refs[refName].addEventListener("click", () => this.runAction(actionId));
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
        ["objectPaste", this.actionIds.PASTE],
        ["objectDelete", this.actionIds.DELETE],
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

    }

    dispose() {
      this.unsubscribe();
    }
  }

  return Object.freeze({ Panel });
});
