# 06 CONTRATO LAYOUT

## Objetivo

Congelar el contrato tecnico real actual de `layout_constructor.json` y del pipeline de datos del editor visual IA, sin cambiar la logica.

## Fuente de verdad auditada

- persistencia: `static/constructor_offset_jobs/<job_id>/layout_constructor.json`
- frontend: `static/js/editor_offset_visual.js`
- backend: `routes.py`
- preview/PDF: `montaje_offset_inteligente.py`

## Pipeline completo de datos

1. `routes.editor_offset_visual` crea o carga `layout_constructor.json`.
2. El template entrega `layout_json` a `window.INITIAL_LAYOUT_JSON`.
3. `parseInitialLayout()` convierte eso en `state.layout`.
4. El frontend agrega defaults y normalizaciones locales:
   - `ensureEngineDefaults()`
   - `ensureCtpDefaults()`
   - `ensureExportDefaults()`
   - `normalizeDesignDefaults()`
   - `normalizeLayoutFaces()`
5. Las acciones del usuario modifican `state.layout`.
6. `layoutToJson()` vuelve a sincronizar defaults y serializa `state.layout`.
7. `POST /editor_offset/save` persiste el JSON final en disco.
8. `POST /editor_offset/preview/<job_id>` y `POST /editor_offset/generar_pdf/<job_id>` no reciben el layout en el body.
9. Preview/PDF releen el layout desde disco y lo consumen con `montar_offset_desde_layout()`.

### Capa operativa IA

La Fase 4 agrega una capa intermedia no persistente:

- `POST /ai/step_repeat_action`
- `ai_agent/agent_controller.py`
- `ai_agent/tools_repeat.py`

Esta ruta recibe un `layout_json`, ejecuta una tool y devuelve un layout sugerido. No reemplaza por si sola el layout persistido: el frontend solo actualiza `state.layout` si el usuario confirma con `Aplicar cambios`.

## Diferencia entre estados

### Estado en memoria del frontend

Incluye:

- `state.layout`
- `state.zoom`
- `state.scale`
- `state.activeFace`
- `state.selectedSlot`
- `state.selectedSlots`
- `state.selectedWork`
- `history`
- `dragState`

Solo `state.layout` es persistible.

### Estado persistido en JSON

Incluye solo el contrato serializado por `layoutToJson()`. Lo que no entra en `state.layout` no llega a disco.

### Estado consumido por preview/PDF

No es el JSON crudo tal cual. `montar_offset_desde_layout()` lo transforma a:

- `disenos`
- `works` indexados por `id`
- `front_positions`
- `back_positions`
- `MontajeConfig`

## Estructura real actual de `layout_constructor.json`

```json
{
  "sheet_mm": [640, 880],
  "margins_mm": [10, 10, 10, 10],
  "bleed_default_mm": 3,
  "gap_default_mm": 5,
  "works": [],
  "slots": [],
  "designs": [],
  "export_settings": {
    "bleed_mm": 3,
    "crop_marks": true,
    "output_mode": "raster"
  },
  "design_export": {},
  "faces": ["front"],
  "active_face": "front",
  "imposition_engine": "repeat",
  "allowed_engines": ["repeat", "nesting", "hybrid"],
  "ctp": {
    "enabled": false,
    "gripper_mm": 40,
    "lock_after": true,
    "show_guide": false,
    "marks": {
      "registro": false,
      "control_strip": false
    },
    "technical_text": {
      "job_name": "",
      "client": "",
      "notes": "",
      "auto_cmyk": true,
      "extra_text": ""
    }
  },
  "snapSettings": {
    "snapSlots": true,
    "snapMargins": true,
    "snapGrid": true,
    "tolerance_mm": 3,
    "grid_mm": 5
  },
  "spacingSettings": {
    "spacingX_mm": 4,
    "spacingY_mm": 3,
    "live": true
  }
}
```

## Bloques del contrato

### `sheet_mm`

- tipo: array de 2 numeros `[ancho_mm, alto_mm]`
- semantica:
  - tamaño del pliego en milimetros
  - usado por render del canvas y por salida final
- obligatorio de facto: si falta, frontend y backend ponen default
- default actual: `[640, 880]`

### `margins_mm`

- tipo: array de 4 numeros `[izq, der, sup, inf]`
- semantica:
  - margenes del pliego en milimetros
  - el orden real actual es izquierda, derecha, superior, inferior
- obligatorio de facto: si falta, frontend y backend ponen default
- default actual: `[10, 10, 10, 10]`
- observacion:
  - existe en contrato y en backend, pero en la UI actual no se ve un editor explicito de margenes

### `bleed_default_mm`

- tipo: numero
- semantica:
  - bleed default del layout
  - fallback para trabajos, diseños y slots
- default actual: `3`

### `gap_default_mm`

- tipo: numero
- semantica:
  - gap base del layout usado por motores de imposicion y repeticion
- default actual: `5`

### `works`

- tipo: array de objetos
- rol:
  - trabajos logicos opcionales
  - sirven para IA de slots y para derivar dimensiones por trabajo

#### estructura real observada / inferida

```json
{
  "id": "w1712870000000",
  "name": "Nuevo trabajo",
  "final_size_mm": [50, 50],
  "desired_copies": 1,
  "default_bleed_mm": 3,
  "has_bleed": false
}
```

#### campos reales

- `id`
- `name`
- `final_size_mm`
- `desired_copies`
- `default_bleed_mm`
- `has_bleed`

#### campos mencionados implícitamente por backend pero no generados claramente por UI actual

- `allow_rotation`
- `forms_per_plate`

Eso significa que el backend tolera esos campos en `related_work`, pero la UI actual de trabajos logicos no los expone ni los guarda de forma explicita.

### `designs`

- tipo: array de objetos
- rol:
  - PDFs subidos y su metadata de imposicion

#### estructura real observada

```json
{
  "ref": "file0",
  "filename": "archivo.pdf",
  "work_id": null,
  "width_mm": 210,
  "height_mm": 297,
  "bleed_mm": 3,
  "allow_rotation": false,
  "forms_per_plate": 4
}
```

#### semantica

- `ref`: identificador estable del diseño dentro del layout
- `filename`: nombre del PDF guardado en el job
- `work_id`: referencia opcional a `works[].id`
- `width_mm` / `height_mm`: tamaño de referencia del diseño
- `bleed_mm`: bleed asociado al diseño
- `allow_rotation`: habilita rotacion para motores auto
- `forms_per_plate`: cantidad declarada de formas por pliego

### `slots`

- tipo: array de objetos
- rol:
  - piezas concretas posicionadas en el pliego
  - es el bloque mas critico para preview/PDF

#### estructura real observada

```json
{
  "id": "sr_0",
  "x_mm": 102,
  "y_mm": 40,
  "w_mm": 216,
  "h_mm": 303,
  "rotation_deg": 0,
  "logical_work_id": null,
  "bleed_mm": 3,
  "crop_marks": true,
  "locked": true,
  "design_ref": "file0",
  "face": "front",
  "group_id": "g1712870000000_123"
}
```

#### semantica

- `id`: identificador estable del slot
- `x_mm`: coordenada horizontal en mm
- `y_mm`: coordenada vertical en mm
- `w_mm`: ancho del slot; en `repeat` representa footprint final
- `h_mm`: alto del slot; en `repeat` representa footprint final
- `rotation_deg`: orientacion del contenido del diseno
- `logical_work_id`: referencia opcional a `works[].id`
- `bleed_mm`: bleed local del slot
- `crop_marks`: marcas de corte locales
- `locked`: bloqueado o editable
- `design_ref`: referencia a `designs[].ref`
- `face`: `"front"` o `"back"`
- `group_id`: agrupacion para mover varios slots juntos

### `faces`

- tipo: array de strings
- semantica:
  - lista de caras disponibles
- valores reales observados:
  - `["front"]`
  - `["front", "back"]`

### `active_face`

- tipo: string
- semantica:
  - cara activa en el editor al persistir
- observacion:
  - tambien existe `state.activeFace` en memoria

### `imposition_engine`

- tipo: string
- valores reales:
  - `repeat`
  - `nesting`
  - `hybrid`

### `allowed_engines`

- tipo: array de strings
- valor default:
  - `["repeat", "nesting", "hybrid"]`

### `export_settings`

- tipo: objeto

```json
{
  "bleed_mm": 3,
  "crop_marks": true,
  "output_mode": "raster"
}
```

#### semantica

- define defaults globales de salida
- orden de prioridad real en backend:
  - primero global
  - luego override por diseño
  - luego slot
  - luego work/defaults segun el caso

### `design_export`

- tipo: mapa por `design_ref`

```json
{
  "file0": {
    "bleed_mm": 1,
    "crop_marks": false
  }
}
```

- semantica:
  - overrides de salida por diseño

### `ctp`

- tipo: objeto

```json
{
  "enabled": true,
  "gripper_mm": 40,
  "lock_after": true,
  "show_guide": true,
  "marks": {
    "registro": true,
    "control_strip": true
  },
  "technical_text": {
    "job_name": "",
    "client": "",
    "notes": "",
    "auto_cmyk": true,
    "extra_text": ""
  }
}
```

- semantica:
  - mezcla configuracion de UI, alineacion y salida tecnica final

### `snapSettings`

- tipo: objeto
- semantica:
  - UX del editor
- no impacta preview/PDF

### `spacingSettings`

- tipo: objeto
- semantica:
  - UX y ayudas de reacomodo
  - fuente real de separacion para Step & Repeat PRO
- campos:
  - `spacingX_mm`
  - `spacingY_mm`
  - `live`
- observacion:
  - `spacingSettings.spacingX_mm` y `spacingSettings.spacingY_mm` impactan la generacion de slots `repeat`
  - no impactan preview/PDF por si mismos; impactan la salida final a traves de los slots ya generados

## Clasificacion de campos

### Obligatorios de facto

- `sheet_mm`
- `margins_mm`
- `bleed_default_mm`
- `works`
- `designs`
- `slots`
- `faces`
- `active_face`
- `imposition_engine`
- `allowed_engines`
- `export_settings`
- `design_export`

### Opcionales pero soportados

- `ctp`
- `snapSettings`
- `spacingSettings`
- `slots[].group_id`
- `slots[].logical_work_id`
- `slots[].design_ref`
- `designs[].work_id`

### Derivados / normalizados

- `designs[].bleed_mm` si falta se rellena desde `bleed_default_mm`
- `designs[].allow_rotation` si falta se normaliza a `true`
- `designs[].forms_per_plate` si falta se normaliza a `1`
- `slots[].face` si falta se normaliza a `"front"`
- `faces` si falta se normaliza a `["front"]`
- `active_face` si falta se normaliza a la primera cara
- `export_settings.*` si faltan se completan
- `ctp.*` si faltan se completan en frontend

### Legacy / tolerados

- `snap_settings`
- `spacing_settings`
- `w_mm` / `h_mm` dentro de `designs` como alias de `width_mm` / `height_mm`
- `rot_deg` / `rot` como alias tolerados por backend al consumir preview/PDF
- `x` / `y` como alias tolerados en algunos puntos del backend

## Representacion exacta de campos clave

### `rotation_deg`

- en frontend:
  - vive en `slots[].rotation_deg`
  - se usa para render visual
- en backend:
  - se lee como `slot.rotation_deg`, con fallback a `rot_deg`
  - se transforma a `rot_deg` en el pipeline interno de preview/PDF
- semantica:
  - grados, normalmente `0`, `90`, `180`, `270`
  - el frontend acepta cualquier numero

### `group_id`

- existe solo en slots
- lo usa el frontend para mover grupos
- backend preview/PDF no lo usa
- sigue siendo parte del contrato persistido

### `forms_per_plate`

- vive en `designs[]`
- se edita en la UI de diseños
- motores repeat lo usan para generar cantidad de slots
- backend garantiza default `1`

### `allow_rotation`

- vive en `designs[]`
- se edita en la UI de diseños
- motores auto lo usan para rotar o no rotar
- backend garantiza default `true`

## Tabla de campos importantes

| Campo | Dónde se escribe | Dónde se lee | Impacto si cambia |
|---|---|---|---|
| `sheet_mm` | frontend `parseInitialLayout`, inputs de pliego, backend default | render canvas, auto layout, impose, preview/PDF | cambia escala, cálculo utilizable y salida final |
| `margins_mm` | backend default, persistencia previa | snap, auto layout, repeat, step repeat, preview/PDF | rompe área útil y posicionamiento |
| `bleed_default_mm` | backend default, frontend normalización | works, designs, slots, preview/PDF | altera medidas, crop y bleed final |
| `gap_default_mm` | backend default | auto layout, repeat/hybrid, config de montaje | altera separaciones y cantidad de slots |
| `works[]` | frontend `newWork/saveWork` | auto layout, upload, preview/PDF vía `logical_work_id` | rompe IA de slots y bleed por trabajo |
| `designs[]` | backend upload, frontend edición | impose, slot form, preview/PDF | sin esto no hay asignación de PDFs |
| `designs[].ref` | backend upload | slot `design_ref`, preview/PDF | si cambia se cortan enlaces slot->PDF |
| `designs[].width_mm` | backend upload, frontend edición | repeat/nesting | cambia tamaño impuesto |
| `designs[].height_mm` | backend upload, frontend edición | repeat/nesting | cambia tamaño impuesto |
| `designs[].bleed_mm` | backend upload/defaults, frontend edición | `_design_dimensions`, preview/PDF fallbacks | cambia caja final y trim |
| `designs[].forms_per_plate` | backend upload/defaults, frontend edición | repeat | cambia cantidad de slots generados |
| `designs[].allow_rotation` | backend upload/defaults, frontend edición | repeat/nesting | cambia aprovechamiento del pliego |
| `slots[]` | frontend edición, auto layout, impose | render visual, preview/PDF | es el bloque más crítico del sistema |
| `slots[].x_mm` | frontend drag/form, auto engines | render visual, preview/PDF | mueve pieza real |
| `slots[].y_mm` | frontend drag/form, auto engines | render visual, preview/PDF | mueve pieza real |
| `slots[].w_mm` | frontend form, auto engines | render visual, preview/PDF | en `repeat` representa footprint final del slot |
| `slots[].h_mm` | frontend form, auto engines | render visual, preview/PDF | en `repeat` representa footprint final del slot |
| `slots[].rotation_deg` | frontend form/engines | render visual, preview/PDF | desalineación inmediata si cambia semántica |
| `slots[].design_ref` | frontend slot form/asignación, engines | preview/PDF | si falta no se renderiza ese slot |
| `slots[].logical_work_id` | frontend slot form, auto layout | preview/PDF bleed/has_bleed | altera trim y bleed efectivos |
| `slots[].face` | frontend normalize/duplicate face/engines | render visual, preview/PDF | decide frente vs dorso |
| `slots[].group_id` | frontend grouping | frontend spacing/drag | impacto UX, no salida final |
| `faces` | frontend normalize/setActiveFace/duplicate face, backend defaults | toggle UI, preview/PDF split | rompe navegación y separación por cara |
| `active_face` | frontend `setActiveFace`, backend defaults | UI inicial, engines | puede desincronizar cara visible |
| `export_settings` | frontend export panel, backend defaults | preview/PDF | cambia bleed/crop/output mode globales |
| `design_export` | frontend export panel | preview/PDF | cambia bleed/crop por diseño |
| `ctp` | frontend CTP panel | guide overlay, preview/PDF final | afecta pinza, bloqueo y marcas técnicas |
| `snapSettings` | frontend snap panel | frontend snap | impacto UX, no salida final |
| `spacingSettings` | frontend spacing panel | frontend spacing/live spacing, repeat | impacta separacion de slots al generar `repeat` |

## Qué parte del frontend escribe o modifica cada bloque

### `sheet_mm`

- inputs `sheet-w`, `sheet-h`
- preset `sheet-preset`

### `margins_mm`

- no se detecta editor visual explicito en la UI actual
- hoy se hereda del JSON/default backend

### `works`

- `newWork()`
- `saveWork()`
- `deleteWork()`

### `designs`

- `uploadDesigns()` reemplaza `state.layout.designs` con respuesta backend
- `renderDesigns()` modifica:
  - `forms_per_plate`
  - `width_mm`
  - `height_mm`
  - `bleed_mm`
  - `allow_rotation`

### `slots`

- `addSlot()`
- `duplicateSlot()`
- `deleteSlot()`
- `groupSelectedSlots()`
- `ungroupSelectedSlots()`
- drag / resize
- `applySlotForm()`
- `applyDesignToSelected()`
- `generateStepRepeatFromSelectedSlot()`
- `duplicateFrontToBack()`
- `applyCtpAlignment()`
- `disableCtpAdjustments()`
- `applyGapToSlots()`
- `applySpacing()`

### `faces` y `active_face`

- `normalizeLayoutFaces()`
- `setActiveFace()`
- `duplicateFrontToBack()`

### `export_settings` y `design_export`

- `ensureExportDefaults()`
- `applyGlobalExportSettings()`
- `updateDesignOverride()`
- `clearDesignOverride()`

### `ctp`

- `ensureCtpDefaults()`
- `readCtpParamsFromUI()`
- `applyCtpAlignment()`
- `disableCtpAdjustments()`

### `snapSettings` y `spacingSettings`

- `parseInitialLayout()`
- `syncSettingsToLayout()`
- `updateSnapSettingsFromUI()`
- `updateSpacingSettingsFromUI()`
- `toggleLiveSpacing()`

### Capa `ai_agent/`

- `POST /ai/step_repeat_action` lee un layout enviado por el frontend
- `handle_agent_request()` decide una tool por prompt simple
- las tools pueden devolver un layout sugerido
- el layout sugerido no se guarda automaticamente
- el contrato base de `layout_constructor.json` no cambia por integrar IA

## Qué endpoints backend leen o escriben cada bloque

| Bloque | Escrito por backend | Leído por backend |
|---|---|---|
| layout completo | `GET /editor_offset_visual` crea default si no existe | `GET /editor_offset_visual`, preview, PDF, apply_imposition, auto_layout |
| `works` | `POST /editor_offset/save` persiste lo que manda frontend | `POST /editor_offset/auto_layout/<job_id>`, `POST /editor_offset/upload/<job_id>`, preview/PDF |
| `designs` | `POST /editor_offset/upload/<job_id>` escribe metadata real | apply_imposition, preview/PDF |
| `slots` | `POST /editor_offset/save`, `POST /editor_offset/auto_layout/<job_id>`, `POST /editor_offset_visual/apply_imposition` | preview/PDF |
| `faces` / `active_face` | `save`, `auto_layout`, `apply_imposition`, normalización en carga | apply_imposition, preview/PDF |
| `export_settings` / `design_export` | `save` | preview/PDF |
| `ctp` | `save` | preview/PDF |
| `snapSettings` | `save` | solo roundtrip y restauracion UI |
| `spacingSettings` | `save` | restauracion UI y generacion `repeat` |

## Qué funciones Python consumen el layout para preview/PDF

### Entrada

- `routes.editor_offset_preview`
- `routes.editor_offset_generar_pdf`

### Orquestacion

- `montaje_offset_inteligente.montar_offset_desde_layout`

### Consumos clave internos

- `_sanitize_slot_bleed()`
- `_resolve_slot_crop_marks()`
- `realizar_montaje_inteligente()`

## Supuestos implícitos frontend-backend

1. `designs[].ref` es estable y unico.
2. `slots[].design_ref` apunta a un `designs[].ref` existente.
3. `slots[].logical_work_id` apunta a `works[].id` o puede ser `null`.
4. `sheet_mm` siempre trae dos numeros.
5. `margins_mm` siempre trae cuatro numeros en orden fijo.
6. `slots[].x_mm` y `y_mm` usan origen bottom-left.
7. `rotation_deg` y `rot_deg` representan la misma idea.
8. `repeat` usa `w_mm/h_mm` como caja final del slot.
   - En `repeat`, `rotation_deg` representa orientacion del contenido y no debe reinterpretar la caja externa.
9. `nesting/hybrid` no siguen exactamente la misma semantica de caja final.
10. `export_settings.crop_marks` global pisa overrides por diseño y slot.
11. `saveLayout()` ocurre antes de preview/PDF.
12. `faces` contiene la cara activa y todos los slots tienen `face`.

## Diferencias entre memoria, JSON y preview/PDF

### Memoria del frontend

- usa `state.activeFace` ademas de `layout.active_face`
- conserva seleccion, historial y drag
- puede tener cambios no persistidos todavia

### JSON persistido

- solo guarda `layout`
- congela defaults y settings al momento de `layoutToJson()`

### Preview/PDF

- vuelve a resolver bleed efectivo
- vuelve a resolver crop marks efectivos
- filtra slots por cara
- traduce `rotation_deg` a `rot_deg`
- decide si `w_mm/h_mm` son trim o caja final segun engine
  - en `repeat`, debe respetarlos como caja final/footprint

## Partes frágiles del contrato

### `design_ref` / `ref`

Es una unión blanda por string. Si cambia naming o unicidad, los slots dejan de dibujar PDF.

### `rotation_deg`

La UI y el backend comparten nombre/semantica, pero no hay validación estricta.

### `w_mm` / `h_mm`

Su interpretación cambia según engine y bleed. Es uno de los puntos más sensibles del contrato.

En Fase 4 quedo consolidada la regla para `repeat`:

- `slot.w_mm / slot.h_mm` = footprint final del slot en el pliego
- `rotation_deg` = orientacion del contenido
- el frontend no debe rotar otra vez la caja externa
- el PDF debe ubicar el contenido dentro de esa caja final

### `face`

Si falta o no coincide con `faces`, puede desaparecer salida de frente/dorso.

### `export_settings.crop_marks`

El backend hoy le da prioridad fuerte. Puede apagar marcas por completo aunque el slot diga otra cosa.

### `ctp.enabled` + `gripper_mm`

Afecta directamente el margen inferior real del pliego final.

## Validaciones faltantes hoy

- schema de `layout_constructor.json`
- tipos numéricos estrictos
- unicidad de `slots[].id`
- unicidad de `designs[].ref`
- referencias cruzadas `design_ref` y `logical_work_id`
- validación de caras
- validación de arrays de tamaño fijo
- validación de `output_mode`
- validación de `rotation_deg`
- validación de coordenadas negativas o fuera de pliego

## Campos recomendados como congelados por compatibilidad

### Bloques congelados

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

### Claves internas congeladas

- `works[].id`
- `works[].final_size_mm`
- `works[].desired_copies`
- `works[].default_bleed_mm`
- `works[].has_bleed`
- `designs[].ref`
- `designs[].filename`
- `designs[].work_id`
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
- `slots[].logical_work_id`
- `slots[].bleed_mm`
- `slots[].crop_marks`
- `slots[].locked`
- `slots[].design_ref`
- `slots[].face`

## Conclusión operativa

El contrato real del editor visual IA no es solo un JSON de layout: es un acuerdo implícito entre:

- normalizaciones del frontend
- helpers de persistencia en `routes.py`
- reinterpretación de salida en `montaje_offset_inteligente.py`

Por compatibilidad, el layout debe tratarse como contrato congelado hasta que exista:

- schema formal
- validadores de referencias cruzadas
- decisión explícita sobre semántica de `w_mm/h_mm`, `rotation_deg`, `bleed` y `face`
