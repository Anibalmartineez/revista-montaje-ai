# Auditoria canvas/output bleed - Editor Offset Visual

## 1. Resumen ejecutivo

Auditoria estatica del flujo de sangrado efectivo entre Canvas, Output Panel, Preview y PDF del Editor Offset Visual.

Conclusion principal: despues de corregir Upload y Step & Repeat, todavia hay riesgo confirmado de que Preview/PDF usen `export_settings.bleed_mm = 3` en vez de `slot.bleed_mm = 1`, salvo que el slot tenga `slot.export_overrides.bleed_mm = true`.

El riesgo esta principalmente en `services/editor_offset_output_service.py`, no en `output_panel.js`. El panel de salida guarda el layout completo con `export_settings.bleed_mm`; el backend decide la precedencia real. La funcion `_sanitize_slot_bleed()` actualmente evalua `design_export` y `export_settings` antes que `slot.bleed_mm` cuando no existe override explicito del slot.

Tambien hay un segundo riesgo, independiente pero relacionado: el canvas renderiza solo `slot.w_mm` / `slot.h_mm` y no dibuja una caja total de bleed. Despues del fix de Step & Repeat, eso significa que el canvas muestra la caja trim, no la caja productiva `trim + 2 * bleed`.

## 2. Estado actual despues de Upload y Step Repeat

Estado confirmado por documentacion y tests recientes:

- Upload con `work.final_size_mm` ya persiste `design.width_mm` / `design.height_mm` como medida final de corte, sin sumar `2 * bleed_mm`.
- Step & Repeat ya persiste `slot.w_mm` / `slot.h_mm` como trim, no como caja total con sangrado.
- Step & Repeat conserva `slot.bleed_mm` como sangrado por lado.
- La caja productiva esperada queda derivada: `slot.w_mm + 2 * slot.bleed_mm` por `slot.h_mm + 2 * slot.bleed_mm`.

Superficies que no fueron corregidas todavia:

- `services/editor_offset_output_service.py`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`
- Canvas/frontend para visualizar caja total de bleed
- Upload sin `work.final_size_mm`, que sigue caracterizado con `MediaBox`

## 3. Flujo de bleed en Canvas

Evidencia revisada:

- `static/js/editor_offset_visual/core/geometry.js`
- `static/js/editor_offset_visual/renderer_canvas.js`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/manual_tools.js`

Hechos confirmados:

- `geometry.getSlotRenderBox(slot)` devuelve `w: slot.w_mm`, `h: slot.h_mm`.
- `renderer_canvas.renderSheetSurface()` usa esa caja para `slotEl.style.width` y `slotEl.style.height`.
- `geometry.getEffectiveSlotBox()` y `getSimpleSlotBox()` usan `slot.w_mm` / `slot.h_mm`.
- No se encontro en el renderer activo una capa visible que dibuje `slot.bleed_mm` como margen adicional.
- `layout.bleed_default_mm` no participa en `getSlotRenderBox()` ni en el render principal del slot.

Respuestas directas:

1. En el canvas no se usa un valor de bleed para dibujar la caja principal.
2. El canvas no usa `slot.bleed_mm` ni `layout.bleed_default_mm` para dimensionar el slot.
3. Despues del fix de Step & Repeat, el canvas muestra caja trim. No muestra caja total con bleed ni ambas cajas.

Riesgo:

- Si un slot tiene `w_mm=50`, `h_mm=30`, `bleed_mm=1`, el canvas mostrara `50x30`, no `52x32`.
- Las herramientas manuales de alineacion/distribucion basadas en `getEffectiveSlotBox()` tambien operan sobre `w_mm/h_mm` sin bleed productivo.
- Esto puede ocultar solapes productivos si dos trims no se solapan pero sus sangrados si.

## 4. Flujo de bleed en Output Panel

Evidencia revisada:

- `static/js/editor_offset_visual/output_panel.js`
- `static/js/editor_offset_visual.js`

Hechos confirmados:

- `output_panel.requestPreview()` y `requestPdf()` llaman `ctx.saveLayout()` antes de pedir preview/PDF.
- `saveLayout()` usa `layoutToJson()`.
- `layoutToJson()` llama `applyGlobalExportSettings(false)`.
- `applyGlobalExportSettings()` lee `#export-bleed-mm` y escribe `state.layout.export_settings.bleed_mm`.
- `ensureExportDefaults()` mantiene `export_settings.bleed_mm`; los defaults lo inicializan en `3`.
- `renderExportSettings()` muestra el valor global de export en el input `export-bleed-mm`.
- El panel por diseno puede escribir `state.layout.design_export[designRef].bleed_mm`.

Respuesta directa:

- Si el input global de export sigue en `3`, `output_panel.js` guarda/envia `export_settings.bleed_mm = 3` dentro del layout antes de preview/PDF.
- Esto no significa por si solo que Preview/PDF deban usar 3; la decision final ocurre en `services/editor_offset_output_service.py`.

Observacion importante:

- `output_panel.js` no envia un payload separado de bleed. Envia el layout persistido. Por tanto, el problema no es que el panel llame a un endpoint con `bleed=3`, sino que guarda `export_settings.bleed_mm=3` y el backend lo prioriza antes que `slot.bleed_mm` en algunos casos.

## 5. Flujo de bleed en Output Service

Evidencia revisada:

- `services/editor_offset_output_service.py`

Precedencia actual confirmada en `_sanitize_slot_bleed()`:

1. Si `_slot_has_export_override(slot, "bleed_mm")` es verdadero, usa `slot.bleed_mm`.
2. Si existe `design_export[design_ref].bleed_mm`, usa ese valor.
3. Si existe `export_settings.bleed_mm`, usa ese valor.
4. Si no hubo valores anteriores, usa `slot.bleed_mm`.
5. Si no hay slot bleed, usa `work.default_bleed_mm`.
6. Si no hay work bleed, usa `layout.bleed_default_mm`.

Hechos confirmados:

- `_positions_for_face()` llama `_sanitize_slot_bleed(..., prefer_slot=engine_name == "repeat")`.
- El parametro `prefer_slot` existe pero no se usa dentro de `_sanitize_slot_bleed()`.
- Por eso, para slots repeat sin override explicito, `export_settings.bleed_mm=3` puede ganar sobre `slot.bleed_mm=1`.
- `applySlotForm()` en `static/js/editor_offset_visual.js` si marca `slot.export_overrides.bleed_mm = true` cuando el usuario edita el formulario de slot.

Respuesta directa:

- Si el usuario edita el slot desde el formulario y pone `1 mm`, `applySlotForm()` guarda `slot.bleed_mm=1` y activa `slot.export_overrides.bleed_mm=true`. En ese caso, output service deberia respetar `slot.bleed_mm`.
- Si el slot viene del motor Step & Repeat con `slot.bleed_mm=1`, pero no tiene `export_overrides.bleed_mm=true`, entonces `export_settings.bleed_mm=3` puede sobrescribirlo en output service.

## 6. Flujo de bleed en Preview/PDF

Evidencia revisada:

- `services/editor_offset_output_service.py`
- `montaje_offset_inteligente.py`

Hechos confirmados:

- Preview/PDF cargan layout persistido y output service transforma `slots[]` en `posiciones_manual`.
- `posiciones_manual[].bleed_mm` sale de `_sanitize_slot_bleed()`.
- `montaje_offset_inteligente.py` usa `pos.get("bleed_mm", sangrado)` como `bleed_effective`.
- La salida legacy calcula `source_draw_w_mm = source_w_mm + 2 * bleed_effective` y `source_draw_h_mm = source_h_mm + 2 * bleed_effective`.
- Las marcas de corte usan `bleed_eff` derivado del mismo flujo.

Respuesta directa:

- Preview/PDF reciben el bleed efectivo desde `posiciones_manual[].bleed_mm`.
- Ese valor puede venir de `slot.bleed_mm` o puede venir del default global `export_settings.bleed_mm=3`, dependiendo de la precedencia descrita arriba.

Riesgo adicional despues del fix de Step & Repeat:

- `_resolve_slot_box_final()` devuelve `True` para repeat no rotado si el slot no declara `slot_box_final`.
- Con slots nuevos de Step & Repeat, `slot.w_mm/h_mm` ahora son trim.
- La capa legacy todavia trata `slot_box_final=True` como caja externa final, lo que puede producir calculos incorrectos de caja/dibujo si output service no se adapta al contrato nuevo.

## 7. Donde aparece el default 3 mm

Fuentes confirmadas del default `3 mm`:

- `static/js/editor_offset_visual.js`: si `state.layout.bleed_default_mm` es `undefined`, lo inicializa en `3`.
- `services/editor_offset_layout_defaults.py`: `default_constructor_layout()` define `bleed_default_mm=3`.
- `services/editor_offset_layout_defaults.py`: `default_constructor_layout()` define `export_settings.bleed_mm=3`.
- `services/editor_offset_layout_defaults.py`: `ensure_export_fields()` rellena `export_settings.bleed_mm=3` si falta.
- `static/js/editor_offset_visual.js`: `applyGlobalExportSettings()` usa `state.layout.export_settings.bleed_mm ?? 3` como fallback del input global.
- `services/editor_offset_output_service.py`: si no puede convertir el bleed efectivo, vuelve a `bleed_default`.
- `montaje_offset_inteligente.py`: `MontajeConfig.sangrado` y parametros legacy tienen default cercano a `3` en varias rutas antiguas.

Confirmacion:

- Si el layout conserva `export_settings.bleed_mm=3`, output service puede usar ese valor aunque el slot tenga `slot.bleed_mm=1`, siempre que el slot no tenga override explicito.

## 8. Riesgo de que slot.bleed_mm sea ignorado

Riesgo confirmado.

Caso concreto:

```json
{
  "imposition_engine": "repeat",
  "export_settings": {"bleed_mm": 3},
  "design_export": {},
  "slots": [
    {
      "w_mm": 50,
      "h_mm": 30,
      "bleed_mm": 1,
      "design_ref": "file0"
    }
  ]
}
```

Si el slot no contiene:

```json
{"export_overrides": {"bleed_mm": true}}
```

entonces `_sanitize_slot_bleed()` puede elegir `export_settings.bleed_mm=3` antes de llegar a `slot.bleed_mm=1`.

Esto afecta especialmente a slots generados por motor, porque Step & Repeat persiste `slot.bleed_mm` pero no marca override manual.

## 9. Riesgo de desalineacion en PDF

Riesgo confirmado por lectura estatica.

Hay dos causas:

1. Bleed efectivo equivocado:
   - Si output service elige `3 mm` en vez de `slot.bleed_mm=1`, `montaje_offset_inteligente.py` construye `source_draw_w/h` con `+ 6 mm` en vez de `+ 2 mm`.

2. Semantica stale de `slot_box_final` para repeat:
   - Despues del fix de Step & Repeat, `slot.w_mm/h_mm` son trim.
   - Output service todavia puede resolver `slot_box_final=True` para repeat.
   - La capa legacy interpreta `slot_box_final=True` como caja externa final, no como trim.

Consecuencia probable:

- Preview/PDF pueden quedar mal ubicados o con marcas de corte sobre una caja incorrecta.
- Si el slot fue generado con bleed `1 mm` y output usa `3 mm`, la caja productiva esperada `52x32` podria pasar a calcularse como `56x36` en partes del flujo.
- Si ademas `slot_box_final=True` se aplica a un slot que ahora es trim, el PDF puede sufrir una segunda distorsion de caja.

No se ejecuto una prueba visual/PDF en esta auditoria, por lo que la magnitud exacta del desplazamiento queda pendiente de validacion automatizada o visual.

## 10. Primera correccion recomendada

Primera correccion recomendada: `services/editor_offset_output_service.py`.

Cambio minimo propuesto:

- Hacer que `_sanitize_slot_bleed()` respete `prefer_slot=True`.
- Para `engine_name == "repeat"`, priorizar `slot.bleed_mm` antes que `design_export.bleed_mm` y `export_settings.bleed_mm`, salvo que haya una decision explicita distinta.
- Agregar tests focalizados para el caso:

```text
slot.bleed_mm = 1
export_settings.bleed_mm = 3
imposition_engine = repeat
```

Resultado esperado:

```text
posiciones_manual[].bleed_mm = 1
```

Por que no empezar por canvas:

- Canvas no decide el bleed efectivo de Preview/PDF.
- Agregar overlay de bleed al canvas es importante, pero no evita que PDF use `3 mm`.

Por que no empezar por output_panel:

- Output panel solo persiste `export_settings.bleed_mm`.
- El problema critico es que output service lo prioriza antes de `slot.bleed_mm` en slots sin override.

Nota SAFE:

- Esta correccion de prioridad de bleed no debe mezclarse con la correccion de `slot_box_final`.
- Sin embargo, inmediatamente despues conviene auditar/corregir `slot_box_final` para slots repeat nuevos que ya guardan trim.

## 11. Archivos que habria que tocar

Primera fase recomendada:

- `services/editor_offset_output_service.py`
- `tests/test_editor_offset_characterization.py`

Fase posterior de canvas:

- `static/js/editor_offset_visual/core/geometry.js`
- `static/js/editor_offset_visual/renderer_canvas.js`
- `static/js/editor_offset_visual/manual_tools.js`
- tests Playwright o unitarios JS si existen para geometria

Fase posterior de `slot_box_final` / salida:

- `services/editor_offset_output_service.py`
- `montaje_offset_inteligente.py` solo si no alcanza con adaptar posiciones manuales
- tests de output con `render_fn` fake

No tocar primero:

- `output_panel.js`, salvo que se decida cambiar la semantica del control global de export.
- `montaje_offset_inteligente.py`, por ser salida legacy compartida.
- PDF final real sin caracterizacion previa.

## 12. Tests necesarios

Tests minimos recomendados antes del fix:

1. Output service respeta `slot.bleed_mm` para repeat:
   - Layout repeat con `slot.bleed_mm=1`.
   - `export_settings.bleed_mm=3`.
   - Sin `slot.export_overrides`.
   - Esperar `posiciones_manual[0].bleed_mm == 1`.

2. Output service mantiene override explicito por slot:
   - `slot.export_overrides.bleed_mm=true`.
   - `slot.bleed_mm=1`.
   - `export_settings.bleed_mm=3`.
   - Esperar `1`.

3. Output service caracteriza `design_export`:
   - Decidir si `design_export.bleed_mm` debe ganar sobre slot para repeat o no.
   - Si queda como override explicito de salida, documentar el orden.

4. Canvas muestra trim y no bleed:
   - Test o Playwright que confirme dimensiones visuales actuales.
   - Este test puede quedar como caracterizacion antes de agregar overlay.

5. PDF/preview con bleed `1` vs global `3`:
   - Usar `render_fn` fake para capturar `config.posiciones_manual`.
   - No hace falta renderizar PDF real en la primera fase.

## 13. Prompt exacto para la siguiente fase

```text
Implementa la correccion minima para que Preview/PDF del Editor Offset Visual respeten slot.bleed_mm en slots Step & Repeat.

Antes de modificar:
1. Ejecuta git status --short --branch.
2. Si estoy en main, detente.
3. Si hay cambios pendientes, detente y avisame.
4. No hagas commit.

Alcance estricto:
- Modifica solo services/editor_offset_output_service.py y tests focalizados.
- No modifiques canvas.
- No modifiques output_panel.js.
- No modifiques motores.
- No modifiques upload.
- No modifiques montaje_offset_inteligente.py.
- No modifiques PDF final directamente.
- No modifiques slot_box_final en esta fase.
- No instales dependencias.

Objetivo:
- Cuando imposition_engine == "repeat", _sanitize_slot_bleed debe priorizar slot.bleed_mm si existe, aun cuando export_settings.bleed_mm sea 3.
- Mantener slot.export_overrides.bleed_mm como override explicito.
- Agregar test con slot.bleed_mm=1 y export_settings.bleed_mm=3 que capture posiciones_manual y espere bleed_mm=1.

Validacion:
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q
.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q
git diff --check

Al final reporta:
1. Archivos modificados.
2. Que precedencia de bleed cambio.
3. Que se mantiene legacy.
4. Tests ejecutados y resultado.
5. Confirmacion de que no tocaste canvas, output_panel, motores, upload, montaje_offset_inteligente.py ni PDF final.
6. Confirmacion de que no hiciste commit.
```
