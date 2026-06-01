# 14 MAPA FUNCIONAL EDITOR VISUAL IA

Este documento es la fuente de verdad arquitectonica actual del **Editor Visual IA / Editor Offset Visual**. Debe servir como mapa rapido para Codex, agentes SDK y desarrolladores humanos antes de tocar frontend, backend, motores, output, contratos o UX.

El detalle cronologico de fases vive en `DOCS/OFFSET/05_DIARIO_OFFSET.md`. El roadmap futuro vive en `DOCS/OFFSET/04_PLAN_OFFSET.md`. Las reglas operativas para agentes viven en `AGENTS.md`. El estado ejecutivo vive en `DOCS/OFFSET/02_ESTADO_OFFSET.md`.

## Estado Actual Canonico

El Editor Visual IA es el flujo principal y mas moderno del modulo offset. Funciona como un constructor visual por job para preparar montajes profesionales de imprenta:

1. carga o inicializa un `layout_constructor.json`
2. permite configurar pliego, trabajos logicos, PDFs, formas, bleed, spacing y CTP
3. permite generar slots automaticamente con Step & Repeat PRO, nesting o hybrid
4. permite editar manualmente slots con seleccion, drag, resize y herramientas PRO
5. permite simular cuadernillos como herramienta visual aislada
6. guarda el layout persistido por job
7. genera preview y PDF final desde el layout persistido

Estado del roadmap activo de separacion modular:

- Fase 1 completada: tests de caracterizacion antes de extraer responsabilidades.
- Fase 2 completada: fachada HTTP del editor en `services/editor_offset_http_service.py`; `routes.py` conserva endpoints publicos y wrappers compatibles.
- Fase 3 completada: salida preview/PDF del editor en `services/editor_offset_output_service.py`; `montaje_offset_inteligente.py` conserva wrapper compatible y funciones legacy.
- Fase 4 completada: `ai_agent/tools_repeat.py` usa `engines.step_repeat_pro_engine.build_step_repeat_slots` y ya no depende de helpers internos de `routes.py`.
- Fase 5A completada: modulos puros frontend `dom_refs.js`, `defaults.js`, `geometry.js`, `geometry_validation.js`.
- Fase 5B completada: modulos frontend de red/paneles `api_client.js`, `output_panel.js`, `ai_panel.js`, `ctp_panel.js`, `booklet_panel.js`.

Fase 10 queda como baseline UX historica cerrada: shell/topbar CAD-preprensa, canvas mas protagonista, panel derecho mas denso, `geometry-validation-panel` unico y agente SDK con UX Surface v2.

## Arquitectura Actual

### Frontend

- Template: `templates/editor_offset_visual.html`.
- Entrypoint compatible: `static/js/editor_offset_visual.js`.
- Estilos principales: `static/css/editor_offset_visual.css`.
- Modulos auxiliares: `static/js/editor_offset_visual/`.

Modulos 5A/5B activos:

- `dom_refs.js`: IDs y referencias DOM criticas.
- `defaults.js`: defaults y normalizadores puros.
- `geometry.js`: geometria pura.
- `geometry_validation.js`: validacion geometrica frontend.
- `api_client.js`: llamadas HTTP del editor.
- `output_panel.js`: preview/PDF y errores de salida.
- `ai_panel.js`: panel IA operativo del editor.
- `ctp_panel.js`: panel CTP y alineacion.
- `booklet_panel.js`: panel del simulador de cuadernillos.

`static/js/editor_offset_visual.js` sigue siendo el entrypoint y mantiene zonas sensibles todavia no extraidas: `renderSheet`, seleccion, drag, resize, box select, nudge, align, distribute, historia/estado global y partes del render del pliego.

### Backend Flask Y Servicios

- `routes.py`: wrapper Flask compatible; expone URLs publicas y aliases legacy.
- `services/editor_offset_http_service.py`: fachada HTTP del Editor Visual IA.
- `services/editor_offset_jobs.py`: paths, job_id, carga/guardado de layouts.
- `services/editor_offset_layout_defaults.py`: defaults y normalizacion de layout.
- `services/editor_offset_uploads.py`: upload de PDFs y metadata `designs[]`.
- `services/editor_offset_imposition_service.py`: selector `repeat`/`nesting`/`hybrid`.
- `services/editor_offset_output_contract.py`: validacion minima antes de preview/PDF.
- `services/editor_offset_output_service.py`: salida preview/PDF del editor.

### Engines Y Output

- Motor principal: `engines/step_repeat_pro_engine.py`.
- Motor auxiliar: `engines/nesting_pro_engine.py`.
- Compatibilidad/legacy de salida: `montaje_offset_inteligente.py`.
- Estrategias legacy/reutilizables: `strategies/*`.

El motor prioritario actual del Editor Visual IA es **Step & Repeat PRO automatico**. `nesting` y `hybrid` existen como motores alternativos conectados desde `services/editor_offset_imposition_service.py`, pero no reemplazan al motor principal.

### IA Y Agente SDK

- IA operativa del panel: `ai_agent/tools_repeat.py`, `ai_agent/openai_tool_bridge.py`, `ai_agent/agent_controller.py`.
- Agente asesor SDK: `ai_agent/editor_advisor/`.

El panel IA del editor aplica Step & Repeat y preferencias de layout. El agente SDK `editor_advisor` es distinto: CLI-only/read-only, sin Flask, sin endpoints, sin UI y sin herramientas de escritura. Usa `AGENTS.md` y este documento como memoria arquitectonica principal.

Actualizacion SAFE del advisor post Fases 1-5B:

- `ai_agent/editor_advisor/tools.py` puede auditar en modo allowlist/read-only `services/editor_offset_http_service.py`, `services/editor_offset_output_service.py`, los 9 modulos frontend 5A/5B y la IA operativa `ai_agent/tools_repeat.py` / `ai_agent/openai_tool_bridge.py`.
- `summarize_editor_architecture()` reconoce `routes.py` como wrapper compatible, `editor_offset_http_service.py` como fachada HTTP, `editor_offset_output_service.py` como salida real del editor y `montaje_offset_inteligente.py` como wrapper legacy.
- `summarize_editor_modular_surface()` resume modulos cargados por HTML, modulos presentes en disco, exports `window.EditorOffsetVisual.*`, responsabilidades criticas aun en `static/js/editor_offset_visual.js` y riesgos pendientes Fase 5C/5D/6.
- `summarize_editor_ux_surface()` lee el JS completo del entrypoint para evitar subconteos de listeners o IDs por truncado.

### Simulador De Cuadernillos

- Motor aislado: `cuadernillos/simulator.py`.
- Endpoint: `POST /editor_offset/cuadernillos/simular`.
- Panel frontend: `booklet_panel.js`.

El simulador no modifica `layout_constructor.json`, no crea `slots[]`, no genera PDF final y no toca Step & Repeat PRO.

## Flujo Funcional Actual

1. El usuario entra a `GET /editor_offset_visual`.
2. `routes.py` mantiene la URL publica y delega la logica del editor a servicios.
3. Se crea o carga el job desde `static/constructor_offset_jobs/<job_id>/layout_constructor.json`.
4. El frontend inicializa `static/js/editor_offset_visual.js` y modulos auxiliares 5A/5B.
5. El usuario configura pliego, trabajos logicos, disenos, forms per plate, spacing, bleed, caras y CTP.
6. `POST /editor_offset/upload/<job_id>` guarda PDFs y actualiza `designs[]`.
7. `POST /editor_offset_visual/apply_imposition` aplica `repeat`, `nesting` o `hybrid`.
8. `repeat` usa `engines.step_repeat_pro_engine.build_step_repeat_slots`.
9. El usuario edita manualmente slots con herramientas PRO.
10. El panel IA puede ajustar metadata o generar repeat mediante tools locales.
11. El simulador de cuadernillos opera como consulta visual independiente.
12. El usuario guarda con `POST /editor_offset/save`.
13. Preview/PDF guardan primero y luego releen el layout persistido.
14. `services.editor_offset_output_contract.validate_constructor_output_layout` bloquea errores minimos de contrato.
15. `services.editor_offset_output_service.montar_offset_desde_layout` transforma slots en posiciones frente/dorso.
16. `montaje_offset_inteligente.montar_offset_desde_layout` conserva wrapper compatible para imports legacy.
17. El frontend muestra la imagen preview o el enlace al PDF final.

Endpoints publicos actuales del editor:

- `GET /editor_offset_visual`
- `POST /editor_offset/save`
- `POST /editor_offset/upload/<job_id>`
- `POST /editor_offset/auto_layout/<job_id>`
- `POST /editor_offset_visual/apply_imposition`
- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`
- `POST /editor_offset/cuadernillos/simular`
- `POST /ai/step_repeat_action`
- `POST /ai/step_repeat_action_openai`

## Contratos Y Semanticas Que No Deben Cambiar

No cambiar sin fase propia, tests y autorizacion explicita:

- URLs publicas del editor.
- Formato JSON de entrada/salida de endpoints.
- `layout_constructor.json`.
- `designs[].ref` y referencias desde `slots[].design_ref`.
- `slots[].id`.
- `slot.face` con `front`/`back`.
- `slot.x_mm`, `slot.y_mm`, `slot.w_mm`, `slot.h_mm`.
- `slot.rotation_deg`.
- `slot.slot_box_final`.
- `slot.bleed_mm`.
- `slot.crop_marks`.
- `forms_per_plate`.
- `spacingSettings`.
- `snapSettings`.
- `export_settings`.
- `ctp`.

Semantica consolidada de Step & Repeat PRO:

- `slot.w_mm / slot.h_mm` representan la caja final ocupada por el slot en el pliego.
- `rotation_deg` representa la orientacion del contenido dentro de esa caja.
- En `repeat`, `slot_box_final=True` indica que `w_mm/h_mm` ya son footprint final.
- El frontend no debe volver a rotar la caja externa cuando `w_mm/h_mm` ya representan el footprint.
- El output debe rotar contenido dentro de la caja final sin stretch.
- `forms_per_plate` es exacto: si faltan formas, el motor debe fallar y no aplicar layout parcial.

## Mapa De Dependencias Por Subsistema

### Frontend Productivo

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/*.js`
- `static/css/editor_offset_visual.css`

IDs/listeners criticos:

- `sheet`
- `sheet-canvas`
- `geometry-validation-panel`
- `data-editor-tab`
- `data-editor-tab-panel`
- botones `btn-*`
- inputs `slot-*`
- inputs `ctp-*`
- inputs `ai-*`

No renombrar IDs, no reordenar DOM funcional y no duplicar listeners sin plan especifico.

### Backend Productivo

- `routes.py`
- `services/editor_offset_http_service.py`
- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`
- `services/editor_offset_imposition_service.py`
- `services/editor_offset_output_contract.py`
- `services/editor_offset_output_service.py`

`routes.py` sigue siendo importante porque expone endpoints y compatibilidad. No debe adelgazarse mas sin tests de endpoints y revision de imports legacy.

### Output Y Legacy Compartido

- `services/editor_offset_output_service.py`
- `montaje_offset_inteligente.py`
- `strategies/*`

`services/editor_offset_output_service.py` es la salida del editor. `montaje_offset_inteligente.py` conserva wrapper y funciones legacy compartidas por otros flujos. No mover estrategias todavia sin tests de equivalencia para preview/PDF y rutas legacy.

### Engines

- `engines/step_repeat_pro_engine.py`: motor canonico de Step & Repeat PRO.
- `engines/nesting_pro_engine.py`: nesting auxiliar para `nesting`/`hybrid`.

`services/editor_offset_imposition_service.py` decide que engine aplicar y conserva el bridge hybrid.

### IA

- `ai_agent/tools_repeat.py`: tools locales alineadas con el motor canonico.
- `ai_agent/openai_tool_bridge.py`: puente OpenAI tool calls.
- `ai_agent/agent_controller.py`: controlador de IA local.
- `ai_agent/editor_advisor/`: asesor SDK read-only.

No integrar `editor_advisor` a Flask/UI ni darle tools de escritura sin fase separada, guardrails y tests.

### Tests Relevantes

- `tests/test_editor_offset_characterization.py`
- `tests/test_step_repeat_pro_engine.py`
- `tests/test_editor_offset_output_contract.py`
- `tests/test_cuadernillos_simulator.py`
- `tests/test_editor_advisor_tools.py`
- `tests/playwright/test_editor_load.py`
- `tests/playwright/test_tabs_scroll.py`

Tests legacy relevantes para salida:

- `tests/test_montaje_offset_inteligente.py`
- `tests/test_montaje_offset_inteligente_same_size.py`
- `tests/test_montaje_features.py`
- `tests/test_montaje_offset_personalizado.py`

## Zonas De Alto Riesgo

### Fase 5C Pendiente

Extraer renderer/canvas/sheet es alto riesgo. No tocar sin plan SAFE, cobertura y validacion visual.

Zonas sensibles:

- `renderSheet`
- zoom/canvas/sheet
- CTP guide
- geometry markers
- escalado mm/pixeles
- render de slots frente/dorso
- estados selected/locked/warnings

### Fase 5D Pendiente

Extraer interacciones complejas es alto riesgo. No tocar sin plan SAFE y pruebas especificas.

Zonas sensibles:

- seleccion simple y multiple
- drag
- resize
- box select
- nudge
- align
- distribute
- group/ungroup
- keyboard shortcuts
- listeners acoplados a IDs y clases

### Fase 6 Pendiente

Mover estructura fisica hacia `editor_offset/` es alto riesgo. Solo debe hacerse cuando wrappers, aliases legacy, tests e imports esten estables.

Reglas:

- no mover archivos en bloque
- no romper imports legacy
- dejar aliases temporales
- migrar por subsistema
- validar endpoints y tests antes de continuar

### Output Y Legacy

Riesgos:

- romper `design_ref -> designs[].ref`
- alterar `slot_box_final`
- cambiar `rotation_deg`
- romper frente/dorso por `face`
- cambiar prioridad de export settings
- romper CTP y pinza
- romper rutas legacy que usan `montaje_offset_inteligente.py`

### Agente SDK

Riesgos:

- convertir `editor_advisor` en automatizacion productiva sin guardrails
- darle herramientas de escritura
- conectarlo a Flask/UI sin fase propia
- perder memoria SAFE si este documento elimina contexto critico

## Validaciones Canonicas

Validacion general:

```bash
python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies
```

Tests minimos del cierre Fases 1-5B:

```bash
venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider
```

Validacion de diferencias:

```bash
git diff --check
```

Validacion frontend, si Node esta disponible:

```bash
node --check static/js/editor_offset_visual.js
node --check static/js/editor_offset_visual/api_client.js
node --check static/js/editor_offset_visual/output_panel.js
node --check static/js/editor_offset_visual/ai_panel.js
node --check static/js/editor_offset_visual/ctp_panel.js
node --check static/js/editor_offset_visual/booklet_panel.js
```

En entorno Codex, `node --check` puede fallar por `Acceso denegado` a `node.exe`. Ese caso se registra como bloqueo de entorno y no debe llevar a tocar configuracion del sistema.

Estado de cierre Fase 5B:

- `python -m compileall ...`: OK
- suite minima: OK, `53 passed`
- `git diff --check`: OK
- `node --check`: bloqueado por `Acceso denegado` a `node.exe`

## Historial Breve

- Fase 8: base de arquitectura SAFE, servicios iniciales, extraccion de Step & Repeat PRO a engine, servicio de imposicion, shell UX y tabs.
- Fase 9: documentacion base, `ai_agent/editor_advisor/` como asesor SDK CLI-only/read-only, UX SAFE Advisor y Codex Prompt Builder.
- Fase 10: baseline UX Canvas Pro cerrada; shell/topbar CAD-preprensa, canvas mas protagonista, panel derecho denso y QA visual/regresion documentada.
- Fases 1-5B de separacion modular: caracterizacion, fachada HTTP, output service, IA repeat sin `routes.py`, modulos puros frontend y paneles/API frontend.
- Fase 11: referencia futura de `Canvas Geometry Polish`; no es el roadmap activo inmediato frente a Fase 5C/5D/6.

## Referencias

- Estado ejecutivo: `DOCS/OFFSET/02_ESTADO_OFFSET.md`
- Roadmap futuro: `DOCS/OFFSET/04_PLAN_OFFSET.md`
- Diario historico: `DOCS/OFFSET/05_DIARIO_OFFSET.md`
- Contrato layout: `DOCS/OFFSET/06_CONTRATO_LAYOUT.md`
- Contrato slots: `DOCS/OFFSET/07_CONTRATO_SLOTS.md`
- Validacion de salida: `DOCS/OFFSET/08_VALIDACION_SALIDA.md`
- Validacion geometrica: `DOCS/OFFSET/09_VALIDACION_GEOMETRICA.md`
- Step & Repeat: `DOCS/OFFSET/12_STEP_REPEAT_INTELIGENTE.md`
- Cuadernillos: `DOCS/OFFSET/13_SIMULADOR_CUADERNILLOS.md`
- Reglas para agentes: `AGENTS.md`

## Regla De Mantenimiento

Este documento debe mantenerse compacto. Si una actualizacion agrega cronologia extensa, logs de validacion detallados, prompts o planes fase por fase, mover ese contenido a `05_DIARIO_OFFSET.md` o `04_PLAN_OFFSET.md` y dejar aqui solo el estado canonico actual.
