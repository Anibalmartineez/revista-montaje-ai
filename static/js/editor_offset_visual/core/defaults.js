(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  const REPEAT_DESIGN_DEFAULT_PRIORITY = 100;
  const REPEAT_DESIGN_ZONES = new Set(['auto', 'top', 'bottom', 'left', 'right', 'center', 'fill']);
  const REPEAT_DESIGN_FLOWS = new Set(['auto', 'horizontal', 'vertical']);
  const REPEAT_DESIGN_ROLES = new Set(['primary', 'secondary', 'fill']);

  function ensureEngineDefaults(layout) {
    if (!Array.isArray(layout.allowed_engines) || layout.allowed_engines.length === 0) {
      layout.allowed_engines = ['repeat', 'nesting', 'hybrid'];
    }
    if (!layout.imposition_engine || !layout.allowed_engines.includes(layout.imposition_engine)) {
      layout.imposition_engine = layout.allowed_engines[0];
    }
  }

  function ensureCtpDefaults(layout) {
    if (!layout) return;
    if (!layout.ctp) {
      layout.ctp = {};
    }
    const ctp = layout.ctp;
    if (ctp.enabled === undefined) ctp.enabled = false;
    if (ctp.gripper_mm === undefined) ctp.gripper_mm = 40;
    if (ctp.lock_after === undefined) ctp.lock_after = true;
    if (ctp.show_guide === undefined) ctp.show_guide = false;

    if (!ctp.marks) {
      ctp.marks = {};
    }
    if (ctp.marks.registro === undefined) ctp.marks.registro = false;
    if (ctp.marks.control_strip === undefined) ctp.marks.control_strip = false;

    if (!ctp.technical_text) {
      ctp.technical_text = {};
    }
    const technicalText = ctp.technical_text;
    if (technicalText.job_name === undefined) technicalText.job_name = '';
    if (technicalText.client === undefined) technicalText.client = '';
    if (technicalText.notes === undefined) technicalText.notes = '';
    if (technicalText.auto_cmyk === undefined) technicalText.auto_cmyk = true;
    if (technicalText.extra_text === undefined) technicalText.extra_text = '';
  }

  function ensureExportDefaults(layout) {
    if (!layout) return;
    if (!layout.export_settings || typeof layout.export_settings !== 'object') {
      layout.export_settings = { bleed_mm: 3, crop_marks: true, output_mode: 'raster' };
    } else {
      if (layout.export_settings.bleed_mm === undefined) {
        layout.export_settings.bleed_mm = 3;
      }
      if (layout.export_settings.crop_marks === undefined) {
        layout.export_settings.crop_marks = true;
      }
      if (!layout.export_settings.output_mode) {
        layout.export_settings.output_mode = 'raster';
      }
    }
    if (!layout.design_export || typeof layout.design_export !== 'object') {
      layout.design_export = {};
    }
  }

  function normalizeRepeatDesignChoice(value, allowed, fallback) {
    const normalized = String(value || fallback).trim().toLowerCase();
    return allowed.has(normalized) ? normalized : fallback;
  }

  function normalizeRepeatDesignPriority(value) {
    const parsed = parseFloat(value);
    if (!Number.isFinite(parsed)) return REPEAT_DESIGN_DEFAULT_PRIORITY;
    return parsed;
  }

  function normalizeRepeatManualOverrides(design) {
    const current = (
      design
      && typeof design.repeat_manual_overrides === 'object'
      && design.repeat_manual_overrides
    ) || {};
    return {
      priority: typeof current.priority === 'boolean'
        ? current.priority
        : normalizeRepeatDesignPriority(design?.priority) !== REPEAT_DESIGN_DEFAULT_PRIORITY,
      preferred_flow: typeof current.preferred_flow === 'boolean'
        ? current.preferred_flow
        : normalizeRepeatDesignChoice(design?.preferred_flow, REPEAT_DESIGN_FLOWS, 'auto') !== 'auto',
      repeat_role: typeof current.repeat_role === 'boolean'
        ? current.repeat_role
        : normalizeRepeatDesignChoice(design?.repeat_role, REPEAT_DESIGN_ROLES, 'secondary') !== 'secondary',
    };
  }

  function normalizeDesignDefaults(layout) {
    layout.designs = (layout.designs || []).map((design) => ({
      ...design,
      width_mm: design.width_mm ?? design.w_mm ?? 0,
      height_mm: design.height_mm ?? design.h_mm ?? 0,
      bleed_mm: design.bleed_mm ?? layout.bleed_default_mm ?? 0,
      allow_rotation: design.allow_rotation !== false,
      forms_per_plate: Math.max(1, parseInt(design.forms_per_plate || '1', 10)),
      priority: normalizeRepeatDesignPriority(design.priority),
      preferred_zone: normalizeRepeatDesignChoice(design.preferred_zone, REPEAT_DESIGN_ZONES, 'auto'),
      preferred_flow: normalizeRepeatDesignChoice(design.preferred_flow, REPEAT_DESIGN_FLOWS, 'auto'),
      repeat_role: normalizeRepeatDesignChoice(design.repeat_role, REPEAT_DESIGN_ROLES, 'secondary'),
      repeat_manual_overrides: normalizeRepeatManualOverrides(design),
    }));
  }

  function normalizeFormsPerPlateValue(value) {
    const parsed = parseInt(value, 10);
    if (!Number.isFinite(parsed) || parsed < 1) return 1;
    return parsed;
  }

  function normalizeNonNegativeNumber(value, fallback = 0) {
    const parsed = parseFloat(value);
    if (!Number.isFinite(parsed) || parsed < 0) return fallback;
    return parsed;
  }

  function firstDefinedNumber(...values) {
    for (const value of values) {
      if (value === undefined || value === null || value === '') continue;
      const parsed = parseFloat(value);
      if (Number.isFinite(parsed)) return parsed;
    }
    return 0;
  }

  function normalizeLayoutFaces(layout) {
    if (!layout) return 'front';
    if (!Array.isArray(layout.faces) || layout.faces.length === 0) {
      layout.faces = ['front'];
    }
    if (!layout.active_face || !layout.faces.includes(layout.active_face)) {
      layout.active_face = layout.faces[0];
    }
    if (!layout.slots) {
      layout.slots = [];
    }
    layout.slots.forEach((slot) => {
      if (!slot.face) {
        slot.face = 'front';
      }
    });
    return layout.active_face || 'front';
  }

  window.EditorOffsetVisual.defaults = {
    REPEAT_DESIGN_DEFAULT_PRIORITY,
    REPEAT_DESIGN_ZONES,
    REPEAT_DESIGN_FLOWS,
    REPEAT_DESIGN_ROLES,
    ensureEngineDefaults,
    ensureCtpDefaults,
    ensureExportDefaults,
    normalizeRepeatDesignChoice,
    normalizeRepeatDesignPriority,
    normalizeRepeatManualOverrides,
    normalizeDesignDefaults,
    normalizeFormsPerPlateValue,
    normalizeNonNegativeNumber,
    firstDefinedNumber,
    normalizeLayoutFaces,
  };
})();
