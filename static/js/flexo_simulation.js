const DEBUG = false;

document.addEventListener('DOMContentLoaded', () => {
  if (DEBUG) console.log('[SIM] DOM ready');

  const canvas = document.getElementById('sim-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

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
  const analisis = window.analisisDetallado || {};
  const advertenciasLista = Array.isArray(window.advertencias) ? window.advertencias : [];
  const advertenciasStats = buildAdvertenciaStats(
    window.indicadoresAdvertencias,
    advertenciasLista,
  );

  const coverageBase = parseCoverageBase(diagnostico);
  const materialNombre = (diagnostico.material || '').toString();
  const diagImgUrl = normalizeUrl(window.diag_img_web || canvas.dataset.simImg || '');

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
  if (diagImgUrl) {
    const cacheBusted = diagImgUrl.includes('?')
      ? `${diagImgUrl}&cb=${Date.now()}`
      : `${diagImgUrl}?cb=${Date.now()}`;
    baseImage.src = cacheBusted;
  }

  let rafId = null;
  let debounceId = null;
  let currentDpr = window.devicePixelRatio || 1;

  applyInitialValues();

  window.addEventListener('resize', resize);
  resize();
  if (!diagImgUrl) render();

  Object.values(inputs).forEach((el) => {
    if (!el) return;
    el.addEventListener('input', scheduleRender);
    el.addEventListener('change', scheduleRender);
  });

  if (metricsEls.saveBtn) {
    metricsEls.saveBtn.addEventListener('click', handleExport);
  }

  function scheduleRender() {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => render());
    }, 120);
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    currentDpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, rect.width * currentDpr);
    canvas.height = Math.max(1, rect.height * currentDpr);
    ctx.setTransform(currentDpr, 0, 0, currentDpr, 0, 0);
    render();
  }

  function handleExport() {
    if (DEBUG) console.log('[SIM] export');
    if (diagImgUrl && !baseReady) {
      alert('La imagen base aún se está cargando. Intentá nuevamente en unos segundos.');
      return;
    }

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    const exportCtx = exportCanvas.getContext('2d');
    if (!exportCtx) return;
    exportCtx.setTransform(currentDpr, 0, 0, currentDpr, 0, 0);
    render(exportCtx, exportCanvas, false);

    exportCanvas.toBlob(async (blob) => {
      if (!blob) return;
      const fd = new FormData();
      fd.append('image', blob, `sim_${window.revisionId || 'resultado'}.png`);
      try {
        const resp = await fetch(`/simulacion/exportar/${window.revisionId}`, {
          method: 'POST',
          body: fd,
        });
        const data = await resp.json();
        if (data && data.url) {
          if (metricsEls.viewLink) metricsEls.viewLink.href = data.url;
          alert(`PNG generado: ${data.url}`);
        }
      } catch (err) {
        if (DEBUG) console.error('[SIM] export error', err);
      }
    });
  }

  function render(targetCtx = ctx, targetCanvas = canvas, updateUi = true) {
    if (!targetCtx || !targetCanvas) return;
    const width = targetCanvas.width / currentDpr;
    const height = targetCanvas.height / currentDpr;
    if (width <= 0 || height <= 0) return;

    const coverageState = getCoverageState();
    if (updateUi) {
      updateLabels();
      updateMetrics(coverageState);
    }

    targetCtx.clearRect(0, 0, width, height);

    if (baseReady && diagImgUrl) {
      targetCtx.drawImage(baseImage, 0, 0, width, height);
    } else {
      drawFallback(targetCtx, width, height);
    }

    drawInkOverlay(targetCtx, width, height, coverageState);
    drawWarningOverlay(targetCtx, width, height);
  }

  function applyInitialValues() {
    const mapping = [
      [inputs.lpi, ['anilox_lpi', 'lpi']],
      [inputs.bcm, ['anilox_bcm', 'bcm']],
      [inputs.paso, ['paso_del_cilindro', 'paso_cilindro', 'paso']],
      [inputs.vel, ['velocidad_impresion', 'velocidad']],
      [inputs.cob, ['tac_total', 'cobertura_estimada', 'cobertura_base_sum']],
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
    const pasoVal = asNumber(inputs.paso ? inputs.paso.value : null) || 0;
    const widthM = getEffectiveWidth();
    const coverageFraction = Math.max(0, Math.min(coverageState.sum / 400, 1.5));
    let transmision = null;
    if (bcmVal !== null && velVal !== null && widthM > 0) {
      const valor = bcmVal * velVal * widthM * coverageFraction;
      transmision = Number.isFinite(valor) ? valor : null;
    }

    const tacInfo = getTacLimit(materialNombre);
    const tacLimit = tacInfo ? tacInfo.limit : null;
    const tacLabel = tacInfo ? tacInfo.label : 'estándar';

    if (metricsEls.ml) {
      metricsEls.ml.textContent =
        transmision !== null ? `${transmision.toFixed(2)} ml/min` : 'Sin datos suficientes';
    }
    if (metricsEls.mlDetalle) {
      const partes = [
        bcmVal !== null ? `BCM ${bcmVal.toFixed(2)}` : null,
        widthM ? `ancho ${widthM.toFixed(2)} m` : null,
        velVal !== null ? `velocidad ${velVal.toFixed(0)} m/min` : null,
        `TAC ${coverageState.sum.toFixed(1)}%`,
      ].filter(Boolean);
      metricsEls.mlDetalle.textContent = partes.join(' · ');
    }

    if (metricsEls.tac) {
      metricsEls.tac.textContent = `${coverageState.sum.toFixed(1)} %`;
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

    const risk = evaluateRisks(
      {
        ml: transmision,
        tac: coverageState.sum,
        tacLimit,
        materialLabel: tacLabel,
        lpi: lpiVal,
        velocidad: velVal || 0,
        width: widthM,
      },
      coverageState,
      advertenciasStats,
    );
    updateRiskUI(risk);

    return risk;
  }

  function updateRiskUI(risk) {
    if (!metricsEls.riesgoBadge || !metricsEls.riesgoValor) return;
    const clases = ['riesgo-verde', 'riesgo-amarillo', 'riesgo-rojo'];
    clases.forEach((cls) => metricsEls.riesgoBadge.classList.remove(cls));
    const nivel = Math.max(0, Math.min(2, risk.level || 0));
    metricsEls.riesgoBadge.classList.add(clases[nivel]);
    const etiquetas = ['Verde', 'Amarillo', 'Rojo'];
    metricsEls.riesgoValor.textContent = etiquetas[nivel];

    if (metricsEls.riesgoDetalle) {
      metricsEls.riesgoDetalle.innerHTML = '';
      risk.reasons.forEach((texto) => {
        const li = document.createElement('li');
        li.textContent = texto;
        metricsEls.riesgoDetalle.appendChild(li);
      });
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
    const lpiVal = asNumber(inputs.lpi ? inputs.lpi.value : null) || 0;
    const bcmVal = asNumber(inputs.bcm ? inputs.bcm.value : null) || 0;
    const velVal = asNumber(inputs.vel ? inputs.vel.value : null) || 0;
    const pasoVal = asNumber(inputs.paso ? inputs.paso.value : null) || 0;

    const spacing = Math.max(2.5, (540 / Math.max(lpiVal, 40)) * 3);
    const bcmFactor = Math.min(1.2, (bcmVal || 0) / 12);
    const coverageFactor = Math.max(0.05, Math.min(1.0, coverageState.sum / 300));
    const density = Math.min(0.9, 0.12 + coverageFactor * (0.6 + bcmFactor));
    const blur = Math.min(4, (velVal / 500) * 3);
    const offset = ((pasoVal || 0) % spacing) / 2;
    const c = Math.min(1, (coverageState.scaled.C || 0) / 100);
    const m = Math.min(1, (coverageState.scaled.M || 0) / 100);
    const y = Math.min(1, (coverageState.scaled.Y || 0) / 100);
    const k = Math.min(1, (coverageState.scaled.K || 0) / 100);
    const rgb = cmykToRgb(c, m, y, k);
    const radius = Math.max(1.2, (spacing / 2) * Math.min(0.85, 0.25 + coverageFactor));

    targetCtx.save();
    if (blur > 0.05) targetCtx.filter = `blur(${blur.toFixed(2)}px)`;
    targetCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${density})`;
    for (let posY = offset; posY < height + spacing; posY += spacing) {
      for (let posX = offset; posX < width + spacing; posX += spacing) {
        targetCtx.beginPath();
        targetCtx.ellipse(
          posX,
          posY,
          radius,
          radius * 0.82,
          Math.sin(pasoVal / 90),
          0,
          Math.PI * 2,
        );
        targetCtx.fill();
      }
    }
    targetCtx.filter = 'none';

    const shadowDensity = density * 0.35;
    targetCtx.fillStyle = `rgba(20, 40, 60, ${shadowDensity})`;
    targetCtx.fillRect(0, 0, width, height);
    targetCtx.restore();
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

  function parseCoverageBase(diag) {
    const CHANNEL_NAMES = { C: 'Cyan', M: 'Magenta', Y: 'Amarillo', K: 'Negro' };
    const result = {
      base: { C: 0, M: 0, Y: 0, K: 0 },
      sum: 0,
      fallback: 0,
    };
    const letras = diag.cobertura || {};
    const nombres = diag.cobertura_por_canal || {};

    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      const letraVal = asNumber(letras[canal]);
      const nombreVal = asNumber(nombres[CHANNEL_NAMES[canal]]);
      const valor = letraVal !== null ? letraVal : nombreVal !== null ? nombreVal : 0;
      result.base[canal] = valor;
    });
    result.sum = ['C', 'M', 'Y', 'K'].reduce((acc, canal) => acc + (result.base[canal] || 0), 0);
    const fallback =
      asNumber(diag.tac_total) ??
      asNumber(diag.cobertura_estimada) ??
      asNumber(diag.cobertura);
    result.fallback = fallback || 0;
    if (result.sum <= 0 && result.fallback > 0) {
      const per = result.fallback / 4;
      result.base = { C: per, M: per, Y: per, K: per };
      result.sum = result.fallback;
    }
    return result;
  }

  function getCoverageState() {
    const baseValues = { ...coverageBase.base };
    let baseSum = coverageBase.sum;
    if (baseSum <= 0 && coverageBase.fallback > 0) {
      const per = coverageBase.fallback / 4;
      ['C', 'M', 'Y', 'K'].forEach((canal) => {
        baseValues[canal] = per;
      });
      baseSum = coverageBase.fallback;
    }

    const sliderVal = asNumber(inputs.cob ? inputs.cob.value : null);
    let factor = 1;
    if (sliderVal !== null) {
      if (baseSum > 0) {
        factor = sliderVal / baseSum;
      } else if (sliderVal > 0) {
        const per = sliderVal / 4;
        ['C', 'M', 'Y', 'K'].forEach((canal) => {
          baseValues[canal] = per;
        });
        baseSum = sliderVal;
        factor = 1;
      }
    }

    const scaled = {};
    ['C', 'M', 'Y', 'K'].forEach((canal) => {
      const valor = (baseValues[canal] || 0) * factor;
      scaled[canal] = Math.max(0, Math.min(120, valor));
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

  function evaluateRisks(metrics, coverageState, stats) {
    const razones = [];
    let nivel = 0;

    if (metrics.ml === null) {
      razones.push('No se pudo calcular la transmisión de tinta. Revisá BCM, ancho y velocidad.');
      nivel = Math.max(nivel, 1);
    } else if (metrics.ml < 60) {
      razones.push('Transmisión baja (<60 ml/min): posible subcarga y pérdida de densidad.');
      nivel = Math.max(nivel, metrics.ml < 40 ? 2 : 1);
    } else if (metrics.ml > 200) {
      razones.push('Transmisión alta (>200 ml/min): riesgo de sobrecarga y ganancia de punto.');
      nivel = Math.max(nivel, metrics.ml > 240 ? 2 : 1);
    }

    if (metrics.tacLimit) {
      if (metrics.tac > metrics.tacLimit + 30) {
        razones.push(
          `TAC ${metrics.tac.toFixed(1)}% excede el límite ${metrics.tacLimit}% para ${metrics.materialLabel}.`,
        );
        nivel = Math.max(nivel, 2);
      } else if (metrics.tac > metrics.tacLimit) {
        razones.push(
          `TAC ${metrics.tac.toFixed(1)}% está por encima del límite ${metrics.tacLimit}% para ${metrics.materialLabel}.`,
        );
        nivel = Math.max(nivel, 1);
      } else if (metrics.tac > metrics.tacLimit - 20) {
        razones.push(
          `TAC ${metrics.tac.toFixed(1)}% cercano al límite recomendado de ${metrics.tacLimit}% (${metrics.materialLabel}).`,
        );
      }
    }

    if (stats.hay_tramas_debiles) {
      if (metrics.lpi > 180) {
        razones.push('LPI > 180 con tramas inferiores al 5%: alto riesgo de pérdida de altas luces.');
        nivel = Math.max(nivel, 2);
      } else if (metrics.lpi > 150) {
        razones.push('Tramas débiles detectadas: mantener LPI ≤150 para conservar el detalle.');
        nivel = Math.max(nivel, 1);
      } else {
        razones.push('El diagnóstico detectó tramas débiles. Controlar presión y ganancia de punto.');
      }
    }

    if (stats.hay_overprint) {
      const count = stats.conteo_overprint || 0;
      razones.push(
        count > 1
          ? `${count} objetos con sobreimpresión detectados: revisar intención de color.`
          : 'Se detectó sobreimpresión: confirmar intención de producción.',
      );
      nivel = Math.max(nivel, count > 5 ? 2 : 1);
    }

    if (stats.hay_texto_pequeno && metrics.velocidad > 260) {
      razones.push('Textos pequeños detectados: reducir velocidad para evitar pérdida de detalle.');
      nivel = Math.max(nivel, 1);
    }

    if (!razones.length) {
      razones.push('Parámetros dentro de los rangos recomendados según el diagnóstico.');
    }

    return { level: nivel, reasons: razones };
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

