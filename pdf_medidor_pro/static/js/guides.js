(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.PdfMedidorPro = root.PdfMedidorPro || {};
    root.PdfMedidorPro.guides = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function createGuide(orientation, valueMm) {
    const normalizedOrientation = orientation === "horizontal" ? "horizontal" : "vertical";
    const position = round(valueMm);
    return {
      id: `g_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
      type: "guide",
      orientation: normalizedOrientation,
      position_mm: position,
      value_mm: position,
      visible: true,
      locked: false,
    };
  }

  function normalizeGuide(guide) {
    const position = guidePosition(guide);
    return Object.assign({}, guide || {}, {
      id: guide && guide.id ? guide.id : `g_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
      type: "guide",
      orientation: guide && guide.orientation === "horizontal" ? "horizontal" : "vertical",
      position_mm: position,
      value_mm: position,
      visible: !(guide && guide.visible === false),
      locked: Boolean(guide && guide.locked),
    });
  }

  function normalizeGuides(guides) {
    return (guides || []).map(normalizeGuide);
  }

  function guidePosition(guide) {
    if (!guide) return 0;
    if (guide.position_mm !== undefined && guide.position_mm !== null) return round(guide.position_mm);
    return round(guide.value_mm);
  }

  function moveGuide(guide, positionMm) {
    const next = normalizeGuide(guide);
    if (next.locked) return next;
    const position = round(positionMm);
    next.position_mm = position;
    next.value_mm = position;
    return next;
  }

  function replaceGuide(guides, guide) {
    const next = normalizeGuide(guide);
    return (guides || []).map((item) => (item.id === next.id ? next : normalizeGuide(item)));
  }

  function toggleGuideVisibility(guides, id) {
    return (guides || []).map((guide) => (
      guide.id === id ? Object.assign({}, normalizeGuide(guide), { visible: guide.visible === false }) : normalizeGuide(guide)
    ));
  }

  function deleteGuide(guides, id) {
    return (guides || []).filter((guide) => guide.id !== id);
  }

  function guideSnapCandidates(guides, renderMm) {
    const page = renderMm || { ancho: 0, alto: 0 };
    const candidates = [];
    (guides || []).forEach((guide) => {
      const item = normalizeGuide(guide);
      if (item.visible === false) return;
      const value = guidePosition(item);
      if (item.orientation === "vertical") {
        candidates.push({ source_id: item.id, kind: "guia_vertical", x_mm: value, y_mm: 0 });
        candidates.push({ source_id: item.id, kind: "guia_vertical_centro", x_mm: value, y_mm: Number(page.alto || 0) / 2 });
      } else {
        candidates.push({ source_id: item.id, kind: "guia_horizontal", x_mm: 0, y_mm: value });
        candidates.push({ source_id: item.id, kind: "guia_horizontal_centro", x_mm: Number(page.ancho || 0) / 2, y_mm: value });
      }
    });
    return candidates;
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  return {
    createGuide,
    normalizeGuide,
    normalizeGuides,
    guidePosition,
    moveGuide,
    replaceGuide,
    toggleGuideVisibility,
    deleteGuide,
    guideSnapCandidates,
  };
});
