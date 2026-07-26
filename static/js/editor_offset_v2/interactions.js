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

  class CanvasInteractions {
    constructor(store, refs, geometry, commands, editPolicy, gestureLifecycle) {
      this.store = store;
      this.refs = refs;
      this.geometry = geometry;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.gestureLifecycle = gestureLifecycle || {};
      this.spacePressed = false;
      this.panSession = null;
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
      const slotId = slotIdFromTarget(event.target);
      if (!slotId) {
        this.store.clearSelection();
        return;
      }
      event.preventDefault();
      const modified = event.shiftKey || event.ctrlKey || event.metaKey;
      if (modified) {
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
        beforePositions,
        selectionBefore,
        previewSlots,
      });
      this.refs.canvas.setPointerCapture(event.pointerId);
      this.refs.canvas.classList.add(
        duplicateMove ? "is-duplicating" : "is-dragging",
      );
    }

    onPointerMove(event) {
      const point = this.domainPoint(event);
      this.store.setCursor(point);
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
      const session = this.store.pointerSession;
      if (!session || session.pointerId !== event.pointerId || !point) {
        return;
      }
      const dx = point.x - session.startMm.x;
      const dy = point.y - session.startMm.y;
      if (!Number.isFinite(dx) || !Number.isFinite(dy)) {
        return;
      }
      const preview = {};
      for (const [slotId, position] of Object.entries(session.beforePositions)) {
        preview[slotId] = {
          x_mm: position.x_mm + dx,
          y_mm: position.y_mm + dy,
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
      const afterPositions = session.type === "duplicate_move"
        ? Object.fromEntries(this.store.previewSlots.map((slot) => [
          slot.id,
          {
            x_mm: slot.geometry.position_mm.x_mm,
            y_mm: slot.geometry.position_mm.y_mm,
          },
        ]))
        : { ...this.store.previewPositions };
      const moved = Object.keys(afterPositions).some((slotId) => {
        const before = session.beforePositions[slotId];
        const after = afterPositions[slotId];
        return before && after
          && (before.x_mm !== after.x_mm || before.y_mm !== after.y_mm);
      });
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
      }
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
        this.store.endPointerSession();
        this.refs.canvas.classList.remove("is-dragging", "is-duplicating");
        if (cancelledDuplicate) {
          this.store.setFeedback("Duplicación por Alt+drag cancelada.");
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
      this.refs.canvas.removeEventListener("pointerdown", this.bound.pointerDown);
      this.refs.canvas.removeEventListener("pointermove", this.bound.pointerMove);
      this.refs.canvas.removeEventListener("pointerup", this.bound.pointerUp);
      this.refs.canvas.removeEventListener("pointercancel", this.bound.pointerCancel);
      this.refs.canvas.removeEventListener("wheel", this.bound.wheel);
      this.refs.slotsList.removeEventListener("click", this.bound.listClick);
    }
  }

  return Object.freeze({ CanvasInteractions, pointerToDomain });
});
