# 02 ESTADO OFFSET

## Estado actual real

Hoy el repo sigue teniendo varios flujos offset coexistiendo, pero el **Editor Visual IA** ya quedo delimitado, auditado y documentado como subsistema propio dentro del modulo.

## Flujo bajo foco en esta fase

### Editor visual IA nuevo

- ruta: `GET /editor_offset_visual`
- template: `templates/editor_offset_visual.html`
- frontend principal: `static/js/editor_offset_visual.js`
- estilos principales: `static/css/editor_offset_visual.css`
- backend de orquestacion: `routes.py`
- servicios internos:
  - `services/editor_offset_jobs.py`
  - `services/editor_offset_layout_defaults.py`
  - `services/editor_offset_uploads.py`
  - `services/editor_offset_imposition_service.py`
- motor Step & Repeat PRO: `engines/step_repeat_pro_engine.py`
- validador de contrato de salida: `services/editor_offset_output_contract.py`
- motor de salida final: `montaje_offset_inteligente.py`
- motor de nesting auxiliar: `engines/nesting_pro_engine.py`
- simulador de cuadernillos: `cuadernillos/simulator.py`
- agente SDK asesor: `ai_agent/editor_advisor/` (CLI-only/read-only, sin Flask/UI)

Este fue el unico flujo trabajado funcionalmente en esta fase.

## Capacidades actuales confirmadas

- carga y persistencia por job via `layout_constructor.json`
- definicion de pliego, margenes y caras frente/dorso
- alta y edicion de trabajos logicos
- subida de PDFs y metadata por diseno
- generacion de slots por IA de trabajos logicos
- imposicion `repeat`, `nesting` y `hybrid`
- selector de imposicion separado en `services/editor_offset_imposition_service.py`
- edicion manual de slots
- agrupacion y desagrupacion de slots
- duplicado de frente a dorso
- ajustes CTP desde frontend
- preview y PDF final desde layout persistido
- Step & Repeat PRO corregido para:
  - respetar `bleed_mm = 0`
  - usar spacing global del editor
  - elegir rotacion solo si mejora capacidad
  - intercambiar `w_mm/h_mm` cuando rota
  - evitar stretch en PDF
  - centrar el bloque correctamente en PDF normal
- seleccion avanzada:
  - seleccionar toda la cara activa
  - centrado horizontal, vertical y completo de bloque
  - seleccion por marco desde area vacia
- panel de Asistente IA conectado a `POST /ai/step_repeat_action_openai`
- Step & Repeat PRO Inteligente en Fase 5:
  - metadata por diseno persistida y normalizada
  - ordenamiento base por `forms_per_plate`, prioridad y rol derivado
  - `preferred_zone` editable desde UI
  - zonas reales basicas para `top`, `bottom`, `left`, `right`, `center`, `auto`
  - `fill` inteligente al final para aprovechar huecos restantes
  - compactacion vertical segura para grupos `top/center/bottom`
  - expansion vertical inteligente para `top/center/bottom` cuando la banda inicial no alcanza
  - expansion vertical de una sola zona cuando contiene uno o varios disenos:
    - `top/top` anclado hacia arriba
    - `bottom/bottom` anclado hacia abajo
    - `center/center` centrado
  - compactacion final segura que integra grupos `auto` cuando conviven con zonas verticales
  - validacion estricta de `forms_per_plate` por diseno
  - error bloqueante si faltan formas solicitadas
  - generacion atomica por diseno para evitar slots parciales
  - aislamiento de ejecuciones para que un error anterior no contamine la siguiente corrida
- Simulador de Cuadernillos Fase 6 integrado al Editor Visual IA:
  - endpoint `POST /editor_offset/cuadernillos/simular`
  - soporte para `cosido_caballete`
  - soporte para `sin_tapa` y `tapa_completa`
  - selector de cuadernillo 8 / 16
  - tapa completa separada como VYV 4 de cara unica
  - tripa generada de forma independiente
  - VYV 4 y VYV 8 automaticos cuando no hay bloque completo
  - patrones reales validados para cuadernillos 8 y 16
  - metadata visual `frente_visual`, `dorso_visual` y `cara_visual`
  - orientacion cabeza con cabeza con valores `90`, `-90`, `180` y `0`
  - render diferenciado de TAPA, TRIPA, frente/dorso y VYV
  - jerarquia visual reforzada para tapa, tripa y cara unica
  - sin integracion con PDF, sin slots y sin persistencia en layout
- Simulador de Cuadernillos Fase 6.1 visual:
  - resumen tecnico superior con paginas originales, paginas finales, blancas, tapa, tipo de cuadernillo y pliegos
  - advertencia visible de simulacion visual: no genera PDF ni modifica el montaje
  - badges de paginas por cara en cada pliego
  - cabeceras uniformes para Frente, Dorso y Cara unica VYV
  - estilos profesionales para resumen, tarjetas, badges y jerarquia visual
  - cambio limitado a presentacion frontend
  - sin cambios en backend, payload, salida JSON, `cuadernillos/simulator.py`, templates ni `layout_constructor.json`
- Fase 8 arquitectura/UX:
  - jobs/defaults/uploads separados en servicios
  - Step & Repeat PRO extraido a `engines/step_repeat_pro_engine.py`
  - tests dedicados en `tests/test_step_repeat_pro_engine.py`
  - servicio de imposicion para `repeat`, `nesting` y `hybrid`
  - `routes.py` queda como fachada/orquestador con wrappers compatibles
  - shell UX profesional con toolbar sticky, canvas central y panel derecho con scroll interno
  - panel derecho con tabs: Pliego, Trabajos, Disenos, Imposicion, Edicion, IA, Cuadernillos, CTP y Salida
  - fix de scroll interno de tabs/panel derecho
  - premium visual pass SAFE CSS-only:
    - toolbar mas tecnica
    - tabs mas densos
    - panel derecho mas profesional
    - inputs/selects mejor integrados
    - canvas/pliego con fondo tecnico
    - estados selected/locked/warnings mas legibles
    - microajustes de contraste para Snap, Espaciado, labels secundarios, unidades mm, inputs tecnicos y botones claros
  - base QA Playwright en `tests/playwright/test_editor_load.py`
  - test Playwright de tabs/scroll en `tests/playwright/test_tabs_scroll.py`
  - decision UX: no agregar barra inferior nueva por ahora; `geometry-validation-panel` queda como area contextual/status existente
- Fase 9 documentacion/agente SDK:
  - `ai_agent/editor_advisor/` existe como prototipo OpenAI Agents SDK
  - funciona como asesor tecnico CLI-only/read-only
  - usa tools con allowlist para leer archivos relevantes del repo
  - bloquea rutas sensibles y externas
  - no esta integrado a Flask, UI ni endpoints
  - no reemplaza al asistente IA Step & Repeat del panel actual

## Validaciones implementadas

### Backend antes de preview/PDF

Documentadas en `08_VALIDACION_SALIDA.md`.

Implementadas:

- unicidad de `designs[].ref`
- unicidad de `slots[].id`
- verificacion de `slots[].design_ref`
- validacion basica de `slot.face`
- validacion numerica minima de campos criticos
- ancho y alto mayores que cero
- warnings para `logical_work_id` no resuelto
- warnings para cara `back` declarada sin slots de dorso
- Fase 7.1 agrega tests dedicados en `tests/test_editor_offset_output_contract.py`
- Fase 7.2 extrae la validacion a `services/editor_offset_output_contract.py` sin cambiar comportamiento

### Frontend visual

Documentadas en `09_VALIDACION_GEOMETRICA.md`.

Implementadas:

- fuera de pliego total
- fuera de area util
- invasion de zona de pinza CTP
- overlap simple por bounding box

### Simulador de cuadernillos

Documentado en `13_SIMULADOR_CUADERNILLOS.md`.

Implementado:

- validacion de payload y modos soportados
- normalizacion de paginas a multiplo de 4
- derivacion automatica de paginas por cara desde `tipo_cuadernillo`
- errores claros para configuraciones no soportadas
- tests dedicados en `tests/test_cuadernillos_simulator.py`

## Mejoras UX implementadas

### Indicador de distancia util durante drag

Documentado en `10_INDICADOR_DISTANCIA_UTIL.md`.

Implementado:

- distancia al margen util mas cercano
- distancia al slot vecino mas cercano de la misma cara
- distancia a pinza si CTP esta activo

### Correccion de interaccion click vs drag

Implementada en frontend:

- click simple vuelve a seleccionar el slot normalmente
- drag solo comienza despues de un umbral minimo de movimiento
- el indicador aparece solo en drag real
- al terminar el drag, el slot arrastrado queda seleccionado

### Herramientas pro iniciales de edicion manual

Documentadas en `11_HERRAMIENTAS_EDICION_PRO.md`.

Implementado:

- alineacion de seleccion
- distribucion horizontal y vertical
- nudge por botones y teclado
- paso configurable en mm
- `Shift` multiplica el paso por 10
- `Alt` reduce el paso a 0.1x
- duplicado y borrado multi-slot
- proteccion de slots bloqueados

### Herramientas de bloque y seleccion avanzada

Implementado:

- seleccionar todos los slots de la cara activa
- `Ctrl/Cmd + A` cuando el foco no esta en inputs
- centrar seleccion en eje horizontal
- centrar seleccion en eje vertical
- centrar bloque completo
- calculo de bbox con footprint real del slot
- seleccion por marco con rectangulo visual
- `Shift/Ctrl/Cmd + drag` suma seleccion
- drag select solo empieza desde area vacia del pliego

### UX de toolbar PRO

Implementado:

- correccion de textos rotos por encoding en la barra PRO
- etiquetas legibles para herramientas de alineacion y nudge
- barra principal simplificada con:
  - seleccionar todo
  - centrar bloque
  - paso + nudge
- panel avanzado colapsable para alineacion y distribucion

### Mejora visual safe Fase 7

Implementado solo en CSS:

- tipografia y paleta mas limpias
- botones con hover y foco visible
- paneles y contenedores con bordes y sombras sutiles
- accordion avanzado mas legible
- badges y bloques con acabado visual mas consistente

Garantias:

- sin cambios en JS
- sin cambios en listeners ni herramientas
- sin cambios en layout JSON
- sin cambios en preview/PDF ni motores

### Base IA Step & Repeat PRO

Implementado:

- carpeta `ai_agent/`
- schemas `ToolRequest` y `ToolResponse`
- tools repeat:
  - `analizar_layout(layout)`
  - `generar_repeat(layout, config)`
  - `optimizar_repeat(layout)`
  - `centrar_layout(layout)`
  - `aplicar_reglas_repeat(layout, reglas)`
  - `set_design_zone(layout, design_ref, preferred_zone)`
  - `set_design_zones(layout, zones_by_design)`
  - `validar_repeat(layout)`
- controller simple `handle_agent_request(prompt, layout)`
- endpoint `POST /ai/step_repeat_action`
- endpoint `POST /ai/step_repeat_action_openai`
- panel frontend "Asistente IA"
- OpenAI se inicializa solo al ejecutar la accion IA; sin `OPENAI_API_KEY`, el editor sigue funcionando y la IA devuelve error claro
- aplicacion del layout devuelto solo al confirmar con "Aplicar cambios"
- la IA puede resolver disenos por `ref`, `filename`, `work_id` o dimensiones tipo `50x40`
- el bridge conserva el ultimo layout generado aunque luego se ejecute una tool de analisis
- el frontend muestra las tools usadas y diferencia cambios de metadata de layouts con slots regenerados

### UI actual de disenos en Fase 5

Implementado:

- `Formas/pliego`
- `Ancho`
- `Alto`
- `Bleed`
- `Permitir rotacion`
- `Ubicacion`

No visibles al usuario final:

- `priority`
- `repeat_role`
- `preferred_flow`

Detalles confirmados:

- el select visible usa textos amigables:
  - `Automatico`
  - `Arriba`
  - `Abajo`
  - `Izquierda`
  - `Derecha`
  - `Centro`
- internamente los values siguen siendo:
  - `auto`
  - `top`
  - `bottom`
  - `left`
  - `right`
  - `center`
- `fill` no aparece como opcion visible de ubicacion

### Automatismos backend Fase 5

Implementado en `routes.py`:

- `priority` automatico si no hay override manual
- `repeat_role` automatico si no hay override manual
- `preferred_flow` reservado pero inactivo
- `repeat_manual_overrides` para distinguir valores historicos/manuales de defaults automaticos

Reglas actuales observadas:

- mayor `forms_per_plate` tiende a quedar primero
- el diseno principal puede quedar como `primary`
- zonas explicitas se respetan por encima del rol derivado
- `fill` se usa al final para ocupar espacio restante
- si todo esta en `auto`, se conserva el comportamiento legacy
- `forms_per_plate` ya no se trata como intencion blanda:
  - si no entran todas las formas solicitadas, el motor falla
  - el error informa `requested_forms`, `placed_forms` y `missing_forms`
- `preferred_zone` funciona como preferencia de inicio:
  - primero se intenta la banda zonal normal
  - si `top/center/bottom` no entran completos y la geometria lo permite, se intenta expansion vertical antes de fallar
  - si varios disenos comparten `top`, `bottom` o `center`, esa zona puede expandirse verticalmente antes de fallar
  - si hay zona vertical explicita mas disenos `auto`, el motor intenta una compactacion final segura para formar un bloque mas natural
- `apply_imposition` no debe aplicar layouts incompletos:
  - backend devuelve `ok: false`
  - frontend no reemplaza `state.layout` en ese caso

## Limitaciones conocidas

- siguen coexistiendo flujos offset legacy en el repo
- `routes.py` continua concentrando mucha orquestacion, aunque la validacion de salida ya fue extraida a `services/`
- `routes.py` ya no contiene el motor Step & Repeat PRO canonico, pero sigue concentrando endpoints y compatibilidad
- la semantica de `w_mm/h_mm` ya quedo consolidada para `repeat`, pero sigue siendo punto sensible frente a otros engines y flujos legacy
- la validacion geometrica usa bounding box simple, no geometria rotada exacta
- parte del feedback UX sigue apoyandose en `alert()`
- no hay schema formal completo del layout ni del slot; existe solo cobertura minima de contrato de salida
- no hay tests automatizados especificos para todos los casos recientes de repeat/rotacion/PDF
- Playwright existe para carga y tabs/scroll, pero falta cobertura avanzada de drag/resize/seleccion y flujos productivos
- la IA del panel actual usa OpenAI tool calling sobre tools locales; tambien sigue existiendo el endpoint local simple `/ai/step_repeat_action`
- el agente SDK `ai_agent/editor_advisor` existe como asesor externo CLI-only/read-only, pero todavia no esta integrado a Flask/UI
- falta edicion masiva avanzada de propiedades de slots
- `preferred_flow` existe en contrato pero todavia no tiene efecto real en el motor
- no hay compactacion horizontal de grupos zonales
- la compactacion actual solo intenta casos verticales `top/center/bottom` y `auto` combinado con esas zonas
- `left/right` no tienen expansion horizontal equivalente todavia
- `fill` mejorado no reemplaza un packing real
- no existe modo `maximize`; el comportamiento actual es exacto respecto de `forms_per_plate`
- no hay sistema formal de modos aun
- el simulador de cuadernillos todavia no genera PDF ni modifica el layout de montaje
- `tapa_simple` no esta implementada
- el simulador solo soporta cosido a caballete y cuadernillos 8/16
- VYV se calcula como cara unica logica, no como frente/dorso de salida final

## Frontera de alcance vigente

### Dentro del alcance de continuidad

- `/editor_offset_visual`
- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`
- endpoints `/editor_offset/*` y `/editor_offset_visual/apply_imposition`
- endpoint `/editor_offset/cuadernillos/simular`
- `montaje_offset_inteligente.py`
- `engines/nesting_pro_engine.py`
- `cuadernillos/simulator.py`

### Fuera del alcance por ahora

- `/montaje_offset`
- `/montaje_offset_inteligente`
- `/imposicion_offset_auto`
- `montaje_offset.py`
- `montaje_offset_personalizado.py`
- `imposicion_offset_auto.py`
- `montaje.py`

## Foco siguiente sugerido

1. cubrir con pruebas o fixtures los bugs corregidos de repeat:
   - bleed 0
   - spacing
   - rotacion inteligente
   - PDF sin stretch
   - centrado global normal
   - zonas verticales y multiples disenos en la misma zona
   - `auto` combinado con zonas verticales
2. ampliar schema y validaciones del contrato sin romper compatibilidad ni duplicar la validacion minima ya cubierta
3. agregar pruebas para IA/tools:
   - multiples zonas en una instruccion
   - generacion posterior a `set_design_zones`
   - preservacion del layout generado en el bridge
4. mejorar surfacing de errores y warnings del editor sin refactor masivo
5. medir con casos reales si la heuristica automatica de `repeat_role` necesita ajuste
6. evaluar modos futuros y expansion horizontal solo con pruebas de regresion
7. definir, en una fase separada, si el simulador de cuadernillos debe integrarse con PDF o mantenerse como herramienta de consulta visual
8. en Fase 9, mantener documentacion base alineada, conservar el agente SDK aislado hasta una fase de integracion y ampliar Playwright a drag/resize/seleccion, upload/apply repeat/preview/PDF
