# Contratos Editor Offset Visual

Fuente principal: `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`.

Este documento describe contratos y estructuras de datos del Editor Offset Visual. Debe consultarse antes de cambiar frontend, backend, motores, persistencia o salida PDF.

## Ubicacion principal

### Hechos confirmados

La persistencia principal del Editor Offset Visual vive en:

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

La gestion de rutas, carga y guardado vive en:

- `services/editor_offset_jobs.py`

`safe_job_id()` acepta solo tokens alfanumericos para `job_id`.

## Campos principales del layout

### Hechos confirmados

Campos principales observados:

- `sheet_mm`
- `margins_mm`
- `bleed_default_mm`
- `gap_default_mm`
- `works`
- `designs`
- `slots`
- `export_settings`
- `design_export`
- `faces`
- `active_face`
- `imposition_engine`
- `allowed_engines`
- `spacingSettings`
- `snapSettings`
- `ctp`

Defaults y normalizacion:

- `services/editor_offset_layout_defaults.py`

## Contrato designs[]

### Hechos confirmados

Campos relevantes:

- `ref`
- `filename`
- `work_id`
- `width_mm`
- `height_mm`
- `bleed_mm`
- `allow_rotation`
- `forms_per_plate`
- `priority`
- `preferred_zone`
- `preferred_flow`
- `repeat_role`
- `repeat_manual_overrides`

Uso conocido:

- `ref` enlaza con `slots[].design_ref`.
- `filename` se resuelve dentro del job para construir PDFs de salida.
- `forms_per_plate` define formas solicitadas para imposicion.
- `preferred_zone`, `preferred_flow`, `repeat_role` y `priority` alimentan Step & Repeat PRO.

### Requiere verificacion

- Si `width_mm` y `height_mm` representan trim, media box del PDF o caja final con bleed.
- Como deben migrarse layouts historicos con semantica distinta.

## Contrato slots[]

### Hechos confirmados

Campos relevantes:

- `id`
- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`
- `rotation_deg`
- `logical_work_id`
- `bleed_mm`
- `crop_marks`
- `locked`
- `design_ref`
- `face`
- `slot_box_final`

Uso conocido:

- `id` identifica el slot para seleccion y validacion.
- `x_mm`, `y_mm`, `w_mm`, `h_mm` definen caja en milimetros.
- `rotation_deg` define rotacion del contenido y sigue siendo el campo canonico de rotacion por slot.
- `design_ref` debe resolver contra `designs[].ref`.
- `face` separa frente/dorso.
- `slot_box_final` protege semantica de Step & Repeat en salida.

### Nota de rotacion frontend

Hechos confirmados:

- No se cambio el contrato JSON de `slots[]`.
- `slots[].rotation_deg` sigue siendo numerico y canonicamente persistido por slot.
- La UI puede editar `rotation_deg` de un slot individual mediante `#slot-rot`.
- La UI puede editar `rotation_deg` de una seleccion mediante `#selection-rotation-deg`, `#btn-apply-selection-rotation`, `static/js/editor_offset_visual/manual_tools.js` / `rotateSelectedSlots()` y el wrapper homonimo en `static/js/editor_offset_visual.js`.
- La validacion geometrica frontend usa huella rotada cardinal para `OUT_OF_SHEET`, `OUT_OF_USABLE_AREA`, `OVERLAP` y `GRIPPER` mediante `static/js/editor_offset_visual/core/geometry_validation.js` / `validationBoxForSlot()`.
- La huella cardinal depende de `static/js/editor_offset_visual/core/geometry.js` / `getCardinalRotatedSlotFootprint()` y aplica solo a rotaciones 0/90/180/270; otros angulos caen a caja simple en validacion frontend.
- Backend, output, PDF, motores, bleed y CTP productivo no cambiaron durante las fases frontend/geometria. La salida PDF recibio despues una correccion especifica para slots rotados manualmente, sin cambiar el contrato JSON.

Inferencia operativa: la validacion visual/frontend puede no ser equivalente al PDF final. La salida PDF tiene una correccion acotada para preservar aspect ratio en slots rotados manualmente, pero no adopta toda la geometria frontend.

### Nota de salida PDF para rotacion

Hechos confirmados:

- No se cambio el contrato JSON de `slots[]`.
- `slots[].rotation_deg` sigue siendo el campo canonico de rotacion persistido por slot.
- `slot_box_final` explicito en el slot tiene prioridad para la salida.
- Si `slot_box_final` no viene explicito, `services/editor_offset_output_service.py` puede inferir la semantica segun el caso:
  - repeat automatico rotado con `w_mm`/`h_mm` ya intercambiados conserva semantica de footprint final;
  - rotacion manual UI con `w_mm`/`h_mm` base se trata como rotacion manual para evitar deformar la fuente.
- `source_w_mm` y `source_h_mm` pueden viajar internamente en `posiciones_manual` hacia `montaje_offset_inteligente.py` para preservar el aspect ratio del PDF fuente.
- `source_w_mm` y `source_h_mm` no son nuevos campos requeridos de `layout_constructor.json`.
- Un slot rotado manualmente, por ejemplo con `rotation_deg=90`, debe rotar en PDF sin invertir ni estirar la proporcion del PDF fuente.

Inferencia operativa: si un layout historico no trae `slot_box_final`, la salida usa dimensiones de `designs[]` y bleed efectivo para distinguir entre repeat automatico y rotacion manual UI.

## Contrato de faces

### Hechos confirmados

Valores conocidos:

- `front`
- `back`

`services/editor_offset_output_contract.py` valida que `slot.face` sea `front` o `back`. Si `faces` declara `back` pero no hay slots `back`, se genera warning.

## Contrato CTP

### Hechos confirmados

Campos y parametros confirmados por auditoria:

- `ctp.enabled`
- `ctp.gripper_mm`
- `ctp.lock_after`
- `ctp.show_guide`
- `ctp.marks.registro`
- `ctp.marks.control_strip`
- `ctp.technical_text`

Relacion frontend/backend:

- UI y acciones: `static/js/editor_offset_visual/ctp_panel.js`.
- Validacion geometrica: `static/js/editor_offset_visual/core/geometry_validation.js`.
- Salida: `services/editor_offset_output_service.py` pasa `ctp_config` a la capa legacy.

### Limitaciones conocidas

Preview no necesariamente representa de forma fiel todo el PDF final CTP. La salida final puede incluir frente/dorso, marcas, strip o texto tecnico que la preview no cubre completamente.

## Reglas de coordenadas

### Hechos confirmados

- Unidades principales: milimetros.
- El frontend renderiza `x_mm/y_mm` con CSS `left`/`bottom`.
- La validacion frontend usa margen inferior como `usableBottom`.
- La salida transforma `slots[]` a `posiciones_manual` en `services/editor_offset_output_service.py`.

### Inferencias

La semantica operativa es origen inferior izquierdo, alineada entre canvas y backend. Cualquier cambio de origen afectaria canvas, JSON y PDF.

## Reglas de validacion conocidas

### Hechos confirmados desde services/editor_offset_output_contract.py

La validacion de salida revisa:

- layout debe ser objeto JSON valido
- `designs[].ref` requerido
- `designs[].ref` unico
- cada slot debe ser objeto JSON valido
- `slots[].id` requerido
- `slots[].id` unico
- `slot.face` debe ser `front` o `back`
- `x_mm` requerido y numerico finito
- `y_mm` requerido y numerico finito
- `w_mm` requerido, numerico finito y mayor que cero
- `h_mm` requerido, numerico finito y mayor que cero
- `bleed_mm` requerido y numerico finito
- `rotation_deg` requerido y numerico finito
- `slot.design_ref` debe resolver contra `designs[].ref`
- `logical_work_id` no resuelto produce warning
- `faces` contiene `back` sin slots `back` produce warning

### Validacion geometrica frontend

Hechos confirmados desde `static/js/editor_offset_visual/core/geometry_validation.js`:

- `OUT_OF_SHEET` usa huella rotada cardinal cuando `rotation_deg` es 0/90/180/270.
- `OUT_OF_USABLE_AREA` usa huella rotada cardinal cuando `rotation_deg` es 0/90/180/270.
- `OVERLAP` usa huella rotada cardinal cuando `rotation_deg` es 0/90/180/270.
- `GRIPPER` frontend usa huella rotada cardinal cuando `rotation_deg` es 0/90/180/270.
- Si la rotacion no es cardinal, `validationBoxForSlot()` vuelve a `geometry.getSimpleSlotBox(slot)`.

Limitacion confirmada: esta validacion es frontend. No define por si sola el contrato de `services/editor_offset_output_contract.py`, motores ni generacion PDF.

### Limitacion confirmada

El contrato valida `design_ref`, pero no confirma existencia fisica del archivo `design.filename`.

## Ambiguedades

### Requiere verificacion

- Si `design.width_mm/height_mm` representa trim, media box o caja final con bleed.
- Posible doble conteo de bleed cuando `work.has_bleed` es falso.
- Precedencia completa entre:
  - `slot.export_overrides`
  - `design_export`
  - `export_settings`
- Existencia fisica de archivos PDF referenciados.
- Alcance contractual de `vector_hybrid`.
- Compatibilidad esperada con layouts historicos.

## Contratos de endpoints

### Hechos confirmados

Endpoints principales:

- `GET /editor_offset_visual`
- `POST /editor_offset/save`
- `POST /editor_offset/upload/<job_id>`
- `POST /editor_offset_visual/apply_imposition`
- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`
- `POST /editor_offset/cuadernillos/simular`
- `POST /ai/step_repeat_action_openai`

Payloads principales:

- Save: `FormData` con `job_id`, `layout_json`.
- Upload: `files[]` y opcional `work_id`.
- Apply imposition: `FormData` con `job_id`, `selected_engine`, `layout_json`.
- Preview/PDF: usan layout persistido.
- Cuadernillos: JSON del simulador.
- IA: `prompt` y `layout_json`.

## Preguntas abiertas

- Debe bloquearse salida si falta `design.filename` en disco?
- Debe normalizarse la semantica de dimensiones antes de tocar bleed?
- Debe `slot_box_final` ser obligatorio para slots generados por `repeat`?
- Debe versionarse el contrato de `layout_constructor.json`?
- Debe documentarse `vector_hybrid` como experimental hasta validacion?

## Inferencias

El contrato actual es suficiente para bloquear errores estructurales basicos, pero todavia deja fuera validaciones productivas importantes: archivo fisico, fidelidad preview/PDF, precedencia de export y semantica exacta de bleed.
