# Análisis previo — Frente/Dorso para un solo pliego V2

Estado: especificación técnico-funcional previa a implementación, 2026-10-04. **No describe una función integral ya disponible ni modifica Layout V2.** Los hechos de implementación indicados abajo se contrastaron por lectura estática del código de esta rama; esta revisión no ejecutó Flask, tests ni una aceptación física nueva. [44 — mapa](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md) localiza la arquitectura, [46 — auditoría](46_AUDITORIA_COBERTURA_Y_HALLAZGOS_V2.md) conserva cobertura y riesgos generales, y [47 — objetivo funcional](47_OBJETIVO_FUNCIONAL_EDITOR_OFFSET_V2.md) sitúa la evolución del producto. Este documento acota el trabajo de un solo pliego con dos caras.

## 1. Propósito y alcance

Preparar una primera experiencia usable para crear, navegar, editar, guardar, validar y generar Frente y Dorso **de un único pliego**. La primera entrega comprende MVP 1 (navegación y edición) y MVP 2 (validación y salida clara). MVP 3, Repeat Dorso, es una entrega posterior.

Quedan fuera múltiples pliegos, revistas, firmas, creep, sincronización automática de pares, registro industrial certificado, CTP y migración de schema. No se debe usar un PDF fuente multipágina como sustituto conceptual de varios pliegos. Se preservan trabajos solo Frente, originales PDF, geometría, revisiones, locks e historial.

## 2. Soporte actual comprobado por código

| Componente | Hecho actual | Evidencia ejecutable |
|---|---|---|
| Contrato | Hay un objeto sheet compartido; faces.enabled admite front/back; faces.duplex guarda enabled y flip none/long_edge/short_edge; cada slot requiere face. | editor_offset_v2/schemas/layout-v2.schema.json; domain/layout_v2.py; domain/validation.py |
| Fuentes | Cada work tiene front_source y back_source opcional; slot.source es la referencia efectiva de la colocación. No se exige igualdad con la fuente predeterminada del work. | schemas/layout-v2.schema.json; static/js/editor_offset_v2/source_semantics.js |
| Exportación | export.faces contiene front, back, combine_in_single_pdf y order. El PDF nativo de face=both usa order para componer las caras habilitadas. El booleano combine_in_single_pdf no es consultado por PdfFinalService en ese recorrido; no atribuirle un efecto que hoy no tiene. | application/pdf_final_service.py |
| Persistencia | JobService valida el layout y JobRepository guarda el documento completo por revisión CAS; pueden coexistir slots de las dos caras si ambas están habilitadas. El job nuevo habilita solo front. | application/job_service.py; domain/validation.py; infrastructure/job_repository.py |
| Frontend | EditorStore retiene el layout completo, un activeFace temporal, selección e historial global. Canvas, lista, árbol, selección avanzada y snap ya consultan activeFace. Los comandos genéricos y SaveCoordinator guardan el layout completo, aunque falta un recorrido de UI para operar sobre Dorso. | static/js/editor_offset_v2/{store,canvas_renderer,object_tree,advanced_selection,snap_engine,commands,autosave}.js |
| Preview | PreviewService acepta front o back individualmente, exige habilitación y slots, compone esa cara y publica PNG. No acepta both. | application/preview_service.py; static/js/editor_offset_v2/output_panel.js |
| PDF final | PdfFinalService acepta front, back o both; both compone dos páginas en el orden de export.faces.order cuando las dos caras están habilitadas. | application/pdf_final_service.py; infrastructure/pdf_compositor.py |
| Preflight | Recorre layout y fuentes de todos los slots, separa solapes por cara y añade faces a varios hallazgos por slot. Las decisiones de bloqueo se calculan por operación sobre el reporte completo, no como permiso independiente por cara. | application/preflight_service.py; application/native_output_capabilities.py |
| Repeat | RepeatService acepta back habilitado; el adaptador usa work.back_source, obstáculos de esa cara e IDs globales. | application/repeat_service.py; infrastructure/repeat_engine_adapter.py |

**Alcance de la evidencia:** que Store y comandos trabajen con objetos del Dorso se infiere de su código genérico por ID/layout. No hay una prueba de navegador que certifique la cadena completa de edición, undo/redo, autosave, Preview y PDF para ambas caras. Los tests actuales de PDF both comprueban páginas y tamaño, no contenido ni registro físico de las dos páginas.

## 3. Limitaciones actuales del recorrido de operador

- Store inicializa activeFace desde faces.enabled[0], pero no hay acción ni setter de navegación en la UI. El rótulo de cara no es un selector. El árbol presenta la otra cara con conteo y estado no editable; el canvas y la lista solo muestran la activa.
- createSlotFromWork fija face=front y work.front_source. La preparación habitual puede copiar **la misma** fuente al back_source, pero no ofrece un emparejamiento explícito entre páginas o PDFs distintos para un work ya preparado.
- El clipboard rechaza paste en Dorso. UpdateWorkCommand bloquea cambios estructurales, incluido back_source, si el work ya tiene slots colocados en cualquiera de las caras; no diseñar la UX suponiendo que el operador podrá asignarlo tarde sin una intervención propia.
- La opción back de Repeat está deshabilitada en HTML y el controlador vuelve a front y rechaza back. Esta restricción no procede del packer.
- El selector de cara del panel de salida no cambia activeFace. Con un layout de ambas caras configurado por otra vía se puede pedir Preview Dorso mientras el canvas continúa en Frente.
- No hay comando productivo de emparejamiento o sincronización automática. El valor de procedencia duplex_copy en el schema/fixture no equivale a edición vinculada.
- La selección del Store no impone por sí misma activeFace: introducir tabs sin limpiar selección permitiría que una selección invisible afecte comandos o inspectores.
- El agrupador visual de hallazgos de preflight no muestra la cara como parte del resumen. Parte de los errores de una sola cara puede bloquear operaciones del layout completo.
- No se encontró un Playwright V2 que cree y edite Frente y Dorso en un mismo job hasta el PDF físico. El Playwright actual confirma incluso que Repeat Back sigue deshabilitado.

## 4. Semántica de flip que existe hoy

El sistema de edición guarda milímetros con origen inferior izquierdo. En pdf_compositor.py, para la página back y solo si faces.duplex.enabled es verdadero: **long_edge transforma X en ancho del pliego menos X**; **short_edge transforma Y en alto menos Y**; none no hace esa reflexión. El compositor aplica la misma transformación a contenido, clipping y marcas de corte. El canvas conserva las coordenadas de edición y no aplica ese flip de salida. content_transform.mirror_x y mirror_y reflejan el contenido del slot antes de esta transformación de página; la rotación cardinal del slot es otra operación independiente.

Estos nombres y fórmulas describen el código, **no una convención universal de pinza, retiro, giro de pliego o máquina**. La UI propuesta debe exponer none, long_edge y short_edge como opciones explícitas con su efecto geométrico. No seleccionar una como correcta para toda imprenta. El valor inicial para trabajos solo Frente permanece none; el perfil de uso dúplex y su aceptación física requieren decisión del propietario.

## 5. Casos de aceptación A–L

| Caso | Comportamiento actual | Límite actual | Resultado esperado de MVP 1 + MVP 2 |
|---|---|---|---|
| A — Solo Frente | Flujo inicial y habitual. | Riesgo de regresión al añadir controles. | Mismas funciones y PDF de una página; Dorso no se habilita implícitamente. |
| B — Colocación independiente | Layout admite slots front/back. | UI no navega ni crea slot back. | Activar Dorso, navegar y colocar/editar piezas distintas en cada cara. |
| C — PDF de dos páginas | Asset admite páginas individuales. | La UI no asigna página 2 como Dorso de un work/slot mediante un flujo claro. | Elegir página 1 para Frente y página 2 para Dorso explícitamente. |
| D — Dos PDFs | Se pueden subir ambos y el contrato admite fuentes distintas. | La preparación ofrece solo copiar la misma fuente a back_source. | Elegir el asset/página efectivo de cada cara sin emparejamiento automático. |
| E — Cantidades distintas | No se exige pareja por slot. | UI no muestra conteo editable por cara. | Mostrar conteos separados; no inventar correspondencia física. |
| F — Selección al navegar | No existe navegación. | Selección de otra cara podría quedar invisible. | Cancelar/finalizar gesto o borrador y limpiar selección, hover y slot clave al cambiar. |
| G — Undo/redo cruzado | Historial global por comandos. | No hay recorrido Dorso en navegador ni protección de selección invisible tras undo. | Deshacer/rehacer cambios de ambas caras sin alterar la otra; selección resultante siempre visible o vacía. |
| H — Autosave/recarga | Se guarda el layout completo con CAS. | Sin prueba integral UI de ambas caras. | Persistir y recargar caras, fuentes, slots, flip, orden y revisión; conflicto visible. |
| I — Preview | Backend genera PNG por cara. | No genera both; selector de salida no navega canvas. | Inspeccionar Frente y Dorso por separado, rotulados por cara, revisión y orientación. |
| J — PDF both | Backend genera dos páginas según order. | Test actual no certifica contenido/flip en ambas. | PDF de dos páginas con orden, contenido y flip comprobados físicamente. |
| K — Error solo Dorso | Hallazgos pueden referenciar back. | UI no lo rotula claramente; bloqueo puede afectar layout completo. | Mostrar cara/slot afectado, explicar el bloqueo y no declarar salida apta con hallazgos relevantes. |
| L — Repeat Back | Servicio/packer soportan back_source y face=back. | UI deshabilita/rechaza Dorso. | Requisito de MVP 3 posterior: propuesta y aplicación por cara sin tocar Frente. |

## 6. UX propuesta, no implementada

Tabs visibles **Frente | Dorso** sobre el canvas, con estado activo textual, foco/teclado, cantidad de slots y señal de hallazgos por cara; el color no será el único indicador. Un job solo Frente conserva su recorrido y ofrece la acción explícita **Habilitar dorso**. Deshabilitar una cara con contenido no puede borrar ni dejar inválidas sus referencias silenciosamente.

Al cambiar de cara se deberán cerrar o cancelar de modo previsible drag, nudge, marquee, borradores numéricos y propuestas temporales aplicables; limpiar selección y slot clave; actualizar canvas, árbol, panel de objetos e inspectores. **Zoom y pan permanecerán globales** inicialmente y fuera del layout. Si luego el uso requiere vistas separadas, se evaluará estado temporal acotado, sin duplicar el Store.

El canvas Dorso dirá que muestra **coordenadas de edición sin flip de salida**. El panel de salida identificará la cara solicitada y el artefacto mostrado; Preview seguirá siendo individual por cara y PDF **Ambas** será una elección explícita. Cambiar cara u opciones invalidará una Preview/reporte que ya no describa la vista u operación anunciada.

## 7. Alcance recomendado y criterio de primera entrega

### MVP 1 — navegación y edición

Usar campos existentes para habilitar/configurar Dorso con un comando reversible; añadir tabs y cambio temporal de activeFace; crear slots manuales en la cara activa con fuente explícita; mantener edición independiente. Revisar filtros, selección, drag, align, snap, locks, inspectores, clipboard, undo/redo, autosave, CAS y recarga. La configuración de caras debe coordinar faces.enabled, faces.duplex y export.faces sin perder un job Frente preexistente.

**Criterio de aceptación:** un operador crea, modifica y guarda piezas diferentes en cada cara, recarga el job y continúa editando ambas. Ningún gesto o comando afecta una selección invisible de la otra cara. Un conflicto de revisión no se presenta como guardado correcto.

### MVP 2 — validación y salida claras

Mostrar hallazgos de preflight por cara cuando la referencia lo permita; conservar visibles los hallazgos globales. Generar Preview Frente y Preview Dorso inequívocas. Generar PDF Ambas con orden, contenido y flip comprobados sobre archivo físico; mostrar revisión/opciones y bloqueos. No afirmar paridad universal canvas/Preview/PDF a partir de un solo fixture.

**Criterio de aceptación:** el operador puede identificar qué cara falló, comprobar cada Preview y descargar un PDF cuyas dos páginas correspondan a las piezas y orientación elegidas. Una salida bloqueada no aparece como apta para producción.

### MVP 3 — entrega posterior, fuera de la primera implementación

Repeat Dorso separado de Frente, tras resolver la fuente back_source y validar propuesta, obstáculos, aplicación reversible, persistencia y PDF. No incluir Repeat sincronizado de ambas caras.

## 8. Decisiones de alcance para MVP 1 + MVP 2 y cuestiones abiertas

1. Reutilizar el schema actual; no migrar ni cambiar layout_schema_version.
2. activeFace es estado temporal de frontend y **no se persiste**. El contrato V2 prohíbe el campo legacy active_face.
3. Frente y Dorso se editan independientemente; no se sincronizan slots ni se crean pares automáticamente.
4. Exponer none, long_edge y short_edge como opciones explícitas, sin prometer compatibilidad con toda máquina.
5. Mantener Preview por cara y PDF Ambas como solicitud explícita.
6. Identificar claramente los problemas del Dorso en preflight y en la UI.
7. No declarar aptitud productiva mientras existan bloqueos relevantes del layout completo. La política exacta sobre salida de Frente aislado ante un problema solo de Dorso sigue **pendiente**; debe definirse, implementarse y probarse de manera visible, sin rebajar bloqueos por accidente.
8. Repeat Dorso queda fuera de la primera entrega.

También queda pendiente acordar la convención de imprenta, referencia de registro y criterio físico de aceptación del flip. La opción de salida no constituye esa aceptación por sí misma.

## 9. Estrategia técnica elegida para estudiar la implementación

**Preferida:** usar slot.face persistido y activeFace temporal; completar navegación, acción de configuración, creación y filtros. Evita una segunda representación de layout y permite que Store, CAS y servicios sigan trabajando con un único documento por job.

**No adoptar ahora:** un estado frontend completo duplicado por cara, porque duplicaría historial/selección/borradores y exigiría reconciliación; ni un contenedor nuevo de caras en el schema, porque el caso de un pliego ya cabe en el contrato y ese cambio impondría migración transversal. Un futuro modelo de varios pliegos no se diseña aquí; esta elección conserva explícita la pertenencia de cada slot a su cara sin introducir estado persistido que después haya que quitar.

## 10. Archivos de intervención probable

La lista identifica responsabilidad y trabajo probable, **no una autorización para modificarlos**. «Verificar» significa cambiar solo si una prueba focalizada descubre un defecto.

| Grupo y archivo | Responsabilidad actual | Cambio probable para esta función |
|---|---|---|
| Template — templates/editor_offset_visual_v2.html | Estructura de canvas, paneles y controles de salida/Repeat. | Tabs, habilitación explícita y rótulos; obligatorio MVP 1. |
| CSS — static/css/editor_offset_visual_v2.css | Disposición, estados y responsive. | Estado activo, conteos, alertas y foco accesible; obligatorio MVP 1. |
| DOM — static/js/editor_offset_v2/dom_refs.js | Contrato de IDs y controles. | Registrar nuevos tabs/controles; obligatorio MVP 1. |
| Inicio — static/js/editor_offset_v2/bootstrap.js | Compone Store, controladores y acciones. | Conectar navegación y controles; obligatorio MVP 1. |
| Estado — static/js/editor_offset_v2/store.js | Layout, activeFace, selección, historial y viewport. | Cambiar cara temporalmente, cancelar estado y filtrar selección; obligatorio MVP 1, riesgo alto. |
| Acciones — static/js/editor_offset_v2/command_registry.js | Frontera de acciones del operador. | Registrar habilitación, flip y navegación; obligatorio MVP 1. |
| Comandos — static/js/editor_offset_v2/commands.js | Mutaciones reversibles y creación manual. | Configurar campos existentes; crear slot de cara/fuente elegida; obligatorio MVP 1, riesgo alto. |
| Assets — static/js/editor_offset_v2/assets_panel.js | Selección de PDF/página/work y creación de slot. | Permitir fuente de Dorso y usar cara activa; obligatorio MVP 1. |
| Preparación — static/js/editor_offset_v2/preparation.js | Borradores de páginas y work. | Revisar elección de página/fuente Dorso; cambio condicionado al diseño de UX. |
| Clipboard — static/js/editor_offset_v2/object_operations.js | Copiar, pegar y filtrar objetos. | Pegar solo en cara compatible y quitar el veto absoluto de Dorso; obligatorio MVP 1. |
| Semántica — static/js/editor_offset_v2/source_semantics.js | Fuente predeterminada por cara y override. | Verificar fuente efectiva y avisos; cambiar solo ante fallo. |
| Canvas — static/js/editor_offset_v2/canvas_renderer.js | Dibuja slots de activeFace. | Actualizar rótulo, conteo y arte al navegar; obligatorio MVP 1. |
| Gestos — static/js/editor_offset_v2/interactions.js | Drag, selección, pan y puntero. | Finalizar/cancelar gesto al cambiar de cara; obligatorio MVP 1, riesgo alto. |
| Selección — static/js/editor_offset_v2/advanced_selection.js | Filtros, marquee y visibilidad. | Verificar que no sobreviva una selección oculta; cambio según prueba. |
| Snap — static/js/editor_offset_v2/snap_engine.js | Objetivos de ajuste por cara. | Confirmar que Dorso no toma obstáculos de Frente; cambio según prueba. |
| Alineación — static/js/editor_offset_v2/alignment_operations.js | Operaciones geométricas con activeFace. | Confirmar selección solo de cara activa; cambio según prueba. |
| Árbol — static/js/editor_offset_v2/object_tree.js | Agrupa slots de la cara activa y anuncia la otra como inactiva. | Mostrar/navegar ambas caras y sus conteos; obligatorio MVP 1. |
| Objetos — static/js/editor_offset_v2/objects_panel.js | Acciones y locks de la selección. | Actualizar al cambiar cara y rechazar selección invisible; obligatorio verificar. |
| Posición — static/js/editor_offset_v2/position_inspector.js | Borrador de edición numérica. | Cancelar borrador al navegar; obligatorio verificar. |
| Contenido — static/js/editor_offset_v2/content_transform_inspector.js | Transformación y derived del slot seleccionado. | Cancelar/actualizar selección y fuente al navegar; obligatorio verificar. |
| Arreglo — static/js/editor_offset_v2/arrangement_panel.js | Vista y borradores de alineación. | Cancelar borradores y slot clave al navegar; obligatorio verificar. |
| Salida UI — static/js/editor_offset_v2/output_panel.js | Preflight, Preview y PDF. | Rotular cara, hallazgos, orientación y artefacto; obligatorio MVP 2. |
| Jobs — editor_offset_v2/application/job_service.py | Validación y CAS. | Sin cambio previsto; probar persistencia de dos caras. |
| Preflight — editor_offset_v2/application/preflight_service.py | Reporte de layout y decisiones por operación. | Cambiar solo tras definir/probar política de bloqueos por cara; riesgo alto. |
| Preview — editor_offset_v2/application/preview_service.py | PNG de una cara. | Sin cambio previsto salvo defecto físico demostrado. |
| PDF — editor_offset_v2/application/pdf_final_service.py | PDF de cara única o both. | Sin cambio previsto salvo defecto de orden/contenido demostrado. |
| Compositor — editor_offset_v2/infrastructure/pdf_compositor.py | Coloca, refleja y marca cada cara. | Sin cambio previsto; verificar flip físico y marcas. |
| Rutas — editor_offset_v2/blueprint.py | Endpoints V2 y opciones de salida. | Reutilizar rutas actuales; cambiar solo ante necesidad demostrada. |
| Validación — editor_offset_v2/domain/validation.py | Contrato runtime y cara habilitada. | Sin cambio previsto; posible regla de coherencia solo tras revisar jobs existentes. |
| Schema — editor_offset_v2/schemas/layout-v2.schema.json | Contrato JSON persistente. | Ningún cambio en MVP 1 + MVP 2. |
| Repeat UI — static/js/editor_offset_v2/repeat_panel.js | Propuesta y aplicación solo Frente en UI. | MVP 3; no habilitar Back en primera entrega. |
| Repeat backend — editor_offset_v2/application/repeat_service.py; infrastructure/repeat_engine_adapter.py | Propuesta por cara y packer V2. | MVP 3; probar antes de cambiar. |
| Python — tests/editor_offset_v2/test_layout_v2_contract.py; test_job_service_v2.py; test_preflight_v2.py; test_preview_v2.py; test_pdf_final_v2.py | Contrato, CAS, diagnóstico y artefactos. | Ampliar casos de dos caras, contenido y flip; obligatorio por MVP. |
| Node — tests/editor_offset_v2/js/object_operations_v2.test.cjs; advanced_selection_object_tree_v2.test.cjs; output_diagnosis_v2.test.cjs | Clipboard, filtros/árbol y lógica de salida. | Añadir navegación, selección y avisos por cara; obligatorio por MVP. |
| Playwright — tests/playwright/test_editor_offset_v2.py; test_editor_offset_v2_output_integration.py | Flujo del operador y salida física. | Añadir recorrido Frente/Dorso completo; obligatorio por MVP. |
| Tests Repeat — tests/editor_offset_v2/test_repeat_service_v2.py; test_repeat_engine_adapter_v2.py; js/repeat_commands_v2.test.cjs | Servicio, adaptador y comando de propuesta. | Ampliar para Back solo en MVP 3. |

El riesgo de edición se concentra en Store, comandos y gestos; el de salida, en la interpretación y verificación física por cara. Los módulos backend existentes se reutilizan antes de proponerles cambios.

## 11. Riesgos principales y protección esperada

- **Selección invisible o gesto activo:** cambiar cara sin cancelar puntero, nudge, borrador o selección puede editar la cara que el operador no ve. Exigir limpieza/cancelación y tests de eventos.
- **Fuente de Dorso:** back_source puede estar ausente y UpdateWorkCommand bloquea cambios estructurales tras colocar slots. Diseñar elección temprana o un flujo explícito que preserve slots; no cambiar fuentes silenciosamente.
- **Canvas y salida desincronizados:** el selector de salida y activeFace son estados distintos hoy. Mostrar cara, revisión y orientación; invalidar artefactos obsoletos.
- **Flip y contenido físico:** dos páginas correctas en cantidad/tamaño aún pueden estar cruzadas, vacías o reflejadas en eje equivocado. Inspeccionar píxeles/objetos asimétricos y marcas en cada página.
- **Preflight del Dorso poco visible:** el reporte recorre todo el layout y algunas decisiones bloquean globalmente. Mostrar cara y explicar política; no ocultar hallazgos para hacer pasar Frente.
- **Regresión solo Frente:** conservar defaults, un PDF de una página, edición habitual, guardado y rutas actuales; usar pruebas equivalentes antes/después.
- **Dependencias de producción:** assets, derivados y marcas se resuelven por slot/fuente; un slot Dorso debe recorrer los mismos controles de hash, sangrado, locks y publicación. No suponer paridad por compartir compositor.

## 12. Tests requeridos después de implementar

**Python:** contrato válido con ambas caras y fuentes distintas; rechazo de slot en cara deshabilitada; CAS/recarga sin pérdida de otra cara; hallazgo solo en Dorso con referencia de cara y decisión de bloqueo esperada; Preview individual de cada cara; PDF de dos páginas con orden y contenido distinguibles; none/long_edge/short_edge sobre arte asimétrico y marcas. Inspeccionar archivo físico y ausencia de publicación parcial. El test actual de PDF both cuenta páginas y tamaño, por lo que no basta como aceptación física.

**Node:** transición de activeFace sin dirty ni historial; limpieza de selección, slot clave, gesto y borradores; comando reversible de habilitación/configuración; creación y paste por cara; undo/redo global sobre ambas; filtros de canvas/árbol/align/snap/locks; invalidación de Preview y preflight al cambiar cara u opciones. Repeat Back se probará en MVP 3.

**Playwright de aceptación:** crear job → cargar una fuente multipágina o dos PDFs → colocar Frente → cambiar a Dorso → colocar Dorso → guardar → recargar → verificar ambos contenidos y geometrías → generar Preview por cara → ejecutar preflight e identificar hallazgos por cara → descargar PDF final de dos páginas → inspeccionar páginas, orden, contenido y flip. Añadir prueba de conflicto CAS y una de cambio de cara con selección/gesto. Usar host V2 de QA según su configuración propia; sus flags no describen el arranque productivo habitual. No ejecutar Playwright V1 como sustituto.

## 13. Orden recomendado de implementación futura

1. Proteger con pruebas el recorrido actual solo Frente y fijar su baseline.
2. Implementar configuración reversible de Dorso mediante campos existentes, con política segura para no deshabilitar una cara con contenido.
3. Añadir tabs y navegación temporal de activeFace.
4. Cerrar selección, gestos, borradores y comandos por cara; verificar filtros e inspectores.
5. Completar creación manual y elección de fuente/página para Dorso.
6. Verificar autosave, recarga, CAS, locks y undo/redo cruzado.
7. Definir y presentar preflight por cara y política de bloqueos del layout.
8. Verificar Preview individual y correspondencia con la cara anunciada.
9. Verificar PDF Ambas, orden, contenido, flip y marcas en archivos físicos.
10. Ejecutar suites V2 pertinentes completas y el recorrido Playwright de aceptación; registrar límites de la evidencia.
11. Abordar Repeat Dorso solo en la siguiente entrega.

Las decisiones industriales pendientes deben resolverse antes de afirmar aptitud de producción; no son permiso para inventar un valor por defecto.

## 14. Fuera de alcance y cierre

No implementar múltiples pliegos, revistas, firmas, creep, sincronización automática de slots, imposición editorial, registro industrial certificado, CTP, PDF/X, un schema nuevo ni Repeat Dorso durante MVP 1 + MVP 2. Tampoco reestructurar V2 ni tocar el producto V1 por conveniencia.

La propuesta queda lista para convertirse en trabajo de implementación **después** de fijar la política de flip/registro aplicable y el comportamiento de salida aislada frente a un error del Dorso. Este documento conserva esas cuestiones como pendientes verificables, no como comportamiento ya aprobado.
