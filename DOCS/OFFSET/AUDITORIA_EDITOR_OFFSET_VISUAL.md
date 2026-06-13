# Auditoria Editor Offset Visual

Auditoria SAFE en modo lectura del Editor Offset Visual. Este documento sintetiza hallazgos confirmados por inspeccion estatica de rutas, simbolos y referencias del repositorio.

No se ejecutaron tests, no se ejecutaron scripts productivos, no se modifico codigo fuente, no se hicieron commits y no se hizo push.

## 1. Alcance real encontrado.

### Hechos confirmados

El Editor Offset Visual no esta contenido en una unica carpeta. Su superficie real incluye template HTML, CSS, entrypoint JavaScript, modulos frontend extraidos, rutas Flask, servicios backend, motores de imposicion, salida legacy compartida, simulador de cuadernillos, herramientas IA, documentacion y tests.

Rutas principales encontradas:

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/`
- `static/js/editor_offset_visual/core/`
- `static/css/editor_offset_visual.css`
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
- `tests/test_editor_offset_characterization.py`
- `tests/test_editor_offset_output_contract.py`
- `tests/test_step_repeat_pro_engine.py`
- `tests/playwright/test_editor_productive_workflows.py`
- `tests/playwright/test_editor_manual_interactions.py`
- `tests/playwright/test_editor_drag_resize_interactions.py`

### Inferencias

El mayor riesgo de regresion no esta aislado en un unico archivo, sino en las fronteras entre `state.layout`, `layout_constructor.json`, `slots[]`, servicios de salida y render final.

## 2. Mapa funcional del Editor Offset Visual.

### Hechos confirmados

El flujo productivo entra por `GET /editor_offset_visual` en `routes.py`, que delega en `services.editor_offset_http_service.editor_visual_context()` y renderiza `templates/editor_offset_visual.html`.

El template define `window.INITIAL_LAYOUT_JSON` y `window.JOB_ID`, y carga scripts clasicos en este orden:

- `static/js/editor_offset_visual/dom_refs.js`
- `static/js/editor_offset_visual/core/defaults.js`
- `static/js/editor_offset_visual/core/geometry.js`
- `static/js/editor_offset_visual/core/geometry_validation.js`
- `static/js/editor_offset_visual/renderer_canvas.js`
- `static/js/editor_offset_visual/manual_tools.js`
- `static/js/editor_offset_visual/slot_interactions.js`
- `static/js/editor_offset_visual/api_client.js`
- `static/js/editor_offset_visual/output_panel.js`
- `static/js/editor_offset_visual/ai_panel.js`
- `static/js/editor_offset_visual/ctp_panel.js`
- `static/js/editor_offset_visual/booklet_panel.js`
- `static/js/editor_offset_visual.js`

Los modulos exportan bajo `window.EditorOffsetVisual.*`; no usan imports ES module.

El entrypoint `static/js/editor_offset_visual.js` conserva:

- estado global `state`
- historial `history`
- seleccion simple y multiple
- box select
- drag/move
- resize latente
- wiring de botones
- listeners globales y temporales
- render orchestration
- save/upload/preview/PDF
- Step & Repeat manual por grilla
- integracion con paneles IA, CTP y cuadernillos

Step & Repeat tiene dos superficies distintas:

- Step & Repeat PRO automatico backend mediante `services/editor_offset_imposition_service.py` y `engines/step_repeat_pro_engine.py`.
- Step & Repeat manual frontend mediante `generateStepRepeatFromSelectedSlot()` en `static/js/editor_offset_visual.js`.

Resize esta presente como rama latente en JS/CSS, pero no operativo porque el renderer activo no crea handles.

### Inferencias

El entrypoint sigue siendo el centro de acoplamiento funcional. Los modulos extraidos reducen complejidad, pero la orquestacion sensible todavia vive mayormente en `static/js/editor_offset_visual.js`.

## 3. Archivos principales y responsabilidad de cada uno.

### Hechos confirmados

Frontend:

- `templates/editor_offset_visual.html`: estructura visual, tabs, formularios, controles, carga de scripts, `window.INITIAL_LAYOUT_JSON`, `window.JOB_ID`.
- `static/css/editor_offset_visual.css`: shell visual, canvas, tabs, slots, estados dinamicos, CTP, cuadernillos, output y responsive.
- `static/js/editor_offset_visual.js`: entrypoint compatible, estado global, wiring, listeners, render wrappers, historial, seleccion, drag, Step & Repeat UI, save, upload, preview/PDF.
- `static/js/editor_offset_visual/dom_refs.js`: mapa de IDs y helpers DOM.
- `static/js/editor_offset_visual/core/defaults.js`: defaults de motores, CTP, export, faces y metadata repeat.
- `static/js/editor_offset_visual/core/geometry.js`: geometria pura, cajas, bounds, agrupaciones por fila/columna.
- `static/js/editor_offset_visual/core/geometry_validation.js`: validacion frontend de pliego, area util, pinza CTP y solapes.
- `static/js/editor_offset_visual/renderer_canvas.js`: render de sheet, slots, guia CTP, zoom visual, distancia y panel geometrico.
- `static/js/editor_offset_visual/manual_tools.js`: operaciones manuales sobre slots seleccionados.
- `static/js/editor_offset_visual/slot_interactions.js`: seleccion, box select, drag/move y resize latente.
- `static/js/editor_offset_visual/api_client.js`: llamadas HTTP del editor.
- `static/js/editor_offset_visual/output_panel.js`: preview/PDF y errores de salida.
- `static/js/editor_offset_visual/ai_panel.js`: panel IA y aplicacion de layout pendiente.
- `static/js/editor_offset_visual/ctp_panel.js`: parametros CTP, guia, alineacion y lock.
- `static/js/editor_offset_visual/booklet_panel.js`: simulador visual de cuadernillos.

Backend:

- `routes.py`: endpoints publicos, wrappers Flask y compatibilidad legacy.
- `services/editor_offset_http_service.py`: fachada HTTP del Editor Offset Visual.
- `services/editor_offset_jobs.py`: rutas de jobs, carga y guardado de `layout_constructor.json`.
- `services/editor_offset_layout_defaults.py`: defaults y normalizacion de layout.
- `services/editor_offset_uploads.py`: upload de PDFs y metadata `designs[]`.
- `services/editor_offset_imposition_service.py`: selector y aplicador `repeat`, `nesting`, `hybrid`.
- `services/editor_offset_output_contract.py`: validacion minima antes de preview/PDF.
- `services/editor_offset_output_service.py`: transformacion de layout a posiciones manuales y generacion de preview/PDF.
- `engines/step_repeat_pro_engine.py`: motor canonico Step & Repeat PRO.
- `engines/nesting_pro_engine.py`: motor alternativo de nesting con `rectpack`.
- `montaje_offset_inteligente.py`: salida legacy compartida y wrapper compatible.
- `cuadernillos/simulator.py`: motor aislado de simulacion de cuadernillos.
- `ai_agent/tools_repeat.py` y `ai_agent/openai_tool_bridge.py`: IA operativa relacionada con Step & Repeat.

## 4. Flujo completo desde la UI hasta preview, persistencia y PDF final.

### Hechos confirmados

Flujo de entrada:

1. `GET /editor_offset_visual` en `routes.py`.
2. `editor_http.editor_visual_context()` carga o inicializa layout.
3. El layout se inyecta en `templates/editor_offset_visual.html` como `window.INITIAL_LAYOUT_JSON`.
4. `static/js/editor_offset_visual.js` inicializa `state.layout` desde ese JSON.

Flujo de edicion:

1. El usuario configura pliego, trabajos logicos, PDFs, formas, spacing, CTP, output y slots.
2. El upload llama `POST /editor_offset/upload/<job_id>` desde `api_client.uploadDesigns()`.
3. La imposicion automatica llama `POST /editor_offset_visual/apply_imposition`.
4. `services/editor_offset_imposition_service.apply_imposition_engine()` decide:
   - `repeat`: `engines.step_repeat_pro_engine.build_step_repeat_slots()`
   - `nesting`: `engines.nesting_pro_engine.compute_nesting()`
   - `hybrid`: nesting base mas repeticion del bloque
5. La edicion manual modifica `state.layout.slots`.

Flujo de persistencia:

1. Guardar llama `POST /editor_offset/save`.
2. `services/editor_offset_jobs.py` persiste en `static/constructor_offset_jobs/<job_id>/layout_constructor.json`.
3. `safe_job_id()` acepta solo tokens alfanumericos para `job_id`.

Flujo de preview/PDF:

1. `output_panel.requestPreview()` y `output_panel.requestPdf()` guardan primero el layout.
2. Preview llama `POST /editor_offset/preview/<job_id>`.
3. PDF final llama `POST /editor_offset/generar_pdf/<job_id>`.
4. `services/editor_offset_http_service.py` carga layout persistido.
5. `services.editor_offset_output_contract.validate_constructor_output_layout()` valida contrato minimo.
6. `services.editor_offset_output_service.montar_offset_desde_layout()` transforma `slots[]` en `posiciones_manual`.
7. La salida final se delega a `montaje_offset_inteligente.realizar_montaje_inteligente()`.

### Inferencias

La preview actual debe leerse como preview de imposicion visual, no como prueba contractual completa del PDF final CTP, porque la preview usa una sola cara visible y el PDF final puede concatenar frente/dorso y agregar marcas/elementos tecnicos.

## 5. Dependencias directas e indirectas.

### Hechos confirmados

Dependencias directas frontend:

- `templates/editor_offset_visual.html`
- `static/css/editor_offset_visual.css`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/*.js`
- `static/js/editor_offset_visual/core/*.js`

Dependencias directas backend:

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

Dependencias indirectas criticas:

- `montaje_offset_inteligente.py`
- `strategies/*`
- `cuadernillos/simulator.py`
- `ai_agent/tools_repeat.py`
- `ai_agent/openai_tool_bridge.py`
- `PyPDF2`
- `reportlab`
- `rectpack`

Superficies relacionadas pero no nucleo principal:

- editor post-imposicion bajo rutas como `/editor`, `/editor_chat/<job_id>`, `/layout/<job_id>/apply`
- flujos legacy de `montaje_offset_inteligente`
- manual editor
- imposicion offset automatica

### Inferencias

La convivencia de flujos legacy obliga a tratar `routes.py` y `montaje_offset_inteligente.py` como superficies compartidas, no como archivos exclusivos del Editor Offset Visual.

## 6. Relación con montaje_offset_inteligente.py.

### Hechos confirmados

`services/editor_offset_output_service.py` no renderiza el PDF final de forma totalmente autonoma. Resuelve `Diseno`, `MontajeConfig` y `realizar_montaje_inteligente` desde `montaje_offset_inteligente.py`.

`services.editor_offset_output_service.montar_offset_desde_layout()`:

- lee `layout_data`
- construye `disenos` desde `designs[]`
- separa posiciones `front` y `back`
- transforma `slots[]` a `posiciones_manual`
- crea `MontajeConfig`
- llama `realizar_montaje_inteligente()`
- concatena frente/dorso cuando ambas caras existen

`montaje_offset_inteligente.py` conserva tambien `montar_offset_desde_layout()` como wrapper compatible hacia el servicio extraido.

### Inferencias

`montaje_offset_inteligente.py` funciona como capa legacy productiva compartida. Cualquier refactor sobre este archivo requiere validar no solo Editor Offset Visual, sino otros flujos offset existentes.

## 7. Contratos y estructuras de datos relevantes.

### Hechos confirmados

Persistencia principal:

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

Campos canonicos del layout:

- `sheet_mm`
- `margins_mm`
- `bleed_default_mm`
- `gap_default_mm`
- `works`
- `designs`
- `slots`
- `export_settings`
- `design_export`
- `faces`
- `active_face`
- `imposition_engine`
- `allowed_engines`
- `spacingSettings`
- `snapSettings`
- `ctp`

Contrato `designs[]`:

- `ref`
- `filename`
- `work_id`
- `width_mm`
- `height_mm`
- `bleed_mm`
- `allow_rotation`
- `forms_per_plate`
- `priority`
- `preferred_zone`
- `preferred_flow`
- `repeat_role`
- `repeat_manual_overrides`

Contrato `slots[]`:

- `id`
- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`
- `rotation_deg`
- `logical_work_id`
- `bleed_mm`
- `crop_marks`
- `locked`
- `design_ref`
- `face`
- `slot_box_final`

`services/editor_offset_output_contract.py` valida:

- `designs[].ref` requerido y unico
- `slots[].id` requerido y unico
- `x_mm`, `y_mm`, `w_mm`, `h_mm`, `bleed_mm`, `rotation_deg` numericos finitos
- `w_mm` y `h_mm` mayores que cero
- `slot.design_ref` existente en `designs[].ref`
- `face` solo `front` o `back`
- `logical_work_id` no resuelto como warning
- `faces` contiene `back` sin slots `back` como warning

### Inferencias

La semantica de `design.width_mm` y `design.height_mm` no esta completamente limpia: en algunos caminos parece representar trim y en otros caja final con bleed. Esta ambiguedad esta ligada al riesgo de doble conteo de bleed.

## 8. Riesgos y puntos frágiles.

### Hechos confirmados

Riesgos altos:

- `static/js/editor_offset_visual.js` concentra estado global, listeners, historial, render orchestration y flujos productivos.
- Renombrar IDs o `data-*` criticos puede romper listeners: `btn-*`, `slot-*`, `ctp-*`, `data-editor-tab`, `data-editor-tab-panel`, `sheet`, `sheet-canvas`.
- Tocar `renderSheet`, seleccion, drag, `layoutToJson`, save, preview o PDF afecta varias superficies a la vez.
- PDFs fisicos faltantes no bloquean contrato de salida: `_build_designs()` ignora archivos inexistentes y si no hay `disenos` puede devolver rutas esperadas sin garantizar que existan.

Riesgos medios o medio-altos:

- `nesting` y `hybrid` no muestran por lectura una validacion equivalente a `IncompleteImpositionError` de `repeat`.
- Upload puede sobrescribir PDFs con el mismo nombre dentro del mismo job.
- Preview no representa completamente PDF final con doble cara y CTP.
- Resize esta latente y no debe considerarse operativo.
- Hay controles visibles sin efecto confirmado en Step & Repeat manual.
- Hay codigo inalcanzable dentro del entrypoint que puede inducir futuras correcciones en el bloque equivocado.

### Inferencias

El mayor riesgo de regresion esta en la frontera UI/estado/persistencia/salida, no en el motor `repeat` aislado, que tiene mejor cobertura.

## 9. Código legado, duplicado o posiblemente huérfano.

### Hechos confirmados

Frontend:

- `renderSheet()` en `static/js/editor_offset_visual.js` delega al renderer y conserva codigo inalcanzable despues de un `return`.
- `renderCtpGuideOverlay()` conserva tambien una rama legacy inalcanzable.
- Existen wrappers locales que delegan a modulos extraidos.
- `aiResultLayout` y `aiResultChangeType` aparecen como variables declaradas sin uso posterior confirmado.
- El renderer activo no crea handles de resize, aunque CSS y ramas JS para `.handle` existen.

UI:

- `sr-offset-x`
- `sr-offset-y`
- `sr-top-margin`
- `sr-bottom-margin`
- `sr-left-margin`
- `sr-right-margin`

Estos controles existen en HTML, pero no se confirmo lectura por `generateStepRepeatFromSelectedSlot()`.

Backend:

- `routes.py` conserva wrappers hacia `step_repeat_pro_engine`.
- `_generate_slots_with_ai()` sigue conectado a `/editor_offset/auto_layout/<job_id>`, pero es un flujo distinto del `apply_imposition` actual.
- Flujos legacy de offset conviven en `routes.py`, `montaje_offset_inteligente.py`, editor post-imposicion, manual editor e imposicion automatica.

### Inferencias

No se detectaron modulos JS huerfanos en disco dentro de `static/js/editor_offset_visual/**/*.js`; todos estan cargados por el template. La deuda principal parece estar dentro del entrypoint y en controles UI parcialmente desconectados.

## 10. Tests existentes y vacíos de cobertura.

### Hechos confirmados

Tests existentes leidos, no ejecutados:

- `tests/test_editor_offset_characterization.py`
- `tests/test_editor_offset_output_contract.py`
- `tests/test_step_repeat_pro_engine.py`
- `tests/test_editor_advisor_tools.py`
- `tests/test_cuadernillos_simulator.py`
- `tests/playwright/test_editor_load.py`
- `tests/playwright/test_editor_productive_workflows.py`
- `tests/playwright/test_editor_manual_interactions.py`
- `tests/playwright/test_editor_drag_resize_interactions.py`

Cobertura detectada:

- defaults y guardado
- upload desde work
- `apply_imposition` con `repeat`
- bloqueo preview/PDF por contrato invalido
- IA repeat alineada con motor canonico
- salida frente/dorso con CTP
- motor Step & Repeat PRO: formas exactas, spacing, zonas, fill, colisiones, rotacion, error incompleto
- contrato de salida
- Playwright: tabs, zoom, caras, geometria, guardar, Step & Repeat UI, undo, upload, imposicion, preview, PDF
- seleccion, duplicado, borrado, agrupar/desagrupar, nudge, align, distribute, box select
- drag simple, drag grupal, spacing live y resize latente

Vacios de cobertura:

- `nesting` y `hybrid` desde UI con equivalencia a `repeat`
- validacion de PDFs fisicos faltantes
- precedencia completa de `slot.export_overrides`, `design_export` y `export_settings`
- paridad canvas-preview-PDF para rotaciones manuales
- CTP marks, strip y texto tecnico en salida final
- doble cara en preview vs PDF final
- `vector_hybrid`
- IA OpenAI real desde UI
- migracion/compatibilidad de layouts historicos en `static/constructor_offset_jobs/**`

### Inferencias

La cobertura existente protege bastante bien `repeat`, contrato minimo y workflows productivos principales. Falta cobertura en motores alternativos, salida CTP fiel y escenarios de persistencia fisica.

## 11. Preguntas abiertas que requieren verificación.

- Debe `design.width_mm` y `design.height_mm` representar trim, media box del PDF o caja final con bleed?
- El contrato debe bloquear preview/PDF si `design.filename` no existe fisicamente?
- `nesting` y `hybrid` deben fallar si no colocan todas las formas solicitadas?
- La preview debe representar solo imposicion visual o debe ser una prueba fiel del PDF final CTP?
- Los controles `sr-offset-*` y margenes SR son placeholders, deuda funcional o deben eliminarse de UI?
- Se debe evitar sobrescritura de PDFs con el mismo nombre dentro del mismo job?
- Se debe exponer centrado horizontal/vertical por separado, dado que existen listeners opcionales pero no botones?
- `vector_hybrid` esta listo como contrato operativo o solo reservado como opcion futura?
- Que layouts historicos bajo `static/constructor_offset_jobs/**` deben considerarse compatibles?

## 12. Próximo plan SAFE recomendado, sin editar archivos.

### Fase 1: Congelar contratos criticos

Sin modificar comportamiento, agregar o revisar caracterizacion para:

- dimensiones `designs[]` y `slots[]`
- `has_bleed=True/False`
- archivo PDF faltante
- `slot_box_final`
- `forms_per_plate`
- `face front/back`
- CTP basico
- preview vs PDF final

### Fase 2: Matriz UI y controles

Crear una matriz de lectura que clasifique:

- controles conectados
- controles visibles sin efecto confirmado
- listeners opcionales sin DOM
- copy desalineado con flujo real
- superficies criticas que no deben renombrarse

### Fase 3: Matriz entrypoint vs modulos

Documentar:

- responsabilidades aun en `static/js/editor_offset_visual.js`
- wrappers que solo delegan
- codigo inalcanzable
- funciones potencialmente huerfanas
- candidatos a extraccion futura

### Fase 4: Auditoria de salida y preprensa

Caracterizar sin cambiar comportamiento:

- existencia fisica de PDFs
- precedencia de bleed/crop/export
- doble cara
- CTP marks/texto tecnico
- paridad canvas-preview-PDF
- `vector_hybrid`

### Fase 5: Plan de implementacion posterior

Solo despues de las fases anteriores, proponer cambios pequenos y reversibles. Orden recomendado:

1. robustecer contrato/persistencia de salida
2. aclarar o corregir deuda UI desconectada
3. limpiar codigo inalcanzable con cobertura previa
4. cubrir `nesting`/`hybrid`
5. tratar resize como fase independiente, no como limpieza incidental

Este plan no autoriza implementacion directa; solo define una ruta SAFE para una fase futura.
