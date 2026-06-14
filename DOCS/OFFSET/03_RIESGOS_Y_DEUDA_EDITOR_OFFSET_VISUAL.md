# Riesgos y Deuda Editor Offset Visual

Fuente principal: `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`.

Este documento concentra advertencias para trabajar de forma SAFE antes de editar cualquier archivo del Editor Offset Visual.

## Hechos confirmados

La auditoria identifico riesgos en frontend, contratos, persistencia, salida PDF, rutas Flask, motores alternativos y superficies legacy compartidas.

## Riesgos altos

- `static/js/editor_offset_visual.js` concentra estado global, history, wiring, shortcuts, listeners globales/temporales, render wrappers y spacing live.
- `state.layout` es frontera critica entre UI, persistencia, motores, preview y PDF final.
- `layout_constructor.json` es contrato persistido en `static/constructor_offset_jobs/<job_id>/`.
- Cambiar `slots[]` o `designs[]` puede romper motor, canvas, guardado y salida.
- Tocar `renderSheet`, seleccion, drag, `layoutToJson`, save, preview o PDF afecta varias superficies.
- PDFs fisicos faltantes no bloquean contrato de salida: `services/editor_offset_output_service.py` puede ignorar disenos cuyo archivo no existe.
- `montaje_offset_inteligente.py` es salida legacy compartida y no debe tratarse como dependencia exclusiva del editor.

## Riesgos medios

- `nesting` y `hybrid` no muestran validacion equivalente a `IncompleteImpositionError` de `repeat`.
- Upload puede sobrescribir PDFs con el mismo nombre dentro del job.
- Preview puede ser parcial frente al PDF final en CTP/doble cara.
- La semantica de bleed y dimensiones no esta completamente limpia.
- Controles UI visibles pueden no tener efecto confirmado.
- Wrappers legacy en `routes.py` aumentan superficie conceptual.
- Codigo inalcanzable en `static/js/editor_offset_visual.js` puede inducir cambios en el lugar incorrecto.

## Riesgos de regresion por IDs, data-* y clases

### Hechos confirmados

No renombrar sin revision:

- `sheet`
- `sheet-canvas`
- `geometry-validation-panel`
- `data-editor-tab`
- `data-editor-tab-panel`
- botones `btn-*`
- inputs `slot-*`
- inputs `ctp-*`
- inputs `ai-*`
- clases dinamicas `.hidden`, `.is-active`, `.slot.selected`, `.slot.locked`, `.slot.geometry-error`, `.slot.geometry-warning`, `.box-selection-rect`, `.ctp-guide`, `.distance-indicator`

## Riesgos por area

### state.layout

`state.layout` es la representacion viva del layout. Cualquier cambio en su forma impacta UI, `layoutToJson`, persistencia, motores y salida.

### layout_constructor.json

El archivo `static/constructor_offset_jobs/<job_id>/layout_constructor.json` es el contrato persistido. Cambios de estructura requieren compatibilidad o migracion.

### slots[]

Campos criticos:

- `id`
- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`
- `rotation_deg`
- `bleed_mm`
- `design_ref`
- `face`
- `slot_box_final`

Riesgo: romper canvas, seleccion, output contract o `posiciones_manual`.

### designs[]

Campos criticos:

- `ref`
- `filename`
- `width_mm`
- `height_mm`
- `bleed_mm`
- `forms_per_plate`

Riesgo: romper upload, motor, contrato y salida PDF.

### Bleed

Existe ambiguedad sobre si `design.width_mm/height_mm` representa trim, media box o caja con bleed. La auditoria marco posible doble conteo de bleed.

### CTP

CTP cruza UI, validacion geometrica y salida PDF. Preview no confirma necesariamente todas las marcas/textos finales.

### Preview

La preview puede usar una sola cara y no representar todo el PDF final, especialmente doble cara y CTP.

### PDF final

El PDF final depende de `services/editor_offset_output_service.py` y `montaje_offset_inteligente.py`. Cambios pueden afectar flujos legacy.

### Uploads

`services/editor_offset_uploads.py` guarda con `secure_filename()` directo en el job. Riesgo confirmado: subir el mismo nombre puede sobrescribir archivo previo.

### Rutas Flask

`routes.py` expone endpoints publicos y wrappers legacy. Cambios requieren revisar compatibilidad.

### montaje_offset_inteligente.py

Es salida legacy compartida. Requiere auditoria previa antes de mover responsabilidades.

## Codigo duplicado, inalcanzable o legacy

### Hechos confirmados

- Codigo inalcanzable despues de `return` en `renderSheet()` dentro de `static/js/editor_offset_visual.js`.
- Codigo inalcanzable en `renderCtpGuideOverlay()`.
- Wrappers en `routes.py` hacia `step_repeat_pro_engine`.
- `_generate_slots_with_ai()` conectado a `/editor_offset/auto_layout/<job_id>`, distinto del flujo actual de `apply_imposition`.
- Resize latente: CSS y ramas JS existen, pero el renderer no crea handles.

## Variables posiblemente huerfanas

### Hechos confirmados

- `aiResultLayout`
- `aiResultChangeType`

La auditoria no encontro uso posterior confirmado.

## Controles UI visibles sin efecto confirmado

### Hechos confirmados

Existen en HTML, pero no se confirmo lectura por `generateStepRepeatFromSelectedSlot()`:

- `sr-offset-x`
- `sr-offset-y`
- `sr-top-margin`
- `sr-bottom-margin`
- `sr-left-margin`
- `sr-right-margin`

Listeners opcionales sin DOM confirmado:

- `btn-center-selection-x`
- `btn-center-selection-y`

## Diferencia Step & Repeat manual vs PRO backend

### Hechos confirmados

Step & Repeat PRO backend:

- usa `services/editor_offset_imposition_service.py`
- usa `engines/step_repeat_pro_engine.py`
- valida formas incompletas en `repeat`

Step & Repeat manual frontend:

- vive en `static/js/editor_offset_visual.js`
- clona desde slot maestro
- no llama al motor backend

### Inferencias

La UI debe evitar presentar ambos como si fueran la misma funcionalidad.

## Riesgos especificos destacados

- PDF faltante: contrato valida `design_ref`, pero no existencia fisica de `filename`.
- Sobrescritura: upload con mismo nombre puede reemplazar archivo dentro del job.
- Nesting/hybrid: posible aceptacion de layout parcial si `rectpack` no coloca todo.
- Preview parcial: no equivale necesariamente a PDF final CTP.

## Preguntas abiertas

- Debe bloquearse salida si falta un PDF fisico?
- Debe normalizarse la semantica de dimensiones/bleed?
- Deben ocultarse, implementar o documentarse controles SR sin efecto confirmado?
- Debe `nesting/hybrid` fallar ante formas incompletas?
- Debe preview tener modo CTP fiel?
- Debe upload generar nombres unicos por job?

## Inferencias

La deuda mas peligrosa no es solo el tamano del entrypoint, sino la combinacion de entrypoint grande, contratos persistidos, salida legacy y controles UI parcialmente desalineados.
