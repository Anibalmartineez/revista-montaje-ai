(function (root, factory) {
  "use strict";
  const preparation = typeof module === "object" && module.exports
    ? require("./preparation.js") : root.EditorOffsetV2.Preparation;
  const api = factory(preparation);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.AssetsPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (Preparation) {
  "use strict";
  const clone = (value) => JSON.parse(JSON.stringify(value));
  function token() { return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`; }
  function thumbnailUrl(baseUrl, assetId, page) { return `${baseUrl}/${encodeURIComponent(assetId)}/thumbnails/${page}`; }
  function option(value, label) {
    const node = document.createElement("option"); node.value = String(value); node.textContent = label; return node;
  }
  function el(tag, text, className) {
    const node = document.createElement(tag); if (text) node.textContent = text; if (className) node.className = className; return node;
  }
  function isReadyAsset(asset) { return Boolean(asset && asset.status === "ready" && asset.pages?.length); }
  class AssetsPanel {
    constructor(store, refs, api, saver, context, commands, editPolicy, runAction) {
      Object.assign(this, { store, refs, api, saver, context, commands, editPolicy, runAction });
      this.uploading = false;
      this.drafts = new Preparation.Drafts();
      this.editing = null;
      this.bind();
      this.unsubscribe = store.subscribe((event) => this.onStoreEvent(event));
      this.renderAll();
    }
    action(operation, payload) { return this.runAction(`preparation.${operation}`, payload); }
    handle(operation, payload) {
      try {
        const methods = { focus: "focusPage", row: "changeRow", all: "selectAll", create: "createPageWorks",
          edit: "editWork", cancel: "cancelEdit", variant: "variantWork", save: "saveWork",
          selectwork: "selectWork", slot: "createSlot", replace: "replaceSource" };
        return this[methods[operation]](payload);
      } catch (error) { this.message(error.message, true); return false; }
    }
    message(text, error = false) {
      this.refs.preparationStatus.textContent = text;
      this.refs.preparationStatus.dataset.state = error ? "error" : "success";
      if (error) this.refs.preparationStatus.scrollIntoView({ block: "nearest" });
    }
    bind() {
      const r = this.refs;
      r.assetUploadForm.addEventListener("submit", (event) => this.upload(event));
      r.assetsList.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-asset-id][data-page]");
        if (button) this.action("focus", { assetId: button.dataset.assetId, page: Number(button.dataset.page) });
      });
      r.assetPagePlanner.addEventListener("input", (event) => this.action("row", event.target));
      r.assetPagePlanner.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-configure-page]");
        if (button) this.action("focus", { assetId: this.asset().id, page: Number(button.dataset.configurePage) });
      });
      for (const [node, operation] of [[r.createPageWorks,"create"],
        [r.preparationSelectAll,"all"], [r.preparationSave,"save"], [r.preparationCancel,"cancel"],
        [r.preparationVariant,"variant"], [r.createRealSlot,"slot"], [r.replaceSource,"replace"]]) {
        node.addEventListener("click", () => this.action(operation));
      }
      r.workSelect.addEventListener("change", () => this.action("selectwork", r.workSelect.value));
      r.preparedWorks.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-edit-work]");
        if (button) this.action("edit", button.dataset.editWork);
      });
    }
    onStoreEvent(event) {
      if (["command", "undo", "redo", "external_update", "save_success", "active_face"].includes(event.type)) {
        this.renderAll();
      } else if (event.type === "asset_selection") {
        this.renderAssets(); this.renderPagePlanner(); this.renderActionState();
      } else if (event.type === "work_selection") this.renderWorks();
      else if (event.type === "upload_state") this.renderUploadState();
      else if (event.type === "selection" || event.type === "matrix_cell_selection") { this.renderActionState(); this.renderWorks(); }
    }
    renderAll() {
      this.renderAssets(); this.renderPagePlanner();
      this.renderWorks(); this.renderUploadState(); this.renderActionState();
    }
    asset() {
      return this.store.layout.assets.find((asset) => asset.id === this.store.assetPanel.selectedAssetId && isReadyAsset(asset));
    }
    current() {
      if (this.editing) return this.editing.draft;
      const selected = this.store.selectedAssetPage();
      return selected ? this.drafts.get(selected.asset, selected.page) : null;
    }
    focusPage({ assetId, page }) {
      const asset = this.store.layout.assets.find((item) => item.id === assetId && isReadyAsset(item));
      const sourcePage = asset?.pages.find((item) => item.number === page);
      if (!sourcePage) throw new Error("Página no disponible.");
      if (this.editing && this.store.layout.slots.some((slot) => slot.work_id === this.editing.before.id)) {
        throw new Error("Crea una variante antes de cambiar la página de un trabajo que ya tiene piezas.");
      }
      if (this.editing) {
        const draft = this.editing.draft;
        const selectedBox = Preparation.detectedBox(sourcePage, this.editing.draft.bleed);
        if (!selectedBox) throw new Error("La página no declara una medida utilizable.");
        draft.assetId = asset.id; draft.page = sourcePage.number; draft.box = selectedBox; draft.sizeMode = "box";
        Preparation.changeBox(draft, sourcePage, selectedBox);
        this.store.setAssetSelection(asset.id, page, selectedBox);
        this.renderAll();
        this.refs.assetPagePlanner.querySelector(`[data-page="${page}"]`)?.scrollIntoView({ block: "nearest" });
        return;
      }
      const draft = this.drafts.get(asset, sourcePage);
      const selectedBox = Preparation.detectedBox(sourcePage, draft.bleed);
      if (selectedBox && draft.box !== selectedBox) Preparation.changeBox(draft, sourcePage, selectedBox);
      this.store.setAssetSelection(asset.id, page, selectedBox);
      this.refs.assetPagePlanner.querySelector(`[data-page="${page}"]`)?.scrollIntoView({ block: "nearest" });
    }
    selectWork(id) { this.store.setSelectedWork(id || null); }
    changeRow(target) {
      const asset = this.asset();
      const page = asset?.pages.find((item) => item.number === Number(target.dataset.page));
      if (!page || !target.dataset.preparationRow) return;
      const field = target.dataset.preparationRow;
      const isEditingPage = this.editing && this.editing.draft.assetId === asset.id && this.editing.draft.page === page.number;
      const draft = isEditingPage ? this.editing.draft : this.drafts.get(asset, page);
      if (field === "rotation") {
        const rotation = Number(target.dataset.rotation);
        draft.rotations = target.checked ? [...new Set([...draft.rotations, rotation])]
          : draft.rotations.filter((value) => value !== rotation);
      } else if (field === "bleed") {
        Preparation.applyBleedIntent(draft, page, target.value);
      } else if (field === "cropMarks" || field === "back" || field === "selected" || field === "variant") draft[field] = target.checked;
      else draft[field] = target.value;
      this.renderSummary();
    }
    selectAll() {
      const asset = this.asset(); if (!asset || this.editing) return;
      const drafts = asset.pages.map((page) => this.drafts.get(asset, page));
      const selected = !drafts.every((draft) => draft.selected);
      drafts.forEach((draft) => { draft.selected = selected; }); this.renderPagePlanner();
    }
    renderPagePlanner() {
      const asset = this.asset(), container = this.refs.assetPagePlanner;
      container.replaceChildren();
      if (!asset) { container.append(el("p", "Sube un PDF para preparar sus páginas.")); this.renderSummary(); return; }
      for (const page of asset.pages) {
        const editingPage = this.editing && this.editing.draft.assetId === asset.id && this.editing.draft.page === page.number;
        const draft = editingPage ? this.editing.draft : this.drafts.get(asset, page);
        const row = el("article", null, "ev2-page-plan-row");
        row.dataset.page = String(page.number);
        row.classList.toggle("is-inspected", this.current()?.page === page.number);
        const sourceButton = el("button", null, "ev2-preparation-thumbnail");
        sourceButton.type = "button"; sourceButton.dataset.configurePage = String(page.number);
        sourceButton.setAttribute("aria-label", `Seleccionar página ${page.number}`);
        const image = el("img"); image.src = thumbnailUrl(this.context.assets_api_url, asset.id, page.number); image.alt = ""; image.loading = "lazy";
        sourceButton.append(image);
        const body = el("div", null, "ev2-preparation-page-body");
        const selectionLabel = el("label", null, "ev2-preparation-page-label");
        const checkbox = el("input"); checkbox.type = "checkbox"; checkbox.checked = draft.selected;
        checkbox.dataset.pagePlanSelected = "true"; checkbox.dataset.page = String(page.number); checkbox.dataset.preparationRow = "selected";
        checkbox.disabled = Boolean(this.editing);
        selectionLabel.append(checkbox, document.createTextNode(`Página ${page.number}`));
        const detectedSize = Preparation.dimensions(page, draft.box);
        const sizeValue = editingPage ? `${draft.width} × ${draft.height} mm` : detectedSize ? `${detectedSize.width} × ${detectedSize.height} mm` : "Medida no disponible";
        const size = el("strong", sizeValue, "ev2-page-plan-size");
        const controls = el("div", null, "ev2-page-plan-controls");
        const addNumber = (labelText, field, value, min, step, disabled = false) => {
          const label = el("label", labelText); const input = el("input");
          input.type = "number"; input.min = String(min); input.step = String(step); input.value = value;
          input.dataset.page = String(page.number); input.dataset.preparationRow = field;
          input.setAttribute("aria-label", `${labelText} página ${page.number}`); input.disabled = disabled;
          label.append(input); return label;
        };
        const placed = editingPage && this.store.layout.slots.some((slot) => slot.work_id === this.editing.before.id);
        const otherPageEditing = Boolean(this.editing && !editingPage);
        controls.append(addNumber("Cantidad", "quantity", draft.quantity, 1, 1, otherPageEditing));
        controls.append(addNumber("Sangrado (mm)", "bleed", draft.bleed, 0, 0.1, Boolean(placed || otherPageEditing)));
        const cropLabel = el("label", null, "ev2-page-plan-check"); const crop = el("input"); crop.type = "checkbox";
        crop.checked = Boolean(draft.cropMarks); crop.dataset.page = String(page.number); crop.dataset.preparationRow = "cropMarks";
        crop.setAttribute("aria-label", `Marcas de corte para página ${page.number}`); crop.disabled = otherPageEditing;
        cropLabel.append(crop, document.createTextNode("Marcas de corte")); controls.append(cropLabel);
        const backLabel = el("label", null, "ev2-page-plan-check"); const back = el("input"); back.type = "checkbox";
        back.checked = Boolean(draft.back); back.dataset.page = String(page.number); back.dataset.preparationRow = "back";
        back.setAttribute("aria-label", `Usar también como dorso página ${page.number}`); back.disabled = Boolean(placed || otherPageEditing);
        backLabel.append(back, document.createTextNode("También como dorso")); controls.append(backLabel);
        const rotations = el("fieldset", null, "ev2-page-plan-rotations");
        rotations.append(el("legend", "Giros"));
        for (const degree of [0, 90, 180, 270]) {
          const label = el("label"); const input = el("input"); input.type = "checkbox";
          input.checked = draft.rotations.includes(degree); input.dataset.page = String(page.number);
          input.dataset.preparationRow = "rotation"; input.dataset.rotation = String(degree);
          input.setAttribute("aria-label", `Permitir giro ${degree} grados en página ${page.number}`);
          input.disabled = Boolean(placed || otherPageEditing);
          label.append(input, document.createTextNode(`${degree}°`)); rotations.append(label);
        }
        controls.append(rotations);
        body.append(selectionLabel, size, controls);
        if (Number(draft.bleed) > 0) {
          body.append(el("small", "Si falta sangrado en el archivo, se completará con espejo."));
        }
        const existing = this.store.layout.works.filter((work) => Preparation.matches(work, draft));
        if (existing.length && !this.editing) {
          body.append(el("small", `${existing.length} trabajo(s) guardado(s). Edita el existente debajo o crea una variante.`));
          const label = el("label", null, "ev2-preparation-page-label"); const variant = el("input"); variant.type = "checkbox";
          variant.checked = draft.variant; variant.dataset.page = String(page.number); variant.dataset.preparationRow = "variant";
          variant.disabled = Boolean(this.editing); label.append(variant, document.createTextNode("Crear variante")); body.append(label);
        }
        row.append(sourceButton, body); container.append(row);
      }
      this.renderSummary();
    }
    renderSummary() {
      const asset = this.asset(); const selected = asset ? this.drafts.selected(asset) : [];
      const quantity = selected.reduce((sum, draft) => sum + Number(draft.quantity), 0);
      this.refs.createPageWorks.textContent = `Crear ${selected.length} trabajos · ${Number.isFinite(quantity) ? quantity : "—"} formas`;
      this.refs.createPageWorks.disabled = !selected.length || Boolean(this.editing);
      this.refs.preparationSelectAll.disabled = !asset || Boolean(this.editing);
      this.refs.preparationSelectAll.textContent = selected.length && selected.length === asset?.pages.length
        ? "Deseleccionar todas" : "Seleccionar todas";
      this.refs.preparationEditActions.hidden = !this.editing;
    }
    renderWorks() {
      const r = this.refs, layout = this.store.layout;
      r.workSelect.replaceChildren(option("", "Selecciona un trabajo")); r.preparedWorks.replaceChildren();
      if (!layout.works.length) r.preparedWorks.append(el("p", "Todavía no hay trabajos guardados."));
      const defaultMarks = layout.export.marks_profiles.find((profile) => profile.id === layout.export.default_marks_profile_id);
      for (const work of layout.works) {
        r.workSelect.append(option(work.id, work.name));
        const card = el("article", null, "ev2-prepared-work");
        const source = work.front_source; const asset = layout.assets.find((a) => a.id === source?.asset_id);
        const count = layout.slots.filter((slot) => slot.work_id === work.id).length;
        const body = el("div"); body.append(el("strong", work.name));
        body.append(el("p", `${asset?.original_filename ?? "Sin fuente"} · pág. ${source?.page ?? "—"} · Final: ${work.trim_size_mm.width} × ${work.trim_size_mm.height} mm`));
        const cropMarks = work.crop_marks ?? defaultMarks?.crop_marks ?? true;
        body.append(el("small", `Repeat ${work.requested_forms} · ${count} piezas · sangrado ${work.bleed_mm} mm · marcas de corte ${cropMarks ? "sí" : "no"} · giros ${work.allowed_rotations_deg.join("° / ")}°`));
        const edit = el("button", "Editar"); edit.type = "button"; edit.dataset.editWork = work.id; edit.disabled = !asset || !source;
        edit.setAttribute("aria-label", `Editar trabajo ${work.name}`); card.append(body, edit); r.preparedWorks.append(card);
      }
      r.workSelect.value = this.store.assetPanel.selectedWorkId || "";
      r.createRealSlot.disabled = !r.workSelect.value;
      r.createRealSlot.textContent = this.store.matrixCellSelectionIds.size
        ? `Asignar PDF a ${this.store.matrixCellSelectionIds.size} cuadro(s)`
        : this.store.activeFace === "back" ? "Colocar en Dorso con página elegida" : "Colocar en Frente";
    }
    editWork(id) {
      if (this.editing) throw new Error("Guarda o cancela la edición actual.");
      const work = this.store.layout.works.find((w) => w.id === id);
      const asset = this.store.layout.assets.find((a) => a.id === work?.front_source?.asset_id);
      const page = asset?.pages.find((p) => p.number === work.front_source.page);
      if (!page) throw new Error("La fuente de este trabajo no está disponible.");
      const selectedBox = Preparation.detectedBox(page, work.bleed_mm);
      const detectedSize = Preparation.dimensions(page, selectedBox);
      const defaultMarks = this.store.layout.export.marks_profiles.find((profile) => profile.id === this.store.layout.export.default_marks_profile_id);
      const draft = { ...clone(this.drafts.get(asset, page)),
        selected: false, name: work.name, box: selectedBox,
        width: detectedSize?.width ?? work.trim_size_mm.width, height: detectedSize?.height ?? work.trim_size_mm.height, sizeMode: "box",
        quantity: work.requested_forms, bleed: work.bleed_mm, rotations: [...work.allowed_rotations_deg],
        bleedStrategy: work.bleed_strategy ?? (Number(work.bleed_mm) > 0 ? "mirror_if_missing" : "source_only"),
        cropMarks: work.crop_marks ?? defaultMarks?.crop_marks ?? true,
        back: this.commands.UpdateWorkCommand.equal(work.back_source, work.front_source), variant: false };
      this.editing = { before: clone(work), draft, initialBack: draft.back };
      const selectedBoxForStore = Preparation.detectedBox(page, work.bleed_mm);
      this.store.setAssetSelection(asset.id, page.number, selectedBoxForStore);
      this.renderAll(); this.refs.assetPagePlanner.querySelector(`[data-page="${page.number}"]`)?.scrollIntoView({ block: "nearest" });
    }
    cancelEdit() { this.editing = null; this.renderAll(); this.message("Edición cerrada. Los borradores de páginas se conservan."); }
    variantWork() {
      if (!this.editing) return;
      const draft = clone(this.editing.draft); this.editing = null;
      draft.bleedStrategy ??= Number(draft.bleed) > 0 ? "mirror_if_missing" : "source_only";
      draft.variant = true; draft.selected = true;
      draft.name = Preparation.uniqueName(draft.name, this.store.layout.works);
      this.drafts.pages.set(`${draft.assetId}:${draft.page}`, draft);
      this.focusPage({ assetId: draft.assetId, page: draft.page });
      this.message("Variante preparada. Ajusta sus valores y pulsa Crear trabajos; el trabajo original se conserva.");
    }
    saveWork() {
      if (!this.editing) return;
      const { before, draft, initialBack } = this.editing;
      const current = this.store.layout.works.find((w) => w.id === before.id);
      if (!this.commands.UpdateWorkCommand.equal(current, before)) throw new Error("El trabajo cambió. Cancela y vuelve a abrir la edición.");
      const placed = this.store.layout.slots.some((s) => s.work_id === before.id);
      let patch = { name: draft.name.trim(), requested_forms: Number(draft.quantity), crop_marks: Boolean(draft.cropMarks) };
      if (!placed && draft.bleedStrategy !== undefined) patch.bleed_strategy = draft.bleedStrategy;
      if (!placed) {
        const asset = this.store.layout.assets.find((a) => a.id === draft.assetId);
        const entry = Preparation.entry(draft, asset);
        const candidate = this.commands.createWorkFromSource(this.store.layout, entry.source, entry.values, token());
        patch = { ...patch, front_source: candidate.front_source, trim_size_mm: candidate.trim_size_mm,
          bleed_mm: candidate.bleed_mm, allowed_rotations_deg: candidate.allowed_rotations_deg, crop_marks: candidate.crop_marks,
          back_source: !initialBack && !draft.back ? before.back_source : candidate.back_source };
      }
      const command = new this.commands.UpdateWorkCommand(this.store.layout, before.id, patch);
      this.store.executeCommand(command); this.editing = null; this.renderAll();
      this.message("Trabajo actualizado. Repeat usará los giros y marcas elegidos; las piezas existentes conservan su configuración.");
    }
    createPageWorks() {
      const asset = this.asset(); if (!asset || this.editing) return;
      const entries = this.drafts.entries(asset, this.store.layout.works);
      const works = this.commands.createWorksFromSources(this.store.layout, entries, {}, (entry, index) => `page_${entry.source.page}_${token()}_${index}`);
      this.store.executeCommand(new this.commands.CreateWorksCommand(works));
      this.drafts.selected(asset).forEach((draft) => { draft.selected = false; draft.variant = false; });
      this.store.setSelectedWork(works.at(-1).id); this.renderPagePlanner();
      this.message(`${works.length} trabajos creados. Continúa en Imponer o coloca una pieza manualmente.`);
    }
    renderUploadState() {
      const state = this.store.assetPanel;
      this.refs.assetUploadButton.disabled = this.uploading || Boolean(this.editing);
      this.refs.assetUploadStatus.textContent = state.error || state.message || "";
      this.refs.assetUploadStatus.dataset.state = state.error ? "error" : state.uploadStatus;
    }
    renderActionState() {
      const ids = [...this.store.selection];
      let source;
      try { source = this.selectedSource(); } catch (_) { source = null; }
      this.refs.replaceSource.disabled = ids.length !== 1 || !source || Boolean(this.editing)
        || !this.editPolicy.can(this.store.layout, ids, "replace_content");
      const asset = source && this.store.layout.assets.find((item) => item.id === source.asset_id);
      const page = asset?.pages.find((item) => item.number === source.page);
      const size = page && Preparation.dimensions(page, source.pdf_box);
      this.refs.replaceSourceLabel.textContent = source
        ? `Fuente preparada: página ${source.page} · medida detectada ${size ? `${size.width} × ${size.height} mm` : "disponible"}. Sustituir afecta solo al slot seleccionado.`
        : "Elige una fuente válida en Preparar.";
    }
    selectedSource() {
      const draft = this.current(); if (!draft) throw new Error("Selecciona una página PDF.");
      const asset = this.store.layout.assets.find((a) => a.id === draft.assetId);
      return Preparation.source(draft, asset);
    }
    renderAssets() {
      this.refs.assetsList.replaceChildren();
      const assets = this.store.layout.assets.filter(isReadyAsset);
      if (!assets.length) {
        const empty = document.createElement("p");
        empty.className = "ev2-list-empty";
        empty.textContent = "Sube un PDF para crear el primer asset real.";
        this.refs.assetsList.append(empty);
        return;
      }
      for (const asset of assets) {
        const card = document.createElement("article");
        card.className = asset.id === this.store.assetPanel.selectedAssetId
          ? "ev2-asset-card is-selected"
          : "ev2-asset-card";
        const heading = document.createElement("div");
        const name = document.createElement("strong");
        const meta = document.createElement("small");
        name.textContent = asset.original_filename;
        meta.textContent = `${asset.page_count} pág. · ${asset.status}`;
        heading.append(name, meta);
        card.append(heading);
        const pages = document.createElement("div");
        pages.className = "ev2-asset-pages";
        for (const page of asset.pages) {
          const button = document.createElement("button");
          button.type = "button";
          button.dataset.assetId = asset.id;
          button.dataset.page = String(page.number);
          button.className = asset.id === this.store.assetPanel.selectedAssetId
            && page.number === this.store.assetPanel.selectedPage ? "is-selected" : "";
          const image = document.createElement("img");
          image.src = thumbnailUrl(this.context.assets_api_url, asset.id, page.number);
          image.alt = `${asset.original_filename}, página ${page.number}`;
          image.loading = "lazy";
          const label = document.createElement("span");
          label.textContent = `Pág. ${page.number}`;
          button.append(image, label);
          pages.append(button);
        }
        card.append(pages);
        this.refs.assetsList.append(card);
      }
    }

    async upload(event) {
      event.preventDefault();
      const file = this.refs.assetFile.files[0];
      if (!file || this.uploading) {
        this.store.setUploadState("error", null, "Selecciona un archivo PDF.");
        return;
      }
      if (this.editing) { this.message("Guarda o cancela la edición antes de subir un PDF.", true); return; }
      this.uploading = true;
      this.store.setUploadState("uploading", "Subiendo, inspeccionando y generando miniaturas…");
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de subir un asset.");
        }
        const response = await this.api.uploadAsset(
          this.context.assets_api_url,
          this.store.revision,
          file,
        );
        this.store.applyServerLayout(response.layout);
        const page = response.asset.pages[0];
        const box = page.boxes_mm.trim ? "trim" : page.boxes_mm.crop ? "crop" : "media";
        this.drafts.get(response.asset, page).selected = true;
        this.store.setAssetSelection(response.asset_id, page.number, box);
        this.refs.assetFile.value = "";
        this.store.setUploadState("success", `Asset ${response.asset.original_filename} listo.`);
      } catch (error) {
        if (error && error.status === 409) this.store.failSave(error, true);
        this.store.setUploadState("error", null, error.message || "No se pudo subir el PDF.");
      } finally {
        this.uploading = false;
        this.renderUploadState();
      }
    }

    createSlot() {
      try {
        const cellIds = [...this.store.matrixCellSelectionIds];
        if (cellIds.length) {
          const cells = cellIds.map((id) => (this.store.layout.matrix_cells || []).find((item) => item.id === id)).filter(Boolean);
          const work = this.store.layout.works.find((item) => item.id === this.refs.workSelect.value);
          if (!cells.length || cells.length !== cellIds.length || !work) throw new Error("Selecciona cuadros vacíos y un trabajo preparado.");
          const source = cells[0].face === "back" ? this.selectedSource() : null;
          if (cells.some((cell) => cell.face !== cells[0].face)) throw new Error("Selecciona cuadros de una sola cara.");
          const slots = cells.map((cell) => this.commands.createSlotFromWork(this.store.layout, work.id, token(), cell.position_mm, cell.face, source));
          for (let index = 0; index < slots.length; index += 1) {
            const cell = cells[index], slot = slots[index];
            const rotation = slot.geometry.rotation_deg;
            slot.geometry.trim_size_mm = [90, 270].includes(rotation)
              ? { width: cell.trim_size_mm.height, height: cell.trim_size_mm.width }
              : { ...cell.trim_size_mm };
            slot.content_transform.fit_mode = "contain";
          }
          this.store.executeCommand(new this.commands.AssignMatrixCellsCommand(this.store.layout, cellIds, slots));
          this.store.setSelection(slots.map((slot) => slot.id), "replace");
          this.store.setUploadState("success", `PDF asignado a ${slots.length} cuadro(s).`);
          return;
        }
        const sheet = this.store.layout.sheet.size_mm;
        const slot = this.commands.createSlotFromWork(
          this.store.layout,
          this.refs.workSelect.value,
          token(),
          {
            x_mm: sheet.width / 2 - this.store.pan.x,
            y_mm: sheet.height / 2 - this.store.pan.y,
          },
          this.store.activeFace,
          this.store.activeFace === "back" ? this.selectedSource() : null,
        );
        this.store.executeCommand(new this.commands.CreateSlotFromWorkCommand(slot));
        this.store.setSelection([slot.id], "replace");
        this.store.setUploadState("success", `Slot real ${slot.id} creado.`);
      } catch (error) {
        this.store.setUploadState("error", null, error.message);
      }
    }

    replaceSource() {
      try {
        if (this.store.selection.size !== 1) {
          throw new Error("Selecciona exactamente un slot.");
        }
        const slotId = [...this.store.selection][0];
        const command = new this.commands.ReplaceSlotSourceCommand(
          this.store.layout,
          slotId,
          this.selectedSource(),
        );
        this.store.executeCommand(command);
        this.store.setUploadState(
          command.dimensionWarning ? "warning" : "success",
          command.dimensionWarning || `Fuente de ${slotId} sustituida.`,
        );
      } catch (error) {
        this.store.setUploadState("error", null, error.message);
      }
    }

    dispose() { this.unsubscribe(); }
  }
  return Object.freeze({ AssetsPanel, thumbnailUrl });
});
