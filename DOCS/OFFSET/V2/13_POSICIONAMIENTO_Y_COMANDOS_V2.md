# Fase 8A — Posicionamiento manual preciso y sistema central de acciones/atajos

## 1. Objetivo

Fase 8A incorpora posicionamiento exacto en milímetros y una frontera central para ejecutar acciones del editor desde teclado o botones, conservando las garantías de Layout V2, `EditorStore`, historial, autosave y locks estabilizadas en 8P.

## 2. Alcance

Se implementaron inspector X/Y, movimiento absoluto de una selección, delta de multiselección, nudge de `0.1`, `1` y `10 mm`, batching de autorepeat, guardado y undo/redo por teclado, ayuda derivada del registro y scopes seguros. No se cambió backend, schema, V1, Repeat ni salida.

## 3. Arquitectura anterior

Antes de 8A, `interactions.js` era propietario tanto de gestos de puntero como de listeners globales para undo, redo, delete, Escape y pan. Los botones llamaban lógica separada en `bootstrap.js`; no existía inspector editable ni catálogo declarativo de acciones.

## 4. Arquitectura del registro de acciones

`command_registry.js` define `ActionRegistry`, valida IDs únicos y conserva metadatos de etiqueta, categoría, descripción, atajos, ayuda, disponibilidad y ejecución. `bootstrap.js` compone un único contexto actual y tanto los botones como `ShortcutManager` ejecutan el mismo ID registrado.

El registro no guarda estado documental y no reemplaza `EditorStore`. Es una frontera de intención y enrutamiento.

## 5. Diferencia entre acción y comando reversible

Una **acción** representa una intención invocable, por ejemplo guardar, deshacer, mover o abrir ayuda. Puede ser temporal y no reversible. Un **comando reversible** representa una mutación confirmada de Layout V2, conserva before/after y entra en `undoStack`/`redoStack`.

Las acciones `selection.move.*` y `selection.nudge` crean o finalizan un `MoveSlotsCommand`; guardar y ayuda no crean comandos.

## 6. Contexto de comandos

El contexto se obtiene bajo demanda e incluye store, layout, selección, historial, `SaveCoordinator`, estado de puntero/pan/foco, módulos de comandos y política, inspector, controlador de nudge y diálogo de ayuda. Así, `enabled` y `execute` leen el mismo estado vigente sin duplicar stores ni historiales.

## 7. Convención de IDs

Los IDs son estables, jerárquicos y separados por punto:

- `editor.save`
- `editor.cancel`
- `history.undo`
- `history.redo`
- `selection.move.absolute`
- `selection.move.delta`
- `selection.nudge`
- `shortcuts.help.toggle`

Los IDs describen intención y dominio; no incluyen tecla, plataforma ni componente visual.

## 8. Shortcut manager

`shortcut_manager.js` es el único propietario de `keydown`, `keyup` y `blur` globales de 8A. Normaliza `Ctrl`, `Meta`, `Alt`, `Shift`, teclas cardinales y `?`; expande `Mod` a Ctrl/Cmd; detecta conflictos al construir el mapa; consulta scopes y delega al registro. El pan con espacio y delete heredados quedaron centralizados como hooks de interacción, sin adelantar acciones de 8B.

## 9. Scopes de teclado

El resolver distingue scope global, editable, ayuda abierta, pan y sesión de puntero. Una acción solo se ejecuta si sus metadatos permiten el scope actual. Movimiento y guardado quedan bloqueados durante gestos incompatibles; Escape puede cancelar la interacción de mayor prioridad.

## 10. Protección de inputs

Se consideran editables `input`, `textarea`, `select`, elementos `contenteditable`, roles `textbox`, `searchbox`, `combobox` y `spinbutton`, además de ancestros con `data-editor-captures-keyboard="true"`. Flechas, delete y atajos no autorizados no escapan de esos controles. Guardar y cancelar tienen permisos editables explícitos y limitados.

## 11. Coordenadas canónicas

Los valores editados son el centro trim canónico de `slot.geometry.position_mm`, en milímetros, con origen inferior izquierdo: X crece hacia la derecha e Y hacia arriba. La inversión vertical pertenece exclusivamente a la proyección SVG en `geometry_view.js`.

## 12. Inspector de selección única

Con un slot seleccionado, el formulario presenta Centro X y Centro Y absolutos. Los valores se precargan a tres decimales para lectura, pero un eje no editado conserva el número original exacto. Confirmar produce como máximo un `MoveSlotsCommand`; un no-op no crea historial ni dirty.

## 13. Delta multiselección

Con varios slots, los mismos campos cambian explícitamente a Delta X y Delta Y. Ambos se aplican a cada centro original, preservando distancias relativas y orden. La operación es atómica: si cualquier slot está bloqueado, no se mueve ninguno.

## 14. Parseo de punto/coma

`parseMillimetres()` acepta signo, espacios exteriores y un único separador decimal `.` o `,`. La coma se normaliza internamente a punto. Se rechazan campos vacíos, texto, separadores múltiples, `NaN` e infinitos; nunca se escribe un número no finito en el layout.

## 15. Validación

La validación ocurre antes de crear el comando y se repite en la política/comando para la mutación real. El inspector expone mensaje accesible, marca campos inválidos y bloquea confirmación. `Ctrl/Cmd+S` intenta confirmar un borrador válido; ante uno inválido no guarda ni cambia revisión.

## 16. Locks

Inspector, nudge y drag reutilizan `edit_policy.js` con capacidad `move`. La selección mixta se evalúa de forma atómica. El formulario queda deshabilitado y lista los IDs bloqueados; aun si la UI fuese forzada, `MoveSlotsCommand` vuelve a validar antes de mutar.

## 17. Nudge 0.1/1/10 mm

Las flechas mueven `0.1 mm`; Shift + flecha mueve `1 mm`; Ctrl/Cmd + Shift + flecha mueve `10 mm`. Derecha/izquierda modifican X; arriba/abajo modifican Y canónica, no el eje SVG. El paso se calcula desde el estado inicial para evitar acumulación progresiva de error.

## 18. Batching de autorepeat

El primer `keydown` abre una sesión `nudge`, captura IDs y posiciones before, y usa `previewPositions` para cada repetición. `keyup`, timeout de inactividad, cambio de selección, blur u otro comando finalizan la sesión. Solo entonces se crea un `MoveSlotsCommand` con before/after completos. Una ráfaga equivale a una entrada de undo y un disparo normal de autosave.

## 19. Escape

Escape respeta prioridades: cierra la ayuda, cancela nudge y restaura preview, descarta un borrador del inspector o cancela el gesto de puntero/pan activo. Descartar estado temporal no modifica Layout V2, dirty ni revisión.

## 20. Enter

Enter dentro del formulario ejecuta su submit accesible y confirma una entrada válida. No hay listener global de Enter, por lo que otros controles conservan su comportamiento nativo.

## 21. Ctrl/Cmd+S

`Mod+S` se resuelve a Ctrl+S o Cmd+S y ejecuta `editor.save`, la misma acción del botón Guardar. Previene el guardado del navegador, confirma un borrador válido y delega en el `SaveCoordinator` existente. Se bloquean doble envío, conflicto y gestos incompatibles.

## 22. Undo/redo

Ctrl/Cmd+Z ejecuta `history.undo`; Ctrl/Cmd+Shift+Z y Ctrl+Y ejecutan `history.redo`. Botones y teclado comparten estas acciones. Antes de otro comando, un nudge activo se finaliza para mantener orden determinista. Sigue existiendo un único historial en `EditorStore`.

## 23. Dirty/autosave

Editar texto, mostrar errores, abrir ayuda y mantener previews no ensucia. Solo un comando confirmado incrementa `changeVersion`; no-op o cancelación no lo hacen. El autosave existente observa ese cambio y persiste una vez por comando, incluida una ráfaga de nudge.

## 24. Ayuda de atajos

`?` y el botón Atajos abren el mismo diálogo. Las filas se derivan de `help` en el registro y se deduplican; Enter se documenta como comportamiento local del formulario. No se implementó paleta de comandos. Abrir o cerrar ayuda no cambia layout, dirty ni revisión.

## 25. Accesibilidad

El inspector usa `form`, `label`, unidad visible, `aria-describedby`, `aria-invalid` y regiones de estado/error. El diálogo usa `<dialog>`, devuelve foco al cerrar y admite Escape. El SVG con `role="application"` tiene `tabindex="0"`, permitiendo abandonar inputs y operar el canvas por teclado.

## 26. Tests

Node cubre registro, IDs, disponibilidad, conflictos, normalización Ctrl/Meta/Shift, scopes editables, parseo, absoluto/delta, locks, tres pasos de nudge, batching, timeout, cambio de selección, otro comando, autosave, save, historial, ayuda y borrador inválido. Playwright cubre un job real con Repeat: inspector, canvas, multi, pasos, ráfaga/undo, guardado/recarga, inputs, coma, inválido, locks, ayuda, etiquetas, capabilities y ausencia de UI 8B. La suite Python garantiza que el backend y contrato V2 permanecen estables.

## 27. Límites

No se implementaron rotación, duplicado, clipboard, locks de usuario, seleccionar todo, alineación, distribución, box select, árbol, snap, guías, resize, transformación de artwork, cara back, preview ni PDF. Delete y espacio-pan se centralizaron solo para retirar listeners globales duplicados; no se amplió su función.

## 28. Siguiente fase 8B

8B debe apoyarse en el registro actual para rotación cardinal, duplicado, copiar/pegar, criterios de selección y locks `user`. Antes de implementarla se recomienda definir IDs y capacidades por acción, separar clipboard temporal de comandos persistentes y ampliar `edit_policy.js` sin relajar locks `engine`, `ctp` o `system`.
