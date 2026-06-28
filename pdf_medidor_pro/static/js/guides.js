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
    return {
      id: `g_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
      orientation: orientation === "horizontal" ? "horizontal" : "vertical",
      value_mm: round(valueMm),
      visible: true,
    };
  }

  function toggleGuideVisibility(guides, id) {
    return (guides || []).map((guide) => (
      guide.id === id ? Object.assign({}, guide, { visible: guide.visible === false }) : guide
    ));
  }

  function deleteGuide(guides, id) {
    return (guides || []).filter((guide) => guide.id !== id);
  }

  function guideSnapCandidates(guides, renderMm) {
    const page = renderMm || { ancho: 0, alto: 0 };
    const candidates = [];
    (guides || []).forEach((guide) => {
      if (guide.visible === false) return;
      const value = Number(guide.value_mm || 0);
      if (guide.orientation === "vertical") {
        candidates.push({ source_id: guide.id, kind: "guia_vertical", x_mm: value, y_mm: 0 });
        candidates.push({ source_id: guide.id, kind: "guia_vertical_centro", x_mm: value, y_mm: Number(page.alto || 0) / 2 });
      } else {
        candidates.push({ source_id: guide.id, kind: "guia_horizontal", x_mm: 0, y_mm: value });
        candidates.push({ source_id: guide.id, kind: "guia_horizontal_centro", x_mm: Number(page.ancho || 0) / 2, y_mm: value });
      }
    });
    return candidates;
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  return {
    createGuide,
    toggleGuideVisibility,
    deleteGuide,
    guideSnapCandidates,
  };
});
