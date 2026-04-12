# Backlog Operativo De Endpoints Críticos

Documento operativo para la refactorización.

Objetivo:

- listar los endpoints HTTP críticos del sistema
- fijar inputs y outputs relevantes
- identificar dependencias de frontend, templates y archivos
- priorizar por riesgo

Este documento no cambia comportamiento.
Es una vista operativa del contrato actual.

## Convenciones

- Riesgo `Muy alto`:
  cambiarlo puede romper editor IA, overlays, simulación o PDFs de producción
- Riesgo `Alto`:
  cambiarlo puede romper flujos de usuario o contratos frontend-backend
- Riesgo `Medio`:
  impacto acotado o con menos consumidores

## 1. Editor Visual IA

## 1.1 Constructor IA

### Endpoint

- Método y ruta:
  `GET /editor_offset_visual`

### Propósito

- abrir el constructor visual IA de montaje offset
- crear o recuperar `job_id`
- inyectar el layout base en template

### Inputs obligatorios

- ninguno

### Inputs opcionales

- `job_id` por query string

### Campos legacy admitidos

- no aplica

### Respuesta esperada

- HTML de `templates/editor_offset_visual.html`
- expone `window.INITIAL_LAYOUT_JSON`

### Dependientes de este contrato

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- persistencia de `layout_constructor.json`

### Riesgo si cambia

- Muy alto

## 1.2 Guardado del constructor

### Endpoint

- Método y ruta:
  `POST /editor_offset/save`

### Propósito

- persistir el layout actual del constructor IA

### Inputs obligatorios

- `job_id`
- `layout_json`

### Inputs opcionales

- ninguno relevante

### Campos legacy admitidos

- no identificados

### Respuesta esperada

```json
{
  "ok": true,
  "job_id": "abc123def456"
}
```

### Dependientes de este contrato

- `static/js/editor_offset_visual.js`
- `layout_constructor.json`

### Riesgo si cambia

- Alto

## 1.3 Upload de diseños al constructor

### Endpoint

- Método y ruta:
  `POST /editor_offset/upload/<job_id>`

### Propósito

- subir PDFs al job del constructor
- poblar `designs[]`

### Inputs obligatorios

- `job_id` en ruta
- al menos un archivo en `files` o `file`

### Inputs opcionales

- `work_id`

### Campos legacy admitidos

- doble nombre del campo de archivo:
  - `files`
  - `file`

### Respuesta esperada

```json
{
  "designs": [ ... ]
}
```

### Dependientes de este contrato

- `static/js/editor_offset_visual.js`
- `designs[]` del layout constructor

### Riesgo si cambia

- Alto

## 1.4 Auto layout del constructor

### Endpoint

- Método y ruta:
  `POST /editor_offset/auto_layout/<job_id>`

### Propósito

- generar `slots[]` automáticos desde trabajos lógicos y/o diseños

### Inputs obligatorios

- `job_id` en ruta

### Inputs opcionales

- `layout_json`

### Campos legacy admitidos

- no identificados

### Respuesta esperada

```json
{
  "ok": true,
  "layout": { ... }
}
```

### Dependientes de este contrato

- `static/js/editor_offset_visual.js`
- `slots[]` del constructor

### Riesgo si cambia

- Muy alto

## 1.5 Aplicar motor de imposición en constructor

### Endpoint

- Método y ruta:
  `POST /editor_offset_visual/apply_imposition`

### Propósito

- recalcular `slots[]` usando motor:
  - `repeat`
  - `nesting`
  - `hybrid`

### Inputs obligatorios

- `job_id`

### Inputs opcionales

- `layout_json`
- `selected_engine`

### Campos legacy admitidos

- `selected_engine` puede venir por `form` o contenido de `layout`

### Respuesta esperada

```json
{
  "ok": true,
  "layout": { ... }
}
```

### Dependientes de este contrato

- `static/js/editor_offset_visual.js`
- contrato de `allowed_engines` / `imposition_engine`

### Riesgo si cambia

- Muy alto

## 1.6 Preview del constructor

### Endpoint

- Método y ruta:
  `POST /editor_offset/preview/<job_id>`

### Propósito

- generar preview PNG desde layout del constructor

### Inputs obligatorios

- `job_id`

### Inputs opcionales

- ninguno relevantes

### Campos legacy admitidos

- no identificados

### Respuesta esperada

```json
{
  "ok": true,
  "url": "/static/..."
}
```

### Dependientes de este contrato

- `static/js/editor_offset_visual.js`
- flujo de preview del constructor

### Riesgo si cambia

- Alto

## 1.7 PDF final del constructor

### Endpoint

- Método y ruta:
  `POST /editor_offset/generar_pdf/<job_id>`

### Propósito

- generar PDF final desde layout del constructor

### Inputs obligatorios

- `job_id`

### Inputs opcionales

- ninguno relevantes

### Campos legacy admitidos

- no identificados

### Respuesta esperada

```json
{
  "ok": true,
  "url": "/static/..."
}
```

### Dependientes de este contrato

- `static/js/editor_offset_visual.js`
- descarga final del constructor

### Riesgo si cambia

- Alto

## 2. Editor Post-Imposición

## 2.1 Recuperar layout del editor

### Endpoint

- Método y ruta:
  `GET /layout/<job_id>.json`

### Propósito

- devolver el layout post-imposición serializado

### Inputs obligatorios

- `job_id` en ruta

### Inputs opcionales

- ninguno

### Campos legacy admitidos

- backend garantiza defaults:
  - `bleed_mm`
  - `min_gap_mm`

### Respuesta esperada

- JSON con:
  - `version`
  - `job_id`
  - `sheet`
  - `items[]`
  - `assets[]`
  - `bleed_mm`
  - `min_gap_mm`

### Dependientes de este contrato

- `templates/editor_post_imposicion.html`
- `static/js/editor_post_imposicion.js`
- `layout.json`

### Riesgo si cambia

- Muy alto

## 2.2 Render del editor post-imposición

### Endpoint

- Método y ruta:
  `GET /editor`

### Propósito

- renderizar el editor post-imposición
- inyectar layout y job al frontend

### Inputs obligatorios

- query string `id`

### Inputs opcionales

- ninguno

### Campos legacy admitidos

- backend vuelve a garantizar:
  - `bleed_mm`
  - `min_gap_mm`

### Respuesta esperada

- HTML de `templates/editor_post_imposicion.html`
- globals:
  - `window.layoutIA`
  - `window.jobIdIA`

### Dependientes de este contrato

- `templates/editor_post_imposicion.html`
- `static/js/editor_post_imposicion.js`

### Riesgo si cambia

- Muy alto

## 2.3 Chat IA del editor

### Endpoint

- Método y ruta:
  `POST /editor_chat/<job_id>`

### Propósito

- traducir una instrucción del usuario en acciones IA para el editor

### Inputs obligatorios

- `job_id` en ruta
- JSON:
  - `message`
  - `layout_state`

### Inputs opcionales

- ninguno relevantes

### Campos legacy admitidos

- no identificados

### Respuesta esperada

```json
{
  "assistant_message": "texto corto",
  "actions": [ ... ]
}
```

### Dependientes de este contrato

- `static/js/editor_post_imposicion.js`
- `call_openai_for_editor_chat()`

### Riesgo si cambia

- Muy alto

## 2.4 Reaplicar layout editado

### Endpoint

- Método y ruta:
  `POST /layout/<job_id>/apply`

### Propósito

- validar `items[]`
- regenerar PDF y preview
- persistir `layout.json` actualizado

### Inputs obligatorios

- `job_id` en ruta
- JSON:
  - `items[]`

### Inputs opcionales

- `version`

### Campos legacy admitidos

- `bleed_override_mm` por item

### Respuesta esperada

```json
{
  "ok": true,
  "pliego": "ia_jobs/<job_id>/pliego_edit.pdf",
  "preview": "ia_jobs/<job_id>/preview_edit.png",
  "pdf_url": "/static/...",
  "preview_url": "/static/..."
}
```

### Dependientes de este contrato

- `static/js/editor_post_imposicion.js`
- `layout.json`
- `meta.json`
- assets del job

### Riesgo si cambia

- Muy alto

## 3. Preview / Exportación PDF Offset

## 3.1 Flujo principal de montaje offset inteligente

### Endpoint

- Método y ruta:
  `GET|POST /montaje_offset_inteligente`

### Propósito

- entrada principal al flujo offset inteligente
- genera preview o PDF
- en modo IA crea job de post-edición

### Inputs obligatorios

- en `POST`:
  - `pliego`
  - `archivos[]`
  - repeticiones
  - márgenes mínimos

### Inputs opcionales

- `accion`
- `mode`
- `modo_ia`
- `export_area_util`
- `export_compat`
- estrategia y parámetros avanzados

### Campos legacy admitidos

- distintos modos de sangrado
- modo `pro`
- acción `preview`

### Respuesta esperada

- `GET`:
  - HTML del formulario
- `POST` estándar:
  - preview en template o `send_file`
- `POST` modo IA:
  - HTML con acceso a editor IA
  - genera `layout.json` + `meta.json`

### Dependientes de este contrato

- `templates/montaje_offset_inteligente.html`
- `tests/test_montaje_offset_inteligente.py`
- editor post-imposición

### Riesgo si cambia

- Muy alto

## 3.2 Preview rápido offset

### Endpoint

- Método y ruta:
  `POST /montaje_offset/preview`

### Propósito

- obtener preview base64 del montaje offset inteligente

### Inputs obligatorios

- mismo form base del montaje offset inteligente

### Inputs opcionales

- `export_area_util`

### Campos legacy admitidos

- no identificados aparte de tolerancia del form

### Respuesta esperada

```json
{
  "ok": true,
  "preview_data": "data:image/jpeg;base64,...",
  "resumen_html": "..."
}
```

### Dependientes de este contrato

- `templates/montaje_offset_inteligente.html`
- preview inline del flujo offset

### Riesgo si cambia

- Alto

## 3.3 Preview manual

### Endpoint

- Método y ruta:
  `POST /api/manual/preview`

### Propósito

- generar preview manual desde `positions[]`

### Inputs obligatorios

- JSON:
  - `positions[]`

### Inputs opcionales

- `export_compat`

### Campos legacy admitidos

- por posición:
  - `rot_deg`
  - `rot`
  - `archivo`
  - `file_idx`

### Respuesta esperada

```json
{
  "preview_path": "/static/...",
  "positions_applied": [ ... ]
}
```

### Dependientes de este contrato

- editor manual en `templates/montaje_offset_inteligente.html`
- estado global:
  - `LAST_UPLOADS`
  - `LAST_SHEET_MM`
  - `LAST_SANGRADO_MM`

### Riesgo si cambia

- Muy alto

## 3.4 PDF manual

### Endpoint

- Método y ruta:
  `POST /api/manual/impose`

### Propósito

- generar PDF manual final desde `positions[]`

### Inputs obligatorios

- JSON:
  - `positions[]`

### Inputs opcionales

- `export_compat`

### Campos legacy admitidos

- igual que `/api/manual/preview`

### Respuesta esperada

```json
{
  "pdf_url": "/static/outputs/...",
  "positions_applied": [ ... ]
}
```

### Dependientes de este contrato

- editor manual en `templates/montaje_offset_inteligente.html`

### Riesgo si cambia

- Muy alto

## 4. Diagnóstico Flexo

## 4.1 Revisión flexográfica principal

### Endpoint

- Método y ruta:
  `GET|POST /revision`

### Propósito

- recibir PDF y parámetros de máquina
- generar diagnóstico, overlays, persistencia y resultado HTML

### Inputs obligatorios

- en `POST`:
  - archivo `archivo_revision`
  - `material`
  - `anilox_lpi`
  - `anilox_bcm`
  - `paso_cilindro`
  - `velocidad_impresion`

### Inputs opcionales

- ninguno relevantes fuera de la revisión principal

### Campos legacy admitidos

- aliases que luego se propagan al `diagnostico_json`:
  - `lpi`
  - `bcm`
  - `paso`
  - `paso_cilindro`
  - `paso_del_cilindro`
  - `velocidad`
  - `velocidad_impresion`

### Respuesta esperada

- `GET`:
  - HTML de `revision_flexo.html`
- `POST`:
  - HTML de `resultado_flexo.html`
  - persistencia de:
    - `diag.json`
    - `res.json`
    - PDF revisado
  - seteo de sesión:
    - `revision_flexo_id`

### Dependientes de este contrato

- `templates/revision_flexo.html`
- `templates/resultado_flexo.html`
- `static/js/flexo_simulation.js`
- `tests/test_diagnostico_flexo.py`

### Riesgo si cambia

- Muy alto

## 4.2 Reabrir resultados flexo

### Endpoint

- Método y ruta:
  `GET /resultado`

### Propósito

- rehidratar resultados flexo desde `res.json` usando sesión

### Inputs obligatorios

- sesión con `revision_flexo_id`

### Inputs opcionales

- ninguno

### Campos legacy admitidos

- si falta `diag_img_web`, lo rellena desde otras claves

### Respuesta esperada

- HTML `resultado_flexo.html`
- globals JS consistentes

### Dependientes de este contrato

- `templates/resultado_flexo.html`
- `tests/test_resultado_flexo_template.py`

### Riesgo si cambia

- Alto

## 4.3 Preview técnica

### Endpoint

- Método y ruta:
  `POST /vista_previa_tecnica`

### Propósito

- regenerar preview técnico con overlay

### Inputs obligatorios

- revisión existente por sesión o `archivo_guardado` válido

### Inputs opcionales

- `archivo_guardado`

### Campos legacy admitidos

- usa `revision_flexo_id` de sesión como fallback

### Respuesta esperada

```json
{
  "preview_url": "/static/previews/..."
}
```

### Dependientes de este contrato

- botón/flujo de preview técnica del diagnóstico flexo
- `preview_tecnico.py`

### Riesgo si cambia

- Muy alto

## 4.4 Sugerencia IA del diagnóstico

### Endpoint

- Método y ruta:
  `POST /sugerencia_ia`

### Propósito

- generar recomendación IA a partir del diagnóstico renderizado

### Inputs obligatorios

- `resultado_revision_b64`
- `diagnostico_texto_b64`

### Inputs opcionales

- `grafico_tinta`

### Campos legacy admitidos

- base64 vacíos tolerados con fallback silencioso

### Respuesta esperada

- render de `revision_flexo.html` con sugerencia incorporada

### Dependientes de este contrato

- flujo de sugerencias IA de flexo

### Riesgo si cambia

- Medio

## 5. Exportación De Simulación / Preview PDF

## 5.1 Exportar simulación flexo

### Endpoint

- Método y ruta:
  `POST /simulacion/exportar/<revision_id>`

### Propósito

- generar PNG final descargable de simulación flexo

### Inputs obligatorios

- `revision_id` en ruta
- JSON:
  - `lpi`
  - `bcm`
  - `paso`
  - `velocidad`
  - `tacObjetivo`
  - `cobertura`

### Inputs opcionales

- ninguno relevantes

### Campos legacy admitidos

- el backend tolera parsing flexible numérico
- cobertura puede reescalarse a partir de diagnóstico persistido

### Respuesta esperada

- binario `image/png`
- descarga con nombre de archivo

### Dependientes de este contrato

- `static/js/flexo_simulation.js`
- resultado flexo

### Riesgo si cambia

- Muy alto

## 6. Variables Globales De Template Congeladas

Estas variables no son endpoints, pero son parte del contrato HTTP efectivo.

### Constructor IA

- `window.INITIAL_LAYOUT_JSON`

### Editor post-imposición

- `window.layoutIA`
- `window.jobIdIA`

### Resultado flexo

- `window.USE_PIPELINE_V2`
- `window.diagnosticoJson`
- `window.advertencias`
- `window.analisisDetallado`
- `window.indicadoresAdvertencias`
- `window.advertenciasResumen`
- `window.revisionId`

### Riesgo si cambian

- Muy alto

Porque alteran el contrato real entre backend, template y JS aunque no cambie la ruta.

## 7. Orden De Protección Recomendado

Prioridad máxima:

1. `GET /editor_offset_visual`
2. `POST /editor_offset/upload/<job_id>`
3. `POST /editor_offset/auto_layout/<job_id>`
4. `POST /editor_offset_visual/apply_imposition`
5. `GET /layout/<job_id>.json`
6. `POST /editor_chat/<job_id>`
7. `POST /layout/<job_id>/apply`
8. `POST /revision`
9. `POST /vista_previa_tecnica`
10. `POST /simulacion/exportar/<revision_id>`

Prioridad alta secundaria:

11. `POST /montaje_offset/preview`
12. `POST /api/manual/preview`
13. `POST /api/manual/impose`
14. `GET /resultado`

## 8. Uso Operativo En Refactor

Antes de tocar un endpoint crítico:

1. revisar esta ficha
2. revisar `DOCS/CONTRATOS_CRITICOS_SISTEMA.md`
3. revisar `DOCS/FUENTES_DE_VERDAD_POR_SUBSISTEMA.md`
4. correr la checklist de `DOCS/SMOKE_TESTS_FUNCIONALES_MINIMOS.md`

Si cambia:

- input obligatorio
- input opcional
- alias legacy
- forma de respuesta
- globals inyectadas

entonces no es un refactor interno.
Es un cambio de contrato.
