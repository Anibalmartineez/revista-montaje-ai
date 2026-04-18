# 00 CONTEXTO OFFSET

## Que es este modulo

El modulo Offset del repo agrupa varios flujos historicos de montaje offset. En esta fase se trabajo exclusivamente sobre el **Editor Visual IA**, que hoy funciona como el constructor visual mas moderno del sistema para:

- definir pliego y caras
- cargar trabajos y disenos
- generar o editar slots manualmente
- aplicar motores de imposicion
- preparar frente y dorso
- aplicar ajustes CTP
- generar preview y PDF final

## Flujo principal

1. `GET /editor_offset_visual`
2. carga o crea `layout_constructor.json`
3. el frontend trabaja sobre `state.layout`
4. el usuario ajusta pliego, disenos, slots y parametros de salida
5. `POST /editor_offset/save` persiste el layout
6. `POST /editor_offset/preview/<job_id>` y `POST /editor_offset/generar_pdf/<job_id>` generan la salida final

## Archivos clave

- `routes.py`
- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`
- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

## Estado actual

- flujo real del editor visual IA auditado y documentado
- mapa del editor consolidado
- contrato de `layout_constructor.json` congelado en documentacion
- subcontrato de `slots[]` congelado en documentacion
- validacion backend previa a preview/PDF implementada
- validacion geometrica visual en frontend implementada
- indicador de distancia util durante drag implementado
- interaccion click vs drag corregida para mantener seleccion y edicion manual

## Riesgos principales

- semantica fragil de `slots[].w_mm/h_mm` segun engine
- enlace blando `slots[].design_ref -> designs[].ref`
- diferencias entre estado en memoria, JSON persistido y estado reinterpretado por preview/PDF
- coexistencia con flujos offset legacy dentro del mismo repo
- validaciones aun parciales en consistencia semantica y geometria exacta

## Proximos pasos sugeridos

1. auditar la semantica geometrica exacta de `w_mm/h_mm + rotation_deg + bleed`
2. formalizar un schema mas estricto del layout y de slots sin romper compatibilidad
3. mejorar el surfacing de warnings y errores en UI sin depender tanto de `alert()`
4. recien despues evaluar micro-refactors internos en frontend y orquestacion
