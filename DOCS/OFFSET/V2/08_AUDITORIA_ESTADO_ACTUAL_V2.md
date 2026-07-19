# Auditoría técnica del estado actual del Editor Offset Visual V2

## 1. Propósito, alcance y autoridad

Esta auditoría reconstruye el estado real del Editor Offset Visual V2 después de las fases 1 a 7. No usa la arquitectura del Editor V1 ni documentos históricos como prueba de funcionamiento.

Orden de evidencia aplicado:

1. código ejecutable actual de V2;
2. tests Python y Node actuales;
3. flujo visible cubierto por Playwright;
4. documentos V2 01 a 07;
5. documentos anteriores, solo como contexto histórico.

La revisión fue estática. En esta tarea no se ejecutaron tests ni se inició Flask; cuando este documento dice **probada**, significa que existe una aserción automatizada directa en la cobertura revisada, no que esa prueba se haya vuelto a ejecutar durante la auditoría.

## 2. Resumen ejecutivo

Editor V2 ya es una aplicación aislada y accesible, no un prototipo documental. Puede crear y abrir jobs, persistir Layout V2 con control de revisión, subir PDFs, inspeccionar páginas y cajas, generar miniaturas, crear works y slots reales, mover y seleccionar slots en SVG, deshacer/rehacer, guardar automáticamente y calcular/aplicar Repeat como una operación reversible.

La base más estable está en Python: contrato estricto, persistencia atómica, almacenamiento seguro de assets, kernel geométrico puro y adaptadores aislados. La base frontend también está modularizada, pero continúa en JavaScript estándar con un kernel de vista reducido y duplicado. Esa duplicación está caracterizada para bounds cardinales mediante fixtures compartidos, no para toda la API geométrica Python.

Antes de incorporar herramientas manuales avanzadas deben resolverse cuatro deudas:

1. los comandos e interacciones actuales no hacen cumplir `locks.geometry`, `locks.content` ni `locks.delete`;
2. `activeFace`, `activeTool` y `hoverId` existen en el store, pero no tienen flujo funcional completo;
3. el artwork SVG no aplica `content_transform`: representa una miniatura completa con `meet` y clip trim;
4. el OutputAdapter existe y está probado de forma aislada, pero no está conectado a endpoints, preview ni PDF final y bloquea transformaciones de contenido avanzadas, CTP activo, páginas distintas de 1 y cajas distintas de TrimBox.

## 3. Mapa de arquitectura actual

```text
app.py
  -> init_editor_offset_v2(app)
     -> Blueprint V2 + feature flag
        -> JobService -> JobRepository -> layout_v2.json
        -> AssetService -> AssetRepository/PdfInspector/ThumbnailRenderer
        -> RepeatService -> RepeatEngineAdapter -> step_repeat_pro_engine.py

Layout V2 persistido
  -> contexto JSON del template
  -> EditorStore
     -> comandos reversibles
     -> Renderer SVG
     -> CanvasInteractions
     -> AssetsPanel / RepeatPanel
     -> SaveCoordinator -> PUT revisionado

Layout V2
  -> OutputAdapter aislado y probado
  -X- todavía no conectado a preview/PDF/montaje_offset_inteligente.py
```

### 3.1 Capas Python

| Capa | Archivos principales | Responsabilidad confirmada |
| --- | --- | --- |
| Dominio | `domain/layout_v2.py`, `validation.py`, `geometry.py`, `output_contract.py`, `repeat_contract.py` | Vocabulario, validación, geometría pura y modelos inmutables de salida/Repeat. |
| Aplicación | `application/job_service.py`, `asset_service.py`, `repeat_service.py`, `output_service.py` | Orquestación de casos de uso, revisiones, capacidades y errores tipados. |
| Infraestructura | `infrastructure/job_repository.py`, `asset_repository.py`, `pdf_inspector.py`, `thumbnail_renderer.py`, `repeat_engine_adapter.py`, `editor_output_adapter.py` | Filesystem, PDF, miniaturas y fronteras hacia motores/renderer legacy. |
| HTTP | `editor_offset_v2/blueprint.py`, `config.py` | Feature flag, contexto del shell, endpoints y traducción de errores a HTTP. |
| Integración Flask | `app.py` | Registra V1 y luego llama `init_editor_offset_v2(app)`; el registro V2 es idempotente. |

El blueprint construye servicios por request desde la configuración Flask. El dominio no conoce Flask, rutas, jobs físicos ni el feature flag.

### 3.2 Endpoints activos

| Método y ruta | Función actual | Persistencia |
| --- | --- | --- |
| `GET /editor_offset_visual_v2` | Shell sin job. | No. |
| `GET /editor_offset_visual_v2/<job_id>` | Abre un job válido e inyecta el layout/contexto. | No. |
| `POST /api/editor-offset-v2/jobs` | Crea ID, estructura y layout inicial. | Sí, revisión 1. |
| `GET /api/editor-offset-v2/jobs/<job_id>` | Lee layout validado. | No. |
| `PUT /api/editor-offset-v2/jobs/<job_id>/layout` | Guarda con compare-and-swap de revisión. | Sí. |
| `POST /api/editor-offset-v2/jobs/<job_id>/assets` | Sube, inspecciona, miniaturiza e incorpora un PDF. | Sí, incrementa revisión. |
| `GET /api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/thumbnails/<page>` | Sirve PNG resuelto por el servidor. | No. |
| `POST /api/editor-offset-v2/jobs/<job_id>/imposition/repeat` | Calcula una propuesta Repeat normalizada. | No; el frontend decide si aplicarla. |

No existen endpoints V2 de preflight productivo, preview, exportación, CTP, Nesting o Hybrid.

### 3.3 Feature flag

`EDITOR_OFFSET_V2_ENABLED` se instala desde configuración Flask y por defecto queda desactivado salvo configuración o variable de entorno explícita. Con la bandera apagada, páginas y API V2 responden 404; la API devuelve `V2_DISABLED`. Los tests verifican que una aplicación V1 de prueba continúa disponible y que la bandera no crea estado global entre apps.

## 4. Jobs, almacenamiento y revisiones

La raíz por defecto es `<instance_path>/editor_offset_v2_jobs`, configurable mediante `EDITOR_OFFSET_V2_JOBS_ROOT`. Cada job usa un ID `ev2_` más 24 caracteres hexadecimales y contiene:

```text
<jobs_root>/<job_id>/
├── layout_v2.json
├── assets/
├── derived/
├── previews/
├── outputs/
└── reports/
```

`JobRepository` valida el ID antes de resolver rutas y no consulta `static/constructor_offset_jobs`. El JSON se escribe en UTF-8, con claves ordenadas, indentación, nueva línea final y `allow_nan=False`. El reemplazo usa un temporal en el mismo directorio, `flush`, `fsync` y `os.replace`.

El guardado es optimista:

1. el cliente envía `base_revision` y un layout con esa misma revisión;
2. `JobService` compara con lo persistido;
3. valida el layout completo;
4. conserva `created_at`, actualiza `updated_at` e incrementa la revisión;
5. `JobRepository` vuelve a comparar dentro de un lock por job del proceso;
6. un cambio concurrente produce `409 REVISION_CONFLICT`.

Limitación confirmada: el lock es local al proceso Flask. Un despliegue multiproceso necesitaría lock de archivo o almacenamiento transaccional compartido.

## 5. Contrato Layout V2

El contrato es un corte limpio con `layout_schema_version = 2`. Sus fuentes ejecutables son `layout_v2.py`, `validation.py` y `layout-v2.schema.json`.

Invariantes confirmados:

- unidad milímetro, origen inferior izquierdo, X derecha, Y arriba;
- posición persistida = centro trim;
- trim persistido antes de rotación;
- bleed uniforme y separado;
- footprint no persistido;
- rotaciones productivas e internas limitadas a 0, 90, 180 y 270;
- referencias explícitas asset/página/caja/work/perfil;
- cajas PDF ausentes representadas por `null`;
- locks separados por geometría, contenido, producción y eliminación;
- estado temporal de UI fuera del layout;
- campos legacy prohibidos en cualquier profundidad.

El contrato permite declarar transformaciones de contenido (`contain`, `cover`, `stretch`, escalas, offsets, espejos y clipping), pero declararlas válidas estructuralmente no significa que el canvas o la salida actual las implementen.

También permite works con fuentes nulas. La UI normal crea `front_source`, y Repeat bloquea la falta de fuente para la cara elegida. No hay una regla contractual que obligue a que la fuente o el trim de cada slot permanezcan iguales a los del work; `ReplaceSlotSourceCommand` explota deliberadamente esa independencia al sustituir una fuente sin cambiar el work ni la geometría.

## 6. Kernel geométrico

`domain/geometry.py` es puro, inmutable y determinista. Proporciona `Point`, `Size`, `Bounds`, `Polygon` y `SlotGeometry`, además de:

- validación finita/positiva/no negativa/cardinal;
- tamaño productivo y orientado;
- polígonos trim y bleed;
- bounds y conversiones desde centro;
- contención;
- SAT para overlap real;
- gaps firmados y distancia entre bounds.

La tolerancia `1e-9 mm` es exclusivamente numérica. El contacto de bordes no es overlap.

Repeat y OutputAdapter consumen este kernel para normalizar y validar geometría. El canvas no puede importar Python: usa `geometry_view.js`, una réplica reducida de tamaño, orientación, bounds, contención y frontera SVG.

### 6.1 Deuda de paridad frontend

Los tests Node ejecutan los mismos `geometry_cases.json` que Python para tamaños y bounds cardinales, e invierten Y. Esta es paridad real, pero parcial. JavaScript todavía no implementa ni prueba:

- polígonos ordenados;
- SAT;
- point-in-polygon;
- tolerancias equivalentes;
- gaps y distancias;
- contención contra márgenes imprimibles;
- APIs para guías, snap o resize.

Por tanto, `geometry_view.js` es una duplicación temporal controlada, no una fuente equivalente completa al kernel.

## 7. Adaptador de salida

`EditorOutputAdapter` está implementado y probado de forma aislada. Convierte Layout V2 válido a modelos `Output*` inmutables, resuelve assets dentro de `job_root`, usa el kernel para convertir centro trim a esquina productiva y serializa al contrato temporal legacy con `slot_box_final = true` únicamente en esa frontera.

Capacidades seguras actuales:

- frente solo o frente/dorso separados en el modelo;
- rotación geométrica cardinal;
- trim y bleed separados;
- página 1 y TrimBox;
- `actual_size`, escala 1, offset 0, rotación interna 0, sin espejo;
- clipping trim con bleed 0 o BleedBox físicamente compatible;
- crop marks básicos;
- CTP desactivado.

Bloquea expresamente capacidades no representables. No existe llamada al adaptador desde el blueprint ni conexión con `montaje_offset_inteligente.py`; preview y PDF final siguen **no implementados en la superficie V2**.

## 8. Arquitectura frontend y store

El frontend usa módulos JavaScript estándar cargados como scripts diferidos bajo el namespace aislado `window.EditorOffsetV2`. No usa Vite, TypeScript ni un framework.

| Módulo | Responsabilidad actual |
| --- | --- |
| `api_client.js` | Crear job, leer, guardar, upload y propuesta Repeat. |
| `store.js` | Layout, revisión, estado temporal, historial y estados de guardado. |
| `commands.js` | Comandos reversibles y fábricas de work/slot/placeholder. |
| `geometry_view.js` | Geometría cardinal reducida y conversión SVG. |
| `canvas_renderer.js` | SVG, lista de slots, inspector y chrome. |
| `interactions.js` | Pointer Events, selección, drag, zoom/pan y atajos existentes. |
| `autosave.js` | Debounce y serialización de guardados. |
| `assets_panel.js` | Upload, selección de fuente, work, slot y sustitución. |
| `repeat_panel.js` | Configuración, cálculo, resumen y aplicación Repeat. |
| `dom_refs.js` | Resolución estricta de elementos del shell. |
| `bootstrap.js` | Composición de módulos y listeners de alto nivel. |

### 8.1 Estado persistente

`store.layout` contiene el Layout V2 completo: job, sheet, faces, assets, works, slots, imposition, export y CTP. `store.revision` sigue la revisión canónica.

### 8.2 Estado temporal

Permanece fuera del layout:

- `activeFace`;
- selección y hover;
- herramienta activa;
- zoom, pan y cursor;
- pointer session y preview positions;
- estado de guardado;
- selección/estado del panel de assets;
- propuesta/estado Repeat;
- undo/redo y contadores de cambio.

`activeFace` se inicializa con la primera cara habilitada, pero no existe setter ni navegación de cara en el shell. `activeTool` queda en `select`; el botón de selección no tiene comportamiento de cambio de herramienta. `hoverId` y `setHover()` no se conectan a interacciones o renderer. Son estados latentes.

## 9. Comandos, undo/redo y guardado

Comandos actuales:

- `CreateSlotCommand` para bundle placeholder;
- `MoveSlotsCommand`;
- `DeleteSlotsCommand`;
- `CreateWorkCommand`;
- `CreateSlotFromWorkCommand`;
- `ReplaceSlotSourceCommand`;
- `ApplyRepeatCommand`.

Los comandos guardan deltas u objetos afectados, no snapshots completos del layout como historial general. `ApplyRepeatCommand` conserva los slots reemplazados y el bloque `imposition` previo para una reversión atómica.

### 9.1 Dirty state

`changeVersion` y `savedChangeVersion` determinan cambios pendientes. Execute, undo y redo incrementan la versión; volver visualmente al estado inicial no declara `clean`. Estados:

```text
clean | dirty | saving | save_error | conflict
```

### 9.2 Autosave

`SaveCoordinator` usa debounce de 900 ms, no guarda durante pointer session, serializa solicitudes y repite inmediatamente si hubo cambios durante una petición. El upload y Repeat exigen primero un estado limpio.

### 9.3 Conflictos

Un 409 conserva layout/revisión local, cambia a `conflict`, detiene autosave y ofrece únicamente recargar. No hay merge ni force-save.

### 9.4 Deuda de locks

Aunque el contrato define locks, actualmente:

- drag crea `MoveSlotsCommand` sin revisar `locks.geometry`;
- `DeleteSlotsCommand` no revisa `locks.delete`;
- `ReplaceSlotSourceCommand` no revisa `locks.content`;
- replace de Repeat elimina slots del work/cara sin revisar locks;
- botones y lista no muestran estado bloqueado.

Esto incluye slots Repeat, que nacen con `locks.geometry = ["engine"]` pero pueden moverse con drag. Antes de añadir más herramientas debe existir una política central y testeada de permisos de comando.

## 10. Canvas SVG

### 10.1 Capas actuales

Cada render reconstruye el SVG:

1. `<defs>` con clips por slot;
2. workspace;
3. pliego;
4. grupos de slot de la cara activa;
5. artwork opcional;
6. bleed y trim;
7. etiquetas;
8. bounds de selección.

Los slots se transforman con `translate(center)` y `rotate(-rotation_deg)`. El signo negativo compensa que el eje visual SVG crece hacia abajo.

### 10.2 Conversión milímetros/SVG

El viewBox usa unidades equivalentes a milímetros:

```text
svg_x = x_mm
svg_y = sheet_height_mm - y_mm
```

El layout nunca se invierte. Pointer Events pasan por `getScreenCTM().inverse()` y después vuelven a dominio.

### 10.3 Trim, bleed y límites

Trim y bleed se dibujan desde dimensiones sin rotar dentro del grupo rotado. `isWithinSheet()` usa bounds productivos con bleed y marca `is-outside`; no corrige ni bloquea el movimiento. Esa señal compara contra el pliego completo, no contra `printable_margins_mm`.

### 10.4 Artwork

Para assets `ready`, el renderer usa `<image>` con URL de miniatura, `preserveAspectRatio="xMidYMid meet"` y clip rectangular trim. El artwork rota con el slot y la selección queda encima.

Limitaciones confirmadas:

- la miniatura representa la página completa, no un recorte exacto de la caja elegida;
- no aplica offset de la caja PDF;
- no aplica `fit_mode`, escala, offset interno, rotación interna ni espejo;
- siempre recorta visualmente a trim, aunque `content_transform.clip_to` declare otra cosa;
- marca mismatch de dimensiones por clase CSS, sin preflight visible detallado.

### 10.5 Selección y drag

Existe selección simple, toggle múltiple con Shift/Ctrl/Cmd, selección desde lista, deselección por fondo y bounds conjuntos basados en bleed. No hay box select, inclusión/solapamiento, ciclo de objetos ni árbol jerárquico.

Durante drag solo cambia `previewPositions`; al soltar se genera un `MoveSlotsCommand` para toda la selección. Escape cancela. No hay snap, colisiones bloqueantes ni restricciones de pliego.

### 10.6 Zoom y pan

Zoom 35–400 % mediante rueda o botones y reset están implementados. Pan usa botón central o Espacio + drag. Son temporales. La conversión de pan por píxel usa una aproximación basada en tamaño de pliego, padding y zoom; no tiene test DOM/E2E específico de precisión después de múltiples zooms.

## 11. Assets, páginas, works y slots reales

### 11.1 Upload y almacenamiento inmutable

El servidor valida nombre, extensión, MIME permitido, tamaño, archivo no vacío, firma `%PDF-` y estructura PDF. Escribe por streaming, calcula SHA-256, genera metadata/miniaturas en staging y publica la carpeta mediante rename. Si falla la incorporación al layout, elimina el asset recién finalizado.

Los IDs físicos no dependen del nombre original. `source.pdf` se crea en modo exclusivo y no se sobrescribe.

### 11.2 Inspección PDF

PyMuPDF obtiene MediaBox, CropBox heredable, TrimBox y BleedBox explícitos, rotación cardinal y dimensiones en mm. No inventa cajas ausentes. La sugerencia es trim, crop, media. No ejecuta preflight profundo de color, DPI, transparencias, overprint o perfiles.

### 11.3 Miniaturas

Genera PNG RGB por página, máximo 900 px y escala máxima 2. La ruta segura verifica identidad, metadata persistida, existencia y symlinks antes de usar `send_file`.

### 11.4 Works

La UI crea works reales desde una página/caja, con nombre, trim, bleed, cantidad y rotaciones. Puede reutilizar la misma fuente como dorso, pero no permite elegir una fuente posterior diferente en el mismo flujo.

### 11.5 Slots reales y sustitución

`CreateSlotFromWorkCommand` crea un slot manual frontal en el centro visible usando `front_source`. No usa `activeFace`, por lo que todavía no crea slots manuales de dorso. `ReplaceSlotSourceCommand` cambia una sola fuente, conserva geometría/work, advierte mismatch y es reversible.

### 11.6 Placeholders

El bundle placeholder continúa en `commands.js`, tiene asset `status=error`, preflight bloqueante y botón visible `Placeholder dev`. No aparece en el panel de assets ready y OutputAdapter/Repeat lo rechazan. Sigue siendo una capacidad de desarrollo expuesta en la UI, no solo una fábrica interna de tests.

## 12. Repeat V2

### 12.1 Flujo

El panel guarda primero cambios locales, envía revisión/work/cara/settings/modo y recibe una propuesta. El servidor no persiste. La propuesta solo entra al layout si el usuario pulsa Aplicar; entonces `ApplyRepeatCommand` realiza add o replace como una sola operación y activa autosave.

### 12.2 Adaptador y motor

`RepeatEngineAdapter` traduce V2 al mínimo legacy esperado por `build_step_repeat_slots()`. El motor usa esquina inferior izquierda de footprint productivo, nombres `width_mm/height_mm`, bleed y rotaciones 0/90. El adaptador reconstruye centro trim, trim original, bleed separado y rotación cardinal V2, y valida bounds/overlap con el kernel.

`step_repeat_pro_engine.py` no fue modificado. El adaptador consume `build_step_repeat_slots` e `IncompleteImpositionError.details`; también depende de que la salida contenga `design_ref`, `x_mm`, `y_mm` y `rotation_deg` 0/90.

### 12.3 Cantidades

Se distinguen requested, placed, unplaced y overproduced. Sin fill no sobreproduce. Con parcial permitido, reduce determinísticamente conteos y recalcula. Con fill, busca capacidad adicional. `exact_quantity` queda registrado, pero el permiso operativo de sobreproducción depende de `fill_remaining_space`.

### 12.4 Frente/dorso

Repeat puede calcular front o back si la cara está habilitada y el work tiene la fuente correspondiente. No inventa ni espeja dorso. El canvas no ofrece navegación de cara, de modo que una propuesta back puede aplicarse pero no existe un control normal para cambiar la vista activa a back.

### 12.5 Limitaciones

- No hay preview fantasma de la propuesta en canvas.
- Add bloquea colisión con slots existentes; el motor no los recibe como obstáculos para reacomodar.
- Replace actúa por work/cara y no aplica locks.
- Fill es determinista por prioridad, no optimización global.
- No hay Nesting ni Hybrid V2.

## 13. Cobertura de tests revisada

### 13.1 Python

Existen 149 funciones `test_*` en `tests/editor_offset_v2/`, varias parametrizadas en muchos casos. Cubren:

- schema/validador, referencias y rotaciones;
- kernel, fixtures, SAT, contención, distancias e inmutabilidad;
- adaptador de salida, seguridad de rutas, capacidades bloqueadas y serialización;
- jobs, JSON estricto, escritura atómica y conflictos;
- blueprint, feature flag, rutas y aislamiento V1;
- upload, rollback, hash, cajas, miniaturas y seguridad;
- Repeat service/adapter, cantidades, parcialidad, fill, caras, overlaps y pureza;
- validación del placeholder JavaScript contra el contrato Python.

### 13.2 Node

Existen 21 bloques `node:test`:

- 10 para geometría de vista, store, comandos base, selección, preview pointer, dirty, autosave y 409;
- 5 para works, slots reales, sustitución, aplicación canónica de upload y URL de miniaturas;
- 6 para ApplyRepeat add/replace, error, parcialidad, autosave y helpers del panel.

No hay entorno DOM unitario: renderer, interactions, assets panel y Repeat panel se prueban principalmente a través de helpers puros o Playwright.

### 13.3 Playwright

Existe un único test visible que:

1. crea un job;
2. sube un PDF;
3. comprueba asset y miniatura;
4. crea un work;
5. calcula Repeat;
6. verifica resumen;
7. aplica cuatro slots con artwork;
8. hace undo/redo;
9. guarda;
10. recarga y verifica persistencia.

No cubre actualmente:

- drag manual y cancelación con Escape;
- precisión con zoom/pan;
- selección múltiple visible y borrado;
- sustitución de fuente visible;
- error de upload visible;
- conflicto 409 y botón de recarga;
- flujo back en UI;
- add/replace visible de Repeat;
- parcialidad/fill visible;
- locks;
- adaptador de salida, preview o PDF.

## 14. Matriz de estado funcional

| Capacidad | Estado | Evidencia y límite |
| --- | --- | --- |
| Contrato Layout V2 | Implementada y probada | Schema, validador, fixtures y tests parametrizados. |
| Kernel Python | Implementada y probada | Modelos, polígonos, SAT, bounds, distancias y fixtures. |
| Jobs/lectura/guardado revisionado | Implementada y probada | Servicio, repositorio, rutas y tests atómicos/conflicto. |
| Feature flag y aislamiento V1 | Implementada y probada | Blueprint y tests por app. |
| Store persistente/temporal | Implementada y probada | Node prueba separación y estado. |
| Comandos y undo/redo | Implementada y probada | Comandos base/assets/Repeat con Node. |
| Dirty/autosave/409 | Implementada y probada | Node y tests HTTP; conflicto visible no está en Playwright. |
| Canvas SVG trim/bleed | Implementada y probada | Código + fixtures Node; sin screenshot/regresión visual. |
| Selección simple/múltiple/lista | Implementada y probada | Node cubre store; interacción DOM no tiene Playwright dedicado. |
| Drag con preview temporal | Implementada parcialmente | Código correcto por sesión/comando; no E2E actual ni locks. |
| Zoom/pan/reset | Implementada parcialmente | Código activo; sin test de precisión DOM/E2E. |
| Fuera de pliego | Implementada parcialmente | Señal visual por bleed contra sheet; no márgenes, no preflight. |
| Upload/asset inmutable/hash | Implementada y probada | Servicio/rutas/rollback/seguridad. |
| Inspección de cajas PDF | Implementada y probada | Cajas y ausencia explícita; no preflight profundo. |
| Miniaturas | Implementada y probada | PNG y endpoint; recorte por caja no implementado. |
| Works y slots reales front | Implementada y probada | Node + Playwright para work y Repeat; slot manual visible no E2E. |
| Fuente posterior distinta | No implementada | Solo checkbox para reutilizar la fuente seleccionada. |
| Slot manual back | No implementada | Fábrica fija `face=front` y `front_source`. |
| Artwork SVG | Implementada parcialmente | Miniatura, clip trim, rotación del slot; no `content_transform` ni caja exacta. |
| Sustitución de fuente | Implementada y probada | Node cubre comando; UI no está en Playwright. |
| Placeholders dev | Implementada y probada | Válidos en contrato, no exportables; siguen visibles en UI. |
| Repeat proposal | Implementada y probada | Servicio/adaptador/endpoints y Playwright. |
| Repeat add/replace | Implementada y probada | Node; Playwright solo aplica modo add. |
| Repeat parcial/fill | Implementada y probada | Python; no flujo visible Playwright. |
| Repeat back | Implementada y probada en backend | Python; bloqueada visualmente por falta de navegación de cara. |
| OutputAdapter | Implementada y probada, latente | No conectado al blueprint ni a producción. |
| Preview productivo | No implementada | Sin endpoint/UI V2. |
| PDF final V2 | No implementada | Sin conexión al renderer productivo. |
| CTP productivo | Bloqueada por otra fase | Contrato existe; adapter bloquea `ctp.enabled=true`. |
| Preflight PDF profundo | No implementada | Solo estructura y campos `not_run`. |
| Inspector editable | No implementada | Renderer genera `<dl>` de solo lectura. |
| Nudge/rotación manual/duplicar/copiar | No implementada | Sin comandos ni UI. |
| Locks operativos | Latente | Contrato presente, comportamiento no aplicado. |
| Box select/árbol/criterios | No implementada | Solo lista plana y selección múltiple directa. |
| Alinear/distribuir/snap/guías/medir | No implementada | Kernel Python tiene primitivas parciales; frontend no. |
| Resize | No implementada | Sin handles/comando/política de artwork. |
| Transformación interna del artwork | Bloqueada por otra fase | Contrato amplio; canvas no aplica y output bloquea. |
| Frente/dorso y mesa de luz | Implementada parcialmente | Contrato/Repeat soportan caras; UI no cambia cara ni superpone. |

## 15. Vigencia de documentos V2 01–07

| Documento | Clasificación | Evidencia |
| --- | --- | --- |
| `01_CONTRATO_LAYOUT_V2.md` | Parcialmente desactualizado | Semántica e invariantes siguen vigentes; todavía habla de API/kernel/adaptador como futuros en algunos apartados. Necesita reflejar que jobs, assets y Repeat ya existen. |
| `02_KERNEL_GEOMETRICO_V2.md` | Parcialmente desactualizado | API y fórmulas coinciden con código; “futura capa SVG/TypeScript” ya tiene una réplica JS parcial. Debe distinguir paridad cardinal actual de paridad completa pendiente. |
| `03_ADAPTADOR_SALIDA_V2.md` | Vigente | Responsabilidades, capacidades y bloqueo de CTP/contenido coinciden con código y tests; sigue correctamente desconectado de Flask/producción. |
| `04_SHELL_Y_JOBS_V2.md` | Contradicho por el código en su descripción del shell actual | Jobs/flag/repositorio siguen vigentes; afirma que el template solo carga un script y no tiene store/canvas/assets/Repeat, lo cual ya no describe el sistema actual. Conserva valor histórico de Fase 4. |
| `05_CANVAS_STORE_V2.md` | Parcialmente desactualizado | Store, comandos base, SVG y autosave siguen vigentes; el inventario de módulos/comandos y los límites “sin assets/Repeat” fueron superados. |
| `06_ASSETS_Y_SLOTS_V2.md` | Parcialmente desactualizado | Upload, inspección, miniaturas, works, slots y artwork coinciden; la afirmación “Repeat no implementado/próxima fase” ya quedó superada. |
| `07_REPEAT_V2.md` | Vigente | Flujo, adapter, cantidades, add/replace, límites y cobertura coinciden con código actual. Necesita ampliación futura cuando exista navegación visual back o preview fantasma. |

No se modificó ninguno de estos documentos durante la auditoría.

## 16. Deuda y riesgos prioritarios

### Alta prioridad antes de herramientas manuales

1. **Locks declarativos sin enforcement.** Es una inconsistencia entre contrato e interacción real y afecta drag, delete, replace y Repeat replace.
2. **Paridad geométrica frontend incompleta.** Bounds cardinales bastan para movimiento/alineación inicial, pero no para box select poligonal, overlap, snap avanzado o resize.
3. **Dos geometrías distintas por concepto.** La UI futura debe separar slot productivo y transformación interna del artwork; mezclarlas produciría diferencias con output.
4. **Exportabilidad no conectada.** No debe presentarse una transformación visual como productiva mientras OutputAdapter la bloquee.

### Prioridad media

5. No hay navegación activa frente/dorso; existen datos back que el operador no puede inspeccionar en el canvas normal.
6. El canvas valida “fuera” contra sheet, mientras Repeat usa márgenes imprimibles.
7. El tree actual es una lista plana de slots de la cara activa.
8. Placeholders siguen expuestos en UI y pueden contaminar jobs de usuario, aunque quedan bloqueados para Repeat/output.
9. Pan no tiene prueba de precisión y su cálculo por píxel no deriva directamente del viewBox real.
10. La cobertura Playwright concentra muchas garantías en un único happy path Repeat.

## 17. Conclusión

V2 está listo para iniciar herramientas manuales de bajo riesgo que solo cambien posición y rotación cardinal mediante comandos. No está listo para habilitar resize, transformación interna del PDF, ocultación productiva, grupos persistentes o herramientas basadas en colisiones avanzadas sin decisiones de contrato y paridad geométrica adicionales.

La siguiente fase recomendada es un incremento pequeño: inspector editable de centro X/Y, nudge y registro de atajos, acompañado por una política central de locks para toda mutación geométrica. No debe editar trim, bleed ni contenido todavía.
