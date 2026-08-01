# Selección avanzada, árbol de objetos y visibilidad temporal V2

## 1. Objetivo y alcance

La Fase 8D incorpora selección espacial y por propiedades, ciclo de objetos
superpuestos, navegación jerárquica cara/work/slot y visibilidad temporal. Su
objetivo es hacer manejables montajes densos sin cambiar Layout V2 ni adelantar
reglas, guías, snap, resize, frente/dorso manual o salida PDF.

La implementación es exclusivamente frontend. No modifica backend, schema,
Repeat, output, Editor V1 ni dependencias.

## 2. Arquitectura reutilizada

8D conserva las fronteras existentes:

- `EditorStore.selection` sigue siendo la única fuente de selección;
- `ActionRegistry` sigue siendo la frontera común de botones y gestos;
- `CanvasInteractions` mantiene una sola sesión de puntero;
- `CanvasRenderer` mantiene el orden de `layout.slots[]`;
- `GeometryView` aporta bounds cardinales trim y footprint;
- el historial único continúa reservado a comandos documentales;
- `SaveCoordinator` solo observa cambios documentales.

`advanced_selection.js` concentra funciones puras de candidatos, rectángulos,
hit testing, similitud e issues actuales. `object_tree.js` deriva y presenta la
jerarquía sin duplicar selección ni mutar el layout.

## 3. Estado temporal

`store.advancedSelection` contiene:

- `marqueeMode`: `contain` o `intersect`;
- `marqueeRect`: preview durante el gesto;
- `hiddenSlotIds`: conjunto de slots temporalmente ocultos;
- `previousHiddenSlotIds`: una instantánea para restaurar visibilidad;
- `visibilityVersion`: señal de actualización visual;
- `expandedFaceIds` y `expandedWorkIds`;
- `knownWorkIds`, usado para abrir por defecto works incorporados después del
  arranque sin reabrir los contraídos por el operador;
- `treeAnchorSlotId`: ancla temporal de rango;
- `cycle`: punto, candidatos, índice y versión usados por Alt+click.

La referencia geométrica y el slot clave continúan en `store.arrangement`. Todo
este estado queda fuera de `store.layout`, no incrementa revisión, no entra en
undo/redo y no activa autosave.

## 4. Referencia Trim/Footprint

Marquee, hit testing, ciclo e issues geométricos usan la misma preferencia
`arrangement.geometryReference` de 8C:

- `trim`: `GeometryView.trimBounds(slot)`;
- `productive`: `GeometryView.bleedBounds(slot)`.

No existe una segunda preferencia. En rotaciones 0/90/180/270, `GeometryView`
intercambia las dimensiones orientadas y mantiene el centro trim canónico. El
modo productivo incluye el bleed uniforme vigente.

## 5. Marquee: inclusión, intersección y modificadores

El gesto empieza únicamente desde fondo del canvas con la herramienta Select.
Captura al inicio los bounds de slots visibles de `activeFace`; por ello el
resultado permanece determinista aunque haya renders durante el movimiento.

- **Inclusión (`contain`)**: selecciona un slot solo si su referencia completa
  queda dentro del rectángulo.
- **Intersección (`intersect`)**: selecciona si ambos rectángulos se tocan o
  comparten área, con la tolerancia numérica del frontend.
- sin modificador: reemplaza;
- Shift: agrega;
- Ctrl/Cmd: alterna;
- Alt desde fondo: sustrae.

El umbral es 4 px de cliente. Por debajo se trata como click vacío: solo el modo
replace limpia la selección. La caja se dibuja con `requestAnimationFrame` y se
cancela con Escape, `pointercancel` o pérdida de foco. Space+drag conserva pan;
drag sobre slot conserva movimiento; Alt+drag sobre slot conserva duplicado.

## 6. Ciclo de slots superpuestos

Alt+click sobre un slot, sin superar el umbral de drag, ejecuta
`selection.cycle_at_point`. El hit testing geométrico considera únicamente
slots visibles de la cara activa y recorre `layout.slots[]` en sentido inverso:
el último renderizado es el primero del ciclo.

Clicks repetidos en el mismo punto avanzan y vuelven al inicio. El ciclo se
reinicia si cambia el punto más allá de la tolerancia, el layout, la cara o la
visibilidad. Shift+Alt conserva selección previa y agrega el candidato; Alt
solo reemplaza. El feedback indica la posición dentro del ciclo. Un movimiento
que supera el umbral sigue siendo Alt+drag y crea un duplicado, no un ciclo.

## 7. Selección por propiedades

Las acciones parten de todos los slots seleccionados y producen la unión de
coincidencias visibles en `activeFace`:

- work por `work_id`;
- asset efectivo mediante `SourceSemantics.effectiveSource`, incluido override;
- tamaño trim no orientado `width/height`, con tolerancia numérica `1e-9 mm`;
- rotación cardinal normalizada;
- procedencia por `generated_by.type`.

Las acciones existentes de cara, work y asset también excluyen ocultos. No se
crean grupos persistentes.

## 8. Selección por locks e issues actuales

Los filtros de locks consultan las superficies vigentes `geometry`, `content`
y `delete`. Un slot coincide si la lista contiene cualquier fuente `user`,
`engine`, `ctp` o `system`; cada ID se devuelve una sola vez.

Los problemas geométricos se recalculan desde el layout actual, nunca desde
issues históricos ni desde la respuesta asíncrona de output:

- fuera del pliego;
- fuera del área imprimible pero dentro del pliego;
- participante de overlap;
- unión de los anteriores.

La contención reutiliza bounds y área imprimible de `GeometryView`. El overlap
usa los bounds cardinales de la referencia elegida; contacto de borde no es
overlap. Todos los filtros se limitan a slots visibles de `activeFace`.

## 9. Árbol cara/work/slot

El panel presenta una jerarquía derivada, sin IDs ni orden alternativos:

```text
cara, en el orden de layout.faces.enabled
  work, en el orden de layout.works
    slot, en el orden de layout.slots
```

La cara activa es operable. Otras caras aparecen como resumen deshabilitado
hasta la fase de frente/dorso. Los slots muestran ordinal corto, rotación,
estado oculto, slot clave `K`, locks e issue actual; el tooltip conserva ID,
work y asset completos. No hay reorder ni drag-and-drop.

Canvas y árbol llaman a `store.setSelection`; `aria-selected` y el resaltado
SVG se derivan del mismo Set. Click reemplaza, Ctrl/Cmd+click alterna y
Shift+click selecciona un rango limitado al mismo work y cara desde
`treeAnchorSlotId`. Seleccionar cara o work usa acciones centrales y solo
incluye visibles.

## 10. Accesibilidad y expandido

El contenedor usa `role=tree`; sus nodos usan `role=treeitem`, `aria-level`,
`aria-expanded`, `aria-selected` y `aria-disabled`. Un único listener delegado
por tipo de evento evita crecimiento por cantidad de slots.

Teclado soportado:

- Arrow Up/Down: nodo visible anterior/siguiente;
- Home/End: primero/último;
- Arrow Right: expandir o entrar al primer hijo;
- Arrow Left: contraer o volver al padre;
- Enter/Espacio: activar selección.

Expandir/contraer solo controla presentación del árbol. Nunca equivale a
mostrar/ocultar. Los works nuevos se abren por defecto una vez; una contracción
explícita se conserva durante la sesión.

## 11. Visibilidad temporal

`hiddenSlotIds` es la única fuente de visibilidad 8D. Ocultar retira el slot del
canvas, lista plana, hit testing, marquee, ciclo y filtros, pero el objeto sigue
en `layout.slots[]` y en el árbol.

Acciones disponibles:

- ocultar seleccionados;
- aislar selección (ocultar los demás visibles de la cara activa);
- mostrar todos;
- restaurar la instantánea anterior;
- alternar un slot;
- alternar todos los slots de un work.

La visibilidad del work es derivada: `visible`, `hidden` o `mixed`. No se
persiste un flag separado. Antes de cada operación se guarda una sola
instantánea anterior suficiente para restaurar el estado previo.

Ocultar elimina esos IDs de la selección y limpia `arrangement.keySlotId` si la
clave quedó oculta. Un slot oculto no entra en Ctrl/Cmd+A. Mostrarlo no lo
selecciona automáticamente. Al recargar se crea un Store nuevo y todos los
slots vuelven visibles.

## 12. Acciones centralizadas

8D registra acciones `selection.select_same_size`,
`selection.select_same_rotation`, `selection.select_same_provenance`, los tres
filtros `selection.select_locked_*`, los cuatro filtros geométricos,
`selection.marquee.mode.set`, `selection.cycle_at_point`, selección visible por
cara/work y las seis acciones `visibility.*`. La UI no muta layout ni Sets
directamente.

## 13. Rendimiento, dirty y persistencia

Las búsquedas usan Sets/Maps para identidad y deduplicación. Marquee captura
candidatos una vez por gesto y el árbol usa listeners delegados constantes. El
caso Node de 500 slots verifica resultado determinista, jerarquía derivable y
cero mutaciones documentales. El diagnóstico de overlaps es cuadrático sobre
los slots visibles de la cara activa; es aceptable para el límite actual y debe
revisarse antes de escalar montajes muy superiores.

Selección, marquee, ciclo, expansión y visibilidad no llaman `markChanged`, no
crean comandos, no alteran `changeVersion`, revisión, undo/redo ni autosave. El
guardado serializa exclusivamente Layout V2; tras recarga no persisten
selección, modo, expansión, ancla, ciclo, ocultos, aislamiento ni slot clave.

## 14. Tests y límites

Node cubre estado temporal, ambos modos de marquee, modificadores, referencias,
rotaciones, bleed, cara/ocultos, ciclo, similitud, locks, issues, jerarquía,
rango, visibilidad, acciones y 500 slots. Playwright recorre un job real con PDF,
work y Repeat, verifica gestos, árbol, slot clave, visibilidad, guardado/recarga,
paneles 8B/8C, output-capabilities, ordinales y consola limpia. La suite previa
protege drag, Alt+drag, rotación, clipboard, locks, alineación, gap, matriz y
atajos en inputs.

Límites deliberados: hit testing e issues usan bounds cardinales, no SAT
poligonal frontend; no hay reorder, capas, grupos, filtros persistentes,
opacidad, resize, reglas, guías, snap, medición, transformación interna,
navegación manual de cara, preflight ni salida PDF.

## 15. Próxima fase

La siguiente fase es **8E — Reglas, guías, snap y medición**. Debe ampliar la
paridad geométrica frontend y reutilizar `hiddenSlotIds`, selección, referencia
Trim/Footprint, árbol, ActionRegistry y sesiones de puntero, sin convertir guías
temporales en Layout V2 ni adelantar resize.
