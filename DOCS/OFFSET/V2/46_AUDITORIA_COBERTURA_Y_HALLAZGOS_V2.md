# Auditoría de cobertura y hallazgos del Editor Offset Visual V2

Corte de consolidación: 2026-10-04. Documento de auditoría y priorización; no constituye aceptación productiva ni cambia contratos.

## 1. Propósito, alcance y tipos de evidencia

Este documento reúne hallazgos de las auditorías estáticas del mapa, la validación dinámica posterior, la revisión de vigencia de tests y la matriz de cobertura. **No reemplaza [44 — Mapa de conexiones](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md)**: 44 localiza arquitectura, rutas y dependencias; 46 registra cobertura, riesgos, deuda y preguntas para futuras mejoras. Tampoco define el producto final ni autoriza corregir código.

Las afirmaciones se distinguen así:

- **Arquitectura actual, lectura estática:** imports, llamadas, rutas y orden de escrituras contrastados con el código del repositorio en este corte. La lectura no demuestra por sí sola el resultado en producción.
- **Validación dinámica anterior:** resultados efectivamente observados en ejecuciones de las revisiones previas de este mismo trabajo. Se conservan con su contexto y fecha; no se repitieron al crear 46.
- **Cobertura:** qué afirma la suite y qué recorrido no prueba, aunque los tests pasen.
- **Riesgo:** una consecuencia posible sustentada por el código o por una ejecución; no se presenta como incidencia generalizada sin evidencia.
- **Comportamiento no definido:** política funcional o productiva que requiere decisión futura. No se convierte una hipótesis en especificación.

Fuentes principales: [41 — bitácora](41_TRABAJO_DIARIO_Y_BITACORA_V2.md), [44](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md), `editor_offset_v2/`, `templates/editor_offset_visual_v2.html`, `static/js/editor_offset_v2/`, `tests/editor_offset_v2/`, `tests/playwright/test_editor_offset_v2*.py`, `tests/fixtures/editor_offset_v2/`, scripts V2 y `.agents/skills/editor-offset-local-qa/`. Los informes previos guiaron la búsqueda; las conexiones importantes se contrastaron de nuevo con el código y las pruebas.

## 2. Estado general del Editor V2

El núcleo más maduro comprende Layout V2 y su validación, estructura de job, persistencia atómica del layout, revisión optimista CAS, geometría cardinal en milímetros, Repeat propio y multipágina, comandos reversibles, autosave, carga de PDF fuente con hash, preflight físico, Preview y PDF final nativo básico. Existen pruebas Python, Node y navegador para estos caminos; “maduro” significa mejor evidencia relativa, no certificación de imprenta.

Siguen en evolución la materialización de derivados como operación completa de UI a disco, política de huérfanos, paridad visual general entre canvas/Preview/PDF, salida raster estructural, concurrencia entre procesos, corpus de PDFs complejos y umbrales productivos finales. La UI actual es un editor de piezas sobre un pliego: la preparación multipágina y Repeat no implementan por sí mismos múltiples pliegos, firmas o imposición editorial completa.

## 3. Evidencia dinámica comprobada en revisiones anteriores

| Ejecución o corte | Observación | Alcance y límite |
|---|---|---|
| Host exclusivo V2, validación dinámica posterior a la segunda revisión estática | Se levantó mediante la skill local y se comprobó identidad `/health/editor-offset-v2`, shell/rutas V2 y perfil efectivo del proceso observado. El arranque habitual habilitó Preview/PDF y dejó derivados/dev tools apagados; los tests de salida usan otro perfil con derivados habilitados. | Identidad y flags de aquel proceso; un script que reutiliza un Flask ya abierto no cambia retrospectivamente sus flags. No prueba todos los despliegues ni la convivencia. |
| Python V2 | **649 passed** en la corrida dinámica posterior. | Suite V2 de aquel corte; pasar no implica cobertura completa. No reejecutada para crear este documento. |
| Node V2 | **165 passed** en 18 archivos de tests. | Lógica frontend probada fuera del navegador; no sustituye integración HTTP/DOM. No reejecutada aquí. |
| Playwright V2 | **37 passed** en seis archivos V2. | Hosts y jobs temporales de QA; no certifica todos los perfiles ni PDFs externos. No reejecutada aquí. |
| 500 colocaciones, corrida posterior aislada | Aproximadamente **21,86 s**, por debajo del umbral `elapsed < 60` del test. El test compone un pliego de 2000 × 1400 mm con 500 slots que comparten una fuente vectorial; verifica una página, 500 ocurrencias de texto y ausencia de imágenes. | Una medición aislada del caso sintético y de ese entorno; no demuestra latencia estable, consumo de memoria, posiciones de las 500 piezas ni rendimiento de trabajos heterogéneos. |
| 500 colocaciones, 2026-09-27 histórico | **66,797 s**, fallo contra el mismo umbral de 60 s, con PDF de 500 textos generado. | Corte anterior, entorno/carga de ejecución no equiparados con la corrida aislada posterior. No declarar el problema universalmente resuelto ni elevar el umbral para ocultarlo. |

La corrida posterior de 500 piezas y el fallo histórico no son una comparación controlada de rendimiento. Para afirmar una mejora estable harían falta repeticiones equivalentes, entorno medido y métricas de memoria/artefacto. Las cifras de tests son resultados de revisiones anteriores, no de la creación de 46.

## 4. Hallazgos arquitectónicos relevantes

### Hosts y fronteras

`editor_offset_v2/web_app.py:create_app` crea el host exclusivo, registra el blueprint V2, identidad y estáticos acotados. `app.py` mantiene convivencia e importa `routes.py` y otros productos; esa carga trae dependencias transitivas legacy que no son llamadas productivas del flujo V2 exclusivo. `scripts/start_editor_offset_v2.ps1` y la skill `editor-offset-local-qa` administran el arranque local. El perfil de un proceso reutilizado debe comprobarse, no inferirse de variables del script recién invocado. Los módulos `prepared_output_adapter.py`, `legacy_output_probe.py`, `editor_output_adapter.py` y `output_service.py` son ensayos/diagnóstico histórico; Repeat y Preview/PDF habituales usan el packer y compositor propios de V2.

### Tres recorridos visuales y salidas

1. **Miniatura simple:** upload → `AssetService`/`thumbnail_renderer` → PNG persistido bajo `assets/` → panel de assets, sin `box`.
2. **Miniatura por caja:** canvas simple → `GET thumbnail?box=...` → validación de caja/hash/metadatos → preparación y PNG en memoria; no reutiliza la miniatura simple. Tiene ETag y caché HTTP.
3. **Artwork preparado:** slot con derivado, bleed o transformación interna → `GET artwork?spec=...` → `OutputSnapshot`, fuente preparada y compositor sobre geometría temporal → PNG para el canvas. Su rotación final también depende del SVG.

Preview compone un PDF de pliego y lo rasteriza a PNG; PDF final publica el compuesto vectorial salvo modo raster explícito. Comparten partes de la preparación, pero tienen geometrías, escalas, cachés y publicación diferentes. La miniatura simple, la miniatura por caja y artwork no son tres pruebas equivalentes de la salida física. Los cachés de fuentes preparadas/documentos del snapshot duran una operación; las respuestas de Preview/PDF son `no-store`.

### Snapshot, preflight, concurrencia y archivos

`output_snapshot.py` congela layout, revisión y fuentes de la operación, aplica un presupuesto agregado de fuente de 128 MiB y envuelve Preview/PDF con un `BoundedSemaphore(2)` **por proceso**. La lectura estática no demuestra un cupo global entre procesos. Preflight independiente publica su reporte; Preview/PDF crean y consumen su propio preflight fresco del snapshot, en vez de confiar como autorización en un reporte anterior de la UI. El preflight independiente y las generaciones no están probados como operación concurrente conjunta.

Cada job reside bajo la raíz configurable `instance/editor_offset_v2_jobs/<job_id>/`, con `layout_v2.json`, `assets/`, `derived/`, `reports/`, `previews/` y `outputs/`. El layout usa temporal, `fsync`, `os.replace`, lock de hilo/archivo y CAS; las fuentes originales se mantienen inmutables. La publicación de salidas usa locks y reemplazo de artefactos, pero no debe confundirse atomicidad de un archivo con transacción de todos los archivos o de una referencia del layout.

`DerivedAssetService.materialize_page` escribe un PDF derivado y después un JSON manifiesto, cada uno mediante `_atomic_write` bajo `.publish.lock`. El POST no lleva `base_revision` ni guarda el layout. `content_transform_inspector.js` recibe la respuesta, ejecuta `SetSlotDerivedSourceCommand` y deja el guardado al autosave. El manifiesto registra procedencia y revisión leída, pero esa revisión no constituye el CAS del posterior PUT. `artifact_lifecycle.py` tiene pruebas de recuperación/retención cuando se invoca expresamente; no se localizó invocador productivo actual y su recuperación no recorre `derived/`. Por tanto, no atribuirle limpieza automática de derivados.

Flask/Werkzeug participan en rutas, límites HTTP y respuestas; PyMuPDF inspecciona cajas, prepara/compone y rasteriza PDF; Pillow interviene en Preview, espejo y transformaciones raster. Sus límites y fallos afectan directamente al comportamiento V2. El host exclusivo no equivale todavía a distribución física independiente de todos los archivos y paquetes legacy.

## 5. Hallazgo confirmado por ejecución controlada: derivados huérfanos

**Hecho observado en la validación dinámica anterior:** sobre un job temporal se materializó una página derivada y el endpoint respondió **201**. Después se intentó guardar un layout con `base_revision` antiguo: el PUT respondió **409 `REVISION_CONFLICT`**. El layout persistido mantuvo su revisión y no incorporó `source.derived`; el PDF derivado y su manifiesto permanecieron físicamente bajo `derived/`. Se comprobó el estado del layout y de los archivos tras ambas respuestas. No fue un test automatizado permanente de la suite.

**Mecanismo contrastado con código:** `POST derived-page` publica antes del PUT CAS, y `content_transform_inspector.js` agrega la referencia mediante comando/autosave después de recibir 201. Por ello una materialización lograda y un guardado rechazado no son una única transacción.

**Riesgo:** archivos sin referencia, consumo de espacio, ambigüedad para recuperación y posibilidad de mostrar materialización exitosa sin persistencia del cambio de layout. No se comprobó que todos los conflictos produzcan el mismo resultado ni se cuantificó frecuencia en uso real.

**Comportamiento deseado aún no definido:** eliminar, conservar temporalmente o reconciliar esos archivos; plazo y propietario de limpieza; mensaje y recuperación de UI. Tampoco está decidida la política ante fallo entre la escritura del PDF y la del manifiesto. Documentar el hecho no elige una de esas políticas.

## 6. Estado resumido de cobertura por subsistema

Escala: **FUERTE** = assertions representativas en varias capas para el recorrido indicado; **PARCIAL** = cobertura útil con escenarios importantes pendientes; **DÉBIL** = comprobaciones superficiales o solo indirectas; **AUSENTE** = sin test relevante del recorrido; **LEGACY/HISTÓRICA** y **OBSOLETA/SOSPECHOSA** describen evidencia que no debe contarse como validación actual del flujo habitual. Una categoría no es porcentaje ni certificación.

| Subsistema | Categoría | Evidencia actual y límite principal |
|---|---|---|
| Jobs: crear, cargar y estructura | **FUERTE** | `test_job_service_v2.py`, `test_job_repository_v2.py`, `test_routes_v2.py` verifican directorios, layout inicial, lectura y shell. No prueban recuperación integrada tras interrupción. |
| Persistencia del layout y CAS | **FUERTE** para una instancia; **PARCIAL** para varios procesos | Revisión, 409, JSON corrupto y fallo de reemplazo se comprueban en repositorio/servicio/ruta. Falta carrera completa con derivados y generación multiproceso. |
| Autosave y conflictos de UI | **PARCIAL** | Node prueba coordinador/estado y Playwright mensaje de 409; no enlaza materialización, autosave y CAS en un solo caso. |
| Undo/redo | **FUERTE** para comandos habituales | Node y navegador prueban Repeat, preparación, objetos y persistencia; no el ciclo completo del derivado materializado bajo conflicto. |
| Upload de assets y hashes | **PARCIAL** | Subida, revisión, hash, errores, tamaño y fuente alterada tienen pruebas Python; falta corrupción física recorrida hasta ambas salidas sin publicación parcial. |
| Miniatura simple | **DÉBIL** | `test_valid_upload_increments_revision_persists_layout_and_serves_thumbnail` comprueba 200, MIME y firma PNG, no contenido/página/orientación/caché. |
| Miniatura por caja | **PARCIAL** | Dimensiones por giro, 304, caja ausente y hash cambiado; no comparación de píxeles del área seleccionada. |
| Artwork preparado y canvas | **PARCIAL** | Cambio de bytes/cobertura y comparación de ROI SVG–Preview en variantes; faltan derived, cajas/giros más amplios y cachés. |
| Geometría y rotaciones | **FUERTE** | Kernel Python, paridad Node/fixtures y flujos de navegador para cardinales, locks y operaciones. Combinaciones con PDFs complejos siguen limitadas. |
| CropBox, TrimBox, MediaBox y BleedBox | **PARCIAL** | Inspector, rutas y preparación con PDFs sintéticos de cajas presentes/ausentes; no corpus complejo de preprensa. |
| Sangrado, espejo y transformaciones internas | **PARCIAL** | Decisiones y salidas puntuales probadas en Python/Node/navegador; falta matriz visual de bordes/cajas/giro/derived. |
| Repeat y Repeat multipágina | **FUERTE** | Propuesta temporal, add/replace, historial, cantidades, cuatro páginas y PDF físico; bordes exactos del packer y cargas extremas quedan fuera. |
| Derivados: servicio y manifiesto | **PARCIAL** | Endpoint comprueba versionado, transformación y manifiesto; no fallo entre PDF y JSON. |
| Derivados: UI → comando → autosave → CAS | **AUSENTE** como recorrido completo | Tests de endpoint y comando separados; Playwright no pulsa materializar. |
| Huérfanos y recuperación de derivados | **AUSENTE** en suite | Existe observación dinámica controlada de 201→409, sin prueba automatizada ni política productiva definida. |
| Preflight y reportes | **FUERTE** para operación individual; **PARCIAL** en concurrencia | Reporte, revisión, hallazgos, corrupción y bloqueo físico probados; no simultaneidad con generaciones/multiproceso. |
| Preview | **PARCIAL** | Artefacto, revisión, límites y UI de descarga probados; diversidad de PDF y paridad completa pendientes. |
| PDF final vectorial | **PARCIAL** | Archivo físico, páginas, texto/dibujos y ausencia de imagen monolítica en casos sintéticos; no certificación PDF/X/CTP. |
| PDF final raster | **DÉBIL** estructuralmente | Un test solicita raster y compara renderización, pero no inspecciona objetos residuales ni diferencia estructural frente a vector. |
| Paridad canvas / Preview / PDF | **PARCIAL** | SVG–Preview por ROI en tres variantes y Preview–PDF raster en otro caso; no comparación integral de tres artefactos para derived/bleed/cajas desplazadas. |
| Concurrencia, `OUTPUT_BUSY`, locks y publicación | **PARCIAL** | Cuatro hilos demuestran cupo y recuperación; lock de dos procesos se prueba aislado; falta generación multiproceso y preflight concurrente. |
| Límites de páginas, píxeles, fuente y colocaciones | **PARCIAL** | Casos 3/20/249 páginas, 24 MP en un recorrido, >500 slots y límite de fuente reducido a 8 por monkeypatch; no 250/251 ni presupuesto real 128 MiB bajo carga. |
| Lifecycle | **DÉBIL** como protección productiva | `test_artifact_lifecycle_v2.py` verifica el componente, incluso lock entre procesos; no demuestra invocador productivo ni limpieza de derivados. |
| Host exclusivo y flags | **PARCIAL** | Test de imports/host, fixtures Playwright y checker mockeado; ciclo real de scripts y perfil reutilizado no forman una prueba integral. |
| Convivencia mediante `app.py` | **PARCIAL** | Registro y no sustitución de V1; no valida un proceso completo `both` y su carga transitiva. |
| PDFs reales o complejos | **DÉBIL** | Fixtures mayormente sintéticos; faltan OutputIntents, fuentes complejas, transparencias, imagen pesada y metadatos conflictivos. |
| Sondas de salida V1/offline | **LEGACY/HISTÓRICA** para salida habitual V2 | Sus tests caracterizan el puente antiguo, no el compositor nativo. |
| Nombres/metadatos de tests históricos | **OBSOLETA/SOSPECHOSA** donde se indica en §9 | Nombre o etiqueta puede sugerir una semántica distinta de la assertion; revisar antes de contar cobertura. |

La cobertura de errores HTTP/layout inválido es **PARCIAL**: existen 400/404/409/413, rutas inseguras y layout corrupto, pero no inyección de fallos en cada etapa de publicación. La frontera declarada de `OutputIntents` en `prepared_pdf_source.py` rechaza con `UNSUPPORTED_OUTPUT_INTENT`; falta fixture y prueba física para esa ruta.

## 7. Huecos críticos P0 — pruebas futuras, sin implementación aquí

### Derivados

1. **Recorrido de operador:** subir/colocar fuente, transformar en `content_transform_inspector.js`, materializar, recibir PDF/manifiesto, ejecutar `SetSlotDerivedSourceCommand`, autosave CAS, recargar y generar Preview/PDF. Assertions sobre revisión, referencia, hashes, procedencia y original inmutable.
2. **Carrera controlada:** materialización 201 seguida de PUT stale 409, mensaje correcto en UI, layout sin referencia falsa e inventario físico de huérfanos. Sin sleeps arbitrarios: usar barrera/intercepción determinista.
3. **Fallo entre PDF y manifiesto:** inyectar error en la segunda publicación; comprobar respuesta, archivos visibles, temporales y revisión. La assertion normativa sobre limpiar o conservar requiere antes resolver la política abierta.

### PDF final raster

Comparar los modos raster y vector con la misma fuente: estructura real mediante PyMuPDF (imágenes, texto y dibujos), DPI efectivo, dimensiones/cajas, contenido residual y rasterización visual dentro de tolerancia. Un PDF que devuelve 200 y se ve parecido puede tener una estructura equivocada.

### Paridad visual

Comparar la misma región física en **canvas, Preview y PDF** para derived persistido, bleed/espejo, rotaciones, offset interno y cajas desplazadas. Fijar DPI, recorte y tolerancia; incluir un control negativo para asegurar que la comparación detecta desplazamientos. Las comprobaciones actuales son parciales y no deben describirse como paridad universal.

## 8. Huecos P1 y P2

**P1 — importantes:** preflight independiente concurrente con Preview/PDF; dos procesos publicando sobre un job; corrupción de fuente hasta salida; límites 250/251 páginas y presupuesto real de 128 MiB; límites de píxeles en todas las ramas aplicables; contenido y ETag de miniaturas simple/por caja; flags efectivos de host iniciado/reutilizado mediante la skill; PDF complejo con rechazo/aceptación explícitos; ausencia de salida parcial ante errores de publicación. La prueba de 500 piezas debe repetirse de modo comparable y con métricas de memoria, sin alterar el umbral para aparentar éxito.

**P2 — mejoras:** bordes exactos del packer (128 tipos, 2000 colocaciones/obstáculos, 1024 rectángulos libres y esfuerzo máximo), corpus versionado de preprensa, separación de helpers de tests legacy, revisión de nombres/etiquetas históricas, y prueba de lifecycle desde una entrada productiva **si esa entrada se define**. P2 no significa que una decisión funcional abierta pueda tomarse dentro de un test.

## 9. Tests actuales a tratar con cautela

- **Legacy/offline:** `test_output_adapter_v2.py`, `test_legacy_output_probe_v2.py` y `test_prepared_output_probe_v2.py` prueban ensayos de compatibilidad, no la ruta nativa habitual. Algunos tests de preparación/sangrado importan helpers de `test_legacy_output_probe_v2.py`; es un acoplamiento de QA, no una dependencia productiva demostrada.
- **Nombre sospechoso:** `test_output_safety_v2.py::test_raster_renderer_cannot_claim_vector_preservation` configura el diagnóstico `vector_hybrid` y comprueba un resultado de capacidades; no inspecciona la estructura de un PDF raster. Conservar su valor como guardia de diagnóstico, sin contarlo como test de raster.
- **Etiqueta histórica:** `pdf_fixture_manifest.json` conserva `requires_future_stage` para `mirror-bleed-candidate.pdf`, mientras ya existe materialización/espejo explícito. La etiqueta describe un corte anterior o necesita revisión; no demuestra ausencia actual.
- **Assertions débiles:** la miniatura simple se acepta por HTTP 200, MIME y firma PNG; algunas rutas se prueban por status 200 sin inspeccionar el archivo en ese mismo caso. Hay pruebas más profundas en otras capas, pero no deben atribuirse a esas assertions concretas. La prueba de 500 slots verifica cantidad de texto y que no haya imágenes, no las 500 posiciones. El test del presupuesto de fuente sustituye 128 MiB por 8 bytes y solo valida la rama de rechazo.
- **Solapamiento:** `test_output_parity_contract_v2.py` y `test_pdf_fixture_parity_v2.py` revisan nombres/metadatos relacionados del manifiesto. Su duplicación aparente no constituye dos verificaciones físicas independientes. Las pruebas CAS a nivel repositorio, servicio y HTTP sí cubren fronteras diferentes y no deben descartarse como duplicadas sin análisis.

No se propone borrar ni cambiar estas pruebas en este documento. Su clasificación indica cómo interpretar la evidencia al planificar una nueva prueba.

## 10. Fixtures y datos faltantes

El corpus actual incluye layouts mínimo/completo; JSON de geometría, Repeat, marcas y bleed; y PDFs sintéticos `boxes-offset`, `boxes-missing`, `multipage-rotations`, `marks-clipping`, `mirror-bleed-candidate` y `front-back-flip`. Es útil para invariantes controladas. El layout completo no representa una referencia derived persistida ni un estado huérfano tras CAS.

Para futuras pruebas hacen falta casos reproducibles y documentados con: OutputIntents/ICC; fuentes incrustadas y subconjuntos; transparencias y grupos complejos; imágenes pesadas; metadatos conflictivos; cajas Media/Crop/Trim/Bleed desplazadas, ausentes o inconsistentes; derived referenciado con hash/manifiesto válidos e inválidos; y PDF/manifiesto sin referencia después de 409. Cada fixture debería declarar procedencia, hash, característica que ejerce y resultado esperado. Los archivos grandes y las pruebas de 128 MiB requieren estrategia de almacenamiento/CI antes de incorporarse.

## 11. Decisiones funcionales todavía abiertas

Estas preguntas **no se resuelven aquí** y no deben codificarse por accidente como expectativas de tests:

1. ¿Qué política rige un PDF/manifiesto derivado sin referencia tras 409, undo o cierre: limpieza inmediata, retención temporal o reconciliación? ¿Quién decide y con qué plazo?
2. ¿Qué se publica o recupera si falla el manifiesto después de publicar el PDF? ¿Cómo se comunica el resultado al operador?
3. ¿Debe `artifact_lifecycle.py` tener invocador productivo? ¿En arranque, por job, por operación o mantenimiento explícito? ¿Qué carpetas y archivos puede tocar sin arriesgar fuentes?
4. ¿Qué semántica final tendrá PDF raster: DPI, color, cajas de página, contenido residual, tamaño y usos admitidos?
5. ¿Qué tolerancias y artefactos definen paridad exigible entre canvas, Preview y PDF, considerando rasterizadores y perfiles distintos?
6. ¿Habrá soporte de PDF/X y OutputIntents gestionados por color? Hoy existe rechazo explícito de OutputIntents en la preparación nativa; ampliar soporte exige contrato y validación, no ignorarlos.
7. ¿Se necesita un límite global entre procesos, cola o bloqueo por job para las salidas? ¿Cómo se recuperan publicaciones interrumpidas?
8. ¿Cuáles serán los límites productivos finales de páginas, píxeles, bytes fuente, fuentes, colocaciones, memoria y tiempo? Los límites ejecutables actuales no son automáticamente un SLA.
9. ¿Cómo evolucionará el producto desde un pliego con piezas hacia múltiples pliegos, firmas, secuencia editorial, imposición para encuadernación y creep?
10. ¿Qué contrato operativo tendrán frente/dorso, flip y verificación de correspondencia entre caras?
11. ¿Qué requisitos de CTP, marcas, separaciones, perfiles y aceptación física deberán cumplirse antes de describir una salida como apta para producción?

## 12. Relación con documentos futuros

- **44 — Mapa de conexiones:** ubicación de módulos, rutas, persistencia y dependencias observadas.
- **46 — Este documento:** hallazgos, calidad de evidencia, cobertura, deuda y decisiones pendientes.
- **47 — Objetivo funcional y roadmap del producto:** documento previsto para definir qué producto se desea y ordenar entregas; todavía no existe como decisión contractual en 46.
- **`GUIA_PARA_AGENTES_EDITOR_V2.md` futura:** guía operativa para agentes cuando arquitectura y objetivo funcional estén suficientemente estabilizados. No se crea ni se presupone su contenido aquí.

El trabajo diario y las intervenciones verificadas se registran en [41](41_TRABAJO_DIARIO_Y_BITACORA_V2.md). Este documento preserva antecedentes útiles sin convertir resultados históricos en validación actual.
