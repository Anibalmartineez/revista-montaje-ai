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
    constructor(store, refs, geometry, commands, editPolicy) {
      this.store = store;
      this.refs = refs;
      this.geometry = geometry;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.spacePressed = false;
      this.panSession = null;
      this.bound = {
        pointerDown: (event) => this.onPointerDown(event),
        pointerMove: (event) => this.onPointerMove(event),
        pointerUp: (event) => this.onPointerUp(event),
        pointerCancel: (event) => this.cancelPointer(event),
        wheel: (event) => this.onWheel(event),
        keyDown: (event) => this.onKeyDown(event),
        keyUp: (event) => this.onKeyUp(event),
        listClick: (event) => this.onListClick(event),
      };
      refs.canvas.addEventListener("pointerdown", this.bound.pointerDown);
      refs.canvas.addEventListener("pointermove", this.bound.pointerMove);
      refs.canvas.addEventListener("pointerup", this.bound.pointerUp);
      refs.canvas.addEventListener("pointercancel", this.bound.pointerCancel);
      refs.canvas.addEventListener("wheel", this.bound.wheel, { passive: false });
      refs.slotsList.addEventListener("click", this.bound.listClick);
      window.addEventListener("keydown", this.bound.keyDown);
      window.addEventListener("keyup", this.bound.keyUp);
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
      const point = this.domainPoint(event);
      if (!point) {
        return;
      }
      const beforePositions = {};
      for (const slot of this.store.layout.slots) {
        if (this.store.selection.has(slot.id)) {
          beforePositions[slot.id] = { ...slot.geometry.position_mm };
        }
      }
      this.store.beginPointerSession({
        type: "move",
        pointerId: event.pointerId,
        startMm: point,
        beforePositions,
      });
      this.refs.canvas.setPointerCapture(event.pointerId);
      this.refs.canvas.classList.add("is-dragging");
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
      this.store.updatePointerPreview(preview);
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
      const afterPositions = { ...this.store.previewPositions };
      const moved = Object.keys(afterPositions).some((slotId) => {
        const before = session.beforePositions[slotId];
        const after = afterPositions[slotId];
        return before && after
          && (before.x_mm !== after.x_mm || before.y_mm !== after.y_mm);
      });
      this.store.endPointerSession();
      this.refs.canvas.classList.remove("is-dragging");
      this.releasePointer(event.pointerId);
      if (moved) {
        try {
          this.store.executeCommand(
            new this.commands.MoveSlotsCommand(session.beforePositions, afterPositions),
          );
        } catch (error) {
          this.store.setFeedback(error.message);
        }
      }
    }

    cancelPointer(event) {
      if (this.panSession) {
        this.panSession = null;
        this.refs.canvas.classList.remove("is-panning");
      }
      if (this.store.pointerSession) {
        this.store.endPointerSession();
        this.refs.canvas.classList.remove("is-dragging");
      }
      if (event && event.pointerId !== undefined) {
        this.releasePointer(event.pointerId);
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

    onKeyDown(event) {
      const editable = event.target instanceof HTMLElement
        && ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName);
      if (editable) {
        return;
      }
      if (event.code === "Space") {
        this.spacePressed = true;
        this.refs.canvas.classList.add("is-pan-ready");
        event.preventDefault();
        return;
      }
      if (event.key === "Escape") {
        this.cancelPointer();
        return;
      }
      if (this.store.pointerSession || this.panSession) {
        return;
      }
      const commandKey = event.ctrlKey || event.metaKey;
      if (commandKey && event.key.toLowerCase() === "z") {
        event.preventDefault();
        event.shiftKey ? this.store.redo() : this.store.undo();
        return;
      }
      if (commandKey && event.key.toLowerCase() === "y") {
        event.preventDefault();
        this.store.redo();
        return;
      }
      if ((event.key === "Delete" || event.key === "Backspace") && this.store.selection.size) {
        event.preventDefault();
        try {
          this.store.executeCommand(
            new this.commands.DeleteSlotsCommand(this.store.layout, [...this.store.selection]),
          );
        } catch (error) {
          this.store.setFeedback(error.message);
        }
      }
    }

    onKeyUp(event) {
      if (event.code === "Space") {
        this.spacePressed = false;
        this.refs.canvas.classList.remove("is-pan-ready");
      }
    }

    dispose() {
      this.refs.canvas.removeEventListener("pointerdown", this.bound.pointerDown);
      this.refs.canvas.removeEventListener("pointermove", this.bound.pointerMove);
      this.refs.canvas.removeEventListener("pointerup", this.bound.pointerUp);
      this.refs.canvas.removeEventListener("pointercancel", this.bound.pointerCancel);
      this.refs.canvas.removeEventListener("wheel", this.bound.wheel);
      this.refs.slotsList.removeEventListener("click", this.bound.listClick);
      window.removeEventListener("keydown", this.bound.keyDown);
      window.removeEventListener("keyup", this.bound.keyUp);
    }
  }

  return Object.freeze({ CanvasInteractions, pointerToDomain });
});
