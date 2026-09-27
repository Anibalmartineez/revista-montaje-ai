# 43 — Salida PDF habitual V2: cinco entregas

Fecha de apertura: 2026-09-27.

## Acuerdo y alcance

Plan solicitado por el usuario después de auditar la salida del editor y el job `ev2_f2347e8ce720eb582054200f`. Se continúa desde el código existente. Este documento registra las cinco entregas acordadas, su propósito, aceptación y evidencia; no sustituye al código ni convierte documentos históricos en requisitos de implementación.

El usuario autorizó las entregas 1, 2 y 3 de forma sucesiva, y después las entregas 4 y 5. La entrega 3 parte de `374f048` y queda completada con la evidencia inferior. No se retoma automáticamente la entrega E del documento 42: es otro alcance.

Flujo esperado: preparar páginas/tamaño/sangrado → montar → preflight nativo V2 → Preview/PDF. La preparación decide el contenido; el montaje decide posiciones y marcas; el preflight decide qué operaciones son admisibles; el generador utiliza esas mismas decisiones; el arranque habilita las funciones habituales.

## Seguimiento

| Entrega | Problema que resuelve | Estado |
|---|---|---|
| 1. Decisiones coherentes de preflight | Bloqueos geométricos ignorados y Preview aprobada que luego supera el presupuesto de píxeles. | **Completado — 2026-09-27** |
| 2. Diagnóstico único de salida | Errores y mensajes del puente legacy confundidos con las capacidades del PDF nativo. | **Completado — 2026-09-27** |
| 3. Preparación y sangrado comprensibles | Cajas técnicas como decisión principal, sangrado faltante descubierto tarde y permiso de espejo que se pierde. | **Completado — 2026-09-27** |
| 4. Salida habilitada en el arranque habitual | Dependencia de un arranque especial de QA para usar Preview/PDF. | **Completado — 2026-09-27** |
| 5. Verificación integral | Ausencia de una comprobación conjunta del recorrido y de los archivos resultantes. | **Completado — 2026-09-27** |

## Entrega 1 — Decisiones coherentes de preflight

**Implementación:** hacer que las decisiones y el contrato del informe respeten `blocks` por operación independientemente de la severidad informativa. Conservar advertencias sin bloqueo, como marcas omitidas con sangrado cero. Compartir dentro de V2 el cálculo y presupuesto del bitmap de Preview entre preflight y render. Informar por separado incidencias del montaje, recursos de Preview y disponibilidad del servidor. Actualizar la versión de política/capacidades para no reutilizar informes anteriores como autorizaciones actuales.

**Aceptación:** sangrado fuera del área imprimible o superpuesto bloquea PDF/CTP según la política ya declarada; Preview puede servir para inspeccionarlo. Una Preview excesiva se detecta antes de renderizar y no bloquea un PDF vectorial por el tamaño del bitmap de pliego. Ninguna salida bloqueada deja artefactos parciales. Pruebas de límites, advertencias no bloqueantes, informes obsoletos, gates y persistencia sin cambios.

**Límite:** no cambia las cajas, el tratamiento del sangrado, los flags de arranque, la UI legacy ni el contrato Layout V2. No certifica PDF/X/CTP ni resuelve el rendimiento de 500 piezas.

## Entrega 2 — Diagnóstico único de salida

**Implementación prevista:** utilizar el preflight nativo como diagnóstico principal; retirar el puente legacy del flujo habitual y los mensajes de «salida temporal» asociados a la salida nativa. Agrupar incidencias por nombre de trabajo/página, explicar la operación afectada y la corrección posible. Distinguir función desactivada, montaje bloqueado y fallo de ejecución.

**Aceptación:** el caso auditado no recibe restricciones de primera página/TrimBox del puente antiguo como diagnóstico de su PDF nativo. Mensajes y botones coinciden con las decisiones actuales; informes desactualizados no habilitan generación.

## Entrega 3 — Preparación y sangrado comprensibles

**Implementación prevista:** mostrar tamaño detectado, tamaño final y sangrado en la preparación unificada. Dejar MediaBox/CropBox/TrimBox/BleedBox en opciones avanzadas, sin inventar cajas ausentes. Detectar si hay contenido de sangrado suficiente y ofrecer una decisión explícita cuando falte: otro archivo, espejo autorizado o cambio de sangrado. Aplicar el mismo flujo a una y varias páginas.

La decisión debe pertenecer al trabajo y sobrevivir a guardar/recargar. Antes de añadir un campo opcional persistente se coordinarán schema, validación, comandos reversibles, lectores, fixtures y comportamiento de trabajos anteriores. No reinterpretar datos existentes silenciosamente.

**Aceptación:** preparación individual/multipágina, cantidades distintas, guardar/recargar y undo/redo mantienen la elección. Canvas, preflight, Preview y PDF usan la misma decisión. El espejo se identifica como generado. Con sangrado cero se omiten las marcas de ese trabajo y se avisa, conforme a la decisión del usuario.

## Entrega 4 — Salida habilitada en el arranque habitual

**Implementación prevista:** establecer un arranque habitual explícito de V2 con Preview/PDF disponibles. Conservar dev tools apagadas y separar derivados de la salida PDF básica. Revisar los scripts existentes, sin cambiar inadvertidamente configuración de otras superficies o despliegues.

**Aceptación:** arranque y reinicio controlados conservan la disponibilidad; rutas y contexto UI coinciden. Los gates habilitan la función, nunca eluden el preflight. El operador no necesita un arranque especial de pruebas.

## Entrega 5 — Verificación integral

**Implementación prevista:** recorrer preparación → Repeat → aplicar → guardar → recargar → Preview → PDF con una copia del caso del usuario y fixtures de distintas cajas, páginas y sangrados.

**Aceptación:** inspeccionar archivos generados: dimensiones de pliego, páginas fuente, posiciones, giros, sangrado y marcas; contrastar canvas/Preview/PDF. Verificar originales inmutables, revisiones, historial y errores sin publicaciones parciales. Un HTTP 200 no constituye aceptación por sí solo. Registrar exclusiones y defectos pendientes, sin equiparar este cierre a certificación industrial.

## Cierre de entrega 4 — 2026-09-27

**Cambio:** `scripts/start_editor_offset_v2.ps1` es el arranque local habitual explícito. Usa el control de PID de `editor-offset-local-qa` con target V2, establece Preview/PDF en 1 y derivados en 0 solo para el proceso hijo; la habilidad fija dev tools en 0. `-Restart` detiene exclusivamente el proceso registrado tras verificar identidad. `scripts/check_editor_offset_v2_start.py` comprueba las rutas con job inválido sin crear artefactos, el gate separado de derivados y el contexto shell de dev tools. Se corrigió en `start_flask.ps1` la mezcla de mensajes con el valor booleano de PID activo/obsoleto. El script anterior `start_editor_offset_v2_output_qa.ps1` sigue siendo un perfil de QA con derivados habilitados. Los defaults de `editor_offset_v2/config.py` y `app.py` no cambiaron: otros arranques y despliegues conservan sus flags explícitos. Comando habitual: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_editor_offset_v2.ps1` (añadir `-Restart` solo para el proceso registrado).

**Evidencia:** al inicio no respondía Flask y existía un PID obsoleto. La habilidad no inició un duplicado; con `-Restart` retiró el registro obsoleto y arrancó PID 7652. Una segunda ejecución con `-Restart` verificó ejecutable, ruta, hora, comando y PID 7652 antes de detenerlo; PID nuevo 11432. Raíz y shell V2 devolvieron 200 tras el reinicio (segundo intento); el verificador confirmó Preview/PDF disponibles, derivados y dev tools desactivados. En la copia `ev2_f50a8ef1f55a4ff89e356d18`, el contexto HTML tiene URLs Preview/PDF y `derived_assets_enabled=false`, `dev_tools_enabled=false`; la UI muestra «Preview: habilitada. PDF: habilitado». Preflight a 300 dpi bloqueó solo Preview por `PREVIEW_RESOURCE_LIMIT`, mientras PDF permaneció elegible; a 150 dpi ambas operaciones fueron elegibles. Los gates no evitan preflight. Se generaron Preview y PDF de la copia sin alterar revisión 42 ni su layout.

**Límite:** este es un perfil local explícito; no cambia el arranque genérico `python app.py`, otros despliegues ni V1. El script de QA conserva sus derivados para pruebas específicas. No se activan CTP, PDF/X ni dev tools. Rollback: retirar los dos scripts nuevos y volver al arranque anterior; no hay migración de layouts.

## Cierre de entrega 5 — 2026-09-27

**Regresión integral nueva:** `test_mixed_boxes_bleed_quantities_repeat_and_output` crea un PDF de tres páginas: TrimBox con 3 mm físicos hasta BleedBox/MediaBox, página MediaBox con espejo de 2 mm autorizado y página CropBox con sangrado cero. Prepara 2/1/1 formas con decisiones `source_only`/`mirror_if_missing`/`source_only`, ejerce undo/redo de preparación y Repeat, calcula/aplica/guarda/recarga, gira una pieza 90° mediante un save con revisión, ejecuta preflight y genera Preview/PDF desde la UI. Comprueba una hoja 700 × 500 mm, textos de las tres páginas con multiplicidades y posiciones en sus footprints, 24 marcas PDF/SVG solo en las tres piezas con sangrado, layout/revisión y PDF fuente sin cambios tras exportar, ausencia de errores JS. Preview bloqueada a 300 dpi y PDF con revisión vieja devuelven 422/409 y dejan idénticos los archivos de `outputs/` y `previews/`. La primera ejecución reveló que el selector avanzado debía abrirse en el test; la segunda reveló que se comparaba el layout previo al incremento de revisión tras el save de giro. Se corrigieron las dos aserciones/acciones del test; ejecución final aprobada.

**Copia del montaje del usuario:** `ev2_f50a8ef1f55a4ff89e356d18`, creada solo con layout/assets, sin copiar salidas ni informes. El original `ev2_f2347e8ce720eb582054200f` ya estaba en revisión **42**, pliego **700 × 700 mm**, **tres** trabajos y **seis** slots: cuatro de páginas 1/2 del PDF original MediaBox, más dos de otro PDF con `mirror_if_missing`, todos con 3 mm. El primer PDF declara MediaBox `[0 0 612 792]`; claves CropBox/TrimBox/BleedBox ausentes (`null`). No se infirieron de los valores por defecto que devuelve PyMuPDF. SHA256 del layout original `723d9ae3dc30fefe68131e8c3a57dfc18735083056de8178b809d114afae8b4b`; fuentes `14e534d2482e463596e64ab5045c3a86f4c3d10ab2b0be087bbd174ba7035243` y `63d0a00bbad45579b9c2830fd5046d38de2d612602bb3021675e57d250318c7a`. Todos conservaron esos valores tras la QA. La copia permaneció en revisión 42; el navegador mostró seis piezas y las URLs Preview/PDF presentes, sin errores/warnings consultados.

**Archivos inspeccionados:** `.codex-runtime/salida43-entrega5/user-copy-preview.png`, `user-copy.pdf` y `user-copy-pdf-raster.png`. Preview a 150 dpi y PDF del perfil `vector_hybrid` a 300 dpi se generaron con revisión 42. El PDF tiene una hoja de **699,99999 × 699,99999 mm**, 7.162 caracteres extraídos, dos apariciones de texto distintivo de página 1 y dos de página 2, y las dos piezas adicionales visibles al pie. Las cuatro piezas grandes y dos pequeñas coinciden visualmente con el canvas de la copia y con el raster del PDF; 48 segmentos de marcas miden 6,09 pt cada uno (cuatro segmentos largos adicionales pertenecen al contenido fuente). Preview y PDF rasterizados a 150 dpi miden ambos 4134 × 4134 px; diferencia RGB media 0,43/255, 0,44 % de píxeles difieren más de 32 niveles. La diferencia pequeña se debe al camino/raster de resolución distinta, por lo que no se declara identidad píxel a píxel. Preflight a 300 dpi bloqueó solo Preview por 68.359.824 píxeles previstos, manteniendo PDF elegible; a 150 dpi ambos elegibles. Las llamadas directas bloqueadas (Preview 422; PDF con revisión vieja 409) no cambiaron los cuatro archivos publicados de la copia.

**Pruebas ejecutadas:** Python V2 `pytest tests/editor_offset_v2 -q -k "not (bounded_placement_load and 500)"`: **623 passed, 1 skipped, 1 deselected**, 20 avisos de dependencias. Node V2 completo: **165 passed**. Seis archivos Playwright V2 completos: **37 passed**, cinco avisos de dependencias; el caso mixto final se repitió tras añadir la aserción de archivos sin publicación parcial: **1 passed**. `py_compile` de los dos Python modificados y `git diff --check` correctos. Se verificó además el arranque normal sin `-Restart` contra el PID activo 11432: reutilizó el proceso, raíz/shell 200 y perfil de salida correcto. No se ejecutaron suite global ni pruebas V1. El caso temporal de **500 piezas** continúa fuera de esta aceptación, sin cambio de umbral ni declaración de rendimiento resuelto.

**Límites:** el contraste visual/métrico cubre estas fixtures y la copia actual; no certifica PDF/X, CTP, gestión de color, análisis de tinta en bordes ni todas las combinaciones industriales. La cobertura física declarada no prueba diseño útil en cada borde. La copia y artefactos QA son recuperables e independientes del original; el rollback de esta entrega consiste en retirar la regresión y artefactos de QA, sin migración ni cambio de código productivo.

## Forma de trabajo y cierre

- Mantener código de producto propio V2; no arreglarlo mediante motores compartidos con V1.
- Preservar archivos originales, jobs del usuario, geometría, guardado e historial.
- Probar cada entrega en proporción al cambio, empezando por regresiones focalizadas.
- Al finalizar cada entrega, actualizar aquí su estado a **Completado**, fecha, archivos/responsabilidades, pruebas realmente ejecutadas, resultado y límites. Registrar también una entrada en 41 con enlace a este documento.
- No marcar entregas futuras como completadas por cobertura parcial. No hacer commit/push sin nueva petición explícita.
- Rollback de esta primera entrega: revertir sus cambios de código; no requiere migrar layouts. Los informes son artefactos derivados y deben regenerarse con la política vigente.

## Evidencia de entregas

### Entrega 1 — Completado — 2026-09-27

**Base:** árbol limpio en `69b197c`, rama `codex/editor-offset-v2-stabilization`. Implementación autorizada expresamente; sin commit/push en esta intervención.

**Cambios y responsabilidades:**

- `domain/preflight_contract.py`: la severidad describe la incidencia; `blocks` determina su efecto por operación. Una función propia V2 se usa tanto al decidir como al validar el informe. Se rechazan operaciones desconocidas y decisiones que omiten una advertencia bloqueante. Política pasa de 2 a 3 y capacidades nativas de 4 a 5; `consume` rechaza informes de versiones anteriores. No cambia el schema de Layout ni el formato del informe.
- `application/preflight_service.py`: `BLEED_OUTSIDE_PRINTABLE` y `BLEED_OVERLAP` ya bloquean PDF/CTP, conservando Preview para inspección. Una advertencia con `blocks=[]` sigue sin bloquear. Se conservan todos los motivos aplicables: informe incompleto, hallazgos y gate desactivado, en lugar de ocultar los últimos por precedencia.
- `domain/preview_policy.py`, `application/native_output_capabilities.py` y `application/preview_service.py`: cálculo único de dimensiones redondeadas del bitmap y presupuesto de 24.000.000 píxeles. El preflight emite `PREVIEW_RESOURCE_LIMIT` con resolución, dimensiones y orientación para reducir dpi. Bloquea únicamente Preview. El renderer conserva una defensa equivalente incluso para llamadas internas sin preflight. No baja resolución silenciosamente ni limita por este motivo el PDF vectorial.
- Regresiones en `tests/editor_offset_v2/test_preflight_decisions_v2.py` y `tests/playwright/test_editor_offset_v2_output_integration.py`. No se modificaron JS, template, CSS, originales, motores compartidos ni el compositor PDF.

**Evidencia automatizada:**

| Comprobación | Resultado |
|---|---|
| Base: preflight y seguridad de salida existentes | 20 passed. |
| Nuevas regresiones antes de corregir | 7 failed y 1 passed: reproducen bloqueos ignorados, falta de presupuesto previo, ocultación del gate y endurecimientos del informe aún ausentes. |
| Primer grupo corregido: preflight nuevo/existente, seguridad, Preview, PDF y compositor nativo | 137 passed, 35,60 s. Incluye marcas con sangrado cero como aviso no bloqueante. |
| Casos finales de decisiones (12) y aceptación operativa (14) | 26 passed, 3 deselected, 16,03 s. Incluye límites por redondeo, rechazo antes de composición, renderer sin preflight, informe adulterado/obsoleto, persistencia intacta, recursos, concurrencia y fuentes multipágina. Ocho casos se repiten respecto al grupo anterior; no sumar los conteos como pruebas distintas. |
| Navegador: archivo completo de integración de salida | 6 passed, 42,58 s. Caso nuevo: Preview a 300 dpi bloqueada en preflight sin petición de render, descarga PDF a 300 dpi, Preview a 150 dpi, layout/revisión intactos y sin errores JS. También pasan paridad visual de transformaciones y descarga/reintento/resultado obsoleto. |
| Whitespace | `git diff --check` correcto. |

Los tres casos excluidos corresponden a carga de 14/100/500 piezas. No se repitió el benchmark de 500 piezas ni se declara resuelto su límite temporal registrado en 41. No se ejecutaron suite global, V1, suite Python V2 completa ni suite Node (sin cambios frontend). Las ejecuciones Python/navegador mostraron cinco avisos de deprecación PyMuPDF/SWIG.

**Copia del montaje del usuario:** `.codex-runtime/salida43-entrega1-wdqcyrqm/`, evidencia en `evidence.json`, PDF en `montaje.pdf`, raster de inspección en `montaje.png` y Preview en `preview.png`. Job original revisión 39, pliego 700 × 700, cuatro piezas, MediaBox/páginas 1 y 2/sangrado 3 mm preservados:

- Sin espejo: permanecen las cuatro incidencias reales de sangrado faltante. Esta entrega no autoriza espejo automáticamente.
- Con espejo y 300 dpi: preflight bloquea solo Preview por presupuesto; la petición directa de Preview devuelve 422 `PREFLIGHT_BLOCKED`; PDF genera una página 700 × 700 y conserva 6.396 caracteres de texto.
- Con espejo y 150 dpi: preflight sin incidencias, Preview HTTP 200.
- Raster del PDF a 60 dpi idéntico píxel a píxel al PDF de la auditoría anterior con espejo; inspección visual confirma las cuatro piezas. Layout original, layout de la copia y hash del PDF original permanecen sin cambios.

**Flask habitual:** reinicio controlado mediante `editor-offset-local-qa` para cargar Python nuevo, conservando la configuración anterior. Se verificó y detuvo exclusivamente PID 11896; nuevo PID 8692. `/` y `/editor_offset_visual_v2` HTTP 200 al primer intento conjunto posterior al arranque. V2=1, dev tools=0; Preview/PDF siguen desactivados. Una petición real de preflight confirmó política 3/capacidades 5, el límite de Preview y el gate desactivado como motivos separados. Revisión 39/hash del layout original verificados nuevamente. El preflight publica un informe derivado, sin editar el montaje.

**Límites y siguiente alcance:** 2–5 permanecen pendientes. La presentación visual de severidades/motivos, el diagnóstico legacy y la agrupación por operación se revisarán en 2: no se confunde la corrección de decisiones backend con ese rediseño. El permiso de espejo sigue temporal hasta 3. La activación habitual sigue pendiente de 4. No se certifican PDF/X, CTP ni todas las combinaciones industriales; no se amplió la política de PDF raster, caras o fuentes. La entrega 5 conserva su verificación integral propia.

### Entrega 2 — Completado — 2026-09-27

**Base y alcance:** árbol limpio en `5aa9b58`, misma rama. Frontend propio V2, pruebas y trazabilidad. Sin cambios de Python de producto, Layout/schema, fuentes, compositor, persistencia ni flags del servidor. Sin commit/push en esta intervención.

**Implementación:**

- «Validar» abre directamente «Comprobar salida · Preflight V2». Se eliminó el panel de compatibilidad legacy, su listener, método de consulta en el cliente JS, mensajes de salida temporal y estado duplicado. Se corrigió la referencia accesible de la pestaña Validar. La ruta backend histórica `/output-capabilities` se conserva para consumidores explícitos; la UI habitual ya no la invoca. Esto no declara independencia total del arranque ni elimina toda la deuda legacy backend.
- «Salida» ofrece el mismo «Comprobar salida», registrado como acción `output.preflight`. Validación y generación comparten análisis y representación del informe nativo. El resumen incluye cara, dpi y permiso de espejo, junto a decisiones separadas de Preview/PDF. CTP pendiente no convierte una salida nativa válida en un error. Las advertencias que bloquean PDF sí producen estado de bloqueo.
- Los hallazgos se agrupan por trabajo, archivo, página y operaciones afectadas. Las referencias faltantes se resuelven con los slots del layout comprobado, de modo que las páginas 1 y 2 de un mismo PDF no se mezclan. Se muestran nombre de trabajo, página, cantidad de piezas y orientación para corregir. Códigos, paths e IDs quedan en «Detalles técnicos». No se deducen los bloqueos de otros hallazgos con el mismo código.
- La disponibilidad del servidor, los problemas del montaje y el fallo al comprobar/generar tienen mensajes distintos. Al generar una operación se muestran sus hallazgos relevantes y avisos no bloqueantes; un problema exclusivo de Preview no se presenta como error del PDF.
- Un informe vigente bloquea únicamente los botones de las operaciones afectadas. Cambiar opciones/montaje invalida el diagnóstico, y cualquier generación vuelve a ejecutar preflight antes de pedir el archivo. Se contrastan job, revisión, versión de cambios, opciones, contador de petición, guardado y sesión de puntero. Respuestas tardías tras cambios, conflictos, undo/redo, actualización externa o cierre del controlador no se publican como autorizaciones actuales.
- `output_panel.js` concentra este recorrido; `dom_refs.js`, `command_registry.js`, `api_client.js`, template y CSS conectan/representan los controles. `bootstrap.js` sigue componiendo el mismo controlador, sin cambios necesarios. Las pruebas anteriores del puente visible se migraron a los controles e informes nativos conservando las comprobaciones de revisiones, selección, agrupación, navegación y estado no persistente.

**QA interactiva:** `editor-offset-local-qa` confirmó raíz y V2 HTTP 200 al primer intento, sin reiniciar ni duplicar el servidor. Navegador integrado mediante CUA, pestaña de prueba separada del usuario, job original revisión 39. «Validar» y «Salida» muestran dos grupos de sangrado faltante, uno por página y dos piezas por grupo; muestran por separado los flags desactivados. Sin errores/warnings en consola consultada, sin mensajes TrimBox/página 1 del puente antiguo. Se inspeccionaron capturas desktop y compacta (900 × 900) del caso sintético de dos páginas MediaBox. No se modificó el montaje del usuario; hash de layout y PDF original verificados intactos.

**Regresiones añadidas:** agrupación con operaciones/páginas distintas, advertencias bloqueantes, CTP pendiente, respuestas tardías, cambio de revisión, selección temporal, generación que revalida y reintento de red. Caso navegador real con dos páginas MediaBox: cuatro piezas, falta de sangrado agrupada por trabajo/página, espejo explícito, descarga PDF con dos copias de cada página, cambio de dpi durante la respuesta y layout/revisión conservados. Se comprueba que no haya solicitudes a `/output-capabilities` ni el control legacy en DOM.

**Resultados de cierre:**

| Comprobación | Resultado |
|---|---|
| Node V2 completo | **161 passed**, 1,54 s. Incluye 15 pruebas nuevas del diagnóstico y migración de pruebas anteriores de agrupación/vigencia. |
| Playwright: edición, caracterización UX e integración de salida | **29 passed**, 166,28 s; cinco avisos de deprecación PyMuPDF/SWIG. Incluye navegación, guardado, revisiones, historial, bloqueo de Preview por presupuesto, descarga y el caso multipágina nativo nuevo. |
| Sintaxis | Los cuatro JS de producto modificados pasan `node --check`. |
| Whitespace | `git diff --check` correcto. |
| Preservación del original | Layout SHA256 `63011552f3e4b2fb4a0ed54de3e379be0b7d07b54d00c112b27f7bc0072fbff1`; PDF SHA256 `14e534d2482e463596e64ab5045c3a86f4c3d10ab2b0be087bbd174ba7035243`, ambos iguales a la auditoría. |

Los primeros recorridos detectaron expectativas obsoletas en tests (panel antes cerrado, GET de compatibilidad, textos antiguos), una variable mal nombrada al migrar el fixture de agrupación y un montaje sintético cuyo giro de Repeat no coincidía con sus posiciones de prueba. Se corrigieron las expectativas al comportamiento nativo y se fijó giro 0 en ese fixture, sin relajar bloqueos ni alterar el motor. También se precisó el mensaje de informe desactualizado: solo pide guardar cuando realmente hay cambios pendientes. Las repeticiones focalizadas pasaron y luego se ejecutó el grupo completo anterior con éxito.

Capturas inspeccionadas y PDF sintético conservados en `.codex-runtime/salida43-entrega2-dde1opn2/`: `native-diagnosis-desktop.png`, `native-diagnosis-compact.png` y `native-pages.pdf`. La prueba comprueba el texto de las dos copias de cada página en el PDF. Para «Ambas caras», el resumen exige elegir Frente o Dorso si se desea Preview y conserva la disponibilidad de PDF por separado; cubierto por test Node.

Se utilizó la habilidad de pruebas de frontend y CUA para la comprobación interactiva; la regresión automatizada usa el Playwright existente del repositorio con servidores/jobs temporales. No se ejecutaron suite global, V1, suite Python V2 completa ni el benchmark de 500 piezas: no hay cambio backend productivo en esta entrega. El servidor habitual no se reinició; se verificó HTTP y se recargó la pestaña de QA para cargar template/JS nuevos.

**Límites:** permiso de espejo aún temporal y cajas en preparación sin cambios (entrega 3); activación habitual pendiente de 4. No se cambian políticas físicas del preflight, PDF/X, CTP, geometría ni rendimiento de 500 piezas. El puente histórico backend se conserva fuera del flujo habitual.

### Entrega 3 — Completado — 2026-09-27

**Base y autorización:** árbol limpio en `374f048`, rama actual. Implementación solicitada expresamente. Código propio V2, pruebas y registro en 41/43; sin commit/push. No se modifica código de producto V1 ni se introducen motores compartidos.

**Preparación:**

- Una y varias páginas usan el mismo borrador: tamaño detectado de la fuente seleccionada, tamaño final, cantidad, sangrado y decisión del trabajo. MediaBox/CropBox/TrimBox/BleedBox quedan bajo «Opciones avanzadas del PDF». Cajas ausentes se rotulan como no disponibles y no se fabrican; una asignación masiva inválida sigue impidiendo crear el lote parcialmente.
- La cobertura declarada se mide por el menor margen de los cuatro bordes, limitado por MediaBox y BleedBox explícitas. Se comparte la regla Python/JS mediante fixtures, con tolerancia de 0,001 mm, orígenes desplazados, cajas ausentes, borde limitante y cajas inconsistentes. La medida acredita extensión física declarada, **no demuestra que haya tinta/diseño útil hasta cada borde**. Con cobertura suficiente se pide comprobación visual; cuando falta se muestran las opciones de otro PDF, cambiar milímetros o autorizar espejo.
- «Usar otro PDF» lleva al selector de archivos; durante edición se pide cerrar el borrador o crear una variante para preservar el trabajo existente. «Cambiar sangrado» enfoca el valor; si el trabajo ya tiene piezas, informa que los milímetros requieren variante. No sustituye fuentes ni cambia tamaños guardados automáticamente.
- «Aplicar a seleccionadas» incluye decisión de sangrado, con selección independiente de cantidades y milímetros. Cada página guarda su propio trabajo. Variantes nuevas parten de una decisión explícita; el trabajo original se conserva. Las tarjetas muestran la decisión guardada separada de cantidades/medidas. Al editar/configurar una página se desplaza el panel al formulario para hacerlo visible.
- Tamaño final distinto del detectado conserva el comportamiento anterior y ahora muestra su limitación: la salida exige dimensiones coincidentes; cambiar ese valor no escala el PDF. Escalado/resize no se implementan en esta entrega.

**Contrato y compatibilidad ejecutable:**

| Campo/valor | Significado |
|---|---|
| `works[].bleed_strategy = "source_only"` | Utiliza únicamente sangrado acreditado por el archivo. Si no alcanza, bloquea la salida que necesita ese contenido; el operador debe corregir el archivo/milímetros o cambiar expresamente la decisión. |
| `"mirror_if_missing"` | Conserva primero el sangrado físico utilizable. Solo si falta autoriza bandas generadas por espejo. |
| Campo ausente | Trabajo anterior. Conserva el permiso temporal `allow_mirror_bleed` de la petición de salida. La UI lo identifica; no se agrega el campo al abrir, guardar o renombrar. Elegir una decisión en Preparar lo incorpora mediante comando reversible. |

Campo **opcional**, sin cambiar `layout_schema_version = 2`. Schema JSON y validador Python coordinados: rechazan null, booleanos, estructuras y valores desconocidos. `createWorkFromSource`, preparación y `UpdateWorkCommand` transportan/validan el campo; antes/after y undo/redo conservan incluso su ausencia. Fixtures antiguos permanecen válidos y cubren compatibilidad; los nuevos fixtures ejercitan cobertura y los tests serializan trabajos nuevos.

La decisión puede editarse en trabajos colocados sin cambiar geometría, fuentes ni transformaciones de sus slots; afecta a todos los slots vinculados al trabajo. Los locks de contenido en piezas con sangrado bloquean el cambio. Cambios de milímetros, fuente o tamaño de un trabajo colocado siguen exigiendo variante. Las mutaciones siguen pasando por acciones/comandos; guardado optimista, revisión e invalidación de diagnóstico/Repeat se conservan.

**Resolución común y salida:**

- `domain/work_bleed.py` y `static/js/editor_offset_v2/work_bleed.js` resuelven autorización y cobertura. La preparación física `prepared_pdf_source.py` utiliza esa misma medida. `PreviewService._prepared_slot` resuelve el trabajo desde el snapshot y hace prevalecer su decisión sobre el permiso global; el índice se construye una vez por snapshot. Preflight, Preview y PDF nativo consumen esa representación. Dos trabajos con la misma fuente y estrategias distintas no comparten una autorización por caché.
- `canvas_renderer.js` envía la decisión efectiva y la estrategia al servicio artwork, incluida la decisión local antes de guardar; su caché URL cambia al modificarla. Artwork conserva el fallback de trim con margen descubierto cuando falta sangrado y no hay autorización. No reutiliza un derivado generado para dibujar ese fallback. El SVG distingue origen `source`, `generated-mirror`, `missing`, `derived` o `none` como evidencia; el aviso legible aparece en preparación/preflight.
- La materialización desde el inspector utiliza la misma decisión; la casilla queda como indicador, con referencia a Preparar o al permiso temporal de Salida para trabajos anteriores. No hay un segundo permiso independiente que pueda contradecir el trabajo.
- Los manifiestos de derivados nuevos incluyen `bleed_origin`. Se vincula su lectura al hash del PDF derivado/original y se incluye como entrada física del snapshot. `source_only` con sangrado positivo exige origen acreditado como `source` y cobertura física suficiente, también si ya existe un derivado. Derivados anteriores sin esa procedencia se identifican como desconocidos; no se reescriben ni se inventa su origen.
- Preflight añade aviso no bloqueante `BLEED_GENERATED_BY_MIRROR` cuando se genera espejo, o `BLEED_DERIVED_REVIEW` para derivados sin procedencia acreditada. Conserva `BLEED_REQUIRES_EXPLICIT_MIRROR` como bloqueo y orienta a Preparar. Política **4**, capacidades **6**: los informes anteriores no sirven como autorizaciones actuales.
- El control general de espejo sigue disponible para **trabajos anteriores sin decisión guardada** y lo indica expresamente. No cambia ni anula `source_only`/`mirror_if_missing`. El resumen de salida ya no presenta el booleano global como permiso de todos los trabajos.
- Se corrigió el recorte de **nuevas** piezas manuales/Repeat de trabajos con estrategia explícita y sangrado positivo: nacen con `clip_to = bleed_box`, independientemente de la caja fuente. El flujo anterior creaba recorte a trim aunque se pidiera sangrado y después bloqueaba PDF. Los slots ya guardados, trabajos sin estrategia y recortes cambiados expresamente por el operador conservan su semántica. Una pieza existente recortada a trim sigue bloqueando PDF con sangrado positivo; autorizar espejo no cambia ese recorte silenciosamente.
- Cero sangrado conserva la omisión de marcas de corte y el warning cuando se solicitan. Las marcas con sangrado siguen dentro de su banda. No cambian fórmulas geométricas, cantidades, pliego ni posiciones.

**Pruebas y evidencia:**

| Comprobación | Resultado |
|---|---|
| Python V2, excluyendo `bounded_placement_load` | **619 passed, 1 skipped, 3 deselected**, 82,05 s. Skip de symlink Windows; excluidas las cargas de 14/100/500 piezas. 20 avisos de deprecación. |
| Python focalizado final: decisión por trabajo + preparación PDF | **51 passed**, 7,47 s. Incluye 18 casos de esta entrega y las pruebas de cajas/rotaciones/bandas anteriores. Dos casos de sangrado real se añadieron después de la ejecución amplia; hay pruebas repetidas entre ejecuciones. |
| Node V2 completo | **164 passed**, 1,44 s, antes del último caso de locks/colocación/compatibilidad. |
| Node focalizado final de sangrado | **4 passed**; incluye ese caso adicional. Misma fixture física Python/JS, cantidades distintas, edición colocada, undo/redo, ausencia del campo y autorización sin fuga. |
| Playwright: edición, UX, salida, Repeat nativo, preparación y sangrado por trabajo | **36 passed**, 215,39 s; cinco avisos PyMuPDF/SWIG. |
| Sintaxis / whitespace | JS modificados comprobados con `node --check`; `git diff --check` correcto. |

No sumar estos conteos como pruebas distintas. No se ejecutaron suite global ni suites Playwright V1; no se declara resuelto el rendimiento de 500 piezas.

Los nuevos casos de navegador preparan PDFs MediaBox de una y dos páginas, con cantidades 2 y 1 y sangrado 3 mm; verifican decisiones diferentes, creación atómica, undo/redo, recarga, Repeat, edición de la decisión después de colocar sin cambiar slots, autorización global incapaz de desbloquear `source_only`, canvas con espejo y descarga con las cantidades/textos de páginas correctos. Se comprueba ausencia de errores JS y desbordamiento horizontal a 1440/390 px. La prueba histórica del permiso temporal se conserva creando explícitamente un trabajo sin el campo nuevo; la de marcas 2 mm autoriza ahora el espejo en el trabajo.

Los casos Python comparan Preview con el raster del PDF píxel a píxel, comprueban dimensiones de pliego, bloqueos directos y ausencia de modificaciones del layout. La fixture de sangrado real tiene una banda magenta distinta del arte trim: ambos modos conservan el magenta, demostrando que autorizar espejo no reemplaza cobertura original. El derivado con espejo conserva su identificación y se rechaza al exigir posteriormente solo fuente. Los tests de cero bleed/marcas siguen pasando en las suites existentes.

Durante QA se corrigieron dos errores del test nuevo (ruta `references.slot_ids` y actualización de revisión al guardar), el control de tipos estructurados del campo opcional y el recorte incorrecto de nuevas piezas mencionado arriba. Las pruebas no se relajaron para eludir bloqueos. La revisión final añadió un caso de sangrado diminuto con BleedBox inconsistente: mostrar 0 mm disponibles no debe ocultar un margen negativo ni aprobarlo por tolerancia.

**Artefactos:** `.codex-runtime/salida43-entrega3/` contiene `work-bleed.pdf`, su raster `pdf-render.png`, fuente sintética y capturas `preparation-2-1440.png` / `preparation-2-390.png`. Se inspeccionaron la captura compacta y el PDF rasterizado: tres piezas, dos de página 1 y una de página 2, giros y marcas en la banda. La vista desktop también se inspeccionó con CUA en el trabajo anterior real; se abrió el editor, se cambió solo el borrador y se canceló.

**Preservación del caso del usuario:** revisión 39 y originales sin cambios. Layout SHA256 `63011552f3e4b2fb4a0ed54de3e379be0b7d07b54d00c112b27f7bc0072fbff1`; PDF SHA256 `14e534d2482e463596e64ab5045c3a86f4c3d10ab2b0be087bbd174ba7035243`. Sin nuevo historial ni errores/warnings de consola en la sesión CUA. El servidor habitual se reinició mediante la habilidad local, verificando la identidad del proceso registrado; target V2/dev tools=0. Se conservan los gates de salida previos: la activación habitual sigue siendo entrega 4. Los servidores de tests usan jobs temporales y habilitan salida para comprobarla.

**Rollback:** los trabajos antiguos sin campo son compatibles y no necesitan migración. El código anterior rechaza el campo nuevo: antes de volver a esa versión debe conservarse una copia de los layouts posteriores y restaurarse una copia compatible o hacerse una conversión explícita autorizada; no eliminar decisiones guardadas automáticamente. Revertir código no revierte slots ya aplicados, archivos PDF producidos ni ediciones de trabajos; en sesión, usar undo cuando corresponda. Informes preflight son regenerables con la versión instalada.

**Servidor al cerrar:** PID registrado 16812, tras reiniciar exclusivamente el PID 16052 verificado para cargar la última corrección de tolerancia. Comprobación posterior: `/` y `/editor_offset_visual_v2` HTTP 200 al primer intento. V2=1, dev tools=0 y gates de salida habituales conservados.

**Límites:** cobertura geométrica declarada, no análisis automático de tinta ni certificación PDF/X/CTP. No se inventan cajas ausentes, no se cambia el trim para conseguir sangrado y no se escala silenciosamente una fuente para otro tamaño final. Espejo añade bandas raster a 300 dpi, no reconstruye diseño. PDF ya materializado sin procedencia no adquiere una procedencia inventada. El backend histórico de diagnóstico/probes queda fuera del flujo habitual; no se declara independencia total del arranque. Entregas 4 y 5 pendientes.
