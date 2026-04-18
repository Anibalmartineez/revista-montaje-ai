# 11 HERRAMIENTAS EDICION PRO

## Objetivo

Inicio de Fase 4 para mejorar la edicion manual del Editor Visual IA con herramientas de precision operativa, sin tocar motores legacy ni cambiar la salida final.

## Alcance implementado

Solo frontend del editor visual:

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`

## Herramientas agregadas

### Alineacion de seleccion

Permite alinear dos o mas slots desbloqueados de la cara activa:

- izquierda
- centro horizontal
- derecha
- abajo
- centro vertical
- arriba

La alineacion usa la caja efectiva del slot, contemplando rotaciones de 90 y 270 grados como ya lo hace el editor para snap/render auxiliar.

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

## Decisiones de seguridad

- los slots bloqueados no se mueven con alineacion, distribucion ni nudge
- no se modifica el contrato persistido de `slots[]`
- no se agregan dependencias nuevas
- no se toca backend ni motores de imposicion/salida
- la geometria sigue basada en bounding boxes efectivas, no geometria rotada exacta

## Pendientes sugeridos

1. Agregar panel de propiedades para edicion masiva de rotacion, bleed, marcas y lock.
2. Agregar seleccion por marco/drag select dentro del pliego.
3. Mejorar feedback no bloqueante en vez de `alert()`.
4. Evaluar guias visuales temporales durante alineacion/distribucion.
