(function () {
  "use strict";

  const API_BASE = "/api/sistema-presupuesto";
  const state = {
    catalogs: {
      materiales: [],
      maquinas: [],
      procesos: [],
    },
    catalogAdmin: {
      items: [],
      selectedId: null,
      selectedSource: null,
    },
    clients: {
      items: [],
      selectedId: null,
    },
    lastResult: null,
  };

  const $ = (selector) => document.querySelector(selector);

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    bindEvents();
    await checkHealth();
    await loadCatalogs();
    await loadCatalogAdmin();
    await refreshBudgets();
    await loadClients();
  }

  function bindEvents() {
    $("#sp-quote-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      await calculate(false);
    });
    $("#sp-save-button").addEventListener("click", async () => {
      await calculate(true);
    });
    $("#sp-refresh-budgets").addEventListener("click", refreshBudgets);
    $("#sp-tipo").addEventListener("change", syncTypeDefaults);
    $("#sp-modo-comercial").addEventListener("change", syncCommercialLimit);
    $("#sp-catalog-type").addEventListener("change", loadCatalogAdmin);
    $("#sp-refresh-catalog").addEventListener("click", loadCatalogAdmin);
    $("#sp-new-catalog-item").addEventListener("click", newCatalogItem);
    $("#sp-catalog-form").addEventListener("submit", saveCatalogItem);
    $("#sp-delete-catalog-item").addEventListener("click", deleteCatalogItem);
    $("#sp-clear-catalog-item").addEventListener("click", clearCatalogEditor);
    $("#sp-refresh-clients").addEventListener("click", loadClients);
    $("#sp-new-client").addEventListener("click", clearClientForm);
    $("#sp-client-form").addEventListener("submit", saveClient);
    $("#sp-delete-client").addEventListener("click", deleteClient);
    $("#sp-clear-client").addEventListener("click", clearClientForm);
  }

  async function checkHealth() {
    const status = $("#sp-api-status");
    try {
      const payload = await requestJson(`${API_BASE}/health`);
      status.textContent = payload.ok ? "API conectada" : "API con error";
      status.classList.toggle("sp-online", Boolean(payload.ok));
    } catch (error) {
      status.textContent = "API no disponible";
      status.classList.remove("sp-online");
    }
  }

  async function loadCatalogs() {
    const [materiales, maquinas, procesos] = await Promise.all([
      requestJson(`${API_BASE}/catalogos/materiales`),
      requestJson(`${API_BASE}/catalogos/maquinas`),
      requestJson(`${API_BASE}/catalogos/procesos`),
    ]);
    state.catalogs.materiales = materiales.catalogo.materiales || [];
    state.catalogs.maquinas = maquinas.catalogo.maquinas || [];
    state.catalogs.procesos = procesos.catalogo.procesos || [];
    fillSelect($("#sp-material"), state.catalogs.materiales);
    fillSelect($("#sp-maquina"), state.catalogs.maquinas);
    fillProcesses();
  }

  function fillSelect(select, items) {
    select.innerHTML = "";
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.nombre;
      select.appendChild(option);
    });
  }

  function fillProcesses() {
    const container = $("#sp-procesos");
    container.innerHTML = "";
    state.catalogs.procesos.forEach((process) => {
      const label = document.createElement("label");
      label.className = "sp-check";
      label.innerHTML = `
        <input type="checkbox" value="${escapeHtml(process.id)}">
        <span>${escapeHtml(process.nombre)}</span>
      `;
      container.appendChild(label);
    });
  }

  async function calculate(shouldSave) {
    const endpoint = shouldSave ? "cotizar-y-guardar" : "cotizar";
    try {
      const payload = buildQuoteRequest();
      const response = await requestJson(`${API_BASE}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = shouldSave ? response.record.result : response.result;
      state.lastResult = result;
      renderResult(result);
      if (shouldSave) {
        await refreshBudgets();
      }
    } catch (error) {
      renderError(error);
    }
  }

  function buildQuoteRequest() {
    const tipo = $("#sp-tipo").value;
    const frente = readInteger("#sp-colores-frente");
    const dorso = readInteger("#sp-colores-dorso");
    const modo = $("#sp-modo-comercial").value;
    const pct = readDecimal("#sp-comercial-pct");
    const impuestoPct = readDecimal("#sp-impuesto-pct");
    const producto = {
      titulo: labelForType(tipo),
      tipo,
      cantidad: readDecimal("#sp-cantidad"),
      unidad_cantidad: tipo === "revista" ? "ejemplar" : "unidad",
      ancho_mm: readDecimal("#sp-ancho-mm"),
      alto_mm: readDecimal("#sp-alto-mm"),
      sangrado_mm: readDecimal("#sp-sangrado-mm"),
      paginas: tipo === "revista" ? readInteger("#sp-paginas") : null,
      caras: dorso > 0 ? 2 : 1,
      colores: {
        frente,
        dorso,
        texto: `${frente}/${dorso}`,
      },
    };

    if (tipo === "revista") {
      producto.encuadernacion = {
        tipo: "caballete",
        proceso_id: "engrampado_caballete",
      };
    }

    if (tipo === "folleto_diptico" || tipo === "folleto_triptico") {
      producto.formato_abierto_mm = {
        ancho: producto.ancho_mm,
        alto: producto.alto_mm,
      };
      producto.formato_cerrado_mm = {
        ancho: String(Number(producto.ancho_mm) / (tipo === "folleto_diptico" ? 2 : 3)),
        alto: producto.alto_mm,
      };
      producto.paneles = tipo === "folleto_diptico" ? 2 : 3;
      producto.pliegues = tipo === "folleto_diptico" ? 1 : 2;
    }

    return {
      schema: "sistema_presupuesto.quote_request",
      schema_version: 1,
      cliente: {
        nombre: "Cliente UI aislada",
        referencia: "UI-AISLADA",
      },
      producto,
      produccion: {
        pliego_base_mm: {
          ancho: readDecimal("#sp-pliego-base-ancho"),
          alto: readDecimal("#sp-pliego-base-alto"),
        },
        pliego_util_mm: {
          ancho: readDecimal("#sp-pliego-util-ancho"),
          alto: readDecimal("#sp-pliego-util-alto"),
        },
        formas_por_pliego_manual: readOptionalDecimal("#sp-formas-manual"),
        merma_arranque_pliegos: readDecimal("#sp-merma-arranque"),
        merma_pct: readDecimal("#sp-merma-pct"),
        imposicion_origen: "ui_aislada",
      },
      costos: {
        moneda: "PYG",
        material_id: $("#sp-material").value,
        maquina_id: $("#sp-maquina").value,
        procesos_ids: selectedProcesses(),
        margen_pct: modo === "margen" ? pct : null,
        markup_pct: modo === "markup" ? pct : null,
        impuestos: impuestoPct === "0" ? [] : [{
          id: "iva_ui",
          nombre: "IVA UI",
          tasa_pct: impuestoPct,
          base: "precio_antes_impuestos",
          incluido: false,
          es_valor_ejemplo: true,
        }],
      },
    };
  }

  function renderResult(result) {
    $("#sp-precio-final").textContent = money(result.costos.precio_final, result.costos.moneda);
    $("#sp-precio-unitario").textContent = money(result.costos.precio_unitario, result.costos.moneda);
    $("#sp-subtotal").textContent = money(result.costos.costo_tecnico, result.costos.moneda);
    $("#sp-pliegos").textContent = result.produccion.pliegos_brutos;
    $("#sp-chapas").textContent = result.produccion.chapas;
    $("#sp-pasadas").textContent = result.produccion.pasadas;
    renderLines(result.costos.items || []);
    renderWarnings(result.warnings || []);
    $("#sp-json-output").textContent = JSON.stringify(result, null, 2);
  }

  function renderLines(items) {
    const container = $("#sp-cost-lines");
    container.innerHTML = "";
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "sp-line";
      row.innerHTML = `
        <div>
          <strong>${escapeHtml(item.descripcion)}</strong>
          <small>${escapeHtml(item.cantidad)} ${escapeHtml(item.unidad)} x ${escapeHtml(item.costo_unitario)}</small>
        </div>
        <strong>${money(item.subtotal, "PYG")}</strong>
      `;
      container.appendChild(row);
    });
  }

  function renderWarnings(warnings) {
    const list = $("#sp-warnings");
    list.innerHTML = "";
    if (!warnings.length) {
      const item = document.createElement("li");
      item.textContent = "Sin advertencias.";
      list.appendChild(item);
      return;
    }
    warnings.forEach((warning) => {
      const item = document.createElement("li");
      item.textContent = `${warning.code}: ${warning.message}`;
      list.appendChild(item);
    });
  }

  async function refreshBudgets() {
    try {
      const payload = await requestJson(`${API_BASE}/presupuestos`);
      renderBudgetList(payload.presupuestos || []);
    } catch (error) {
      $("#sp-budget-list").innerHTML = `<div class="sp-alert sp-error">${escapeHtml(error.message)}</div>`;
    }
  }

  async function loadClients() {
    try {
      const payload = await requestJson(`${API_BASE}/clientes`);
      state.clients.items = payload.clientes || [];
      renderClientList();
      showClientMessage("");
    } catch (error) {
      state.clients.items = [];
      renderClientList();
      showClientMessage(error.message, true);
    }
  }

  function renderClientList() {
    const container = $("#sp-client-list");
    container.innerHTML = "";
    if (!state.clients.items.length) {
      container.innerHTML = "<div class=\"sp-alert\">No hay clientes guardados.</div>";
      return;
    }
    state.clients.items.forEach((client) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sp-client-row";
      button.innerHTML = `
        <strong>${escapeHtml(client.nombre)}</strong>
        <span>${escapeHtml(client.empresa || client.email || client.telefono || client.cliente_id)}</span>
      `;
      button.addEventListener("click", () => selectClient(client));
      container.appendChild(button);
    });
  }

  function selectClient(client) {
    state.clients.selectedId = client.cliente_id;
    $("#sp-client-nombre").value = client.nombre || "";
    $("#sp-client-empresa").value = client.empresa || "";
    $("#sp-client-telefono").value = client.telefono || "";
    $("#sp-client-email").value = client.email || "";
    $("#sp-client-ruc").value = client.ruc || "";
    $("#sp-client-notas").value = client.notas || "";
    $("#sp-delete-client").disabled = false;
    showClientMessage("");
  }

  async function saveClient(event) {
    event.preventDefault();
    const payload = buildClientPayload();
    const isUpdate = Boolean(state.clients.selectedId);
    const url = isUpdate
      ? `${API_BASE}/clientes/${encodeURIComponent(state.clients.selectedId)}`
      : `${API_BASE}/clientes`;
    try {
      const response = await requestJson(url, {
        method: isUpdate ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.clients.selectedId = response.cliente.cliente_id;
      selectClient(response.cliente);
      await loadClients();
      showClientMessage(isUpdate ? "Cliente actualizado." : "Cliente creado.");
    } catch (error) {
      showClientMessage(error.message, true);
    }
  }

  async function deleteClient() {
    const clientId = state.clients.selectedId;
    if (!clientId) {
      showClientMessage("Selecciona un cliente para eliminar.", true);
      return;
    }
    try {
      await requestJson(`${API_BASE}/clientes/${encodeURIComponent(clientId)}`, {
        method: "DELETE",
      });
      clearClientForm();
      await loadClients();
      showClientMessage("Cliente eliminado.");
    } catch (error) {
      showClientMessage(error.message, true);
    }
  }

  function clearClientForm() {
    state.clients.selectedId = null;
    $("#sp-client-form").reset();
    $("#sp-delete-client").disabled = true;
    showClientMessage("");
  }

  function buildClientPayload() {
    return {
      nombre: $("#sp-client-nombre").value,
      empresa: $("#sp-client-empresa").value,
      telefono: $("#sp-client-telefono").value,
      email: $("#sp-client-email").value,
      ruc: $("#sp-client-ruc").value,
      notas: $("#sp-client-notas").value,
    };
  }

  function showClientMessage(message, isError) {
    const box = $("#sp-client-message");
    box.textContent = message;
    box.classList.toggle("sp-error", Boolean(isError));
  }

  async function loadCatalogAdmin() {
    const type = $("#sp-catalog-type").value;
    const collectionKey = catalogCollectionKey(type);
    try {
      const payload = await requestJson(`${API_BASE}/catalogos/${encodeURIComponent(type)}`);
      state.catalogAdmin.items = payload.catalogo[collectionKey] || [];
      renderCatalogList();
      showCatalogMessage("");
    } catch (error) {
      state.catalogAdmin.items = [];
      renderCatalogList();
      showCatalogMessage(error.message, true);
    }
  }

  function renderCatalogList() {
    const container = $("#sp-catalog-list");
    container.innerHTML = "";
    if (!state.catalogAdmin.items.length) {
      container.innerHTML = "<div class=\"sp-alert\">No hay items en este catalogo.</div>";
      return;
    }
    state.catalogAdmin.items.forEach((item) => {
      const source = item.origen_catalogo || "custom";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sp-catalog-row";
      button.innerHTML = `
        <strong>${escapeHtml(item.nombre || item.id)}</strong>
        <span>${escapeHtml(item.id)} · ${escapeHtml(source)}</span>
      `;
      button.addEventListener("click", () => selectCatalogItem(item));
      container.appendChild(button);
    });
  }

  function selectCatalogItem(item) {
    state.catalogAdmin.selectedId = item.id;
    state.catalogAdmin.selectedSource = item.origen_catalogo || "custom";
    $("#sp-catalog-json").value = JSON.stringify(stripCatalogUiFields(item), null, 2);
    $("#sp-delete-catalog-item").disabled = state.catalogAdmin.selectedSource !== "custom";
    showCatalogMessage(
      state.catalogAdmin.selectedSource === "default"
        ? "Item default seleccionado. Guardar crea un custom con el mismo ID y sobrescribe en la vista combinada."
        : ""
    );
  }

  function newCatalogItem() {
    state.catalogAdmin.selectedId = null;
    state.catalogAdmin.selectedSource = null;
    $("#sp-catalog-json").value = JSON.stringify(catalogTemplate($("#sp-catalog-type").value), null, 2);
    $("#sp-delete-catalog-item").disabled = true;
    showCatalogMessage("");
  }

  async function saveCatalogItem(event) {
    event.preventDefault();
    const type = $("#sp-catalog-type").value;
    let item;
    try {
      item = JSON.parse($("#sp-catalog-json").value || "{}");
    } catch (error) {
      showCatalogMessage("JSON invalido en el editor.", true);
      return;
    }

    const existing = state.catalogAdmin.items.find(
      (candidate) => candidate.id === item.id && candidate.origen_catalogo === "custom"
    );
    const isUpdate = Boolean(existing);
    const url = isUpdate
      ? `${API_BASE}/catalogos/${encodeURIComponent(type)}/custom/${encodeURIComponent(item.id)}`
      : `${API_BASE}/catalogos/${encodeURIComponent(type)}/custom`;

    try {
      const payload = await requestJson(url, {
        method: isUpdate ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item),
      });
      showCatalogMessage(isUpdate ? "Item custom actualizado." : "Item custom creado.");
      state.catalogAdmin.selectedId = payload.item.id;
      state.catalogAdmin.selectedSource = "custom";
      await loadCatalogs();
      await loadCatalogAdmin();
    } catch (error) {
      showCatalogMessage(error.message, true);
    }
  }

  async function deleteCatalogItem() {
    const type = $("#sp-catalog-type").value;
    const itemId = state.catalogAdmin.selectedId;
    if (!itemId || state.catalogAdmin.selectedSource !== "custom") {
      showCatalogMessage("Solo se pueden eliminar items custom.", true);
      return;
    }
    try {
      await requestJson(`${API_BASE}/catalogos/${encodeURIComponent(type)}/custom/${encodeURIComponent(itemId)}`, {
        method: "DELETE",
      });
      showCatalogMessage("Item custom eliminado.");
      clearCatalogEditor();
      await loadCatalogs();
      await loadCatalogAdmin();
    } catch (error) {
      showCatalogMessage(error.message, true);
    }
  }

  function clearCatalogEditor() {
    state.catalogAdmin.selectedId = null;
    state.catalogAdmin.selectedSource = null;
    $("#sp-catalog-json").value = "";
    $("#sp-delete-catalog-item").disabled = true;
  }

  function showCatalogMessage(message, isError) {
    const box = $("#sp-catalog-message");
    box.textContent = message;
    box.classList.toggle("sp-error", Boolean(isError));
  }

  function stripCatalogUiFields(item) {
    const copied = { ...item };
    delete copied.origen_catalogo;
    return copied;
  }

  function catalogCollectionKey(type) {
    return {
      materiales: "materiales",
      maquinas: "maquinas",
      procesos: "procesos",
    }[type] || "materiales";
  }

  function catalogTemplate(type) {
    if (type === "maquinas") {
      return {
        id: "maquina_custom",
        nombre: "Maquina custom",
        tipo: "offset_plana",
        cuerpos_color: 1,
        formato_minimo_mm: { ancho: "1", alto: "1" },
        formato_maximo_mm: { ancho: "1", alto: "1" },
        costos: {
          moneda: "PYG",
          costo_hora: "0",
          costo_arranque: "0",
          costo_lavado_por_color: "0",
          es_valor_ejemplo: true,
        },
        rendimiento: {
          velocidad_pliegos_hora: "1",
          setup_horas: "0",
          unidad: "pliegos_hora",
        },
        activo: true,
      };
    }
    if (type === "procesos") {
      return {
        id: "proceso_custom",
        nombre: "Proceso custom",
        categoria: "terminacion",
        modo_cobro: "fijo",
        base_calculo: "trabajo",
        tarifa: {
          moneda: "PYG",
          valor: "0",
          unidad: "trabajo",
          es_valor_ejemplo: true,
        },
        merma_extra_pct: "0",
        activo: true,
      };
    }
    return {
      id: "material_custom",
      nombre: "Material custom",
      tipo: "papel",
      gramaje_g_m2: "1",
      formato_pliego_mm: { ancho: "1", alto: "1" },
      costo: {
        modo: "por_pliego",
        moneda: "PYG",
        valor: "0",
        unidad: "pliego",
        es_valor_ejemplo: true,
      },
      merma_recomendada_pct: "0",
      activo: true,
    };
  }

  function renderBudgetList(items) {
    const container = $("#sp-budget-list");
    container.innerHTML = "";
    if (!items.length) {
      container.innerHTML = "<div class=\"sp-alert\">No hay presupuestos guardados.</div>";
      return;
    }
    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sp-budget-row";
      button.innerHTML = `
        <strong>${escapeHtml(item.presupuesto_id)}</strong>
        <span>${escapeHtml(item.estado)} · ${money(item.precio_final || "0", item.moneda || "PYG")}</span>
      `;
      button.addEventListener("click", () => openBudget(item.presupuesto_id));
      container.appendChild(button);
    });
  }

  async function openBudget(id) {
    try {
      const payload = await requestJson(`${API_BASE}/presupuestos/${encodeURIComponent(id)}`);
      $("#sp-budget-detail").textContent = JSON.stringify(payload.record, null, 2);
    } catch (error) {
      $("#sp-budget-detail").textContent = error.message;
    }
  }

  function syncTypeDefaults() {
    const tipo = $("#sp-tipo").value;
    if (tipo === "tarjeta") {
      $("#sp-ancho-mm").value = "90";
      $("#sp-alto-mm").value = "50";
      $("#sp-colores-dorso").value = "4";
    } else if (tipo === "revista") {
      $("#sp-ancho-mm").value = "210";
      $("#sp-alto-mm").value = "297";
      $("#sp-paginas").value = "32";
      $("#sp-colores-dorso").value = "4";
    } else if (tipo === "folleto_diptico" || tipo === "folleto_triptico") {
      $("#sp-ancho-mm").value = "297";
      $("#sp-alto-mm").value = "210";
      $("#sp-colores-dorso").value = "4";
    } else {
      $("#sp-ancho-mm").value = "148";
      $("#sp-alto-mm").value = "210";
      $("#sp-colores-dorso").value = "0";
    }
  }

  function syncCommercialLimit() {
    $("#sp-comercial-pct").max = $("#sp-modo-comercial").value === "margen" ? "99" : "999";
  }

  async function requestJson(url, options) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      const message = payload.error ? `${payload.error.code || payload.error.type}: ${payload.error.message}` : "Error de API";
      throw new Error(message);
    }
    return payload;
  }

  function renderError(error) {
    $("#sp-precio-final").textContent = "-";
    $("#sp-precio-unitario").textContent = "-";
    $("#sp-cost-lines").innerHTML = "";
    renderWarnings([{ code: "ERROR", message: error.message }]);
    $("#sp-json-output").textContent = JSON.stringify({ ok: false, error: error.message }, null, 2);
  }

  function selectedProcesses() {
    return Array.from(document.querySelectorAll("#sp-procesos input:checked")).map((input) => input.value);
  }

  function readDecimal(selector) {
    return String($(selector).value || "0");
  }

  function readOptionalDecimal(selector) {
    const value = $(selector).value;
    return value === "" ? null : String(value);
  }

  function readInteger(selector) {
    return Number.parseInt($(selector).value || "0", 10);
  }

  function labelForType(tipo) {
    return {
      volante: "Volante",
      tarjeta: "Tarjeta",
      revista: "Revista",
      folleto_diptico: "Folleto diptico",
      folleto_triptico: "Folleto triptico",
    }[tipo] || "Trabajo offset";
  }

  function money(value, currency) {
    const number = Number(value || 0);
    return `${currency || "PYG"} ${number.toLocaleString("es-PY", { maximumFractionDigits: 2 })}`;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#039;",
    }[char]));
  }
})();
