# 03 AUDITORIA OFFSET

## Alcance de esta auditoria

Auditado exclusivamente el flujo real actual del editor visual IA de offset, sin cambiar logica.

## 1. Que ruta Flask renderiza `/editor_offset_visual`

- Ruta: `GET /editor_offset_visual`
- Funcion: `editor_offset_visual` en `routes.py`
- Flujo:
  - toma `job_id` desde querystring
  - si no existe, genera uno nuevo
  - carga o inicializa layout con `_load_or_init_constructor_layout`
  - renderiza `editor_offset_visual.html`

## 2. Que template HTML usa

- `templates/editor_offset_visual.html`

## 3. Que archivos JS y CSS participan directamente

### Directos

- JS: `static/js/editor_offset_visual.js`
- CSS: `static/css/editor_offset_visual.css`

### Inline relevante en el template

- script que define:
  - `window.INITIAL_LAYOUT_JSON`
  - `window.JOB_ID`

No se observan otros assets JS/CSS cargados directamente por ese template.

## 4. Que endpoints llama el frontend

- `POST /editor_offset/save`
- `POST /editor_offset/auto_layout/<job_id>`
- `POST /editor_offset_visual/apply_imposition`
- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`
- `POST /editor_offset/upload/<job_id>`

Ademas, la pantalla entra por:

- `GET /editor_offset_visual`

## 5. Que funciones Python procesan esos endpoints

### Carga pantalla

- `routes.editor_offset_visual`

### Guardar layout

- `routes.editor_offset_save`

### Subir PDFs

- `routes.editor_offset_upload`

### Generar slots con IA

- `routes.editor_offset_auto_layout`
- helper principal: `routes._generate_slots_with_ai`

### Aplicar motor de imposicion

- `routes.editor_offset_apply_imposition`
- helper principal: `routes._apply_imposition_engine`

### Preview

- `routes.editor_offset_preview`
- motor: `montaje_offset_inteligente.montar_offset_desde_layout`

### PDF final

- `routes.editor_offset_generar_pdf`
- motor: `montaje_offset_inteligente.montar_offset_desde_layout`

## 6. Que modulos intervienen realmente por subflujo

### Cargar editor

- `routes.py`
- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`

### Subir PDFs

- frontend: `static/js/editor_offset_visual.js` -> `uploadDesigns()`
- backend: `routes.editor_offset_upload`
- auxiliares:
  - `werkzeug.secure_filename`
  - `routes._pdf_page_size_mm`
  - persistencia en `layout_constructor.json`

### Definir formas por pliego

- frontend: `renderDesigns()` y handlers de `forms_per_plate`
- persistencia: `layout.designs[].forms_per_plate`
- backend:
  - `routes.editor_offset_upload` inicializa defaults
  - `routes._ensure_imposition_fields` garantiza defaults

### Aplicar motor de imposicion

- frontend: `applyImpositionEngine()`
- backend: `routes.editor_offset_apply_imposition`
- motores reales:
  - repeat: `routes._build_step_repeat_slots`
  - nesting: `engines.nesting_pro_engine.compute_nesting`
  - hybrid: `routes._repeat_pattern_over_sheet`

### Editar slots manualmente

- casi todo ocurre en frontend:
  - `renderSheet()`
  - drag/resize
  - `applySlotForm()`
  - `addSlot()`
  - `duplicateSlot()`
  - `deleteSlot()`
  - `groupSelectedSlots()`
  - `ungroupSelectedSlots()`
  - spacing / gap / step-repeat local
- backend solo persiste con `editor_offset_save`

### Duplicar a dorso

- frontend: `duplicateFrontToBack()`
- backend no participa en la duplicacion
- backend solo consume luego `slot.face` al generar preview/PDF

### Aplicar produccion / CTP

- frontend:
  - `readCtpParamsFromUI()`
  - `applyCtpAlignment()`
  - `disableCtpAdjustments()`
- backend de salida:
  - `montaje_offset_inteligente.montar_offset_desde_layout`
  - `montaje_offset_inteligente.realizar_montaje_inteligente`

### Generar preview

- frontend: `requestPreview()`
- backend: `routes.editor_offset_preview`
- motor: `montaje_offset_inteligente.montar_offset_desde_layout`
- render final: `montaje_offset_inteligente.realizar_montaje_inteligente`

### Generar PDF final

- frontend: `requestPdf()`
- backend: `routes.editor_offset_generar_pdf`
- motor: `montaje_offset_inteligente.montar_offset_desde_layout`
- render final: `montaje_offset_inteligente.realizar_montaje_inteligente`

## 7. Cuales de estos archivos se usan realmente desde el editor visual IA

### `montaje_offset_inteligente.py`

- Si, se usa realmente.
- Uso directo:
  - `realizar_montaje_inteligente`
  - `montar_offset_desde_layout`
- Rol:
  - generar slots IA desde trabajos logicos
  - renderizar preview
  - renderizar PDF final
  - procesar caras frente/dorso
  - aplicar export mode y datos CTP en salida

### `montaje_offset.py`

- No participa en el flujo principal del editor visual IA.
- Se usa desde la ruta legacy `/montaje_offset`.

### `montaje_offset_personalizado.py`

- No participa en el flujo principal del editor visual IA.
- Se usa desde el flujo `montaje_offset_inteligente` en modo `pro`.

### `imposicion_offset_auto.py`

- No participa en el flujo principal del editor visual IA.
- Se usa desde la ruta legacy `/imposicion_offset_auto`.

### `montaje.py`

- No participa en el flujo principal del editor visual IA.
- Resuelve otro problema: montaje de paginas por cara, no constructor visual offset por slots.

## 8. Responsabilidades duplicadas o solapadas

### Motores de imposicion coexistentes

- `routes._build_step_repeat_slots`
- `engines.nesting_pro_engine.compute_nesting`
- `montaje_offset_inteligente.realizar_montaje_inteligente`
- `imposicion_offset_auto.py`
- `montaje_offset.py`
- `montaje_offset_personalizado.py`

Hay varias formas de calcular distribucion de piezas/pliegos dentro del repo.

### Step & Repeat en dos niveles

- nivel editor: `routes._build_step_repeat_slots`
- nivel salida/render: `montaje_offset_inteligente.realizar_montaje_inteligente`

Eso exige entender bien si el slot ya viene final o si el motor vuelve a reinterpretarlo.

### CTP repartido entre frontend y backend

- frontend alinea y bloquea slots
- backend interpreta `ctp` para salida tecnica final

La semantica esta repartida entre dos capas.

### Sangrado y crop marks repartidos

- defaults en layout
- overrides por diseno
- flags por slot
- resolucion final en `montar_offset_desde_layout`

Hay varias fuentes de verdad parciales.

### Frente / dorso

- el frontend crea clones y cambia `face`
- el backend vuelve a separar por cara y fusiona PDFs

## 9. Que archivos parecen legacy

- `templates/montaje_offset.html`
- `montaje_offset.py`
- ruta `/montaje_offset`
- `templates/imposicion_offset_auto.html`
- `imposicion_offset_auto.py`
- ruta `/imposicion_offset_auto`
- `montaje.py`

`/montaje_offset_inteligente` no es exactamente legacy muerto, pero si es un flujo previo/paralelo al constructor visual IA actual y puede generar confusion de ownership.

## 10. Riesgos si se refactoriza sin delimitar primero el flujo

- romper contratos frontend-backend del editor constructor
- mezclar conceptos distintos de slot, pieza, forma y posicion manual
- duplicar o eliminar logica que en realidad se usa desde otra pantalla offset
- tocar `montaje_offset_inteligente.py` pensando solo en el editor nuevo y romper `/montaje_offset_inteligente`
- tocar `routes.py` y romper rutas legacy que usan otros motores
- unificar sangrado/crop/CTP sin definir antes la fuente de verdad
- alterar el manejo de `face=front/back` y romper dorso final
- confundir motores:
  - motor para crear slots
  - motor para imponer
  - motor para render final

## Conclusiones

El editor visual IA nuevo tiene flujo propio, pero no esta aislado en un modulo cerrado. La orquestacion vive en `routes.py`, el estado interactivo vive casi entero en `static/js/editor_offset_visual.js`, y la salida real vive en `montaje_offset_inteligente.py`.

Antes de cualquier refactor conviene congelar esta frontera y decidir explicitamente:

- que archivo es orquestador oficial del editor
- que motor calcula slots
- que motor genera salida final
- que rutas legacy quedan fuera del alcance
