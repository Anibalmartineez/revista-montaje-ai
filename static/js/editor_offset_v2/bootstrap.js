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
    const renderer = new modules.CanvasRenderer.Renderer(
      store,
      refs,
      modules.GeometryView,
      context.assets_api_url,
    );
    const saver = new modules.Autosave.SaveCoordinator(store, api, context.save_layout_url);
    const interactions = new modules.Interactions.CanvasInteractions(
      store,
      refs,
      modules.GeometryView,
      modules.Commands,
      modules.EditPolicy,
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

    refs.save.addEventListener("click", () => saver.manualSave());
    refs.undo.addEventListener("click", () => store.undo());
    refs.redo.addEventListener("click", () => store.redo());
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
      if (!store.selection.size) {
        return;
      }
      try {
        store.executeCommand(
          new modules.Commands.DeleteSlotsCommand(store.layout, [...store.selection]),
        );
      } catch (error) {
        store.setFeedback(error.message);
      }
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
    };
    root.__EDITOR_OFFSET_V2__ = instance;
    return instance;
  }

  return Object.freeze({ start, parseContext });
});
