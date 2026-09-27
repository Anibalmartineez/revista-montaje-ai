# 43 — Salida PDF habitual V2: cinco entregas

Fecha de apertura: 2026-09-27.

## Acuerdo y alcance

Plan solicitado por el usuario después de auditar la salida del editor y el job `ev2_f2347e8ce720eb582054200f`. Se continúa desde el código existente. Este documento registra las cinco entregas acordadas, su propósito, aceptación y evidencia; no sustituye al código ni convierte documentos históricos en requisitos de implementación.

El usuario autorizó primero la entrega 1 y, tras guardarla en `5aa9b58`, autorizó continuar con **la entrega 2**. Las entregas 3–5 quedan pendientes. No se retoma automáticamente la entrega E del documento 42: es otro alcance.

Flujo esperado: preparar páginas/tamaño/sangrado → montar → preflight nativo V2 → Preview/PDF. La preparación decide el contenido; el montaje decide posiciones y marcas; el preflight decide qué operaciones son admisibles; el generador utiliza esas mismas decisiones; el arranque habilita las funciones habituales.

## Seguimiento

| Entrega | Problema que resuelve | Estado |
|---|---|---|
| 1. Decisiones coherentes de preflight | Bloqueos geométricos ignorados y Preview aprobada que luego supera el presupuesto de píxeles. | **Completado — 2026-09-27** |
| 2. Diagnóstico único de salida | Errores y mensajes del puente legacy confundidos con las capacidades del PDF nativo. | **Completado — 2026-09-27** |
| 3. Preparación y sangrado comprensibles | Cajas técnicas como decisión principal, sangrado faltante descubierto tarde y permiso de espejo que se pierde. | Pendiente |
| 4. Salida habilitada en el arranque habitual | Dependencia de un arranque especial de QA para usar Preview/PDF. | Pendiente |
| 5. Verificación integral | Ausencia de una comprobación conjunta del recorrido y de los archivos resultantes. | Pendiente |

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
