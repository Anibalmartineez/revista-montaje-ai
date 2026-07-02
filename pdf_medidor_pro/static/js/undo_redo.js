(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.PdfMedidorPro = root.PdfMedidorPro || {};
    root.PdfMedidorPro.undoRedo = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DEFAULT_LIMIT = 50;

  function createHistory(limit) {
    const max = Math.max(1, Number(limit || DEFAULT_LIMIT));
    const undoStack = [];
    const redoStack = [];

    function capture(state) {
      const next = snapshot(state);
      const last = undoStack[undoStack.length - 1];
      if (last && sameSnapshot(last, next)) return;
      undoStack.push(next);
      while (undoStack.length > max) undoStack.shift();
      redoStack.length = 0;
    }

    function undo(current) {
      if (!undoStack.length) return snapshot(current);
      redoStack.push(snapshot(current));
      return undoStack.pop();
    }

    function redo(current) {
      if (!redoStack.length) return snapshot(current);
      undoStack.push(snapshot(current));
      while (undoStack.length > max) undoStack.shift();
      return redoStack.pop();
    }

    function reset() {
      undoStack.length = 0;
      redoStack.length = 0;
    }

    return {
      capture,
      undo,
      redo,
      reset,
      canUndo: () => undoStack.length > 0,
      canRedo: () => redoStack.length > 0,
      sizes: () => ({ undo: undoStack.length, redo: redoStack.length }),
    };
  }

  function snapshot(state) {
    return {
      measurements: clone(state && state.measurements ? state.measurements : []),
      guides: clone(state && state.guides ? state.guides : []),
      selectedMeasurementId: state && state.selectedMeasurementId ? state.selectedMeasurementId : null,
      selectedGuideId: state && state.selectedGuideId ? state.selectedGuideId : null,
      finalMeasurementId: state && state.finalMeasurementId ? state.finalMeasurementId : null,
      finalOrigin: state && state.finalOrigin ? state.finalOrigin : "auto",
      finalConfidence: state && state.finalConfidence ? state.finalConfidence : "media",
    };
  }

  function sameSnapshot(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  return {
    createHistory,
    snapshot,
  };
});
