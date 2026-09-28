# Editor Offset Visual V2 — segunda revisión de subagentes y explicación funcional

Fecha de la revisión y de la consolidación: 2026-09-27.

## 1. Propósito y procedencia

Este documento reúne la **segunda entrega de los tres subagentes**, el recorrido del agente principal y la explicación entregada al usuario después de probar el sistema. La primera entrega había construido un inventario estático; esta segunda revisión contrastó ese inventario con pruebas, interfaz, persistencia y archivos PDF generados.

El objetivo fue entender cómo funciona V2, comprobar las conexiones del [mapa 44](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md), corregir un error reproducido y estudiar posibles herramientas para publicaciones. El mapa 44 conserva la localización de archivos y conexiones; este informe explica sus resultados y el funcionamiento para el operador. La [bitácora 41](41_TRABAJO_DIARIO_Y_BITACORA_V2.md) registra las intervenciones. Las ideas de ampliación son opciones investigadas, no funciones implementadas ni una agenda obligatoria.

La revisión se repartió así:

- **Subagente backend:** servicios, rutas, validación, persistencia, snapshots, pruebas Python, rendimiento y archivos PDF.
- **Subagente frontend:** módulos JavaScript, herramientas, historial, guardado, seis archivos Playwright V2 y comprobaciones responsive.
- **Subagente de investigación:** límites del dominio actual, posibilidades para revistas y documentación oficial de imposición.
- **Agente principal:** coordinación, gestión controlada de Flask, copia del montaje del usuario, recorrido interactivo, contraste de artefactos y actualización del mapa.

Los cambios de código y la evidencia de esta revisión quedaron guardados previamente en el commit `a357fac`. Este informe consolida esa entrega; su creación no representa una nueva ejecución de las suites ni el desarrollo de herramientas editoriales adicionales.

## 2. Conclusión general

V2 funciona como un **editor de piezas y formas sobre un pliego**. Permite preparar páginas de PDF, definir cantidades independientes, distribuirlas con Repeat, ajustar su geometría o contenido, guardar con historial y producir Preview/PDF mediante un compositor propio.

Las conexiones principales del mapa coincidieron con la ejecución. Se precisaron cuatro afirmaciones técnicas: el contenido de la petición de preflight, el preflight fresco de cada generación, el lugar donde se valida el layout y la función que produce artwork para el canvas. Además, se corrigió un fallo con layouts de estructura corrupta.

El alcance actual conserva límites concretos: el proceso Flask completo carga también rutas legacy; la navegación de caras no está completa en la UI; no existe un modelo editorial de secuencia, firmas o múltiples pliegos; y la carga de 500 piezas sigue excediendo el presupuesto temporal probado. No se certificó PDF/X, CTP ni funcionamiento industrial general.

## 3. Segunda entrega del subagente backend

### 3.1. Qué comprobó en las conexiones

El registro HTTP sigue en `app.py` y `editor_offset_v2/blueprint.py`. El paquete V2 contiene servicios y reglas propias para jobs, assets, Repeat, preflight y salida. Repeat utiliza `domain/repeat_packer.py`; Preview/PDF utiliza la preparación de fuentes y el compositor PDF V2. Las sondas y ensayos legacy conservan imports locales antiguos, pero están fuera de la salida habitual.

La independencia debe describirse con ese alcance. `app.py` importa y registra `routes.py` legacy antes de registrar V2. Por tanto, la propiedad del motor Repeat y del compositor V2 no demuestra que todo el proceso Flask pueda arrancar sin el resto del producto.

El subagente también confirmó que `ArtifactLifecycleService` tiene pruebas, pero no localizó una llamada productiva. La existencia de una utilidad de retención/recuperación no permite afirmar que se ejecute automáticamente durante el uso del editor.

### 3.2. Precisiones que se incorporaron al mapa

**Preflight recibe opciones, no una operación única.** El POST admite `face`, `dpi` y `allow_mirror_bleed`. El reporte devuelve decisiones separadas para Preview, PDF final y CTP. Así puede bloquear una operación y permitir otra según sus requisitos.

**Cada generación vuelve a comprobar las entradas.** La UI consulta preflight para informar al operador, pero el backend de Preview/PDF crea un snapshot nuevo y ejecuta/consume su propio preflight. La revisión solicitada mediante `expected_revision` se comprueba en esa frontera. Un informe anterior de la UI no es una autorización permanente para producir un archivo.

**La validación pertenece a los servicios.** `domain/validation.py` valida el contrato y es utilizado por los servicios. `JobRepository` gestiona lectura, revisión y escritura; no importa ni llama directamente al validador. Esta distinción evita atribuir al repositorio garantías que pertenecen a otra capa.

**Artwork se produce con una función.** `application/artwork_service.py` exporta `render_artwork`; no existe una clase denominada `ArtworkService`. Su resultado es la imagen aproximada que representa el contenido en el canvas.

### 3.3. Error encontrado y corregido

El subagente reprodujo el fallo con datos temporales: un `layout_v2.json` que contenía `{}` o un slot con `geometry=null` era JSON legible, pero no tenía una estructura válida. Preflight registraba problemas del contrato y después intentaba recorrer campos que no podía interpretar. Preview/PDF pasaban por ese mismo recorrido. El resultado podía ser una excepción y una respuesta HTML 500 fuera del formato JSON esperado.

La corrección en `application/preflight_service.py` rechaza campos requeridos ausentes o tipos estructurales incorrectos antes de recorrer fuentes y geometría. Devuelve HTTP500 con JSON `INVALID_LAYOUT` e información del validador. Los errores semánticos que sí permiten recorrer la estructura continúan produciendo un reporte con bloqueos; no se sustituyeron todos los diagnósticos por una excepción.

Se añadieron siete regresiones en `test_preflight_v2.py`: seis combinan las tres rutas con las dos corrupciones estructurales y otra conserva el comportamiento de diagnóstico semántico. Comprueban el formato JSON, el error, la conservación exacta del layout y las fuentes, y la ausencia de reportes, Preview o PDF parciales. El agente principal verificó también las tres rutas en Flask después del reinicio y restauró el job QA al layout válido inicial.

### 3.4. Qué encontró al inspeccionar los PDF

La inspección combinó métricas y render visual. Los fixtures de marcas conservaron un pliego de 120×100 mm y ocho segmentos de marcas dentro del sangrado en los giros cardinales. El fixture dúplex produjo dos páginas de 700×500 mm y permitió revisar el volteo `long_edge`. También se verificó un PDF vectorial de 700×700 mm mientras la Preview 300 dpi quedaba bloqueada por presupuesto de píxeles.

Las cargas de 14 y 100 piezas conservaron el contenido esperado y no añadieron imágenes al fixture vectorial. El PDF de 500 piezas tuvo una página de aproximadamente 2000×1400 mm, 500 ocurrencias del texto esperado y cero imágenes. TrimBox/BleedBox estaban ausentes en ese PDF; no se inventaron cajas.

Las imágenes de marcas a 90° y ambas caras dúplex se renderizaron con Poppler. Hubo avisos de fuentes de visualización no instaladas, aunque los archivos se generaron y el texto del fixture resultó visible. Esto se conservó como límite de la inspección del entorno.

### 3.5. Rendimiento pendiente

El caso de 500 piezas se ejecutó por separado con el umbral existente de 60 s. El render tardó **66,797 s**, por lo que la prueba falló. El contenido físico del PDF pasó las comprobaciones previas al límite temporal. El hallazgo permite distinguir integridad del archivo y rendimiento: el límite de tiempo continúa abierto y no se elevó para ocultarlo.

## 4. Segunda entrega del subagente frontend

### 4.1. Recorridos comprobados

Las pruebas verificaron la preparación de páginas, cantidades independientes, variantes y decisiones de sangrado. Los lotes inválidos no crearon trabajos parciales. En Imponer, el cambio de pliego conservó la geometría de los slots y Repeat mantuvo la propuesta temporal hasta aplicar.

También se comprobaron alternativas de Repeat, add/replace, descarte y vigencia de la propuesta frente a cambios de revisión u opciones. Aplicar entra al historial mediante un comando reversible. Las pruebas de herramientas incluyeron drag, Alt-drag, posición precisa, nudge, rotación cardinal, clipboard, locks, selecciones, árbol, alineación, distribución, matriz, reglas, guías, snap y medición.

Undo/redo, autosave y recarga conservaron el layout y las revisiones. Los conflictos de guardado se mostraron al operador sin sobrescribir silenciosamente. La propuesta Repeat, selección y otras ayudas temporales no se incorporaron como datos del layout.

En Validar/Salida se comprobaron el diagnóstico agrupado por trabajo/página, la invalidación de respuestas tardías y el rechazo de resultados obsoletos. Una Preview que excede recursos no bloquea por ese mismo motivo el PDF vectorial. La suite contrastó SVG, Preview y PDF para casos de escala, espejo, giro/offset, sangrado y marcas de 2 mm, además de combinaciones de cajas, páginas y cantidades.

### 4.2. Interfaz y responsive

La suite existente utilizó varios tamaños desktop y compactos e incluyó 390 px en casos de preparación/sangrado. El smoke adicional comprobó 1440×1000,540×844 y 390×844. La URL y el título correspondían a V2, había contenido significativo, no se observó overlay de error y no hubo errores de página ni warnings/errors de consola en ese smoke.

Los clicks reales de las cinco etapas cambiaron la selección y el panel correspondiente a 540 y 390 px. El ancho del documento no excedió el viewport. Algunas barras de acciones y etapas disponen de scroll horizontal local; que un control quede fuera de su carril visible no equivale por sí solo a un desbordamiento del documento.

En el navegador CUA del agente principal, algunos clicks inicialmente no cambiaron el estado esperado. La activación por teclado funcionó y el smoke Playwright no reprodujo el problema con clicks reales. No se declaró ese episodio como un defecto del producto.

### 4.3. Entorno y evidencia

Los Playwright utilizaron servidores Flask de puerto efímero y raíces temporales de jobs. El subagente no administró el puerto 5000 ni accedió a originales del usuario. Usó la regresión Playwright existente porque la skill Browser no estaba listada y el usuario había autorizado ejecución e interacción.

Las capturas documentan ajuste desktop, preparación a 390 px, propuestas Repeat, canvas/PDF, mensajes de diagnóstico y conflicto visible. Los warnings de la suite correspondieron a deprecaciones SWIG/PyMuPDF, no a errores de la UI.

## 5. Recorrido del agente principal con la copia real

El montaje original tenía revisión 42, pliego 700×700 mm, tres trabajos, seis piezas y dos PDF fuente. Se creó la copia `ev2_712410ef8ebb0395c13d304a`, preservando el original. Su revisión inicial de copia fue 2.

En esa copia se calculó una propuesta Repeat de reemplazo con seis piezas solicitadas y seis propuestas, sin faltantes ni sobreproducción. Antes de aplicar, el canvas distinguió piezas nuevas y piezas a reemplazar y explicó que la propuesta no se guardaba ni exportaba. Después se comprobó aplicar, deshacer, rehacer, autosave y recarga.

El preflight permitió Preview, pero bloqueó PDF debido a clipping TrimBox en piezas de trabajos históricos con sangrado solicitado. El operador debe resolver ese recorte explícitamente. En la copia se cambió el clipping a BleedBox mediante el inspector de contenido; se conservó el original y no se migraron decisiones antiguas silenciosamente.

La salida final de copia, revisión 6, tuvo seis slots y un PDF de una página de aproximadamente 700×700 mm. La Preview a 150 dpi midió 4134×4134 píxeles. Al rasterizar el PDF con las mismas dimensiones, la comparación RGB dio diferencia media 0 y 0% de píxeles por encima del umbral de diferencia 32. Esta igualdad corresponde a esa revisión y esas opciones, no a todos los casos posibles.

La UI informó PDF listo y descarga iniciada. El evento de descarga esperado por CUA agotó su tiempo; el PDF publicado sí pudo leerse e inspeccionarse directamente. Los Playwright comprobaron las descargas en sus recorridos. Los hashes del layout original y sus dos PDF fuente coincidieron entre el inicio y el final.

Para cargar la corrección backend se verificó la identidad del proceso registrado y se reinició Flask mediante la skill: PID 11432 → 16248. Dev tools permaneció en 0, Preview/PDF activos y derivados apagados. La primera comprobación de la raíz tuvo timeout; el segundo intento obtuvo raíz y shell V2 HTTP200. El verificador confirmó el perfil habitual y la copia volvió a abrirse sin errores de consola.

## 6. Resultados y alcance de las pruebas

| Comprobación | Resultado | Lectura correcta del resultado |
|---|---|---|
| Python V2 antes de la corrección | 623 passed, 1 skipped, 1 deselected; 136,01 s | El skip fue WinError 1314 al crear symlink; el excluido fue el caso 500. Las cargas 14/100 sí se ejecutaron |
| Caso 500 aislado | Falló; 66,797 s de render frente a 60 s | PDF con 500 textos correcto; rendimiento pendiente, umbral intacto |
| Node V2 completo | 165 passed | Cobertura de los 18 módulos de pruebas JS |
| Seis Playwright V2 | 37 passed; 271,44 s | Cinco avisos de deprecación; servidores y jobs temporales |
| Backend después de corregir | 56 passed; 20,37 s | Preflight, decisiones, seguridad de salida, PDF y Preview; incluye siete regresiones nuevas |
| Probe Flask después del reinicio | Tres rutas con JSON 500 `INVALID_LAYOUT` | Sin publicación parcial; job QA restaurado |
| Responsive adicional | Desktop 1440 y compactos 540/390 correctos | Smoke de identidad, contenido, consola, tabs, diagnóstico y ancho del documento |
| Copia real y artefactos | Historial/recarga y PDF/Preview comprobados | Originales inmutables y comparación RGB idéntica para el caso probado |
| `git diff --check` | Correcto | Comprobación de cambios, no prueba funcional |

La suite amplia Python fue anterior a la corrección. Las 56 pruebas relevantes y el probe live fueron posteriores. No deben sumarse reejecuciones como si fueran casos distintos ni presentarse estos resultados como una suite global posterior al cambio. No se ejecutó la suite global del repositorio ni Playwright V1.

Los comandos exactos de cobertura están en [44 — Contraste mediante ejecución](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md#contraste-mediante-ejecución--2026-09-27). Los seis archivos de navegador ejecutados fueron edición, caracterización UX, integración de salida, preparación, Repeat nativo y sangrado por trabajo.

Los artefactos backend/XML permanecieron en `.codex-runtime/audit44-backend-*`; la copia, hashes, métricas y probes en `.codex-runtime/audit44/`. Las capturas Playwright se produjeron en los directorios temporales `pytest-273` y `ev2-mobile-audit-mhb3igqi`. Esas ubicaciones son evidencia local de la sesión y pueden desaparecer al limpiar temporales; no forman parte de un paquete versionado de artefactos.

## 7. Cómo funciona V2 paso a paso

### Paso 1 — Crear o abrir el montaje

Un montaje tiene un identificador de job, un `layout_v2.json` y una revisión. El backend prepara sus carpetas de assets, derivados, previews, outputs y reports. Al abrir su URL, Flask entrega la plantilla y un contexto JSON con layout, revisión, endpoints y gates. El bootstrap construye store, controladores, paneles y canvas.

### Paso 2 — Incorporar los PDF fuente

La subida conserva el archivo original y genera metadatos y miniaturas. El inspector identifica páginas, medidas, giros y cajas declaradas. Si un PDF solo declara MediaBox, V2 no inventa TrimBox/BleedBox. Las miniaturas ayudan a elegir páginas; no certifican el contenido físico ni la calidad de impresión.

### Paso 3 — Preparar trabajos por página

Un **asset** es el PDF fuente; un **work** es la preparación de una página con sus opciones; un **slot** es una pieza colocada en el pliego. Una página puede tener variantes de trabajo. Cada trabajo define sus cantidades, medida final, sangrado y rotaciones permitidas.

La decisión de sangrado distingue usar únicamente el archivo, autorizar espejo si falta o conservar el comportamiento temporal de un trabajo anterior sin decisión guardada. El sangrado físico utilizable tiene prioridad. El espejo repite bordes y exige revisión visual; las cajas por sí solas no demuestran diseño útil en todo el perímetro.

### Paso 4 — Definir el pliego

Se configura ancho, alto y márgenes imprimibles. La UI muestra el impacto sobre las piezas existentes. Cambiar el pliego conserva tamaño y posición de los slots; el operador revisa los que puedan quedar fuera. La unidad es milímetros y la posición canónica del slot es su centro trim.

### Paso 5 — Colocar piezas o calcular Repeat

Puede colocarse una pieza preparada y ajustarla manualmente, o seleccionar trabajos para Repeat. Repeat considera cantidades, separaciones y giros permitidos y calcula una propuesta. Permite comparar distribuciones, aceptar resultados parciales cuando corresponda, completar espacio y elegir añadir o reemplazar.

La propuesta vive en estado temporal. Aplicar convierte el resultado en un comando del historial; entonces sus slots pasan a formar parte del layout y pueden guardarse. Descartar la propuesta conserva el montaje aplicado anterior.

### Paso 6 — Ajustar geometría y contenido

Las operaciones geométricas cambian posición, giro o disposición de las piezas. Las correcciones gráficas modifican la colocación interna del contenido: escala, offset, giro, espejo y clipping. El editor distingue ambas responsabilidades y respeta locks de geometría, contenido y eliminación.

Canvas, etiquetas, guías, selección y medición ayudan a revisar la composición. Algunas correcciones visibles pueden estar limitadas para salida: el preflight debe comprobar el perfil exportable. Resize del slot y las herramientas editoriales futuras no se deducen de la existencia del inspector de contenido.

### Paso 7 — Guardar y conservar el historial

Las mutaciones persistentes pasan por acciones y comandos reversibles. El store mantiene undo/redo y marca cambios pendientes. Autosave o Guardar envían el layout con `base_revision`. El servidor compara esa revisión y solo publica la nueva escritura si coincide; un conflicto se devuelve al operador.

Selección, viewport, guías temporales, borradores, propuesta Repeat y opciones de salida no se convierten en campos del layout por el solo hecho de estar visibles. El historial de comandos comprobado pertenece a la sesión del editor; esta revisión no acredita un historial de undo completo persistido entre sesiones.

### Paso 8 — Validar las opciones de salida

Validar y Salida utilizan el mismo diagnóstico nativo. Primero se resuelven cambios pendientes de guardado y luego se comprueban fuentes, revisión, geometría y opciones. El reporte agrupa mensajes por trabajo/página y diferencia avisos y bloqueos para Preview/PDF/CTP.

Un bloqueo de recursos de Preview puede dejar disponible el PDF vectorial. Una pieza fuera de área o un recorte que elimina el sangrado requiere revisar el motivo correspondiente. Editar el montaje o cambiar las opciones invalida el diagnóstico anterior.

### Paso 9 — Generar y revisar Preview/PDF

La petición del artefacto incluye la revisión esperada. El backend toma un snapshot fresco, vuelve a validar y compone las fuentes preparadas. Preview rasteriza esa composición a la resolución solicitada; PDF conserva objetos fuente dentro del perfil nativo, con raster donde corresponde, como bandas de espejo.

La publicación del archivo está protegida y los errores no deben dejar una salida parcial. La revisión del resultado y su formato se comprueban en la UI. La última comprobación del operador sigue siendo el archivo real: dimensiones, páginas, orientación, posición, sangrado y marcas. Un HTTP200 no sustituye esa inspección.

## 8. Herramientas disponibles y qué hace cada grupo

| Grupo | Herramientas existentes | Uso y límites |
|---|---|---|
| Preparación | PDF multipágina, selección de páginas, cantidades independientes, variantes, edición de trabajos y campos comunes | Configura formas por página; no representa todavía una secuencia editorial |
| Sangrado y cajas | Medida detectada/final, cajas en opciones avanzadas, sangrado y decisión por trabajo | Mantiene diferencias entre fuente física, espejo autorizado y trabajos anteriores |
| Pliego | Ancho/alto, intercambio de dimensiones, márgenes y evaluación de impacto | Conserva geometría de slots; no escala automáticamente el montaje |
| Repeat | Packer propio, alternativas, gaps, giros, parcial/fill, add/replace, aplicar y descartar | Propuesta temporal hasta aplicar; dorso deshabilitado en la UI actual |
| Geometría manual | Drag, Alt-drag para duplicar, posición precisa, desplazamientos y giros cardinales | No equivale a resize libre ni admite giros arbitrarios del contrato actual |
| Objetos y selección | Copiar/cortar/pegar, duplicar/eliminar, selección por trabajo/asset, árbol y locks | Restricciones de cara y permisos se conservan; locks engine/CTP/system no se retiran desde la UI |
| Organización | Alineación, centrado, distribución, gap exacto, slot clave y matriz | Puede usar trim o footprint productivo como referencia |
| Precisión y vista | Reglas, guías, smart guides, snap, medición, zoom, pan y etiquetas | Son ayudas de edición; no se imprimen selección, etiquetas o guías |
| Contenido interno | Fit, escala, offset, giro cardinal, espejo, clipping y restablecer | Debe contrastarse con preflight y PDF; no modifica el original físico |
| Derivados | Materialización de página y manifiesto de procedencia | Función existente con gate separado, apagada en el arranque habitual probado |
| Guardado | Autosave, Guardar, revisiones, conflictos y undo/redo en sesión | Preserva el guardado optimista y la escritura atómica |
| Salida | Diagnóstico común, Preview, PDF y marcas dentro del sangrado | Cero sangrado omite marcas con aviso; no certifica PDF/X/CTP |

## 9. Segunda entrega del subagente de investigación

### 9.1. Qué diferencia encontró para revistas

El dominio actual tiene un único `sheet`, caras `front/back` y slots. No encontró un modelo propio de secuencia editorial, firmas, encuadernación, creep o múltiples pliegos. El compositor genera una página por cara solicitada; el servicio PDF ordena frente/dorso, pero no una colección de pliegos editoriales.

Hay bases parciales útiles: fuentes frente/dorso, configuración de flip, cantidades por trabajo, transformación de contenido, sangrado y preflight. Sin embargo, el store inicializa la cara activa desde las caras habilitadas y no se localizó una acción completa de navegación; creación/paste conserva restricciones a frente. El Repeat de dorso aparece deshabilitado y lo explica al operador.

Para una publicación deben distinguirse página editorial, posición impuesta, cara, pliego y ejemplar. Esa distinción permite comprobar que la lectura final tenga todas las páginas en orden, incluso cuando las posiciones de impresión no siguen el orden de lectura. La cantidad de formas repetidas no constituye por sí sola ese contrato editorial.

### 9.2. Ocho ideas de ampliación

#### 1. Secuencia editorial con blancos explícitos

Permitir ordenar páginas de varios assets, insertar blancos identificados, seleccionar rangos y separar tapa/interior. La herramienta debería advertir páginas omitidas o duplicadas. La preparación multipágina ya existe; lo nuevo sería el orden de lectura de la publicación.

Requiere un contrato editorial ligado a referencias estables de asset/página. Un blanco debe tener identidad explícita, sin fingir una fuente PDF. Las pruebas tendrían que cubrir rangos, archivos combinados, faltantes, blancos, undo/recarga y trazabilidad.

#### 2. Caras operativas y prueba de volteo

Completar la navegación frente/dorso, seleccionar otra fuente posterior y revisar ambas caras vinculadas, incluyendo una superposición de control. Aprovecharía `faces`, `front_source/back_source` y el compositor existentes.

El flip matemático debe validarse con una fixture asimétrica con flechas y numeración, y con una maqueta impresa/doblada cuando corresponda. También deben revisarse las restricciones actuales de creación y paste, conservando comandos reversibles.

#### 3. Documento con múltiples pliegos

Permitir navegar varios pliegos, conservar geometría propia por cada uno y exportarlos en orden elegido. Esto amplía el dominio de un montaje individual a una publicación que necesita varias hojas/caras.

La decisión contractual es importante: extender/versionar el layout o crear un documento editorial que referencie layouts. La implementación debe ser propiedad V2. Deben probarse referencias entre pliegos, revisiones, cambios aislados, orden/caras y exportación sin publicación parcial.

#### 4. Imposición grapada 2-up propia V2

Generar propuestas de parejas de páginas para doblar, apilar y grapar, con revisión antes de aplicar y conteo de ejemplares completos. Necesita un motor de paginación propio, construido sobre secuencia, caras y pliegos.

La aceptación debe incluir maquetas numeradas de 4/8/12/16 páginas, direcciones de encuadernación y orientaciones. La comprobación consiste en que la publicación terminada se lea en orden, además de medir el PDF impuesto. Los blancos necesarios deben ser explícitos.

#### 5. Firmas y partes de publicación

Agrupar cuadernillos y diferenciar tapa, interior, papeles, tirajes y orden de reunión. El operador podría definir tamaño de firma y revisar remanentes antes de exportar.

Requiere definir parte/firma/pliegos y las unidades de cantidad. Grapado, cosido y encolado tienen decisiones distintas. Las pruebas deben contemplar portadas separadas, firmas incompletas, blancos, multiplicidades y orden de salida.

#### 6. Compensación de creep controlada

Aplicar desplazamientos progresivos de contenido según la posición dentro del cuadernillo y su espesor, mostrando el valor por página. El offset interno actual es una base técnica parcial; aún no existe una regla editorial de compensación.

Se deben definir signo, referencia, medición, movimiento de marcas y excepciones. No corresponde copiar sin interpretación la convención de otro producto. Deben probarse interior/exterior, caras, giros, clipping, doble compensación y gráficos que cruzan páginas. No añadir bottling con giros arbitrarios como efecto lateral: el contrato actual restringe las rotaciones.

#### 7. Sangrado y medianil por borde editorial

Revisar separadamente lomo y borde exterior, páginas enfrentadas y continuidad gráfica. El sangrado uniforme y la decisión por trabajo ya existen; una política por borde sería una ampliación de contrato y geometría.

El riesgo principal es cortar diseño o invadir la página vecina. Se necesitan fixtures con imágenes cruzadas, cajas desplazadas y cobertura insuficiente. El espejo genérico no debe convertirse automáticamente en una solución para el lomo editorial.

#### 8. Prueba de lectura y ficha de fabricación

Ofrecer dos vistas vinculadas: lectura normal y pliegos impuestos. La ficha podría registrar página→firma/pliego/cara/posición, blancos, ejemplares completos, orientación, corte y plegado, siempre asociada a la revisión exportada.

Puede comenzar como diagnóstico o artefacto temporal antes de cambiar todo el layout. Su aceptación debe comprobar la presencia y destino de cada página. La simulación ayuda a revisar; no sustituye una prueba física de fabricación.

### 9.3. Dependencias entre las ideas

Como criterio técnico opcional, completar caras, secuencia editorial y prueba de lectura permite validar decisiones de uso. La imposición grapada depende después de múltiples pliegos. Firmas, creep y sangrado por borde requieren especificar fabricación y contratos anteriores. Este razonamiento no establece una cola obligatoria ni autoriza implementar automáticamente las ocho herramientas.

### 9.4. Fuentes primarias de la investigación

Estas fuentes fueron consultadas durante la segunda revisión; este documento consolida aquella investigación:

- [Adobe Acrobat — impresión de cuadernillos](https://helpx.adobe.com/acrobat/kb/print-booklets-acrobat-reader.html): disposición por cara/hoja, frente/dorso y dirección de encuadernación.
- [Adobe InDesign — configuración de cuadernillos](https://helpx.adobe.com/indesign/desktop/print/print-booklets/booklet-printing-settings.html): grapado, firmas, blancos, medianil, bleed entre páginas y creep.
- [Kodak Preps — bottling y shingling](https://workflowhelp.kodak.com/pages/viewpage.action?pageId=224648119): compensaciones, espesor, encuadernación y excepciones.
- [Kodak Preps 11 — guía oficial](https://www.workflowhelp.kodak.com/download/attachments/296223191/PREPS_v11_QuickStartGuide.pdf?api=v2): diferencias entre lista de lectura, contenido y posiciones de plantilla.
- [Heidelberg Prinect — notas oficiales](https://onlinehelp.prinect-lounge.com/App/App_release_notes/en/index.htm): pliegos plegados, esquemas, etiquetas y comportamiento de marcas durante creep.

## 10. Límites que permanecen y lectura del informe

El mapa es un inventario funcional de archivos y conexiones, no un grafo de cada símbolo/import ni una demostración de todas las combinaciones. Las pruebas aportan evidencia dentro de su cobertura. El proceso Flask continúa vinculado al registro legacy y la retención auxiliar no quedó conectada por esta revisión.

La navegación de caras y el dominio editorial siguen incompletos. Derivados permanecen separados de la salida básica. Los originales, geometría, locks, revisión optimista y comandos deben conservarse al ampliar el producto. Rendimiento 500, PDF/X, CTP y certificación de prensa siguen fuera de lo demostrado.

Este documento entrega la explicación de la segunda revisión y las opciones discutidas. Para localizar código, utilizar 44; para el registro operativo, 41; para la aceptación previa de salida habitual, 43. Las nuevas funciones deberán definirse y comprobarse según una solicitud concreta y la evidencia del sistema en ese momento.
