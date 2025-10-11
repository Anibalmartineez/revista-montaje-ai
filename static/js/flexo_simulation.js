const DEBUG = false;

document.addEventListener('DOMContentLoaded', () => {
  if (DEBUG) console.log('[SIM] DOM ready');

  const PREVIEW_PIXEL_SCALE = 0.28;
  const RENDER_DEBOUNCE_MS = 380;
  const canvas = document.getElementById('sim-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const baseImgEl = document.getElementById('sim-base-image');

  const inputs = {
    lpi: document.getElementById('lpi'),
    bcm: document.getElementById('bcm'),
    paso: document.getElementById('paso'),
    vel: document.getElementById('vel'),
    cob: document.getElementById('cov'),
  };

  const labels = {
    lpi: document.getElementById('lpi-val'),
    bcm: document.getElementById('bcm-val'),
    paso: document.getElementById('paso-val'),
    vel: document.getElementById('vel-val'),
    cob: document.getElementById('cov-val'),
  };

  const metricsEls = {
    ml: document.getElementById('metric-ml'),
    mlDetalle: document.getElementById('metric-ml-detalle'),
    mlIdeal: document.getElementById('metric-ml-ideal'),
    mlColors: document.getElementById('metric-ml-colors'),
    tac: document.getElementById('metric-tac'),
    tacDetalle: document.getElementById('metric-tac-limite'),
    trama: document.getElementById('metric-trama'),
    overprint: document.getElementById('metric-overprint'),
    coverage: document.getElementById('metric-coverage'),
    riesgoBadge: document.getElementById('riesgo-global'),
    riesgoValor: document.getElementById('riesgo-valor'),
    riesgoDetalle: document.getElementById('riesgo-detalle'),
    saveBtn: document.getElementById('sim-save'),
    viewLink: document.getElementById('sim-view'),
  };

  const diagnostico = window.diagnosticoJson || {};
  const usePipelineV2 = Boolean(window.USE_PIPELINE_V2);
  const analisis = window.analisisDetallado || {};
  const advertenciasLista = Array.isArray(window.advertencias) ? window.advertencias : [];
  const advertenciasStats = buildAdvertenciaStats(
    window.indicadoresAdvertencias,
    advertenciasLista,
  );

  const materialCoefficients = window.materialCoefficients || {};
  const materialCoefPreset = asNumber(window.materialCoefSeleccionado);
  const materialCoefDiagnostico = asNumber(diagnostico.coef_material);
  const materialCoefBase =
    materialCoefDiagnostico ?? materialCoefPreset ?? asNumber(materialCoefficients.default);

  const coverageBase = parseCoverageBase(diagnostico, usePipelineV2);
  const materialNombre = (diagnostico.material || '').toString();
  const baseImgUrl = normalizeUrl(
    canvas.dataset.baseImg ||
      (baseImgEl ? baseImgEl.getAttribute('src') : '') ||
      window.diag_img_web ||
      canvas.dataset.simImg ||
      '',
  );

  const baseImage = new Image();
  baseImage.crossOrigin = 'anonymous';
  let baseReady = false;
  let baseNaturalWidth = 0;
  let baseNaturalHeight = 0;

  baseImage.onload = () => {
    baseReady = true;
    baseNaturalWidth = baseImage.naturalWidth || baseImage.width || 0;
    baseNaturalHeight = baseImage.naturalHeight || baseImage.height || 0;
    if (DEBUG) console.log('[SIM] imagen base cargada');
    render();
  };
  baseImage.onerror = () => {
    baseReady = false;
    baseNaturalWidth = 0;
    baseNaturalHeight = 0;
    if (DEBUG) console.warn('[SIM] error cargando imagen base');
    render();
  };
  if (baseImgUrl) {
    const cacheBusted = baseImgUrl.includes('?')
      ? `${baseImgUrl}&cb=${Date.now()}`
      : `${baseImgUrl}?cb=${Date.now()}`;
    baseImage.src = cacheBusted;
  }

  let rafId = null;
  let debounceId = null;
  let currentDpr = window.devicePixelRatio || 1;
  let previewScaleFactor = 1;
  let displayWidth = 0;
  let displayHeight = 0;
  let lastDownloadUrl = null;
  let userModifiedAnyControl = false;
  const patternCache = {
    key: null,
    canvas: null,
    spacing: 0,
    offset: 0,
    blur: 0,
    shadow: 0,
  };

  applyInitialValues();

  window.addEventListener('resize', resize);
  window.addEventListener('beforeunload', () => {
    if (lastDownloadUrl) URL.revokeObjectURL(lastDownloadUrl);
  });
  if (baseImgEl) {
    baseImgEl.addEventListener('load', () => {
      if (DEBUG) console.log('[SIM] base img element load');
      resize();
    });
  }
  resize();
  if (!baseImgUrl) render();

  Object.values(inputs).forEach((el) => {
    if (!el) return;
    const handleInput = () => {
      userModifiedAnyControl = true;
      if (el === inputs.cob) {
        el.dataset.userModified = '1';
      }
      scheduleRender();
    };
    el.addEventListener('input', handleInput);
    el.addEventListener('change', handleInput);
  });

  if (metricsEls.saveBtn) {
    metricsEls.saveBtn.addEventListener('click', handleExport);
  }

  function scheduleRender() {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => render());
    }, RENDER_DEBOUNCE_MS);
  }

  function resize() {
    const rect = baseImgEl ? baseImgEl.getBoundingClientRect() : canvas.getBoundingClientRect();
    const container = canvas.parentElement;
    const fallbackWidth = container ? container.clientWidth : rect.width;
    const fallbackHeight = container ? container.clientHeight : rect.height;
    displayWidth = rect.width || fallbackWidth || canvas.clientWidth || canvas.width || 0;
    displayHeight = rect.height || fallbackHeight || canvas.clientHeight || canvas.height || 0;
    currentDpr = window.devicePixelRatio || 1;
    previewScaleFactor = Math.max(0.12, currentDpr * PREVIEW_PIXEL_SCALE);
    const targetWidth = Math.max(1, Math.round(displayWidth * previewScaleFactor));
    const targetHeight = Math.max(1, Math.round(displayHeight * previewScaleFactor));
    if (canvas.width !== targetWidth) canvas.width = targetWidth;
    if (canvas.height !== targetHeight) canvas.height = targetHeight;
    ctx.setTransform(previewScaleFactor, 0, 0, previewScaleFactor, 0, 0);
    render();
  }

  async function handleExport() {
    if (DEBUG) console.log('[SIM] export');
    if (baseImgUrl && !baseReady) {
      alert('La imagen base aún se está cargando. Intentá nuevamente en unos segundos.');
      return;
    }

    const revisionId = (window.revisionId || '').toString().trim() || 'actual';
    const coverageState = getCoverageState();
    const payload = {
      lpi: asNumber(inputs.lpi ? inputs.lpi.value : null),
      bcm: asNumber(inputs.bcm ? inputs.bcm.value : null),
      paso: asNumber(inputs.paso ? inputs.paso.value : null),
      velocidad: asNumber(inputs.vel ? inputs.vel.value : null),
      tacObjetivo: coverageState.slider ?? coverageState.sum,
    };

    const overlay = {};
    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      overlay[canal] = coverageState.scaled[canal] || 0;
    });
    payload.cobertura = overlay;

    if (metricsEls.saveBtn) {
      metricsEls.saveBtn.disabled = true;
      metricsEls.saveBtn.dataset.originalText = metricsEls.saveBtn.dataset.originalText || metricsEls.saveBtn.textContent;
      metricsEls.saveBtn.textContent = 'Generando PNG…';
    }

    try {
      const resp = await fetch(`/simulacion/exportar/${revisionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        let message = 'No se pudo generar el PNG final.';
        try {
          const errorJson = await resp.json();
          if (errorJson && errorJson.error) message = errorJson.error;
        } catch (e) {
          if (DEBUG) console.warn('[SIM] export error payload parse', e);
        }
        alert(message);
        return;
      }

      const blob = await resp.blob();
      if (!blob) {
        alert('No se recibió ningún archivo del servidor.');
        return;
      }

      if (lastDownloadUrl) URL.revokeObjectURL(lastDownloadUrl);
      lastDownloadUrl = URL.createObjectURL(blob);

      let filename = `sim_${revisionId}.png`;
      const disposition = resp.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      if (match) {
        filename = decodeURIComponent(match[1] || match[2]);
      }

      const tmpLink = document.createElement('a');
      tmpLink.href = lastDownloadUrl;
      tmpLink.download = filename;
      document.body.appendChild(tmpLink);
      tmpLink.click();
      document.body.removeChild(tmpLink);

      if (metricsEls.viewLink) {
        metricsEls.viewLink.href = lastDownloadUrl;
        metricsEls.viewLink.download = filename;
        metricsEls.viewLink.textContent = '🔍 Abrir PNG generado';
      }
    } catch (err) {
      if (DEBUG) console.error('[SIM] export error', err);
      alert('Ocurrió un error al comunicarse con el servidor.');
    } finally {
      if (metricsEls.saveBtn) {
        metricsEls.saveBtn.disabled = false;
        const label = metricsEls.saveBtn.dataset.originalText || '🖼️ Generar PNG final';
        metricsEls.saveBtn.textContent = label;
      }
    }
  }

  function render(updateUi = true) {
    const width = displayWidth || canvas.clientWidth || 0;
    const height = displayHeight || canvas.clientHeight || 0;
    if (width <= 0 || height <= 0) return;

    const coverageState = getCoverageState();
    if (updateUi) {
      updateLabels();
      updateMetrics(coverageState);
    }

    ctx.clearRect(0, 0, width, height);
    drawInkOverlay(ctx, width, height, coverageState);
    drawWarningOverlay(ctx, width, height);
  }

  function applyInitialValues() {
    if (inputs.cob) {
      inputs.cob.dataset.userModified = '0';
    }
    const mapping = [
      [inputs.lpi, ['anilox_lpi', 'lpi']],
      [inputs.bcm, ['anilox_bcm', 'bcm']],
      [inputs.paso, ['paso_del_cilindro', 'paso_cilindro', 'paso']],
      [inputs.vel, ['velocidad_impresion', 'velocidad']],
    ];

    mapping.forEach(([input, keys]) => {
      if (!input) return;
      const valor = resolveDiagnosticoValue(keys);
      if (valor === null || valor === undefined) return;
      const numerico = asNumber(valor);
      if (numerico !== null) {
        input.value = String(clampToInputRange(numerico, input));
      } else {
        input.value = valor;
      }
    });

    if (inputs.cob) {
      const tacInicial = leerTacFromDj(diagnostico, usePipelineV2);
      if (tacInicial !== null) {
        inputs.cob.value = String(clampToInputRange(tacInicial, inputs.cob));
      }
    }

    updateLabels();
  }

  function updateLabels() {
    if (inputs.lpi && labels.lpi) labels.lpi.textContent = `${formatNumber(inputs.lpi.value, 0)} lpi`;
    if (inputs.bcm && labels.bcm) labels.bcm.textContent = `${formatNumber(inputs.bcm.value, 1)} cm³/m²`;
    if (inputs.paso && labels.paso) labels.paso.textContent = `${formatNumber(inputs.paso.value, 0)} mm`;
    if (inputs.vel && labels.vel) labels.vel.textContent = `${formatNumber(inputs.vel.value, 0)} m/min`;
    if (inputs.cob && labels.cob) {
      const val = asNumber(inputs.cob.value);
      const display = val !== null ? val.toFixed(1) : formatNumber(inputs.cob.value, 1);
      labels.cob.textContent = `${display} % TAC`;
    }
  }

  function updateMetrics(coverageState) {
    const bcmVal = asNumber(inputs.bcm ? inputs.bcm.value : null);
    const velVal = asNumber(inputs.vel ? inputs.vel.value : null);
    const lpiVal = asNumber(inputs.lpi ? inputs.lpi.value : null) || 0;
    const widthM = getEffectiveWidth();
    const tacTotal = coverageState.sum;

    const coefUsado =
      materialCoefBase ?? resolveMaterialCoefficient(materialNombre, materialCoefPreset);
    const transmissionData = simulateInkTransfer(diagnostico, {
      bcm: bcmVal,
      velocidad: velVal,
      ancho: widthM,
      coberturaPorCanal: coverageState.scaled,
      coefMaterial: coefUsado,
    });
    const transmisionBase = asNumber(diagnostico.tinta_ml_min);
    const transmisionSim = transmissionData.global;
    const transmision =
      transmisionSim !== null && transmisionSim !== undefined
        ? transmisionSim
        : transmisionBase;
    const ideal = getInkIdeal(diagnostico);

    const perColorFallback =
      diagnostico.tinta_por_canal_ml_min &&
      typeof diagnostico.tinta_por_canal_ml_min === 'object'
        ? diagnostico.tinta_por_canal_ml_min
        : null;
    const porColor = { C: 0, M: 0, Y: 0, K: 0 };
    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      const simVal = transmissionData.porColor?.[canal];
      if (simVal !== undefined && simVal !== null && Number.isFinite(simVal)) {
        porColor[canal] = simVal;
      } else if (perColorFallback && perColorFallback[canal] !== undefined) {
        const fallbackVal = asNumber(perColorFallback[canal]);
        porColor[canal] = fallbackVal !== null ? Math.round(fallbackVal * 100) / 100 : 0;
      }
    });

    const tacInfo = getTacLimit(materialNombre);
    const tacLimit = tacInfo ? tacInfo.limit : null;
    const tacLabel = tacInfo ? tacInfo.label : 'estándar';

    if (metricsEls.ml) {
      metricsEls.ml.textContent =
        transmision !== null && transmision !== undefined
          ? `${transmision.toFixed(2)} ml/min`
          : 'Sin datos suficientes';
    }
    if (metricsEls.mlDetalle) {
      const partes = [
        bcmVal !== null ? `BCM ${bcmVal.toFixed(2)}` : null,
        coefUsado !== null && coefUsado !== undefined
          ? `coef ${formatNumber(coefUsado, 2)}`
          : null,
        widthM ? `ancho ${widthM.toFixed(2)} m` : null,
        velVal !== null ? `velocidad ${velVal.toFixed(0)} m/min` : null,
        `TAC ${tacTotal.toFixed(1)}%`,
        Number.isFinite(ideal) ? `ideal ${ideal.toFixed(0)} ml/min` : null,
      ].filter(Boolean);
      metricsEls.mlDetalle.textContent = partes.join(' · ');
    }

    if (metricsEls.mlIdeal) {
      if (Number.isFinite(ideal)) {
        metricsEls.mlIdeal.textContent = `Ideal: ${ideal.toFixed(0)} ml/min`;
      } else {
        metricsEls.mlIdeal.textContent = 'Ideal: --';
      }
    }

    updateInkTransmissionList(porColor);

    if (metricsEls.tac) {
      metricsEls.tac.textContent = `${tacTotal.toFixed(1)} %`;
    }
    if (metricsEls.tacDetalle) {
      metricsEls.tacDetalle.textContent = tacLimit
        ? `Límite recomendado: ${tacLimit}% (${tacLabel})`
        : 'Material sin límite definido. Usar criterio del operador.';
    }

    if (metricsEls.trama) {
      if (!advertenciasStats.hay_tramas_debiles) {
        metricsEls.trama.textContent = 'Sin tramas débiles detectadas';
      } else if (lpiVal > 150) {
        metricsEls.trama.textContent = `⚠️ ${advertenciasStats.conteo_tramas || 1} zona(s) <5% con ${lpiVal.toFixed(
          0,
        )} lpi`;
      } else {
        metricsEls.trama.textContent = `${advertenciasStats.conteo_tramas || 1} zona(s) con tramas por debajo del 5%`;
      }
    }

    if (metricsEls.overprint) {
      if (!advertenciasStats.hay_overprint) {
        metricsEls.overprint.textContent = 'Sin sobreimpresiones detectadas';
      } else {
        const count = advertenciasStats.conteo_overprint || 0;
        metricsEls.overprint.textContent = `⚠️ ${count} objeto(s) con sobreimpresión activa`;
      }
    }

    updateCoverageList(coverageState);

    const transmisionVal =
      transmision !== null && transmision !== undefined && Number.isFinite(transmision)
        ? transmision
        : null;
    const idealVal = Number.isFinite(ideal) && ideal > 0 ? ideal : null;
    const ratio = transmisionVal !== null && idealVal !== null ? transmisionVal / idealVal : null;
    const deltaPct = ratio !== null ? (ratio - 1) * 100 : null;
    let riskLevel = 1;
    let riskLabel = 'Amarillo';
    let reasons = [];
    if (ratio !== null && Number.isFinite(ratio)) {
      if (ratio >= 0.9 && ratio <= 1.1) {
        riskLevel = 0;
        riskLabel = 'Verde';
        reasons.push(
          `Dentro de ±10% del ideal (${transmisionVal.toFixed(2)} vs ${idealVal.toFixed(0)} ml/min).`,
        );
      } else if (ratio >= 0.75 && ratio < 0.9) {
        riskLevel = 1;
        riskLabel = 'Amarillo';
        reasons.push(`Subcarga ${Math.abs(deltaPct).toFixed(0)}% bajo el ideal.`);
      } else if (ratio > 1.1 && ratio <= 1.3) {
        riskLevel = 1;
        riskLabel = 'Amarillo';
        reasons.push(`Sobre carga +${deltaPct.toFixed(0)}% sobre el ideal.`);
      } else if (ratio < 0.75) {
        riskLevel = 2;
        riskLabel = 'Rojo';
        reasons.push(`Subcarga ${Math.abs(deltaPct).toFixed(0)}% bajo el ideal.`);
      } else {
        riskLevel = 2;
        riskLabel = 'Rojo';
        reasons.push(`Sobre carga +${deltaPct.toFixed(0)}% sobre el ideal.`);
      }
    } else {
      reasons.push('Sin datos suficientes para evaluar la transmisión de tinta.');
    }

    let risk = { level: riskLevel, label: riskLabel, reasons };
    const backendRisk = diagnostico.ink_risk;
    const puedeUsarBackend =
      !userModifiedAnyControl && backendRisk && typeof backendRisk === 'object';
    if (puedeUsarBackend) {
      const backendLevel = Number.isFinite(Number(backendRisk.level))
        ? Number(backendRisk.level)
        : 1;
      const backendLabel =
        backendRisk.label || (backendLevel === 0 ? 'Verde' : backendLevel === 2 ? 'Rojo' : 'Amarillo');
      const backendReasons = Array.isArray(backendRisk.reasons)
        ? backendRisk.reasons.slice()
        : [];
      risk = { level: backendLevel, label: backendLabel, reasons: backendReasons };
    }

    updateRiskUI(risk);

    return risk;
  }

  function updateRiskUI(risk) {
    if (!metricsEls.riesgoBadge || !metricsEls.riesgoValor) return;
    const clases = ['riesgo-verde', 'riesgo-amarillo', 'riesgo-rojo'];
    clases.forEach((cls) => metricsEls.riesgoBadge.classList.remove(cls));
    const nivel = Math.max(0, Math.min(2, Number(risk.level ?? 0)));
    metricsEls.riesgoBadge.classList.add(clases[nivel]);
    const etiquetas = ['Verde', 'Amarillo', 'Rojo'];
    const label = risk.label || etiquetas[nivel];
    metricsEls.riesgoValor.textContent = label;

    if (metricsEls.riesgoDetalle) {
      metricsEls.riesgoDetalle.innerHTML = '';
      const razones = Array.isArray(risk.reasons) ? risk.reasons : [];
      razones.forEach((texto) => {
        const li = document.createElement('li');
        li.textContent = texto;
        metricsEls.riesgoDetalle.appendChild(li);
      });
    }
  }

  function updateInkTransmissionList(transmissions) {
    if (!metricsEls.mlColors) return;
    metricsEls.mlColors.innerHTML = '';
    const nombres = { C: 'Cian', M: 'Magenta', Y: 'Amarillo', K: 'Negro' };
    const canales = ['C', 'M', 'Y', 'K'];
    canales.forEach((canal) => {
      const li = document.createElement('li');
      let valor = null;
      if (transmissions && Object.prototype.hasOwnProperty.call(transmissions, canal)) {
        const num = Number(transmissions[canal]);
        if (Number.isFinite(num)) valor = num;
      }
      if (valor === null) {
        li.innerHTML = `<strong>${nombres[canal]}:</strong> --`;
      } else {
        li.innerHTML = `<strong>${nombres[canal]}:</strong> ${valor.toFixed(2)} ml/min`;
      }
      metricsEls.mlColors.appendChild(li);
    });
    if (!metricsEls.mlColors.children.length) {
      const li = document.createElement('li');
      li.textContent = 'Sin datos suficientes.';
      li.style.gridColumn = '1 / -1';
      metricsEls.mlColors.appendChild(li);
    }
  }

  function updateCoverageList(coverageState) {
    if (!metricsEls.coverage) return;
    metricsEls.coverage.innerHTML = '';
    const nombres = { C: 'Cian', M: 'Magenta', Y: 'Amarillo', K: 'Negro' };
    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      const valor = coverageState.scaled[canal] || 0;
      const item = document.createElement('li');
      item.innerHTML = `<strong>${nombres[canal]}:</strong> ${valor.toFixed(1)} %`;
      metricsEls.coverage.appendChild(item);
    });
  }

  function drawFallback(targetCtx, width, height) {
    targetCtx.fillStyle = '#fff';
    targetCtx.fillRect(0, 0, width, height);
    targetCtx.fillStyle = '#d4e4f2';
    const spacing = 18;
    for (let y = 0; y < height; y += spacing) {
      for (let x = 0; x < width; x += spacing) {
        targetCtx.beginPath();
        targetCtx.arc(x + spacing / 2, y + spacing / 2, 1.4, 0, Math.PI * 2);
        targetCtx.fill();
      }
    }
  }

  function drawInkOverlay(targetCtx, width, height, coverageState) {
    if (!targetCtx || !coverageState || coverageState.sum <= 0) return;

    const lpiVal = asNumber(inputs.lpi ? inputs.lpi.value : null) || 0;
    const bcmVal = asNumber(inputs.bcm ? inputs.bcm.value : null) || 0;
    const velVal = asNumber(inputs.vel ? inputs.vel.value : null) || 0;
    const pasoVal = asNumber(inputs.paso ? inputs.paso.value : null) || 0;

    const spacingRaw = Math.max(2.5, (540 / Math.max(lpiVal || 0, 40)) * 3);
    const spacing = Math.max(6, spacingRaw);
    const bcmFactor = Math.min(1.2, (bcmVal || 0) / 12);
    const coverageFactor = Math.max(0.05, Math.min(1.0, coverageState.sum / 300));
    const density = Math.min(0.9, 0.12 + coverageFactor * (0.6 + bcmFactor));
    if (density <= 0.01) return;
    const blur = Math.min(4, (velVal / 500) * 3);
    const offset = ((pasoVal || 0) % spacing) / 2;
    const c = Math.min(1, (coverageState.scaled.C || 0) / 100);
    const m = Math.min(1, (coverageState.scaled.M || 0) / 100);
    const y = Math.min(1, (coverageState.scaled.Y || 0) / 100);
    const k = Math.min(1, (coverageState.scaled.K || 0) / 100);
    const rgb = cmykToRgb(c, m, y, k);
    const radiusBase = Math.max(1.2, (spacing / 2) * Math.min(0.85, 0.25 + coverageFactor));
    const radius = Math.min(radiusBase, spacing * 0.48);
    const rotation = Math.sin(pasoVal / 90);

    const keyParts = [
      spacing.toFixed(3),
      radius.toFixed(3),
      density.toFixed(4),
      rotation.toFixed(4),
      rgb.r,
      rgb.g,
      rgb.b,
    ];
    const patternKey = keyParts.join('|');
    if (patternCache.key !== patternKey) {
      const tileSize = Math.max(8, Math.round(spacing));
      const tileCanvas = document.createElement('canvas');
      tileCanvas.width = tileSize;
      tileCanvas.height = tileSize;
      const tileCtx = tileCanvas.getContext('2d');
      if (!tileCtx) return;
      tileCtx.clearRect(0, 0, tileSize, tileSize);
      const safeRadius = Math.min(radius, tileSize * 0.45);
      tileCtx.save();
      tileCtx.translate(tileSize / 2, tileSize / 2);
      tileCtx.rotate(rotation);
      tileCtx.beginPath();
      tileCtx.ellipse(0, 0, safeRadius, safeRadius * 0.82, 0, 0, Math.PI * 2);
      tileCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${density})`;
      tileCtx.fill();
      tileCtx.restore();

      patternCache.key = patternKey;
      patternCache.canvas = tileCanvas;
      patternCache.spacing = tileSize;
    }

    patternCache.offset = offset % (patternCache.spacing || spacing || 1);
    patternCache.blur = blur;
    patternCache.shadow = density * 0.3;

    if (!patternCache.canvas) return;
    const pattern = targetCtx.createPattern(patternCache.canvas, 'repeat');
    if (!pattern) return;

    targetCtx.save();
    if (pattern.setTransform && typeof DOMMatrix === 'function') {
      const transform = new DOMMatrix();
      transform.translateSelf(patternCache.offset, patternCache.offset);
      pattern.setTransform(transform);
      targetCtx.fillStyle = pattern;
      if (blur > 0.05) targetCtx.filter = `blur(${blur.toFixed(2)}px)`;
      targetCtx.fillRect(0, 0, width, height);
    } else {
      if (blur > 0.05) targetCtx.filter = `blur(${blur.toFixed(2)}px)`;
      targetCtx.translate(patternCache.offset, patternCache.offset);
      targetCtx.fillStyle = pattern;
      const extend = patternCache.spacing || spacing;
      targetCtx.fillRect(-patternCache.offset, -patternCache.offset, width + extend, height + extend);
    }
    targetCtx.restore();

    const shadowDensity = patternCache.shadow;
    if (shadowDensity > 0.001) {
      targetCtx.save();
      targetCtx.fillStyle = `rgba(20, 40, 60, ${shadowDensity})`;
      targetCtx.fillRect(0, 0, width, height);
      targetCtx.restore();
    }
  }

  function drawWarningOverlay(targetCtx, width, height) {
    if (!advertenciasLista.length) return;
    const WARNING_COLORS = {
      texto_pequeno: { stroke: 'rgba(220,53,69,0.9)', fill: 'rgba(220,53,69,0.18)' },
      trama_debil: { stroke: 'rgba(128,0,128,0.9)', fill: 'rgba(128,0,128,0.18)' },
      imagen_baja: { stroke: 'rgba(255,140,0,0.9)', fill: 'rgba(255,140,0,0.18)' },
      overprint: { stroke: 'rgba(0,123,255,0.9)', fill: 'rgba(0,123,255,0.18)' },
      sin_sangrado: { stroke: 'rgba(0,150,0,0.9)', fill: 'rgba(0,150,0,0.18)' },
      default: { stroke: 'rgba(255,193,7,0.9)', fill: 'rgba(255,193,7,0.18)' },
    };

    const naturalWidth = baseNaturalWidth || baseImage.naturalWidth || width;
    const naturalHeight = baseNaturalHeight || baseImage.naturalHeight || height;
    const scaleX = naturalWidth ? width / naturalWidth : 1;
    const scaleY = naturalHeight ? height / naturalHeight : 1;

    targetCtx.save();
    const baseLineWidth = Math.max(1.5, 2 / Math.max(scaleX, scaleY));
    advertenciasLista.forEach((adv) => {
      const bbox = adv.bbox || adv.box;
      if (!Array.isArray(bbox) || bbox.length !== 4) return;
      const tipoRaw = (adv.tipo || adv.type || '').toString().toLowerCase();
      const tipo = tipoRaw.startsWith('trama') ? 'trama_debil' : tipoRaw;
      const colores = WARNING_COLORS[tipo] || WARNING_COLORS.default;
      const x0 = bbox[0] * scaleX;
      const y0 = bbox[1] * scaleY;
      const x1 = bbox[2] * scaleX;
      const y1 = bbox[3] * scaleY;
      const w = Math.max(4, x1 - x0);
      const h = Math.max(4, y1 - y0);

      targetCtx.fillStyle = colores.fill;
      targetCtx.fillRect(x0, y0, w, h);
      targetCtx.lineWidth = baseLineWidth;
      targetCtx.strokeStyle = colores.stroke;
      targetCtx.strokeRect(x0, y0, w, h);
    });
    targetCtx.restore();
  }

  function calculateInkTransmission({
    bcm,
    coberturaPorCanal,
    velocidad,
    ancho,
    coefMaterial,
  }) {
    const bcmVal = Math.max(0, asNumber(bcm) ?? 0);
    const velocidadVal = Math.max(0, asNumber(velocidad) ?? 0);
    const anchoVal = Math.max(0, asNumber(ancho) ?? 0);
    const coefVal = Math.max(0, asNumber(coefMaterial) ?? 0);

    const porColor = { C: 0, M: 0, Y: 0, K: 0 };
    let total = 0;

    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      const coberturaPct = Math.max(
        0,
        Math.min(100, asNumber(coberturaPorCanal?.[canal]) ?? 0),
      );
      const volumen =
        bcmVal * (coberturaPct / 100) * velocidadVal * anchoVal * coefVal;
      const redondeado = Math.round(volumen * 100) / 100;
      porColor[canal] = Number.isFinite(redondeado) ? redondeado : 0;
      total += porColor[canal];
    });

    total = Math.round(total * 100) / 100;
    return {
      global: Number.isFinite(total) ? total : null,
      porColor,
      coefMaterial: coefVal,
    };
  }

  function simulateInkTransfer(dj, sliders = {}) {
    const cobertura = sliders.coberturaPorCanal || sliders.coverage || {};
    const anchoMm = asNumber(dj.ancho_mm);
    const anchoDiagnostico = asNumber(dj.ancho_util_m);
    const ancho =
      sliders.ancho !== undefined
        ? sliders.ancho
        : anchoDiagnostico !== null
        ? anchoDiagnostico
        : anchoMm !== null
        ? anchoMm / 1000
        : 0;

    const velocidadBase =
      dj.velocidad_impresion ?? dj.velocidad ?? dj.velocidad_estimada ?? null;

    return calculateInkTransmission({
      bcm: sliders.bcm ?? dj.anilox_bcm ?? dj.bcm,
      coberturaPorCanal: cobertura,
      velocidad: sliders.velocidad ?? velocidadBase,
      ancho,
      coefMaterial: sliders.coefMaterial ?? dj.coef_material,
    });
  }

  function resolveMaterialCoefficient(material, preset) {
    const presetNum = asNumber(preset);
    if (presetNum !== null) return presetNum;

    const clave = normalizeMaterialKey(material);
    if (clave && Object.prototype.hasOwnProperty.call(materialCoefficients, clave)) {
      const valor = asNumber(materialCoefficients[clave]);
      if (valor !== null) return valor;
    }

    if (Object.prototype.hasOwnProperty.call(materialCoefficients, 'default')) {
      const valorDefault = asNumber(materialCoefficients.default);
      if (valorDefault !== null) return valorDefault;
    }

    return 0.8;
  }

  function normalizeMaterialKey(nombre) {
    if (!nombre) return '';
    return nombre
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim()
      .replace(/\s+/g, '_');
  }

  function getInkIdeal(dj) {
    const directo = asNumber(dj && dj.tinta_ideal_ml_min);
    if (directo !== null) return directo;
    const matRaw = dj && dj.material ? dj.material.toString().toLowerCase() : '';
    const map = { film: 120, papel: 180, carton: 200, 'etiqueta adhesiva': 150, default: 150 };
    if (Object.prototype.hasOwnProperty.call(map, matRaw)) return map[matRaw];
    const normalized = normalizeMaterialKey(matRaw).replace(/_/g, ' ');
    return Object.prototype.hasOwnProperty.call(map, normalized) ? map[normalized] : map.default;
  }

  function parseCoverageBase(diag, useV2) {
    const base = { C: 0, M: 0, Y: 0, K: 0 };
    let sum = 0;
    let hasRealData = false;

    const cobertura =
      diag && typeof diag.cobertura_por_canal === 'object' && diag.cobertura_por_canal !== null
        ? diag.cobertura_por_canal
        : diag && typeof diag.cobertura === 'object' && diag.cobertura !== null
        ? diag.cobertura
        : null;

    if (cobertura) {
      ['C', 'M', 'Y', 'K'].forEach((canal) => {
        const valor = asNumber(cobertura[canal]);
        if (valor !== null) {
          const clamped = Math.max(0, Math.min(100, valor));
          base[canal] = clamped;
          sum += clamped;
          hasRealData = true;
        }
      });
    }

    let fallback = leerTacFromDj(diag, useV2);
    fallback = fallback !== null ? asNumber(fallback) : null;
    if (fallback === null && diag && typeof diag.cobertura !== 'object') {
      fallback = asNumber(diag.cobertura);
    }

    return {
      base,
      sum: hasRealData ? sum : 0,
      fallback: fallback !== null ? fallback : null,
      hasRealData,
    };
  }

  function getCoverageState() {
    const baseValues = { ...coverageBase.base };
    let baseSum = coverageBase.sum;
    const sliderVal = asNumber(inputs.cob ? inputs.cob.value : null);
    const sliderTouched = inputs.cob && inputs.cob.dataset.userModified === '1';

    if (
      baseSum <= 0 &&
      !coverageBase.hasRealData &&
      sliderTouched &&
      sliderVal !== null &&
      sliderVal > 0
    ) {
      const per = sliderVal / 4;
      ['C', 'M', 'Y', 'K'].forEach((canal) => {
        baseValues[canal] = per;
      });
      baseSum = sliderVal;
    }

    if (baseSum <= 0 && !coverageBase.hasRealData) {
      const fallbackTac = coverageBase.fallback;
      if (fallbackTac !== null) {
        const per = fallbackTac / 4;
        ['C', 'M', 'Y', 'K'].forEach((canal) => {
          baseValues[canal] = per;
        });
        baseSum = fallbackTac;
      }
    }

    let factor = 1;
    if (sliderVal !== null && baseSum > 0) {
      factor = sliderVal / baseSum;
    }

    const scaled = {};
    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      const valor = (baseValues[canal] || 0) * factor;
      scaled[canal] = Math.max(0, Math.min(100, valor));
    });
    const sum = ['C', 'M', 'Y', 'K'].reduce((acc, canal) => acc + scaled[canal], 0);

    return {
      base: baseValues,
      scaled,
      sum,
      slider: sliderVal,
      factor,
    };
  }

  function getEffectiveWidth() {
    const anchoUtil = asNumber(diagnostico.ancho_util_m);
    if (anchoUtil && anchoUtil > 0) return anchoUtil;
    const anchoMm = asNumber(diagnostico.ancho_mm);
    if (anchoMm && anchoMm > 0) return anchoMm / 1000;
    const pasoVal = asNumber(inputs.paso ? inputs.paso.value : null);
    if (pasoVal && pasoVal > 0) return Math.max(0.18, pasoVal / 1000);
    return 0.35;
  }

  function getTacLimit(material) {
    const normalizado = (material || '').toString().toLowerCase();
    if (!normalizado) return null;
    const reglas = [
      { tokens: ['papel'], limit: 280, label: 'papel' },
      { tokens: ['carton', 'cartón'], limit: 320, label: 'cartón' },
      { tokens: ['film', 'bopp', 'opp', 'polietileno', 'polipropileno'], limit: 340, label: 'film' },
      { tokens: ['etiqueta'], limit: 300, label: 'etiqueta adhesiva' },
    ];
    for (const regla of reglas) {
      if (regla.tokens.some((token) => normalizado.includes(token))) {
        return { limit: regla.limit, label: regla.label };
      }
    }
    return { limit: 300, label: normalizado };
  }

  function buildAdvertenciaStats(baseStats, advertencias) {
    const stats = {
      por_tipo: {},
      total: 0,
      conteo_tramas: 0,
      conteo_overprint: 0,
      conteo_texto: 0,
      hay_tramas_debiles: false,
      hay_overprint: false,
      hay_texto_pequeno: false,
    };

    if (baseStats && typeof baseStats === 'object') {
      if (baseStats.por_tipo && typeof baseStats.por_tipo === 'object') {
        Object.entries(baseStats.por_tipo).forEach(([tipo, cantidad]) => {
          stats.por_tipo[tipo] = Number(cantidad) || 0;
        });
      }
      stats.total = Number(baseStats.total) || stats.total;
      stats.conteo_tramas = Number(baseStats.conteo_tramas) || stats.conteo_tramas;
      stats.conteo_overprint = Number(baseStats.conteo_overprint) || stats.conteo_overprint;
      stats.conteo_texto = Number(baseStats.conteo_texto) || stats.conteo_texto;
      stats.hay_tramas_debiles = Boolean(baseStats.hay_tramas_debiles);
      stats.hay_overprint = Boolean(baseStats.hay_overprint);
      stats.hay_texto_pequeno = Boolean(baseStats.hay_texto_pequeno);
    }

    advertencias.forEach((adv) => {
      const tipo = (adv.tipo || adv.type || '').toString().toLowerCase();
      if (!tipo) return;
      stats.por_tipo[tipo] = (stats.por_tipo[tipo] || 0) + 1;
    });

    const conteoTramas = Object.entries(stats.por_tipo)
      .filter(([tipo]) => tipo.includes('trama'))
      .reduce((acc, [, cantidad]) => acc + cantidad, 0);
    stats.conteo_tramas = stats.conteo_tramas || conteoTramas;
    stats.conteo_overprint = stats.conteo_overprint || stats.por_tipo.overprint || 0;
    stats.conteo_texto = stats.conteo_texto || stats.por_tipo['texto_pequeno'] || 0;
    stats.hay_tramas_debiles = stats.hay_tramas_debiles || stats.conteo_tramas > 0;
    stats.hay_overprint = stats.hay_overprint || stats.conteo_overprint > 0;
    stats.hay_texto_pequeno = stats.hay_texto_pequeno || stats.conteo_texto > 0;
    stats.total = Math.max(
      stats.total,
      advertencias.length,
      Object.values(stats.por_tipo).reduce((acc, cantidad) => acc + cantidad, 0),
    );

    return stats;
  }

  function resolveDiagnosticoValue(keys) {
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(diagnostico, key)) {
        const val = diagnostico[key];
        if (val !== null && val !== undefined) return val;
      }
    }
    return null;
  }

  function leerTacFromDj(dj, useV2) {
    if (!dj || typeof dj !== 'object') return null;
    if (dj.tac_total_v2 !== null && dj.tac_total_v2 !== undefined) {
      const valV2 = asNumber(dj.tac_total_v2);
      if (valV2 !== null) return valV2;
    }
    const legacyKeys = ['tac_total', 'cobertura_estimada', 'cobertura_base_sum'];
    for (const key of legacyKeys) {
      if (dj[key] === null || dj[key] === undefined) continue;
      const val = asNumber(dj[key]);
      if (val !== null) return val;
    }
    return null;
  }

  function normalizeUrl(url) {
    if (!url) return '';
    const trimmed = String(url).trim();
    if (!trimmed) return '';
    if (/^(?:https?:|data:|blob:)/i.test(trimmed) || trimmed.startsWith('//')) return trimmed;
    if (trimmed.startsWith('/')) return trimmed;
    const clean = trimmed.replace(/^\.?\//, '');
    if (clean.startsWith('static/')) return `/${clean}`;
    return `/static/${clean}`;
  }

  function cmykToRgb(c, m, y, k) {
    const r = 255 * (1 - c) * (1 - k);
    const g = 255 * (1 - m) * (1 - k);
    const b = 255 * (1 - y) * (1 - k);
    return { r: Math.round(r), g: Math.round(g), b: Math.round(b) };
  }

  function asNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }

  function clampToInputRange(num, input) {
    if (!input) return num;
    const min = asNumber(input.min);
    const max = asNumber(input.max);
    let resultado = num;
    if (min !== null && resultado < min) resultado = min;
    if (max !== null && resultado > max) resultado = max;
    return resultado;
  }

  function formatNumber(value, decimals = 0) {
    const num = asNumber(value);
    if (num === null) return value !== undefined && value !== null ? String(value) : '';
    return num.toFixed(decimals);
  }
});

