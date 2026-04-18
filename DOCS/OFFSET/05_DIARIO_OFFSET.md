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

## 2026-04-18

### Mejora implementada

- validacion geometrica visual en el editor
- indicador flotante de distancia util durante drag manual de slots

### Que hace el indicador

- muestra distancia al margen util mas cercano
- muestra distancia al slot vecino mas cercano de la misma cara
- si CTP esta activo, muestra distancia a la zona de pinza

### Alcance tecnico

- solo frontend
- sin cambios en backend
- sin cambios en motores de imposicion
- sin cambios en contratos persistidos

### Observacion importante

Los calculos usan bounding box simple en mm. Sirven como ayuda operativa rapida, no como verificacion geometrica exacta de salida final.

## 2026-04-18 Cierre de fase

### Resumen de lo realizado

- auditoria del flujo real del editor visual IA
- documentacion del mapa del editor
- congelamiento del contrato de layout
- congelamiento del subcontrato de slots
- validacion backend antes de preview y PDF
- validacion geometrica visual en frontend
- indicador de distancia util durante drag
- correccion de UX para distinguir click simple vs drag real y preservar seleccion manual
- consolidacion documental del modulo para continuidad

### Pruebas realizadas

- verificacion del flujo y contratos mediante lectura cruzada de:
  - `routes.py`
  - `static/js/editor_offset_visual.js`
  - `templates/editor_offset_visual.html`
  - `montaje_offset_inteligente.py`
- revision de ejemplos reales de `layout_constructor.json`
- compilacion Python previa sobre `routes.py` durante la fase de validacion backend
- verificacion manual del cableado frontend y de la documentacion consolidada

### Estado resultante

- el Editor Visual IA quedo con contexto tecnico claro y trazable
- el contrato de datos principal quedo documentado
- la salida tiene validacion minima previa en backend
- el editor tiene asistencia visual y geometrica adicional en frontend
- la interaccion de edicion manual quedo estable tras el ajuste click vs drag

### Pendientes

- formalizar mejor schema y validaciones profundas del layout
- revisar con mas precision la semantica geometrica de `w_mm/h_mm`, `rotation_deg` y bleed por engine
- mejorar presentacion UX de warnings y errores sin depender tanto de `alert()`
- decidir cuando conviene empezar micro-refactors internos sin tocar flujos legacy

## 2026-04-18 Inicio Fase 4

### Objetivo

Empezar la fase `fase4-editor-offset-pro` con mejoras profesionales de edicion manual en el Editor Visual IA.

### Mejora implementada

- barra de edicion manual con alineacion de seleccion
- distribucion horizontal y vertical de tres o mas slots
- nudge de precision por botones y flechas de teclado
- paso configurable en milimetros para movimiento fino
- duplicado y borrado multi-slot

### Alcance tecnico

- solo frontend del Editor Visual IA
- sin cambios en backend
- sin cambios en motores de imposicion
- sin cambios en contrato persistido de `slots[]`

### Observacion importante

Las operaciones nuevas trabajan sobre la caja efectiva del slot, consistente con las ayudas visuales actuales. No reemplazan una validacion geometrica rotada exacta de salida final.
