# 04 PLAN OFFSET

## Objetivo de esta etapa

Consolidar el Editor Visual IA como flujo operativo profesional del modulo Offset, manteniendo compatibilidad con el layout existente y evitando refactors amplios.

## Etapa actual

- Estado documentado: Fase 10 cerrada y estable antes de merge a `main`
- Fase 8 queda como base cerrada de arquitectura SAFE y shell UX del Editor Visual IA
- Sin refactor masivo
- Sin limpieza agresiva
- Sin eliminacion de archivos
- Cambios acotados sobre el Editor Visual IA
- Foco real acumulado:
  - Step & Repeat PRO Inteligente cerrado como Fase 5
  - simulador de cuadernillos cerrado como Fase 6 visual/logica
  - separacion explicita entre simulacion de cuadernillos y salida PDF
  - validacion de salida protegida con tests y extraida a un modulo chico en Fase 7
  - jobs/defaults/uploads separados en servicios en Fase 8.1
  - Step & Repeat PRO extraido a `engines/step_repeat_pro_engine.py` en Fase 8.1B
  - servicio de imposicion `repeat`/`nesting`/`hybrid` en Fase 8.1C
  - shell UX y tabs profesionales en Fases 8.2/8.3
  - premium visual pass SAFE y microajustes de contraste CSS-only
  - base Playwright inicial para carga, tabs y scroll del editor
  - prototipo OpenAI Agents SDK `ai_agent/editor_advisor/` como asesor CLI-only/read-only
  - Fase 9.2 completada: `editor_advisor` especializado como UX SAFE Advisor
  - Fase 9.3 completada: premium pass CSS-only del panel derecho en `static/css/editor_offset_visual.css`
  - Fase 9.4 completada: Codex Prompt Builder con `prompt_para_codex` y `--codex-prompt-only`
  - Fase 10.0 completada: auditoria visual y baseline de header/topbar/canvas/panel derecho
  - Fase 10.1 completada: Canvas Pro Shell CSS-only, con topbar CAD/preprensa y canvas mas protagonista
  - Fase 10.2 completada: Panel Derecho Pro Density CSS-only, con tabs, scroll, formularios y paneles mas compactos
  - Fase 10.3 completada: Agent SDK UX Surface v2, con `summarize_editor_ux_surface()` ampliado
  - Fase 10.4 completada: QA visual/regresion; advisor tests `12 passed`; Playwright manual funciona desde Git CMD y `WinError 5` queda acotado al entorno Codex

## Plan propuesto por fases

### Fase 1. Congelar mapa actual

- mantener esta documentacion actualizada
- confirmar que el alcance de la rama es solo `/editor_offset_visual`
- evitar cambios en rutas offset legacy salvo correcciones puntuales justificadas

### Fase 2. Delimitar fronteras

- definir frontera entre:
  - editor visual IA nuevo
  - flujos offset legacy
  - motores reutilizables
- marcar dependencias reales y dependencias accidentales

### Fase 3. Congelar contratos

- documentar payload minimo de:
  - `layout_json`
  - `designs[]`
  - `slots[]`
  - `ctp`
  - `export_settings`
- documentar que endpoints son canonicos para el editor

### Fase 4 historica. Auditoria tecnica puntual

- revisar coherencia de:
  - bleed
  - crop marks
  - `forms_per_plate`
  - `face`
  - `rotation_deg`
  - `slot_box_final`
- detectar que reglas se resuelven en frontend y cuales en backend

### Fase 4 actual. Editor Offset PRO

Objetivo de la rama `fase4-editor-offset-pro`:

- mejorar la edicion manual sin tocar flujos legacy
- sumar herramientas de precision para operadores
- mantener contrato de layout compatible
- documentar cada herramienta incorporada

Bloques implementados:

- alineacion de seleccion
- distribucion horizontal y vertical
- nudge por botones y teclado
- paso configurable en mm
- `Shift x10` y `Alt x0.1`
- duplicado/borrado multi-slot
- proteccion de slots bloqueados
- correccion visual y de encoding de la toolbar PRO
- seleccion de todos los slots de la cara activa
- centrado horizontal, vertical y completo de bloque
- `Ctrl/Cmd + A`
- simplificacion de toolbar:
  - acciones rapidas visibles
  - herramientas tecnicas en panel avanzado
- seleccion por marco desde area vacia del pliego
- `Shift/Ctrl/Cmd + drag` para sumar seleccion
- correcciones profundas de Step & Repeat PRO:
  - `bleed_mm = 0` respetado como valor explicito
  - spacing desde `spacingSettings`
  - rotacion inteligente por capacidad
  - intercambio real de `w_mm/h_mm` al rotar
  - eliminacion de stretch en PDF
  - semantica consolidada de slot rotado
  - centrado global correcto en PDF normal
- base `ai_agent/` con tools repeat y controller
- endpoint `POST /ai/step_repeat_action`
- endpoint `POST /ai/step_repeat_action_openai` para el panel actual con OpenAI lazy
- panel "Asistente IA" integrado al editor

### Fase 4 siguiente. IA operativa guiada

Objetivo:

- mantener la capa `ai_agent/` como intermediaria entre UI, LLM y funciones reales
- conectar OpenAI tool calls sin permitir que el LLM modifique layout directamente
- ampliar tools con acciones verificables y reversibles
- registrar respuestas y sugerencias de forma no destructiva hasta que el usuario aplique cambios

### Fase 5. Step & Repeat PRO Inteligente

Estado real de esta rama:

- Fase 5.1.a:
  - metadata por diseno para repeat
  - ordenamiento base compatible con layouts viejos
- Fase 5.1.b:
  - UI minima inicial para preferencias por diseno
- Fase 5.2:
  - zonas reales basicas por bandas
- Fase 5.3:
  - `fill` inteligente para huecos utiles restantes
- Fase 5.4:
  - simplificacion UX:
    - solo queda visible `Ubicacion`
    - `priority`, `repeat_role` y `preferred_flow` pasan a logica interna
  - textos amigables en UI
  - `preferred_flow` reservado pero inactivo
- Fase 5.5:
  - compactacion vertical segura de grupos zonales
- Fase 5.6:
  - validacion estricta de formas solicitadas vs colocadas
  - error bloqueante para montajes incompletos
  - generacion atomica por diseno
  - aislamiento de ejecuciones para evitar contaminacion entre corridas
  - expansion vertical inteligente de zonas `top/center/bottom`
- Fase 5.7:
  - correccion de `center` rigido
  - expansion vertical para una sola zona `center`
  - expansion vertical para multiples disenos dentro de la misma zona:
    - `top/top`
    - `bottom/bottom`
    - `center/center`
  - mantenimiento de anclaje:
    - `top` hacia arriba
    - `bottom` hacia abajo
    - `center` centrado
- Fase 5.8:
  - compactacion final segura que incluye `auto` cuando convive con `top/center/bottom`
  - preservacion del comportamiento legacy cuando todo esta en `auto`
- Fase 5.9:
  - tools IA alineadas con el motor:
    - `set_design_zone`
    - `set_design_zones`
    - `generar_repeat`
    - `validar_repeat`
    - `optimizar_repeat`
  - soporte de referencias por dimensiones como `50x40`
  - encadenamiento de tools y preservacion del layout generado
  - distincion frontend entre `metadata_only` y `layout_with_slots`

Decisiones consolidadas:

- `preferred_zone` es el control principal visible
- `priority` y `repeat_role` se derivan automaticamente cuando no hay override manual
- `preferred_flow` se conserva en contrato pero no participa todavia del motor
- `slot.w_mm/h_mm` sigue siendo footprint final en `repeat`
- `rotation_deg` sigue siendo orientacion del contenido
- el modo actual es exacto respecto de `forms_per_plate`; no existe todavia modo `maximize`

### Fase 6. Simulador de Cuadernillos

Estado real:

- modulo aislado `cuadernillos/simulator.py`
- endpoint `POST /editor_offset/cuadernillos/simular`
- panel integrado al Editor Visual IA
- soporte para cosido a caballete
- soporte para `sin_tapa` y `tapa_completa`
- selector de cuadernillo 8 / 16
- tapa completa como VYV 4 de cara unica
- tripa separada
- VYV 4 y VYV 8 automaticos para restos parciales
- patrones reales auditables para 8 y 16 paginas
- metadata visual de orientacion cabeza con cabeza
- render diferenciado de TAPA, TRIPA, frente/dorso y VYV

Limites:

- no modifica `layout_constructor.json`
- no crea `slots[]`
- no toca Step & Repeat PRO
- no genera preview ni PDF final

### Fase 7. Estabilidad y validacion de salida

Estado real:

- Fase 7.1 agrega tests de contrato de salida en `tests/test_editor_offset_output_contract.py`
- Fase 7.2 extrae la validacion backend a `services/editor_offset_output_contract.py`
- `routes.py` conserva alias compatible para `_validate_constructor_output_layout`
- no cambia JSON, contratos, preview/PDF, frontend JS ni motores
- se agrega una mejora visual safe en CSS para botones, paneles, accordion y foco visible

Objetivo cerrado:

- blindar la validacion backend actual sin agregar reglas nuevas
- reducir deuda en `routes.py` de forma conservadora
- dejar base testeable para futuras validaciones
- mejorar lectura visual del editor sin tocar comportamiento

### Fase 8. Arquitectura SAFE y UX shell

Estado real:

- Fase 8.0 completada: mapa funcional/técnico del Editor Visual IA.
- Fase 8.1 completada: `services/editor_offset_jobs.py`, `services/editor_offset_layout_defaults.py`, `services/editor_offset_uploads.py`.
- Fase 8.1B completada: `engines/step_repeat_pro_engine.py` y `tests/test_step_repeat_pro_engine.py`.
- Fase 8.1C completada: `services/editor_offset_imposition_service.py`.
- Fase 8.2 completada: shell UX profesional con toolbar sticky, canvas central y panel derecho con scroll interno.
- Fase 8.3 completada: tabs del panel derecho y fix de scroll.
- Premium Visual Pass SAFE completado: refinamiento visual CSS-only, densidad tecnica, contraste, canvas, toolbar, tabs, panel derecho, inputs y estados visuales.
- Microfase de contraste completada: Snap, Espaciado, labels secundarios, unidades mm, inputs tecnicos y botones claros.
- QA inicial completada:
  - `tests/playwright/test_editor_load.py`
  - `tests/playwright/test_tabs_scroll.py`

Garantias:

- `routes.py` conserva wrappers compatibles.
- no se cambiaron contratos JSON.
- no se cambio preview/PDF.
- no se tocaron motores de salida.
- no se toco JS funcional ni backend durante el premium visual pass.

Decision UX:

- no se agrego una barra inferior contextual nueva.
- `geometry-validation-panel` ya opera como area contextual/status parcial.
- cualquier status bar futura deberia evolucionar o compactar ese bloque, no duplicarlo.

### Fase 9. Redisenio panel editor, documentacion base y agente SDK

Estado real:

- rama actual: `fase9-redisenio-panel-editor`
- el panel derecho sigue evolucionando sobre la base de tabs/scroll interno de Fase 8
- se creo `ai_agent/editor_advisor/` como prototipo OpenAI Agents SDK
- el agente SDK es CLI-only/read-only, sin Flask, sin endpoints y sin UI
- el agente usa `AGENTS.md` y `DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md` como contexto arquitectonico clave
- Fase 9.2 completada: el agente SDK ahora actua como UX/UI SAFE Advisor del Editor Visual IA
- Fase 9.2 agrega `summarize_editor_ux_surface()` para detectar tabs, paneles, ids criticos, listeners, selectores sensibles y `geometry-validation-panel`
- Fase 9.2 clasifica cambios como `CSS-only seguro`, `HTML/DOM riesgoso`, `JS/listeners riesgoso` y `backend/contrato prohibido`
- Fase 9.3 completada: refinamiento visual CSS-only del panel derecho, aplicado solo sobre `static/css/editor_offset_visual.css`
- Fase 9.3 mejora `.side-panel`, `.editor-tabs`, scroll interno, accordions, formularios, `geometry-validation-panel`, foco visible y estetica premium tecnica sin cambiar DOM ni listeners
- Fase 9.4 completada: el agente genera `prompt_para_codex` para convertir auditorias en prompts SAFE listos para Codex
- Fase 9.4 agrega `--codex-prompt-only` para imprimir solo el prompt accionable, sin JSON

Prioridades SAFE:

- mantener documentacion base alineada con el codigo real
- no integrar `editor_advisor` a Flask/UI sin fase separada
- no permitir que `editor_advisor` escriba archivos ni modifique HTML/JS automaticamente
- sostener workflow: agente audita -> genera prompt SAFE para Codex -> Codex planifica -> Codex implementa solo si se aprueba -> validaciones -> agente vuelve a auditar
- ampliar Playwright para drag, resize, seleccion y flujos productivos
- evolucionar `geometry-validation-panel` solo si aporta valor y sin duplicar informacion
- evaluar inspector contextual y modularizacion frontend como cambios separados

### Fase 10. Editor UX Canvas Pro

Estado real:

- Fase 10.0 completada: auditoria visual y baseline sin modificar archivos.
- Fase 10.1 completada: refinamiento CSS-only del shell superior/topbar/subtoolbar para dar mas protagonismo al canvas.
- Fase 10.2 completada: refinamiento CSS-only de density del panel derecho, manteniendo tabs, scroll interno, ids y listeners.
- Fase 10.3 completada: `ai_agent/editor_advisor/` incorpora UX Surface v2; `summarize_editor_ux_surface()` ahora audita header, topbar, subtoolbar, workspace, canvas, zoom, panel derecho, ids por zona y listeners sensibles.
- Fase 10.4 completada: QA visual y regresion documentation-safe; `git diff --check`, `python -m compileall ai_agent`, `tests/test_editor_advisor_tools.py` con `12 passed`, revision estatica de selectores criticos y `geometry-validation-panel` unico.

Garantias:

- no se cambiaron contratos JSON.
- no se tocaron HTML, JS, Flask, services, engines, Step & Repeat PRO, preview/PDF, CTP ni cuadernillos.
- `editor_advisor` sigue CLI-only/read-only, sin Flask/UI/endpoints ni escritura.
- Playwright manual funciona desde Git CMD; `WinError 5` queda registrado solo como bloqueo del entorno Codex.

### Fase 11 futura. Canvas Geometry Polish

Objetivo futuro:

- pulir la lectura geometrica y visual del canvas sin cambiar contratos ni motores.
- mantener como base el shell Fase 10 y el `geometry-validation-panel` unico.
- separar cualquier cambio HTML/JS o de interaccion en fases SAFE especificas.

## Priorizacion sugerida

1. Mantener documentados los contratos despues de cada cambio de semantica
2. Ampliar pruebas de regresion para Step & Repeat PRO inteligente
3. Ampliar Playwright para drag, resize, seleccion y flujos productivos antes de mas cambios UX grandes
4. Endurecer guardrails y pruebas del flujo OpenAI tool calling sobre `ai_agent/`
5. Mantener `ai_agent/editor_advisor` aislado, read-only y CLI-only hasta definir integracion, aunque genere prompts para Codex
6. Mejorar feedback no bloqueante de errores/warnings
7. Avanzar en schema/validaciones adicionales solo con tests dedicados
8. Evaluar sistema de modos (`exact`, `maximize`, etc.) sin romper el contrato actual
9. Evaluar compactacion o expansion horizontal solo si mantiene seguridad
10. Mantener el simulador de cuadernillos aislado hasta definir una integracion PDF explicita
11. Avanzar Fase 11 `Canvas Geometry Polish` como siguiente fase futura, sin mezclar contratos, motores ni integracion del agente SDK

## Cambios explicitamente postergados

- fusionar todos los motores offset
- borrar rutas legacy
- mover muchas funciones fuera de `routes.py` sin tests; Fase 7 solo extrajo el validador de salida con cobertura dedicada
- reescribir el JS del editor
- modularizar frontend monolitico sin fase propia y pruebas de regresion
- redisenar persistencia por job
- permitir que IA modifique persistencia sin confirmacion del usuario
- integrar `ai_agent/editor_advisor` a Flask/UI sin fase tecnica separada, guardrails y tests
- cambiar el contrato base de `layout_constructor.json` sin migracion
- documentar `preferred_flow` como funcional antes de implementarlo
- declarar soporte de expansion horizontal `left/right` antes de tener motor y pruebas
- convertir el simulador de cuadernillos en generador de PDF sin fase tecnica separada
- persistir resultados del simulador en el layout sin contrato previo
- agregar una barra inferior contextual que duplique `geometry-validation-panel` sin redisenio previo

## Criterio de seguridad para siguientes pasos

Todo cambio futuro en este modulo deberia responder antes:

- afecta solo `/editor_offset_visual` o tambien otro flujo offset
- toca contrato de `layout_json`
- cambia semantica de slot/bleed/face/ctp
- modifica salida final de `montaje_offset_inteligente.py`

Si alguna respuesta es "si", conviene abrir subtarea especifica y documentarla antes de editar.

Para nuevas validaciones posteriores a Fase 7:

- agregar primero tests de contrato
- no cambiar textos, `code`, `path`, `value` ni estructura de errores sin fase explicita
- mantener preview/PDF consumiendo el layout persistido desde disco
