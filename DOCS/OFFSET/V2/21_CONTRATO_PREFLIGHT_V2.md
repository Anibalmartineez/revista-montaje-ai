# Contrato canónico de preflight del Editor Offset Visual V2

> Actualización 39A (2026-09-16): preflight nativo V2, política/capacidades versión 2; snapshot de layout, opciones y archivos efectivos. Se rechazan reportes incompletos, obsoletos o incompatibles y derivados ausentes/alterados. Publicación y limpieza coordinadas; entrega desde bytes de la petición. El candidato PDF raster bloquea preservación vectorial hasta 39B. Gates globales apagados. Evidencia y continuación: [plan 39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md). Lo que sigue conserva el corte histórico indicado.

## 1. Estado, autorización y jerarquía

Fecha: 2026-09-06.

Fase: 21-A, definición documental de preflight, independiente del rediseño cerrado. No existe una Fase 19-H.

Estado: contrato implementado parcialmente en la Fase 24 como reporte mínimo ejecutable. La implementación no habilita salida productiva ni sustituye las decisiones pendientes de PDF, preview, marcas o CTP. Posteriormente el usuario aclaró que permite reutilizar temporalmente las funciones V1 y aprobó código y pruebas del ensayo offline [22](22_ENSAYO_REUTILIZACION_SALIDA_V1.md). V2 principal e independiente sigue siendo el destino.

Clasificación de las afirmaciones:

- **Decisión aprobada:** independencia futura de V2, copia selectiva y reutilización temporal explícita de funciones V1 en infraestructura.
- **Hecho actual:** comportamiento contrastado con código, schema o persistencia durante la auditoría previa.
- **Especificación propuesta:** reglas del futuro preflight definidas aquí para revisión y posterior implementación.
- **Pendiente:** decisiones operativas, tolerancias o detalles que deben cerrarse antes de su fase dependiente.

Fuentes relacionadas:

- [20 — Estado operativo](20_ESTADO_ACTUAL_POST_REDISENO_UX_V2.md): entrada vigente, evidencia histórica de cierre y actualización posterior.
- [19 — Trazabilidad UX](19_PLAN_Y_TRAZABILIDAD_REDISENO_UX_V2.md): fase cerrada; no se modifica.
- [01 — Layout V2](01_CONTRATO_LAYOUT_V2.md): contrato persistente vigente; no se amplía con este documento.
- [02 — Kernel geométrico](02_KERNEL_GEOMETRICO_V2.md): semántica geométrica canónica.
- [03 — Adaptador temporal](03_ADAPTADOR_SALIDA_V2.md): capacidades del puente existente, no capacidades objetivo de V2.
- [11 — Decisiones arquitectónicas](11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md): dirección aprobada y pendientes transversales.

Este documento es la referencia de diseño del nuevo reporte. La forma ejecutable y la persistencia mínima están descritas en [24](24_PREFLIGHT_EJECUTABLE_V2.md). Las reglas de salida productiva siguen siendo intención documental hasta cerrar sus fases correspondientes.

## 2. Dirección arquitectónica aprobada: V2 principal e independiente

V2 será propietario de su dominio, geometría, preflight, persistencia, imposición y salida. Su destino es funcionar sin importar ni ejecutar lógica productiva V1 o módulos de negocio compartidos con V1. El editor anterior permanece como legacy.

Puede copiarse código útil del editor anterior dentro de superficies propias de V2, sujeto a:

1. identificar origen, responsabilidad y dependencias de lo copiado;
2. conservar los avisos y condiciones de licencia aplicables;
3. adaptar entradas, errores y comportamiento al contrato V2;
4. retirar defaults, heurísticas y acoplamientos legacy que no correspondan;
5. aportar pruebas V2 y evidencia de paridad con el resultado esperado;
6. mantener después esa copia de manera independiente, sin sincronización implícita ni importación de regreso a V1.

Independencia no obliga a reescribir bibliotecas externas como PyMuPDF o Flask. Tampoco decide todavía empaquetado, despliegue separado o división del repositorio.

Las dependencias actuales son deuda de transición explícita: registro en `app.py` compartido y motor Repeat en `engines/step_repeat_pro_engine.py`, entre otras que deberá completar una auditoría de extracción. Se retirarán en fases propias. Esta fase no las elimina ni modifica.

La futura salida propia V2 puede alcanzarse mediante reutilización temporal de funciones V1, según la aclaración posterior del usuario. El dominio y el montaje permanecen en V2; los imports temporales se concentran en infraestructura. El ensayo 22 caracteriza esa frontera antes de habilitar funciones en la aplicación. Comparar con legacy no obliga a reproducir errores ni a conservar su semántica de bleed, defaults o rotaciones.

## 3. Punto de partida comprobado

Auditoría de solo lectura sobre `codex/editor-offset-v2-output-preflight`, HEAD `fe596efcdf24fb46d077f857c8fbc4862c1671ca`, árbol limpio antes de esta fase documental.

| Evidencia | Hecho confirmado | Límite |
| --- | --- | --- |
| `editor_offset_v2/blueprint.py`, `application/output_service.py` | GET capabilities carga el layout persistido y devuelve revisión, compatibilidad e issues | No resuelve archivos ni genera salida |
| `static/js/editor_offset_v2/output_panel.js` | La UI guarda cambios pendientes antes de consultar e invalida diagnósticos obsoletos | El endpoint es de solo lectura; la acción completa puede guardar |
| `infrastructure/editor_output_adapter.py` | Resuelve ubicación/existencia y construye OutputJob o rechaza sin job parcial | No recalcula hash, reinspecciona PDF ni ejecuta renderer |
| `application/asset_service.py`, `infrastructure/pdf_inspector.py` | Upload guarda hash, páginas, cajas y miniaturas; inicia preflight en `not_run` | No es preflight profundo |
| `application/job_service.py` | El PUT valida estructura/revisión del layout recibido | No coteja sus metadatos de assets con el archivo físico |
| `domain/validation.py` | Comprueba referencias, tamaños, números y cardinales | No comprueba colisiones, contención ni suma de márgenes contra tamaño |
| `static/js/editor_offset_v2/canvas_renderer.js` | Coloca miniatura proporcional con clip trim y marca artwork aproximado | No representa exactamente cajas desplazadas ni transformaciones internas |
| `domain/output_contract.py` | Hay modelos temporales inmutables e issues `error`/`warning` | Falta cobertura, política, huella física y transporte del volteo dúplex |
| `tests/editor_offset_v2/test_output_adapter_v2.py` | Usa archivos `%PDF-simulated` | Demuestra adaptación estructural, no fidelidad PDF |

El job local documentado `ev2_14d0c6f8f60e601aed51f833` se leyó en revisión 57: pliego 650 × 550 mm, un asset, un work y ocho slots front. Selecciona CropBox, bleed de 3 mm y `clip_to = trim_box`; TrimBox/BleedBox ausentes, preflight `not_run`, carpetas `reports`, `previews` y `outputs` vacías. El hash físico coincidió con layout y metadata. Esta evidencia local no es un fixture canónico ni una reinspección/render del PDF.

No se ejecutaron tests ni recorridos durante la auditoría. Los resultados 19-G del documento 20 son históricos, no un baseline nuevo.

### 3.1 Diferencias con el flujo legacy

La frontera revisada atraviesa `routes.py` → `services/editor_offset_http_service.py` → `editor_offset_output_contract.py` → `editor_offset_output_service.py` → `montaje_offset_inteligente.py` → `strategies/manual.py`/`common.py` → renderer.

Hechos relevantes para reutilizar código:

- legacy espera `layout_constructor.json`, defaults y precedencias que V2 no comparte;
- el servicio puede omitir diseños cuyo archivo no existe;
- la configuración activa centrado por defecto y la rama manual puede recentrar;
- raster y vector hybrid pueden sintetizar bleed reflejando bordes del trim;
- la normalización manual no conserva `crop_marks` por posición y el dibujado condiciona esas marcas a bleed positivo;
- preview utiliza una ruta en gris desde la página original escalada, separada del PDF final;
- el puente transmite la rotación V2 y rutas raster/preview legacy aplican `-rot`: la correspondencia requiere artwork asimétrico y caracterización;
- separar posiciones front/back no demuestra aplicar `faces.duplex.flip`.

Inferencia: una conexión directa puede cambiar contenido, posiciones o marcas aunque capabilities informe compatibilidad. No se afirma una reproducción runtime; estos riesgos provienen de lectura de código y deben caracterizarse con fixtures aislados si se reutilizan esas piezas.

## 4. Objetivo y separación de responsabilidades

El preflight deberá responder: qué entrada exacta se examinó, qué comprobaciones se completaron, qué problemas existen y si esa evidencia permite una operación concreta bajo una política identificada.

Se separan cuatro superficies:

| Superficie | Autoridad | Resultado |
| --- | --- | --- |
| Validación Layout V2 | Contrato 01, schema y validador actuales | Documento estructuralmente aceptable para edición/persistencia |
| Capabilities temporal | Puente existente | Compatibilidad limitada con su representación |
| Preflight de asset | Inspección de bytes fuente identificados por hash | Evidencia física por archivo/página, sin aprobación del montaje |
| Preflight de layout | Snapshot de layout, evidencia física, kernel y política V2 | Decisión por operación y alcance de caras |

Un asset inspeccionado satisfactoriamente no aprueba automáticamente cada slot que lo usa. Resolución efectiva, clipping, cobertura, posición y colisiones dependen del montaje.

El preflight no corrige, no impone, no mueve slots, no modifica fuentes, no activa funcionalidades ni sustituye la autorización del operador para producir. La futura generación verificará otra vez la vigencia del reporte y las capacidades implementadas.

## 5. Entradas y autoridad física

### 5.1 Snapshot del montaje

Entrada obligatoria para alcance `layout`:

- job ID, revisión y hash SHA-256 de los bytes exactos de `layout_v2.json` examinados;
- copia inmutable de esos bytes y resultado de validación, sin defaults nuevos;
- operaciones solicitadas: `preview`, `pdf_final` o `ctp`;
- caras y orden solicitados, coherentes con `faces.enabled` y `export.faces`;
- política de preflight y capacidades objetivo, ambas identificadas por ID y versión.

El hash de bytes evita exigir ahora una serialización JSON canónica nueva. Un cambio de formato también invalida conservadoramente el snapshot. No se incluyen reportes o índices dentro de ese archivo. Cada lectura analiza los mismos bytes que se hashean; no se hashea una lectura y valida otra.

### 5.2 Manifiesto físico

Para cada asset utilizado por slots de las caras solicitadas: ID, storage key relativa, hash declarado y observado, tamaño observado, páginas físicas y evidencias de cajas/rotación. Resolver la ubicación desde la raíz configurada y la identidad gestionada por el servidor; rechazar escapes y archivos inseguros. No confiar en una ruta absoluta o un hash enviado por el cliente como prueba.

La inspección debe usar los mismos bytes identificados por el hash, mediante lectura estable o snapshot controlado. La implementación concreta depende del gate de límites de recursos y almacenamiento. Un cambio durante la lectura impide una decisión favorable.

Se comparará PDF físico, metadata del servidor y declaración del layout. Una discrepancia relevante genera issue; no se corrige silenciosamente ni se reescribe el original. La política para proteger campos de assets en PUT es una fase de compatibilidad separada: no se endurece ahora la aceptación de layouts existentes.

Los assets no usados pueden analizarse a pedido con alcance `asset`. Sus problemas no bloquean automáticamente una salida que no los utiliza. La integridad estructural de referencias del layout completo sigue validándose antes de elegir alcance.

## 6. Contrato lógico del reporte propuesto

Destino: `reports/<report_id>.json`, relativo a la raíz del job. Reporte completo e inmutable; IDs y nombres físicos generados/controlados por el servidor. No se publican rutas absolutas en la respuesta de operador.

Versión documental inicial: `report_schema_version = 1`, independiente de `layout_schema_version`. Cambios incompatibles de estructura/semántica exigen otra versión del reporte; cambios de reglas/tolerancias exigen otra versión de política. No se añade `layout_schema_revision`.

| Campo | Tipo/regla |
| --- | --- |
| `report_schema_version` | Entero exacto `1` |
| `report_id` | Identidad única de reporte |
| `scope` | `asset` o `layout` |
| `subject` | Job ID; revisión/hash layout para `layout`, ambos `null` para `asset`; asset ID para `asset`, `null` para `layout` |
| `inputs` | Manifiesto físico, referencias a reportes de asset reutilizados con su hash, operaciones y caras solicitadas |
| `policy` | ID y versión; tolerancias explícitas con unidades; catálogo de checks aplicables |
| `capabilities` | ID y versión del conjunto objetivo realmente implementado |
| `analyzer` | ID y versión; versiones de herramientas que afecten resultados |
| `started_at`, `completed_at` | Instantes UTC; metadatos operativos que no cambian el significado de findings |
| `execution` | `complete` o `incomplete`, derivado de cobertura |
| `checks` | Resultados individuales con ID estable, referencias, estado y evidencia |
| `issues` | Hallazgos normalizados y vinculados a checks |
| `decisions` | Una entrada por operación solicitada; vacío en alcance `asset` |

Todos esos campos son obligatorios en el reporte completo; las estructuras anidadas se formalizarán en schema ejecutable antes de implementar su escritor. No deben ampliarse durante una implementación sin actualizar esta referencia. Se rechazan valores no finitos y campos desconocidos críticos. Los ejemplos de la sección 12 son casos de aceptación, no sustitutos de ese schema.

### 6.1 Checks y cobertura

Cada check registra `check_id`, alcance/entidades, `status`, `issue_ids` y `evidence`. Estados:

- `passed`: ejecutado sin findings;
- `findings`: ejecutado y produjo hallazgos;
- `not_applicable`: no aplica, con justificación verificable de política;
- `not_run`: no ejecutado;
- `failed`: no pudo completarse, con error controlado.

La política define qué checks son obligatorios por operación. Un reporte no decide por sí mismo que un check requerido es opcional. No puede usar `not_applicable` para encubrir una capacidad no implementada.

`execution = complete` exige que todas las instancias aplicables del alcance obligatorio terminen en `passed`, `findings` o `not_applicable` justificado. Puede haber un reporte completo con errores bloqueantes. `not_run`, `failed` o ausencia de un check obligatorio producen `incomplete` y bloqueo.

### 6.2 Issues

Cada issue contiene:

- `issue_id`, `check_id`, `code` estable y `severity` (`info`, `warning`, `error`);
- `message` comprensible y acción correctiva orientativa, sin ejecutar reparación;
- `references`: path del layout y listas de asset IDs, páginas, work IDs, slot IDs y caras afectadas según corresponda;
- `evidence`: observado, esperado, unidad, tolerancia y origen de la medición cuando existan;
- `blocks`: operaciones afectadas, derivadas de política y nunca editables libremente por el cliente.

`code` gobierna clasificación, no el texto traducido. Severidad y bloqueo se registran por separado. Un warning puede bloquear una operación si la política lo exige; su nombre no implica autorización. No hay bypass genérico, aceptación silenciosa ni aprobación mediante un checkbox en esta fase.

La UI puede agrupar hallazgos repetidos sin eliminar sus referencias ni el detalle canónico. Los issues de un reporte de asset conservan procedencia al ser usados por el reporte de layout; no se sustituyen por un warning genérico sin evidencia.

### 6.3 Decisiones y vigencia

Cada decisión registra `operation`, `status` (`eligible` o `blocked`), `blocking_issue_ids` y `reason_codes`. `eligible` exige simultáneamente:

1. cobertura obligatoria completa;
2. ausencia de bloqueos para la operación;
3. capacidad objetivo implementada y habilitada en el gate aprobado;
4. snapshot, assets y versiones aún vigentes al consumir el resultado.

La vigencia se calcula al leer/consumir el reporte; no se reescribe el reporte inmutable para marcarlo obsoleto. Cambiar layout, revisión, bytes de assets, política, analizador o capacidades impide reutilizarlo como aprobación vigente. Una selección, zoom o panel temporal no cambia el snapshot.

En el estado ejecutable actual ninguna ruta productiva V2 existe: este diseño no puede usarse para mostrar esas operaciones como habilitadas. Una futura evidencia favorable tampoco autoriza por sí sola el envío a CTP.

## 7. Geometría, cajas y contenido

### 7.1 Invariantes ya existentes

Conservar centro trim, milímetros, origen inferior izquierdo, giro antihorario cardinal, trim sin rotar y bleed separado. Footprints, bounds y polígonos se derivan mediante el kernel V2; no se persisten ni se recalculan con fórmulas distintas en el renderer.

El epsilon `1e-9 mm` resuelve ruido numérico. La tolerancia actual de capabilities `0.01 mm` compara tamaño fuente/trim. Ninguna de ellas es automáticamente una tolerancia mecánica, de clipping, registro o aprobación visual de imprenta.

### 7.2 Cajas y transformación: límites explícitos

- Registrar las cajas físicamente declaradas, su origen y rotación; conservar `null` para cajas ausentes en Layout V2.
- Diferenciar caja seleccionada de fuente, trim geométrico del slot, bleed disponible y región final de clipping.
- Una caja efectiva derivada para interpretar el PDF no debe presentarse como caja físicamente declarada ni persistirse como tal.
- Elegir explícitamente CropBox o MediaBox no es, por sí mismo, un error V2. Su soportabilidad debe evaluarse en el renderer nativo; no heredar el veto del puente a toda caja distinta de TrimBox.
- Una caja seleccionada inexistente sigue siendo referencia inválida. No sustituirla automáticamente.
- Definir y comprobar coordenadas de cajas desplazadas, herencia, referencias indirectas, unidades PDF y relaciones entre cajas antes de habilitar cada caso.
- Evaluar `actual_size` contra la fuente efectiva y su orientación intrínseca, preservando trim persistido.
- Las escalas, offset, giro interno, espejos y clipping solo pueden aprobarse con un orden de composición y una semántica métrica definidos y probados.
- Un bleed geométrico de 3 mm no prueba que haya artwork utilizable en esos 3 mm. La igualdad de cajas tampoco prueba cobertura de contenido.
- Queda prohibido sintetizar bleed, expandir, escalar o cambiar clipping silenciosamente. Cualquier corrección futura creará un asset propio e inmutable y requerirá una acción explícita.

El orden matricial exacto y el significado operativo de `clip_to` respecto de caja física y envolvente de slot siguen pendientes. Hasta resolverlos, esos casos se informan como capacidad no demostrada; no se improvisa una transformación al implementar el preflight.

## 8. Matriz inicial de reglas y severidades propuestas

Los códigos siguientes pertenecen al nuevo reporte; no renombran los issues del endpoint temporal. Son reglas de diseño a revisar, no nuevos bloqueos de guardado.

| Código | Condición | Severidad | Consecuencia propuesta |
| --- | --- | --- | --- |
| `LAYOUT_INVALID` | Incumplimiento del contrato existente | error | Bloquear las operaciones solicitadas; no continuar con geometría no confiable |
| `ASSET_UNSAFE_PATH` | Resolución física insegura | error | Bloquear operaciones que requieren ese asset |
| `ASSET_MISSING` | Archivo utilizado ausente | error | Bloquear; no omitir slots |
| `ASSET_IDENTITY_MISMATCH` | Hash/metadata/archivo no concuerdan | error | Bloquear hasta resolver identidad |
| `PDF_UNREADABLE` | PDF utilizado no puede inspeccionarse | error | Bloquear sin publicación parcial favorable |
| `PDF_METADATA_MISMATCH` | Página, caja o rotación física difiere de la declaración | error | Bloquear; no normalizar el layout |
| `PDF_SEMANTICS_UNSUPPORTED` | Unidades, cajas o comportamiento no representable con evidencia | error | Bloquear operaciones afectadas |
| `PREFLIGHT_INCOMPLETE` | Check obligatorio faltante, no ejecutado o fallido | error | Bloquear, aunque los demás checks pasen |
| `OUTPUT_FEATURE_UNSUPPORTED` | Opción pedida no implementada para esa operación | error | Bloquear esa operación |
| `PRINTABLE_AREA_EMPTY` | Márgenes no dejan área útil | error | Bloquear producción; preview solo bajo política diagnóstica explícita |
| `TRIM_OUTSIDE_SHEET` | Parte del trim queda fuera del pliego | error | Bloquear PDF/CTP; preview debe poder mostrar el hallazgo si el render es fiel |
| `BLEED_OUTSIDE_PRINTABLE` | Footprint con bleed excede área imprimible, incluido pliego | warning | Bloquear producción hasta aprobar política de borde de imprenta |
| `TRIM_OVERLAP` | Intersección de área positiva entre trims de una misma cara | error | Bloquear producción; no mezclar caras en colisiones |
| `BLEED_OVERLAP` | Intersección solo por bleed | warning | Bloquear producción hasta decidir política de corte/bleed compartido |
| `CONTENT_COVERAGE_UNPROVEN` | Cobertura de trim/bleed requerida no demostrada | error | Bloquear producción; no confundir caja con artwork |
| `CONTENT_TRANSFORM_UNSUPPORTED` | Transformación o clipping solicitado no demostrado | error | Bloquear render que no pueda representarlo fielmente |
| `SOURCE_SIZE_MISMATCH` | `actual_size` incompatible según tolerancia aprobada | error | Bloquear producción; no escalar automáticamente |
| `QUANTITY_MISMATCH` | Conteo actual distinto de lo requerido | warning | Bloquear producción hasta una política explícita para parcialidad/sobrantes |
| `FACE_REQUEST_INVALID` | Cara/orden solicitado incoherente o cara requerida vacía | error | Bloquear operación afectada |
| `DUPLEX_UNSUPPORTED` | Se solicita volteo no implementado y demostrado | error | Bloquear salida dúplex; no reinterpretar como dos caras simples |
| `MARKS_UNSUPPORTED` | Perfil solicitado no soportado íntegramente | error | Bloquear; no descartar marcas |
| `CTP_UNSUPPORTED` | Operación/configuración CTP sin gate propio | error | Mantener CTP bloqueado |

El contacto por borde o vértice no es overlap bajo el kernel vigente. La política productiva puede exigir un gap positivo independiente del epsilon.

Fuentes, color, perfiles, resolución efectiva, transparencias y sobreimpresión necesitan checks específicos según el perfil productivo. No se declaran seguros por estar ausentes del catálogo provisional: hasta definir esa cobertura, la política de producción está incompleta y no puede emitir `eligible`.

Una preview diagnóstica podrá representar montajes con hallazgos productivos si su propio gate de seguridad/fidelidad se cumple. Esto no permite ignorar archivos, clipping o transformaciones que no puede representar. La UI futura deberá mostrar el alcance y los bloqueos sin rotularla como PDF aprobado.

## 9. Caras, cantidades y procedencia

La validación contractual comprende el layout completo. Los checks físicos y productivos se aplican a las caras explícitamente solicitadas y a sus slots, sin depender de la cara visible, selección, aislamiento o visibilidad temporal.

No copiar frente a dorso ni invertir automáticamente contenidos. El reporte identifica orden y configuración dúplex; dos objetos OutputFace no demuestran correspondencia física del volteo. Un modo no implementado se bloquea.

Usar `slot.source` para cada instancia. Derivar conteos actuales desde `slots[]`, por work y cara. `imposition.last_result` conserva historia y no aprueba cantidades después de ediciones. La correspondencia entre cantidades por cara y unidades terminadas dúplex necesita política propia; no se suman automáticamente front y back como productos independientes.

Locks regulan edición; `generated_by` conserva procedencia. Ninguno sustituye el preflight ni constituye permiso de exportación. El preflight no modifica esos campos.

## 10. Persistencia, publicación y recuperación

Propuesta inicial para evitar ciclos de revisión:

1. Capturar snapshot y manifiesto identificados; analizar sin mutar Layout V2.
2. Construir y validar el reporte completo en un archivo temporal controlado bajo `reports/`.
3. Publicarlo atómicamente con ID nuevo, sin sobrescribir reportes existentes.
4. Comparar snapshot y versiones al consumirlo; si el job cambió, conservar evidencia histórica pero devolver estado obsoleto.
5. Ante un fallo de escritura, no devolver reporte favorable ni URL utilizable. Limpiar exclusivamente el temporal propio y conservar fuentes/layout.

La primera implementación no actualizará `assets[].preflight_*` ni `pages[].preflight` al publicar un reporte de montaje. Así no incrementa revisión ni invalida su propio snapshot. Esos campos actuales se conservan por compatibilidad; el consumidor del nuevo reporte no los tratará como evidencia suficiente.

Los futuros reportes de asset pueden reutilizarse por identidad física y versiones; no dependen de posiciones del montaje. Si se decide actualizar sus resúmenes en Layout V2, deberá diseñarse por separado la publicación coordinada y el incremento de revisión. Un reporte de montaje no debe escribirse en un campo que describe preflight de asset.

No se incorpora un índice mutable de «último reporte aprobado» en esta fase. Si se necesita más adelante, su actualización y recuperación requieren diseño explícito. Los nombres de rutas API, tratamiento HTTP y límites de recursos pertenecen al gate de implementación.

El lock actual solo protege un proceso. No se declarará producción multiproceso segura. La futura generación deberá garantizar identidad del snapshot hasta finalizar el artefacto; una comprobación previa seguida de lectura mutable no basta. Retención, borrado de reportes/derivados, backups y despliegue multiproceso siguen como fases separadas.

## 11. Responsabilidades futuras y compatibilidad

Ubicaciones candidatas, todavía inexistentes y sin autorización para crearlas como código:

| Superficie V2 | Responsabilidad propuesta |
| --- | --- |
| `domain/preflight_contract.py` y schema propio del reporte | Modelos, estados, issues y reglas de estructura |
| `domain/` | Decisión de política y geometría; sin acceso a archivos o Flask |
| `application/preflight_service.py` | Orquestación de snapshot, inspección y decisiones |
| `infrastructure/` | Lectura física segura, inspector y repositorio de reportes |
| API y panel V2, en fase posterior | Solicitud, alcance, vigencia y presentación |

El nuevo dominio no debe importar `montaje_offset_inteligente.py`, servicios V1, estrategias legacy ni el OutputJob temporal como contrato nativo. Si se copia una función útil, la copia debe residir y mantenerse dentro de V2.

Capabilities conserva su ruta, respuesta y significado actuales. Un nuevo reporte no reutiliza `compatible` como sinónimo de aprobación. La incorporación futura de API/UI requiere acciones propias y pruebas de revisión/obsolescencia, sin alterar undo/redo, autosave, locks ni controles existentes.

No se impone a todos los jobs V2 un campo obligatorio nuevo. Un layout válido podrá permanecer editable aunque esté bloqueado para producción. Compatibilidad de edición y elegibilidad de exportación son contratos distintos.

## 12. Casos de aceptación del contrato

| Caso | Entradas y cobertura | Resultado esperado |
| --- | --- | --- |
| C-01: asset inspeccionado | Hash observado coincide, todas las páginas del alcance inspeccionadas, checks completos | Reporte `asset`, sin decisiones de montaje |
| C-02: montaje apto bajo una capacidad futura habilitada | Snapshot vigente, checks obligatorios completos y sin bloqueos | `execution = complete`, decisión `eligible` solo para operación solicitada |
| C-03: página en `not_run` | Resumen layout sin evidencia física reutilizable y check físico sin ejecutar | `incomplete`, `PREFLIGHT_INCOMPLETE`, operación bloqueada |
| C-04: hash cambiado | Layout conserva referencia, bytes físicos distintos | `ASSET_IDENTITY_MISMATCH`, sin salida parcial |
| C-05: revisión cambia durante análisis | Reporte examina revisión N; job actual N+1 | Reporte histórico conservado; consumo lo presenta obsoleto y bloquea reutilización |
| C-06: TrimBox ausente, CropBox seleccionado | Referencia V2 válida, caja física coherente | No aplicar veto legacy a CropBox; evaluar capacidad nativa y cobertura, bloquear si no demostradas |
| C-07: bleed solo declarado | Slot pide 3 mm y cobertura no demostrada | `CONTENT_COVERAGE_UNPROVEN`; no reflejar bordes automáticamente |
| C-08: colisión entre trims | Checks completos con intersección en la misma cara | `complete` con `TRIM_OVERLAP`; PDF/CTP bloqueados; preview requiere gate propio |
| C-09: fallo de analizador | Una comprobación requerida no termina | `incomplete`, sin `eligible` pese a otros checks exitosos |
| C-10: dorso excluido | Exportación explícita front, referencias estructurales válidas | No inspeccionar recursos back como requisito productivo front; registrar alcance |
| C-11: parcialidad ambigua | Conteo actual difiere de intención histórica | `QUANTITY_MISMATCH`; no usar last_result como aceptación automática |
| C-12: renderer inexistente | Checks físicos/geometría favorables, capacidad productiva ausente | `OUTPUT_FEATURE_UNSUPPORTED`; ninguna operación se habilita por documentación |
| C-13: fallo al publicar | No se pudo publicar reporte completo | Error controlado; fuentes/layout intactos, sin aprobación ni URL parcial |

## 13. Fixtures y pruebas necesarias, no ejecutadas

La siguiente fase preparará fixtures aislados bajo `tests/fixtures/editor_offset_v2/` y pruebas V2, sin modificar el job real. Cada fixture tendrá origen reproducible, hash de bytes, intención, medidas/cajas esperadas y resultado esperado por política. Si una librería produce bytes no deterministas, el artefacto fijado y su hash serán la referencia; la receta no sustituye su identidad.

| Grupo | Casos necesarios | Evidencia exigida |
| --- | --- | --- |
| Contrato de reporte | Campos, enums, referencias, checks faltantes, versiones, no finitos, cobertura/decisiones incoherentes | Validación estructural y semántica; no aprobación por omisión |
| Identidad/seguridad | Archivo ausente, reemplazado, homónimos, rutas inseguras, symlinks, metadata discrepante | Bytes y hashes; bloqueo sin omitir slots |
| PDF físico | Multipágina, cajas ausentes/desplazadas/heredadas/indirectas, unidades, cajas contradictorias, dañado/cifrado y límites | Página/caja realmente inspeccionada; error controlado o soporte demostrado |
| Geometría | Cardinales, decimales, centros, márgenes vacíos, fuera de pliego/imprimible, contacto, overlap trim/bleed por cara | Fixtures del kernel y medidas en mm |
| Artwork | Esquinas identificadas, textos distintos por página/cara, bleed real distinto de reflejo, cobertura insuficiente | Detección visual/métrica de espejo, giro, desplazamiento y clipping |
| Transformaciones | `actual_size`, tamaños discrepantes, escalas, offsets, giro intrínseco/slot/contenido, mirrors y clip | Semántica aprobada o bloqueo explícito, nunca degradación |
| Caras/cantidades | Frente solo, dorso solo, ambas, orden, vacías, fuente sobrescrita, conteos tras edición, dúplex | Alcance exacto y ningún dorso inventado |
| Reportes | Revisión/hash/versiones cambiantes, dos análisis simultáneos, fallo de publicación y lectura incompleta | Inmutabilidad, obsolescencia y recuperación |
| Producción futura | PDF con páginas/cajas esperadas y preview derivado de la misma representación | Paridad geométrica y visual, sin tomar el canvas aproximado o legacy como oráculo único |

Cobertura existente localizada: `tests/editor_offset_v2/test_output_adapter_v2.py`, `test_pdf_inspector_v2.py`, `test_asset_service_v2.py`, `test_assets_routes_v2.py`, `test_routes_v2.py`, `test_geometry_v2.py`, `js/geometry_parity_v2.test.cjs`, `js/semantic_stabilization_v2.test.cjs` y ambos Playwright V2. Su existencia no prueba que pasen en este corte.

No se fijan ahora umbrales de DPI efectivo, diferencias de color, registro o error visual aceptable. La receta de comparación deberá definir resolución de rasterización, referencias, métricas y tolerancias por separado del epsilon geométrico.

## 14. Decisiones pendientes y gate que las necesita

| ID | Decisión requerida | Propuesta o contención actual | Antes de |
| --- | --- | --- | --- |
| PF-D01 | Severidades/bloqueos para bordes, overlap bleed y cantidades | Matriz conservadora de sección 8; sin bypass | Implementar evaluación productiva |
| PF-D02 | Orden matricial y semántica de clipping | No habilitar casos ambiguos; preservar Layout V2 | Implementar checks de contenido o renderer |
| PF-D03 | Primer conjunto de cajas/páginas/rotaciones soportado | Diseñar para V2; no heredar página 1/TrimBox como límite obligatorio | Fixtures del primer renderer |
| PF-D04 | Tolerancias y cobertura del perfil de imprenta | Política incompleta impide producción favorable | Aprobar perfil productivo |
| PF-D05 | Lectura estable, recursos y API de reportes | Snapshot propio, publicación inmutable sin tocar layout | Implementar servicio/repositorio |
| PF-D06 | Protección de metadatos enviados por PUT | Verificar físicamente para salida; no romper guardado existente | Cambiar propiedad de campos/persistencia |
| PF-D07 | Dúplex, marcas y CTP | Bloquear lo no soportado; fases propias | Habilitar esas capacidades |
| PF-D08 | Extracción de Repeat y otras dependencias compartidas | Copia selectiva adaptada y pruebas V2; inventario de extracción pendiente | Declarar independencia completa |
| PF-D09 | Reportes de asset y resúmenes en layout | Mantener campos actuales; publicación inicial sin actualizarlos | Sincronizar summaries o migrar su autoridad |

El documento entrega una base revisable; no declara cerrados los gates que dependen de esas decisiones. Pueden avanzar fixtures de identidad, estructura y geometría ya definidas sin resolver todavía CTP, dúplex o métricas de color, siempre bajo autorización de su fase.

## 15. Plan SAFE, aceptación y rollback

### 21-A — Documento actual

Alcance autorizado: este documento, referencias/decisiones necesarias en 20 y 11, correcciones puntuales auditadas de 02 y 03. Se conservan 01, 19, AGENTS.md, código, schema, tests y datos reales.

Aceptación documental:

- dirección V2 independiente claramente aprobada y separada de su estado actual;
- evidencias, limitaciones e inferencias identificadas;
- reporte, cobertura, severidades, decisiones, vigencia y publicación definidos a nivel documental;
- decisiones abiertas con gate propio, sin umbrales inventados;
- pruebas, archivos candidatos, compatibilidad y rollback identificados;
- enlaces y diff revisados; solo documentos del alcance modificados.

### Gate posterior a 21-A — Ensayo de reutilización autorizado

El usuario aprobó la identificación de funciones útiles V1 y posteriormente su ensayo controlado. [22](22_ENSAYO_REUTILIZACION_SALIDA_V1.md) registra alcance, fixtures, resultados y bloqueos del invocador offline. La autorización cubre este ensayo y su documentación; no implementa el preflight canónico, preparación de páginas/cajas ni habilitación productiva. Las decisiones de bleed, clipping y marcas siguen abiertas para la siguiente adaptación.

### Gates posteriores, independientes

Actualización posterior: el usuario autorizó y se implementó el ensayo preparado
de [Fase 23](23_PREPARACION_FUENTES_Y_PARIDAD_SALIDA_V2.md), con página/caja,
orientación, bleed fuente o espejo explícito y marcas por slot. Esa evidencia
amplía el ensayo; no implementa el reporte canónico de este documento ni sustituye
los gates siguientes. La aceptación documental y el cierre 21-A de este archivo
conservan su alcance histórico.

1. Preflight ejecutable nativo y publicación de reportes.
2. Preview mínimo con representación fiel y capacidades explícitas.
3. PDF final con verificación de artefactos.
4. CTP/marcas y dúplex según fases aprobadas.
5. Extracción completa de dependencias productivas compartidas, sin mezclarla con correcciones de salida.

Cada gate necesita alcance, aceptación, pruebas autorizadas y rollback propios. La independencia es el destino aprobado; este orden no autoriza aplazarla indefinidamente ni ampliar el puente como arquitectura final.

Rollback documental: retirar o corregir exclusivamente este cambio documental mediante diff revisado, preservando evidencia histórica y cambios ajenos. No requiere migración, limpieza de jobs ni operación Git destructiva. El futuro preflight deberá poder retirarse sin modificar fuentes/layouts o el diagnóstico existente; quitar un gate no puede habilitar salida sin validación.

## 16. Trazabilidad de la fase

| Fecha | Evento | Estado y alcance |
| --- | --- | --- |
| 2026-09-06 | Auditoría SAFE de salida/preflight presentada al usuario | Solo lectura; código, documentos, tests leídos y evidencia local; sin ejecución productiva |
| 2026-09-06 | Usuario define V2 principal con código independiente y permite copiar lo útil de V1 | Decisión arquitectónica aprobada; extracción física todavía no realizada |
| 2026-09-06 | Usuario indica «inicia, aprobado» para la fase documental | Autoriza esta especificación y alineación necesaria; no código ni pruebas |
| 2026-09-06 | Especificación 21-A y referencias documentales preparadas | Revisión documental; próximo gate pendiente de aprobación, sin funciones productivas nuevas |
| 2026-09-06 | Aclaración posterior: compartir temporalmente funciones V1 está permitido; ensayo controlado aprobado | Ejecución aislada y resultados en documento 22; independencia futura preservada |

Comprobación documental de cierre: diff de los documentos existentes revisado, enlaces Markdown locales resueltos y los cinco documentos sin espacios finales ni bloques de código desequilibrados. `git diff --check` sin errores; avisos informativos LF/CRLF de Git. El archivo nuevo se comprobó también directamente porque aún no está rastreado. No se ejecutaron suites, Flask, navegador ni generación PDF; no hay commit o push.

La Fase 19 permanece cerrada. No se habilitan Preview, PDF final, CTP, resize, transformaciones avanzadas o IA mediante esta documentación.
