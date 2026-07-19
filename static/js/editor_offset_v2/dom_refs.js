(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.DomRefs = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function byId(id, required) {
    const element = document.getElementById(id);
    if (!element && required !== false) {
      throw new Error(`Missing Editor V2 DOM element: #${id}`);
    }
    return element;
  }

  function collect() {
    return {
      context: byId("editor-offset-v2-context"),
      newJob: byId("ev2-new-job"),
      save: byId("ev2-save"),
      undo: byId("ev2-undo"),
      redo: byId("ev2-redo"),
      createSlot: byId("ev2-create-slot"),
      deleteSlots: byId("ev2-delete-slots"),
      selectTool: byId("ev2-select-tool"),
      reloadConflict: byId("ev2-reload-conflict"),
      zoomIn: byId("ev2-zoom-in"),
      zoomOut: byId("ev2-zoom-out"),
      resetView: byId("ev2-reset-view"),
      jobId: byId("ev2-job-id"),
      jobName: byId("ev2-job-name"),
      revision: byId("ev2-revision"),
      saveStatus: byId("ev2-save-status"),
      statusMessage: byId("ev2-status-message"),
      slotsList: byId("ev2-slots-list"),
      canvas: byId("ev2-canvas"),
      inspector: byId("ev2-inspector-values"),
      activeFace: byId("ev2-active-face"),
      cursor: byId("ev2-cursor"),
      zoom: byId("ev2-zoom"),
      slotCount: byId("ev2-slot-count"),
    };
  }

  return Object.freeze({ byId, collect });
});
