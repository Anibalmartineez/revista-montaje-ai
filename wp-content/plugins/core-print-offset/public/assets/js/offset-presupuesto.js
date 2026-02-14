(function () {
    const form = document.querySelector('[data-cpo-presupuesto]');
    if (!form || typeof window.cpoOffsetPresupuesto === 'undefined') {
        return;
    }

    const config = window.cpoOffsetPresupuesto;
    const calcButton = form.querySelector('[data-cpo-calc]');
    const saveButton = form.querySelector('[data-cpo-save]');
    const createOrderPrimaryButton = form.querySelector('[data-cpo-create-order-primary]');
    const alertBox = form.querySelector('[data-cpo-alert]');
    const materialSelect = form.querySelector('[data-material-select]');
    const materialPrice = form.querySelector('[data-material-price]');
    const pliegoSelect = form.querySelector('[data-pliego-select]');
    const pliegoCustom = form.querySelector('[data-pliego-custom]');
    const pliegoOverride = form.querySelector('[data-pliego-override]');
    const machineSelect = form.querySelector('[data-machine-select]');
    const horasInput = form.querySelector('[data-horas-input]');
    const costoInput = form.querySelector('[data-costo-input]');
    const clienteSelect = form.querySelector('[data-cliente-select]');
    const clienteTextWrapper = form.querySelector('[data-cliente-text]');
    const presupuestoIdInput = form.querySelector('[data-presupuesto-id]');
    const breakdownBox = form.querySelector('[data-result-breakdown]');
    const workTypeSelect = form.querySelector('[name="work_type"]');
    const structureBox = form.querySelector('[data-work-structure]');
    const productionSummaryNode = form.querySelector('[data-production-summary]');
    const productionChipsNode = form.querySelector('[data-production-chips]');
    const warningsNode = form.querySelector('[data-technical-warnings]');
    const cannotCalculateNode = form.querySelector('[data-cannot-calculate]');

    let currentCanCalculate = true;

    const formatCurrency = (value) => {
        if (Number.isNaN(value)) {
            return '-';
        }
        return new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
    };

    const showAlert = (message, type = 'error') => {
        if (!alertBox) {
            return;
        }
        alertBox.textContent = message;
        alertBox.hidden = false;
        alertBox.classList.toggle('is-success', type === 'success');
        alertBox.classList.toggle('is-warning', type === 'warning');
    };

    const clearAlert = () => {
        if (!alertBox) {
            return;
        }
        alertBox.textContent = '';
        alertBox.hidden = true;
        alertBox.classList.remove('is-success');
        alertBox.classList.remove('is-warning');
    };

    const parseNumber = (value) => {
        const parsed = parseFloat(value);
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const getFieldValue = (fieldName) => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (!field) {
            return '';
        }
        if (field.type === 'checkbox') {
            return field.checked ? '1' : '';
        }
        return (field.value || '').trim();
    };

    const setSaveButtonState = () => {
        if (!saveButton) {
            return;
        }
        if (currentCanCalculate) {
            saveButton.disabled = false;
            saveButton.title = '';
        } else {
            saveButton.disabled = true;
            saveButton.title = config.strings.technicalIncomplete || 'Complete los datos técnicos para continuar';
        }
    };

    const setRequiredLabels = (requiredFields = [], missingFields = []) => {
        const wrappers = form.querySelectorAll('[data-work-field]');
        wrappers.forEach((wrapper) => {
            const field = wrapper.dataset.workField;
            const isRequired = requiredFields.includes(field);
            const isMissing = missingFields.includes(field);
            wrapper.classList.toggle('is-required', isRequired);
            wrapper.classList.toggle('is-missing', isMissing);

            const labelTitle = wrapper.querySelector('.cpo-required-tag');
            if (labelTitle) {
                labelTitle.remove();
            }
            if (isRequired) {
                const tag = document.createElement('small');
                tag.className = 'cpo-required-tag';
                tag.textContent = 'requerido';
                wrapper.appendChild(tag);
            }
        });
    };

    const toggleStructureByWorkType = () => {
        const workType = workTypeSelect?.value || 'otro';
        if (!structureBox) {
            return;
        }
        const visibility = {
            paginas: ['revista', 'folleto'],
            encuadernacion: ['revista', 'folleto'],
            troquel: ['troquel', 'caja'],
            costo_troquel: ['troquel', 'caja'],
            merma_troquel_extra: ['troquel', 'caja'],
            material_bobina: ['etiqueta', 'caja'],
            anilox: ['etiqueta', 'caja'],
            cilindro: ['etiqueta', 'caja'],
        };

        structureBox.querySelectorAll('[data-work-field]').forEach((node) => {
            const key = node.dataset.workField;
            const show = (visibility[key] || []).includes(workType);
            node.hidden = !show;
        });
    };

    const updateMaterialPrice = () => {
        if (!materialSelect || !materialPrice) {
            return;
        }
        const selected = materialSelect.options[materialSelect.selectedIndex];
        const price = selected ? selected.dataset.price : '';
        const currency = selected ? selected.dataset.moneda : 'PYG';
        materialPrice.textContent = price
            ? `Precio vigente: ${formatCurrency(parseFloat(price))} ${currency}`
            : config.strings.priceMissing;
    };

    const updateClienteFields = () => {
        if (!clienteSelect || !clienteTextWrapper) {
            return;
        }
        const showOther = clienteSelect.value === 'other';
        clienteTextWrapper.hidden = !showOther;
    };

    const getSelectedClienteId = () => {
        if (!clienteSelect) {
            return 0;
        }
        const value = clienteSelect.value;
        if (value === 'other' || value === '0' || value === '') {
            return 0;
        }
        const parsed = parseNumber(value);
        return parsed > 0 ? parsed : 0;
    };

    const updateCreateOrderButtonState = () => {
        if (!createOrderPrimaryButton) {
            return;
        }
        const presupuestoId = presupuestoIdInput?.value ? parseNumber(presupuestoIdInput.value) : 0;
        createOrderPrimaryButton.disabled = presupuestoId <= 0;
        createOrderPrimaryButton.title = presupuestoId > 0 ? '' : (config.strings.coreSaveRequired || 'Guarda y acepta el presupuesto para crear la OT.');
    };

    const getPliegosEstimados = () => {
        const cantidad = parseNumber(form.querySelector('[name="cantidad"]')?.value);
        const formas = parseNumber(form.querySelector('[name="formas_por_pliego"]')?.value);
        const merma = parseNumber(form.querySelector('[name="merma_pct"]')?.value);
        if (!cantidad || !formas) {
            return 0;
        }
        return Math.ceil((cantidad / Math.max(1, formas)) * (1 + merma / 100));
    };

    const updateMachineFields = () => {
        if (!machineSelect) {
            return;
        }
        const selected = machineSelect.options[machineSelect.selectedIndex];
        const cost = selected ? parseNumber(selected.dataset.cost) : 0;
        const rendimiento = selected ? parseNumber(selected.dataset.rendimiento) : 0;
        const setupMin = selected ? parseNumber(selected.dataset.setup) : 0;

        if (costoInput && (!costoInput.value || costoInput.dataset.userEdited !== 'true')) {
            costoInput.value = cost ? cost.toFixed(2) : '';
        }
        if (horasInput && horasInput.dataset.userEdited !== 'true' && rendimiento > 0) {
            const pliegos = getPliegosEstimados();
            if (pliegos > 0) {
                horasInput.value = ((setupMin / 60) + (pliegos / rendimiento)).toFixed(2);
            }
        }
    };

    const ensurePliegoOption = (value, label) => {
        if (!pliegoSelect) {
            return;
        }
        const options = Array.from(pliegoSelect.options);
        if (!options.some((option) => option.value === value)) {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label || value;
            pliegoSelect.appendChild(option);
        }
    };

    const applyPliegoFromMaterial = () => {
        if (!materialSelect || !pliegoSelect) {
            return '';
        }
        const selected = materialSelect.options[materialSelect.selectedIndex];
        const formatoBase = selected ? selected.dataset.formatoBase : '';
        if (formatoBase) {
            ensurePliegoOption(formatoBase, formatoBase);
            pliegoSelect.value = formatoBase;
        }
        return formatoBase || '';
    };

    const toggleCustomPliego = () => {
        if (!pliegoSelect || !pliegoCustom) {
            return;
        }
        const selected = materialSelect ? materialSelect.options[materialSelect.selectedIndex] : null;
        const formatoBase = selected ? selected.dataset.formatoBase : '';
        const override = pliegoOverride && pliegoOverride.checked;
        const shouldUseMaterial = Boolean(formatoBase) && !override;

        if (shouldUseMaterial) {
            applyPliegoFromMaterial();
        }

        pliegoSelect.hidden = shouldUseMaterial;
        if (pliegoOverride) {
            pliegoOverride.hidden = !formatoBase;
        }

        const isCustom = pliegoSelect.value === 'custom';
        pliegoCustom.hidden = shouldUseMaterial || !isCustom;
    };

    const getFormData = () => {
        const formData = new FormData(form);
        if (!formData.get('work_type')) {
            formData.append('work_type', 'otro');
        }
        formData.append('nonce', config.nonce);
        formData.append('cliente_id', String(getSelectedClienteId()));
        return formData;
    };

    const renderTechnicalSummary = (data = {}) => {
        if (productionSummaryNode) {
            productionSummaryNode.textContent = data.production_summary || '';
        }

        if (productionChipsNode) {
            productionChipsNode.innerHTML = '';
            const production = data.production || {};
            const chips = [
                ['Chapas', production.chapas],
                ['Pasadas', production.pasadas],
                ['Merma técnica', production.merma_pliegos],
                ['Pliegos', production.pliegos],
                ['Tiempo', production.tiempo_horas ? `${production.tiempo_horas} h` : ''],
            ].filter((item) => item[1] !== undefined && item[1] !== null && item[1] !== '');

            chips.forEach(([label, value]) => {
                const chip = document.createElement('span');
                chip.className = 'cpo-chip';
                chip.textContent = `${label}: ${value}`;
                productionChipsNode.appendChild(chip);
            });
        }

        const warnings = Array.isArray(data.warnings) ? data.warnings : [];
        if (warningsNode) {
            warningsNode.hidden = warnings.length === 0;
            warningsNode.innerHTML = warnings.length
                ? `<strong>Advertencias</strong><ul>${warnings.map((warning) => `<li>${warning}</li>`).join('')}</ul>`
                : '';
        }

        const missing = Array.isArray(data.missing_fields) ? data.missing_fields : [];
        if (cannotCalculateNode) {
            cannotCalculateNode.hidden = currentCanCalculate;
            cannotCalculateNode.textContent = currentCanCalculate ? '' : `Complete los campos requeridos: ${missing.join(', ')}`;
        }
    };

    const applyResults = (data) => {
        form.querySelectorAll('[data-result]').forEach((node) => {
            const key = node.dataset.result;
            if (!key) return;
            if (key === 'price_note') {
                node.textContent = data.price_note || '';
                return;
            }
            const value = data[key];
            if (key === 'pliegos_necesarios') {
                node.textContent = value ?? '-';
            } else if (typeof value === 'number') {
                node.textContent = formatCurrency(value);
            } else {
                node.textContent = value ?? '-';
            }
        });

        if (horasInput && typeof data.horas_maquina === 'number' && horasInput.dataset.userEdited !== 'true') {
            horasInput.value = data.horas_maquina ? parseNumber(data.horas_maquina).toFixed(2) : '';
        }
        if (costoInput && typeof data.costo_hora === 'number' && costoInput.dataset.userEdited !== 'true') {
            costoInput.value = data.costo_hora ? parseNumber(data.costo_hora).toFixed(2) : '';
        }

        if (breakdownBox) {
            breakdownBox.innerHTML = '';
            const items = [];
            if (data.material) {
                items.push({ label: `Papel${data.material?.nombre ? ` (${data.material.nombre})` : ''}`, detail: `${data.pliegos_con_merma ?? data.pliegos_necesarios ?? 0} pliegos x ${formatCurrency(data.precio_pliego ?? 0)}`, total: data.costo_papel ?? 0 });
            }
            if (data.maquina && data.costo_maquina) {
                items.push({ label: `Máquina${data.maquina?.nombre ? ` (${data.maquina.nombre})` : ''}`, detail: `${data.horas_maquina ?? 0} h x ${formatCurrency(data.costo_hora ?? 0)}`, total: data.costo_maquina ?? 0 });
            }
            if (Array.isArray(data.procesos)) {
                data.procesos.forEach((process) => {
                    items.push({ label: `Proceso (${process.nombre})`, detail: process.detalle_calculo || `${process.cantidad} x ${formatCurrency(process.unitario ?? 0)}`, total: process.subtotal ?? 0 });
                });
            }
            if (items.length) {
                items.forEach((item) => {
                    const row = document.createElement('div');
                    row.className = 'cpo-breakdown__row';
                    row.innerHTML = `<span>${item.label}<small>${item.detail}</small></span><strong>${formatCurrency(item.total)}</strong>`;
                    breakdownBox.appendChild(row);
                });
                breakdownBox.hidden = false;
            } else {
                breakdownBox.hidden = true;
            }
        }

        renderTechnicalSummary(data);
    };

    const validateStructure = async () => {
        const formData = getFormData();
        formData.append('action', 'cpo_offset_validate_structure');

        const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
        const payload = await response.json();
        if (!payload.success) {
            return null;
        }

        const data = payload.data || {};
        currentCanCalculate = data.can_calculate !== false;
        setRequiredLabels(data.required_fields || [], data.missing_fields || []);
        setSaveButtonState();
        renderTechnicalSummary(data);
        return data;
    };

    const applyPayloadToForm = (payload, meta = {}) => {
        if (!payload) return;

        const setValue = (name, value) => {
            const field = form.querySelector(`[name="${name}"]`);
            if (!field) return;
            if (field.type === 'checkbox') {
                field.checked = Boolean(value) && value !== '0';
            } else {
                field.value = value ?? '';
            }
        };

        ['descripcion', 'cantidad', 'ancho_mm', 'alto_mm', 'colores', 'sangrado_mm', 'material_id', 'pliego_formato', 'pliego_ancho_mm', 'pliego_alto_mm', 'formas_por_pliego', 'merma_pct', 'work_type', 'paginas', 'encuadernacion', 'material_bobina', 'anilox', 'cilindro', 'costo_troquel', 'merma_troquel_extra'].forEach((field) => {
            setValue(field, payload[field]);
        });
        setValue('troquel', payload.troquel);
        setValue('margin_pct', payload.margin_pct || payload.margen_pct || 30);

        if (pliegoOverride) pliegoOverride.checked = Boolean(payload.pliego_personalizado);
        if (machineSelect) machineSelect.value = payload.maquina_id != null ? String(payload.maquina_id) : '0';

        if (clienteSelect) {
            const clienteId = meta.cliente_id || payload.cliente_id || 0;
            clienteSelect.value = clienteId ? String(clienteId) : (payload.cliente_texto ? 'other' : '0');
            const textInput = clienteTextWrapper?.querySelector('input');
            if (textInput) textInput.value = payload.cliente_texto || meta.cliente_texto || '';
        }

        updateMaterialPrice();
        toggleCustomPliego();
        updateMachineFields();
        updateClienteFields();
        toggleStructureByWorkType();
        updateCreateOrderButtonState();
    };

    const fetchPresupuesto = async (presupuestoId) => {
        const formData = getFormData();
        formData.append('action', 'cpo_offset_get_presupuesto');
        formData.append('presupuesto_id', presupuestoId);
        const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.loadFailed);
            return null;
        }
        return payload.data;
    };

    const loadPresupuesto = async (presupuestoId) => {
        clearAlert();
        const payload = await fetchPresupuesto(presupuestoId);
        if (!payload) return;
        if (presupuestoIdInput) presupuestoIdInput.value = payload.id;
        applyPayloadToForm(payload.payload, { cliente_id: payload.cliente_id, cliente_texto: payload.cliente_texto });
        if (payload.calc_result) applyResults(payload.calc_result);
        await validateStructure();
        showAlert('Presupuesto cargado.', 'success');
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    const calculate = async () => {
        clearAlert();
        await validateStructure();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_calculate');
        const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || 'Error');
            return null;
        }
        applyResults(payload.data);
        return payload.data;
    };

    const savePresupuesto = async () => {
        if (!config.canSave) {
            showAlert('Debes iniciar sesión para guardar.');
            return;
        }
        if (!currentCanCalculate) {
            showAlert(config.strings.technicalIncomplete || 'Complete los datos técnicos para continuar', 'warning');
            return;
        }
        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_save_presupuesto');

        const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.savingError);
            setRequiredLabels(payload.data?.required_fields || [], payload.data?.fields || []);
            return;
        }
        showAlert(payload.data?.message || config.strings.saved, 'success');
        if (presupuestoIdInput && payload.data?.id) presupuestoIdInput.value = payload.data.id;
        updateCreateOrderButtonState();
        renderTechnicalSummary(payload.data || {});
    };

    const createOrderFromPresupuesto = async (presupuestoId) => {
        if (!presupuestoId) return;
        const numeroOrden = window.prompt('Número de OT (opcional):', '');
        if (numeroOrden === null) return;
        const fechaEntrega = window.prompt('Fecha de entrega (YYYY-MM-DD, opcional):', '');
        if (fechaEntrega === null) return;
        const notas = window.prompt('Notas de OT (opcional):', '');
        if (notas === null) return;

        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_convert_to_order');
        formData.append('presupuesto_id', presupuestoId);
        formData.append('numero_orden', numeroOrden || '');
        formData.append('fecha_entrega', fechaEntrega || '');
        formData.append('notas', notas || '');

        const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.orderCreateFailed);
            return;
        }
        showAlert(payload.data?.message || config.strings.orderCreated, 'success');
        window.setTimeout(() => window.location.reload(), 300);
    };

    const generateInvoiceFromOrder = async (ordenId) => {
        const formData = getFormData();
        formData.append('action', 'cpo_offset_generate_core_document_from_order');
        formData.append('orden_id', ordenId);
        const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.invoiceFromOrderFailed);
            return;
        }
        showAlert(payload.data?.message || config.strings.coreCreated, 'success');
        window.setTimeout(() => window.location.reload(), 300);
    };

    calcButton?.addEventListener('click', calculate);
    saveButton?.addEventListener('click', savePresupuesto);
    createOrderPrimaryButton?.addEventListener('click', () => createOrderFromPresupuesto(presupuestoIdInput?.value || ''));

    const reactiveFields = ['work_type', 'cantidad', 'paginas', 'material_id', 'ancho_mm', 'alto_mm', 'troquel', 'anilox', 'encuadernacion', 'cilindro', 'material_bobina'];
    reactiveFields.forEach((fieldName) => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (!field) return;
        field.addEventListener(field.type === 'checkbox' ? 'change' : 'input', () => {
            if (fieldName === 'work_type') toggleStructureByWorkType();
            validateStructure();
        });
    });

    materialSelect?.addEventListener('change', () => {
        updateMaterialPrice();
        toggleCustomPliego();
        validateStructure();
    });
    clienteSelect?.addEventListener('change', () => {
        updateClienteFields();
        updateCreateOrderButtonState();
    });
    pliegoSelect?.addEventListener('change', () => {
        toggleCustomPliego();
        updateMachineFields();
        validateStructure();
    });
    pliegoOverride?.addEventListener('change', () => {
        toggleCustomPliego();
        validateStructure();
    });
    machineSelect?.addEventListener('change', updateMachineFields);
    horasInput?.addEventListener('input', () => { horasInput.dataset.userEdited = 'true'; });
    costoInput?.addEventListener('input', () => { costoInput.dataset.userEdited = 'true'; });

    updateMaterialPrice();
    toggleCustomPliego();
    updateMachineFields();
    updateClienteFields();
    toggleStructureByWorkType();
    setSaveButtonState();
    validateStructure();
    if (createOrderPrimaryButton) updateCreateOrderButtonState();

    document.addEventListener('click', async (event) => {
        const openButton = event.target.closest('[data-cpo-open]');
        if (openButton) return loadPresupuesto(openButton.dataset.cpoOpen);

        const duplicateButton = event.target.closest('[data-cpo-duplicate]');
        if (duplicateButton) {
            const formData = getFormData();
            formData.append('action', 'cpo_offset_duplicate_presupuesto');
            formData.append('presupuesto_id', duplicateButton.dataset.cpoDuplicate);
            const response = await fetch(config.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: formData });
            const payload = await response.json();
            if (payload.success && payload.data?.id) {
                await loadPresupuesto(payload.data.id);
            }
            return;
        }

        const createOrderButton = event.target.closest('[data-cpo-create-order]');
        if (createOrderButton?.dataset.cpoCreateOrder) return createOrderFromPresupuesto(createOrderButton.dataset.cpoCreateOrder);

        const generateInvoiceButton = event.target.closest('[data-cpo-generate-invoice]');
        if (generateInvoiceButton?.dataset.cpoGenerateInvoice) return generateInvoiceFromOrder(generateInvoiceButton.dataset.cpoGenerateInvoice);
    });

    const initialPresupuestoId = new URLSearchParams(window.location.search).get('cpo_presupuesto_id');
    if (initialPresupuestoId) loadPresupuesto(initialPresupuestoId);
})();
