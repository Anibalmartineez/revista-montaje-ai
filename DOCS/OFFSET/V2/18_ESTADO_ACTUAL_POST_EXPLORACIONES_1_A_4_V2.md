# Estado actual del Editor Offset Visual V2 después de las exploraciones 1 a 4

## 1. Estado y propósito del documento

Fecha de corte: 2026-09-04.

Este documento es la fotografía operativa más reciente del Editor Offset Visual V2 después de cuatro exploraciones interactivas realizadas contra la aplicación Flask real.

Sus objetivos son:

- registrar qué se comprobó realmente en navegador;
- separar funcionamiento confirmado, defectos reproducidos, inferencias y trabajo pendiente;
- alinear los documentos V2 anteriores con el comportamiento observado;
- dejar una ruta SAFE antes de cualquier cambio de código;
- enumerar todo lo que todavía debe revisarse para comprender el sistema productivo completo.

Este archivo no reemplaza:

- el contrato persistente de 01_CONTRATO_LAYOUT_V2.md;
- el kernel definido en 02_KERNEL_GEOMETRICO_V2.md;
- la frontera de salida de 03_ADAPTADOR_SALIDA_V2.md;
- los documentos históricos de las fases 04 a 17.

Sí reemplaza a 08_AUDITORIA_ESTADO_ACTUAL_V2.md como resumen operativo de estado. El documento 08 debe conservarse como auditoría histórica porque incluye afirmaciones y matrices previas a las exploraciones 1 a 4.

## 2. Alcance y límites de esta actualización

### Revisado

- los 17 documentos existentes en DOCS/OFFSET/V2;
- la documentación SAFE base de DOCS/OFFSET;
- registro de Flask y configuración de V2;
- rutas HTTP V2;
- contrato Layout V2 y validación semántica;
- store, comandos, autosave y conflicto de revisión;
- canvas, selección, drag, visibilidad y geometría;
- assets, works, slots y Repeat;
- operaciones de objeto y clipboard;
- alineación, distribución, gaps y matriz;
- reglas, guías, snap y medición;
- output-capabilities y sus límites;
- inventario estático de pruebas Python, Node y Playwright;
- cuatro recorridos interactivos reales.

### No realizado durante esta actualización

- no se modificó código de producción;
- no se ejecutó pytest;
- no se ejecutaron los tests Node;
- no se ejecutó la suite Playwright existente;
- no se generó preview productivo V2;
- no se generó PDF final V2;
- no se validó CTP productivo;
- no se modificó un PDF fuente;
- no se hizo commit ni push.

Las conclusiones sobre ejecución proceden exclusivamente de las cuatro exploraciones manuales. Las conclusiones sobre cobertura automatizada significan que la prueba existe y fue inspeccionada, no que se haya ejecutado nuevamente.

## 3. Jerarquía de evidencia

Este documento utiliza las siguientes etiquetas:

- Confirmado en ejecución: observado y reproducido en la aplicación real.
- Confirmado por persistencia: comprobado en layout_v2.json.
- Confirmado por código: existe un flujo ejecutable identificable.
- Cubierto por prueba existente: existe una aserción automatizada relevante.
- Inferencia: explicación probable respaldada por evidencia parcial.
- Pendiente: requiere inspección o validación adicional.

La existencia de código o de una prueba no demuestra por sí sola que el comportamiento funcione correctamente en el navegador actual.

## 4. Resumen ejecutivo

Editor V2 ya es una aplicación funcional e independiente de V1. Puede crear jobs, subir PDFs, crear works y slots, aplicar Repeat, editar posiciones, usar operaciones de objeto, guardar con revisión optimista y ofrecer herramientas avanzadas de composición y precisión.

Las cuatro exploraciones confirman que la mayor parte de la edición manual funciona y persiste. También descubrieron defectos y brechas que obligan a introducir una fase de estabilización antes de continuar con 8F Resize.

Hallazgos principales:

1. El servidor protege el contrato, pero la UI puede crear temporalmente un layout inválido al eliminar un slot que es origen de duplicados.
2. El nudge mueve el slot, pero produce TypeError: Illegal invocation en el navegador.
3. El diagnóstico output-capabilities funciona, pero puede quedar visualmente asociado a una revisión anterior y no realiza preflight geométrico.
4. La matriz es funcional, pero después de aplicarla cambia la selección y recalcula sus fuentes, haciendo riesgoso un segundo clic.
5. El conflicto 409 protege la versión remota, aunque la recuperación y los mensajes necesitan una UX más clara.
6. La detección visual de fuera de pliego, fuera de imprimible y overlap funciona.
7. El job real explorado no es compatible con la salida temporal por CropBox y clipping interno.
8. La vista responsive conserva el editor, pero pierde comodidad operativa en anchos aproximados de 820 a 1050 px.

Conclusión SAFE: antes de resize, transformaciones internas, dúplex o PDF nativo, hay que convertir estos hallazgos en pruebas de regresión y corregir primero la estabilidad del comportamiento existente.

## 5. Arquitectura actual confirmada

### 5.1 Entrada y aislamiento

Flujo:

    app.py
      -> init_editor_offset_v2(app)
      -> editor_offset_v2/blueprint.py
      -> feature flags y rutas V2

Feature flags:

- EDITOR_OFFSET_V2_ENABLED habilita la superficie V2.
- EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED controla únicamente herramientas de desarrollo.
- EDITOR_OFFSET_V2_JOBS_ROOT define la raíz privada de jobs.
- EDITOR_OFFSET_V2_MAX_UPLOAD_BYTES limita uploads; el default V2 es 50 MiB.

V2 no guarda sus jobs en static/constructor_offset_jobs. Su almacenamiento por defecto es:

    instance/editor_offset_v2_jobs/<job_id>/
      layout_v2.json
      assets/
      derived/
      previews/
      outputs/
      reports/

### 5.2 Rutas activas

| Método y ruta | Responsabilidad |
| --- | --- |
| GET /editor_offset_visual_v2 | Abre el shell sin job. |
| GET /editor_offset_visual_v2/<job_id> | Abre un job e inyecta su contexto. |
| POST /api/editor-offset-v2/jobs | Crea un job y su Layout V2 inicial. |
| GET /api/editor-offset-v2/jobs/<job_id> | Lee el layout persistido y validado. |
| PUT /api/editor-offset-v2/jobs/<job_id>/layout | Guarda con base_revision y control de conflicto. |
| POST /api/editor-offset-v2/jobs/<job_id>/assets | Incorpora un PDF físico. |
| GET /api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/thumbnails/<page> | Sirve miniaturas seguras. |
| POST /api/editor-offset-v2/jobs/<job_id>/imposition/repeat | Calcula Repeat sin persistirlo. |
| GET /api/editor-offset-v2/jobs/<job_id>/output-capabilities | Diagnostica compatibilidad con la frontera temporal de salida. |

No existen todavía endpoints V2 de preview productivo, PDF final, Nesting, Hybrid, CTP productivo o preflight profundo.

### 5.3 Backend

Dominio:

- editor_offset_v2/domain/layout_v2.py
- editor_offset_v2/domain/validation.py
- editor_offset_v2/domain/geometry.py
- editor_offset_v2/domain/repeat_contract.py
- editor_offset_v2/domain/output_contract.py
- editor_offset_v2/schemas/layout-v2.schema.json

Aplicación:

- editor_offset_v2/application/job_service.py
- editor_offset_v2/application/asset_service.py
- editor_offset_v2/application/repeat_service.py
- editor_offset_v2/application/output_service.py

Infraestructura:

- editor_offset_v2/infrastructure/job_repository.py
- editor_offset_v2/infrastructure/asset_repository.py
- editor_offset_v2/infrastructure/pdf_inspector.py
- editor_offset_v2/infrastructure/thumbnail_renderer.py
- editor_offset_v2/infrastructure/repeat_engine_adapter.py
- editor_offset_v2/infrastructure/editor_output_adapter.py

Dependencia compartida relevante:

- engines/step_repeat_pro_engine.py

Frontera legacy todavía desconectada de V2:

- montaje_offset_inteligente.py
- services/editor_offset_output_service.py
- strategies/

### 5.4 Frontend

Superficies principales:

- templates/editor_offset_visual_v2.html
- static/css/editor_offset_visual_v2.css
- static/js/editor_offset_visual_v2.js
- static/js/editor_offset_v2/

Responsabilidades:

| Módulo | Responsabilidad actual |
| --- | --- |
| bootstrap.js | Composición de la aplicación y listeners de alto nivel. |
| dom_refs.js | Contrato de IDs y elementos DOM. |
| store.js | Layout, revisión, selección, viewport, historial y estados temporales. |
| commands.js | Mutaciones reversibles de Layout V2. |
| command_registry.js | Acciones centrales y disponibilidad. |
| shortcut_manager.js | Teclado, scopes y atajos. |
| autosave.js | Debounce y serialización de guardados. |
| geometry_kernel.js | Geometría frontend pura y paritaria. |
| geometry_view.js | Conversión de dominio a SVG y área imprimible. |
| canvas_renderer.js | Render del pliego, slots, artwork y estados. |
| interactions.js | Pointer Events, selección, drag, Alt+drag, zoom, pan y herramientas. |
| edit_policy.js | Aplicación atómica de locks. |
| assets_panel.js | Upload, works, slots y sustitución de fuente. |
| repeat_panel.js | Cálculo y aplicación de Repeat. |
| output_panel.js | Consulta y presentación de output-capabilities. |
| object_operations.js | Clipboard, filtros y preparación de duplicados. |
| objects_panel.js | UI de operaciones y locks. |
| alignment_operations.js | Planes puros de alineación, distribución, gap y matriz. |
| arrangement_panel.js | UI de composición y borradores. |
| advanced_selection.js | Marquee, ciclo, filtros e issues geométricos. |
| object_tree.js | Árbol cara/work/slot y visibilidad temporal. |
| precision_tools.js | Reglas, guías, medición y métricas. |
| snap_engine.js | Candidatos y resolución de snap. |
| precision_panel.js | UI de precisión. |
| nudge_controller.js | Sesión y batching de movimiento por teclado. |
| position_inspector.js | Edición exacta de X/Y y delta. |

El template carga estos módulos como scripts clásicos diferidos y publica la aplicación bajo window.EditorOffsetV2. No hay Vite, TypeScript ni framework frontend.

## 6. Contratos que deben preservarse

### 6.1 Layout V2

Layout V2 es un corte limpio y exige layout_schema_version = 2.

Invariantes principales:

- milímetros;
- origen en esquina inferior izquierda;
- X hacia la derecha;
- Y hacia arriba;
- posición = centro trim;
- trim persistido antes de rotación;
- bleed uniforme separado;
- footprint derivado y no persistido;
- rotaciones 0, 90, 180 o 270;
- IDs únicos;
- referencias explícitas entre jobs, assets, páginas, cajas, works, slots y perfiles;
- estado temporal fuera del layout;
- campos legacy prohibidos;
- referencias rotas bloqueantes.

### 6.2 Procedencia y locks

- generated_by describe cómo se creó un slot.
- locks describe qué puede editarse actualmente.
- geometry, content, production y delete son superficies separadas.
- user, engine, ctp y system son fuentes válidas.
- una selección múltiple con un elemento bloqueado debe rechazarse de forma atómica.

### 6.3 Persistencia y concurrencia

- el cliente guarda con base_revision;
- el servidor compara contra la revisión persistida;
- el servidor incrementa la revisión;
- un conflicto devuelve 409;
- no hay merge automático;
- la escritura usa reemplazo atómico;
- el lock actual es por proceso Flask y no resuelve despliegues con varios workers.

### 6.4 Geometría

- el kernel Python es la referencia del dominio;
- geometry_kernel.js replica el alcance requerido en frontend;
- la tolerancia geométrica 1e-9 mm es numérica, no productiva;
- la tolerancia PDF/trim de output es 0.01 mm y tiene otra finalidad;
- contacto de bordes no equivale a overlap;
- las operaciones visuales no deben calcular una geometría paralela.

### 6.5 Output

output-capabilities:

- analiza el layout persistido;
- no modifica revisión;
- no resuelve el PDF final;
- no es preview;
- no es preflight profundo;
- no garantiza que el trabajo esté listo para imprenta.

## 7. Estado exacto al cierre de las exploraciones

Job principal:

- ID: ev2_14d0c6f8f60e601aed51f833.
- Revisión final: 43.
- Works: 1.
- Assets: 1.
- Slots: 8.
- Cara habilitada: front.
- Locks activos: ninguno.
- Pliego: 700 x 500 mm.
- Márgenes imprimibles: 0 mm.

La revisión 42 colocó temporalmente un slot fuera del pliego. Undo produjo la revisión 43. Comparado con la revisión 41, el contenido productivo final fue semánticamente idéntico, excluyendo revision y updated_at.

Permanece deliberadamente el solapamiento entre el slot original y su duplicado. Esto sirve como caso de caracterización, pero impide considerar el montaje listo para producción.

La aplicación quedó:

- guardada;
- recargada;
- sin cambios locales;
- sin errores de aplicación en consola después de la recarga final;
- con Flask respondiendo HTTP 200;
- con output incompatible por CropBox y clipping interno.

## 8. Exploración 1: flujo base y primer defecto contractual

### Acciones realizadas

- apertura del estado sin job;
- creación de un job V2;
- upload de un PDF real;
- creación de un work de aproximadamente 100 x 50 mm;
- bleed de 3 mm;
- cantidad solicitada de 6;
- creación de slot manual;
- cálculo y aplicación de Repeat;
- duplicado;
- selección, borrado y undo;
- reglas, snap y guía vertical;
- verificación responsive en escritorio, 1050 px y 820 px;
- consulta de output-capabilities.

### Resultado

El flujo produjo 8 slots:

- 1 original;
- 6 Repeat;
- 1 duplicado.

El guardado y la restauración funcionaron.

### Defecto reproducido: eliminar el origen de un duplicado

El duplicado persiste:

    generated_by.type = duplicate
    generated_by.source_slot_id = ID del origen

DeleteSlotsCommand elimina los IDs seleccionados sin comprobar si otro slot depende de ellos. El validador backend sí exige que source_slot_id exista.

Al eliminar el origen:

1. la UI lo retiró del layout local;
2. el autosave envió el documento;
3. el servidor respondió 400 INVALID_LAYOUT;
4. el issue fue BROKEN_REFERENCE;
5. la revisión persistida quedó protegida;
6. undo restauró el origen.

Clasificación:

- integridad del servidor: correcta;
- prevención en frontend: ausente;
- coherencia visual después del rechazo: insuficiente;
- riesgo: alto.

Decisión recomendada pendiente:

- bloquear por defecto la eliminación de un slot con dependientes;
- ofrecer en una fase posterior una acción explícita para convertir dependientes en manuales o eliminar en cascada;
- no elegir una cascada silenciosa.

### Responsive

La aplicación no se rompió, pero:

- a 1050 px las tres columnas quedan muy estrechas;
- aparecen scrolls independientes;
- parte del contenido del inspector pierde claridad;
- a 820 px el panel de assets deja de estar disponible en la misma composición;
- el inspector domina el espacio;
- se ocultan datos y acciones secundarias del encabezado;
- los controles quedan densos y pequeños.

Esto es un riesgo de usabilidad observado, no una auditoría WCAG completa.

## 9. Exploración 2: teclado, locks, drag y visibilidad

### Acciones realizadas

- nudge con flechas;
- undo y redo;
- lock de geometría;
- lock de eliminación;
- drag y snap a una guía;
- Alt+drag;
- rotación de la selección completa;
- ocultar y mostrar;
- recarga;
- apertura de otro job compatible con salida.

### Funcionamiento confirmado

- ArrowRight modificó X de 350 a 350.1 mm.
- El lock geométrico bloqueó movimiento.
- El lock delete bloqueó eliminación.
- Los desbloqueos restauraron las capacidades.
- Alt+drag creó copias.
- La rotación múltiple mostró correctamente slots fuera del pliego.
- La visibilidad fue temporal y la recarga mostró nuevamente todos los slots.
- Un job de referencia con 25 slots y TrimBox mostró compatibilidad verde.

### Defecto reproducido: nudge

Cada pulsación produjo:

    TypeError: Illegal invocation

Causa confirmada por código:

- el constructor guarda setTimeout sin enlazarlo;
- armTimeout lo invoca mediante this.setTimer(...);
- el navegador rechaza el receptor utilizado.

El movimiento inmediato ocurre, pero el batching por timeout no puede considerarse sano.

La prueba existente valida desplazamiento e historial, pero no comprueba que pageerror permanezca vacío. Por eso el fallo puede pasar aun cuando la geometría esperada coincida.

Clasificación:

- movimiento inmediato: funciona;
- batching documentado: requiere corrección y regresión;
- consola: defectuosa;
- riesgo: alto por historial/autosave.

## 10. Exploración 3: clipboard, composición, matriz, medición y conflictos

### Clipboard

Confirmado:

- copiar y pegar crea IDs nuevos;
- el primer paste desplaza +5 mm en X y -5 mm en Y;
- undo restaura el conteo de slots;
- cut elimina y undo restaura el mismo ID.

Desalineación observada:

- después de undo, el estado visible del clipboard continuó indicando 1 pegado.

El contador pertenece al estado temporal y no es undo-aware.

### Alineación y distribución

Funcionaron:

- selección de tres slots;
- slot clave temporal;
- alineación de centros al slot clave;
- centrado del grupo en el pliego;
- distribución horizontal;
- gap horizontal y vertical exacto;
- undo y autosave.

### Matriz

Una matriz 2 x 2 desde un origen:

- creó 3 slots nuevos;
- pasó de 8 a 11 slots;
- dejó 2 slots fuera del pliego;
- dejó 1 solapamiento;
- pudo deshacerse.

Riesgo de interacción:

- después de aplicar, la selección pasa a las copias;
- el resumen se recalcula sobre la nueva selección;
- la misma matriz cambia de 1 fuente y 3 nuevos a 3 fuentes y 9 nuevos;
- un segundo clic accidental puede multiplicar el layout.

El límite de 500 copias evita crecimiento ilimitado, pero no evita el error operativo.

### Medición

Funcionó sin modificar revisión:

- Delta X: 127.865 mm.
- Delta Y: -127.865 mm.
- Distancia: 180.828 mm.

Desalineación menor:

- Limpiar retiró la medición local;
- el mensaje global inferior permaneció hasta otra acción.

### Conflicto entre pestañas

Confirmado:

- el servidor devolvió 409 REVISION_CONFLICT;
- no se sobrescribió la versión remota;
- la UI conservó el layout local rechazado;
- se mostró Recargar versión remota;
- beforeunload protegió cambios locales;
- la recarga recuperó el estado persistido.

Problemas de UX:

- mensaje técnico en inglés;
- texto truncado;
- no se explica qué se conservará o perderá;
- recuperación limitada a recarga completa.

## 11. Exploración 4: geometría y alcance real de output-capabilities

### Baseline

Estado:

- 8 slots visibles;
- 1 par solapado;
- 0 fuera del pliego;
- 0 fuera del área imprimible;
- márgenes imprimibles en cero.

Los filtros encontraron:

- Fuera del pliego: 0.
- Fuera imprimible: 0.
- Overlaps: 2 participantes.
- Cualquier problema geométrico: los mismos 2 participantes.

Métricas del solapamiento:

- gap X: -95.076 mm;
- gap Y: -45.038 mm;
- Delta de centros X/Y: 5 mm / 5 mm;
- distancia de centros: 7.071 mm;
- overlap X: 95.076 mm;
- overlap Y: 45.038 mm;
- área de intersección de bounds: 4282.033 mm2.

### Caso fuera de pliego

Se movió un slot de X 53.038 mm a X -20 mm.

Confirmado:

- canvas marcó el slot;
- árbol de objetos lo marcó;
- inspector lo marcó;
- filtro Fuera del pliego devolvió exactamente 1;
- autosave creó la revisión 42;
- undo lo restauró en revisión 43.

### Output-capabilities

El baseline devolvió:

- compatible = false;
- revisión analizada = 41;
- 16 errores;
- 2 errores por cada uno de los 8 slots.

Errores:

- UNSUPPORTED_PDF_BOX por utilizar CropBox;
- UNSUPPORTED_CONTENT_CLIP por clipping interno no representable.

La UI los agrupó en dos filas con 8 slots afectados cada una.

Al mover el slot fuera del pliego:

- el panel llegó a conservar visualmente el diagnóstico de revisión 41 mientras el job ya estaba en revisión 42;
- una consulta manual de revisión 42 devolvió los mismos 16 errores;
- no apareció un issue geométrico por fuera de pliego;
- después de undo y consulta nueva, el diagnóstico informó revisión 43.

Interpretación correcta:

- output-capabilities cumple su alcance documentado;
- no es un preflight geométrico final;
- no reemplaza validación de colisiones, bounds, archivos, color, DPI, caras o CTP;
- la UI debería invalidar o marcar como obsoleto el resultado después de cualquier cambio persistente.

## 12. Estado funcional actualizado

| Capacidad | Estado después de las exploraciones |
| --- | --- |
| Contrato Layout V2 | Implementado y defendido por backend. |
| Jobs y persistencia | Operativos en ejecución. |
| Revisión optimista | Operativa; conflicto 409 comprobado. |
| Upload PDF | Operativo con PDF real. |
| Miniaturas | Operativas en canvas. |
| Works y slots front | Operativos. |
| Repeat calculate/apply | Operativo. |
| Add/replace Repeat | Add comprobado en ejecución; replace requiere recorrido específico. |
| Partial/fill Repeat | Respaldado por código/tests; pendiente de recorrido UI dirigido. |
| Store e historial | Operativos; existen bordes defectuosos en nudge y estados temporales. |
| Selección y drag | Operativos. |
| Locks | Operativos y atómicos en escenarios explorados. |
| Rotación cardinal | Operativa. |
| Clipboard/cut/paste | Operativos; contador temporal queda desactualizado tras undo. |
| Alt+drag | Operativo. |
| Alineación/distribución/gap | Operativos. |
| Matriz | Operativa con riesgo de segundo clic. |
| Marquee/ciclo/árbol | Operativos en recorridos explorados. |
| Visibilidad temporal | Operativa y no persistente. |
| Reglas/guías/snap | Operativos. |
| Medición/métricas | Operativas; feedback global puede quedar obsoleto. |
| Filtros geométricos | Operativos para el alcance cardinal actual. |
| Output-capabilities | Operativo como diagnóstico estrecho; no es preflight. |
| OutputAdapter | Implementado y probado de forma aislada; no conectado a PDF V2. |
| Preview productivo V2 | No implementado. |
| PDF final V2 | No implementado. |
| CTP productivo V2 | No implementado; configuración activa bloqueada. |
| Navegación front/back | No implementada en la UI. |
| Slot manual back | No implementado en la UI. |
| Transformación exacta del artwork | No implementada en canvas/salida. |
| Resize | No implementado. |
| Nesting/Hybrid V2 | No implementados. |
| Preflight PDF profundo | No implementado. |

## 13. Hallazgos priorizados

### Prioridad alta

#### A. Integridad referencial al eliminar

La UI debe impedir que DeleteSlotsCommand deje dependientes con source_slot_id roto.

Archivos relacionados:

- static/js/editor_offset_v2/commands.js
- static/js/editor_offset_v2/command_registry.js
- static/js/editor_offset_v2/edit_policy.js
- editor_offset_v2/domain/validation.py
- tests/editor_offset_v2/js/object_operations_v2.test.cjs
- tests/playwright/test_editor_offset_v2.py

#### B. Nudge produce error de navegador

El timer del controlador debe mantener un receptor válido y sus pruebas deben ejecutarse en un contexto equivalente al navegador.

Archivos relacionados:

- static/js/editor_offset_v2/nudge_controller.js
- static/js/editor_offset_v2/shortcut_manager.js
- static/js/editor_offset_v2/command_registry.js
- tests/editor_offset_v2/js/positioning_commands_v2.test.cjs
- tests/playwright/test_editor_offset_v2.py

#### C. Falta un preflight productivo unificado

La geometría visual y output-capabilities son diagnósticos separados. Ninguno constituye por sí solo un gate final de producción.

Áreas mínimas del futuro preflight:

- contrato;
- assets físicos;
- página y cajas;
- color, fuentes, transparencias, overprint y DPI;
- trim/bleed;
- fuera de pliego y área imprimible;
- overlaps;
- marcas;
- caras y dúplex;
- CTP;
- capacidad real del renderer;
- coherencia preview/PDF.

### Prioridad media

#### D. Diagnóstico de output obsoleto

Después de una mutación debe:

- borrarse;
- marcarse como pendiente;
- o mostrar claramente que pertenece a otra revisión.

#### E. Matriz sensible a la selección posterior

Debe evitarse que el mismo formulario cambie silenciosamente de fuentes después de aplicar. Opciones a decidir:

- congelar las fuentes hasta cambiar parámetros o selección deliberadamente;
- pedir confirmación antes de una cantidad elevada;
- deshabilitar temporalmente el botón después de aplicar;
- mostrar diferencia entre fuentes originales y selección resultante.

#### F. Conflicto de revisión

Necesita mensajes localizados y una explicación de la elección de recuperación.

#### G. Responsive

Necesita una fase de diseño operativo que preserve assets, canvas e inspector sin ocultar capacidades esenciales.

### Prioridad baja

- contador de pegados no sincronizado con undo;
- feedback global de medición no limpiado inmediatamente;
- favicon 404 observado al inicio;
- traducciones parciales y mensajes técnicos.

## 14. Alineación de la documentación existente

| Documento | Estado actual |
| --- | --- |
| 01_CONTRATO_LAYOUT_V2.md | Fuente contractual vigente. |
| 02_KERNEL_GEOMETRICO_V2.md | Fórmulas vigentes; algunos apartados de no implementado son históricos frente a 8E. |
| 03_ADAPTADOR_SALIDA_V2.md | Vigente como frontera temporal y desconectada. |
| 04_SHELL_Y_JOBS_V2.md | Histórico de Fase 4. |
| 05_CANVAS_STORE_V2.md | Histórico de Fase 5. |
| 06_ASSETS_Y_SLOTS_V2.md | Histórico de Fase 6. |
| 07_REPEAT_V2.md | Histórico de Fase 7. |
| 08_AUDITORIA_ESTADO_ACTUAL_V2.md | Auditoría histórica acumulativa; contiene matrices internamente desactualizadas. |
| 09_PLAN_HERRAMIENTAS_MANUALES_V2.md | Roadmap útil, pero no debe iniciar 8F antes de estabilizar hallazgos 1 a 4. |
| 10_ESTABILIZACION_SEMANTICA_V2.md | Decisiones vigentes; límites históricos superados por fases posteriores. |
| 11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md | Vigente y todavía abierto. |
| 12_CORRECCION_COMPATIBILIDAD_DE_MEDIDA_Y_ETIQUETAS_V2.md | Vigente. |
| 13_POSICIONAMIENTO_Y_COMANDOS_V2.md | Diseño vigente, pero el nudge real contradice la afirmación de funcionamiento limpio. |
| 14_OPERACIONES_DE_OBJETO_Y_CLIPBOARD_V2.md | Función vigente; falta documentar la dependencia source_slot_id al eliminar. |
| 15_ALINEACION_DISTRIBUCION_Y_MATRIZ_V2.md | Función vigente; falta registrar riesgo de selección posterior y segundo clic. |
| 16_SELECCION_AVANZADA_Y_ARBOL_V2.md | Vigente para alcance actual. |
| 17_REGLAS_GUIAS_SNAP_Y_MEDICION_V2.md | Vigente; falta limpiar feedback global observado. |
| 18_ESTADO_ACTUAL_POST_EXPLORACIONES_1_A_4_V2.md | Resumen operativo vigente desde este corte. |

## 15. Inventario actual de pruebas

Conteo por inspección estática:

- 161 funciones test Python bajo tests/editor_offset_v2;
- 100 casos test Node bajo tests/editor_offset_v2/js;
- 9 recorridos Playwright en tests/playwright/test_editor_offset_v2.py.

La parametrización hace que el número real de casos Python ejecutados pueda ser mayor.

Los nueve recorridos Playwright existentes cubren:

1. Repeat visible, apply, undo/redo, guardado y recarga.
2. Locks contra drag, delete y sustitución.
3. Semántica visual, área imprimible, output y artwork aproximado.
4. Muchos slots, etiquetas, issues agrupados, zoom, drag y visibilidad.
5. Posicionamiento exacto, atajos, batching, persistencia y locks.
6. Operaciones de objeto, clipboard, Alt+drag y persistencia.
7. Alineación, distribución, gaps, matriz y persistencia.
8. Selección avanzada, árbol y visibilidad.
9. Reglas, guías, snap, medición y recarga.

### Brecha metodológica confirmada

Una prueba funcional puede pasar aunque la página produzca errores JavaScript. Los tests críticos deben capturar pageerror y errores de consola de aplicación.

### Regresiones que faltan antes de corregir código

1. Nudge no produce pageerror.
2. Una ráfaga de nudge mantiene un solo comando en navegador real.
3. Eliminar origen con dependientes se bloquea o sigue la política decidida.
4. Un 400 de autosave no deja una falsa apariencia de persistencia.
5. Output-capabilities se invalida al cambiar la revisión.
6. Fuera de pliego y overlap participan en el futuro preflight, no solo en filtros.
7. Matriz no cambia silenciosamente el alcance de un segundo submit.
8. Undo de paste actualiza el estado visual esperado.
9. Limpiar medición limpia todos los mensajes relacionados.
10. Conflicto 409 presenta recuperación comprensible.
11. Responsive 820/1050 mantiene accesibles las tareas principales.
12. Consola limpia en cada recorrido crítico.

## 16. Todo lo que falta revisar para comprender el sistema completo

Esta sección es una lista obligatoria antes de futuros cambios importantes.

### 16.1 Contrato y compatibilidad histórica

Revisar:

- schema completo;
- validador semántico completo;
- fixtures mínimo y completo;
- todos los layouts V2 persistidos que deban conservarse;
- política de campos opcionales aditivos;
- semántica y ciclo de vida de generated_by.source_slot_id;
- tamaño máximo práctico de layout y payload.

Decidir:

- qué referencias son productivas y cuáles solo históricas;
- qué debe ocurrir al eliminar una fuente de procedencia;
- cuándo un cambio exige Layout V3.

### 16.2 Persistencia y concurrencia

Revisar:

- JobService;
- JobRepository;
- compare-and-swap;
- temporales y os.replace;
- recuperación después de fallo;
- uploads concurrentes;
- dos pestañas;
- múltiples procesos Flask;
- backups, limpieza y retención de jobs.

Pendiente:

- elegir file lock, SQLite o almacenamiento transaccional para varios workers;
- definir recuperación sin perder trabajo local.

### 16.3 Assets y PDF

Revisar:

- AssetService y AssetRepository completos;
- staging y rollback;
- hash y metadata;
- cajas heredadas y explícitas;
- rotación intrínseca;
- miniatura versus caja seleccionada;
- archivos dañados, cifrados, enormes o multipágina;
- symlinks y traversal;
- lifecycle de assets derivados.

Pendiente:

- preflight profundo;
- recorte visual exacto por caja;
- PreparedAssetService;
- linaje de correcciones;
- política de retención.

### 16.4 Repeat y motor compartido

Revisar:

- RepeatService;
- RepeatEngineAdapter;
- contrato RepeatResultV2;
- add y replace;
- partial y fill;
- back;
- colisiones con slots existentes;
- dependencia exacta de step_repeat_pro_engine.py;
- estabilidad de sus campos legacy de entrada/salida.

Pendiente:

- recorrer UI de replace, partial, fill y back;
- validar resultados con escenarios reales de imprenta;
- definir si V2 necesitará motor nativo o conservará el adaptador.

### 16.5 Frontend y contrato DOM

Revisar completamente:

- template;
- CSS;
- orden de carga de scripts;
- dom_refs.js;
- bootstrap.js;
- IDs, data attributes y clases dinámicas;
- estados disabled, hidden, aria-live y foco;
- fallos de inicialización parcial;
- disposición responsive.

Regla:

- no renombrar IDs ni clases funcionales sin buscar todos sus consumidores y pruebas.

### 16.6 Store, comandos e historial

Revisar:

- separación persistente/temporal;
- cada comando execute/undo/redo;
- selectionBefore/selectionAfter;
- hooks before-command;
- no-ops;
- atomicidad de locks;
- changeVersion y savedChangeVersion;
- interacción entre comandos y estado temporal;
- dependencia entre slots duplicados y su origen.

Pendiente:

- política formal de referencias de procedencia;
- coherencia de clipboard y medición con undo;
- límites de memoria del historial.

### 16.7 Guardado y conflictos

Revisar:

- debounce;
- guardado durante pointer session;
- cambios durante request;
- error normal versus conflicto;
- reintento;
- beforeunload;
- recarga remota;
- traducción de errores backend.

Pendiente:

- indicador de qué revisión está viendo cada panel;
- recuperación guiada del conflicto;
- preservación opcional de cambios locales.

### 16.8 Interacciones del canvas

Revisar mediante navegador:

- click y multiselección;
- marquee y modificadores;
- ciclo de superpuestos;
- drag;
- Alt+drag;
- pan;
- zoom;
- pérdida de foco;
- pointercancel;
- Escape;
- teclado;
- touch/pointer distintos;
- slots ocultos;
- gran cantidad de slots.

Pendiente:

- pruebas de precisión con varios niveles de zoom/pan;
- rendimiento de render y hit testing;
- navegadores adicionales si V2 se despliega fuera del entorno local.

### 16.9 Geometría

Revisar:

- paridad Python/JavaScript;
- trim versus footprint;
- bleed;
- cardinales;
- contención;
- SAT versus AABB;
- gaps y distancias;
- tolerancias;
- márgenes imprimibles inválidos o extremos;
- posiciones negativas;
- contacto de bordes.

Pendiente:

- definir el gate geométrico productivo;
- separar warning visual, error de guardado y error de exportación;
- decidir escalabilidad del análisis cuadrático de overlaps.

### 16.10 Herramientas manuales

Revisar una por una:

- inspector absoluto/delta;
- nudge y batching;
- rotación;
- duplicate/copy/cut/paste/delete;
- locks;
- alineación;
- distribución;
- gaps;
- matriz;
- visibilidad;
- reglas;
- guías;
- snap;
- medición.

Para cada herramienta verificar:

- disponibilidad;
- teclado y botón por la misma acción;
- locks;
- undo/redo;
- autosave;
- persistencia;
- no-op;
- errores de consola;
- selección resultante;
- feedback;
- responsive.

### 16.11 Salida y preprensa

Revisar antes de conectar producción:

- validate_output_capabilities;
- EditorOutputAdapter;
- serialización temporal;
- resolución física de assets;
- página y caja;
- CropBox, TrimBox, BleedBox y MediaBox;
- actual_size y clipping;
- escalas, offsets, espejos y rotación interna;
- crop marks;
- perfiles de marcas;
- front/back;
- CTP;
- vector_hybrid;
- renderer legacy y strategies;
- preview versus PDF final.

Pendiente crítico:

- definir y construir preflight final;
- decidir motor nativo V2;
- generar fixtures PDF de comparación;
- validar medidas y contenido renderizado, no solo estructura JSON;
- establecer tolerancias productivas explícitas.

### 16.12 Dúplex y CTP

Revisar:

- fuentes independientes front/back;
- navegación de cara;
- selección y edición visible por cara;
- flips de borde largo/corto;
- mesa de luz;
- offsets de plancha;
- pinza;
- barras;
- marcas de registro;
- texto técnico;
- orden de páginas y combinación.

No implementar mediante copia automática del frente sin un contrato de orientación aprobado.

### 16.13 Resize y transformaciones internas

Antes de 8F/8G decidir:

- ancla de resize;
- proporción;
- comportamiento bajo rotación cardinal;
- resize individual versus múltiple;
- locks aplicables;
- relación con actual_size;
- mismatch de fuente;
- handles y accesibilidad;
- snap de handles;
- diferencia entre cambiar trim y escalar artwork;
- exportabilidad inmediata.

Resize y content_transform deben ser fases separadas.

### 16.14 UX, accesibilidad y rendimiento

Revisar:

- flujo principal del operador;
- descubrimiento de herramientas;
- densidad de paneles;
- jerarquía de advertencias;
- mensajes en español;
- foco y teclado;
- contraste;
- targets táctiles;
- lector de pantalla;
- responsive;
- scrolls anidados;
- 100, 500 y más slots;
- costo del render completo del SVG;
- costo de overlaps y métricas.

Las exploraciones realizadas no sustituyen una auditoría WCAG formal.

### 16.15 Integración con V1 y superficies compartidas

Aunque V2 está aislado, revisar antes de tocar:

- app.py;
- registro de blueprints;
- engines/step_repeat_pro_engine.py;
- montaje_offset_inteligente.py;
- services/editor_offset_output_service.py;
- strategies/;
- configuración global de Flask;
- límites globales de upload;
- dependencias Python compartidas.

No introducir vocabulario V1 en Layout V2.

### 16.16 Despliegue y operación

Pendiente revisar:

- modo debug versus producción;
- servidor y cantidad de workers;
- permisos de instance/;
- backups;
- límites de disco;
- limpieza de temporales;
- logging estructurado;
- errores sin stack trace;
- trazabilidad de jobs, assets, revisiones y outputs;
- seguridad de archivos;
- timeouts para PDFs grandes.

## 17. Plan SAFE actualizado

### Fase A: congelar los hallazgos actuales

Objetivo:

- convertir exploraciones 1 a 4 en una matriz de cobertura;
- decidir comportamiento esperado de eliminación con dependientes;
- conservar fixtures y jobs de prueba aislados;
- añadir captura global de errores JavaScript a Playwright.

No cambiar todavía comportamiento.

### Fase B: pruebas de caracterización y regresión

Agregar pruebas focalizadas para:

- nudge sin pageerror;
- delete con source_slot_id dependiente;
- 400 de autosave;
- invalidación de output-capabilities;
- matriz y segundo submit;
- conflicto 409 visible;
- estados de clipboard/medición;
- responsive crítico.

Ejecutar primero solo estas pruebas. La suite completa requiere autorización expresa.

### Fase C: estabilización mínima

Orden recomendado:

1. corregir timer del nudge;
2. implementar política dependency-aware para delete;
3. invalidar diagnóstico de output al cambiar la revisión;
4. proteger matriz contra repetición accidental;
5. mejorar mensajes de conflicto y errores;
6. sincronizar feedback temporal.

Un problema por cambio. Sin refactor masivo.

### Fase D: preflight productivo

Diseñar primero el contrato del preflight. Debe reunir:

- validez del layout;
- compatibilidad de output;
- archivos;
- PDF;
- geometría;
- marcas;
- caras;
- CTP.

No reutilizar output-capabilities como si ya fuera ese preflight.

### Fase E: usabilidad y responsive

Después de estabilizar:

- priorizar tareas principales;
- reducir scrolls anidados;
- mantener assets, canvas e inspector accesibles;
- mejorar mensajes, estados y progresión;
- comprobar teclado y accesibilidad;
- validar 820, 1050, 1440 px y tamaños adicionales.

### Fase F: retomar roadmap 8F en adelante

Solo después de A-E:

- 8F Resize productivo;
- 8G Transformaciones internas;
- 8H Frente/dorso;
- 8I Productividad;
- 8J Modos y recetas;
- 8K Preflight PDF;
- 8L Planificación;
- Fase 9 motor PDF nativo;
- Fase 10 presupuesto.

## 18. Gates obligatorios antes de modificar código

Antes de cualquier cambio:

1. definir problema y comportamiento esperado;
2. identificar contrato y estado persistente afectados;
3. localizar acción, comando, store, UI, backend y tests relacionados;
4. decidir si el cambio es temporal, documental o productivo;
5. crear o ajustar caracterización;
6. confirmar que no se rompe V1;
7. limitar el cambio a una fase;
8. definir rollback;
9. obtener aprobación si afecta contrato, PDF, CTP, motor o persistencia.

Después de un cambio autorizado:

- validar sintaxis Python y JavaScript;
- ejecutar tests focalizados;
- comprobar consola del navegador;
- comprobar undo/redo/autosave/recarga;
- comprobar revisión y conflicto;
- comprobar layout persistido;
- ejecutar Playwright focalizado;
- ejecutar suite completa solo con autorización;
- ejecutar git diff --check;
- actualizar este documento o el documento de fase si cambió el comportamiento.

## 19. Superficies que no deben romperse

- Layout V2 y layout_v2.json;
- sistema de coordenadas;
- centro trim;
- bleed separado;
- assets inmutables;
- referencias asset/página/caja/work/slot;
- IDs y generated_by;
- locks y atomicidad;
- revisión optimista;
- escritura atómica;
- selección, drag y Alt+drag;
- undo/redo;
- autosave;
- Repeat;
- filtros geométricos;
- output-capabilities;
- aislamiento de V1;
- seguridad de rutas;
- archivos PDF fuente.

## 20. Qué no debe tocarse todavía

- no activar resize;
- no implementar rotación libre;
- no mezclar trim del slot con escala del artwork;
- no conectar V2 directamente a montaje_offset_inteligente.py;
- no declarar output-capabilities como preflight;
- no habilitar CTP parcial;
- no inventar dorso a partir del frente;
- no cambiar schema sin decisión de versión;
- no borrar documentos históricos;
- no refactorizar todos los módulos frontend al corregir un defecto;
- no cambiar Step & Repeat PRO para resolver problemas exclusivamente visuales;
- no crear automatización IA que escriba el layout sin confirmación.

## 21. Preguntas abiertas que requieren decisión

1. ¿Delete debe bloquear, convertir dependientes en manuales o eliminarlos en cascada?
2. ¿generated_by.source_slot_id es una referencia contractual permanente o trazabilidad histórica tolerante?
3. ¿Cuándo debe invalidarse y recalcularse output-capabilities?
4. ¿Qué condiciones constituyen un montaje listo para producción?
5. ¿Overlap o fuera de pliego deben bloquear guardado, bloquear exportación o solo advertir?
6. ¿Qué cajas PDF debe soportar primero el motor de salida?
7. ¿Se prepararán assets derivados para CropBox, rotación y clipping?
8. ¿Qué fidelidad debe alcanzar el canvas antes de preview/PDF?
9. ¿Cuál es el comportamiento seguro de matriz después de aplicar?
10. ¿Cómo debe recuperarse un conflicto sin perder cambios locales?
11. ¿Cuál es la prioridad real entre estabilización, preflight, responsive y resize?
12. ¿Qué estrategia de concurrencia se usará en producción multiproceso?
13. ¿Qué jobs V2 existentes forman parte de la compatibilidad obligatoria?
14. ¿Cuándo se retira el puente legacy y comienza el motor nativo?

## 22. Evidencia conservada

Artefactos:

- output/playwright/v2-baseline-20260830/
- output/playwright/v2-second-exploration-20260903/
- output/playwright/v2-third-exploration-20260903/
- output/playwright/v2-fourth-exploration-20260904/

Job de caracterización:

- instance/editor_offset_v2_jobs/ev2_14d0c6f8f60e601aed51f833/layout_v2.json

Trace final de la cuarta exploración:

- .playwright-cli/traces/trace-1788494992380.trace

Estas evidencias no son fixtures canónicos todavía. Antes de incorporarlas a tests deben aislarse de timestamps, IDs aleatorios y estado local.

## 23. Próximo paso recomendado

El próximo trabajo no debe ser 8F Resize.

El siguiente paso SAFE es preparar, para aprobación, una fase pequeña de pruebas de regresión que cubra:

1. nudge sin errores;
2. eliminación con dependencias;
3. revisión del diagnóstico output;
4. seguridad de matriz;
5. conflicto 409;
6. consola limpia.

Solo después de que esas pruebas fallen por los motivos esperados debe comenzar la primera corrección de código.
