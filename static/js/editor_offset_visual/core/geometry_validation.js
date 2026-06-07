(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function validateGeometry(layout) {
    const geometry = window.EditorOffsetVisual.geometry;
    const result = {
      errors: [],
      warnings: [],
      bySlot: {},
    };

    if (!layout || !Array.isArray(layout.slots)) {
      return result;
    }

    const sheet = Array.isArray(layout.sheet_mm) ? layout.sheet_mm : [0, 0];
    const margins = Array.isArray(layout.margins_mm) ? layout.margins_mm : [0, 0, 0, 0];
    const sheetW = Number(sheet[0] || 0);
    const sheetH = Number(sheet[1] || 0);
    const [marginLeft, marginRight, marginTop, marginBottom] = margins.map((value) => Number(value || 0));
    const usableLeft = marginLeft;
    const usableRight = sheetW - marginRight;
    const usableBottom = marginBottom;
    const usableTop = sheetH - marginTop;
    const ctp = layout.ctp || {};
    const gripperEnabled = !!ctp.enabled;
    const gripper = Number(ctp.gripper_mm || 0);

    const addIssue = (level, type, slotId, message, extra = {}) => {
      const issue = { type, slot_id: slotId, message, ...extra };
      if (level === 'error') {
        result.errors.push(issue);
      } else {
        result.warnings.push(issue);
      }

      if (!slotId) return;
      if (!result.bySlot[slotId]) {
        result.bySlot[slotId] = { level, issues: [issue] };
        return;
      }
      result.bySlot[slotId].issues.push(issue);
      if (result.bySlot[slotId].level !== 'error' && level === 'error') {
        result.bySlot[slotId].level = 'error';
      }
    };

    const slots = layout.slots.filter((slot) => slot && typeof slot === 'object');

    slots.forEach((slot) => {
      const slotId = slot.id || '(sin id)';
      const face = slot.face || 'front';
      const { x, y, w, h } = geometry.getSimpleSlotBox(slot);
      const right = x + w;
      const top = y + h;

      if (x < 0 || y < 0 || right > sheetW || top > sheetH) {
        addIssue(
          'error',
          'OUT_OF_SHEET',
          slotId,
          `Slot ${slotId} (${face}) est\u00e1 fuera del pliego total.`,
          { face },
        );
      }

      if (x < usableLeft || y < usableBottom || right > usableRight || top > usableTop) {
        addIssue(
          'warning',
          'OUT_OF_USABLE_AREA',
          slotId,
          `Slot ${slotId} (${face}) invade m\u00e1rgenes o sale del \u00e1rea \u00fatil del pliego.`,
          { face },
        );
      }

      if (gripperEnabled && y < gripper) {
        addIssue(
          'warning',
          'GRIPPER',
          slotId,
          `Slot ${slotId} (${face}) invade la zona de pinza/CTP (${gripper} mm).`,
          { face },
        );
      }
    });

    for (let i = 0; i < slots.length; i += 1) {
      const a = slots[i];
      const boxA = geometry.getSimpleSlotBox(a);
      const aRight = boxA.x + boxA.w;
      const aTop = boxA.y + boxA.h;
      for (let j = i + 1; j < slots.length; j += 1) {
        const b = slots[j];
        const faceA = a.face || 'front';
        const faceB = b.face || 'front';
        if (faceA !== faceB) continue;
        const boxB = geometry.getSimpleSlotBox(b);
        const bRight = boxB.x + boxB.w;
        const bTop = boxB.y + boxB.h;
        const overlaps = boxA.x < bRight && aRight > boxB.x && boxA.y < bTop && aTop > boxB.y;
        if (!overlaps) continue;

        addIssue(
          'warning',
          'OVERLAP',
          a.id || '(sin id)',
          `Slot ${a.id || '(sin id)'} (${faceA}) se superpone con ${b.id || '(sin id)'}.`,
          { face: faceA, other_slot_id: b.id || '(sin id)' },
        );
        addIssue(
          'warning',
          'OVERLAP',
          b.id || '(sin id)',
          `Slot ${b.id || '(sin id)'} (${faceB}) se superpone con ${a.id || '(sin id)'}.`,
          { face: faceB, other_slot_id: a.id || '(sin id)' },
        );
      }
    }

    return result;
  }

  window.EditorOffsetVisual.geometryValidation = {
    validateGeometry,
  };
})();
