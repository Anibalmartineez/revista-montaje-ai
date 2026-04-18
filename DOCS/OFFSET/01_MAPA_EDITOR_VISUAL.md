# 01 MAPA EDITOR VISUAL IA

## Objetivo

Documentar el flujo real actual del editor visual IA de montaje offset sin refactor ni cambios de negocio.

## Ruta de entrada

- Ruta Flask: `GET /editor_offset_visual`
- Funcion: `routes.editor_offset_visual` en `routes.py`
- Responsabilidad:
  - valida o genera `job_id`
  - carga o inicializa `layout_constructor.json`
  - serializa `layout_json`
  - renderiza el template del editor

## Template usado

- Template: `templates/editor_offset_visual.html`
- Este template:
  - monta toda la UI del editor
  - inyecta `window.INITIAL_LAYOUT_JSON`
  - inyecta `window.JOB_ID`
  - carga un unico JS principal
  - carga un unico CSS principal

## Archivos frontend directos

### HTML

- `templates/editor_offset_visual.html`

### JS

- `static/js/editor_offset_visual.js`

### CSS

- `static/css/editor_offset_visual.css`

### Bootstrap inline dentro del template

- `window.INITIAL_LAYOUT_JSON`
- `window.JOB_ID`

No se ve carga directa de otros JS/CSS desde el template del editor visual IA.

## Endpoints que consume el frontend del editor

### Carga inicial

- `GET /editor_offset_visual`

### Persistencia de layout

- `POST /editor_offset/save`

### Subida de PDFs

- `POST /editor_offset/upload/<job_id>`

### Generacion de slots por IA

- `POST /editor_offset/auto_layout/<job_id>`

### Aplicacion de motor de imposicion

- `POST /editor_offset_visual/apply_imposition`

### Salida

- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`

## Flujo real resumido

1. El navegador abre `GET /editor_offset_visual`.
2. `routes.py` crea o recupera un job bajo `static/constructor_offset_jobs/<job_id>/`.
3. El template entrega al JS el `layout_json` inicial.
4. `static/js/editor_offset_visual.js` toma control total del estado en memoria.
5. El usuario puede:
   - editar pliego y margenes
   - definir trabajos logicos
   - subir PDFs
   - definir formas por pliego por diseno
   - crear slots por IA
   - aplicar motor repeat / nesting / hybrid
   - editar slots manualmente
   - duplicar frente a dorso
   - aplicar ajustes CTP
   - generar preview y PDF final
6. Cada salida importante se persiste en `layout_constructor.json`.
7. Preview y PDF final se generan desde `montaje_offset_inteligente.py`.

## Fuente de verdad actual

### Estado del editor

- Frontend vivo: `static/js/editor_offset_visual.js`
- Persistencia: `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

### Orquestacion backend

- `routes.py`

### Motor real de salida preview/PDF

- `montaje_offset_inteligente.py`

## Carpetas de trabajo involucradas

- `templates/`
- `static/js/`
- `static/css/`
- `static/constructor_offset_jobs/`
- `routes.py`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`

## Limite de este mapa

Este documento describe el flujo real del editor visual IA nuevo. No documenta en detalle las otras pantallas offset legacy salvo cuando interfieren o se solapan con este editor.
