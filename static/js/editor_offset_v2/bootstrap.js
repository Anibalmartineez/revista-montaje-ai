(function (root, factory) {
  "use strict";
  const api = factory(root);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.Bootstrap = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  "use strict";

  function parseContext(element) {
    const context = JSON.parse(element.textContent || "{}");
    if (!context || typeof context !== "object") {
      throw new Error("El contexto inicial del Editor V2 no es válido.");
    }
    return context;
  }

  function developmentToken() {
    const random = Math.random().toString(36).slice(2, 8);
    return `${Date.now().toString(36)}_${random}`;
  }

  function showBootstrapError(refs, error) {
    refs.statusMessage.textContent = error && error.message
      ? error.message
      : "No se pudo iniciar el Editor V2.";
  }

  function start() {
    const modules = root.EditorOffsetV2;
    const refs = modules.DomRefs.collect();
    const context = parseContext(refs.context);
    const api = new modules.ApiClient.EditorApiClient();

    refs.newJob.addEventListener("click", async () => {
      refs.newJob.disabled = true;
      refs.statusMessage.textContent = "Creando job V2…";
      try {
        const response = await api.createJob(context.create_job_url);
        window.location.assign(response.open_url);
      } catch (error) {
        showBootstrapError(refs, error);
        refs.newJob.disabled = false;
      }
    });

    if (!context.layout || !context.job_id) {
      refs.statusMessage.textContent = "Crea un job para abrir el canvas V2.";
      return null;
    }

    const store = new modules.Store.EditorStore(context.layout);
    const saver = new modules.Autosave.SaveCoordinator(store, api, context.save_layout_url);
    const actionRegistry = new modules.CommandRegistry.ActionRegistry();
    modules.CommandRegistry.registerEditorActions(actionRegistry);
    let renderer = null;
    let interactions = null;
    let positionInspector = null;
    let nudgeController = null;
    let shortcutHelp = null;
    let shortcutManager = null;
    let objectsPanel = null;
    let arrangementPanel = null;
    let precisionPanel = null;
    let objectTree = null;
    const contextProvider = () => ({
      store,
      layout: store.layout,
      selectedSlotIds: [...store.selection],
      selectedSlots: store.layout.slots.filter((slot) => store.selection.has(slot.id)),
      activeFace: store.activeFace,
      history: store,
      saveCoordinator: saver,
      pointerSession: store.pointerSession,
      focusedElement: document.activeElement,
      isSaving: store.saveState.status === "saving",
      dirty: store.hasUnsavedChanges(),
      commands: modules.Commands,
      objectOperations: modules.ObjectOperations,
      advancedSelection: modules.AdvancedSelection,
      alignmentOperations: modules.AlignmentOperations,
      precisionTools: modules.PrecisionTools,
      snapEngine: modules.SnapEngine,
      geometry: modules.GeometryView,
      positioning: modules.PositionInspector,
      editPolicy: modules.EditPolicy,
      renderer,
      interactions,
      positionInspector,
      nudgeController,
      shortcutHelp,
      objectsPanel,
      arrangementPanel,
      precisionPanel,
      objectTree,
    });
    function runAction(actionId, payload) {
      try {
        const result = actionRegistry.execute(actionId, contextProvider(), payload);
        if (result && typeof result.catch === "function") {
          result.catch((error) => store.setFeedback(error.message || String(error)));
        }
        return result;
      } catch (error) {
        store.setFeedback(error.message || String(error));
        return false;
      }
    }
    nudgeController = new modules.NudgeController.Controller(
      store,
      modules.Commands,
      modules.EditPolicy,
    );
    positionInspector = new modules.PositionInspector.Controller(
      store,
      refs,
      actionRegistry,
      contextProvider,
      modules.EditPolicy,
      modules.CommandRegistry.ACTION_IDS,
    );
    shortcutHelp = new modules.ShortcutManager.ShortcutHelp(refs, actionRegistry);
    interactions = new modules.Interactions.CanvasInteractions(
      store,
      refs,
      modules.GeometryView,
      modules.Commands,
      modules.EditPolicy,
      {
        beforePointerAction: () => nudgeController.finish(),
        advancedSelection: modules.AdvancedSelection,
        snapEngine: modules.SnapEngine,
        precisionTools: modules.PrecisionTools,
        actionIds: modules.CommandRegistry.ACTION_IDS,
        runAction,
      },
    );
    renderer = new modules.CanvasRenderer.Renderer(
      store,
      refs,
      modules.GeometryView,
      context.assets_api_url,
      {
        registry: actionRegistry,
        actionIds: modules.CommandRegistry.ACTION_IDS,
        contextProvider,
      },
      modules.PrecisionTools,
    );
    shortcutManager = new modules.ShortcutManager.Manager(
      actionRegistry,
      contextProvider,
      {
        setSpacePressed: (pressed) => interactions.setSpacePressed(pressed),
        onBlur: () => {
          if (interactions.hasPointerActivity()) interactions.cancelPointer();
        },
      },
    );
    const assetsPanel = new modules.AssetsPanel.AssetsPanel(
      store,
      refs,
      api,
      saver,
      context,
      modules.Commands,
      modules.EditPolicy,
    );
    const repeatPanel = new modules.RepeatPanel.Panel(
      store,
      refs,
      api,
      saver,
      context,
      modules.Commands,
      modules.EditPolicy,
    );
    const outputPanel = new modules.OutputPanel.Panel(
      store,
      refs,
      api,
      saver,
      context,
    );
    objectsPanel = new modules.ObjectsPanel.Panel(
      store,
      refs,
      actionRegistry,
      contextProvider,
      modules.CommandRegistry.ACTION_IDS,
      modules.ObjectOperations,
      runAction,
    );
    arrangementPanel = new modules.ArrangementPanel.Panel(
      store,
      refs,
      actionRegistry,
      contextProvider,
      modules.CommandRegistry.ACTION_IDS,
      modules.AlignmentOperations,
      runAction,
    );
    precisionPanel = new modules.PrecisionPanel.Panel(
      store,
      refs,
      actionRegistry,
      contextProvider,
      modules.CommandRegistry.ACTION_IDS,
      modules.PrecisionTools,
      modules.GeometryView,
      runAction,
    );
    objectTree = new modules.ObjectTree.Panel(
      store,
      refs,
      actionRegistry,
      contextProvider,
      modules.CommandRegistry.ACTION_IDS,
      modules.AdvancedSelection,
      runAction,
    );

    refs.save.addEventListener("click", () => runAction(modules.CommandRegistry.ACTION_IDS.SAVE));
    refs.undo.addEventListener("click", () => runAction(modules.CommandRegistry.ACTION_IDS.UNDO));
    refs.redo.addEventListener("click", () => runAction(modules.CommandRegistry.ACTION_IDS.REDO));
    refs.shortcutsHelpButton.addEventListener("click", () => (
      runAction(modules.CommandRegistry.ACTION_IDS.HELP_TOGGLE)
    ));
    if (refs.createSlot && context.dev_tools_enabled === true) {
      refs.createSlot.addEventListener("click", () => {
        const bundle = modules.Commands.createDevelopmentPlaceholderBundle(
          store.layout,
          developmentToken(),
        );
        store.executeCommand(new modules.Commands.CreateSlotCommand(bundle));
        store.setSelection([bundle.slot.id], "replace");
      });
    }
    refs.deleteSlots.addEventListener("click", () => {
      runAction(modules.CommandRegistry.ACTION_IDS.DELETE);
    });
    refs.zoomIn.addEventListener("click", () => {
      store.setZoom(modules.GeometryView.clampZoom(store.zoom * 1.2));
    });
    refs.zoomOut.addEventListener("click", () => {
      store.setZoom(modules.GeometryView.clampZoom(store.zoom / 1.2));
    });
    refs.resetView.addEventListener("click", () => store.resetView());
    refs.toggleLabels.addEventListener("click", () => {
      store.setSlotLabelsVisible(!store.showSlotLabels);
    });
    refs.reloadConflict.addEventListener("click", () => window.location.reload());

    window.addEventListener("beforeunload", (event) => {
      if (!store.hasUnsavedChanges()) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    });

    const instance = {
      context,
      store,
      renderer,
      saver,
      interactions,
      assetsPanel,
      repeatPanel,
      outputPanel,
      objectsPanel,
      arrangementPanel,
      precisionPanel,
      objectTree,
      actionRegistry,
      shortcutManager,
      shortcutHelp,
      positionInspector,
      nudgeController,
      runAction,
    };
    root.__EDITOR_OFFSET_V2__ = instance;
    return instance;
  }

  return Object.freeze({ start, parseContext });
});
