# 05 DIARIO OFFSET

## 2026-04-17

### Contexto

Se abre rama enfocada solo en modulo de montaje offset, especialmente en el editor visual IA.

### Objetivo de la jornada

- auditar flujo real actual
- crear base documental interna
- no cambiar logica de negocio

### Hallazgos principales

- el editor visual IA nuevo entra por `GET /editor_offset_visual`
- usa `templates/editor_offset_visual.html`
- depende directamente de:
  - `static/js/editor_offset_visual.js`
  - `static/css/editor_offset_visual.css`
- el frontend llama cinco endpoints POST del constructor:
  - save
  - upload
  - auto_layout
  - apply_imposition
  - preview / generar_pdf
- la orquestacion del editor vive en `routes.py`
- la salida real de preview/PDF vive en `montaje_offset_inteligente.py`
- el motor de nesting real usado por el editor es `engines/nesting_pro_engine.py`

### Hallazgos de arquitectura

- el repo tiene varios flujos offset coexistiendo
- el editor visual IA no esta todavia aislado como modulo cerrado
- hay solapamientos entre calculo de slots, imposicion y render final
- varias rutas legacy siguen activas y comparten motores o conceptos

### Decision de esta etapa

- documentar primero
- no limpiar ni borrar archivos
- no refactorizar todavia
- delimitar con precision que pertenece al editor visual IA y que no

### Proxima accion recomendada

- documentar contrato exacto de `layout_constructor.json`
- luego auditar en detalle bleed / crop / face / ctp / export mode

## 2026-04-18

### Mejora implementada

- validacion geometrica visual en el editor
- indicador flotante de distancia util durante drag manual de slots

### Que hace el indicador

- muestra distancia al margen util mas cercano
- muestra distancia al slot vecino mas cercano de la misma cara
- si CTP esta activo, muestra distancia a la zona de pinza

### Alcance tecnico

- solo frontend
- sin cambios en backend
- sin cambios en motores de imposicion
- sin cambios en contratos persistidos

### Observacion importante

Los calculos usan bounding box simple en mm. Sirven como ayuda operativa rapida, no como verificacion geometrica exacta de salida final.

## 2026-04-18 Cierre de fase

### Resumen de lo realizado

- auditoria del flujo real del editor visual IA
- documentacion del mapa del editor
- congelamiento del contrato de layout
- congelamiento del subcontrato de slots
- validacion backend antes de preview y PDF
- validacion geometrica visual en frontend
- indicador de distancia util durante drag
- correccion de UX para distinguir click simple vs drag real y preservar seleccion manual
- consolidacion documental del modulo para continuidad

### Pruebas realizadas

- verificacion del flujo y contratos mediante lectura cruzada de:
  - `routes.py`
  - `static/js/editor_offset_visual.js`
  - `templates/editor_offset_visual.html`
  - `montaje_offset_inteligente.py`
- revision de ejemplos reales de `layout_constructor.json`
- compilacion Python previa sobre `routes.py` durante la fase de validacion backend
- verificacion manual del cableado frontend y de la documentacion consolidada

### Estado resultante

- el Editor Visual IA quedo con contexto tecnico claro y trazable
- el contrato de datos principal quedo documentado
- la salida tiene validacion minima previa en backend
- el editor tiene asistencia visual y geometrica adicional en frontend
- la interaccion de edicion manual quedo estable tras el ajuste click vs drag

### Pendientes

- formalizar mejor schema y validaciones profundas del layout
- revisar con mas precision la semantica geometrica de `w_mm/h_mm`, `rotation_deg` y bleed por engine
- mejorar presentacion UX de warnings y errores sin depender tanto de `alert()`
- decidir cuando conviene empezar micro-refactors internos sin tocar flujos legacy

## 2026-04-18 Inicio Fase 4

### Objetivo

Empezar la fase `fase4-editor-offset-pro` con mejoras profesionales de edicion manual en el Editor Visual IA.

### Mejora implementada

- barra de edicion manual con alineacion de seleccion
- distribucion horizontal y vertical de tres o mas slots
- nudge de precision por botones y flechas de teclado
- paso configurable en milimetros para movimiento fino
- duplicado y borrado multi-slot

### Alcance tecnico

- solo frontend del Editor Visual IA
- sin cambios en backend
- sin cambios en motores de imposicion
- sin cambios en contrato persistido de `slots[]`

### Observacion importante

Las operaciones nuevas trabajan sobre la caja efectiva del slot, consistente con las ayudas visuales actuales. No reemplazan una validacion geometrica rotada exacta de salida final.

## Fase 4 - Consolidacion de herramientas PRO

### Fix visual de toolbar

Se corrigio la barra PRO de edicion manual:

- eliminacion de textos rotos por encoding en etiquetas y botones
- `Edicion` vuelve a verse de forma legible
- botones de alineacion con etiquetas claras:
  - Izq
  - Centro H
  - Der
  - Abajo
  - Centro V
  - Arriba
- nudge con controles direccionales claros
- mejora de espaciado, tamanos y alineacion del control `Paso` + `mm`

### Herramientas de bloque

Se agregaron acciones para operar sobre selecciones completas:

- seleccionar todos los slots de la cara activa
- atajo `Ctrl/Cmd + A` fuera de inputs
- centrar horizontalmente la seleccion
- centrar verticalmente la seleccion
- centrar bloque completo

El centrado usa el bounding box real del grupo y el area util del pliego. Los slots bloqueados quedan protegidos segun la misma politica de herramientas editables.

### Refactor UX de barra PRO

La barra principal quedo simplificada:

- visibles:
  - seleccionar todo
  - centrar bloque
  - paso en mm
  - nudge
- ocultas en panel avanzado:
  - alineacion relativa
  - distribucion horizontal/vertical

La logica existente de align, distribute, nudge y seleccion no se elimino; solo se reorganizo visualmente.

### Seleccion por marco

Se implemento drag select / box select sobre el pliego:

- empieza solo desde area vacia
- muestra rectangulo azul semitransparente
- selecciona slots de la cara activa por interseccion de bbox
- `Shift/Ctrl/Cmd + drag` suma a la seleccion actual
- no interfiere con click simple ni drag de slots
- usa `slot.w_mm/h_mm` como footprint visual real

## Fase 4 - Correcciones profundas de Step & Repeat PRO

### Bleed y spacing

Se corrigio un bug donde `bleed_mm = 0` caia al fallback `bleed_default_mm = 3` por uso de truthiness.

Estado resultante:

- `bleed_mm = 0` es valor explicito valido
- repeat no infla el slot si el PDF ya trae sangrado incorporado
- `slot.bleed_mm` refleja el bleed realmente usado
- `slot.w_mm/h_mm` reflejan la caja final esperada
- repeat toma separacion desde:
  - `spacingSettings.spacingX_mm`
  - `spacingSettings.spacingY_mm`

### Rotacion inteligente

Se corrigio la estrategia de rotacion en repeat:

- compara capacidad sin rotacion vs con rotacion
- no rota si todo entra sin rotar
- rota solo si mejora capacidad
- si rota 90/270, intercambia `w_mm/h_mm`
- las posiciones de grid se calculan con dimensiones ya rotadas

Caso importante documentado:

- diseno 100x50
- 35 formas
- permitir rotacion
- resultado esperado: layout limpio 5x7 con `rotation_deg = 0`

### Semantica consolidada de slot rotado

Queda consolidada esta regla:

- `slot.w_mm / slot.h_mm` = caja final ocupada por el slot en el pliego
- `rotation_deg` = orientacion del contenido del diseno
- el frontend no debe volver a rotar la caja externa si `w_mm/h_mm` ya representan footprint final
- el render PDF debe rotar el contenido dentro de esa caja final, con traslacion correcta

### Render PDF sin stretch

Se corrigio el render de contenido rotado:

- no se fuerza resize deformante
- se respeta la proporcion original
- se aplican compensaciones explicitas para 90/180/270
- el contenido queda dentro de la caja final del slot

### Centrado global del PDF normal

Se corrigio un bug donde el PDF normal podia quedar desplazado aunque CTP lo centrara bien.

Conclusion del bug:

- el problema ya no era geometria individual del slot
- habia un segundo centrado generico que no respetaba el footprint final consolidado

Estado resultante:

- el bbox global usa `slot.w_mm/h_mm` como caja final
- repeat y posiciones manuales no pasan por un segundo centrado incorrecto
- el bloque se centra dentro del area util del pliego
- el PDF normal ya no depende del flujo CTP para quedar completo y centrado

## Fase 4 - Base IA Step & Repeat PRO

### Backend de agente por tools

Se creo una capa intermedia desacoplada en `ai_agent/`:

- `schemas.py`
- `tools_repeat.py`
- `agent_controller.py`

Tools iniciales:

- `analizar_layout(layout)`
- `generar_repeat(layout, config)`
- `optimizar_repeat(layout)`
- `centrar_layout(layout)`
- `aplicar_reglas_repeat(layout, reglas)`

Tambien se agrego:

- `POST /ai/step_repeat_action`

La capa no integra todavia OpenAI API. Por ahora interpreta prompts simples y despacha a tools locales reales.

### Panel IA en frontend

Se integro un panel "Asistente IA" dentro del Editor Visual IA:

- textarea para prompt
- boton `Ejecutar`
- respuesta visible
- boton `Aplicar cambios`

Regla importante:

- ejecutar una accion no reemplaza `state.layout`
- el layout devuelto solo se aplica cuando el usuario confirma con `Aplicar cambios`

### Estado de continuidad

La base queda preparada para el flujo futuro:

`OpenAI -> tool call -> agent_controller -> tools reales -> layout sugerido -> aplicacion manual por usuario`

## 2026-04-22 / 2026-04-23 Fase 5 - Step & Repeat PRO Inteligente

### Objetivo general

Volver mas util el motor Step & Repeat PRO del Editor Visual IA sin pasar a packing complejo ni romper compatibilidad con Fase 4.

### Implementaciones reales cerradas en la rama

- metadata persistida por diseno para repeat:
  - `priority`
  - `preferred_zone`
  - `preferred_flow`
  - `repeat_role`
  - `repeat_manual_overrides`
- ordenamiento base y compatibilidad con layouts viejos
- UI minima inicial para preferencias por diseno
- zonas reales basicas por bandas
- `fill` inteligente para huecos utiles restantes
- simplificacion UX:
  - queda visible solo `Ubicacion`
  - se ocultan:
    - `priority`
    - `repeat_role`
    - `preferred_flow`
- textos amigables en UI:
  - `Automatico`
  - `Arriba`
  - `Abajo`
  - `Izquierda`
  - `Derecha`
  - `Centro`
- `preferred_flow` reservado pero inactivo
- compactacion vertical segura de grupos zonales

### Reglas consolidadas de producto y motor

- `preferred_zone` pasa a ser el control principal visible para el usuario
- `priority` y `repeat_role` se derivan automaticamente cuando no hay override manual
- `preferred_flow` se conserva en contrato, pero no participa del motor
- `fill` se procesa al final para ocupar huecos utiles
- si todo esta en `auto`, se mantiene comportamiento legacy

### Semanticas que se mantuvieron intactas

- `slot.w_mm / slot.h_mm` siguen siendo footprint final en `repeat`
- `rotation_deg` sigue siendo orientacion del contenido
- no se toco semantica de preview/PDF ni `montaje_offset_inteligente.py`

### Limitaciones abiertas al cierre de Fase 5

- no hay compactacion horizontal
- no hay packing avanzado
- `preferred_flow` no tiene implementacion funcional todavia
- la heuristica de `repeat_role` automatico puede requerir ajuste con casos reales

## 2026-04-23 / 2026-04-24 Correcciones finales Fase 5

### Problemas corregidos

- el motor podia aceptar montajes incompletos si no entraban todas las formas solicitadas
- `top/bottom` podia fallar por bandas demasiado rigidas aunque el mismo pliego entrara en `auto/auto`
- una corrida con error no debia contaminar la siguiente ejecucion

### Cambios reales implementados

- validacion estricta por diseno:
  - `requested_forms`
  - `placed_forms`
  - `missing_forms`
- error especifico `IncompleteImpositionError`
- respuesta JSON bloqueante en `apply_imposition`:
  - `ok: false`
  - `error`
  - `details`
- generacion atomica por diseno:
  - los slots se arman primero en memoria local
  - solo se agregan al resultado si el diseno entra completo
- aislamiento de ejecuciones:
  - el backend trabaja sobre copia aislada del layout
  - fuerza `slots = []` antes de regenerar
- expansion vertical inteligente:
  - primero se intenta la banda preferida normal
  - luego, para `top/center/bottom`, se puede expandir hacia el centro
  - si el bloque expandido entra geometricamente, se reconstruye y se compacta

### Diferencia consolidada

- compactacion vertical:
  - acerca grupos ya colocados
- expansion vertical:
  - permite que `top/center/bottom` usen mas altura util si la banda inicial no alcanza

### Flujo validado

- `auto/auto` OK
- `bottom/top` puede entrar si geometricamente cabe tras expansion vertical
- volver a `auto/auto` OK
- si realmente no entra todo:
  - el motor falla
  - no aplica layout incompleto

### Pendientes que quedan abiertos

- no existe expansion horizontal equivalente para `left/right`
- `fill` sigue siendo heuristico
- `preferred_flow` sigue reservado e inactivo

## 2026-04-25 Actualizacion real Fase 5 - Motor, IA y frontend

### Problemas corregidos en Step & Repeat PRO

- `center` podia quedar demasiado rigido:
  - un diseno en `center` podia fallar aunque en `auto` entrara
  - se corrigio permitiendo expansion vertical de `center` como zona unica
- `top/top` y `bottom/bottom` podian fallar por quedar encerrados en la banda inicial:
  - ahora una zona vertical unica puede expandirse si geometricamente cabe
  - `top` queda anclado hacia arriba
  - `bottom` queda anclado hacia abajo
  - `center` queda centrado
- `auto` quedaba fuera de la compactacion vertical:
  - cuando convive con `top`, `center` o `bottom`, se registra su rango de slots
  - se intenta una compactacion final segura de grupos verticales + `auto`
- se mantiene el comportamiento legacy si todos los disenos estan en `auto`

### Garantias conservadas

- `forms_per_plate` sigue siendo estricto
- si faltan formas, se devuelve `IncompleteImpositionError`
- el motor no acepta montajes incompletos silenciosamente
- `slot.w_mm / slot.h_mm` siguen siendo footprint final
- `rotation_deg` sigue siendo orientacion del contenido
- no se tocaron preview/PDF ni `montaje_offset_inteligente.py`

### IA/tools actualizadas

- `set_design_zone` cambia una zona por diseno
- `set_design_zones` permite multiples cambios de zona en una misma instruccion
- `generar_repeat` devuelve layout completo con slots regenerados
- `validar_repeat` interpreta errores del motor sin aplicar layout
- `optimizar_repeat` conserva retry controlado, incluyendo reset de zonas a `auto` si corresponde
- el bridge de OpenAI encadena tools y conserva el ultimo layout generado
- la IA puede identificar disenos por:
  - `ref`
  - `filename`
  - `work_id`
  - dimensiones tipo `50x40`

### Frontend IA

- el panel distingue:
  - `metadata_only`: preferencias listas, sin slots regenerados
  - `layout_with_slots`: cambios visuales listos para aplicar
- se muestran tools usadas cuando la respuesta IA las incluye
- no se debe presentar como montaje generado un cambio que solo modifica metadata

### Limitaciones que siguen abiertas

- no hay expansion horizontal para `left/right`
- no hay compactacion horizontal completa
- no hay packing avanzado
- no existe modo `maximize`
- `preferred_flow` sigue reservado e inactivo
- no hay sistema formal de modos; el motor actual es exacto respecto de `forms_per_plate`

## Fase 6 - Simulador de Cuadernillos

### Objetivo general

Agregar al Editor Visual IA una herramienta visual/logica para que el operador pueda entender el armado de cuadernillos antes de cualquier integracion con PDF o slots.

### Implementaciones reales cerradas

- modulo aislado `cuadernillos/simulator.py`
- endpoint `POST /editor_offset/cuadernillos/simular`
- panel integrado en `templates/editor_offset_visual.html`
- render en `static/js/editor_offset_visual.js`
- estilos en `static/css/editor_offset_visual.css`
- soporte para `cosido_caballete`
- soporte para `sin_tapa` y `tapa_completa`
- selector de cuadernillo 8 / 16
- tapa completa separada como VYV 4 de cara unica
- tripa generada de forma independiente
- patrones reales validados para cuadernillos de 8 y 16 paginas
- VYV 4 y VYV 8 automaticos cuando la tripa no completa otro cuadernillo
- metadata visual para orientacion cabeza con cabeza:
  - `frente_visual`
  - `dorso_visual`
  - `cara_visual`
- jerarquia visual de TAPA, TRIPA y VYV en el editor

### Garantias conservadas

- no se modifico Step & Repeat PRO
- no se modifico `montaje_offset_inteligente.py`
- no se modifico el contrato de `layout_constructor.json`
- no se generan ni modifican `slots[]`
- no se genera PDF desde el simulador

### Validacion

- tests dedicados en `tests/test_cuadernillos_simulator.py`
- casos cubiertos para tapa completa, 28/32/36 paginas, cuadernillo 16, VYV y metadata visual de orientacion

### Limitaciones abiertas

- no hay `tapa_simple`
- no hay otros tipos de encuadernacion
- no hay integracion PDF
- no hay persistencia del resultado simulado

## Fase 6.1 - Panel profesional de lectura de cuadernillo

### Objetivo

Mejorar la lectura operativa del resultado del simulador dentro del Editor Visual IA, convirtiendolo en una hoja tecnica visual para imprenta.

### Mejora implementada

- resumen tecnico superior con:
  - paginas originales
  - paginas finales
  - blancas agregadas
  - tipo de tapa
  - tipo de cuadernillo
  - cantidad de pliegos
- advertencia visible:
  - simulacion visual
  - no genera PDF
  - no modifica el montaje
- badges de paginas por cara en cada pliego
- cabeceras uniformes para:
  - Frente
  - Dorso
  - Cara unica VYV
- estilos profesionales para:
  - resumen operativo
  - tarjetas de pliego
  - badges
  - separacion visual de frente, dorso y VYV

### Alcance tecnico

- solo frontend visual del simulador
- cambios en `static/js/editor_offset_visual.js`
- cambios en `static/css/editor_offset_visual.css`
- sin cambios en `templates/editor_offset_visual.html`
- sin cambios en backend
- sin cambios en `cuadernillos/simulator.py`
- sin cambios en payload, salida JSON, slots, PDF ni `layout_constructor.json`

### Validacion

- se verifico que el payload enviado al endpoint se mantiene igual
- se verificaron casos directos del simulador:
  - 28 paginas + tapa completa + cuadernillo 16
  - 32 paginas + tapa completa + cuadernillo 16
  - 36 paginas + tapa completa + cuadernillo 16
  - 32 paginas + sin tapa + cuadernillo 8
- `git diff --check` no reporto errores
- `node --check` no pudo ejecutarse por acceso denegado a `node.exe`
- `pytest` no pudo ejecutarse porque el entorno Python actual no tenia `pytest` instalado

## Fase 7 - Estabilidad y validacion de salida

### Objetivo general

Cerrar una fase de robustez sin cambiar comportamiento funcional:

- blindar la validacion backend actual antes de preview/PDF
- extraer esa validacion a un modulo chico y testeable
- mantener contratos y respuestas existentes
- registrar una mejora visual safe del editor sin tocar JS ni motores

### Fase 7.1 - Tests de contrato de salida

Se agrego:

- `tests/test_editor_offset_output_contract.py`

Casos cubiertos:

- layout valido
- `design_ref` invalido
- `designs[].ref` duplicado
- `slots[].id` duplicado
- campo numerico faltante
- `face` invalido
- warning por `logical_work_id` sin resolver
- warning por `faces[]` con `back` sin slots de dorso

### Fase 7.2 - Extraccion conservadora del validador

Se agrego:

- `services/editor_offset_output_contract.py`

Se movio desde `routes.py`:

- helper interno `_layout_issue()`
- funcion publica `validate_constructor_output_layout(layout)`

`routes.py` conserva compatibilidad mediante:

- `_validate_constructor_output_layout = validate_constructor_output_layout`

Garantias conservadas:

- no se agregaron validaciones nuevas
- no cambio JSON
- no cambio contrato
- no cambio preview/PDF
- no se tocaron motores
- no se tocaron JS ni templates
- no cambiaron textos, `code`, `path`, `value` ni estructura de errores/warnings

### Mejora visual safe del editor

Se ajusto solo `static/css/editor_offset_visual.css`:

- tipografia y colores generales
- botones con hover/focus visible
- paneles con bordes y sombras sutiles
- accordion avanzado mas legible
- badges y bloques con acabado mas consistente

No cambia:

- listeners
- herramientas
- layout persistido
- payloads
- preview/PDF
- motores

### Validacion ejecutada

En esta rama se uso el `pytest` del virtualenv del proyecto:

- `python -m compileall routes.py services tests`
- `venv\Scripts\pytest.exe tests\test_editor_offset_output_contract.py -q`
- `venv\Scripts\pytest.exe tests\test_cuadernillos_simulator.py tests\test_editor_offset_output_contract.py -q`
- `git diff --check`

Resultado observado:

- tests de contrato de salida: `7 passed`
- tests cuadernillos + contrato de salida: `31 passed`
- `git diff --check` sin errores

Notas:

- pytest puede mostrar warnings de cache por permisos y de dependencias; no afectan los asserts.
- los cambios visuales son CSS-only y no requieren `node --check` porque no modifican JS.

## Fase 8 - Mapa, arquitectura SAFE, shell UX y QA inicial

### Fase 8.0 - Mapa funcional del Editor Visual IA

Se creo `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md` para ordenar el mapa funcional y tecnico del editor antes del redisenio UX.

### Fase 8.1 - Separacion interna SAFE

Se extrajeron responsabilidades de bajo riesgo desde `routes.py`:

- `services/editor_offset_jobs.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_uploads.py`

`routes.py` mantiene wrappers compatibles para no romper endpoints, IA, tests ni imports legacy.

### Fase 8.1B - Step & Repeat PRO

Se creo:

- `engines/step_repeat_pro_engine.py`
- `tests/test_step_repeat_pro_engine.py`

El motor Step & Repeat PRO canonico vive ahora en `engines/step_repeat_pro_engine.py`. `routes.py` conserva wrappers compatibles.

### Fase 8.1C - Servicio de imposicion

Se creo:

- `services/editor_offset_imposition_service.py`

El servicio encapsula la seleccion/aplicacion de `repeat`, `nesting` y `hybrid`. Los endpoints siguen en `routes.py`.

### Fase 8.2 - Shell UX profesional SAFE

Se reorganizo la base visual sin cambiar comportamiento:

- toolbar superior sticky
- canvas/pliego central protagonista
- panel derecho fijo con scroll interno
- ids y controles existentes preservados

### Fase 8.3 - Tabs del panel derecho

Se agregaron tabs como capa visual:

- Pliego
- Trabajos
- Disenos
- Imposicion
- Edicion
- IA
- Cuadernillos
- CTP
- Salida

Los paneles ocultos siguen en el DOM. Se corrigio luego el scroll interno del panel derecho y del tab activo.

### QA Playwright inicial

Se creo:

- `tests/playwright/test_editor_load.py`

Valida carga de `/editor_offset_visual`, existencia de `#sheet`, `#sheet-canvas`, tabs esperados y errores graves de consola JS. El test asume Flask corriendo con `python app.py`.

### Premium Visual Pass SAFE

Se refino visualmente el editor con cambios CSS-only:

- toolbar superior mas tecnica y compacta
- tabs mas densos
- panel derecho con acabado mas profesional
- inputs/selects mas consistentes
- canvas/pliego con fondo tecnico y grid sutil
- estados `selected`, `locked`, `geometry-warning` y `geometry-error` mas legibles
- scrollbars internos pulidos

Luego se realizo una microfase de contraste:

- Snap
- Espaciado
- labels secundarios
- unidades `mm`
- inputs tecnicos
- botones claros dentro de toolbar oscura

Garantias:

- no se toco JS funcional
- no se toco backend
- no se tocaron motores ni contratos
- no se modificaron endpoints ni payloads

### QA Playwright de tabs y scroll

Se agrego:

- `tests/playwright/test_tabs_scroll.py`

Valida:

- tabs visibles por `data-editor-tab`
- click en todos los tabs principales
- panel activo visible
- scroll interno real en `.editor-tab-panels`
- ausencia de errores graves de consola JS

Los tests Playwright requieren Flask corriendo localmente con `python app.py`.

### Decision UX de cierre

No se agrego una barra inferior contextual nueva.

Motivo:

- el bloque actual `Validacion geometrica` ya funciona parcialmente como area contextual/status del editor.
- duplicarlo con otra barra podria agregar ruido y repetir informacion.
- queda como mejora futura evolucionar ese bloque hacia una status bar tecnica compacta o sumar un inspector contextual solo si aporta informacion nueva.

### Cierre Fase 8 antes de merge

Fase 8 queda practicamente completa:

- mapa funcional/tecnico creado
- jobs/defaults/uploads separados
- Step & Repeat PRO extraido y cubierto con tests
- selector de imposicion separado
- `routes.py` como fachada/orquestador con wrappers compatibles
- shell UX profesional
- tabs y scroll interno
- premium visual pass y contraste
- QA Playwright inicial para carga, tabs y scroll

Pendientes trasladados a Fase 9:

- Playwright para drag/resize/seleccion
- Playwright para upload/apply repeat/preview/PDF
- status bar tecnica compacta basada en `geometry-validation-panel`
- inspector contextual futuro sin duplicar informacion
- posible servicio futuro para preview/PDF
- modularizacion frontend por capas

## Fase 9 - Documentacion base y agente SDK asesor

### Contexto

La rama actual `fase9-redisenio-panel-editor` continua la evolucion SAFE del Editor Visual IA, con foco en el panel derecho y en mantener documentacion confiable para cambios posteriores.

### Agente SDK asesor

Se incorporo el prototipo:

- `ai_agent/editor_advisor/`

Caracteristicas actuales:

- OpenAI Agents SDK Python
- CLI-only
- read-only
- sin integracion Flask
- sin endpoints
- sin conexion al panel IA ni a la UI
- tools con allowlist de archivos del repo
- bloqueo de rutas sensibles y externas
- salida estructurada de asesoria tecnica en espanol

### Decision de seguridad

El agente SDK no reemplaza al asistente IA Step & Repeat integrado en el editor. Por ahora funciona como herramienta externa de analisis y planificacion. Cualquier integracion futura con Flask/UI debe tratarse como fase separada, con guardrails, tests y documentacion previa.

### Documentacion actualizada

Queda como prioridad de Fase 9 mantener alineados:

- `AGENTS.md`
- `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md`

Estos documentos alimentan el contexto arquitectonico del agente SDK y deben reflejar el estado real antes de cambios grandes.

## Fase 9.2 - UX SAFE Advisor sobre Agent SDK

### Objetivo

Especializar `ai_agent/editor_advisor/` como asesor UX/UI tecnico del Editor Visual IA, sin cambiar su frontera de seguridad.

### Cambios reales

- `ai_agent/editor_advisor/prompts/editor_advisor.md` pasa a orientar respuestas sobre UX/UI SAFE, panel derecho, sobrecarga visual, densidad y riesgos DOM/listeners.
- `ai_agent/editor_advisor/schemas.py` mantiene compatibilidad y agrega campos UX:
  - `problemas_ux_visuales`
  - `riesgos_dom_listeners`
  - `cambios_css_only_seguros`
  - `cambios_html_js_riesgosos`
  - `zonas_peligrosas_de_tocar`
  - `checklist_ux_antes`
  - `checklist_ux_despues`
  - `fase_safe_sugerida`
- `ai_agent/editor_advisor/tools.py` agrega `summarize_editor_ux_surface()` como tool read-only deterministica.
- `ai_agent/editor_advisor/agent.py` registra la nueva tool.
- `ai_agent/editor_advisor/cli.py` conserva el comando actual y describe el enfoque UX/UI SAFE.
- `tests/test_editor_advisor_tools.py` cubre defaults del schema y comportamiento read-only de las tools.

### Clasificacion SAFE incorporada

- `CSS-only seguro`
- `HTML/DOM riesgoso`
- `JS/listeners riesgoso`
- `backend/contrato prohibido`

### Garantias conservadas

- CLI-only
- read-only
- sin SandboxAgent
- sin Flask
- sin endpoints
- sin UI
- sin cambios productivos en HTML, JS, CSS real del editor, motores, servicios ni contratos

### Validacion ejecutada

- `python -m compileall ai_agent`
- `venv\Scripts\pytest.exe -p no:cacheprovider tests\test_editor_advisor_tools.py`
- `git diff --check`
- validacion de alcance para confirmar que no se tocaron Flask, frontend productivo, motores, servicios ni contratos

Resultado observado:

- tests del agente: `7 passed`

## Fase 9.3 - CSS-only premium pass del panel derecho

### Objetivo

Mejorar visualmente el panel derecho del Editor Visual IA con estetica premium/profesional, mayor jerarquia, menor saturacion, mejor contraste, foco accesible y scroll interno mas legible.

### Cambio real

Se modifico unicamente:

- `static/css/editor_offset_visual.css`

### Bloques refinados

- `.side-panel`
- `.editor-tabs`
- `.editor-tab`
- `.editor-tab-panels`
- `.panel-accordion`
- `.geometry-validation-panel`
- formularios, inputs, selects, textareas, labels y ayudas del panel derecho
- listas y tarjetas internas del panel
- scrollbars internos
- foco visible y estados hover/active

### Garantias conservadas

- no se toco HTML
- no se toco JS
- no se tocaron ids
- no se tocaron `data-editor-tab` ni `data-editor-tab-panel`
- no se duplico `geometry-validation-panel`
- no se toco Flask, `routes.py`, `app.py`, services, engines, contratos JSON, preview/PDF, CTP, Step & Repeat PRO ni cuadernillos
- no se uso `display:none` ni `pointer-events:none` sobre controles funcionales

### Validacion ejecutada

- `git diff --name-only`: confirmo solo `static/css/editor_offset_visual.css`
- validacion de alcance con `rg`: no aparecieron `routes.py`, `app.py`, templates, JS, engines ni services
- `git diff --check`: sin errores; solo avisos CRLF existentes por conversion de line endings

### Validaciones pendientes

- `node --check static/js/editor_offset_visual.js` quedo pendiente/bloqueado por `Acceso denegado` a `node.exe`
- Playwright quedo pendiente porque Flask fue detenido manualmente con `CTRL+C` y no debe relanzarse en ese contexto

### Workflow SAFE consolidado

La continuidad recomendada para fases UX queda:

1. el agente SDK analiza usando `AGENTS.md` y `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md`
2. el agente propone una fase SAFE y clasifica riesgos
3. Codex implementa dentro del alcance aprobado
4. se validan diff, alcance, formato y regresiones disponibles
5. el agente vuelve a auditar antes de nuevas fases

### Comandos operativos registrados

Uso del agente SDK desde PowerShell:

```powershell
venv\Scripts\python.exe -m ai_agent.editor_advisor.cli --pretty "analiza el panel derecho y propone mejoras CSS-only"
venv\Scripts\python.exe -m ai_agent.editor_advisor.cli --pretty "detecta que partes del editor son peligrosas de tocar"
venv\Scripts\python.exe -m ai_agent.editor_advisor.cli --pretty "sugiere una fase SAFE para mejorar UX"
```

Uso de `rg` en validaciones SAFE:

```powershell
git diff --name-only | rg "routes.py|app.py|templates/|static/js/|static/css/|engines/|services/|ai_agent/"
rg -n "9\.2|9\.3|summarize_editor_ux_surface|CSS-only seguro|HTML/DOM riesgoso|JS/listeners riesgoso|backend/contrato prohibido|static/css/editor_offset_visual.css" AGENTS.md DOCS/OFFSET
```

## Fase 9.4 - Codex Prompt Builder

### Objetivo

Hacer que `ai_agent/editor_advisor/` no solo entregue auditoria tecnica/UX, sino tambien un prompt SAFE listo para pegar en Codex y convertir el diagnostico en una siguiente fase planificable.

### Cambios reales

- `ai_agent/editor_advisor/schemas.py` agrega `prompt_para_codex: str = ""` a `EditorAdvisorReport`.
- `ai_agent/editor_advisor/prompts/editor_advisor.md` exige generar un prompt accionable para Codex con:
  - objetivo de fase
  - alcance permitido
  - archivos permitidos
  - archivos prohibidos
  - riesgos detectados
  - instrucciones SAFE
  - validaciones requeridas
  - cierre textual: "Antes de implementar, dame un plan SAFE."
- `ai_agent/editor_advisor/cli.py` agrega `--codex-prompt-only` para imprimir solo el prompt limpio, sin JSON.
- `tests/test_editor_advisor_tools.py` agrega tests del nuevo campo y del render CLI sin llamar OpenAI.

### Comando nuevo

```powershell
venv\Scripts\python.exe -m ai_agent.editor_advisor.cli --codex-prompt-only "analiza el panel derecho y propone mejoras CSS-only"
```

### Garantias conservadas

- CLI-only
- read-only
- sin Flask
- sin endpoints
- sin UI
- sin escritura de archivos
- sin cambios automaticos
- sin tocar frontend productivo, services, engines, contratos JSON ni Step & Repeat PRO

### Validacion ejecutada

- `python -m compileall ai_agent`: OK
- `venv\Scripts\pytest.exe -p no:cacheprovider tests\test_editor_advisor_tools.py`: OK, `10 passed`
- `git diff --check`: OK, solo warnings CRLF
- validacion de alcance: solo 4 archivos del agente/tests; no toco Flask, frontend productivo, services, engines, contratos ni Step & Repeat PRO

### Decision de seguridad

`prompt_para_codex` acelera el traspaso desde auditoria hacia trabajo en Codex, pero no reemplaza la fase de plan. El prompt generado debe pedir explicitamente un plan SAFE antes de implementar.

## Fase 10 - Editor UX Canvas Pro

### Objetivo

Cerrar una fase UX SAFE enfocada en que el Editor Visual IA se sienta mas profesional, compacto y operativo como herramienta CAD/preprensa, con el canvas central como protagonista.

### Fase 10.0 - Auditoria visual y baseline

Se reviso sin modificar archivos:

- header
- topbar
- subtoolbar
- workspace
- canvas
- panel derecho
- `geometry-validation-panel`

Resultado:

- se identificaron selectores seguros para CSS-only
- se mapearon ids/listeners sensibles de barra superior, snap, edicion rapida, frente/dorso, zoom, preview/PDF, IA, CTP y cuadernillos
- se confirmo que cambios HTML/DOM o JS/listeners requeririan fase separada

### Fase 10.1 - CSS-only Canvas Pro Shell

Se modifico unicamente `static/css/editor_offset_visual.css`.

Cambios reales:

- header mas fino
- topbar mas tecnica y compacta
- acciones principales con mejor jerarquia visual
- snap, spacing y edicion rapida mas densos
- selector frente/dorso mas claro
- menor peso visual del marco superior
- canvas central con mayor protagonismo
- `geometry-validation-panel` mas compacto y aun visible

Garantias:

- sin tocar HTML
- sin tocar JS
- sin mover controles
- sin renombrar ids
- sin tocar listeners
- sin cambiar contratos, preview/PDF, CTP, Step & Repeat PRO ni cuadernillos

### Fase 10.2 - CSS-only Panel Derecho Pro Density

Se modifico unicamente `static/css/editor_offset_visual.css`.

Cambios reales:

- tabs del panel derecho mas compactos
- scroll interno con mas espacio util
- accordions mas densos
- inputs, selects, labels y ayudas mas contenidos
- listas de trabajos/disenos mas legibles y compactas
- paneles IA, CTP, Salida y Cuadernillos mejor integrados visualmente
- estetica tecnica coherente con el shell CAD/preprensa

Garantias:

- no se tocaron `data-editor-tab` ni `data-editor-tab-panel`
- no se ocultaron controles funcionales
- no se uso `pointer-events:none` sobre controles
- no se duplico `geometry-validation-panel`

### Fase 10.3 - Agent SDK UX Surface v2

Se actualizaron solo:

- `ai_agent/editor_advisor/tools.py`
- `ai_agent/editor_advisor/prompts/editor_advisor.md`
- `tests/test_editor_advisor_tools.py`

Cambios reales:

- `summarize_editor_ux_surface()` ahora reporta:
  - header/topbar/subtoolbar
  - `.editor-workspace`
  - canvas, `#sheet`, zoom controls y `geometry-validation-panel`
  - panel derecho, tabs, panels, accordions y scroll interno
  - selectores CSS shell/canvas/panel derecho
  - ids por zona
  - listeners sensibles de topbar, snap, spacing, edicion, cara activa, zoom, preview/PDF, IA, CTP y cuadernillos
- el prompt del advisor audita explicitamente Fase 10:
  - header
  - topbar
  - canvas
  - panel derecho
  - density
  - `geometry-validation-panel`
- el schema y CLI se mantuvieron compatibles
- el agente sigue CLI-only/read-only, sin Flask/UI/endpoints y sin escritura

Validacion:

- `python -m compileall ai_agent`: OK
- `venv\Scripts\pytest.exe -p no:cacheprovider tests\test_editor_advisor_tools.py`: OK, `12 passed`
- `git diff --check`: OK, solo warnings CRLF

### Fase 10.4 - QA visual y regresion

QA ejecutada sin aplicar parches.

Validaciones completadas:

- `git diff --check`: OK
- `python -m compileall ai_agent`: OK
- `venv\Scripts\pytest.exe -p no:cacheprovider tests\test_editor_advisor_tools.py`: OK, `12 passed`
- inspeccion estatica de reglas peligrosas: sin nuevas reglas `display:none`, `pointer-events:none`, `visibility:hidden` ni `opacity:0` sobre controles funcionales
- revision de selectores criticos:
  - `.handle`
  - `.slot.selected`
  - `.slot.locked`
  - `.geometry-validation-*`
  - `.editor-tabs`
  - `.editor-tab-panels`
  - `.preview-area`
  - `.pdf-output`
  - `.panel-ctp`
  - `.panel-cuadernillos`
- `geometry-validation-panel` aparece una sola vez en el template
- preview/PDF, CTP y cuadernillos siguen presentes/accesibles en HTML

Playwright:

- Playwright funciona manualmente desde Git CMD segun cierre operativo del usuario.
- En entorno Codex persiste `PermissionError: [WinError 5] Acceso denegado` al crear pipe/subprocess de Playwright antes de abrir navegador.
- Ese error se registra como bloqueo del entorno Codex, no como regresion del Editor Visual IA.

### Cierre de Fase 10

Fase 10 queda considerada estable y cerrada.

No se cambiaron:

- contratos JSON
- HTML
- JS
- Flask
- services
- engines
- Step & Repeat PRO
- preview/PDF
- CTP productivo
- cuadernillos

Fase futura sugerida:

- Fase 11: `Canvas Geometry Polish`

## 2026-06-01 Cierre parcial separacion modular SAFE Fases 1-5B

### Objetivo

Actualizar el estado documental del proyecto despues de completar las Fases 1, 2, 3, 4, 5A y 5B del roadmap de separacion del Editor Visual IA, sin modificar codigo productivo, frontend funcional, backend, tests ni contratos JSON.

### Estado completado

- Fase 1: tests de caracterizacion para congelar comportamiento antes de extraer responsabilidades.
- Fase 2: fachada backend en `services/editor_offset_http_service.py`; `routes.py` conserva URLs publicas y wrappers compatibles.
- Fase 3: output del editor extraido a `services/editor_offset_output_service.py`; `montaje_offset_inteligente.py` conserva wrapper compatible y funciones legacy.
- Fase 4: `ai_agent/tools_repeat.py` usa `engines.step_repeat_pro_engine.build_step_repeat_slots` y deja de depender de helpers internos de `routes.py`.
- Fase 5A: modulos frontend puros extraidos en `static/js/editor_offset_visual/dom_refs.js`, `defaults.js`, `geometry.js`, `geometry_validation.js`.
- Fase 5B: modulos frontend de red/paneles extraidos en `api_client.js`, `output_panel.js`, `ai_panel.js`, `ctp_panel.js`, `booklet_panel.js`.

### Metricas registradas

- Servicios extraidos en el roadmap de separacion: 2 (`editor_offset_http_service.py`, `editor_offset_output_service.py`).
- Modulos JS extraidos: 9 bajo `static/js/editor_offset_visual/`.
- Tests relevantes actuales:
  - `tests/test_editor_offset_characterization.py`
  - `tests/test_step_repeat_pro_engine.py`
  - `tests/test_editor_offset_output_contract.py`
  - `tests/test_cuadernillos_simulator.py`
  - `tests/test_editor_advisor_tools.py`

### Validacion de cierre Fase 5B

- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, `53 passed`.
- `git diff --check`: OK.
- `node --check` sobre `static/js/editor_offset_visual.js` y modulos 5B: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex. No se toco configuracion del sistema.

### Riesgos pendientes

- Fase 5C: renderer/canvas/sheet sigue siendo alto riesgo por `renderSheet`, CTP guide, geometry markers, zoom y dependencias visuales.
- Fase 5D: interacciones complejas siguen siendo alto riesgo por seleccion, drag, resize, box select, nudge, align, distribute y listeners acoplados a IDs.
- Fase 6: movimiento fisico a paquete `editor_offset/` sigue bloqueado hasta tener aliases legacy, tests e imports completamente estabilizados.

### Decision documental

Fase 10 queda como baseline UX historica cerrada. El roadmap activo actual pasa a ser la separacion modular SAFE del Editor Visual IA, con Fases 1-5B completadas y Fases 5C/5D/6 pendientes.

## 2026-06-01 Actualizacion SAFE Editor Advisor SDK post Fases 1-5B

### Objetivo

Actualizar `ai_agent/editor_advisor/` para que audite el estado real del Editor Visual IA despues de las Fases 1-5B, sin modificar codigo productivo del editor, frontend funcional, backend, engines ni contratos JSON.

### Cambios reales

- `ai_agent/editor_advisor/tools.py` amplio la allowlist read-only para incluir:
  - `services/editor_offset_http_service.py`
  - `services/editor_offset_output_service.py`
  - los 9 modulos frontend 5A/5B bajo `static/js/editor_offset_visual/`
  - `ai_agent/tools_repeat.py`
  - `ai_agent/openai_tool_bridge.py`
- `summarize_editor_architecture()` ahora reconoce:
  - `routes.py` como wrapper compatible
  - `editor_offset_http_service.py` como fachada HTTP
  - `editor_offset_output_service.py` como salida preview/PDF real del editor
  - `montaje_offset_inteligente.py` como wrapper legacy
  - modulos JS 5A/5B
  - IA operativa del panel vs advisor SDK
- Se agrego `summarize_editor_modular_surface()` para resumir:
  - modulos cargados por HTML
  - modulos presentes en disco
  - exports `window.EditorOffsetVisual.*`
  - responsabilidades criticas aun en `static/js/editor_offset_visual.js`
  - riesgos pendientes Fase 5C/5D/6
- `summarize_editor_ux_surface()` lee el entrypoint completo para evitar subconteos por truncado.
- `ai_agent/editor_advisor/prompts/editor_advisor.md` queda reenfocado a auditoria estructural post Fases 1-5B, manteniendo UX SAFE.
- `tests/test_editor_advisor_tools.py` cubre servicios, modulos JS, IA operativa, resumen arquitectonico, resumen modular y validaciones recomendadas.

### Garantias conservadas

- `editor_advisor` sigue CLI-only/read-only.
- No se integro a Flask/UI.
- No se agregaron endpoints.
- No se agregaron tools de escritura.
- No se tocaron HTML, JS productivo, CSS productivo, Flask, services productivos, engines, preview/PDF, CTP, cuadernillos ni contratos JSON.

## 2026-06-01 Fase 5C-0 Preparacion SAFE del Renderer Canvas

### Objetivo

Auditar y planificar la futura extraccion del renderer/canvas/sheet del Editor Visual IA sin implementar todavia Fase 5C.

La fase documenta el contrato interno propuesto para `renderSheet`, zoom, sheet, guia CTP, marcadores geometricos y estados visuales, separando las interacciones complejas que quedan reservadas para Fase 5D.

### Mapa de dependencias confirmado

- `renderSheet` sigue siendo la funcion critica del renderer visual.
- `renderSheet` recalcula validacion geometrica, dimensiona `#sheet`, limpia y recrea slots, aplica clases visuales, conecta listeners por slot, renderiza CTP guide, aplica zoom, renderiza distance indicator y actualiza `geometry-validation-panel`.
- `recalcScale`, `mmToPx`, `applyZoom` y `sheetPointFromEvent` conectan `#sheet-canvas`, `#sheet`, `state.scale`, `state.zoom` y `layout.sheet_mm`.
- los estados visuales de slot dependen de `slot.locked`, `state.selectedSlot`, `state.selectedSlots` y `state.geometryValidation.bySlot`.
- `renderCtpGuideOverlay` depende de `layout.ctp.enabled`, `layout.ctp.show_guide`, `layout.ctp.gripper_mm` y de que la cara activa sea `front`.
- `renderGeometryValidationPanel` depende del resultado de `geometry_validation.js` y debe seguir usando el panel unico existente.
- `renderDistanceIndicator` depende de `state.distanceIndicator` y se monta dentro de `#sheet`.

### Contrato interno propuesto para Fase 5C

Futuro modulo sugerido, aun no creado:

- `static/js/editor_offset_visual/renderer_canvas.js`

Responsabilidad esperada:

- renderizar superficie visual del pliego y slots visibles.
- calcular view models de slots sin mutar layout.
- aplicar zoom y escala visual con dependencias explicitas.
- renderizar guia CTP, indicador de distancia y panel de validacion geometrica.
- recibir callbacks de interaccion desde el entrypoint compatible.

Funciones candidatas:

- `recalcSheetScale({ sheetCanvas, layout, minScale })`
- `applySheetZoom({ sheetEl, zoom, zoomLabelEl })`
- `buildVisibleSlotViewModels({ layout, activeFace, selectedSlotId, selectedSlotIds, geometryValidation })`
- `renderSheetSurface(context)`
- `renderCtpGuide({ sheetEl, ctp, activeFace, mmToPx })`
- `renderGeometryValidationPanel({ validation, activeFace, summaryEl, listEl })`
- `renderDistanceIndicator({ sheetEl, distanceIndicator, activeFace, mmToPx })`

Regla clave:

- `renderer_canvas.js` no debe registrar listeners globales ni mutar `state.layout`, seleccion, historial, drag state o contratos.
- `onSlotPointerDown` y `onSlotClick` deben seguir definidos fuera del modulo y pasarse como callbacks hasta una Fase 5D separada.

### Fuera de alcance

- no se implemento `renderer_canvas.js`.
- no se modifico `static/js/editor_offset_visual.js`.
- no se modificaron modulos JS 5A/5B.
- no se modificaron templates.
- no se modifico CSS.
- no se modifico backend, services, engines, strategies, contratos JSON, preview/PDF, CTP productivo, cuadernillos ni Step & Repeat PRO.
- no se agregaron tests en esta fase.

### Checklist de caracterizacion previa a Fase 5C

- `#sheet`, `#sheet-canvas` y `#geometry-validation-panel` deben existir una sola vez.
- cambio de `sheet_mm` debe actualizar ancho y alto visuales del pliego.
- zoom por botones y `Ctrl + wheel` debe conservar transform y label.
- cambio de cara debe filtrar slots `front`/`back` sin mezclar seleccion.
- slots deben conservar clases `.selected`, `.locked`, `.geometry-warning` y `.geometry-error`.
- `.ctp-guide` debe aparecer solo en `front` cuando CTP esta activo y `show_guide` esta habilitado.
- `.distance-indicator` debe aparecer durante drag real y ocultarse al finalizar.
- `geometry-validation-panel` debe mostrar resumen y lista de errores/warnings de la cara activa.
- resize de ventana debe recalcular escala y re-renderizar sin romper la superficie.

### Clasificacion SAFE

- CSS-only seguro: pulido visual de selectores existentes sin ocultar controles.
- HTML/DOM riesgoso: mover `#sheet`, `#sheet-canvas`, `#geometry-validation-panel`, tabs o paneles.
- JS/listeners riesgoso: `renderSheet`, zoom, slot click, pointerdown, box select, drag, resize, nudge, align y distribute.
- backend/contrato prohibido: rutas, services, engines, contratos JSON, preview/PDF, CTP productivo, cuadernillos y Step & Repeat PRO.

### Validacion solicitada

- `git diff --check`: OK, solo warnings LF/CRLF de Git sobre los Markdown editados.

## 2026-06-01 Fase 5C Real inicial - Renderer Canvas

### Objetivo

Implementar la primera extraccion SAFE del renderer/canvas/sheet hacia un modulo frontend clasico, manteniendo `static/js/editor_offset_visual.js` como entrypoint compatible y sin mover interacciones complejas.

### Cambios reales

- Se creo `static/js/editor_offset_visual/renderer_canvas.js` como script clasico bajo `window.EditorOffsetVisual.rendererCanvas`.
- Se cargo el nuevo modulo desde `templates/editor_offset_visual.html` antes del entrypoint principal.
- `static/js/editor_offset_visual.js` conserva wrappers compatibles:
  - `renderSheet`
  - `recalcScale`
  - `applyZoom`
  - `renderGeometryValidationPanel`
- El modulo nuevo contiene helpers de render visual:
  - `recalcSheetScale`
  - `applySheetZoom`
  - `buildVisibleSlotViewModels`
  - `renderSheetSurface`
  - `renderCtpGuide`
  - `renderGeometryValidationPanel`
  - `renderDistanceIndicator`

### Garantias conservadas

- `renderer_canvas.js` no registra listeners globales ni listeners de slot por cuenta propia.
- Los listeners `pointerdown` y `click` de slot siguen registrandose desde el entrypoint mediante callback.
- No se tocaron drag, resize, seleccion, box select, nudge, align, distribute, group/ungroup ni shortcuts.
- No se cambiaron IDs, DOM funcional, CSS, contratos JSON, backend, services, engines, strategies, preview/PDF, CTP productivo, cuadernillos ni Step & Repeat PRO.
- `renderSheet` sigue existiendo como callback compatible para CTP y otros flujos frontend.

### Validacion

- `node --check static/js/editor_offset_visual/renderer_canvas.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, `53 passed`.
- `git diff --check`: OK, solo warnings LF/CRLF de Git sobre archivos editados.
- `git diff --check --no-index NUL static/js/editor_offset_visual/renderer_canvas.js`: sin errores de whitespace; exit code 1 esperado por diferencias contra `NUL`.
- Playwright no se ejecuto porque no habia servidor Flask escuchando en `http://127.0.0.1:5000/editor_offset_visual`.

## 2026-06-01 Fase 5D-0 Auditoria SAFE de Interacciones Complejas

### Objetivo

Auditar las interacciones complejas del Editor Visual IA antes de extraerlas a modulos, sin modificar codigo productivo.

La auditoria se enfoca en seleccion simple/multiple, box select, drag, resize, nudge, align, distribute, group/ungroup, shortcuts y listeners acoplados a IDs/clases. Tambien documenta la frontera con `renderer_canvas.js`, creado en Fase 5C real inicial.

### Mapa de funciones actuales

- Seleccion:
  - `selectSlot`
  - `getSelectedSlotIds`
  - `getSelectedSlots`
  - `selectAllSlotsOnActiveFace`
  - `refreshSelectionAfterEdit`
- Box select:
  - `sheetPointFromEvent`
  - `getBoxSelectionRectMm`
  - `renderBoxSelectionRect`
  - `clearBoxSelectionRect`
  - `resetBoxSelectState`
  - `selectSlotsInBox`
  - `startBoxSelect`
  - `moveBoxSelect`
  - `endBoxSelect`
- Drag/resize:
  - `startDrag`
  - `moveDrag`
  - `endDrag`
  - `onSlotPointerDown`
- Herramientas manuales:
  - `duplicateSlot`
  - `deleteSlot`
  - `groupSelectedSlots`
  - `ungroupSelectedSlots`
  - `alignSelectedSlots`
  - `distributeSelectedSlots`
  - `centerSelectedBlock`
  - `nudgeSelectedSlots`
  - `applyGapToSlots`
  - `applySpacing`
- Listeners acoplados:
  - `attachSlotHandlers` pasado a `renderer_canvas.js`
  - `sheetEl.addEventListener('pointerdown', startBoxSelect)`
  - listeners temporales `document.pointermove`, `document.pointerup`, `document.pointercancel`
  - `document.click` para limpiar seleccion
  - `document.keydown` para undo, Ctrl/Cmd+A y flechas/nudge
  - botones `btn-*` de edicion manual, alineacion, distribucion, nudge, group/ungroup y slots

### Dependencias de estado

- `state.selectedSlot` y `state.selectedSlots` sostienen seleccion simple y multiple.
- `state.activeFace` y `state.layout.active_face` filtran operaciones por frente/dorso.
- `state.layout.slots` es mutado por seleccion aplicada, drag, resize, duplicado, borrado, agrupacion, alineacion, distribucion, nudge, gap y spacing.
- `state.scale` y `state.zoom` participan en conversion pointer -> mm.
- `state.spacingSettings.live` permite aplicar spacing durante drag.
- `dragState` sostiene pointer activo, slot, elemento, coordenadas iniciales, handle, grupo, posiciones iniciales y handlers temporales.
- `boxSelectState` sostiene pointer activo, rectangulo visual, seleccion aditiva, suppress click-clear y handlers temporales.
- `renderer_canvas.js` pinta slots y recibe `attachSlotHandlers`, pero no registra listeners por su cuenta.

### Riesgos detectados

- `moveDrag` mezcla movimiento, resize, snap, grupo, live spacing, distance indicator, render y formulario.
- `boxSelectState.suppressClickClear` evita que el click global borre la seleccion despues de box select; romperlo degrada seleccion.
- `renderSheet` recrea nodos de slot, por lo que los handlers deben re-adjuntarse en cada render desde el entrypoint.
- `applySpacing` se usa desde botones y desde drag live; extraerlo sin caracterizacion puede cambiar posiciones durante arrastre.
- `selectedSlot` y `selectedSlots` conviven como fuentes de seleccion; hay que conservar la semantica de primer seleccionado para el formulario.
- `group_id` afecta drag grupal, duplicado y spacing; no debe tratarse como metadata pasiva.
- shortcuts deben ignorar inputs, textareas y selects para no interferir con edicion de formularios.

### Contrato interno futuro

`slot_interactions.js` futuro:

- debe concentrar seleccion, box select, drag/resize y handlers de interaccion directa con slots.
- API candidata:
  - `createSelectionController(ctx)`
  - `createBoxSelectController(ctx)`
  - `createDragController(ctx)`
  - `attachSlotHandlers(slotEl, slot)`
- debe recibir dependencias explicitas: `state`, `sheetEl`, `sheetCanvas`, geometria, `renderSheet`, `renderSlotForm`, `pushHistory`, `applySnap`, `applySpacing`, `updateDistanceIndicator`, `hideDistanceIndicator`.
- no debe registrar listeners globales en la primera extraccion real; el wiring debe quedar en el entrypoint hasta una fase separada.

`manual_tools.js` futuro:

- debe concentrar operaciones PRO sobre slots seleccionados:
  - duplicar
  - borrar
  - agrupar/desagrupar
  - alinear
  - distribuir
  - centrar bloque
  - nudge
  - gap
  - spacing
- debe conservar proteccion de slots bloqueados, historial, seleccion actual y render mediante wrappers/callbacks del entrypoint.
- no debe tocar DOM estructural, listeners globales, backend ni contratos.

### Que NO debe moverse todavia

- `document.keydown`, `document.click`, `window.resize` y wiring de botones `btn-*`.
- drag/resize completo.
- box select completo.
- listeners temporales de pointer.
- clases e IDs criticos: `.slot`, `.selected`, `.locked`, `.box-selection-rect`, `#sheet`, `#sheet-canvas`, `slot-*`.
- backend, services, engines, contracts JSON, preview/PDF, CTP productivo, cuadernillos y Step & Repeat PRO.

### Plan por fases 5D

- Fase 5D-1: caracterizacion de seleccion simple/multiple, limpiar seleccion, box select, shortcuts y nudge.
- Fase 5D-2: extraer `manual_tools.js` para operaciones sin listeners, manteniendo wrappers en entrypoint.
- Fase 5D-3: extraer controlador de seleccion en `slot_interactions.js`, manteniendo wiring en entrypoint.
- Fase 5D-4: extraer box select con cobertura de click vs drag y seleccion aditiva.
- Fase 5D-5: extraer drag/resize solo con cobertura especifica de snap, grupos, live spacing, distancia util e historial.

### Garantias conservadas

- No se modifico `static/js/editor_offset_visual.js`.
- No se creo `slot_interactions.js`.
- No se creo `manual_tools.js`.
- No se tocaron templates, CSS, backend, services, engines, strategies, contratos JSON, preview/PDF, CTP productivo ni cuadernillos.
- No se agregaron tests.

### Validacion solicitada

- `git diff --check`: OK, solo warnings LF/CRLF de Git sobre los Markdown editados.

---

## 2026-06-01 - Fase 5D-1 SAFE: caracterizacion UI de herramientas manuales

Se agrego cobertura Playwright de caracterizacion para interacciones complejas antes de extraer `manual_tools.js`.

Archivo creado:

- `tests/playwright/test_editor_manual_interactions.py`

Cobertura agregada:

- seleccion simple mediante click sobre `.slot`
- seleccion multiple mediante Ctrl+click
- Ctrl+A sobre el editor
- duplicado de seleccion desde `#btn-dup-slot`
- borrado de seleccion desde `#btn-del-slot`
- agrupar y desagrupar desde `#btn-group-slots` y `#btn-ungroup-slots`
- nudge desde controles UI reales y `#nudge-step`
- alineacion desde herramientas avanzadas
- distribucion desde herramientas avanzadas

Garantias conservadas:

- Los tests operan exclusivamente mediante UI publica.
- No se accede a `state` interno ni a APIs privadas del editor.
- No se aplican monkeypatches ni hacks sobre el editor.
- Los locators de slots se reconsultan despues de renders.
- Las coordenadas se modifican desde controles UI reales del formulario de slot.
- No se modifico `static/js/editor_offset_visual.js`.
- No se modifico `static/js/editor_offset_visual/renderer_canvas.js`.
- No se tocaron templates, CSS, backend, services, engines, contratos JSON, preview/PDF, CTP productivo ni cuadernillos.

Validaciones:

- `git diff --check`: OK antes del cierre documental.
- `venv\Scripts\pytest.exe tests\playwright\test_editor_manual_interactions.py -s`: fallo inicialmente en sandbox por `PermissionError: [WinError 5] Acceso denegado` al inicializar Playwright/subprocess.
- `venv\Scripts\pytest.exe tests\playwright\test_editor_manual_interactions.py -s` fuera del sandbox: OK, 2 passed.

---

## 2026-06-01 - Fase 5D-2 SAFE: manual_tools puro-compatible

Se implemento la primera extraccion SAFE de herramientas manuales hacia un modulo frontend clasico sin listeners.

Cambios reales:

- Se creo `static/js/editor_offset_visual/manual_tools.js` bajo `window.EditorOffsetVisual.manualTools`.
- Se cargo `manual_tools.js` desde `templates/editor_offset_visual.html` antes del entrypoint.
- `static/js/editor_offset_visual.js` conserva wrappers compatibles para:
  - `duplicateSlot`
  - `deleteSlot`
  - `groupSelectedSlots`
  - `ungroupSelectedSlots`
  - `alignSelectedSlots`
  - `distributeSelectedSlots`
  - `centerSelectedBlock`
  - `nudgeSelectedSlots`
  - `applyGapToSlots`
  - `applySpacing`

Garantias conservadas:

- `manual_tools.js` no accede al DOM, no registra eventos, no llama `renderSheet`, `renderSlotForm`, `pushHistory` ni `alert`.
- El entrypoint conserva wiring de botones, shortcuts, render, historial, seleccion y lectura de inputs DOM.
- `applySpacing` mantiene el wrapper actual y sigue siendo llamado desde drag live sin mover `moveDrag` ni estado efimero de drag.
- No se tocaron drag, resize, box select, selection controller, `document.keydown`, `document.click` ni `sheetEl.pointerdown`.
- No se tocaron backend, services, engines, contracts JSON, CSS, preview/PDF, CTP productivo ni cuadernillos.

Validaciones:

- `node --check static/js/editor_offset_visual/manual_tools.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/renderer_canvas.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, 53 passed.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_manual_interactions.py -s`: fallo inicialmente en sandbox por `PermissionError: [WinError 5] Acceso denegado`; reejecutado fuera del sandbox: OK, 2 passed.
- `git diff --check`: OK antes del cierre documental, solo warnings LF/CRLF de Git sobre archivos editados.

---

## 2026-06-01 - Sincronizacion documental post 5C y 5D-2

Se actualizo la documentacion corta para reflejar el estado real antes de planificar Fase 5D-3.

Cambios documentales:

- `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md` ahora registra `renderer_canvas.js`, `manual_tools.js` y `tests/playwright/test_editor_manual_interactions.py` como activos.
- `DOCS/OFFSET/04_PLAN_OFFSET.md` mueve Fase 5C, Fase 5D-1 y Fase 5D-2 a completadas.
- Se mantienen como pendientes Fase 5D-3, Fase 5D-4, Fase 5D-5 y Fase 6.

Garantias:

- No se declaro Fase 5D completa.
- Drag, resize, box select, selection controller y shortcuts globales siguen pendientes.
- No se tocaron JS, templates, CSS, backend, services, engines, contratos JSON ni tests.

---

## 2026-06-01 - Fase 5D-3 SAFE: Selection Controller

Se implemento la extraccion inicial de seleccion simple/multiple hacia un modulo frontend clasico sin listeners.

Cambios reales:

- Se creo `static/js/editor_offset_visual/slot_interactions.js` bajo `window.EditorOffsetVisual.slotInteractions`.
- Se cargo `slot_interactions.js` desde `templates/editor_offset_visual.html` antes del entrypoint.
- `static/js/editor_offset_visual.js` conserva wrappers compatibles para:
  - `selectSlot`
  - `getSelectedSlotIds`
  - `getSelectedSlots`
  - `selectAllSlotsOnActiveFace`
  - `refreshSelectionAfterEdit`

Garantias conservadas:

- `slot_interactions.js` no accede al DOM, no registra eventos, no llama `renderSheet`, `renderSlotForm`, `pushHistory` ni `alert`.
- El entrypoint conserva render, formulario, wiring, shortcuts, `attachSlotHandlers`, `document.keydown`, `document.click` y `sheetEl.pointerdown`.
- No se movio `getSelectedSlot`.
- No se movio `selectSlotsInBox`.
- No se tocaron drag, resize, box select, `manual_tools.js`, `renderer_canvas.js`, backend, services, engines, CSS, contracts JSON, preview/PDF, CTP productivo ni cuadernillos.

Validaciones:

- `node --check static/js/editor_offset_visual/slot_interactions.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/manual_tools.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/renderer_canvas.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, 53 passed.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_manual_interactions.py -s`: fallo inicialmente en sandbox por `PermissionError: [WinError 5] Acceso denegado`; reejecutado fuera del sandbox: OK, 2 passed.

---

## 2026-06-02 - Fase 5D-4 SAFE: Box Select Controller

Se implemento la extraccion SAFE de la logica de box select hacia el controlador de interacciones existente, sin mover listeners ni estado efimero sensible.

Cambios reales:

- `static/js/editor_offset_visual/slot_interactions.js` ahora expone `slotInteractions.boxSelect`.
- `static/js/editor_offset_visual.js` conserva wrappers compatibles para:
  - `getBoxSelectionRectMm`
  - `renderBoxSelectionRect`
  - `clearBoxSelectionRect`
  - `resetBoxSelectState`
  - `selectSlotsInBox`
  - `startBoxSelect`
  - `moveBoxSelect`
  - `endBoxSelect`
- Se agrego cobertura Playwright minima de box select en `tests/playwright/test_editor_manual_interactions.py`.

Garantias conservadas:

- `boxSelectState` sigue viviendo en el entrypoint.
- `suppressClickClear` sigue viviendo en el entrypoint.
- `dragState.active` sigue validandose en el entrypoint.
- `sheetEl.pointerdown` no se movio.
- `document.pointermove`, `document.pointerup` y `document.pointercancel` temporales no se movieron.
- `slotInteractions.boxSelect` no accede al DOM, no registra eventos, no llama `renderSheet`, `renderSlotForm`, `pushHistory` ni `alert`.
- No se tocaron drag, resize, `manual_tools.js`, `renderer_canvas.js`, templates, CSS, backend, services, engines, contratos JSON, preview/PDF, CTP productivo ni cuadernillos.

Validaciones:

- `node --check static/js/editor_offset_visual/slot_interactions.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/manual_tools.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/renderer_canvas.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, 53 passed.
- `venv\Scripts\pytest.exe tests\playwright\test_editor_manual_interactions.py -s`: OK, 3 passed con Flask temporal local.
- `git diff --check`: OK antes del cierre documental, solo warnings LF/CRLF de Git sobre archivos editados.

---

## 2026-06-02 - Fase 5D-5-0 SAFE: caracterizacion drag/resize

Se agrego cobertura Playwright UI-only para caracterizar drag/resize antes de extraer un controller.

Archivo creado:

- `tests/playwright/test_editor_drag_resize_interactions.py`

Cobertura agregada:

- drag simple mueve un slot desde la UI y conserva seleccion.
- durante drag simple aparece `.distance-indicator` y se limpia al finalizar.
- drag de slot agrupado mueve tambien los miembros del grupo.
- live spacing activo no rompe render ni seleccion durante drag.
- resize queda caracterizado como latente cuando no existen handles reales `.slot .handle` en el renderer activo.

Hallazgos:

- El renderer activo no crea handles reales de resize en los slots; por tanto, la logica de resize por `.handle.br/.bl/.tr/.tl` queda como soporte latente en `static/js/editor_offset_visual.js`.
- No se implemento `dragResize` controller.
- No se modifico `static/js/editor_offset_visual.js`.
- No se modificaron `slot_interactions.js`, `renderer_canvas.js`, `manual_tools.js`, templates, CSS, backend, services, engines, contracts JSON, preview/PDF, CTP productivo ni cuadernillos.

Validaciones:

- `git diff --check`: OK antes del cierre documental.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_drag_resize_interactions.py -s`: OK, 4 passed con Flask temporal local.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_manual_interactions.py -s`: OK, 3 passed con Flask temporal local.

---

## 2026-06-02 - Fase 5D-5 Real SAFE: Drag Controller inicial

Se implemento la extraccion inicial de logica de drag/move no-resize hacia `slotInteractions.dragResize`, manteniendo el entrypoint compatible y sin activar resize.

Cambios reales:

- `static/js/editor_offset_visual/slot_interactions.js` ahora expone `slotInteractions.dragResize`.
- `static/js/editor_offset_visual.js` conserva wrappers compatibles para:
  - `onSlotPointerDown`
  - `startDrag`
  - `moveDrag`
  - `endDrag`
- Se extrajo al subcontrolador:
  - construccion de estado inicial de drag
  - deteccion de drag grupal
  - `groupInitialPositions`
  - calculo de delta mm desde pointer y escala efectiva
  - movimiento de slot o grupo usando `applySnap` como callback
  - resultado final de seleccion al terminar drag
  - reset de `dragState`

Garantias conservadas:

- Los listeners temporales `document.pointermove`, `document.pointerup` y `document.pointercancel` siguen en `static/js/editor_offset_visual.js`.
- `setPointerCapture` y `releasePointerCapture` siguen en el entrypoint.
- `renderSheet`, `renderSlotForm`, `pushHistory`, `applySpacing` live, `updateDistanceIndicator` y `hideDistanceIndicator` siguen en el entrypoint.
- Resize queda latente: no se crearon handles, no se activo resize y la rama legacy por `.handle` no se movio al controller.
- No se tocaron `renderer_canvas.js`, `manual_tools.js`, templates, CSS, backend, services, engines, contracts JSON, preview/PDF, CTP productivo ni cuadernillos.

Validaciones:

- `node --check static/js/editor_offset_visual/slot_interactions.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/manual_tools.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `node --check static/js/editor_offset_visual/renderer_canvas.js`: bloqueado por `Acceso denegado` a `node.exe` en entorno Codex.
- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`: OK.
- `venv\Scripts\pytest.exe tests\test_step_repeat_pro_engine.py tests\test_editor_offset_output_contract.py tests\test_cuadernillos_simulator.py tests\test_editor_offset_characterization.py -q -p no:cacheprovider`: OK, 53 passed.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_manual_interactions.py -s`: OK, 3 passed con Flask temporal local.
- `venv\Scripts\pytest.exe tests/playwright/test_editor_drag_resize_interactions.py -s`: OK, 4 passed con Flask temporal local.
- `git diff --check`: OK antes del cierre documental, solo warnings LF/CRLF de Git sobre archivos editados.
