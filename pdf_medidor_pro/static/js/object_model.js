(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.PdfMedidorPro = root.PdfMedidorPro || {};
    root.PdfMedidorPro.objectModel = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const HANDLE_MIN_SIZE_MM = 0.01;

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  function createLine(a, b, patch) {
    return Object.assign(
      {
        id: `m_${Date.now()}`,
        tipo: "linea",
        origen: "manual",
        nombre: "Linea manual",
        visible: true,
        locked: false,
        color: "#d97706",
        stroke_width: 2,
        pagina: 1,
        a: point(a),
        b: point(b),
        confianza: 1,
      },
      patch || {}
    );
  }

  function createRectangle(a, b, patch) {
    const x = Math.min(Number(a.x_mm || 0), Number(b.x_mm || 0));
    const y = Math.min(Number(a.y_mm || 0), Number(b.y_mm || 0));
    const w = Math.abs(Number(b.x_mm || 0) - Number(a.x_mm || 0));
    const h = Math.abs(Number(b.y_mm || 0) - Number(a.y_mm || 0));
    return Object.assign(
      {
        id: `r_${Date.now()}`,
        tipo: "rectangulo",
        origen: "manual",
        nombre: "Rectangulo manual",
        visible: true,
        locked: false,
        color: "#2563eb",
        stroke_width: 2,
        pagina: 1,
        x_mm: round(x),
        y_mm: round(y),
        ancho_mm: round(w),
        alto_mm: round(h),
        confianza: 1,
      },
      patch || {}
    );
  }

  function point(value) {
    return { x_mm: round(value.x_mm), y_mm: round(value.y_mm) };
  }

  function constrainLineAngle(start, end) {
    const dx = Number(end.x_mm || 0) - Number(start.x_mm || 0);
    const dy = Number(end.y_mm || 0) - Number(start.y_mm || 0);
    const length = Math.hypot(dx, dy);
    if (length === 0) return point(end);
    const angle = Math.atan2(dy, dx);
    const step = Math.PI / 4;
    const locked = Math.round(angle / step) * step;
    return {
      x_mm: round(Number(start.x_mm || 0) + Math.cos(locked) * length),
      y_mm: round(Number(start.y_mm || 0) + Math.sin(locked) * length),
    };
  }

  function moveObject(object, dxMm, dyMm) {
    const next = clone(object);
    if (next.locked) return next;
    if (next.tipo === "linea") {
      next.a.x_mm = round(next.a.x_mm + dxMm);
      next.a.y_mm = round(next.a.y_mm + dyMm);
      next.b.x_mm = round(next.b.x_mm + dxMm);
      next.b.y_mm = round(next.b.y_mm + dyMm);
    } else if (next.tipo === "rectangulo") {
      next.x_mm = round(next.x_mm + dxMm);
      next.y_mm = round(next.y_mm + dyMm);
    }
    return next;
  }

  function resizeRectangle(rect, handle, pointMm) {
    const next = clone(rect);
    if (next.locked || next.tipo !== "rectangulo") return next;

    let left = Number(next.x_mm || 0);
    let top = Number(next.y_mm || 0);
    let right = left + Number(next.ancho_mm || 0);
    let bottom = top + Number(next.alto_mm || 0);
    const x = Number(pointMm.x_mm || 0);
    const y = Number(pointMm.y_mm || 0);

    if (handle.includes("w")) left = x;
    if (handle.includes("e")) right = x;
    if (handle.includes("n")) top = y;
    if (handle.includes("s")) bottom = y;

    if (right < left) [left, right] = [right, left];
    if (bottom < top) [top, bottom] = [bottom, top];

    next.x_mm = round(left);
    next.y_mm = round(top);
    next.ancho_mm = round(Math.max(HANDLE_MIN_SIZE_MM, right - left));
    next.alto_mm = round(Math.max(HANDLE_MIN_SIZE_MM, bottom - top));
    return next;
  }

  function updateObject(object, patch) {
    return Object.assign(clone(object), patch || {});
  }

  function renameObject(object, name) {
    return updateObject(object, { nombre: String(name || "").trim() || object.nombre || "Medicion" });
  }

  function setObjectColor(object, color) {
    return updateObject(object, { color: color || object.color || "#0f766e" });
  }

  function setObjectVisible(object, visible) {
    return updateObject(object, { visible: Boolean(visible) });
  }

  function duplicateObject(object) {
    const next = moveObject(object, 5, 5);
    next.id = `${object.id || "obj"}_copy_${Date.now()}`;
    next.nombre = `${object.nombre || "Medicion"} copia`;
    return next;
  }

  function deleteObject(objects, id) {
    return (objects || []).filter((item) => item.id !== id);
  }

  function replaceObject(objects, object) {
    return (objects || []).map((item) => (item.id === object.id ? object : item));
  }

  function metrics(object, factor) {
    const scale = Number(factor || 1);
    if (!object) return {};
    if (object.tipo === "linea") {
      const dx = (Number(object.b.x_mm || 0) - Number(object.a.x_mm || 0)) * scale;
      const dy = (Number(object.b.y_mm || 0) - Number(object.a.y_mm || 0)) * scale;
      const distance = Math.hypot(dx, dy);
      return {
        x_mm: round(Math.min(object.a.x_mm, object.b.x_mm)),
        y_mm: round(Math.min(object.a.y_mm, object.b.y_mm)),
        ancho_mm: round(Math.abs(dx)),
        alto_mm: round(Math.abs(dy)),
        area_mm2: 0,
        perimetro_mm: round(distance),
        distancia_mm: round(distance),
        delta_x_mm: round(dx),
        delta_y_mm: round(dy),
        angulo_deg: round((Math.atan2(dy, dx) * 180) / Math.PI),
      };
    }
    const width = Number(object.ancho_mm || 0) * scale;
    const height = Number(object.alto_mm || 0) * scale;
    return {
      x_mm: round(object.x_mm),
      y_mm: round(object.y_mm),
      ancho_mm: round(width),
      alto_mm: round(height),
      area_mm2: round(width * height),
      perimetro_mm: round((width + height) * 2),
      distancia_mm: round(Math.hypot(width, height)),
      delta_x_mm: round(width),
      delta_y_mm: round(height),
      angulo_deg: 0,
    };
  }

  return {
    createLine,
    createRectangle,
    constrainLineAngle,
    moveObject,
    resizeRectangle,
    updateObject,
    renameObject,
    setObjectColor,
    setObjectVisible,
    duplicateObject,
    deleteObject,
    replaceObject,
    metrics,
    round,
  };
});
