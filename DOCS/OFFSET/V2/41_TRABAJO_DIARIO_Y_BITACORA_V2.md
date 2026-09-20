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
