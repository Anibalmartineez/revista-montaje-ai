(function (root, factory) {
  "use strict";
  const api = factory(root);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ResponsivePanels = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  "use strict";

  const COMPACT_QUERY = "(max-width: 1180px)";
  const PANEL_NAMES = Object.freeze(["sources", "inspector"]);

  function panelForStage(stage) {
    return String(stage || "").toLowerCase() === "prepare" ? "sources" : "inspector";
  }

  function validPanelName(name) {
    return PANEL_NAMES.includes(name) ? name : null;
  }

  class Controller {
    constructor(refs, options) {
      this.refs = refs;
      this.options = options || {};
      this.mediaQuery = this.options.mediaQuery
        || root.matchMedia?.(COMPACT_QUERY)
        || { matches: false };
      this.activePanel = null;
      this.lastTrigger = null;
      this.listeners = [];
      this.onMediaChange = () => this.syncMode();
      this.bind();
      this.syncMode();
    }

    listen(element, type, listener) {
      if (!element) return;
      element.addEventListener(type, listener);
      this.listeners.push(() => element.removeEventListener(type, listener));
    }

    panelElement(name) {
      return name === "sources" ? this.refs.objectsRegion : this.refs.inspectorRegion;
    }

    toggleElement(name) {
      return name === "sources"
        ? this.refs.responsiveSourcesToggle
        : this.refs.responsiveInspectorToggle;
    }

    closeElement(name) {
      return name === "sources"
        ? this.refs.responsiveSourcesClose
        : this.refs.responsiveInspectorClose;
    }

    isCompact() {
      return Boolean(this.mediaQuery.matches);
    }

    isOpen(name) {
      if (!this.activePanel) return false;
      return name ? this.activePanel === name : true;
    }

    setPanelState(name, open) {
      const panel = this.panelElement(name);
      const toggle = this.toggleElement(name);
      panel.classList.toggle("is-responsive-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      if (this.isCompact()) {
        panel.inert = !open;
        panel.setAttribute("aria-hidden", String(!open));
      } else {
        panel.inert = false;
        panel.removeAttribute("aria-hidden");
      }
    }

    open(name, options) {
      const normalized = validPanelName(name);
      if (!normalized || !this.isCompact()) return false;
      const settings = options || {};
      if (settings.trigger) this.lastTrigger = settings.trigger;
      for (const panelName of PANEL_NAMES) {
        this.setPanelState(panelName, panelName === normalized);
      }
      this.activePanel = normalized;
      this.refs.responsivePanelBackdrop.hidden = false;
      if (settings.focus === true) {
        this.closeElement(normalized).focus({ preventScroll: true });
      }
      return true;
    }

    close(options) {
      const wasOpen = Boolean(this.activePanel);
      const settings = options || {};
      for (const name of PANEL_NAMES) this.setPanelState(name, false);
      this.activePanel = null;
      this.refs.responsivePanelBackdrop.hidden = true;
      if (wasOpen && settings.restoreFocus !== false && this.lastTrigger?.focus) {
        this.lastTrigger.focus({ preventScroll: true });
      }
      this.lastTrigger = null;
      return wasOpen;
    }

    toggle(name, trigger) {
      if (this.isOpen(name)) return this.close({ restoreFocus: true });
      return this.open(name, { trigger, focus: true });
    }

    openForStage(stage, trigger) {
      return this.open(panelForStage(stage), { trigger, focus: false });
    }

    syncMode() {
      if (!this.isCompact()) {
        this.activePanel = null;
        this.lastTrigger = null;
        this.refs.responsivePanelBackdrop.hidden = true;
      }
      for (const name of PANEL_NAMES) {
        this.setPanelState(name, this.isCompact() && this.activePanel === name);
      }
    }

    bind() {
      this.listen(this.refs.responsiveSourcesToggle, "click", (event) => {
        this.toggle("sources", event.currentTarget);
      });
      this.listen(this.refs.responsiveInspectorToggle, "click", (event) => {
        this.toggle("inspector", event.currentTarget);
      });
      this.listen(this.refs.responsiveSourcesClose, "click", () => {
        this.close({ restoreFocus: true });
      });
      this.listen(this.refs.responsiveInspectorClose, "click", () => {
        this.close({ restoreFocus: true });
      });
      this.listen(this.refs.responsivePanelBackdrop, "click", () => {
        this.close({ restoreFocus: true });
      });
      if (this.mediaQuery.addEventListener) {
        this.mediaQuery.addEventListener("change", this.onMediaChange);
        this.listeners.push(() => this.mediaQuery.removeEventListener("change", this.onMediaChange));
      } else if (this.mediaQuery.addListener) {
        this.mediaQuery.addListener(this.onMediaChange);
        this.listeners.push(() => this.mediaQuery.removeListener(this.onMediaChange));
      }
    }

    destroy() {
      for (const remove of this.listeners.splice(0)) remove();
      this.close({ restoreFocus: false });
    }
  }

  return Object.freeze({
    COMPACT_QUERY,
    PANEL_NAMES,
    Controller,
    panelForStage,
    validPanelName,
  });
});
