(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.CommandRegistry = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const ACTION_IDS = Object.freeze({
    SAVE: "editor.save",
    CANCEL: "editor.cancel",
    UNDO: "history.undo",
    REDO: "history.redo",
    MOVE_ABSOLUTE: "selection.move.absolute",
    MOVE_DELTA: "selection.move.delta",
    NUDGE: "selection.nudge",
    ROTATE_CLOCKWISE: "selection.rotate.clockwise",
    ROTATE_COUNTERCLOCKWISE: "selection.rotate.counterclockwise",
    ROTATE_SET: "selection.rotate.set",
    DUPLICATE: "selection.duplicate",
    DELETE: "selection.delete",
    COPY: "clipboard.copy",
    CUT: "clipboard.cut",
    PASTE: "clipboard.paste",
    SELECT_ALL_FACE: "selection.select_all_face",
    SELECT_SAME_WORK: "selection.select_same_work",
    SELECT_SAME_ASSET: "selection.select_same_asset",
    SELECT_SAME_SIZE: "selection.select_same_size",
    SELECT_SAME_ROTATION: "selection.select_same_rotation",
    SELECT_SAME_PROVENANCE: "selection.select_same_provenance",
    SELECT_LOCKED_GEOMETRY: "selection.select_locked_geometry",
    SELECT_LOCKED_CONTENT: "selection.select_locked_content",
    SELECT_LOCKED_DELETE: "selection.select_locked_delete",
    SELECT_OUTSIDE_SHEET: "selection.select_outside_sheet",
    SELECT_OUTSIDE_PRINTABLE: "selection.select_outside_printable",
    SELECT_OVERLAPS: "selection.select_overlaps",
    SELECT_GEOMETRY_ISSUES: "selection.select_geometry_issues",
    SELECT_FACE_VISIBLE: "selection.select_face_visible",
    SELECT_WORK_VISIBLE: "selection.select_work_visible",
    MARQUEE_MODE_SET: "selection.marquee.mode.set",
    CYCLE_AT_POINT: "selection.cycle_at_point",
    VISIBILITY_HIDE_SELECTION: "visibility.hide_selection",
    VISIBILITY_ISOLATE_SELECTION: "visibility.hide_unselected",
    VISIBILITY_SHOW_ALL: "visibility.show_all",
    VISIBILITY_RESTORE_PREVIOUS: "visibility.restore_previous",
    VISIBILITY_SLOT_TOGGLE: "visibility.slot.toggle",
    VISIBILITY_WORK_TOGGLE: "visibility.work.toggle",
    USER_LOCKS_SET: "selection.user_locks.set",
    KEY_SLOT_SET: "selection.key_slot.set",
    KEY_SLOT_CLEAR: "selection.key_slot.clear",
    ALIGN_LEFT: "selection.align.left",
    ALIGN_RIGHT: "selection.align.right",
    ALIGN_TOP: "selection.align.top",
    ALIGN_BOTTOM: "selection.align.bottom",
    ALIGN_HORIZONTAL_CENTER: "selection.align.horizontal_center",
    ALIGN_VERTICAL_CENTER: "selection.align.vertical_center",
    CENTER_HORIZONTAL: "selection.center.horizontal",
    CENTER_VERTICAL: "selection.center.vertical",
    CENTER_BOTH: "selection.center.both",
    DISTRIBUTE_HORIZONTAL: "selection.distribute.horizontal",
    DISTRIBUTE_VERTICAL: "selection.distribute.vertical",
    GAP_HORIZONTAL: "selection.gap.horizontal",
    GAP_VERTICAL: "selection.gap.vertical",
    MATRIX_CREATE: "selection.matrix.create",
    PRECISION_RULERS_TOGGLE: "precision.rulers.toggle",
    PRECISION_GUIDES_TOGGLE: "precision.guides.toggle",
    PRECISION_SMART_GUIDES_TOGGLE: "precision.smart_guides.toggle",
    PRECISION_SNAP_TOGGLE: "precision.snap.toggle",
    PRECISION_SNAP_SOURCE_SET: "precision.snap.source.set",
    PRECISION_SNAP_REFERENCE_SET: "precision.snap.reference.set",
    PRECISION_SNAP_THRESHOLD_SET: "precision.snap.threshold.set",
    PRECISION_GUIDE_CREATE: "precision.guide.create",
    PRECISION_GUIDE_UPDATE: "precision.guide.update",
    PRECISION_GUIDE_DELETE: "precision.guide.delete",
    PRECISION_GUIDES_CLEAR: "precision.guides.clear",
    PRECISION_MEASURE_TOGGLE: "precision.measure.toggle",
    PRECISION_MEASURE_CLEAR: "precision.measure.clear",
    HELP_TOGGLE: "shortcuts.help.toggle",
  });

  class UnknownActionError extends Error {
    constructor(actionId) {
      super(`Unknown editor action: ${actionId}`);
      this.name = "UnknownActionError";
      this.code = "UNKNOWN_EDITOR_ACTION";
      this.actionId = actionId;
    }
  }

  class DisabledActionError extends Error {
    constructor(actionId, reason) {
      super(reason || `Editor action is disabled: ${actionId}`);
      this.name = "DisabledActionError";
      this.code = "EDITOR_ACTION_DISABLED";
      this.actionId = actionId;
    }
  }

  function freezeAction(definition) {
    if (!definition || typeof definition !== "object") {
      throw new TypeError("Action definition must be an object");
    }
    const id = String(definition.id || "").trim();
    if (!/^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_-]*)+$/.test(id)) {
      throw new Error(`Invalid editor action id: ${id || "<empty>"}`);
    }
    if (typeof definition.execute !== "function") {
      throw new TypeError(`Editor action ${id} requires execute(context, payload)`);
    }
    return Object.freeze({
      ...definition,
      id,
      label: String(definition.label || id),
      category: String(definition.category || "general"),
      description: String(definition.description || ""),
      shortcuts: Object.freeze([...(definition.shortcuts || [])].map(String)),
      help: Object.freeze([...(definition.help || [])].map((entry) => Object.freeze({ ...entry }))),
      modifiesLayout: Boolean(definition.modifiesLayout),
      requiresSelection: Boolean(definition.requiresSelection),
      enabled: typeof definition.enabled === "function" ? definition.enabled : () => true,
    });
  }

  class ActionRegistry {
    constructor() {
      this.actions = new Map();
    }

    register(definition) {
      const action = freezeAction(definition);
      if (this.actions.has(action.id)) {
        throw new Error(`Duplicate editor action id: ${action.id}`);
      }
      this.actions.set(action.id, action);
      return action;
    }

    get(actionId) {
      return this.actions.get(actionId) || null;
    }

    list() {
      return [...this.actions.values()];
    }

    isEnabled(actionId, context, payload) {
      const action = this.get(actionId);
      return Boolean(action && action.enabled(context, payload));
    }

    execute(actionId, context, payload) {
      const action = this.get(actionId);
      if (!action) throw new UnknownActionError(actionId);
      if (!action.enabled(context, payload)) {
        const reason = typeof action.disabledReason === "function"
          ? action.disabledReason(context, payload)
          : null;
        throw new DisabledActionError(actionId, reason);
      }
      return action.execute(context, payload);
    }
  }

  function selectedIds(context) {
    return [...context.store.selection];
  }

  function selectedSlots(context) {
    const ids = new Set(selectedIds(context));
    return context.store.layout.slots.filter((slot) => ids.has(slot.id));
  }

  function blockUnselectedDeleteDependents(context) {
    const dependents = context.commands.unselectedDeleteDependents(
      context.store.layout,
      selectedIds(context),
    );
    if (!dependents.length) return false;
    context.store.setFeedback(context.commands.deleteDependencyMessage(dependents));
    return true;
  }

  function blockedMoveIds(context) {
    return context.editPolicy.blockedSlotIds(
      context.store.layout,
      selectedIds(context),
      "move",
    );
  }

  function blockedIds(context, capability) {
    return context.editPolicy.blockedSlotIds(
      context.store.layout,
      selectedIds(context),
      capability,
    );
  }

  function objectActionReady(context) {
    return !context.store.pointerSession && !context.interactions?.hasPanSession();
  }

  function objectDisabledReason(context, capability, verb) {
    const blocked = capability ? blockedIds(context, capability) : [];
    if (blocked.length) return `No se puede ${verb}: slots bloqueados ${blocked.join(", ")}.`;
    if (context.interactions?.hasPanSession()) return `No se puede ${verb} durante pan.`;
    if (context.store.pointerSession) return `No se puede ${verb} durante otra interacción.`;
    return "La selección actual no permite esta acción.";
  }

  function hasIncompatiblePointerSession(context) {
    const session = context.store.pointerSession;
    return Boolean(session && session.type !== "nudge");
  }

  function moveDisabledReason(context) {
    const blocked = blockedMoveIds(context);
    if (blocked.length) return `No se puede mover: slots bloqueados ${blocked.join(", ")}.`;
    if (context.interactions?.hasPanSession()) return "No se puede mover durante pan.";
    if (hasIncompatiblePointerSession(context)) return "No se puede mover durante otra interacción.";
    return "La selección actual no permite esta acción.";
  }

  function nudgePayload(shortcut) {
    const direction = shortcut.match(/Arrow(?:Left|Right|Up|Down)$/)?.[0];
    if (!direction) throw new Error(`Unsupported nudge shortcut: ${shortcut}`);
    const large = /(?:Ctrl|Meta)\+Shift\+/.test(shortcut);
    const step = large ? 10 : shortcut.includes("Shift+") ? 1 : 0.1;
    const deltas = {
      ArrowLeft: { dx: -step, dy: 0 },
      ArrowRight: { dx: step, dy: 0 },
      ArrowUp: { dx: 0, dy: step },
      ArrowDown: { dx: 0, dy: -step },
    };
    return { direction, step, ...deltas[direction] };
  }

  function registerEditorActions(registry) {
    function hiddenIds(context) {
      return context.store.advancedSelection.hiddenSlotIds;
    }

    function visibleFaceIds(context) {
      if (context.advancedSelection) {
        return context.advancedSelection.visibleSlots(
          context.store.layout,
          context.store.activeFace,
          hiddenIds(context),
        ).map((slot) => slot.id);
      }
      return context.objectOperations.selectAllFace(
        context.store.layout,
        context.store.activeFace,
        hiddenIds(context),
      );
    }

    function replaceSelection(context, ids, label) {
      context.store.setSelection(ids, "replace");
      context.store.setFeedback(`${label}: ${ids.length} slot(s).`);
      return ids;
    }

    function geometryIssueIds(context, issue) {
      const index = context.advancedSelection.geometryIssueIndex(
        context.store.layout,
        context.store.activeFace,
        hiddenIds(context),
        context.geometry,
        context.store.arrangement.geometryReference,
      );
      return context.advancedSelection.selectGeometryIssues(index, issue);
    }

    function cancelVisibilityDependentSession(context) {
      if (context.interactions?.hasPointerActivity()) context.interactions.cancelPointer();
      context.nudgeController?.cancel();
      context.store.clearSelectionCycle(false);
    }

    function arrangementOptions(context, extra) {
      return {
        geometryReference: context.store.arrangement.geometryReference,
        target: context.store.arrangement.target,
        keySlotId: context.store.arrangement.keySlotId,
        activeFace: context.store.activeFace,
        ...extra,
      };
    }

    function arrangementReady(context) {
      return objectActionReady(context) && Boolean(context.alignmentOperations && context.geometry);
    }

    function alignmentPlan(context, alignment) {
      return context.alignmentOperations.buildAlignmentPlan(
        context.store.layout,
        selectedIds(context),
        context.geometry,
        arrangementOptions(context, { alignment }),
      );
    }

    function distributionPlan(context, axis) {
      return context.alignmentOperations.buildDistributionPlan(
        context.store.layout,
        selectedIds(context),
        context.geometry,
        arrangementOptions(context, { axis }),
      );
    }

    function planEnabled(context, factory) {
      if (!arrangementReady(context)) return false;
      try {
        const plan = factory();
        return context.editPolicy.can(context.store.layout, plan.affectedIds, "move");
      } catch (_error) {
        return false;
      }
    }

    function planDisabledReason(context, factory, fallback) {
      try {
        const plan = factory();
        const blocked = context.editPolicy.blockedSlotDetails(
          context.store.layout,
          plan.affectedIds,
          "move",
        );
        if (blocked.length) {
          return `Movimiento bloqueado: ${blocked.map(
            (item) => `${item.id} [${item.sources.join(", ")}]`,
          ).join("; ")}.`;
        }
      } catch (error) {
        return error.message || fallback;
      }
      return fallback;
    }

    function executeMovePlan(context, plan, description, feedback) {
      context.nudgeController?.finish();
      if (!plan.changed) {
        context.store.setFeedback("La operación no produjo cambios.");
        return Object.freeze({ changed: false, affectedIds: [] });
      }
      const selection = selectedIds(context);
      const command = new context.commands.MoveSlotsCommand(
        plan.beforePositions,
        plan.afterPositions,
        { description, selectionBefore: selection, selectionAfter: selection },
      );
      context.store.executeCommand(command);
      context.store.setFeedback(feedback || `${description}: ${command.affectedIds.length} slot(s).`);
      return Object.freeze({ changed: true, affectedIds: command.affectedIds, plan });
    }

    function registerAlignmentAction(id, label, alignment) {
      registry.register({
        id,
        label,
        category: "arrangement",
        description: `${label} usando la referencia geométrica y el destino activos.`,
        modifiesLayout: true,
        requiresSelection: true,
        enabled: (context) => planEnabled(context, () => alignmentPlan(context, alignment)),
        disabledReason: (context) => planDisabledReason(
          context,
          () => alignmentPlan(context, alignment),
          "La selección, el destino o los locks no permiten esta alineación.",
        ),
        execute: (context) => executeMovePlan(
          context,
          alignmentPlan(context, alignment),
          label,
        ),
      });
    }

    registry.register({
      id: ACTION_IDS.SAVE,
      label: "Guardar",
      category: "document",
      description: "Guarda el Layout V2 mediante el coordinador existente.",
      shortcuts: ["Mod+S"],
      help: [{ keys: "Ctrl/Cmd+S", label: "Guardar" }],
      allowInEditable: true,
      enabled: (context) => !["saving", "conflict"].includes(context.store.saveState.status)
        && !hasIncompatiblePointerSession(context)
        && !context.interactions?.hasPanSession()
        && (context.store.hasUnsavedChanges()
          || Boolean(context.positionInspector?.hasPendingDraft())),
      disabledReason: (context) => context.positionInspector?.hasInvalidDraft()
        ? "Corrige la posición inválida antes de guardar."
        : "No hay cambios confirmados para guardar.",
      execute: async (context) => {
        context.nudgeController?.finish();
        if (context.positionInspector?.hasPendingDraft()
            && !context.positionInspector.confirmPending()) {
          return false;
        }
        return context.saveCoordinator.manualSave();
      },
    });

    registry.register({
      id: ACTION_IDS.UNDO,
      label: "Deshacer",
      category: "history",
      description: "Deshace el último comando reversible.",
      shortcuts: ["Mod+Z"],
      help: [{ keys: "Ctrl/Cmd+Z", label: "Deshacer" }],
      modifiesLayout: true,
      enabled: (context) => Boolean(context.store.undoStack.length)
        || Boolean(context.nudgeController?.isActive()),
      execute: (context) => {
        context.positionInspector?.cancelPending(false);
        context.nudgeController?.finish();
        return context.store.undo();
      },
    });

    registry.register({
      id: ACTION_IDS.REDO,
      label: "Rehacer",
      category: "history",
      description: "Rehace el último comando reversible deshecho.",
      shortcuts: ["Mod+Shift+Z", "Ctrl+Y"],
      help: [{ keys: "Ctrl/Cmd+Shift+Z o Ctrl+Y", label: "Rehacer" }],
      modifiesLayout: true,
      enabled: (context) => Boolean(context.store.redoStack.length)
        || Boolean(context.nudgeController?.isActive()),
      execute: (context) => {
        context.positionInspector?.cancelPending(false);
        context.nudgeController?.finish();
        return context.store.redo();
      },
    });

    registry.register({
      id: ACTION_IDS.MOVE_ABSOLUTE,
      label: "Aplicar posición absoluta",
      category: "selection",
      description: "Mueve el centro trim de un slot a X/Y exactos.",
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedSlots(context).length === 1
        && blockedMoveIds(context).length === 0
        && !context.store.pointerSession
        && !context.interactions?.hasPanSession(),
      disabledReason: moveDisabledReason,
      execute: (context, payload) => {
        context.nudgeController?.finish();
        const plan = context.positioning.buildMovePlan(
          context.store.layout,
          selectedIds(context),
          "absolute",
          payload,
        );
        if (!plan.changed) return Object.freeze({ changed: false, affectedIds: [] });
        context.store.executeCommand(
          new context.commands.MoveSlotsCommand(plan.beforePositions, plan.afterPositions),
        );
        return Object.freeze({ changed: true, affectedIds: plan.affectedIds });
      },
    });

    registry.register({
      id: ACTION_IDS.MOVE_DELTA,
      label: "Aplicar desplazamiento",
      category: "selection",
      description: "Desplaza atómicamente una multiselección por Delta X/Y.",
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedSlots(context).length >= 2
        && blockedMoveIds(context).length === 0
        && !context.store.pointerSession
        && !context.interactions?.hasPanSession(),
      disabledReason: moveDisabledReason,
      execute: (context, payload) => {
        context.nudgeController?.finish();
        const plan = context.positioning.buildMovePlan(
          context.store.layout,
          selectedIds(context),
          "delta",
          payload,
        );
        if (!plan.changed) return Object.freeze({ changed: false, affectedIds: [] });
        context.store.executeCommand(
          new context.commands.MoveSlotsCommand(plan.beforePositions, plan.afterPositions),
        );
        return Object.freeze({ changed: true, affectedIds: plan.affectedIds });
      },
    });

    registry.register({
      id: ACTION_IDS.NUDGE,
      label: "Mover con flechas",
      category: "selection",
      description: "Previsualiza una ráfaga y la confirma como un solo movimiento.",
      shortcuts: [
        "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
        "Shift+ArrowLeft", "Shift+ArrowRight", "Shift+ArrowUp", "Shift+ArrowDown",
        "Mod+Shift+ArrowLeft", "Mod+Shift+ArrowRight",
        "Mod+Shift+ArrowUp", "Mod+Shift+ArrowDown",
      ],
      help: [
        { keys: "Flechas", label: "Mover 0,1 mm" },
        { keys: "Shift+Flechas", label: "Mover 1 mm" },
        { keys: "Ctrl/Cmd+Shift+Flechas", label: "Mover 10 mm" },
      ],
      modifiesLayout: true,
      requiresSelection: true,
      allowDuringPointer: "nudge",
      shortcutPayload: (shortcut, event) => ({ ...nudgePayload(shortcut), repeat: Boolean(event.repeat) }),
      enabled: (context) => selectedSlots(context).length > 0
        && blockedMoveIds(context).length === 0
        && !hasIncompatiblePointerSession(context)
        && !context.interactions?.hasPanSession()
        && !context.positionInspector?.hasInvalidDraft(),
      disabledReason: moveDisabledReason,
      execute: (context, payload) => context.nudgeController.handleKeyDown(payload),
    });

    registry.register({
      id: ACTION_IDS.ROTATE_CLOCKWISE,
      label: "Rotar +90°",
      category: "objects",
      description: "Suma 90° cardinales a la geometría seleccionada.",
      shortcuts: ["R"],
      help: [{ keys: "R", label: "Rotar +90°" }],
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0
        && blockedIds(context, "rotate").length === 0
        && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, "rotate", "rotar"),
      execute: (context) => {
        context.nudgeController?.finish();
        const command = new context.commands.RotateSlotsCommand(
          context.store.layout,
          selectedIds(context),
          (rotation) => rotation + 90,
        );
        context.store.executeCommand(command);
        context.store.setFeedback(`Rotación aplicada a ${command.affectedIds.length} slot(s).`);
        return command;
      },
    });

    registry.register({
      id: ACTION_IDS.ROTATE_COUNTERCLOCKWISE,
      label: "Rotar -90°",
      category: "objects",
      description: "Resta 90° cardinales a la geometría seleccionada.",
      shortcuts: ["Shift+R"],
      help: [{ keys: "Shift+R", label: "Rotar -90°" }],
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0
        && blockedIds(context, "rotate").length === 0
        && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, "rotate", "rotar"),
      execute: (context) => {
        context.nudgeController?.finish();
        const command = new context.commands.RotateSlotsCommand(
          context.store.layout,
          selectedIds(context),
          (rotation) => rotation - 90,
        );
        context.store.executeCommand(command);
        context.store.setFeedback(`Rotación aplicada a ${command.affectedIds.length} slot(s).`);
        return command;
      },
    });

    registry.register({
      id: ACTION_IDS.ROTATE_SET,
      label: "Establecer rotación cardinal",
      category: "objects",
      description: "Establece 0°, 90°, 180° o 270° sin cambiar centro ni trim.",
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0
        && blockedIds(context, "rotate").length === 0
        && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, "rotate", "rotar"),
      execute: (context, payload) => {
        context.nudgeController?.finish();
        const target = context.commands.normalizeCardinalRotation(Number(payload?.rotation));
        const slots = selectedSlots(context);
        if (slots.every((slot) => slot.geometry.rotation_deg === target)) {
          return Object.freeze({ changed: false, affectedIds: [] });
        }
        const command = new context.commands.RotateSlotsCommand(
          context.store.layout,
          selectedIds(context),
          target,
        );
        context.store.executeCommand(command);
        context.store.setFeedback(`Rotación establecida en ${target}°.`);
        return Object.freeze({ changed: true, affectedIds: command.affectedIds });
      },
    });

    registry.register({
      id: ACTION_IDS.DUPLICATE,
      label: "Duplicar",
      category: "objects",
      description: "Duplica la selección con offset de 5 mm sin modificar originales.",
      shortcuts: ["Mod+D"],
      help: [{ keys: "Ctrl/Cmd+D", label: "Duplicar selección" }],
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, null, "duplicar"),
      execute: (context) => {
        context.nudgeController?.finish();
        const command = new context.commands.DuplicateSlotsCommand(
          context.store.layout,
          selectedIds(context),
          {
            offset: context.objectOperations.DUPLICATE_OFFSET_MM,
            selectionBefore: selectedIds(context),
          },
        );
        context.store.executeCommand(command);
        context.store.setFeedback(`Copias creadas: ${command.affectedIds.join(", ")}.`);
        return command;
      },
    });

    registry.register({
      id: ACTION_IDS.COPY,
      label: "Copiar",
      category: "clipboard",
      description: "Copia profundamente slots al clipboard interno del job.",
      shortcuts: ["Mod+C"],
      help: [{ keys: "Ctrl/Cmd+C", label: "Copiar selección" }],
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, null, "copiar"),
      execute: (context) => {
        const clipboard = context.objectOperations.copySelection(context.store);
        context.store.setFeedback(`${clipboard.slots.length} slot(s) copiado(s) al clipboard interno.`);
        return clipboard;
      },
    });

    registry.register({
      id: ACTION_IDS.CUT,
      label: "Cortar",
      category: "clipboard",
      description: "Copia y elimina atómicamente la selección respetando locks delete.",
      shortcuts: ["Mod+X"],
      help: [{ keys: "Ctrl/Cmd+X", label: "Cortar selección" }],
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0
        && blockedIds(context, "delete").length === 0
        && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, "delete", "cortar"),
      execute: (context) => {
        context.nudgeController?.finish();
        if (blockUnselectedDeleteDependents(context)) return false;
        const command = new context.commands.DeleteSlotsCommand(
          context.store.layout,
          selectedIds(context),
        );
        const clipboard = context.objectOperations.clipboardPayload(context.store);
        context.store.setClipboard(clipboard);
        context.store.executeCommand(command);
        context.store.setFeedback(`${clipboard.slots.length} slot(s) cortado(s).`);
        return command;
      },
    });

    registry.register({
      id: ACTION_IDS.PASTE,
      label: "Pegar",
      category: "clipboard",
      description: "Pega copias del clipboard interno únicamente en el mismo job y cara.",
      shortcuts: ["Mod+V"],
      help: [{ keys: "Ctrl/Cmd+V", label: "Pegar desde clipboard interno" }],
      modifiesLayout: true,
      enabled: (context) => context.objectOperations.validateClipboard(
        context.store.layout,
        context.store.clipboard,
        context.store.activeFace,
      ).ok && objectActionReady(context),
      disabledReason: (context) => context.objectOperations.validateClipboard(
        context.store.layout,
        context.store.clipboard,
        context.store.activeFace,
      ).reason || objectDisabledReason(context, null, "pegar"),
      execute: (context) => {
        context.nudgeController?.finish();
        const prepared = context.objectOperations.createPasteCommand(
          context.store,
          context.commands,
        );
        context.store.executeCommand(prepared.command);
        context.store.setClipboardPasteCount(prepared.pasteCount);
        context.store.setFeedback(
          `Pegado ${prepared.pasteCount}: ${prepared.command.affectedIds.join(", ")}.`,
        );
        return prepared.command;
      },
    });

    registry.register({
      id: ACTION_IDS.DELETE,
      label: "Eliminar",
      category: "objects",
      description: "Elimina la selección como un comando reversible y atómico.",
      shortcuts: ["Delete"],
      help: [{ keys: "Delete", label: "Eliminar selección" }],
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0
        && blockedIds(context, "delete").length === 0
        && objectActionReady(context),
      disabledReason: (context) => objectDisabledReason(context, "delete", "eliminar"),
      execute: (context) => {
        context.nudgeController?.finish();
        if (blockUnselectedDeleteDependents(context)) return false;
        const command = new context.commands.DeleteSlotsCommand(
          context.store.layout,
          selectedIds(context),
        );
        context.store.executeCommand(command);
        context.store.setFeedback(`${command.affectedIds.length} slot(s) eliminado(s).`);
        return command;
      },
    });

    registry.register({
      id: ACTION_IDS.SELECT_ALL_FACE,
      label: "Seleccionar todos en la cara",
      category: "selection",
      description: "Selecciona todos los slots de la cara activa.",
      shortcuts: ["Mod+A"],
      help: [{ keys: "Ctrl/Cmd+A", label: "Seleccionar todos en la cara activa" }],
      enabled: (context) => visibleFaceIds(context).length > 0 && objectActionReady(context),
      execute: (context) => {
        const ids = context.objectOperations.selectAllFace(
          context.store.layout,
          context.store.activeFace,
          hiddenIds(context),
        );
        context.store.setSelection(ids, "replace");
        context.store.setFeedback(`${ids.length} slot(s) seleccionados en la cara activa.`);
        return ids;
      },
    });

    registry.register({
      id: ACTION_IDS.SELECT_SAME_WORK,
      label: "Seleccionar mismo work",
      category: "selection",
      description: "Selecciona la unión de works de la selección en la cara activa.",
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
      execute: (context) => {
        const ids = context.objectOperations.selectSameWork(
          context.store.layout,
          selectedIds(context),
          context.store.activeFace,
          hiddenIds(context),
        );
        context.store.setSelection(ids, "replace");
        context.store.setFeedback(`${ids.length} slot(s) del mismo work seleccionados.`);
        return ids;
      },
    });

    registry.register({
      id: ACTION_IDS.SELECT_SAME_ASSET,
      label: "Seleccionar mismo asset",
      category: "selection",
      description: "Selecciona por asset efectivo del slot en la cara activa.",
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
      execute: (context) => {
        const ids = context.objectOperations.selectSameAsset(
          context.store.layout,
          selectedIds(context),
          context.store.activeFace,
          hiddenIds(context),
        );
        context.store.setSelection(ids, "replace");
        context.store.setFeedback(`${ids.length} slot(s) del mismo asset efectivo seleccionados.`);
        return ids;
      },
    });

    for (const [id, criterion, label] of [
      [ACTION_IDS.SELECT_SAME_SIZE, "size", "Mismo tamaño trim"],
      [ACTION_IDS.SELECT_SAME_ROTATION, "rotation", "Misma rotación"],
      [ACTION_IDS.SELECT_SAME_PROVENANCE, "provenance", "Misma procedencia"],
    ]) {
      registry.register({
        id,
        label,
        category: "selection",
        description: `${label} en los slots visibles de la cara activa.`,
        requiresSelection: true,
        enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
        execute: (context) => replaceSelection(
          context,
          context.advancedSelection.selectSimilar(
            context.store.layout,
            selectedIds(context),
            context.store.activeFace,
            hiddenIds(context),
            criterion,
          ),
          label,
        ),
      });
    }

    for (const [id, surface, label] of [
      [ACTION_IDS.SELECT_LOCKED_GEOMETRY, "geometry", "Locks efectivos de geometría"],
      [ACTION_IDS.SELECT_LOCKED_CONTENT, "content", "Locks efectivos de contenido"],
      [ACTION_IDS.SELECT_LOCKED_DELETE, "delete", "Locks efectivos de eliminación"],
    ]) {
      registry.register({
        id,
        label,
        category: "selection",
        description: `${label}, con cualquier fuente válida.`,
        enabled: (context) => objectActionReady(context),
        execute: (context) => replaceSelection(
          context,
          context.advancedSelection.selectLocked(
            context.store.layout,
            context.store.activeFace,
            hiddenIds(context),
            surface,
          ),
          label,
        ),
      });
    }

    for (const [id, issue, label] of [
      [ACTION_IDS.SELECT_OUTSIDE_SHEET, "outside_sheet", "Fuera del pliego"],
      [ACTION_IDS.SELECT_OUTSIDE_PRINTABLE, "outside_printable", "Fuera del área imprimible"],
      [ACTION_IDS.SELECT_OVERLAPS, "overlap", "Participantes de overlap"],
      [ACTION_IDS.SELECT_GEOMETRY_ISSUES, "any", "Cualquier problema geométrico"],
    ]) {
      registry.register({
        id,
        label,
        category: "selection",
        description: `${label} según la geometría vigente y visible.`,
        enabled: (context) => objectActionReady(context),
        execute: (context) => replaceSelection(context, geometryIssueIds(context, issue), label),
      });
    }

    registry.register({
      id: ACTION_IDS.SELECT_FACE_VISIBLE,
      label: "Seleccionar cara visible",
      category: "selection",
      description: "Selecciona los slots visibles de la cara activa.",
      enabled: (context) => visibleFaceIds(context).length > 0 && objectActionReady(context),
      execute: (context) => replaceSelection(context, visibleFaceIds(context), "Cara activa"),
    });

    registry.register({
      id: ACTION_IDS.SELECT_WORK_VISIBLE,
      label: "Seleccionar work visible",
      category: "selection",
      description: "Selecciona los slots visibles de un work en la cara activa.",
      enabled: (context) => objectActionReady(context),
      execute: (context, payload) => {
        const workId = String(payload?.workId || "");
        const ids = context.advancedSelection.visibleSlots(
          context.store.layout,
          context.store.activeFace,
          hiddenIds(context),
        ).filter((slot) => slot.work_id === workId).map((slot) => slot.id);
        return replaceSelection(context, ids, `Work ${workId}`);
      },
    });

    registry.register({
      id: ACTION_IDS.MARQUEE_MODE_SET,
      label: "Cambiar modo marquee",
      category: "selection",
      description: "Cambia entre inclusión completa e intersección sin persistirlo.",
      enabled: (context) => objectActionReady(context),
      execute: (context, payload) => {
        context.store.setMarqueeMode(payload?.mode);
        context.store.setFeedback(
          payload?.mode === "contain" ? "Marquee: dentro completamente." : "Marquee: tocar/intersectar.",
        );
        return payload?.mode;
      },
    });

    registry.register({
      id: ACTION_IDS.CYCLE_AT_POINT,
      label: "Ciclar objetos bajo el punto",
      category: "selection",
      description: "Selecciona el siguiente slot visible según el orden real de render.",
      enabled: (context) => Boolean(context.advancedSelection && context.geometry)
        && objectActionReady(context),
      execute: (context, payload) => {
        const result = context.advancedSelection.cycleAtPoint({
          layout: context.store.layout,
          activeFace: context.store.activeFace,
          hiddenSlotIds: hiddenIds(context),
          geometry: context.geometry,
          reference: context.store.arrangement.geometryReference,
          point: payload?.point,
          currentSlotId: payload?.currentSlotId,
          previousCycle: context.store.advancedSelection.cycle,
          layoutVersion: context.store.changeVersion,
          visibilityVersion: context.store.advancedSelection.visibilityVersion,
        });
        context.store.setSelectionCycle(result.cycle);
        if (!result.selectedId) {
          context.store.setFeedback("No hay slots visibles bajo el punto.");
          return result;
        }
        context.store.setSelection([result.selectedId], payload?.additive ? "add" : "replace");
        const ordinal = context.store.layout.slots.findIndex((slot) => slot.id === result.selectedId) + 1;
        context.store.setFeedback(
          `Ciclo ${result.position}/${result.total}: #${ordinal} · ${result.selectedId}.`,
        );
        return result;
      },
    });

    registry.register({
      id: ACTION_IDS.VISIBILITY_HIDE_SELECTION,
      label: "Ocultar seleccionados",
      category: "visibility",
      description: "Oculta temporalmente la selección solo en vista.",
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0,
      execute: (context) => {
        cancelVisibilityDependentSession(context);
        const ids = selectedIds(context);
        context.store.hideSlots(ids, { capturePrevious: true });
        context.store.setFeedback(`${ids.length} slot(s) ocultos solo en vista.`);
        return ids;
      },
    });

    registry.register({
      id: ACTION_IDS.VISIBILITY_ISOLATE_SELECTION,
      label: "Aislar selección",
      category: "visibility",
      description: "Oculta temporalmente los demás slots visibles de la cara activa.",
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0,
      execute: (context) => {
        cancelVisibilityDependentSession(context);
        const selected = new Set(selectedIds(context));
        const next = new Set(hiddenIds(context));
        for (const slot of context.store.layout.slots) {
          if (slot.face === context.store.activeFace && !selected.has(slot.id)) next.add(slot.id);
        }
        context.store.setHiddenSlotIds(next, { capturePrevious: true });
        context.store.setFeedback(`Selección aislada: ${selected.size} slot(s) visibles.`);
        return [...selected];
      },
    });

    registry.register({
      id: ACTION_IDS.VISIBILITY_SHOW_ALL,
      label: "Mostrar todos",
      category: "visibility",
      description: "Muestra todos los slots de la cara activa.",
      enabled: (context) => context.store.layout.slots.some(
        (slot) => slot.face === context.store.activeFace && hiddenIds(context).has(slot.id),
      ),
      execute: (context) => {
        cancelVisibilityDependentSession(context);
        const next = new Set(hiddenIds(context));
        for (const slot of context.store.layout.slots) {
          if (slot.face === context.store.activeFace) next.delete(slot.id);
        }
        context.store.setHiddenSlotIds(next, { capturePrevious: true });
        context.store.setFeedback("Todos los slots de la cara activa están visibles.");
        return true;
      },
    });

    registry.register({
      id: ACTION_IDS.VISIBILITY_RESTORE_PREVIOUS,
      label: "Restaurar visibilidad anterior",
      category: "visibility",
      description: "Restaura la única instantánea temporal de visibilidad.",
      enabled: (context) => Boolean(context.store.advancedSelection.previousHiddenSlotIds),
      execute: (context) => {
        cancelVisibilityDependentSession(context);
        const changed = context.store.restorePreviousVisibility();
        context.store.setFeedback(changed ? "Visibilidad anterior restaurada." : "No hay visibilidad anterior distinta.");
        return changed;
      },
    });

    registry.register({
      id: ACTION_IDS.VISIBILITY_SLOT_TOGGLE,
      label: "Alternar visibilidad de slot",
      category: "visibility",
      description: "Muestra u oculta temporalmente un slot desde el árbol.",
      enabled: (context) => Boolean(context.store.layout.slots.length),
      execute: (context, payload) => {
        cancelVisibilityDependentSession(context);
        const slotId = String(payload?.slotId || "");
        const hidden = hiddenIds(context).has(slotId);
        if (hidden) context.store.showSlots([slotId]);
        else context.store.hideSlots([slotId]);
        context.store.setFeedback(`Slot ${slotId} ${hidden ? "visible" : "oculto solo en vista"}.`);
        return !hidden;
      },
    });

    registry.register({
      id: ACTION_IDS.VISIBILITY_WORK_TOGGLE,
      label: "Alternar visibilidad de work",
      category: "visibility",
      description: "Deriva y alterna la visibilidad temporal de un work.",
      enabled: (context) => Boolean(context.store.layout.slots.length),
      execute: (context, payload) => {
        cancelVisibilityDependentSession(context);
        const workId = String(payload?.workId || "");
        const ids = context.store.layout.slots
          .filter((slot) => slot.face === context.store.activeFace && slot.work_id === workId)
          .map((slot) => slot.id);
        const allHidden = ids.length > 0 && ids.every((id) => hiddenIds(context).has(id));
        if (allHidden) context.store.showSlots(ids, { capturePrevious: true });
        else context.store.hideSlots(ids, { capturePrevious: true });
        context.store.setFeedback(`Work ${workId}: ${allHidden ? "visible" : "oculto solo en vista"}.`);
        return !allHidden;
      },
    });

    registry.register({
      id: ACTION_IDS.USER_LOCKS_SET,
      label: "Cambiar locks de usuario",
      category: "objects",
      description: "Agrega o retira solamente la fuente user de una superficie.",
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
      execute: (context, payload) => {
        context.nudgeController?.finish();
        const surface = String(payload?.surface || "");
        const locked = Boolean(payload?.locked);
        const slots = selectedSlots(context);
        const state = context.objectOperations.userLockState(slots, surface);
        if ((locked && state === "all") || (!locked && state === "none")) {
          return Object.freeze({ changed: false, affectedIds: [] });
        }
        const command = new context.commands.SetSlotUserLocksCommand(
          context.store.layout,
          selectedIds(context),
          surface,
          locked,
        );
        context.store.executeCommand(command);
        const remaining = !locked
          ? context.objectOperations.remainingLockSources(selectedSlots(context), surface)
          : [];
        context.store.setFeedback(
          remaining.length
            ? `Lock user retirado; permanecen: ${remaining.join(", ")}.`
            : `${locked ? "Bloqueados" : "Desbloqueados"} ${command.affectedIds.length} slot(s) en ${surface}.`,
        );
        return Object.freeze({ changed: true, affectedIds: command.affectedIds });
      },
    });

    registry.register({
      id: ACTION_IDS.KEY_SLOT_SET,
      label: "Definir slot clave",
      category: "arrangement",
      description: "Define una referencia temporal dentro de la selección.",
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && objectActionReady(context),
      execute: (context, payload) => {
        const slotId = String(payload?.slotId || "");
        context.store.setKeySlot(slotId);
        context.store.setFeedback(`Slot clave definido: ${slotId}.`);
        return slotId;
      },
    });

    registry.register({
      id: ACTION_IDS.KEY_SLOT_CLEAR,
      label: "Retirar slot clave",
      category: "arrangement",
      description: "Retira la referencia temporal sin modificar el layout.",
      enabled: (context) => Boolean(context.store.arrangement.keySlotId),
      execute: (context) => {
        context.store.setKeySlot(null);
        context.store.setFeedback("Slot clave retirado.");
        return true;
      },
    });

    registerAlignmentAction(ACTION_IDS.ALIGN_LEFT, "Alinear a la izquierda", "left");
    registerAlignmentAction(ACTION_IDS.ALIGN_HORIZONTAL_CENTER, "Alinear centros horizontales", "horizontal_center");
    registerAlignmentAction(ACTION_IDS.ALIGN_RIGHT, "Alinear a la derecha", "right");
    registerAlignmentAction(ACTION_IDS.ALIGN_TOP, "Alinear arriba", "top");
    registerAlignmentAction(ACTION_IDS.ALIGN_VERTICAL_CENTER, "Alinear centros verticales", "vertical_center");
    registerAlignmentAction(ACTION_IDS.ALIGN_BOTTOM, "Alinear abajo", "bottom");
    registerAlignmentAction(ACTION_IDS.CENTER_HORIZONTAL, "Centrar horizontalmente", "horizontal_center");
    registerAlignmentAction(ACTION_IDS.CENTER_VERTICAL, "Centrar verticalmente", "vertical_center");
    registerAlignmentAction(ACTION_IDS.CENTER_BOTH, "Centrar en ambos ejes", "both");

    for (const [id, label, axis] of [
      [ACTION_IDS.DISTRIBUTE_HORIZONTAL, "Distribuir horizontalmente", "horizontal"],
      [ACTION_IDS.DISTRIBUTE_VERTICAL, "Distribuir verticalmente", "vertical"],
    ]) {
      registry.register({
        id,
        label,
        category: "arrangement",
        description: `${label} con gap uniforme y orden geométrico estable.`,
        modifiesLayout: true,
        requiresSelection: true,
        enabled: (context) => planEnabled(context, () => distributionPlan(context, axis)),
        disabledReason: (context) => planDisabledReason(
          context,
          () => distributionPlan(context, axis),
          "Distribuir requiere al menos tres slots, un destino compatible y geometría editable.",
        ),
        execute: (context) => {
          const plan = distributionPlan(context, axis);
          const overlap = plan.overlap ? " Se obtuvo un gap negativo determinista." : "";
          return executeMovePlan(
            context,
            plan,
            label,
            `${label}: gap ${plan.gapMm.toFixed(3)} mm.${overlap}`,
          );
        },
      });
    }

    for (const [id, label, axis] of [
      [ACTION_IDS.GAP_HORIZONTAL, "Aplicar gap horizontal", "horizontal"],
      [ACTION_IDS.GAP_VERTICAL, "Aplicar gap vertical", "vertical"],
    ]) {
      registry.register({
        id,
        label,
        category: "arrangement",
        description: `${label} con anclaje explícito.`,
        modifiesLayout: true,
        requiresSelection: true,
        enabled: (context) => selectedIds(context).length >= 2 && arrangementReady(context),
        disabledReason: () => "El gap exacto requiere al menos dos slots y una interacción libre.",
        execute: (context, payload) => {
          const plan = context.alignmentOperations.buildExactGapPlan(
            context.store.layout,
            selectedIds(context),
            context.geometry,
            arrangementOptions(context, {
              axis,
              anchor: payload?.anchor,
              gapMm: payload?.gapMm,
            }),
          );
          return executeMovePlan(context, plan, label, `${label}: ${plan.gapMm} mm.`);
        },
      });
    }

    registry.register({
      id: ACTION_IDS.MATRIX_CREATE,
      label: "Crear matriz",
      category: "arrangement",
      description: "Duplica la selección como celda fuente en una matriz determinista.",
      modifiesLayout: true,
      requiresSelection: true,
      enabled: (context) => selectedIds(context).length > 0 && arrangementReady(context),
      disabledReason: () => "La matriz requiere una selección y una interacción libre.",
      execute: (context, payload) => {
        context.nudgeController?.finish();
        const prepared = context.alignmentOperations.prepareMatrixCopies(
          context.store.layout,
          selectedIds(context),
          context.geometry,
          context.commands,
          arrangementOptions(context, payload),
        );
        const command = new context.commands.DuplicateSlotsCommand(
          context.store.layout,
          prepared.sourceIds,
          {
            description: `Crear matriz ${prepared.rows}×${prepared.columns}`,
            preparedSlots: prepared.copies,
            selectionBefore: selectedIds(context),
          },
        );
        context.store.executeCommand(command);
        context.store.setFeedback(
          `Matriz ${prepared.rows}×${prepared.columns}: ${prepared.newSlots} slots nuevos.`,
        );
        return Object.freeze({ changed: true, affectedIds: command.affectedIds, prepared });
      },
    });

    for (const [id, option, label] of [
      [ACTION_IDS.PRECISION_RULERS_TOGGLE, "rulersVisible", "Mostrar reglas"],
      [ACTION_IDS.PRECISION_GUIDES_TOGGLE, "guidesVisible", "Mostrar guías"],
      [ACTION_IDS.PRECISION_SMART_GUIDES_TOGGLE, "smartGuidesVisible", "Mostrar smart guides"],
      [ACTION_IDS.PRECISION_SNAP_TOGGLE, "snapEnabled", "Activar snap"],
    ]) {
      registry.register({
        id,
        label,
        category: "precision",
        description: `${label} como estado editorial temporal.`,
        enabled: () => true,
        execute: (context, payload) => context.store.setPrecisionOption(
          option,
          payload?.enabled ?? !context.store.precisionTools[option],
        ),
      });
    }

    registry.register({
      id: ACTION_IDS.PRECISION_SNAP_SOURCE_SET,
      label: "Configurar fuente de snap",
      category: "precision",
      description: "Activa o desactiva una fuente de snap temporal.",
      enabled: () => true,
      execute: (context, payload) => {
        const options = {
          guides: "snapToGuides",
          slots: "snapToSlots",
          sheet: "snapToSheet",
          printable: "snapToPrintable",
        };
        const option = options[payload?.source];
        if (!option) throw new Error(`Fuente de snap no válida: ${payload?.source}.`);
        return context.store.setPrecisionOption(option, payload?.enabled);
      },
    });

    registry.register({
      id: ACTION_IDS.PRECISION_SNAP_REFERENCE_SET,
      label: "Referencia de snap",
      category: "precision",
      description: "Reutiliza la referencia Trim/Footprint transversal.",
      enabled: () => true,
      execute: (context, payload) => context.store.setArrangementGeometryReference(
        payload?.reference,
      ),
    });

    registry.register({
      id: ACTION_IDS.PRECISION_SNAP_THRESHOLD_SET,
      label: "Umbral de snap",
      category: "precision",
      description: "Define el umbral temporal en píxeles de pantalla.",
      enabled: () => true,
      execute: (context, payload) => context.store.setSnapThresholdPx(payload?.pixels),
    });

    registry.register({
      id: ACTION_IDS.PRECISION_GUIDE_CREATE,
      label: "Crear guía",
      category: "precision",
      description: "Crea una guía temporal en milímetros.",
      enabled: () => true,
      execute: (context, payload) => {
        const ids = context.store.precisionTools.guides.map((item) => item.id);
        const id = payload?.id || context.precisionTools.nextGuideId(ids, payload?.token);
        const item = context.precisionTools.guide(payload?.axis, payload?.position_mm, id);
        context.store.createGuide(item);
        context.store.setFeedback(`Guía ${item.axis === "x" ? "vertical" : "horizontal"} en ${item.position_mm} mm.`);
        return item;
      },
    });

    registry.register({
      id: ACTION_IDS.PRECISION_GUIDE_UPDATE,
      label: "Mover guía",
      category: "precision",
      description: "Actualiza una guía temporal sin historial documental.",
      enabled: (context, payload) => context.store.precisionTools.guides.some(
        (item) => item.id === payload?.id,
      ),
      execute: (context, payload) => context.store.updateGuide(payload?.id, payload?.position_mm),
    });

    registry.register({
      id: ACTION_IDS.PRECISION_GUIDE_DELETE,
      label: "Eliminar guía",
      category: "precision",
      description: "Elimina una guía temporal.",
      enabled: (context, payload) => context.store.precisionTools.guides.some(
        (item) => item.id === payload?.id,
      ),
      execute: (context, payload) => context.store.deleteGuide(payload?.id),
    });

    registry.register({
      id: ACTION_IDS.PRECISION_GUIDES_CLEAR,
      label: "Eliminar todas las guías",
      category: "precision",
      description: "Vacía todas las guías temporales.",
      enabled: (context) => context.store.precisionTools.guides.length > 0,
      execute: (context) => context.store.clearGuides(),
    });

    registry.register({
      id: ACTION_IDS.PRECISION_MEASURE_TOGGLE,
      label: "Herramienta de medición",
      category: "precision",
      description: "Activa o desactiva medición punto a punto temporal.",
      enabled: () => true,
      execute: (context, payload) => context.store.setMeasurementMode(
        payload?.enabled ?? !context.store.precisionTools.measurementMode,
      ),
    });

    registry.register({
      id: ACTION_IDS.PRECISION_MEASURE_CLEAR,
      label: "Limpiar medición",
      category: "precision",
      description: "Limpia el resultado temporal de medición.",
      enabled: (context) => Boolean(
        context.store.precisionTools.measurementDraft
        || context.store.precisionTools.lastMeasurement,
      ),
      execute: (context) => context.store.clearMeasurement(),
    });

    registry.register({
      id: ACTION_IDS.HELP_TOGGLE,
      label: "Ayuda de atajos",
      category: "help",
      description: "Abre o cierra la ayuda temporal de atajos implementados.",
      shortcuts: ["?"],
      help: [{ keys: "?", label: "Abrir o cerrar esta ayuda" }],
      allowWhenHelpOpen: true,
      enabled: () => true,
      execute: (context) => {
        context.nudgeController?.finish();
        return context.shortcutHelp.toggle();
      },
    });

    registry.register({
      id: ACTION_IDS.CANCEL,
      label: "Cancelar",
      category: "general",
      description: "Cancela la interacción temporal de mayor prioridad.",
      shortcuts: ["Escape"],
      help: [{ keys: "Escape", label: "Cancelar o cerrar" }],
      allowWhenHelpOpen: true,
      allowDuringPointer: true,
      allowDuringPan: true,
      allowInEditable: (context, event) => Boolean(context.shortcutHelp?.isOpen())
        || Boolean(event.target?.closest?.("#ev2-position-form, .ev2-arrangement-form, .ev2-precision-form")),
      enabled: () => true,
      execute: (context) => {
        if (context.shortcutHelp?.isOpen()) return context.shortcutHelp.close();
        if (context.interactions?.hasPointerActivity()) {
          context.interactions.cancelPointer();
          return true;
        }
        if (context.store.precisionTools.measurementDraft) {
          return context.store.cancelMeasurementDraft();
        }
        if (context.precisionPanel?.cancelActiveDraft()) return true;
        if (context.nudgeController?.isActive()) return context.nudgeController.cancel();
        if (context.positionInspector?.hasPendingDraft()) {
          return context.positionInspector.cancelPending(true);
        }
        if (context.arrangementPanel?.hasPendingDraft()) {
          return context.arrangementPanel.cancelDraft(true);
        }
        return false;
      },
    });

    return registry;
  }

  return Object.freeze({
    ACTION_IDS,
    ActionRegistry,
    DisabledActionError,
    UnknownActionError,
    nudgePayload,
    registerEditorActions,
  });
});
