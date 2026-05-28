# 14 MAPA FUNCIONAL EDITOR VISUAL IA

## Objetivo de Fase 8.0

Crear un mapa funcional y tecnico completo del estado actual del **Editor Visual IA / Editor Offset Visual** antes de iniciar cualquier redisenio UX.

Esta fase es exclusivamente de diagnostico y documentacion:

- no modifica codigo
- no modifica motores
- no modifica contratos JSON
- no modifica `layout_constructor.json`
- no renombra ids ni clases criticas
- no cambia drag, resize, seleccion, preview, PDF, Step & Repeat PRO ni CTP

## Estado actual Fase 9

Este documento sigue siendo la fuente de verdad arquitectonica del Editor Visual IA, pero ya no describe solo el cierre de Fase 8. En la rama `fase9-redisenio-panel-editor` el editor conserva la base de Fase 8 y suma dos hechos relevantes:

- el panel derecho y la experiencia del Editor Visual IA siguen evolucionando sobre la arquitectura SAFE existente
- existe un prototipo de agente asesor con OpenAI Agents SDK en `ai_agent/editor_advisor/`
- Fase 9.2 especializa ese agente como UX/UI SAFE Advisor
- Fase 9.3 aplica un premium pass CSS-only del panel derecho en `static/css/editor_offset_visual.css`
- Fase 9.4 agrega Codex Prompt Builder con `prompt_para_codex` y `--codex-prompt-only`

El agente SDK es actualmente **CLI-only y read-only**. No esta integrado a Flask, no tiene endpoints, no esta conectado a la UI, no modifica archivos y debe tratarse como una herramienta de analisis/planificacion y generacion de prompts SAFE para Codex, no como automatizacion productiva.

## 1. Resumen general del Editor Visual IA

El Editor Visual IA es hoy el flujo principal y mas moderno del modulo offset. Funciona como un constructor visual por job para preparar montajes de imprenta:

1. carga o inicializa un `layout_constructor.json`
2. permite configurar pliego, trabajos logicos, PDFs, formas, bleed, spacing y CTP
3. permite generar slots automaticamente con Step & Repeat PRO, nesting o hybrid
4. permite editar manualmente slots con seleccion, drag, resize y herramientas PRO
5. permite simular cuadernillos como herramienta visual aislada
6. guarda el layout persistido por job
7. genera preview y PDF final desde el layout persistido

La fuente operativa principal esta repartida entre:

- frontend vivo: `static/js/editor_offset_visual.js`
- template: `templates/editor_offset_visual.html`
- estilos: `static/css/editor_offset_visual.css`
- orquestacion Flask / fachada compatible: `routes.py`
- persistencia, defaults y uploads: `services/editor_offset_jobs.py`, `services/editor_offset_layout_defaults.py`, `services/editor_offset_uploads.py`
- selector de imposicion: `services/editor_offset_imposition_service.py`
- motor Step & Repeat PRO: `engines/step_repeat_pro_engine.py`
- validacion de salida: `services/editor_offset_output_contract.py`
- salida preview/PDF: `montaje_offset_inteligente.py`
- nesting auxiliar: `engines/nesting_pro_engine.py`
- simulador aislado: `cuadernillos/simulator.py`
- asesor SDK read-only: `ai_agent/editor_advisor/`
- persistencia: `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

El motor prioritario actual del Editor Visual IA es **Step & Repeat PRO automatico** en `engines/step_repeat_pro_engine.py`. `routes.py` conserva wrappers compatibles para imports legacy y endpoints, mientras que `services/editor_offset_imposition_service.py` decide entre `repeat`, `nesting` y `hybrid`. Nesting existe como motor alternativo/auxiliar para `nesting` y `hybrid`, no como motor principal del editor.

Importante: `routes.py` sigue siendo fachada/orquestador Flask, pero no concentra en exclusiva la logica del editor. Jobs, defaults, uploads, imposicion y validacion de salida ya tienen servicios dedicados.

## 2. Lista de funcionalidades actuales

### Configuracion base

- entrada por `GET /editor_offset_visual`
- creacion o carga de job por `job_id`
- persistencia en `layout_constructor.json`
- configuracion de pliego por ancho/alto y presets
- normalizacion de `sheet_mm`, `margins_mm`, `faces`, `active_face`, `export_settings`, `ctp`, `snapSettings`, `spacingSettings`
- seleccion de motor: `repeat`, `nesting`, `hybrid`
- shell visual profesional tipo CAD/preprensa:
  - toolbar superior sticky
  - canvas/pliego central protagonista
  - panel derecho con scroll interno
  - navegacion por tabs del panel derecho
  - premium visual pass CSS-only con mayor densidad, contraste y acabado tecnico
- area contextual existente:
  - `geometry-validation-panel` actua como estado tecnico/validacion geometrica visible
  - no conviene duplicarla con una barra inferior nueva sin redisenio previo

### Panel derecho por tabs

Tabs actuales:

- Pliego
- Trabajos
- Disenos
- Imposicion
- Edicion
- IA
- Cuadernillos
- CTP
- Salida

Los tabs son una capa visual: alternan visibilidad de paneles, pero los controles internos siguen en el DOM y conservan sus ids criticos.

Estado Fase 9:

- el redisenio del panel derecho continua sobre esta base de tabs y scroll interno
- cualquier cambio debe preservar `data-editor-tab`, `data-editor-tab-panel`, ids internos y listeners existentes
- no se debe convertir el panel derecho en una nueva fuente de contrato; sigue siendo organizacion visual sobre el mismo layout persistido

### PDFs y disenos

- subida multiple de PDFs
- deteccion de medida de pagina PDF
- asignacion opcional a trabajo logico
- metadata por diseno:
  - `ref`
  - `filename`
  - `work_id`
  - `width_mm`
  - `height_mm`
  - `bleed_mm`
  - `forms_per_plate`
  - `allow_rotation`
  - `preferred_zone`
  - metadata interna repeat: `priority`, `repeat_role`, `preferred_flow`, `repeat_manual_overrides`
- overrides de salida por diseno en `design_export`

### Trabajos logicos

- alta, edicion y borrado de trabajos
- nombre
- medida final
- copias deseadas
- bleed default
- flag de PDF con sangrado incorporado
- uso en generacion de slots IA legacy y en resolucion de bleed en salida

### Slots y edicion manual

- crear slot manual
- duplicar seleccion
- borrar seleccion
- asignar PDF a slot o seleccion
- editar X/Y/ancho/alto/rotacion/bleed/crop/lock/work/design
- seleccion simple y multiple
- seleccion por marco
- seleccionar todos los slots de la cara activa
- agrupar y desagrupar slots
- drag
- resize por handles
- movimiento de grupos
- bloqueo de slots para herramientas PRO
- historial interno basico

### Herramientas PRO

- alineacion izquierda, centro horizontal, derecha
- alineacion abajo, centro vertical, arriba
- distribucion horizontal y vertical
- nudge por botones y teclado
- paso configurable en mm
- multiplicadores `Shift x10` y `Alt x0.1`
- centrado de bloque horizontal, vertical y completo
- aplicacion de separacion/gap entre slots
- spacing live por filas/columnas/todos
- snap a slots, margenes y grilla
- indicador de distancia util durante drag
- validacion geometrica visual no bloqueante

### Caras

- cara activa `front` / `back`
- normalizacion de slots sin `face` a `front`
- duplicar frente a dorso
- render visual por cara activa
- salida final separada por `slots[].face`

### Step & Repeat PRO automatico

- endpoint `POST /editor_offset_visual/apply_imposition`
- motor principal en `engines.step_repeat_pro_engine.build_step_repeat_slots(layout)`
- wrapper compatible en `routes._build_step_repeat_slots(layout)`
- uso de `spacingSettings.spacingX_mm` y `spacingSettings.spacingY_mm`
- respeto de `bleed_mm = 0`
- rotacion inteligente solo si mejora capacidad
- `slot.w_mm/h_mm` como footprint final en `repeat`
- `rotation_deg` como orientacion del contenido
- zonas `auto`, `top`, `bottom`, `left`, `right`, `center`
- `fill` inteligente interno
- compactacion vertical segura
- expansion vertical segura para `top`, `bottom`, `center`
- soporte para varios disenos en la misma zona vertical
- compactacion final de zonas verticales con `auto`
- validacion estricta de `forms_per_plate`
- error bloqueante `IncompleteImpositionError`
- generacion atomica por diseno
- aislamiento de corridas fallidas

### Nesting e hybrid

- `nesting`: usa `engines.nesting_pro_engine.compute_nesting`
- `hybrid`: usa `compute_nesting` y luego repite el patron desde `services.editor_offset_imposition_service`
- estos motores no son el foco principal actual del editor, pero estan conectados al selector de motor

### Preview y PDF final

- preview: `POST /editor_offset/preview/<job_id>`
- PDF final: `POST /editor_offset/generar_pdf/<job_id>`
- ambos leen el layout persistido desde disco
- ambos validan con `validate_constructor_output_layout(layout)`
- ambos generan salida con `montaje_offset_inteligente.montar_offset_desde_layout`
- salida por frente/dorso segun `slots[].face`
- soporte de `export_settings`
- soporte de `design_export`
- soporte de CTP y texto tecnico
- soporte de `output_mode` raster/vector_hybrid segun salida actual

### Produccion CTP

- configuracion visual:
  - `ctp.enabled`
  - `gripper_mm`
  - `show_guide`
  - `lock_after`
  - marcas de registro
  - tira CMYK/control
  - texto tecnico
- aplicacion de alineacion CTP desde frontend
- bloqueo opcional de slots despues de aplicar CTP
- interpretacion final en `montaje_offset_inteligente.py`

### Simulador de cuadernillos

- endpoint `POST /editor_offset/cuadernillos/simular`
- motor aislado `cuadernillos/simulator.py`
- soporte actual:
  - cosido a caballete
  - sin tapa
  - tapa completa
  - cuadernillos 8 y 16
  - VYV 4 y VYV 8 automaticos
  - metadata visual de orientacion
- render dentro del editor como hoja tecnica visual
- no modifica layout
- no crea slots
- no genera preview/PDF
- no persiste resultado

### Asistente IA

- panel en el editor
- endpoint legacy local: `POST /ai/step_repeat_action`
- endpoint usado por la UI actual: `POST /ai/step_repeat_action_openai`
- tools locales en `ai_agent/tools_repeat.py`
- bridge OpenAI en `ai_agent/openai_tool_bridge.py`
- puede analizar layout, cambiar zonas, validar repeat, generar repeat y optimizar repeat
- la aplicacion del layout devuelto requiere confirmacion del usuario
- distingue `metadata_only` de `layout_with_slots`

### Agente SDK asesor

- prototipo en `ai_agent/editor_advisor/`
- construido con OpenAI Agents SDK Python
- entrada local por CLI, no por Flask
- tools read-only con allowlist de archivos del repo
- bloqueo de rutas sensibles como `.env`, `venv`, outputs, previews, uploads y paths fuera del repo
- contexto principal desde `AGENTS.md` y `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md`
- tool UX read-only `summarize_editor_ux_surface()` para detectar tabs, paneles, ids criticos, listeners, selectores sensibles y `geometry-validation-panel`
- salida estructurada en espanol para asesoria tecnica:
  - fortalezas actuales
  - problemas detectados
  - riesgos tecnicos
  - dependencias
  - mejoras recomendadas
  - validaciones necesarias
  - proximo paso sugerido
- Codex Prompt Builder:
  - `prompt_para_codex` dentro de `EditorAdvisorReport`
  - prompt SAFE listo para pegar en Codex
  - cierre obligatorio: "Antes de implementar, dame un plan SAFE."
  - no autoriza escritura ni aplicacion automatica de cambios
- salida extendida UX SAFE con `EditorAdvisorReport`:
  - problemas UX visuales
  - riesgos DOM/listeners
  - cambios CSS-only seguros
  - cambios HTML/JS riesgosos
  - zonas peligrosas de tocar
  - checklist UX antes/despues
  - fase SAFE sugerida
  - prompt para Codex
- clasificacion obligatoria de propuestas:
  - CSS-only seguro
  - HTML/DOM riesgoso
  - JS/listeners riesgoso
  - backend/contrato prohibido
- no modifica archivos
- no aplica cambios automaticamente
- no crea endpoints
- no esta integrado al panel IA ni a la UI
- no reemplaza al asistente IA Step & Repeat actual

### QA navegador

- base Playwright inicial en `tests/playwright/test_editor_load.py`
- smoke test de carga de `/editor_offset_visual`
- valida `#sheet`, `#sheet-canvas`, tabs esperados y errores graves de consola JS
- test Playwright de tabs/scroll en `tests/playwright/test_tabs_scroll.py`
- valida clicks de tabs, panel activo visible y scroll interno del panel derecho
- el test asume Flask ya corriendo localmente con `python app.py`

## 3. Flujo funcional del usuario desde carga de PDF hasta salida final

1. El usuario entra a `/editor_offset_visual`.
2. `routes.editor_offset_visual` valida/genera `job_id`, carga o crea `layout_constructor.json` y renderiza el template.
3. El template inyecta:
   - `window.INITIAL_LAYOUT_JSON`
   - `window.JOB_ID`
4. `static/js/editor_offset_visual.js` ejecuta `parseInitialLayout()` y normaliza defaults.
5. El usuario configura pliego y, si corresponde, trabajos logicos.
6. El usuario sube PDFs desde el panel de disenos.
7. `POST /editor_offset/upload/<job_id>` guarda archivos y agrega metadata en `designs[]`.
8. El usuario ajusta por diseno:
   - formas por pliego
   - medidas
   - bleed
   - rotacion permitida
   - ubicacion preferida
9. El usuario aplica el motor:
   - `repeat`: Step & Repeat PRO en `engines/step_repeat_pro_engine.py`
   - `nesting`: `engines/nesting_pro_engine.py`
   - `hybrid`: nesting + patron repetido desde `services/editor_offset_imposition_service.py`
10. El backend devuelve un layout con `slots[]` regenerado y lo persiste.
11. El usuario edita manualmente:
   - seleccion
   - drag
   - resize
   - alineacion
   - centrado
   - nudge
   - spacing
   - agrupacion
   - frente/dorso
   - CTP
12. El usuario guarda con `POST /editor_offset/save`.
13. Para preview/PDF, el frontend solicita primero guardar el layout.
14. Preview/PDF no leen el estado efimero del navegador; releen el JSON persistido.
15. `services.editor_offset_output_contract.validate_constructor_output_layout` bloquea errores de contrato.
16. `montaje_offset_inteligente.montar_offset_desde_layout` transforma `slots[]` en posiciones de frente/dorso.
17. `montaje_offset_inteligente.realizar_montaje_inteligente` genera preview o PDF final.
18. El frontend muestra la imagen de preview o el enlace al PDF.

## 4. Mapa de archivos conectados al editor

### Frontend directo

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`

### Backend Flask directo

- `routes.py`
- `app.py` como registro de app/blueprints

### Motores y logica principal

- `engines/step_repeat_pro_engine.py`
- `services/editor_offset_imposition_service.py`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`
- `cuadernillos/simulator.py`

### Servicios y capas auxiliares

- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`
- `services/editor_offset_imposition_service.py`
- `services/editor_offset_output_contract.py`
- `services/editor_layout_contracts.py` para editor post-imposicion, no fuente principal del Editor Visual IA
- `services/openai_client.py`

### IA

- `ai_agent/schemas.py`
- `ai_agent/tools_repeat.py`
- `ai_agent/agent_controller.py`
- `ai_agent/openai_tool_bridge.py`
- `ai_agent/editor_advisor/agent.py`
- `ai_agent/editor_advisor/tools.py` con `summarize_editor_architecture()` y `summarize_editor_ux_surface()`
- `ai_agent/editor_advisor/schemas.py`
- `ai_agent/editor_advisor/cli.py`
- `ai_agent/editor_advisor/prompts/editor_advisor.md`

### Estrategias

- `strategies/__init__.py`
- `strategies/manual.py`
- `strategies/grid.py`
- `strategies/flow.py`
- `strategies/maxrects.py`
- `strategies/nesting_pro_strategy.py`
- `strategies/hybrid_nesting_strategy.py`
- `strategies/common.py`
- `strategies/base.py`

Estas estrategias son usadas por `montaje_offset_inteligente.py` para flujos internos/legacy de montaje. En el Editor Visual IA actual, el Step & Repeat PRO canonico se calcula en `engines/step_repeat_pro_engine.py`.

### Tests relacionados

- `tests/test_editor_offset_output_contract.py`
- `tests/test_cuadernillos_simulator.py`
- `tests/test_step_repeat_pro_engine.py`
- `tests/playwright/test_editor_load.py`
- `tests/playwright/test_tabs_scroll.py`
- `tests/test_montaje_offset_inteligente.py`
- `tests/test_montaje_offset_inteligente_same_size.py`
- `tests/test_montaje_features.py`
- `tests/test_montaje_offset_personalizado.py`
- `tests/test_editor_advisor_tools.py`

## 5. Separacion por capas

### Frontend

Archivos:

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`

Responsabilidades:

- estructura visual del editor
- estado interactivo en memoria
- render del pliego
- seleccion, drag y resize
- herramientas PRO
- shell visual con toolbar sticky, canvas central y panel derecho con scroll interno
- tabs de panel derecho para pliego, trabajos, disenos, imposicion, edicion, IA, cuadernillos, CTP y salida
- premium visual pass y microajustes de contraste CSS-only
- area contextual de validacion geometrica existente bajo el canvas
- paneles de disenos, trabajos, slots, CTP, export, IA y cuadernillos
- llamadas `fetch` a endpoints
- serializacion del layout con `layoutToJson()`
- validacion geometrica visual no bloqueante

### Backend Flask

Archivo:

- `routes.py`

Responsabilidades:

- exponer endpoints del editor
- actuar como fachada/orquestador compatible
- delegar persistencia, defaults, uploads e imposicion a servicios
- exponer endpoints IA
- exponer simulador de cuadernillos
- validar y generar preview/PDF

### Motores de imposicion

Archivos:

- `engines/step_repeat_pro_engine.py`: Step & Repeat PRO principal
- `engines/nesting_pro_engine.py`: nesting alternativo
- `services/editor_offset_imposition_service.py`: selector `repeat`/`nesting`/`hybrid` y bridge hybrid
- `montaje_offset_inteligente.py`: motor de salida/render, no generador principal de Step & Repeat del editor

### Servicios

Archivos:

- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`
- `services/editor_offset_imposition_service.py`
- `services/editor_offset_output_contract.py`
- `services/openai_client.py`

Responsabilidades:

- persistencia y paths de jobs
- defaults y normalizacion de layout
- upload de PDFs y medicion de paginas
- seleccion y aplicacion de motor de imposicion
- validar contrato minimo antes de preview/PDF
- cliente OpenAI lazy reutilizable para flujos IA existentes
- devolver `errors[]` y `warnings[]`

### IA y agente SDK

Archivos:

- `ai_agent/tools_repeat.py`
- `ai_agent/openai_tool_bridge.py`
- `ai_agent/editor_advisor/`

Responsabilidades:

- asistente IA integrado al panel actual para Step & Repeat PRO
- tool calling local con confirmacion del usuario antes de aplicar layouts
- agente SDK asesor externo, CLI-only/read-only, para analizar el repo y proponer planes seguros
- mantener separadas la IA operativa del editor y la asesoria arquitectonica del SDK

### Logica compartida

Archivos:

- `montaje_offset_inteligente.py`
- `strategies/*`
- `engines/nesting_pro_engine.py`
- `ai_agent/tools_repeat.py`

Responsabilidades mezcladas:

- render PDF
- calculos de posicion
- nesting
- tools IA que conservan compatibilidad mediante wrappers de `routes.py`
- compatibilidad con flujos offset previos

### Documentacion

Archivos:

- `DOCS/OFFSET/00_CONTEXTO_OFFSET.md` a `13_SIMULADOR_CUADERNILLOS.md`
- este documento `14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md`

Responsabilidad:

- congelar mapa funcional, contratos, riesgos y fases de evolucion

### Tests

Responsabilidades actuales:

- contrato minimo de salida
- simulador de cuadernillos
- Step & Repeat PRO
- smoke test Playwright de carga del editor
- Playwright basico de tabs y scroll interno
- montaje inteligente general
- features historicas de montaje

Faltan pruebas especificas amplias para:

- drag/resize/seleccion frontend
- upload/apply repeat/preview/PDF con Playwright
- endpoints completos del editor
- IA tools
- CTP desde layout constructor

## 6. Que hace cada archivo importante

### `templates/editor_offset_visual.html`

Define la estructura completa del editor:

- header
- shell `editor-shell`
- toolbar principal sticky
- subtoolbar de snap, spacing y herramientas manuales
- workspace con canvas/pliego central
- panel de validacion geometrica
- panel derecho con scroll interno y tabs:
  - pliego
  - trabajos
  - PDFs/disenos
  - motor de imposicion
  - herramientas avanzadas
  - IA
  - cuadernillos
  - CTP
  - salida/export/preview/PDF
- bootstrap de `window.INITIAL_LAYOUT_JSON` y `window.JOB_ID`
- carga de `static/js/editor_offset_visual.js`

Sus ids son criticos porque `editor_offset_visual.js` los busca directamente con `getElementById`.

### `static/js/editor_offset_visual.js`

Es el archivo mas cargado del editor. Controla:

- estado global `state`
- normalizacion del layout
- render del pliego y slots
- escala y zoom
- snap
- spacing
- seleccion simple/multiple
- box select
- drag/resize
- formulario de slots
- trabajos
- PDFs/disenos
- export settings
- CTP
- Step Repeat manual desde slot seleccionado
- apply imposition backend
- IA
- cuadernillos
- preview y PDF
- validacion geometrica visual

Hoy funciona como mini-aplicacion monolitica del editor.

### `static/css/editor_offset_visual.css`

Define:

- layout general
- shell profesional
- premium visual pass SAFE
- toolbar/subtoolbar sticky
- botones
- pliego
- slots
- handles
- estados selected/locked/error/warning
- guia CTP
- indicador de distancia
- paneles laterales
- tabs del panel derecho
- contraste tecnico de toolbar/paneles/inputs
- formularios
- IA
- cuadernillos
- preview/PDF

Es visual, pero esta acoplado a clases que el JS agrega dinamicamente.

### `routes.py`

Es la fachada/orquestador principal del Editor Visual IA. Mantiene endpoints y wrappers compatibles, pero varias responsabilidades internas ya fueron extraidas a servicios y motores. Responsabilidades:

- rutas `/editor_offset_visual`
- persistencia `/editor_offset/save` delegada a `services/editor_offset_jobs.py`
- upload `/editor_offset/upload/<job_id>` delegado a `services/editor_offset_uploads.py`
- cuadernillos `/editor_offset/cuadernillos/simular`
- auto layout `/editor_offset/auto_layout/<job_id>`
- apply imposition `/editor_offset_visual/apply_imposition`
- IA `/ai/step_repeat_action` y `/ai/step_repeat_action_openai`
- preview `/editor_offset/preview/<job_id>`
- PDF `/editor_offset/generar_pdf/<job_id>`
- wrappers compatibles para helpers de layout constructor
- wrappers compatibles para defaults/normalizacion
- wrapper compatible para Step & Repeat PRO
- wrapper compatible para nesting/hybrid bridge

Sigue siendo un archivo importante por compatibilidad e integracion HTTP, pero ya no es el lugar canonico del motor Step & Repeat PRO ni del selector de imposicion.

### `engines/step_repeat_pro_engine.py`

Motor canonico del Step & Repeat PRO automatico:

- ordena y normaliza disenos repeat
- calcula zonas `auto`, `top`, `bottom`, `left`, `right`, `center` y `fill`
- aplica spacing y bleed
- elige rotacion cuando mejora capacidad
- compacta/expande zonas verticales seguras
- valida `forms_per_plate`
- lanza `IncompleteImpositionError`
- devuelve `slots[]` con estructura compatible

`routes.py` conserva wrappers para no romper imports existentes.

### `services/editor_offset_imposition_service.py`

Servicio de imposicion del Editor Visual IA:

- selecciona/aplica `repeat`, `nesting` o `hybrid`
- convierte resultados de nesting a slots del editor
- arma el patron hybrid
- delega `repeat` a `engines/step_repeat_pro_engine.py`

El endpoint Flask sigue en `routes.py`.

### `services/editor_offset_jobs.py`

Servicio de persistencia y paths:

- job_id seguro
- paths de jobs
- carga/guardado JSON
- carga/guardado de `layout_constructor.json`

### `services/editor_offset_layout_defaults.py`

Servicio de defaults y normalizacion:

- layout base
- faces
- export settings
- imposition settings
- spacing settings
- metadata repeat

### `services/editor_offset_uploads.py`

Servicio de uploads:

- subida de PDFs
- lectura de medidas PDF
- construccion de metadata `designs[]`

### `montaje_offset_inteligente.py`

Es el motor real de salida final. Para el Editor Visual IA:

- recibe `layout_constructor.json`
- resuelve PDFs reales desde `designs[]`
- separa posiciones por `slots[].face`
- transforma slots a posiciones internas
- resuelve bleed/crop efectivo
- interpreta `imposition_engine`
- usa `slot_box_final` para `repeat`
- genera preview o PDF
- arma frente/dorso cuando corresponde
- aplica CTP y marcas tecnicas segun configuracion

No debe tratarse como el motor principal de Step & Repeat del editor. Es el motor de render/salida.

### `engines/nesting_pro_engine.py`

Motor alternativo de nesting basado en `rectpack`:

- normaliza disenos
- calcula area disponible
- empaca piezas
- devuelve `NestingResult(slots, bbox)`

Participa cuando el usuario elige `nesting` o `hybrid`. No reemplaza al Step & Repeat PRO principal.

### `cuadernillos/simulator.py`

Motor aislado para simulacion visual/logica de cuadernillos:

- valida payload
- normaliza paginas
- arma patrones 8/16
- arma VYV 4/8
- separa tapa completa
- agrega metadata visual de orientacion

No toca slots ni PDF final.

### `services/editor_offset_output_contract.py`

Validador de contrato minimo previo a preview/PDF:

- valida `designs[].ref`
- valida `slots[].id`
- valida `slots[].design_ref`
- valida `slot.face`
- valida campos numericos criticos del slot
- valida `w_mm > 0` y `h_mm > 0`
- advierte `logical_work_id` no resuelto
- advierte `faces[]` con `back` sin slots de dorso

### `ai_agent/tools_repeat.py`

Tools locales para IA:

- analiza layout
- genera repeat usando wrappers compatibles de `routes.py`, que delegan al motor en `engines/step_repeat_pro_engine.py`
- valida repeat
- cambia zonas de disenos
- centra layout
- optimiza repeat con retry controlado

Depende de la fachada compatible de `routes.py`; el motor real vive en `engines/step_repeat_pro_engine.py`.

### `ai_agent/openai_tool_bridge.py`

Puente entre OpenAI tool calling y tools locales. Decide herramientas, interpreta intenciones de zonas y devuelve respuesta al frontend.

### `ai_agent/editor_advisor/`

Prototipo de agente asesor con OpenAI Agents SDK:

- `agent.py`: define `Agent`, tools SDK y `Runner.run`
- `tools.py`: expone lecturas y busquedas read-only con allowlist
- `schemas.py`: define `EditorAdvisorReport`
- `cli.py`: entrada local para consultas desde terminal
- `prompts/editor_advisor.md`: instrucciones base del asesor

Limite actual:

- no escribe archivos
- no ejecuta cambios sobre el repo
- no usa `SandboxAgent`
- no esta conectado a Flask ni al panel IA
- no debe integrarse a UI/endpoints sin una fase tecnica separada

### `strategies/*`

Estrategias historicas/reutilizables para `montaje_offset_inteligente.py`. Son importantes para el sistema, pero no deben confundirse con el motor Step & Repeat PRO automatico del Editor Visual IA.

## 7. Funcionalidades que dependen de `editor_offset_visual.js`

Dependen directamente del JS:

- bootstrap de layout inicial
- estado en memoria del editor
- render visual del pliego
- escala, zoom y conversion mm/px
- seleccion simple y multiple
- box select
- drag
- resize
- seleccion persistente despues del drag
- handles visuales
- formulario de slot
- creacion, duplicacion y borrado de slots
- agrupacion/desagrupacion
- aplicar PDF a slots seleccionados
- duplicar frente a dorso
- render y edicion de trabajos
- render y edicion de disenos
- cambios de `forms_per_plate`, medidas, bleed, rotacion y ubicacion
- seleccion del motor de imposicion
- llamadas a upload, save, auto layout, apply imposition, preview y PDF
- panel IA y aplicacion manual del layout sugerido
- panel de cuadernillos y render de simulacion
- CTP visual y alineacion
- snap y spacing
- herramientas PRO de alineacion, distribucion, nudge y centrado
- validacion geometrica visual
- indicador de distancia util
- render de warnings/errors de salida

Riesgo: cualquier redisenio HTML que cambie ids o estructura esperada por este archivo puede romper funciones criticas aunque no cambie logica backend.

## 8. Funcionalidades que dependen de `routes.py`

Dependen directamente de `routes.py` como fachada Flask y capa de compatibilidad, aunque varias responsabilidades internas ya estan delegadas a `services/` o `engines/`:

- entrada `/editor_offset_visual`
- orquestacion HTTP de creacion/carga/guardado de jobs
- wrappers compatibles para defaults de `layout_constructor.json`
- wrappers compatibles para normalizacion de `faces`, `imposition_engine`, `export_settings`, repeat metadata
- endpoint de upload de PDFs
- generacion legacy de slots desde trabajos logicos
- wrapper de Step & Repeat PRO automatico
- wrapper de nesting/hybrid bridge
- persistencia despues de apply imposition
- endpoints IA
- simulador de cuadernillos como endpoint Flask
- preview y PDF como endpoints Flask
- alias de validacion de salida

Riesgo: `routes.py` sigue concentrando endpoints y compatibilidad. Un refactor apresurado puede romper imports legacy o endpoints aunque jobs, defaults, uploads, imposicion, validacion de salida y Step & Repeat PRO ya tengan modulos dedicados.

## 9. Funcionalidades que dependen de `montaje_offset_inteligente.py`

Dependen directamente de este archivo:

- render real de preview
- generacion real de PDF final
- lectura de PDFs fuente
- conversion de slots a posiciones
- separacion frente/dorso
- interpretacion de `rotation_deg`
- interpretacion de `w_mm/h_mm` por engine
- `slot_box_final` para repeat
- bleed efectivo
- crop marks efectivos
- raster/vector hybrid
- marcas de corte
- marcas de registro y tiras tecnicas
- armado de PDF final frente/dorso
- funciones legacy de montaje inteligente usadas por otras rutas

Riesgo: cambios hechos pensando solo en el Editor Visual IA pueden romper `/montaje_offset_inteligente` u otros flujos que comparten este motor.

## 10. Partes mezcladas que conviene separar en el futuro

### En frontend

- estado global + render + IO + herramientas + IA + cuadernillos en un solo JS
- listeners acoplados a ids especificos
- validacion visual mezclada con render de pliego
- `geometry-validation-panel` ya funciona como area contextual/status, pero puede evolucionar a status bar tecnica compacta
- CTP mezcla configuracion, alineacion y render
- cuadernillos comparte archivo JS/CSS con el editor principal aunque no modifica layout
- preview/PDF usa alerts y manejo de errores dentro del mismo flujo del editor

Separacion futura recomendada:

- `editor_state.js`
- `editor_contract.js`
- `sheet_renderer.js`
- `slot_interactions.js`
- `manual_tools.js`
- `designs_panel.js`
- `ctp_panel.js`
- `output_panel.js`
- `ai_panel.js`
- `booklet_simulator_panel.js`
- `editor_status_bar.js` si se decide evolucionar la validacion geometrica existente sin duplicarla

### En backend

- `routes.py` todavia concentra:
  - HTTP
  - wrappers de compatibilidad
  - IA endpoints
  - preview/PDF endpoints
  - endpoint de cuadernillos
- persistencia, defaults, uploads, Step & Repeat PRO y selector de imposicion ya tienen modulos dedicados
- validaciones de layout estan parcialmente en frontend, parcialmente en service y parcialmente implicitas en motores
- CTP vive repartido entre frontend y salida
- `montaje_offset_inteligente.py` sirve al editor y a flujos legacy

Separacion ya realizada:

- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`
- `engines/step_repeat_pro_engine.py`
- `services/editor_offset_imposition_service.py`

Separacion futura recomendada:

- `services/editor_offset_output_service.py`
- `services/editor_offset_ctp_service.py`
- mantener `services/editor_offset_output_contract.py` como validador incremental

### En contratos

- `layout_constructor.json` tiene campos de UI, motor, salida y CTP juntos
- `spacingSettings` es UX, pero impacta generacion repeat
- `snapSettings` es UX, pero viaja en el mismo contrato persistido
- `ctp` mezcla guia visual, bloqueo y salida tecnica
- `preferred_flow` existe pero no tiene efecto real
- `locked` y `group_id` afectan UI, no salida final

## 11. Arquitectura propuesta para escalar el Editor Visual IA

### Principio rector

Separar sin cambiar contrato externo. Primero mover responsabilidades internas con wrappers compatibles; despues redisenar UX.

### Arquitectura objetivo backend

```text
routes.py
  solo endpoints del editor
  llama servicios

services/editor_offset_jobs.py
  job_id, paths, cargar/guardar layout

services/editor_offset_layout_defaults.py
  default layout
  ensure faces
  ensure imposition
  ensure export
  ensure CTP
  normalizar repeat metadata

services/editor_offset_uploads.py
  upload PDFs
  medir PDFs
  construir designs[]

engines/step_repeat_pro_engine.py
  _build_step_repeat_slots
  zonas
  fill
  compactacion
  expansion
  IncompleteImpositionError

services/editor_offset_imposition_service.py
  recibe layout + engine
  decide repeat/nesting/hybrid
  devuelve slots

services/editor_offset_output_contract.py
  validacion minima y futuras reglas versionadas

services/editor_offset_output_service.py
  prepara preview/PDF desde layout persistido
  llama montaje_offset_inteligente.py

cuadernillos/simulator.py
  se mantiene aislado

ai_agent/*
  llama a servicios estables, no a internals de routes.py
```

### Arquitectura objetivo frontend

```text
editor_offset_visual.js
  bootstrap temporal o entrypoint

editor/state.js
  state, history, layoutToJson, defaults

editor/dom_refs.js
  ids y referencias DOM criticas centralizadas

editor/sheet_renderer.js
  pliego, slots, CTP guide, geometry markers

editor/slot_interactions.js
  click, seleccion, drag, resize, box select

editor/manual_tools.js
  align, distribute, nudge, center, group, duplicate

editor/designs_panel.js
  render y edicion designs[]

editor/works_panel.js
  render y edicion works[]

editor/imposition_panel.js
  motor y apply_imposition

editor/ctp_panel.js
  CTP UI y alineacion

editor/output_panel.js
  save, preview, PDF, warnings/errors

editor/ai_panel.js
  asistente IA

editor/booklet_panel.js
  simulador cuadernillos aislado
```

### Secuencia segura

1. Crear modulos espejo sin cambiar comportamiento.
2. Mover funciones puras primero.
3. Mover servicios backend con tests de equivalencia.
4. Mantener aliases compatibles.
5. Recien despues tocar layout visual.

## 12. Que NO se debe tocar todavia

No tocar todavia:

- contrato base de `layout_constructor.json`
- nombres de campos en `sheet_mm`, `margins_mm`, `works`, `designs`, `slots`, `faces`, `export_settings`, `design_export`, `ctp`
- ids del template usados por `editor_offset_visual.js`
- clases dinamicas usadas por JS/CSS:
  - `slot`
  - `selected`
  - `locked`
  - `geometry-error`
  - `geometry-warning`
  - `handle`
  - `hidden`
- `slots[].w_mm/h_mm` como footprint final en `repeat`
- `rotation_deg` como orientacion de contenido
- `slots[].design_ref -> designs[].ref`
- `slots[].face`
- flujo preview/PDF desde JSON persistido
- validacion existente en `services/editor_offset_output_contract.py`
- wrappers compatibles de Step & Repeat PRO en `routes.py` sin revisar dependencias externas
- `montaje_offset_inteligente.py` sin mapa de impacto de rutas legacy
- `cuadernillos/simulator.py` como motor aislado
- `preferred_flow` como campo reservado
- `nesting_pro_engine.py` como si fuera motor principal del editor
- shell/tabs del editor sin pruebas Playwright basicas de carga y regresion visual
- barra inferior nueva que duplique `geometry-validation-panel` sin redisenio funcional previo

## 13. Riesgos tecnicos

### Riesgos altos

- romper `design_ref` y dejar slots sin PDF en salida
- romper `face` y generar frente/dorso incorrecto
- cambiar semantica de `w_mm/h_mm` y desalinear editor vs PDF
- cambiar `rotation_deg` y provocar stretch o desplazamientos en PDF
- modificar `routes.py` y afectar endpoints del editor o rutas legacy
- tocar `montaje_offset_inteligente.py` sin cubrir preview/PDF y flujos antiguos
- redisenar HTML renombrando ids que el JS usa directamente
- cambiar wrappers o motor Step & Repeat PRO sin tests de regresion para zonas, fill y errores incompletos
- confundir simulador de cuadernillos con salida productiva
- conectar `ai_agent/editor_advisor` a Flask/UI sin fase propia, guardrails y pruebas
- permitir que el agente SDK escriba archivos o lea rutas sensibles fuera de su allowlist
- permitir que el agente SDK modifique HTML/JS automaticamente o aplique cambios de DOM/listeners sin revision humana
- tocar Step & Repeat PRO desde una fase UX/CSS-only sin pruebas de motor
- documentacion desalineada que haga que el agente planifique desde supuestos viejos

### Riesgos medios

- cambios de CSS que oculten handles, estados selected o warnings
- cambios visuales que resten contraste a Snap/Espaciado, unidades mm, tabs o botones tecnicos
- confundir un cambio CSS-only seguro con cambios HTML/DOM o JS/listeners riesgosos
- desacople incorrecto entre `state.activeFace` y `layout.active_face`
- que preview/PDF use layout persistido mientras UI tiene cambios no guardados
- `locked` se entienda como bloqueo productivo cuando solo es UI
- CTP aplicado en frontend pero reinterpretado distinto en backend
- warnings de salida aun dependen de surfacing basico en frontend
- confundir el asistente IA Step & Repeat integrado con el agente SDK asesor CLI-only

### Riesgos de deuda

- `routes.py` aun concentra endpoints y compatibilidad
- `editor_offset_visual.js` demasiado monolitico para redisenio UX seguro
- falta schema formal completo
- falta ampliar suite Playwright para drag/resize/seleccion y flujos productivos
- Playwright ya cubre carga y tabs/scroll, pero falta drag/resize/seleccion
- falta test automatizado frontend para drag/resize/seleccion
- varios flujos offset legacy comparten conceptos y motores
- documentacion desactualizada puede alimentar mal al agente SDK asesor porque usa `AGENTS.md` y este mapa como contexto arquitectonico

## 14. Pruebas necesarias antes de cualquier refactor

### Validacion minima actual

Ejecutar antes y despues de cambios:

```bash
python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies
git diff --check
node --check static/js/editor_offset_visual.js
pytest
```

### Tests prioritarios a crear antes de mover motor repeat

- repeat respeta `bleed_mm = 0`
- repeat usa `spacingSettings.spacingX_mm/Y_mm`
- rotacion no ocurre si no mejora capacidad
- rotacion intercambia footprint cuando corresponde
- `forms_per_plate` incompleto lanza `IncompleteImpositionError`
- rerun despues de error no conserva slots parciales
- `auto/auto` conserva comportamiento legacy
- `top/bottom` con expansion vertical
- `center` con expansion vertical
- multiples disenos `top/top`, `bottom/bottom`, `center/center`
- zonas verticales + `auto` con compactacion final
- `left/right` sin prometer expansion horizontal
- `fill` no colisiona con slots existentes

### Tests de contrato/salida

- `design_ref` invalido bloquea preview/PDF
- `face` invalido bloquea preview/PDF
- `back` sin slots produce warning
- `rotation_deg` y `slot_box_final` mantienen salida sin stretch
- PDF final frente/dorso conserva orden y cantidad de paginas
- CTP con pinza y marcas no desplaza indebidamente el bloque

### Tests frontend recomendados

Idealmente con Playwright o equivalente:

- cargar editor (base inicial ya existe en `tests/playwright/test_editor_load.py`)
- validar tabs del panel derecho (base inicial ya existe en `tests/playwright/test_tabs_scroll.py`)
- validar scroll de tabs/panel derecho (base inicial ya existe en `tests/playwright/test_tabs_scroll.py`)
- subir fixture PDF
- aplicar repeat
- seleccionar slot
- drag
- resize
- multi-select
- box select
- alinear
- centrar bloque
- duplicar frente a dorso
- guardar
- preview
- PDF
- simular cuadernillo
- validar que no haya errores JS de consola

### Tests IA recomendados

- `set_design_zone`
- `set_design_zones`
- generar repeat despues de cambiar zonas
- validar repeat con error incompleto
- `metadata_only` vs `layout_with_slots`
- identificacion por dimensiones `50x40`
- no aplicar layout sin confirmacion frontend

### Tests agente SDK recomendados

- mantener `tests/test_editor_advisor_tools.py` para tools read-only
- verificar que `.env`, `venv`, outputs, previews, uploads y rutas externas sigan bloqueadas
- validar que el CLI falla claro si falta `OPENAI_API_KEY`
- antes de cualquier integracion Flask/UI, agregar pruebas de contrato para no permitir escritura ni aplicacion automatica de cambios

## 15. Hoja de ruta Fase 8.x / Fase 9

### Estado actualizado

- Fase 8.0 completada: mapa funcional y tecnico del Editor Visual IA.
- Fase 8.1 completada: separacion SAFE de jobs, defaults y uploads.
- Fase 8.1B completada: extraccion de Step & Repeat PRO a `engines/step_repeat_pro_engine.py` con tests.
- Fase 8.1C completada: servicio de imposicion en `services/editor_offset_imposition_service.py`.
- Fase 8.2 completada: shell UX profesional SAFE.
- Fase 8.3 completada: tabs del panel derecho y fix de scroll interno.
- Premium Visual Pass SAFE completado: refinamiento CSS-only, densidad tecnica, contraste, tabs, toolbar, panel derecho, inputs, canvas, estados y scrollbars.
- QA inicial completada: smoke test Playwright de carga del editor y test Playwright de tabs/scroll.
- Fase 9 en curso: redisenio/continuidad del panel derecho sobre la base SAFE existente.
- Prototipo Agents SDK creado: `ai_agent/editor_advisor/` como asesor CLI-only/read-only.
- Fase 9.2 completada: UX SAFE Advisor sobre `ai_agent/editor_advisor/`.
- Fase 9.3 completada: CSS-only premium pass del panel derecho aplicado solo en `static/css/editor_offset_visual.css`.
- Fase 9.4 completada: Codex Prompt Builder con `prompt_para_codex` y `--codex-prompt-only`.

Antes de continuar con cambios mayores de UX o IA, conviene mantener revision SAFE, documentacion alineada y ampliar Playwright para drag/resize/seleccion y flujos productivos.

Pendientes:

- status bar tecnica compacta basada en `geometry-validation-panel`, sin duplicar informacion
- inspector contextual futuro solo si aporta informacion no cubierta por la validacion geometrica
- Playwright avanzado para drag, resize y seleccion
- Playwright para upload, apply repeat, preview y PDF
- posible servicio futuro de salida preview/PDF
- posible modularizacion frontend en fases futuras
- integracion futura del agente SDK solo como fase separada, con guardrails y tests
- mantener `AGENTS.md` y este documento alineados porque alimentan el contexto del agente SDK
- auditoria visual posterior al CSS-only premium pass cuando Flask este disponible y el contexto permita relanzarlo

### Fase 8.1: separacion/orden interno SAFE (completada)

Problema real:

- `routes.py` y `editor_offset_visual.js` concentran demasiadas responsabilidades.

Valor operativo:

- permitir refactors y UX futura con menor riesgo.

Usuario beneficiado:

- equipo tecnico y operadores, porque se reduce la probabilidad de regresiones.

Archivos que podria tocar:

- `routes.py`
- nuevos `services/editor_offset_*.py`
- posible nuevo `engines/step_repeat_pro_engine.py`
- tests nuevos
- documentacion

No debe tocar:

- UI visual
- ids/classes del template
- contrato JSON
- semantica de slots
- salida PDF

Estrategia:

Resultado real:

1. `services/editor_offset_jobs.py`
2. `services/editor_offset_layout_defaults.py`
3. `services/editor_offset_uploads.py`
4. wrappers compatibles en `routes.py`
5. endpoints iguales

Riesgo:

- medio/alto si se mueve motor sin tests; bajo/medio si se hace por wrappers y equivalencia.

### Fase 8.1B: extraccion Step & Repeat PRO (completada)

Resultado real:

- `engines/step_repeat_pro_engine.py`
- `tests/test_step_repeat_pro_engine.py`
- `routes.py` conserva wrappers compatibles
- no se modificaron contratos, preview/PDF ni frontend

### Fase 8.1C: servicio de imposicion (completada)

Resultado real:

- `services/editor_offset_imposition_service.py`
- selector `repeat` / `nesting` / `hybrid`
- bridge nesting/hybrid
- `routes.py` conserva wrappers compatibles

### Fase 8.2: redisenio UX shell (completada)

Problema real:

- la interfaz actual funciona, pero no tiene shell profesional tipo CAD/preprensa.

Valor operativo:

- mejorar orientacion, jerarquia y eficiencia sin tocar logica.

Archivos que podria tocar:

- `templates/editor_offset_visual.html`
- `static/css/editor_offset_visual.css`
- minimo JS solo si se mantienen ids o se crea capa de refs

No debe tocar:

- motores
- contratos
- endpoints
- semantica de slots

Estrategia:

Resultado real:

- shell visual nuevo manteniendo ids criticos
- toolbar superior sticky
- canvas central protagonista
- panel derecho fijo con scroll interno
- sin cambios funcionales

Riesgo:

- medio por acoplamiento del JS a ids.

### Fase 8.3: tabs/paneles profesionales (completada)

Problema real:

- demasiados paneles abiertos en una columna dificultan operacion profesional.

Valor operativo:

- dividir configuracion, disenos, montaje, CTP, salida e IA en areas logicas.

Archivos que podria tocar:

- template
- CSS
- JS de navegacion visual si hace falta

No debe tocar:

- contratos
- motores
- ids internos de controles sin adaptador

Estrategia:

Resultado real:

- tabs: Pliego, Trabajos, Disenos, Imposicion, Edicion, IA, Cuadernillos, CTP y Salida
- tabs solo de visibilidad, no de logica
- controles internos conservan ids
- fix CSS posterior para scroll interno del panel derecho y tab activo

Riesgo:

- medio si se ocultan controles que algun listener espera disponibles.

### Fase 8.4: status/contexto tecnico (postergada)

Problema real:

- el operador necesita informacion de seleccion y acciones de precision siempre visibles.

Valor operativo:

- mostrar contexto de slot/seleccion, coordenadas, medidas, warnings, cara activa, zoom y acciones rapidas.

Decision de cierre Fase 8:

- no se agrego una barra inferior nueva.
- el bloque actual de `Validacion geometrica` ya cumple parcialmente funcion de status/contexto tecnico.
- cualquier evolucion futura debe convertir o compactar ese bloque antes de duplicar informacion con otra barra.

Archivos que podria tocar:

- template
- CSS
- JS frontend

No debe tocar:

- backend
- motores
- salida
- contratos

Estrategia:

- leer estado existente
- no duplicar fuente de verdad
- acciones contextuales deben llamar funciones existentes

Riesgo:

- medio por seleccion y estado global.

### Fase 8.5: pulido visual industrial / premium visual pass SAFE (completada)

Problema real:

- el editor necesita acabado visual de software profesional de preprensa.

Valor operativo:

- mayor confianza operativa, lectura rapida y mejor ergonomia.

Archivos que podria tocar:

- principalmente CSS
- pequenos ajustes HTML si son seguros

No debe tocar:

- JS funcional
- endpoints
- contratos
- motores

Estrategia:

- mejorar densidad, contraste, estados hover/focus, handles, guias, warnings
- validar desktop/mobile
- evitar estilos que oculten controles funcionales

Resultado real:

- toolbar mas tecnica y compacta
- tabs mas densos y con estado activo mas claro
- panel derecho con acabado mas profesional
- inputs/selects mas consistentes e integrados
- canvas/pliego con fondo tecnico y grid sutil
- estados selected/locked/warnings/error mas legibles
- scrollbars internos pulidos
- microajuste posterior de contraste para Snap, Espaciado, labels secundarios, unidades mm, inputs tecnicos y botones claros
- cambios CSS-only, sin tocar JS funcional ni backend

Riesgo:

- bajo/medio si es CSS-only; medio si se reestructura DOM.

### Fase 9: documentacion base y agente SDK asesor (en curso)

Problema real:

- el Editor Visual IA ya tiene varias capas separadas y la documentacion de Fase 8 quedo como contexto base para agentes humanos y SDK.
- si `AGENTS.md` o este mapa quedan desactualizados, el agente SDK puede planificar desde supuestos incorrectos.

Valor operativo:

- permitir analisis tecnico mas confiable antes de cambios grandes.
- separar asesoria arquitectonica de la IA operativa que ya vive en el panel del editor.

Resultado real actual:

- `ai_agent/editor_advisor/` existe como prototipo OpenAI Agents SDK.
- el agente SDK usa CLI local, tools read-only y salida estructurada.
- no esta integrado a Flask, UI ni endpoints.
- `requirements.txt` incluye `openai-agents`.
- `tests/test_editor_advisor_tools.py` cubre restricciones basicas de lectura.

No debe tocar:

- contratos JSON
- `routes.py`
- frontend
- motores
- servicios existentes
- preview/PDF

Proximos pasos SAFE:

- mantener el agente SDK aislado hasta definir una fase de integracion.
- ampliar pruebas del agente antes de habilitar nuevas tools.
- si se integra a Flask/UI, hacerlo como plan separado con permisos explicitos, guardrails y pruebas.
- usar este documento y `AGENTS.md` como contexto obligatorio antes de cambios estructurales.

### Fase 9.2: UX SAFE Advisor sobre Agent SDK (completada)

Problema real:

- el agente SDK necesitaba entender mejor el panel derecho, la densidad visual, los riesgos DOM/listeners y la diferencia entre cambios CSS-only y cambios funcionales riesgosos.

Valor operativo:

- convertir `ai_agent/editor_advisor/` en asesor UX/UI tecnico antes de tocar frontend productivo.
- permitir diagnosticos como "analiza el panel derecho", "detecta sobrecarga visual" o "propone mejoras premium sin romper listeners".

Resultado real:

- `ai_agent/editor_advisor/prompts/editor_advisor.md` define el rol UX/UI SAFE.
- `EditorAdvisorReport` conserva campos tecnicos y agrega campos UX SAFE.
- `summarize_editor_ux_surface()` resume tabs, paneles, ids criticos, listeners, selectores sensibles y `geometry-validation-panel`.
- `agent.py` registra la tool nueva.
- `cli.py` mantiene el uso actual por PowerShell.
- `tests/test_editor_advisor_tools.py` cubre tools read-only y defaults del schema.

Clasificacion SAFE obligatoria:

- `CSS-only seguro`
- `HTML/DOM riesgoso`
- `JS/listeners riesgoso`
- `backend/contrato prohibido`

Garantias:

- CLI-only
- read-only
- sin Flask/UI/endpoints
- sin SandboxAgent
- sin escritura de archivos
- sin cambios en Step & Repeat PRO, contratos, preview/PDF, CTP ni cuadernillos

Comando real de uso desde PowerShell:

```powershell
venv\Scripts\python.exe -m ai_agent.editor_advisor.cli --pretty "analiza el panel derecho y propone mejoras CSS-only"
```

### Fase 9.3: CSS-only premium pass del panel derecho (completada)

Problema real:

- el panel derecho funcionaba, pero seguia mostrando saturacion visual, baja jerarquia en algunos bloques y scroll interno mejorable para uso tecnico prolongado.

Valor operativo:

- mejorar lectura, contraste, foco accesible y sensacion profesional sin tocar DOM ni comportamiento.

Resultado real:

- se modifico unicamente `static/css/editor_offset_visual.css`.
- no se tocaron HTML, JS, Flask, services, engines, contratos JSON, preview/PDF, CTP, Step & Repeat PRO ni cuadernillos.
- no se renombraron ids.
- no se tocaron `data-editor-tab` ni `data-editor-tab-panel`.
- no se duplico `geometry-validation-panel`.

Selectores/bloques refinados:

- `.side-panel`
- `.editor-tabs`
- `.editor-tab`
- `.editor-tab-panels`
- `.panel-accordion`
- `.geometry-validation-panel`
- inputs, selects, textareas, labels, ayudas y botones del panel derecho
- listas/tarjetas internas
- scrollbars internos
- estados hover, active y focus-visible

Validacion ejecutada:

- `git diff --name-only` confirmo que solo cambio `static/css/editor_offset_visual.css`.
- validacion de alcance con `rg` confirmo que no aparecieron `routes.py`, `app.py`, templates, JS, engines ni services.
- `git diff --check` no reporto errores; solo avisos CRLF por line endings.

Validaciones pendientes:

- `node --check static/js/editor_offset_visual.js` quedo bloqueado por `Acceso denegado` a `node.exe`.
- Playwright quedo pendiente porque Flask fue detenido manualmente con `CTRL+C` y no debe relanzarse en ese contexto.

### Fase 9.4: Codex Prompt Builder (completada)

Problema real:

- el agente SDK auditaba bien, pero el usuario tenia que convertir manualmente el diagnostico en un prompt accionable para Codex.

Valor operativo:

- reducir friccion entre auditoria, planificacion SAFE e implementacion posterior.
- hacer que cada reporte pueda incluir un prompt limpio, seguro y listo para pegar en Codex.

Resultado real:

- `EditorAdvisorReport` agrega `prompt_para_codex: str = ""`.
- `prompts/editor_advisor.md` exige generar un prompt con objetivo, alcance, archivos permitidos/prohibidos, riesgos, instrucciones SAFE, validaciones y cierre "Antes de implementar, dame un plan SAFE."
- `cli.py` agrega `--codex-prompt-only` para imprimir solo el prompt limpio, sin JSON.
- `tests/test_editor_advisor_tools.py` cubre el nuevo campo y el render CLI sin llamar OpenAI.

Comando real de uso desde PowerShell:

```powershell
venv\Scripts\python.exe -m ai_agent.editor_advisor.cli --codex-prompt-only "analiza el panel derecho y propone mejoras CSS-only"
```

Validacion ejecutada:

- `python -m compileall ai_agent`: OK
- `venv\Scripts\pytest.exe -p no:cacheprovider tests\test_editor_advisor_tools.py`: OK, `10 passed`
- `git diff --check`: OK, solo warnings CRLF
- alcance: solo archivos del agente/tests; sin Flask, frontend productivo, services, engines, contratos ni Step & Repeat PRO

Garantias:

- CLI-only
- read-only
- sin Flask/UI/endpoints
- sin escritura de archivos
- sin aplicacion automatica de cambios
- no reemplaza la planificacion SAFE; la refuerza

### Workflow SAFE actual con agente SDK

Para fases visuales o arquitectonicas amplias:

1. `editor_advisor` analiza usando `AGENTS.md` y este documento como contexto principal.
2. El agente propone una SAFE phase, clasifica riesgos y genera `prompt_para_codex`.
3. Codex recibe el prompt y devuelve plan SAFE antes de implementar.
4. Codex implementa solo si el usuario aprueba el alcance.
5. Se validan diff, alcance, formato y regresiones disponibles.
6. El agente vuelve a auditar antes de una nueva fase.

## Conclusiones actualizadas

El Editor Visual IA ya tiene capacidades potentes y Fase 8 dejo una base mas ordenada para seguir escalando. La arquitectura ya no esta concentrada solo en `routes.py`: jobs, defaults, uploads, Step & Repeat PRO y seleccion de motor tienen modulos dedicados con wrappers compatibles.

El frontend sigue concentrado principalmente en:

- `static/js/editor_offset_visual.js`

La fachada Flask sigue siendo:

- `routes.py`

La salida productiva depende de:

- `services/editor_offset_output_contract.py`
- `montaje_offset_inteligente.py`

El Step & Repeat PRO automatico actual esta en `engines/step_repeat_pro_engine.py` y debe tratarse como motor principal del editor. `engines/nesting_pro_engine.py` es importante, pero es alternativo/auxiliar.

La evolucion segura hacia UX profesional ya dejo cerrada una base usable: shell, tabs, scroll interno, premium visual pass, Fase 9.3 CSS-only del panel derecho y QA Playwright inicial. La validacion geometrica queda como area contextual existente; no conviene duplicarla con otra barra inferior sin redisenio previo.

En Fase 9, las prioridades SAFE son mantener actualizado este mapa, sostener el redisenio del panel derecho sin romper ids/listeners/contratos, usar `ai_agent/editor_advisor/` como UX SAFE Advisor y Codex Prompt Builder CLI-only/read-only, ampliar Playwright para drag/resize/seleccion y flujos productivos, y no integrar el SDK a Flask/UI hasta que exista una fase explicita con guardrails y tests.
