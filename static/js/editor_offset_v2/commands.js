(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.Commands = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function clone(value) {
    return typeof structuredClone === "function"
      ? structuredClone(value)
      : JSON.parse(JSON.stringify(value));
  }

  function finitePosition(position) {
    return position
      && Number.isFinite(position.x_mm)
      && Number.isFinite(position.y_mm);
  }

  class CreateSlotCommand {
    constructor(bundle) {
      this.description = "Crear slot de prueba";
      this.asset = clone(bundle.asset);
      this.work = clone(bundle.work);
      this.slot = clone(bundle.slot);
      this.affectedIds = Object.freeze([this.slot.id]);
    }

    execute(layout) {
      if (layout.slots.some((slot) => slot.id === this.slot.id)) {
        throw new Error(`Slot ${this.slot.id} already exists`);
      }
      if (layout.assets.some((asset) => asset.id === this.asset.id)) {
        throw new Error(`Asset ${this.asset.id} already exists`);
      }
      if (layout.works.some((work) => work.id === this.work.id)) {
        throw new Error(`Work ${this.work.id} already exists`);
      }
      layout.assets.push(clone(this.asset));
      layout.works.push(clone(this.work));
      layout.slots.push(clone(this.slot));
    }

    undo(layout) {
      layout.slots = layout.slots.filter((slot) => slot.id !== this.slot.id);
      layout.works = layout.works.filter((work) => work.id !== this.work.id);
      layout.assets = layout.assets.filter((asset) => asset.id !== this.asset.id);
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  class MoveSlotsCommand {
    constructor(beforePositions, afterPositions) {
      this.description = "Mover slots";
      this.beforePositions = clone(beforePositions);
      this.afterPositions = clone(afterPositions);
      this.affectedIds = Object.freeze(Object.keys(this.afterPositions));
      if (!this.affectedIds.length) {
        throw new Error("MoveSlotsCommand requires at least one slot");
      }
      if (Object.keys(this.beforePositions).sort().join("\0")
          !== [...this.affectedIds].sort().join("\0")) {
        throw new Error("MoveSlotsCommand requires matching before and after ids");
      }
      for (const position of [
        ...Object.values(this.beforePositions),
        ...Object.values(this.afterPositions),
      ]) {
        if (!finitePosition(position)) {
          throw new TypeError("Move positions must be finite millimetres");
        }
      }
    }

    apply(layout, positions) {
      for (const slot of layout.slots) {
        const position = positions[slot.id];
        if (position) {
          slot.geometry.position_mm.x_mm = position.x_mm;
          slot.geometry.position_mm.y_mm = position.y_mm;
        }
      }
    }

    execute(layout) {
      this.apply(layout, this.afterPositions);
    }

    undo(layout) {
      this.apply(layout, this.beforePositions);
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  class DeleteSlotsCommand {
    constructor(layout, slotIds) {
      this.description = "Eliminar slots";
      const ids = new Set(slotIds);
      this.deleted = layout.slots
        .map((slot, index) => ({ slot: clone(slot), index }))
        .filter((entry) => ids.has(entry.slot.id));
      this.affectedIds = Object.freeze(this.deleted.map((entry) => entry.slot.id));
      if (!this.affectedIds.length) {
        throw new Error("DeleteSlotsCommand requires existing slots");
      }
    }

    execute(layout) {
      const ids = new Set(this.affectedIds);
      layout.slots = layout.slots.filter((slot) => !ids.has(slot.id));
    }

    undo(layout) {
      for (const entry of [...this.deleted].sort((a, b) => a.index - b.index)) {
        layout.slots.splice(entry.index, 0, clone(entry.slot));
      }
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  function createDevelopmentPlaceholderBundle(layout, token, nowIso) {
    const safeToken = String(token).replace(/[^a-z0-9_-]/gi, "").slice(0, 40);
    if (!safeToken) {
      throw new Error("A placeholder token is required");
    }
    const assetId = `dev_asset_${safeToken}`;
    const workId = `dev_work_${safeToken}`;
    const slotId = `dev_slot_${safeToken}`;
    const sheet = layout.sheet.size_mm;
    const offset = layout.slots.length * 8;
    const timestamp = nowIso || new Date().toISOString();
    const source = { asset_id: assetId, page: 1, pdf_box: "trim" };
    const boxes = {
      media: { x: 0, y: 0, width: 96, height: 56 },
      trim: { x: 3, y: 3, width: 90, height: 50 },
      bleed: { x: 0, y: 0, width: 96, height: 56 },
      crop: null,
    };
    return {
      asset: {
        id: assetId,
        original_filename: "placeholder-development.pdf",
        storage_key: `development/placeholders/${assetId}.pdf`,
        mime_type: "application/pdf",
        sha256: "0".repeat(64),
        page_count: 1,
        status: "error",
        created_at: timestamp,
        pages: [{
          number: 1,
          intrinsic_rotation_deg: 0,
          boxes_mm: boxes,
          preview_key: null,
          preflight: {
            status: "error",
            color_spaces: [],
            minimum_effective_dpi: null,
            has_transparency: null,
            has_overprint: null,
            issues: [{
              code: "DEVELOPMENT_PLACEHOLDER",
              level: "error",
              message: "Placeholder sin PDF físico; no exportable.",
            }],
          },
        }],
      },
      work: {
        id: workId,
        name: "Slot de prueba V2",
        trim_size_mm: { width: 90, height: 50 },
        bleed_mm: 3,
        requested_forms: 1,
        allowed_rotations_deg: [0, 90, 180, 270],
        priority: 0,
        preferred_zone: "none",
        preferred_flow: "manual",
        front_source: source,
        back_source: null,
      },
      slot: {
        id: slotId,
        face: "front",
        work_id: workId,
        source,
        geometry: {
          position_mm: {
            x_mm: sheet.width / 2 + offset,
            y_mm: sheet.height / 2 + offset,
            anchor: "trim_center",
          },
          trim_size_mm: { width: 90, height: 50 },
          bleed_mm: 3,
          rotation_deg: 0,
        },
        content_transform: {
          fit_mode: "actual_size",
          scale_x: 1,
          scale_y: 1,
          offset_mm: { x: 0, y: 0 },
          rotation_deg: 0,
          mirror_x: false,
          mirror_y: false,
          clip_to: "bleed_box",
        },
        locks: { geometry: [], content: [], production: [], delete: [] },
        production: { marks_profile_id: layout.export.default_marks_profile_id },
        generated_by: { type: "manual" },
      },
    };
  }

  return Object.freeze({
    CreateSlotCommand,
    MoveSlotsCommand,
    DeleteSlotsCommand,
    createDevelopmentPlaceholderBundle,
  });
});
