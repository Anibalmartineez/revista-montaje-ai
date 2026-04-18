# 05 DIARIO OFFSET

## 2026-04-17

### Contexto

Se abre rama enfocada solo en modulo de montaje offset, especialmente en el editor visual IA.

### Objetivo de la jornada

- auditar flujo real actual
- crear base documental interna
- no cambiar logica de negocio

### Hallazgos principales

- el editor visual IA nuevo entra por `GET /editor_offset_visual`
- usa `templates/editor_offset_visual.html`
- depende directamente de:
  - `static/js/editor_offset_visual.js`
  - `static/css/editor_offset_visual.css`
- el frontend llama cinco endpoints POST del constructor:
  - save
  - upload
  - auto_layout
  - apply_imposition
  - preview / generar_pdf
- la orquestacion del editor vive en `routes.py`
- la salida real de preview/PDF vive en `montaje_offset_inteligente.py`
- el motor de nesting real usado por el editor es `engines/nesting_pro_engine.py`

### Hallazgos de arquitectura

- el repo tiene varios flujos offset coexistiendo
- el editor visual IA no esta todavia aislado como modulo cerrado
- hay solapamientos entre calculo de slots, imposicion y render final
- varias rutas legacy siguen activas y comparten motores o conceptos

### Decision de esta etapa

- documentar primero
- no limpiar ni borrar archivos
- no refactorizar todavia
- delimitar con precision que pertenece al editor visual IA y que no

### Proxima accion recomendada

- documentar contrato exacto de `layout_constructor.json`
- luego auditar en detalle bleed / crop / face / ctp / export mode
