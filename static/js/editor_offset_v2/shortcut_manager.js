(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ShortcutManager = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const MODIFIER_ORDER = Object.freeze(["Ctrl", "Meta", "Alt", "Shift"]);
  const EDITABLE_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);
  const EDITABLE_ROLES = new Set(["textbox", "searchbox", "combobox", "spinbutton"]);

  class ShortcutConflictError extends Error {
    constructor(shortcut, firstActionId, secondActionId) {
      super(`Shortcut ${shortcut} conflicts between ${firstActionId} and ${secondActionId}`);
      this.name = "ShortcutConflictError";
      this.code = "SHORTCUT_CONFLICT";
      this.shortcut = shortcut;
      this.actionIds = Object.freeze([firstActionId, secondActionId]);
    }
  }

  function normalizedKey(key, code) {
    if (key === "Esc") return "Escape";
    if (key === " " || key === "Spacebar" || code === "Space") return "Space";
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Escape", "Enter", "Delete", "Backspace"].includes(key)) {
      return key;
    }
    if (key === "?") return "?";
    if (typeof key === "string" && key.length === 1 && /[a-z0-9]/i.test(key)) {
      return key.toUpperCase();
    }
    return key || code || "";
  }

  function canonicalShortcut(modifiers, key) {
    if (key === "?") return "?";
    return [...MODIFIER_ORDER.filter((modifier) => modifiers.has(modifier)), key]
      .filter(Boolean)
      .join("+");
  }

  function normalizeKeyboardEvent(event) {
    const key = event?.key === "/" && event?.shiftKey
      ? "?"
      : normalizedKey(event?.key, event?.code);
    const modifiers = new Set();
    if (event?.ctrlKey) modifiers.add("Ctrl");
    if (event?.metaKey) modifiers.add("Meta");
    if (event?.altKey) modifiers.add("Alt");
    if (event?.shiftKey && key !== "?") modifiers.add("Shift");
    return canonicalShortcut(modifiers, key);
  }

  function normalizeShortcutDefinition(definition) {
    const raw = String(definition || "").trim();
    if (!raw) throw new Error("Shortcut definition must not be empty");
    if (raw === "?") return "?";
    const parts = raw.split("+").map((part) => part.trim()).filter(Boolean);
    const keyToken = parts.pop();
    const key = normalizedKey(keyToken, keyToken);
    const modifiers = new Set();
    let hasMod = false;
    for (const token of parts) {
      const lower = token.toLowerCase();
      if (lower === "mod") hasMod = true;
      else if (["ctrl", "control"].includes(lower)) modifiers.add("Ctrl");
      else if (["meta", "cmd", "command"].includes(lower)) modifiers.add("Meta");
      else if (lower === "alt") modifiers.add("Alt");
      else if (lower === "shift") modifiers.add("Shift");
      else throw new Error(`Unknown shortcut modifier: ${token}`);
    }
    const prefix = [hasMod ? "Mod" : null, ...MODIFIER_ORDER.filter((item) => modifiers.has(item))]
      .filter(Boolean);
    return [...prefix, key].join("+");
  }

  function expandShortcutDefinition(definition) {
    const normalized = normalizeShortcutDefinition(definition);
    if (!normalized.startsWith("Mod+")) return [normalized];
    const suffix = normalized.slice(4);
    return [`Ctrl+${suffix}`, `Meta+${suffix}`];
  }

  function elementIsEditable(element) {
    if (!element || typeof element !== "object") return false;
    const tagName = String(element.tagName || "").toUpperCase();
    if (EDITABLE_TAGS.has(tagName)) return true;
    if (element.isContentEditable === true) return true;
    const contentEditable = element.getAttribute?.("contenteditable");
    if (contentEditable !== null && contentEditable !== undefined
        && String(contentEditable).toLowerCase() !== "false") return true;
    const role = String(element.getAttribute?.("role") || element.role || "").toLowerCase();
    if (EDITABLE_ROLES.has(role)) return true;
    const capture = element.getAttribute?.("data-editor-captures-keyboard")
      ?? element.dataset?.editorCapturesKeyboard;
    return String(capture).toLowerCase() === "true";
  }

  function isEditableTarget(target) {
    let element = target;
    while (element) {
      if (elementIsEditable(element)) return true;
      element = element.parentElement || element.parentNode || null;
    }
    return false;
  }

  function scopeAllows(action, event, context) {
    const helpOpen = Boolean(context.shortcutHelp?.isOpen());
    if (helpOpen && !action.allowWhenHelpOpen) return false;
    if (isEditableTarget(event.target)) {
      const allowed = typeof action.allowInEditable === "function"
        ? action.allowInEditable(context, event)
        : action.allowInEditable;
      if (!allowed) return false;
    }
    if (context.interactions?.hasPanSession() && !action.allowDuringPan) return false;
    const pointerType = context.store.pointerSession?.type;
    if (pointerType) {
      const allowedPointer = action.allowDuringPointer === true
        || action.allowDuringPointer === pointerType;
      if (!allowedPointer) return false;
    }
    return true;
  }

  class Manager {
    constructor(registry, contextProvider, hooks) {
      this.registry = registry;
      this.contextProvider = contextProvider;
      this.hooks = hooks || {};
      this.shortcuts = new Map();
      this.refresh();
      this.boundKeyDown = (event) => this.handleKeyDown(event);
      this.boundKeyUp = (event) => this.handleKeyUp(event);
      this.boundBlur = () => this.handleBlur();
      if (typeof window !== "undefined") {
        window.addEventListener("keydown", this.boundKeyDown);
        window.addEventListener("keyup", this.boundKeyUp);
        window.addEventListener("blur", this.boundBlur);
      }
    }

    refresh() {
      this.shortcuts.clear();
      for (const action of this.registry.list()) {
        for (const definition of action.shortcuts) {
          for (const shortcut of expandShortcutDefinition(definition)) {
            const previous = this.shortcuts.get(shortcut);
            if (previous && previous.action.id !== action.id) {
              throw new ShortcutConflictError(shortcut, previous.action.id, action.id);
            }
            this.shortcuts.set(shortcut, { action, definition });
          }
        }
      }
    }

    resolve(event, context) {
      const shortcut = normalizeKeyboardEvent(event);
      const match = this.shortcuts.get(shortcut) || null;
      if (!match || !scopeAllows(match.action, event, context)) return null;
      return { ...match, shortcut };
    }

    handleKeyDown(event) {
      const context = this.contextProvider();
      const editable = isEditableTarget(event.target);
      const noModifiers = !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey;
      if (normalizeKeyboardEvent(event) === "Space" && noModifiers && !editable
          && !context.shortcutHelp?.isOpen() && !context.store.pointerSession) {
        event.preventDefault?.();
        this.hooks.setSpacePressed?.(true);
        return true;
      }
      if (["Delete", "Backspace"].includes(event.key) && noModifiers && !editable
          && !context.shortcutHelp?.isOpen() && !context.store.pointerSession
          && !context.interactions?.hasPanSession()) {
        const handled = this.hooks.deleteSelection?.();
        if (handled) event.preventDefault?.();
        return Boolean(handled);
      }

      const match = this.resolve(event, context);
      if (!match) return false;
      event.preventDefault?.();
      const payload = typeof match.action.shortcutPayload === "function"
        ? match.action.shortcutPayload(match.shortcut, event)
        : { shortcut: match.shortcut, repeat: Boolean(event.repeat) };
      try {
        this.registry.execute(match.action.id, context, payload);
      } catch (error) {
        if (error?.code === "EDITOR_ACTION_DISABLED") {
          context.store.setFeedback(error.message);
          return true;
        }
        throw error;
      }
      return true;
    }

    handleKeyUp(event) {
      const key = normalizedKey(event.key, event.code);
      if (key === "Space") {
        this.hooks.setSpacePressed?.(false);
        return true;
      }
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(key)) {
        return Boolean(this.contextProvider().nudgeController?.handleKeyUp(key));
      }
      return false;
    }

    handleBlur() {
      this.hooks.setSpacePressed?.(false);
      this.contextProvider().nudgeController?.finish();
      this.hooks.onBlur?.();
    }

    dispose() {
      if (typeof window !== "undefined") {
        window.removeEventListener("keydown", this.boundKeyDown);
        window.removeEventListener("keyup", this.boundKeyUp);
        window.removeEventListener("blur", this.boundBlur);
      }
    }
  }

  class ShortcutHelp {
    constructor(refs, registry) {
      this.refs = refs;
      this.registry = registry;
      this.previousFocus = null;
      this.boundClose = () => this.close();
      this.boundCancel = (event) => {
        event.preventDefault();
        this.close();
      };
      refs.shortcutsHelpClose.addEventListener("click", this.boundClose);
      refs.shortcutsHelp.addEventListener("cancel", this.boundCancel);
      this.render();
    }

    entries() {
      const entries = this.registry.list().flatMap((action) => action.help);
      entries.push({ keys: "Enter", label: "Confirmar el inspector de posición" });
      const seen = new Set();
      return entries.filter((entry) => {
        const key = `${entry.keys}\0${entry.label}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    }

    render() {
      this.refs.shortcutsHelpList.replaceChildren();
      for (const entry of this.entries()) {
        const row = document.createElement("div");
        const term = document.createElement("dt");
        const description = document.createElement("dd");
        const keys = document.createElement("kbd");
        keys.textContent = entry.keys;
        term.append(keys);
        description.textContent = entry.label;
        row.append(term, description);
        this.refs.shortcutsHelpList.append(row);
      }
    }

    isOpen() {
      return Boolean(this.refs.shortcutsHelp.open);
    }

    open() {
      if (this.isOpen()) return false;
      this.previousFocus = document.activeElement;
      this.render();
      this.refs.shortcutsHelp.showModal();
      this.refs.shortcutsHelpClose.focus();
      return true;
    }

    close() {
      if (!this.isOpen()) return false;
      this.refs.shortcutsHelp.close();
      if (this.previousFocus?.focus) this.previousFocus.focus();
      this.previousFocus = null;
      return true;
    }

    toggle() {
      return this.isOpen() ? this.close() : this.open();
    }

    dispose() {
      this.refs.shortcutsHelpClose.removeEventListener("click", this.boundClose);
      this.refs.shortcutsHelp.removeEventListener("cancel", this.boundCancel);
    }
  }

  return Object.freeze({
    Manager,
    ShortcutConflictError,
    ShortcutHelp,
    elementIsEditable,
    expandShortcutDefinition,
    isEditableTarget,
    normalizeKeyboardEvent,
    normalizeShortcutDefinition,
    scopeAllows,
  });
});
