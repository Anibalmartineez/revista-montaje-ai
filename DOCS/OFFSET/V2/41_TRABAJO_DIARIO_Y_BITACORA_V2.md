# Editor Offset Visual V2 — nuevo punto de partida y bitácora

Fecha de apertura: 2026-09-19.

## Decisión del usuario

Continuar desde el código que ya existe, probando el editor, detectando problemas y mejorándolo en el trabajo diario. El agente conduce la investigación técnica, propone y ejecuta correcciones dentro de lo solicitado, verifica el resultado y deja registro de lo que realmente ocurrió.

Este documento inicia una nueva forma de trabajo. No establece fases, un roadmap, un orden obligatorio de defectos ni un siguiente paso predeterminado. Tampoco implica borrar o reescribir desde cero el editor existente. Las prioridades nacen del uso, de los errores reproducidos y de las necesidades que aparezcan en la sesión.

## V2 debe tener código propio e independiente

La dirección definida por el usuario es que V2 no comparta código del producto con V1 u otras superficies del repositorio. Esto incluye motores, servicios, adaptadores, reglas de negocio, frontend y persistencia. No introducir dependencias nuevas hacia módulos compartidos ni solucionar un problema V2 modificando un motor común.

Cuando una función dependa de código compartido, examinar esa dependencia y llevar la responsabilidad a una implementación propiedad de V2, con sus pruebas. Se puede aprovechar y adaptar código existente del repositorio; la versión V2 debe quedar mantenida dentro de su propia superficie y sin importar ni delegar en la implementación antigua. Un wrapper V2 alrededor de un motor compartido no acredita independencia.

Comprobar también dependencias transitivas y arranque: no afirmar independencia total por haber eliminado un único import. Las bibliotecas externas de propósito general, como Flask o las bibliotecas PDF, no son código del producto compartido con V1; esta decisión no exige reimplementarlas. La composición actual de la aplicación tampoco demuestra un arranque independiente y deberá contrastarse cuando se trabaje esa frontera.

**Estado comprobado al abrir esta bitácora:** `editor_offset_v2/infrastructure/repeat_engine_adapter.py` importa `engines.step_repeat_pro_engine` y lo utiliza. Esa dependencia contradice el objetivo de independencia y permanece sin resolver. Esta comprobación es puntual, no un inventario exhaustivo de dependencias. En esta apertura no se cambió código productivo.

## Cómo conocer el estado real

Las instrucciones actuales del usuario definen el resultado buscado. El código, el schema ejecutable, los datos y el comportamiento observado permiten determinar qué hace hoy el sistema. Las pruebas aportan evidencia dentro de su cobertura; también pueden contener expectativas obsoletas y deben revisarse cuando corresponda.

El comportamiento observado no es automáticamente correcto: un error reproducido sigue siendo un error aunque esté implementado y tenga antecedentes documentales. Evaluar los resultados contra la necesidad del operador, la integridad de sus datos y los requisitos físicos de la salida.

Los documentos anteriores siguen disponibles como referencia y memoria. No son la fuente de verdad del producto, no fijan el trabajo siguiente y no deben cargarse como lectura obligatoria para cada sesión. Consultar un antecedente concreto únicamente cuando ayude a resolver una duda actual. Sus contratos escritos describen decisiones previas que deben contrastarse con el código y la intención actual del usuario; no autorizan cambios silenciosos de formatos o geometría.

Los planes de 20, 40 y otros documentos dejan de dirigir el avance. Sus hallazgos pueden servir como pistas, pero no se heredan como una cola obligatoria ni se declaran actuales o resueltos sin comprobación. La propuesta de crear una habilidad de trazabilidad tampoco queda como tarea pendiente automática.

Este documento es la entrada al método de trabajo y a sus registros. No certifica el estado completo del editor ni reemplaza la comprobación del código.

## Trabajo diario dirigido por el agente

Partir del problema o recorrido que tenga sentido en ese momento. Probar el flujo, observar qué falla o qué dificulta trabajar y seguir la causa hasta el código responsable. Resolver decisiones técnicas rutinarias sin devolver al usuario la organización de cada paso.

Una corrección debe ser acotada y comprobable. Reproducir el problema cuando sea posible, corregirlo, comprobar el comportamiento y registrar el resultado. Para errores relevantes de geometría, persistencia o salida, conservar una regresión reproducible dentro del repositorio; no depender únicamente de archivos temporales.

Las pruebas de navegador, API, servicios y artefactos se complementan. Para un PDF, comprobar el archivo y su contenido físico/visual; un botón funcional o un HTTP 200 no demuestra una salida correcta. Al modificar una interacción, comprobar los aspectos afectados de guardado, recarga y undo/redo. La amplitud de las pruebas depende del cambio, no de una lista universal que haya que ejecutar diariamente.

Usar jobs de prueba o copias explícitas para explorar. Conservar originales, montajes del usuario y trabajo ajeno. Usar `editor-offset-local-qa` para gestionar Flask V2 cuando se necesite; las herramientas dev no arreglan la capacidad de Repeat ni sustituyen assets reales.

No exigir un plan formal ni una aprobación repetida para cada ajuste rutinario comprendido en la tarea. Si aparece una decisión de producto que no pueda inferirse, una alteración incompatible de datos o una operación destructiva, explicar la consecuencia concreta y resolver esa decisión con el usuario. Revisar el impacto inmediato no crea un roadmap.

La conducción técnica no implica trabajo programado en segundo plano ni autoriza publicación, merge, push o nuevos commits por defecto. La autorización anterior de guardar un conjunto de cambios no se extiende automáticamente a cambios futuros.

## Registro después del trabajo

Mantener aquí una bitácora breve por intervención. Documentar después de observar o cambiar; no presentar intenciones como hechos consumados. Actualizar otra referencia técnica únicamente si el cambio la afecta y resulta útil conservarla, sin sincronizar por rutina todos los documentos antiguos.

Cada entrada debe permitir entender:

- qué pidió el usuario o qué se observó;
- qué se reprodujo y en qué condiciones;
- qué cambió y en qué archivos;
- qué se verificó, con qué resultado y qué no se comprobó;
- qué quedó abierto, sin asignarle un orden obligatorio;
- el commit, si efectivamente se creó.

Usar estados explícitos: observado, reproducido, corregido y verificado, o pendiente de verificar. No dar por corregido algo porque se redactó un documento. Si una corrección se demuestra insuficiente, añadir la nueva evidencia conservando el registro anterior.

No es necesario crear un documento numerado por cada ajuste. Separar una explicación extensa solo cuando ayude a entender el trabajo, y enlazarla desde su entrada. No mantener otro mapa completo ni otro listado de prioridades en paralelo.

## Bitácora

### 2026-09-27 — Alineación de AGENTS.md con el mapa V2

**Solicitud:** revisar y actualizar `AGENTS.md` si sus instrucciones sobre V2 estuvieran desactualizadas. **Observado:** la directriz inicial ya apuntaba a esta bitácora, pero secciones inferiores exigían la lectura de 20/40, describían Repeat como dependiente del motor compartido, listaban solo parte de las rutas y pruebas, trataban el cierre de salida como futuro y proponían un roadmap. El código y el mapa 44 muestran packer/compositor V2 propios, 14 rutas, seis archivos Playwright V2 y una frontera legacy en el arranque global de `app.py`; 43 registra las cinco entregas de salida como completadas con límites explícitos.

**Cambiado:** se alineó `AGENTS.md` con 41/44/43, se actualizaron recorridos, módulos, pruebas y límites de salida, y se retiró el orden de trabajo heredado. Se conservaron las reglas de protección de datos, aislamiento V1/V2 y Git. No se modificó código productivo ni persistencia.

**Verificado:** contraste estático con `blueprint.py`, adaptador/packer Repeat, scripts de arranque, inventario Playwright y documentos 43/44; `git diff --check`. No se ejecutaron pruebas ni se inició Flask, porque el cambio es de instrucciones y documentación. Sin commit en esta intervención.

### 2026-09-27 — Mapa integral de conexiones del Editor Offset Visual V2

**Solicitud:** localizar todos los archivos y conexiones del editor V2 en el repositorio, con revisión paralela de backend, frontend y referencias externas. **Observado:** `app.py` es la entrada de registro y también carga `routes.py` legacy al iniciar Flask; el producto V2 reúne 40 Python y 2 schemas propios, un HTML, un CSS, una entrada JS y 35 módulos JS cargados por la plantilla. Hay 28 módulos de prueba Python, 18 Node y 6 Playwright V2, además de fixtures, scripts y 49 Markdown previos de V2. El flujo habitual de Repeat usa el empaquetador propio; el preflight/Preview/PDF usa servicios y compositor V2. La ruta de capacidades históricas no tiene consumidor en la UI habitual, y `artifact_lifecycle.py` no tiene invocador productivo localizado.

**Cambiado:** se añadió [44 — Mapa de conexiones](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md) con entradas HTTP, relaciones entre capas, inventario exhaustivo de archivos, persistencia, pruebas y fronteras legacy; se enlazó desde `README.md`. No se modificó código de producto, schema ni datos de jobs.

**Verificado:** búsquedas de archivos y referencias, lectura de registro, template, imports, rutas y puntos de composición; tres revisiones paralelas de solo lectura. No se inició Flask, no hubo recorrido interactivo ni se ejecutaron tests: el mapa describe conexiones estáticas y no certifica funcionamiento. No se creó commit. Queda abierta la dependencia de arranque de `app.py` respecto al registro legacy y la diferencia entre utilidades históricas presentes y rutas de producto activas; este registro no las convierte en tareas automáticas.

### 2026-09-27 — Decisión de sangrado por trabajo: entrega 3 de salida PDF habitual

**Solicitud:** implementar la preparación comprensible de una o varias páginas, con decisión de sangrado persistente y coherente entre canvas, preflight, Preview y PDF. Base limpia `374f048`; sin commit/push en esta intervención.

**Resultado:** entrega 3 **Completado** en [43 — Salida PDF habitual](43_PLAN_SALIDA_PDF_HABITUAL_V2.md). La preparación muestra tamaño detectado/final, milímetros y cobertura física declarada; las cajas quedan en opciones avanzadas. Permite subir otro archivo, ajustar el sangrado o autorizar espejo. `works[].bleed_strategy` es opcional, con `source_only` y `mirror_if_missing`; ausencia conserva el permiso temporal anterior y se muestra explícitamente, sin migrar trabajos al abrir o renombrar. Las decisiones nuevas sobreviven a guardar/recargar y undo/redo, también al editar trabajos colocados, respetando locks de contenido y conservando geometría.

**Integración:** una resolución propia V2 gobierna autorización, fuente preparada y diagnóstico. El espejo generado se avisa; los derivados nuevos registran su origen y no pueden eludir `source_only`. Nuevas colocaciones manuales/Repeat de trabajos con decisión explícita y sangrado positivo usan recorte con sangrado. Se encontró este defecto en la prueba completa: antes nacían con recorte al corte y el PDF las bloqueaba. No se cambia el recorte de slots guardados. Cero sangrado conserva la omisión de marcas y su aviso. Las bandas de espejo siguen raster a 300 dpi; el contenido central conserva el compositor existente.

**Evidencia:** Python V2 sin las tres pruebas de carga: 619 passed, 1 skipped; después, 18 pruebas focalizadas pasan e incluyen dos casos adicionales de sangrado real conservado. Node completo: 164 passed; test focalizado final: 4 passed, incluyendo un caso adicional de locks/colocación/compatibilidad. No sumar repeticiones. Playwright: 36 passed entre edición, UX, salida, Repeat nativo, preparación y nuevo flujo de sangrado; se verifica PDF descargado, cantidades 2/1, historial, recarga, políticas mezcladas y canvas. Casos Python comparan raster PDF/Preview píxel a píxel y color del sangrado físico para distinguirlo del espejo. Capturas desktop/390 px y PDF inspeccionados en `.codex-runtime/salida43-entrega3/`.

**QA local:** reinicio mediante `editor-offset-local-qa`, exclusivamente PID registrado 8692 → 16052; target V2, dev tools=0, rutas raíz/V2 HTTP 200 en el primer intento posterior. Se mantienen los gates de salida habituales anteriores. CUA verificó el trabajo del usuario revisión 39 y la selección de espejo en un borrador que se canceló; sin errores/warnings de consola y sin historial nuevo. Hashes del layout y PDF original coinciden con los registrados en entrega 2.

**Límites:** las cajas acreditan extensión física, no la presencia/calidad del diseño en todos los bordes; no se inventan cajas ni se certifica tinta útil. Tamaño personalizado distinto de la fuente se advierte y sigue bloqueado para salida; no se implementa escalado automático. Derivados anteriores sin origen quedan identificados como desconocidos y requieren revisión; elegir `source_only` exige procedencia acreditada cuando hay sangrado. Código V1, originales, geometría existente y flags habituales sin cambios. Entregas 4 y 5 pendientes; exclusiones y rollback del campo opcional en 43.

**Cierre final:** revisión de tolerancia para sangrado diminuto con BleedBox inconsistente, con fixture común Python/JS. Reejecución focalizada: 51 Python y 4 Node pasan; sintaxis JS y `git diff --check` correctos. Reinicio controlado final de PID 16052 → 16812 para cargar esa corrección; raíz y V2 HTTP 200 al primer intento posterior, mismos flags.

### 2026-09-27 — Diagnóstico nativo unificado: entrega 2 de salida PDF habitual

**Solicitud:** continuar con la entrega 2 de [43 — Salida PDF habitual V2](43_PLAN_SALIDA_PDF_HABITUAL_V2.md). Base limpia `5aa9b58`. **Entrega 2 completada**, con entregas 3–5 pendientes; sin commit/push en esta intervención.

**Corregido y verificado:** Validar y Salida usan el mismo preflight nativo. Se retiraron panel, consulta JS y mensajes de compatibilidad/salida temporal del flujo habitual. La ruta histórica backend se conserva fuera de la UI; no se declara eliminada toda la deuda legacy. Hallazgos por nombre de trabajo/página/piezas afectadas, con códigos/IDs en detalles técnicos y operaciones bloqueadas propias de cada grupo. La UI distingue función desactivada, problemas del montaje y fallo de petición; CTP pendiente no vuelve rojo un PDF admisible. Los resultados muestran sus opciones y, al generar, solo los hallazgos relevantes para esa operación.

**Vigencia:** las opciones, comandos, undo/redo, actualizaciones externas, revisiones, conflictos y puntero invalidan el informe. Una respuesta tardía no puede revalidarlo; cada generación vuelve a analizar la revisión guardada. Los botones respetan bloqueos por operación y disponibilidad del servidor. La acción nueva `output.preflight` coordina ambos botones de comprobación. Guardado/historial, Layout/schema, fuentes y compositor no cambiaron.

**Archivos:** controlador `output_panel.js`, cliente API, referencias DOM, registro de acciones, template y CSS V2; pruebas Node y los tres archivos Playwright de edición/caracterización/salida revisados y adaptados. `bootstrap.js` mantiene la composición existente. Sin cambios Python de producto ni motores compartidos.

**Evidencia:** Node V2 **161 passed**; Playwright de los tres recorridos **29 passed** en 166,28 s. Incluye dos páginas MediaBox, cuatro piezas, incidencias agrupadas, espejo explícito y PDF con dos copias de cada página; cambio de opciones durante la respuesta; 900 × 900 sin desbordamiento del panel; sin solicitudes legacy ni errores JS. Sintaxis de los cuatro JS y `git diff --check` correctos. Cinco avisos de deprecación PyMuPDF/SWIG. Fallos intermedios de adaptación de fixtures/textos y su corrección están descritos en 43; no se ocultaron bloqueos del producto para hacer pasar tests.

**QA del usuario:** skill `editor-offset-local-qa` confirmó HTTP 200 raíz/V2; sin reinicio ni cambio de flags. CUA sobre pestaña independiente del job `ev2_f2347e8ce720eb582054200f`: diagnóstico de falta de sangrado por página, dos piezas por grupo, flags desactivados explicados aparte, sin rechazos legacy de MediaBox/página 2. Revisión 39, hash del layout y hash del PDF originales intactos. Capturas y PDF sintético en `.codex-runtime/salida43-entrega2-dde1opn2/`.

**Límites:** no suite global/V1/Python V2 completo ni benchmark de 500 piezas. Espejo persistente y simplificación de cajas pendientes de 3; salida habilitada al arrancar pendiente de 4; cierre integral pendiente de 5. Esta intervención no certifica PDF/X/CTP.

### 2026-09-27 — Preflight coherente: entrega 1 de salida PDF habitual

**Solicitud:** registrar las cinco entregas propuestas y ejecutar únicamente la primera. Se creó [43 — Plan de salida PDF habitual V2](43_PLAN_SALIDA_PDF_HABITUAL_V2.md), con problema resuelto, implementación prevista, aceptación y estado por entrega. **Entrega 1 completada; 2–5 pendientes.** No reanuda automáticamente E del documento 42. Base limpia `69b197c`; sin commit/push en esta intervención.

**Corregido y verificado:** servicio y contrato del informe respetan `blocks` por operación independientemente de `severity`. Sangrado fuera del área imprimible o superpuesto bloquea PDF/CTP; Preview sigue disponible para inspeccionar. Advertencias sin bloqueo, como marcas omitidas con sangrado cero, conservan su comportamiento. Los motivos de hallazgos y gate deshabilitado se informan conjuntamente. Política 3/capacidades 5 impiden consumir informes antiguos como autorización actual.

El cálculo redondeado del bitmap y presupuesto de 24 millones de píxeles reside en un módulo propio V2, usado por preflight y renderer de Preview. `PREVIEW_RESOURCE_LIMIT` aparece antes de renderizar y afecta solamente Preview; el PDF vectorial no se bloquea por ese límite del pliego. No se modifican Layout/schema, fuentes originales, geometría, frontend, compositor ni motores compartidos.

**Validación:** base focalizada 20 passed; regresiones nuevas antes de corregir 7 failed/1 passed; grupo de preflight/seguridad/Preview/PDF/compositor 137 passed; grupo final de 12 casos de decisiones y 14 de aceptación 26 passed/3 deselected (conteos parcialmente repetidos). Integración de salida en navegador: 6 passed, incluyendo rechazo a 300 dpi antes de pedir Preview, PDF descargable a 300 dpi y Preview a 150 dpi, sin cambiar la revisión. `git diff --check` correcto. Cinco avisos de deprecación PyMuPDF/SWIG. No se ejecutaron V1, suite global, Python V2 completo ni Node; se excluyeron cargas 14/100/500 y no se declara corregido el benchmark temporal de 500 piezas.

**Caso del usuario:** copia aislada del job `ev2_f2347e8ce720eb582054200f`, revisión 39, en `.codex-runtime/salida43-entrega1-wdqcyrqm/`. Sin espejo conserva cuatro bloqueos de sangrado; con espejo/300 dpi bloquea Preview, permite PDF 700 × 700 con las cuatro piezas; con espejo/150 dpi Preview correcta. PDF inspeccionado visualmente y raster a 60 dpi idéntico al de la auditoría previa. Originales y layouts sin cambios. Detalles y evidencia en 43.

**Servidor:** skill `editor-offset-local-qa`, target V2; reinicio solo del proceso registrado/verificado para cargar el backend. PID 11896 → 8692; raíz y V2 HTTP 200 tras iniciar. Dev tools=0 y flags Preview/PDF conservados apagados, como corresponde antes de entrega 4. Preflight real confirmó nuevas versiones y motivos; la revisión/hash del montaje original siguen intactos. Los mensajes/presentación legacy quedan para 2 y la configuración persistente del sangrado para 3.

### 2026-09-19 — Apertura del nuevo método

- **Solicitud:** trabajar día a día desde el código existente, con conducción técnica del agente, independencia de V2, pruebas y registro posterior; abandonar los planes anteriores como guía obligatoria.
- **Comprobado:** el árbol de trabajo estaba limpio al comenzar. Repeat V2 mantiene un import y llamadas al motor compartido en `repeat_engine_adapter.py`. No se ejecutó una auditoría completa de dependencias ni se reevaluaron los defectos del documento 40.
- **Cambios documentales:** creado este documento; ajustadas las entradas de `AGENTS.md` y `README.md` para que las sesiones futuras usen esta directriz. Se conservan los documentos anteriores.
- **Resultado:** nueva orientación registrada. No se modificaron Python, JavaScript, HTML, CSS, schema ni jobs. No se creó una habilidad, no se reinició Flask y no se ejecutaron suites del editor en esta intervención documental.
- **Validación documental:** comprobados los enlaces locales y el balance de bloques de código de los tres documentos afectados; `git diff --check` sin errores de whitespace. Sin commit en esta intervención.
- **Abierto:** la independencia de código es un requisito adoptado, todavía no una propiedad demostrada del sistema. El trabajo funcional se elegirá durante el uso y la investigación, sin una secuencia impuesta por esta bitácora.

### 2026-09-19 — Prueba real de preparación multipágina y propuesta de unificación

**Solicitud:** comprobar en el sistema la duplicación entre «Páginas del PDF» y «Fuente y work», y después proponer una experiencia unificada. Alcance: prueba y propuesta; sin implementar cambios de interfaz.

**Entorno y evidencia:** `check_flask.py --target v2` comprobó `/` y `/editor_offset_visual_v2` con HTTP 200 en el primer intento. El servidor ya estaba activo; no se inició otro ni se reinició. Registro de la skill: target V2, enabled=1, dev tools=0. Recorrido interactivo en Chrome, screenshots y lectura del layout persistido. Se creó el job de prueba `ev2_e949f202f1f39e2e1317cd6f` y se subió `tests/fixtures/editor_offset_v2/multipage-rotations.pdf` mediante el selector de archivos. No se modificó el montaje del usuario.

Se contrastó el comportamiento con `static/js/editor_offset_v2/assets_panel.js`, en `renderSourceControls`, `createWork` y `createPageWorks`. No se tomó un plan antiguo como especificación del flujo.

**Resultados reproducidos:**

| Prueba | Resultado comprobado |
|---|---|
| Seleccionar las tres páginas y cantidades 2, 3 y 4; crear works seleccionados | Se crean tres trabajos con esas cantidades, bleed 0 y giros 0/90/180/270. No se crean slots. |
| Caja visible TrimBox al crear ese lote | Las páginas 1 y 3 usan trim; la 2 usa crop, porque no dispone de trim. La tabla de páginas no muestra la sustitución ni la caja efectiva por página. |
| Introducir bleed 3 y cantidad individual 9; después cambiar a MediaBox | El formulario restablece bleed a 0 y cantidad a 1. El código también restablece nombre y dimensiones cuando reinicia los valores de fuente. |
| Con MediaBox ya seleccionada, introducir de nuevo bleed 3 y cantidad 9, dejar solo giro 0; crear el lote otra vez | Se añaden otros tres trabajos con MediaBox, bleed 3 y giro 0. Conservan cantidades por página 2/3/4; la cantidad individual 9 no se aplica al lote. |
| Comparar los dos lotes | Existen seis trabajos con nombres repetidos por página, aunque sus cajas, dimensiones, sangrado y giros son distintos. La segunda creación no actualiza los anteriores ni muestra advertencia de repetición. |
| Crear mediante «Crear work real», con nombre «QA individual página 1» | Añade un séptimo trabajo: página 1, MediaBox, cantidad 9, bleed 3, giro 0. Confirma que el formulario inferior también crea trabajos. |
| Deshacer dos veces y rehacer dos veces | Retira/restaura el trabajo individual y el lote completo, respectivamente. |
| Autosave y recarga | Se conservan los siete trabajos, revisión 9, cero slots. El planificador vuelve a cantidades 1 y solo página 1 seleccionada; el formulario vuelve a valores iniciales. Son borradores de creación, no una vista de los valores persistidos. |
| Consola del navegador | Sin errores/warnings en los registros consultados de la pestaña de prueba. |

**Conclusión:** no falta completamente el soporte de sangrado en la creación multipágina. Existe una dependencia poco visible: el botón superior lee caja, bleed, giros y opción de dorso del formulario inferior, mientras ignora su cantidad individual, nombre y medidas manuales y calcula los propios por página. La herencia de caja/bleed/giros y la separación de cantidades se comprobaron en ejecución; la lectura de dorso y el cálculo de nombre/medidas se constataron en código, sin probar todas sus variantes.

Visualmente, la preparación se concentra en una columna estrecha con scroll. El botón del lote aparece antes que las opciones que utiliza. El centro conserva un pliego vacío y el panel derecho solo indica crear works a la izquierda. «Fuente y work» mezcla creación individual, selección de trabajos existentes, creación de slots y sustitución de fuente. Todo ello dificulta distinguir preparar, crear y editar.

**Propuesta basada en esta prueba, todavía sin implementar:**

- Usar la etapa Preparar para un área amplia de páginas y configuración, con un único flujo para una o varias páginas. La biblioteca muestra el archivo una sola vez; la selección para preparar y la inspección de una miniatura deben distinguirse.
- Mostrar una fila o tarjeta por página con miniatura, selección, cantidad, caja efectiva, tamaño final, sangrado solicitado y estado. Presentar controles comunes «Aplicar a seleccionadas» y permitir excepciones por página.
- Mantener cantidad y sangrado al cambiar de caja; recalcular solamente las medidas afectadas e indicar el cambio. Si una caja elegida no existe en una página, mostrar el problema y permitir elegir explícitamente otra; no sustituirla silenciosamente.
- Separar tamaño de la caja fuente y tamaño final cuando se permita edición manual. Indicar si el sangrado solicitado dispone de cobertura en la fuente; escribir 3 mm no crea contenido exterior automáticamente. No prometer validación física completa solo por comparar tamaños de cajas.
- Ofrecer un único botón «Crear trabajos»: por ejemplo, «Crear 3 trabajos · 9 formas». Mostrar el resumen efectivo antes de crear. Una nueva creación de páginas ya utilizadas debe permitir una variante explícita o dirigir a editar el trabajo existente, sin impedir usos legítimos de una misma página.
- Debajo, mostrar «Trabajos preparados» con sus valores guardados y acciones diferenciadas para editar, duplicar como variante y colocar. Editar debe conservar identidad y resolver de forma explícita su efecto sobre slots existentes; no cambiar un montaje silenciosamente.
- Conservar colocación manual y sustitución de fuente, ubicadas con los trabajos o slots correspondientes, sin mantener un segundo formulario competidor de creación. Usar «Trabajo», «Archivo PDF», «Sangrado» y «Cantidad de formas» como lenguaje visible.
- Mantener creación en lote reversible, autosave y recarga. Los borradores nuevos y los trabajos guardados deben verse distintos. La implementación de esta mejora debe permanecer en código propio V2, sin introducir reutilización de motores compartidos.

**Límites y estado:** hallazgos reproducidos; propuesta pendiente de implementación. No se probaron Repeat, generación PDF, dorso, varias cargas simultáneas ni todas las combinaciones de cajas en este recorrido. No se ejecutó la suite general. Un primer intento de selector de archivos falló en la herramienta de navegador; se recuperó con una pestaña nueva y la carga UI posterior funcionó. No se atribuye ese incidente al editor. Se conserva el job de QA para inspección. Solo se modifica esta bitácora; sin cambios productivos ni commit.

### 2026-09-19 — Plan solicitado para Preparar unificado y Repeat propio

- **Solicitud:** preparar cómo implementar ambas mejoras sobre el código existente preservando su funcionamiento. Esta petición concreta autoriza planificar; no convierte los roadmaps anteriores en agenda ni inicia la implementación.
- **Inspección:** panel de assets, helpers/comandos de trabajos y Repeat, Store, panel Repeat, servicio/adaptador/resultado Python, geometría y referencias de integración/tests. Se conserva la entrada anterior de QA que ya estaba sin commit.
- **Resultado documental:** creado [42 — Plan de preparación unificada y Repeat propio](42_PLAN_PREPARACION_UNIFICADA_Y_REPEAT_PROPIO_V2.md), con archivos afectados, política propuesta de edición segura, motor V2 sin dependencia compartida, vigencia de propuestas, aceptación y rollback.
- **Riesgos identificados en código:** los slots copian datos del work; editarlo no los sincroniza automáticamente. La aplicación de Repeat requiere guardas de estado/revisión y respuestas tardías; su comando debe validar completamente antes de retirar slots. Son puntos a cubrir en implementación, sin reproducción adicional en navegador en esta sesión.
- **Estado:** plan preparado, código productivo intacto. No se ejecutaron suites, no se reinició Flask y no se hizo commit. La independencia de Repeat y la interfaz unificada siguen pendientes de implementación.


### 2026-09-20 — Primera entrega de preparación unificada

**Solicitud y alcance:** avanzar con la primera entrega de 42 sobre el código existente: Preparar unificado, pruebas de protección y edición segura de trabajos. Implementación exclusivamente en superficies V2. La rama comenzó limpia en `6f5a08c`; no se creó commit en esta intervención.

**Cambios implementados:**

- Preparar ocupa el centro del editor con páginas y configuración; el canvas conserva su instancia y vuelve a mostrarse en las otras etapas. Se retiran los dos caminos competidores de creación. Una o varias páginas pasan por «Crear N trabajos · M formas» y un único comando reversible.
- `preparation.js` mantiene borradores temporales por archivo/página. Se conservan nombre, cantidad, sangrado y giros al cambiar caja o archivo. «Según caja» recalcula medidas considerando el giro intrínseco; «Personalizado» conserva las medidas introducidas. Estos borradores no se guardan en Layout.
- Cada página muestra caja efectiva, medidas, cantidad, sangrado y giros. «Aplicar a seleccionadas» copia únicamente los campos marcados. Una caja solicitada inexistente se muestra y bloquea el lote; no se sustituye silenciosamente. Los errores de preparación identifican la página. El lote se valida completo antes de mutar el layout.
- Los trabajos persistidos aparecen separados de los borradores. Se evita recrear una página ya utilizada sin optar por una variante. Las variantes reciben ID nuevo y un nombre diferenciado; el original se conserva.
- `UpdateWorkCommand` permite editar trabajos sin slots y limita los ya colocados a nombre/cantidad. La guarda inspecciona todas las caras, no solamente la selección actual. No propaga medidas, fuentes o sangrado a slots existentes. Conserva referencias de dorso distintas si no se cambia esa opción; la opción de misma fuente en dorso sigue al frente cuando se edita un trabajo sin slots.
- Colocar una pieza y sustituir una fuente continúan accesibles en Fuentes. No existe un segundo formulario de creación. Las acciones de preparación pasan por el registro de acciones V2.
- Repeat invalida propuestas ante comandos, undo/redo y actualización externa. Captura revisión, versión local y secuencia de petición para descartar resultados tardíos y rechazar una aplicación obsoleta. No cambia su algoritmo ni el adaptador compartido.
- Navegación y responsive: Preparar se muestra directamente en el centro; Fuentes continúa como panel desplegable en pantallas compactas. El inspector lateral no se abre sobre la nueva preparación. Se ajustan formulario y cabecera estrecha para evitar superposición de controles.

**Superficies:** template/CSS V2; `preparation.js`, `assets_panel.js`, `commands.js`, `command_registry.js`, `dom_refs.js`, `bootstrap.js`, `workflow_navigation.js`, `repeat_panel.js`; pruebas JavaScript y Playwright V2. No se modifican Python productivo, schema, persistencia, motores compartidos ni V1.

**Validación y evidencia:**

| Comprobación | Resultado |
|---|---|
| Baseline focalizado anterior a cambios: assets commands, Repeat commands y workflow navigation | 19 pruebas Node aprobadas. No constituye baseline de todo el repositorio. |
| Suite JavaScript V2 final | 138 aprobadas, incluidas 14 pruebas nuevas de preparación, edición y vigencia de Repeat. |
| Python focalizado: frontend placeholder, rutas, contrato Layout y rutas de assets | 114 aprobadas, 1 omitida al no poder crear symlinks de prueba en Windows. Warnings de dependencias; no fallos. |
| Tres suites Playwright V2 existentes más la nueva de preparación | 29 aprobadas. Incluyen edición manual/locks, navegación, conflictos de guardado, preflight y el recorrido existente Preview/PDF. No acreditan todo caso industrial de salida. |
| Pruebas específicas de preparación | Dos PDFs con borradores distintos; cambio de caja conservando valores; medidas manuales; página sin TrimBox bloquea todo el lote; corrección explícita; creación, edición sin slots, variantes, undo/redo y recarga. |
| Trabajo colocado | Edición de cantidad conserva slots exactos, bloquea campos estructurales, invalida Repeat y permite undo/redo. Guarda de slots en dorso cubierta también con Node. |
| Responsive | Pruebas en 1140, 820 y 390 px; controles de preparación utilizables sin desbordamiento horizontal del documento. Revisión visual en Chrome a tamaño de escritorio y 390 px; viewport restaurado después. |
| Flask y navegador local | Se reutilizó el proceso registrado por `editor-offset-local-qa`, target V2, dev tools=0. Sin segundo servidor ni reinicio. Job QA nuevo `ev2_33d67636f47a19597e5ce109`, fixture `multipage-rotations.pdf`, tres trabajos guardados en revisión 3, cantidades 4/1/1 y sangrado 3; cero slots. Recarga comprobada y consola consultada sin errores/warnings. |

Las pruebas detectaron durante la implementación que el orden de claves devuelto por el servidor podía convertir una edición de cantidad en una falsa modificación estructural. Se corrigió mediante comparación por contenido y se añadió regresión. También se actualizaron expectativas antiguas de tests que mostraban el canvas/panel lateral al entrar en Preparar: ahora verifican la superficie central. No se presentan esos fallos iniciales como defectos previos del sistema.

**Límites y trabajo abierto:** el caso de cuatro páginas y el motor Repeat independiente siguen pendientes de la entrega C. La vista temporal de distribución y la revisión de atomicidad del comando ApplyRepeat de 42 no se completan aquí. V2 todavía depende del motor compartido actual; esta entrega no declara independencia total. La interfaz informa del sangrado solicitado y remite la cobertura física a preflight; no incorpora un nuevo cálculo geométrico de cobertura ni certifica arte útil fuera del corte. No se amplían marcas, CTP, PDF/X, nesting, separación de slots ni dúplex completo. No se ejecuta la suite global del repositorio ni toda la suite Python V2. Los originales y el job del usuario permanecen intactos.

**Cierre de la intervención:** sintaxis de los ocho archivos JavaScript modificados/nuevos comprobada con `node --check`; `git diff --check` sin errores. Cambios conservados sin commit en la rama actual.

### 2026-09-20 — Repeat propio V2: entrega C

**Solicitud y alcance:** avanzar con el motor propio del plan 42 después de la preparación unificada. Base Git limpia en `d41d041`, rama `codex/editor-offset-v2-stabilization`. Intervención sobre Repeat V2, contrato transitorio de propuesta, registro de versión al aplicar y pruebas. No se modifican motores comunes, V1, schema persistente ni originales del usuario.

**Base reproducida:** antes de sustituir el adaptador, 35 tests focalizados de Repeat pasaron. Un fixture independiente con cuatro trabajos de 254 × 142,875 mm en pliego 700 × 500, separación 3 mm y bleed 0 devolvió `INCOMPLETE_IMPOSITION`, sin propuesta aplicable, pese a caber geométricamente. El caso quedó fijado como regresión; la prueba final usa cuatro páginas físicas distintas y conserva sus identidades.

**Cambio y mapa del flujo ejecutable:**

```text
RepeatPanel → API Repeat → RepeatService (revisión y petición)
  → RepeatEngineAdapter (fuentes, preferencias, alcance y obstáculos)
  → domain/repeat_packer.py (búsqueda pura propia V2)
  → adapter + kernel geometry (validación final, slots y cuentas por work)
  → propuesta temporal actual → ApplyRepeatCommand → undo/redo + guardado
```

- `domain/repeat_packer.py` sustituye completamente la llamada al motor compartido. Busca rectángulos libres compartidos entre trabajos; resta obstáculos y separaciones antes de colocar. No lee archivos ni persiste. El adaptador conserva su punto de entrada para sus consumidores, con implementación nativa, sin traducción ni fallback al motor anterior.
- La huella incluye trim y bleed, orientados con giros cardinales admitidos. Gap H/V es la distancia mínima en un eje separador entre huellas; se cuenta una sola vez y no se exige contra el borde además del margen. El kernel vuelve a validar límites, rotaciones, dimensiones, IDs, obstáculos y separaciones al construir los slots.
- `add` añade la demanda completa a los slots retenidos; no significa completar faltantes. `replace_work_face` excluye solo slots de trabajos/cara elegidos; un lock de eliminación bloquea el reemplazo entero. Piezas de otros trabajos y caras conservan identidad; los obstáculos de la cara se consideran aunque no estén visibles en la selección.
- Sin fill no hay extras. Fill atiende toda la demanda antes de rellenar y no rellena mientras falte algún trabajo. Las cuentas se calculan por work antes de sumar. Sin permiso de parcialidad, un resultado incompleto no entrega slots aplicables. `exact_quantity` mantiene compatibilidad con el servicio existente; no incorpora una tercera política.
- `RepeatResultV2` añade `engine_version` y `work_counts` transitorios. La versión `v2-repeat-1.0.0` participa en la identidad de operación y se conserva en `imposition.engine_version` al aplicar. Undo restaura el valor anterior; propuestas antiguas sin ese campo conservan la compatibilidad de versión del adaptador. No hay migración ni cambio del schema de Layout V2.
- Diagnósticos distintos: `PIECE_EXCEEDS_PRINTABLE_AREA`, `INCOMPLETE_IMPOSITION`, `REPLACE_LOCKED`, `UNSUPPORTED_PREFERENCE` y `CALCULATION_LIMIT`. No encontrar una distribución no se presenta como demostración de que las piezas no caben.

**Preferencias, determinismo y límites:** prioridad ascendente cuando está activada; desempate estable por identidad. Se comparan hasta cuatro ordenaciones dentro de cada prioridad (identidad, área, lado mayor y lado menor), con dos variantes de selección de orientación/posición. Se priorizan propuestas completas, cumplimiento por prioridad, cantidad, área productiva y envolvente compacta. En igualdad se conserva el primer resultado. Esto produce un 2×2 en la regresión sin imponer una posición a cada ID como contrato general.

Zonas admitidas: auto/top/bottom/left/right/center/fill; `none` equivale a auto. Son preferencias, no regiones rígidas; fill se ordena después dentro de la misma prioridad. Flujos: auto/horizontal/vertical; rows/columns equivalen a horizontal/vertical y manual/none a auto. Preferencias desconocidas fallan explícitamente. Los giros exactos 180/270 se conservan aunque compartan huella con 0/90.

Límites definidos en el módulo: 128 trabajos, 2.000 formas solicitadas/placements, 2.000 obstáculos, 1.024 rectángulos libres y 1.000.000 unidades de esfuerzo contabilizado. La cantidad se mantiene compacta; no se expanden solicitudes enormes. Un límite puede devolver el mejor resultado válido y un aviso, o bloquear si la política exige completitud. La búsqueda es heurística y acotada, no optimización garantizada.

Medición local del **motor puro**, sin suites/navegador pesados ejecutándose en paralelo: 20 trabajos, tamaños 10–12 × 10–11 mm, área 680 × 480, gaps 2/3, giros 0/90. No incluye HTTP, validación final cuadrática, render ni PDF:

| Solicitadas | Colocadas | Límite alcanzado | Esfuerzo | Tiempo observado |
|---|---:|---|---:|---:|
| 200 | 200 | No | 150.168 | 0,714 s |
| 1.000 | 1.000 | Sí, al comparar alternativas después de completar | 1.000.001 | 1,352 s |
| 2.000 | 1.363 | Sí | 1.000.001 | 1,218 s |

No se certifica capacidad industrial a partir de estas mediciones. Con 2.000 solicitadas y sin parcialidad, esa propuesta incompleta queda bloqueada; alcanzar el límite no certifica el aprovechamiento máximo.

**Prueba interactiva:** skill `editor-offset-local-qa`, target V2, enabled=1, dev tools=0. Se reinició únicamente el proceso registrado y verificado para cargar el Python nuevo (sin reloader); PID final 21352. Después del reinicio, `/` y `/editor_offset_visual_v2` devolvieron HTTP 200 en el segundo intento conjunto. No se lanzó otro servidor sobre el puerto ocupado.

En Chrome se creó el job QA `ev2_661d38208d8a79bb1f83f53d` con un PDF sintético de cuatro páginas coloreadas. Tras calcular: 4 solicitadas, 4 colocadas, 0 faltantes, 0 extras; el montaje aún vacío hasta aplicar. Se aplicó, deshizo (0), rehízo (4), guardó y recargó. Layout final revisión 8, cuatro fuentes distintas y motor nativo. Distribución 2×2 con centros X 127/384 e Y 71,4375/217,3125 mm, rotación 0, gaps 3 y dimensiones 254 × 142,875. Consola consultada sin errores/warnings. El job original `ev2_c2ae50a13c42689bafd97ab3` no se modificó.

**Salida y límite observado:** el caso de margen cero/gap 3 con marcas predeterminadas se bloquea por `CROP_MARK_OUTSIDE_SHEET` y/o `CROP_MARK_OVERPRINT`. Se conserva ese bloqueo, sin atribuirlo a un fallo previo no comparado. En el fixture aislado de Playwright se eligió explícitamente un perfil QA sin marcas mediante API, conservando exactamente los slots: PDF y Preview correctos, una página 700 × 500 mm, contenido vectorial sin imágenes raster, cuatro textos/colores de página en sus posiciones. El producto no desactiva marcas automáticamente. Encaje de footprints y espacio para marcas son comprobaciones distintas; el motor no reserva geometría de marcas.

**Cobertura y límites de independencia:** una prueba en intérprete nuevo prohíbe importar engines/services/strategies/montaje_offset_inteligente, luego importa y ejecuta tanto el packer como RepeatService con repositorio temporal. Pasa sin dependencias transitivas de esos paquetes. Se comprobó también el arranque real de Flask. Esto demuestra aislamiento del camino Repeat; no declara independencia total del arranque de la aplicación ni de las otras superficies de V2.

Dos tests Playwright existentes se ajustaron para fijar la geometría de su escenario: uno coloca explícitamente el slot que debe quedar dentro del nuevo margen; otro separa el objetivo de Alt+arrastre de copias anteriores. Conservan las aserciones de estado visual y procedencia exacta. Ya no dependen de las posiciones arbitrarias del motor anterior.

**Pendiente dentro de 42:** D conserva la capa de propuesta visible antes de aplicar, detalle por trabajo y prevalidación atómica completa de ApplyRepeat. Solo se adelantó el registro de versión necesario para C. La guarda de propuestas obsoletas de B se mantiene. El recorrido integrado realizado aporta evidencia a E, pero no cierra el plan sin D. No se amplían marcas, CTP, PDF/X, nesting, dúplex ni separación masiva de slots. Rollback de código no revierte montajes guardados: los slots siguen siendo Layout V2 normales, con undo en su sesión cuando proceda.

**Validación final de esta intervención:**

| Comprobación | Resultado |
|---|---|
| Python focalizado Repeat: adaptador, servicio y packer | 57 passed; cuatro páginas, fuentes, cardinales, bleed, gaps, obstáculos, reemplazo, locks, parcial/fill, preferencias, límites y aislamiento transitivo. |
| Suite Python V2 `tests/editor_offset_v2` | 567 passed, 1 skipped (symlink no disponible en Windows), 20 avisos de deprecación de dependencias; 137 s. |
| Todos los tests Node V2 | 139 passed; incluye versión nativa al aplicar y restauración de metadatos mediante undo/redo. |
| Playwright V2: edición, caracterización UX, salida, preparación y Repeat nativo | 30 passed; 171 s. Cinco avisos de deprecación de PyMuPDF/SWIG. |
| Sintaxis y whitespace | `node --check static/js/editor_offset_v2/commands.js` y `git diff --check` correctos. |
| Artefacto de salida | Preview PNG inspeccionada visualmente: 2×2 con páginas/colores correctos. PDF comprobado por dimensiones, texto, posiciones, color y ausencia de raster. |

No se ejecutó la suite global del repositorio ni Playwright V1. Estos resultados no certifican todas las combinaciones productivas ni ausencia de defectos fuera del alcance. Cambios conservados en la rama actual, **sin commit** en esta intervención.

### 2026-09-26 — Propuesta integrada y aplicación segura: entrega D

**Solicitud:** implementar y probar D de 42 con las herramientas necesarias. Base limpia en `5603263`, rama `codex/editor-offset-v2-stabilization`. Alcance: frontend propio V2, historial de Repeat, pruebas y esta trazabilidad; sin cambio de schema, motor Python, originales, V1 ni superficies compartidas. No se interpreta la autorización de implementación como permiso para commit/push.

**Comportamiento implementado:**

- «Calcular» dibuja las piezas propuestas con borde azul discontinuo, transparencia y aviso «Propuesta sin aplicar». La representación reutiliza geometría y artwork del renderer V2. Se conservan las piezas actuales; en reemplazo se atenúan/señalan en ámbar las que se retirarán. Los obstáculos ocultos se muestran temporalmente atenuados para revisar el alcance, sin alterar su estado de visibilidad.
- Las piezas de propuesta tienen clase/atributos separados, sin `data-slot-id`, foco de teclado ni eventos de puntero. No entran en selección editable, lista de slots, historial, Layout, autosave, PDF ni Preview de salida. La capa es distinta de `previewSlots`/`previewPositions` usados por arrastre y duplicación.
- El panel muestra por trabajo y página las formas solicitadas, propuestas, faltantes, extras, conservadas y total al aplicar. También resume piezas retiradas/conservadas/añadidas para toda la cara. Añadir sigue sumando la demanda; reemplazar sigue afectando únicamente a los trabajos/cara elegidos.
- «Descartar propuesta» elimina solamente el estado temporal. Calcular, aplicar y descartar pasan por acciones `repeat.calculate`, `repeat.apply` y `repeat.discard` registradas, con contexto compuesto desde bootstrap.
- La propuesta captura job, revisión, versión de cambios, trabajos, cara, modo y opciones. Mantiene el contador de peticiones para descartar respuestas tardías. Cambiar un gap invalida ya durante `input`, sin esperar a salir del campo. Comandos, undo/redo, actualización externa, conflictos/errores de guardado y cambios de revisión retiran la propuesta. Antes de aplicar se vuelven a contrastar identidad, controles y estado de guardado. Durante una interacción de puntero no se muestra ni aplica la capa.
- `ApplyRepeatCommand` prepara y valida el conjunto de slots antes de escribir. Comprueba alcance, referencias, IDs/colisiones, geometría cardinal mediante kernel, transformaciones, perfil de marcas, procedencia, bloqueos y vigencia de las piezas a retirar. Clona también los metadatos antes de las dos asignaciones finales. Un error de validación conserva layout, selección, dirty state e historial. La selección anterior se restaura mediante undo y la nueva mediante redo.
- Hallazgo asociado: el fixture anterior de reemplazo conservaba una copia en dorso cuyo `source_slot_id` apuntaba a un slot eliminado. El nuevo comando bloquea explícitamente cualquier referencia de origen que quedaría colgando. El test positivo usa ahora una pieza realmente independiente y un test negativo cubre la copia dependiente. No se borra ni reescribe silenciosamente su procedencia.
- Ajuste mínimo de Store: `redo` retira el comando de su pila después de ejecutarlo con éxito; si la validación falla, se conserva la posibilidad de rehacer. No se reescribe el Store ni se cambia su contrato persistente.

**Archivos:** `commands.js` y `store.js` contienen aplicación/prevalidación y estado temporal; `repeat_panel.js` controla petición, vigencia, acciones y detalle; `canvas_renderer.js` representa la capa; `bootstrap.js`, `command_registry.js`, `dom_refs.js`, template y CSS V2 conectan los controles. Pruebas en `repeat_commands_v2.test.cjs`, `repeat_proposal_freshness_v2.test.cjs` y `test_editor_offset_v2_native_repeat.py`.

**QA interactiva y datos:** Flask local se inició con la skill `editor-offset-local-qa`, target V2, enabled=1 y dev tools=0, PID 11976. Las comprobaciones previas no respondían; el primer inicio encontró un proceso registrado y se negó a duplicarlo. La comprobación posterior de parada informó que ya no existía PID guardado y no detuvo procesos. El siguiente inicio controlado tuvo éxito; `/` y `/editor_offset_visual_v2` respondieron HTTP 200 en el segundo intento conjunto. Se conservan los logs; no se finalizaron procesos desconocidos.

El navegador integrado creó `ev2_a649fe5c253fa93e2e0f7671` y cargó un PDF sintético de cuatro páginas de 254 × 142,875 mm. Un primer intento de selector de archivos falló porque Fuentes estaba cerrado en la vista compacta; se recuperó abriendo ese panel y usando el selector. No se presenta como fallo del editor. Recorrido comprobado: cuatro trabajos → gap 3/3 → cuatro piezas temporales en 2×2, cero slots persistidos → descartar (cero/cero) → recalcular y aplicar (cuatro slots, sin capa) → undo (cero) → redo (cuatro). Luego se calculó reemplazo con gap horizontal 15: cuatro a retirar/cuatro nuevas; se descartó y recargó, conservando las cuatro piezas aplicadas con gap 3. Consola consultada sin errores/warnings. No se usó ni modificó el job original del usuario.

**Salida:** el recorrido automatizado comprueba que, con propuesta visible y dos slots guardados, el PDF contiene solamente las dos piezas persistidas. Un job vacío con cuatro piezas temporales sigue bloqueado para exportar. Tras aplicar, se comprueban PDF/Preview nativos de cuatro páginas fuente, dimensiones 700 × 500, posiciones, colores, texto y contenido vectorial. Los perfiles QA sin marcas se eligen explícitamente en datos aislados; los controles productivos de marcas/preflight no se cambian.

**Límites:** la vista temporal es orientativa y usa el artwork de canvas; no sustituye preflight ni la Preview/PDF nativa. Se conserva el límite de marcas documentado en C. No se amplían CTP, PDF/X, dúplex, nesting ni separación masiva. D usa únicamente módulos propios V2, pero no declara independencia de toda la aplicación. La entrega E conserva el cierre integral del plan; esta ejecución aporta regresiones y recorridos concretos, no certificación de todas las combinaciones productivas.

**Validación de D:**

| Comprobación | Evidencia |
|---|---|
| Baseline focalizado antes de editar | 11 tests Node de comandos Repeat/vigencia pasaron. |
| Node V2 completo | 146 passed. Incluye error de colisión sin cambios parciales, fuente dependiente, scope/fuente/geometría/transformación inválida, revalidación al ejecutar, redo fallido con pila intacta, estado temporal/cuentas, respuestas tardías y conflictos. |
| Playwright V2 completo | 31 passed en 187 s: edición, caracterización UX, salida, preparación y Repeat nativo. |
| Regresión final Repeat nativo | 2 passed en 34 s tras ampliar el caso de obstáculos ocultos: se revelan solo durante revisión, sin selección editable ni cambios de visibilidad al descartar. |
| Python V2 completo | 566 passed, 1 skipped (symlink de Windows), 1 failed; 20 avisos de deprecación. El fallo es el presupuesto temporal del test de salida con 500 piezas. |
| Rendimiento de salida, comparación equivalente | Árbol actual: 60,532 s durante suite y 64,750 s al ejecutar solo el caso. Copia aislada de `5603263`, mismo venv/comando/caso: 63,063 s. En ambos se genera PDF y pasan las aserciones de contenido antes de fallar `elapsed < 60`. |
| Sintaxis/whitespace | Los siete JS modificados pasan `node --check`; `git diff --check` sin errores. |
| Persistencia QA interactiva | Revisión 4; cuatro páginas/slots, motor `v2-repeat-1.0.0`, gaps persistidos 3/3. Descartar reemplazo con gap 15 no altera esos valores. |

La comparación reproduce el fallo temporal también en la base anterior a D; no demuestra su causa ni garantiza rendimiento en otras cargas. Se mantiene el umbral de 60 segundos y el fallo abierto, sin modificar código de salida ni atribuir una suite totalmente verde. El test de symlinks y las deprecaciones conservan sus límites de entorno. No se ejecutó la suite global ni Playwright V1.

**Cierre:** D implementada y probada en el alcance descrito; 42 actualizado a B/C/D implementadas con cierre integral E pendiente. Registrar aparte el rendimiento de salida de 500 piezas cuando se aborde esa superficie. Cambios en la rama actual, sin commit ni push en esta intervención.

### 2026-09-26 — Alternativas de Repeat y marcas dentro del sangrado

**Solicitud y decisión:** posponer E para poder cambiar la distribución propuesta por Repeat y mantener las marcas de corte dentro del sangrado. El usuario eligió explícitamente omitir marcas con aviso cuando el sangrado sea cero. Base limpia `19f2d5d`; intervención en la rama actual. Se aplicaron las habilidades `system-architect` para impacto y `editor-offset-local-qa` para Flask.

**Repeat:** selector con automática, priorizar filas, priorizar columnas y priorizar giros de 90°/270°. «Probar otra distribución» recorre esas opciones y recalcula; si reproduce el montaje anterior lo avisa. La propuesta sigue siendo temporal hasta aplicar. Cambiar la selección invalida la propuesta; se incluye la distribución en el contexto de vigencia y se comprueba nuevamente al aplicar. Continúan las guardas de revisión, cambios locales, respuesta tardía, conflicto y puntero. Calcular no está disponible mientras espera una respuesta. Se eliminó la duplicación visual de mensajes que llegaban como issue y como warning.

El campo opcional `distribution` pertenece a la petición Repeat, admite `auto`, `rows`, `columns`, `rotated` y participa en la identidad de operación. No se añade al Layout ni a sus settings persistidos. El packer propio V2 pasa a `v2-repeat-1.1.0`; conserva presupuesto de búsqueda, obstáculos, cantidades, prioridad, zonas, separaciones, política partial/fill y giros permitidos. Una distribución explícita orienta el flujo en lugar de la preferencia de filas/columnas del trabajo; las zonas se conservan cuando están activadas. Son heurísticas deterministas: no garantizan un resultado diferente ni una solución óptima. No se conecta un servicio IA ni un motor compartido. El resultado aplicado conserva posiciones y versión de motor mediante el comando reversible existente.

**Marcas:** `domain/crop_marks.py` define la geometría propia V2 usada por PDF nativo y, por composición, Preview. Canvas replica las dimensiones en `geometry_view.js`, con fixtures métricos compartidos. Cada marca se alinea con una arista trim y se extiende hacia fuera del corte, dentro de la banda de sangrado. Para sangrado `b > 0`: grosor `min(0,2; b/5)`, inicio `min(1; b/4)`, extremo `min(b - grosor/2; inicio + 3)`, todo en mm. Se usan extremos rectos y una reserva de medio trazo; no se invade el trim ni se excede el bleed. Con 2 mm: trazo 0,2, inicio 0,5 y extremo 1,9 mm. En sangrados muy pequeños las marcas también se acortan/afinan; no se certifica su legibilidad industrial.

Con sangrado cero no se dibujan marcas, manteniendo activado el perfil guardado. Repeat y preflight muestran `CROP_MARKS_OMITTED_NO_BLEED`; en preflight es warning sin operaciones bloqueadas. Los controles de marcas fuera de pliego y sobreimpresión de otras piezas siguen activos con el grosor real. La versión de capacidades de preflight pasa de 3 a 4 para rechazar informes anteriores. Se mantienen los bloqueos por falta de sangrado físico o clipping incompatible; no se sintetiza sangrado sin la opción explícita existente.

**Compatibilidad y alcance:** no cambian schema, originales ni layouts guardados. Sí cambia intencionalmente cómo se representan y exportan las marcas de jobs existentes al volver a abrir/generar salida. Los PDFs ya producidos no se reescriben. V1, motores compartidos y probes históricos del puente legacy no se modificaron; esta política se aplica al camino nativo operativo V2. No se declara independencia de toda la aplicación. E permanece pendiente y no se crea otro roadmap.

**Validación y hallazgos durante QA:**

- Node V2 completo: **148 passed**. Incluye paridad dimensional Python/JS, alternativa idéntica y rechazo al cambiar distribución antes de aplicar.
- Python focalizado inicial: **147 passed** entre packer, servicio, adaptador y compositor. Pruebas nuevas de identidad/no persistencia, alternativas distintas, giros permitidos y tinta dentro del bleed/fuera del trim en 0/90/180/270°.
- La primera suite Python sin carga temporal obtuvo 586 passed, 1 skipped, 3 deselected y un fallo del fixture Preview que seguía esperando marcas con sangrado cero. Se actualizó a 2 mm, 144 dpi y generación de sangrado explícita para ese PDF sintético; Preview/compositor completos: **105 passed**, incluidos cuatro tests nuevos que leen trazos del PDF generado.
- Playwright de edición, UX y preparación: **24 passed**. La primera ejecución de salida encontró tres aserciones antiguas que esperaban ocho marcas con sangrado cero. Ahora verifican que permanecen exactamente los dos rectángulos vectoriales fuente y ninguna marca. Conservan la comparación visual SVG/Preview/PDF. Un test nuevo leyó el servidor antes del guardado inicial; se corrigió esperando guardado y exigiendo dos slots antes de continuar.
- Reejecución final de Repeat nativo y salida: **8 passed**. Incluye cuatro páginas, alternativas, invalidación, aplicar/undo/redo/recarga, propuesta excluida del PDF, omisión con cero bleed, y dos piezas con 2 mm: 16 marcas SVG medidas, 16 trazos PDF y Preview real. Se inspeccionaron las imágenes de canvas, Preview y raster del PDF; las exportaciones conservaron el Layout exacto.
- Reejecución Python final `tests/editor_offset_v2 -k 'not (bounded_placement_load and 500)'`: **593 passed, 1 skipped, 1 deselected**, 73 s y 20 avisos de deprecación. El skip corresponde a symlink en Windows; se excluyó únicamente el presupuesto temporal de 500 piezas. Las cargas de 14 y 100 piezas sí pasaron. Las cinco superficies Playwright suman **32 casos pasados** en las ejecuciones finales por alcance (24 + 8).
- Sintaxis de los JS modificados y `git diff --check` correctos. No se ejecutó suite global ni Playwright V1.

**QA manual:** Flask comprobado, reiniciado únicamente tras verificar el PID registrado 11976, nuevo PID 11896, target V2 y dev tools=0. `/` y `/editor_offset_visual_v2` respondieron HTTP 200 tras el reinicio. En el navegador integrado se usó el job sintético `ev2_a649fe5c253fa93e2e0f7671`: calcular reemplazo, filas con aviso de igualdad, columnas con distribución distinta, descartar y recargar. Quedaron cuatro piezas, sin propuesta, revisión 4 y sin errores/warnings de consola. No se modificó el job original del usuario.

**Límites y cierre:** sigue pendiente el rendimiento de salida con 500 piezas registrado en D; no se eleva su umbral ni se resuelve como parte de esta mejora. Revertir código restituye la política de representación, pero no revierte montajes aplicados; éstos conservan undo en sesión y slots V2 normales. Cambios sin commit ni push en esta intervención.

### 2026-09-27 — Salida habitual V2, entrega 4 de 43

**Observado:** rama `codex/editor-offset-v2-output-deliveries-4-5` limpia al comenzar. Preview/PDF estaban apagados salvo flags temporales; el script QA además activaba derivados. El job del usuario cambió desde la referencia: revisión 42, tres trabajos y seis piezas, pliego 700 × 700 mm. Los dos trabajos originales usan páginas 1/2 del PDF MediaBox y sangrado 3 mm; el tercero, agregado después, usa otro PDF y `mirror_if_missing`. Hash actual del layout original `723d9ae3dc30fefe68131e8c3a57dfc18735083056de8178b809d114afae8b4b`, sin alteración en esta intervención.

**Cambiado y verificado:** el nuevo `scripts/start_editor_offset_v2.ps1` fija Preview/PDF activos y derivados apagados para el proceso local V2; dev tools permanece apagado por `editor-offset-local-qa`. El nuevo verificador comprueba las tres rutas/gates y el contexto shell. La habilidad encontró un registro PID obsoleto y evitó duplicar procesos; `-Restart` lo retiró, inició PID 7652 y un segundo reinicio verificó su identidad antes de detenerlo e iniciar PID 11432. Se corrigió la mezcla de texto/booleano en `start_flask.ps1`; una ejecución normal posterior reconoció y reutilizó PID 11432. Raíz y shell 200, rutas de salida disponibles, derived-page deshabilitada, contexto UI correcto. En copia del job, preflight a 300 dpi bloquea Preview por recursos pero no PDF; a 150 dpi permite ambas. Preview/PDF generados de la copia sin alterar su layout/revisión ni el original. Detalle, límites y rollback en [43](43_PLAN_SALIDA_PDF_HABITUAL_V2.md#cierre-de-entrega-4--2026-09-27). Entrega 5 continúa separada; no se hizo commit/push.

### 2026-09-27 — Verificación integral, entrega 5 de 43

**Observado:** el original tenía revisión 42, seis slots y dos PDFs fuente; la referencia de revisión 39/cuatro slots era histórica. Su primer PDF declara solo MediaBox en el diccionario real; los valores TrimBox/BleedBox que devuelve PyMuPDF son defaults, no declaraciones. Se clonaron layout y assets a `ev2_f50a8ef1f55a4ff89e356d18` sin informes/salidas; originales y copia conservaron layout y fuentes tras las pruebas.

**Cambiado:** se añadió en `test_editor_offset_v2_native_repeat.py` un recorrido reproducible de preparación de tres páginas con cajas y sangrados distintos, cantidades 2/1/1 y decisiones mixtas; Repeat temporal/aplicar, historial, save/reload, giro 90°, preflight, Preview y descarga PDF. El test mide dimensiones, multiplicidades y ubicaciones del texto, 24 marcas en PDF/SVG, fuentes inmutables, y rechazos 422/409 sin cambio en los archivos publicados. Se corrigieron solo dos supuestos del propio test durante la primera ejecución: abrir opciones avanzadas y comparar la revisión devuelta por el save.

**Verificado:** Python V2 623 passed, 1 skipped, 1 deselected (caso temporal 500 piezas); Node V2 165 passed; los seis archivos Playwright V2 37 passed; caso mixto final repetido 1 passed. `py_compile` y `git diff --check` correctos. En la copia real, PDF de una página ~700 × 700 mm con seis piezas, páginas 1/2 duplicadas, 48 segmentos de marcas y dos piezas adicionales; Preview y PDF raster muestran la misma distribución. A 150 dpi ambos raster miden 4134 × 4134, error RGB medio 0,43/255 y 0,44 % de píxeles difieren >32. Preview de 300 dpi bloqueada; PDF con revisión vieja rechazado; cuatro archivos publicados de la copia intactos tras esos rechazos. Hash del layout original y los dos PDF fuente comprobados iguales al inicio/final. Artefactos y detalle en [43](43_PLAN_SALIDA_PDF_HABITUAL_V2.md#cierre-de-entrega-5--2026-09-27). No se ejecutó suite global/V1, no se resolvió el límite de 500 piezas, ni se hicieron commit/push.
