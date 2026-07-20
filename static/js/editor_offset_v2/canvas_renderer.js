(function (root, factory) {
  "use strict";
  const sourceSemantics = typeof module === "object" && module.exports
    ? require("./source_semantics.js")
    : root.EditorOffsetV2?.SourceSemantics;
  const editPolicy = typeof module === "object" && module.exports
    ? require("./edit_policy.js")
    : root.EditorOffsetV2?.EditPolicy;
  const api = factory(sourceSemantics, editPolicy);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.CanvasRenderer = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (SourceSemantics, EditPolicy) {
  "use strict";

  if (!SourceSemantics || !EditPolicy) throw new Error("Editor V2 renderer policies are required");

  const SVG_NS = "http://www.w3.org/2000/svg";
  const SLOT_LABEL_BASE_FONT_MM = 4;
  const SLOT_LABEL_MIN_PHYSICAL_MM = 6;
  const SLOT_LABEL_MIN_VISIBLE_MM = 10;
  const SOURCE_TRIM_VISUAL_TOLERANCE_MM = 0.01;

  function svgElement(name, attributes, text) {
    const element = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attributes || {})) {
      element.setAttribute(key, String(value));
    }
    if (text !== undefined) {
      element.textContent = text;
    }
    return element;
  }

  function shortSlotLabel(slot, ordinal) {
    const suffix = String(slot?.id || "").match(/_(\d+)$/);
    const number = suffix ? Number(suffix[1]) : Number(ordinal);
    return `#${Number.isInteger(number) && number > 0 ? number : ordinal}`;
  }

  function slotLabelPresentation(slot, ordinal, zoom, enabled) {
    const width = Number(slot?.geometry?.trim_size_mm?.width);
    const height = Number(slot?.geometry?.trim_size_mm?.height);
    const safeZoom = Number.isFinite(zoom) && zoom > 0 ? zoom : 1;
    const minimum = Math.min(width, height);
    const text = shortSlotLabel(slot, ordinal);
    const fontSizeMm = SLOT_LABEL_BASE_FONT_MM / safeZoom;
    const estimatedWidthMm = text.length * fontSizeMm * 0.62;
    const visible = Boolean(enabled)
      && Number.isFinite(minimum)
      && minimum >= SLOT_LABEL_MIN_PHYSICAL_MM
      && minimum * safeZoom >= SLOT_LABEL_MIN_VISIBLE_MM
      && estimatedWidthMm <= width * 0.75
      && fontSizeMm <= height * 0.6;
    return Object.freeze({ visible, text, fontSizeMm });
  }

  function withPreview(slot, store) {
    const position = store.effectivePosition(slot);
    if (position === slot.geometry.position_mm) {
      return slot;
    }
    return {
      ...slot,
      geometry: {
        ...slot.geometry,
        position_mm: { ...slot.geometry.position_mm, ...position },
      },
    };
  }

  function artworkForSlot(slot, layout, assetsApiUrl, clipId) {
    const asset = layout.assets.find((item) => item.id === slot.source.asset_id);
    const page = asset?.pages.find((item) => item.number === slot.source.page);
    const sourceBox = page?.boxes_mm?.[slot.source.pdf_box];
    if (!asset || asset.status !== "ready" || !page || !sourceBox || !assetsApiUrl) {
      return null;
    }
    const trim = slot.geometry.trim_size_mm;
    const image = svgElement("image", {
      x: -trim.width / 2,
      y: -trim.height / 2,
      width: trim.width,
      height: trim.height,
      href: `${assetsApiUrl}/${encodeURIComponent(asset.id)}/thumbnails/${page.number}`,
      preserveAspectRatio: "xMidYMid meet",
      class: "ev2-svg-artwork",
      "clip-path": `url(#${clipId})`,
      "data-slot-id": slot.id,
      "data-asset-id": asset.id,
      "data-page": page.number,
      "data-pdf-box": slot.source.pdf_box,
    });
    const rotated = [90, 270].includes(page.intrinsic_rotation_deg);
    const sourceWidth = rotated ? sourceBox.height : sourceBox.width;
    const sourceHeight = rotated ? sourceBox.width : sourceBox.height;
    if (Math.abs(sourceWidth - trim.width) > SOURCE_TRIM_VISUAL_TOLERANCE_MM
        || Math.abs(sourceHeight - trim.height) > SOURCE_TRIM_VISUAL_TOLERANCE_MM) {
      image.classList.add("is-source-mismatch");
    }
    return image;
  }

  function artworkIsApproximate(slot, layout, assetsApiUrl) {
    const asset = layout.assets.find((item) => item.id === slot.source.asset_id);
    const page = asset?.pages.find((item) => item.number === slot.source.page);
    return Boolean(asset && asset.status === "ready" && page && assetsApiUrl);
  }

  function slotPlacementClasses(slot, sheet, geometry) {
    const placement = geometry.classifySlotPlacement(slot, sheet);
    return {
      placement,
      className: placement === "outside_sheet"
        ? "is-outside-sheet"
        : placement === "outside_printable" ? "is-outside-printable" : "",
      message: placement === "outside_sheet"
        ? "Fuera del pliego"
        : placement === "outside_printable" ? "Fuera del área imprimible" : "",
    };
  }

  class Renderer {
    constructor(store, refs, geometry, assetsApiUrl, actionSystem) {
      this.store = store;
      this.refs = refs;
      this.geometry = geometry;
      this.assetsApiUrl = assetsApiUrl;
      this.actionSystem = actionSystem || null;
      this.unsubscribe = store.subscribe(() => this.render());
      this.render();
    }

    render() {
      const state = this.store.getState();
      this.renderCanvas(state);
      this.renderSlotsList(state);
      this.renderInspector(state);
      this.renderChrome(state);
    }

    renderCanvas(state) {
      const svg = this.refs.canvas;
      const sheet = state.layout.sheet.size_mm;
      const padding = 28;
      const baseWidth = sheet.width + padding * 2;
      const baseHeight = sheet.height + padding * 2;
      const viewWidth = baseWidth / state.zoom;
      const viewHeight = baseHeight / state.zoom;
      const centerX = sheet.width / 2 - state.pan.x;
      const centerY = sheet.height / 2 + state.pan.y;
      svg.setAttribute(
        "viewBox",
        `${centerX - viewWidth / 2} ${centerY - viewHeight / 2} ${viewWidth} ${viewHeight}`,
      );
      svg.replaceChildren();

      const definitions = svgElement("defs");
      svg.append(definitions);

      const workspace = svgElement("rect", {
        x: centerX - viewWidth,
        y: centerY - viewHeight,
        width: viewWidth * 2,
        height: viewHeight * 2,
        class: "ev2-svg-workspace",
        "data-canvas-background": "true",
      });
      const sheetRect = svgElement("rect", {
        x: 0,
        y: 0,
        width: sheet.width,
        height: sheet.height,
        class: "ev2-svg-sheet",
        "data-canvas-background": "true",
      });
      const printable = this.geometry.printableBounds(state.layout.sheet);
      const printableRect = svgElement("rect", {
        x: printable.left,
        y: this.geometry.mmToSvgY(printable.top, sheet.height),
        width: printable.width,
        height: printable.height,
        class: "ev2-svg-printable-area",
        "data-printable-area": "true",
      });
      svg.append(workspace, sheetRect, printableRect);

      const visibleSlots = state.layout.slots
        .filter((slot) => slot.face === state.activeFace)
        .map((slot) => withPreview(slot, this.store));

      for (const [slotIndex, slot] of visibleSlots.entries()) {
        const center = slot.geometry.position_mm;
        const trim = slot.geometry.trim_size_mm;
        const bleed = slot.geometry.bleed_mm;
        const selected = state.selection.includes(slot.id);
        const placement = slotPlacementClasses(slot, state.layout.sheet, this.geometry);
        const approximate = artworkIsApproximate(slot, state.layout, this.assetsApiUrl);
        const group = svgElement("g", {
          class: [
            "ev2-svg-slot",
            selected && "is-selected",
            placement.className,
            approximate && "has-approximate-artwork",
          ]
            .filter(Boolean)
            .join(" "),
          transform: `translate(${this.geometry.mmToSvgX(center.x_mm)} ${this.geometry.mmToSvgY(center.y_mm, sheet.height)}) rotate(${-slot.geometry.rotation_deg})`,
          "data-slot-id": slot.id,
          tabindex: "0",
        });
        if (slot.id || placement.message || approximate) {
          group.append(svgElement(
            "title",
            {},
            [slot.id, placement.message, approximate && "Vista aproximada del PDF"]
              .filter(Boolean)
              .join(" · "),
          ));
        }
        const clipId = `ev2-slot-clip-${slotIndex}`;
        const clipPath = svgElement("clipPath", {
          id: clipId,
          clipPathUnits: "userSpaceOnUse",
        });
        clipPath.append(svgElement("rect", {
          x: -trim.width / 2,
          y: -trim.height / 2,
          width: trim.width,
          height: trim.height,
        }));
        definitions.append(clipPath);
        const artwork = artworkForSlot(
          slot,
          state.layout,
          this.assetsApiUrl,
          clipId,
        );
        if (artwork) group.append(artwork);
        group.append(
          svgElement("rect", {
            x: -(trim.width + 2 * bleed) / 2,
            y: -(trim.height + 2 * bleed) / 2,
            width: trim.width + 2 * bleed,
            height: trim.height + 2 * bleed,
            class: "ev2-svg-bleed",
            "data-slot-id": slot.id,
          }),
          svgElement("rect", {
            x: -trim.width / 2,
            y: -trim.height / 2,
            width: trim.width,
            height: trim.height,
            class: "ev2-svg-trim",
            "data-slot-id": slot.id,
          }),
        );
        svg.append(group);
        const label = slotLabelPresentation(
          slot,
          slotIndex + 1,
          state.zoom,
          state.showSlotLabels,
        );
        if (label.visible) {
          svg.append(svgElement("text", {
            x: this.geometry.mmToSvgX(center.x_mm),
            y: this.geometry.mmToSvgY(center.y_mm, sheet.height),
            class: "ev2-svg-slot-label",
            "font-size": label.fontSizeMm,
            "aria-hidden": "true",
          }, label.text));
        }
      }

      const selectedSlots = visibleSlots.filter((slot) => state.selection.includes(slot.id));
      const selectionBounds = this.geometry.boundsUnion(
        selectedSlots.map((slot) => this.geometry.bleedBounds(slot)),
      );
      if (selectionBounds) {
        svg.append(svgElement("rect", {
          x: selectionBounds.left,
          y: this.geometry.mmToSvgY(selectionBounds.top, sheet.height),
          width: selectionBounds.width,
          height: selectionBounds.height,
          class: "ev2-svg-selection-bounds",
          "data-selection-bounds": "true",
        }));
      }
    }

    renderSlotsList(state) {
      this.refs.slotsList.replaceChildren();
      const slots = state.layout.slots.filter((slot) => slot.face === state.activeFace);
      if (!slots.length) {
        const empty = document.createElement("li");
        empty.className = "ev2-list-empty";
        empty.textContent = "No hay slots en esta cara.";
        this.refs.slotsList.append(empty);
        return;
      }
      for (const slot of slots) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.slotId = slot.id;
        button.className = state.selection.includes(slot.id) ? "is-selected" : "";
        const name = document.createElement("span");
        const dimensions = document.createElement("small");
        name.textContent = slot.id;
        dimensions.textContent = `${slot.geometry.trim_size_mm.width} × ${slot.geometry.trim_size_mm.height} mm`;
        button.append(name, dimensions);
        if (SourceSemantics.hasSourceOverride(state.layout, slot)) {
          const override = document.createElement("small");
          override.className = "ev2-source-override";
          override.textContent = "Fuente sobrescrita en este slot";
          button.append(override);
        }
        if (artworkIsApproximate(slot, state.layout, this.assetsApiUrl)) {
          const approximate = document.createElement("small");
          approximate.className = "ev2-approximate-artwork";
          approximate.textContent = "Vista aproximada del PDF";
          button.append(approximate);
        }
        item.append(button);
        this.refs.slotsList.append(item);
      }
    }

    renderInspector(state) {
      this.refs.inspector.replaceChildren();
      const selected = state.layout.slots.filter((slot) => state.selection.includes(slot.id));
      const values = selected.length === 1
        ? [
          ["ID", selected[0].id],
          ["Cara", selected[0].face],
          ["Trim", `${selected[0].geometry.trim_size_mm.width} × ${selected[0].geometry.trim_size_mm.height} mm`],
          ["Bleed", `${selected[0].geometry.bleed_mm} mm`],
          ["Rotación", `${selected[0].geometry.rotation_deg}°`],
        ]
        : [["Selección", selected.length ? `${selected.length} slots` : "Ninguna"]];
      if (selected.length === 1) {
        const slot = selected[0];
        if (SourceSemantics.hasSourceOverride(state.layout, slot)) {
          values.push(["Fuente", "Fuente sobrescrita en este slot"]);
        }
        if (artworkIsApproximate(slot, state.layout, this.assetsApiUrl)) {
          values.push([
            "Artwork",
            "Vista aproximada del PDF. La miniatura muestra la página completa ajustada al slot. El recorte y las transformaciones productivas exactas aún no están conectados.",
          ]);
        }
        const placement = slotPlacementClasses(slot, state.layout.sheet, this.geometry);
        if (placement.message) values.push(["Geometría", placement.message]);
      }
      for (const [label, value] of values) {
        const row = document.createElement("div");
        const term = document.createElement("dt");
        const description = document.createElement("dd");
        term.textContent = label;
        description.textContent = value;
        row.append(term, description);
        this.refs.inspector.append(row);
      }
    }

    renderChrome(state) {
      const labels = {
        clean: "Guardado",
        dirty: "Cambios sin guardar",
        saving: "Guardando…",
        save_error: "Error al guardar",
        conflict: "Conflicto de revisión",
      };
      this.refs.revision.textContent = String(state.revision);
      this.refs.saveStatus.textContent = labels[state.saveState.status];
      this.refs.saveStatus.dataset.state = state.saveState.status;
      this.refs.statusMessage.textContent = state.saveState.error || state.feedback || "";
      if (this.actionSystem) {
        const context = this.actionSystem.contextProvider();
        this.refs.save.disabled = !this.actionSystem.registry.isEnabled(
          this.actionSystem.actionIds.SAVE,
          context,
        );
        this.refs.undo.disabled = !this.actionSystem.registry.isEnabled(
          this.actionSystem.actionIds.UNDO,
          context,
        );
        this.refs.redo.disabled = !this.actionSystem.registry.isEnabled(
          this.actionSystem.actionIds.REDO,
          context,
        );
      } else {
        this.refs.save.disabled = !state.hasUnsavedChanges
          || state.saveState.status === "saving"
          || state.saveState.status === "conflict";
        this.refs.undo.disabled = !state.canUndo;
        this.refs.redo.disabled = !state.canRedo;
      }
      this.refs.deleteSlots.disabled = state.selection.length === 0
        || !EditPolicy.can(state.layout, state.selection, "delete");
      this.refs.reloadConflict.hidden = state.saveState.status !== "conflict";
      this.refs.activeFace.textContent = state.activeFace === "front" ? "Frente" : "Dorso";
      this.refs.cursor.textContent = state.cursorMm.x === null
        ? "—"
        : `X ${state.cursorMm.x.toFixed(2)} · Y ${state.cursorMm.y.toFixed(2)} mm`;
      this.refs.zoom.textContent = `${Math.round(state.zoom * 100)}%`;
      this.refs.toggleLabels.textContent = state.showSlotLabels ? "Etiquetas: sí" : "Etiquetas: no";
      this.refs.toggleLabels.setAttribute("aria-pressed", String(state.showSlotLabels));
      this.refs.slotCount.textContent = `${state.layout.slots.length} slot${state.layout.slots.length === 1 ? "" : "s"}`;
    }

    dispose() {
      this.unsubscribe();
    }
  }

  return Object.freeze({
    Renderer,
    artworkForSlot,
    artworkIsApproximate,
    shortSlotLabel,
    slotLabelPresentation,
    slotPlacementClasses,
    svgElement,
    withPreview,
  });
});
