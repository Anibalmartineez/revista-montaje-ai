# Contrato tecnico de sangrado - Editor Offset Visual

## 1. Resumen ejecutivo

Este documento propone el contrato definitivo de sangrado para el Editor Offset Visual y define la primera correccion productiva segura.

Conclusion principal: el sistema debe adoptar una semantica unica de trim y sangrado:

- `design.width_mm` / `design.height_mm` = medida final de corte, sin sangrado.
- `design.bleed_mm` = sangrado recomendado por lado para ese diseno.
- `slot.w_mm` / `slot.h_mm` = medida final de corte colocada en el pliego, sin sangrado.
- `slot.bleed_mm` = sangrado adicional por lado para ese slot.
- caja total de dibujo = `slot.w_mm + 2 * slot.bleed_mm` por `slot.h_mm + 2 * slot.bleed_mm`.

La primera correccion productiva recomendada no debe tocar PDF final ni motores todavia. Debe corregir primero `services/editor_offset_uploads.py` para que los nuevos uploads persistan `design.width_mm` / `design.height_mm` como trim, no como caja ya expandida. Es la fuente mas temprana del doble conteo y tiene menor blast radius que cambiar motores, output o `montaje_offset_inteligente.py`.

Esta primera fase debe mantener compatibilidad con trabajos historicos: no migrar automaticamente jobs existentes y no reinterpretar layouts guardados sin una bandera o normalizador explicito.

## 2. Evidencia encontrada en los tests de caracterizacion

Tests nuevos o reforzados en `tests/test_editor_offset_characterization.py`:

- `test_editor_offset_upload_current_behavior_expands_work_final_size_without_bleed`: caracteriza que hoy un work con `final_size_mm=[50, 30]`, `default_bleed_mm=2` y `has_bleed=False` persiste `design.width_mm=54`, `design.height_mm=34`, `design.bleed_mm=2`.
- `test_editor_offset_upload_characterizes_current_behavior_uses_pdf_mediabox`: caracteriza que hoy upload usa `MediaBox` como fuente de `design.width_mm` / `design.height_mm`; en el test, un PDF con `MediaBox=80x40`, `TrimBox=50x30` y `BleedBox=54x34` queda persistido como `80x40`.
- `test_output_service_characterizes_current_behavior_with_expanded_design_size`: caracteriza que output service acepta un diseno ya expandido `54x34` con `bleed_mm=2`, un slot `58x38`, y genera `posiciones_manual` con `w_mm=58`, `h_mm=38`, `bleed_mm=2`, `slot_box_final=True`, `source_w_mm=54`, `source_h_mm=34`.

Tests nuevos en `tests/test_step_repeat_pro_engine.py`:

- `test_repeat_current_behavior_expands_trim_design_size_by_bleed`: caracteriza que un diseno trim `50x30` con `bleed_mm=2` genera slot `54x34`.
- `test_repeat_characterizes_current_behavior_double_counts_bleed_for_expanded_design_size`: caracteriza que un diseno ya expandido `54x34` con `bleed_mm=2` genera slot `58x38`.

Estos tests no declaran que el comportamiento actual sea correcto. Son tests de congelamiento para poder corregir despues con seguridad.

## 3. Comportamiento actual del sistema

Evidencia de `services/editor_offset_uploads.py`:

- `pdf_page_size_mm()` lee `page.mediabox.width` y `page.mediabox.height`.
- Si existe `work.final_size_mm`, upload reemplaza la medida del PDF por esa medida.
- Si `related_work.has_bleed` es falso, upload suma `2 * bleed_mm` a ancho y alto antes de persistir el diseno.
- El campo persistido `design.bleed_mm` se guarda igualmente.

Evidencia de `engines/step_repeat_pro_engine.py`:

- `design_dimensions()` toma `design.width_mm`, `design.height_mm` y `design.bleed_mm`.
- Devuelve `width + 2 * bleed`, `height + 2 * bleed`, `bleed`.
- Los slots generados por repeat usan esas dimensiones como `slot.w_mm` / `slot.h_mm`.

Evidencia de `engines/nesting_pro_engine.py`:

- `NestingPiece.padded_size` devuelve `width_mm + 2 * bleed_mm`, `height_mm + 2 * bleed_mm`.
- `compute_nesting()` genera slots usando ese tamano acolchado como `w_mm` / `h_mm`.

Evidencia de `services/editor_offset_output_service.py`:

- `_design_trim_size()` trata `design.width_mm` / `design.height_mm` como tamano trim.
- `_resolve_slot_box_final()` compara slots contra `design.width_mm + 2 * bleed_mm`.
- `_positions_for_face()` resuelve un `bleed_val`, calcula `source_w_mm` / `source_h_mm` desde `design.width_mm` / `design.height_mm`, y pasa `posiciones_manual` hacia la salida legacy.
- Para `engine_name == "repeat"`, hoy deja `trim_w = w_mm` y `trim_h = h_mm`, aunque esos `w_mm` / `h_mm` suelen venir ya expandidos por el motor.

Evidencia de `montaje_offset_inteligente.py`:

- La rama manual documenta que `posiciones_manual` viene con `w/h = TRIM`, pero tambien contiene comentarios de compatibilidad indicando que para repeat el slot puede representar caja final con bleed.
- En el dibujado final vuelve a calcular `source_draw_w_mm = source_w_mm + 2 * bleed_effective` y `source_draw_h_mm = source_h_mm + 2 * bleed_effective`.
- Si `slot_box_final` esta activo, la caja externa puede reemplazarse por `slot_w_mm` / `slot_h_mm`.
- Las marcas de corte se dibujan alrededor del trim calculado a partir de esa caja.

Evidencia de `services/editor_offset_layout_defaults.py`:

- `default_constructor_layout()` define `bleed_default_mm=3` y `export_settings.bleed_mm=3`.
- `ensure_imposition_fields()` rellena `design.bleed_mm` desde `layout.bleed_default_mm` si falta.
- `ensure_export_fields()` asegura `export_settings.bleed_mm`.

## 4. Doble conteo detectado

El caso mas claro es:

```text
final_size_mm = 50 x 30
bleed_mm = 2
has_bleed = False
```

Comportamiento actual:

1. Upload persiste `design.width_mm=54`, `design.height_mm=34`, `design.bleed_mm=2`.
2. Repeat vuelve a sumar sangrado y genera `slot.w_mm=58`, `slot.h_mm=38`.
3. Output service trata `design.width_mm=54`, `design.height_mm=34` como `source_w_mm` / `source_h_mm`.
4. La salida legacy vuelve a construir caja de dibujo como `source + 2 * bleed`.

Por eso la cadena puede producir una caja efectiva de `58x38` para un trabajo cuyo trim real era `50x30` y cuya caja esperada con sangrado era `54x34`.

Tambien existe doble conteo cuando el PDF fisico trae sangrado en `MediaBox` o `BleedBox`: upload usa `MediaBox` como medida de diseno, y los motores pueden volver a sumar `design.bleed_mm`.

## 5. Contrato tecnico recomendado

Contrato definitivo:

```text
design.width_mm  = trim width, sin sangrado
design.height_mm = trim height, sin sangrado
design.bleed_mm  = sangrado recomendado por lado

slot.w_mm        = trim width colocado, sin sangrado
slot.h_mm        = trim height colocado, sin sangrado
slot.bleed_mm    = sangrado efectivo por lado del slot

caja_total_w     = slot.w_mm + 2 * slot.bleed_mm
caja_total_h     = slot.h_mm + 2 * slot.bleed_mm
```

Reglas derivadas:

- Canvas y validacion geometrica deben distinguir entre caja trim y caja total cuando el objetivo sea detectar solapes productivos.
- Preview/PDF deben dibujar contenido y marcas con trim explicito y sangrado explicito.
- Los motores no deben guardar `slot.w_mm` / `slot.h_mm` como caja total si el contrato final ya define esos campos como trim.
- `slot_box_final` debe quedar como compatibilidad historica o metadata de migracion, no como contrato principal para layouts nuevos.

## 6. Semantica propuesta para design.width_mm/design.height_mm

`design.width_mm` y `design.height_mm` deben representar siempre medida final de corte del diseno, sin sangrado.

Fuentes recomendadas por prioridad en upload nuevo:

1. `work.final_size_mm`, si existe y es valido.
2. `TrimBox` del PDF, si existe y es valido.
3. Una medida declarada manualmente por el usuario.
4. `MediaBox` solo como fallback cuando no exista mejor informacion.

Metadata recomendada para una fase posterior:

- `design.pdf_media_box_mm`
- `design.pdf_trim_box_mm`
- `design.pdf_bleed_box_mm`
- `design.size_semantics`, por ejemplo `"trim"` para layouts nuevos.

No conviene agregar todos esos campos en la primera correccion si el objetivo es un cambio minimo. Pero el contrato deberia reservarlos como salida natural de una normalizacion posterior.

## 7. Semantica propuesta para slot.w_mm/slot.h_mm

`slot.w_mm` y `slot.h_mm` deben representar medida final de corte colocada en el pliego, sin sangrado.

Consecuencias:

- Un diseno trim `50x30` con `slot.bleed_mm=2` deberia guardar `slot.w_mm=50`, `slot.h_mm=30`.
- La caja total para packing, preview, solapes productivos y PDF se calcula como `54x34`.
- Si el slot esta rotado 90/270, la semantica debe seguir siendo trim en coordenadas del slot colocado. La caja total rotada debe derivarse de trim y bleed, no de una mezcla de campos.

Compatibilidad:

- Layouts historicos generados por repeat/nesting pueden tener `slot.w_mm` / `slot.h_mm` como caja total. Deben reconocerse mediante `slot_box_final`, una bandera de version de contrato, o una funcion normalizadora de lectura.

## 8. Semantica propuesta para bleed_mm

`bleed_mm` debe significar siempre sangrado adicional por lado.

Campos:

- `design.bleed_mm`: recomendacion por diseno.
- `slot.bleed_mm`: sangrado efectivo persistido en el slot.
- `layout.bleed_default_mm`: default global para inicializar disenos o slots nuevos.
- `export_settings.bleed_mm`: default global de salida, no deberia sobrescribir silenciosamente slots ya definidos salvo que el usuario lo pida.
- `design_export[ref].bleed_mm`: override de salida por diseno.
- `slot.export_overrides.bleed_mm`: confirmacion explicita de override por slot.

Regla critica: ningun campo de dimension debe venir ya expandido por bleed si tambien se persiste `bleed_mm`.

## 9. Precedencia recomendada de sangrado

Precedencia recomendada para calcular el sangrado efectivo de salida:

1. `slot.bleed_mm` si `slot.export_overrides.bleed_mm` es verdadero o si el slot proviene de un motor nuevo que persiste contrato versionado.
2. `design_export[design_ref].bleed_mm` si existe como override explicito de salida.
3. `design.bleed_mm` si existe.
4. `work.default_bleed_mm` si el slot conserva `logical_work_id`.
5. `export_settings.bleed_mm` como default de salida global.
6. `layout.bleed_default_mm`.
7. `0`.

La precedencia actual de `_sanitize_slot_bleed()` en `services/editor_offset_output_service.py` prioriza `design_export` y `export_settings` antes que `slot.bleed_mm` cuando no hay override de slot. Eso es compatible con una UI de exportacion, pero es riesgoso para contrato geometrico porque puede hacer que la salida use un bleed distinto al que el motor uso para crear el slot.

Recomendacion: separar dos conceptos en fases futuras:

- `slot.bleed_mm`: geometria productiva del slot.
- `export bleed override`: ajuste de salida que debe recalcular caja total, marcas y validaciones de forma explicita.

## 10. Compatibilidad con trabajos historicos

No se debe reinterpretar automaticamente todo `layout_constructor.json` existente como contrato nuevo.

Riesgos historicos:

- Uploads anteriores pueden tener `design.width_mm` / `design.height_mm` ya expandidos.
- Slots existentes de repeat/nesting pueden tener `slot.w_mm` / `slot.h_mm` como caja total.
- `slot_box_final=True` puede estar preservando una salida que hoy depende de esa caja total.
- Operadores pueden haber compensado manualmente doble sangrado con cambios de bleed o dimensiones.

Estrategia recomendada:

- Para nuevos uploads, persistir trim y dejar evidencia de semantica nueva con una marca versionada en una fase posterior.
- Para layouts existentes sin marca, mantener comportamiento legacy por defecto.
- Para jobs que se guarden despues de una migracion explicita, normalizar con una herramienta separada y reversible.
- No cambiar `slot_box_final` en la primera correccion.
- No tocar `montaje_offset_inteligente.py` en la primera correccion.

Posible bandera futura:

```json
{
  "geometry_contract": "trim_plus_bleed_v1"
}
```

## 11. Primera correccion productiva recomendada

Primera correccion: modificar solo upload para que los nuevos disenos persistan `design.width_mm` / `design.height_mm` como trim.

Cambio minimo recomendado:

- En `services/editor_offset_uploads.py`, cuando exista `work.final_size_mm`, guardar esa medida tal cual.
- Si `related_work.has_bleed` es falso, no sumar `2 * bleed_mm` a `design.width_mm` / `design.height_mm`.
- Mantener `design.bleed_mm` con el valor recomendado del work o del layout.
- Para PDFs sin `work.final_size_mm`, si existe `TrimBox` valido, usarlo como trim en una fase ideal; si se quiere mantener el primer cambio aun mas pequeno, dejar MediaBox para ese caso y corregir solo el camino de `work.final_size_mm`.

Por que esta capa primero:

- Es la fuente mas temprana del dato ambiguo.
- Reduce el doble conteo para jobs nuevos con work definido sin tocar motores ni PDF final.
- Tiene cobertura directa en `tests/test_editor_offset_characterization.py`.
- Evita cambiar `step_repeat_pro_engine.py`, `nesting_pro_engine.py`, `services/editor_offset_output_service.py` y `montaje_offset_inteligente.py` en la misma fase.

Efecto esperado de esa primera correccion:

- Upload de final `50x30` con bleed `2` debe persistir `design.width_mm=50`, `design.height_mm=30`, `design.bleed_mm=2`.
- Repeat actual seguira generando slot `54x34`, que todavia es semantica legacy de caja total, pero ya no sera `58x38`.
- Output actual con `slot_box_final=True` y `source_w_mm=50`, `source_h_mm=30` podra producir caja de dibujo `54x34`.

Esta primera correccion no completa el contrato ideal de `slot.w_mm` / `slot.h_mm` como trim. Solo elimina el doble conteo mas temprano y deja preparada la fase de motores.

## 12. Archivos que habria que tocar

Primera fase recomendada:

- `services/editor_offset_uploads.py`
- `tests/test_editor_offset_characterization.py`

Fases posteriores:

- `engines/step_repeat_pro_engine.py`
- `engines/nesting_pro_engine.py`
- `services/editor_offset_output_service.py`
- `services/editor_offset_output_contract.py`
- `services/editor_offset_layout_defaults.py`
- `montaje_offset_inteligente.py`
- tests de caracterizacion y contrato relacionados

No tocar en la primera fase:

- `montaje_offset_inteligente.py`
- `services/editor_offset_output_service.py`
- `engines/step_repeat_pro_engine.py`
- `engines/nesting_pro_engine.py`
- `slot_box_final`
- rutas publicas
- PDF final

## 13. Tests que deberian actualizarse o agregarse

Cuando se corrija upload:

- Cambiar `test_editor_offset_upload_current_behavior_expands_work_final_size_without_bleed` para esperar `50x30` en vez de `54x34`.
- Mantener o agregar un test que confirme `design.bleed_mm=2`.
- Decidir si `test_editor_offset_upload_characterizes_current_behavior_uses_pdf_mediabox` sigue documentando legacy o pasa a contrato esperado con `TrimBox`. Si la primera correccion solo toca `work.final_size_mm`, este test no deberia cambiar todavia.

Cuando se corrijan motores al contrato ideal:

- Cambiar `test_repeat_current_behavior_expands_trim_design_size_by_bleed` para esperar `slot.w_mm=50`, `slot.h_mm=30`, `slot.bleed_mm=2`.
- Cambiar `test_repeat_characterizes_current_behavior_double_counts_bleed_for_expanded_design_size` para validar que no se vuelve a sumar bleed sobre dimensiones ya normalizadas, o convertirlo en test de compatibilidad legacy.
- Agregar tests equivalentes para `engines/nesting_pro_engine.py`.

Cuando se corrija output:

- Cambiar `test_output_service_characterizes_current_behavior_with_expanded_design_size` para que `posiciones_manual` transporte trim y bleed sin duplicacion.
- Agregar tests de precedencia de bleed: slot override, `design_export`, `design.bleed_mm`, `work.default_bleed_mm`, `export_settings`, `layout.bleed_default_mm`.
- Agregar test de crop marks sobre trim real.

Cuando se corrija PDF:

- Agregar test con PDF que tenga `MediaBox`, `TrimBox` y `BleedBox`.
- Validar que las marcas de corte caen sobre `TrimBox` / trim esperado.
- Validar que no se agrega sangrado espejo si el flujo decide usar sangrado existente del PDF.

## 14. Riesgos

Riesgos de corregir upload:

- Jobs nuevos quedaran con dimensiones distintas a jobs historicos.
- Si un flujo sin work depende de `MediaBox`, seguira ambiguo hasta una fase posterior.
- Si la UI muestra `design.width_mm` como caja total, habra que ajustar copy o documentacion de usuario en una fase posterior.

Riesgos de corregir motores:

- Cambia packing, colisiones, ocupacion de pliego y cantidad de formas que entran.
- Puede romper tests actuales que asumen slots como caja total.
- Requiere actualizar canvas, validacion geometrica y output para usar caja total derivada.

Riesgos de corregir output/PDF:

- Alto impacto en preview, PDF final, CTP, marcas de corte, rotacion y doble cara.
- `montaje_offset_inteligente.py` es legacy compartido; tocarlo sin fase separada puede afectar otros flujos.

Riesgos de compatibilidad:

- Layouts historicos no tienen un campo confiable que indique si dimensiones son trim o caja expandida.
- `slot_box_final` ayuda, pero no reemplaza un contrato versionado.

## 15. Prompt exacto para la siguiente fase

```text
Implementa la primera correccion productiva segura del contrato de sangrado del Editor Offset Visual.

Alcance estricto:
- Corrige solo el camino de upload con work.final_size_mm en services/editor_offset_uploads.py.
- Cuando work.final_size_mm existe, persiste design.width_mm/design.height_mm como medida final de corte, sin sumar 2 * bleed_mm.
- Mantiene design.bleed_mm como sangrado recomendado por lado.
- No cambies motores.
- No cambies output_service.
- No cambies montaje_offset_inteligente.py.
- No cambies slot_box_final.
- No cambies PDF final.
- No hagas refactor.
- No hagas commit.
- No instales dependencias.

Actualiza solo los tests necesarios:
- tests/test_editor_offset_characterization.py

Cambios esperados en tests:
- El test de upload con final_size_mm=[50, 30], default_bleed_mm=2 y has_bleed=False debe pasar de caracterizar 54x34 como current behavior a validar 50x30 como contrato esperado.
- Debe seguir validando design.bleed_mm=2.
- No cambies todavia el test de MediaBox/TrimBox si no vas a corregir ese camino.
- No cambies tests de repeat ni output en esta fase.

Validacion:
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q
git diff --check

Al final reporta:
1. Archivos modificados.
2. Que comportamiento cambio.
3. Que comportamiento legacy queda igual.
4. Tests ejecutados y resultado.
5. Confirmacion de que no tocaste motores, output/PDF ni montaje_offset_inteligente.py.
```
