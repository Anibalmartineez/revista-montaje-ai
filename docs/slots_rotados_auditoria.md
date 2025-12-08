# Auditoría de slots rotados (editor offset vs PDF)

## Flujo y puntos de uso de `rotation_deg`

- **Generación inicial (backend Step & Repeat PRO)**: en `routes._build_step_repeat_slots` se asignan `x_mm/y_mm`, `w_mm/h_mm` y `rotation_deg` para cada slot producido por el motor automático. Las coordenadas se calculan con origen en la esquina inferior izquierda del pliego utilizable (márgenes ya descontados) y `rotation_deg` se fija en 90° cuando la pieza se rota para caber en el ancho utilizable. `w_mm/h_mm` se invierten según esa rotación. 【F:routes.py†L497-L560】
- **Entrega al editor**: los layouts se serializan como JSON y el editor los normaliza (`parseInitialLayout` en `static/js/editor_offset_visual.js`). `renderSheet` posiciona cada slot con `style.left` y `style.bottom` usando `slot.x_mm/slot.y_mm`, y aplica `transform: rotate(...)` sobre un `div` con tamaño fijo `w_mm/h_mm`; el origen asumido es bottom-left y la rotación es alrededor del centro del rectángulo sin rotar. 【F:static/js/editor_offset_visual.js†L203-L310】【F:static/js/editor_offset_visual.js†L408-L469】
- **Rotación manual en el editor**: el panel lateral escribe `slot.rotation_deg` a partir del input (`applySlotForm`). No se ajustan `x_mm/y_mm` ni se intercambian `w_mm/h_mm`, por lo que el centro se mantiene y la caja visual se extiende usando `getEffectiveSlotBox` para snap y cálculos de bounding. 【F:static/js/editor_offset_visual.js†L1460-L1505】【F:static/js/editor_offset_visual.js†L226-L276】
- **Serialización hacia el backend**: `layoutToJson` hace `JSON.stringify` del estado (incluyendo `rotation_deg`) y se envía vía `saveLayout` o en el cuerpo de las llamadas a `/editor_offset/preview` y `/editor_offset/generar_pdf`. 【F:static/js/editor_offset_visual.js†L1608-L1686】
- **Ingesta en Python para generar PDF**: `montar_offset_desde_layout` filtra los slots por cara y arma `posiciones_manual` con `x_mm/y_mm/w_mm/h_mm` y `rot_deg` respetando lo recibido. Se documenta explícitamente que las posiciones manuales vienen en mm con origen en la esquina inferior izquierda y con `w/h` ya en TRIM. 【F:montaje_offset_inteligente.py†L1610-L1679】【F:montaje_offset_inteligente.py†L930-L986】
- **Dibujado en PDF**: al renderizar cada slot con ReportLab, si `rot` es 90°/270° se intercambian `draw_w_mm/draw_h_mm` y luego se rota la imagen PIL antes de llamar a `drawImage` usando `x_pt/y_pt` sin compensación adicional. 【F:montaje_offset_inteligente.py†L1325-L1368】

## Observaciones de origen, dimensiones y rotación

- **Editor (HTML/CSS)**: usa `left/bottom` (origen inferior izquierdo) con `w_mm/h_mm` originales. La rotación se aplica con `transform: rotate(...)` centrada en el rectángulo base; para snap se usa el bounding box efectivo (`effW/effH`) calculado a partir de `w_mm/h_mm` y del centro `(cx, cy)`. 【F:static/js/editor_offset_visual.js†L226-L310】【F:static/js/editor_offset_visual.js†L390-L470】
- **Preview/PDF (Python)**: las posiciones manuales también se interpretan como bottom-left. Para 90°/270° el código intercambia explícitamente las dimensiones antes de dibujar, asumiendo que `x/y` ya corresponden a la caja rotada. No hay ajuste para conservar el centro original del slot no rotado. 【F:montaje_offset_inteligente.py†L1325-L1368】【F:montaje_offset_inteligente.py†L930-L986】

## Incongruencias y puntos sospechosos

- **Desplazamiento al rotar**: en el editor, rotar mantiene el centro del slot y deja `x_mm/y_mm` anclados a la caja sin rotar. En el render PDF, al intercambiar `draw_w_mm/draw_h_mm` y dibujar en `x_pt/y_pt` sin recálculo del origen, el bounding box rotado queda anclado en la esquina inferior izquierda, lo que produce un corrimiento vertical u horizontal respecto a la vista del editor cuando `rot_deg` es 90° o 270°. 【F:montaje_offset_inteligente.py†L1325-L1368】
- **Consistencia de tamaños**: los motores de imposición que rotan automáticamente (Step & Repeat PRO) ya entregan `w_mm/h_mm` intercambiados cuando colocan a 90°. Los slots rotados manualmente mantienen `w_mm/h_mm` originales, de modo que el backend asume dimensiones rotadas en un caso y no en el otro; esto mezcla referencias de origen y puede explicar la discrepancia. 【F:routes.py†L497-L560】【F:static/js/editor_offset_visual.js†L1460-L1505】

## Recomendaciones inmediatas

- Revisar el cálculo de `x_pt/y_pt` en el render PDF para slots con `rot_deg` 90°/270°: debería conservar el centro `(x + w/2, y + h/2)` del rectángulo sin rotar, ajustando el origen del bounding box rotado (`cx - eff_w/2`, `cy - eff_h/2`). Ver comentario `TODO(rotated-slots)` agregado en `montaje_offset_inteligente.py` como punto de entrada. 【F:montaje_offset_inteligente.py†L1325-L1368】
- Unificar el criterio de `w_mm/h_mm` entre autoimposición y rotación manual: decidir si `w_mm/h_mm` representan siempre el tamaño sin rotar o el tamaño efectivo rotado, y documentarlo para evitar interpretaciones divergentes. 【F:routes.py†L497-L560】【F:static/js/editor_offset_visual.js†L226-L310】

## Fix aplicado

- En `montaje_offset_inteligente.py` el cálculo de la posición para el PDF ahora usa el centro del slot (`x_mm + w/2`, `y_mm + h/2`) como referencia y reconstruye la esquina inferior izquierda de la caja rotada con las dimensiones efectivas (`eff_draw_w_mm/eff_draw_h_mm`). El bounding box y el trim se recalculan con esas dimensiones, manteniendo la rotación alrededor del centro igual que en el editor visual. 【F:montaje_offset_inteligente.py†L1325-L1371】
