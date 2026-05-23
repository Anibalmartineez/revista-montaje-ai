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
