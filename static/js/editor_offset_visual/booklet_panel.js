(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function renderPages(pages) {
    return (pages || [])
      .map((pageItem) => {
        const isVisualPage = pageItem && typeof pageItem === 'object';
        const pageNumber = isVisualPage ? pageItem.pagina : pageItem;
        const rotation = isVisualPage ? Number(pageItem.rotacion || 0) : 0;
        const isBlank = pageNumber === 'BLANCO';
        let rotationClass = ' pagina-rotada-0';
        let pageRotationClass = ' cuadernillo-page-rot-0';
        let rotationLabel = '0';
        if (rotation === 90) rotationClass = ' pagina-rotada-90';
        if (rotation === 90) {
          pageRotationClass = ' cuadernillo-page-rot-90';
          rotationLabel = '90';
        }
        if (rotation === -90) {
          rotationClass = ' pagina-rotada--90';
          pageRotationClass = ' cuadernillo-page-rot--90';
          rotationLabel = '-90';
        }
        if (rotation === 180) {
          rotationClass = ' pagina-rotada-180';
          pageRotationClass = ' cuadernillo-page-rot-180';
          rotationLabel = '180';
        }
        return `
          <span class="cuadernillo-page${pageRotationClass}${isBlank ? ' cuadernillo-page-blank' : ''}">
            <span class="cuadernillo-page-rotation">${rotationLabel}</span>
            <span class="cuadernillo-page-number${rotationClass}">${pageNumber}</span>
          </span>
        `;
      })
      .join('');
  }

  function getPagesClass(pliego) {
    const paginasPorCara = Number(pliego?.paginas_por_cara || 4);
    if (paginasPorCara === 8) return 'cuadernillo-pages cuadernillo-pages-8 cuadernillo-grid-2x4';
    return 'cuadernillo-pages cuadernillo-pages-4 cuadernillo-grid-2x2';
  }

  function getModeLabel(pliego) {
    if (pliego?.tipo === 'vyv_8' || pliego?.modo === 'vyv_8_paginas') return 'VYV 8 paginas';
    if (pliego?.tipo === 'vyv_4' || pliego?.modo === 'vyv_4_paginas') return 'VYV 4 paginas';
    if (pliego?.tipo === 'cuadernillo_16') return 'Cuadernillo 16';
    if (pliego?.tipo === 'cuadernillo_8') return 'Cuadernillo 8';
    return '';
  }

  function renderTechSummary(simulacion) {
    const tipoTapaLabel = simulacion.tipo_tapa === 'tapa_completa' ? 'Tapa completa' : 'Sin tapa';
    const tipoCuadernillo = Number(simulacion.tipo_cuadernillo || 0);
    const tipoCuadernilloLabel = tipoCuadernillo ? `${tipoCuadernillo} paginas` : 'Automatico';
    const pliegos = simulacion.tipo_tapa === 'tapa_completa'
      ? (simulacion.tripa?.pliegos || simulacion.pliegos || [])
      : (simulacion.pliegos || []);
    const totalPliegos = pliegos.length + (simulacion.tapa ? 1 : 0);
    const items = [
      ['Original', simulacion.total_paginas_original],
      ['Final', simulacion.total_paginas_final],
      ['Blancas', simulacion.blancas_agregadas],
      ['Tapa', tipoTapaLabel],
      ['Cuadernillo', tipoCuadernilloLabel],
      ['Pliegos', totalPliegos],
    ];

    return `
      <section class="cuadernillo-tech-summary" aria-label="Resumen operativo del cuadernillo">
        <div class="cuadernillo-summary-grid">
          ${items
            .map(([label, value]) => `
              <div class="cuadernillo-summary-card">
                <span>${label}</span>
                <strong>${value ?? 0}</strong>
              </div>
            `)
            .join('')}
        </div>
        <p class="cuadernillo-summary-note">Simulacion visual: no genera PDF ni modifica el montaje.</p>
      </section>
    `;
  }

  function renderPliegos(pliegos, title) {
    const pliegosHtml = (pliegos || [])
      .map((pliego) => {
        const isVyv = pliego.tipo === 'vyv_8' || pliego.tipo === 'vyv_4' || String(pliego.modo || '').startsWith('vyv_');
        const pagesClass = getPagesClass(pliego);
        const modeLabel = getModeLabel(pliego);
        const label = modeLabel ? `<span class="cuadernillo-mode-label">${modeLabel}</span>` : '';
        const pagesLabel = `<span class="cuadernillo-mode-label">${Number(pliego.paginas_por_cara || 4)} pags cara</span>`;
        const vyvLabel = isVyv
          ? '<span class="cuadernillo-mode-label cuadernillo-vyv-badge">Cara unica</span>'
          : '';
        const caraUnica = Array.isArray(pliego.cara)
          ? `
            <div class="cuadernillo-face cuadernillo-single-face">
              <div class="cuadernillo-face-heading">
                <strong>Cara unica VYV</strong>
                <span class="cuadernillo-face-badge">Sin dorso</span>
              </div>
              <span class="cuadernillo-orientation-label">Cabeza con cabeza</span>
              <div class="${pagesClass}">${renderPages(pliego.cara_visual || pliego.cara)}</div>
            </div>
          `
          : '';
        const frenteDorso = !caraUnica
          ? `
            <div class="cuadernillo-face cuadernillo-front">
              <div class="cuadernillo-face-heading">
                <strong>Frente</strong>
                <span class="cuadernillo-face-badge cuadernillo-orientation-label">Cabeza con cabeza</span>
              </div>
              <div class="${pagesClass}">${renderPages(pliego.frente_visual || pliego.frente)}</div>
            </div>
            <div class="cuadernillo-face cuadernillo-back">
              <div class="cuadernillo-face-heading">
                <strong>Dorso</strong>
                <span class="cuadernillo-face-badge cuadernillo-orientation-label">Cabeza con cabeza</span>
              </div>
              <div class="${pagesClass}">${renderPages(pliego.dorso_visual || pliego.dorso)}</div>
            </div>
          `
          : '';
        return `
          <article class="cuadernillo-card${isVyv ? ' pliego-vyv' : ''}">
            <h4>
              <span>Pliego ${pliego.pliego}</span>
              <span class="cuadernillo-card-badges">${label}${pagesLabel}${vyvLabel}</span>
            </h4>
            ${caraUnica || frenteDorso}
          </article>
        `;
      })
      .join('');
    return `
      <section class="cuadernillo-block cuadernillo-tripa-block">
        ${title ? `<h4 class="cuadernillo-section-title"><span>${title}</span><span class="cuadernillo-section-badge">Pliegos interiores</span></h4>` : ''}
        ${pliegosHtml}
      </section>
    `;
  }

  function renderTapa(tapa) {
    if (!tapa) return '';
    if (Array.isArray(tapa.cara) || Array.isArray(tapa.cara_visual)) {
      return `
        <section class="cuadernillo-block cuadernillo-tapa-block tapa-vyv">
          <h4 class="cuadernillo-section-title"><span>TAPA</span><span class="cuadernillo-section-badge">VYV 4 - Cara unica</span></h4>
          <div class="cuadernillo-face cuadernillo-single-face">
            <div class="cuadernillo-face-heading">
              <strong>Cara unica VYV</strong>
              <span class="cuadernillo-face-badge">Tapa completa</span>
            </div>
            <span class="cuadernillo-orientation-label">Cabeza con cabeza</span>
            <div class="cuadernillo-pages cuadernillo-pages-4 cuadernillo-grid-2x2">
              ${renderPages(tapa.cara_visual || tapa.cara)}
            </div>
          </div>
        </section>
      `;
    }
    return `
      <section class="cuadernillo-block cuadernillo-tapa-block">
        <h4 class="cuadernillo-section-title"><span>TAPA</span><span class="cuadernillo-section-badge">Separada</span></h4>
        <div class="cuadernillo-face cuadernillo-front">
          <div class="cuadernillo-face-heading">
            <strong>Frente</strong>
            <span class="cuadernillo-face-badge cuadernillo-orientation-label">Cabeza con cabeza</span>
          </div>
          <div class="cuadernillo-pages cuadernillo-pages-cover">${renderPages(tapa.frente_visual || tapa.frente)}</div>
        </div>
        <div class="cuadernillo-face cuadernillo-back">
          <div class="cuadernillo-face-heading">
            <strong>Dorso</strong>
            <span class="cuadernillo-face-badge cuadernillo-orientation-label">Cabeza con cabeza</span>
          </div>
          <div class="cuadernillo-pages cuadernillo-pages-cover">${renderPages(tapa.dorso_visual || tapa.dorso)}</div>
        </div>
      </section>
    `;
  }

  function renderSimulation(simulacion) {
    const resultEl = window.EditorOffsetVisual.domRefs.byId('cuadernillo-resultado');
    if (!resultEl) return;
    const resumen = renderTechSummary(simulacion);
    if (simulacion.tipo_tapa === 'tapa_completa') {
      resultEl.innerHTML = `
        ${resumen}
        ${renderTapa(simulacion.tapa)}
        ${renderPliegos(simulacion.tripa?.pliegos || simulacion.pliegos || [], 'TRIPA')}
      `;
      return;
    }
    resultEl.innerHTML = `${resumen}${renderPliegos(simulacion.pliegos || [], '')}`;
  }

  async function simulate() {
    const byId = window.EditorOffsetVisual.domRefs.byId;
    const resultEl = byId('cuadernillo-resultado');
    const totalInput = byId('cuadernillo-total-paginas');
    const tipoSelect = byId('cuadernillo-tipo');
    const tipoTapaSelect = byId('cuadernillo-tipo-tapa');
    const tipoCuadernilloSelect = byId('cuadernillo-tipo-cuadernillo');
    if (!resultEl || !totalInput || !tipoSelect || !tipoTapaSelect || !tipoCuadernilloSelect) return;

    resultEl.textContent = 'Simulando...';
    const payload = {
      total_paginas: parseInt(totalInput.value, 10),
      tipo_encuadernacion: tipoSelect.value,
      tipo_tapa: tipoTapaSelect.value,
      tipo_cuadernillo: parseInt(tipoCuadernilloSelect.value, 10),
    };

    try {
      const result = await window.EditorOffsetVisual.apiClient.simulateBooklet(payload);
      const data = result.data;
      if (!result.ok || !data.ok) {
        resultEl.innerHTML = `<p class="cuadernillo-error">${data.error || 'No se pudo simular el cuadernillo.'}</p>`;
        return;
      }
      renderSimulation(data.simulacion);
    } catch (err) {
      resultEl.innerHTML = '<p class="cuadernillo-error">No se pudo conectar con el simulador.</p>';
    }
  }

  window.EditorOffsetVisual.bookletPanel = {
    renderPages,
    getPagesClass,
    getModeLabel,
    renderTechSummary,
    renderPliegos,
    renderTapa,
    renderSimulation,
    simulate,
  };
})();
