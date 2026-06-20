(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function clearChildren(el) {
    if (!el) return;
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function recalcSheetScale(ctx) {
    const { sheetCanvas, layout, previousScale = 1, minScale = 0.2 } = ctx;
    const sheet = layout?.sheet_mm || [640, 880];
    const maxW = Math.max((sheetCanvas?.clientWidth || 0) - 20, 0);
    const maxH = Math.max(Math.max((sheetCanvas?.clientHeight || 0) - 20, 400), 0);
    if (!maxW || !maxH || !sheet[0] || !sheet[1]) {
      return previousScale;
    }
    const scale = Math.min(maxW / sheet[0], maxH / sheet[1]);
    if (!Number.isFinite(scale) || scale <= 0) {
      return previousScale;
    }
    return Math.max(scale, minScale);
  }

  function applySheetZoom(ctx) {
    const { sheetEl, zoom, zoomLabelEl, updateHandleScale } = ctx;
    if (!sheetEl) return;
    sheetEl.style.transformOrigin = 'top left';
    sheetEl.style.transform = `scale(${zoom})`;
    if (zoomLabelEl) {
      zoomLabelEl.textContent = `${Math.round(zoom * 100)}%`;
    }
    if (typeof updateHandleScale === 'function') {
      updateHandleScale();
    }
  }

  function buildVisibleSlotViewModels(ctx) {
    const {
      layout,
      activeFace,
      selectedSlotId,
      selectedSlotIds,
      geometryValidation,
      getSlotRenderBox,
    } = ctx;
    const face = activeFace || 'front';
    const selectedIds = selectedSlotIds || new Set();

    return (layout?.slots || [])
      .filter((slot) => (slot.face || 'front') === face)
      .map((slot) => {
        const classes = ['slot'];
        if (slot.locked) classes.push('locked');

        const geometryIssue = geometryValidation?.bySlot?.[slot.id];
        if (geometryIssue?.level === 'error') {
          classes.push('geometry-error');
        } else if (geometryIssue?.level === 'warning') {
          classes.push('geometry-warning');
        }

        if (selectedIds.has(slot.id) || selectedSlotId === slot.id) {
          classes.push('selected');
        }

        const title = geometryIssue?.issues?.length
          ? geometryIssue.issues.map((issue) => issue.message).join('\n')
          : '';
        const renderBox = getSlotRenderBox(slot);

        return {
          slot,
          classes,
          title,
          renderBox,
        };
      });
  }

  function renderCtpGuide(ctx) {
    const { sheetEl, ctp, activeFace, mmToPx } = ctx;
    if (!ctp || !ctp.show_guide || !ctp.enabled) return;
    if ((activeFace || 'front') !== 'front') return;
    if (!sheetEl) return;

    const gripper = Number(ctp.gripper_mm || 0);
    const guideEl = document.createElement('div');
    guideEl.className = 'ctp-guide';
    guideEl.style.height = `${mmToPx(Math.max(0, gripper))}px`;
    sheetEl.appendChild(guideEl);
  }

  function renderGeometryValidationPanel(ctx) {
    const { validation, activeFace, summaryEl, listEl } = ctx;
    if (!summaryEl || !listEl) return;

    const safeValidation = validation || { errors: [], warnings: [], bySlot: {} };
    const face = activeFace || 'front';
    const visibleErrors = safeValidation.errors.filter((issue) => !issue.face || issue.face === face);
    const visibleWarnings = safeValidation.warnings.filter((issue) => !issue.face || issue.face === face);
    const visibleIssues = visibleErrors.concat(visibleWarnings);

    if (!visibleIssues.length) {
      summaryEl.textContent = `Cara ${face}: sin problemas geométricos`;
      listEl.innerHTML = '<div class="geometry-validation-empty">No se detectaron conflictos geométricos en la cara visible.</div>';
      return;
    }

    summaryEl.textContent = `Cara ${face}: ${visibleErrors.length} errores, ${visibleWarnings.length} advertencias`;
    clearChildren(listEl);

    visibleIssues.slice(0, 12).forEach((issue) => {
      const item = document.createElement('div');
      const isError = visibleErrors.includes(issue);
      item.className = `geometry-validation-item ${isError ? 'error' : 'warning'}`;
      item.innerHTML = `<strong>${issue.type}</strong>${issue.message}`;
      listEl.appendChild(item);
    });

    if (visibleIssues.length > 12) {
      const more = document.createElement('div');
      more.className = 'geometry-validation-empty';
      more.textContent = `Hay ${visibleIssues.length - 12} problemas adicionales en esta cara.`;
      listEl.appendChild(more);
    }
  }

  function renderDistanceIndicator(ctx) {
    const { sheetEl, distanceIndicator, activeFace, mmToPx } = ctx;
    if (!distanceIndicator?.active) return;
    if ((distanceIndicator.face || 'front') !== (activeFace || 'front')) return;

    const indicator = document.createElement('div');
    indicator.className = 'distance-indicator';
    indicator.style.left = `${mmToPx(distanceIndicator.x_mm)}px`;
    indicator.style.bottom = `${mmToPx(distanceIndicator.y_mm)}px`;

    distanceIndicator.items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'distance-indicator-row';
      row.innerHTML = `<span class="distance-indicator-label">${item.label}</span><strong>${item.value}</strong>`;
      indicator.appendChild(row);
    });

    sheetEl.appendChild(indicator);
  }

  function renderSheetSurface(ctx) {
    const {
      sheetEl,
      layout,
      activeFace,
      selectedSlot,
      selectedSlots,
      geometryValidation,
      distanceIndicator,
      mmToPx,
      getSlotRenderBox,
      attachSlotHandlers,
      updateHandleScale,
      zoom,
      zoomLabelEl,
      geometryValidationSummaryEl,
      geometryValidationListEl,
    } = ctx;
    if (!sheetEl) return;

    const [sheetW, sheetH] = layout.sheet_mm;
    sheetEl.style.width = `${mmToPx(sheetW)}px`;
    sheetEl.style.height = `${mmToPx(sheetH)}px`;
    clearChildren(sheetEl);

    renderCtpGuide({
      sheetEl,
      ctp: layout?.ctp,
      activeFace,
      mmToPx,
    });

    const slotViewModels = buildVisibleSlotViewModels({
      layout,
      activeFace,
      selectedSlotId: selectedSlot?.id || null,
      selectedSlotIds: selectedSlots,
      geometryValidation,
      getSlotRenderBox,
    });

    slotViewModels.forEach((viewModel) => {
      const { slot, renderBox } = viewModel;
      const slotEl = document.createElement('div');
      slotEl.className = viewModel.classes.join(' ');
      if (viewModel.title) {
        slotEl.title = viewModel.title;
      }
      slotEl.dataset.slotId = slot.id;
      slotEl.style.left = `${mmToPx(renderBox.x)}px`;
      slotEl.style.bottom = `${mmToPx(renderBox.y)}px`;
      slotEl.style.width = `${mmToPx(renderBox.w)}px`;
      slotEl.style.height = `${mmToPx(renderBox.h)}px`;
      slotEl.style.transformOrigin = 'center';
      slotEl.style.setProperty('--slot-rotation-deg', `${renderBox.rotation || 0}deg`);
      if (renderBox.rotation) {
        slotEl.dataset.rotation = String(renderBox.rotation);
      }

      if (typeof attachSlotHandlers === 'function') {
        attachSlotHandlers(slotEl, slot);
      }
      sheetEl.appendChild(slotEl);
    });

    applySheetZoom({
      sheetEl,
      zoom,
      zoomLabelEl,
      updateHandleScale,
    });
    renderDistanceIndicator({
      sheetEl,
      distanceIndicator,
      activeFace,
      mmToPx,
    });
    renderGeometryValidationPanel({
      validation: geometryValidation,
      activeFace,
      summaryEl: geometryValidationSummaryEl,
      listEl: geometryValidationListEl,
    });
  }

  window.EditorOffsetVisual.rendererCanvas = {
    recalcSheetScale,
    applySheetZoom,
    buildVisibleSlotViewModels,
    renderSheetSurface,
    renderCtpGuide,
    renderGeometryValidationPanel,
    renderDistanceIndicator,
  };
})();
