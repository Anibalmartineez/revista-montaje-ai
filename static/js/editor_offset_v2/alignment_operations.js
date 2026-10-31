(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.AlignmentOperations = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const EPSILON_MM = 1e-9;
  const MAX_MATRIX_NEW_SLOTS = 500;
  const GEOMETRY_REFERENCES = Object.freeze(["trim", "productive"]);
  const TARGETS = Object.freeze(["selection", "key", "sheet", "printable"]);
  const GAP_ANCHORS = Object.freeze(["start", "end", "key"]);
  const DECIMAL_PATTERN = /^[+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)$/;

  function assertChoice(value, allowed, name) {
    if (!allowed.includes(value)) throw new Error(`${name} no válido: ${value}.`);
    return value;
  }

  function parseNonNegativeMillimetres(rawValue) {
    const text = String(rawValue ?? "").trim();
    if (!text || !DECIMAL_PATTERN.test(text)) {
      return Object.freeze({ ok: false, value: null, error: "Introduce un número finito mayor o igual a 0." });
    }
    const value = Number(text.replace(",", "."));
    if (!Number.isFinite(value) || value < 0) {
      return Object.freeze({ ok: false, value: null, error: "Introduce un número finito mayor o igual a 0." });
    }
    return Object.freeze({ ok: true, value, error: null });
  }

  function parsePositiveInteger(rawValue, label) {
    const text = String(rawValue ?? "").trim();
    if (!/^\d+$/.test(text)) {
      return Object.freeze({ ok: false, value: null, error: `${label} debe ser un entero mayor o igual a 1.` });
    }
    const value = Number(text);
    if (!Number.isSafeInteger(value) || value < 1) {
      return Object.freeze({ ok: false, value: null, error: `${label} debe ser un entero mayor o igual a 1.` });
    }
    return Object.freeze({ ok: true, value, error: null });
  }

  function boundsCenter(bounds) {
    return {
      x: bounds.left + bounds.width / 2,
      y: bounds.bottom + bounds.height / 2,
    };
  }

  function slotBounds(slot, geometry, reference) {
    assertChoice(reference, GEOMETRY_REFERENCES, "Referencia geométrica");
    return reference === "trim" ? geometry.trimBounds(slot) : geometry.bleedBounds(slot);
  }

  function aggregateBounds(slots, geometry, reference) {
    const bounds = geometry.boundsUnion(slots.map((slot) => slotBounds(slot, geometry, reference)));
    if (!bounds) throw new Error("La operación requiere al menos un slot.");
    return bounds;
  }

  function sheetBounds(layout) {
    return {
      left: 0,
      right: layout.sheet.size_mm.width,
      bottom: 0,
      top: layout.sheet.size_mm.height,
      width: layout.sheet.size_mm.width,
      height: layout.sheet.size_mm.height,
    };
  }

  function targetBounds(layout, geometry, target) {
    if (target === "sheet") return sheetBounds(layout);
    if (target === "printable") return geometry.printableBounds(layout.sheet);
    throw new Error(`El destino ${target} no define un rectángulo contenedor.`);
  }

  function selectedSlots(layout, slotIds, activeFace) {
    const requested = new Set(slotIds || []);
    const slots = layout.slots.filter((slot) => requested.has(slot.id));
    if (!requested.size || slots.length !== requested.size) {
      throw new Error("La selección contiene slots inexistentes.");
    }
    const incompatible = slots.find((slot) => slot.face !== activeFace);
    if (incompatible) throw new Error(`El slot ${incompatible.id} no pertenece a la cara activa.`);
    return slots;
  }

  function stableOrder(layout, slots, geometry, reference, axis) {
    const indexes = new Map(layout.slots.map((slot, index) => [slot.id, index]));
    return [...slots].sort((left, right) => {
      const leftBounds = slotBounds(left, geometry, reference);
      const rightBounds = slotBounds(right, geometry, reference);
      const primary = axis === "horizontal"
        ? leftBounds.left - rightBounds.left
        : rightBounds.top - leftBounds.top;
      if (Math.abs(primary) > EPSILON_MM) return primary;
      const byLayout = indexes.get(left.id) - indexes.get(right.id);
      return byLayout || left.id.localeCompare(right.id);
    });
  }

  function movePlan(slots, desiredPositions, metadata) {
    const beforePositions = {};
    const afterPositions = {};
    for (const slot of slots) {
      const desired = desiredPositions[slot.id];
      if (!desired) continue;
      const before = slot.geometry.position_mm;
      if (Math.abs(before.x_mm - desired.x_mm) <= EPSILON_MM
          && Math.abs(before.y_mm - desired.y_mm) <= EPSILON_MM) continue;
      beforePositions[slot.id] = { x_mm: before.x_mm, y_mm: before.y_mm };
      afterPositions[slot.id] = { x_mm: desired.x_mm, y_mm: desired.y_mm };
    }
    const affectedIds = Object.keys(afterPositions);
    return Object.freeze({
      ...metadata,
      changed: affectedIds.length > 0,
      affectedIds: Object.freeze(affectedIds),
      beforePositions: Object.freeze(beforePositions),
      afterPositions: Object.freeze(afterPositions),
    });
  }

  function alignedPosition(slot, bounds, referenceBounds, alignment) {
    const position = slot.geometry.position_mm;
    const next = { x_mm: position.x_mm, y_mm: position.y_mm };
    if (["left", "right", "horizontal_center", "both"].includes(alignment)) {
      if (alignment === "left") next.x_mm += referenceBounds.left - bounds.left;
      else if (alignment === "right") next.x_mm += referenceBounds.right - bounds.right;
      else next.x_mm += boundsCenter(referenceBounds).x - boundsCenter(bounds).x;
    }
    if (["top", "bottom", "vertical_center", "both"].includes(alignment)) {
      if (alignment === "top") next.y_mm += referenceBounds.top - bounds.top;
      else if (alignment === "bottom") next.y_mm += referenceBounds.bottom - bounds.bottom;
      else next.y_mm += boundsCenter(referenceBounds).y - boundsCenter(bounds).y;
    }
    return next;
  }

  function buildAlignmentPlan(layout, slotIds, geometry, options) {
    const reference = assertChoice(options?.geometryReference, GEOMETRY_REFERENCES, "Referencia geométrica");
    const target = assertChoice(options?.target, TARGETS, "Destino");
    const alignment = assertChoice(options?.alignment, [
      "left", "right", "top", "bottom", "horizontal_center", "vertical_center", "both",
    ], "Alineación");
    const slots = selectedSlots(layout, slotIds, options?.activeFace);
    const desired = {};

    if (target === "selection") {
      if (slots.length < 2) throw new Error("Alinear respecto a la selección requiere al menos dos slots.");
      const aggregate = aggregateBounds(slots, geometry, reference);
      for (const slot of slots) {
        desired[slot.id] = alignedPosition(
          slot,
          slotBounds(slot, geometry, reference),
          aggregate,
          alignment,
        );
      }
    } else if (target === "key") {
      if (slots.length < 2) throw new Error("Alinear al slot clave requiere al menos dos slots.");
      const keySlot = slots.find((slot) => slot.id === options?.keySlotId);
      if (!keySlot) throw new Error("Define un slot clave válido dentro de la selección.");
      const keyBounds = slotBounds(keySlot, geometry, reference);
      for (const slot of slots) {
        if (slot.id === keySlot.id) continue;
        desired[slot.id] = alignedPosition(
          slot,
          slotBounds(slot, geometry, reference),
          keyBounds,
          alignment,
        );
      }
    } else {
      const aggregate = aggregateBounds(slots, geometry, reference);
      const container = targetBounds(layout, geometry, target);
      const aggregatePosition = {
        geometry: { position_mm: { x_mm: boundsCenter(aggregate).x, y_mm: boundsCenter(aggregate).y } },
      };
      const shifted = alignedPosition(aggregatePosition, aggregate, container, alignment);
      const dx = shifted.x_mm - boundsCenter(aggregate).x;
      const dy = shifted.y_mm - boundsCenter(aggregate).y;
      for (const slot of slots) {
        desired[slot.id] = {
          x_mm: slot.geometry.position_mm.x_mm + dx,
          y_mm: slot.geometry.position_mm.y_mm + dy,
        };
      }
    }
    return movePlan(slots, desired, { target, geometryReference: reference, alignment });
  }

  function buildDistributionPlan(layout, slotIds, geometry, options) {
    const reference = assertChoice(options?.geometryReference, GEOMETRY_REFERENCES, "Referencia geométrica");
    const target = assertChoice(options?.target, ["selection", "sheet", "printable"], "Destino");
    const axis = assertChoice(options?.axis, ["horizontal", "vertical"], "Eje");
    const slots = selectedSlots(layout, slotIds, options?.activeFace);
    if (slots.length < 3) throw new Error("Distribuir requiere al menos tres slots.");
    const ordered = stableOrder(layout, slots, geometry, reference, axis);
    const bounds = ordered.map((slot) => slotBounds(slot, geometry, reference));
    const container = target === "selection"
      ? axis === "horizontal"
        ? {
          left: bounds[0].left,
          right: bounds[bounds.length - 1].right,
          bottom: Math.min(...bounds.map((item) => item.bottom)),
          top: Math.max(...bounds.map((item) => item.top)),
          width: bounds[bounds.length - 1].right - bounds[0].left,
          height: Math.max(...bounds.map((item) => item.top))
            - Math.min(...bounds.map((item) => item.bottom)),
        }
        : {
          left: Math.min(...bounds.map((item) => item.left)),
          right: Math.max(...bounds.map((item) => item.right)),
          bottom: bounds[bounds.length - 1].bottom,
          top: bounds[0].top,
          width: Math.max(...bounds.map((item) => item.right))
            - Math.min(...bounds.map((item) => item.left)),
          height: bounds[0].top - bounds[bounds.length - 1].bottom,
        }
      : targetBounds(layout, geometry, target);
    const span = axis === "horizontal" ? container.width : container.height;
    const occupied = bounds.reduce((total, item) => total + (axis === "horizontal" ? item.width : item.height), 0);
    const gapMm = (span - occupied) / (ordered.length - 1);
    const desired = {};

    if (axis === "horizontal") {
      let cursor = container.left;
      ordered.forEach((slot, index) => {
        const item = bounds[index];
        desired[slot.id] = {
          x_mm: cursor + item.width / 2,
          y_mm: slot.geometry.position_mm.y_mm,
        };
        cursor += item.width + gapMm;
      });
    } else {
      let cursor = container.top;
      ordered.forEach((slot, index) => {
        const item = bounds[index];
        desired[slot.id] = {
          x_mm: slot.geometry.position_mm.x_mm,
          y_mm: cursor - item.height / 2,
        };
        cursor -= item.height + gapMm;
      });
    }
    return movePlan(slots, desired, {
      target,
      geometryReference: reference,
      axis,
      gapMm,
      overlap: gapMm < -EPSILON_MM,
      orderedIds: Object.freeze(ordered.map((slot) => slot.id)),
    });
  }

  function buildExactGapPlan(layout, slotIds, geometry, options) {
    const reference = assertChoice(options?.geometryReference, GEOMETRY_REFERENCES, "Referencia geométrica");
    const axis = assertChoice(options?.axis, ["horizontal", "vertical"], "Eje");
    const anchor = assertChoice(options?.anchor, GAP_ANCHORS, "Anclaje");
    const gapMm = Number(options?.gapMm);
    if (!Number.isFinite(gapMm) || gapMm < 0) throw new Error("El gap debe ser finito y mayor o igual a 0.");
    const slots = selectedSlots(layout, slotIds, options?.activeFace);
    if (slots.length < 2) throw new Error("El gap exacto requiere al menos dos slots.");
    const ordered = stableOrder(layout, slots, geometry, reference, axis);
    const bounds = ordered.map((slot) => slotBounds(slot, geometry, reference));
    const keyIndex = anchor === "key" ? ordered.findIndex((slot) => slot.id === options?.keySlotId) : -1;
    if (anchor === "key" && keyIndex < 0) throw new Error("Define un slot clave válido dentro de la selección.");
    const fixedIndex = anchor === "start" ? 0 : anchor === "end" ? ordered.length - 1 : keyIndex;
    const desired = Object.fromEntries(ordered.map((slot) => [slot.id, {
      x_mm: slot.geometry.position_mm.x_mm,
      y_mm: slot.geometry.position_mm.y_mm,
    }]));

    for (let index = fixedIndex + 1; index < ordered.length; index += 1) {
      const previous = ordered[index - 1];
      const current = ordered[index];
      if (axis === "horizontal") {
        const previousRight = desired[previous.id].x_mm + bounds[index - 1].width / 2;
        desired[current.id].x_mm = previousRight + gapMm + bounds[index].width / 2;
      } else {
        const previousBottom = desired[previous.id].y_mm - bounds[index - 1].height / 2;
        desired[current.id].y_mm = previousBottom - gapMm - bounds[index].height / 2;
      }
    }
    for (let index = fixedIndex - 1; index >= 0; index -= 1) {
      const next = ordered[index + 1];
      const current = ordered[index];
      if (axis === "horizontal") {
        const nextLeft = desired[next.id].x_mm - bounds[index + 1].width / 2;
        desired[current.id].x_mm = nextLeft - gapMm - bounds[index].width / 2;
      } else {
        const nextTop = desired[next.id].y_mm + bounds[index + 1].height / 2;
        desired[current.id].y_mm = nextTop + gapMm + bounds[index].height / 2;
      }
    }
    return movePlan(slots, desired, {
      geometryReference: reference,
      axis,
      anchor,
      gapMm,
      orderedIds: Object.freeze(ordered.map((slot) => slot.id)),
      fixedId: ordered[fixedIndex].id,
    });
  }

  function matrixSummary(sourceCount, rows, columns) {
    if (!Number.isSafeInteger(rows) || rows < 1 || !Number.isSafeInteger(columns) || columns < 1) {
      throw new Error("Filas y columnas deben ser enteros mayores o iguales a 1.");
    }
    if (rows === 1 && columns === 1) throw new Error("La matriz debe tener más de una celda.");
    const totalCells = rows * columns;
    const copiedCells = totalCells - 1;
    const newSlots = sourceCount * copiedCells;
    if (!Number.isSafeInteger(newSlots) || newSlots > MAX_MATRIX_NEW_SLOTS) {
      throw new Error(`La matriz excede el límite de ${MAX_MATRIX_NEW_SLOTS} slots nuevos por operación.`);
    }
    return Object.freeze({ sourceCount, rows, columns, totalCells, copiedCells, newSlots });
  }

  function prepareMatrixCopies(layout, slotIds, geometry, commands, options) {
    const reference = assertChoice(options?.geometryReference, GEOMETRY_REFERENCES, "Referencia geométrica");
    const rows = Number(options?.rows);
    const columns = Number(options?.columns);
    const gapX = Number(options?.gapX);
    const gapY = Number(options?.gapY);
    if (!Number.isFinite(gapX) || gapX < 0 || !Number.isFinite(gapY) || gapY < 0) {
      throw new Error("Los gaps de matriz deben ser finitos y mayores o iguales a 0.");
    }
    const sources = selectedSlots(layout, slotIds, options?.activeFace);
    const summary = matrixSummary(sources.length, rows, columns);
    const cell = aggregateBounds(sources, geometry, reference);
    const pitchX = cell.width + gapX;
    const pitchY = cell.height + gapY;
    const reservedIds = new Set();
    const copies = [];
    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        if (row === 0 && column === 0) continue;
        copies.push(...commands.prepareDuplicateSlotsFromSlots(
          layout,
          sources,
          { x_mm: column * pitchX, y_mm: -row * pitchY },
          { idFactory: options?.idFactory, reservedIds },
        ));
      }
    }
    return Object.freeze({
      ...summary,
      geometryReference: reference,
      gapX,
      gapY,
      pitchX,
      pitchY,
      sourceIds: Object.freeze(sources.map((slot) => slot.id)),
      copies: Object.freeze(copies),
    });
  }

  function parsePositiveMillimetres(rawValue) {
    const parsed = parseNonNegativeMillimetres(rawValue);
    if (!parsed.ok || parsed.value <= 0) return Object.freeze({ ok: false, value: null, error: "Introduce una medida mayor que 0 mm." });
    return Object.freeze({ ok: true, value: parsed.value, error: null });
  }

  const MATRIX_CLEARANCE_MM = 0.5;

  function rectsOverlap(left, right) {
    return left.left < right.right - EPSILON_MM
      && left.right > right.left + EPSILON_MM
      && left.bottom < right.top - EPSILON_MM
      && left.top > right.bottom + EPSILON_MM;
  }

  function matrixObstacles(layout, face) {
    const slots = (layout.slots || []).filter((slot) => slot.face === face).map((slot) => {
      const geometry = slot.geometry;
      const rotation = ((Number(geometry.rotation_deg) % 360) + 360) % 360;
      const width = [90, 270].includes(rotation) ? geometry.trim_size_mm.height : geometry.trim_size_mm.width;
      const height = [90, 270].includes(rotation) ? geometry.trim_size_mm.width : geometry.trim_size_mm.height;
      const bleed = Number(geometry.bleed_mm || 0) + MATRIX_CLEARANCE_MM;
      return { left: geometry.position_mm.x_mm - width / 2 - bleed, right: geometry.position_mm.x_mm + width / 2 + bleed,
        bottom: geometry.position_mm.y_mm - height / 2 - bleed, top: geometry.position_mm.y_mm + height / 2 + bleed };
    });
    const cells = (layout.matrix_cells || []).filter((cell) => cell.face === face).map((cell) => ({
      left: cell.position_mm.x_mm - cell.trim_size_mm.width / 2 - MATRIX_CLEARANCE_MM,
      right: cell.position_mm.x_mm + cell.trim_size_mm.width / 2 + MATRIX_CLEARANCE_MM,
      bottom: cell.position_mm.y_mm - cell.trim_size_mm.height / 2 - MATRIX_CLEARANCE_MM,
      top: cell.position_mm.y_mm + cell.trim_size_mm.height / 2 + MATRIX_CLEARANCE_MM,
    }));
    return [...slots, ...cells];
  }

  function findMatrixPlacement(layout, options) {
    const rows = Number(options?.rows), columns = Number(options?.columns);
    const width = Number(options?.width), height = Number(options?.height);
    const gapX = Number(options?.gapX), gapY = Number(options?.gapY);
    const face = options?.activeFace;
    if (![rows, columns].every((value) => Number.isSafeInteger(value) && value > 0)) throw new Error("Filas y columnas deben ser enteros mayores que cero.");
    if (rows * columns > MAX_MATRIX_NEW_SLOTS) throw new Error(`La matriz excede el límite de ${MAX_MATRIX_NEW_SLOTS} cuadros.`);
    if (![width, height].every((value) => Number.isFinite(value) && value > 0)) throw new Error("El ancho y el alto deben ser mayores que cero.");
    if (![gapX, gapY].every((value) => Number.isFinite(value) && value >= 0)) throw new Error("Las separaciones deben ser números no negativos.");
    if (!layout.faces.enabled.includes(face)) throw new Error("La cara seleccionada no está habilitada.");
    const margins = layout.sheet.printable_margins_mm, sheet = layout.sheet.size_mm;
    const printable = { left: margins.left, right: sheet.width - margins.right,
      bottom: margins.bottom, top: sheet.height - margins.top };
    printable.width = printable.right - printable.left;
    printable.height = printable.top - printable.bottom;
    const totalWidth = columns * width + (columns - 1) * gapX;
    const totalHeight = rows * height + (rows - 1) * gapY;
    if (totalWidth > printable.width + EPSILON_MM || totalHeight > printable.height + EPSILON_MM) throw new Error("La matriz no cabe en el área imprimible del pliego.");
    const centerX = (printable.left + printable.right - totalWidth) / 2;
    const centerY = (printable.bottom + printable.top - totalHeight) / 2;
    const obstacles = matrixObstacles(layout, face);
    const candidates = (starts, extent, minimum, maximum, center) => [...new Set(starts.filter((value) => Number.isFinite(value)
      && value >= minimum - EPSILON_MM && value + extent <= maximum + EPSILON_MM))]
      .sort((a, b) => Math.abs(a - center) - Math.abs(b - center) || a - b);
    const xStarts = candidates([centerX, printable.left, printable.right - totalWidth,
      ...obstacles.flatMap((rect) => [rect.right, rect.left - totalWidth])], totalWidth,
    printable.left, printable.right, centerX);
    const yStarts = candidates([centerY, printable.bottom, printable.top - totalHeight,
      ...obstacles.flatMap((rect) => [rect.top, rect.bottom - totalHeight])], totalHeight,
    printable.bottom, printable.top, centerY);
    for (const left of xStarts) for (const bottom of yStarts) {
      const group = { left, right: left + totalWidth, bottom, top: bottom + totalHeight };
      if (!obstacles.some((obstacle) => rectsOverlap(group, obstacle))) {
        return Object.freeze({ left, bottom, right: group.right, top: group.top, width: totalWidth, height: totalHeight });
      }
    }
    throw new Error("No hay espacio libre para esta matriz en la cara seleccionada. Reduce su tamaño o separaciones, o elige la otra cara.");
  }

  function buildEmptyMatrixCells(layout, options) {
    const rows = Number(options?.rows), columns = Number(options?.columns);
    const width = Number(options?.width), height = Number(options?.height);
    const gapX = Number(options?.gapX), gapY = Number(options?.gapY);
    const face = options?.activeFace;
    const totalWidth = columns * width + (columns - 1) * gapX;
    const totalHeight = rows * height + (rows - 1) * gapY;
    const placement = findMatrixPlacement(layout, options);
    const left = placement.left;
    const top = placement.top;
    const taken = new Set([...(layout.slots || []).map((item) => item.id), ...(layout.matrix_cells || []).map((item) => item.id)]);
    const makeId = options?.idFactory || (() => `matrix_cell_${globalThis.crypto?.randomUUID?.().replace(/-/g, "") || Math.random().toString(36).slice(2)}`);
    const cells = [];
    for (let row = 0; row < rows; row += 1) for (let column = 0; column < columns; column += 1) {
      let id = String(makeId());
      if (!id || taken.has(id)) throw new Error("No se pudo generar un ID único para los cuadros.");
      taken.add(id);
      cells.push({ id, face, position_mm: { x_mm: left + column * (width + gapX) + width / 2, y_mm: top - row * (height + gapY) - height / 2 }, trim_size_mm: { width, height } });
    }
    if (new Set(cells.map((cell) => cell.id)).size !== cells.length) throw new Error("No se pudo generar IDs únicos para los cuadros.");
    return Object.freeze({ rows, columns, width, height, gapX, gapY, placement,
      cells: Object.freeze(cells) });
  }

  return Object.freeze({
    EPSILON_MM,
    MAX_MATRIX_NEW_SLOTS,
    GEOMETRY_REFERENCES,
    TARGETS,
    GAP_ANCHORS,
    aggregateBounds,
    buildAlignmentPlan,
    buildDistributionPlan,
    buildExactGapPlan,
    buildEmptyMatrixCells,
    findMatrixPlacement,
    matrixSummary,
    parseNonNegativeMillimetres,
    parsePositiveInteger,
    parsePositiveMillimetres,
    prepareMatrixCopies,
    sheetBounds,
    slotBounds,
    stableOrder,
    targetBounds,
  });
});
