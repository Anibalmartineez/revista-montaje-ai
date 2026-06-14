# Mapa Editor Offset Visual

Fuente principal: `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`.

Este documento es el mapa operativo principal del Editor Offset Visual. Debe consultarse antes de tocar frontend, backend, motores, persistencia, preview/PDF, CTP, cuadernillos o IA relacionada.

## Proposito

### Hechos confirmados

El Editor Offset Visual es el flujo visual principal para construir un montaje offset por job. Permite cargar o crear un `layout_constructor.json`, configurar pliego, trabajos logicos, PDFs, formas, bleed, spacing y CTP, aplicar motores de imposicion, editar slots manualmente, guardar el layout, generar preview y generar PDF final.

### Inferencias

El editor funciona como puente entre una UI tipo CAD/preprensa y la salida productiva legacy basada en `montaje_offset_inteligente.py`.

## Alcance real encontrado

### Hechos confirmados

El editor no vive en una sola carpeta. Su alcance real incluye:

- `templates/editor_offset_visual.html`
- `static/css/editor_offset_visual.css`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/`
- `static/js/editor_offset_visual/core/`
- `routes.py`
- `services/editor_offset_http_service.py`
- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`
- `services/editor_offset_imposition_service.py`
- `services/editor_offset_output_contract.py`
- `services/editor_offset_output_service.py`
- `engines/step_repeat_pro_engine.py`
- `engines/nesting_pro_engine.py`
- `montaje_offset_inteligente.py`
- `cuadernillos/simulator.py`
- `ai_agent/tools_repeat.py`
- `ai_agent/openai_tool_bridge.py`
- tests unitarios y Playwright relacionados.

## Archivos principales

### HTML/template

- `templates/editor_offset_visual.html`: estructura visual, tabs, formularios, controles, carga de scripts, `window.INITIAL_LAYOUT_JSON` y `window.JOB_ID`.

### CSS

- `static/css/editor_offset_visual.css`: estilos del shell, canvas, slots, estados dinamicos, CTP, cuadernillos, output y responsive.

### JavaScript principal

- `static/js/editor_offset_visual.js`: entrypoint compatible. Conserva estado global, wiring, listeners, history, seleccion, drag, Step & Repeat manual, save, upload, preview/PDF y orquestacion de paneles.

### Modulos JavaScript extraidos

- `static/js/editor_offset_visual/dom_refs.js`: IDs y helpers DOM.
- `static/js/editor_offset_visual/core/defaults.js`: defaults y normalizadores.
- `static/js/editor_offset_visual/core/geometry.js`: geometria pura.
- `static/js/editor_offset_visual/core/geometry_validation.js`: validacion geometrica frontend.
- `static/js/editor_offset_visual/renderer_canvas.js`: render del sheet, slots, guia CTP, zoom visual y panel geometrico.
- `static/js/editor_offset_visual/manual_tools.js`: operaciones manuales sobre slots seleccionados.
- `static/js/editor_offset_visual/slot_interactions.js`: seleccion, box select, drag/move y resize latente.
- `static/js/editor_offset_visual/api_client.js`: llamadas HTTP.
- `static/js/editor_offset_visual/output_panel.js`: preview/PDF.
- `static/js/editor_offset_visual/ai_panel.js`: panel IA.
- `static/js/editor_offset_visual/ctp_panel.js`: panel CTP.
- `static/js/editor_offset_visual/booklet_panel.js`: panel de cuadernillos.

### Backend Flask

- `routes.py`: expone las rutas publicas y conserva wrappers legacy.

### Servicios

- `services/editor_offset_http_service.py`: fachada HTTP del editor.
- `services/editor_offset_jobs.py`: rutas de jobs y persistencia.
- `services/editor_offset_layout_defaults.py`: defaults y normalizacion.
- `services/editor_offset_uploads.py`: upload de PDFs y `designs[]`.
- `services/editor_offset_imposition_service.py`: seleccion `repeat`, `nesting`, `hybrid`.
- `services/editor_offset_output_contract.py`: validacion minima antes de salida.
- `services/editor_offset_output_service.py`: conversion de layout a preview/PDF.

### Motores de imposicion

- `engines/step_repeat_pro_engine.py`: motor canonico Step & Repeat PRO.
- `engines/nesting_pro_engine.py`: motor alternativo de nesting.

### Persistencia

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`: ubicacion principal del layout del Editor Offset Visual.

### Preview/PDF

- `services/editor_offset_output_service.py`: transforma `slots[]` a `posiciones_manual`.
- `montaje_offset_inteligente.py`: render/salida legacy compartida.

### CTP

- Frontend: `static/js/editor_offset_visual/ctp_panel.js` y validacion en `core/geometry_validation.js`.
- Backend/salida: `services/editor_offset_output_service.py` pasa `ctp_config` y pinza al render legacy.

### Cuadernillos

- Frontend: `static/js/editor_offset_visual/booklet_panel.js`.
- Backend: `cuadernillos/simulator.py`.
- Endpoint: `POST /editor_offset/cuadernillos/simular`.

### IA

- Frontend: `static/js/editor_offset_visual/ai_panel.js`.
- Backend operativo: `ai_agent/tools_repeat.py`, `ai_agent/openai_tool_bridge.py`.

### Tests

- `tests/test_editor_offset_characterization.py`
- `tests/test_editor_offset_output_contract.py`
- `tests/test_step_repeat_pro_engine.py`
- `tests/test_cuadernillos_simulator.py`
- `tests/playwright/test_editor_load.py`
- `tests/playwright/test_editor_productive_workflows.py`
- `tests/playwright/test_editor_manual_interactions.py`
- `tests/playwright/test_editor_drag_resize_interactions.py`

## Flujo general del editor

### Hechos confirmados

1. Entrada por `GET /editor_offset_visual` en `routes.py`.
2. `services.editor_offset_http_service.editor_visual_context()` carga o crea layout.
3. `templates/editor_offset_visual.html` inyecta `INITIAL_LAYOUT_JSON` y `JOB_ID`.
4. `static/js/editor_offset_visual.js` inicializa `state.layout`.
5. La UI permite configurar pliego, trabajos, disenos, slots, spacing, export y CTP.
6. Upload llama `POST /editor_offset/upload/<job_id>`.
7. Apply imposition llama `POST /editor_offset_visual/apply_imposition`.
8. Edicion manual modifica `state.layout.slots`.
9. Save llama `POST /editor_offset/save`.
10. Preview guarda primero y luego llama `POST /editor_offset/preview/<job_id>`.
11. PDF final guarda primero y luego llama `POST /editor_offset/generar_pdf/<job_id>`.

## Relaciones principales

### Hechos confirmados

- `templates/editor_offset_visual.html` define DOM, controles y carga scripts.
- `static/js/editor_offset_visual.js` consume el DOM y coordina modulos.
- `static/js/editor_offset_visual/` contiene modulos auxiliares exportados por `window.EditorOffsetVisual.*`.
- `services/editor_offset_*.py` concentra jobs, defaults, uploads, imposicion, contrato y salida.
- `engines/step_repeat_pro_engine.py` es el motor principal de `repeat`.
- `engines/nesting_pro_engine.py` alimenta `nesting` y `hybrid`.
- `montaje_offset_inteligente.py` sigue siendo la salida legacy compartida para preview/PDF.

## Step & Repeat PRO backend vs Step & Repeat manual frontend

### Hechos confirmados

Step & Repeat PRO backend:

- Entra por `POST /editor_offset_visual/apply_imposition`.
- Usa `services/editor_offset_imposition_service.py`.
- Para `repeat`, llama `engines.step_repeat_pro_engine.build_step_repeat_slots()`.
- Valida formas incompletas mediante `IncompleteImpositionError`.

Step & Repeat manual frontend:

- Vive en `generateStepRepeatFromSelectedSlot()` dentro de `static/js/editor_offset_visual.js`.
- Clona desde el slot maestro seleccionado.
- No llama al motor canonico backend.

### Inferencias

Estas dos superficies pueden divergir semanticamente. Conviene tratarlas como funcionalidades distintas en documentacion, tests y UI.

## Dependencias directas e indirectas

### Hechos confirmados

Directas:

- HTML, CSS, entrypoint JS y modulos JS del editor.
- `routes.py` y servicios `editor_offset_*`.
- `engines/step_repeat_pro_engine.py`.
- `engines/nesting_pro_engine.py`.

Indirectas:

- `montaje_offset_inteligente.py`
- `strategies/*`
- `cuadernillos/simulator.py`
- `ai_agent/tools_repeat.py`
- `ai_agent/openai_tool_bridge.py`
- `PyPDF2`
- `reportlab`
- `rectpack`

## Superficies compartidas o legacy

### Hechos confirmados

No tocar sin revision:

- `routes.py`
- `montaje_offset_inteligente.py`
- `strategies/*`
- contratos de `layout_constructor.json`
- endpoints publicos del editor
- IDs y `data-*` criticos del template
- `static/js/editor_offset_visual.js`

### Inferencias

`routes.py` y `montaje_offset_inteligente.py` no son propiedad exclusiva del Editor Offset Visual. Cambios alli pueden afectar flujos legacy.

## Preguntas abiertas

- Que layouts historicos bajo `static/constructor_offset_jobs/**` deben seguir siendo compatibles?
- Debe el Step & Repeat manual frontend alinearse semanticamente con el Step & Repeat PRO backend?
- Debe preview representar solo montaje visual o salida final CTP fiel?
