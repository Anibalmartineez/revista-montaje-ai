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
        || Boolean(event.target?.closest?.("#ev2-position-form")),
      enabled: () => true,
      execute: (context) => {
        if (context.shortcutHelp?.isOpen()) return context.shortcutHelp.close();
        if (context.nudgeController?.isActive()) return context.nudgeController.cancel();
        if (context.positionInspector?.hasPendingDraft()) {
          return context.positionInspector.cancelPending(true);
        }
        if (context.interactions?.hasPointerActivity()) {
          context.interactions.cancelPointer();
          return true;
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
