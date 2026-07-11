# Reporte fix upload bleed - Editor Offset Visual

## 1. Resumen ejecutivo

Se implemento la primera correccion productiva segura del contrato de sangrado del Editor Offset Visual, limitada al camino de upload con `work.final_size_mm`.

Desde este cambio, cuando existe `work.final_size_mm`, `design.width_mm` y `design.height_mm` se persisten como medida final de corte, sin sumar `2 * bleed_mm`. `design.bleed_mm` se mantiene como sangrado recomendado por lado.

El objetivo fue cortar el doble conteo en la primera fuente del dato, sin tocar motores, salida PDF, `slot_box_final` ni compatibilidad legacy de otros caminos.

## 2. Problema corregido

Antes del fix, el upload podia persistir dimensiones ya expandidas por sangrado cuando el trabajo tenia:

```text
final_size_mm=[50, 30]
default_bleed_mm=2
has_bleed=False
```

Ese caso guardaba:

```text
design.width_mm=54
design.height_mm=34
design.bleed_mm=2
```

Luego repeat podia volver a sumar `2 * bleed_mm`, generando slots `58x38`. Esa cadena documentaba el doble conteo actual.

## 3. Comportamiento anterior

En `services/editor_offset_uploads.py`, dentro de `append_uploaded_designs()`, cuando existia `work.final_size_mm`:

1. `width_mm` tomaba `final_size_mm[0]`.
2. `height_mm` tomaba `final_size_mm[1]`.
3. Si `related_work.has_bleed` era falso, se sumaba `2 * bleed_mm` a ancho y alto.
4. Se persistia `design.bleed_mm` de todos modos.

Resultado anterior para final `50x30` con bleed `2`:

```text
design.width_mm=54
design.height_mm=34
design.bleed_mm=2
```

## 4. Comportamiento nuevo

Cuando existe `work.final_size_mm`, el upload persiste `design.width_mm` y `design.height_mm` como trim o medida final de corte, sin expansion por sangrado.

Resultado nuevo para:

```text
final_size_mm=[50, 30]
default_bleed_mm=2
has_bleed=False
```

es:

```text
design.width_mm=50
design.height_mm=30
design.bleed_mm=2
```

`design.bleed_mm` conserva la semantica de sangrado recomendado por lado.

## 5. Archivos modificados

Archivos modificados en la correccion:

- `services/editor_offset_uploads.py`
- `tests/test_editor_offset_characterization.py`

Este reporte fue agregado despues para documentar el cambio:

- `DOCS/OFFSET/REPORTE_FIX_UPLOAD_BLEED_EDITOR_OFFSET_VISUAL.md`

## 6. Detalle tecnico del cambio en services/editor_offset_uploads.py

Se elimino la expansion condicional:

```python
if not related_work.get("has_bleed"):
    width_mm += 2 * bleed_mm
    height_mm += 2 * bleed_mm
```

El flujo queda asi cuando `work.final_size_mm` existe:

```text
width_mm = final_size_mm[0]
height_mm = final_size_mm[1]
bleed_mm = related_work.default_bleed_mm o fallback del layout
```

El campo persistido `design.bleed_mm` no cambia. Sigue guardandose como sangrado recomendado por lado.

## 7. Detalle tecnico del cambio en tests/test_editor_offset_characterization.py

El test de upload con `final_size_mm`, `default_bleed_mm` y `has_bleed=False` se actualizo de caracterizacion de comportamiento anterior a contrato esperado.

Nombre anterior:

```text
test_editor_offset_upload_current_behavior_expands_work_final_size_without_bleed
```

Nombre nuevo:

```text
test_editor_offset_upload_persists_work_final_size_as_trim_without_bleed
```

Expectativa anterior:

```text
width_mm=54
height_mm=34
bleed_mm=2
```

Expectativa nueva:

```text
width_mm=50
height_mm=30
bleed_mm=2
```

## 8. Que se mantiene legacy

Se mantiene legacy el camino de PDFs sin `work.final_size_mm`.

El test `test_editor_offset_upload_characterizes_current_behavior_uses_pdf_mediabox` no se cambio. Por tanto, upload todavia caracteriza que un PDF con `MediaBox=80x40`, `TrimBox=50x30` y `BleedBox=54x34` persiste `design.width_mm=80`, `design.height_mm=40`.

`MediaBox`, `TrimBox` y `BleedBox` quedan para una fase posterior.

Repeat tambien mantiene comportamiento legacy: `engines/step_repeat_pro_engine.py` todavia suma `2 * bleed_mm` al generar `slot.w_mm` / `slot.h_mm`.

## 9. Que NO se toco

No se tocaron:

- motores;
- `engines/step_repeat_pro_engine.py`;
- `engines/nesting_pro_engine.py`;
- `services/editor_offset_output_service.py`;
- `montaje_offset_inteligente.py`;
- `slot_box_final`;
- PDF final;
- preview/PDF;
- rutas;
- contrato general de salida;
- tests de repeat;
- tests de output.

## 10. Tests ejecutados y resultado

Se ejecutaron los comandos obligatorios:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
```

Resultado:

```text
14 passed
```

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q
```

Resultado:

```text
16 passed
```

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q
```

Resultado:

```text
7 passed
```

## 11. Validacion con git diff --check

Se ejecuto:

```powershell
git diff --check
```

Resultado:

```text
exit code 0
```

Git mostro advertencias LF/CRLF para los dos archivos modificados:

- `services/editor_offset_uploads.py`
- `tests/test_editor_offset_characterization.py`

No se reportaron errores de whitespace.

## 12. Riesgos pendientes

Riesgos aun pendientes:

- Upload sin `work.final_size_mm` sigue usando `MediaBox`.
- No se corrigio todavia lectura de `TrimBox` / `BleedBox`.
- Repeat todavia suma bleed al generar slots.
- Nesting todavia usa tamano acolchado con `2 * bleed_mm`.
- Output service todavia contiene compatibilidad mixta entre trim, caja final y `slot_box_final`.
- `montaje_offset_inteligente.py` todavia reconstruye caja de dibujo con `source_w_mm/source_h_mm + 2 * bleed_effective`.
- Jobs historicos pueden tener `design.width_mm/design.height_mm` y `slot.w_mm/slot.h_mm` ya expandidos.

## 13. Proxima fase recomendada

La siguiente fase deberia elegir una sola superficie:

1. Motores: normalizar `step_repeat_pro_engine.py` y luego `nesting_pro_engine.py` para que `slot.w_mm/slot.h_mm` representen trim y la caja total se derive de `slot.bleed_mm`.
2. Cajas PDF: normalizar upload sin `work.final_size_mm` para leer `TrimBox` / `BleedBox` / `MediaBox` con metadata explicita.

No conviene hacer motores y normalizacion de cajas PDF en la misma fase. Mezclarlas aumentaria el riesgo porque cambiaria a la vez la fuente de dimensiones y la geometria generada.

Recomendacion SAFE: avanzar primero con motores si el objetivo inmediato es evitar doble conteo en Step & Repeat; avanzar primero con cajas PDF si el objetivo inmediato es importar PDFs reales de preprensa con `TrimBox` y `BleedBox` confiables.
