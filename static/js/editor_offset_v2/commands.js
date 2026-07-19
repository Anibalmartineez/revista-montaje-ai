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

  function sourcePage(layout, source) {
    const asset = layout.assets.find((item) => item.id === source.asset_id);
    const page = asset?.pages.find((item) => item.number === source.page);
    const box = page?.boxes_mm?.[source.pdf_box];
    if (!asset || !page || !box) {
      throw new Error("Source must reference an existing asset page and PDF box");
    }
    return { asset, page, box };
  }

  function safeToken(value) {
    const token = String(value).replace(/[^a-z0-9_-]/gi, "").slice(0, 48);
    if (!token) throw new Error("A safe command token is required");
    return token;
  }

  class CreateWorkCommand {
    constructor(work) {
      this.description = "Crear trabajo desde PDF";
      this.work = clone(work);
      this.affectedIds = Object.freeze([this.work.id]);
    }

    execute(layout) {
      if (layout.works.some((work) => work.id === this.work.id)) {
        throw new Error(`Work ${this.work.id} already exists`);
      }
      sourcePage(layout, this.work.front_source);
      if (this.work.back_source) sourcePage(layout, this.work.back_source);
      layout.works.push(clone(this.work));
    }

    undo(layout) {
      if (layout.slots.some((slot) => slot.work_id === this.work.id)) {
        throw new Error("Undo the work slots before removing their work");
      }
      layout.works = layout.works.filter((work) => work.id !== this.work.id);
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  class CreateSlotFromWorkCommand {
    constructor(slot) {
      this.description = "Crear slot real desde trabajo";
      this.slot = clone(slot);
      this.affectedIds = Object.freeze([this.slot.id]);
    }

    execute(layout) {
      if (layout.slots.some((slot) => slot.id === this.slot.id)) {
        throw new Error(`Slot ${this.slot.id} already exists`);
      }
      if (!layout.works.some((work) => work.id === this.slot.work_id)) {
        throw new Error("Slot must reference an existing work");
      }
      sourcePage(layout, this.slot.source);
      layout.slots.push(clone(this.slot));
    }

    undo(layout) {
      layout.slots = layout.slots.filter((slot) => slot.id !== this.slot.id);
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  class ReplaceSlotSourceCommand {
    constructor(layout, slotId, replacementSource) {
      const slot = layout.slots.find((item) => item.id === slotId);
      if (!slot) throw new Error("ReplaceSlotSourceCommand requires an existing slot");
      const replacement = sourcePage(layout, replacementSource);
      this.description = "Sustituir fuente del slot";
      this.slotId = slotId;
      this.beforeSource = clone(slot.source);
      this.afterSource = clone(replacementSource);
      this.affectedIds = Object.freeze([slotId]);
      const rotation = replacement.page.intrinsic_rotation_deg;
      const boxWidth = rotation === 90 || rotation === 270
        ? replacement.box.height
        : replacement.box.width;
      const boxHeight = rotation === 90 || rotation === 270
        ? replacement.box.width
        : replacement.box.height;
      const trim = slot.geometry.trim_size_mm;
      this.dimensionWarning = Math.abs(trim.width - boxWidth) > 0.01
        || Math.abs(trim.height - boxHeight) > 0.01
        ? `La nueva caja mide ${boxWidth.toFixed(2)} × ${boxHeight.toFixed(2)} mm; el slot conserva ${trim.width.toFixed(2)} × ${trim.height.toFixed(2)} mm.`
        : null;
    }

    apply(layout, source) {
      sourcePage(layout, source);
      const slot = layout.slots.find((item) => item.id === this.slotId);
      if (!slot) throw new Error("The slot no longer exists");
      slot.source = clone(source);
    }

    execute(layout) {
      this.apply(layout, this.afterSource);
    }

    undo(layout) {
      this.apply(layout, this.beforeSource);
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  class ApplyRepeatCommand {
    constructor(layout, result, options) {
      if (!result || result.success !== true || !Array.isArray(result.slots)
          || !result.slots.length) {
        throw new Error("ApplyRepeatCommand requires a successful non-empty proposal");
      }
      const mode = options?.mode || "add";
      if (!["add", "replace_work_face"].includes(mode)) {
        throw new Error("Unknown Repeat apply mode");
      }
      const workIds = new Set(options?.workIds || []);
      const face = options?.face;
      if (!workIds.size || !["front", "back"].includes(face)) {
        throw new Error("Repeat apply context is incomplete");
      }
      this.description = mode === "add"
        ? "Añadir propuesta Repeat"
        : "Reemplazar slots mediante Repeat";
      this.mode = mode;
      this.workIds = Object.freeze([...workIds]);
      this.face = face;
      this.proposed = clone(result.slots);
      this.removed = mode === "replace_work_face"
        ? layout.slots
          .map((slot, index) => ({ slot: clone(slot), index }))
          .filter((entry) => entry.slot.face === face && workIds.has(entry.slot.work_id))
        : [];
      const proposedIds = this.proposed.map((slot) => slot.id);
      if (new Set(proposedIds).size !== proposedIds.length) {
        throw new Error("Repeat proposal contains duplicate slot ids");
      }
      this.beforeImposition = clone(layout.imposition);
      this.afterImposition = clone(layout.imposition);
      this.afterImposition.engine = "repeat";
      this.afterImposition.engine_version = "2.0.0-adapter";
      this.afterImposition.settings = {
        ...this.afterImposition.settings,
        horizontal_gap_mm: Number(options.settings.horizontal_gap_mm),
        vertical_gap_mm: Number(options.settings.vertical_gap_mm),
        exact_quantity: Boolean(options.settings.exact_quantity),
        fill_remaining_space: Boolean(options.settings.fill_remaining_space),
      };
      this.afterImposition.last_result = {
        operation_id: result.operation_id,
        status: result.unplaced > 0 ? "incomplete" : "complete",
        requested: result.requested,
        placed: result.placed,
        unplaced: result.unplaced,
        overproduced: result.overproduced,
        generated_at: result.generated_at,
        warnings: clone(result.warnings || []),
      };
      this.affectedIds = Object.freeze([
        ...new Set([...proposedIds, ...this.removed.map((entry) => entry.slot.id)]),
      ]);
    }

    execute(layout) {
      const workIds = new Set(this.workIds);
      if (this.mode === "replace_work_face") {
        layout.slots = layout.slots.filter(
          (slot) => !(slot.face === this.face && workIds.has(slot.work_id)),
        );
      }
      const existingIds = new Set(layout.slots.map((slot) => slot.id));
      if (this.proposed.some((slot) => existingIds.has(slot.id))) {
        throw new Error("Repeat proposal collides with an existing slot id");
      }
      layout.slots.push(...clone(this.proposed));
      layout.imposition = clone(this.afterImposition);
    }

    undo(layout) {
      const proposedIds = new Set(this.proposed.map((slot) => slot.id));
      layout.slots = layout.slots.filter((slot) => !proposedIds.has(slot.id));
      for (const entry of [...this.removed].sort((a, b) => a.index - b.index)) {
        layout.slots.splice(Math.min(entry.index, layout.slots.length), 0, clone(entry.slot));
      }
      layout.imposition = clone(this.beforeImposition);
    }

    redo(layout) {
      this.execute(layout);
    }
  }

  function createWorkFromSource(layout, source, values, token) {
    const selected = sourcePage(layout, source);
    const width = Number(values.width);
    const height = Number(values.height);
    const bleed = Number(values.bleed);
    const requestedForms = Number(values.requestedForms);
    const rotations = [...new Set(values.allowedRotations.map(Number))];
    if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
      throw new Error("Trim width and height must be positive millimetres");
    }
    if (!Number.isFinite(bleed) || bleed < 0) {
      throw new Error("Bleed must be zero or greater");
    }
    if (!Number.isInteger(requestedForms) || requestedForms < 1) {
      throw new Error("Requested quantity must be a positive integer");
    }
    if (!rotations.length || rotations.some((value) => ![0, 90, 180, 270].includes(value))) {
      throw new Error("At least one cardinal rotation is required");
    }
    const name = String(values.name || selected.asset.original_filename).trim();
    if (!name || name.length > 160) {
      throw new Error("Work name must contain between 1 and 160 characters");
    }
    const id = `work_${safeToken(token)}`;
    return {
      id,
      name,
      trim_size_mm: { width, height },
      bleed_mm: bleed,
      requested_forms: requestedForms,
      allowed_rotations_deg: rotations,
      priority: 0,
      preferred_zone: "none",
      preferred_flow: "manual",
      front_source: clone(source),
      back_source: values.useSameSourceForBack ? clone(source) : null,
    };
  }

  function createSlotFromWork(layout, workId, token, center) {
    const work = layout.works.find((item) => item.id === workId);
    if (!work || !work.front_source) throw new Error("An existing work with a front source is required");
    sourcePage(layout, work.front_source);
    if (!center || !Number.isFinite(center.x_mm) || !Number.isFinite(center.y_mm)) {
      throw new Error("A finite visible center is required");
    }
    return {
      id: `slot_${safeToken(token)}`,
      face: "front",
      work_id: work.id,
      source: clone(work.front_source),
      geometry: {
        position_mm: { x_mm: center.x_mm, y_mm: center.y_mm, anchor: "trim_center" },
        trim_size_mm: clone(work.trim_size_mm),
        bleed_mm: work.bleed_mm,
        rotation_deg: work.allowed_rotations_deg.includes(0) ? 0 : work.allowed_rotations_deg[0],
      },
      content_transform: {
        fit_mode: "actual_size",
        scale_x: 1,
        scale_y: 1,
        offset_mm: { x: 0, y: 0 },
        rotation_deg: 0,
        mirror_x: false,
        mirror_y: false,
        clip_to: work.front_source.pdf_box === "bleed" ? "bleed_box" : "trim_box",
      },
      locks: { geometry: [], content: [], production: [], delete: [] },
      production: { marks_profile_id: layout.export.default_marks_profile_id },
      generated_by: { type: "manual" },
    };
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
    CreateWorkCommand,
    CreateSlotFromWorkCommand,
    ReplaceSlotSourceCommand,
    ApplyRepeatCommand,
    createWorkFromSource,
    createSlotFromWork,
    sourcePage,
    createDevelopmentPlaceholderBundle,
  });
});
