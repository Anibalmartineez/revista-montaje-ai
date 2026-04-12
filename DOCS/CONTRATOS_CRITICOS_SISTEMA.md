# Contratos Críticos Del Sistema

Documento de referencia para congelar el comportamiento actual antes de la refactorización.

Objetivo:

- Identificar rutas y endpoints críticos.
- Fijar payloads y respuestas que hoy consume el frontend.
- Documentar los módulos Python y JS cuya interacción no debe romperse.

No describe diseño ideal. Describe el contrato actual.

## 1. Rutas Principales Del Sistema Flask

### Offset / montaje

- `GET /editor_offset_visual`
  Editor visual IA nuevo para definición de slots y asignación de diseños.
- `POST /editor_offset/save`
  Guarda `layout_json` del editor visual IA.
- `POST /editor_offset/upload/<job_id>`
  Sube PDFs y los incorpora al `layout`.
- `POST /editor_offset/auto_layout/<job_id>`
  Genera slots automáticos con IA/motor inteligente.
- `POST /editor_offset_visual/apply_imposition`
  Aplica motor de imposición (`repeat`, `nesting`, `hybrid`) al layout.
- `POST /editor_offset/preview/<job_id>`
  Genera preview del montaje desde layout.
- `POST /editor_offset/generar_pdf/<job_id>`
  Genera PDF final desde layout.
- `GET|POST /montaje_offset_inteligente`
  Flujo principal de montaje offset inteligente.
- `POST /montaje_offset/preview`
  Preview rápido del montaje offset inteligente.
- `POST /api/manual/preview`
  Preview manual basado en posiciones editadas.
- `POST /api/manual/impose`
  Genera PDF manual basado en posiciones editadas.
- `GET /layout/<job_id>.json`
  Devuelve layout serializado para el editor post-imposición.
- `GET /editor`
  Renderiza editor post-imposición IA.
- `POST /editor_chat/<job_id>`
  Chat IA del editor post-imposición.
- `POST /layout/<job_id>/apply`
  Reaplica layout editado y regenera preview/PDF.
- `GET|POST /imposicion_offset_auto`
  Flujo alternativo de imposición automática.

### Flexo / diagnóstico

- `GET|POST /montaje_flexo_avanzado`
  Flujo de montaje flexo avanzado.
- `GET|POST /revision`
  Flujo principal de diagnóstico flexográfico.
- `GET /resultado`
  Reabre resultados flexo persistidos en sesión.
- `POST /vista_previa_tecnica`
  Regenera preview técnico con overlays.
- `POST /sugerencia_ia`
  Sugerencia IA sobre diagnóstico.
- `POST /sugerencia_produccion`
  Sugerencia de producción.
- `POST /simulacion/exportar/<revision_id>`
  Exporta PNG final de simulación flexo.
- `GET /descargar_montaje_flexo_avanzado`
- `GET /descargar_reporte_flexo_avanzado`

### Utilitarios PDF / legado

- `GET|POST /`
- `POST /diagnostico_offset`
- `GET /descargar`
- `GET /outputs/<path:filename>`
- `GET|POST /montaje_offset`
- `GET /descargar_pliego_offset`
- `GET /descargar_reporte_offset`
- `POST /vista_previa`
- `GET /preview`
- `POST /generar_pdf_final`

## 2. Endpoints Usados Por El Editor Visual IA

Hay dos etapas distintas.

### A. Editor visual IA “constructor”

Template:

- `templates/editor_offset_visual.html`

JS:

- `static/js/editor_offset_visual.js`

Endpoints:

- `GET /editor_offset_visual`
- `POST /editor_offset/save`
- `POST /editor_offset/upload/<job_id>`
- `POST /editor_offset/auto_layout/<job_id>`
- `POST /editor_offset_visual/apply_imposition`
- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`

Variables inyectadas:

- `window.INITIAL_LAYOUT_JSON`

### B. Editor post-imposición IA

Template:

- `templates/editor_post_imposicion.html`

JS:

- `static/js/editor_post_imposicion.js`

Endpoints:

- `GET /editor?id=<job_id>`
- `GET /layout/<job_id>.json`
- `POST /editor_chat/<job_id>`
- `POST /layout/<job_id>/apply`

Variables inyectadas:

- `window.layoutIA`
- `window.jobIdIA`

## 3. Estructura De Los Payloads JSON Críticos

## 3.1 Layout del editor visual IA

Payload persistido en constructor y usado por:

- `POST /editor_offset/save`
- `POST /editor_offset/auto_layout/<job_id>`
- `POST /editor_offset_visual/apply_imposition`
- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`

Forma base observada:

```json
{
  "sheet_mm": [640, 880],
  "margins_mm": [10, 10, 10, 10],
  "bleed_default_mm": 3,
  "gap_default_mm": 5,
  "works": [],
  "slots": [],
  "designs": [],
  "export_settings": {
    "bleed_mm": 3,
    "crop_marks": true,
    "output_mode": "raster"
  },
  "design_export": {},
  "faces": ["front"],
  "active_face": "front",
  "imposition_engine": "repeat",
  "allowed_engines": ["repeat", "nesting", "hybrid"]
}
```

Campos relevantes:

- `works[]`
  trabajos lógicos para IA.
- `designs[]`
  PDFs subidos y metadatos de tamaño.
- `slots[]`
  posiciones editables en pliego.
- `sheet_mm`
  tamaño del pliego.
- `margins_mm`
  márgenes `[left, right, top, bottom]`.
- `faces` / `active_face`
  soporte frente/dorso.
- `imposition_engine`
  motor seleccionado.

Ejemplo de `designs[]`:

```json
{
  "ref": "file0",
  "filename": "pieza.pdf",
  "work_id": "work_1",
  "width_mm": 100.0,
  "height_mm": 50.0,
  "bleed_mm": 3.0,
  "allow_rotation": true,
  "forms_per_plate": 1
}
```

Ejemplo de `slots[]`:

```json
{
  "id": "nest_0",
  "x_mm": 10.0,
  "y_mm": 20.0,
  "w_mm": 106.0,
  "h_mm": 56.0,
  "rotation_deg": 0,
  "logical_work_id": null,
  "bleed_mm": 3.0,
  "crop_marks": true,
  "locked": false,
  "design_ref": "file0",
  "face": "front"
}
```

## 3.2 `POST /editor_offset/save`

Entrada esperada:

- `job_id`
- `layout_json`

Respuesta:

```json
{
  "ok": true,
  "job_id": "abc123def456"
}
```

## 3.3 `POST /editor_offset/upload/<job_id>`

Entrada:

- multipart form-data
- archivos en `files` o `file`
- opcional `work_id`

Respuesta:

```json
{
  "designs": [ ... ]
}
```

## 3.4 `POST /editor_offset/auto_layout/<job_id>`

Entrada:

- opcional `job_id`
- opcional `layout_json`

Respuesta:

```json
{
  "ok": true,
  "layout": { ...layout actualizado... }
}
```

## 3.5 `POST /editor_offset_visual/apply_imposition`

Entrada:

- `job_id`
- opcional `layout_json`
- opcional `selected_engine`

Respuesta:

```json
{
  "ok": true,
  "layout": { ...layout con slots recalculados... }
}
```

## 3.6 Layout post-imposición (`/layout/<job_id>.json`)

Este es el contrato más delicado del editor IA posterior.

Forma observada:

```json
{
  "version": 1,
  "job_id": "abc123def456",
  "sheet": {
    "w_mm": 700.0,
    "h_mm": 1000.0,
    "pinza_mm": 0.0,
    "margins_mm": {
      "top": 10.0,
      "bottom": 10.0,
      "left": 10.0,
      "right": 10.0
    }
  },
  "grid_mm": {
    "enabled": false,
    "rows": null,
    "cols": null,
    "cell_w": null,
    "cell_h": null
  },
  "bleed_mm": 3.0,
  "items": [
    {
      "id": "item0",
      "src": "assets/00_pieza.pdf",
      "page": 0,
      "x_mm": 10.0,
      "y_mm": 20.0,
      "w_mm": 100.0,
      "h_mm": 50.0,
      "rotation": 0,
      "flip_x": false,
      "flip_y": false,
      "file_idx": 0
    }
  ],
  "assets": [
    {
      "id": "asset0",
      "src": "assets/00_pieza.pdf",
      "original_src": "C:/.../pieza.pdf",
      "cantidad": 4,
      "file_idx": 0
    }
  ],
  "pdf_filename": "pliego.pdf",
  "preview_filename": "preview_edit.png",
  "min_gap_mm": 0
}
```

Notas:

- El backend garantiza `bleed_mm` y `min_gap_mm` al responder `/layout/<job_id>.json`.
- `items[]` es la fuente de verdad del editor post-imposición.
- `assets[]` alimenta selector de reemplazo e integridad del layout.

## 3.7 `POST /editor_chat/<job_id>`

Entrada:

```json
{
  "message": "texto del usuario",
  "layout_state": { ...layout actual del editor... }
}
```

Respuesta esperada del backend:

```json
{
  "assistant_message": "texto corto",
  "actions": [ ... ]
}
```

Notas:

- `call_openai_for_editor_chat()` fuerza respuesta JSON.
- Este contrato es crítico para `editor_post_imposicion.js`.

## 3.8 `POST /layout/<job_id>/apply`

Entrada:

```json
{
  "version": 1,
  "items": [
    {
      "id": "item0",
      "src": "assets/00_pieza.pdf",
      "page": 0,
      "x_mm": 10.0,
      "y_mm": 20.0,
      "w_mm": 100.0,
      "h_mm": 50.0,
      "rotation": 0,
      "flip_x": false,
      "flip_y": false,
      "file_idx": 0,
      "bleed_override_mm": 2.0
    }
  ]
}
```

Validaciones críticas:

- `src` debe existir en metadatos del job.
- No puede salir del pliego/márgenes.
- No puede haber solapes.
- La cantidad por diseño debe coincidir con el montaje original.

Respuesta:

```json
{
  "ok": true,
  "pliego": "ia_jobs/<job_id>/pliego_edit.pdf",
  "preview": "ia_jobs/<job_id>/preview_edit.png",
  "pdf_url": "/static/ia_jobs/<job_id>/pliego_edit.pdf",
  "preview_url": "/static/ia_jobs/<job_id>/preview_edit.png"
}
```

## 3.9 `POST /api/manual/preview`

Entrada:

```json
{
  "positions": [
    {
      "uid": "slot-1",
      "file_idx": 0,
      "archivo": "pieza.pdf",
      "x_mm": 10.0,
      "y_mm": 20.0,
      "w_mm": 100.0,
      "h_mm": 50.0,
      "rot_deg": 90
    }
  ],
  "export_compat": "pdfx1a"
}
```

Respuesta:

```json
{
  "preview_path": "/static/previews/manual_xxx.png",
  "positions_applied": [ ... ]
}
```

Notas:

- Acepta compatibilidad legacy por `rot`.
- Usa `LAST_UPLOADS`, `LAST_SHEET_MM` y `LAST_SANGRADO_MM` en `current_app.config`.

## 3.10 `POST /api/manual/impose`

Entrada:

```json
{
  "positions": [ ... ],
  "export_compat": "adobe_compatible"
}
```

Respuesta:

```json
{
  "pdf_url": "/static/outputs/manual_xxx.pdf",
  "positions_applied": [ ... ]
}
```

## 3.11 Contrato de diagnóstico flexo

Entrada de `POST /revision`:

- multipart form-data
- archivo PDF en `archivo_revision`
- `material`
- `anilox_lpi`
- `anilox_bcm`
- `paso_cilindro`
- `velocidad_impresion`

Respuesta:

- render HTML de `resultado_flexo.html`
- persiste estado en:
  - `static/uploads/<revision_id>/diag.json`
  - `static/uploads/<revision_id>/res.json`
  - `static/uploads/<revision_id>/<revision_id>.pdf`
  - imágenes de diagnóstico y overlay

Claves críticas de `diagnostico_json` usadas por frontend:

- `archivo`
- `pdf_path`
- `anilox_lpi`
- `anilox_bcm`
- `lpi`
- `bcm`
- `paso`
- `paso_cilindro`
- `paso_del_cilindro`
- `velocidad`
- `velocidad_impresion`
- `material`
- `coef_material`
- `ancho_mm`
- `alto_mm`
- `ancho_util_m`
- `advertencias_resumen`
- `indicadores_advertencias`
- `cobertura_por_canal`
- `cobertura`
- `cobertura_total`
- `tac_total`
- `tac_total_v2`
- `tac_p95`
- `tac_max`
- `cobertura_estimada`
- `cobertura_base_sum`
- `tinta_ml_min`
- `tinta_por_canal_ml_min`

## 3.12 `POST /vista_previa_tecnica`

Entrada:

- form-data con `archivo_guardado` opcional
- si no viene, usa `revision_flexo_id` de sesión

Respuesta:

```json
{
  "preview_url": "/static/previews/preview_diagnostico_flexo_xxx.png"
}
```

## 3.13 `POST /simulacion/exportar/<revision_id>`

Entrada:

```json
{
  "lpi": 400,
  "bcm": 3.5,
  "paso": 350,
  "velocidad": 80,
  "tacObjetivo": 240,
  "cobertura": {
    "C": 50,
    "M": 45,
    "Y": 40,
    "K": 35
  }
}
```

Salida:

- respuesta binaria `image/png`
- `Content-Disposition` con nombre descargable

## 4. Archivos JS Críticos Y Cómo Se Conectan Con El Backend

### `static/js/editor_offset_visual.js`

Conecta con:

- `window.INITIAL_LAYOUT_JSON`
- `POST /editor_offset/save`
- `POST /editor_offset/upload/<job_id>`
- `POST /editor_offset/auto_layout/<job_id>`
- `POST /editor_offset_visual/apply_imposition`
- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`

Responsabilidad:

- gestionar sheet, works, designs y slots
- edición visual del constructor
- selección de motor de imposición

### `static/js/editor_post_imposicion.js`

Conecta con:

- `window.layoutIA`
- `window.jobIdIA`
- `GET /layout/<job_id>.json`
- `POST /editor_chat/<job_id>`
- `POST /layout/<job_id>/apply`

Responsabilidad:

- editar piezas finales
- mover, redimensionar, rotar, alinear
- mostrar trim/bleed boxes
- aplicar instrucciones IA
- guardar preview/PDF regenerados

### `static/js/flexo_simulation.js`

Conecta con:

- `window.USE_PIPELINE_V2`
- `window.diagnosticoJson`
- `window.analisisDetallado`
- `window.indicadoresAdvertencias`
- `window.advertencias`
- `window.revisionId`
- `POST /simulacion/exportar/<revision_id>`

Responsabilidad:

- simulación visual flexo
- cálculo derivado de cobertura/TAC
- exportación PNG final

## 5. Módulos Python Críticos Del Sistema

### Orquestación Flask

- `app.py`
- `routes.py`

### Offset inteligente / editor IA

- `montaje_offset_inteligente.py`
- `montaje_offset_personalizado.py`
- `montaje_offset.py`
- `imposicion_offset_auto.py`
- `engines/nesting_pro_engine.py`
- `strategies/nesting_pro_strategy.py`
- `ai_strategy_selector.py`

### Flexo / overlays / diagnóstico

- `montaje_flexo.py`
- `diagnostico_flexo.py`
- `diagnostico_pdf.py`
- `preview_tecnico.py`
- `advertencias_disenio.py`
- `cobertura_utils.py`
- `reporte_tecnico.py`
- `simulador_riesgos.py`
- `flexo_config.py`
- `tinta_utils.py`

### Utilidades transversales

- `utils.py`
- `utils_geom.py`
- `utils_img.py`
- `pdf_compat.py`
- `ia_sugerencias.py`

## 6. Flujo De Datos Del Editor Visual IA

## 6.1 Constructor de layout

1. `GET /editor_offset_visual`
2. Backend crea o carga `job_id` y serializa `layout_json`.
3. Template inyecta `window.INITIAL_LAYOUT_JSON`.
4. `editor_offset_visual.js` renderiza pliego, trabajos, diseños y slots.
5. Frontend guarda o recalcula usando:
   - `/editor_offset/save`
   - `/editor_offset/upload/<job_id>`
   - `/editor_offset/auto_layout/<job_id>`
   - `/editor_offset_visual/apply_imposition`
6. Frontend puede pedir:
   - preview con `/editor_offset/preview/<job_id>`
   - PDF con `/editor_offset/generar_pdf/<job_id>`

## 6.2 Paso a editor post-imposición

1. `POST /montaje_offset_inteligente` en modo IA genera montaje.
2. Backend copia assets a `static/ia_jobs/<job_id>/assets`.
3. Backend escribe:
   - `layout.json`
   - `meta.json`
   - PDF base del pliego
4. Template de `montaje_offset_inteligente.html` muestra botón “Editar montaje IA”.
5. `GET /editor?id=<job_id>` carga editor post-imposición.

## 6.3 Edición IA posterior

1. `GET /editor`
2. Template inyecta `window.layoutIA` y `window.jobIdIA`.
3. `editor_post_imposicion.js` renderiza piezas y overlays de caja trim/bleed.
4. Si el usuario usa IA:
   - frontend envía `message + layout_state` a `/editor_chat/<job_id>`
   - backend responde `assistant_message + actions`
5. Si el usuario guarda:
   - frontend envía `items[]` a `/layout/<job_id>/apply`
   - backend valida, regenera PDF, regenera preview y actualiza `layout.json`
6. Backend devuelve nuevas URLs públicas de preview y PDF.

## 7. Flujo De Diagnóstico Flexo

1. Usuario entra a `GET /revision`.
2. Envía PDF y parámetros a `POST /revision`.
3. Backend:
   - valida archivo y parámetros
   - normaliza material
   - ejecuta `revisar_diseño_flexo()`
   - genera overlays con `analizar_riesgos_pdf()`
   - genera imágenes con `generar_preview_diagnostico()`
   - calcula resumen/riesgos/simulación
   - construye `diagnostico_json`
   - persiste `diag.json` y `res.json`
   - guarda `revision_flexo_id` en sesión
4. Renderiza `resultado_flexo.html`
5. Template expone:
   - `window.diagnosticoJson`
   - `window.advertencias`
   - `window.analisisDetallado`
   - `window.indicadoresAdvertencias`
   - `window.revisionId`
6. `flexo_simulation.js` usa esos datos para simulación/exportación.
7. `GET /resultado` rehidrata el estado desde `res.json`.
8. `POST /vista_previa_tecnica` puede regenerar preview técnico desde `diag.json`.

## 8. Flujo De Generación / Exportación PDF

### Offset inteligente estándar

1. `POST /montaje_offset_inteligente`
2. Backend parsea form.
3. Llama `realizar_montaje_inteligente()`.
4. Si no es modo IA:
   - devuelve `send_file()` del PDF generado.
5. Si es modo IA:
   - genera job persistido
   - serializa layout y assets
   - expone PDF por URL estática

### Preview offset rápido

1. `POST /montaje_offset/preview`
2. Backend ejecuta montaje sin PDF final.
3. Responde:

```json
{
  "ok": true,
  "preview_data": "data:image/jpeg;base64,...",
  "resumen_html": "..."
}
```

### Manual preview / manual impose

1. Frontend envía `positions[]`.
2. `POST /api/manual/preview`
   devuelve PNG de preview por URL.
3. `POST /api/manual/impose`
   devuelve PDF final por URL.

### Editor post-imposición

1. Frontend edita `items[]`.
2. `POST /layout/<job_id>/apply`
3. Backend:
   - valida integridad
   - regenera PDF final editado
   - regenera preview
   - actualiza `layout.json` y `meta.json`
4. Devuelve URLs nuevas.

### Exportación flexo PNG

1. `flexo_simulation.js` arma payload de simulación.
2. `POST /simulacion/exportar/<revision_id>`
3. Backend genera PNG final en memoria.
4. Devuelve descarga `image/png`.

## Puntos De Congelación Recomendados

No romper en refactorización:

- claves de `layout.json`
- claves de `diagnostico_json`
- firma de `POST /editor_chat/<job_id>`
- estructura de `items[]` en `/layout/<job_id>/apply`
- `positions[]` de `/api/manual/preview` y `/api/manual/impose`
- variables globales inyectadas en templates:
  - `INITIAL_LAYOUT_JSON`
  - `layoutIA`
  - `jobIdIA`
  - `diagnosticoJson`
  - `advertencias`
  - `analisisDetallado`
  - `indicadoresAdvertencias`
  - `revisionId`
