# Análisis previo — MVP 3 Repeat Dorso en un pliego V2

Estado: propuesta técnico-funcional, 2026-10-04. Contrastada con el código en la rama `codex/editor-offset-v2-montajes-revistas`, commit `a1743094c97dbc627983b294572bcede032f1e69`. **No es una implementación ni una aceptación productiva.** Se apoya en [44 — mapa](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md), [46 — cobertura](46_AUDITORIA_COBERTURA_Y_HALLAZGOS_V2.md), [47 — objetivo](47_OBJETIVO_FUNCIONAL_EDITOR_OFFSET_V2.md) y [48 — Frente/Dorso MVP 1 + 2](48_ANALISIS_FRENTE_DORSO_MVP_V2.md). Las secciones históricas de 48 anteriores a su actualización inicial no describen el estado vigente.

## 1. Alcance y estado ejecutable

Objetivo: proponer y aplicar Repeat en **Dorso de un único pliego**, independientemente del Frente, conservando edición posterior, guardado, undo/redo, CAS, recarga y salida existentes. Repeat Frente debe conservar su comportamiento.

- `RepeatService.propose` acepta `face=front|back`, rechaza una cara no habilitada y comprueba `base_revision` ([servicio](../../../editor_offset_v2/application/repeat_service.py)). El [adaptador](../../../editor_offset_v2/infrastructure/repeat_engine_adapter.py) ya genera slots con `face=back`, copia su fuente efectiva y filtra obstáculos por cara. El [packer V2](../../../editor_offset_v2/domain/repeat_packer.py) recibe rectángulos y piezas; no necesita distinguir caras internamente.
- El bloqueo operativo principal está en [`repeat_panel.js`](../../../static/js/editor_offset_v2/repeat_panel.js): deshabilita la opción back, inicializa el selector en front y rechaza calcular otra cara. El [template](../../../templates/editor_offset_visual_v2.html) mantiene la opción Dorso deshabilitada y una nota anterior a la navegación ya entregada. La lista de works se inicializa mirando `front_source`.
- MVP 1 + 2 ya aportó tabs Frente/Dorso y `store.activeFace` temporal, selección filtrada, creación manual con `slot.source` explícito, Preview por cara y PDF `both`. No aportó Repeat Dorso. La cobertura actual de Repeat Back se limita principalmente a casos del adaptador; faltan servicio con Back habilitado, aplicación cruzada y aceptación de navegador.

## 2. Cara de Repeat: decisión preferida

**Usar `store.activeFace` como cara de trabajo de Repeat (opción A).** No mantener un segundo selector de cara salvo necesidad funcional demostrada. Mostrar `Repeat — Frente` o `Repeat — Dorso` según la cara activa. La petición HTTP conservará el campo explícito `face`, tomado de `activeFace`, para que servicio y propuesta tengan una identidad de cara verificable.

El selector propio actual (opción B) puede discrepar del canvas y de los tabs. Cambiar a la cara Dorso requiere que `faces.enabled` la incluya; no se habilita automáticamente al entrar a Repeat.

## 3. Fuentes: brecha y propuesta

Hoy el adaptador resuelve `work.front_source` o `work.back_source` según `face`. Si falta `back_source`, devuelve `SOURCE_NOT_FOUND`; si asset, página, estado ready o caja PDF fallan, devuelve un issue de fuente. No consulta un `slot.source` existente para decidir qué repetir. La creación manual de MVP 1 + 2 sí puede usar otra página del mismo PDF o un PDF distinto como `slot.source`. [`UpdateWorkCommand`](../../../static/js/editor_offset_v2/commands.js) trata `back_source` como cambio estructural y lo bloquea si ese work ya tiene slots.

**Propuesta para implementar:** permitir source overrides **temporales y explícitos por work en la petición Repeat**. Para cada work seleccionado, usar su `back_source` cuando corresponda o exigir una elección explícita de asset, página y caja si falta o si el operador elige otra fuente. No inventar pareja con Frente ni cambiar el work persistido. El servicio debe validar la identidad/referencias de cada override; el adaptador debe usarlo para construir cada `slot.source`; el hash/ID de operación debe incluir la elección para distinguir propuestas con fuentes distintas. La estructura JSON exacta queda por definir y probar durante implementación, sin añadir campos a Layout V2.

El schema actual permite una referencia `derived` dentro de `source`; Repeat puede copiar una referencia existente, pero la UI de selección manual ofrece asset/página/caja y el adaptador no comprueba físicamente un derivado al proponer. No anunciar selección explícita de derivados sin validar su identidad y recorrido físico; Preview/PDF y preflight conservan sus controles de salida. Una fuente inválida debe producir un error comprensible y no modificar el layout.

## 4. Coordenadas, obstáculos e IDs

**Repeat calcula en coordenadas de edición.** El adaptador obtiene el rectángulo imprimible del único `sheet`, sus márgenes y los slots retenidos **de la cara solicitada**; pasa sus huellas al packer junto con el gap solicitado. Slots Frente no son obstáculos al proponer Dorso, ni viceversa. Los IDs de slot siguen siendo globales: la normalización comprueba colisiones incluso contra la otra cara. Tamaño de pliego y márgenes son comunes; gaps y preferencias de work usan los controles/valores actuales. Las zonas preferidas son preferencias del packer, no un nuevo mapa persistido de zonas prohibidas por cara.

El packing no consulta `faces.duplex.flip`. El flip de Dorso se aplica después en [`pdf_compositor.py`](../../../editor_offset_v2/infrastructure/pdf_compositor.py) al generar Preview/PDF. No usar coordenadas reflejadas para obstáculos o colocaciones.

## 5. Propuesta temporal e invalidación

La propuesta vive en `EditorStore.repeatPanel`, no en Layout ni en historial. El panel guarda `proposalContext.face`, job, revisión, versión local, works, ajustes y modo. El canvas ya muestra una propuesta solo cuando su cara coincide con `activeFace`; la acción de tab de MVP 1 + 2 llama `invalidateProposal()`.

La protección aún debe cerrarse para MVP 3: `repeat_panel.js` no escucha hoy el evento `active_face`, `store.getRepeatPreview()` no exige cara activa coincidente y `apply()` compara contra el selector Repeat actual. Una llamada directa a `setActiveFace` o una respuesta HTTP tardía no debe instalar ni dejar aplicable una propuesta de otra cara. Invalidar al cambiar `activeFace` y al cambiar fuente, works, modo, gaps, distribución, layout o revisión; invalidar también las peticiones pendientes mediante la secuencia existente. Tras recibir respuesta y **justo antes de aplicar**, comprobar `proposalContext.face === store.activeFace`. El contexto de la propuesta debe incluir la selección de fuentes efectivas para detectar cambios silenciosos.

## 6. Aplicación, replace y undo/redo

[`ApplyRepeatCommand`](../../../static/js/editor_offset_v2/commands.js) ya acepta front/back, valida que cada slot propuesto tenga la cara y work esperados, comprueba referencias, IDs y locks, escribe mediante un comando reversible y actualiza `imposition.last_result` global. El panel guarda antes de proponer; aplicar marca dirty y el autosave/CAS persiste luego el layout completo.

- **`add`:** conserva todos los slots existentes y añade los propuestos en la cara objetivo.
- **`replace_work_face`:** retira únicamente slots cuyos `work_id` estén seleccionados **y** cuya `face` sea la cara objetivo. Un Replace Dorso exitoso no elimina slots Frente; una dependencia `source_slot_id` que quedaría huérfana hace fallar el comando antes de escribir.
- **Advertencia UX:** Replace incluye también slots **manuales Dorso** de esos works, no solo resultados de Repeat anteriores. La revisión debe mostrar cuántos y cuáles se retirarán, además de respetar locks.
- **Undo/redo:** el comando repone los slots retirados y el `imposition` anterior al deshacer, y reaplica al rehacer. Debe verificarse en Dorso y comparar exactamente los slots Frente antes/después. `imposition.last_result` es global aunque las colocaciones pertenezcan a una cara.

## 7. Casos mínimos de aceptación A–L

| Caso | Resultado esperado |
|---|---|
| A — Job solo Frente | Repeat Frente mantiene selección, cantidades, add/replace, historial y PDF de una página; Dorso no se habilita solo. |
| B — Ambas caras, operador en Frente | Repeat propone y aplica solo slots Frente. |
| C — Operador en Dorso | Con fuente válida, propone y aplica exclusivamente slots `face=back`. |
| D — Dorso add | Conserva slots Frente y Dorso existentes; respeta obstáculos Dorso. |
| E — Dorso replace | Reemplaza solo works seleccionados en Dorso, informa también los manuales afectados y deja Frente idéntico. |
| F — Cambio de cara | Propuesta lista o pendiente se invalida; nunca se aplica silenciosamente en otra cara. |
| G — Undo Dorso | Restaura exactamente los slots retirados y metadatos previos, sin cambio en Frente. |
| H — Redo Dorso | Reaplica el resultado correcto y conserva Frente. |
| I — Autosave/recarga | CAS guarda ambas caras; recarga recupera los slots Dorso y fuentes elegidas. |
| J — Salida | Preview Dorso y PDF Ambas muestran físicamente el Repeat aplicado, con orden y flip existentes. |
| K — Fuente ausente/inválida | Error claro para falta de `back_source`/override, asset, página o caja; propuesta fallida y layout intacto. |
| L — Página 2 | Dorso repite la página 2 elegida del mismo PDF; `slot.source` y artefacto físico coinciden. |

## 8. UX mínima

El panel muestra la cara activa, la fuente/página/caja efectiva por work y las cantidades solicitadas, colocadas, faltantes y sobrantes ya existentes. Para Dorso sin `back_source`, exige elección explícita antes de calcular. La propuesta permanece visualmente temporal, se descarta al cambiar de cara y no se guarda ni exporta antes de aplicar. El resultado aplicado sigue siendo editable. Cantidades y fuentes de Frente/Dorso no se emparejan ni sincronizan automáticamente.

## 9. Intervención probable por archivo

| Área | Archivo | Cambio previsto |
|---|---|---|
| Frontend | `static/js/editor_offset_v2/repeat_panel.js` | Cara desde `activeFace`, fuente efectiva por work, contexto y guardas de propuesta, mensajes/cantidades. |
| Frontend | `templates/editor_offset_visual_v2.html`, `static/js/editor_offset_v2/dom_refs.js` | Retirar selector duplicado y nota obsoleta; mostrar cara y elección de fuente de Dorso. |
| Frontend | `static/js/editor_offset_v2/store.js` | Cerrar la invariante temporal de propuesta/cara incluso fuera de la acción del tab. |
| Frontend condicional | `static/js/editor_offset_v2/bootstrap.js` | Solo si la conexión de nuevos controles no cabe en el panel existente. |
| Backend | `editor_offset_v2/application/repeat_service.py` | Validar overrides temporales por work e incluirlos en identidad de operación. Ya acepta `face=back`; cambiar únicamente esta brecha. |
| Backend | `editor_offset_v2/infrastructure/repeat_engine_adapter.py` | Resolver fuente override/default, validarla y copiarla a slots. Ya filtra obstáculos y genera slots Dorso. |
| Sin cambio previsto salvo prueba fallida | `editor_offset_v2/domain/repeat_packer.py`, `static/js/editor_offset_v2/commands.js`, `static/js/editor_offset_v2/canvas_renderer.js`, Preview/PDF | Reutilizar packing, ApplyRepeatCommand, filtro visual y salida actuales; no hacer refactor preventivo. |

El contrato de la **petición** Repeat puede ampliarse para overrides, pero `slot.face`, `slot.source`, `work.back_source` opcional y estado temporal ya permiten representar el resultado. **No se justifica nuevo campo Layout, cambio de `layout_schema_version` ni migración.**

## 10. Pruebas necesarias, sin escribirlas en esta fase

- **Python:** ampliar `test_repeat_service_v2.py` y `test_repeat_engine_adapter_v2.py` para Back habilitado, fuente `back_source` o override de página/PDF/caja, fuente ausente/inválida, hash de operación distinto, obstáculos exclusivamente Dorso, `add`, `replace_work_face`, locks e IDs globales. Comprobar propuesta read-only y Front intacto; el packer no necesita test nuevo si su contrato no cambia.
- **Node:** ampliar `repeat_commands_v2.test.cjs` y `repeat_proposal_freshness_v2.test.cjs` para cara activa, contexto/fuente, invalidación por cambio de cara incluso con respuesta tardía, guarda previa a Apply, Add/Replace Dorso, slots Frente exactamente iguales, bloqueo de manuales, undo/redo y estado sin dirty al proponer.
- **Playwright:** ampliar `test_editor_offset_v2_native_repeat.py` y la integración de salida V2: crear job, colocar Frente, habilitar Dorso, entrar a Dorso, elegir fuente/página, calcular, revisar y aplicar, volver a Frente y verificar integridad, regresar a Dorso, guardar/recargar, comprobar resultado, Preview Dorso y PDF Ambas con contenido físico distinguible. Usar esperas por estado/respuesta, sin sleeps arbitrarios. Actualizar la caracterización que hoy exige que la opción Dorso de Repeat esté deshabilitada.

## 11. Orden y límites

1. Proteger Repeat Frente y Replace Dorso cruzado con pruebas focalizadas.
2. Definir el contrato temporal del source override por work, sin cambiar Layout.
3. Validar y resolver override en servicio/adaptador; incluirlo en el hash de operación.
4. Ligar UI Repeat a `store.activeFace`, mostrar cara y fuente efectiva.
5. Invalidar propuesta y respuesta tardía al cambiar cara/fuente; verificar cara inmediatamente antes de aplicar.
6. Aplicar Add/Replace Dorso con revisión explícita de slots retirados y locks.
7. Verificar undo/redo.
8. Verificar autosave, CAS y recarga.
9. Verificar Preview Dorso y PDF Ambas sobre artefactos físicos.
10. Ejecutar pruebas focalizadas y suites V2 pertinentes completas, registrando límites.

Riesgo estimado: **medio-alto**, concentrado en fuente efectiva, propuesta obsoleta y alcance visible de Replace. Fuera de esta entrega: Repeat sincronizado Frente/Dorso, parejas automáticas, cantidades vinculadas, múltiples pliegos, revistas, firmas, creep, CTP y cambios de schema. No definir aquí registro industrial ni rebajar por accidente el bloqueo global de preflight.
