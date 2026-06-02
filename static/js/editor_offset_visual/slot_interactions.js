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

  window.EditorOffsetVisual.slotInteractions = {
    selectSlot,
    getSelectedSlotIds,
    getSelectedSlots,
    selectAllSlotsOnActiveFace,
    refreshSelectionAfterEdit,
  };
})();
