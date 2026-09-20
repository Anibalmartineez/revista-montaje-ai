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
  const boxLabel = (box) => `${box[0].toUpperCase()}${box.slice(1)}Box`;
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
        const methods = { focus: "focusPage", row: "changeRow", field: "changeField", asset: "changeAsset",
          page: "changePage", common: "applyCommon", all: "selectAll", create: "createPageWorks",
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
      r.assetSelect.addEventListener("change", () => this.action("asset"));
      r.assetPage.addEventListener("change", () => this.action("page"));
      for (const node of [r.assetBox, r.workName, r.workWidth, r.workHeight, r.workBleed,
        r.workQuantity, r.workSizeMode, r.workBack, ...r.workRotations]) {
        node.addEventListener("input", () => this.action("field", node));
      }
      for (const [node, operation] of [[r.createPageWorks,"create"], [r.preparationApply,"common"],
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
      if (["command", "undo", "redo", "external_update", "save_success"].includes(event.type)) {
        this.renderAll();
      } else if (event.type === "asset_selection") {
        this.renderAssets(); this.renderPagePlanner(); this.renderSourceControls(); this.renderActionState();
      } else if (event.type === "work_selection") this.renderWorks();
      else if (event.type === "upload_state") this.renderUploadState();
      else if (event.type === "selection") this.renderActionState();
    }
    renderAll() {
      this.renderAssets(); this.renderPagePlanner(); this.renderSourceControls();
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
      if (this.editing) throw new Error("Guarda o cancela la edición del trabajo antes de cambiar de página.");
      const asset = this.store.layout.assets.find((item) => item.id === assetId && isReadyAsset(item));
      const sourcePage = asset?.pages.find((item) => item.number === page);
      if (!sourcePage) throw new Error("Página no disponible.");
      const draft = this.drafts.get(asset, sourcePage);
      // Store selection only accepts existing boxes; missing draft boxes stay explicit in the form.
      const selectedBox = sourcePage.boxes_mm[draft.box] ? draft.box : Preparation.BOXES.find((box) => sourcePage.boxes_mm[box]);
      this.store.setAssetSelection(asset.id, page, selectedBox);
      this.refs.preparationSettings.focus({ preventScroll: true });
    }
    changeSource(assetId, pageNumber) {
      if (!this.editing) return this.focusPage({ assetId, page: pageNumber });
      if (this.store.layout.slots.some((s) => s.work_id === this.editing.before.id)) {
        throw new Error("Un trabajo colocado requiere una variante para cambiar su fuente.");
      }
      const asset = this.store.layout.assets.find((a) => a.id === assetId && isReadyAsset(a));
      const page = asset?.pages.find((p) => p.number === pageNumber);
      if (!page) throw new Error("Página no disponible.");
      Object.assign(this.editing.draft, { assetId, page: pageNumber });
      Preparation.changeBox(this.editing.draft, page, this.editing.draft.box);
      this.renderSourceControls();
    }
    changeAsset() { this.changeSource(this.refs.assetSelect.value, this.store.layout.assets.find((a) => a.id === this.refs.assetSelect.value).pages[0].number); }
    changePage() { this.changeSource(this.current().assetId, Number(this.refs.assetPage.value)); }
    selectWork(id) { this.store.setSelectedWork(id || null); }
    changeRow(target) {
      const page = this.asset()?.pages.find((item) => item.number === Number(target.dataset.page));
      if (!page || !target.dataset.preparationRow) return;
      const draft = this.drafts.get(this.asset(), page);
      const field = target.dataset.preparationRow;
      draft[field] = target.type === "checkbox" ? target.checked : target.value;
      this.renderSummary();
      if (this.current() === draft) this.renderSourceControls();
    }
    changeField(node) {
      const draft = this.current(); if (!draft) return;
      const r = this.refs;
      Object.assign(draft, { name: r.workName.value, quantity: r.workQuantity.value, bleed: r.workBleed.value,
        rotations: [...r.workRotations].filter((item) => item.checked).map((item) => Number(item.value)),
        back: r.workBack.checked, width: r.workWidth.value, height: r.workHeight.value,
        sizeMode: r.workSizeMode.value });
      const asset = this.store.layout.assets.find((a) => a.id === draft.assetId);
      const page = asset.pages.find((p) => p.number === draft.page);
      if (node === r.assetBox || node === r.workSizeMode) {
        Preparation.changeBox(draft, page, r.assetBox.value);
        this.renderSourceControls();
      } else this.renderCoverage(draft, page);
      this.renderPagePlanner();
      this.renderActionState();
    }
    applyCommon() {
      if (this.editing) return;
      const asset = this.asset(), draft = this.current();
      if (!draft || !this.drafts.selected(asset).length) throw new Error("Selecciona las páginas que recibirán los valores.");
      const fields = this.refs.preparationFields.filter((input) => input.checked).map((input) => input.dataset.preparationField);
      if (!fields.length) throw new Error("Elige los campos que quieres aplicar.");
      this.drafts.apply(asset, clone(draft), fields);
      this.renderPagePlanner(); this.renderSourceControls();
      this.message(`Valores aplicados a ${this.drafts.selected(asset).length} página(s). Revisa las cajas y cantidades antes de crear.`);
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
        const draft = this.drafts.get(asset, page);
        const row = el("article", null, "ev2-page-plan-row");
        row.dataset.page = String(page.number);
        row.classList.toggle("is-inspected", this.current()?.page === page.number && !this.editing);
        const sourceButton = el("button", null, "ev2-preparation-thumbnail");
        sourceButton.type = "button"; sourceButton.dataset.configurePage = String(page.number);
        sourceButton.setAttribute("aria-label", `Configurar página ${page.number}`);
        const image = el("img"); image.src = thumbnailUrl(this.context.assets_api_url, asset.id, page.number); image.alt = ""; image.loading = "lazy";
        sourceButton.append(image);
        const body = el("div", null, "ev2-preparation-page-body");
        const selectionLabel = el("label", null, "ev2-preparation-page-label");
        const checkbox = el("input"); checkbox.type = "checkbox"; checkbox.checked = draft.selected;
        checkbox.dataset.pagePlanSelected = "true"; checkbox.dataset.page = String(page.number); checkbox.dataset.preparationRow = "selected";
        checkbox.disabled = Boolean(this.editing);
        selectionLabel.append(checkbox, document.createTextNode(`Página ${page.number}`));
        const qtyLabel = el("label", "Formas"); const qty = el("input"); qty.type = "number"; qty.min = "1"; qty.step = "1"; qty.value = draft.quantity;
        qty.dataset.pagePlanQuantity = "true"; qty.dataset.page = String(page.number); qty.dataset.preparationRow = "quantity";
        qty.setAttribute("aria-label", `Cantidad de formas para página ${page.number}`); qty.disabled = Boolean(this.editing); qtyLabel.append(qty);
        const validBox = page.boxes_mm[draft.box];
        const info = el("p", `${boxLabel(draft.box)}${validBox ? "" : " · NO DISPONIBLE"} · ${draft.width} × ${draft.height} mm · sangrado ${draft.bleed} mm · ${draft.rotations.join("° / ")}°`);
        if (!validBox) info.className = "ev2-preparation-warning";
        body.append(selectionLabel, qtyLabel, info);
        const existing = this.store.layout.works.filter((work) => Preparation.matches(work, draft));
        if (existing.length) {
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
      this.refs.preparationApply.disabled = !selected.length || Boolean(this.editing);
    }
    renderCoverage(draft, page) {
      const size = Preparation.dimensions(page, draft.box);
      this.refs.boxDimensions.textContent = size ? `Caja fuente: ${size.width} × ${size.height} mm` : "Caja no disponible en esta página";
      this.refs.preparationCoverage.textContent = Number(draft.bleed) > 0
        ? `Sangrado solicitado: ${draft.bleed} mm. La cobertura física se comprueba en preflight; este valor no genera contenido fuera del corte.`
        : "Sin sangrado solicitado. El tamaño final y la caja fuente son datos distintos.";
    }
    renderSourceControls() {
      const r = this.refs, draft = this.current();
      r.assetSelect.replaceChildren();
      for (const asset of this.store.layout.assets.filter(isReadyAsset)) r.assetSelect.append(option(asset.id, asset.original_filename));
      const asset = draft && this.store.layout.assets.find((a) => a.id === draft.assetId);
      const page = asset?.pages.find((p) => p.number === draft.page);
      const placed = this.editing && this.store.layout.slots.some((s) => s.work_id === this.editing.before.id);
      r.assetPage.replaceChildren(); r.assetBox.replaceChildren();
      if (asset) for (const p of asset.pages) r.assetPage.append(option(p.number, `Página ${p.number}`));
      if (page) for (const box of Preparation.BOXES) {
        const opt = option(box, `${boxLabel(box)}${page.boxes_mm[box] ? "" : " · no disponible"}`);
        // Missing boxes stay selectable to make invalid bulk assignments visible and correctable.
        r.assetBox.append(opt);
      }
      for (const node of [r.assetSelect, r.assetPage]) node.disabled = !draft || Boolean(placed);
      for (const node of [r.assetBox, r.workSizeMode, r.workBleed, r.workBack, ...r.workRotations]) node.disabled = !draft || Boolean(placed);
      for (const node of [r.workName, r.workQuantity]) node.disabled = !draft;
      r.workWidth.disabled = r.workHeight.disabled = !draft || Boolean(placed) || draft.sizeMode === "box";
      r.preparationBulk.hidden = Boolean(this.editing);
      r.preparationEditActions.hidden = !this.editing;
      r.preparationTitle.textContent = this.editing ? `Editar: ${this.editing.before.name}` : `Configurar página ${draft?.page ?? ""}`;
      r.preparationNote.textContent = this.editing
        ? placed ? "Trabajo colocado: puedes cambiar nombre y cantidad sin alterar piezas. Para caja, medidas o sangrado, crea una variante." : "Editas un trabajo guardado sin piezas colocadas. Guarda para confirmar los cambios."
        : "Estos valores corresponden a la página indicada. Usa Aplicar a seleccionadas para compartir campos concretos.";
      if (!draft || !page) return;
      r.assetSelect.value = asset.id; r.assetPage.value = String(page.number); r.assetBox.value = draft.box;
      r.workName.value = draft.name; r.workWidth.value = draft.width; r.workHeight.value = draft.height;
      r.workSizeMode.value = draft.sizeMode; r.workQuantity.value = draft.quantity; r.workBleed.value = draft.bleed; r.workBack.checked = draft.back;
      for (const rotation of r.workRotations) rotation.checked = draft.rotations.includes(Number(rotation.value));
      this.renderCoverage(draft, page);
    }
    renderWorks() {
      const r = this.refs, layout = this.store.layout;
      r.workSelect.replaceChildren(option("", "Selecciona un trabajo")); r.preparedWorks.replaceChildren();
      if (!layout.works.length) r.preparedWorks.append(el("p", "Todavía no hay trabajos guardados."));
      for (const work of layout.works) {
        r.workSelect.append(option(work.id, work.name));
        const card = el("article", null, "ev2-prepared-work");
        const source = work.front_source; const asset = layout.assets.find((a) => a.id === source?.asset_id);
        const count = layout.slots.filter((slot) => slot.work_id === work.id).length;
        const body = el("div"); body.append(el("strong", work.name));
        body.append(el("p", `${asset?.original_filename ?? "Sin fuente"} · pág. ${source?.page ?? "—"} · ${source?.pdf_box ? boxLabel(source.pdf_box) : "—"} · ${work.trim_size_mm.width} × ${work.trim_size_mm.height} mm`));
        body.append(el("small", `${work.requested_forms} formas solicitadas · ${count} piezas colocadas (todas las caras) · sangrado ${work.bleed_mm} mm · ${work.allowed_rotations_deg.join("° / ")}°`));
        const edit = el("button", "Editar"); edit.type = "button"; edit.dataset.editWork = work.id; edit.disabled = !asset || !source;
        edit.setAttribute("aria-label", `Editar trabajo ${work.name}`); card.append(body, edit); r.preparedWorks.append(card);
      }
      r.workSelect.value = this.store.assetPanel.selectedWorkId || "";
      r.createRealSlot.disabled = !r.workSelect.value;
    }
    editWork(id) {
      if (this.editing) throw new Error("Guarda o cancela la edición actual.");
      const work = this.store.layout.works.find((w) => w.id === id);
      const asset = this.store.layout.assets.find((a) => a.id === work?.front_source?.asset_id);
      const page = asset?.pages.find((p) => p.number === work.front_source.page);
      if (!page) throw new Error("La fuente de este trabajo no está disponible.");
      const draft = { ...clone(this.drafts.get(asset, page)),
        selected: false, name: work.name, box: work.front_source.pdf_box,
        width: work.trim_size_mm.width, height: work.trim_size_mm.height, sizeMode: "custom",
        quantity: work.requested_forms, bleed: work.bleed_mm, rotations: [...work.allowed_rotations_deg],
        back: this.commands.UpdateWorkCommand.equal(work.back_source, work.front_source), variant: false };
      this.editing = { before: clone(work), draft, initialBack: draft.back };
      this.renderAll(); this.refs.preparationSettings.focus({ preventScroll: true });
    }
    cancelEdit() { this.editing = null; this.renderAll(); this.message("Edición cerrada. Los borradores de páginas se conservan."); }
    variantWork() {
      if (!this.editing) return;
      const draft = clone(this.editing.draft); this.editing = null;
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
      let patch = { name: draft.name.trim(), requested_forms: Number(draft.quantity) };
      if (!placed) {
        const asset = this.store.layout.assets.find((a) => a.id === draft.assetId);
        const entry = Preparation.entry(draft, asset);
        const candidate = this.commands.createWorkFromSource(this.store.layout, entry.source, entry.values, token());
        patch = { ...patch, front_source: candidate.front_source, trim_size_mm: candidate.trim_size_mm,
          bleed_mm: candidate.bleed_mm, allowed_rotations_deg: candidate.allowed_rotations_deg,
          back_source: !initialBack && !draft.back ? before.back_source : candidate.back_source };
      }
      const command = new this.commands.UpdateWorkCommand(this.store.layout, before.id, patch);
      this.store.executeCommand(command); this.editing = null; this.renderAll(); this.message("Trabajo actualizado. Las piezas existentes no se han modificado.");
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
      this.refs.replaceSourceLabel.textContent = source ? `Fuente preparada: página ${source.page} · ${boxLabel(source.pdf_box)}. Sustituir afecta solo al slot seleccionado.` : "Elige una fuente válida en Preparar.";
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
        const sheet = this.store.layout.sheet.size_mm;
        const slot = this.commands.createSlotFromWork(
          this.store.layout,
          this.refs.workSelect.value,
          token(),
          {
            x_mm: sheet.width / 2 - this.store.pan.x,
            y_mm: sheet.height / 2 - this.store.pan.y,
          },
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
