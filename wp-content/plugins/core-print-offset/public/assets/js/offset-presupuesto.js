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

    const updateMaterialPrice = () => {
        if (!materialSelect || !materialPrice) {
            return;
        }
        const selected = materialSelect.options[materialSelect.selectedIndex];
        const price = selected ? selected.dataset.price : '';
        const currency = selected ? selected.dataset.moneda : 'PYG';
        if (price) {
            materialPrice.textContent = `Precio vigente: ${formatCurrency(parseFloat(price))} ${currency}`;
        } else {
            materialPrice.textContent = config.strings.priceMissing;
        }
    };

    const updateClienteFields = () => {
        if (!clienteSelect || !clienteTextWrapper) {
            return;
        }
        const showOther = clienteSelect.value === 'other';
        clienteTextWrapper.hidden = !showOther;
        if (!showOther) {
            const input = clienteTextWrapper.querySelector('input');
            if (input) {
                input.value = '';
            }
        }
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
        formData.append('nonce', config.nonce);
        return formData;
    };

    const applyResults = (data) => {
        const results = form.querySelectorAll('[data-result]');
        results.forEach((node) => {
            const key = node.dataset.result;
            if (!key) {
                return;
            }
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
        if (machineSelect && data.maquina_id && parseNumber(machineSelect.value) === 0) {
            machineSelect.value = String(data.maquina_id);
        }

        if (breakdownBox) {
            breakdownBox.innerHTML = '';
            const items = [];

            if (data.material) {
                items.push({
                    label: `Papel${data.material?.nombre ? ` (${data.material.nombre})` : ''}`,
                    detail: `${data.pliegos_con_merma ?? data.pliegos_necesarios ?? 0} pliegos x ${formatCurrency(data.precio_pliego ?? 0)}`,
                    total: data.costo_papel ?? 0,
                });
            }

            if (data.maquina && data.costo_maquina) {
                items.push({
                    label: `Máquina${data.maquina?.nombre ? ` (${data.maquina.nombre})` : ''}`,
                    detail: `${data.horas_maquina ?? 0} h x ${formatCurrency(data.costo_hora ?? 0)}`,
                    total: data.costo_maquina ?? 0,
                });
            }

            if (Array.isArray(data.procesos)) {
                data.procesos.forEach((process) => {
                    items.push({
                        label: `Proceso (${process.nombre})`,
                        detail: process.detalle_calculo || `${process.cantidad} x ${formatCurrency(process.unitario ?? 0)}`,
                        total: process.subtotal ?? 0,
                    });
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
    };

    const applyPayloadToForm = (payload, meta = {}) => {
        if (!payload) {
            return;
        }

        const setValue = (name, value) => {
            const field = form.querySelector(`[name="${name}"]`);
            if (!field) {
                return;
            }
            if (field.type === 'checkbox') {
                field.checked = Boolean(value);
            } else if (field.tagName === 'SELECT') {
                field.value = value != null ? String(value) : '';
            } else {
                field.value = value ?? '';
            }
        };

        setValue('descripcion', payload.descripcion || '');
        setValue('cantidad', payload.cantidad || 1);
        setValue('ancho_mm', payload.ancho_mm || '');
        setValue('alto_mm', payload.alto_mm || '');
        setValue('colores', payload.colores || '');
        setValue('sangrado_mm', payload.sangrado_mm || '');
        setValue('material_id', payload.material_id || 0);
        setValue('pliego_formato', payload.pliego_formato || '');
        setValue('pliego_ancho_mm', payload.pliego_ancho_mm || '');
        setValue('pliego_alto_mm', payload.pliego_alto_mm || '');
        if (pliegoOverride) {
            pliegoOverride.checked = Boolean(payload.pliego_personalizado);
        }
        setValue('formas_por_pliego', payload.formas_por_pliego || 1);
        setValue('merma_pct', payload.merma_pct || 0);
        setValue('margin_pct', payload.margin_pct || payload.margen_pct || 0);
        if (machineSelect) {
            machineSelect.value = payload.maquina_id != null ? String(payload.maquina_id) : '0';
        }
        if (horasInput) {
            horasInput.value = payload.horas_maquina ? Number(payload.horas_maquina).toFixed(2) : '';
            horasInput.dataset.userEdited = '';
        }
        if (costoInput) {
            costoInput.value = payload.costo_hora ? Number(payload.costo_hora).toFixed(2) : '';
            costoInput.dataset.userEdited = '';
        }

        const procesos = Array.isArray(payload.procesos) ? payload.procesos.map(String) : [];
        const procesoInputs = form.querySelectorAll('input[name="procesos[]"]');
        procesoInputs.forEach((input) => {
            input.checked = procesos.includes(input.value);
        });

        if (clienteSelect) {
            const clienteId = meta.cliente_id || payload.cliente_id || 0;
            if (clienteId) {
                clienteSelect.value = String(clienteId);
                if (clienteTextWrapper) {
                    const textInput = clienteTextWrapper.querySelector('input');
                    if (textInput) {
                        textInput.value = '';
                    }
                }
            } else if (payload.cliente_texto || meta.cliente_texto) {
                clienteSelect.value = 'other';
                if (clienteTextWrapper) {
                    const textInput = clienteTextWrapper.querySelector('input');
                    if (textInput) {
                        textInput.value = meta.cliente_texto || payload.cliente_texto || '';
                    }
                }
            } else {
                clienteSelect.value = '0';
            }
        }

        updateMaterialPrice();
        toggleCustomPliego();
        updateMachineFields();
        updateClienteFields();
        updateCreateOrderButtonState();
    };

    const fetchPresupuesto = async (presupuestoId) => {
        const formData = getFormData();
        formData.append('action', 'cpo_offset_get_presupuesto');
        formData.append('presupuesto_id', presupuestoId);

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

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
        if (!payload) {
            return;
        }
        if (presupuestoIdInput) {
            presupuestoIdInput.value = payload.id;
        }
        applyPayloadToForm(payload.payload, {
            cliente_id: payload.cliente_id,
            cliente_texto: payload.cliente_texto,
        });
        if (payload.calc_result) {
            applyResults(payload.calc_result);
        }
        showAlert('Presupuesto cargado.', 'success');
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    const calculate = async () => {
        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_calculate');

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || 'Error');
            return null;
        }
        applyResults(payload.data);
        if (payload.data?.price_note) {
            showAlert(payload.data.price_note, 'warning');
        } else if (Array.isArray(payload.data?.warnings) && payload.data.warnings.length) {
            showAlert(payload.data.warnings.join(' '), 'warning');
        }
        return payload.data;
    };

    const savePresupuesto = async () => {
        if (!config.canSave) {
            showAlert('Debes iniciar sesión para guardar.');
            return;
        }
        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_save_presupuesto');

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.savingError);
            return;
        }
        showAlert(payload.data?.message || config.strings.saved, 'success');
        if (presupuestoIdInput && payload.data?.id) {
            presupuestoIdInput.value = payload.data.id;
        }
        updateCreateOrderButtonState();
    };


    const createOrderFromPresupuesto = async (presupuestoId) => {
        if (!presupuestoId) {
            showAlert(config.strings.orderCreateFailed || 'No se pudo crear la orden de trabajo.');
            return;
        }
        const numeroOrden = window.prompt('Número de OT (opcional):', '');
        if (numeroOrden === null) {
            return;
        }
        const fechaEntrega = window.prompt('Fecha de entrega (YYYY-MM-DD, opcional):', '');
        if (fechaEntrega === null) {
            return;
        }
        const notas = window.prompt('Notas de OT (opcional):', '');
        if (notas === null) {
            return;
        }

        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_convert_to_order');
        formData.append('presupuesto_id', presupuestoId);
        formData.append('numero_orden', numeroOrden || '');
        formData.append('fecha_entrega', fechaEntrega || '');
        formData.append('notas', notas || '');

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.orderCreateFailed);
            return;
        }

        showAlert(payload.data?.message || config.strings.orderCreated, 'success');
        window.setTimeout(() => window.location.reload(), 400);
    };

    const generateInvoiceFromOrder = async (ordenId) => {
        if (!config.coreAvailable) {
            showAlert(config.strings.coreUnavailable || 'Core Global no disponible');
            return;
        }

        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_generate_core_document_from_order');
        formData.append('orden_id', ordenId);

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.invoiceFromOrderFailed);
            return;
        }

        showAlert(payload.data?.message || config.strings.coreCreated, 'success');
        window.setTimeout(() => window.location.reload(), 400);
    };


    calcButton?.addEventListener('click', () => {
        calculate();
    });

    saveButton?.addEventListener('click', () => {
        savePresupuesto();
    });
    createOrderPrimaryButton?.addEventListener('click', () => {
        createOrderFromPresupuesto(presupuestoIdInput?.value || '');
    });

    materialSelect?.addEventListener('change', () => {
        updateMaterialPrice();
        toggleCustomPliego();
    });
    clienteSelect?.addEventListener('change', () => {
        updateClienteFields();
        updateCreateOrderButtonState();
    });
    pliegoSelect?.addEventListener('change', () => {
        toggleCustomPliego();
        updateMachineFields();
    });
    pliegoOverride?.addEventListener('change', () => {
        toggleCustomPliego();
    });
    machineSelect?.addEventListener('change', updateMachineFields);

    horasInput?.addEventListener('input', () => {
        horasInput.dataset.userEdited = 'true';
    });
    costoInput?.addEventListener('input', () => {
        costoInput.dataset.userEdited = 'true';
    });

    updateMaterialPrice();
    toggleCustomPliego();
    updateMachineFields();
    updateClienteFields();

    if (createOrderPrimaryButton) {
        updateCreateOrderButtonState();
    }

    document.addEventListener('click', async (event) => {
        const openButton = event.target.closest('[data-cpo-open]');
        if (openButton) {
            event.preventDefault();
            await loadPresupuesto(openButton.dataset.cpoOpen);
            return;
        }

        const duplicateButton = event.target.closest('[data-cpo-duplicate]');
        if (duplicateButton) {
            event.preventDefault();
            clearAlert();
            const formData = getFormData();
            formData.append('action', 'cpo_offset_duplicate_presupuesto');
            formData.append('presupuesto_id', duplicateButton.dataset.cpoDuplicate);
            const response = await fetch(config.ajaxUrl, {
                method: 'POST',
                credentials: 'same-origin',
                body: formData,
            });
            const payload = await response.json();
            if (!payload.success) {
                showAlert(payload.data?.message || config.strings.duplicateFailed);
                return;
            }
            showAlert(payload.data?.message || 'Presupuesto duplicado.', 'success');
            if (payload.data?.id) {
                await loadPresupuesto(payload.data.id);
            }
            return;
        }

        const createOrderButton = event.target.closest('[data-cpo-create-order]');
        if (createOrderButton && createOrderButton.dataset.cpoCreateOrder) {
            event.preventDefault();
            await createOrderFromPresupuesto(createOrderButton.dataset.cpoCreateOrder);
            return;
        }

        const generateInvoiceButton = event.target.closest('[data-cpo-generate-invoice]');
        if (generateInvoiceButton && generateInvoiceButton.dataset.cpoGenerateInvoice) {
            event.preventDefault();
            await generateInvoiceFromOrder(generateInvoiceButton.dataset.cpoGenerateInvoice);
            return;
        }
    });

    const urlParams = new URLSearchParams(window.location.search);
    const initialPresupuestoId = urlParams.get('cpo_presupuesto_id');
    if (initialPresupuestoId) {
        loadPresupuesto(initialPresupuestoId);
    }
})();
