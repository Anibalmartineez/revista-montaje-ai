# Estado actual del Editor Offset Visual V2 después del rediseño UX

> Actualización 39A (2026-09-16): preflight nativo V2, política/capacidades versión 2; snapshot de layout, opciones y archivos efectivos. Se rechazan reportes incompletos, obsoletos o incompatibles y derivados ausentes/alterados. Publicación y limpieza coordinadas; entrega desde bytes de la petición. El candidato PDF raster bloquea preservación vectorial hasta 39B. Gates globales apagados. Evidencia y continuación: [plan 39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md). Lo que sigue conserva el corte histórico indicado.

## 1. Control documental

Fecha de corte: 2026-09-06.

Actualización posterior al cierre UX, también del 2026-09-06: la auditoría SAFE de salida/preflight fue presentada y el usuario aprobó iniciar su fase documental en `codex/editor-offset-v2-output-preflight`. V2 será el editor principal, con código productivo propio e independiente; puede copiar y adaptar código útil de V1, sin mantener dependencias legacy como arquitectura final. La especificación nueva está en [21_CONTRATO_PREFLIGHT_V2.md](21_CONTRATO_PREFLIGHT_V2.md). No hay implementación productiva nueva. Los datos de rama y pruebas siguientes pertenecen al cierre 19-G, salvo actualización expresamente identificada.

Actualización posterior de salida: el usuario autorizó reutilización temporal de funciones V1 y el ensayo controlado [22 — Reutilización de salida V1](22_ENSAYO_REUTILIZACION_SALIDA_V1.md). Existe un invocador offline V2 con snapshots de fuentes, PDF experimental y preview derivada del mismo PDF. La validación focalizada ejecutó 78 pruebas (23 nuevas de ensayo, 50 de adaptador y 5 de inspector). Se demostraron posiciones y giros sin bleed en ambos modos; se reprodujeron diferencias de bleed y marcas. No se modificaron rutas, canvas, contrato, jobs reales ni motor V1. Preview/PDF/CTP productivos continúan pendientes. La rama y evidencia que siguen corresponden al cierre UX histórico.

Actualización vigente de salida — [Fase 23](23_PREPARACION_FUENTES_Y_PARIDAD_SALIDA_V2.md): preparación propia V2 de página/caja/rotación, bleed fuente o espejo explícito, marcas por slot y ensayo PDF con fuentes derivadas. El canvas solicita ahora miniaturas de la caja seleccionada. Se reutiliza la geometría V2 y el renderer manual V1 sin modificar módulos compartidos. Validación: 404 tests Python V2 y 1 skipped, 117 Node y 21 Playwright V2; copia del montaje real con ocho piezas comprobada.

Actualización vigente de salida — [Fase 24](24_PREFLIGHT_EJECUTABLE_V2.md): preflight mínimo ejecutable y reporte inmutable bajo `reports/`, con comprobaciones de contrato, identidad física PDF, cajas, geometría, solapes y capacidades temporales. La UI puede ejecutarlo sobre la última revisión guardada y marca el reporte como desactualizado cuando cambia el Layout. Preview, PDF final y CTP permanecen bloqueados; todavía no hay renderer productivo V2. Los apartados de evidencia UX inferiores mantienen su corte histórico.

Actualización vigente de salida — [Fase 26](26_FIXTURES_Y_PARIDAD_PDF_V2.md): fixtures PDF canónicos y prueba de contrato/paridad métrica incorporados bajo `tests/fixtures/editor_offset_v2/`. Se cubren cajas desplazadas y ausentes, multipágina, rotaciones intrínsecas, candidato de bleed por espejo explícito, marcas/clipping y expectativas declaradas de frente/dorso y transformaciones. La prueba focalizada pasa (4 tests), la suite Python V2 pasa (412 tests, 1 omitido) y los bytes se mantienen estables al regenerar. Preview, PDF final y CTP siguen bloqueados; la tolerancia visual final y el renderer V2 propio continúan pendientes.

Actualización vigente de salida — [Fase 27](27_PREVIEW_MINIMA_GATED_V2.md): Preview V2 mínima propia implementada como PNG derivado por cara, con validación física, gate `EDITOR_OFFSET_V2_PREVIEW_ENABLED` apagado por defecto y publicación atómica bajo `previews/`. Solo admite transformación interna identidad y bloquea explícitamente marcas, flip dúplex y capacidades no resueltas. Sus 4 pruebas pasan y la suite Python V2 queda en 416 passed y 1 omitido. PDF final y CTP permanecen fuera de alcance.

Actualización vigente de salida — [Fase 28](28_PARIDAD_PREVIEW_CANVAS_V2.md): se añadió evidencia automática de paridad geométrica Preview–canvas con un PDF asimétrico sintético, comprobando dimensiones de hoja, footprint del slot, orden izquierda/derecha y preservación de revisión. La prueba focalizada queda en 9 passed y la suite Python V2 en 417 passed y 1 omitido. La tolerancia visual completa, transformaciones internas, clipping, bleed por espejo, marcas y flip dúplex siguen pendientes; Preview continúa detrás de su gate.

Actualización vigente de salida — [Fase 29](29_TRANSFORMACIONES_PREVIEW_V2.md): la Preview V2 propia admite `actual_size`, `contain`, `cover`, `stretch`, escalas, offsets, rotaciones internas, espejos y clipping a trim/bleed. El bleed por espejo requiere la opción explícita `allow_mirror_bleed`. La prueba focalizada queda en 9 passed y la suite Python V2 en 421 passed y 1 omitido. Marcas, flip dúplex, clipping sin límite, tolerancia visual final y PDF productivo permanecen pendientes.

Actualización vigente de salida — [Fase 30](30_MARCAS_Y_DUPLEX_PREVIEW_V2.md): la Preview V2 propia dibuja marcas de corte por slot y representa el flip dúplex horizontal o vertical de la cara posterior. Registro, texto técnico y barras siguen bloqueados explícitamente. La prueba focalizada queda en 10 passed y la suite Python V2 en 422 passed y 1 omitido. El PDF productivo continúa pendiente.

Actualización vigente de salida — [Fase 31](31_PDF_FINAL_GATED_V2.md): se incorporó una ruta PDF V2 propia detrás de `EDITOR_OFFSET_V2_PDF_FINAL_ENABLED`, con páginas por cara, tamaño físico del pliego, publicación atómica y errores estructurados. El artefacto actual es un candidato rasterizado basado en el compositor V2; no declara preservación vectorial ni habilitación productiva. La prueba focalizada pasa (3 tests) y la suite Python V2 queda en 425 passed y 1 omitido.

Rama revisada:

    codex/editor-offset-v2-ux-foundation

Base de comparación:

    main
    merge-base 9ee6e79e0e58af1ec166bfb5edd59592be4dae05
    HEAD revisado 3694602

Este documento es la fuente operativa vigente para comprender el Editor Offset Visual V2 después de completar las Fases 19-A a 19-G.

Jerarquía documental:

- `01_CONTRATO_LAYOUT_V2.md` continúa siendo la fuente contractual de Layout V2;
- `02_KERNEL_GEOMETRICO_V2.md` continúa siendo la fuente geométrica;
- `03_ADAPTADOR_SALIDA_V2.md` continúa describiendo la frontera temporal de salida;
- los documentos 04 a 17 conservan historia y decisiones específicas de sus fases;
- `18_ESTADO_ACTUAL_POST_EXPLORACIONES_1_A_4_V2.md` es el snapshot histórico previo a las correcciones;
- `19_PLAN_Y_TRAZABILIDAD_REDISENO_UX_V2.md` conserva plan, decisiones, pruebas y bitácora del rediseño;
- este documento 20 resume el estado actual y debe consultarse primero para planificar cambios nuevos;
- el documento 21 define el contrato canónico del reporte; la implementación mínima y su evidencia están registradas en los documentos 24 y 25.

No se reescribió el contenido histórico del documento 18. Solo se le agregó una advertencia que dirige a este estado vigente.

## 2. Resumen ejecutivo

Editor V2 es actualmente un editor visual independiente de V1, con jobs propios, Layout V2 validado, assets PDF inmutables, works, slots, Repeat, edición manual, historial reversible, guardado con revisión optimista y herramientas de composición y precisión.

El programa de rediseño no reconstruyó el editor. Estabilizó seis defectos observados, mejoró la legibilidad, organizó las herramientas por flujo, incorporó la configuración segura del pliego y resolvió el acceso responsive sin cambiar backend, esquema ni salida.

Estado general:

- estabilidad del flujo editado: validada;
- contrato y persistencia Layout V2: conservados;
- UX incremental de escritorio: implementada;
- operación responsive en 1440, 1050 y 820 px: validada;
- configuración de pliego por job: implementada y persistente;
- preview mínima V2: implementada detrás de gate; Preview productiva completa: pendiente;
- PDF final V2: no implementado;
- preflight mínimo ejecutable: implementado en Fase 24; no equivale a preflight productivo completo;
- CTP productivo V2: no implementado;
- Resize 8F y transformaciones internas 8G: no implementados.

Conclusión: la rama está preparada para revisión focalizada de V2. No debe confundirse “rediseño UX cerrado” con “editor listo para producción PDF/CTP”.

## 3. Evidencia usada

### Confirmado por código

- diff completo de la rama contra `main`;
- template, CSS, bootstrap, Store, comandos, registro de acciones y controladores;
- blueprint, servicios, dominio, esquema, repositorios y adaptador de salida V2;
- suites Python, Node y Playwright V2;
- documentos V2 01 a 19.

### Confirmado por ejecución automatizada

- sintaxis de todos los módulos JavaScript V2;
- 117 tests Node V2;
- 331 tests Python V2, con 1 skipped;
- 20 recorridos Playwright V2;
- `git diff --check`.

### Confirmado en navegador y persistencia

- ruta V2 y Flask activos;
- página no vacía y sin overlay de framework;
- consola sin warnings ni errores relevantes;
- panel responsive Fuentes abre, cierra con Escape y restaura foco;
- job real leído mediante API sin mutarlo;
- screenshot de la interfaz actual en ancho compacto.

## 4. Límite real de la aplicación

El flujo de alto nivel permanece:

```text
app.py
  -> editor_offset_v2.blueprint
  -> rutas HTML y API V2
  -> servicios de jobs, assets, Repeat y output-capabilities
  -> JobRepository privado en instance/editor_offset_v2_jobs

GET shell/job
  -> templates/editor_offset_visual_v2.html
  -> contexto JSON inicial
  -> bootstrap.js
  -> EditorStore + controladores + registro de acciones
  -> canvas SVG y paneles

comando persistente
  -> store.executeCommand()
  -> undo/redo + changeVersion
  -> SaveCoordinator
  -> PUT layout con base_revision
  -> compare-and-swap + revisión nueva
```

El frontend sigue siendo JavaScript clásico cargado con `defer`. No se introdujeron React, Vite, TypeScript ni un build frontend.

## 5. Rutas activas y responsabilidades

| Método y ruta | Estado y responsabilidad |
| --- | --- |
| `GET /editor_offset_visual_v2` | Activo. Abre el shell sin job. |
| `GET /editor_offset_visual_v2/<job_id>` | Activo. Abre un job y carga su contexto. |
| `POST /api/editor-offset-v2/jobs` | Activo. Crea un job con fallback de pliego 700 × 500 mm. |
| `GET /api/editor-offset-v2/jobs/<job_id>` | Activo. Lee Layout V2 persistido. |
| `PUT /api/editor-offset-v2/jobs/<job_id>/layout` | Activo. Guarda con `base_revision` y conflicto 409. |
| `POST /api/editor-offset-v2/jobs/<job_id>/assets` | Activo. Incorpora un PDF físico e inmutable. |
| `GET /api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/thumbnails/<page>` | Activo. Sirve miniatura segura; `?box=` usa la caja física elegida por el canvas desde Fase 23. |
| `POST /api/editor-offset-v2/jobs/<job_id>/imposition/repeat` | Activo. Calcula Repeat sin persistir hasta Aplicar. |
| `GET /api/editor-offset-v2/jobs/<job_id>/output-capabilities` | Activo, diagnóstico temporal. No genera salida. |
| `POST /api/editor-offset-v2/jobs/<job_id>/preflight` | Activo. Publica un reporte mínimo inmutable; no genera salida. |
| `POST /api/editor-offset-v2/jobs/<job_id>/preview` | Implementado detrás de `EDITOR_OFFSET_V2_PREVIEW_ENABLED`; apagado por defecto y limitado a la Preview mínima de la Fase 27. |

No existe Preview productiva habilitada por defecto ni hay rutas V2 de PDF final, nesting, hybrid, preflight profundo completo o CTP productivo.

## 6. Mapa actualizado de conexiones frontend

| Superficie | Propietario principal | Acción o dependencia | Persistencia |
| --- | --- | --- | --- |
| Inicio y composición | `bootstrap.js` | Construye Store, API, renderer, interacciones y paneles | No por sí mismo |
| Contrato DOM | `dom_refs.js` | Resuelve IDs usados por todos los controladores | No |
| Flujo por etapas | `workflow_navigation.js` | Preparar, Imponer, Ajustar, Validar y Salida | Temporal |
| Responsive | `responsive_panels.js` | Cajones Fuentes/Inspector, `inert`, ARIA y foco | Temporal |
| Fuentes y works | `assets_panel.js` | Upload y comandos de work/slot/fuente | Sí, por API/comando |
| Canvas | `canvas_renderer.js` | Renderiza pliego, área imprimible, artwork y slots | Solo lectura |
| Pointer y viewport | `interactions.js` | Selección, drag, Alt+drag, pan, zoom y medición | Mixto; solo comandos persisten |
| Acciones | `command_registry.js` | Frontera única para botones y atajos | Según acción |
| Mutaciones | `commands.js` | Execute, undo y redo reversibles | Sí |
| Estado | `store.js` | Layout, revisión, historial y estado temporal separado | Layout sí; UI temporal no |
| Guardado | `autosave.js` | Debounce, serialización y conflicto | Sí |
| Pliego | `sheet_panel.js` | Borrador, validación, impacto y confirmación | Solo al ejecutar `sheet.update` |
| Repeat | `repeat_panel.js` | Calculate y Apply | Propuesta temporal; Apply persiste |
| Objetos | `objects_panel.js` | Operaciones, locks y clipboard | Según comando |
| Composición | `arrangement_panel.js` | Alinear, distribuir, gaps y matriz | Según comando |
| Precisión | `precision_panel.js` | Reglas, guías, snap y medición | Temporal salvo movimiento ejecutado |
| Selección avanzada | `object_tree.js` | Árbol, visibilidad y selección | Temporal |
| Compatibilidad | `output_panel.js` | Consulta e invalida diagnóstico por revisión | Diagnóstico temporal |
| Preflight mínimo | `output_panel.js` + `preflight_service.py` | Comprueba revisión guardada, fuentes físicas y geometría | Reporte inmutable en `reports/` |

Regla central: un control nuevo no debe mutar Layout V2 directamente. Debe delegar en una acción registrada y, cuando corresponda, en un comando reversible.

## 7. Flujo actual del operador

### 7.1 Preparar

- crear un job;
- subir un PDF;
- seleccionar página y caja PDF;
- crear un work real;
- crear o sustituir una fuente de slot.

### 7.2 Imponer

- consultar la medida actual del pliego;
- abrir Configurar;
- editar ancho, alto y márgenes;
- revisar área útil e impacto geométrico;
- confirmar advertencias cuando corresponda;
- calcular y aplicar Repeat.

### 7.3 Ajustar

- posición exacta y nudge;
- rotación cardinal;
- duplicate, copy, cut, paste y delete;
- locks de usuario;
- alineación, centrado, distribución, gaps y matriz;
- reglas, guías, snap, smart guides y medición.

### 7.4 Validar

- selección avanzada y árbol de objetos;
- issues geométricos visuales;
- consulta de compatibilidad con el puente temporal de salida.

### 7.5 Salida

La etapa existe para mostrar la progresión y está rotulada “pendiente”. No ofrece botones productivos ni genera archivos.

## 8. Estado persistente y temporal

### Persistente

- Layout V2 bajo `layout_schema_version = 2`;
- sheet, assets, works, slots, imposition y output declarativo;
- revisión del job;
- mutaciones ejecutadas por comandos y guardadas por autosave.

### Temporal

- etapa activa;
- panel responsive abierto;
- selección actual;
- viewport, zoom y pan;
- clipboard interno y contador de pegado;
- borradores de posición, pliego, gaps, matriz, guía y medición;
- slot clave;
- visibilidad e aislamiento;
- diagnóstico output-capabilities presentado en pantalla.

El rediseño mantuvo esta separación. Navegar, abrir un panel, cambiar de etapa o consultar una vista no incrementa revisión ni ensucia el job.

## 9. Configuración actual del pliego

El job nace todavía con fallback 700 × 500 mm. La edición ocurre después de crearlo mediante Configurar.

Política aplicada:

- se editan únicamente `sheet.size_mm` y `sheet.printable_margins_mm`;
- ancho y alto deben ser positivos;
- márgenes deben ser no negativos y dejar área imprimible;
- punto y coma decimal son aceptados por la UI;
- Intercambiar y Restaurar trabajan primero sobre un borrador;
- slots existentes no se mueven, escalan, rotan ni eliminan;
- el impacto clasifica slots dentro, fuera del imprimible y fuera del pliego;
- una advertencia exige segunda confirmación;
- Apply crea un único `UpdateSheetCommand` reversible;
- undo, redo, autosave y recarga conservan el comportamiento;
- no existen presets inventados ni preferencia global del operador.

## 10. Modelo responsive vigente

- más de 1180 px: herramientas, Fuentes, canvas e Inspector visibles simultáneamente;
- 1180 px o menos: barra de herramientas y canvas en el grid; Fuentes e Inspector son cajones exclusivos;
- Preparar dirige a Fuentes;
- Imponer, Ajustar, Validar y Salida dirigen a Inspector;
- Configurar, Alinear, Distribuir y Repetir abren el contexto necesario;
- panel cerrado usa `inert` y `aria-hidden`;
- control de apertura usa `aria-controls` y `aria-expanded`;
- Cerrar, fondo y Escape restituyen el foco;
- controles de cajón tienen 44 px mínimos;
- Atajos permanece visible en 820 px;
- el editor no se declara optimizado para teléfonos.

## 11. Estabilizaciones cerradas

| ID | Estado actual |
| --- | --- |
| STAB-001 | Nudge usa temporizadores con receptor válido; no produce `Illegal invocation`. |
| STAB-002 | Delete y Cut bloquean un origen si quedan dependientes fuera de la selección; el conjunto puede borrarse atómicamente. |
| STAB-003 | Output-capabilities queda obsoleto al cambiar layout o revisión y exige reconsulta. |
| STAB-004 | Matriz bloquea un segundo submit accidental sobre la selección generada sin impedir una repetición deliberada. |
| STAB-005 | Conflicto 409 explica preservación local, efecto de recarga y recuperación. |
| STAB-006 | Clipboard acompaña undo/redo y Limpiar medición retira solo su feedback propio. |

Estas decisiones están cubiertas en tests Node y Playwright. No convierten output-capabilities en preflight productivo.

## 12. Evidencia del job real actual

Lectura realizada sin mutación:

| Dato | Valor observado |
| --- | --- |
| Job | `ev2_14d0c6f8f60e601aed51f833` |
| Revisión persistida | 57 |
| Schema | Layout V2 |
| Pliego | 650 × 550 mm |
| Márgenes | 0 mm en los cuatro lados |
| Assets | 1 |
| Works | 1 |
| Slots | 8 |
| Cara visible en UI | Frente, estado temporal |
| Estado del documento | Guardar deshabilitado; sin cambios locales pendientes observados |
| Consola | Sin warnings ni errores |
| Output-capabilities | No compatible, revisión 57 |
| Issues de salida | 16: `UNSUPPORTED_PDF_BOX` y `UNSUPPORTED_CONTENT_CLIP` repetidos por los slots afectados |

Este job sigue siendo evidencia local, no un fixture canónico. Sus medidas y revisión pueden evolucionar por acciones del usuario.

## 13. Cobertura validada al cierre

| Capa | Resultado 19-G |
| --- | --- |
| Sintaxis JavaScript V2 | Correcta en entrypoint y módulos |
| Node V2 | 117 passed |
| Python V2 | 331 passed, 1 skipped |
| Playwright V2 | 20 passed |
| Flask target V2 | `/` y `/editor_offset_visual_v2` HTTP 200 |
| Navegador integrado | Identidad, contenido, consola, screenshot e interacción correctos |
| Diff | `git diff --check` correcto |

Los 20 recorridos Playwright usados en 19-G pertenecen únicamente a:

- `tests/playwright/test_editor_offset_v2.py`;
- `tests/playwright/test_editor_offset_v2_ux_characterization.py`.

No se ejecutaron los archivos Playwright legacy que navegan a `/editor_offset_visual`.

La última suite global, ejecutada en 19-F, produjo 662 passed, 1 skipped y 14 failed. Los fallos corresponden a archivos fuera del diff de la rama. Como no se ejecutó el mismo baseline sobre `main`, no se afirma documentalmente que todos sean preexistentes.

## 14. Revisión de la rama

### Confirmado

- 12 commits funcionales/documentales antes del cierre 19-G;
- 27 archivos cambiados respecto de `main` antes de agregar este documento y la nota histórica;
- 6143 inserciones y 33 eliminaciones en ese corte;
- todos los cambios de producción pertenecen al frontend V2;
- no hay cambios en contratos JSON, rutas, dominio Python, persistencia backend o motores;
- no hay cambios en V1;
- no hay dependencias nuevas;
- cada bloque corresponde a una fase registrada en el documento 19.

### Evaluación

- estabilidad y correcciones focalizadas: riesgo bajo, bien cubierto y reversible por commit;
- reorganización HTML/CSS y navegación contextual: riesgo moderado por contrato DOM, mitigado por 20 Playwright e IDs únicos;
- configuración del pliego: riesgo moderado por mutación persistente, mitigado por comando único, undo/redo, autosave, recarga y conservación exacta de slots;
- responsive: riesgo bajo a moderado, porque solo agrega estado temporal y no cambia Layout V2;
- salida productiva: sin cambio; riesgo pendiente alto para una fase futura.

### Recomendación de revisión

La rama puede pasar a revisión focalizada de V2. Si el proceso de integración exige que toda la suite del repositorio esté verde, los 14 fallos globales deben triagiarse por separado o compararse contra `main`; no deben mezclarse silenciosamente con la implementación de esta rama.

## 15. Documentación alineada, histórica y pendiente

| Documento | Clasificación después de 19-G |
| --- | --- |
| 01 | Contractual vigente. |
| 02 | Geometría vigente. |
| 03 | Frontera temporal de salida vigente; producción pendiente. |
| 04-08 | Históricos de construcción y auditoría. |
| 09 | Roadmap útil; 8A-8E están superadas por implementación, 8F en adelante sigue futuro. |
| 10 | Decisiones semánticas vigentes, con contexto histórico. |
| 11 | Decisiones arquitectónicas de salida, concurrencia y linaje todavía abiertas. |
| 12-17 | Documentos específicos vigentes con límites históricos de su corte. |
| 18 | Snapshot histórico de exploraciones 1 a 4. |
| 19 | Plan, decisiones y bitácora completa del rediseño. |
| 20 | Estado operativo vigente. |
| 21 | Contrato canónico de preflight; parcialmente ejecutado por la Fase 24. |
| 24 | Implementación mínima ejecutable del preflight y su endpoint. |
| 25 | Guía de pruebas amplias, hallazgos y recomendaciones de esta auditoría. |
| 26 | Fixtures PDF canónicos y criterios de paridad; evidencia previa al renderer. |
| 27 | Preview mínima V2 propia detrás de gate separado; no es PDF final. |

Al cerrar el rediseño no se actualizaron 01, 02, 03 o el schema porque esa fase no cambió sus contratos. La fase documental posterior 21-A corrige descripciones auditadas en 02 y 03; conserva 01 y el schema sin cambios.

## 16. Pendientes reales después del rediseño

### Prioridad alta: preparación productiva

1. Completar el preflight profundo sobre el contrato 21 y el reporte mínimo de la Fase 24; la ejecución básica ya está disponible.
2. Resolver la matriz propuesta de advertencias/bloqueos y las decisiones PF-D01 a PF-D09 según el gate de cada una.
3. Resolver archivos físicos, página, cajas PDF, CropBox/TrimBox, clipping y `actual_size`.
4. Definir y aprobar criterios de paridad visual sobre los fixtures de la Fase 26.
5. Validar la Preview mínima de la Fase 27 contra canvas y fixtures, y cerrar transformaciones, clipping y marcas.
6. Diseñar el motor de salida propio V2 conforme a la independencia aprobada; el puente queda para diagnóstico/caracterización, sin ampliación productiva por defecto.
7. Establecer coherencia demostrable entre canvas, preview y PDF final.
8. Diseñar CTP, marcas, pinza, barras, texto técnico y caras como contrato específico.

### Prioridad media: robustez y operación

1. Definir concurrencia para más de un proceso Flask.
2. Diseñar recuperación de conflictos sin pérdida opcional de cambios locales.
3. Definir backups, retención y limpieza de jobs y derivados.
4. Probar PDFs dañados, cifrados, enormes, multipágina y con rotación intrínseca.
5. Validar Repeat `replace`, `partial`, `fill` y dorso con escenarios reales.
6. Medir render, hit testing y overlaps con 500 o más slots en navegador.
7. Ejecutar auditoría WCAG con lector de pantalla y navegadores adicionales.

### Prioridad posterior: herramientas nuevas

1. Presets reales de pliego basados en catálogo aprobado.
2. Resize 8F con ancla, proporción, rotación, locks, snap y exportabilidad definidos.
3. Transformaciones internas de artwork 8G separadas del trim del slot.
4. Frente/dorso, navegación de caras y mesa de luz 8H.
5. Productividad inteligente, recetas e IA con confirmación y guardrails.

## 17. Preguntas abiertas

1. ¿`generated_by.source_slot_id` será referencia contractual permanente o trazabilidad histórica tolerante?
2. ¿Qué condiciones exactas convierten un montaje en “listo para producción”?
3. ¿Qué issues bloquean guardado, cuáles bloquean exportación y cuáles solo informan?
4. ¿Qué cajas PDF soportará primero el renderer productivo?
5. ¿Se crearán assets derivados inmutables para normalizar caja, clipping o rotación?
6. ¿Qué tolerancias métricas y visuales aceptará la imprenta para preview/PDF?
7. ¿Qué estrategia de concurrencia se utilizará en producción multiproceso?
8. ¿Qué jobs existentes forman el conjunto obligatorio de compatibilidad?
9. ¿Cuándo se retira el diagnóstico temporal? El motor nativo independiente ya es la dirección aprobada; no es necesario conectar primero el puente a producción.
10. ¿Qué formatos de pliego reales justifican presets?

Preguntas resueltas por Fase 19:

- Delete bloquea dependientes no seleccionados y permite el conjunto atómico;
- output-capabilities se invalida al mutar layout o cambiar revisión;
- matriz bloquea únicamente la repetición accidental equivalente;
- conflicto explica la recuperación sin merge automático;
- el pliego se configura después de crear el job y no transforma slots;
- el responsive prioriza canvas y conserva acceso mediante cajones;
- Salida se muestra como pendiente, sin prometer PDF o CTP.

## 18. Revisión obligatoria antes de futuros cambios

### Si cambia la interfaz

Revisar juntos:

- `templates/editor_offset_visual_v2.html`;
- `static/css/editor_offset_visual_v2.css`;
- `dom_refs.js`;
- `bootstrap.js`;
- `workflow_navigation.js`;
- `responsive_panels.js`;
- `shortcut_manager.js` y `command_registry.js`;
- tests Node propietarios y ambos archivos Playwright V2.

### Si cambia el pliego o la geometría

Revisar además:

- `01_CONTRATO_LAYOUT_V2.md` y schema;
- dominio y validación Python;
- `geometry_kernel.js`, `geometry_view.js` y fixtures de paridad;
- `sheet_panel.js` y `UpdateSheetCommand`;
- Repeat, canvas, output-capabilities y persistencia;
- slots existentes, bleed, márgenes, undo/redo y recarga.

### Si cambia Repeat

Revisar:

- `repeat_panel.js` y `ApplyRepeatCommand`;
- RepeatService y RepeatEngineAdapter;
- `engines/step_repeat_pro_engine.py` compartido;
- modos add/replace/partial/fill/back;
- locks, procedencia, selección resultante y output.

### Si cambia preview, PDF o CTP

Revisar antes de programar:

- `03_ADAPTADOR_SALIDA_V2.md` y `11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md`;
- `21_CONTRATO_PREFLIGHT_V2.md`, sus reglas propuestas, cobertura y gates pendientes;
- output contract, output service y EditorOutputAdapter;
- resolución física y seguridad de assets;
- cajas PDF, trim, bleed, clipping, transformaciones y páginas;
- frente/dorso, marcas, perfiles y CTP;
- `montaje_offset_inteligente.py`, `services/editor_offset_output_service.py` y `strategies/` como superficies legacy compartidas;
- fixtures renderizados, tolerancias y comparación canvas/preview/PDF;
- error model, preflight y rollback.

### Si cambia persistencia o despliegue

Revisar:

- JobRepository, escritura atómica y compare-and-swap;
- revisión optimista, conflicto y beforeunload;
- varios workers, locks compartidos y recuperación;
- permisos, backups, límites, retención, logs y seguridad de archivos.

## 19. Próximo paso SAFE recomendado

La Fase 19 está cerrada. Actualización de 2026-09-16: las fases 34, 35 y 36 quedaron implementadas y verificadas en `codex/editor-offset-v2-output-preflight`; las fases 37 y 38 quedaron implementadas y verificadas en `codex/editor-offset-v2-output-contract-parity`. Repeat multipágina conserva las cuatro orientaciones cardinales; Preview y PDF final consumen preflight vigente por operación; la regeneración, los fallos de publicación, la concurrencia multiproceso y la limpieza conservadora tienen cobertura específica. La siguiente prioridad SAFE es ampliar fixtures y tolerancias de color/vector antes de habilitar producción amplia; no es 19-H.

Orden recomendado:

1. ampliar fixtures y tolerancias de color/vector antes de producción;
2. habilitar Preview productiva mínima detrás de su gate explícito;
3. implementar el renderer PDF final V2 propio con verificación de artefactos;
4. CTP, marcas y dúplex productivo bajo sus fases correspondientes;
5. independizar Repeat y demás código compartido mediante fases de extracción, sin ampliar el puente como arquitectura final;
6. retomar Resize 8F únicamente cuando su efecto sobre exportación esté definido.

No conviene comenzar directamente por botones de PDF o CTP. Primero debe existir un contrato capaz de decidir con evidencia si un montaje puede producirse y cómo se representa cada error o advertencia.

La independencia es una decisión de destino, no una descripción del runtime actual. Las bibliotecas externas pueden seguir utilizándose. Empaquetado, despliegue y separación de repositorio no se han decidido. El inventario completo de dependencias a extraer corresponde a una fase propia.

## 20. Gate para comenzar la siguiente fase

Antes de modificar código nuevamente:

- aprobar el objetivo de la fase;
- elegir una única prioridad productiva;
- definir entradas, salidas y no objetivos;
- listar contratos y archivos afectados;
- caracterizar el comportamiento actual;
- crear fixtures aislados;
- definir rollback;
- decidir qué pruebas deben pasar;
- confirmar si se requiere compatibilidad con jobs actuales;
- no usar el job real como fixture destructivo;
- no mezclar preflight, PDF, CTP, resize e IA en un mismo bloque.

La Fase 24 habilita únicamente diagnóstico y publicación de reportes. Los detalles de política productiva, clipping, perfiles, caras, preview, PDF y CTP siguen sujetos a fases propias y no están habilitados por este endpoint.

### Fase 32A — Trabajos multipágina

La interfaz V2 incorpora un planificador temporal por página para el asset seleccionado.
Permite seleccionar varias páginas, asignar cantidades independientes y crear un work
por página mediante un comando único reversible. El contrato Layout V2 no cambia; firmas,
encuadernaciones y edición derivada de assets permanecen fuera de esta fase.

### Fase 32B — Correcciones gráficas

El inspector V2 permite editar de forma reversible el `content_transform` de uno o
varios slots: ajuste, escala, offset interno, rotación cardinal, espejo y clipping.
El PDF fuente sigue inmutable. Recorte físico, extensión de fondos y edición derivada
de páginas quedan pendientes de 32C.

### Fase 32C — Derivados de página

Se añadió una infraestructura optativa y bloqueada para materializar una página PDF
derivada con la preparación V2, hash y manifiesto atómico. El asset original y Layout
V2 permanecen intactos; la conexión del derivado con slots y salida productiva requiere
un contrato propio posterior.

### Fase 32D — Integración de derivados

`sourceRef` admite ahora una referencia derivada opcional y verificada. El inspector
puede vincular una página derivada a un slot mediante un comando reversible. Preview y
PDF final comprueban ruta, hash y legibilidad antes de consumirla; los gates de
materialización, Preview y PDF final continúan separados y apagados por defecto.

### Fase 32E — Guardia de paridad para derivados

Fase intermedia cerrada: protegió la materialización mientras el servicio aún no
aplicaba una matriz PDF completa. Su resultado queda sustituido por 32F.

### Fase 32F — Materialización transformada

La página derivada hornea la transformación gráfica V2 a 300 DPI y registra la
transformación en el manifiesto. La vinculación al slot restablece el
`content_transform` a identidad dentro del mismo comando reversible, por lo que
Preview y PDF final no aplican dos veces la matriz. La salida continúa detrás de
los gates existentes y requiere evidencia visual adicional antes de producción.

### Fase 33 — Paridad de derivados, Preview y PDF

Se añadió una prueba canónica con artwork asimétrico que compara el recorte de la
Preview contra el PDF derivado transformado y la Preview completa contra el PDF
candidato. La prueba fija tolerancias de caracterización para el fixture y DPI
36; no habilita salida productiva. Color, preservación vectorial, CTP y perfiles
de imprenta siguen pendientes.

### Fase 34 — Repeat multipágina y orientaciones cardinales

El planificador de páginas activa 0°, 90°, 180° y 270° por defecto y conserva la
selección por work. El adaptador V2 traduce explícitamente las clases 180°/270°;
el motor compartido V1 no se modificó.

### Fase 35 — Preflight obligatorio

Preview y PDF final generan y consumen un reporte con hash y revisión del layout,
decisión por operación y gate explícito. Un reporte incompleto, obsoleto o con
hallazgos bloqueantes impide la salida y no deja PDF parcial.

### Fase 36 — Endurecimiento operativo

Se verificaron cantidades altas, documentos multipágina, Repeat, regeneración
determinista y limpieza de temporales. La concurrencia multiproceso y la política
de retención automática siguen pendientes de una prueba operativa dedicada.

### Fase 37 — Contrato canónico de paridad de salida

Se centralizaron versión y tolerancias métricas/visuales para cajas PDF,
geometría del canvas y comparaciones Preview/PDF. Los fixtures existentes
continúan cubriendo cajas, páginas, rotaciones, bleed, clipping, marcas y
frente/dorso. La captura DOM SVG, color/vector y CTP permanecen fuera de esta
fase.

### Fase 38 — Concurrencia, retención y recuperación operativa

Se añadió un lock de archivo multiplataforma para escrituras de layout y
publicación de artefactos, además de recuperación conservadora de temporales y
retención explícita de previews, reports y outputs. Los assets fuente y
derivados inmutables quedan fuera de la limpieza automática; la ejecución
programada de retención requiere una decisión operativa posterior.
