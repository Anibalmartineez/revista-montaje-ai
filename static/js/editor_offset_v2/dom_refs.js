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
      createSlot: byId("ev2-create-slot", false),
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
      assetUploadForm: byId("ev2-asset-upload-form"),
      assetFile: byId("ev2-asset-file"),
      assetUploadButton: byId("ev2-asset-upload-button"),
      assetUploadStatus: byId("ev2-asset-upload-status"),
      assetsList: byId("ev2-assets-list"),
      assetSelect: byId("ev2-asset-select"),
      assetPage: byId("ev2-asset-page"),
      assetBox: byId("ev2-asset-box"),
      boxDimensions: byId("ev2-box-dimensions"),
      workName: byId("ev2-work-name"),
      workWidth: byId("ev2-work-width"),
      workHeight: byId("ev2-work-height"),
      workBleed: byId("ev2-work-bleed"),
      workQuantity: byId("ev2-work-quantity"),
      workRotations: document.querySelectorAll('[name="ev2-work-rotation"]'),
      workBack: byId("ev2-work-back"),
      createWork: byId("ev2-create-work"),
      workSelect: byId("ev2-work-select"),
      createRealSlot: byId("ev2-create-real-slot"),
      replaceSource: byId("ev2-replace-source"),
      repeatWorks: byId("ev2-repeat-works"),
      repeatFace: byId("ev2-repeat-face"),
      repeatGapX: byId("ev2-repeat-gap-x"),
      repeatGapY: byId("ev2-repeat-gap-y"),
      repeatPartial: byId("ev2-repeat-partial"),
      repeatFill: byId("ev2-repeat-fill"),
      repeatModes: document.querySelectorAll('[name="ev2-repeat-mode"]'),
      repeatCalculate: byId("ev2-repeat-calculate"),
      repeatApply: byId("ev2-repeat-apply"),
      repeatStatus: byId("ev2-repeat-status"),
      repeatSummary: byId("ev2-repeat-summary"),
      repeatRequested: byId("ev2-repeat-requested"),
      repeatPlaced: byId("ev2-repeat-placed"),
      repeatUnplaced: byId("ev2-repeat-unplaced"),
      repeatOverproduced: byId("ev2-repeat-overproduced"),
      repeatProposalUtilization: byId("ev2-repeat-proposal-utilization"),
      repeatProjectedUtilization: byId("ev2-repeat-projected-utilization"),
      repeatIssues: byId("ev2-repeat-issues"),
      repeatHistory: byId("ev2-repeat-history"),
      repeatCurrentFace: byId("ev2-repeat-current-face"),
      repeatCurrentWorks: byId("ev2-repeat-current-works"),
      repeatCurrentOperation: byId("ev2-repeat-current-operation"),
      outputCheck: byId("ev2-output-check"),
      outputStatus: byId("ev2-output-status"),
      outputIssues: byId("ev2-output-issues"),
    };
  }

  return Object.freeze({ byId, collect });
});
