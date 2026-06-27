(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function snapPoint(point, measurements, enabled, strict) {
    const base = { x_mm: round(point.x_mm), y_mm: round(point.y_mm) };
    if (!enabled) {
      return { snapped: false, point: base, candidate: null };
    }
    const threshold = strict ? 0.75 : 2;
    let best = null;
    snapCandidates(measurements).forEach((candidate) => {
      const distance = Math.hypot(candidate.x_mm - base.x_mm, candidate.y_mm - base.y_mm);
      if (distance <= threshold && (!best || distance < best.distance_mm)) {
        best = { candidate, distance_mm: distance };
      }
    });
    if (!best) {
      return { snapped: false, point: base, candidate: null };
    }
    return {
      snapped: true,
      point: { x_mm: round(best.candidate.x_mm), y_mm: round(best.candidate.y_mm) },
      candidate: best.candidate,
      distance_mm: round(best.distance_mm),
    };
  }

  function snapCandidates(measurements) {
    const candidates = [];
    (measurements || []).forEach((item) => {
      if (item.visible === false) return;
      if (item.tipo === "linea" && item.a && item.b) {
        candidates.push({ source_id: item.id, kind: "linea_inicio", x_mm: item.a.x_mm, y_mm: item.a.y_mm });
        candidates.push({ source_id: item.id, kind: "linea_fin", x_mm: item.b.x_mm, y_mm: item.b.y_mm });
      }
      if (item.tipo === "rectangulo") {
        const x = Number(item.x_mm || 0);
        const y = Number(item.y_mm || 0);
        const w = Number(item.ancho_mm || 0);
        const h = Number(item.alto_mm || 0);
        [
          ["esquina_sup_izq", x, y],
          ["esquina_sup_der", x + w, y],
          ["esquina_inf_izq", x, y + h],
          ["esquina_inf_der", x + w, y + h],
          ["centro", x + w / 2, y + h / 2],
          ["borde_sup", x + w / 2, y],
          ["borde_inf", x + w / 2, y + h],
          ["borde_izq", x, y + h / 2],
          ["borde_der", x + w, y + h / 2],
        ].forEach(([kind, px, py]) => {
          candidates.push({ source_id: item.id, kind, x_mm: round(px), y_mm: round(py) });
        });
      }
    });
    return candidates;
  }

  function round(value) {
    return window.PdfMedidorPro.roundMm(value);
  }

  window.PdfMedidorPro.snapPoint = snapPoint;
  window.PdfMedidorPro.snapCandidates = snapCandidates;
})();
