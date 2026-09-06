(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.Interactions = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function pointerToDomain(svg, event, sheetHeight, geometry) {
    const matrix = svg.getScreenCTM();
    if (!matrix) {
      return null;
    }
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const local = point.matrixTransform(matrix.inverse());
    const x = geometry.svgToMmX(local.x);
    const y = geometry.svgToMmY(local.y, sheetHeight);
    return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
  }

  function slotIdFromTarget(target) {
    const element = target instanceof Element ? target.closest("[data-slot-id]") : null;
    return element ? element.dataset.slotId : null;
  }

  function dataFromTarget(target, selector, key) {
    const element = target instanceof Element ? target.closest(selector) : null;
    return element ? element.dataset[key] : null;
  }

  function screenPixelsToDomain(svg, pixels) {
    const matrix = svg.getScreenCTM();
    if (!matrix) return null;
    const inverse = matrix.inverse();
    const origin = svg.createSVGPoint();
    origin.x = 0;
    origin.y = 0;
    const horizontal = svg.createSVGPoint();
    horizontal.x = pixels;
    horizontal.y = 0;
    const vertical = svg.createSVGPoint();
    vertical.x = 0;
    vertical.y = pixels;
    const start = origin.matrixTransform(inverse);
    const x = horizontal.matrixTransform(inverse);
    const y = vertical.matrixTransform(inverse);
    return {
      x: Math.abs(x.x - start.x),
      y: Math.abs(y.y - start.y),
    };
  }

  class CanvasInteractions {
    constructor(store, refs, geometry, commands, editPolicy, gestureLifecycle) {
      this.store = store;
      this.refs = refs;
      this.geometry = geometry;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.gestureLifecycle = gestureLifecycle || {};
      this.advancedSelection = this.gestureLifecycle.advancedSelection || null;
      this.snapEngine = this.gestureLifecycle.snapEngine || null;
      this.precisionTools = this.gestureLifecycle.precisionTools || null;
      this.actionIds = this.gestureLifecycle.actionIds || null;
      this.runAction = this.gestureLifecycle.runAction || null;
      this.measurementTargets = null;
      this.spacePressed = false;
      this.panSession = null;
      this.marqueeFrame = null;
      this.pendingMarqueeRect = null;
      this.bound = {
        pointerDown: (event) => this.onPointerDown(event),
        pointerMove: (event) => this.onPointerMove(event),
        pointerUp: (event) => this.onPointerUp(event),
        pointerCancel: (event) => this.cancelPointer(event),
        wheel: (event) => this.onWheel(event),
        listClick: (event) => this.onListClick(event),
      };
      refs.canvas.addEventListener("pointerdown", this.bound.pointerDown);
      refs.canvas.addEventListener("pointermove", this.bound.pointerMove);
      refs.canvas.addEventListener("pointerup", this.bound.pointerUp);
      refs.canvas.addEventListener("pointercancel", this.bound.pointerCancel);
      refs.canvas.addEventListener("wheel", this.bound.wheel, { passive: false });
      refs.slotsList.addEventListener("click", this.bound.listClick);
    }

    domainPoint(event) {
      return pointerToDomain(
        this.refs.canvas,
        event,
        this.store.layout.sheet.size_mm.height,
        this.geometry,
      );
    }

    snapThresholdMm() {
      const threshold = this.store.precisionTools.snapThresholdPx;
      return screenPixelsToDomain(this.refs.canvas, threshold) || { x: threshold, y: threshold };
    }

    snapSources() {
      const precision = this.store.precisionTools;
      return {
        guides: precision.snapToGuides && precision.guidesVisible,
        slots: precision.snapToSlots,
        sheet: precision.snapToSheet,
        printable: precision.snapToPrintable,
      };
    }

    captureSnapTargets(movingIds) {
      if (!this.snapEngine) return null;
      return this.snapEngine.captureTargets({
        layout: this.store.layout,
        activeFace: this.store.activeFace,
        hiddenSlotIds: this.store.advancedSelection.hiddenSlotIds,
        movingIds: movingIds || [],
        guides: this.store.precisionTools.guides,
        geometry: this.geometry,
        reference: this.store.arrangement.geometryReference,
        sources: this.snapSources(),
      });
    }

    snappedMeasurementPoint(point) {
      if (!this.store.precisionTools.snapEnabled || !this.snapEngine) {
        return { point, guides: [] };
      }
      const targets = this.measurementTargets || this.captureSnapTargets([]);
      return this.snapEngine.snapPoint({
        point,
        targets,
        thresholdMm: this.snapThresholdMm(),
        enabled: true,
      });
    }

    beginGuidePointer(event, axis, guideId) {
      const point = this.domainPoint(event);
      if (!point) return false;
      const existing = guideId
        ? this.store.precisionTools.guides.find((guide) => guide.id === guideId) : null;
      if (guideId && !existing) return false;
      const position = existing?.position_mm ?? (axis === "x" ? point.x : point.y);
      this.store.setActiveGuide(guideId || null);
      this.store.beginPointerSession({
        type: existing ? "guide_move" : "guide_create",
        pointerId: event.pointerId,
        axis,
        guideId: existing?.id || null,
        originalPosition: existing?.position_mm ?? null,
        startClient: { x: event.clientX, y: event.clientY },
      });
      this.store.setGuideDraft({
        id: existing?.id || null,
        axis,
        position_mm: position,
      });
      this.refs.canvas.setPointerCapture(event.pointerId);
      this.refs.canvas.classList.add("is-guide-dragging");
      return true;
    }

    guideDropIsValid(event, axis) {
      const rect = this.refs.canvas.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right
          || event.clientY < rect.top || event.clientY > rect.bottom) return false;
      const rulerBand = 24;
      return axis === "x"
        ? event.clientY > rect.top + rulerBand
        : event.clientX > rect.left + rulerBand;
    }

    measurementClick(point) {
      if (!this.store.precisionTools.measurementDraft) {
        this.measurementTargets = this.captureSnapTargets([]);
        const snapped = this.snappedMeasurementPoint(point);
        this.store.startMeasurement(snapped.point);
        this.store.setSnapPreview({ guides: snapped.guides, mode: "measurement" });
        this.store.setFeedback("Primer punto de medición fijado.", "measurement");
        return;
      }
      const snapped = this.snappedMeasurementPoint(point);
      const result = this.precisionTools.measurement(
        this.store.precisionTools.measurementDraft.start,
        snapped.point,
      );
      this.store.finishMeasurement(result);
      this.measurementTargets = null;
      this.store.setFeedback(
        `Medición: ΔX ${result.deltaX.toFixed(3)} · ΔY ${result.deltaY.toFixed(3)} · ${result.distance.toFixed(3)} mm.`,
        "measurement",
      );
    }

    onPointerDown(event) {
      this.gestureLifecycle.beforePointerAction?.();
      if (event.button === 1 || this.spacePressed) {
        event.preventDefault();
        this.panSession = {
          pointerId: event.pointerId,
          clientX: event.clientX,
          clientY: event.clientY,
          pan: { ...this.store.pan },
        };
        this.refs.canvas.setPointerCapture(event.pointerId);
        this.refs.canvas.classList.add("is-panning");
        return;
      }
      if (event.button !== 0) {
        return;
      }
      const guideId = dataFromTarget(event.target, "[data-guide-id]", "guideId");
      if (guideId && this.store.precisionTools.guidesVisible) {
        event.preventDefault();
        const guide = this.store.precisionTools.guides.find((item) => item.id === guideId);
        if (guide) this.beginGuidePointer(event, guide.axis, guide.id);
        return;
      }
      const rulerAxis = dataFromTarget(event.target, "[data-ruler-axis]", "rulerAxis");
      if (rulerAxis && this.store.precisionTools.rulersVisible) {
        event.preventDefault();
        this.beginGuidePointer(event, rulerAxis, null);
        return;
      }
      if (this.store.precisionTools.measurementMode) {
        const point = this.domainPoint(event);
        if (!point) return;
        event.preventDefault();
        this.measurementClick(point);
        return;
      }
      const slotId = slotIdFromTarget(event.target);
      if (!slotId) {
        if (!this.advancedSelection) {
          this.store.clearSelection();
          return;
        }
        const point = this.domainPoint(event);
        if (!point) return;
        event.preventDefault();
        this.store.beginPointerSession({
          type: "marquee",
          pointerId: event.pointerId,
          startMm: point,
          startClient: { x: event.clientX, y: event.clientY },
          selectionBefore: [...this.store.selection],
          selectionMode: this.advancedSelection.selectionModeFromModifiers(event, false),
          marqueeMode: this.store.advancedSelection.marqueeMode,
          geometryReference: this.store.arrangement.geometryReference,
          candidates: this.advancedSelection.captureMarqueeCandidates(
            this.store.layout,
            this.store.activeFace,
            this.store.advancedSelection.hiddenSlotIds,
            this.geometry,
            this.store.arrangement.geometryReference,
          ),
          thresholdExceeded: false,
        });
        this.refs.canvas.setPointerCapture(event.pointerId);
        this.refs.canvas.classList.add("is-marquee-selecting");
        return;
      }
      event.preventDefault();
      const modified = event.shiftKey || event.ctrlKey || event.metaKey;
      if (event.altKey && event.shiftKey) {
        if (!this.store.selection.has(slotId)) this.store.setSelection([slotId], "add");
      } else if (modified) {
        this.store.setSelection([slotId], "toggle");
      } else if (!this.store.selection.has(slotId)) {
        this.store.setSelection([slotId], "replace");
      }
      if (!this.store.selection.has(slotId)) {
        return;
      }
      const duplicateMove = Boolean(event.altKey);
      if (!duplicateMove) {
        try {
          this.editPolicy.assertCan(
            this.store.layout,
            [...this.store.selection],
            "move",
          );
        } catch (error) {
          this.store.setFeedback(error.message);
          return;
        }
      }
      const point = this.domainPoint(event);
      if (!point) {
        return;
      }
      const selectionBefore = [...this.store.selection];
      const previewSlots = duplicateMove
        ? this.commands.prepareDuplicateSlots(
          this.store.layout,
          selectionBefore,
          { x_mm: 0, y_mm: 0 },
        )
        : [];
      const positionSlots = duplicateMove
        ? previewSlots
        : this.store.layout.slots.filter((slot) => this.store.selection.has(slot.id));
      const beforePositions = Object.fromEntries(
        positionSlots.map((slot) => [slot.id, { ...slot.geometry.position_mm }]),
      );
      this.store.beginPointerSession({
        type: duplicateMove ? "duplicate_move" : "move",
        pointerId: event.pointerId,
        startMm: point,
        startClient: { x: event.clientX, y: event.clientY },
        beforePositions,
        selectionBefore,
        previewSlots,
        targetSlotId: slotId,
        cycleAdditive: Boolean(event.shiftKey),
        snapTargets: this.captureSnapTargets(selectionBefore),
        snapSourceBounds: this.snapEngine
          ? this.snapEngine.groupBounds(
            positionSlots,
            this.geometry,
            this.store.arrangement.geometryReference,
          )
          : null,
      });
      this.refs.canvas.setPointerCapture(event.pointerId);
      this.refs.canvas.classList.add(
        duplicateMove ? "is-duplicating" : "is-dragging",
      );
    }

    onPointerMove(event) {
      const point = this.domainPoint(event);
      this.store.setCursor(point);
      const cyclePoint = this.store.advancedSelection?.cycle?.point;
      if (point && cyclePoint && Math.hypot(point.x - cyclePoint.x, point.y - cyclePoint.y)
          > (this.advancedSelection?.CYCLE_POINT_TOLERANCE_MM || 0.75)) {
        this.store.clearSelectionCycle();
      }
      if (this.panSession && this.panSession.pointerId === event.pointerId) {
        const rect = this.refs.canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return;
        }
        const sheet = this.store.layout.sheet.size_mm;
        const unitsPerPixelX = (sheet.width + 56) / (this.store.zoom * rect.width);
        const unitsPerPixelY = (sheet.height + 56) / (this.store.zoom * rect.height);
        this.store.setPan({
          x: this.panSession.pan.x
            + (event.clientX - this.panSession.clientX) * unitsPerPixelX,
          y: this.panSession.pan.y
            - (event.clientY - this.panSession.clientY) * unitsPerPixelY,
        });
        return;
      }
      if (point && this.store.precisionTools.measurementMode
          && this.store.precisionTools.measurementDraft && !this.store.pointerSession) {
        const snapped = this.snappedMeasurementPoint(point);
        this.store.updateMeasurement(snapped.point);
        this.store.setSnapPreview({ guides: snapped.guides, mode: "measurement" });
        return;
      }
      const session = this.store.pointerSession;
      if (!session || session.pointerId !== event.pointerId || !point) {
        return;
      }
      if (session.type === "marquee") {
        const distance = Math.hypot(
          event.clientX - session.startClient.x,
          event.clientY - session.startClient.y,
        );
        if (distance < this.advancedSelection.MARQUEE_DRAG_THRESHOLD_PX) return;
        session.thresholdExceeded = true;
        this.scheduleMarqueeRect(
          this.advancedSelection.rectangleFromPoints(session.startMm, point),
        );
        return;
      }
      if (session.type === "guide_create" || session.type === "guide_move") {
        this.store.setGuideDraft({
          id: session.guideId,
          axis: session.axis,
          position_mm: session.axis === "x" ? point.x : point.y,
        });
        return;
      }
      const dx = point.x - session.startMm.x;
      const dy = point.y - session.startMm.y;
      if (!Number.isFinite(dx) || !Number.isFinite(dy)) {
        return;
      }
      const snapped = this.snapEngine && session.snapSourceBounds
        ? this.snapEngine.snapTranslation({
          sourceBounds: session.snapSourceBounds,
          rawDx: dx,
          rawDy: dy,
          targets: session.snapTargets,
          thresholdMm: this.snapThresholdMm(),
          enabled: this.store.precisionTools.snapEnabled,
        })
        : { dx, dy, guides: [] };
      this.store.setSnapPreview({
        guides: this.store.precisionTools.smartGuidesVisible ? snapped.guides : [],
        mode: session.type,
      });
      const preview = {};
      for (const [slotId, position] of Object.entries(session.beforePositions)) {
        preview[slotId] = {
          x_mm: position.x_mm + snapped.dx,
          y_mm: position.y_mm + snapped.dy,
        };
      }
      if (session.type === "duplicate_move") {
        const previewSlots = session.previewSlots.map((slot) => ({
          ...slot,
          geometry: {
            ...slot.geometry,
            position_mm: {
              ...slot.geometry.position_mm,
              ...preview[slot.id],
            },
          },
        }));
        this.store.updatePointerPreviewSlots(previewSlots);
      } else {
        this.store.updatePointerPreview(preview);
      }
    }

    onPointerUp(event) {
      if (this.panSession && this.panSession.pointerId === event.pointerId) {
        this.panSession = null;
        this.refs.canvas.classList.remove("is-panning");
        this.releasePointer(event.pointerId);
        return;
      }
      const session = this.store.pointerSession;
      if (!session || session.pointerId !== event.pointerId) {
        return;
      }
      if (session.type === "guide_create" || session.type === "guide_move") {
        const draft = this.store.precisionTools.guideDraft
          ? { ...this.store.precisionTools.guideDraft } : null;
        const validDrop = draft && this.guideDropIsValid(event, session.axis);
        const rect = this.refs.canvas.getBoundingClientRect();
        const outsideCanvas = event.clientX < rect.left || event.clientX > rect.right
          || event.clientY < rect.top || event.clientY > rect.bottom;
        this.store.endPointerSession();
        this.refs.canvas.classList.remove("is-guide-dragging");
        this.releasePointer(event.pointerId);
        if (validDrop) {
          this.runAction(
            session.type === "guide_create"
              ? this.actionIds.PRECISION_GUIDE_CREATE
              : this.actionIds.PRECISION_GUIDE_UPDATE,
            session.type === "guide_create"
              ? { axis: draft.axis, position_mm: draft.position_mm }
              : { id: session.guideId, position_mm: draft.position_mm },
          );
        } else if (session.type === "guide_move" && outsideCanvas) {
          this.runAction(this.actionIds.PRECISION_GUIDE_DELETE, { id: session.guideId });
          this.store.setFeedback("Guía eliminada al soltar fuera del canvas.");
        } else {
          this.store.setFeedback("Creación o movimiento de guía cancelado.");
        }
        return;
      }
      if (session.type === "marquee") {
        const point = this.domainPoint(event);
        const distance = Math.hypot(
          event.clientX - session.startClient.x,
          event.clientY - session.startClient.y,
        );
        const dragged = Boolean(point)
          && distance >= this.advancedSelection.MARQUEE_DRAG_THRESHOLD_PX;
        const rectangle = dragged
          ? this.advancedSelection.rectangleFromPoints(session.startMm, point)
          : null;
        this.cancelMarqueeFrame();
        this.store.clearMarqueeRect(false);
        this.store.endPointerSession();
        this.refs.canvas.classList.remove("is-marquee-selecting");
        this.releasePointer(event.pointerId);
        if (rectangle) {
          const matched = this.advancedSelection.matchingMarqueeIds(
            session.candidates,
            rectangle,
            session.marqueeMode,
          );
          const finalIds = this.advancedSelection.applySelectionMode(
            session.selectionBefore,
            matched,
            session.selectionMode,
          );
          this.store.setSelection(finalIds, "replace");
          this.store.setFeedback(
            `Marquee ${session.marqueeMode === "contain" ? "dentro completamente" : "tocar/intersectar"}: ${matched.length} coincidencia(s), ${finalIds.length} seleccionada(s).`,
          );
        } else if (session.selectionMode === "replace") {
          this.store.clearSelection();
        }
        return;
      }
      const afterPositions = session.type === "duplicate_move"
        ? Object.fromEntries(this.store.previewSlots.map((slot) => [
          slot.id,
          {
            x_mm: slot.geometry.position_mm.x_mm,
            y_mm: slot.geometry.position_mm.y_mm,
          },
        ]))
        : { ...this.store.previewPositions };
      const movedGeometry = Object.keys(afterPositions).some((slotId) => {
        const before = session.beforePositions[slotId];
        const after = afterPositions[slotId];
        return before && after
          && (before.x_mm !== after.x_mm || before.y_mm !== after.y_mm);
      });
      const moved = session.type === "duplicate_move"
        ? movedGeometry && Math.hypot(
          event.clientX - session.startClient.x,
          event.clientY - session.startClient.y,
        ) >= (this.advancedSelection?.MARQUEE_DRAG_THRESHOLD_PX || 4)
        : movedGeometry;
      const preparedSlots = session.type === "duplicate_move"
        ? structuredClone(this.store.previewSlots)
        : null;
      this.store.endPointerSession();
      this.refs.canvas.classList.remove("is-dragging", "is-duplicating");
      this.releasePointer(event.pointerId);
      if (moved) {
        try {
          const command = session.type === "duplicate_move"
            ? new this.commands.DuplicateSlotsCommand(
              this.store.layout,
              session.selectionBefore,
              {
                description: "Duplicar mediante Alt+drag",
                preparedSlots,
                selectionBefore: session.selectionBefore,
              },
            )
            : new this.commands.MoveSlotsCommand(session.beforePositions, afterPositions);
          this.store.executeCommand(command);
          if (session.type === "duplicate_move") {
            this.store.setFeedback(`Copias creadas por Alt+drag: ${command.affectedIds.join(", ")}.`);
          }
        } catch (error) {
          this.store.setFeedback(error.message);
        }
      } else if (session.type === "duplicate_move" && this.runAction && this.actionIds) {
        const point = this.domainPoint(event) || session.startMm;
        this.runAction(this.actionIds.CYCLE_AT_POINT, {
          point,
          currentSlotId: session.targetSlotId,
          additive: session.cycleAdditive,
        });
      }
    }

    scheduleMarqueeRect(rectangle) {
      this.pendingMarqueeRect = rectangle;
      if (this.marqueeFrame !== null) return;
      const requestFrame = typeof requestAnimationFrame === "function"
        ? requestAnimationFrame
        : (callback) => setTimeout(callback, 0);
      this.marqueeFrame = requestFrame(() => {
        this.marqueeFrame = null;
        const next = this.pendingMarqueeRect;
        this.pendingMarqueeRect = null;
        if (next && this.store.pointerSession?.type === "marquee") {
          this.store.setMarqueeRect(next);
        }
      });
    }

    cancelMarqueeFrame() {
      if (this.marqueeFrame !== null) {
        if (typeof cancelAnimationFrame === "function") cancelAnimationFrame(this.marqueeFrame);
        else clearTimeout(this.marqueeFrame);
      }
      this.marqueeFrame = null;
      this.pendingMarqueeRect = null;
    }

    cancelPointer(event) {
      const capturedPointerIds = [];
      if (this.panSession) {
        capturedPointerIds.push(this.panSession.pointerId);
        this.panSession = null;
        this.refs.canvas.classList.remove("is-panning");
      }
      if (this.store.pointerSession) {
        capturedPointerIds.push(this.store.pointerSession.pointerId);
        const cancelledDuplicate = this.store.pointerSession.type === "duplicate_move";
        const cancelledMarquee = this.store.pointerSession.type === "marquee";
        const cancelledGuide = ["guide_create", "guide_move"].includes(
          this.store.pointerSession.type,
        );
        this.cancelMarqueeFrame();
        this.store.clearMarqueeRect(false);
        this.store.endPointerSession();
        this.refs.canvas.classList.remove(
          "is-dragging",
          "is-duplicating",
          "is-marquee-selecting",
          "is-guide-dragging",
        );
        if (cancelledDuplicate) {
          this.store.setFeedback("Duplicación por Alt+drag cancelada.");
        } else if (cancelledMarquee) {
          this.store.setFeedback("Selección rectangular cancelada.");
        } else if (cancelledGuide) {
          this.store.setFeedback("Guía temporal cancelada.");
        }
      }
      if (event && event.pointerId !== undefined) {
        capturedPointerIds.push(event.pointerId);
      }
      for (const pointerId of new Set(capturedPointerIds)) {
        this.releasePointer(pointerId);
      }
    }

    releasePointer(pointerId) {
      if (this.refs.canvas.hasPointerCapture(pointerId)) {
        this.refs.canvas.releasePointerCapture(pointerId);
      }
    }

    onWheel(event) {
      event.preventDefault();
      const factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
      this.store.setZoom(this.geometry.clampZoom(this.store.zoom * factor));
    }

    onListClick(event) {
      const button = event.target.closest("button[data-slot-id]");
      if (!button) {
        return;
      }
      const mode = event.shiftKey || event.ctrlKey || event.metaKey ? "toggle" : "replace";
      this.store.setSelection([button.dataset.slotId], mode);
    }

    setSpacePressed(pressed) {
      this.spacePressed = Boolean(pressed);
      this.refs.canvas.classList.toggle("is-pan-ready", this.spacePressed);
    }

    hasPanSession() {
      return Boolean(this.panSession);
    }

    hasPointerActivity() {
      return Boolean(this.panSession || this.store.pointerSession);
    }

    dispose() {
      this.cancelMarqueeFrame();
      this.refs.canvas.removeEventListener("pointerdown", this.bound.pointerDown);
      this.refs.canvas.removeEventListener("pointermove", this.bound.pointerMove);
      this.refs.canvas.removeEventListener("pointerup", this.bound.pointerUp);
      this.refs.canvas.removeEventListener("pointercancel", this.bound.pointerCancel);
      this.refs.canvas.removeEventListener("wheel", this.bound.wheel);
      this.refs.slotsList.removeEventListener("click", this.bound.listClick);
    }
  }

  return Object.freeze({ CanvasInteractions, pointerToDomain, screenPixelsToDomain });
});
