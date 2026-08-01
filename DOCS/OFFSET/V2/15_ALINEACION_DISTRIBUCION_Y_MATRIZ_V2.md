# Fase 8C — Alineación, distribución, gap exacto y matriz

## 1. Objetivo y alcance

La Fase 8C añade herramientas deterministas de composición manual al Editor
Offset Visual V2. Opera exclusivamente en frontend sobre Layout V2 ya cargado y
no cambia backend, schema, versión de layout, Repeat, assets, output, PDF, CTP ni
Editor V1.

Incluye alineación, centrado, distribución, gap exacto y matriz. No incluye
snap, guías, reglas, medición, resize, grupos persistentes, transformaciones del
artwork, navegación de caras ni auto-fit.

## 2. Arquitectura reutilizada

La intención entra por el `ActionRegistry`; `arrangement_panel.js` no muta el
layout. Las operaciones puras viven en `alignment_operations.js`, producen un
plan before/after y las mutaciones geométricas usan el `MoveSlotsCommand`
existente. La matriz prepara copias y usa un único `DuplicateSlotsCommand`.

Se conservan un solo `EditorStore`, historial, selección, política de locks,
`ShortcutManager`, `SaveCoordinator` y flujo de persistencia. Los botones usan
IDs registrados; no contienen una ruta paralela de mutación.

## 3. Acciones registradas

Estado temporal:

```text
selection.key_slot.set
selection.key_slot.clear
```

Geometría:

```text
selection.align.left
selection.align.horizontal_center
selection.align.right
selection.align.top
selection.align.vertical_center
selection.align.bottom
selection.center.horizontal
selection.center.vertical
selection.center.both
selection.distribute.horizontal
selection.distribute.vertical
selection.gap.horizontal
selection.gap.vertical
selection.matrix.create
```

No se añadieron atajos globales. La ayuda `?` continúa derivándose únicamente
de atajos activos.

## 4. Modelo de comandos y atomicidad

- Alinear, centrar, distribuir y gap exacto generan como máximo un
  `MoveSlotsCommand`.
- Matriz genera un `DuplicateSlotsCommand` con todas las copias preparadas.
- Un no-op no crea comando, historial, dirty ni autosave.
- Un gesto válido crea una entrada de undo y un ciclo normal de autosave.
- Los mapas before/after contienen únicamente slots que cambian.
- `MoveSlotsCommand` vuelve a validar `move` al ejecutar y al rehacer.
- `selectionBefore` y `selectionAfter` conservan la selección de operaciones
  geométricas; matriz selecciona solo las copias y undo restaura las fuentes.

## 5. Centro trim, referencias y bounds

`slot.geometry.position_mm` continúa siendo el centro trim canónico, en
milímetros, con origen inferior izquierdo, X hacia la derecha e Y hacia arriba.
Toda operación calcula un centro nuevo; nunca escribe bounds ni footprint.

La referencia **Trim** usa `GeometryView.trimBounds()`. La referencia
**Footprint productivo** usa `GeometryView.bleedBounds()`, es decir, trim más
bleed uniforme antes de la rotación cardinal. En 90°/270° se intercambia el
tamaño orientado; 0°/180° lo conserva. La elección es temporal y no modifica el
slot.

Los aggregate bounds se derivan del layout, no del DOM. No se usa
`getBoundingClientRect()` ni se redondean las posiciones persistidas. La
tolerancia de no-op es `1e-9 mm`, exclusivamente numérica.

## 6. Slot clave temporal

El Store mantiene `arrangement.keySlotId` fuera de Layout V2. El slot clave:

- debe estar seleccionado y pertenecer a `activeFace`;
- es único;
- se limpia al salir de la selección, desaparecer o dejar de pertenecer a la
  cara activa;
- no es un lock;
- no genera comando, dirty, autosave ni revisión;
- aparece en panel con ordinal/ID y en canvas mediante badge `K`, tooltip y
  estilo no dependiente solo del color.

Si el slot clave es referencia fija, su propio lock geométrico no bloquea. Solo
se validan los slots que realmente se moverán.

## 7. Destinos de alineación y centrado

### Selección

Requiere dos o más slots. Cada slot alinea el borde o centro elegido contra el
aggregate bounds previo. Puede superponer objetos deliberadamente.

### Slot clave

Requiere clave y otro slot. La clave permanece fija; los demás alinean bordes o
centros respecto a sus bounds. Una clave bloqueada es válida porque no cambia.

### Pliego

Usa `[0,width] × [0,height]`. La selección se mueve como grupo y conserva todas
las distancias relativas.

### Área imprimible

Usa `sheet.printable_margins_mm` mediante `GeometryView.printableBounds()`. No se
confunde con el pliego ni se recalcula. También mueve el grupo completo.

El centrado horizontal, vertical o total aplica la misma semántica del destino.
Un solo slot puede centrarse en pliego o área imprimible, pero no respecto a la
propia selección.

## 8. Distribución horizontal y vertical

La distribución requiere tres o más slots.

Horizontalmente se ordena por `minX`; verticalmente, de arriba abajo por `maxY`
descendente en coordenadas canónicas. Los empates se resuelven por orden de
`slots[]` y luego ID.

Con destino selección, los endpoints geométricos quedan fijos y solo cambian
los interiores. Con pliego o área imprimible, el primer y último slot se llevan
a los bordes del contenedor y los interiores completan el span. El gap es:

```text
(span - suma de tamaños en el eje) / (cantidad - 1)
```

El resultado puede ser negativo. Se conserva de forma determinista y se avisa
que existe solapamiento potencial; no se corrige automáticamente. Slot clave no
es un destino de distribución en 8C.

## 9. Gap exacto

Los formularios aceptan punto o coma decimal, espacios exteriores, cero y
números finitos mayores o iguales a cero. Rechazan vacío, negativos, texto,
NaN, infinito y separadores múltiples.

Horizontal avanza visualmente hacia `+X`. Vertical usa orden de arriba abajo y
avanza hacia `-Y` canónica. Los anclajes son:

- **Inicio:** primer slot horizontal o superior fijo;
- **Final:** último slot horizontal o inferior fijo;
- **Slot clave:** clave fija, anteriores hacia izquierda/arriba y posteriores
  hacia derecha/abajo.

El orden relativo no cambia. No hay snap, auto-fit ni restricción al pliego.

## 10. Matriz, celda y pitch

La selección completa es la celda fuente de fila 1, columna 1. Sus originales
no se mueven. La celda usa aggregate bounds trim o footprint según la referencia
activa:

```text
pitch X = ancho de celda + gap X
pitch Y = alto de celda + gap Y
columna siguiente = +X
fila siguiente = -Y canónica
```

Cada celda adicional duplica toda la selección y conserva posiciones internas,
work, cara, source efectivo, trim, bleed, rotación, `content_transform`, locks y
metadata válida.

Filas/columnas deben ser enteros mayores o iguales a 1, al menos una dimensión
debe superar 1 y ambos gaps son finitos no negativos. El resumen informa
fuentes, celdas y slots nuevos antes de aplicar.

## 11. IDs, procedencia y orden

`prepareDuplicateSlotsFromSlots()` continúa siendo la única fábrica de copias.
Se generalizó únicamente para aceptar un `Set` compartido de IDs reservados
entre celdas. Cada copia recibe un ID nuevo una sola vez y:

```json
{
  "type": "duplicate",
  "source_slot_id": "<slot fuente>"
}
```

No conserva `engine` ni `operation_id` de Repeat. `DuplicateSlotsCommand`
retiene las copias preparadas: undo las elimina y redo restaura los mismos IDs y
orden al final de `slots[]`. La selección final contiene solo las copias; undo
restaura la selección fuente.

## 12. Locks y límite de seguridad

Todas las transformaciones de posición usan capacidad `move` y
`locks.geometry`. Solo los IDs que cambian requieren permiso. Referencias y
endpoints fijos pueden estar bloqueados. Si un slot que debe cambiar contiene
`user`, `engine`, `ctp` o `system`, se rechaza todo el comando y el feedback
muestra ID y fuentes.

Duplicar lee los originales y preserva exactamente sus locks; esos locks no
bloquean la copia. Como no existía límite aplicable de slots/payload, la matriz
adopta un límite frontend conservador de **500 slots nuevos por operación**.

## 13. Estado temporal, UI y accesibilidad

La referencia geométrica, destino, slot clave y borradores de formularios no se
persisten. Escribir o cancelar no cambia `changeVersion`. Escape cancela el
borrador 8C mediante la acción central; Enter somete el formulario válido con
semántica nativa.

El panel usa botones semánticos, labels asociados, unidades visibles,
`aria-describedby`, `aria-invalid`, regiones `aria-live`, disabled real y texto
además de marcas visuales. Los inputs conservan sus teclas nativas y no reciben
atajos de alineación.

## 14. Tests

Node prueba referencias y cuatro rotaciones, aggregate bounds, ausencia de DOM
contractual, ciclo del slot clave, seis alineaciones, cuatro destinos, mixed
sizes, locks, no-op, undo/redo, distribución H/V, gap negativo, tres anclajes,
parseo, matriz, IDs, procedencia, contenido, locks, límite y registro de
acciones.

Playwright crea un job real, sube PDF, crea work, aplica Repeat y recorre panel,
trim, alineación, undo/redo, clave visible, pliego, área imprimible,
distribución, gap punto/coma e inválido, rechazo por lock, matriz 2×3,
undo/redo con IDs estables, guardado/recarga, inputs, ayuda, capabilities,
ordinales, panel 8B y ausencia de árbol 8D.

## 15. Límites y próxima fase

No hay ghost preview geométrico nuevo: alineación/distribución se aplican como
acciones discretas y los formularios muestran validación/resumen previo. Las
operaciones pueden dejar slots fuera del pliego y reutilizan las advertencias de
canvas existentes.

La próxima fase es **8D — Selección avanzada y árbol**. No debe reimplementar
las acciones 8C ni convertir el slot clave en estado persistente.
