# 06 - Mapa de conexiones del Editor Offset Visual

Documento de referencia SAFE para entender las conexiones internas del Editor Offset Visual y planificar futuras funcionalidades sin romper el flujo actual.

Este documento fue construido por lectura de archivos del repositorio. No implica cambios de codigo, ejecucion de tests ni ejecucion de scripts productivos.

## Changelog de rotacion

Hechos confirmados contra el codigo actual:

| Fase | Estado documentado | Archivos/simbolos |
| --- | --- | --- |
| Fase 1 | Rotacion grupal logica en frontend. Reutiliza `slots[].rotation_deg` y opera sobre seleccion editable. | `templates/editor_offset_visual.html` (`#selection-rotation-deg`, `#btn-apply-selection-rotation`), `static/js/editor_offset_visual/manual_tools.js` (`rotateSelectedSlots()`), `static/js/editor_offset_visual.js` (`rotateSelectedSlots()`, listener del boton). |
| Fase 2 | Rotacion visual en canvas. El render setea `data-rotation` y la variable CSS `--slot-rotation-deg`; CSS aplica `transform: rotate(...)`. | `static/js/editor_offset_visual/renderer_canvas.js`, `static/css/editor_offset_visual.css` (`.slot[data-rotation]`). |
| Fase 3.1 | Helper de huella rotada cardinal sin cambiar la semantica de `getEffectiveSlotBox()`, `slotFootprintRect()` ni `getSimpleSlotBox()`. | `static/js/editor_offset_visual/core/geometry.js` (`normalizeRotationDeg()`, `getCardinalRotatedSlotFootprint()`). |
| Fase 3.2A | `OUT_OF_SHEET` y `OUT_OF_USABLE_AREA` usan huella rotada cardinal cuando la rotacion es 0/90/180/270. | `static/js/editor_offset_visual/core/geometry_validation.js` (`validationBoxForSlot()`). |
| Fase 3.2B | `OVERLAP` usa la misma caja de validacion cardinal. | `static/js/editor_offset_visual/core/geometry_validation.js`. |
| Fase 3.2C | `GRIPPER` frontend usa huella rotada cardinal mediante `validationBoxForSlot()`. | `static/js/editor_offset_visual/core/geometry_validation.js`. |
| Fix salida PDF | La salida PDF distingue rotacion manual UI vs repeat automatico rotado para evitar deformar el PDF fuente. Respeta `slot_box_final` explicito y puede pasar `source_w_mm`/`source_h_mm` internos hacia montaje. | `services/editor_offset_output_service.py` (`_resolve_slot_box_final()`, `_positions_for_face()`), `montaje_offset_inteligente.py` (`source_w_mm`, `source_h_mm`). |

Pendientes confirmados: `box select`, `drag`, `snap`, `align/distribute`, `distance indicator`, angulos libres y colision poligonal real. Canvas, validacion frontend y PDF siguen siendo superficies distintas.

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
| `static/js/editor_offset_visual/core/geometry.js` | conversion mm/px, cajas, bounds, huella cardinal | Usado por renderer, validacion, seleccion, drag y herramientas manuales. Expone `normalizeRotationDeg()` y `getCardinalRotatedSlotFootprint()`. |
| `static/js/editor_offset_visual/core/geometry_validation.js` | validacion geometrica | Revisa limites de hoja, area util, pinza CTP y overlaps por cara. Para rotaciones cardinales usa `validationBoxForSlot()` en `OUT_OF_SHEET`, `OUT_OF_USABLE_AREA`, `OVERLAP` y `GRIPPER`. |
| `static/js/editor_offset_visual/renderer_canvas.js` | `renderSheetSurface()` | Renderiza `.slot`, overlays, guias CTP, warnings/errores, estado visual y rotacion visual con `data-rotation`/`--slot-rotation-deg`. |
| `static/js/editor_offset_visual/manual_tools.js` | duplicate/delete/group/align/distribute/center/nudge/spacing/rotation | Operaciones manuales sobre slots seleccionados, incluida `rotateSelectedSlots()`. |
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
| Render de hoja/slots | `static/js/editor_offset_visual/renderer_canvas.js` + wrapper en entrypoint | `renderSheetSurface()`, `.slot`, `.selected`, `.locked`, `.geometry-error`, `.geometry-warning`, `data-rotation`, `--slot-rotation-deg`. |
| Tabs | `templates/editor_offset_visual.html` + entrypoint | `data-editor-tab`, `data-editor-tab-panel`. |
| Seleccion simple | `slot_interactions.js` + entrypoint | `selectSlot()`, `state.selectedSlot`, `state.selectedSlots`. |
| Seleccion multiple | `slot_interactions.js` + entrypoint | `getSelectedSlotIds()`, `getSelectedSlots()`, `selectedSlots`. |
| Box select | `slot_interactions.js` | `.box-selection-rect`, calculo de interseccion con slots visibles. |
| Drag | `slot_interactions.js` | movimiento en mm, snap/grid segun contexto. |
| Resize | `slot_interactions.js`, CSS, entrypoint | Latente; el renderer activo no crea handles operativos. |
| Edicion de slot | `static/js/editor_offset_visual.js` | `renderSlotForm()`, `applySlotForm()`, IDs `slot-x`, `slot-y`, `slot-w`, `slot-h`, `slot-rot`, `slot-bleed`, `slot-crop`, `slot-locked`, `slot-work`, `slot-design`. |
| Herramientas manuales | `manual_tools.js` + wrappers entrypoint | duplicar, borrar, alinear, distribuir, centrar, nudges, spacing, rotacion grupal. |
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
| Aplicar rotacion a seleccion | `static/js/editor_offset_visual.js` + `manual_tools.rotateSelectedSlots()` | Lee `#selection-rotation-deg`, obtiene `getSelectedSlots({ editableOnly: true })`, escribe `slot.rotation_deg`, llama un solo `pushHistory()` y refresca seleccion/render. |
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

Estado actual de rotacion individual/grupal:

| Necesidad | Estado |
| --- | --- |
| Control individual | Implementado con `templates/editor_offset_visual.html` / `#slot-rot`. |
| Logica individual | Implementada en `static/js/editor_offset_visual.js` / `applySlotForm()`. |
| Control grupal | Implementado en `#manual-advanced-tools` con `#selection-rotation-deg` y `#btn-apply-selection-rotation`. |
| Operacion grupal | Implementada en `static/js/editor_offset_visual/manual_tools.js` / `rotateSelectedSlots()`. |
| Wiring grupal | Implementado en `static/js/editor_offset_visual.js` / `rotateSelectedSlots()` y listener de `#btn-apply-selection-rotation`. |
| Seleccion multiple | Usa `getSelectedSlots({ editableOnly: true })` y respeta la cara activa igual que las herramientas manuales existentes. |
| Persistencia | Sigue el flujo existente: `layoutToJson()` + `saveLayout()` + `/editor_offset/save`. |
| Render | `renderSheet()` / `renderer_canvas.js` muestran la rotacion visual con CSS. |

### Inferencias

La rotacion grupal ya sigue el patron SAFE previsto para herramientas manuales: modifica slots seleccionados editables, usa un solo `pushHistory()`, refresca seleccion/render y persiste solo mediante el flujo existente de guardado.

---

## 6. Rotacion actual

### Hechos confirmados

Superficie actual de rotacion:

| Capa | Archivo/simbolo | Estado |
| --- | --- | --- |
| Contrato slot | `slots[].rotation_deg` | Campo confirmado y validado como numerico. |
| UI individual | `templates/editor_offset_visual.html` / `#slot-rot` | Existe input para un slot seleccionado. |
| Aplicacion individual | `static/js/editor_offset_visual.js` / `applySlotForm()` | Escribe `slot.rotation_deg`. |
| UI grupal | `templates/editor_offset_visual.html` / `#selection-rotation-deg`, `#btn-apply-selection-rotation` | Existe control para aplicar rotacion a seleccion editable. |
| Aplicacion grupal | `static/js/editor_offset_visual/manual_tools.js` / `rotateSelectedSlots()` + wrapper en `static/js/editor_offset_visual.js` | Escribe `slot.rotation_deg` en los slots seleccionados editables con un solo `pushHistory()`. |
| Step & Repeat manual | `#sr-rotation`, `generateStepRepeatFromSelectedSlot()` | Puede asignar rotacion al master/clones generados. |
| Renderer visual | `renderer_canvas.js` + CSS | Setea `data-rotation` y `--slot-rotation-deg`; `.slot[data-rotation]` aplica `transform: rotate(...)`. |
| Geometria core | `core/geometry.js` / `getEffectiveSlotBox()` | Normaliza `rotation_deg`; `effW`/`effH` se mantienen como base W/H. La semantica no fue migrada. |
| Helper huella cardinal | `core/geometry.js` / `normalizeRotationDeg()`, `getCardinalRotatedSlotFootprint()` | Calcula huella visual para 0/90/180/270; en 90/270 intercambia W/H manteniendo centro. |
| Validacion frontend | `core/geometry_validation.js` / `validationBoxForSlot()` | Usa huella cardinal para `OUT_OF_SHEET`, `OUT_OF_USABLE_AREA`, `OVERLAP` y `GRIPPER`; angulos no cardinales caen a caja simple. |
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

La rotacion actual combina partes implementadas y limites deliberados:

| Tipo | Estado inferido |
| --- | --- |
| Por slot individual | Soportada como dato, UI individual, persistencia, render visual y salida productiva via `rot_deg`. |
| Por seleccion grupal | Soportada como edicion de dato frontend usando `slots[].rotation_deg`; no toca backend ni contratos. |
| Por motor | Soportada en `repeat` y `nesting` como dato de layout. |
| Por render visual | Soportada en canvas mediante CSS transform sobre `.slot[data-rotation]`. |
| Por geometria core general | Parcial: existe helper cardinal, pero `getEffectiveSlotBox()`, `slotFootprintRect()` y `getSimpleSlotBox()` siguen con semantica no rotada. |
| Por validacion frontend | Parcial: `OUT_OF_SHEET`, `OUT_OF_USABLE_AREA`, `OVERLAP` y `GRIPPER` usan huella cardinal; no hay colision poligonal ni soporte geometrico real para angulos libres. |
| Por interacciones | Pendiente: `box select`, `drag`, `snap`, `align/distribute` y `distance indicator` siguen usando cajas no rotadas por los flujos actuales. |
| Por salida PDF | Soportada via `rot_deg` en `montaje_offset_inteligente.py`. |

### Preguntas abiertas

Antes de evolucionar la rotacion hay que confirmar:

| Tema | Pregunta |
| --- | --- |
| Caja efectiva | Si `w_mm`/`h_mm` representan caja final ya rotada o dimensiones del arte antes de rotar. |
| Colisiones | Si una fase futura debe pasar de AABB cardinal a colision poligonal real. |
| Drag/snap | Si rotar debe cambiar bounds usados para drag, snap y guias de distancia. |
| Bleed | Como afecta rotacion a bleed, crop marks y `slot_box_final`. |
| Angulos libres | Si deben soportarse en geometria o mantenerse solo como dato/render/salida. |
| Multi-face | Si futuras operaciones globales deben operar solo sobre `active_face` o tambien sobre seleccion cruzada. |
| PDF/productivo | Si la huella validada en frontend debe alinearse contractualmente con preview/PDF final. |

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

Semantica actual de salida PDF para rotacion:

| Tema | Comportamiento confirmado |
| --- | --- |
| `slot_box_final` explicito | `services/editor_offset_output_service.py` lo respeta antes de inferir cualquier semantica. |
| Repeat automatico rotado | Si el slot repeat no trae `slot_box_final` y su `w_mm`/`h_mm` ya coinciden con la huella rotada del diseno, la salida mantiene `slot_box_final=True`. |
| Rotacion manual UI | Si el slot repeat no trae `slot_box_final`, tiene `rotation_deg` 90/270 y conserva `w_mm`/`h_mm` base del diseno, la salida lo trata como `slot_box_final=False` y recalcula la huella rotada centrada. |
| Aspect ratio | `source_w_mm`/`source_h_mm` pueden viajar como datos internos de `posiciones_manual` hacia `montaje_offset_inteligente.py` para dibujar el PDF fuente sin invertir proporcion antes de rotar. |
| `rotation_deg=90` | Debe rotar sin deformar el PDF fuente; la fuente mantiene sus dimensiones de origen y la huella rotada se calcula aparte. |

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

Canvas, preview y PDF final no deben asumirse equivalentes. La rotacion, el bleed, CTP, doble cara y `slot_box_final` pueden verse o interpretarse distinto entre capas. La salida PDF tiene una correccion especifica para no deformar slots rotados manualmente, pero eso no convierte automaticamente la validacion frontend, el canvas y el PDF en una unica geometria compartida.

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

Tests relevantes para consolidar y evolucionar rotacion individual/grupal:

| Area | Tests a revisar/agregar |
| --- | --- |
| UI individual | Playwright para `#slot-rot`, `applySlotForm()` y persistencia. |
| UI grupal | Playwright para seleccion multiple + `#selection-rotation-deg` + `#btn-apply-selection-rotation`. |
| Persistencia | Unit/characterization sobre `layout_constructor.json` con `rotation_deg`. |
| Contrato | `tests/test_editor_offset_output_contract.py` para valores validos/invalidos si cambia regla. |
| Output | `tests/test_editor_offset_characterization.py` para `rot_deg` en posiciones manuales. |
| Motores | `tests/test_step_repeat_pro_engine.py` si cambia semantica de caja/rotacion. |
| Canvas | Playwright visual o DOM para `data-rotation`, `--slot-rotation-deg` y `transform` en `.slot[data-rotation]`. |
| Geometria frontend | Unit/DOM aislado para `getCardinalRotatedSlotFootprint()` y `validationBoxForSlot()` en `OUT_OF_SHEET`, `OUT_OF_USABLE_AREA`, `OVERLAP` y `GRIPPER`. |

### Inferencias

Las fases ya implementadas evitaron tocar motores y salida al reutilizar `slots[].rotation_deg`. Antes de migrar interacciones o contratos conviene agregar cobertura focalizada para no mezclar geometria frontend con salida productiva.

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

## 11. Rotacion individual y grupal: estado implementado + pendientes

### Hechos confirmados

Rotacion individual:

| Pieza | Archivo/simbolo |
| --- | --- |
| Campo UI | `templates/editor_offset_visual.html` / `#slot-rot` |
| Lectura/escritura | `static/js/editor_offset_visual.js` / `applySlotForm()` |
| Persistencia | `layoutToJson()` + `/editor_offset/save` |
| Contrato | `services/editor_offset_output_contract.py` / `rotation_deg` |
| Salida | `services/editor_offset_output_service.py` / `rot_deg` |
| Productivo | `montaje_offset_inteligente.py` / `rot_deg` |

Rotacion grupal implementada:

| Pieza | Archivo/simbolo | Estado |
| --- | --- | --- |
| Campo UI grupal | `templates/editor_offset_visual.html` / `#selection-rotation-deg` | Control numerico ubicado en `#manual-advanced-tools`. |
| Accion UI grupal | `templates/editor_offset_visual.html` / `#btn-apply-selection-rotation` | Boton dedicado para aplicar la rotacion a la seleccion. |
| Operacion pura | `static/js/editor_offset_visual/manual_tools.js` / `rotateSelectedSlots()` | Normaliza y escribe `slot.rotation_deg` en slots recibidos. |
| Wrapper/listener | `static/js/editor_offset_visual.js` / `rotateSelectedSlots()` | Lee input, llama `getSelectedSlots({ editableOnly: true })`, ejecuta operacion, hace un solo `pushHistory()` y refresca seleccion. |
| Render visual | `static/js/editor_offset_visual/renderer_canvas.js` + CSS | `data-rotation`, `--slot-rotation-deg` y `.slot[data-rotation]` aplican rotacion visual. |
| Huella cardinal | `static/js/editor_offset_visual/core/geometry.js` | `getCardinalRotatedSlotFootprint()` calcula AABB cardinal sin alterar `getEffectiveSlotBox()`. |
| Validacion frontend | `static/js/editor_offset_visual/core/geometry_validation.js` | `validationBoxForSlot()` alimenta `OUT_OF_SHEET`, `OUT_OF_USABLE_AREA`, `OVERLAP` y `GRIPPER`. |

### Pendientes confirmados

| Pendiente | Estado actual |
| --- | --- |
| `box select` | `slot_interactions.js` sigue intersectando contra `slotFootprintRect()`, que usa `getEffectiveSlotBox()` sin huella rotada. |
| `drag` | Movimiento y limites/snap asociados siguen basados en cajas no rotadas. |
| `snap` | `applySnap()` en el entrypoint usa `getEffectiveSlotBox()`; no considera huella cardinal. |
| `align/distribute` | `manual_tools.js` usa `getEffectiveSlotBox()`; alinear/distribuir no considera huella rotada. |
| `distance indicator` | El indicador de distancia usa `getSimpleSlotBox()` en el entrypoint. |
| Angulos libres | La validacion geometrica solo usa huella rotada para cardinales 0/90/180/270; otros angulos caen a caja simple. |
| Colision poligonal real | No implementada; `OVERLAP` usa AABB cardinal, no poligonos rotados. |
| PDF/productivo | Tiene correccion especifica para no deformar rotacion manual UI, pero sigue siendo una superficie distinta de canvas y validacion frontend. |
| Tests dedicados | No queda documentada cobertura automatizada especifica para todas las fases de rotacion frontend. |

### Que no conviene tocar sin fase nueva

| No tocar | Motivo |
| --- | --- |
| `engines/step_repeat_pro_engine.py` | El motor ya produce `rotation_deg`; no es necesario para UI grupal. |
| `engines/nesting_pro_engine.py` | Riesgo independiente. |
| `services/editor_offset_output_service.py` | Traduce `rotation_deg` a `rot_deg` y contiene la inferencia de `slot_box_final`; no tocar sin caracterizacion de salida. |
| `montaje_offset_inteligente.py` | Ya consume `rot_deg`; alto riesgo productivo. |
| Resize | Funcionalidad latente separada. |
| Bleed/CTP | Superficies criticas no necesarias para rotacion grupal inicial. |
| IDs existentes | Riesgo de romper listeners/tests. |
| `getEffectiveSlotBox()` | Cambiarlo tendria impacto amplio sobre seleccion, drag, herramientas manuales y validaciones. |
| `slotFootprintRect()` | Migrarlo afectaria box select e interacciones; requiere fase propia y pruebas. |

### Preguntas abiertas

| Tema | Pregunta |
| --- | --- |
| UI | Si el control grupal debe mostrar valor comun, estado mixto o campo vacio cuando hay rotaciones distintas. |
| Semantica global | Si una fase futura debe migrar `getEffectiveSlotBox()` o mantener un helper separado por caso de uso. |
| Interacciones | Si `box select`, `drag`, `snap`, `align/distribute` y `distance indicator` deben usar AABB cardinal o geometria poligonal. |
| Salida | Si futuras validaciones backend/PDF deben alinearse mas con la huella frontend o conservar la correccion acotada actual. |
| Bloqueados | Si slots `locked` deben ignorarse, bloquear operacion o permitir override explicito. |

---

## 12. Proximos pasos SAFE

### Recomendacion

Despues de las fases de rotacion ya aplicadas:

1. Mantener `slots[].rotation_deg` como campo canonico y no cambiar el contrato JSON sin fase explicita.
2. Agregar cobertura focalizada para rotacion grupal, render visual y validacion cardinal antes de tocar mas geometria.
3. Planificar `box select`, `drag`, `snap`, `align/distribute` y `distance indicator` como fases separadas, porque hoy siguen usando cajas no rotadas.
4. No migrar `getEffectiveSlotBox()` ni `slotFootprintRect()` de forma global sin caracterizar impactos en seleccion, herramientas manuales, validacion y tests Playwright.
5. Mantener motores, bleed y CTP productivo fuera de las siguientes fases; tocar PDF/output solo con caracterizacion y regresiones.
6. Definir si los angulos libres deben quedar como dato/render/salida o si requieren colision poligonal real.
7. Comparar canvas, validacion frontend y PDF final antes de declarar equivalencia productiva.

### Tabla funcionalidad -> archivo responsable

| Funcionalidad | Archivo responsable |
| --- | --- |
| Layout inicial | `services/editor_offset_http_service.py`, `services/editor_offset_jobs.py`, `templates/editor_offset_visual.html` |
| Estado frontend | `static/js/editor_offset_visual.js` |
| DOM refs | `static/js/editor_offset_visual/dom_refs.js` |
| Render visual | `static/js/editor_offset_visual/renderer_canvas.js` |
| Rotacion visual canvas | `static/js/editor_offset_visual/renderer_canvas.js`, `static/css/editor_offset_visual.css` |
| Seleccion/drag/box select | `static/js/editor_offset_visual/slot_interactions.js` |
| Herramientas manuales | `static/js/editor_offset_visual/manual_tools.js` |
| Rotacion grupal | `templates/editor_offset_visual.html`, `static/js/editor_offset_visual/manual_tools.js`, `static/js/editor_offset_visual.js` |
| Huella rotada cardinal | `static/js/editor_offset_visual/core/geometry.js` |
| Validacion geometrica rotada cardinal | `static/js/editor_offset_visual/core/geometry_validation.js` |
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
| Validacion frontend cardinal no equivalente al PDF | `geometry_validation.js`, output/PDF | Mantener documentada la diferencia entre canvas, validacion frontend y salida; agregar tests antes de acoplar mas contrato productivo. |
| Interacciones usan caja no rotada | `slot_interactions.js`, `manual_tools.js`, `static/js/editor_offset_visual.js` | Migrar `box select`, `drag`, `snap`, `align/distribute` y `distance indicator` en fases separadas. |
| Angulos libres sin geometria real | `geometry.js`, `geometry_validation.js` | Mantener fallback a caja simple hasta definir soporte poligonal. |
| Doble conteo de bleed | Upload/output/legacy | No tocar bleed junto con rotacion; fase separada. |
| Romper motor repeat | `engines/step_repeat_pro_engine.py` | No tocar para edicion UI inicial. |
| Activar resize accidentalmente | CSS/JS de handles | Mantener resize como fase independiente. |
| Guardado inconsistente | `layoutToJson()`, `/editor_offset/save` | Usar flujo existente de persistencia. |
| IA escribiendo sin guardrails | `ai_agent/*` | No conectar a escritura automatica sin aprobacion y validaciones. |

---

## Estado del documento

Este documento es una referencia de conexiones. No reemplaza los contratos de `DOCS/OFFSET/05_CONTRATOS_EDITOR_OFFSET_VISUAL.md` ni la auditoria base `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`; los complementa con un mapa operativo orientado a cambios futuros.
