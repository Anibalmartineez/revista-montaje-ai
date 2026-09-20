# Preparación unificada y Repeat propio V2 — plan de implementación

Fecha del plan: 2026-09-19. Actualización: 2026-09-20. Estado: **B y C implementadas: preparación unificada, edición segura y Repeat propio; D y cierre E pendientes**.

La primera intervención cubrió la base de pruebas para Preparar, B y las guardas de vigencia de propuestas de D necesarias al editar trabajos. La segunda implementa C y adelanta únicamente el registro de versión nativa al aplicar. Se comprobó el recorrido de cuatro páginas hasta PDF, sin cerrar E: faltan la capa temporal de propuesta, el detalle por trabajo en UI y la prevalidación atómica completa de ApplyRepeat de D. Resultados y límites en [41 — Bitácora](41_TRABAJO_DIARIO_Y_BITACORA_V2.md#2026-09-20--repeat-propio-v2-entrega-c).

Las secciones siguientes conservan la especificación y la inspección del momento de planificación. Sus observaciones sobre el motor compartido y la versión fija describen la base anterior, no el código después de C. La evidencia de ejecución actual se registra en 41.

Este plan responde únicamente a la mejora acordada: preparar páginas/trabajos en una sola interfaz y distribuirlos mediante código propio V2. No reactiva roadmaps anteriores ni establece una agenda para el resto del editor. La bitácora de ejecución continúa en [41 — Trabajo diario](41_TRABAJO_DIARIO_Y_BITACORA_V2.md).

## 1. Resultado esperado

Un recorrido continuo: **subir PDF → seleccionar páginas → configurar trabajos → revisar trabajos preparados → proponer distribución → aplicar montaje**.

Preparar define qué se imprime: archivo, página, caja, tamaño final, cantidad, sangrado y giros permitidos. Imponer define dónde se coloca: pliego, márgenes, separaciones, trabajos incluidos y política de colocación. Repeat lee los trabajos guardados; no mantiene otra copia editable de sus cantidades o fuentes.

Conservar el editor existente. La mejora debe abrir jobs anteriores, respetar originales, conservar la geometría y mantener guardado optimista, undo/redo, selección, edición manual, corrección gráfica y salida. No se puede prometer ausencia absoluta de regresiones; se exige evidencia proporcional antes de dar cada cambio por terminado.

## 2. Base comprobada y superficies reutilizables

La prueba interactiva previa, registrada en 41, creó dos lotes de tres trabajos y un trabajo individual con el fixture `multipage-rotations.pdf`. Se comprobaron valores persistidos, creación duplicada, herencia poco visible de opciones, reinicio de campos al cambiar caja, sustitución de TrimBox por CropBox, undo/redo y recarga.

Lectura de código realizada para este plan:

| Superficie actual | Qué conservar / qué cambiar |
|---|---|
| `assets_panel.js` | Conservar upload y coordinación con guardado; sustituir los dos formularios de creación y sus lecturas cruzadas del DOM. |
| `commands.js` | Reutilizar `createWorkFromSource`, `createWorksFromSources`, `CreateWorksCommand` y comandos de slots. Añadir edición explícita de trabajos y revisar aplicación atómica de Repeat. |
| `store.js`, `autosave.js` | Conservar Layout, historial, revisión y CAS. Añadir estado temporal de preparación y vigencia de propuestas sin persistir borradores en Layout. |
| `repeat_panel.js` | Conservar petición/propuesta/aplicación y modos existentes; añadir distribución visible, detalle por trabajo y rechazo de resultados obsoletos. |
| `repeat_service.py` | Conservar ruta, validación de petición y revisión base. Sustituir dependencia del motor y enriquecer diagnóstico de forma coordinada. |
| `repeat_engine_adapter.py` | Extraer o adaptar validaciones propias V2; retirar import, llamadas, excepciones y traducción al motor compartido. |
| `domain/geometry.py` | Fuente para footprint, cardinales, límites y solapes; usarla como comprobación final del nuevo motor. |
| `domain/repeat_contract.py` | Conservar resultado base; coordinar metadatos transitorios nuevos con servicio, frontend y pruebas. |

Hechos adicionales observados **en código, no reproducidos en navegador en esta intervención**:

- Un slot copia fuente, trim y bleed del trabajo al crearse. No existe entre ambos una sincronización automática que haga segura cualquier edición del trabajo.
- `RepeatPanel` invalida ante cambios de sus controles, pero sus eventos de comandos/undo/redo/actualización externa solo vuelven a representar trabajos e historial. El contexto no captura revisión ni `changeVersion` para impedir aplicación obsoleta; hay que cubrir también respuestas tardías.
- `ApplyRepeatCommand` escribe `engine_version = "2.0.0-adapter"`; debe registrar correctamente el motor propio al aplicarlo, sin cambiar historia previa.
- En reemplazo, el comando elimina entradas antes de comprobar ciertas colisiones de IDs. Como el Store ejecuta sobre el layout vivo, la validación previa a toda mutación es necesaria para que un error no deje cambios parciales.
- El adaptador actual comprueba solapes con slots retenidos después de generar. El motor propio debe recibir esos obstáculos al buscar huecos.

## 3. Límites y compatibilidad

- Código nuevo de producto solo en superficies V2. No modificar `engines/step_repeat_pro_engine.py`, V1 ni servicios legacy para conseguir esta mejora.
- Mantener `layout_schema_version = 2`, IDs existentes, semántica de mm, centro trim, trim sin rotar, bleed separado y cardinales. No se prevé migración ni nuevos campos persistentes.
- Una mejora del resultado transitorio de Repeat no es un cambio de Layout. Si se añaden campos a la respuesta, actualizarlos de forma coordinada y conservar lectura de resultados/historial anteriores.
- Mantener rutas de jobs/assets/layout/repeat, almacenamiento físico y CAS. No reescribir jobs al abrirlos ni recalcular montajes automáticamente.
- No mezclar aquí controles nuevos de marcas, CTP, PDF/X, resize del slot, color, IA, nesting irregular, hybrid ni edición dúplex completa. Conservar capacidades existentes de backend por cara y no activar una UI de dorso incompleta.
- El motor nuevo será independiente de código compartido. Esto no acredita todavía independencia de **todo** V2: arranque y otras dependencias requieren su propia comprobación cuando se aborden.

## 4. Preparar: comportamiento propuesto

### Una sola área

Mostrar la biblioteca de PDFs y una superficie amplia para configurar páginas en la etapa Preparar. El centro puede mostrar esta superficie en lugar del pliego vacío; el canvas permanece disponible en las otras etapas. Evitar duplicar nodos/IDs del editor o perder su estado al navegar.

Cada fila o tarjeta muestra miniatura, selección, cantidad, caja efectiva, medidas, sangrado solicitado, giros y advertencias. Un panel «Aplicar a seleccionadas» cambia solo los campos elegidos; no sobrescribe excepciones de otras páginas accidentalmente. Una página usa exactamente el mismo flujo que varias.

Separar selección para crear de la página que se inspecciona. Mantener borradores por archivo/página durante la sesión. Cambiar archivo, miniatura o caja no debe borrar cantidades, nombres personalizados o sangrados. Tras recargar, mostrar claramente el borrador nuevo y, por separado, los trabajos guardados; no afirmar que un borrador fue guardado si no lo fue.

### Cajas, medidas y sangrado

- Al cargar, se puede sugerir una caja disponible, indicando cuál se eligió en cada página. Si el operador pide una caja inexistente, bloquear esa entrada y pedir una elección explícita; no sustituirla silenciosamente.
- Calcular las medidas con las cajas reales y rotación intrínseca del PDF. Distinguir caja fuente de tamaño final. Conservar la posibilidad actual de medida manual como opción explícita: «Según caja» / «Personalizado».
- Cambiar caja recalcula medidas automáticas; conserva cantidad y sangrado. Para medidas personalizadas, mostrar la discrepancia y permitir restaurar las medidas de caja, sin sobrescribirlas automáticamente.
- Mostrar sangrado solicitado y cobertura geométrica estimada, cuando pueda calcularse correctamente con coordenadas/cajas. Una caja grande no certifica que haya arte útil en el sangrado. El preflight de salida conserva su responsabilidad; no prometer inventar contenido ni permitir espejo implícito.
- Conservar la opción existente de usar la misma fuente para dorso como ajuste explícito avanzado, sin confundirla con preparación completa de un trabajo dúplex.

### Crear y revisar

Un único botón: «Crear N trabajos · M formas». Validar todas las entradas antes de ejecutar un solo `CreateWorksCommand`; si alguna es inválida, explicar la página y no crear un lote parcial. Tras éxito, marcar las páginas creadas y limpiar su selección de creación para reducir duplicaciones accidentales.

Una página ya utilizada puede generar otro trabajo legítimo. Ofrecer «Editar existente» o «Crear variante» con identidad nueva y nombre distinguible; no deduplicar automáticamente ni fusionar cantidades de trabajos existentes. Si hay varias variantes, permitir elegir cuál editar.

«Trabajos preparados» muestra datos persistidos: archivo/página, caja, tamaño, cantidad, bleed y giros. Conservar acceso a colocar una pieza manualmente y a sustituir la fuente de un slot, ubicados en su contexto, sin otro formulario competidor de creación.

## 5. Editar sin alterar montajes silenciosamente

Añadir un comando reversible de actualización de trabajo, con validación completa antes de modificar el layout y preservando el ID.

Política inicial propuesta para acotar el riesgo:

| Situación | Comportamiento |
|---|---|
| Trabajo sin slots en ninguna cara | Editar sus campos en una operación reversible. |
| Trabajo colocado: nombre o cantidad | Permitir edición; no añadir/eliminar slots automáticamente. Mostrar cantidad solicitada y colocada actual; invalidar la propuesta Repeat. |
| Trabajo colocado: fuente, caja, trim, sangrado, giros o dorso | No aplicar cambios estructurales al trabajo o sus slots de forma implícita. Ofrecer una variante con nuevos valores; conservar el montaje existente. |
| Sustituir piezas colocadas | Usar una acción explícita con resumen de lo que será retirado y colocado. El reemplazo Repeat actual actúa sobre los mismos IDs de trabajo: no atribuirle sustitución entre variantes que no implementa. |

La actualización estructural en sitio de un trabajo ya colocado necesita decidir cómo tratar transformaciones, fuentes sustituidas, derivados y locks por slot. Queda delimitada como decisión adicional; no ocultarla dentro de «Editar». La propuesta de variante permite preparar valores nuevos sin poner en riesgo el montaje. Esta limitación debe verse en la UI.

Preservar comportamiento manual, locks y fuentes derivadas de piezas existentes. No usar la edición de cantidad como prueba de que ya se cumplió la tirada ni modificar la política general de preflight de cantidades dentro de esta mejora.

## 6. Repeat propio V2

### Responsabilidades

Crear un módulo puro V2, nombre propuesto `editor_offset_v2/domain/repeat_packer.py`, que reciba piezas, cantidades, orientaciones admitidas, área imprimible, separaciones y obstáculos. No lee archivos, no guarda jobs y no importa motores externos del producto.

El servicio/adaptador V2 valida fuentes y configura el problema; el motor produce placements con identidad del work; el código V2 construye slots y verifica el resultado con el kernel. Mantener el punto de entrada del adaptador si ayuda a reducir cambios en sus consumidores, pero sustituir su implementación completamente: ningún wrapper hacia el motor antiguo ni fallback silencioso.

### Búsqueda de posiciones

- Trabajar con rectángulos productivos: trim más bleed, orientados con los giros permitidos. Conservar el giro exacto admitido, incluidos 180/270, aunque compartan huella con 0/90.
- Usar una búsqueda determinista y acotada de rectángulos libres/posiciones candidatas. Reutilizar huecos entre trabajos y admitir distintos works en una fila; no asignar una franja exclusiva a cada work.
- Comparar un conjunto pequeño y definido de ordenaciones/candidatos, respetando prioridad y preferencias reconocidas. No introducir optimización ilimitada ni depender del azar. Documentar desempates y límites de esfuerzo/tamaño.
- Auditar valores reales de `preferred_zone` y `preferred_flow` y sus pruebas antes del reemplazo. Mantener los casos soportados; una preferencia no interpretable debe producir un diagnóstico explícito, no ignorarse silenciosamente.
- Definir gap H/V como separación mínima entre footprints productivos; no sumarlo dos veces ni exigir un gap extra contra el borde además del margen. Comprobar la paridad con la semántica actual antes de activar el motor.
- Incorporar como obstáculos las piezas retenidas de la cara, también si están ocultas en UI. No moverlas. En modo reemplazar, retirar del problema solo los slots reemplazables del alcance elegido; si un lock impide reemplazar, bloquear la operación completa.
- Validar finalmente límites, overlaps, distancias, cardinales, fuentes, IDs y contabilidad por work. Los tests no deben exigir las posiciones defectuosas del motor previo cuando el propósito es mejorarlas.

### Cantidades y modos

- Conservar `add` como añadir la cantidad solicitada en la propuesta, además de las piezas existentes; rotular ese efecto claramente. No convertirlo implícitamente en «completar faltantes».
- Conservar `replace_work_face` para reemplazar solo los trabajos/cara incluidos, sin tocar otras caras ni trabajos.
- Sin fill: nunca sobreproducir. Sin permiso de parcialidad: no entregar una propuesta aplicable si faltan piezas.
- Con parcialidad: indicar faltantes por trabajo. Con fill: colocar primero la demanda y luego extras, sin sacrificar formas necesarias para sobreproducir otro work; indicar excesos por trabajo.
- Calcular faltantes y sobrantes por work antes de sumar: un exceso de una página no compensa la ausencia de otra.
- Mantener compatibilidad de `exact_quantity` con la semántica vigente y sus tests; no inventar una tercera política.

### Diagnóstico y procedencia

Distinguir pieza que excede el área en todos sus giros permitidos, búsqueda que no encontró distribución completa, obstáculo/lock, entrada inválida y límite de cálculo. La imposibilidad de una heurística no demuestra imposibilidad geométrica.

Conservar campos actuales de `RepeatResultV2`. Proponer metadatos transitorios aditivos para resumen por work y versión del motor; coordinar serialización y lectores. Incorporar versión del algoritmo a la identidad de operación para que distintas implementaciones no reutilicen la misma procedencia. Guardar la versión propia en `imposition.engine_version` al aplicar; no reetiquetar resultados antiguos.

## 7. Propuesta visible y vigencia

Representar la propuesta en una capa temporal del canvas, distinta del montaje guardado. En reemplazo, indicar qué piezas se sustituirán; en añadir, mostrar las retenidas. La capa no entra en `layout.slots`, autosave, exportación, selección editable ni historial hasta aplicar. Reutilizar representación/transformación geométrica V2, sin secuestrar la preview temporal de arrastre.

Mostrar totales y detalle por trabajo: solicitado, propuesto, faltante, sobrante y cantidad final proyectada. «Aplicar montaje» ejecuta un único comando reversible.

Capturar revisión guardada, `changeVersion`, job, cara, works, opciones y un identificador de petición. Invalidar al cambiar layout, configuración, modo o selección de trabajos. Al recibir una respuesta, descartar resultados de una petición anterior o de un estado que cambió durante el cálculo. Comprobar otra vez la vigencia antes de aplicar. Undo/redo, cambios externos y conflictos de guardado también deben cubrirse.

Prevalidar íntegramente `ApplyRepeatCommand` antes de borrar/agregar slots. Un error deja layout e historial sin cambios. No ampliar esto a una reescritura general del Store.

## 8. Cambios separados y verificables

Esta secuencia es para implementar la mejora solicitada; cada entrega deja el editor utilizable.

| Entrega | Archivos principales | Demostración necesaria |
|---|---|---|
| A. Base reproducible | Fixtures sintéticos y tests V2 existentes/nuevos | Caracterizar comportamientos válidos y fijar reproducciones de bugs, sin bendecir fallos como comportamiento esperado. Registrar baseline real. |
| B. Preparación unificada | Template/CSS V2, `assets_panel.js`, nuevo módulo de borradores si se justifica, `dom_refs.js`, `bootstrap.js`, `workflow_navigation.js`, `command_registry.js`, `commands.js`, `store.js` | Un flujo para una/muchas páginas; cantidades y opciones correctas; edición segura; lotes atómicos; recarga y responsive. Repeat anterior permanece funcional hasta su reemplazo verificado. |
| C. Motor propio | Nuevo `domain/repeat_packer.py`, `repeat_engine_adapter.py`, `repeat_service.py`, `repeat_contract.py` | Cuatro páginas colocadas, casos mixtos/obstáculos/políticas correctos, fuentes/cardinales válidos y dependencia del motor compartido eliminada del camino Repeat. |
| D. Propuesta integrada | `repeat_panel.js`, `store.js`, `commands.js`, `canvas_renderer.js`, registro de acciones, referencias DOM y template/CSS | Vista temporal, versión del motor, detalle por trabajo, descarte de respuestas obsoletas y aplicación atómica. |
| E. Recorrido completo | Pruebas V2, navegador, bitácora 41 | Preparar → proponer → aplicar → undo/redo → guardar → recargar → validar salida dentro de sus límites. |

Cada control nuevo usa una acción registrada; las mutaciones usan comandos. No refactorizar de paso los paneles o comandos ajenos. Revisar todos los consumidores de selectores que se muevan o retiren, incluidos los tres Playwright V2. Eliminar la creación duplicada solo cuando su capacidad esté cubierta por el flujo unificado.

## 9. Verificación y aceptación

### Casos esenciales

1. Una página y varias páginas, cantidades distintas, selección parcial y más de un PDF. Cambiar archivo/caja conserva valores del borrador correspondientes; no cruza opciones entre archivos.
2. Cajas distintas/ausentes, rotación intrínseca, medidas personalizadas y sangrado: sin sustituciones ni reinicios silenciosos. Error en una página no crea medio lote.
3. Doble clic y repetición deliberada: sin creación accidental duplicada; variante explícita disponible. Edición preserva IDs y política de slots colocados.
4. Undo/redo de creación y edición; autosave, reload y conflicto 409. Jobs anteriores abren sin migración; originales físicos conservan sus hashes.
5. Caso de cuatro páginas de 254 × 142,875 mm, pliego 700 × 500, gap 3, bleed 0: colocar cuatro sin solape. Una disposición 2×2 es evidencia de factibilidad, no la única salida aceptable. Usar copia o fixture sintético, nunca modificar el job del usuario para probar.
6. Piezas de tamaños mixtos, bleed 0/3, gaps H/V diferentes, márgenes asimétricos y giros 0/90/180/270 restringidos. Conservar identidad archivo/página/work.
7. Añadir con obstáculos; reemplazar con piezas ajenas, ocultas, otra cara y locks. Verificar modos parcial/fill y contabilidad por work, incluido exceso de un work junto con faltante de otro.
8. Cambiar un trabajo, pliego o gap después de calcular; editar durante la petición; lanzar dos peticiones; undo/redo durante cálculo. Ninguna respuesta obsoleta es aplicable.
9. Fallo al aplicar: ningún slot eliminado, agregado o historial alterado parcialmente. Propuesta repetida no se aplica dos veces.
10. Vista previa temporal no cambia el JSON guardado ni sale en PDF. Tras aplicar, conservar marcas, fuentes efectivas y transformaciones previstas; revisar PDF/Preview con un fixture exportable.
11. Perfil aceptado de carga: medir motor con muchos works/cantidades y respetar límites actuales de salida. No construir listas descontroladas ni ocultar tiempos excesivos aumentando umbrales. No ejecutar mediciones sensibles en paralelo con navegador/suites pesadas.
12. Foco/teclado y escritorio/responsive; al cambiar de etapa, mantener viewport, selección y herramientas manuales. No dejar controles duplicados ni listeners huérfanos.

### Pruebas a ejecutar durante implementación

- Node focalizado: `assets_commands_v2.test.cjs`, `repeat_commands_v2.test.cjs`, navegación y nuevos tests de borrador/controlador/vigencia. No limitarse a comprobar helpers: cubrir los listeners que hoy mezclan las opciones.
- Python focalizado: `test_repeat_engine_adapter_v2.py`, `test_repeat_service_v2.py`, nuevos tests del motor y geometría. Sustituir mocks del motor legacy por contratos V2 conservando escenarios válidos.
- Sintaxis de cada JS modificado y `git diff --check`.
- Tras integración: suite Python `tests/editor_offset_v2`, todos los Node V2 y los tres Playwright V2 de edición, UX y salida. No ejecutar UI V1 ni suite global por defecto.
- QA interactiva con la skill local en target V2, dev tools=0, jobs propios. Preflight y archivo PDF real para fixtures compatibles: dimensiones, páginas, identidad y posición de contenido. Encaje geométrico no garantiza espacio para marcas; reportar cualquier bloqueo existente sin desactivarlo silenciosamente.
- Comprobación estática y de ejecución de que el camino Repeat usa solo módulos propios V2 y bibliotecas generales. No confundir referencias históricas/tests de caracterización con dependencias productivas, ni afirmar aislamiento de la aplicación entera.

En esta intervención de planificación no se ejecutan esas suites ni se certifican resultados nuevos. Los defectos conocidos de salida pueden bloquear una aceptación PDF; reproducirlos y registrarlos, sin atribuir el bloqueo al cambio ni ampliar esta implementación sin delimitar la corrección necesaria.

## 10. Reversibilidad y cierre

Conservar el cambio documental que ya estaba pendiente en 41. Antes de implementar, comprobar el estado Git y mantener conjuntos de cambios pequeños y separables. No crear commits, ramas, merge o push por este plan; se harán cuando corresponda y estén autorizados.

Sin migración, retirar un cambio de UI o motor no debe invalidar un job existente: las posiciones ya aplicadas son slots V2 normales. El rollback del código no revierte montajes guardados; para una operación aplicada usar undo en su sesión o restauración explícita de una copia verificada. No restaurar en masa jobs del usuario.

Si falla la nueva propuesta, conservar el montaje y permitir edición manual; no caer silenciosamente en el motor compartido. Una entrega no sustituye el camino operativo hasta pasar sus comprobaciones. Si una retirada puntual del código exige conservar temporalmente el funcionamiento anterior, declarar que se recuperó el estado previo con su deuda, no presentarlo como independencia conseguida.

Cierre verificable: un solo flujo de preparación, trabajos guardados comprensibles, caso de cuatro páginas resuelto por Repeat propio, cantidades/gaps/locks correctos, propuesta vigente y reversible, jobs anteriores utilizables y evidencia registrada en 41. Las exclusiones de esta mejora y cualquier fallo no resuelto deben seguir explícitos.
