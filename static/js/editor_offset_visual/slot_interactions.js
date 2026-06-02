(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function normalizeSelectedSlots(selectedSlots) {
    if (selectedSlots instanceof Set) return new Set(selectedSlots);
    return new Set(selectedSlots || []);
  }

  function findSlotById(layout, id) {
    if (!id) return null;
    return (layout?.slots || []).find((slot) => slot.id === id) || null;
  }

  function firstSelectedSlot(layout, selectedSlots) {
    const firstSelectedId = selectedSlots.values().next().value;
    return findSlotById(layout, firstSelectedId);
  }

  function selectSlot(ctx) {
    const { layout, selectedSlots: currentSelectedSlots, id, toggle = false } = ctx;

    if (!id) {
      return {
        selectedSlot: null,
        selectedSlots: new Set(),
      };
    }

    const selectedSlots = normalizeSelectedSlots(currentSelectedSlots);
    if (toggle) {
      if (selectedSlots.has(id)) {
        selectedSlots.delete(id);
      } else {
        selectedSlots.add(id);
      }
    } else {
      selectedSlots.clear();
      selectedSlots.add(id);
    }

    return {
      selectedSlot: firstSelectedSlot(layout, selectedSlots),
      selectedSlots,
    };
  }

  function getSelectedSlotIds(ctx) {
    const { selectedSlot, selectedSlots } = ctx;
    if (selectedSlots && selectedSlots.size > 0) {
      return Array.from(selectedSlots);
    }
    return selectedSlot?.id ? [selectedSlot.id] : [];
  }

  function getSelectedSlots(ctx) {
    const {
      layout,
      selectedSlot,
      selectedSlots,
      activeFace,
      editableOnly = false,
      sameFaceOnly = true,
    } = ctx;
    const ids = new Set(getSelectedSlotIds({ selectedSlot, selectedSlots }));
    return (layout?.slots || []).filter((slot) => {
      if (!ids.has(slot.id)) return false;
      if (editableOnly && slot.locked) return false;
      if (sameFaceOnly && (slot.face || 'front') !== (activeFace || 'front')) return false;
      return true;
    });
  }

  function selectAllSlotsOnActiveFace(ctx) {
    const { layout, activeFace } = ctx;
    const face = activeFace || 'front';
    const slots = (layout?.slots || []).filter((slot) => (slot.face || 'front') === face);
    if (!slots.length) {
      return {
        changed: false,
        selectedSlot: null,
        selectedSlots: new Set(),
      };
    }
    return {
      changed: true,
      selectedSlot: slots[0] || null,
      selectedSlots: new Set(slots.map((slot) => slot.id)),
    };
  }

  function refreshSelectionAfterEdit(ctx) {
    const { layout, selectedSlot, selectedSlotIds } = ctx;
    const selectedId = selectedSlot?.id || selectedSlotIds?.[0];
    return {
      selectedSlot: findSlotById(layout, selectedId),
    };
  }

  function getBoxSelectionRectMm(ctx) {
    const { boxSelectState, scale, sheetMm } = ctx;
    if (!boxSelectState?.startPx || !boxSelectState?.currentPx) return null;
    const [sheetW, sheetH] = sheetMm || [0, 0];
    const minXPx = Math.min(boxSelectState.startPx.xPx, boxSelectState.currentPx.xPx);
    const maxXPx = Math.max(boxSelectState.startPx.xPx, boxSelectState.currentPx.xPx);
    const minYPx = Math.min(boxSelectState.startPx.yPx, boxSelectState.currentPx.yPx);
    const maxYPx = Math.max(boxSelectState.startPx.yPx, boxSelectState.currentPx.yPx);
    return {
      minX: Math.max(0, minXPx / scale),
      maxX: Math.min(sheetW, maxXPx / scale),
      minY: Math.max(0, sheetH - maxYPx / scale),
      maxY: Math.min(sheetH, sheetH - minYPx / scale),
    };
  }

  function renderBoxSelectionRect(ctx) {
    const { boxSelectState } = ctx;
    if (!boxSelectState?.startPx || !boxSelectState?.currentPx) return null;
    const minX = Math.min(boxSelectState.startPx.xPx, boxSelectState.currentPx.xPx);
    const maxX = Math.max(boxSelectState.startPx.xPx, boxSelectState.currentPx.xPx);
    const minY = Math.min(boxSelectState.startPx.yPx, boxSelectState.currentPx.yPx);
    const maxY = Math.max(boxSelectState.startPx.yPx, boxSelectState.currentPx.yPx);
    return {
      left: `${minX}px`,
      top: `${minY}px`,
      width: `${maxX - minX}px`,
      height: `${maxY - minY}px`,
    };
  }

  function clearBoxSelectionRect() {
    return {
      rectEl: null,
    };
  }

  function resetBoxSelectState() {
    return {
      active: false,
      pointerId: null,
      startPx: null,
      currentPx: null,
      additive: false,
      moved: false,
      moveHandler: null,
      upHandler: null,
    };
  }

  function selectSlotsInBox(ctx) {
    const {
      layout,
      activeFace,
      selectedSlots: currentSelectedSlots,
      boxSelectState,
      scale,
      rectsIntersect,
      slotFootprintRect,
    } = ctx;
    const rect = getBoxSelectionRectMm({
      boxSelectState,
      scale,
      sheetMm: layout?.sheet_mm || [0, 0],
    });
    if (!rect) return null;

    const face = activeFace || 'front';
    const matchedIds = (layout?.slots || [])
      .filter((slot) => (slot.face || 'front') === face)
      .filter((slot) => rectsIntersect(rect, slotFootprintRect(slot)))
      .map((slot) => slot.id);

    const selectedSlots = boxSelectState?.additive ? normalizeSelectedSlots(currentSelectedSlots) : new Set();
    matchedIds.forEach((id) => selectedSlots.add(id));

    return {
      selectedSlot: firstSelectedSlot(layout, selectedSlots),
      selectedSlots,
      matchedIds,
    };
  }

  function startBoxSelect(ctx) {
    const { point, pointerId, clientX, clientY, additive } = ctx;
    return {
      active: true,
      pointerId,
      startClientX: clientX,
      startClientY: clientY,
      startPx: point,
      currentPx: point,
      additive: !!additive,
      moved: false,
    };
  }

  function moveBoxSelect(ctx) {
    const { boxSelectState, pointerId, clientX, clientY, point, dragThresholdPx } = ctx;
    if (!boxSelectState?.active) return { shouldMove: false };
    if (boxSelectState.pointerId != null && pointerId !== boxSelectState.pointerId) {
      return { shouldMove: false };
    }
    const dragDistancePx = Math.hypot(
      clientX - boxSelectState.startClientX,
      clientY - boxSelectState.startClientY,
    );
    if (!boxSelectState.moved && dragDistancePx < dragThresholdPx) {
      return { shouldMove: false };
    }
    return {
      shouldMove: true,
      moved: true,
      currentPx: point,
    };
  }

  function endBoxSelect(ctx) {
    const { boxSelectState, pointerId } = ctx;
    if (!boxSelectState?.active) return { shouldEnd: false };
    if (boxSelectState.pointerId != null && pointerId !== boxSelectState.pointerId) {
      return { shouldEnd: false };
    }
    return {
      shouldEnd: true,
      moved: !!boxSelectState.moved,
    };
  }

  function startDrag(ctx) {
    const { layout, slot, targetClassNames, pointerId, clientX, clientY } = ctx;
    const classes = Array.isArray(targetClassNames) ? targetClassNames : [];
    const isHandle = classes.includes('handle');
    const handleType = isHandle
      ? classes.find((className) => ['br', 'bl', 'tr', 'tl'].includes(className)) || null
      : null;
    const isGroupMove = !isHandle && !!slot?.group_id;
    const groupSlots = isGroupMove
      ? (layout?.slots || []).filter((candidate) => candidate.group_id === slot.group_id)
      : [];
    const groupInitialPositions = new Map();
    if (isGroupMove) {
      groupSlots.forEach((groupSlot) => {
        groupInitialPositions.set(groupSlot.id, {
          x: groupSlot.x_mm,
          y: groupSlot.y_mm,
        });
      });
    }

    return {
      active: true,
      pointerId,
      slot,
      startX: clientX,
      startY: clientY,
      initSlot: { ...slot },
      handleType,
      isHandle,
      isGroupMove,
      groupSlots,
      groupInitialPositions,
      moved: false,
    };
  }

  function moveDrag(ctx) {
    const {
      dragState,
      pointerId,
      clientX,
      clientY,
      effectiveScale,
      dragThresholdPx,
      applySnap,
    } = ctx;
    if (!dragState?.active) return { shouldMove: false };
    if (dragState.pointerId != null && pointerId !== dragState.pointerId) {
      return { shouldMove: false };
    }

    const dxPx = clientX - dragState.startX;
    const dyPx = dragState.startY - clientY;
    const dragDistancePx = Math.hypot(dxPx, dyPx);
    if (!dragState.moved && dragDistancePx < dragThresholdPx) {
      return { shouldMove: false };
    }

    const safeScale = Number(effectiveScale) || 1;
    const dx = dxPx / safeScale;
    const dy = dyPx / safeScale;
    const { initSlot, slot, isHandle, isGroupMove, groupSlots, groupInitialPositions } = dragState;

    if (isHandle) {
      return {
        shouldMove: true,
        moved: true,
        resizeLatent: true,
        dx,
        dy,
      };
    }

    if (isGroupMove) {
      const snapped = applySnap(initSlot.x_mm + dx, initSlot.y_mm + dy, slot);
      const deltaX = snapped.x - initSlot.x_mm;
      const deltaY = snapped.y - initSlot.y_mm;
      groupSlots.forEach((groupSlot) => {
        const initPos = groupInitialPositions.get(groupSlot.id);
        if (!initPos) return;
        groupSlot.x_mm = initPos.x + deltaX;
        groupSlot.y_mm = initPos.y + deltaY;
      });
    } else {
      const snapped = applySnap(initSlot.x_mm + dx, initSlot.y_mm + dy, slot);
      slot.x_mm = snapped.x;
      slot.y_mm = snapped.y;
    }

    return {
      shouldMove: true,
      moved: true,
      resizeLatent: false,
      slot,
    };
  }

  function endDrag(ctx) {
    const { layout, selectedSlots: currentSelectedSlots, dragState } = ctx;
    const selectedSlots = currentSelectedSlots instanceof Set
      ? currentSelectedSlots
      : new Set(currentSelectedSlots || []);
    const draggedId = dragState?.slot?.id;

    if (selectedSlots.size > 1 && selectedSlots.has(draggedId)) {
      return {
        selectedSlot: findSlotById(layout, draggedId),
        selectedSlots,
      };
    }

    if (draggedId) {
      const nextSelectedSlots = new Set([draggedId]);
      return {
        selectedSlot: findSlotById(layout, draggedId),
        selectedSlots: nextSelectedSlots,
      };
    }

    return {
      selectedSlot: null,
      selectedSlots,
    };
  }

  function resetDragState() {
    return {
      active: false,
      pointerId: null,
      slot: null,
      slotElement: null,
      startX: 0,
      startY: 0,
      initSlot: null,
      handleType: null,
      isHandle: false,
      isGroupMove: false,
      groupSlots: [],
      groupInitialPositions: new Map(),
      moved: false,
      moveHandler: null,
      upHandler: null,
    };
  }

  window.EditorOffsetVisual.slotInteractions = {
    selectSlot,
    getSelectedSlotIds,
    getSelectedSlots,
    selectAllSlotsOnActiveFace,
    refreshSelectionAfterEdit,
    boxSelect: {
      getBoxSelectionRectMm,
      renderBoxSelectionRect,
      clearBoxSelectionRect,
      resetBoxSelectState,
      selectSlotsInBox,
      startBoxSelect,
      moveBoxSelect,
      endBoxSelect,
    },
    dragResize: {
      startDrag,
      moveDrag,
      endDrag,
      resetDragState,
    },
  };
})();
