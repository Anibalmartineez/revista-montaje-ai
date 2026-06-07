# 04 PLAN OFFSET

## Objetivo de esta etapa

Consolidar el Editor Visual IA como flujo operativo profesional del modulo Offset, manteniendo compatibilidad con el layout existente y evitando refactors amplios.

## Etapa actual

- Estado documentado: Fase 10 UX cerrada como baseline historica y separacion modular SAFE completada hasta Fase 5D-5, con Fase 6-0, 6A, 6B, 6C-0 y 6C-1 cerradas
- Fase 8 queda como base cerrada de arquitectura SAFE y shell UX del Editor Visual IA
- Sin refactor masivo
- Sin limpieza agresiva
- Sin eliminacion de archivos
- Cambios acotados sobre el Editor Visual IA
- Roadmap activo actual: consolidar arquitectura y cobertura antes de mover estructura fisica
- Foco real acumulado:
  - Step & Repeat PRO Inteligente cerrado como Fase 5
  - simulador de cuadernillos cerrado como Fase 6 historica visual/logica
  - separacion explicita entre simulacion de cuadernillos y salida PDF
  - validacion de salida protegida con tests y extraida a un modulo chico en Fase 7
  - jobs/defaults/uploads separados en servicios en Fase 8.1
  - Step & Repeat PRO extraido a `engines/step_repeat_pro_engine.py` en Fase 8.1B
  - servicio de imposicion `repeat`/`nesting`/`hybrid` en Fase 8.1C
  - shell UX y tabs profesionales en Fases 8.2/8.3
  - premium visual pass SAFE y microajustes de contraste CSS-only
  - base Playwright inicial para carga, tabs y scroll del editor
  - prototipo OpenAI Agents SDK `ai_agent/editor_advisor/` como asesor CLI-only/read-only
  - Fase 9.2 completada: `editor_advisor` especializado como UX SAFE Advisor
  - Fase 9.3 completada: premium pass CSS-only del panel derecho en `static/css/editor_offset_visual.css`
  - Fase 9.4 completada: Codex Prompt Builder con `prompt_para_codex` y `--codex-prompt-only`
  - Fase 10.0 completada: auditoria visual y baseline de header/topbar/canvas/panel derecho
  - Fase 10.1 completada: Canvas Pro Shell CSS-only, con topbar CAD/preprensa y canvas mas protagonista
  - Fase 10.2 completada: Panel Derecho Pro Density CSS-only, con tabs, scroll, formularios y paneles mas compactos
  - Fase 10.3 completada: Agent SDK UX Surface v2, con `summarize_editor_ux_surface()` ampliado
  - Fase 10.4 completada: QA visual/regresion; advisor tests `12 passed`; Playwright manual funciona desde Git CMD y `WinError 5` queda acotado al entorno Codex
  - Separacion modular Fase 1 completada: tests de caracterizacion antes de extraer responsabilidades
  - Separacion modular Fase 2 completada: `services/editor_offset_http_service.py` y `routes.py` como wrapper compatible
  - Separacion modular Fase 3 completada: `services/editor_offset_output_service.py` y wrapper compatible en `montaje_offset_inteligente.py`
  - Separacion modular Fase 4 completada: IA repeat deja de depender de `routes.py`
  - Separacion modular Fase 5A completada: modulos puros frontend (`dom_refs`, `defaults`, `geometry`, `geometry_validation`)
  - Separacion modular Fase 5B completada: modulos API/paneles (`api_client`, `output_panel`, `ai_panel`, `ctp_panel`, `booklet_panel`)
  - Separacion modular Fase 5C completada: `renderer_canvas.js` extraido inicialmente con wrappers compatibles
  - Separacion modular Fase 5D-1 completada: caracterizacion Playwright de herramientas manuales
  - Separacion modular Fase 5D-2 completada: `manual_tools.js` extraido inicialmente sin listeners propios
  - Separacion modular Fase 5D-3 completada: `slot_interactions.js` extrae seleccion simple/multiple y helpers de seleccion
  - Separacion modular Fase 5D-4 completada: box select extraido dentro de `slot_interactions.js`, manteniendo listeners en el entrypoint
  - Separacion modular Fase 5D-5 completada: drag/move no-resize extraido inicialmente en `slotInteractions.dragResize`
  - Fase DOC-Encoding completada: correccion dirigida de textos visibles con mojibake, sin tocar contratos ni logica
  - Fase 6-0 completada: auditoria SAFE del frontend post 5D-5, sin modificar archivos
  - Fase 6A documental completada: fuentes de verdad y roadmap modular 6A-6E consolidados
  - Fase 6B completada: cobertura Playwright de workflows productivos en `tests/playwright/test_editor_productive_workflows.py`
  - Fase 6C-0 completada: auditoria SAFE de reorganizacion fisica y decision de avanzar por subfases
  - Fase 6C-1 completada: modulos puros movidos a `static/js/editor_offset_visual/core/` conservando entrypoint y namespace

## Roadmap activo de separacion modular SAFE

### Fases completadas

- Fase 1: caracterizacion y seguridad antes de mover codigo.
- Fase 2: fachada backend del Editor Visual IA sin cambiar URLs ni JSON.
- Fase 3: output preview/PDF del editor extraido sin cambiar `slot_box_final`, `rotation_deg`, `face` ni `design_ref`.
- Fase 4: IA repeat normalizada sobre el motor canonico `engines.step_repeat_pro_engine`.
- Fase 5A: extraccion frontend de defaults, DOM refs, geometria pura y validacion geometrica.
- Fase 5B: extraccion frontend de cliente API y paneles IA/CTP/cuadernillos/salida.
- Fase 5C: extraccion inicial de renderer/canvas/sheet en `static/js/editor_offset_visual/renderer_canvas.js`.
- Fase 5D-1: caracterizacion Playwright de seleccion y herramientas manuales en `tests/playwright/test_editor_manual_interactions.py`.
- Fase 5D-2: extraccion inicial de herramientas manuales puras en `static/js/editor_offset_visual/manual_tools.js`.
- Fase 5D-3: extraccion inicial de seleccion simple/multiple y helpers en `static/js/editor_offset_visual/slot_interactions.js`.
- Fase 5D-4: extraccion inicial de box select dentro de `slot_interactions.js`, con cobertura Playwright minima.
- Fase 5D-5-0: caracterizacion Playwright de drag/resize en `tests/playwright/test_editor_drag_resize_interactions.py`.
- Fase 5D-5: extraccion inicial de drag/move no-resize en `slotInteractions.dragResize`.
- Fase DOC-Encoding: correccion dirigida de mojibake en textos visibles, comentarios y mensajes seguros.
- Fase 6-0: auditoria SAFE del frontend post 5D-5.
- Fase 6A: consolidacion documental/arquitectonica SAFE.
- Fase 6B: cobertura Playwright de workflows productivos (`front/back`, zoom, save, Step & Repeat UI, undo, upload PDF, apply_imposition, preview y generar_pdf).
- Fase 6C-0: auditoria SAFE de reorganizacion fisica del frontend.
- Fase 6C-1: movimiento de `defaults.js`, `geometry.js` y `geometry_validation.js` a `static/js/editor_offset_visual/core/`.

### Fases pendientes de alto riesgo

- Resize operativo: sigue latente; no hay handles activos en el renderer actual y no debe activarse sin fase propia.
- Listeners globales y temporales: `document.keydown`, `document.click`, `window.resize`, `sheetEl.pointerdown`, `document.pointermove/pointerup/pointercancel` siguen en el entrypoint.
- Fase 6C-2: mover `dom_refs.js` y `api_client.js` con orden de carga y namespace protegidos.
- Fase 6C-3: mover paneles (`output_panel.js`, `ai_panel.js`, `ctp_panel.js`, `booklet_panel.js`) sin cambiar UX ni listeners.
- Fase 6C-4: mover renderer/interacciones (`renderer_canvas.js`, `manual_tools.js`, `slot_interactions.js`) solo con wrappers/aliases y validaciones especificas.
- Fase 6C-5: sincronizar advisor/tests/docs y limpiar aliases solo si la compatibilidad ya esta probada.
- Fase 6D futura: evaluar store/state architecture solo si el entrypoint deja de escalar de forma manejable.
- Fase 6E futura: resize real, separado y con caracterizacion previa; no mezclar con reorganizacion fisica.

### Validacion base post 5D-5

- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, `53 passed`.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_manual_interactions.py -s`: OK, `3 passed` con Flask temporal local.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_drag_resize_interactions.py -s`: OK, `4 passed` con Flask temporal local.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_productive_workflows.py -s -p no:cacheprovider`: OK local, `4 passed`.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_load.py -s -p no:cacheprovider`: OK local, `1 passed`.
- `git diff --check`: OK.
- `node --check`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex; no tocar configuracion del sistema.

## Plan propuesto por fases

### Fase 1. Congelar mapa actual

- mantener esta documentacion actualizada
- confirmar que el alcance de la rama es solo `/editor_offset_visual`
- evitar cambios en rutas offset legacy salvo correcciones puntuales justificadas

### Fase 2. Delimitar fronteras

- definir frontera entre:
  - editor visual IA nuevo
  - flujos offset legacy
  - motores reutilizables
- marcar dependencias reales y dependencias accidentales

### Fase 3. Congelar contratos

- documentar payload minimo de:
  - `layout_json`
  - `designs[]`
  - `slots[]`
  - `ctp`
  - `export_settings`
- documentar que endpoints son canonicos para el editor

### Fase 4 historica. Auditoria tecnica puntual

- revisar coherencia de:
  - bleed
  - crop marks
  - `forms_per_plate`
  - `face`
  - `rotation_deg`
  - `slot_box_final`
- detectar que reglas se resuelven en frontend y cuales en backend

### Fase 4 actual. Editor Offset PRO

Objetivo de la rama `fase4-editor-offset-pro`:

- mejorar la edicion manual sin tocar flujos legacy
- sumar herramientas de precision para operadores
- mantener contrato de layout compatible
- documentar cada herramienta incorporada

Bloques implementados:

- alineacion de seleccion
- distribucion horizontal y vertical
- nudge por botones y teclado
- paso configurable en mm
- `Shift x10` y `Alt x0.1`
- duplicado/borrado multi-slot
- proteccion de slots bloqueados
- correccion visual y de encoding de la toolbar PRO
- seleccion de todos los slots de la cara activa
- centrado horizontal, vertical y completo de bloque
- `Ctrl/Cmd + A`
- simplificacion de toolbar:
  - acciones rapidas visibles
  - herramientas tecnicas en panel avanzado
- seleccion por marco desde area vacia del pliego
- `Shift/Ctrl/Cmd + drag` para sumar seleccion
- correcciones profundas de Step & Repeat PRO:
  - `bleed_mm = 0` respetado como valor explicito
  - spacing desde `spacingSettings`
  - rotacion inteligente por capacidad
  - intercambio real de `w_mm/h_mm` al rotar
  - eliminacion de stretch en PDF
  - semantica consolidada de slot rotado
  - centrado global correcto en PDF normal
- base `ai_agent/` con tools repeat y controller
- endpoint `POST /ai/step_repeat_action`
- endpoint `POST /ai/step_repeat_action_openai` para el panel actual con OpenAI lazy
- panel "Asistente IA" integrado al editor

### Fase 4 siguiente. IA operativa guiada

Objetivo:

- mantener la capa `ai_agent/` como intermediaria entre UI, LLM y funciones reales
- conectar OpenAI tool calls sin permitir que el LLM modifique layout directamente
- ampliar tools con acciones verificables y reversibles
- registrar respuestas y sugerencias de forma no destructiva hasta que el usuario aplique cambios

### Fase 5. Step & Repeat PRO Inteligente

Estado real de esta rama:

- Fase 5.1.a:
  - metadata por diseno para repeat
  - ordenamiento base compatible con layouts viejos
- Fase 5.1.b:
  - UI minima inicial para preferencias por diseno
- Fase 5.2:
  - zonas reales basicas por bandas
- Fase 5.3:
  - `fill` inteligente para huecos utiles restantes
- Fase 5.4:
  - simplificacion UX:
    - solo queda visible `Ubicacion`
    - `priority`, `repeat_role` y `preferred_flow` pasan a logica interna
  - textos amigables en UI
  - `preferred_flow` reservado pero inactivo
- Fase 5.5:
  - compactacion vertical segura de grupos zonales
- Fase 5.6:
  - validacion estricta de formas solicitadas vs colocadas
  - error bloqueante para montajes incompletos
  - generacion atomica por diseno
  - aislamiento de ejecuciones para evitar contaminacion entre corridas
  - expansion vertical inteligente de zonas `top/center/bottom`
- Fase 5.7:
  - correccion de `center` rigido
  - expansion vertical para una sola zona `center`
  - expansion vertical para multiples disenos dentro de la misma zona:
    - `top/top`
    - `bottom/bottom`
    - `center/center`
  - mantenimiento de anclaje:
    - `top` hacia arriba
    - `bottom` hacia abajo
    - `center` centrado
- Fase 5.8:
  - compactacion final segura que incluye `auto` cuando convive con `top/center/bottom`
  - preservacion del comportamiento legacy cuando todo esta en `auto`
- Fase 5.9:
  - tools IA alineadas con el motor:
    - `set_design_zone`
    - `set_design_zones`
    - `generar_repeat`
    - `validar_repeat`
    - `optimizar_repeat`
  - soporte de referencias por dimensiones como `50x40`
  - encadenamiento de tools y preservacion del layout generado
  - distincion frontend entre `metadata_only` y `layout_with_slots`

Decisiones consolidadas:

- `preferred_zone` es el control principal visible
- `priority` y `repeat_role` se derivan automaticamente cuando no hay override manual
- `preferred_flow` se conserva en contrato pero no participa todavia del motor
- `slot.w_mm/h_mm` sigue siendo footprint final en `repeat`
- `rotation_deg` sigue siendo orientacion del contenido
- el modo actual es exacto respecto de `forms_per_plate`; no existe todavia modo `maximize`

### Fase 6 historica. Simulador de Cuadernillos

Estado real:

- modulo aislado `cuadernillos/simulator.py`
- endpoint `POST /editor_offset/cuadernillos/simular`
- panel integrado al Editor Visual IA
- soporte para cosido a caballete
- soporte para `sin_tapa` y `tapa_completa`
- selector de cuadernillo 8 / 16
- tapa completa como VYV 4 de cara unica
- tripa separada
- VYV 4 y VYV 8 automaticos para restos parciales
- patrones reales auditables para 8 y 16 paginas
- metadata visual de orientacion cabeza con cabeza
- render diferenciado de TAPA, TRIPA, frente/dorso y VYV

Limites:

- no modifica `layout_constructor.json`
- no crea `slots[]`
- no toca Step & Repeat PRO
- no genera preview ni PDF final

### Fase 7. Estabilidad y validacion de salida

Estado real:

- Fase 7.1 agrega tests de contrato de salida en `tests/test_editor_offset_output_contract.py`
- Fase 7.2 extrae la validacion backend a `services/editor_offset_output_contract.py`
- `routes.py` conserva alias compatible para `_validate_constructor_output_layout`
- no cambia JSON, contratos, preview/PDF, frontend JS ni motores
- se agrega una mejora visual safe en CSS para botones, paneles, accordion y foco visible

Objetivo cerrado:

- blindar la validacion backend actual sin agregar reglas nuevas
- reducir deuda en `routes.py` de forma conservadora
- dejar base testeable para futuras validaciones
- mejorar lectura visual del editor sin tocar comportamiento

### Fase 8. Arquitectura SAFE y UX shell

Estado real:

- Fase 8.0 completada: mapa funcional/técnico del Editor Visual IA.
- Fase 8.1 completada: `services/editor_offset_jobs.py`, `services/editor_offset_layout_defaults.py`, `services/editor_offset_uploads.py`.
- Fase 8.1B completada: `engines/step_repeat_pro_engine.py` y `tests/test_step_repeat_pro_engine.py`.
- Fase 8.1C completada: `services/editor_offset_imposition_service.py`.
- Fase 8.2 completada: shell UX profesional con toolbar sticky, canvas central y panel derecho con scroll interno.
- Fase 8.3 completada: tabs del panel derecho y fix de scroll.
- Premium Visual Pass SAFE completado: refinamiento visual CSS-only, densidad tecnica, contraste, canvas, toolbar, tabs, panel derecho, inputs y estados visuales.
- Microfase de contraste completada: Snap, Espaciado, labels secundarios, unidades mm, inputs tecnicos y botones claros.
- QA inicial completada:
  - `tests/playwright/test_editor_load.py`
  - `tests/playwright/test_tabs_scroll.py`

Garantias:

- `routes.py` conserva wrappers compatibles.
- no se cambiaron contratos JSON.
- no se cambio preview/PDF.
- no se tocaron motores de salida.
- no se toco JS funcional ni backend durante el premium visual pass.

Decision UX:

- no se agrego una barra inferior contextual nueva.
- `geometry-validation-panel` ya opera como area contextual/status parcial.
- cualquier status bar futura deberia evolucionar o compactar ese bloque, no duplicarlo.

### Fase 9. Redisenio panel editor, documentacion base y agente SDK

Estado real:

- rama actual: `fase9-redisenio-panel-editor`
- el panel derecho sigue evolucionando sobre la base de tabs/scroll interno de Fase 8
- se creo `ai_agent/editor_advisor/` como prototipo OpenAI Agents SDK
- el agente SDK es CLI-only/read-only, sin Flask, sin endpoints y sin UI
- el agente usa `AGENTS.md` y `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md` como contexto arquitectonico clave
- Fase 9.2 completada: el agente SDK ahora actua como UX/UI SAFE Advisor del Editor Visual IA
- Fase 9.2 agrega `summarize_editor_ux_surface()` para detectar tabs, paneles, ids criticos, listeners, selectores sensibles y `geometry-validation-panel`
- Fase 9.2 clasifica cambios como `CSS-only seguro`, `HTML/DOM riesgoso`, `JS/listeners riesgoso` y `backend/contrato prohibido`
- Fase 9.3 completada: refinamiento visual CSS-only del panel derecho, aplicado solo sobre `static/css/editor_offset_visual.css`
- Fase 9.3 mejora `.side-panel`, `.editor-tabs`, scroll interno, accordions, formularios, `geometry-validation-panel`, foco visible y estetica premium tecnica sin cambiar DOM ni listeners
- Fase 9.4 completada: el agente genera `prompt_para_codex` para convertir auditorias en prompts SAFE listos para Codex
- Fase 9.4 agrega `--codex-prompt-only` para imprimir solo el prompt accionable, sin JSON

Prioridades SAFE:

- mantener documentacion base alineada con el codigo real
- no integrar `editor_advisor` a Flask/UI sin fase separada
- no permitir que `editor_advisor` escriba archivos ni modifique HTML/JS automaticamente
- sostener workflow: agente audita -> genera prompt SAFE para Codex -> Codex planifica -> Codex implementa solo si se aprueba -> validaciones -> agente vuelve a auditar
- ampliar Playwright para drag, resize, seleccion y flujos productivos
- evolucionar `geometry-validation-panel` solo si aporta valor y sin duplicar informacion
- evaluar inspector contextual y modularizacion frontend como cambios separados

### Fase 10. Editor UX Canvas Pro

Estado real:

- Fase 10.0 completada: auditoria visual y baseline sin modificar archivos.
- Fase 10.1 completada: refinamiento CSS-only del shell superior/topbar/subtoolbar para dar mas protagonismo al canvas.
- Fase 10.2 completada: refinamiento CSS-only de density del panel derecho, manteniendo tabs, scroll interno, ids y listeners.
- Fase 10.3 completada: `ai_agent/editor_advisor/` incorpora UX Surface v2; `summarize_editor_ux_surface()` ahora audita header, topbar, subtoolbar, workspace, canvas, zoom, panel derecho, ids por zona y listeners sensibles.
- Fase 10.4 completada: QA visual y regresion documentation-safe; `git diff --check`, `python -m compileall ai_agent`, `tests/test_editor_advisor_tools.py` con `12 passed`, revision estatica de selectores criticos y `geometry-validation-panel` unico.
- Actualizacion SAFE post Fases 1-5B del Editor Advisor SDK completada: allowlist read-only ampliada a servicios HTTP/output, modulos JS 5A/5B e IA operativa; resumen arquitectonico actualizado; nuevo resumen modular 5A/5B; prompt del advisor reenfocado a auditoria estructural post 1-5B sin perder UX SAFE.

Garantias:

- no se cambiaron contratos JSON.
- no se tocaron HTML, JS, Flask, services, engines, Step & Repeat PRO, preview/PDF, CTP ni cuadernillos.
- `editor_advisor` sigue CLI-only/read-only, sin Flask/UI/endpoints ni escritura.
- Playwright manual funciona desde Git CMD; `WinError 5` queda registrado solo como bloqueo del entorno Codex.

### Fase 5C. Renderer Canvas Inicial

Objetivo:

- `renderer_canvas.js` ya fue implementado como extraccion inicial del renderer/canvas/sheet.
- `static/js/editor_offset_visual.js` conserva wrappers compatibles para render, zoom y panel geometrico.
- se separa explicitamente renderer visual de interacciones complejas, ya extraidas parcialmente en Fase 5D mediante `manual_tools.js` y `slot_interactions.js`.

Mapa de dependencias actual:

- `renderSheet` recalcula validacion geometrica, dimensiona `#sheet`, limpia y recrea slots, aplica clases visuales, registra listeners por slot, renderiza guia CTP, aplica zoom, renderiza indicador de distancia y actualiza `geometry-validation-panel`.
- `recalcScale`, `mmToPx`, `applyZoom` y `sheetPointFromEvent` dependen de `#sheet-canvas`, `#sheet`, `state.scale`, `state.zoom` y `layout.sheet_mm`.
- `renderCtpGuideOverlay` depende de `layout.ctp.enabled`, `layout.ctp.show_guide`, `layout.ctp.gripper_mm` y solo debe mostrarse en cara `front`.
- los estados visuales de slot dependen de `slot.locked`, `state.selectedSlot`, `state.selectedSlots` y `state.geometryValidation.bySlot`.
- el indicador de distancia depende de `state.distanceIndicator` y se renderiza dentro de `#sheet`.

Contrato interno implementado inicialmente:

- modulo: `static/js/editor_offset_visual/renderer_canvas.js`.
- no debe registrar listeners globales ni mutar `state.layout`, seleccion, historial, drag state o contratos.
- debe recibir dependencias explicitas: `sheetEl`, `sheetCanvas`, elementos del panel geometrico, `layout`, `activeFace`, `scale`, `zoom`, seleccion, `distanceIndicator`, helpers de geometria y callbacks de interaccion.
- funciones esperadas:
  - `recalcSheetScale({ sheetCanvas, layout, minScale })`
  - `applySheetZoom({ sheetEl, zoom, zoomLabelEl })`
  - `buildVisibleSlotViewModels({ layout, activeFace, selectedSlotId, selectedSlotIds, geometryValidation })`
  - `renderSheetSurface(context)`
  - `renderCtpGuide({ sheetEl, ctp, activeFace, mmToPx })`
  - `renderGeometryValidationPanel({ validation, activeFace, summaryEl, listEl })`
  - `renderDistanceIndicator({ sheetEl, distanceIndicator, activeFace, mmToPx })`
- los callbacks `onSlotPointerDown` y `onSlotClick` siguen entrando desde `static/js/editor_offset_visual.js`; el entrypoint conserva wiring, listeners, pointer capture/release y wrappers compatibles.

Fuera de alcance que sigue vigente:

- no mover DOM, no renombrar IDs, no tocar `data-editor-tab` ni `data-editor-tab-panel`.
- no tocar resize latente, shortcuts ni listeners globales sin fase propia.
- no tocar backend, services, engines, preview/PDF, CTP productivo, cuadernillos, Step & Repeat PRO ni contratos JSON.

Checklist de caracterizacion renderer/canvas:

- `#sheet`, `#sheet-canvas` y `#geometry-validation-panel` existen una sola vez.
- cambio de `sheet_mm` actualiza ancho/alto visual del pliego.
- zoom por botones y `Ctrl + wheel` conserva escala visible y label.
- cambio de cara filtra slots `front`/`back` sin mezclar seleccion.
- slots conservan clases `.selected`, `.locked`, `.geometry-warning` y `.geometry-error`.
- guia `.ctp-guide` aparece solo en `front` cuando CTP esta activo y `show_guide` esta habilitado.
- indicador `.distance-indicator` aparece durante drag real y se oculta al finalizar.
- `geometry-validation-panel` muestra resumen y lista de errores/warnings de la cara activa.
- resize de ventana recalcula escala y re-renderiza sin romper slots.

Clasificacion SAFE:

- CSS-only seguro: pulido visual de selectores existentes sin ocultar controles.
- HTML/DOM riesgoso: mover `#sheet`, `#sheet-canvas`, `#geometry-validation-panel`, tabs o paneles.
- JS/listeners riesgoso: `renderSheet`, zoom, slot click, pointerdown, box select, drag, resize, nudge, align y distribute.
- backend/contrato prohibido: rutas, services, engines, contratos JSON, preview/PDF, CTP productivo, cuadernillos y Step & Repeat PRO.

### Fase 5D-0. Auditoria SAFE De Interacciones Complejas

Objetivo:

- auditar seleccion, multi-seleccion, box select, drag, resize, nudge, align, distribute, group/ungroup y shortcuts antes de extraerlos a modulos.
- congelar contratos para `slot_interactions.js` y `manual_tools.js`.
- mantener la frontera con `renderer_canvas.js`: el renderer pinta slots y recibe `attachSlotHandlers`, pero la interaccion sigue en el entrypoint hasta fases posteriores.

Mapa funcional actual:

- seleccion: `selectSlot`, `getSelectedSlotIds`, `getSelectedSlots`, `selectAllSlotsOnActiveFace`, `refreshSelectionAfterEdit`.
- box select: `sheetPointFromEvent`, `getBoxSelectionRectMm`, `renderBoxSelectionRect`, `clearBoxSelectionRect`, `resetBoxSelectState`, `selectSlotsInBox`, `startBoxSelect`, `moveBoxSelect`, `endBoxSelect`.
- drag/resize: `startDrag`, `moveDrag`, `endDrag`, `onSlotPointerDown`.
- herramientas manuales: `duplicateSlot`, `deleteSlot`, `groupSelectedSlots`, `ungroupSelectedSlots`, `alignSelectedSlots`, `distributeSelectedSlots`, `centerSelectedBlock`, `nudgeSelectedSlots`, `applyGapToSlots`, `applySpacing`.
- listeners criticos: `attachSlotHandlers` pasado a `renderer_canvas.js`, `sheetEl.pointerdown`, listeners temporales `document.pointermove/pointerup/pointercancel`, `document.click`, `document.keydown`, botones `btn-*` de herramientas PRO.

Dependencias de estado:

- `state.selectedSlot`, `state.selectedSlots`, `state.activeFace`, `state.layout.slots`, `state.scale`, `state.zoom`, `state.spacingSettings`.
- `dragState` para pointer activo, slot inicial, handle, grupo, posiciones iniciales y movimiento.
- `boxSelectState` para rectangulo, pointer activo, modo aditivo, supresion de click-clear y handlers temporales.
- helpers de geometria: `getEffectiveSlotBox`, `slotCoordsFromBox`, `slotFootprintRect`, `getSelectionBounds`, `groupSlotsByRow`, `groupSlotsByColumn`, `roundMm`.
- callbacks actuales: `renderSheet`, `renderSlotForm`, `pushHistory`, `applySnap`, `applySpacing`, `updateDistanceIndicator`, `hideDistanceIndicator`.

Contrato implementado y estado actual:

- `slot_interactions.js`:
  - concentra seleccion simple/multiple, helpers de seleccion, box select y drag/move no-resize.
  - expone subcontroladores bajo `window.EditorOffsetVisual.slotInteractions`, incluyendo `boxSelect` y `dragResize`.
  - recibe estado, geometria y callbacks explicitos desde el entrypoint; no debe tocar DOM estructural ni backend.
- `manual_tools.js` implementado:
  - concentra duplicar, borrar, agrupar, desagrupar, alinear, distribuir, centrar, nudge, gap y spacing.
  - preserva historial, seleccion, render y lectura DOM mediante wrappers del entrypoint.
  - no registra listeners ni accede al DOM por su cuenta.

Que no debe moverse todavia:

- `document.keydown`, `document.click`, `window.resize` y wiring de botones `btn-*`.
- `sheetEl.pointerdown`, listeners temporales de pointer y pointer capture/release.
- resize operativo: sigue latente porque no hay handles activos en el renderer actual.
- shortcuts globales.
- clases/IDs `.slot`, `.selected`, `.locked`, `.box-selection-rect`, `#sheet`, `#sheet-canvas`, `slot-*`.
- contratos JSON, backend, preview/PDF, CTP productivo, cuadernillos, engines y services.

Plan por fases 5D:

- Fase 5D-1 completada: caracterizacion Playwright de seleccion simple/multiple, Ctrl+A, duplicate/delete, group/ungroup, nudge, align y distribute.
- Fase 5D-2 completada: extraer `manual_tools.js` para operaciones sin listeners, manteniendo wrappers en entrypoint.
- Fase 5D-3 completada: extraer controlador de seleccion en `slot_interactions.js`, manteniendo wiring en entrypoint.
- Fase 5D-4 completada: extraer box select con cobertura de click vs drag y seleccion aditiva.
- Fase 5D-5-0 completada: caracterizar drag/resize por UI publica; resize queda latente por ausencia de handles activos.
- Fase 5D-5 completada: extraer drag/move no-resize en `slotInteractions.dragResize`, manteniendo listeners, pointer capture, render, historial, spacing live e indicador de distancia en entrypoint.

### Fase 11 futura. Canvas Geometry Polish

Objetivo futuro:

- pulir la lectura geometrica y visual del canvas sin cambiar contratos ni motores.
- mantener como base el shell Fase 10 y el `geometry-validation-panel` unico.
- separar cualquier cambio HTML/JS o de interaccion en fases SAFE especificas.

## Priorizacion sugerida

1. Mantener documentados los contratos despues de cada cambio de semantica.
2. Ejecutar Fase 6C-2: mover `dom_refs.js` y `api_client.js` con aliases/wrappers y orden de carga protegidos.
3. Mantener Playwright load, tabs, manual, drag/resize y workflows productivos como red de regresion antes de cada subfase 6C.
4. Preparar Fase 6C-3 solo despues de validar 6C-2, sin mover paneles en bloque si aparecen dependencias cruzadas.
5. Endurecer guardrails y pruebas del flujo OpenAI tool calling sobre `ai_agent/`.
6. Mantener `ai_agent/editor_advisor` aislado, read-only y CLI-only hasta definir integracion, aunque genere prompts para Codex.
7. Evaluar Fase 6D store/state architecture solo si la orquestacion del entrypoint deja de ser manejable.
8. Evaluar Fase 6E resize real en fase separada, sin declarar resize operativo antes de handles activos y caracterizacion.
9. Mejorar feedback no bloqueante de errores/warnings.
10. Avanzar en schema/validaciones adicionales solo con tests dedicados.
11. Mantener el simulador de cuadernillos aislado hasta definir una integracion PDF explicita.

## Cambios explicitamente postergados

- fusionar todos los motores offset
- borrar rutas legacy
- mover muchas funciones fuera de `routes.py` sin tests; Fase 7 solo extrajo el validador de salida con cobertura dedicada
- reescribir el JS del editor
- modularizar frontend monolitico sin fase propia y pruebas de regresion
- redisenar persistencia por job
- permitir que IA modifique persistencia sin confirmacion del usuario
- integrar `ai_agent/editor_advisor` a Flask/UI sin fase tecnica separada, guardrails y tests
- cambiar el contrato base de `layout_constructor.json` sin migracion
- documentar `preferred_flow` como funcional antes de implementarlo
- declarar soporte de expansion horizontal `left/right` antes de tener motor y pruebas
- convertir el simulador de cuadernillos en generador de PDF sin fase tecnica separada
- persistir resultados del simulador en el layout sin contrato previo
- agregar una barra inferior contextual que duplique `geometry-validation-panel` sin redisenio previo

## Criterio de seguridad para siguientes pasos

Todo cambio futuro en este modulo deberia responder antes:

- afecta solo `/editor_offset_visual` o tambien otro flujo offset
- toca contrato de `layout_json`
- cambia semantica de slot/bleed/face/ctp
- modifica salida final de `montaje_offset_inteligente.py`

Si alguna respuesta es "si", conviene abrir subtarea especifica y documentarla antes de editar.

Para nuevas validaciones posteriores a Fase 7:

- agregar primero tests de contrato
- no cambiar textos, `code`, `path`, `value` ni estructura de errores sin fase explicita
- mantener preview/PDF consumiendo el layout persistido desde disco
