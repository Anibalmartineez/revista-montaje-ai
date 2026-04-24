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

## Fase 4 - Consolidacion de herramientas PRO

### Fix visual de toolbar

Se corrigio la barra PRO de edicion manual:

- eliminacion de textos rotos por encoding en etiquetas y botones
- `Edicion` vuelve a verse de forma legible
- botones de alineacion con etiquetas claras:
  - Izq
  - Centro H
  - Der
  - Abajo
  - Centro V
  - Arriba
- nudge con controles direccionales claros
- mejora de espaciado, tamanos y alineacion del control `Paso` + `mm`

### Herramientas de bloque

Se agregaron acciones para operar sobre selecciones completas:

- seleccionar todos los slots de la cara activa
- atajo `Ctrl/Cmd + A` fuera de inputs
- centrar horizontalmente la seleccion
- centrar verticalmente la seleccion
- centrar bloque completo

El centrado usa el bounding box real del grupo y el area util del pliego. Los slots bloqueados quedan protegidos segun la misma politica de herramientas editables.

### Refactor UX de barra PRO

La barra principal quedo simplificada:

- visibles:
  - seleccionar todo
  - centrar bloque
  - paso en mm
  - nudge
- ocultas en panel avanzado:
  - alineacion relativa
  - distribucion horizontal/vertical

La logica existente de align, distribute, nudge y seleccion no se elimino; solo se reorganizo visualmente.

### Seleccion por marco

Se implemento drag select / box select sobre el pliego:

- empieza solo desde area vacia
- muestra rectangulo azul semitransparente
- selecciona slots de la cara activa por interseccion de bbox
- `Shift/Ctrl/Cmd + drag` suma a la seleccion actual
- no interfiere con click simple ni drag de slots
- usa `slot.w_mm/h_mm` como footprint visual real

## Fase 4 - Correcciones profundas de Step & Repeat PRO

### Bleed y spacing

Se corrigio un bug donde `bleed_mm = 0` caia al fallback `bleed_default_mm = 3` por uso de truthiness.

Estado resultante:

- `bleed_mm = 0` es valor explicito valido
- repeat no infla el slot si el PDF ya trae sangrado incorporado
- `slot.bleed_mm` refleja el bleed realmente usado
- `slot.w_mm/h_mm` reflejan la caja final esperada
- repeat toma separacion desde:
  - `spacingSettings.spacingX_mm`
  - `spacingSettings.spacingY_mm`

### Rotacion inteligente

Se corrigio la estrategia de rotacion en repeat:

- compara capacidad sin rotacion vs con rotacion
- no rota si todo entra sin rotar
- rota solo si mejora capacidad
- si rota 90/270, intercambia `w_mm/h_mm`
- las posiciones de grid se calculan con dimensiones ya rotadas

Caso importante documentado:

- diseno 100x50
- 35 formas
- permitir rotacion
- resultado esperado: layout limpio 5x7 con `rotation_deg = 0`

### Semantica consolidada de slot rotado

Queda consolidada esta regla:

- `slot.w_mm / slot.h_mm` = caja final ocupada por el slot en el pliego
- `rotation_deg` = orientacion del contenido del diseno
- el frontend no debe volver a rotar la caja externa si `w_mm/h_mm` ya representan footprint final
- el render PDF debe rotar el contenido dentro de esa caja final, con traslacion correcta

### Render PDF sin stretch

Se corrigio el render de contenido rotado:

- no se fuerza resize deformante
- se respeta la proporcion original
- se aplican compensaciones explicitas para 90/180/270
- el contenido queda dentro de la caja final del slot

### Centrado global del PDF normal

Se corrigio un bug donde el PDF normal podia quedar desplazado aunque CTP lo centrara bien.

Conclusion del bug:

- el problema ya no era geometria individual del slot
- habia un segundo centrado generico que no respetaba el footprint final consolidado

Estado resultante:

- el bbox global usa `slot.w_mm/h_mm` como caja final
- repeat y posiciones manuales no pasan por un segundo centrado incorrecto
- el bloque se centra dentro del area util del pliego
- el PDF normal ya no depende del flujo CTP para quedar completo y centrado

## Fase 4 - Base IA Step & Repeat PRO

### Backend de agente por tools

Se creo una capa intermedia desacoplada en `ai_agent/`:

- `schemas.py`
- `tools_repeat.py`
- `agent_controller.py`

Tools iniciales:

- `analizar_layout(layout)`
- `generar_repeat(layout, config)`
- `optimizar_repeat(layout)`
- `centrar_layout(layout)`
- `aplicar_reglas_repeat(layout, reglas)`

Tambien se agrego:

- `POST /ai/step_repeat_action`

La capa no integra todavia OpenAI API. Por ahora interpreta prompts simples y despacha a tools locales reales.

### Panel IA en frontend

Se integro un panel "Asistente IA" dentro del Editor Visual IA:

- textarea para prompt
- boton `Ejecutar`
- respuesta visible
- boton `Aplicar cambios`

Regla importante:

- ejecutar una accion no reemplaza `state.layout`
- el layout devuelto solo se aplica cuando el usuario confirma con `Aplicar cambios`

### Estado de continuidad

La base queda preparada para el flujo futuro:

`OpenAI -> tool call -> agent_controller -> tools reales -> layout sugerido -> aplicacion manual por usuario`

## 2026-04-22 / 2026-04-23 Fase 5 - Step & Repeat PRO Inteligente

### Objetivo general

Volver mas util el motor Step & Repeat PRO del Editor Visual IA sin pasar a packing complejo ni romper compatibilidad con Fase 4.

### Implementaciones reales cerradas en la rama

- metadata persistida por diseno para repeat:
  - `priority`
  - `preferred_zone`
  - `preferred_flow`
  - `repeat_role`
  - `repeat_manual_overrides`
- ordenamiento base y compatibilidad con layouts viejos
- UI minima inicial para preferencias por diseno
- zonas reales basicas por bandas
- `fill` inteligente para huecos utiles restantes
- simplificacion UX:
  - queda visible solo `Ubicacion`
  - se ocultan:
    - `priority`
    - `repeat_role`
    - `preferred_flow`
- textos amigables en UI:
  - `Automatico`
  - `Arriba`
  - `Abajo`
  - `Izquierda`
  - `Derecha`
  - `Centro`
- `preferred_flow` reservado pero inactivo
- compactacion vertical segura de grupos zonales

### Reglas consolidadas de producto y motor

- `preferred_zone` pasa a ser el control principal visible para el usuario
- `priority` y `repeat_role` se derivan automaticamente cuando no hay override manual
- `preferred_flow` se conserva en contrato, pero no participa del motor
- `fill` se procesa al final para ocupar huecos utiles
- si todo esta en `auto`, se mantiene comportamiento legacy

### Semanticas que se mantuvieron intactas

- `slot.w_mm / slot.h_mm` siguen siendo footprint final en `repeat`
- `rotation_deg` sigue siendo orientacion del contenido
- no se toco semantica de preview/PDF ni `montaje_offset_inteligente.py`

### Limitaciones abiertas al cierre de Fase 5

- no hay compactacion horizontal
- no hay packing avanzado
- `preferred_flow` no tiene implementacion funcional todavia
- la heuristica de `repeat_role` automatico puede requerir ajuste con casos reales
