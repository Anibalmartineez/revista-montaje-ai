# 11 HERRAMIENTAS EDICION PRO

## Objetivo

Documentar el estado actual de la edicion PRO del Editor Visual IA en Fase 4: herramientas manuales, acciones de bloque, seleccion avanzada y organizacion UX de la toolbar, sin tocar motores legacy ni romper el contrato persistido.

## Alcance implementado

Principalmente frontend del editor visual:

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`

Las tools IA y correcciones de repeat estan documentadas en los documentos de estado/diario/contratos. Este documento se enfoca en la experiencia de edicion del operador dentro del editor.

## Estado actual de la barra PRO

La toolbar PRO fue simplificada para separar uso frecuente de herramientas tecnicas.

### Acciones rapidas visibles

- seleccionar todo
- centrar bloque
- control `Paso` en mm
- nudge direccional

### Panel avanzado colapsable

Agrupa acciones menos frecuentes:

- alineacion relativa
- distribucion horizontal
- distribucion vertical

La reorganizacion no elimina listeners ni funciones previas. Solo reduce ruido visual en la barra principal.

## Herramientas manuales

### Alineacion de seleccion

Permite alinear dos o mas slots desbloqueados de la cara activa:

- izquierda
- centro horizontal
- derecha
- abajo
- centro vertical
- arriba

La alineacion usa el footprint real del slot:

- `slot.w_mm`
- `slot.h_mm`

No reinterpreta el tamano fuente del PDF.

### Distribucion de seleccion

Permite distribuir tres o mas slots desbloqueados:

- horizontalmente
- verticalmente

La distribucion conserva los extremos del bloque seleccionado y reparte el espacio libre entre slots.

### Nudge de precision

Permite mover la seleccion desbloqueada por pasos en milimetros:

- botones direccionales en la barra de edicion
- flechas del teclado cuando el foco no esta en un input
- `Shift` multiplica el paso por 10
- `Alt` reduce el paso a 0.1x

El paso base se define en el control `Paso`.

### Acciones multi-slot

Se amplio el comportamiento existente:

- duplicar ahora duplica todos los slots seleccionados
- borrar ahora elimina todos los slots seleccionados
- al duplicar grupos, las copias reciben un nuevo `group_id` y no quedan vinculadas al grupo original

## Herramientas de bloque

### Seleccionar todo

Permite seleccionar todos los slots de la cara activa.

Reglas:

- no selecciona slots de la otra cara
- actualiza `selectedSlots`
- actualiza `selectedSlot` con un primer slot consistente
- soporta `Ctrl/Cmd + A` cuando el foco no esta en inputs

### Centrado de bloque

Acciones implementadas:

- centrar horizontalmente
- centrar verticalmente
- centrar bloque completo

La herramienta calcula:

1. bounding box de la seleccion
2. area util del pliego desde `sheet_mm` y `margins_mm`
3. delta necesario para mover el grupo como bloque

La operacion conserva posiciones relativas entre slots y usa el footprint real:

- `slot.x_mm`
- `slot.y_mm`
- `slot.w_mm`
- `slot.h_mm`

## Seleccion por marco

Se agrego seleccion multiple por marco sobre el pliego.

### Comportamiento

- empieza con pointerdown sobre area vacia del pliego
- muestra un rectangulo visual azul semitransparente
- al soltar, selecciona slots de la cara activa que intersectan el marco
- si no hay modificador, reemplaza seleccion
- con `Shift`, `Ctrl` o `Cmd`, suma a la seleccion actual

### Compatibilidad

La seleccion por marco no reemplaza el drag de slots:

- pointerdown sobre slot mantiene comportamiento de seleccion/drag existente
- pointerdown sobre area vacia habilita box select
- usa umbral minimo de movimiento para evitar selecciones accidentales

### Semantica geometrica

La interseccion se calcula por bbox usando footprint real:

- `slot.w_mm / slot.h_mm` = caja final visible
- `rotation_deg` no cambia la caja externa

## Decisiones de seguridad

- los slots bloqueados no se mueven con alineacion, distribucion ni nudge
- las acciones de centrado editan solo slots desbloqueados seleccionados
- no se modifica el contrato persistido de `slots[]`
- no se agregan dependencias nuevas
- las herramientas visuales usan bounding boxes efectivas
- el panel IA aplica layout solo despues de confirmacion del usuario

## Relacion con Step & Repeat PRO

Estas herramientas operan sobre el resultado ya generado por motores como `repeat`, `nesting` o edicion manual.

Con la semantica consolidada de Fase 4:

- `slot.w_mm/h_mm` representa footprint final del slot
- `rotation_deg` representa orientacion del contenido
- las herramientas de seleccion, bbox, centrado y drag select trabajan sobre el footprint final

## Pendientes sugeridos de edicion PRO

1. Agregar panel de propiedades para edicion masiva de rotacion, bleed, marcas y lock.
2. Mejorar feedback no bloqueante en vez de `alert()`.
3. Evaluar guias visuales temporales durante alineacion/distribucion.
4. Agregar snap/guias inteligentes para futuras acciones de IA asistida.
