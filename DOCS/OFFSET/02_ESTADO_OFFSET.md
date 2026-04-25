# 02 ESTADO OFFSET

## Estado actual real

Hoy el repo sigue teniendo varios flujos offset coexistiendo, pero el **Editor Visual IA** ya quedo delimitado, auditado y documentado como subsistema propio dentro del modulo.

## Flujo bajo foco en esta fase

### Editor visual IA nuevo

- ruta: `GET /editor_offset_visual`
- template: `templates/editor_offset_visual.html`
- frontend principal: `static/js/editor_offset_visual.js`
- estilos principales: `static/css/editor_offset_visual.css`
- backend de orquestacion: `routes.py`
- motor de salida final: `montaje_offset_inteligente.py`
- motor de nesting auxiliar: `engines/nesting_pro_engine.py`

Este fue el unico flujo trabajado funcionalmente en esta fase.

## Capacidades actuales confirmadas

- carga y persistencia por job via `layout_constructor.json`
- definicion de pliego, margenes y caras frente/dorso
- alta y edicion de trabajos logicos
- subida de PDFs y metadata por diseno
- generacion de slots por IA de trabajos logicos
- imposicion `repeat`, `nesting` y `hybrid`
- edicion manual de slots
- agrupacion y desagrupacion de slots
- duplicado de frente a dorso
- ajustes CTP desde frontend
- preview y PDF final desde layout persistido
- Step & Repeat PRO corregido para:
  - respetar `bleed_mm = 0`
  - usar spacing global del editor
  - elegir rotacion solo si mejora capacidad
  - intercambiar `w_mm/h_mm` cuando rota
  - evitar stretch en PDF
  - centrar el bloque correctamente en PDF normal
- seleccion avanzada:
  - seleccionar toda la cara activa
  - centrado horizontal, vertical y completo de bloque
  - seleccion por marco desde area vacia
- panel de Asistente IA conectado a `POST /ai/step_repeat_action`
- Step & Repeat PRO Inteligente en Fase 5:
  - metadata por diseno persistida y normalizada
  - ordenamiento base por `forms_per_plate`, prioridad y rol derivado
  - `preferred_zone` editable desde UI
  - zonas reales basicas para `top`, `bottom`, `left`, `right`, `center`, `auto`
  - `fill` inteligente al final para aprovechar huecos restantes
  - compactacion vertical segura para grupos `top/center/bottom`
  - expansion vertical inteligente para `top/center/bottom` cuando la banda inicial no alcanza
  - validacion estricta de `forms_per_plate` por diseno
  - error bloqueante si faltan formas solicitadas
  - generacion atomica por diseno para evitar slots parciales
  - aislamiento de ejecuciones para que un error anterior no contamine la siguiente corrida

## Validaciones implementadas

### Backend antes de preview/PDF

Documentadas en `08_VALIDACION_SALIDA.md`.

Implementadas:

- unicidad de `designs[].ref`
- unicidad de `slots[].id`
- verificacion de `slots[].design_ref`
- validacion basica de `slot.face`
- validacion numerica minima de campos criticos
- ancho y alto mayores que cero
- warnings para `logical_work_id` no resuelto
- warnings para cara `back` declarada sin slots de dorso

### Frontend visual

Documentadas en `09_VALIDACION_GEOMETRICA.md`.

Implementadas:

- fuera de pliego total
- fuera de area util
- invasion de zona de pinza CTP
- overlap simple por bounding box

## Mejoras UX implementadas

### Indicador de distancia util durante drag

Documentado en `10_INDICADOR_DISTANCIA_UTIL.md`.

Implementado:

- distancia al margen util mas cercano
- distancia al slot vecino mas cercano de la misma cara
- distancia a pinza si CTP esta activo

### Correccion de interaccion click vs drag

Implementada en frontend:

- click simple vuelve a seleccionar el slot normalmente
- drag solo comienza despues de un umbral minimo de movimiento
- el indicador aparece solo en drag real
- al terminar el drag, el slot arrastrado queda seleccionado

### Herramientas pro iniciales de edicion manual

Documentadas en `11_HERRAMIENTAS_EDICION_PRO.md`.

Implementado:

- alineacion de seleccion
- distribucion horizontal y vertical
- nudge por botones y teclado
- paso configurable en mm
- `Shift` multiplica el paso por 10
- `Alt` reduce el paso a 0.1x
- duplicado y borrado multi-slot
- proteccion de slots bloqueados

### Herramientas de bloque y seleccion avanzada

Implementado:

- seleccionar todos los slots de la cara activa
- `Ctrl/Cmd + A` cuando el foco no esta en inputs
- centrar seleccion en eje horizontal
- centrar seleccion en eje vertical
- centrar bloque completo
- calculo de bbox con footprint real del slot
- seleccion por marco con rectangulo visual
- `Shift/Ctrl/Cmd + drag` suma seleccion
- drag select solo empieza desde area vacia del pliego

### UX de toolbar PRO

Implementado:

- correccion de textos rotos por encoding en la barra PRO
- etiquetas legibles para herramientas de alineacion y nudge
- barra principal simplificada con:
  - seleccionar todo
  - centrar bloque
  - paso + nudge
- panel avanzado colapsable para alineacion y distribucion

### Base IA Step & Repeat PRO

Implementado:

- carpeta `ai_agent/`
- schemas `ToolRequest` y `ToolResponse`
- tools repeat:
  - `analizar_layout(layout)`
  - `generar_repeat(layout, config)`
  - `optimizar_repeat(layout)`
  - `centrar_layout(layout)`
  - `aplicar_reglas_repeat(layout, reglas)`
- controller simple `handle_agent_request(prompt, layout)`
- endpoint `POST /ai/step_repeat_action`
- panel frontend "Asistente IA"
- aplicacion del layout devuelto solo al confirmar con "Aplicar cambios"

### UI actual de disenos en Fase 5

Implementado:

- `Formas/pliego`
- `Ancho`
- `Alto`
- `Bleed`
- `Permitir rotacion`
- `Ubicacion`

No visibles al usuario final:

- `priority`
- `repeat_role`
- `preferred_flow`

Detalles confirmados:

- el select visible usa textos amigables:
  - `Automatico`
  - `Arriba`
  - `Abajo`
  - `Izquierda`
  - `Derecha`
  - `Centro`
- internamente los values siguen siendo:
  - `auto`
  - `top`
  - `bottom`
  - `left`
  - `right`
  - `center`
- `fill` no aparece como opcion visible de ubicacion

### Automatismos backend Fase 5

Implementado en `routes.py`:

- `priority` automatico si no hay override manual
- `repeat_role` automatico si no hay override manual
- `preferred_flow` reservado pero inactivo
- `repeat_manual_overrides` para distinguir valores historicos/manuales de defaults automaticos

Reglas actuales observadas:

- mayor `forms_per_plate` tiende a quedar primero
- el diseno principal puede quedar como `primary`
- zonas explicitas se respetan por encima del rol derivado
- `fill` se usa al final para ocupar espacio restante
- si todo esta en `auto`, se conserva el comportamiento legacy
- `forms_per_plate` ya no se trata como intencion blanda:
  - si no entran todas las formas solicitadas, el motor falla
  - el error informa `requested_forms`, `placed_forms` y `missing_forms`
- `preferred_zone` funciona como preferencia de inicio:
  - primero se intenta la banda zonal normal
  - si `top/center/bottom` no entran completos y la geometria lo permite, se intenta expansion vertical antes de fallar
- `apply_imposition` no debe aplicar layouts incompletos:
  - backend devuelve `ok: false`
  - frontend no reemplaza `state.layout` en ese caso

## Limitaciones conocidas

- siguen coexistiendo flujos offset legacy en el repo
- `routes.py` continua concentrando mucha orquestacion
- la semantica de `w_mm/h_mm` ya quedo consolidada para `repeat`, pero sigue siendo punto sensible frente a otros engines y flujos legacy
- la validacion geometrica usa bounding box simple, no geometria rotada exacta
- parte del feedback UX sigue apoyandose en `alert()`
- no hay schema formal completo del layout ni del slot
- no hay tests automatizados especificos para todos los casos recientes de repeat/rotacion/PDF
- la IA integrada es una base por tools locales y prompt simple; todavia no hay OpenAI tool calling conectado
- falta edicion masiva avanzada de propiedades de slots
- `preferred_flow` existe en contrato pero todavia no tiene efecto real en el motor
- no hay compactacion horizontal de grupos zonales
- la compactacion actual solo intenta casos verticales `top/center/bottom`
- `left/right` no tienen expansion horizontal equivalente todavia
- `fill` mejorado no reemplaza un packing real

## Frontera de alcance vigente

### Dentro del alcance de continuidad

- `/editor_offset_visual`
- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`
- endpoints `/editor_offset/*` y `/editor_offset_visual/apply_imposition`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`

### Fuera del alcance por ahora

- `/montaje_offset`
- `/montaje_offset_inteligente`
- `/imposicion_offset_auto`
- `montaje_offset.py`
- `montaje_offset_personalizado.py`
- `imposicion_offset_auto.py`
- `montaje.py`

## Foco siguiente sugerido

1. cubrir con pruebas o fixtures los bugs corregidos de repeat:
   - bleed 0
   - spacing
   - rotacion inteligente
   - PDF sin stretch
   - centrado global normal
2. endurecer schema y validaciones del contrato sin romper compatibilidad
3. conectar OpenAI tool calls sobre la capa `ai_agent/`
4. mejorar surfacing de errores y warnings del editor sin refactor masivo
5. medir con casos reales si la heuristica automatica de `repeat_role` necesita ajuste
6. recien luego evaluar micro-refactors internos
