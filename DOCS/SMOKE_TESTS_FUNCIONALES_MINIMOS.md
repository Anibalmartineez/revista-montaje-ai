# Smoke Tests Funcionales Mínimos

Checklist manual de validación para proteger los flujos críticos antes del primer refactor real.

Objetivo:

- validar que los contratos críticos sigan vivos
- detectar roturas rápidamente
- cubrir el editor IA, layout, diagnóstico flexo y exportación de simulación

Este documento no cambia código.
Es una red mínima, operativa y reversible.

## Uso recomendado

- correr estos checks antes de empezar cambios de Fase 2
- repetirlos después de cada cambio que toque contratos, serialización, jobs, IA o flujo flexo
- si falla uno, no avanzar con refactor estructural hasta explicar la causa

## 1. Editor Visual IA

### Smoke test: abrir constructor IA

- Precondiciones:
  - app Flask levantada
  - ruta `/editor_offset_visual` accesible
- Entrada mínima:
  - `GET /editor_offset_visual`
- Resultado esperado:
  - responde `200`
  - renderiza la pantalla del editor visual IA
  - existe `window.INITIAL_LAYOUT_JSON`
  - el layout incluye al menos claves base del constructor:
    - `sheet_mm`
    - `margins_mm`
    - `works`
    - `designs`
    - `slots`
    - `faces`
    - `active_face`
- Archivos o contratos que valida:
  - `templates/editor_offset_visual.html`
  - `static/js/editor_offset_visual.js`
  - contrato de constructor documentado en `DOCS/CONTRATOS_CRITICOS_SISTEMA.md`

### Smoke test: subir un PDF al constructor

- Precondiciones:
  - editor abierto
  - `job_id` válido en URL
  - PDF simple disponible
- Entrada mínima:
  - `POST /editor_offset/upload/<job_id>`
  - multipart con un PDF en `files`
- Resultado esperado:
  - respuesta JSON válida
  - devuelve `designs[]`
  - cada diseño nuevo contiene:
    - `ref`
    - `filename`
    - `width_mm`
    - `height_mm`
    - `bleed_mm`
    - `forms_per_plate`
- Archivos o contratos que valida:
  - `routes.py` upload constructor
  - estructura `designs[]`

### Smoke test: generar slots automáticos

- Precondiciones:
  - constructor con al menos un diseño o trabajo lógico cargado
- Entrada mínima:
  - `POST /editor_offset/auto_layout/<job_id>`
- Resultado esperado:
  - respuesta `{"ok": true, "layout": ...}`
  - `layout.slots` existe y es lista
  - si se generaron slots, cada slot conserva:
    - `id`
    - `x_mm`
    - `y_mm`
    - `w_mm`
    - `h_mm`
    - `rotation_deg`
    - `face`
- Archivos o contratos que valida:
  - contrato de `layout` constructor
  - persistencia de `layout_constructor.json`

## 2. GET /layout/<job_id>.json

### Smoke test: recuperar layout post-imposición

- Precondiciones:
  - existe un job IA post-imposición válido
  - `ENABLE_POST_EDITOR` activo
  - existe `static/ia_jobs/<job_id>/layout.json`
- Entrada mínima:
  - `GET /layout/<job_id>.json`
- Resultado esperado:
  - responde `200`
  - el JSON incluye:
    - `version`
    - `job_id`
    - `sheet`
    - `items`
    - `assets`
    - `bleed_mm`
    - `min_gap_mm`
  - `items[]` es lista no vacía para un job válido
  - `assets[]` referencia los recursos usados
- Archivos o contratos que valida:
  - `GET /layout/<job_id>.json`
  - `templates/editor_post_imposicion.html`
  - `static/js/editor_post_imposicion.js`
  - `DOCS/FUENTES_DE_VERDAD_POR_SUBSISTEMA.md`

## 3. POST /layout/<job_id>/apply

### Smoke test: reaplicar layout editado mínimo

- Precondiciones:
  - existe job IA válido
  - `layout.json` cargable
  - `items[]` actuales disponibles
- Entrada mínima:
  - `POST /layout/<job_id>/apply`
  - JSON con:
    - `version`
    - `items[]` tomados del layout actual sin alteraciones
- Resultado esperado:
  - responde `200`
  - JSON incluye:
    - `ok: true`
    - `pliego`
    - `preview`
    - `pdf_url`
    - `preview_url`
  - no falla validación de integridad
  - el preview y PDF regenerados son accesibles
- Archivos o contratos que valida:
  - contrato de `items[]`
  - regeneración desde `layout.json`
  - sincronía entre `layout.json`, `meta.json` y assets

### Smoke test: rechazo de layout inválido

- Precondiciones:
  - mismo job válido
- Entrada mínima:
  - enviar un `items[]` con una pieza fuera del pliego o con ancho `<= 0`
- Resultado esperado:
  - respuesta JSON de error
  - no modifica silenciosamente el layout
- Archivos o contratos que valida:
  - validación backend de `layout/<job_id>/apply`
  - contrato de errores JSON

## 4. POST /editor_chat/<job_id>

### Smoke test: respuesta estructurada del chat IA

- Precondiciones:
  - job IA válido
  - endpoint accesible
  - si OpenAI no está disponible, usar entorno/test donde responda o mock manual
- Entrada mínima:
  - JSON:
    - `message`: instrucción simple
    - `layout_state`: layout actual
- Resultado esperado:
  - responde JSON
  - incluye siempre:
    - `assistant_message`
    - `actions`
  - `actions` es lista, incluso si está vacía
  - no devuelve texto libre fuera del objeto JSON
- Archivos o contratos que valida:
  - `POST /editor_chat/<job_id>`
  - contrato congelado del editor IA
  - consumo en `static/js/editor_post_imposicion.js`

## 5. POST /revision

### Smoke test: diagnóstico flexo mínimo

- Precondiciones:
  - app levantada
  - PDF simple disponible
  - valores válidos para:
    - `material`
    - `anilox_lpi`
    - `anilox_bcm`
    - `paso_cilindro`
    - `velocidad_impresion`
- Entrada mínima:
  - multipart a `POST /revision`
  - archivo en `archivo_revision`
  - parámetros mínimos válidos
- Resultado esperado:
  - responde `200`
  - renderiza `resultado_flexo.html`
  - genera `revision_id`
  - persiste:
    - `diag.json`
    - `res.json`
    - PDF persistido
  - `diagnostico_json` incluye claves críticas:
    - `material`
    - `anilox_lpi`
    - `anilox_bcm`
    - `paso`
    - `velocidad_impresion`
    - `tac_total`
    - `tac_total_v2`
    - `cobertura_por_canal`
- Archivos o contratos que valida:
  - `POST /revision`
  - `templates/resultado_flexo.html`
  - `diagnostico_json`
  - flujo persistido en `uploads/<revision_id>/`

### Smoke test: validación de error por input faltante

- Precondiciones:
  - app levantada
- Entrada mínima:
  - `POST /revision` sin material o sin PDF
- Resultado esperado:
  - responde sin crash
  - renderiza `revision_flexo.html`
  - muestra warning en lugar de error no controlado
- Archivos o contratos que valida:
  - validaciones de entrada del flujo flexo

## 6. POST /vista_previa_tecnica

### Smoke test: regenerar preview técnica desde revisión existente

- Precondiciones:
  - ya se ejecutó un `POST /revision` exitoso
  - `revision_flexo_id` existe en sesión
  - `diag.json` existe
- Entrada mínima:
  - `POST /vista_previa_tecnica`
  - sin parámetros adicionales, o con `archivo_guardado` válido
- Resultado esperado:
  - responde JSON con `preview_url`
  - la URL resultante es accesible
  - se mantiene overlay técnico visible
- Archivos o contratos que valida:
  - `preview_tecnico.py`
  - `diag.json`
  - contrato de preview técnica

## 7. POST /simulacion/exportar/<revision_id>

### Smoke test: exportar PNG de simulación

- Precondiciones:
  - existe revisión flexo válida
  - `revision_id` accesible
  - frontend o request manual puede construir payload
- Entrada mínima:
  - JSON con:
    - `lpi`
    - `bcm`
    - `paso`
    - `velocidad`
    - `tacObjetivo`
    - `cobertura` con `C`, `M`, `Y`, `K`
- Resultado esperado:
  - responde `200`
  - `Content-Type: image/png`
  - devuelve binario descargable
  - no devuelve HTML ni JSON
- Archivos o contratos que valida:
  - `POST /simulacion/exportar/<revision_id>`
  - `static/js/flexo_simulation.js`
  - contrato de exportación PNG

## 8. Qué Ya Tiene Cobertura Parcial En tests/

Cobertura útil ya presente:

- `tests/test_montaje_offset_inteligente.py`
  - cubre parte de `POST /montaje_offset_inteligente`
  - verifica generación de `layout.json` en modo IA
- `tests/test_diagnostico_flexo.py`
  - cubre parte relevante de `POST /revision`
  - cubre diagnóstico, TAC, cobertura y template flexo
- `tests/test_resultado_flexo_template.py`
  - cubre parte del render del template de resultados

## 9. Tests Mínimos Adicionales: recomendación

Por seguridad, en esta tarea no se agregan tests nuevos en `tests/`.

Motivo:

- los flujos pendientes más críticos (`/layout/<job_id>.json`, `/layout/<job_id>/apply`, `/editor_chat/<job_id>`, `/vista_previa_tecnica`, `/simulacion/exportar/<revision_id>`) dependen de jobs, sesión, archivos persistidos y estado de app
- para cubrirlos bien haría falta armar fixtures específicas del sistema actual
- eso ya empieza a tocar setup estructural del entorno de test

Recomendación para siguiente paso si se quiere automatizar sin mucho riesgo:

- agregar primero tests de smoke de solo lectura para:
  - `GET /layout/<job_id>.json`
  - `POST /editor_chat/<job_id>` con mock
- dejar para después los tests que regeneran PDF/preview o dependen de sesión flexo

## 10. Secuencia Recomendada De Uso

Antes de refactor:

1. `POST /revision`
2. `POST /vista_previa_tecnica`
3. `POST /simulacion/exportar/<revision_id>`
4. abrir `GET /editor_offset_visual`
5. subir un PDF al constructor
6. generar slots
7. abrir `GET /layout/<job_id>.json`
8. llamar `POST /editor_chat/<job_id>`
9. llamar `POST /layout/<job_id>/apply` con payload sin cambios

Si estos checks pasan, el sistema está en condición mínima de seguridad para comenzar cambios reales.
