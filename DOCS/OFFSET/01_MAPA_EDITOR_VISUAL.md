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

## Dependencias reales no visuales

### Persistencia por job

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`
- ahi vive el contrato persistido del editor

### Backend de orquestacion

- `routes.py`

### Validacion backend de salida

- `services/editor_offset_output_contract.py`

### Motor de nesting usado por el editor

- `engines/nesting_pro_engine.py`

### Motor real de preview y PDF final

- `montaje_offset_inteligente.py`

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

### Simulador de cuadernillos

- `POST /editor_offset/cuadernillos/simular`

### Salida

- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`

## Pipeline de datos resumido

1. `GET /editor_offset_visual` carga o crea `layout_constructor.json`.
2. El template serializa ese layout en `window.INITIAL_LAYOUT_JSON`.
3. `static/js/editor_offset_visual.js` lo normaliza y lo convierte en `state.layout`.
4. Las acciones del usuario modifican `state.layout`.
5. `layoutToJson()` sincroniza defaults y serializa el contrato persistible.
6. `POST /editor_offset/save` guarda el JSON en disco.
7. Preview y PDF final nunca consumen el estado efimero del navegador.
8. Preview/PDF validan el contrato persistido con `validate_constructor_output_layout(layout)`.
9. Preview/PDF leen solo el layout persistido desde disco y lo reinterpretan en `montaje_offset_inteligente.py`.

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
   - simular cuadernillos de forma visual/logica
   - generar preview y PDF final
6. Cada salida importante se persiste en `layout_constructor.json`.
7. Preview y PDF final se generan desde `montaje_offset_inteligente.py`.

## Simulador de cuadernillos

### Responsabilidad

- vive como herramienta auxiliar dentro del Editor Visual IA
- calcula armado logico de cuadernillos para cosido a caballete
- muestra TAPA, TRIPA, pliegos frente/dorso y VYV de cara unica
- representa orientacion cabeza con cabeza mediante metadata visual

### Backend

- modulo: `cuadernillos/simulator.py`
- ruta: `POST /editor_offset/cuadernillos/simular`
- orquestacion: `routes.py`

### Frontend

- panel: `templates/editor_offset_visual.html`
- render: `static/js/editor_offset_visual.js`
- estilos: `static/css/editor_offset_visual.css`

### Limites

- no persiste datos en `layout_constructor.json`
- no crea ni modifica `slots[]`
- no participa en `apply_imposition`
- no alimenta preview/PDF final
- no modifica Step & Repeat PRO ni motores legacy

## Fuente de verdad actual

### Estado del editor

- Frontend vivo: `static/js/editor_offset_visual.js`
- Persistencia: `static/constructor_offset_jobs/<job_id>/layout_constructor.json`
- Estado efimero no persistido:
  - `zoom`
  - `scale`
  - `selectedSlot`
  - `selectedSlots`
  - `selectedWork`
  - `history`
  - `dragState`
  - resultado visual del simulador de cuadernillos

### Orquestacion backend

- `routes.py`
- `services/editor_offset_output_contract.py` para validacion previa a preview/PDF

### Motor real de salida preview/PDF

- `montaje_offset_inteligente.py`

## Carpetas de trabajo involucradas

- `templates/`
- `static/js/`
- `static/css/`
- `static/constructor_offset_jobs/`
- `services/`
- `routes.py`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`

## Limite de este mapa

Este documento describe el flujo real del editor visual IA nuevo. No documenta en detalle las otras pantallas offset legacy salvo cuando interfieren o se solapan con este editor.
