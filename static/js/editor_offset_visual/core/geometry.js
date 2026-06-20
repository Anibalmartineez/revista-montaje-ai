(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function mmToPx(mm, scale) {
    return mm * scale;
  }

  function normalizeRotationDeg(value) {
    const parsed = Number(value || 0);
    if (!Number.isFinite(parsed)) return 0;
    return ((parsed % 360) + 360) % 360;
  }

  function getCardinalRotatedSlotFootprint(slot, override = {}) {
    const baseW = Number(slot?.w_mm || 0);
    const baseH = Number(slot?.h_mm || 0);
    const x = Number(override.x ?? slot?.x_mm ?? 0);
    const y = Number(override.y ?? slot?.y_mm ?? 0);
    const rotation = normalizeRotationDeg(slot?.rotation_deg || 0);
    const isCardinal = rotation === 0 || rotation === 90 || rotation === 180 || rotation === 270;
    const swapsFootprint = isCardinal && (rotation === 90 || rotation === 270);
    const effW = swapsFootprint ? baseH : baseW;
    const effH = swapsFootprint ? baseW : baseH;
    const cx = x + baseW / 2;
    const cy = y + baseH / 2;

    return {
      rotation,
      isCardinal,
      swapsFootprint,
      baseW,
      baseH,
      effW,
      effH,
      cx,
      cy,
      x: cx - effW / 2,
      y: cy - effH / 2,
    };
  }

  function getEffectiveSlotBox(slot, override = {}) {
    const baseW = slot.w_mm || 0;
    const baseH = slot.h_mm || 0;
    const x = override.x ?? slot.x_mm;
    const y = override.y ?? slot.y_mm;
    const rotation = ((slot.rotation_deg || 0) % 360 + 360) % 360;
    const cx = x + baseW / 2;
    const cy = y + baseH / 2;

    return {
      rotation,
      baseW,
      baseH,
      effW: baseW,
      effH: baseH,
      cx,
      cy,
      x,
      y,
    };
  }

  function slotCoordsFromBox(box) {
    return {
      x: box.cx - box.baseW / 2,
      y: box.cy - box.baseH / 2,
    };
  }

  function getSlotRenderBox(slot) {
    const baseW = slot.w_mm || 0;
    const baseH = slot.h_mm || 0;
    const rotation = ((slot.rotation_deg || 0) % 360 + 360) % 360;

    return {
      x: slot.x_mm,
      y: slot.y_mm,
      w: baseW,
      h: baseH,
      rotation,
    };
  }

  function getSimpleSlotBox(slot) {
    return {
      x: Number(slot.x_mm || 0),
      y: Number(slot.y_mm || 0),
      w: Number(slot.w_mm || 0),
      h: Number(slot.h_mm || 0),
    };
  }

  function formatSignedDistance(value) {
    const rounded = Number(value || 0).toFixed(1);
    return `${rounded} mm`;
  }

  function rectDistance(boxA, boxB) {
    const dx = Math.max(boxB.x - (boxA.x + boxA.w), boxA.x - (boxB.x + boxB.w), 0);
    const dy = Math.max(boxB.y - (boxA.y + boxA.h), boxA.y - (boxB.y + boxB.h), 0);
    return Math.sqrt(dx * dx + dy * dy);
  }

  function roundMm(value) {
    return Math.round((Number(value) || 0) * 1000) / 1000;
  }

  function rectsIntersect(a, b) {
    return a.minX <= b.maxX && a.maxX >= b.minX && a.minY <= b.maxY && a.maxY >= b.minY;
  }

  function slotFootprintRect(slot) {
    const box = getEffectiveSlotBox(slot);
    return {
      minX: box.x,
      maxX: box.x + box.effW,
      minY: box.y,
      maxY: box.y + box.effH,
    };
  }

  function getUsableSheetBounds(layout) {
    const sheet = layout.sheet_mm || [0, 0];
    const margins = layout.margins_mm || [0, 0, 0, 0];
    const [left = 0, right = 0, top = 0, bottom = 0] = margins;
    const sheetW = Number(sheet[0] || 0);
    const sheetH = Number(sheet[1] || 0);
    return {
      minX: Number(left || 0),
      maxX: Math.max(Number(left || 0), sheetW - Number(right || 0)),
      minY: Number(bottom || 0),
      maxY: Math.max(Number(bottom || 0), sheetH - Number(top || 0)),
    };
  }

  function getSelectionBounds(slots) {
    const boxes = slots.map((slot) => ({ slot, box: getEffectiveSlotBox(slot) }));
    return boxes.reduce(
      (acc, item) => {
        acc.minX = Math.min(acc.minX, item.box.x);
        acc.maxX = Math.max(acc.maxX, item.box.x + item.box.effW);
        acc.minY = Math.min(acc.minY, item.box.y);
        acc.maxY = Math.max(acc.maxY, item.box.y + item.box.effH);
        return acc;
      },
      { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity },
    );
  }

  function groupSlotsByRow(slots) {
    const margin = 2;
    const rows = [];
    const byCenterY = [...slots].sort((a, b) => {
      const boxA = getEffectiveSlotBox(a);
      const boxB = getEffectiveSlotBox(b);
      return boxA.cy - boxB.cy;
    });

    byCenterY.forEach((slot) => {
      const box = getEffectiveSlotBox(slot);
      const centerY = box.cy;
      let targetRow = rows.find(
        (row) => Math.abs(row.centerY - centerY) <= (Math.max(row.maxHeight, box.effH) / 2 + margin),
      );
      if (!targetRow) {
        targetRow = { slots: [], centerY, maxHeight: box.effH };
        rows.push(targetRow);
      }
      targetRow.slots.push(slot);
      targetRow.centerY =
        (targetRow.centerY * (targetRow.slots.length - 1) + centerY) / targetRow.slots.length;
      targetRow.maxHeight = Math.max(targetRow.maxHeight, box.effH);
    });

    rows.sort((a, b) => a.centerY - b.centerY);
    rows.forEach((row) => row.slots.sort((a, b) => getEffectiveSlotBox(a).x - getEffectiveSlotBox(b).x));
    return rows;
  }

  function groupSlotsByColumn(slots) {
    const margin = 2;
    const cols = [];
    const byCenterX = [...slots].sort((a, b) => {
      const boxA = getEffectiveSlotBox(a);
      const boxB = getEffectiveSlotBox(b);
      return boxA.cx - boxB.cx;
    });

    byCenterX.forEach((slot) => {
      const box = getEffectiveSlotBox(slot);
      const centerX = box.cx;
      let targetCol = cols.find(
        (col) => Math.abs(col.centerX - centerX) <= (Math.max(col.maxWidth, box.effW) / 2 + margin),
      );
      if (!targetCol) {
        targetCol = { slots: [], centerX, maxWidth: box.effW };
        cols.push(targetCol);
      }
      targetCol.slots.push(slot);
      targetCol.centerX =
        (targetCol.centerX * (targetCol.slots.length - 1) + centerX) / targetCol.slots.length;
      targetCol.maxWidth = Math.max(targetCol.maxWidth, box.effW);
    });

    cols.sort((a, b) => a.centerX - b.centerX);
    cols.forEach((col) =>
      col.slots.sort((a, b) => getEffectiveSlotBox(a).y - getEffectiveSlotBox(b).y),
    );
    return cols;
  }

  window.EditorOffsetVisual.geometry = {
    mmToPx,
    normalizeRotationDeg,
    getCardinalRotatedSlotFootprint,
    getEffectiveSlotBox,
    slotCoordsFromBox,
    getSlotRenderBox,
    getSimpleSlotBox,
    formatSignedDistance,
    rectDistance,
    roundMm,
    rectsIntersect,
    slotFootprintRect,
    getUsableSheetBounds,
    getSelectionBounds,
    groupSlotsByRow,
    groupSlotsByColumn,
  };
})();
