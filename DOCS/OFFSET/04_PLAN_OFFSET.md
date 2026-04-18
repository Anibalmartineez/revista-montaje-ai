# 04 PLAN OFFSET

## Objetivo de esta etapa

Mapear y estabilizar el flujo real del editor visual IA antes de hacer cambios estructurales.

## Etapa actual

- Sin refactor masivo
- Sin limpieza agresiva
- Sin eliminacion de archivos
- Sin cambio de logica de negocio

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

### Fase 4. Auditoria tecnica puntual

- revisar coherencia de:
  - bleed
  - crop marks
  - `forms_per_plate`
  - `face`
  - `rotation_deg`
  - `slot_box_final`
- detectar que reglas se resuelven en frontend y cuales en backend

### Fase 5. Refactor pequeno y seguro

Solo despues de cerrar Fase 1 a Fase 4:

- extraer helpers pequeños con cobertura
- aislar naming y contratos
- reducir duplicacion con cambios minimos

## Priorizacion sugerida

1. Documentar contrato del layout del editor
2. Documentar pipeline de preview/PDF
3. Documentar diferencia entre editor nuevo y rutas legacy
4. Recien despues evaluar micro-refactors

## Cambios explicitamente postergados

- fusionar todos los motores offset
- borrar rutas legacy
- mover muchas funciones fuera de `routes.py`
- reescribir el JS del editor
- redisenar persistencia por job

## Criterio de seguridad para siguientes pasos

Todo cambio futuro en este modulo deberia responder antes:

- afecta solo `/editor_offset_visual` o tambien otro flujo offset
- toca contrato de `layout_json`
- cambia semantica de slot/bleed/face/ctp
- modifica salida final de `montaje_offset_inteligente.py`

Si alguna respuesta es "si", conviene abrir subtarea especifica y documentarla antes de editar.
