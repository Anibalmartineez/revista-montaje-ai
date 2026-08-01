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

    isEnabled(actionId, context) {
      const action = this.get(actionId);
      return Boolean(action && action.enabled(context));
    }

    execute(actionId, context, payload) {
      const action = this.get(actionId);
      if (!action) throw new UnknownActionError(actionId);
      if (!action.enabled(context)) {
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
      enabled: (context) => context.store.layout.slots.some(
        (slot) => slot.face === context.store.activeFace,
      ) && objectActionReady(context),
      execute: (context) => {
        const ids = context.objectOperations.selectAllFace(
          context.store.layout,
          context.store.activeFace,
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
        );
        context.store.setSelection(ids, "replace");
        context.store.setFeedback(`${ids.length} slot(s) del mismo asset efectivo seleccionados.`);
        return ids;
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
        || Boolean(event.target?.closest?.("#ev2-position-form, .ev2-arrangement-form")),
      enabled: () => true,
      execute: (context) => {
        if (context.shortcutHelp?.isOpen()) return context.shortcutHelp.close();
        if (context.interactions?.hasPointerActivity()) {
          context.interactions.cancelPointer();
          return true;
        }
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
