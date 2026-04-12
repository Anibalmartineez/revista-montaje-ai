# Fuentes De Verdad Por Subsistema

Documento de congelación operativa de Fase 2.

Objetivo:

- dejar explícito qué estructura manda hoy en cada subsistema
- distinguir qué datos son derivados
- distinguir qué datos son auxiliares o legacy
- señalar dónde existe riesgo actual de inconsistencia

Este documento no cambia comportamiento.
No redefine contratos.
Solo fija la lectura correcta del sistema actual para la refactorización.

## 1. Editor Visual Constructor

### Fuente de verdad principal

- `layout` del constructor offset IA
- persistido por job en:
  - `static/constructor_offset_jobs/<job_id>/layout_constructor.json`
- estructura base controlada por:
  - `routes.py`
  - `templates/editor_offset_visual.html`
  - `static/js/editor_offset_visual.js`

### Qué contiene

- `sheet_mm`
- `margins_mm`
- `bleed_default_mm`
- `gap_default_mm`
- `works[]`
- `designs[]`
- `slots[]`
- `faces`
- `active_face`
- `imposition_engine`
- `allowed_engines`
- `export_settings`
- `design_export`

### Estructuras derivadas

- preview generado por:
  - `POST /editor_offset/preview/<job_id>`
- PDF generado por:
  - `POST /editor_offset/generar_pdf/<job_id>`
- slots recalculados por:
  - `POST /editor_offset/auto_layout/<job_id>`
  - `POST /editor_offset_visual/apply_imposition`

Estas salidas no son la fuente primaria.
Se regeneran desde `layout_constructor.json`.

### Estructuras auxiliares o legacy

- `works[]` son auxiliares para IA y definición lógica, no son el montaje final
- `designs[]` son metadatos de assets, no la salida final
- `slots[]` son la representación editable del constructor, no la representación definitiva del editor post-imposición

### Riesgo actual de inconsistencia

- Medio

Motivos:

- el constructor usa una representación distinta del editor post-imposición
- `works`, `designs` y `slots` conviven en el mismo layout con roles distintos
- el mismo `layout` puede ser mutado por varios endpoints

## 2. Editor Post-Imposición

### Fuente de verdad principal

- `layout.json` del job IA post-imposición
- persistido por job en:
  - `static/ia_jobs/<job_id>/layout.json`
- servido por:
  - `GET /layout/<job_id>.json`
- cargado por:
  - `GET /editor?id=<job_id>`

### Qué contiene

- `version`
- `job_id`
- `sheet`
- `grid_mm`
- `bleed_mm`
- `items[]`
- `assets[]`
- `pdf_filename`
- `preview_filename`
- `min_gap_mm` (inyectado/garantizado por backend)

### Regla operativa

- `items[]` es la fuente de verdad del montaje final editable

Todo lo que el editor mueve, rota, redimensiona o reaplica termina expresado en `items[]`.

### Estructuras derivadas

- PDF editado:
  - `pliego_edit.pdf`
- preview editada:
  - `preview_edit.png`
- respuesta de:
  - `POST /layout/<job_id>/apply`

Estas salidas son derivadas del `layout.json` validado y reaplicado.

### Estructuras auxiliares o legacy

- `assets[]` es catálogo/control de integridad, no layout final
- `meta.json` es soporte del job, no representación primaria del montaje
- trim box / bleed box en frontend son representación visual derivada

### Riesgo actual de inconsistencia

- Alto

Motivos:

- `layout.json`, `meta.json`, `assets[]` e `items[]` deben quedar alineados
- el editor chat IA también consume una vista del layout
- hay validaciones en backend y representación paralela en frontend

## 3. Montaje Manual

### Fuente de verdad principal

- `positions[]` enviados por cliente a:
  - `POST /api/manual/preview`
  - `POST /api/manual/impose`

### Regla operativa

- en el flujo manual, la fuente de verdad inmediata no es `layout.json`
- la fuente de verdad es la lista `positions[]` del request actual

### Qué contiene cada posición

- `uid`
- `file_idx`
- o alternativamente `archivo`
- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`
- `rot_deg`
- compatibilidad legacy: `rot`

### Estructuras derivadas

- preview manual PNG
- PDF manual final
- `positions_applied[]` devueltos por backend

### Estructuras auxiliares o legacy

- `current_app.config["LAST_UPLOADS"]`
- `current_app.config["LAST_SHEET_MM"]`
- `current_app.config["LAST_SANGRADO_MM"]`

Estas estructuras son dependencias de contexto del flujo manual.
No son una fuente de verdad robusta; son estado efímero del servidor.

### Riesgo actual de inconsistencia

- Muy alto

Motivos:

- el flujo manual depende de estado global efímero en `current_app.config`
- usa una representación distinta del editor post-imposición
- mezcla `file_idx` y `archivo` como resolución de asset

## 4. Diagnóstico Flexo

### Fuente de verdad principal

- `diagnostico_json` construido en backend durante `POST /revision`
- persistido como parte de:
  - `static/uploads/<revision_id>/diag.json`
  - `static/uploads/<revision_id>/res.json`

### Regla operativa

- `diagnostico_json` es la fuente de verdad semántica del diagnóstico

Debe considerarse la estructura principal para:

- parámetros de máquina
- material
- TAC/cobertura
- advertencias resumidas
- indicadores
- datos usados por la simulación frontend

### Estructuras derivadas

- `resultado_flexo.html` renderizado
- `window.diagnosticoJson`
- `window.analisisDetallado`
- `window.indicadoresAdvertencias`
- overlays HTML del resultado
- simulación interactiva de `flexo_simulation.js`
- preview técnico regenerado

### Estructuras auxiliares o legacy

- `analisis_detallado`
- `advertencias_iconos`
- `tabla_riesgos`
- `diag.json` completo como contenedor operativo
- `res.json` como snapshot de render y estado

Estas estructuras son muy importantes, pero la semántica congelada debe leerse desde `diagnostico_json`.

### Riesgo actual de inconsistencia

- Muy alto

Motivos:

- backend, template y JS reinterpretan parte del mismo diagnóstico
- algunas claves se duplican con alias:
  - `anilox_lpi` / `lpi`
  - `anilox_bcm` / `bcm`
  - `paso` / `paso_cilindro` / `paso_del_cilindro`
  - `velocidad` / `velocidad_impresion`
  - `tac_total` / `tac_total_v2` / `cobertura_estimada` / `cobertura_base_sum`

## 5. Exportación Y Preview PDF

### Fuente de verdad principal

No hay una única fuente de verdad transversal para todos los flujos PDF.
La fuente de verdad depende del subsistema:

- constructor offset:
  `layout_constructor.json`
- editor post-imposición:
  `layout.json`
- montaje manual:
  `positions[]` + estado efímero del servidor
- flexo diagnóstico:
  PDF persistido por `revision_id` + `diag.json`

### Regla operativa

- el archivo PDF o PNG nunca debe considerarse la fuente primaria
- la fuente primaria es siempre la estructura de entrada que permite regenerarlo

### Estructuras derivadas

- PDFs finales
- previews PNG
- URLs públicas estáticas
- base64 previews en algunos flujos legacy

### Estructuras auxiliares o legacy

- `output/`
- `output_flexo/`
- `preview_temp/`
- previews inline en base64
- archivos temporales/copias intermedias

### Riesgo actual de inconsistencia

- Alto

Motivos:

- conviven varios mecanismos de salida:
  - archivo estático
  - `send_file`
  - URL estática
  - base64 inline
- distintos flujos regeneran el mismo concepto de preview/PDF desde representaciones diferentes

## 6. Variables Globales De Template Congeladas Como Contrato

Estas variables deben tratarse como contrato frontend-backend congelado.

## 6.1 Constructor offset IA

Template:

- `templates/editor_offset_visual.html`

Variables globales:

- `window.INITIAL_LAYOUT_JSON`

## 6.2 Editor post-imposición

Template:

- `templates/editor_post_imposicion.html`

Variables globales:

- `window.layoutIA`
- `window.jobIdIA`

## 6.3 Resultado flexo

Template:

- `templates/resultado_flexo.html`

Variables globales:

- `window.USE_PIPELINE_V2`
- `window.diagnosticoJson`
- `window.advertencias`
- `window.analisisDetallado`
- `window.indicadoresAdvertencias`
- `window.advertenciasResumen`
- `window.revisionId`

### Riesgo actual de inconsistencia de globals

- Alto

Motivos:

- varias de estas globals son derivadas del mismo backend payload
- el template agrega defaults y aliases
- el JS asume presencia de claves con fallback implícito

## 7. Resumen Operativo Por Subsistema

### Editor visual constructor

- Fuente principal:
  `layout_constructor.json`
- Derivados:
  preview/PDF/slots recalculados
- Auxiliar:
  `works[]`, `designs[]`
- Riesgo:
  medio

### Editor post-imposición

- Fuente principal:
  `static/ia_jobs/<job_id>/layout.json`
- Derivados:
  PDF editado, preview editada
- Auxiliar:
  `assets[]`, `meta.json`
- Riesgo:
  alto

### Montaje manual

- Fuente principal:
  `positions[]` del request
- Derivados:
  preview/PDF manual
- Auxiliar/legacy:
  `LAST_UPLOADS`, `LAST_SHEET_MM`, `LAST_SANGRADO_MM`
- Riesgo:
  muy alto

### Diagnóstico flexo

- Fuente principal:
  `diagnostico_json`
- Derivados:
  template, overlays, simulación, preview técnico
- Auxiliar:
  `analisis_detallado`, `res.json`, `diag.json`
- Riesgo:
  muy alto

### Exportación / preview PDF

- Fuente principal:
  depende del subsistema; nunca el archivo final
- Derivados:
  PDF/PNG/URL/base64
- Auxiliar:
  outputs temporales
- Riesgo:
  alto

## 8. Regla De Refactorización A Partir De Este Documento

Antes de mover código:

- no cambiar la fuente de verdad de un subsistema sin declarar el reemplazo
- no promover una estructura derivada a fuente primaria de hecho
- no hacer que frontend y backend tengan dos fuentes semánticas paralelas

La prioridad correcta es:

1. conservar la fuente de verdad actual
2. aislarla
3. después recién extraer servicios o unificar duplicaciones
