(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.AssetsPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function token() {
    return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function thumbnailUrl(baseUrl, assetId, pageNumber) {
    return `${baseUrl}/${encodeURIComponent(assetId)}/thumbnails/${pageNumber}`;
  }

  function option(value, label) {
    const item = document.createElement("option");
    item.value = String(value);
    item.textContent = label;
    return item;
  }

  function isReadyAsset(asset) {
    return Boolean(asset && asset.status === "ready" && asset.pages && asset.pages.length);
  }

  class AssetsPanel {
    constructor(store, refs, api, saver, context, commands, editPolicy) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.uploading = false;
      this.bind();
      this.unsubscribe = store.subscribe((event) => this.onStoreEvent(event));
      this.renderAll(true);
    }

    bind() {
      this.refs.assetUploadForm.addEventListener("submit", (event) => this.upload(event));
      this.refs.assetsList.addEventListener("click", (event) => this.selectThumbnail(event));
      this.refs.assetSelect.addEventListener("change", () => this.changeAsset());
      this.refs.assetPage.addEventListener("change", () => this.changePage());
      this.refs.assetBox.addEventListener("change", () => this.changeBox());
      this.refs.createWork.addEventListener("click", () => this.createWork());
      this.refs.workSelect.addEventListener("change", () => {
        this.store.setSelectedWork(this.refs.workSelect.value || null);
      });
      this.refs.createRealSlot.addEventListener("click", () => this.createSlot());
      this.refs.replaceSource.addEventListener("click", () => this.replaceSource());
    }

    onStoreEvent(event) {
      if (["external_update", "command", "undo", "redo", "save_success"].includes(event.type)) {
        this.renderAll(false);
      } else if (event.type === "asset_selection") {
        this.renderAssets();
        this.renderSourceControls(true);
      } else if (event.type === "work_selection") {
        this.renderWorks();
      } else if (event.type === "upload_state") {
        this.renderUploadState();
      } else if (event.type === "selection") {
        this.renderActionState();
      }
    }

    renderAll(resetDefaults) {
      this.renderAssets();
      this.renderSourceControls(resetDefaults);
      this.renderWorks();
      this.renderUploadState();
      this.renderActionState();
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

    renderSourceControls(resetDefaults) {
      const selected = this.store.selectedAssetPage();
      this.refs.assetSelect.replaceChildren();
      for (const asset of this.store.layout.assets.filter(isReadyAsset)) {
        this.refs.assetSelect.append(option(asset.id, asset.original_filename));
      }
      if (!selected) {
        for (const control of [
          this.refs.assetSelect,
          this.refs.assetPage,
          this.refs.assetBox,
          this.refs.createWork,
        ]) control.disabled = true;
        this.refs.boxDimensions.textContent = "—";
        return;
      }
      this.refs.assetSelect.disabled = false;
      this.refs.assetPage.disabled = false;
      this.refs.assetBox.disabled = false;
      this.refs.createWork.disabled = false;
      this.refs.assetSelect.value = selected.asset.id;
      this.refs.assetPage.replaceChildren();
      for (const page of selected.asset.pages) {
        this.refs.assetPage.append(option(page.number, `Página ${page.number}`));
      }
      this.refs.assetPage.value = String(selected.page.number);
      this.refs.assetBox.replaceChildren();
      for (const boxName of ["trim", "crop", "media", "bleed"]) {
        if (selected.page.boxes_mm[boxName]) {
          this.refs.assetBox.append(option(boxName, `${boxName[0].toUpperCase()}${boxName.slice(1)}Box`));
        }
      }
      this.refs.assetBox.value = this.store.assetPanel.selectedPdfBox;
      const box = selected.page.boxes_mm[this.store.assetPanel.selectedPdfBox];
      const rotated = [90, 270].includes(selected.page.intrinsic_rotation_deg);
      const width = rotated ? box.height : box.width;
      const height = rotated ? box.width : box.height;
      this.refs.boxDimensions.textContent = `${width.toFixed(2)} × ${height.toFixed(2)} mm`;
      if (resetDefaults) {
        this.refs.workName.value = selected.asset.original_filename.replace(/\.pdf$/i, "");
        this.refs.workWidth.value = width.toFixed(3);
        this.refs.workHeight.value = height.toFixed(3);
        this.refs.workBleed.value = "0";
        this.refs.workQuantity.value = "1";
      }
    }

    renderWorks() {
      this.refs.workSelect.replaceChildren(option("", "Selecciona un work"));
      for (const work of this.store.layout.works) {
        this.refs.workSelect.append(option(work.id, work.name));
      }
      const selectedId = this.store.assetPanel.selectedWorkId;
      if (selectedId && this.store.layout.works.some((work) => work.id === selectedId)) {
        this.refs.workSelect.value = selectedId;
      }
      this.refs.createRealSlot.disabled = !this.refs.workSelect.value;
    }

    renderUploadState() {
      const state = this.store.assetPanel;
      this.refs.assetUploadButton.disabled = this.uploading;
      this.refs.assetUploadStatus.textContent = state.error || state.message || "";
      this.refs.assetUploadStatus.dataset.state = state.uploadStatus;
    }

    renderActionState() {
      const ids = [...this.store.selection];
      this.refs.replaceSource.disabled = ids.length !== 1
        || !this.store.selectedAssetPage()
        || !this.editPolicy.can(this.store.layout, ids, "replace_content");
    }

    selectThumbnail(event) {
      const button = event.target.closest("button[data-asset-id][data-page]");
      if (!button) return;
      const asset = this.store.layout.assets.find(
        (item) => item.id === button.dataset.assetId && isReadyAsset(item),
      );
      const page = asset?.pages.find((item) => item.number === Number(button.dataset.page));
      if (!asset || !page) return;
      const box = page.boxes_mm.trim ? "trim" : page.boxes_mm.crop ? "crop" : "media";
      this.store.setAssetSelection(asset.id, page.number, box);
    }

    changeAsset() {
      const asset = this.store.layout.assets.find(
        (item) => item.id === this.refs.assetSelect.value && isReadyAsset(item),
      );
      if (!asset) return;
      const page = asset.pages[0];
      const box = page.boxes_mm.trim ? "trim" : page.boxes_mm.crop ? "crop" : "media";
      this.store.setAssetSelection(asset.id, page.number, box);
    }

    changePage() {
      const selected = this.store.layout.assets.find(
        (item) => item.id === this.store.assetPanel.selectedAssetId,
      );
      const page = selected?.pages.find((item) => item.number === Number(this.refs.assetPage.value));
      if (!selected || !page) return;
      const box = page.boxes_mm.trim ? "trim" : page.boxes_mm.crop ? "crop" : "media";
      this.store.setAssetSelection(selected.id, page.number, box);
    }

    changeBox() {
      this.store.setAssetSelection(
        this.store.assetPanel.selectedAssetId,
        this.store.assetPanel.selectedPage,
        this.refs.assetBox.value,
      );
    }

    async upload(event) {
      event.preventDefault();
      const file = this.refs.assetFile.files[0];
      if (!file || this.uploading) {
        this.store.setUploadState("error", null, "Selecciona un archivo PDF.");
        return;
      }
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

    selectedSource() {
      const selected = this.store.selectedAssetPage();
      if (!selected) throw new Error("Selecciona una página de asset.");
      return {
        asset_id: selected.asset.id,
        page: selected.page.number,
        pdf_box: this.store.assetPanel.selectedPdfBox,
      };
    }

    createWork() {
      try {
        const work = this.commands.createWorkFromSource(
          this.store.layout,
          this.selectedSource(),
          {
            name: this.refs.workName.value,
            width: this.refs.workWidth.value,
            height: this.refs.workHeight.value,
            bleed: this.refs.workBleed.value,
            requestedForms: Number(this.refs.workQuantity.value),
            allowedRotations: [...this.refs.workRotations]
              .filter((item) => item.checked)
              .map((item) => Number(item.value)),
            useSameSourceForBack: this.refs.workBack.checked,
          },
          token(),
        );
        this.store.executeCommand(new this.commands.CreateWorkCommand(work));
        this.store.setSelectedWork(work.id);
        this.store.setUploadState("success", `Work ${work.name} creado.`);
      } catch (error) {
        this.store.setUploadState("error", null, error.message);
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

    dispose() {
      this.unsubscribe();
    }
  }

  return Object.freeze({ AssetsPanel, thumbnailUrl });
});
