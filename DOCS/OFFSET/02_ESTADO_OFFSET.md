# 02 ESTADO OFFSET

## Estado actual observado

Hoy conviven varios flujos offset dentro del repo. No forman un unico modulo limpio; son varias generaciones de UI y motores que comparten conceptos parecidos.

## Flujos detectados

### 1. Editor visual IA nuevo

- Ruta: `GET /editor_offset_visual`
- Template: `templates/editor_offset_visual.html`
- JS principal: `static/js/editor_offset_visual.js`
- Backend principal: `routes.py`
- Motor de salida: `montaje_offset_inteligente.py`
- Motor de nesting auxiliar: `engines/nesting_pro_engine.py`

Este es el flujo objetivo de esta rama.

### 2. Montaje offset clasico

- Ruta: `/montaje_offset`
- Template: `templates/montaje_offset.html`
- Backend/motor: `routes.py` + `montaje_offset.py`

Es otro flujo distinto. No es el editor visual IA.

### 3. Montaje offset inteligente anterior

- Ruta: `/montaje_offset_inteligente`
- Template: `templates/montaje_offset_inteligente.html`
- Backend/motor: `routes.py` + `montaje_offset_inteligente.py`

Comparte el motor inteligente, pero no es la misma UI del editor visual IA constructor.

### 4. Imposicion offset automatica

- Ruta: `/imposicion_offset_auto`
- Template: `templates/imposicion_offset_auto.html`
- Backend/motor: `routes.py` + `imposicion_offset_auto.py`

Es un flujo aparte para calcular layouts automaticos por cantidad/formato.

### 5. Montaje offset personalizado PRO

- Entrada desde `routes.py`
- Motor: `montaje_offset_personalizado.py`

Tambien es otro flujo separado.

## Modulos realmente usados por el editor visual IA

### Usados directamente

- `routes.py`
- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`

### Importados en `routes.py` pero no usados por este editor en su flujo principal

- `montaje_offset.py`
- `montaje_offset_personalizado.py`
- `imposicion_offset_auto.py`
- `montaje.py`

## Responsabilidad real por capa

### UI y estado interactivo

- `static/js/editor_offset_visual.js`

### Contrato de entrada/salida del editor

- `routes.py`

### Persistencia por job

- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

### Calculo de slots automaticos por IA de trabajos logicos

- `routes._generate_slots_with_ai`
- `montaje_offset_inteligente.realizar_montaje_inteligente`

### Motores de imposicion desde el editor

- Repeat: `routes._build_step_repeat_slots`
- Nesting: `engines.nesting_pro_engine.compute_nesting`
- Hybrid: `routes._repeat_pattern_over_sheet`

### Render de preview y PDF final

- `montaje_offset_inteligente.montar_offset_desde_layout`
- `montaje_offset_inteligente.realizar_montaje_inteligente`

## Conclusiones de estado

- El editor visual IA nuevo ya tiene flujo propio y persistencia propia.
- El repo todavia mezcla varios motores offset que resuelven problemas parecidos.
- Antes de refactorizar conviene congelar el flujo real del editor y definir frontera entre:
  - constructor visual nuevo
  - pantallas offset legacy
  - motores reutilizables

## Decision operativa para esta rama

En esta rama conviene trabajar con esta frontera:

- Dentro del alcance:
  - `/editor_offset_visual`
  - su template
  - su JS/CSS
  - endpoints `/editor_offset/*` y `/editor_offset_visual/apply_imposition`
  - `montaje_offset_inteligente.py`
  - `engines/nesting_pro_engine.py`

- Fuera del alcance por ahora:
  - `/montaje_offset`
  - `/montaje_offset_inteligente`
  - `/imposicion_offset_auto`
  - motores legacy salvo analisis de solapamiento
