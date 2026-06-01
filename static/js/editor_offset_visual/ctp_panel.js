(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function readParamsFromUI(ctx) {
    const { state, ensureCtpDefaults } = ctx;
    if (!state.layout) return;
    state.layout.ctp = state.layout.ctp || {};
    ensureCtpDefaults();
    const byId = window.EditorOffsetVisual.domRefs.byId;
    const gripperInput = byId('ctp-gripper-mm');
    const showGuideInput = byId('ctp-show-guide');
    const lockAfterInput = byId('ctp-lock-after');
    const marksRegistroInput = byId('ctp-marks-registro');
    const stripInput = byId('ctp-strip-cmyk');
    const jobNameInput = byId('ctp-job-name');
    const clientInput = byId('ctp-client');
    const notesInput = byId('ctp-notes');
    const autoCmykInput = byId('ctp-auto-cmyk');
    const extraTextInput = byId('ctp-extra-text');

    const gripperVal = gripperInput ? parseFloat(gripperInput.value || '0') : state.layout.ctp.gripper_mm;
    state.layout.ctp.gripper_mm = Number.isFinite(gripperVal) ? gripperVal : state.layout.ctp.gripper_mm || 0;
    state.layout.ctp.show_guide = !!showGuideInput?.checked;
    state.layout.ctp.lock_after = lockAfterInput?.checked !== false;

    state.layout.ctp.marks = state.layout.ctp.marks || {};
    state.layout.ctp.marks.registro = !!marksRegistroInput?.checked;
    state.layout.ctp.marks.control_strip = !!stripInput?.checked;

    state.layout.ctp.technical_text = state.layout.ctp.technical_text || {};
    const text = state.layout.ctp.technical_text;
    text.job_name = jobNameInput ? jobNameInput.value || '' : text.job_name || '';
    text.client = clientInput ? clientInput.value || '' : text.client || '';
    text.notes = notesInput ? notesInput.value || '' : text.notes || '';
    text.auto_cmyk = autoCmykInput ? !!autoCmykInput.checked : text.auto_cmyk !== false;
    text.extra_text = extraTextInput ? extraTextInput.value || '' : text.extra_text || '';
  }

  function syncUIFromLayout(ctx) {
    const { state, ensureCtpDefaults } = ctx;
    ensureCtpDefaults();
    const byId = window.EditorOffsetVisual.domRefs.byId;
    const ctp = state.layout?.ctp || {};
    const text = ctp.technical_text || {};
    const marks = ctp.marks || {};
    const gripperInput = byId('ctp-gripper-mm');
    const showGuideInput = byId('ctp-show-guide');
    const lockAfterInput = byId('ctp-lock-after');
    const marksRegistroInput = byId('ctp-marks-registro');
    const stripInput = byId('ctp-strip-cmyk');
    const jobNameInput = byId('ctp-job-name');
    const clientInput = byId('ctp-client');
    const notesInput = byId('ctp-notes');
    const autoCmykInput = byId('ctp-auto-cmyk');
    const extraTextInput = byId('ctp-extra-text');
    if (gripperInput) gripperInput.value = ctp.gripper_mm ?? 40;
    if (showGuideInput) showGuideInput.checked = !!ctp.show_guide;
    if (lockAfterInput) lockAfterInput.checked = ctp.lock_after !== false;
    if (marksRegistroInput) marksRegistroInput.checked = !!marks.registro;
    if (stripInput) stripInput.checked = !!marks.control_strip;
    if (jobNameInput) jobNameInput.value = text.job_name ?? '';
    if (clientInput) clientInput.value = text.client ?? '';
    if (notesInput) notesInput.value = text.notes ?? '';
    if (autoCmykInput) autoCmykInput.checked = text.auto_cmyk !== false;
    if (extraTextInput) extraTextInput.value = text.extra_text ?? '';
  }

  function computeFrontBlockBBox(layout) {
    const frontSlots = (layout.slots || []).filter((slot) => (slot.face || 'front') === 'front');
    if (!frontSlots.length) return null;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    frontSlots.forEach((slot) => {
      const baseW = Number(slot.w_mm || 0);
      const baseH = Number(slot.h_mm || 0);
      const x0 = Number(slot.x_mm || 0);
      const y0 = Number(slot.y_mm || 0);
      const x1 = x0 + baseW;
      const y1 = y0 + baseH;
      minX = Math.min(minX, x0);
      maxX = Math.max(maxX, x1);
      minY = Math.min(minY, y0);
      maxY = Math.max(maxY, y1);
    });

    if (!isFinite(minX) || !isFinite(minY)) return null;
    return { minX, maxX, minY, maxY };
  }

  function applyAlignment(ctx) {
    const { state, renderSheet, renderSlotForm, pushHistory } = ctx;
    readParamsFromUI(ctx);
    const ctp = state.layout?.ctp;
    if (!ctp) return;
    const bbox = computeFrontBlockBBox(state.layout);
    if (!bbox) {
      alert('No hay slots en el frente para aplicar ProducciÃƒÂ³n / CTP.');
      return;
    }

    const sheetW = (state.layout.sheet_mm && state.layout.sheet_mm[0]) || 0;
    const blockWidth = bbox.maxX - bbox.minX;
    const desiredMinX = (sheetW - blockWidth) / 2;
    const deltaX = desiredMinX - bbox.minX;
    const desiredMinY = Number(ctp.gripper_mm || 0);
    const deltaY = desiredMinY - bbox.minY;

    state.layout.slots.forEach((slot) => {
      if ((slot.face || 'front') !== 'front') return;
      slot.x_mm = (slot.x_mm || 0) + deltaX;
      slot.y_mm = (slot.y_mm || 0) + deltaY;
      if (ctp.lock_after !== false) {
        slot.locked = true;
      }
    });

    ctp.enabled = true;
    renderSheet();
    renderSlotForm();
    pushHistory();
  }

  function disableAdjustments(ctx) {
    const { state, renderSheet, renderSlotForm, pushHistory } = ctx;
    if (!state.layout?.ctp) return;
    state.layout.ctp.enabled = false;
    state.layout.ctp.show_guide = false;
    (state.layout.slots || []).forEach((slot) => {
      slot.locked = false;
    });
    syncUIFromLayout(ctx);
    renderSheet();
    renderSlotForm();
    pushHistory();
  }

  window.EditorOffsetVisual.ctpPanel = {
    readParamsFromUI,
    syncUIFromLayout,
    computeFrontBlockBBox,
    applyAlignment,
    disableAdjustments,
  };
})();
