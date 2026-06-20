(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function getSelectedIdSet(selectedSlotIds) {
    return new Set(selectedSlotIds || []);
  }

  function duplicateSelectedSlots(ctx) {
    const { layout, bases, activeFace, roundMm } = ctx;
    if (!bases || !bases.length) return { changed: false };

    const now = Date.now();
    const groupMap = new Map();
    const copies = bases.map((base, index) => {
      const copy = { ...base, id: `s${now}_${index + 1}` };
      copy.face = copy.face || base.face || activeFace || 'front';
      copy.x_mm = roundMm((copy.x_mm || 0) + 5);
      copy.y_mm = roundMm((copy.y_mm || 0) + 5);
      if (base.group_id) {
        if (!groupMap.has(base.group_id)) {
          groupMap.set(base.group_id, `g${now}_${groupMap.size + 1}`);
        }
        copy.group_id = groupMap.get(base.group_id);
      }
      return copy;
    });

    layout.slots.push(...copies);
    return {
      changed: true,
      selectedSlot: copies[0] || null,
      selectedSlotIds: copies.map((copy) => copy.id),
    };
  }

  function deleteSelectedSlots(ctx) {
    const { layout, selectedSlotIds } = ctx;
    const ids = getSelectedIdSet(selectedSlotIds);
    if (!ids.size) return { changed: false };
    layout.slots = (layout.slots || []).filter((slot) => !ids.has(slot.id));
    return { changed: true, selectedSlot: null, selectedSlotIds: [] };
  }

  function groupSelectedSlots(ctx) {
    const { layout, selectedSlotIds } = ctx;
    const ids = getSelectedIdSet(selectedSlotIds);
    if (ids.size < 2) {
      return { changed: false, message: 'Selecciona al menos dos slots para agrupar.' };
    }

    const groupId = `g${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    (layout.slots || []).forEach((slot) => {
      if (ids.has(slot.id)) {
        slot.group_id = groupId;
      }
    });
    return { changed: true };
  }

  function ungroupSelectedSlots(ctx) {
    const { layout, selectedSlotIds } = ctx;
    const ids = getSelectedIdSet(selectedSlotIds);
    if (!ids.size) {
      return { changed: false, message: 'No hay slots seleccionados para desagrupar.' };
    }

    (layout.slots || []).forEach((slot) => {
      if (ids.has(slot.id)) {
        delete slot.group_id;
      }
    });
    return { changed: true };
  }

  function alignSelectedSlots(ctx) {
    const { slots, mode, getSelectionBounds, getEffectiveSlotBox, setSlotEffectiveBox } = ctx;
    if (!slots || slots.length < 2) {
      return { changed: false, message: 'Selecciona al menos dos slots desbloqueados para alinear.' };
    }

    const bounds = getSelectionBounds(slots);
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;

    slots.forEach((slot) => {
      const box = getEffectiveSlotBox(slot);
      let left = box.x;
      let bottom = box.y;

      if (mode === 'left') left = bounds.minX;
      if (mode === 'center-x') left = centerX - box.effW / 2;
      if (mode === 'right') left = bounds.maxX - box.effW;
      if (mode === 'bottom') bottom = bounds.minY;
      if (mode === 'center-y') bottom = centerY - box.effH / 2;
      if (mode === 'top') bottom = bounds.maxY - box.effH;

      setSlotEffectiveBox(slot, left, bottom);
    });

    return { changed: true };
  }

  function distributeSelectedSlots(ctx) {
    const { slots, axis, getEffectiveSlotBox, setSlotEffectiveBox } = ctx;
    if (!slots || slots.length < 3) {
      return { changed: false, message: 'Selecciona al menos tres slots desbloqueados para distribuir.' };
    }

    const items = slots
      .map((slot) => ({ slot, box: getEffectiveSlotBox(slot) }))
      .sort((a, b) => {
        if (axis === 'x') return a.box.x - b.box.x;
        return a.box.y - b.box.y;
      });

    const first = items[0];
    const last = items[items.length - 1];
    const start = axis === 'x' ? first.box.x : first.box.y;
    const end = axis === 'x' ? last.box.x + last.box.effW : last.box.y + last.box.effH;
    const totalSize = items.reduce((sum, item) => sum + (axis === 'x' ? item.box.effW : item.box.effH), 0);
    const gap = (end - start - totalSize) / (items.length - 1);

    let cursor = start;
    items.forEach((item) => {
      if (axis === 'x') {
        setSlotEffectiveBox(item.slot, cursor, item.box.y);
        cursor += item.box.effW + gap;
      } else {
        setSlotEffectiveBox(item.slot, item.box.x, cursor);
        cursor += item.box.effH + gap;
      }
    });

    return { changed: true };
  }

  function normalizeRotationDeg(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return null;
    const normalized = ((parsed % 360) + 360) % 360;
    return Object.is(normalized, -0) ? 0 : normalized;
  }

  function rotateSelectedSlots(ctx) {
    const { slots, rotationDeg } = ctx;
    if (!slots || !slots.length) {
      return { changed: false, message: 'Selecciona al menos un slot desbloqueado para rotar.' };
    }

    const normalizedRotation = normalizeRotationDeg(rotationDeg);
    if (normalizedRotation === null) {
      return { changed: false, message: 'Ingresa una rotacion valida.' };
    }

    let changed = false;
    slots.forEach((slot) => {
      if (slot.rotation_deg !== normalizedRotation) {
        slot.rotation_deg = normalizedRotation;
        changed = true;
      }
    });

    return { changed, rotationDeg: normalizedRotation };
  }

  function centerSelectedBlock(ctx) {
    const { slots, axis, getSelectionBounds, getUsableSheetBounds, roundMm } = ctx;
    if (!slots || !slots.length) return { changed: false };

    const bounds = getSelectionBounds(slots);
    const usable = getUsableSheetBounds();
    const targetMinX = usable.minX + ((usable.maxX - usable.minX) - (bounds.maxX - bounds.minX)) / 2;
    const targetMinY = usable.minY + ((usable.maxY - usable.minY) - (bounds.maxY - bounds.minY)) / 2;
    const dx = axis === 'y' ? 0 : targetMinX - bounds.minX;
    const dy = axis === 'x' ? 0 : targetMinY - bounds.minY;

    slots.forEach((slot) => {
      slot.x_mm = roundMm((slot.x_mm || 0) + dx);
      slot.y_mm = roundMm((slot.y_mm || 0) + dy);
    });

    return { changed: true };
  }

  function nudgeSelectedSlots(ctx) {
    const { slots, dx, dy, roundMm } = ctx;
    if (!slots || !slots.length) return { changed: false };

    slots.forEach((slot) => {
      slot.x_mm = roundMm((slot.x_mm || 0) + dx);
      slot.y_mm = roundMm((slot.y_mm || 0) + dy);
    });

    return { changed: true };
  }

  function applyGapToSlots(ctx) {
    const { layout, selectedSlotIds, gapX, gapY, groupSlotsByRow } = ctx;
    if (!layout.slots || layout.slots.length === 0) {
      return { changed: false, message: 'No hay slots para reordenar.' };
    }

    const ids = selectedSlotIds || [];
    const targetSlots =
      ids.length >= 2
        ? layout.slots.filter((slot) => ids.includes(slot.id))
        : ids.length === 0
        ? [...layout.slots]
        : null;

    if (!targetSlots) {
      return { changed: false, message: 'Selecciona al menos 2 slots o ninguno para aplicar la separacion.' };
    }

    const startX = Math.min(...targetSlots.map((slot) => slot.x_mm));
    const startY = Math.min(...targetSlots.map((slot) => slot.y_mm));
    const rows = groupSlotsByRow(targetSlots);
    let currentY = startY;

    rows.forEach((row) => {
      let currentX = startX;
      row.slots.forEach((slot) => {
        slot.x_mm = currentX;
        slot.y_mm = currentY;
        currentX += slot.w_mm + gapX;
      });
      currentY += row.maxHeight + gapY;
    });

    return { changed: true };
  }

  function applySpacing(ctx) {
    const {
      layout,
      mode = 'all',
      face = 'front',
      spacingX = 0,
      spacingY = 0,
      getEffectiveSlotBox,
      groupSlotsByRow,
      groupSlotsByColumn,
    } = ctx;
    const visibleSlots = (layout.slots || []).filter((slot) => (slot.face || 'front') === face);
    if (!visibleSlots.length) return { changed: false };

    const createInitialMap = () => {
      const map = new Map();
      (layout.slots || []).forEach((slot) => map.set(slot.id, { x: slot.x_mm, y: slot.y_mm }));
      return map;
    };

    const moveGroup = (slot, dx, dy, initialMap, movedGroups) => {
      if (!slot.group_id || movedGroups.has(slot.group_id)) return;
      const faceKey = slot.face || face;
      const members = (layout.slots || []).filter(
        (member) => member.group_id === slot.group_id && (member.face || 'front') === faceKey,
      );
      members.forEach((member) => {
        const init = initialMap.get(member.id) || { x: member.x_mm, y: member.y_mm };
        member.x_mm = init.x + dx;
        member.y_mm = init.y + dy;
      });
      movedGroups.add(slot.group_id);
    };

    if (mode === 'all' || mode === 'rows') {
      const initialMap = createInitialMap();
      const movedGroups = new Set();
      const rows = groupSlotsByRow(visibleSlots);
      rows.forEach((row) => {
        let currentX = getEffectiveSlotBox(row.slots[0]).x;
        row.slots.forEach((slot, index) => {
          const box = getEffectiveSlotBox(slot);
          if (index === 0) {
            const dx = currentX - box.x;
            const newCx = box.cx + dx;
            slot.x_mm = newCx - box.baseW / 2;
            moveGroup(slot, dx, 0, initialMap, movedGroups);
            return;
          }
          const prev = row.slots[index - 1];
          const prevBox = getEffectiveSlotBox(prev);
          currentX = prevBox.x + prevBox.effW + spacingX;
          const dx = currentX - box.x;
          const newCx = box.cx + dx;
          slot.x_mm = newCx - box.baseW / 2;
          moveGroup(slot, dx, 0, initialMap, movedGroups);
        });
      });
    }

    if (mode === 'all' || mode === 'columns') {
      const initialMap = createInitialMap();
      const movedGroups = new Set();
      const cols = groupSlotsByColumn(visibleSlots);
      cols.forEach((col) => {
        let currentY = getEffectiveSlotBox(col.slots[0]).y;
        col.slots.forEach((slot, index) => {
          const box = getEffectiveSlotBox(slot);
          if (index === 0) {
            const dy = currentY - box.y;
            const newCy = box.cy + dy;
            slot.y_mm = newCy - box.baseH / 2;
            moveGroup(slot, 0, dy, initialMap, movedGroups);
            return;
          }
          const prev = col.slots[index - 1];
          const prevBox = getEffectiveSlotBox(prev);
          currentY = prevBox.y + prevBox.effH + spacingY;
          const dy = currentY - box.y;
          const newCy = box.cy + dy;
          slot.y_mm = newCy - box.baseH / 2;
          moveGroup(slot, 0, dy, initialMap, movedGroups);
        });
      });
    }

    return { changed: true };
  }

  window.EditorOffsetVisual.manualTools = {
    duplicateSelectedSlots,
    deleteSelectedSlots,
    groupSelectedSlots,
    ungroupSelectedSlots,
    alignSelectedSlots,
    distributeSelectedSlots,
    rotateSelectedSlots,
    centerSelectedBlock,
    nudgeSelectedSlots,
    applyGapToSlots,
    applySpacing,
  };
})();
