# 07 CONTRATO SLOTS

## Objetivo

Congelar el subcontrato más sensible del editor visual IA: cómo cada elemento de `slots[]` persistido en `layout_constructor.json` se transforma en las estructuras internas usadas por preview y PDF final.

## Fuente auditada

- persistencia: `layout_constructor.json`
- orquestación de lectura: `montaje_offset_inteligente.montar_offset_desde_layout()`
- normalización manual final: rama `estrategia == "manual"` dentro de `montaje_offset_inteligente.realizar_montaje_inteligente()`
- generación previa de slots automáticos:
  - `routes._build_step_repeat_slots()`
  - `routes._slots_from_nesting_result()`
  - `routes._repeat_pattern_over_sheet()`
  - frontend manual en `static/js/editor_offset_visual.js`

## Resumen del pipeline `slots[] -> preview/PDF`

1. El layout persistido contiene `slots[]`.
2. `montar_offset_desde_layout()` recorre todos los slots.
3. Filtra por `face` y arma dos listas:
   - `front_positions`
   - `back_positions`
4. Cada slot válido:
   - resuelve `design_ref -> designs[].ref -> file_idx`
   - resuelve `logical_work_id -> works[].id`
   - calcula `bleed_mm` efectivo
   - calcula `crop_marks` efectivo
   - decide si `w_mm/h_mm` representan trim o caja final según `imposition_engine`
   - traduce `rotation_deg` a `rot_deg`
5. Esas listas entran en `MontajeConfig.posiciones_manual`.
6. `realizar_montaje_inteligente()` vuelve a normalizar cada posición manual.
7. El render final dibuja el PDF/preview respetando:
   - `x_mm`, `y_mm`
   - `rot_deg`
   - `bleed_mm`
   - `crop_marks`
   - `slot_box_final`

## 1. Cómo `montar_offset_desde_layout()` recorre y transforma `slots[]`

El trabajo real ocurre en la función interna `_positions_for_face(target_face)`.

### Flujo exacto

Por cada `slot` de `layout_data["slots"]`:

1. Lee `slot.face`; si no existe usa `"front"`.
2. Convierte la cara a minúsculas.
3. Descarta el slot si no coincide con `target_face`.
4. Lee `slot.design_ref`.
5. Descarta el slot si:
   - `design_ref` no existe
   - o no está en `ref_to_idx`
6. Busca `work = works.get(slot.logical_work_id)`.
7. Calcula `bleed_val = _sanitize_slot_bleed(...)`.
8. Lee `w_mm` y `h_mm`.
9. Evalúa `has_bleed` del work si existe.
10. Decide `trim_w` / `trim_h` en función de:
   - `has_bleed`
   - `imposition_engine`
11. Calcula `crop_flag = _resolve_slot_crop_marks(...)`.
12. Agrega una posición normalizada con:
   - `file_idx`
   - `x_mm`
   - `y_mm`
   - `w_mm`
   - `h_mm`
   - `rot_deg`
   - `bleed_mm`
   - `crop_marks`
   - `slot_box_final`

## 2. Cómo separa y construye `front_positions` y `back_positions`

La separación no usa `faces[]` como fuente de verdad principal, sino `slots[].face`.

### Construcción

- `front_positions, front_crop = _positions_for_face("front")`
- `back_positions, back_crop = _positions_for_face("back")`

### Regla real

- si `slot.face` falta, se asume `"front"`
- solo entran a `back_positions` los slots con `face == "back"`
- `faces[]` y `active_face` no deciden la salida final por sí solos

### Consecuencia

Un layout puede tener:

- `faces = ["front", "back"]`
- `active_face = "back"`

y aun así no producir dorso si ningún slot persistido tiene `face = "back"`.

## 3. Qué campos exactos consume del slot

### `id`

- no se consume en preview/PDF
- sirve para UI y selección

### `x_mm`

- sí se consume
- origen esperado: bottom-left
- fallback: `slot.get("x", 0)`

### `y_mm`

- sí se consume
- origen esperado: bottom-left
- fallback: `slot.get("y", 0)`

### `w_mm`

- sí se consume
- su semántica depende de engine y `slot_box_final`

### `h_mm`

- sí se consume
- su semántica depende de engine y `slot_box_final`

### `rotation_deg` / `rot_deg`

- sí se consume
- prioridad:
  - `rotation_deg`
  - fallback `rot_deg`

### `design_ref`

- sí se consume
- si falta o no resuelve contra `designs[]`, el slot se descarta completamente

### `logical_work_id`

- sí se consume indirectamente
- sirve para buscar `work.has_bleed` y `work.default_bleed_mm`

### `bleed_mm`

- sí se consume
- pero puede ser pisado por `export_settings` o `design_export`

### `crop_marks`

- sí se consume
- pero también puede ser pisado por configuración global/per-design

### `locked`

- no se consume en preview/PDF
- sólo afecta UI/edición

### `face`

- sí se consume
- define si el slot va a frente, dorso o se asume frente si falta

### `group_id`

- no se consume en preview/PDF
- solo afecta comportamiento de agrupación en frontend

## 4. Fallbacks si faltan campos

### Fallbacks de cara

- `slot.face` faltante -> `"front"`

### Fallbacks de posición

- `x_mm` faltante -> `x` -> `0`
- `y_mm` faltante -> `y` -> `0`

### Fallbacks de rotación

- `rotation_deg` -> `rot_deg` -> `0`

### Fallbacks de bleed

Orden real en `_sanitize_slot_bleed()`:

1. `export_settings.bleed_mm`
2. `design_export[design_ref].bleed_mm`
3. `slot.bleed_mm`
4. `work.default_bleed_mm`
5. `bleed_default_mm`

### Fallbacks de crop marks

Orden real en `_resolve_slot_crop_marks()`:

1. `export_settings.crop_marks`
2. `design_export[design_ref].crop_marks`
3. `slot.crop_marks`
4. `True`

### Fallbacks de tamaño trim

Si `trim_w <= 0`:

- `trim_w = max(1.0, w_mm)`

Si `trim_h <= 0`:

- `trim_h = max(1.0, h_mm)`

## 5. Cómo se resuelve `slots[].design_ref -> designs[].ref`

Primero `montar_offset_desde_layout()` arma:

- `ref_to_idx[str(ref)] = len(disenos)`

solo para diseños que cumplen:

- tienen `filename`
- tienen `ref`
- el archivo existe físicamente en `job_dir`

### Regla final

- si `slot.design_ref` no existe en `ref_to_idx`, el slot no entra en preview/PDF

### Implicación

El enlace real no es solo string a string:

- depende de `designs[].ref`
- depende de `designs[].filename`
- depende de que el PDF exista en disco

## 6. Cómo se resuelve `logical_work_id -> works[].id`

Se construye:

- `works = { w["id"]: w for w in works[] }`

Luego:

- `work = works.get(slot.logical_work_id)`

### Uso real de `work`

- `work.has_bleed`
- `work.default_bleed_mm`

### Si no resuelve

- `work = None`
- no rompe preview/PDF
- simplemente se usan defaults/fallbacks

## 7. En qué punto se decide si `w_mm/h_mm` representan trim o caja final

Esta decisión ocurre en dos niveles.

### Regla consolidada Fase 4 para `repeat`

Para slots generados por Step & Repeat PRO:

- `slot.w_mm / slot.h_mm` = caja final ocupada por el slot en el pliego
- `rotation_deg` = orientacion del contenido del diseno
- si `rotation_deg` es `90` o `270`, `w_mm/h_mm` ya deben venir intercambiados
- el frontend no debe rotar la caja externa otra vez
- el render PDF debe colocar el contenido dentro de esa caja final

### Nivel 1. En `montar_offset_desde_layout()`

#### Si `has_bleed` del work es `True`

- `trim_w = w_mm`
- `trim_h = h_mm`

#### Si `has_bleed` es `False` y engine es `repeat`

- `trim_w = w_mm`
- `trim_h = h_mm`
- además se marca:
  - `slot_box_final = True`

Comentario real del código:

- para `repeat`, el slot ya representa la caja final con bleed incluido
- si `bleed_mm = 0`, la caja final coincide con el tamano real del PDF/diseno

#### Si engine es `nesting` o `hybrid`

- `trim_w = w_mm - 2 * bleed_layout`
- `trim_h = h_mm - 2 * bleed_layout`
- y `slot_box_final = False`

### Nivel 2. En la rama manual de `realizar_montaje_inteligente()`

Si `slot_box_final` es `True`:

- se asume que `w_mm/h_mm` son tamaño final externo
- entonces se resta `2 * bleed_effective` para obtener el trim/base:
  - `base_w_mm = final_w_mm - 2 * bleed_effective`
  - `base_h_mm = final_h_mm - 2 * bleed_effective`

Si `slot_box_final` es `False`:

- `w_mm/h_mm` ya se toman como base/trim

## 8. Cómo impactan `imposition_engine`, `bleed_default_mm`, `designs[].bleed_mm`, `design_export`, `export_settings`

### `imposition_engine`

Impacta directamente:

- cómo se interpretan `w_mm/h_mm`
- si se marca o no `slot_box_final`
- estrategia interna:
  - `repeat` -> `grid`
  - `nesting` -> `nesting_pro`
  - `hybrid` -> `hybrid_nesting_repeat`

### `bleed_default_mm`

- fallback global del layout
- además se usa como `bleed_layout`
- en `nesting/hybrid` se resta desde `w_mm/h_mm` para obtener trim
- no debe pisar `bleed_mm = 0` cuando ese valor viene explicitamente desde el diseno o slot

### `designs[].bleed_mm`

- no se lee directamente al construir `front_positions/back_positions`
- influye antes:
  - al construir slots automáticos repeat
  - al nesting

Observacion Fase 4:

- `designs[].bleed_mm = 0` es valor explicito valido
- `0` no significa "usar fallback"

### `design_export`

- puede pisar `bleed_mm` por diseño
- puede pisar `crop_marks` por diseño

### `export_settings`

- prioridad máxima para `bleed_mm`
- prioridad máxima para `crop_marks`
- además define `output_mode`

## 9. Cómo se resuelven finalmente crop marks y bleed efectivos por slot

### Bleed efectivo por slot

#### Nivel 1. `_sanitize_slot_bleed()`

Prioridad real:

1. `export_settings.bleed_mm`
2. `design_export[design_ref].bleed_mm`
3. `slot.bleed_mm`
4. `work.default_bleed_mm`
5. `bleed_default_mm`

Observacion Fase 4:

- los valores `0` deben tratarse como explicitos
- solo debe usarse fallback si el campo esta ausente o es `None`

#### Nivel 2. Rama manual

Si `slot_box_final` es `True`:

- `bleed_effective` se recorta para no exceder media anchura/altura del slot

### Crop marks por slot

#### Nivel 1. `_resolve_slot_crop_marks()`

Prioridad real:

1. `export_settings.crop_marks`
2. `design_export[design_ref].crop_marks`
3. `slot.crop_marks`
4. `True`

#### Nivel 2. Render final

Las marcas sólo se dibujan si:

- `cutmarks_por_forma` es `True` a nivel config de cara
- `bleed_eff > 0`
- `pos.get("crop_marks", True)` es `True`

## 10. Cómo se interpreta `face` y qué pasa si está ausente o inconsistente

### Si falta en el slot

- se usa `"front"`

### Si es inconsistente con `faces[]`

- preview/PDF igual usa `slot.face`
- `faces[]` no invalida ni corrige el slot

### Si `active_face` dice una cosa y `slot.face` otra

- la salida final sigue a `slot.face`

### Riesgo real

Se puede guardar un layout visualmente “en dorso” pero sin slots `face = "back"`.

## 11. Cómo se traduce `rotation_deg` al formato interno real de salida

### En `montar_offset_desde_layout()`

- `rotation_deg` se convierte a:
  - `rot_deg`

### En rama manual

- `rot_deg = int(p.get("rot_deg", p.get("rot", 0)) or 0) % 360`

### En render final

- `rot = int(pos.get("rot_deg") or 0) % 360`
- si `rot in (90, 270)`:
  - el contenido se rota dentro de la caja final ya resuelta
  - no se debe estirar la imagen
  - se aplica traslacion explicita para que el contenido quede completo dentro del slot

### Regla de compatibilidad

En `repeat`, `rotation_deg` no significa "rotar el contenedor visual". El contenedor ya esta expresado por `w_mm/h_mm` como footprint final. La rotacion afecta al contenido fuente.

## 12. Diferencias entre slots generados por repeat, nesting, hybrid y edición manual

### Slots `repeat`

Origen:

- `routes._build_step_repeat_slots()`

Características:

- `design_ref = design.ref`
- `logical_work_id = design.work_id`
- `bleed_mm = bleed del diseño/layout`
- `crop_marks = True`
- `locked = False`
- `face = active_face`
- `w_mm/h_mm` representan footprint final del slot
- `rotation_deg` representa orientacion del contenido
- cuando rota 90/270, `w_mm/h_mm` ya se intercambian en la generacion
- en salida:
  - `slot_box_final = True`

### Slots `nesting`

Origen:

- `routes._slots_from_nesting_result()`

Características:

- `logical_work_id = None`
- `design_ref = slot.design_ref or slot.file`
- `bleed_mm` tomado del resultado o del layout
- `crop_marks = True`
- `locked = False`
- `face = active_face`
- en salida:
  - `slot_box_final = False`
  - se resta `2 * bleed_layout` a `w_mm/h_mm`

### Slots `hybrid`

Origen:

- base `nesting`
- luego `routes._repeat_pattern_over_sheet()`

Características:

- heredan la estructura de nesting
- solo cambia:
  - `id`
  - `x_mm`
  - `y_mm`
- en salida:
  - se comportan igual que `nesting`
  - `slot_box_final = False`

### Slots de edición manual pura

Origen:

- `addSlot()`
- `duplicateSlot()`
- drag/resize
- `applySlotForm()`
- `generateStepRepeatFromSelectedSlot()`
- `duplicateFrontToBack()`

Características:

- el usuario define `w_mm/h_mm` directamente
- el backend no sabe si representan trim o caja final por intención del usuario
- esa interpretación termina dependiendo de `imposition_engine`

## 13. Validaciones que faltarían para blindar el contrato de slots

- validar schema estricto de cada slot
- exigir `id` único
- exigir `face` dentro de `{front, back}`
- validar `design_ref` contra `designs[].ref`
- validar `logical_work_id` contra `works[].id`
- validar números finitos en `x_mm`, `y_mm`, `w_mm`, `h_mm`, `bleed_mm`
- validar `w_mm > 0` y `h_mm > 0`
- validar `rotation_deg` dentro de un conjunto permitido o normalizarlo explícitamente
- validar que no haya slots sin `design_ref` al generar preview/PDF si el usuario espera salida real
- validar consistencia entre engine y semántica de `w_mm/h_mm`
- validar que `back_positions` no quede vacío si `faces` contiene `"back"` y el usuario espera retiro

## 14. Campos de slots que conviene declarar como estrictamente congelados

- `id`
- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`
- `rotation_deg`
- `design_ref`
- `logical_work_id`
- `bleed_mm`
- `crop_marks`
- `face`

### Congelados secundarios

- `locked`
- `group_id`

No afectan render final, pero sí continuidad de edición y jobs guardados.

## Ejemplo concreto 1: slot frente `repeat`

### Slot persistido

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
  "face": "front"
}
```

### `front_positions` resultante

Suponiendo:

- `designs[].ref = "file0"`
- `imposition_engine = "repeat"`
- `export_settings.bleed_mm = 3`
- `export_settings.crop_marks = true`

Se transforma en:

```json
{
  "file_idx": 0,
  "x_mm": 102.0,
  "y_mm": 40.0,
  "w_mm": 216.0,
  "h_mm": 303.0,
  "rot_deg": 0,
  "bleed_mm": 3.0,
  "crop_marks": true,
  "slot_box_final": true
}
```

### Posición interna manual resultante

Luego la rama manual lo convierte aproximadamente en:

```json
{
  "archivo": "<ruta_pdf_real>",
  "file_idx": 0,
  "x": 102.0,
  "y": 40.0,
  "ancho": 210.0,
  "alto": 297.0,
  "rot_deg": 0,
  "bleed_mm": 3.0,
  "source_w_mm": 210.0,
  "source_h_mm": 297.0
}
```

Observación:

- `216 x 303` era caja final
- se resta bleed para recuperar trim `210 x 297`

## Ejemplo concreto 2: slot dorso clonado

### Slot persistido

```json
{
  "id": "s1712870000000_0_back",
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
  "face": "back"
}
```

### `back_positions` resultante

```json
{
  "file_idx": 0,
  "x_mm": 102.0,
  "y_mm": 40.0,
  "w_mm": 216.0,
  "h_mm": 303.0,
  "rot_deg": 0,
  "bleed_mm": 3.0,
  "crop_marks": true,
  "slot_box_final": true
}
```

### Comportamiento final

- entra en `back_positions`
- se renderiza en `montaje_back.pdf`
- luego se concatena con `montaje_front.pdf` para formar `montaje_final.pdf`

## Campos de slot ignorados por preview/PDF

- `id`
- `locked`
- `group_id`

Pueden persistirse, pero no cambian el render final.

## Conclusión operativa

El contrato real de `slots[]` no es solamente geométrico. Cada slot combina:

- referencia a diseño
- referencia opcional a work
- geometría
- cara
- bleed/crop resolubles por prioridad
- interpretación dependiente del engine

La zona más frágil hoy es esta:

- `design_ref`
- `face`
- `rotation_deg`
- semántica de `w_mm/h_mm`
- prioridades de bleed/crop
- `slot_box_final` implícito por engine

Si algo de eso cambia sin congelar compatibilidad, preview y PDF pueden divergir del editor aunque el JSON siga “pareciendo válido”.
