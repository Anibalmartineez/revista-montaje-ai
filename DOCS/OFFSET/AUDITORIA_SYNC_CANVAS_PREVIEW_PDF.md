# Auditoria tecnica: sincronizacion Canvas / Preview / PDF

## 1. Resumen ejecutivo

No se modifico codigo fuente durante la auditoria. Se ejecutaron solo los tests permitidos por el prompt original y pasaron:

- `tests/test_editor_offset_output_contract.py`: 7 passed
- `tests/test_editor_offset_characterization.py`: 11 passed
- `tests/test_step_repeat_pro_engine.py`: 14 passed

Problema mas probable: el preview PNG invierte el eje Y porque recibe coordenadas `x_mm/y_mm` con semantica de origen inferior izquierdo, pero las dibuja con PIL usando origen superior izquierdo. El canvas y el PDF final parecen usar origen inferior izquierdo con mas consistencia.

La segunda causa fuerte es de sangrado ambiguo y potencialmente duplicado: `design.width_mm/height_mm` a veces ya incluyen sangrado, pero motores y salida vuelven a sumar `bleed_mm`.

Riesgo para produccion: alto. Puede generar previews que no representan la salida real y PDFs con cajas de corte/sangrado incorrectas.

## 2. Flujo real detectado

### Carga inicial

- `services/editor_offset_http_service.py:32-40` arma el contexto con `editor_visual_context()`.
- `templates/editor_offset_visual.html:535-536` inyecta:
  - `window.INITIAL_LAYOUT_JSON`
  - `window.JOB_ID`
- `static/js/editor_offset_visual.js:117-142` parsea ese JSON y arma `state.layout`.

### Canvas

- `static/js/editor_offset_visual/renderer_canvas.js:197-200` renderiza slots con:
  - `style.left = x_mm`
  - `style.bottom = y_mm`
- Por tanto, el canvas usa origen inferior izquierdo.
- La rotacion se aplica con `transform: rotate(...)` en `renderer_canvas.js:201-204` y CSS.
- No se encontro un overlay activo separado de bleed en el renderer moderno; el slot visual se dibuja como caja. El rojo observado puede venir de seleccion, errores o estilos, no necesariamente de una caja tecnica de bleed.

### Save

- `layoutToJson()` esta en `static/js/editor_offset_visual.js:2254-2263`.
- `saveLayout()` envia `layout_json` a `/editor_offset/save`.
- `services/editor_offset_jobs.py:88-99` persiste `layout_constructor.json`.

### Preview

- Boton: `#btn-preview`.
- JS: `output_panel.requestPreview()`.
- Endpoint: `POST /editor_offset/preview/<job_id>`.
- El JS primero llama `saveLayout()`, pero luego el backend lee el layout persistido; no recibe layout vivo en el request.
- Backend: `services/editor_offset_http_service.py:148-163`.
- Generacion: `services/editor_offset_output_service.py` -> `montaje_offset_inteligente.py`.
- Preview usa `generar_preview_pliego()` con PIL.

### PDF final

- Boton: `#btn-pdf`.
- JS: `output_panel.requestPdf()`.
- Endpoint: `POST /editor_offset/generar_pdf/<job_id>`.
- Tambien guarda antes y luego backend lee layout persistido.
- Backend: `services/editor_offset_http_service.py:166-181`.
- Transformacion principal: `services/editor_offset_output_service.py:_positions_for_face()`.
- Render final: `montaje_offset_inteligente.py`, con ReportLab, cuyo origen es inferior izquierdo.

### Upload

- `services/editor_offset_uploads.py:14-22` lee tamano desde `MediaBox`.
- No usa de forma explicita `TrimBox`, `BleedBox` o `CropBox` para definir `design.width_mm/height_mm`.
- Si hay `work.final_size_mm` y `has_bleed=False`, suma `2 * bleed_mm` a ancho/alto. Esto esta caracterizado en `tests/test_editor_offset_characterization.py:123-165`.

### Bleed

- `design.width_mm/height_mm` no tiene una semantica unica en todo el flujo.
- Upload puede tomar tamano fisico del PDF desde `MediaBox`.
- Upload tambien puede expandir una medida final con `2 * bleed_mm`.
- Motores como repeat y nesting vuelven a sumar bleed.
- Output service puede volver a resolver cajas finales usando `design_w + 2 * bleed`.

### Marks

- Las marcas de corte en la salida final intentan dibujarse alrededor del trim.
- Si la caja base ya incluye sangrado pero se interpreta como trim, las marcas pueden caer sobre una caja incorrecta.

### CTP

- No se identifico a CTP como causa primaria del eje Y invertido.
- CTP sigue siendo superficie sensible porque comparte salida productiva y debe validarse antes de cambios en PDF final.

## 3. Causa probable de preview invertido

Archivo principal: `montaje_offset_inteligente.py`.

Evidencia:

- `generar_preview_pliego()` crea una imagen PIL.
- En `montaje_offset_inteligente.py:135-137` hace:
  - `x_px = mm_to_px(pos["x_mm"])`
  - `y_px = mm_to_px(pos["y_mm"])`
  - `canvas_img.paste(..., (x_px, y_px))`

PIL pega imagenes desde origen superior izquierdo. Pero `pos["y_mm"]` llega desde slots que el editor y el PDF interpretan como origen inferior izquierdo.

Conversion que parece faltar en preview:

```text
y_px_preview = sheet_height_px - y_px - slot_height_px
```

El PDF parece verse mejor porque ReportLab usa origen inferior izquierdo y recibe `x_mm/y_mm` sin invertir, lo cual coincide con el canvas CSS que usa `bottom`.

Diagnostico: el preview no aplica la conversion Y necesaria para renderizar coordenadas bottom-left en un raster top-left.

## 4. Causa probable de desincronizacion Canvas/Preview/PDF

Preview y PDF guardan antes de generar, pero usan layout persistido:

- `output_panel.js:22` guarda antes de preview.
- `output_panel.js:49` guarda antes de PDF.
- `api_client.js:52-61` llama endpoints sin mandar layout.
- Backend carga desde disco en `generate_preview()` y `generate_pdf()`.

Riesgos:

- `saveLayout()` no valida claramente el resultado antes de seguir. Si el save falla y devuelve JSON de error, preview/PDF pueden continuar usando layout viejo.
- No se encontro bandera dirty/unsaved.
- Preview tiene cache busting: `?t=Date.now()`.
- PDF no tiene cache busting equivalente; el enlace puede apuntar siempre a `montaje_final.pdf`.
- Upload carga layout desde disco, no desde estado vivo JS. Si hay cambios visuales no guardados antes de subir PDF, puede haber divergencia temporal.

Conclusion: la desincronizacion principal de coordenadas viene de preview, pero hay riesgos reales de estado viejo por save no verificado, ausencia de dirty flag y cache de PDF.

## 5. Causa probable del problema de sangrado

Hoy los campos no tienen una semantica unica.

- `design.width_mm/height_mm`: a veces son `MediaBox`; a veces `final_size + 2*bleed`.
- `slot.w_mm/h_mm`: caja visual/persistida del slot; para repeat puede representar caja ya expandida.
- `slot.bleed_mm`: sangrado por slot, pero puede ser reemplazado por `design_export` o `export_settings`.
- `design.bleed_mm`: sangrado usado por motores.
- `bleed_default_mm`: fallback global de layout y exportacion.

Evidencia de doble conteo:

- Upload puede guardar diseno expandido: `services/editor_offset_uploads.py:66-78`.
- Step & Repeat vuelve a sumar bleed: `engines/step_repeat_pro_engine.py:28-32`.
- Nesting tambien suma bleed: `engines/nesting_pro_engine.py:20-22`.
- Output tambien calcula caja final como `design_w + 2*bleed` en `services/editor_offset_output_service.py:133-135`.

Si un PDF subido ya trae sangrado en `MediaBox`, o si upload ya expandio la medida final, el sistema puede tratar esa medida como trim y volver a sumar sangrado.

Marcas de corte: `montaje_offset_inteligente.py` intenta dibujarlas alrededor del trim, pero si la caja base ya esta contaminada con bleed, las marcas caen sobre una caja incorrecta.

Regla tecnica recomendada para una fase futura:

```text
slot.w_mm y slot.h_mm = medida final / corte
slot.bleed_mm = sangrado adicional por lado
w_total = w_mm + bleed_mm * 2
h_total = h_mm + bleed_mm * 2
```

## 6. Errores o riesgos encontrados

### Preview usa origen Y incorrecto

- Severidad: alta.
- Zona: `montaje_offset_inteligente.py:135-137`.
- Evidencia: PIL usa top-left; canvas/PDF usan bottom-left.
- Explicacion: `y_mm` se pega directamente como pixel Y en PIL, lo que invierte verticalmente el resultado respecto al canvas.
- Recomendacion: caracterizar con test visual minimo y corregir solo preview.

### Contrato ambiguo de `design.width_mm/height_mm`

- Severidad: alta.
- Zona: upload, motores, output service.
- Evidencia: upload usa `MediaBox` o suma bleed; motores vuelven a sumar.
- Explicacion: el mismo campo puede representar caja fisica del PDF o tamano final expandido.
- Recomendacion: definir si esos campos son trim o caja fisica y migrar con compatibilidad.

### Riesgo claro de doble sangrado

- Severidad: alta.
- Zona: `editor_offset_uploads.py`, `step_repeat_pro_engine.py`, `nesting_pro_engine.py`, `editor_offset_output_service.py`.
- Evidencia: varias capas aplican `+ 2*bleed`.
- Explicacion: un PDF o diseno que ya llega con sangrado puede expandirse de nuevo en motor/salida.
- Recomendacion: una sola fuente de verdad: slot trim + bleed por lado.

### Preview/PDF dependen de save previo no verificado

- Severidad: media-alta.
- Zona: `output_panel.js`.
- Evidencia: `await ctx.saveLayout()` pero no se comprueba `ok`.
- Explicacion: si el guardado falla, el flujo puede continuar y generar desde layout viejo.
- Recomendacion: bloquear salida si save falla.

### PDF sin cache busting

- Severidad: media.
- Zona: `output_panel.js`.
- Evidencia: preview agrega `?t=...`; PDF no.
- Explicacion: el navegador puede mostrar o descargar un PDF cacheado si la URL no cambia.
- Recomendacion: agregar cache busting en fase controlada.

### `slot_box_final` es fragil

- Severidad: media-alta.
- Zona: `services/editor_offset_output_service.py:114-143`.
- Evidencia: la heuristica depende de `design.width + 2*bleed`.
- Explicacion: si `design.width` ya incluye bleed, la inferencia de caja final puede fallar.
- Recomendacion: no tocar hasta fijar contrato de bleed.

### Validacion frontend no bloquea salida

- Severidad: media.
- Zona: `output_panel.js`, `geometry_validation.js`.
- Evidencia: `OUT_OF_SHEET`, `OVERLAP`, `GRIPPER` alertan, pero se continua.
- Explicacion: errores geometricos criticos pueden llegar a preview/PDF.
- Recomendacion: bloquear errores criticos, dejar warnings como decision explicita.

## 7. Tests existentes relacionados

Se encontro cobertura util, pero no cubre el bug principal.

Cubren:

- Contrato estructural backend: `tests/test_editor_offset_output_contract.py`.
- Caracterizacion de upload, rotacion, `slot_box_final`: `tests/test_editor_offset_characterization.py`.
- Motor repeat: `tests/test_step_repeat_pro_engine.py`.

No se encontraron tests para:

- Orden vertical canvas vs preview.
- Preview raster con conversion bottom-left/top-left.
- No duplicar bleed cuando PDF ya tiene `MediaBox` con sangrado.
- `requestPreview()` abortando si save falla.
- Bloqueo real de preview/PDF con `OUT_OF_SHEET`.
- Cache busting de PDF.
- Marcas de corte sobre trim cuando existe `BleedBox/TrimBox`.

Tests recomendados:

- Test unitario de preview con dos slots: uno arriba y otro abajo.
- Test de transformacion Y en preview PNG.
- Test de upload con PDF cuyo `MediaBox` incluye sangrado y `TrimBox` representa corte.
- Test de motores para asegurar que no suman bleed dos veces.
- Test de `saveLayout()` fallido antes de preview/PDF.
- Test de bloqueo para errores geometricos criticos.

## 8. Plan SAFE de correccion futura

### Fase 1: caracterizar coordenadas preview vs PDF

Crear un layout minimo de dos slots, uno arriba y uno abajo, y verificar que canvas, preview y PDF mantienen el mismo orden vertical.

### Fase 2: corregir preview Y si esta invertido

Corregir solo la conversion Y del preview PNG. No tocar PDF, motores, upload ni contrato de sangrado en esta fase.

### Fase 3: definir contrato de sangrado

Definir explicitamente:

- `slot.w_mm/h_mm` como medida final/corte.
- `slot.bleed_mm` como sangrado adicional por lado.
- Caja total como `w/h + 2*bleed`.

### Fase 4: evitar doble conteo de bleed

Revisar upload, motores y output service para que solo una capa expanda caja con sangrado.

### Fase 5: mejorar UI de salida

Agregar estado dirty/unsaved, verificar resultado de save antes de generar y agregar cache busting al PDF.

### Fase 6: bloquear preview/PDF con errores criticos

Bloquear salida ante errores como `OUT_OF_SHEET`; mantener warnings como confirmacion explicita o aviso no bloqueante segun decision de producto.

## 9. Archivos que no conviene tocar todavia

- `montaje_offset_inteligente.py`: alto riesgo productivo; solo tocar preview con test especifico.
- `services/editor_offset_output_service.py`: concentra conversiones, bleed, rotacion y `slot_box_final`.
- `services/editor_offset_uploads.py`: cambiarlo puede afectar trabajos historicos.
- `engines/step_repeat_pro_engine.py`: motor canonico repeat.
- `engines/nesting_pro_engine.py`: sensible a semantica de caja expandida.
- `static/js/editor_offset_visual.js`: entrypoint fragil con estado, save, panels y listeners.
- `templates/editor_offset_visual.html`: IDs y botones conectados a JS.
- `routes.py`: superficie publica y compatibilidad legacy.
- `static/js/editor_offset_visual/output_panel.js`: sensible porque decide cuando guardar y generar.

## 10. Proximo prompt recomendado

```text
Corrige unicamente el bug confirmado de eje Y invertido en el preview PNG del Editor Offset Visual.

No cambies PDF, upload, motores ni contrato de sangrado.
Primero agrega o ajusta una prueba minima de caracterizacion para dos slots verticales.
Luego aplica la correccion mas pequena posible.
Ejecuta solo los tests relacionados.
No hagas refactors.
No hagas commits.
```
