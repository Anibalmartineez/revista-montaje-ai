# Auditoría técnica: sangrado, medidas finales y doble conteo - Editor Offset Visual

## 1. Resumen ejecutivo

Auditoría técnica de solo lectura sobre el flujo de sangrado, medidas finales y posible doble conteo del Editor Offset Visual.

Archivos revisados durante la auditoría:

- `services/editor_offset_uploads.py`
- `services/editor_offset_layout_defaults.py`
- `services/editor_offset_imposition_service.py`
- `services/editor_offset_output_service.py`
- `services/editor_offset_output_contract.py`
- `engines/step_repeat_pro_engine.py`
- `engines/nesting_pro_engine.py`
- `montaje_offset_inteligente.py`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/renderer_canvas.js`
- `static/js/editor_offset_visual/output_panel.js`
- `static/js/editor_offset_visual/core/geometry.js`
- `tests/test_editor_offset_characterization.py`
- `tests/test_editor_offset_output_contract.py`
- `tests/test_step_repeat_pro_engine.py`

Conclusión principal: el flujo actual no tiene una semántica única para sangrado. `design.width_mm/height_mm`, `slot.w_mm/h_mm` y las cajas usadas en salida cambian de significado según upload, motor, `has_bleed`, `imposition_engine`, `export_settings`, `design_export` y `slot_box_final`.

La causa más probable del doble conteo es esta cadena:

1. `upload` puede guardar `design.width_mm/height_mm` ya expandidos con `2 * bleed_mm`.
2. `step_repeat_pro_engine.py` y `nesting_pro_engine.py` vuelven a sumar `2 * bleed_mm`.
3. `editor_offset_output_service.py` trata `design.width_mm/height_mm` como si fueran trim.
4. `montaje_offset_inteligente.py` vuelve a construir `source_draw_w/h = source_w/h + 2 * bleed`.

Riesgo: alto para producción. Las marcas de corte pueden caer sobre una caja ya expandida, no sobre la medida final real.

## 2. Flujo actual del sangrado

### Upload

Evidencia principal: `services/editor_offset_uploads.py`.

- `pdf_page_size_mm()` lee el tamaño del PDF desde `page.mediabox.width` y `page.mediabox.height`.
- No usa `TrimBox`, `BleedBox` ni `CropBox` para calcular `design.width_mm/height_mm`.
- Si no hay `work_id`, el tamaño persistido del diseño sale del `MediaBox`.
- Si hay `work_id` y el trabajo tiene `final_size_mm`, el tamaño leído desde `MediaBox` se reemplaza por `final_size_mm`.
- Si además `related_work.has_bleed` es falso, se suma `2 * bleed_mm` a ancho y alto.
- `design.bleed_mm` se guarda desde `work.default_bleed_mm` si existe, o desde `layout.bleed_default_mm`.

Flujo aproximado:

```text
PDF upload
  -> PyPDF2 PdfReader
  -> page.mediabox.width / page.mediabox.height
  -> width_mm / height_mm
  -> si work.final_size_mm existe: width_mm / height_mm = final_size_mm
  -> si work.has_bleed es false: width_mm += 2 * bleed_mm; height_mm += 2 * bleed_mm
  -> guardar design.width_mm / design.height_mm / design.bleed_mm
```

### Defaults

Evidencia principal: `services/editor_offset_layout_defaults.py`.

- `default_constructor_layout()` define `bleed_default_mm = 3`.
- También define `export_settings = {"bleed_mm": 3, "crop_marks": True, "output_mode": "raster"}`.
- `ensure_imposition_fields()` rellena `design.bleed_mm` desde `layout.bleed_default_mm` si falta.
- `ensure_export_fields()` rellena `export_settings.bleed_mm` y `crop_marks` si faltan.

### Frontend y canvas

Evidencia principal:

- `static/js/editor_offset_visual/core/geometry.js`
- `static/js/editor_offset_visual/renderer_canvas.js`
- `static/js/editor_offset_visual.js`

El canvas usa directamente `slot.w_mm` y `slot.h_mm`:

- `getSlotRenderBox()` devuelve `w: slot.w_mm`, `h: slot.h_mm`.
- `renderer_canvas.js` aplica `style.width` y `style.height` desde esa caja.
- No se encontró un overlay técnico activo de bleed separado del slot en el renderer moderno.

Conclusión: si el motor ya creó un slot con sangrado incluido, el canvas muestra el slot agrandado como caja real, no como trim más overlay de bleed.

### Output panel

Evidencia principal: `static/js/editor_offset_visual/output_panel.js`.

- Preview y PDF guardan el layout y luego llaman endpoints de salida.
- El panel no redefine semántica de sangrado.
- Los controles de exportación permiten configurar `export_settings.bleed_mm`, `design_export[ref].bleed_mm` y crop marks.

## 3. Dónde se suma sangrado actualmente

### Upload

Archivo: `services/editor_offset_uploads.py`.

Cuando hay `work.final_size_mm` y `related_work.has_bleed` es falso:

```text
width_mm += 2 * bleed_mm
height_mm += 2 * bleed_mm
```

Esto significa que `design.width_mm/height_mm` puede quedar guardado como medida final más sangrado, aunque el campo no lo declare explícitamente.

### Step & Repeat PRO

Archivo: `engines/step_repeat_pro_engine.py`.

Función relevante: `design_dimensions()`.

Comportamiento:

```text
bleed = design.bleed_mm o layout.bleed_default_mm
width = design.width_mm
height = design.height_mm
return width + 2 * bleed, height + 2 * bleed, bleed
```

El motor usa ese resultado para crear `slot.w_mm` y `slot.h_mm`. Por tanto, en repeat, los slots generados suelen tener sangrado incluido.

### Nesting PRO

Archivo: `engines/nesting_pro_engine.py`.

Clase relevante: `NestingPiece`.

Propiedad relevante: `padded_size`.

Comportamiento:

```text
padded_size = width_mm + 2 * bleed_mm, height_mm + 2 * bleed_mm
```

Luego `compute_nesting()` genera slots con `w_mm/h_mm` usando ese tamaño acolchado. Por tanto, nesting también puede crear slots con sangrado incluido.

### Output service

Archivo: `services/editor_offset_output_service.py`.

Zonas relevantes:

- `_sanitize_slot_bleed()`
- `_design_trim_size()`
- `_resolve_slot_box_final()`
- `_positions_for_face()`

Comportamiento clave:

- `_design_trim_size()` devuelve `design.width_mm/height_mm` como si fueran tamaño trim.
- `_resolve_slot_box_final()` calcula:

```text
final_w = design_w + 2 * bleed_mm
final_h = design_h + 2 * bleed_mm
```

- `_positions_for_face()` también calcula:

```text
source_draw_w = source_w_mm + 2 * bleed_val
source_draw_h = source_h_mm + 2 * bleed_val
```

### PDF final

Archivo: `montaje_offset_inteligente.py`.

Zonas relevantes:

- `_pdf_a_imagen_con_sangrado()`
- `_render_vector_hybrid_bleed()`
- rama manual de `realizar_montaje_inteligente()`
- bloque final de dibujo con ReportLab
- `draw_cutmarks_around_form_reportlab()`

Comportamiento clave:

- `_pdf_a_imagen_con_sangrado()` puede rasterizar usando `TrimBox` si se pide `usar_trimbox=True` y luego añadir un borde de sangrado espejado.
- En el render final se calcula:

```text
source_draw_w_mm = source_w_mm + 2 * bleed_effective
source_draw_h_mm = source_h_mm + 2 * bleed_effective
```

- Si `slot_box_final` está activo, se puede reemplazar el tamaño dibujado por `slot_w_mm/slot_h_mm`.
- Las marcas de corte se dibujan alrededor de un trim calculado, pero ese trim depende de si las cajas previas estaban limpias o ya expandidas.

## 4. Dónde puede duplicarse

### Caso 1: work con final_size_mm y has_bleed=False

Ejemplo:

```text
final_size_mm = [50, 30]
default_bleed_mm = 2
has_bleed = False
```

Flujo actual:

1. Upload guarda:

```text
design.width_mm = 50 + 2*2 = 54
design.height_mm = 30 + 2*2 = 34
design.bleed_mm = 2
```

2. Repeat toma `54x34` y vuelve a sumar bleed:

```text
slot.w_mm = 54 + 2*2 = 58
slot.h_mm = 34 + 2*2 = 38
```

3. Output service puede volver a tratar `design.width_mm/height_mm` como trim.

4. PDF final puede volver a construir caja de dibujo con:

```text
source_draw_w_mm = source_w_mm + 2 * bleed_effective
```

Resultado probable: sangrado duplicado o marcas sobre una caja equivocada.

Este caso está parcialmente caracterizado por `tests/test_editor_offset_characterization.py`, que espera que upload guarde `54x34` para final `50x30` con bleed `2`.

### Caso 2: PDF físico ya tiene sangrado en MediaBox

Si un PDF tiene:

```text
TrimBox = medida final
BleedBox / MediaBox = medida final + sangrado
```

El upload actual toma `MediaBox` como `design.width_mm/height_mm`.

Luego motores y salida pueden interpretarlo como trim y volver a sumar `bleed_mm`.

Resultado probable: doble sangrado aunque el PDF ya traiga sangrado físico.

### Caso 3: export_settings redefine bleed efectivo

`_sanitize_slot_bleed()` resuelve el bleed efectivo con esta prioridad aproximada:

1. override explícito del slot si `slot.export_overrides.bleed_mm` está activo.
2. `design_export[design_ref].bleed_mm`.
3. `export_settings.bleed_mm`.
4. `slot.bleed_mm`.
5. `work.default_bleed_mm`.
6. `layout.bleed_default_mm`.

Riesgo: un slot generado con `slot.bleed_mm` puede salir con otro bleed si `export_settings.bleed_mm` o `design_export` lo reemplazan.

### Caso 4: slot_box_final con diseño ya expandido

`_resolve_slot_box_final()` compara el slot contra:

```text
design.width_mm + 2 * bleed
design.height_mm + 2 * bleed
```

Si `design.width_mm/height_mm` ya incluyen sangrado, la heurística compara contra una caja doblemente expandida.

Resultado probable: clasificación incorrecta de `slot_box_final`, especialmente con rotaciones 90/270.

## 5. Qué campos tienen semántica ambigua

### design.width_mm / design.height_mm

Semántica actual: ambigua.

Puede representar:

- tamaño físico del PDF según `MediaBox`;
- `work.final_size_mm`;
- `work.final_size_mm + 2 * bleed_mm`;
- una medida editada manualmente por el usuario desde el panel de diseños.

No hay campo persistido que indique si representa trim, MediaBox, BleedBox o caja total.

### design.bleed_mm

Semántica actual: sangrado asociado al diseño para motores y defaults.

Riesgo: se guarda aunque `design.width_mm/height_mm` ya puedan incluir sangrado. Por tanto, el par `width_mm + bleed_mm` no garantiza una caja derivable sin doble conteo.

### slot.w_mm / slot.h_mm

Semántica actual: ambigua.

Puede representar:

- medida manual ingresada por usuario;
- caja total generada por repeat;
- caja total generada por nesting;
- caja visual del canvas;
- en algunos tramos de output, tamaño tratado como trim.

El canvas no distingue trim y bleed: dibuja `slot.w_mm/h_mm` directamente.

### slot.bleed_mm

Semántica actual: sangrado del slot, pero no siempre es la fuente final de verdad.

Puede ser reemplazado por:

- `design_export[design_ref].bleed_mm`;
- `export_settings.bleed_mm`;
- `work.default_bleed_mm`;
- `layout.bleed_default_mm`.

Si el usuario edita el slot desde el formulario, `applySlotForm()` marca `slot.export_overrides.bleed_mm = true`, lo que sí le da precedencia al slot.

### bleed_default_mm

Semántica actual: default global de layout.

Se usa como fallback en defaults, upload, motores y salida. Puede actuar como valor técnico de producción aunque el usuario no lo haya confirmado para un diseño específico.

### export_settings

Semántica actual: configuración global de salida.

`export_settings.bleed_mm` puede reemplazar el bleed efectivo de slots si no hay override específico.

### design_export

Semántica actual: override por diseño para salida.

Puede modificar bleed y crop marks en salida sin cambiar `design.bleed_mm` ni `slot.bleed_mm`.

### slot_box_final

Semántica actual: bandera o heurística para decidir si el slot ya representa caja final con bleed incluido.

Riesgo alto:

- si falta, se infiere;
- la inferencia usa `design.width_mm + 2*bleed`;
- si `design.width_mm` ya está expandido, la inferencia puede fallar;
- afecta rotación, `source_w_mm/source_h_mm`, preview y PDF final.

### crop_marks

Semántica actual: activa o desactiva marcas de corte por forma.

Las marcas se dibujan alrededor del trim calculado. Si el trim fue calculado desde una caja ya expandida, las marcas pueden quedar desplazadas hacia una caja incorrecta.

## 6. Riesgos para trabajos históricos

Cambiar de golpe la semántica rompería layouts existentes porque algunos jobs probablemente ya guardaron `design.width_mm/height_mm` expandidos.

Riesgos concretos:

- Jobs viejos pueden haber sido ajustados manualmente para compensar doble bleed.
- Slots repeat existentes pueden representar caja final con bleed, no trim.
- `slot_box_final` intenta preservar compatibilidad con ese historial.
- Uploads sin `work_id` dependen de `MediaBox`; si un PDF ya incluía sangrado, no hay dato persistido que indique si ese tamaño es trim o caja física.
- Marcas de corte históricas pueden haber sido generadas sobre cajas incorrectas sin que el contrato lo detecte.
- `export_settings.bleed_mm` puede haber sido usado por operadores como corrección manual para salidas antiguas.
- Corregir motores sin migración o compatibilidad podría achicar o agrandar montajes existentes.

Compatibilidades sensibles:

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`
- `designs[].width_mm`
- `designs[].height_mm`
- `designs[].bleed_mm`
- `slots[].w_mm`
- `slots[].h_mm`
- `slots[].bleed_mm`
- `slots[].slot_box_final`
- `export_settings`
- `design_export`

## 7. Tests existentes

### tests/test_editor_offset_characterization.py

Cobertura encontrada:

- Caracteriza upload con `work.final_size_mm`, `default_bleed_mm` y `has_bleed=False`.
- El test espera que un trabajo final `50x30` con bleed `2` persista diseño como `54x34`.
- Cubre endpoints de preview/PDF bloqueando layout inválido.
- Cubre algunos casos de rotación y `slot_box_final` en output service.

Limitación:

- No verifica que no se duplique sangrado después del upload.
- No verifica `TrimBox`, `BleedBox`, `CropBox` ni `MediaBox` con sangrado real.
- No verifica marcas de corte sobre trim real.

### tests/test_step_repeat_pro_engine.py

Cobertura encontrada:

- `test_repeat_respects_explicit_zero_bleed()` confirma que si `bleed_mm = 0`, los slots quedan sin expansión.
- Hay tests de distribución, spacing, zonas, rotación y contrato básico de slots.
- `test_all_generated_slots_include_required_contract_fields()` confirma que los slots generados incluyen `bleed_mm`.

Limitación:

- No hay test que pruebe diseño con `width_mm/height_mm` ya expandido y `bleed_mm > 0`.
- No hay test que asegure que repeat suma bleed exactamente una vez.
- No hay test que conecte upload -> repeat -> output.

### tests/test_editor_offset_output_contract.py

Cobertura encontrada:

- Valida estructura mínima:
  - refs de diseños;
  - ids de slots;
  - campos numéricos;
  - `face`;
  - `design_ref`;
  - duplicados.

Limitación:

- No valida semántica de sangrado.
- No valida relación entre `design.width_mm`, `slot.w_mm`, `slot.bleed_mm` y `export_settings.bleed_mm`.
- No bloquea doble conteo.
- No valida cajas PDF.
- No valida crop marks.

## 8. Tests faltantes recomendados

Tests de caracterización antes de corregir:

1. Upload con `work.final_size_mm` y `has_bleed=False`.
   - Confirmar comportamiento actual.
   - Documentar que hoy persiste medida expandida.

2. Upload con PDF cuyo `MediaBox` incluye sangrado.
   - Crear PDF de prueba con `MediaBox` mayor que trim esperado.
   - Confirmar que upload toma `MediaBox`.

3. Upload con `TrimBox` y `BleedBox`.
   - Confirmar que hoy no se usan para `design.width_mm/height_mm`.

4. Repeat con diseño trim `50x30` y bleed `2`.
   - Confirmar slot esperado si se decide contrato ideal: `54x34`.
   - Antes de corregir, caracterizar comportamiento actual.

5. Repeat con diseño ya expandido `54x34` y bleed `2`.
   - Confirmar si actualmente produce `58x38`.
   - Este test demostraría el doble conteo.

6. Output service con `design.width_mm/height_mm` expandido.
   - Verificar `posiciones_manual`.
   - Verificar `source_w_mm/source_h_mm`.
   - Verificar `slot_box_final`.

7. PDF final con crop marks.
   - Verificar que las marcas caen sobre trim real, no sobre caja con bleed.

8. Precedencia de bleed.
   - Comparar `slot.bleed_mm`, `design_export`, `export_settings`, `work.default_bleed_mm` y `bleed_default_mm`.

9. Test de compatibilidad histórica.
   - Layout con `slot_box_final=True`.
   - Confirmar que no se altera caja externa.

## 9. Plan SAFE de corrección por fases

### Fase 1: caracterizar el comportamiento actual

Agregar tests sin cambiar código productivo.

Objetivo:

- demostrar dónde se expande sangrado;
- confirmar si se duplica en upload -> motor -> output;
- proteger compatibilidad antes de tocar lógica.

Archivos probables:

- `tests/test_editor_offset_characterization.py`
- `tests/test_step_repeat_pro_engine.py`

### Fase 2: definir contrato explícito

Definir semántica deseada:

```text
slot.w_mm / slot.h_mm = medida final / corte
slot.bleed_mm = sangrado adicional por lado
w_total = w_mm + bleed_mm * 2
h_total = h_mm + bleed_mm * 2
```

Decidir semántica única para:

- `design.width_mm/height_mm`;
- `design.bleed_mm`;
- `slot.w_mm/h_mm`;
- `slot_box_final`.

### Fase 3: separar datos históricos de datos nuevos

Agregar estrategia compatible:

- migración suave;
- bandera explícita de semántica;
- normalización al cargar;
- o compatibilidad por heurística acotada.

No cambiar trabajos históricos sin una regla clara.

### Fase 4: corregir upload

Evitar que upload mezcle silenciosamente medida final y caja con sangrado.

Opciones a evaluar:

- persistir trim en `design.width_mm/height_mm`;
- persistir tamaño físico del PDF en campo separado;
- registrar `pdf_media_box_mm`, `pdf_trim_box_mm`, `pdf_bleed_box_mm`;
- usar `TrimBox` si existe;
- dejar `MediaBox` como metadata, no como medida final.

### Fase 5: corregir motores

Motores deben sumar bleed una sola vez y solo desde una fuente clara.

Repeat y nesting no deberían sumar `2*bleed` sobre una medida que ya está expandida.

### Fase 6: corregir output y marcas

Output debe recibir o calcular de forma inequívoca:

- trim;
- bleed por lado;
- caja total;
- caja de dibujo;
- caja de marcas.

Las marcas de corte deben caer sobre trim real.

### Fase 7: validación con PDFs reales

Validar manual y automáticamente con:

- PDF sin cajas especiales;
- PDF con `MediaBox` expandido;
- PDF con `TrimBox`;
- PDF con `BleedBox`;
- PDF ya sangrado;
- PDF sin sangrado.

## 10. Próximo prompt recomendado

```text
Agrega únicamente tests de caracterización para el flujo de sangrado del Editor Offset Visual, sin cambiar código productivo.

Cubre estos casos:
1. upload con work.final_size_mm, default_bleed_mm y has_bleed=False;
2. repeat con design.width_mm/height_mm ya expandido y bleed_mm > 0;
3. output service generando posiciones_manual con source_w_mm/source_h_mm y slot_box_final;
4. confirmación de que hoy no se usan TrimBox/BleedBox/CropBox para design.width_mm/design.height_mm.

No corrijas todavía la lógica.
No cambies PDF final.
No cambies upload.
No cambies motores.
No cambies contrato de sangrado.
No hagas commits.
```
