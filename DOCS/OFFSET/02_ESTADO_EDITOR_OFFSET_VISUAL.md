# Estado Editor Offset Visual

Fuente principal: `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`.

Este documento resume el estado actual del Editor Offset Visual. No autoriza cambios; sirve como referencia SAFE antes de editar.

## Hechos confirmados

El Editor Offset Visual esta operativo como flujo de construccion visual por job: carga o crea layout, permite configurar elementos principales, aplicar imposicion, editar slots, guardar, generar preview y generar PDF final.

El sistema esta modularizado parcialmente. Existen modulos extraidos en `static/js/editor_offset_visual/`, pero `static/js/editor_offset_visual.js` sigue siendo el centro de acoplamiento funcional.

## Que esta operativo

- Entrada por `GET /editor_offset_visual`.
- Carga o creacion de `layout_constructor.json`.
- Inyeccion de `window.INITIAL_LAYOUT_JSON` y `window.JOB_ID`.
- Inicializacion de `state.layout`.
- Configuracion UI de pliego, trabajos, disenos, spacing, export y CTP.
- Upload de PDFs por `POST /editor_offset/upload/<job_id>`.
- Guardado por `POST /editor_offset/save`.
- Apply imposition por `POST /editor_offset_visual/apply_imposition`.
- Motor `repeat` mediante `engines/step_repeat_pro_engine.py`.
- Edicion manual: seleccion, multiseleccion, box select, drag/move, duplicar, borrar, agrupar, alinear, distribuir y nudge.
- Preview por `POST /editor_offset/preview/<job_id>`.
- PDF final por `POST /editor_offset/generar_pdf/<job_id>`.
- Simulacion de cuadernillos por `POST /editor_offset/cuadernillos/simular`.
- Panel IA conectado a endpoints de Step & Repeat/bridge OpenAI.

## Que esta parcialmente operativo

### Nesting/hybrid

`nesting` y `hybrid` estan conectados desde `services/editor_offset_imposition_service.py` y usan `engines/nesting_pro_engine.py`. La auditoria no encontro validacion equivalente a `IncompleteImpositionError` de `repeat` para garantizar que todas las formas solicitadas se hayan colocado.

### Preview/PDF

Preview y PDF comparten transformador backend en `services/editor_offset_output_service.py`. Sin embargo, la preview no necesariamente representa de forma fiel todo el PDF final CTP, especialmente en doble cara y marcas/textos tecnicos.

### IA

La IA operativa existe en `ai_agent/tools_repeat.py` y `ai_agent/openai_tool_bridge.py`, con panel frontend en `ai_panel.js`. La auditoria no confirma cobertura Playwright con respuesta OpenAI real desde UI.

## Que esta latente

### Resize

Resize existe como rama latente:

- CSS para `.slot .handle` en `static/css/editor_offset_visual.css`.
- Logica de resize latente en `static/js/editor_offset_visual.js`.
- Deteccion de `.handle` en `static/js/editor_offset_visual/slot_interactions.js`.

Pero no debe considerarse operativo porque el renderer activo no crea handles.

## Que parece legacy

- Wrappers de `routes.py` hacia `engines/step_repeat_pro_engine.py`.
- `_generate_slots_with_ai()` en `routes.py`, conectado a `/editor_offset/auto_layout/<job_id>`, distinto del flujo actual de `apply_imposition`.
- Bloques inalcanzables en `renderSheet()` y `renderCtpGuideOverlay()` dentro de `static/js/editor_offset_visual.js`.
- Flujos offset antiguos convivientes: editor post-imposicion, manual editor e imposicion automatica.

## Que esta desalineado

### Hechos confirmados

- Algunos controles visibles del panel Step & Repeat manual no tienen lectura confirmada por `generateStepRepeatFromSelectedSlot()`: `sr-offset-x`, `sr-offset-y`, `sr-top-margin`, `sr-bottom-margin`, `sr-left-margin`, `sr-right-margin`.
- Existen listeners opcionales para `btn-center-selection-x` y `btn-center-selection-y`, pero esos IDs no existen en el HTML auditado.
- El panel "Pliego y margenes" no expone editor explicito de `margins_mm`.
- El boton topbar "Generar slots con IA" exige trabajos logicos, mientras el panel de imposicion puede operar sobre disenos/PDFs.

### Inferencias

La UI conserva restos o controles adelantados de una intencion funcional mas amplia. Se requiere verificacion antes de eliminarlos o activarlos.

## Que falta validar

- Existencia fisica de PDFs referenciados por `design.filename`.
- Semantica exacta de `design.width_mm` y `design.height_mm`.
- Precedencia entre `slot.export_overrides`, `design_export` y `export_settings`.
- Paridad entre canvas, preview y PDF final.
- Doble cara en preview vs PDF final.
- CTP marks, strip y texto tecnico.
- `vector_hybrid`.
- `nesting/hybrid` incompleto.
- Compatibilidad con layouts historicos.

## Estado del frontend

### Hechos confirmados

El frontend esta activo y dividido en template, CSS, entrypoint y modulos. Los modulos ayudan, pero la orquestacion sensible permanece mayormente en `static/js/editor_offset_visual.js`.

Superficies criticas:

- `templates/editor_offset_visual.html`
- `static/css/editor_offset_visual.css`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/*.js`
- `static/js/editor_offset_visual/core/*.js`

## Estado del backend

### Hechos confirmados

El backend activo del editor esta separado en servicios:

- `services/editor_offset_http_service.py`
- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`
- `services/editor_offset_imposition_service.py`
- `services/editor_offset_output_contract.py`
- `services/editor_offset_output_service.py`

`routes.py` sigue siendo wrapper publico y compatibilidad legacy.

## Estado de persistencia

### Hechos confirmados

La persistencia principal vive en:

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

`safe_job_id()` acepta solo tokens alfanumericos.

### Requiere verificacion

No esta definido en la auditoria que layouts historicos deben mantenerse compatibles.

## Estado de preview/PDF

### Hechos confirmados

Preview/PDF validan contrato y luego usan `services/editor_offset_output_service.py`, que delega salida a `montaje_offset_inteligente.py`.

### Inferencias

La preview es util como preview visual de imposicion, pero no equivale necesariamente a una prueba completa de PDF final CTP.

## Estado de CTP

### Hechos confirmados

CTP tiene soporte frontend y backend:

- UI en `static/js/editor_offset_visual/ctp_panel.js`.
- Validacion geometrica en `core/geometry_validation.js`.
- Salida con `ctp_config` en `services/editor_offset_output_service.py`.

### Requiere verificacion

Falta caracterizar salida final con marks, strip, texto tecnico y doble cara.

## Estado de cuadernillos

### Hechos confirmados

El simulador de cuadernillos esta aislado:

- Frontend: `static/js/editor_offset_visual/booklet_panel.js`.
- Backend: `cuadernillos/simulator.py`.
- Endpoint: `POST /editor_offset/cuadernillos/simular`.

No se confirmo que modifique `layout_constructor.json`.

## Estado de IA

### Hechos confirmados

IA operativa relacionada:

- `static/js/editor_offset_visual/ai_panel.js`
- `ai_agent/tools_repeat.py`
- `ai_agent/openai_tool_bridge.py`

### Requiere verificacion

Cobertura UI con respuesta OpenAI real.

## Estado de tests

### Hechos confirmados

Existe cobertura unitaria y Playwright para flujos principales, Step & Repeat PRO, contrato, edicion manual, drag y resize latente.

### Requiere verificacion

La auditoria fue read-only y no ejecuto tests.

## Estado de resize

Resize esta latente, no operativo. No debe declararse funcional mientras el renderer no cree handles y no exista una fase propia de validacion.

## Estado de nesting/hybrid

`nesting` y `hybrid` existen como motores alternativos conectados, pero falta validar comportamiento incompleto, cobertura UI y paridad con contrato de `repeat`.

## Funcionalidades productivas, alternativas y antiguas

Productivas:

- Editor Visual con `layout_constructor.json`.
- `repeat` backend.
- edicion manual.
- preview/PDF.

Alternativas:

- `nesting`.
- `hybrid`.
- IA Step & Repeat.
- cuadernillos como simulador aislado.

Antiguas o legacy:

- `_generate_slots_with_ai()` y `/editor_offset/auto_layout/<job_id>`.
- editor post-imposicion.
- flujos manuales/offset antiguos en `routes.py`.

## Preguntas abiertas

- Debe `auto_layout` seguir visible o documentarse como legacy?
- Que debe ocurrir si `nesting/hybrid` colocan menos formas que las solicitadas?
- Que alcance debe tener la preview frente a PDF final CTP?
