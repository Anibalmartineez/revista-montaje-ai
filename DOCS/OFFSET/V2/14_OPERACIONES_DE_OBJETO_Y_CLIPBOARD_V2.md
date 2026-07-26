# Fase 8B — Operaciones de objeto y clipboard interno

## 1. Estado

La Fase 8B está **implementada y validada** en la rama
`feat/editor-offset-v2-object-operations`.

Esta fase incorpora operaciones manuales de objeto sobre la arquitectura V2
existente. No cambia el schema Layout V2, el backend, los motores de imposición,
Repeat, el adaptador de salida, PDF, CTP, V1 ni dependencias.

## 2. Alcance completado

- rotación cardinal `0/90/180/270`;
- rotación incremental `+90°` y `-90°`;
- duplicado por acción y `Ctrl/Cmd+D`;
- clipboard interno con copiar, cortar y pegar;
- pegados sucesivos con desplazamiento acumulado;
- eliminación centralizada en `ActionRegistry`;
- duplicado interactivo mediante `Alt+arrastrar`;
- selección de todos los slots de la cara activa;
- selección por work;
- selección por asset efectivo del slot;
- locks de usuario para geometría, contenido y eliminación;
- estados de lock `ninguno`, `todos` y `mixto`;
- undo/redo, dirty y autosave coherentes;
- ayuda de atajos y protección de controles editables;
- cobertura Node y Playwright.

## 3. Decisiones de contrato

### 3.1 Rotación

La rotación manual edita exclusivamente
`slot.geometry.rotation_deg`. Los únicos valores persistibles son:

```text
0 | 90 | 180 | 270
```

La operación:

- conserva el centro trim en `position_mm`;
- conserva `trim_size_mm`;
- conserva `bleed_mm`;
- conserva `source`;
- conserva `content_transform`;
- no intercambia width/height persistidos;
- no modifica `work.allowed_rotations_deg`.

`allowed_rotations_deg` continúa describiendo restricciones o preferencias del
work para propuestas automáticas. No se convirtió en una restricción general de
edición manual porque el contrato V2 ya admite todas las rotaciones cardinales
en slots.

### 3.2 Duplicado

Cada copia conserva los datos productivos y referencias del slot fuente, salvo:

- `id`, que siempre es nuevo y único;
- `geometry.position_mm`, desplazado;
- `generated_by`, reemplazado por:

```json
{
  "type": "duplicate",
  "source_slot_id": "<slot-origen>"
}
```

No se arrastra el engine ni el operation ID histórico de Repeat como procedencia
de la copia. El slot original permanece intacto.

El duplicado estándar aplica:

```text
x = x original + 5 mm
y = y original - 5 mm
```

El comando prepara los IDs una sola vez. Undo elimina exactamente las copias y
redo restaura los mismos IDs.

### 3.3 Clipboard

El clipboard es interno al Editor V2 y no usa el portapapeles del sistema como
contrato de datos. Vive fuera de `layout` y contiene:

- `job_id` de origen;
- cara activa de origen;
- snapshot profundo e inmutable de los slots copiados;
- contador de pegados.

Copiar:

- no modifica el layout;
- no crea historial;
- no activa dirty;
- no activa autosave;
- reinicia el contador de pegados.

Pegar valida:

- mismo job;
- cara activa compatible;
- work existente;
- asset existente;
- página existente;
- caja PDF existente cuando corresponde.

Cada pegado genera IDs nuevos y un único comando reversible. El desplazamiento
se calcula desde los originales del clipboard:

```text
pegado 1: +5 mm X / -5 mm Y
pegado 2: +10 mm X / -10 mm Y
pegado n: +(5 × n) mm X / -(5 × n) mm Y
```

Cortar primero valida atómicamente `locks.delete`. Si algún slot está bloqueado,
no elimina nada y tampoco reemplaza el clipboard anterior. Si es válido, copia y
ejecuta un único `DeleteSlotsCommand`. Undo restaura slots y selección, mientras
el clipboard permanece disponible.

## 4. Selecciones básicas

Las selecciones 8B son temporales: no generan comandos, dirty ni autosave.

- **Todos · cara:** selecciona todos los slots de `activeFace`.
- **Mismo work:** toma los work IDs de la selección y selecciona su unión en la
  cara activa.
- **Mismo asset:** usa `slot.source.asset_id`, es decir, la fuente efectiva del
  slot y no el asset predeterminado del work.

La navegación operativa de dorso continúa fuera de alcance; por eso estas
acciones no seleccionan objetos invisibles de otra cara.

## 5. Locks de usuario

Se implementó `SetSlotUserLocksCommand` para:

```text
locks.geometry
locks.content
locks.delete
```

La UI solo agrega o retira la fuente `user`. Nunca elimina implícitamente
`engine`, `ctp` o `system`.

Ejemplos:

```text
["engine"] + bloquear usuario   -> ["engine", "user"]
["engine", "user"] + desbloquear usuario -> ["engine"]
```

En multiselección, la UI informa:

- `ninguno`: ningún slot contiene `user`;
- `todos`: todos contienen `user`;
- `mixto`: solo una parte contiene `user`.

También muestra otras fuentes de lock que seguirán vigentes. Los cambios son
atómicos, reversibles y no-op cuando el estado pedido ya existe.

La política efectiva queda:

| Superficie | Acciones gobernadas |
| --- | --- |
| `geometry` | mover, nudge, inspector, rotar y futuras transformaciones geométricas |
| `content` | sustitución o transformación del contenido |
| `delete` | eliminar, cortar y reemplazos que retiren slots |

Los comandos vuelven a validar la política en ejecución; deshabilitar botones no
es la única defensa.

## 6. ActionRegistry y atajos

Las operaciones de objeto se registraron con IDs estables:

```text
selection.rotate.clockwise
selection.rotate.counterclockwise
selection.rotate.set
selection.duplicate
selection.delete
clipboard.copy
clipboard.cut
clipboard.paste
selection.select_all_face
selection.select_same_work
selection.select_same_asset
selection.user_locks.set
```

Atajos activos:

| Atajo | Acción |
| --- | --- |
| `R` | rotar `+90°` |
| `Shift+R` | rotar `-90°` |
| `Ctrl/Cmd+D` | duplicar |
| `Ctrl/Cmd+C` | copiar |
| `Ctrl/Cmd+X` | cortar |
| `Ctrl/Cmd+V` | pegar |
| `Ctrl/Cmd+A` | seleccionar todos los slots de la cara activa |
| `Delete` | eliminar |
| `?` | ayuda central de atajos |
| `Escape` | cancelar la interacción temporal prioritaria |

Botones y teclado ejecutan las mismas acciones. Se eliminó la ruta especial de
Delete en el shortcut manager.

Los atajos de objeto se ignoran dentro de `input`, `textarea`, `select`,
`contenteditable` y roles editables. Guardar y Escape mantienen sus excepciones
controladas existentes.

## 7. Alt+arrastrar

`Alt` se evalúa al iniciar el pointer gesture.

1. se congela la selección fuente;
2. se crean IDs de preview una sola vez;
3. se renderizan copias temporales;
4. el layout no cambia durante el arrastre;
5. pointerup con desplazamiento confirma un único `DuplicateSlotsCommand`;
6. las copias quedan seleccionadas;
7. Escape, blur o pointercancel descartan el preview sin historial ni dirty.

La cancelación libera también la captura del puntero. Un Alt+click sin
desplazamiento no duplica.

El duplicado interactivo puede copiar slots con geometría bloqueada porque no
mueve los originales ni altera su geometría; las copias preservan sus locks.

## 8. Store, historial y autosave

El Store separa:

### Persistente

- layout;
- slots rotados, duplicados o pegados;
- locks de usuario;
- revisión.

### Temporal

- selección;
- clipboard;
- contador de pegados;
- preview de duplicado;
- pointer session;
- viewport, hover y feedback.

Los comandos declaran `selectionBefore` y `selectionAfter`, de modo que
execute/undo/redo restauran la selección asociada sin convertirla en estado
persistente.

Solo una mutación confirmada incrementa `changeVersion`, crea historial, marca
dirty y habilita autosave. Copiar, seleccionar y mover previews no lo hacen.

## 9. UI y accesibilidad

Se añadió un panel compacto **Operaciones de objeto** con:

- contador de selección;
- controles `-90°`, selector cardinal y `+90°`;
- duplicar, copiar, cortar, pegar y eliminar;
- selección por cara, work y asset;
- estado del clipboard con `role=status` y `aria-live`;
- locks explícitos por superficie;
- etiquetas accesibles para bloquear/desbloquear;
- estado de lock anunciado como ninguno/todos/mixto;
- aviso de que otras fuentes de lock no se retiran;
- ayuda central de atajos actualizada.

Los controles se deshabilitan desde la disponibilidad real del registro de
acciones.

## 10. Archivos frontend

Archivos nuevos:

- `static/js/editor_offset_v2/object_operations.js`;
- `static/js/editor_offset_v2/objects_panel.js`.

Archivos ampliados:

- `store.js`;
- `commands.js`;
- `edit_policy.js`;
- `command_registry.js`;
- `shortcut_manager.js`;
- `interactions.js`;
- `canvas_renderer.js`;
- `dom_refs.js`;
- `bootstrap.js`;
- `templates/editor_offset_visual_v2.html`;
- `static/css/editor_offset_visual_v2.css`.

No se modificaron archivos Python de producción ni contratos.

## 11. Cobertura

Node cubre:

- las cuatro rotaciones y normalización;
- conservación exacta de geometría no rotacional, fuente y contenido;
- locks de geometría y atomicidad;
- duplicado, IDs, offset, procedencia y redo estable;
- clipboard profundo, inmutable y temporal;
- validación same-job y referencias;
- paste acumulado;
- cut/delete atómicos;
- selecciones por cara/work/asset efectivo;
- estados de locks y preservación de otras fuentes;
- scopes de teclado;
- no-op, historial, dirty y autosave;
- secuencia mover → bloquear → undo/redo.

Playwright cubre el flujo visible:

- rotación, undo/redo y selector cardinal;
- duplicado por atajo;
- copiar/pegar repetido;
- cortar, eliminar y undo;
- selecciones básicas;
- lock/unlock y bloqueo efectivo;
- protección de inputs;
- Alt+drag con preview;
- cancelación con Escape;
- guardado y recarga;
- ayuda de atajos.

## 12. Riesgos residuales y límites

- El clipboard no cruza jobs ni pestañas y no pretende sustituir el clipboard
  del sistema.
- Los pegados no realizan auto-fit, snap ni búsqueda de espacio libre.
- La selección por cara depende de `activeFace`; la navegación back pertenece a
  una fase posterior.
- No existe árbol jerárquico completo; el panel 8B es una superficie compacta de
  operaciones.
- No se agregó preflight, preview ni PDF.
- Una copia preserva locks; puede nacer bloqueada por decisión deliberada.
- La exportabilidad de un slot duplicado sigue dependiendo de las capacidades
  actuales del adaptador de salida.

## 13. Fuera de alcance confirmado

No se implementó:

- alineación, distribución, gap exacto o matriz;
- box select, árbol avanzado o grupos;
- resize;
- snap, reglas o guías;
- transformaciones de artwork;
- edición manual de dorso;
- modos/recetas;
- preflight;
- planificación productiva;
- preview/PDF;
- presupuesto.

## 14. Próxima fase

La siguiente fase SAFE es **8C — Alineación, centrado, distribución y matriz**.
Debe reutilizar el registro central, la política `move`, los comandos atómicos y
la semántica de centro trim. No debe mezclarse con snap, resize ni salida PDF.
