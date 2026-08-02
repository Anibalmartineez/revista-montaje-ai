# Reglas, guías, snap y medición del Editor Offset Visual V2

## 1. Objetivo y alcance

La Fase 8E entrega una base geométrica frontend verificable y herramientas de
precisión para el canvas SVG: reglas, guías temporales, snap determinista, smart
guides, medición punto a punto y métricas de selección. No añade resize,
rotación libre, transformaciones internas, persistencia de preferencias ni
salida PDF.

## 2. Arquitectura reutilizada

Se mantienen un único `EditorStore`, selección, historial, `ActionRegistry`,
`ShortcutManager`, política de locks y flujo de mutación. `CanvasInteractions`
prepara previews; una confirmación documental sigue usando exactamente un
`MoveSlotsCommand` o `DuplicateSlotsCommand`. `PrecisionPanel` solo despacha
acciones centrales y lee derivados.

Los módulos incorporados son:

- `geometry_kernel.js`: geometría contractual pura en milímetros;
- `precision_tools.js`: ticks, parseo, guías, medición y métricas;
- `snap_engine.js`: captura y resolución determinista de targets;
- `precision_panel.js`: UI y accesibilidad del estado temporal.

`geometry_view.js` reutiliza el kernel y conserva únicamente área imprimible,
clasificación, zoom y conversión SVG.

## 3. Paridad geométrica Python/frontend

El kernel Python de referencia es `editor_offset_v2/domain/geometry.py`. Sus
tipos `Point`, `Size`, `Bounds`, `Polygon` y `SlotGeometry` se expresan en JS
como objetos inmutables y funciones puras. Ambos kernels cubren:

- validación finita, positiva y no negativa;
- cardinales exactos `0/90/180/270`, sin normalización silenciosa;
- tamaño productivo, orientación, rotación, polígonos trim/bleed y bounds;
- contención de punto/polígono/bounds, unión de bounds y SAT;
- overlap con área positiva, gaps firmados y distancias.

La tolerancia común es `1e-9 mm`, solo numérica. Contacto de borde o penetración
igual o menor a esa tolerancia no es overlap SAT. No es tolerancia productiva,
de PDF ni de seguridad.

`tests/fixtures/editor_offset_v2/geometry_cases.json` es la fuente compartida.
Incluye cuatro cardinales, bleed cero/positivo, tamaños distintos, decimales,
posiciones negativas, límites, overlap parcial/total, separación, containment,
gaps, distancia 3-4-5 y cercanía a tolerancia. Python y Node consumen esos
mismos resultados.

## 4. Coordenadas y frontera SVG

La geometría contractual usa origen inferior izquierdo, X positiva a la
derecha e Y positiva hacia arriba. La posición del slot es el centro trim.
Solo la frontera visual invierte Y:

```text
svgY = sheetHeight - domainY
domainY = sheetHeight - svgY
```

Zoom y pan modifican el `viewBox`, no las coordenadas contractuales. El umbral
de pantalla se convierte mediante la inversa del CTM vigente.

## 5. Reglas y ticks adaptativos

Las reglas horizontal y vertical y su esquina se renderizan dentro del SVG y
son decorativas fuera del orden de tab. X muestra valores crecientes a la
derecha; la regla vertical calcula y etiqueta Y canónica creciente hacia
arriba. Zoom y pan regeneran el rango visible.

Los pasos disponibles van de `0.1` a `500 mm`. El paso mayor se elige para
mantener aproximadamente 64 px entre etiquetas; el menor se degrada de quinto
a mitad o mayor cuando faltan píxeles. Cada regla queda limitada a 400 ticks,
incluidos rangos amplios o zoom bajo.

## 6. Guías temporales

Una guía tiene `{id, axis: "x" | "y", position_mm}`. Eje X es una guía
vertical; eje Y, una guía horizontal en Y canónica.

- arrastrar desde la regla horizontal crea guía vertical;
- arrastrar desde la regla vertical crea guía horizontal;
- el draft se ve durante el gesto y Escape/pointercancel lo descartan;
- soltar dentro del canvas y fuera de la banda de reglas confirma;
- una guía existente se mueve por drag; soltarla fuera del canvas la elimina;
- el panel permite crear y editar con punto, coma, signo y espacios;
- posiciones negativas o fuera del pliego no se corrigen ni redondean; el
  listado accesible permite gestionarlas aunque queden fuera del viewport;
- Enter aplica una edición; Escape o blur restauran el valor confirmado;
- Delete solo elimina cuando el foco pertenece explícitamente a la fila y el
  evento se consume antes del Delete global de slots.

Mostrar/ocultar reglas, guías o smart guides y todo el CRUD de guías afecta
solo `store.precisionTools`.

## 7. Snap y umbral de pantalla

Snap está desactivado por defecto y usa 6 px, configurables entre 1 y 24. La
conversión a milímetros se realiza con el CTM actual en cada movimiento, por lo
que la sensación se conserva al cambiar zoom.

La referencia geométrica no se duplica: usa
`store.arrangement.geometryReference`, compartida con 8C/8D:

- `trim`: bounds del trim cardinal;
- `productive`: bounds trim más bleed cardinal.

La selección movida se reduce a un único aggregate bounds. Sus anclas por eje
son mínimo, centro y máximo; el offset X/Y elegido se aplica como una sola
traslación, preservando distancias internas.

## 8. Fuentes, resolución y prioridades

Al iniciar drag o Alt+drag se capturan una sola vez:

1. guías visibles habilitadas;
2. bordes y centros del área imprimible real;
3. bordes y centros del pliego;
4. bordes y centros de otros slots visibles de `activeFace`.

Se excluyen `hiddenSlotIds`, slots movidos y slots de otra cara. La captura es
lineal; no se recorre el árbol en cada pointermove.

Para cada eje se consideran candidatos dentro del umbral. Gana la menor
distancia absoluta; en empate: guía, imprimible, pliego, slot; luego borde,
centro, orden de layout, ID y ancla. Se aplica como máximo un offset X y uno Y,
permitiendo snap simultáneo. El orden estable evita jitter sin hysteresis.

Snap actúa exclusivamente en drag normal, Alt+drag y, opcionalmente, puntos de
medición. No modifica nudge, inspector, alineación, distribución, gap, matriz,
rotación, paste ni operaciones programáticas exactas.

## 9. Smart guides

Cuando hay candidato activo se muestran una línea vertical y/o horizontal y
una etiqueta textual con fuente/tipo. Tienen `pointer-events: none`, tamaño de
texto adaptado al zoom y contraste por trazo, no solo color. Se eliminan al
confirmar, cancelar o desactivar su visualización. No se implementan todavía
guías de igualdad de gaps.

## 10. Drag, Alt+drag y locks

Los targets y bounds fuente se fijan al inicio. Pointermove solo resuelve
offsets y actualiza `previewPositions` o `previewSlots`; no recaptura el árbol
ni ejecuta análisis de pares. Marquee conserva su actualización visual por
`requestAnimationFrame`; el renderer compartido permanece síncrono para evitar
identidad DOM transitoria en los gestos existentes.

Durante preview no cambian layout, revision, dirty, autosave ni historial. Al
confirmar, drag crea un `MoveSlotsCommand`; Alt+drag crea un
`DuplicateSlotsCommand` con IDs ya preparados y locks preservados. Un no-op no
crea comando. Escape y pointercancel limpian preview y smart guides.

La política atómica `move` existente no cambia. Cualquier lock efectivo impide
el drag normal completo. Alt+drag lee originales sin mutarlos y conserva locks
en las copias.

## 11. Medición punto a punto

El botón activa un modo temporal. Primer click fija inicio; pointermove muestra
preview; segundo click confirma. Un click nuevo inicia otra medición. Escape
cancela el draft; Limpiar descarta draft/resultado; salir del modo descarta el
draft pero conserva el último resultado hasta limpiar o medir de nuevo.

Se muestran X1, Y1, X2, Y2, Delta X, Delta Y y distancia euclidiana en mm. Delta
Y usa dominio canónico, por lo que subir produce un valor positivo. Si snap
está activo, ambos puntos pueden ajustarse a targets capturados sin mover slots.

## 12. Métricas de selección

La referencia trim/footprint es compartida y los ocultos/otra cara se excluyen.

- un slot: centro, trim, footprint, rotación y bounds usados;
- dos slots: gaps firmados X/Y, delta y distancia de centros, profundidad de
  overlap, área de intersección de bounds e IDs;
- tres o más: aggregate bounds, ancho/alto, gap mínimo/máximo por eje y pares
  con overlap.

Para bounds A y B:

```text
gapX > 0 separación; gapX = 0 contacto; gapX < 0 profundidad de overlap X
gapY > 0 separación; gapY = 0 contacto; gapY < 0 profundidad de overlap Y
distance = hypot(max(gapX, 0), max(gapY, 0))
```

El panel informa overlap solo si ambas profundidades son positivas. Esta
medición visual usa bounds cardinales; SAT sigue siendo la semántica poligonal
precisa del kernel cuando resulte necesario.

Las métricas complejas se cachean por versión documental, selección,
referencia, visibilidad y cara. El análisis de pares no se ejecuta en cada
pointermove. Una prueba de 500 slots midió aproximadamente 90 ms para capturar
498 targets válidos en el entorno Node de desarrollo; es evidencia local, no
una garantía universal.

## 13. Dirty, autosave, persistencia y accesibilidad

`precisionTools` es estado editorial temporal. No se serializa, no incrementa
`changeVersion`, no cambia revision y no entra en undo/redo. Guardar y recargar
conserva posiciones/duplicados confirmados, pero reinicia reglas, guías, snap,
smart guides y mediciones.

El panel usa fieldsets, labels, unidades visibles, botones disabled reales,
`aria-live`, `aria-pressed`, errores asociados y listado de guías navegable por
teclado. Reglas no reciben foco; resultados y smart guides también tienen
representación textual.

## 14. Tests y límites

Python valida el fixture compartido contra el kernel de dominio. Node valida
paridad, reglas, estado temporal, fuentes/prioridades, trim/footprint,
multiselección, medición, métricas y 500 slots, además de todas las regresiones
8A–8D. Playwright recorre PDF real, Repeat, reglas, zoom/pan, guías por regla y
valor, edición segura, snap/undo/redo, Alt+drag, cancelación, medición,
métricas, guardado/recarga, output-capabilities y ausencia de UI 8F.

Quedan fuera: resize/handles, grid persistente, rotación libre, igualdad de
gaps, transformaciones internas, frente/dorso, preflight y motor PDF.

## 15. Próxima fase 8F

8F debe reutilizar este kernel y la conversión de umbral, pero primero fijar
anclas de resize, proporción, comportamiento cardinal, multiselección, locks y
exportabilidad. No debe persistir dimensiones derivadas ni confundir trim del
slot con transformación del artwork.
