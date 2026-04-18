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

## Riesgos de contrato y compatibilidad

### Persistencia parcial vs estado real del editor

- preview y PDF final no leen el estado vivo del navegador
- leen el JSON persistido desde disco
- si un cambio modifica `state.layout` pero no pasa por `layoutToJson()` y `saveLayout()`, la salida final puede no reflejar la UI

### Doble semantica de rotacion

- el frontend renderiza `rotation_deg` manteniendo centro visual
- el backend vuelve a reconstruir posiciones usando `rot_deg`, `w_mm`, `h_mm` y `slot_box_final`
- cambios pequeños en esa semantica pueden romper alineacion visual vs PDF

### Orden de prioridad bleed/crop

- `export_settings`
- `design_export`
- `slot.bleed_mm` / `slot.crop_marks`
- `work.default_bleed_mm`
- `bleed_default_mm`

Ese orden existe hoy de forma implicita en Python. Si cambia sin documentarse puede romper preview/PDF sin que la UI lo haga evidente.

### `repeat` vs `nesting/hybrid`

- para `repeat`, el backend marca `slot_box_final=True`
- eso cambia como se interpretan `w_mm` y `h_mm`
- si se unifica mal este criterio, los slots pueden salir con tamaño o bleed incorrectos

### Cara activa y caras persistidas

- `state.activeFace` y `layout.active_face` deben mantenerse consistentes
- `slots[].face` es la verdad final para render
- si alguno se rompe, el usuario puede ver una cara y generar otra

### Datos auxiliares guardados en el mismo layout

- `snapSettings`
- `spacingSettings`

No afectan preview/PDF, pero hoy viajan dentro del mismo contrato persistido. Refactors que “limpien” esos campos pueden romper continuidad de UX e historial de jobs.

### Pipeline `slots -> preview/PDF`

- un slot sin `design_ref` válido se omite silenciosamente
- un `logical_work_id` inválido no rompe, pero cambia bleed/trim implícitos
- `face` faltante manda el slot a frente
- `repeat` y `nesting/hybrid` no comparten la misma semántica de `w_mm/h_mm`
- `rotation_deg` se traduce a `rot_deg` y se vuelve a reinterpretar al dibujar
- `locked` y `group_id` se guardan, pero no protegen ni modifican la salida final
- `export_settings.crop_marks` global puede pisar la intención local del slot
- `export_settings.bleed_mm` global puede pisar el bleed declarado en el slot
- la vista del editor y el PDF solo coinciden si el contrato de slot y la lectura por engine siguen alineados

## Riesgos específicos del pipeline slots -> preview/PDF

### Omisión silenciosa de slots

- si `slot.design_ref` no resuelve contra `designs[].ref`, el slot desaparece de la salida
- hoy no hay error explícito ni warning de contrato

### Interpretación variable de `w_mm/h_mm`

- en `repeat` el backend los trata como caja final
- en `nesting/hybrid` los reduce restando bleed layout
- en manual puro la intención del usuario queda subordinada al engine activo

### Prioridad bleed/crop poco obvia

- el slot no tiene la última palabra
- preview/PDF aplican una jerarquía que puede sobreescribir `slot.bleed_mm` y `slot.crop_marks`

### Frente/dorso dependiente de `slot.face`

- `faces[]` y `active_face` no bastan para garantizar dorso real
- el corte efectivo entre frente y dorso se hace slot por slot

### Campos persistidos pero no efectivos

- `id`, `locked`, `group_id` son relevantes para edición, no para render
- un usuario puede asumir que “bloqueado” congela salida, pero hoy solo congela la UI

## Validaciones faltantes detectadas

- no se valida longitud exacta de `sheet_mm`
- no se valida longitud exacta de `margins_mm`
- no se valida schema de `works[]`, `designs[]` ni `slots[]`
- no se validan rangos de `rotation_deg`
- no se valida unicidad de `slots[].id`
- no se valida unicidad de `designs[].ref`
- no se valida que `slot.design_ref` exista realmente en `designs[]`
- no se valida que `slot.logical_work_id` exista realmente en `works[]`
- no se valida consistencia entre `faces`, `active_face` y `slots[].face`
- no se valida que `group_id` agrupe slots de la misma cara
- no se valida que `forms_per_plate` y dimensiones sean enteros/positivos de forma estricta en backend
- no se valida que `output_mode` pertenezca al set permitido al generar preview/PDF

## Validación mínima implementada en salida

Se agregó una validación previa a preview/PDF en `routes.py` mediante `_validate_constructor_output_layout(layout)`.

### Bloquean preview/PDF

- `designs[].ref` duplicado o faltante
- `slots[].id` duplicado o faltante
- `slots[].design_ref` inexistente
- `slot.face` inválido
- `x_mm`, `y_mm`, `w_mm`, `h_mm`, `bleed_mm`, `rotation_deg` ausentes o no numéricos
- `w_mm <= 0`
- `h_mm <= 0`

### Quedan como warning

- `logical_work_id` no resuelto contra `works[].id`
- `faces[]` declara `back` sin slots `face="back"`

### Efecto operativo

- preview/PDF ya no omiten silenciosamente slots rotos por `design_ref` inválido
- la salida devuelve JSON estructurado con `errors[]` y `warnings[]`
- el frontend del editor ahora informa esos problemas al usuario

## Validación geométrica visual en editor

Se agregó además una validación liviana en frontend documentada en `09_VALIDACION_GEOMETRICA.md`.

### Detecta

- slots fuera del pliego total
- slots fuera del área útil
- slots invadiendo pinza CTP
- overlap simple entre slots

### No bloquea

- edición
- preview
- PDF final

### Rol

Es una capa de ayuda visual temprana. No reemplaza la validación backend de contrato ni redefine la geometría real de salida.

## Campos que conviene tratar como congelados por compatibilidad

- `sheet_mm`
- `margins_mm`
- `bleed_default_mm`
- `gap_default_mm`
- `works`
- `designs`
- `slots`
- `faces`
- `active_face`
- `imposition_engine`
- `allowed_engines`
- `export_settings`
- `design_export`
- `ctp`
- `snapSettings`
- `spacingSettings`

Dentro de esos bloques, especialmente sensibles:

- `designs[].ref`
- `designs[].filename`
- `designs[].width_mm`
- `designs[].height_mm`
- `designs[].bleed_mm`
- `designs[].forms_per_plate`
- `designs[].allow_rotation`
- `slots[].id`
- `slots[].x_mm`
- `slots[].y_mm`
- `slots[].w_mm`
- `slots[].h_mm`
- `slots[].rotation_deg`
- `slots[].design_ref`
- `slots[].logical_work_id`
- `slots[].bleed_mm`
- `slots[].crop_marks`
- `slots[].locked`
- `slots[].face`

## Conclusiones

El editor visual IA nuevo tiene flujo propio, pero no esta aislado en un modulo cerrado. La orquestacion vive en `routes.py`, el estado interactivo vive casi entero en `static/js/editor_offset_visual.js`, y la salida real vive en `montaje_offset_inteligente.py`.

Antes de cualquier refactor conviene congelar esta frontera y decidir explicitamente:

- que archivo es orquestador oficial del editor
- que motor calcula slots
- que motor genera salida final
- que rutas legacy quedan fuera del alcance
