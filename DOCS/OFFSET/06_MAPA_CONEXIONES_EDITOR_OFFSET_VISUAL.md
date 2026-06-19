# 06 - Mapa de conexiones del Editor Offset Visual

Documento de referencia SAFE para entender las conexiones internas del Editor Offset Visual y planificar futuras funcionalidades sin romper el flujo actual.

Este documento fue construido por lectura de archivos del repositorio. No implica cambios de codigo, ejecucion de tests ni ejecucion de scripts productivos.

---

## 1. Alcance real del mapa de conexiones

### Hechos confirmados

El Editor Offset Visual no vive en un unico archivo. Su superficie directa e indirecta incluye frontend, rutas Flask, servicios, motores, salida productiva legacy, IA, cuadernillos y tests.

Nucleo principal:

| Area | Archivos/carpetas | Responsabilidad |
| --- | --- | --- |
| Template | `templates/editor_offset_visual.html` | Estructura HTML, paneles, formularios, tabs, IDs, `data-*`, variables globales iniciales y carga de scripts. |
| CSS | `static/css/editor_offset_visual.css` | Layout visual, hoja, slots, estados visuales, CTP, output, responsive y estilos latentes de resize. |
| Entrypoint JS | `static/js/editor_offset_visual.js` | Estado global, wiring, listeners, render orchestration, historial, seleccion, drag, guardado, upload, preview, PDF, Step & Repeat manual y paneles. |
| Modulos JS | `static/js/editor_offset_visual/` | DOM refs, renderer, herramientas manuales, interacciones de slots, cliente API, panel output, IA, CTP y cuadernillos. |
| Core JS | `static/js/editor_offset_visual/core/` | Defaults, geometria y validacion geometrica desacoplada del DOM. |

Dependencias directas backend:

| Area | Archivos/carpetas | Responsabilidad |
| --- | --- | --- |
| Rutas | `routes.py` | Rutas publicas, wrappers Flask y delegacion a servicios del editor. |
| Fachada HTTP | `services/editor_offset_http_service.py` | Orquestacion HTTP del editor visual. |
| Jobs | `services/editor_offset_jobs.py` | Persistencia de jobs en `static/constructor_offset_jobs/<job_id>/layout_constructor.json`. |
| Defaults | `services/editor_offset_layout_defaults.py` | Defaults y normalizacion inicial de layout. |
| Uploads | `services/editor_offset_uploads.py` | Carga de PDFs y metadata en `designs[]`. |
| Imposicion | `services/editor_offset_imposition_service.py` | Seleccion y aplicacion de motores `repeat`, `nesting`, `hybrid`. |
| Contrato output | `services/editor_offset_output_contract.py` | Validacion minima antes de preview/PDF. |
| Servicio output | `services/editor_offset_output_service.py` | Transformacion del layout a posiciones productivas y delegacion a salida final. |

Dependencias indirectas:

| Area | Archivos/carpetas | Responsabilidad |
| --- | --- | --- |
| Motor repeat | `engines/step_repeat_pro_engine.py` | Motor canonico Step & Repeat PRO backend. |
| Motor nesting | `engines/nesting_pro_engine.py` | Motor alternativo para nesting. |
| Cuadernillos | `cuadernillos/simulator.py` | Simulacion visual de cuadernillos. |
| IA repeat | `ai_agent/tools_repeat.py` | Herramientas IA que reutilizan `build_step_repeat_slots()`. |
| Bridge OpenAI | `ai_agent/openai_tool_bridge.py` | Puente de acciones IA para Step & Repeat. |
| Advisor IA | `ai_agent/editor_advisor/` | Asistente SAFE de lectura/analisis sobre el editor. |

Legacy compartido y salida productiva:

| Area | Archivos/carpetas | Responsabilidad |
| --- | --- | --- |
| Salida productiva | `montaje_offset_inteligente.py` | Generacion legacy/productiva de preview y PDF final. |
| Estrategias | `strategies/` | Estrategias de montaje usadas por la salida productiva. |

Tests relacionados:

| Area | Archivos |
| --- | --- |
| Caracterizacion | `tests/test_editor_offset_characterization.py` |
| Contrato output | `tests/test_editor_offset_output_contract.py` |
| Motor repeat | `tests/test_step_repeat_pro_engine.py` |
| IA | `tests/test_editor_advisor_tools.py` |
| Cuadernillos | `tests/test_cuadernillos_simulator.py` |
| Playwright carga | `tests/playwright/test_editor_load.py` |
| Playwright flujos productivos | `tests/playwright/test_editor_productive_workflows.py` |
| Playwright interacciones manuales | `tests/playwright/test_editor_manual_interactions.py` |
| Playwright drag/resize | `tests/playwright/test_editor_drag_resize_interactions.py` |

Documentacion base:

| Archivo | Uso |
| --- | --- |
| `AGENTS.md` | Reglas operativas del repositorio. |
| `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md` | Evidencia original de auditoria SAFE. |
| `DOCS/OFFSET/01_MAPA_EDITOR_OFFSET_VISUAL.md` | Mapa principal del sistema. |
| `DOCS/OFFSET/02_ESTADO_EDITOR_OFFSET_VISUAL.md` | Estado actual, partes operativas, latentes y legacy. |
| `DOCS/OFFSET/03_RIESGOS_Y_DEUDA_EDITOR_OFFSET_VISUAL.md` | Riesgos y deuda tecnica. |
| `DOCS/OFFSET/04_PLAN_SAFE_EDITOR_OFFSET_VISUAL.md` | Ruta futura de trabajo por fases. |
| `DOCS/OFFSET/05_CONTRATOS_EDITOR_OFFSET_VISUAL.md` | Contratos de datos y reglas criticas. |

### Inferencias

El editor debe tratarse como una superficie integrada. Cambios aparentemente locales en HTML, IDs, seleccion, `slots[]`, `rotation_deg`, bleed, CTP o preview pueden afectar persistencia, salida final, tests Playwright y compatibilidad legacy.

---

## 2. Mapa frontend

### Hechos confirmados

`templates/editor_offset_visual.html` inyecta:

| Simbolo | Uso |
| --- | --- |
| `window.INITIAL_LAYOUT_JSON` | Layout inicial serializado desde backend. |
| `window.JOB_ID` | Identificador del job activo. |

Orden real de carga de scripts:

1. `static/js/editor_offset_visual/dom_refs.js`
2. `static/js/editor_offset_visual/core/defaults.js`
3. `static/js/editor_offset_visual/core/geometry.js`
4. `static/js/editor_offset_visual/core/geometry_validation.js`
5. `static/js/editor_offset_visual/renderer_canvas.js`
6. `static/js/editor_offset_visual/manual_tools.js`
7. `static/js/editor_offset_visual/slot_interactions.js`
8. `static/js/editor_offset_visual/api_client.js`
9. `static/js/editor_offset_visual/output_panel.js`
10. `static/js/editor_offset_visual/ai_panel.js`
11. `static/js/editor_offset_visual/ctp_panel.js`
12. `static/js/editor_offset_visual/booklet_panel.js`
13. `static/js/editor_offset_visual.js`

Los modulos exponen API bajo `window.EditorOffsetVisual.*`.

| Archivo | Export / simbolos principales | Conexiones |
| --- | --- | --- |
| `static/js/editor_offset_visual/dom_refs.js` | `window.EditorOffsetVisual.domRefs` | Centraliza referencias a IDs como `sheet`, `sheet-canvas`, `works-list`, `designs-list`, `preview-image`, `pdf-output`, `slot-form`, `slot-none`, `upload-form`, `geometry-validation-summary`, `geometry-validation-list`. |
| `static/js/editor_offset_visual/core/defaults.js` | defaults y normalizadores | Usado por el entrypoint para `imposition_engine`, CTP, export, faces y defaults de diseno. |
| `static/js/editor_offset_visual/core/geometry.js` | conversion mm/px, cajas, bounds | Usado por renderer, validacion, seleccion, drag y herramientas manuales. |
| `static/js/editor_offset_visual/core/geometry_validation.js` | validacion geometrica | Revisa limites de hoja, area util, pinza CTP y overlaps por cara. |
| `static/js/editor_offset_visual/renderer_canvas.js` | `renderSheetSurface()` | Renderiza `.slot`, overlays, guias CTP, warnings/errores y estado visual. |
| `static/js/editor_offset_visual/manual_tools.js` | duplicate/delete/group/align/distribute/center/nudge/spacing | Operaciones manuales sobre slots seleccionados. |
| `static/js/editor_offset_visual/slot_interactions.js` | seleccion, box select, drag, resize latente | Maneja interacciones directas sobre slots y hoja. |
| `static/js/editor_offset_visual/api_client.js` | save/upload/imposition/preview/pdf/IA/cuadernillos | Encapsula llamadas HTTP del frontend. |
| `static/js/editor_offset_visual/output_panel.js` | preview/PDF panel | Valida geometria, guarda y pide preview/PDF. |
| `static/js/editor_offset_visual/ai_panel.js` | panel IA | Ejecuta IA, mantiene layout pendiente y aplica cambios al estado. |
| `static/js/editor_offset_visual/ctp_panel.js` | panel CTP | Lee/escribe `layout.ctp`, alinea frente y puede bloquear slots. |
| `static/js/editor_offset_visual/booklet_panel.js` | panel cuadernillos | Simula cuadernillos sin modificar montaje ni generar PDF. |
| `static/js/editor_offset_visual.js` | entrypoint | Inicializa estado, listeners, paneles, historial, render y persistencia. |

Interacciones y archivo responsable:

| Funcionalidad | Archivo responsable principal | Simbolos/IDs relevantes |
| --- | --- | --- |
| Inicializacion | `static/js/editor_offset_visual.js` | `parseInitialLayout()`, `state.layout`, `window.INITIAL_LAYOUT_JSON`, `window.JOB_ID`. |
| Referencias DOM | `static/js/editor_offset_visual/dom_refs.js` | `domRefs`, IDs `sheet`, `sheet-canvas`, `slot-form`. |
| Render de hoja/slots | `static/js/editor_offset_visual/renderer_canvas.js` + wrapper en entrypoint | `renderSheetSurface()`, `.slot`, `.selected`, `.locked`, `.geometry-error`, `.geometry-warning`. |
| Tabs | `templates/editor_offset_visual.html` + entrypoint | `data-editor-tab`, `data-editor-tab-panel`. |
| Seleccion simple | `slot_interactions.js` + entrypoint | `selectSlot()`, `state.selectedSlot`, `state.selectedSlots`. |
| Seleccion multiple | `slot_interactions.js` + entrypoint | `getSelectedSlotIds()`, `getSelectedSlots()`, `selectedSlots`. |
| Box select | `slot_interactions.js` | `.box-selection-rect`, calculo de interseccion con slots visibles. |
| Drag | `slot_interactions.js` | movimiento en mm, snap/grid segun contexto. |
| Resize | `slot_interactions.js`, CSS, entrypoint | Latente; el renderer activo no crea handles operativos. |
| Edicion de slot | `static/js/editor_offset_visual.js` | `renderSlotForm()`, `applySlotForm()`, IDs `slot-x`, `slot-y`, `slot-w`, `slot-h`, `slot-rot`, `slot-bleed`, `slot-crop`, `slot-locked`, `slot-work`, `slot-design`. |
| Herramientas manuales | `manual_tools.js` + wrappers entrypoint | duplicar, borrar, alinear, distribuir, centrar, nudges, spacing. |
| Output panel | `output_panel.js` + `api_client.js` | `requestPreview()`, `requestPdf()`, `saveLayout()`. |
| Panel IA | `ai_panel.js` + `api_client.js` | `runAi()`, `setLayout()`, `refreshEditorAfterLayoutReplace()`. |
| Panel CTP | `ctp_panel.js` | `layout.ctp`, overlays, alineacion frontal. |
| Panel cuadernillos | `booklet_panel.js` | `simulateBooklet()`. |

### Inferencias

`static/js/editor_offset_visual.js` es la zona de mayor acoplamiento frontend. Aunque ya hay modulos extraidos, el entrypoint sigue coordinando demasiadas responsabilidades y debe tocarse en pasos pequenos.

---

## 3. Mapa backend

### Hechos confirmados

`routes.py` delega la mayor parte de la logica a servicios extraidos:

| Ruta | Metodo | Archivo responsable | Servicio/funcion llamada | Payload confirmado | Respuesta confirmada | Riesgos |
| --- | --- | --- | --- | --- | --- | --- |
| `/editor_offset_visual` | GET | `routes.py` | `editor_http.editor_visual_context(request.args.get("job_id"))` | Query opcional `job_id` | Render de `templates/editor_offset_visual.html` con `job_id`, `layout_json`, `job_dir`. | Cambios en contexto rompen inyeccion de `window.INITIAL_LAYOUT_JSON`/`window.JOB_ID`. |
| `/editor_offset/save` | POST | `routes.py` | `editor_http.save_constructor_layout_from_payload()` | Form/JSON con `job_id`, `layout_json`. | JSON de guardado. | Payload mal serializado rompe persistencia. |
| `/editor_offset/upload/<job_id>` | POST | `routes.py` | `editor_http.upload_editor_designs()` | FormData con `files` y `work_id`. | JSON con layout actualizado/disenos. | Sobrescritura por filename y metadata PDF ambigua. |
| `/editor_offset/auto_layout/<job_id>` | POST | `routes.py` | `editor_http.generate_auto_layout(..., _generate_slots_with_ai)` | JSON con `layout_json`. | JSON con layout/slots. | Flujo legacy o alternativo frente a motor canonico. |
| `/editor_offset_visual/apply_imposition` | POST | `routes.py` | `editor_http.apply_imposition()` | FormData `job_id`, `selected_engine`, `layout_json`. | JSON con layout persistido y slots generados. | `repeat`, `nesting`, `hybrid` no tienen misma madurez/cobertura. |
| `/editor_offset/preview/<job_id>` | POST | `routes.py` | `editor_http.generate_preview()` | Job en URL; layout persistido en disco. | JSON con URL estatica de preview o 422 si contrato falla. | Preview no debe asumirse identico al PDF final. |
| `/editor_offset/generar_pdf/<job_id>` | POST | `routes.py` | `editor_http.generate_pdf()` | Job en URL; layout persistido en disco. | JSON con URL estatica de PDF o 422 si contrato falla. | Cambios impactan salida productiva legacy. |
| `/editor_offset/cuadernillos/simular` | POST | `routes.py` | `editor_http.simulate_cuadernillo()` | JSON de simulacion. | JSON de simulacion. | Es visual/simulador, no salida productiva. |
| `/ai/step_repeat_action_openai` | POST | `routes.py` | `run_openai_step_repeat_assistant()` | JSON `prompt`, `layout_json`. | JSON con respuesta IA/layout sugerido. | No persiste automaticamente; requiere guardrails. |

Servicios backend:

| Archivo | Funciones/simbolos | Conexiones |
| --- | --- | --- |
| `services/editor_offset_http_service.py` | `EditorHttpResult`, `editor_visual_context()`, `save_constructor_layout_from_payload()`, `upload_editor_designs()`, `apply_imposition()`, `generate_preview()`, `generate_pdf()` | Fachada HTTP principal. |
| `services/editor_offset_jobs.py` | `safe_job_id()`, `constructor_root()`, `job_dir()`, `load_layout()`, `save_layout()`, `layout_path()` | Maneja `static/constructor_offset_jobs/<job_id>/layout_constructor.json`. |
| `services/editor_offset_layout_defaults.py` | `default_constructor_layout()`, normalizadores | Define estructura base del layout. |
| `services/editor_offset_uploads.py` | `append_uploaded_designs()` | Guarda PDFs, lee dimensiones con `PdfReader`, agrega entradas en `designs[]`. |
| `services/editor_offset_imposition_service.py` | `select_imposition_engine()`, `apply_imposition_engine()`, `repeat_pattern_over_sheet()`, `slots_from_nesting_result()` | Orquesta motores `repeat`, `nesting`, `hybrid`. |
| `services/editor_offset_output_contract.py` | `validate_constructor_output_layout()` | Valida layout antes de preview/PDF. |
| `services/editor_offset_output_service.py` | `montar_offset_desde_layout()`, `_build_designs()`, `_positions_for_face()` | Convierte layout a `MontajeConfig` y `posiciones_manual`. |

### Inferencias

La fachada `services/editor_offset_http_service.py` es el punto mas seguro para entender los flujos HTTP antes de cambiar rutas. `routes.py` debe mantenerse como capa delgada siempre que sea posible.

---

## 4. Estado y persistencia

### Hechos confirmados

Flujo de estado:

1. Backend carga o inicializa layout.
2. `templates/editor_offset_visual.html` inyecta `window.INITIAL_LAYOUT_JSON` y `window.JOB_ID`.
3. `static/js/editor_offset_visual.js` ejecuta `parseInitialLayout()`.
4. El estado vivo queda en `state.layout`.
5. La UI modifica `state.layout`.
6. `layoutToJson()` sincroniza defaults y settings antes de serializar.
7. `saveLayout()` envia `job_id` y `layout_json` a `/editor_offset/save`.
8. Backend persiste `layout_constructor.json` en `static/constructor_offset_jobs/<job_id>/`.
9. Preview/PDF leen el layout persistido y validan contrato.

Campos de contrato relevantes:

| Campo | Vive en frontend | Se persiste | Llega a preview/PDF | Notas |
| --- | --- | --- | --- | --- |
| `sheet_mm` | Si | Si | Si | Usado para hoja y salida. |
| `margins_mm` | Si | Si | Si | Afecta validacion/area util. |
| `bleed_default_mm` | Si | Si | Si | Precedencia con diseno/slot/export requiere cuidado. |
| `gap_default_mm` | Si | Si | Indirecto | Usado por imposicion/spacing. |
| `works[]` | Si | Si | Indirecto | Puede referenciarse desde slots/disenos. |
| `designs[]` | Si | Si | Si | `ref`, `filename`, dimensiones, bleed, `allow_rotation`, preferencias. |
| `slots[]` | Si | Si | Si | Superficie critica: coordenadas, tamano, `rotation_deg`, `face`, `design_ref`. |
| `faces` | Si | Si | Si | Debe contener `front`/`back`. |
| `active_face` | Si | Si | Parcial | Controla UI; salida filtra por `face`. |
| `spacingSettings` | Si | Si | Parcial/indirecto | Usado en UI/herramientas. |
| `snapSettings` | Si | Si | No confirmado directo | Usado en interacciones frontend. |
| `ctp` | Si | Si | Si/indirecto | Afecta guias/validacion y salida segun flujo. |
| `export_settings` | Si | Si | Si | Configuracion global de salida. |
| `design_export` | Si | Si | Si | Overrides por diseno. |
| `imposition_engine` | Si | Si | Si | Define estrategia de salida. |
| `allowed_engines` | Si | Si | No directo | Control de motores disponibles. |

Contrato `slots[]` confirmado por documentacion y validacion:

| Campo | Regla |
| --- | --- |
| `id` | Requerido y unico. |
| `x_mm`, `y_mm`, `w_mm`, `h_mm` | Numericos finitos; `w_mm` y `h_mm` mayores a cero. |
| `rotation_deg` | Numerico finito. |
| `logical_work_id` | Puede generar warning si no resuelve. |
| `bleed_mm` | Numerico finito. |
| `crop_marks` | Usado en salida/export. |
| `locked` | Usado por UI/herramientas. |
| `design_ref` | Debe existir en `designs[].ref`. |
| `face` | Debe ser `front` o `back`. |
| `slot_box_final` | Usado por salida productiva para interpretar caja final. |

### Inferencias

`snapSettings` y parte de `spacingSettings` parecen vivir principalmente como configuracion de UI. Cambios en esos objetos deben confirmarse contra listeners y persistencia antes de asumir impacto productivo.

### Preguntas abiertas

| Tema | Pregunta |
| --- | --- |
| Dimensiones de `designs[]` | Semantica exacta de `width_mm`/`height_mm`: trim, media box, caja final con bleed o valor ya expandido. |
| Bleed | Riesgo de doble conteo entre design, slot, export y salida. |
| Overrides | Precedencia exacta entre `slot.export_overrides`, `design_export` y `export_settings`. |
| PDFs fisicos | El contrato valida referencias logicas, pero no confirma existencia fisica de PDFs. |

---

## 5. Seleccion y edicion manual

### Hechos confirmados

Estado de seleccion:

| Simbolo | Archivo | Uso |
| --- | --- | --- |
| `state.selectedSlot` | `static/js/editor_offset_visual.js` | Slot principal seleccionado. |
| `state.selectedSlots` | `static/js/editor_offset_visual.js` | Conjunto/lista de seleccion multiple. |
| `selectSlot()` | `static/js/editor_offset_visual.js` + `slot_interactions.js` | Actualiza seleccion y llama render/panel. |
| `getSelectedSlotIds()` | `static/js/editor_offset_visual.js` | Devuelve IDs seleccionados. |
| `getSelectedSlots()` | `static/js/editor_offset_visual.js` | Devuelve objetos slot seleccionados. |

Edicion manual:

| Accion | Archivo/funcion | Comportamiento |
| --- | --- | --- |
| Render formulario | `static/js/editor_offset_visual.js` / `renderSlotForm()` | Toma `state.selectedSlot` o primer ID de `selectedSlots` y llena campos. |
| Aplicar formulario | `static/js/editor_offset_visual.js` / `applySlotForm()` | Modifica solo `state.selectedSlot`; actualiza `x_mm`, `y_mm`, `w_mm`, `h_mm`, `rotation_deg`, `bleed_mm`, `crop_marks`, `locked`, `logical_work_id`, `design_ref`. |
| Render posterior | `applySlotForm()` | Llama `renderSheet()` y `pushHistory()`. |
| Aplicar diseno a seleccion | `applyDesignToSelected()` | Aplica `design_ref` a multiples slots seleccionados y llama `pushHistory()`. |
| Duplicar | `manual_tools.js` + wrapper entrypoint | Duplica slots seleccionados. |
| Borrar | `manual_tools.js` + wrapper entrypoint | Elimina slots seleccionados. |
| Alinear | `manual_tools.js` + wrapper entrypoint | Alinea seleccion. |
| Distribuir | `manual_tools.js` + wrapper entrypoint | Distribuye seleccion. |
| Centrar/nudge/spacing | `manual_tools.js` + wrapper entrypoint | Ajustes manuales de posicion/espaciado. |
| Drag | `slot_interactions.js` | Mueve slots seleccionados con conversion a mm. |
| Box select | `slot_interactions.js` | Crea rectangulo `.box-selection-rect` y selecciona slots intersectados. |

IDs de formulario de slot:

| ID | Campo |
| --- | --- |
| `slot-x` | `x_mm` |
| `slot-y` | `y_mm` |
| `slot-w` | `w_mm` |
| `slot-h` | `h_mm` |
| `slot-rot` | `rotation_deg` |
| `slot-bleed` | `bleed_mm` |
| `slot-crop` | `crop_marks` |
| `slot-locked` | `locked` |
| `slot-work` | `logical_work_id` |
| `slot-design` | `design_ref` |

Candidatos futuros para rotacion individual/grupal:

| Necesidad | Candidato |
| --- | --- |
| Control individual existente | `templates/editor_offset_visual.html` con `#slot-rot`. |
| Logica individual existente | `static/js/editor_offset_visual.js` / `applySlotForm()`. |
| Operacion grupal nueva | `static/js/editor_offset_visual/manual_tools.js`. |
| Wiring grupal | `static/js/editor_offset_visual.js`. |
| Seleccion multiple | `slot_interactions.js` y helpers `getSelectedSlots()`. |
| Persistencia | `layoutToJson()` + `saveLayout()` + `/editor_offset/save`. |
| Render | `renderSheet()` / `renderer_canvas.js`. |

### Inferencias

El patron mas seguro para una futura rotacion grupal es seguir el estilo de herramientas manuales: modificar slots seleccionados, llamar una sola vez a `pushHistory()`, luego `renderSheet()` y `renderSlotForm()`, y persistir solo cuando el usuario guarde o cuando el flujo existente invoque `saveLayout()`.

---

## 6. Rotacion actual

### Hechos confirmados

Superficie actual de rotacion:

| Capa | Archivo/simbolo | Estado |
| --- | --- | --- |
| Contrato slot | `slots[].rotation_deg` | Campo confirmado y validado como numerico. |
| UI individual | `templates/editor_offset_visual.html` / `#slot-rot` | Existe input para un slot seleccionado. |
| Aplicacion individual | `static/js/editor_offset_visual.js` / `applySlotForm()` | Escribe `slot.rotation_deg`. |
| Step & Repeat manual | `#sr-rotation`, `generateStepRepeatFromSelectedSlot()` | Puede asignar rotacion al master/clones generados. |
| Renderer visual | `renderer_canvas.js` | Guarda `dataset.rotation`, pero aplica `transform = 'none'`. |
| Geometria core | `core/geometry.js` / `getEffectiveSlotBox()` | Normaliza `rotation_deg`; `effW`/`effH` se mantienen como base W/H. |
| Contrato output | `services/editor_offset_output_contract.py` | Valida `rotation_deg`. |
| Transformacion a salida | `services/editor_offset_output_service.py` / `_positions_for_face()` | Convierte `rotation_deg` a `rot_deg`. |
| Preview/productivo | `montaje_offset_inteligente.py` | Usa `rot_deg` para rotar raster/canvas. |
| Motor repeat | `engines/step_repeat_pro_engine.py` | Genera `rotation_deg`, incluyendo 90 grados si conviene y `allow_rotation`. |
| Motor nesting | `engines/nesting_pro_engine.py` | Produce `rotation_deg`. |

Tests relacionados confirmados:

| Test | Cobertura |
| --- | --- |
| `tests/test_step_repeat_pro_engine.py::test_repeat_rotation_keeps_slot_dimensions_as_final_footprint` | Rotacion en motor repeat. |
| `tests/test_editor_offset_characterization.py` | Caracteriza salida front/back y `rot_deg` en algunas posiciones. |

### Inferencias

La rotacion actual es parcial:

| Tipo | Estado inferido |
| --- | --- |
| Por slot individual | Parcialmente soportada: se edita/persiste/sale a PDF, pero no se ve rotada en canvas activo. |
| Por motor | Soportada en `repeat` y `nesting` como dato de layout. |
| Por render visual | Parcial/no activa: `renderer_canvas.js` no aplica transform visual. |
| Por salida PDF | Soportada via `rot_deg` en `montaje_offset_inteligente.py`. |
| Por UI grupal | No confirmada como funcional; no hay control grupal dedicado. |

### Preguntas abiertas

Antes de agregar rotacion grupal hay que confirmar:

| Tema | Pregunta |
| --- | --- |
| Canvas | Si debe visualizarse la rotacion real en `.slot` o solo persistirse/salir a PDF. |
| Caja efectiva | Si `w_mm`/`h_mm` representan caja final ya rotada o dimensiones del arte antes de rotar. |
| Colisiones | Si la validacion de overlaps debe considerar huella rotada o caja sin rotar. |
| Drag/snap | Si rotar debe cambiar bounds usados para drag y snap. |
| Bleed | Como afecta rotacion a bleed, crop marks y `slot_box_final`. |
| Multi-face | Si rotacion grupal debe operar solo sobre `active_face` o tambien sobre seleccion cruzada. |

---

## 7. Motores

### Hechos confirmados

Mapa de motores y flujos:

| Flujo | Archivo/simbolos | Estado |
| --- | --- | --- |
| Step & Repeat PRO backend | `services/editor_offset_imposition_service.py` + `engines/step_repeat_pro_engine.py` | Motor canonico para imposicion automatica `repeat`. |
| Nesting backend | `services/editor_offset_imposition_service.py` + `engines/nesting_pro_engine.py` | Motor alternativo `nesting`. |
| Hybrid backend | `services/editor_offset_imposition_service.py` | Combina nesting + patron repeat. |
| Step & Repeat manual frontend | `static/js/editor_offset_visual.js` / `generateStepRepeatFromSelectedSlot()` | Flujo manual que clona/genera slots desde UI. |
| IA repeat | `ai_agent/tools_repeat.py` | Reutiliza `build_step_repeat_slots()` y devuelve layout sugerido. |
| Bridge IA | `ai_agent/openai_tool_bridge.py` | Ejecuta acciones IA y puede modificar layout devuelto. |
| Legacy output | `montaje_offset_inteligente.py` + `strategies/` | Salida productiva y estrategias de montaje. |

Detalles:

| Archivo | Responsabilidad |
| --- | --- |
| `engines/step_repeat_pro_engine.py` | Calcula capacidad, orientacion, repeticion y slots; puede lanzar `IncompleteImpositionError`. |
| `engines/nesting_pro_engine.py` | Usa rectpack con rotacion para packing; produce posiciones/rotacion. |
| `services/editor_offset_imposition_service.py` | Normaliza seleccion de engine, aplica `repeat`, `nesting` o `hybrid`. |
| `ai_agent/tools_repeat.py` | Herramientas IA como `generar_repeat()`, `validar_repeat()`, `optimizar_repeat()`. |
| `ai_agent/openai_tool_bridge.py` | Puente para `/ai/step_repeat_action_openai`. |

### Inferencias

`repeat` es el flujo backend mas maduro. `nesting` e `hybrid` deben tratarse con mas cautela por menor caracterizacion visible y posibles diferencias de contrato.

Pregunta abierta: en `engines/nesting_pro_engine.py`, la opcion `allow_rotation` parece participar en la interpretacion de rotacion, pero la configuracion del packer usa rotacion global. Hay que confirmarlo antes de prometer controles finos de rotacion por diseno en nesting.

---

## 8. Preview, PDF, CTP y bleed

### Hechos confirmados

Flujo preview/PDF:

1. Frontend llama `output_panel.js`.
2. `output_panel.js` valida geometria y ejecuta `saveLayout()`.
3. `api_client.js` llama:
   - `requestPreview()` -> `POST /editor_offset/preview/<job_id>`
   - `requestPdf()` -> `POST /editor_offset/generar_pdf/<job_id>`
4. `services/editor_offset_http_service.py` carga layout persistido.
5. `validate_constructor_output_layout()` valida contrato.
6. `services/editor_offset_output_service.py` transforma `slots[]` a `posiciones_manual`.
7. `montaje_offset_inteligente.realizar_montaje_inteligente()` genera salida.
8. Backend devuelve URL estatica de preview/PDF.

Transformacion importante:

| Campo layout | Salida manual |
| --- | --- |
| `slot.x_mm` | posicion manual X |
| `slot.y_mm` | posicion manual Y |
| `slot.w_mm` | ancho |
| `slot.h_mm` | alto |
| `slot.rotation_deg` | `rot_deg` |
| `slot.bleed_mm` | `bleed_mm` |
| `slot.crop_marks` | marcas/crop |
| `slot.slot_box_final` | interpretacion de caja final |
| `slot.face` | filtro por `front`/`back` |

CTP:

| Capa | Archivo | Responsabilidad |
| --- | --- | --- |
| UI/panel | `static/js/editor_offset_visual/ctp_panel.js` | Lee/escribe `layout.ctp`, aplica alineacion a slots frontales, puede bloquear slots. |
| Render | `renderer_canvas.js` + CSS | Dibuja overlays/guias CTP. |
| Validacion frontend | `geometry_validation.js` | Considera pinza/area CTP. |
| Salida | `services/editor_offset_output_service.py` + `montaje_offset_inteligente.py` | Usa layout/export/config para salida final. |

Bleed:

| Capa | Archivo | Observacion |
| --- | --- | --- |
| Defaults | `services/editor_offset_layout_defaults.py` | `bleed_default_mm`. |
| Upload | `services/editor_offset_uploads.py` | Puede expandir dimensiones si work tiene tamano final y bleed. |
| Slot | `slots[].bleed_mm` | Campo por slot. |
| Output | `services/editor_offset_output_service.py` | `_sanitize_slot_bleed()` y resolucion de export/crop. |
| Productivo | `montaje_offset_inteligente.py` | Usa bleed y `slot_box_final`. |

### Inferencias

Canvas, preview y PDF final no deben asumirse equivalentes. La rotacion, el bleed, CTP, doble cara y `slot_box_final` pueden verse o interpretarse distinto entre capas.

---

## 9. Tests relacionados

### Hechos confirmados

| Test | Tipo | Cobertura principal |
| --- | --- | --- |
| `tests/test_editor_offset_characterization.py` | Caracterizacion | Salida, estrategias, front/back, CTP, posiciones manuales y compatibilidad legacy. |
| `tests/test_editor_offset_output_contract.py` | Contrato | Validacion de layout, slots, designs, faces, duplicados y warnings. |
| `tests/test_step_repeat_pro_engine.py` | Motor | Step & Repeat PRO, capacidad, incomplete imposition, rotacion y dimensiones. |
| `tests/test_editor_advisor_tools.py` | IA SAFE | Herramientas de lectura/listado/resumen del advisor. |
| `tests/test_cuadernillos_simulator.py` | Cuadernillos | Simulador de cuadernillos. |
| `tests/playwright/test_editor_load.py` | E2E/UI | Carga basica del editor. |
| `tests/playwright/test_editor_productive_workflows.py` | E2E/UI | Flujos productivos principales. |
| `tests/playwright/test_editor_manual_interactions.py` | E2E/UI | Interacciones manuales. |
| `tests/playwright/test_editor_drag_resize_interactions.py` | E2E/UI | Drag y caracterizacion de resize latente. |

Tests relevantes antes de implementar rotacion individual/grupal:

| Area | Tests a revisar/agregar |
| --- | --- |
| UI individual | Playwright para `#slot-rot`, `applySlotForm()` y persistencia. |
| UI grupal | Playwright para seleccion multiple + nuevo control grupal. |
| Persistencia | Unit/characterization sobre `layout_constructor.json` con `rotation_deg`. |
| Contrato | `tests/test_editor_offset_output_contract.py` para valores validos/invalidos si cambia regla. |
| Output | `tests/test_editor_offset_characterization.py` para `rot_deg` en posiciones manuales. |
| Motores | `tests/test_step_repeat_pro_engine.py` si cambia semantica de caja/rotacion. |
| Canvas | Playwright visual o DOM si se decide mostrar rotacion real en `.slot`. |

### Inferencias

La primera implementacion de rotacion grupal deberia evitar tocar motores y salida si solo escribe `slots[].rotation_deg`, porque ya existe contrato y salida para ese campo.

---

## 10. Zonas fragiles y reglas de no tocar

### Hechos confirmados

Archivos de alto riesgo:

| Archivo | Riesgo |
| --- | --- |
| `static/js/editor_offset_visual.js` | Entrypoint muy acoplado: estado, listeners, render, historial, seleccion, output y paneles. |
| `templates/editor_offset_visual.html` | IDs y `data-*` consumidos por JS y tests. |
| `static/css/editor_offset_visual.css` | Estados visuales, layout, seleccion, CTP y resize latente. |
| `routes.py` | Rutas publicas y compatibilidad Flask. |
| `services/editor_offset_output_service.py` | Transformacion critica a salida productiva. |
| `montaje_offset_inteligente.py` | Legacy compartido/productivo. |
| `engines/step_repeat_pro_engine.py` | Motor canonico repeat. |
| `services/editor_offset_output_contract.py` | Contrato previo a preview/PDF. |

IDs y `data-*` criticos:

| Tipo | Simbolos |
| --- | --- |
| Hoja/canvas | `sheet`, `sheet-canvas` |
| Slot form | `slot-form`, `slot-none`, `slot-x`, `slot-y`, `slot-w`, `slot-h`, `slot-rot`, `slot-bleed`, `slot-crop`, `slot-locked`, `slot-work`, `slot-design` |
| Geometry | `geometry-validation-summary`, `geometry-validation-list` |
| Upload/output | `upload-form`, `preview-image`, `pdf-output` |
| Tabs | `data-editor-tab`, `data-editor-tab-panel` |
| Botones | IDs `btn-*` usados por listeners |
| CTP | IDs `ctp-*` |
| IA | IDs `ai-*` |

Clases criticas:

| Clase | Uso |
| --- | --- |
| `.slot` | Elemento visual de slot. |
| `.selected` | Estado de seleccion. |
| `.locked` | Estado bloqueado. |
| `.geometry-error` | Error geometrico. |
| `.geometry-warning` | Warning geometrico. |
| `.box-selection-rect` | Rectangulo de box select. |
| `.ctp-guide` | Guias visuales CTP. |
| `.distance-indicator` | Indicadores visuales de distancia. |

Zonas latentes o dudosas:

| Zona | Estado |
| --- | --- |
| Resize | CSS/JS contiene referencias a handles, pero renderer activo no crea handles operativos. |
| `sr-offset-x`, `sr-offset-y` | Controles Step & Repeat manual sin efecto confirmado. |
| `sr-top-margin`, `sr-bottom-margin`, `sr-left-margin`, `sr-right-margin` | Controles Step & Repeat manual sin lectura confirmada en generacion. |
| Wrappers duplicados/legacy del entrypoint | Pueden existir funciones aparentemente huerfanas o ramas posteriores a `return`. |

### Reglas de no tocar

No tocar sin fase especifica:

| Superficie | Motivo |
| --- | --- |
| Semantica de `slots[]` | Afecta UI, persistencia, motores y salida. |
| Semantica de `rotation_deg` | Afecta canvas, preview, PDF, motores y tests. |
| Semantica de bleed | Riesgo de doble conteo. |
| `slot_box_final` | Critico para salida productiva. |
| `montaje_offset_inteligente.py` | Legacy/productivo compartido. |
| Rutas publicas | Usadas por frontend y tests. |
| IDs HTML existentes | Usados por listeners y Playwright. |
| Resize | Debe tratarse como fase independiente. |

---

## 11. Integracion futura: rotacion individual y grupal

Esta seccion es un plan de integracion. No implementa la funcionalidad.

### Hechos confirmados

Rotacion individual ya tiene piezas existentes:

| Pieza | Archivo/simbolo |
| --- | --- |
| Campo UI | `templates/editor_offset_visual.html` / `#slot-rot` |
| Lectura/escritura | `static/js/editor_offset_visual.js` / `applySlotForm()` |
| Persistencia | `layoutToJson()` + `/editor_offset/save` |
| Contrato | `services/editor_offset_output_contract.py` / `rotation_deg` |
| Salida | `services/editor_offset_output_service.py` / `rot_deg` |
| Productivo | `montaje_offset_inteligente.py` / `rot_deg` |

### Plan SAFE propuesto

1. Mantener `rotation_deg` como campo canonico por slot.
2. No cambiar motores, output, CTP, bleed ni contrato en la primera fase si solo se agrega edicion grupal.
3. Agregar el control grupal en una zona de herramientas manuales o panel de edicion existente, evitando renombrar IDs actuales.
4. Crear IDs nuevos con nombres especificos y no ambiguos, por ejemplo:
   - `slot-selection-rot`
   - `btn-apply-selection-rotation`
5. Escuchar el evento en `static/js/editor_offset_visual.js`, junto al wiring actual de herramientas manuales.
6. Implementar la operacion pura en `static/js/editor_offset_visual/manual_tools.js`, siguiendo el patron de align/distribute/nudge.
7. La operacion debe recibir slots seleccionados editables, ignorar bloqueados o respetar el patron existente de `getSelectedSlots({ editableOnly: true })` si aplica.
8. Modificar `slot.rotation_deg` en cada slot seleccionado.
9. Llamar una sola vez a `pushHistory()` despues de aplicar cambios.
10. Llamar `renderSheet()` y `renderSlotForm()` despues de actualizar estado.
11. Persistir mediante el flujo existente: `layoutToJson()` y `saveLayout()`.
12. Agregar o revisar tests antes de declarar completo.

### Riesgos especificos

| Riesgo | Mitigacion |
| --- | --- |
| Canvas no muestra rotacion real | Decidir si la primera fase solo persiste/sale a PDF o si tambien rota visualmente `.slot`. |
| Validacion de overlaps no considera huella rotada | No cambiar validacion hasta definir semantica de caja efectiva. |
| Seleccion multiple con slots bloqueados | Respetar comportamiento actual de herramientas manuales. |
| Confusion entre rotacion individual y grupal | Mantener `#slot-rot` para un slot y crear control grupal separado. |
| Historial ruidoso | Un solo `pushHistory()` por operacion grupal. |
| Cambios accidentales en output | No tocar `services/editor_offset_output_service.py` ni `montaje_offset_inteligente.py` en primera fase. |

### Que no conviene tocar en esa fase

| No tocar | Motivo |
| --- | --- |
| `engines/step_repeat_pro_engine.py` | El motor ya produce `rotation_deg`; no es necesario para UI grupal. |
| `engines/nesting_pro_engine.py` | Riesgo independiente. |
| `services/editor_offset_output_service.py` | Ya traduce `rotation_deg` a `rot_deg`. |
| `montaje_offset_inteligente.py` | Ya consume `rot_deg`; alto riesgo productivo. |
| Resize | Funcionalidad latente separada. |
| Bleed/CTP | Superficies criticas no necesarias para rotacion grupal inicial. |
| IDs existentes | Riesgo de romper listeners/tests. |

### Preguntas abiertas

| Tema | Pregunta |
| --- | --- |
| UI | Si el control grupal debe mostrar valor comun, estado mixto o campo vacio cuando hay rotaciones distintas. |
| Visual | Si el canvas debe aplicar transform visual real. |
| Semantica | Si rotar 90/270 debe intercambiar huella efectiva o conservar `w_mm`/`h_mm` como caja final. |
| Bloqueados | Si slots `locked` deben ignorarse, bloquear operacion o permitir override explicito. |

---

## 12. Proximos pasos SAFE

### Recomendacion

Antes de implementar rotacion individual/grupal:

1. Confirmar semantica deseada de rotacion visual: persistencia solamente vs transform visual en canvas.
2. Confirmar semantica de caja: `w_mm`/`h_mm` como caja final o arte antes de rotar.
3. Escribir plan pequeno de implementacion limitado a HTML + `manual_tools.js` + wiring en `static/js/editor_offset_visual.js`.
4. No tocar backend si el cambio solo escribe `slots[].rotation_deg`.
5. Revisar IDs/listeners antes de agregar nuevos controles.
6. Agregar tests focalizados despues de implementar:
   - Playwright para seleccion multiple y control grupal.
   - Persistencia de `rotation_deg`.
   - Caracterizacion de salida si se modifica comportamiento visual/productivo.
7. Tratar resize, bleed, CTP y visualizacion real de rotacion como fases separadas si requieren cambios de semantica.

### Tabla funcionalidad -> archivo responsable

| Funcionalidad | Archivo responsable |
| --- | --- |
| Layout inicial | `services/editor_offset_http_service.py`, `services/editor_offset_jobs.py`, `templates/editor_offset_visual.html` |
| Estado frontend | `static/js/editor_offset_visual.js` |
| DOM refs | `static/js/editor_offset_visual/dom_refs.js` |
| Render visual | `static/js/editor_offset_visual/renderer_canvas.js` |
| Seleccion/drag/box select | `static/js/editor_offset_visual/slot_interactions.js` |
| Herramientas manuales | `static/js/editor_offset_visual/manual_tools.js` |
| API frontend | `static/js/editor_offset_visual/api_client.js` |
| Guardado | `api_client.js`, `/editor_offset/save`, `services/editor_offset_jobs.py` |
| Upload | `/editor_offset/upload/<job_id>`, `services/editor_offset_uploads.py` |
| Imposicion | `/editor_offset_visual/apply_imposition`, `services/editor_offset_imposition_service.py` |
| Preview/PDF | `output_panel.js`, `services/editor_offset_output_service.py`, `montaje_offset_inteligente.py` |
| CTP | `static/js/editor_offset_visual/ctp_panel.js`, `geometry_validation.js` |
| Cuadernillos | `static/js/editor_offset_visual/booklet_panel.js`, `cuadernillos/simulator.py` |
| IA | `ai_agent/tools_repeat.py`, `ai_agent/openai_tool_bridge.py`, `ai_agent/editor_advisor/` |

### Tabla riesgo -> archivo -> mitigacion

| Riesgo | Archivo/superficie | Mitigacion |
| --- | --- | --- |
| Romper listeners por renombrar IDs | `templates/editor_offset_visual.html`, `static/js/editor_offset_visual.js` | Buscar referencias antes de cambiar; agregar IDs nuevos sin alterar existentes. |
| Desalinear canvas y PDF | `renderer_canvas.js`, `services/editor_offset_output_service.py`, `montaje_offset_inteligente.py` | Caracterizar visual vs salida antes de cambiar semantica. |
| Doble conteo de bleed | Upload/output/legacy | No tocar bleed junto con rotacion; fase separada. |
| Romper motor repeat | `engines/step_repeat_pro_engine.py` | No tocar para edicion UI inicial. |
| Activar resize accidentalmente | CSS/JS de handles | Mantener resize como fase independiente. |
| Guardado inconsistente | `layoutToJson()`, `/editor_offset/save` | Usar flujo existente de persistencia. |
| IA escribiendo sin guardrails | `ai_agent/*` | No conectar a escritura automatica sin aprobacion y validaciones. |

---

## Estado del documento

Este documento es una referencia de conexiones. No reemplaza los contratos de `DOCS/OFFSET/05_CONTRATOS_EDITOR_OFFSET_VISUAL.md` ni la auditoria base `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`; los complementa con un mapa operativo orientado a cambios futuros.
