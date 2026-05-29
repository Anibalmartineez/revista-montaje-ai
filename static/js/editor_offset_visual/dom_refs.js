(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  const ids = {
    sheet: 'sheet',
    sheetCanvas: 'sheet-canvas',
    worksList: 'works-list',
    designsList: 'designs-list',
    previewImage: 'preview-image',
    pdfOutput: 'pdf-output',
    slotForm: 'slot-form',
    slotNone: 'slot-none',
    uploadForm: 'upload-form',
    geometryValidationSummary: 'geometry-validation-summary',
    geometryValidationList: 'geometry-validation-list',
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function all(selector) {
    return Array.from(document.querySelectorAll(selector));
  }

  window.EditorOffsetVisual.domRefs = {
    ids,
    byId,
    all,
  };
})();
