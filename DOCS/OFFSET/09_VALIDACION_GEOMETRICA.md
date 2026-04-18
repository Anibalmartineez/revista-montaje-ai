# 09 VALIDACION GEOMETRICA

## Objetivo

Agregar validación geométrica básica dentro del editor visual IA para detectar problemas antes de generar preview/PDF, sin tocar:

- motores backend
- semántica de imposición
- lógica de bleed/crop
- contratos persistidos

## Alcance implementado

Principalmente en:

- `static/js/editor_offset_visual.js`
- `templates/editor_offset_visual.html`
- `static/css/editor_offset_visual.css`

## Qué valida

La validación corre sobre `state.layout.slots` y genera:

- `errors`
- `warnings`

guardados en:

- `state.geometryValidation`

## Tipos de validación

### 1. `OUT_OF_SHEET`

Error.

Detecta si el slot sale del pliego total:

- `x_mm < 0`
- `y_mm < 0`
- `x_mm + w_mm > sheet_mm[0]`
- `y_mm + h_mm > sheet_mm[1]`

### 2. `OUT_OF_USABLE_AREA`

Warning.

Detecta si el slot invade márgenes o sale del área útil:

- `x_mm < margen_izquierdo`
- `y_mm < margen_inferior`
- `x_mm + w_mm > sheet_mm[0] - margen_derecho`
- `y_mm + h_mm > sheet_mm[1] - margen_superior`

### 3. `GRIPPER`

Warning.

Si `ctp.enabled = true`, detecta si el slot invade la zona de pinza inferior:

- `y_mm < ctp.gripper_mm`

Esta regla sigue la implementación visual actual del editor, donde la guía de pinza está en el borde inferior.

### 4. `OVERLAP`

Warning.

Detecta superposición entre slots usando bounding boxes simples:

- `(x, y, w, h)`

Solo compara slots de la misma cara:

- `front` con `front`
- `back` con `back`

## Qué no valida

- precisión geométrica con rotaciones reales
- intersección poligonal
- semántica de trim vs caja final
- consistencia por engine (`repeat`, `nesting`, `hybrid`)
- conflictos de bleed/crop
- referencias cruzadas de contrato backend
- tamaño real del PDF asignado

## Limitaciones conocidas

### Bounding box simple

La validación de overlap usa:

- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`

sin recalcular caja efectiva por rotación. Es una validación rápida de ayuda visual, no un detector geométrico exacto.

### Márgenes

La validación distingue:

- fuera del pliego total
- fuera del área útil

pero no corrige nada automáticamente.

### Pinza / CTP

Se considera la pinza en el borde inferior, coherente con la UI actual.

## Integración visual

### Slots

Cada slot visible puede recibir clases:

- `geometry-error`
- `geometry-warning`

### Tooltip simple

Cada slot con problemas recibe `title` con el detalle acumulado.

### Panel debajo del pliego

Se agregó un panel:

- resumen por cara visible
- lista de errores/warnings
- sin bloquear edición

## Cuándo se recalcula

La validación se recalcula dentro de `renderSheet()`, por lo tanto se actualiza después de:

- drag
- resize
- apply slot
- apply gap
- spacing
- CTP
- duplicate face
- apply imposition
- cambios de pliego
- cambio de cara visible

Además se refresca explícitamente antes de:

- `requestPreview()`
- `requestPdf()`

## Comportamiento frente a preview/PDF

No bloquea acciones.

Si hay problemas geométricos:

- el editor muestra advertencia local
- el panel queda actualizado
- preview/PDF pueden seguir

El bloqueo real de salida sigue estando en la validación backend del contrato persistido.

## Beneficio concreto

Esta capa mejora la confiabilidad operativa del editor porque permite detectar antes:

- piezas salidas del pliego
- piezas invadiendo márgenes
- piezas dentro de pinza
- superposiciones simples

sin tocar los motores de imposición ni cambiar el contrato existente.
