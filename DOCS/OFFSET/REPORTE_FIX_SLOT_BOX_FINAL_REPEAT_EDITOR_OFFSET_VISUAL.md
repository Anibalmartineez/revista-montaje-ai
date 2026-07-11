# Reporte fix slot_box_final repeat - Editor Offset Visual

## 1. Resumen ejecutivo

Se corrigio de forma acotada la interpretacion implicita de `slot_box_final` para slots Step & Repeat despues de normalizar el contrato de sangrado.

Desde fases previas, Step & Repeat persiste:

```text
slot.w_mm / slot.h_mm = trim
slot.bleed_mm = sangrado por lado
```

Pero `services/editor_offset_output_service.py` todavia podia resolver `slot_box_final=True` para slots repeat no rotados. Eso hacia que `montaje_offset_inteligente.py` interpretara `w_mm/h_mm` como caja exterior final, aunque ahora esos campos representan trim.

## 2. Problema corregido

El output service decidia `slot_box_final=True` por defecto para repeat no rotado antes de comparar si el slot coincidia con trim o con caja expandida.

Eso era inconsistente con el nuevo contrato:

```text
design 50 x 30 mm
slot 50 x 30 mm
bleed 1 mm
```

En ese caso, el slot ya no representa una caja final exterior de `52 x 32`; representa el trim `50 x 30` con bleed separado.

## 3. Comportamiento anterior

Para `imposition_engine="repeat"` y rotacion 0:

```text
slot.w_mm = 50
slot.h_mm = 30
slot.bleed_mm = 1
design.width_mm = 50
design.height_mm = 30
```

`_resolve_slot_box_final()` devolvia `True` sin comparar cajas.

## 4. Comportamiento nuevo

Para repeat sin `slot_box_final` explicito:

- Si `slot.w_mm/h_mm` coincide con el trim del design y `bleed_mm > 0`, devuelve `False`.
- Si `slot.w_mm/h_mm` coincide con la caja expandida `trim + 2 * bleed`, conserva `True` para layouts legacy.
- Si el slot trae `slot_box_final` explicito, se respeta.
- Si falta informacion de design, se mantiene el comportamiento conservador legacy.

## 5. Archivos modificados

- `services/editor_offset_output_service.py`
- `tests/test_editor_offset_characterization.py`
- `DOCS/OFFSET/REPORTE_FIX_SLOT_BOX_FINAL_REPEAT_EDITOR_OFFSET_VISUAL.md`

## 6. Detalle tecnico del cambio en output service

Se agrego un helper interno para calcular cajas esperadas de repeat:

```python
_repeat_expected_boxes(design_w, design_h, bleed_mm, rot)
```

Ese helper devuelve:

- caja trim esperada
- caja final/productiva esperada

La funcion `_resolve_slot_box_final()` ahora compara `slot.w_mm/h_mm` contra esas cajas antes de decidir.

La salida temprana para repeat no rotado fue eliminada para que rotacion 0 tambien pase por la comparacion trim vs final.

## 7. Detalle tecnico de los tests

Se agrego:

```text
test_output_service_repeat_trim_slot_is_not_treated_as_final_box
```

Ese test construye un layout repeat con:

```text
design.width_mm = 50
design.height_mm = 30
slot.w_mm = 50
slot.h_mm = 30
slot.bleed_mm = 1
export_settings.bleed_mm = 3
```

Y valida que `posiciones_manual[0]` conserve:

```text
w_mm = 50
h_mm = 30
bleed_mm = 1
slot_box_final = False
source_w_mm = 50
source_h_mm = 30
```

El test existente de layout legacy expandido sigue cubriendo el caso donde `slot.w_mm/h_mm` ya coincide con caja final expandida y debe conservar `slot_box_final=True`.

## 8. Que se mantiene legacy

Se mantiene:

- `slot.slot_box_final` explicito como prioridad.
- Comportamiento conservador si no hay design size confiable.
- Compatibilidad con slots repeat legacy que ya guardan caja expandida.
- Ruta especial de rotacion manual legacy para cajas expandidas no rotadas con `rotation_deg` 90/270.
- Semantica de otros motores.

## 9. Que NO se toco

No se tocaron:

- Canvas.
- `output_panel.js`.
- Upload.
- Step Repeat engine.
- Nesting engine.
- `montaje_offset_inteligente.py`.
- Render PDF directo.
- Preview PNG.
- Contrato de `design_export`.

## 10. Tests ejecutados y resultado

Se ejecuto:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
```

Resultado:

```text
17 passed
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

## 11. Validacion con git diff --check

Se ejecuto:

```powershell
git diff --check
```

Resultado: exit code 0. Git mostro solo advertencias LF/CRLF normales de Windows, sin errores de whitespace.

## 12. Riesgos pendientes

Quedan pendientes:

- Canvas todavia no muestra overlay real de bleed en todos los casos.
- La posicion visual del trim en canvas puede diferir de la caja productiva que usa output.
- Nesting todavia no fue normalizado al contrato trim + bleed separado.
- Upload sin `work.final_size_mm` sigue usando MediaBox y queda pendiente TrimBox/BleedBox.
- `montaje_offset_inteligente.py` conserva logica legacy, aunque esta fase evita enviarle `slot_box_final=True` en slots repeat nuevos con trim.

## 13. Proxima fase recomendada

La siguiente fase recomendada es una auditoria/correccion acotada del canvas para visualizar bleed efectivo sin cambiar el contrato:

1. Confirmar si el canvas puede dibujar trim y bleed box separadas.
2. Usar `slot.bleed_mm` como fuente preferente en repeat.
3. Evitar que `bleed_default_mm=3` pinte sangrado cuando el slot trae `bleed_mm=1`.
4. No tocar PDF ni motores en esa fase.

