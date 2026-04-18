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

## Limitaciones conocidas

- siguen coexistiendo flujos offset legacy en el repo
- `routes.py` continua concentrando mucha orquestacion
- la semantica de `w_mm/h_mm` sigue siendo sensible y depende del engine
- la validacion geometrica usa bounding box simple, no geometria rotada exacta
- parte del feedback UX sigue apoyandose en `alert()`
- no hay schema formal completo del layout ni del slot

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

1. auditar semantica geometrica exacta de slots y rotaciones en salida final
2. endurecer schema y validaciones del contrato sin romper compatibilidad
3. mejorar surfacing de errores y warnings del editor sin refactor masivo
4. recien luego evaluar micro-refactors internos
