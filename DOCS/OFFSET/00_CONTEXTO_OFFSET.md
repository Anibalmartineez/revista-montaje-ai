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
- fase 4 avanzada con herramientas pro de edicion manual:
  - seleccion multiple
  - alineacion y distribucion
  - nudge por botones y teclado
  - paso configurable en mm
  - multiplicadores `Shift x10` y `Alt x0.1`
  - duplicado y borrado multi-slot
  - seleccion por marco
  - seleccion de toda la cara activa
  - centrado de bloque
- toolbar PRO simplificada:
  - acciones rapidas visibles
  - herramientas tecnicas en panel avanzado colapsable
- Step & Repeat PRO corregido en puntos criticos:
  - `bleed_mm = 0` se respeta como valor explicito
  - spacing real desde `spacingSettings.spacingX_mm` y `spacingSettings.spacingY_mm`
  - rotacion inteligente solo cuando mejora capacidad
  - `slot.w_mm/h_mm` consolidado como footprint final del slot
  - `rotation_deg` consolidado como orientacion del contenido
  - PDF sin stretch y con centrado global consistente
- base de agente IA creada:
  - carpeta `ai_agent/`
  - tools repeat
  - controller simple
  - endpoint `POST /ai/step_repeat_action`
- panel "Asistente IA" integrado al editor:
  - prompt
  - ejecucion contra backend
  - respuesta visible
  - aplicacion manual del layout devuelto
  - la UI actual usa `/ai/step_repeat_action_openai` y requiere `OPENAI_API_KEY` solo al ejecutar IA
- fase 5 consolidada para Step & Repeat PRO Inteligente:
  - metadata por diseno para repeat
  - `preferred_zone` como control principal visible en UI
  - `priority` automatico derivado por backend
  - `repeat_role` automatico derivado por backend
  - `preferred_flow` reservado para futuro, pero inactivo
  - `repeat_manual_overrides` para distinguir overrides historicos/manuales
  - zonas reales basicas:
    - `top`
    - `bottom`
    - `left`
    - `right`
    - `center`
    - `auto`
  - `fill` inteligente para ocupar huecos utiles al final
  - compactacion vertical segura de grupos zonales
  - UI simplificada en lista de disenos:
    - se mantiene visible `Ubicacion`
    - se ocultan prioridad, rol repeat y flujo
    - textos amigables:
      - `Automatico`
      - `Arriba`
      - `Abajo`
      - `Izquierda`
      - `Derecha`
      - `Centro`

## Riesgos principales

- coexistencia de semanticas historicas de `slots[].w_mm/h_mm` en flujos legacy
- riesgo de regresion si nuevos motores no respetan que en `repeat` `w_mm/h_mm` son footprint final
- enlace blando `slots[].design_ref -> designs[].ref`
- diferencias entre estado en memoria, JSON persistido y estado reinterpretado por preview/PDF
- coexistencia con flujos offset legacy dentro del mismo repo
- validaciones aun parciales en schema formal y consistencia semantica profunda
- existe endpoint local `/ai/step_repeat_action`, pero el panel actual usa `/ai/step_repeat_action_openai`; si falta `OPENAI_API_KEY`, solo falla la accion IA y el editor sigue funcionando
- `preferred_flow` sigue en contrato pero todavia no participa en decisiones reales del motor
- la compactacion actual de grupos zonales es solo vertical
- `fill` mejoro aprovechamiento de huecos, pero sigue sin packing avanzado

## Proximos pasos sugeridos

1. formalizar un schema mas estricto del layout y de slots sin romper compatibilidad
2. agregar tests de regresion para repeat:
   - `bleed_mm = 0`
   - spacing
   - rotacion 0/90
   - PDF normal vs CTP
3. conectar el agente IA a tool calls reales de OpenAI manteniendo el controller actual como capa intermedia
4. mejorar el surfacing de warnings y errores en UI sin depender tanto de `alert()`
5. extender compactacion a casos horizontales `left/center/right` solo si se mantiene segura
6. evaluar micro-refactors internos solo despues de cubrir los casos criticos de salida final
