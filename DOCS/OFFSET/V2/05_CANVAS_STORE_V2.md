# Fase 5 — Store, comandos, guardado y canvas SVG básico

> ESTADO: DOCUMENTO HISTÓRICO DE FASE
>
> Este archivo describe el sistema al finalizar esta fase. No representa por sí solo el estado funcional actual.
>
> Estado actual: `08_AUDITORIA_ESTADO_ACTUAL_V2.md`
>
> Roadmap vigente: `09_PLAN_HERRAMIENTAS_MANUALES_V2.md`

## Objetivo

Esta fase incorpora el primer núcleo interactivo del Editor Offset Visual V2 sin conectar assets PDF reales ni la salida productiva. Un Layout V2 persistido se carga en un store aislado, las modificaciones confirmadas pasan por comandos y el resultado se guarda mediante la API con control de revisión creada en la Fase 4.

El flujo implementado es:

```text
layout_v2.json
    ↓
EditorStore
    ↓
CreateSlotCommand / MoveSlotsCommand / DeleteSlotsCommand
    ↓
Canvas SVG
    ↓
SaveCoordinator
    ↓
PUT /api/editor-offset-v2/jobs/<job_id>/layout
```

## Organización frontend

La fase usa JavaScript estándar servido directamente por Flask. No añade Vite, TypeScript, frameworks ni dependencias.

```text
static/js/editor_offset_v2/
├── api_client.js        # cliente HTTP y errores estructurados
├── autosave.js          # coordinación serial de guardados
├── bootstrap.js         # composición de módulos y controles del shell
├── canvas_renderer.js   # render SVG y paneles derivados del store
├── commands.js          # comandos reversibles y placeholder de desarrollo
├── dom_refs.js          # referencias DOM del shell V2
├── geometry_view.js     # frontera geométrica cardinal para la vista
├── interactions.js      # Pointer Events, selección, drag, zoom y pan
└── store.js             # estado central persistente y temporal
```

Los módulos se publican únicamente bajo `window.EditorOffsetV2`. No reutilizan `window.EditorOffsetVisual` ni módulos del Editor V1. También exponen `module.exports` cuando se ejecutan en Node para probar las partes puras sin instalar infraestructura adicional.

`static/js/editor_offset_visual_v2.js` es un entrypoint pequeño: espera al DOM y delega el arranque a `Bootstrap.start()`.

## Store central

`EditorStore` mantiene dos categorías de estado.

### Estado persistente

`store.layout` contiene el Layout V2 completo y, por tanto, sheet, faces, assets, works, slots, imposition, export y CTP. `store.revision` refleja la revisión canónica del servidor.

### Estado temporal

El store mantiene fuera del layout:

* cara activa;
* selección y hover;
* herramienta activa;
* zoom y pan;
* coordenadas del cursor;
* sesión Pointer;
* posiciones de previsualización durante drag;
* estado y error de guardado;
* pilas undo/redo;
* contadores internos de cambios.

Selección, zoom, pan, dirty state, historial y sesiones Pointer nunca se serializan dentro de `layout_v2.json`.

## Sistema de comandos

Toda modificación confirmada de esta fase usa uno de estos comandos:

* `CreateSlotCommand`: agrega un asset placeholder, un work placeholder y su slot.
* `MoveSlotsCommand`: guarda únicamente las posiciones anteriores y posteriores de los slots afectados.
* `DeleteSlotsCommand`: guarda únicamente los slots eliminados y sus índices originales.

Cada comando expone `execute`, `undo`, `redo`, `description` y `affectedIds`. El historial no usa copias completas del layout como mecanismo principal.

Un drag actualiza solo `previewPositions`. Al soltar, se genera un único `MoveSlotsCommand`. Escape descarta la previsualización sin tocar la geometría persistente.

## Undo, redo y dirty state

Los estados de guardado son:

```text
clean | dirty | saving | save_error | conflict
```

Ejecutar, deshacer o rehacer un comando incrementa una versión interna de cambio y deja el documento `dirty`. Volver visualmente al contenido anterior mediante undo no implica `clean`, porque no se infiere igualdad con una revisión remota a partir de la apariencia.

Un guardado toma un ticket inmutable con revisión base, copia del layout y versión de cambio. Si no hubo cambios concurrentes, la respuesta canónica reemplaza el layout local y el estado pasa a `clean`. Si se confirmó otro comando mientras la petición estaba en curso, se conserva el contenido local, se incorpora la nueva revisión del servidor y se inicia otra iteración de guardado.

## Guardado manual y autosave

El guardado usa exclusivamente:

```http
PUT /api/editor-offset-v2/jobs/<job_id>/layout
```

```json
{
  "base_revision": 1,
  "layout": {}
}
```

`SaveCoordinator` impide peticiones competidoras. El autosave tiene un debounce explícito de `900 ms`, se programa solo tras comandos confirmados, undo o redo, y nunca se inicia durante una sesión Pointer activa.

Los errores permanecen visibles. Una nueva modificación permite reintentar un error normal; un conflicto requiere recargar deliberadamente el job.

## Conflictos de revisión

Una respuesta HTTP `409` cambia el store a `conflict` y conserva sin cambios el layout y la revisión locales. La interfaz ofrece únicamente **Recargar versión remota**. No existe merge automático ni sobrescritura forzada.

Este estado será consultable por preview y exportación en fases posteriores para impedir producción desde un documento no sincronizado.

## Placeholder de desarrollo

Como aún no existe carga de assets, **Slot prueba** crea explícitamente tres objetos válidos para el contrato:

* un asset PDF placeholder con `status = error`;
* un work manual de 90 × 50 mm y bleed de 3 mm;
* un slot frontal asociado, centrado en el pliego.

El asset declara el issue de preflight `DEVELOPMENT_PLACEHOLDER` y una ruta lógica bajo `development/placeholders/`. No se crea ni se finge un PDF físico. Por ello el objeto sirve para probar edición y persistencia, pero queda inequívocamente bloqueado para exportación. Los assets reales reemplazarán este mecanismo en la Fase 6.

## Canvas SVG

El canvas es un único SVG que representa:

* workspace;
* pliego y su límite;
* trim de cada slot;
* overlay de bleed;
* señal visual de slot fuera del pliego;
* selección y bounding box de la selección;
* etiqueta básica del slot.

Los slots se dibujan desde su centro trim. Las dimensiones persistidas permanecen anteriores a la rotación. Las rotaciones de 90° y 270° solo intercambian el footprint derivado.

## Conversión de coordenadas

El dominio conserva milímetros, origen inferior izquierdo e Y positiva hacia arriba. La inversión de Y ocurre exclusivamente en `geometry_view.js`:

```text
svg_y = sheet_height_mm - domain_y_mm
domain_y_mm = sheet_height_mm - svg_y
```

X se conserva directamente. El SVG usa unidades de viewBox equivalentes a milímetros; zoom y pan modifican únicamente el viewport, no el layout. Pointer Events se convierten primero a coordenadas SVG mediante la matriz del elemento y después a coordenadas del dominio.

## Geometría de vista y deuda temporal

`geometry_view.js` aísla las fórmulas mínimas requeridas por el renderer: tamaño productivo, tamaño orientado, bounds cardinales, contención del pliego y frontera SVG. Sus pruebas consumen `tests/fixtures/editor_offset_v2/geometry_cases.json`, compartido con el kernel Python.

Esta es una frontera temporal, no un segundo contrato geométrico. Antes de habilitar resize, rotación interactiva, snap, smart guides o colisiones avanzadas se debe incorporar paridad automática completa entre el kernel Python y el futuro kernel frontend TypeScript.

Renderer, preflight y adaptador de salida no deben reimplementar estas fórmulas de manera independiente.

## Selección y movimiento

La fase incluye:

* selección simple en canvas o lista;
* selección múltiple con Shift, Ctrl o Cmd;
* deselección al pulsar el fondo;
* borrado mediante botón, Delete o Backspace;
* drag de todos los slots seleccionados con Pointer Events;
* cancelación del drag mediante Escape;
* valores persistidos en milímetros y centro trim;
* señal visual, sin corrección automática, cuando el bleed sale del pliego.

No hay box select, snap ni colisiones bloqueantes.

## Zoom y pan

El zoom se controla mediante rueda o botones y se limita al intervalo 35%–400%. Pan se activa con botón central o Espacio más drag. **Restablecer** devuelve zoom y pan a sus valores iniciales. Ninguno de estos valores se persiste.

## Shell visual

El template incluye barra superior de documento y guardado, barra de herramientas, árbol simple de slots, canvas central, inspector de solo lectura y barra inferior con cara, cursor, zoom y conteo. No replica las nueve pestañas de Editor V1 y no carga sus scripts.

## API HTTP reutilizada

No se agregaron endpoints. El contexto del template expone las URLs canónicas ya existentes:

* `GET /api/editor-offset-v2/jobs/<job_id>`;
* `PUT /api/editor-offset-v2/jobs/<job_id>/layout`.

El control de revisión, validación V2 y escritura atómica continúan en `JobService` y `JobRepository`.

## Límites de la fase

Esta fase no implementa:

* assets PDF reales ni upload;
* thumbnails;
* Repeat;
* OutputAdapter;
* preview o PDF;
* CTP operativo;
* resize o rotación interactiva;
* snap, smart guides, box select o preflight visual;
* edición del inspector;
* cambio de frente/dorso desde la interfaz;
* persistencia de estado de UI.

## Próxima fase

La Fase 6 debe sustituir los placeholders por assets reales administrados por el job V2, selección de página/caja PDF, miniaturas y creación de works/slots a partir de fuentes físicas verificables. Antes de ampliar las herramientas geométricas debe definirse el kernel frontend con pruebas de paridad contra los fixtures canónicos de Python.
