# Reporte fix Step Repeat bleed - Editor Offset Visual

## 1. Resumen ejecutivo

Se implemento la normalizacion de Step & Repeat para el contrato de sangrado del Editor Offset Visual.

Desde esta fase, `engines/step_repeat_pro_engine.py` persiste `slot.w_mm` y `slot.h_mm` como trim, no como caja total con sangrado. `slot.bleed_mm` conserva el sangrado adicional por lado.

El motor sigue usando caja total productiva internamente para packing, bounds y solapes:

```text
caja_total_w = slot.w_mm + 2 * slot.bleed_mm
caja_total_h = slot.h_mm + 2 * slot.bleed_mm
```

## 2. Problema corregido

Antes de esta fase, Step & Repeat tomaba `design.width_mm`, `design.height_mm` y `design.bleed_mm`, y persistia slots con dimensiones ya expandidas:

```text
slot.w_mm = design.width_mm + 2 * bleed_mm
slot.h_mm = design.height_mm + 2 * bleed_mm
```

Esto duplicaba o propagaba ambiguedad cuando el diseno ya venia expandido o cuando otras capas volvian a interpretar `slot.w_mm/h_mm` como trim.

## 3. Comportamiento anterior

Ejemplo anterior:

```text
design.width_mm=50
design.height_mm=30
design.bleed_mm=2
```

Step & Repeat persistia:

```text
slot.w_mm=54
slot.h_mm=34
slot.bleed_mm=2
```

Si el diseno ya venia como `54x34` con `bleed_mm=2`, Step & Repeat persistia `58x38`, caracterizando doble conteo en dimensiones persistidas.

## 4. Comportamiento nuevo

Ejemplo nuevo:

```text
design.width_mm=50
design.height_mm=30
design.bleed_mm=2
```

Step & Repeat persiste:

```text
slot.w_mm=50
slot.h_mm=30
slot.bleed_mm=2
```

Para packing, el motor calcula internamente la caja productiva `54x34`.

Si el diseno viene como `54x34` con `bleed_mm=2`, el slot persistido queda `54x34` y `bleed_mm=2`; ya no se expande a `58x38`.

## 5. Archivos modificados

Archivos modificados en esta fase:

- `engines/step_repeat_pro_engine.py`
- `tests/test_step_repeat_pro_engine.py`
- `DOCS/OFFSET/REPORTE_FIX_STEP_REPEAT_BLEED_EDITOR_OFFSET_VISUAL.md`

No se modifico `tests/test_editor_offset_characterization.py` en esta fase.

## 6. Detalle tecnico del cambio en engines/step_repeat_pro_engine.py

Cambios principales:

- `design_dimensions()` ahora devuelve trim y bleed separado: `width`, `height`, `bleed`.
- Se agrego `productive_size(width, height, bleed)` para derivar la caja total productiva.
- Se agrego `slot_productive_size(slot)` para calcular caja total desde `slot.w_mm/h_mm` y `slot.bleed_mm`.
- `slot_overlaps_existing()` ahora evalua solapes con caja productiva derivada.
- `append_step_repeat_slots_in_bounds()` usa caja total para:
  - elegir orientacion;
  - calcular columnas;
  - avanzar posiciones `x/y`;
  - validar bounds;
  - avanzar `cursor_y`.
- El slot persistido guarda trim orientado:
  - sin rotacion: `w_mm=trim_w`, `h_mm=trim_h`;
  - rotacion 90/270: `w_mm=trim_h`, `h_mm=trim_w`.
- `estimate_repeat_group_height()` usa caja total para estimar altura de grupos.
- `append_fill_slots_smart()` usa caja total para candidatos y packing, pero persiste trim.
- `slot_group_bbox()`, `can_place_translated_group()` y `translated_groups_are_safe()` usan caja productiva para compactacion y validaciones internas.

## 7. Detalle tecnico del cambio en tests/test_step_repeat_pro_engine.py

Cambios principales:

- `_overlaps()` ahora calcula solapes usando caja productiva:

```text
w_productivo = slot.w_mm + 2 * slot.bleed_mm
h_productivo = slot.h_mm + 2 * slot.bleed_mm
```

- `test_repeat_current_behavior_expands_trim_design_size_by_bleed` fue reemplazado por:

```text
test_repeat_persists_trim_design_size_and_bleed_separately
```

Valida que `design 50x30` con `bleed 2` persiste `slot 50x30` y `slot.bleed_mm=2`.

- `test_repeat_characterizes_current_behavior_double_counts_bleed_for_expanded_design_size` fue reemplazado por:

```text
test_repeat_avoids_double_counting_bleed_in_persisted_slot_dimensions
```

Valida que `design 54x34` con `bleed 2` persiste `slot 54x34`, no `58x38`.

- Se agrego:

```text
test_repeat_packs_with_productive_bleed_box_while_persisting_trim_size
```

Valida que dos piezas `50x30` con `bleed 2` y spacing `0` se separan productivamente por `54 mm`, aunque el slot persistido conserve `w_mm=50`.

## 8. Que se mantiene legacy

Se mantiene legacy:

- Upload sin `work.final_size_mm` sigue usando `MediaBox`.
- `engines/nesting_pro_engine.py` sigue usando tamano acolchado con `width_mm + 2 * bleed_mm`.
- `services/editor_offset_output_service.py` no fue adaptado todavia al contrato completo.
- `montaje_offset_inteligente.py` conserva su logica actual de salida y compatibilidad.
- `slot_box_final` no fue modificado.
- PDF final y preview no fueron modificados.

## 9. Que NO se toco

No se tocaron:

- `services/editor_offset_uploads.py`;
- `engines/nesting_pro_engine.py`;
- `services/editor_offset_output_service.py`;
- `montaje_offset_inteligente.py`;
- `slot_box_final`;
- PDF final;
- preview;
- rutas Flask;
- tests de upload;
- tests de output.

## 10. Tests ejecutados y resultado

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q
```

Resultado:

```text
17 passed
```

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
```

Resultado:

```text
14 passed
```

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q
```

Resultado:

```text
7 passed
```

## 11. Validacion con git diff --check

Validacion final esperada para esta fase:

```powershell
git diff --check
```

Resultado observado:

```text
exit code 0
```

Git puede mostrar advertencias LF/CRLF en archivos tocados por la plataforma, pero no se reportaron errores de whitespace.

## 12. Riesgos pendientes

Riesgos pendientes:

- `services/editor_offset_output_service.py` todavia contiene compatibilidad mixta entre slots repeat como caja final y slots como trim.
- `montaje_offset_inteligente.py` todavia reconstruye caja de dibujo con `source_w_mm/source_h_mm + 2 * bleed_effective`.
- `engines/nesting_pro_engine.py` todavia persiste `slot.w_mm/h_mm` como caja acolchada.
- Upload sin `work.final_size_mm` todavia toma `MediaBox`; `TrimBox` y `BleedBox` quedan pendientes.
- Layouts historicos pueden tener slots repeat ya guardados con `w_mm/h_mm` como caja total.

## 13. Proxima fase recomendada

La proxima fase debe elegir una sola superficie:

1. Normalizar `engines/nesting_pro_engine.py` para que persista trim y use caja productiva internamente, igual que Step & Repeat.
2. O adaptar `services/editor_offset_output_service.py` para consumir el nuevo contrato de slots repeat como trim y mantener compatibilidad con layouts historicos.

No conviene hacer nesting y output en la misma fase. Nesting cambia generacion de slots; output cambia interpretacion productiva y PDF. Separarlas reduce el riesgo y mantiene validaciones focalizadas.
