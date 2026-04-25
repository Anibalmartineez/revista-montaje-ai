# 04 PLAN OFFSET

## Objetivo de esta etapa

Consolidar el Editor Visual IA como flujo operativo profesional del modulo Offset, manteniendo compatibilidad con el layout existente y evitando refactors amplios.

## Etapa actual

- Rama actual documentada: `fase5-step-repeat-inteligente`
- Sin refactor masivo
- Sin limpieza agresiva
- Sin eliminacion de archivos
- Cambios acotados sobre Editor Visual IA y Step & Repeat PRO
- Foco real de esta etapa:
  - automatizacion del motor repeat por diseno
  - zonas preferidas reales como preferencia de inicio
  - UI de disenos simplificada
  - mejor aprovechamiento de huecos con `fill`
  - compactacion vertical segura de grupos
  - expansion vertical segura de zonas como preferencia, no carcel
  - integracion de `auto` con grupos verticales
  - alineacion de IA/tools con el motor Fase 5

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

### Fase 6 sugerida. IA operativa sobre motor inteligente

Objetivo:

- consolidar guardrails y pruebas de la IA sobre controls estables del motor inteligente
- evitar que la IA manipule numerica o geometria sin validacion del motor
- usar `preferred_zone`, `forms_per_plate` y tools repeat como superficie principal
- dejar packing complejo y optimizaciones profundas para una fase posterior

## Priorizacion sugerida

1. Mantener documentados los contratos despues de cada cambio de semantica
2. Agregar fixtures o pruebas de regresion para Step & Repeat PRO inteligente
3. Endurecer guardrails y pruebas del flujo OpenAI tool calling sobre `ai_agent/`
4. Mejorar feedback no bloqueante de errores/warnings
5. Evaluar sistema de modos (`exact`, `maximize`, etc.) sin romper el contrato actual
6. Evaluar compactacion o expansion horizontal solo si mantiene seguridad
7. Recien despues evaluar micro-refactors

## Cambios explicitamente postergados

- fusionar todos los motores offset
- borrar rutas legacy
- mover muchas funciones fuera de `routes.py`
- reescribir el JS del editor
- redisenar persistencia por job
- permitir que IA modifique persistencia sin confirmacion del usuario
- cambiar el contrato base de `layout_constructor.json` sin migracion
- documentar `preferred_flow` como funcional antes de implementarlo
- declarar soporte de expansion horizontal `left/right` antes de tener motor y pruebas

## Criterio de seguridad para siguientes pasos

Todo cambio futuro en este modulo deberia responder antes:

- afecta solo `/editor_offset_visual` o tambien otro flujo offset
- toca contrato de `layout_json`
- cambia semantica de slot/bleed/face/ctp
- modifica salida final de `montaje_offset_inteligente.py`

Si alguna respuesta es "si", conviene abrir subtarea especifica y documentarla antes de editar.
