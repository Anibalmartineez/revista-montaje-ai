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

### 1.1 Actualización operativa — Fase 8P

La Fase 8P posterior a esta auditoría fue implementada y validada. Las secciones históricas de hallazgos se conservan como evidencia del problema original, pero su resolución vigente es:

- Repeat normal conserva `generated_by` y crea slots editables con `locks.geometry = []`;
- `edit_policy.js` aplica de forma atómica locks de geometría, delete y contenido a drag y comandos, incluido Repeat replace;
- la UI distingue fuente predeterminada del work y fuente efectiva del slot, con override derivado;
- `imposition.last_result` se presenta como resultado histórico y los conteos actuales se derivan de `slots[]`;
- Repeat distingue aprovechamiento de propuesta y total proyectado, manteniendo `utilization_percent` como alias compatible de la propuesta;
- `exact_quantity` permanece aceptado por API pero oculto y fijado a `true` en la UI;
- canvas muestra área imprimible y diferencia fuera del pliego de fuera del área imprimible;
- Repeat back sigue soportado por backend, pero está deshabilitado temporalmente en la UI;
- placeholder dev queda oculto por defecto bajo `EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED`;
- existe diagnóstico visible de compatibilidad con la salida temporal, sin preview ni PDF;
- el artwork real se etiqueta como `Vista aproximada del PDF`;
- 04–07 son documentos históricos de fase; 01–03, 08–09 siguen vivos.

Corrección posterior documentada en `12_CORRECCION_COMPATIBILIDAD_DE_MEDIDA_Y_ETIQUETAS_V2.md`:

- output capabilities usa `0.01 mm` como tolerancia explícita PDF/trim y trata 90/270 como orientación derivada sin reescribir trim;
- issues repetidos se agrupan visualmente por código, asset y work, conservando IDs desplegables;
- el canvas muestra ordinales cortos adaptados al zoom, oculta etiquetas en slots pequeños y mantiene su visibilidad como estado temporal no persistente.

### 1.2 Actualización operativa — Fase 8A

La Fase 8A posterior a esta auditoría también fue implementada y validada. El estado vigente se documenta en `13_POSICIONAMIENTO_Y_COMANDOS_V2.md`:

- existe un registro central de acciones con IDs estables, disponibilidad, ejecución, atajos y ayuda;
- botones y teclado ejecutan las mismas acciones de guardar, undo, redo y ayuda;
- el inspector edita centro X/Y absoluto para un slot y delta X/Y para multiselección;
- punto y coma decimal se normalizan sin permitir `NaN` ni infinitos;
- nudge usa `0.1`, `1` y `10 mm`, con Y canónica hacia arriba;
- una ráfaga de autorepeat produce un único `MoveSlotsCommand`;
- inputs, `contenteditable`, roles editables, diálogo, pan y sesiones de puntero tienen scopes explícitos;
- inspector, nudge y drag reutilizan la política atómica `move` y la defensa del comando;
- borradores, previews y ayuda son temporales; solo una confirmación válida activa dirty/autosave.

### 1.3 Actualización operativa — Fase 8B

La Fase 8B posterior a esta auditoría también fue implementada y validada. Su
estado vigente y decisiones se documentan en
`14_OPERACIONES_DE_OBJETO_Y_CLIPBOARD_V2.md`:

- rotación manual cardinal, sin cambiar centro trim, trim, bleed ni contenido;
- duplicado con IDs estables para redo y procedencia `type=duplicate`;
- clipboard profundo, temporal, same-job y con paste acumulativo;
- cortar y eliminar atómicos sobre la misma acción/política;
- Alt+arrastrar con preview temporal y un comando al confirmar;
- selección por cara activa, work y asset efectivo del slot;
- locks de usuario explícitos para geometry/content/delete, preservando
  `engine`, `ctp` y `system`;
- botones y teclado comparten `ActionRegistry`;
- selección, clipboard y previews no activan dirty/autosave;
- Node y Playwright cubren historial, locks, referencias, accesibilidad,
  persistencia y cancelación.

## 2. Resumen ejecutivo

Editor V2 ya es una aplicación aislada y accesible, no un prototipo documental. Puede crear y abrir jobs, persistir Layout V2 con control de revisión, subir PDFs, inspeccionar páginas y cajas, generar miniaturas, crear works y slots reales, mover y seleccionar slots en SVG, deshacer/rehacer, guardar automáticamente y calcular/aplicar Repeat como una operación reversible.

La base más estable está en Python: contrato estricto, persistencia atómica, almacenamiento seguro de assets, kernel geométrico puro y adaptadores aislados. La base frontend también está modularizada, pero continúa en JavaScript estándar con un kernel de vista reducido y duplicado. Esa duplicación está caracterizada para bounds cardinales mediante fixtures compartidos, no para toda la API geométrica Python.

La Fase 8P resolvió las contradicciones de locks, procedencia, fuentes, historial y estado visible; Fase 8A añadió precisión manual y una frontera central de acciones/atajos; Fase 8B completó las operaciones cardinales de objeto, clipboard interno, selecciones básicas y locks de usuario sin cambiar contrato ni backend. Permanecen como deudas para fases posteriores:

1. `activeFace`, `activeTool` y `hoverId` existen en el store, pero no tienen flujo funcional completo;
2. el artwork SVG no aplica `content_transform`: representa una miniatura completa con `meet` y clip trim, ahora advertida explícitamente como aproximada;
3. el OutputAdapter sigue sin conectar preview ni PDF final y bloquea transformaciones avanzadas, CTP activo, páginas distintas de 1 y cajas distintas de TrimBox;
4. la paridad geométrica JavaScript continúa siendo cardinal y parcial.

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
| `GET /api/editor-offset-v2/jobs/<job_id>/output-capabilities` | Diagnostica compatibilidad del layout persistido con el puente temporal. | No; informa la revisión analizada. |

No existen endpoints V2 de preflight profundo, preview, exportación ejecutable, CTP, Nesting o Hybrid.

### 3.3 Feature flag

`EDITOR_OFFSET_V2_ENABLED` se instala desde configuración Flask y por defecto queda desactivado salvo configuración o variable de entorno explícita. Con la bandera apagada, páginas y API V2 responden 404; la API devuelve `V2_DISABLED`. Los tests verifican que una aplicación V1 de prueba continúa disponible y que la bandera no crea estado global entre apps.

`EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED` es independiente y `false` por defecto. Solo controla la visibilidad de la herramienta placeholder; no habilita ni deshabilita Editor V2.

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
| `edit_policy.js` | Capacidades puras y enforcement atómico de locks. |
| `source_semantics.js` | Fuente predeterminada del work y override efectivo del slot. |
| `layout_metrics.js` | Conteos actuales derivados e historial de operación. |
| `output_panel.js` | Consulta y presentación del diagnóstico de salida temporal. |
| `object_operations.js` | Clipboard, filtros de selección, estado de locks y preparación de paste. |
| `objects_panel.js` | UI accesible de rotación, clipboard, selección y locks de usuario. |
| `command_registry.js` | Frontera central de acciones, disponibilidad, atajos y ayuda. |
| `shortcut_manager.js` | Normalización y scopes de teclado; no contiene rutas paralelas de mutación. |
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
- previews de slots duplicados;
- clipboard interno y contador de pegados;
- estado de guardado;
- selección/estado del panel de assets;
- propuesta/estado Repeat;
- undo/redo y contadores de cambio.

`activeFace` se inicializa con la primera cara habilitada, pero no existe setter ni navegación de cara en el shell. `activeTool` queda en `select`; el botón de selección no tiene comportamiento de cambio de herramienta. `hoverId` y `setHover()` no se conectan a interacciones o renderer. Son estados latentes.

## 9. Comandos, undo/redo y guardado

Comandos actuales:

- `CreateSlotCommand` para bundle placeholder;
- `MoveSlotsCommand`;
- `RotateSlotsCommand`;
- `DuplicateSlotsCommand`;
- `DeleteSlotsCommand`;
- `SetSlotUserLocksCommand`;
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

### 9.4 Política de locks estabilizada

`edit_policy.js` resuelve `move`, `rotate`, `delete`, `replace_content` y `replace_by_repeat`. Cualquier fuente válida (`user`, `engine`, `ctp`, `system`) bloquea cuando realmente está presente. Drag, inspector, nudge, rotación, cut/delete y sustitución consultan la política; los comandos vuelven a defenderla; y una operación múltiple con un bloqueado rechaza el conjunto completo con IDs visibles. La UI 8B solo agrega o retira `user` y preserva las otras fuentes. Repeat normal ya no crea un lock de geometría: su procedencia permanece exclusivamente en `generated_by`.

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

Trim y bleed se dibujan desde dimensiones sin rotar dentro del grupo rotado. La vista deriva bounds productivos con bleed, dibuja el rectángulo de `printable_margins_mm` y clasifica por separado `is-outside-sheet` e `is-outside-printable`. No corrige ni bloquea el movimiento.

### 10.4 Artwork

Para assets `ready`, el renderer usa `<image>` con URL de miniatura, `preserveAspectRatio="xMidYMid meet"` y clip rectangular trim. El artwork rota con el slot y la selección queda encima.

Limitaciones confirmadas:

- la miniatura representa la página completa, no un recorte exacto de la caja elegida;
- no aplica offset de la caja PDF;
- no aplica `fit_mode`, escala, offset interno, rotación interna ni espejo;
- siempre recorta visualmente a trim, aunque `content_transform.clip_to` declare otra cosa;
- marca mismatch de dimensiones por clase CSS;
- muestra una advertencia no intrusiva `Vista aproximada del PDF`; el diagnóstico de salida temporal permanece separado.

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

El bundle placeholder continúa en `commands.js`, tiene asset `status=error` y preflight bloqueante. OutputAdapter y Repeat lo rechazan. El botón solo se renderiza con `EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED=true`; el editor normal lo oculta.

## 12. Repeat V2

### 12.1 Flujo

El panel guarda primero cambios locales, envía revisión/work/cara/settings/modo y recibe una propuesta. El servidor no persiste. La propuesta solo entra al layout si el usuario pulsa Aplicar; entonces `ApplyRepeatCommand` realiza add o replace como una sola operación y activa autosave.

### 12.2 Adaptador y motor

`RepeatEngineAdapter` traduce V2 al mínimo legacy esperado por `build_step_repeat_slots()`. El motor usa esquina inferior izquierda de footprint productivo, nombres `width_mm/height_mm`, bleed y rotaciones 0/90. El adaptador reconstruye centro trim, trim original, bleed separado y rotación cardinal V2, y valida bounds/overlap con el kernel.

`step_repeat_pro_engine.py` no fue modificado. El adaptador consume `build_step_repeat_slots` e `IncompleteImpositionError.details`; también depende de que la salida contenga `design_ref`, `x_mm`, `y_mm` y `rotation_deg` 0/90.

### 12.3 Cantidades

Se distinguen requested, placed, unplaced y overproduced. Sin fill no sobreproduce. Con parcial permitido, reduce determinísticamente conteos y recalcula. Con fill, busca capacidad adicional. `exact_quantity` queda registrado, pero el permiso operativo de sobreproducción depende de `fill_remaining_space`.

### 12.4 Frente/dorso

Repeat puede calcular front o back en backend si la cara está habilitada y el work tiene la fuente correspondiente. No inventa ni espeja dorso. Hasta que exista navegación de cara, la UI deshabilita `back` y solo envía `front`.

### 12.5 Semántica de resultado y métricas

`last_result` se conserva como trazabilidad histórica del momento de aplicación. La UI deriva de los slots actuales el total de la cara, total por work y cuántos slots de la última `operation_id` siguen presentes. La respuesta Repeat expone `proposal_utilization_pct` y `projected_total_utilization_pct`; `utilization_percent` se conserva temporalmente con el significado histórico de propuesta.

### 12.6 Limitaciones

- No hay preview fantasma de la propuesta en canvas.
- Add bloquea colisión con slots existentes; el motor no los recibe como obstáculos para reacomodar.
- Replace actúa por work/cara y, desde 8P, respeta atómicamente locks de delete/contenido mediante `edit_policy.js` y defensa del comando.
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

La cobertura vigente suma 66 casos Node: 51 casos hasta Fase 8A y 15 casos
específicos de Fase 8B. La cobertura acumulada incluye:

- registro de acciones, IDs únicos, disponibilidad y conflictos de atajos;
- normalización Ctrl/Meta/Shift, `?` y protección de inputs/roles editables;
- parseo punto/coma, absoluto, delta, no-op y atomicidad de locks;
- nudge de tres pasos, batching, timeout, cambio de selección, blur y otro comando;
- integración con save, undo/redo, dirty, autosave y ayuda temporal.
- rotación cardinal, no-op, conservación de centro/trim/bleed/source y locks;
- duplicado, IDs, procedencia, offsets, selección y redo estable;
- clipboard profundo, same-job, referencias y paste acumulativo;
- cut/delete atómicos, selecciones por cara/work/asset efectivo;
- locks de usuario mixtos y preservación de otras fuentes;
- scopes de atajos de objeto y separación entre preview/clipboard y autosave.

No hay entorno DOM unitario: renderer, interactions, assets panel y Repeat panel se prueban principalmente a través de helpers puros o Playwright.

### 13.3 Playwright

La suite aislada vigente contiene seis recorridos Playwright. Además del flujo
productivo original y la precisión 8A, Fase 8B prueba un job real con PDF, work y
slots Repeat para:

1. posición absoluta con punto/coma y reflejo en SVG;
2. delta multiselección conservando distancias;
3. nudge `0.1`, `1`, `10 mm` y una ráfaga = un undo;
4. Ctrl+S, undo/redo por teclado y persistencia después de recargar;
5. aislamiento de flechas en input y rechazo de valor inválido sin guardar;
6. lock geométrico contra drag, inspector y nudge con feedback;
7. ayuda `?`/Escape sin dirty ni revisión;
8. continuidad de etiquetas visuales y output capabilities;
9. rotación cardinal, selector, undo/redo, duplicado y persistencia;
10. clipboard, cut/delete, selecciones básicas y locks de usuario;
11. protección de inputs, Alt+drag, preview y cancelación con Escape;
12. ayuda central actualizada.

Continúa sin cubrir en Playwright:

- precisión con zoom/pan;
- sustitución de fuente visible;
- error de upload visible;
- conflicto 409 y botón de recarga;
- flujo back en UI;
- add/replace visible de Repeat;
- parcialidad/fill visible;
- adaptador de salida, preview o PDF.

## 14. Matriz de estado funcional

| Capacidad | Estado | Evidencia y límite |
| --- | --- | --- |
| Contrato Layout V2 | Implementada y probada | Schema, validador, fixtures y tests parametrizados. |
| Kernel Python | Implementada y probada | Modelos, polígonos, SAT, bounds, distancias y fixtures. |
| Jobs/lectura/guardado revisionado | Implementada y probada | Servicio, repositorio, rutas y tests atómicos/conflicto. |
| Feature flag y aislamiento V1 | Implementada y probada | Blueprint y tests por app. |
| Store persistente/temporal | Implementada y probada | Node prueba separación y estado. |
| Registro central de acciones/atajos | Implementada y probada | IDs estables, conflictos, scopes, ayuda y rutas únicas desde botones/teclado. |
| Comandos y undo/redo | Implementada y probada | Comandos base/assets/Repeat/posición; botones y Ctrl/Cmd+Z/Shift+Z/Ctrl+Y comparten acciones. |
| Dirty/autosave/409 | Implementada y probada | Node y tests HTTP; conflicto visible no está en Playwright. |
| Canvas SVG trim/bleed | Implementada y probada | Código + fixtures Node; sin screenshot/regresión visual. |
| Selección simple/múltiple/lista | Implementada y probada | Node cubre store; interacción DOM no tiene Playwright dedicado. |
| Drag con preview temporal | Implementada y probada | Política de move, comando, undo/redo, autosave y Playwright con slot Repeat. |
| Zoom/pan/reset | Implementada parcialmente | Código activo; sin test de precisión DOM/E2E. |
| Pliego y área imprimible | Implementada y probada | Señales separadas por footprint con bleed; no bloquean ni corrigen. |
| Upload/asset inmutable/hash | Implementada y probada | Servicio/rutas/rollback/seguridad. |
| Inspección de cajas PDF | Implementada y probada | Cajas y ausencia explícita; no preflight profundo. |
| Miniaturas | Implementada y probada | PNG y endpoint; recorte por caja no implementado. |
| Works y slots reales front | Implementada y probada | Node + Playwright para work y Repeat; slot manual visible no E2E. |
| Fuente posterior distinta | No implementada | Solo checkbox para reutilizar la fuente seleccionada. |
| Slot manual back | No implementada | Fábrica fija `face=front` y `front_source`. |
| Artwork SVG | Implementada parcialmente | Miniatura, clip trim, rotación del slot; no `content_transform` ni caja exacta. |
| Sustitución de fuente | Implementada y probada | Node cubre comando; UI no está en Playwright. |
| Placeholders dev | Implementada y probada | Válidos en contrato, no exportables; ocultos por defecto con flag independiente. |
| Repeat proposal | Implementada y probada | Servicio/adaptador/endpoints y Playwright. |
| Repeat add/replace | Implementada y probada | Node; Playwright solo aplica modo add. |
| Repeat parcial/fill | Implementada y probada | Python; no flujo visible Playwright. |
| Repeat back | Implementada y probada en backend | UI temporalmente deshabilitada hasta navegación de cara. |
| Output capabilities | Implementada y probada | Endpoint/UI de solo lectura; no equivale a preflight ni PDF. |
| OutputAdapter | Implementada y probada, puente temporal | Diagnóstico conectado; renderer productivo todavía desconectado. |
| Preview productivo | No implementada | Sin endpoint/UI V2. |
| PDF final V2 | No implementada | Sin conexión al renderer productivo. |
| CTP productivo | Bloqueada por otra fase | Contrato existe; adapter bloquea `ctp.enabled=true`. |
| Preflight PDF profundo | No implementada | Solo estructura y campos `not_run`. |
| Inspector editable X/Y | Implementada y probada | Absoluto para uno, delta para varios, punto/coma, Enter/Escape, no-op y locks. |
| Nudge | Implementada y probada | `0.1/1/10 mm`, Y canónica, multiselección y autorepeat agrupado en un comando. |
| Rotación manual cardinal | Implementada y probada | Acción/UI/atajos, locks, undo/redo y persistencia sin alterar centro trim. |
| Duplicar/clipboard/cut/delete | Implementada y probada | IDs nuevos, procedencia duplicate, paste acumulativo y política atómica. |
| Locks operativos y UI de usuario | Implementada y probada | Geometry/content/delete; solo alterna `user` y preserva otras fuentes. |
| Selección por cara/work/asset | Implementada y probada | Temporal, sobre cara activa y fuente efectiva del slot. |
| Alt+drag duplicado | Implementada y probada | Preview temporal, un comando, Escape/blur/pointercancel sin dirty. |
| Box select/árbol avanzado | No implementada | Solo lista plana, multiselección y criterios básicos 8B. |
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
| `04_SHELL_Y_JOBS_V2.md` | Histórico de fase | Conserva el cierre de Fase 4 y enlaza a estado/roadmap vigentes. |
| `05_CANVAS_STORE_V2.md` | Histórico de fase | Conserva el cierre de Fase 5 y enlaza a estado/roadmap vigentes. |
| `06_ASSETS_Y_SLOTS_V2.md` | Histórico de fase | Conserva el cierre de Fase 6 y enlaza a estado/roadmap vigentes. |
| `07_REPEAT_V2.md` | Histórico de fase | Conserva el cierre de Fase 7; la semántica posterior está en esta auditoría y en Fase 8P. |

No se modificó ninguno de estos documentos durante la auditoría.

## 16. Deuda y riesgos prioritarios

### Alta prioridad después de Fase 8B

1. **Paridad geométrica frontend incompleta.** Bounds cardinales y área imprimible bastan para movimiento inicial, pero no para box select poligonal, overlap, snap avanzado o resize.
2. **Dos geometrías distintas por concepto.** La UI futura debe separar slot productivo y transformación interna del artwork; mezclarlas produciría diferencias con output.
3. **Salida productiva desconectada.** El diagnóstico informa compatibilidad, pero no debe confundirse con preview/PDF ni ejecutar el puente legacy.

### Prioridad media

4. No hay navegación activa frente/dorso; la UI bloquea back para evitar objetos invisibles.
5. El tree actual es una lista plana de slots de la cara activa.
6. Pan no tiene prueba de precisión y su cálculo por píxel no deriva directamente del viewBox real.
7. Preflight profundo, corrección PDF y motor de salida nativo siguen pendientes.

## 17. Conclusión

Tras 8B, V2 dispone de posicionamiento manual exacto, acciones centrales,
rotación cardinal, duplicado, clipboard interno, selecciones básicas, locks de
usuario y Alt+drag sobre un único Store/historial. No está listo para habilitar
resize, transformación interna del PDF, ocultación productiva, grupos
persistentes o herramientas basadas en colisiones avanzadas sin decisiones de
contrato y paridad geométrica adicionales.

La siguiente fase recomendada es 8C: alineación, centrado, distribución y
matriz. Debe reutilizar el registro y la política central sin incorporar snap,
resize, artwork ni salida productiva.
