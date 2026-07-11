# Reporte fix output bleed repeat - Editor Offset Visual

## 1. Resumen ejecutivo

Se implemento la correccion minima para que Preview/PDF del Editor Offset Visual respeten `slot.bleed_mm` en slots Step & Repeat.

Desde esta fase, cuando `imposition_engine == "repeat"`, `services/editor_offset_output_service.py` usa `slot.bleed_mm` como prioridad antes de `design_export.bleed_mm` y `export_settings.bleed_mm`, siempre que el slot tenga `bleed_mm` definido.

Se mantiene `slot.export_overrides.bleed_mm = true` como override explicito de slot.

## 2. Problema corregido

Antes del cambio, un layout repeat podia tener:

```text
slot.bleed_mm = 1
export_settings.bleed_mm = 3
slot sin export_overrides
```

Pero `_sanitize_slot_bleed()` priorizaba `export_settings.bleed_mm` antes de `slot.bleed_mm`. Como resultado, `posiciones_manual[].bleed_mm` podia quedar en `3` aunque el slot generado por Step & Repeat tuviera `1`.

Eso podia hacer que Preview/PDF usaran caja productiva con 3 mm por lado en vez de 1 mm por lado.

## 3. Comportamiento anterior

Precedencia anterior relevante en `_sanitize_slot_bleed()`:

1. `slot.export_overrides.bleed_mm` si existia.
2. `design_export[design_ref].bleed_mm`.
3. `export_settings.bleed_mm`.
4. `slot.bleed_mm`.
5. `work.default_bleed_mm`.
6. `layout.bleed_default_mm`.

Con esa precedencia, `export_settings.bleed_mm=3` podia sobrescribir `slot.bleed_mm=1` para slots repeat sin override explicito.

## 4. Comportamiento nuevo

Cuando output service llama `_sanitize_slot_bleed(..., prefer_slot=True)` para `imposition_engine == "repeat"`:

- Si el slot tiene `bleed_mm`, ese valor se usa antes que `design_export` y `export_settings`.
- `slot.export_overrides.bleed_mm=true` sigue siendo la prioridad explicita mas alta.

Caso obligatorio validado:

```text
imposition_engine = repeat
slot.bleed_mm = 1
export_settings.bleed_mm = 3
slot sin export_overrides
```

Resultado:

```text
posiciones_manual[0].bleed_mm = 1
```

## 5. Archivos modificados

Archivos modificados:

- `services/editor_offset_output_service.py`
- `tests/test_editor_offset_characterization.py`
- `DOCS/OFFSET/REPORTE_FIX_OUTPUT_BLEED_REPEAT_EDITOR_OFFSET_VISUAL.md`

## 6. Detalle tecnico del cambio en services/editor_offset_output_service.py

Se uso el parametro existente `prefer_slot`.

Cambio aplicado en `_sanitize_slot_bleed()`:

```python
if bleed_val is None and prefer_slot and slot.get("bleed_mm") is not None:
    bleed_val = slot.get("bleed_mm")
```

Este bloque queda despues de la prioridad explicita de `slot.export_overrides.bleed_mm` y antes de `design_export` / `export_settings`.

`_positions_for_face()` ya pasaba:

```python
prefer_slot=engine_name == "repeat"
```

Por tanto, el cambio se limita a activar el comportamiento previsto para repeat sin alterar otros motores.

## 7. Detalle tecnico de los tests

Se agregaron dos tests focalizados en `tests/test_editor_offset_characterization.py`.

Primer test:

```text
test_output_service_repeat_prefers_slot_bleed_over_export_default
```

Valida:

- `imposition_engine = "repeat"`
- `slot.bleed_mm = 1`
- `export_settings.bleed_mm = 3`
- sin `slot.export_overrides`
- `posiciones_manual[0].bleed_mm == 1`

Segundo test:

```text
test_output_service_repeat_keeps_explicit_slot_bleed_override
```

Valida:

- `slot.bleed_mm = 1`
- `slot.export_overrides.bleed_mm = true`
- `design_export[ref].bleed_mm = 2`
- `export_settings.bleed_mm = 3`
- `posiciones_manual[0].bleed_mm == 1`

Ambos tests usan `render_fn` fake para capturar `config.posiciones_manual`. No renderizan PDF real.

## 8. Precedencia de bleed anterior

Precedencia anterior:

1. `slot.bleed_mm` solo si `slot.export_overrides.bleed_mm` era verdadero.
2. `design_export[design_ref].bleed_mm`.
3. `export_settings.bleed_mm`.
4. `slot.bleed_mm`.
5. `work.default_bleed_mm`.
6. `layout.bleed_default_mm`.

Problema: para repeat, un `slot.bleed_mm` generado por el motor podia quedar debajo del default global de export.

## 9. Precedencia de bleed nueva para repeat

Precedencia nueva para repeat:

1. `slot.bleed_mm` si `slot.export_overrides.bleed_mm` es verdadero.
2. `slot.bleed_mm` si existe y `prefer_slot=True`.
3. `design_export[design_ref].bleed_mm`.
4. `export_settings.bleed_mm`.
5. `work.default_bleed_mm`.
6. `layout.bleed_default_mm`.

La precedencia para otros motores no se cambia en esta fase, porque `prefer_slot` solo llega verdadero cuando `engine_name == "repeat"`.

## 10. Que se mantiene legacy

Se mantiene legacy:

- La semantica de `design_export.bleed_mm` para otros motores.
- La semantica de `export_settings.bleed_mm` para otros motores.
- La logica actual de `slot_box_final`.
- El render legacy de `montaje_offset_inteligente.py`.
- El canvas sin overlay de bleed.
- `output_panel.js` sigue guardando `export_settings.bleed_mm`.
- PDF final no fue modificado directamente.

## 11. Que NO se toco

No se tocaron:

- Canvas.
- `static/js/editor_offset_visual.js`.
- `static/js/editor_offset_visual/renderer_canvas.js`.
- `static/js/editor_offset_visual/output_panel.js`.
- Motores.
- Upload.
- `montaje_offset_inteligente.py`.
- PDF final directamente.
- `slot_box_final`.

## 12. Tests ejecutados y resultado

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
```

Resultado:

```text
16 passed
```

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q
```

Resultado:

```text
7 passed
```

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q
```

Resultado:

```text
17 passed
```

## 13. Validacion con git diff --check

Validacion:

```powershell
git diff --check
```

Resultado:

```text
exit code 0
```

Git mostro advertencias LF/CRLF para archivos modificados en Windows, pero no reporto errores de whitespace.

## 14. Riesgos pendientes

Riesgos pendientes:

- No se corrigio `slot_box_final`.
- Despues del fix de Step & Repeat, los slots repeat nuevos guardan `w_mm/h_mm` como trim, pero output service todavia puede resolver `slot_box_final=True` para repeat no rotado.
- No se agrego overlay de bleed al canvas.
- El canvas sigue mostrando `slot.w_mm/h_mm` como caja visible.
- `montaje_offset_inteligente.py` sigue usando la logica legacy de caja de dibujo y marcas.
- `engines/nesting_pro_engine.py` sigue pendiente de normalizacion.
- Upload sin `work.final_size_mm` sigue pendiente de normalizacion de `MediaBox` / `TrimBox` / `BleedBox`.

## 15. Proxima fase recomendada

La siguiente fase recomendada debe ser `slot_box_final` para repeat, antes del canvas.

Motivo:

- Preview/PDF son la superficie productiva critica.
- Si `slot_box_final` sigue tratando slots repeat nuevos como caja externa final, el PDF puede quedar desalineado aunque el bleed efectivo ya sea correcto.
- El overlay de bleed en canvas es importante para UX y validacion visual, pero no debe anteponerse a corregir la interpretacion productiva de output.

Alcance recomendado para la siguiente fase:

- Auditar y corregir solo `services/editor_offset_output_service.py` para que slots repeat nuevos con `w_mm/h_mm` trim no se traten como caja final.
- Agregar tests con `render_fn` fake que validen `posiciones_manual` para repeat trim + bleed.
- No tocar `montaje_offset_inteligente.py` salvo que la adaptacion en output service no alcance.
