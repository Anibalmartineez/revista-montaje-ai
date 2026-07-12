# Reporte overlay bleed canvas - Editor Offset Visual

## 1. Comportamiento anterior del canvas

Antes de esta fase, `static/js/editor_offset_visual/renderer_canvas.js` creaba cada elemento `.slot` usando exclusivamente la caja devuelta por `getSlotRenderBox(slot)`:

- `left` desde `slot.x_mm`;
- `bottom` desde `slot.y_mm`;
- `width` desde `slot.w_mm`;
- `height` desde `slot.h_mm`.

Para los slots Repeat normalizados, `w_mm` y `h_mm` representan trim. El canvas mostraba por tanto el trim, pero no una caja exterior independiente para el bleed. La inspeccion previa del codigo, CSS y DOM confirmo que no existia un elemento, pseudo-elemento, borde ni `box-shadow` de bleed, y tampoco existia un valor visual fijo de 3 mm.

El formulario `#slot-bleed` ya mostraba `slot.bleed_mm ?? 0`. La limitacion era visual; no se encontro un valor productivo incorrecto que debiera corregirse en esta fase.

## 2. Solucion implementada

Se agrego una solucion localizada en el renderer:

- `resolveVisualBleedMm(layout, slot)` resuelve el bleed visual con validacion numerica explicita;
- `slotUsesFinalBox(slot)` reconoce valores compatibles de `slot_box_final`;
- `renderSlotBleedOverlay(ctx)` crea un hijo `.slot-bleed-overlay` cuando corresponde;
- el overlay usa `pointer-events: none`;
- el elemento principal `.slot` conserva sus dimensiones, posicion, seleccion, estados e interacciones;
- el renderer no escribe datos nuevos en `state.layout` ni en el JSON persistido.

El overlay se posiciona con `left/top = -bleed_mm` y se dimensiona como:

```text
outer_width_mm = slot.w_mm + 2 * bleed_mm
outer_height_mm = slot.h_mm + 2 * bleed_mm
```

La conversion usa el mismo `mmToPx()` del renderer. Al ser hijo del `.slot`, acompana el zoom del pliego, el movimiento y la transformacion de rotacion del slot.

### Auditoria de simetria geometrica

Una revision posterior con `getBoundingClientRect()` confirmo que la primera version del overlay era asimetrica. Aunque tanto `.slot` como `.slot-bleed-overlay` usaban `box-sizing: border-box`, el containing block del hijo absoluto comenzaba dentro del borde de `.slot`. Con un borde computado de 0.8 px, la expansion resultaba aproximadamente `bleed - 0.8 px` a izquierda/arriba y `bleed + 0.8 px` a derecha/abajo. La desviacion maxima era 1.63 px a zoom 100% y 3.25 px a zoom 200%.

La correccion minima fue desplazar el overlay en su sistema local mediante:

```css
transform: translate(-1px, -1px);
```

El desplazamiento corresponde al borde CSS declarado de `.slot`. Al ser una transformacion local, rota y escala junto con el slot. No cambia `left`, `top`, `width`, `height`, coordenadas en milimetros ni datos persistidos.

Medidas finales en el job real, en pixeles:

| Zoom | Bleed | Rotacion | Izquierda | Derecha | Superior | Inferior | Spread maximo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100% | 1 mm | 0 | 0.725 | 0.350 | 0.725 | 0.338 | 0.387 |
| 100% | 3 mm | 0 | 1.800 | 1.412 | 1.800 | 1.400 | 0.400 |
| 100% | 1 mm | 90 | 0.337 | 0.725 | 0.725 | 0.350 | 0.388 |
| 100% | 3 mm | 90 | 1.400 | 1.800 | 1.800 | 1.412 | 0.400 |
| 200% | 1 mm | 0 | 1.450 | 0.700 | 1.450 | 0.675 | 0.775 |
| 200% | 3 mm | 0 | 3.600 | 2.825 | 3.600 | 2.800 | 0.800 |
| 200% | 1 mm | 90 | 0.675 | 1.450 | 1.450 | 0.700 | 0.775 |
| 200% | 3 mm | 90 | 2.800 | 3.600 | 3.600 | 2.825 | 0.800 |

Todas las combinaciones quedan dentro de la tolerancia maxima de 1 px. El ancho y alto exteriores medidos corresponden a trim mas dos veces el bleed convertido a pixeles. El borde de 1 px del overlay permanece incluido dentro de esas dimensiones por `box-sizing: border-box`; no agrega expansion geometrica exterior.

## 3. Tratamiento de bleed 0, 1 y 3 mm

La prioridad visual implementada es:

1. `slot.bleed_mm` explicito, finito y mayor o igual a cero;
2. `design.bleed_mm` del `design_ref` asociado;
3. `layout.bleed_default_mm`;
4. cero si no existe ningun valor valido.

No se usa una expresion truthy, por lo que cero no cae al default.

Validacion real en el job `9855c231f1a6`, con trim `210 x 297 mm`:

- `bleed_mm=0`: el formulario mostro 0, no se creo `.slot-bleed-overlay` y el trim mantuvo sus dimensiones.
- `bleed_mm=1`: el overlay declaro `212 x 299 mm`, extendio 1 mm por lado y reporto `pointer-events: none`.
- `bleed_mm=3`: el overlay declaro `216 x 303 mm`, extendio 3 mm por lado y fue mayor que el caso de 1 mm.

En los tres casos, el `.slot` mantuvo los mismos valores CSS de ancho y alto correspondientes al trim. Las capturas de evidencia se guardaron bajo `output/playwright/` y no forman parte del codigo fuente.

## 4. Tratamiento de slot_box_final

### `slot_box_final=False` o ausente

El elemento `.slot` sigue representando trim y el overlay se expande hacia afuera con el bleed efectivo. El job real usado no persiste un valor explicito de `slot_box_final`; este caso se trata como caja trim y la salida productiva existente lo resuelve como Repeat normalizado.

### `slot_box_final=True`

No se crea overlay exterior y no se suma bleed nuevamente. El test automatizado usa un slot legacy `52 x 32 mm`, bleed de 1 mm y `slot_box_final=True`, y confirma que no se genera una caja `54 x 34 mm`.

No se modifico la semantica productiva de `slot_box_final` ni el Output Service.

## 5. Movimiento y rotacion

### Movimiento

Se arrastro el slot real en el navegador integrado. Antes del drag, las cajas observadas fueron aproximadamente:

- slot: `x=205.04`, `y=540.54` px;
- overlay: `x=205.31`, `y=540.81` px.

Despues del drag:

- slot: `x=255.35`, `y=516.70` px;
- overlay: `x=255.63`, `y=516.98` px.

El offset relativo se mantuvo, el overlay continuo siendo hijo de `sr_0` y el drag no fue bloqueado.

### Rotacion

Se validaron 0, 90, 180 y 270 grados mediante la interfaz. En todos los casos:

- `data-rotation` y `--slot-rotation-deg` reflejaron el angulo esperado;
- el overlay continuo asociado al mismo `.slot`;
- `bleed_mm` permanecio en 1;
- `pointer-events` permanecio en `none`.

No se modifico geometria de drag, snap, seleccion, validacion ni salida productiva.

## 6. Guardado y recarga

Se guardo y recargo el job `9855c231f1a6`. El JSON persistido conservo:

- `slot.id = sr_0`;
- `x_mm = 105`;
- `y_mm = 55`;
- `w_mm = 210`;
- `h_mm = 297`;
- `bleed_mm = 1`;
- `rotation_deg = 0`.

Tras la recarga, el renderer reconstruyo el overlay `212 x 299 mm` desde el layout, con `pointer-events: none`, y el formulario volvio a mostrar bleed 1. No fue necesario persistir ningun dato visual nuevo.

## 7. Tests ejecutados

Linea base previa a la implementacion:

- `tests/test_editor_offset_characterization.py`: 17 aprobados.
- `tests/test_step_repeat_pro_engine.py`: 17 aprobados.
- `tests/test_editor_offset_output_contract.py`: 7 aprobados.

Validacion final:

- `.\venv\Scripts\python.exe -m pytest tests/playwright/test_editor_bleed_overlay.py -q`: 3 aprobados, 0 fallidos, 0 omitidos.
- `.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q`: 17 aprobados, 0 fallidos, 0 omitidos; 20 warnings de dependencias deprecadas.
- `.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q`: 17 aprobados, 0 fallidos, 0 omitidos; 20 warnings de dependencias deprecadas.
- `.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q`: 7 aprobados, 0 fallidos, 0 omitidos.
- `node --check static/js/editor_offset_visual/renderer_canvas.js`: codigo de salida 0.

Cobertura focalizada:

- cajas 0, 1 y 3 mm;
- `slot_box_final=True` sin doble expansion;
- render sin mutacion del layout;
- fallback de bleed;
- rotaciones cardinales;
- estados selected, locked, geometry-warning y geometry-error;
- eventos click y pointerdown no interceptados;
- reconstruccion desde una copia serializada del layout.
- simetria de las cuatro extensiones mediante `getBoundingClientRect()` para zoom 100/200%, bleed 1/3 mm y rotacion 0/90 grados.

## 8. Validaciones con navegador integrado

URL usada:

`http://127.0.0.1:5000/editor_offset_visual?job_id=9855c231f1a6`

Datos:

- job: `9855c231f1a6`;
- PDF: `resumen_editor_offset_visual.pdf`;
- cara validada: front;
- slot: `sr_0`.

Se inspeccionaron DOM, estilos calculados, atributos `data-*`, bounding boxes, consola y red. Resultados:

- consola sin warnings ni errores;
- guardado: HTTP 200;
- preview: HTTP 200;
- PDF final: HTTP 200;
- overlay de 1 mm con `pointer-events: none`;
- overlay de 3 mm mayor que el de 1 mm;
- bleed 0 sin overlay;
- drag operativo;
- rotaciones cardinales operativas;
- guardado y recarga conservan bleed.

No se uso Computer Use ni Google Chrome en esta continuacion. La validacion se realizo exclusivamente con el navegador integrado y APIs de diagnostico del mismo.

## 9. Validaciones mediante Playwright y DOM

El test focalizado crea layouts DOM aislados sobre la aplicacion cargada y verifica estilos sin recurrir a comparaciones fragiles de pixeles. Se comprobaron:

- `data-bleed-mm`;
- `data-outer-width-mm`;
- `data-outer-height-mm`;
- `left`, `top`, `width` y `height` del overlay;
- `getComputedStyle(...).pointerEvents`;
- relacion padre-hijo entre overlay y slot;
- ausencia de mutacion antes/despues del render;
- estabilidad despues de serializar y reconstruir el layout.

La inspeccion DOM del job real confirmo los mismos contratos en la aplicacion productiva levantada.

## 10. Resultado de Preview y PDF

Preview:

- generado correctamente;
- archivo `preview.png` cargado en la UI;
- dimensiones observadas: `3628 x 4989` px;
- posicion persistida del slot sin cambios.

PDF:

- generado correctamente como `montaje_final.pdf`;
- una pagina;
- MediaBox aproximado `1814.173 x 2494.488 pt`, equivalente al pliego `640 x 880 mm`;
- render visual revisado con Poppler;
- el arte se muestra en la posicion esperada;
- no aparece la guia magenta/discontinua del overlay del canvas;
- el texto extraido no contiene `slot-bleed-overlay` ni etiquetas del overlay.

La generacion de Preview/PDF guardo primero el mismo layout y no cambio `x_mm`, `y_mm`, `w_mm`, `h_mm`, `bleed_mm` ni `rotation_deg`. No se modifico la precedencia productiva de bleed.

## 11. Limitaciones y riesgos pendientes

- La validacion visual real se realizo sobre cara front; no se creo un caso back adicional para evitar ampliar el alcance del job.
- El caso legacy `slot_box_final=True` se valido por DOM automatizado, no alterando el job real.
- Herramientas manuales considerando caja productiva siguen fuera de alcance.
- Overlap visual/productivo sigue fuera de alcance.
- Drag y snap con caja de bleed siguen fuera de alcance.
- Box select sigue usando la geometria existente.
- Align/distribute y distance indicator siguen usando la geometria existente.
- Nesting no fue modificado ni normalizado.
- TrimBox/BleedBox de Upload sigue fuera de alcance.
- Una comparacion industrial completa Canvas -> Preview -> PDF, con mas PDFs, doble cara y CTP, queda como fase separada.

## 12. Archivos modificados

Cambios de esta fase:

- `static/js/editor_offset_visual/renderer_canvas.js`;
- `static/css/editor_offset_visual.css`;
- `tests/playwright/test_editor_bleed_overlay.py`;
- `DOCS/OFFSET/REPORTE_OVERLAY_BLEED_CANVAS_EDITOR_OFFSET_VISUAL.md`.

Archivo previamente modificado por el usuario, preservado y no editado durante esta fase:

- `DOCS/OFFSET/REPORTE_FIX_SLOT_BOX_FINAL_REPEAT_EDITOR_OFFSET_VISUAL.md`.

No fueron modificados:

- `services/editor_offset_uploads.py`;
- `engines/step_repeat_pro_engine.py`;
- `services/editor_offset_output_service.py`;
- `services/editor_offset_output_contract.py`;
- `services/editor_offset_imposition_service.py`;
- `montaje_offset_inteligente.py`;
- `routes.py`;
- logica de Preview PNG productiva;
- logica de generacion PDF productiva.

## 13. Estado Git final

- Rama: `fix/editor-offset-visual-slot-box-final-bleed`.
- No se hizo commit.
- No se hizo merge.
- No se hizo rebase.
- No se hizo push.
- No se ejecuto `git pull`.
- No se cambio de rama.
- No se inicio ni reinicio el servidor.
- No se cerraron ni mataron procesos Python.
- No se agregaron PDFs de prueba al control de versiones.
- Los artefactos del job de validacion permanecen bajo el job ignorado `9855c231f1a6`.

## 14. Siguiente fase recomendada

Mantener esta fase cerrada y revisar el diff antes de autorizar commit. Como trabajo posterior separado, caracterizar la comparacion Canvas -> Preview -> PDF con doble cara, CTP y varios disenos, sin mezclarla con cambios en drag, snap, overlap, Nesting o Upload.
