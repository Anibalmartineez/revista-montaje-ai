# 04 PLAN OFFSET

## Objetivo de esta etapa

Consolidar el Editor Visual IA como flujo operativo profesional del modulo Offset, manteniendo compatibilidad con el layout existente y evitando refactors amplios.

## Etapa actual

- Fase 4 nueva: `fase4-editor-offset-pro`
- Sin refactor masivo
- Sin limpieza agresiva
- Sin eliminacion de archivos
- Cambios acotados sobre Editor Visual IA y correcciones puntuales de repeat/salida final
- Foco en:
  - herramientas profesionales de edicion manual
  - estabilidad de Step & Repeat PRO
  - UX de seleccion y toolbar
  - base de agente IA desacoplada

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
- panel "Asistente IA" integrado al editor

### Fase 4 siguiente. IA operativa guiada

Objetivo:

- mantener la capa `ai_agent/` como intermediaria entre UI, LLM y funciones reales
- conectar OpenAI tool calls sin permitir que el LLM modifique layout directamente
- ampliar tools con acciones verificables y reversibles
- registrar respuestas y sugerencias de forma no destructiva hasta que el usuario aplique cambios

### Fase 5. Refactor pequeno y seguro

Solo despues de cerrar Fase 1 a Fase 4:

- extraer helpers pequeños con cobertura
- aislar naming y contratos
- reducir duplicacion con cambios minimos

## Priorizacion sugerida

1. Mantener documentados los contratos despues de cada cambio de semantica
2. Agregar fixtures o pruebas de regresion para Step & Repeat PRO
3. Conectar OpenAI tool calls sobre `ai_agent/`
4. Mejorar feedback no bloqueante de errores/warnings
5. Recien despues evaluar micro-refactors

## Cambios explicitamente postergados

- fusionar todos los motores offset
- borrar rutas legacy
- mover muchas funciones fuera de `routes.py`
- reescribir el JS del editor
- redisenar persistencia por job
- permitir que IA modifique persistencia sin confirmacion del usuario
- cambiar el contrato base de `layout_constructor.json` sin migracion

## Criterio de seguridad para siguientes pasos

Todo cambio futuro en este modulo deberia responder antes:

- afecta solo `/editor_offset_visual` o tambien otro flujo offset
- toca contrato de `layout_json`
- cambia semantica de slot/bleed/face/ctp
- modifica salida final de `montaje_offset_inteligente.py`

Si alguna respuesta es "si", conviene abrir subtarea especifica y documentarla antes de editar.
