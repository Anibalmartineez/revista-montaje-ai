# Objetivo funcional del Editor Offset Visual V2

Estado del documento: propuesta de visión y roadmap, 2026-10-04; estado funcional actualizado tras MVP 1 + MVP 2 Frente/Dorso de un pliego. No modifica el contrato Layout V2 ni decide políticas de producción pendientes.

## Cómo leer este documento

Las etiquetas usadas en cada sección tienen significados distintos:

- **Existente:** recorrido implementado y verificable en el código actual. No implica certificación productiva.
- **Parcial:** existe una parte del recorrido, pero falta una capacidad necesaria para el objetivo descrito.
- **Objetivo propuesto:** dirección funcional para evaluar y desarrollar; todavía no es un requisito aprobado.
- **Decisión pendiente:** elección del propietario del producto o definición técnica/industrial que no puede inferirse del código.

[44 — Mapa de conexiones](44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md) describe la arquitectura real; [46 — Auditoría de cobertura](46_AUDITORIA_COBERTURA_Y_HALLAZGOS_V2.md) conserva riesgos, huecos y evidencia. Este 47 define hacia dónde podría evolucionar el producto. La bitácora operativa continúa en [41](41_TRABAJO_DIARIO_Y_BITACORA_V2.md). Las propuestas no autorizan implementar automáticamente todas las fases.

## 1. Visión del producto

**Objetivo propuesto:** una herramienta visual de preprensa y montaje gráfico para producción offset, que lleve PDFs fuente desde inspección y preparación hasta una salida física revisable. Debe permitir intervención manual, automatización acotada y trazabilidad de las decisiones que afectan geometría, contenido y archivo final.

La evolución prevista abarca preparación de piezas y análisis de cajas PDF; posicionamiento manual y Repeat; trabajos multipágina; frente/dorso; múltiples pliegos; imposición de revistas y firmas; sangrado, marcas y transformaciones; preflight, Preview, PDF final y preparación para flujo CTP. Esta enumeración es una **visión progresiva**, no un inventario de capacidades ya disponibles ni una promesa de PDF/X o compatibilidad CTP actual.

El operador debe poder entender qué fuente se usó, qué transformación se aplicó, qué revisión se guardó, qué bloqueó la salida y qué contiene el artefacto generado. La automatización debería producir un montaje inspeccionable y corregible, conservando fuentes originales y decisiones reversibles cuando sea posible.

## 2. Estado funcional actual

La clasificación se refiere al uso actual de V2, no a que una clase o campo exista. **ESTABLE / NÚCLEO** significa base interna relativamente madura con pruebas representativas; no significa aptitud industrial general. **FUNCIONAL PERO EN EVOLUCIÓN** funciona en recorridos acotados con límites conocidos. **PARCIAL** cubre solo parte del flujo del operador. **EXPERIMENTAL** existe bajo gate, ensayo o validación insuficiente para tratarlo como flujo habitual. **NO IMPLEMENTADO** no tiene recorrido operativo V2.

| Funcionalidad | Estado | Frontera comprobada |
|---|---|---|
| Jobs: creación, carga y estructura | ESTABLE / NÚCLEO | Job V2 con layout, carpetas y revisión propios. |
| Persistencia, CAS y conflictos | ESTABLE / NÚCLEO | PUT con base_revision, revisión servidor, locks y reemplazo atómico del layout; no transacción con derivados publicados antes del PUT. |
| Assets, carga PDF y hash de fuente | ESTABLE / NÚCLEO | Upload, identidad física y miniaturas; fuente original inmutable. |
| Inspección y selección de cajas PDF | FUNCIONAL PERO EN EVOLUCIÓN | Media/Crop/Trim/Bleed declaradas se distinguen; la cobertura de PDFs de preprensa complejos sigue limitada. |
| Canvas, selección, movimiento y rotación cardinal | ESTABLE / NÚCLEO | Edición de slots sobre un pliego con kernel geométrico y réplica visual; canvas no es prueba por sí solo de salida física idéntica. |
| Alineación, distribución, guías y snap | FUNCIONAL PERO EN EVOLUCIÓN | Herramientas manuales existentes; precisiones y escenarios extremos requieren evolución propia. |
| Locks, undo/redo y autosave | ESTABLE / NÚCLEO | Comandos reversibles y guardado coordinado; el recorrido de derivados con conflicto todavía requiere política y verificación integral. |
| Configuración de tamaño y márgenes de un pliego | FUNCIONAL PERO EN EVOLUCIÓN | Configura el pliego actual sin redefinir varios pliegos. |
| Repeat de piezas | FUNCIONAL PERO EN EVOLUCIÓN | Packer V2, propuesta temporal, add/replace, cantidades y aplicación reversible. No es imposición editorial. |
| Repeat con distintas páginas fuente | FUNCIONAL PERO EN EVOLUCIÓN | Varias páginas/piezas pueden proponerse y salir en el pliego actual; no implica varios pliegos ni firmas. |
| Sangrado, espejo y marcas básicas | FUNCIONAL PERO EN EVOLUCIÓN | Estrategias por trabajo y marcas físicas acotadas; no son certificación de tinta útil, separaciones o CTP. |
| Transformaciones internas del contenido | FUNCIONAL PERO EN EVOLUCIÓN | Escala, desplazamiento, giro y clipping definidos en recorridos actuales; falta paridad amplia con PDFs difíciles. |
| Derivados materializados | EXPERIMENTAL | Servicio, PDF/manifiesto y comando existen; gate apagado en arranque habitual, y un 409 posterior puede dejar archivos sin referencia. |
| Preflight físico y reportes | FUNCIONAL PERO EN EVOLUCIÓN | Diagnóstico por revisión y operación, con bloqueo de salida; no cubre aún todo el análisis industrial deseable. |
| Preview | FUNCIONAL PERO EN EVOLUCIÓN | PNG del pliego a DPI solicitado, bajo gate y presupuesto; representación de control, no artefacto productivo. |
| PDF final vectorial habitual | FUNCIONAL PERO EN EVOLUCIÓN | Compositor nativo conserva contenido vectorial en los casos soportados; no certifica PDF/X ni CTP. |
| PDF final raster explícito | EXPERIMENTAL | Rama implementada que inserta imágenes rasterizadas en PDF; faltan política funcional y validación estructural amplia. |
| Frente/dorso manual y salida de un pliego (MVP 1 + MVP 2) | FUNCIONAL PERO EN EVOLUCIÓN | Habilitación explícita, navegación temporal, edición independiente, Preview por cara y PDF `both` con orden/flip verificados en fixture asimétrico; Repeat Dorso, registro industrial y correspondencia automática pendientes. |
| Múltiples pliegos de un job | NO IMPLEMENTADO | Layout actual contiene un único objeto sheet. |
| Firmas, revistas e imposición editorial | NO IMPLEMENTADO | No hay secuencia editorial, asignación a firmas/pliegos ni plegado operativo. |
| Creep | NO IMPLEMENTADO | No existe ajuste de encuadernación como flujo V2. |
| Salida preparada/certificada para CTP | NO IMPLEMENTADO | El diagnóstico puede representar la operación CTP como no disponible; no existe entrega industrial certificada. |

## 3. Flujo de trabajo objetivo del operador

El flujo siguiente es una **propuesta de experiencia**, no una secuencia obligatoria actual. La columna de estado evita presentar pasos futuros como implementados.

| Paso | Acción esperada del operador | Estado |
|---|---|---|
| 1 | Crear un trabajo y recuperar su revisión. | Existente |
| 2 | Cargar uno o varios PDF, conservando originales. | Existente |
| 3 | Inspeccionar páginas, dimensiones, rotaciones y cajas disponibles. | Existente, con corpus limitado |
| 4 | Elegir la caja fuente apropiada y ver su efecto en la pieza. | Existente |
| 5 | Preparar sangrado o espejo cuando la política del trabajo lo permita; entender cobertura insuficiente. | Parcial para casos complejos |
| 6 | Colocar y corregir piezas manualmente, con locks e historial. | Existente |
| 7 | Elegir montaje manual, Repeat o futura imposición editorial. | Manual/Repeat existentes; imposición futura |
| 8 | Configurar tamaño y márgenes del pliego; más adelante, pliegos por trabajo. | Un pliego existente; varios futuros |
| 9 | Configurar, navegar y comprobar frente/dorso cuando corresponda. | Existente para edición manual de un pliego; registro industrial y Repeat Dorso pendientes |
| 10 | Revisar visualmente fuentes, colocaciones, marcas y caras. | Existente para un pliego; revisión editorial futura |
| 11 | Ejecutar preflight de la revisión guardada. | Existente |
| 12 | Resolver errores y volver a validar la revisión resultante. | Existente; diagnósticos futuros por ampliar |
| 13 | Generar Preview y revisar geometría/contenido. | Existente bajo gate |
| 14 | Generar PDF final de la revisión aprobada. | Existente para perfil nativo acotado |
| 15 | Inspeccionar físicamente páginas, cajas, contenido, marcas y correspondencia con Preview. | Parcial; aceptación industrial por definir |
| 16 | Entregar al flujo productivo/CTP según especificación de máquina y contrato de salida. | Futuro |

## 4. Tipos de trabajo a soportar

### A. Montaje manual

**Existente:** colocar, seleccionar, mover, rotar cardinalmente, alinear, bloquear, deshacer/rehacer y guardar piezas en un pliego. **Objetivo propuesto:** conservar control fino y correcciones posteriores a cualquier automatización; mostrar con claridad fuente/caja, dimensiones, sangrado y estado de salida. **Decisión pendiente:** qué herramientas adicionales de manipulación son prioritarias; resize sigue necesitando reglas explícitas de ancla, proporción, locks y contenido.

### B. Step & Repeat

**Existente:** Repeat V2 propone posiciones/cantidades sobre el pliego actual, con add/replace, tratamiento de faltantes, páginas distintas y aplicación reversible. **Objetivo propuesto:** que el operador entienda cantidades solicitadas/colocadas/sobrantes y restricciones antes de aplicar; que luego pueda editar el resultado. **Decisión pendiente:** preferencias de optimización, presets, reglas de máquinas y comportamiento sobre varios pliegos.

### C. Trabajo multipágina: cuatro conceptos distintos

- **PDF de varias páginas — existente:** una fuente puede contener varias páginas inspeccionadas individualmente.
- **Varias piezas/páginas en el mismo pliego — existente:** works y slots pueden referirse a fuentes distintas; Repeat multipágina coloca varios elementos.
- **Varios pliegos del mismo job — no implementado:** requeriría identidad, navegación, persistencia y salida por pliego/cara.
- **Imposición editorial — no implementada:** asignaría una secuencia de lectura a posiciones, firmas, pliegos y caras según encuadernación. Repetir páginas no realiza esa asignación.

### D. Frente/dorso

**Existente para un pliego, MVP 1 + MVP 2:** el operador habilita Dorso mediante un comando reversible, navega con tabs sin persistir `activeFace`, coloca y edita fuentes distintas por cara, valida hallazgos rotulados, genera Preview individual y PDF de ambas caras. `slot.source` permite elegir página/PDF sin modificar silenciosamente `work.back_source`. El flip `none`/`long_edge`/`short_edge` se aplica en salida; el canvas Dorso conserva coordenadas de edición. **Pendiente:** Repeat Dorso, correspondencia automática y aceptación de registro, pinza y volteo por perfil productivo.

### E. Revistas cosidas a caballo

**Futuro:** representar páginas de lectura, formato terminado, firmas, pliegos, caras y plegado; calcular orden de páginas y distribución; considerar creep, marcas y correspondencia frente/dorso. El operador debería poder revisar cada pliego y corregir un resultado automático antes del PDF final. Aquí no se especifican algoritmo, fórmulas ni defaults de taller.

### F. Otras encuadernaciones

**Futuro, sin prioridad automática:** lomo cuadrado/pegado, firmas múltiples y otros esquemas de imposición podrían necesitar políticas distintas de secuencia, retiro y tolerancias. Su soporte debe depender de trabajos reales y contrato de producción, no heredarse implícitamente del caso cosido a caballo.

## 5. Modelo futuro de pliegos

**Existente:** un Job V2 persiste un objeto sheet, caras habilitadas y una colección de slots; las fuentes viven como assets/works. Esta organización representa un pliego de trabajo. No se debe llamar “varios pliegos” a un PDF multipágina de origen ni a un PDF final con dos caras.

**Modelo conceptual propuesto, no schema decidido:**

Job → Sheets/Pliegos → Sides/Caras → Slots → Sources

Varios pliegos podrían permitir agrupar una revista o un trabajo que exceda un solo pliego, navegar cada cara, mantener identidad y revisión de cada resultado, y producir archivos en orden verificable. También ampliarían Repeat y operaciones manuales sin confundir posiciones de distintos pliegos.

**Impacto probable:** Layout y validación; Store, comandos, autosave e historial; selección/canvas; Repeat; preflight; snapshots; reportes y publicación de PDF; referencias de artefactos y tests. **Compatibilidad necesaria:** apertura segura de jobs V2 existentes, preservación de geometría, revisiones, fuentes y hashes, y ausencia de migración implícita destructiva. Este documento no cambia el schema ni decide si se versiona o migra el contrato.

**Preguntas abiertas:** ¿un sheet comparte tamaño, márgenes y marcas con otros? ¿Qué identidad y orden tienen pliegos/caras? ¿Qué edición es global y cuál local? ¿Cómo se guardan y bloquean revisiones? ¿Qué unidad representa un Preview, un reporte o un PDF final? ¿Cómo se recuperan jobs antiguos?

## 6. Frente y dorso

**Existente para un pliego:** Layout y UI admiten edición manual separada de front/back, navegación temporal, fuente efectiva por slot, preflight rotulado, Preview individual y PDF `both` con orden y flips comprobados físicamente en un caso sintético asimétrico. Repeat Dorso sigue deshabilitado. Esta capacidad no equivale a una verificación física de registro industrial frente/dorso.

**Objetivo propuesto:** ampliar la experiencia del pliego actual con Repeat Dorso explícito (MVP 3), y más adelante seleccionar cada cara de varios pliegos, vincular fuentes cuando el operador lo requiera, validar coincidencia, márgenes, pinza y zonas de marcas, y generar salidas trazables conforme a un perfil industrial definido.

**Decisiones pendientes:** convención industrial de volteo y registro, referencia de pinza, política de salida Frente aislada ante error exclusivo de Dorso, tratamiento productivo de piezas sin dorso y tolerancias que debe medir preflight. La edición independiente y los ejes geométricos de flip ya están definidos para este MVP.

## 7. Revistas e imposición editorial

**Visión funcional futura, no implementación actual:** el operador selecciona, por ejemplo, un PDF de 16 páginas, define formato terminado, tamaño de pliego y tipo de encuadernación, y decide una firma. El sistema calcula cuántos pliegos requiere, asigna páginas de lectura a caras/posiciones, presenta un Preview por pliego, permite correcciones manuales y finalmente genera archivos verificables. Creep, marcas y correspondencia frente/dorso forman parte del análisis. Este ejemplo no fija una secuencia numérica de imposición ni un algoritmo.

La operación debería dejar visibles: número de páginas de entrada; páginas faltantes o en blanco; agrupación en firmas; orden de impresión; pliego/cara/posición de cada página; sentido de plegado; márgenes y pinza; ajustes manuales posteriores; reporte de preflight editorial. La relación entre orden de lectura y orden de impresión debe ser auditable, no una caja negra.

**Decisiones pendientes del propietario:** múltiplos de páginas aceptados, inserción de blancos, sentido de plegado, orientación y retiro, creep automático o manual, pinza, marcas, tolerancias, tipos de encuadernación y tratamiento de cubiertas. La propuesta no implica que V2 ya sepa imponer una revista.

## 8. Evolución de Repeat

| Tema | Ya existente | Mejora incremental propuesta | Función futura o decisión |
|---|---|---|---|
| Cantidades | Solicitadas, colocadas, faltantes y sobreproducción explícita según política. | Hacer más legible la revisión previa a aplicar y su efecto en el pliego. | Política de cantidades entre varios pliegos. |
| Mezcla y páginas | Varios works y páginas fuente en propuesta; add/replace. | Presets reproducibles de distribución y restricciones, sin ocultar faltantes. | Repeat coordinado entre firmas/pliegos. |
| Separación, márgenes, zonas | Packer considera geometría, gap y obstáculos del pliego actual. | Controles y diagnóstico más claros para áreas prohibidas y preferencias. | Presets por máquina/plancha sujetos a contrato de producción. |
| Frente/dorso | Backend admite cara; UI fuerza frente en Repeat habitual. | Habilitar experiencia de dorso tras definir correspondencia/flip. | Distribución simultánea de ambas caras y varios pliegos. |
| Optimización | Distribuciones acotadas y presupuesto de esfuerzo. | Comparación explicable de alternativas y límites. | Objetivos industriales de optimización por definir. |

Repeat debe continuar entregando una **propuesta revisable**, aplicada mediante una operación reversible; no debe escribir silenciosamente un montaje definitivo.

## 9. Preparación PDF y contenido

**Existente:** selección de cajas realmente declaradas, rotación y escala/offset internos, sangrado por trabajo, espejo autorizado cuando falta cobertura, materialización opcional de derived, preparación para Preview/PDF y salida vectorial o raster según modo. Las fuentes originales se identifican por hash y permanecen inmutables.

**Objetivo propuesto:** que cada pieza muestre caja elegida, tamaño trim, bleed disponible o generado, transformación interna y expectativa de contenido vectorial. El operador debería entender cuándo una transformación requiere materializar un derivado, qué se pierde al rasterizar y qué salida concreta será publicada. La preparación debe ser reproducible desde fuente y decisiones guardadas.

**Fronteras pendientes:** fuentes incrustadas/subconjuntos, transparencias, imágenes pesadas, perfiles/OutputIntents y metadata conflictiva necesitan política explícita de aceptación, preservación o rechazo. El código actual rechaza OutputIntents en preparación nativa con un error explícito; eso no equivale a gestión de color. PDF/X es una posibilidad futura condicionada por requisitos de imprenta, perfiles, validación y pruebas; no es una entrega inmediata asumida.

## 10. Preflight objetivo

El preflight debería evaluar la **revisión y el artefacto que se pretende producir**, con severidad, localización del problema y acción posible para el operador. El preflight existente publica reportes y bloquea operaciones según hallazgos; Preview/PDF repiten preflight interno sobre su snapshot fresco. Un reporte anterior de la UI no autoriza automáticamente una generación posterior.

| Comprobación | Situación actual | Objetivo propuesto o decisión |
|---|---|---|
| Job/layout, referencias, IDs, geometría y posiciones fuera del pliego | Validación y diagnóstico físicos existentes. | Mantener localización precisa por slot, cara y futuro pliego. |
| Fuente faltante o hash alterado | Se comprueba identidad física antes de salida. | Mantener bloqueo y explicar recuperación segura. |
| Páginas y cajas PDF declaradas | Inspección física y selección actual. | Diagnosticar metadatos contradictorios y cajas inadecuadas para el uso elegido. |
| Bleed, clipping y marcas básicas | Política y hallazgos actuales en perfil nativo. | Verificar cobertura útil y perfil de marcas definido por producción. |
| Límites de páginas, píxeles, fuente y slots | Existen límites por módulo/operación. | Distinguir límite técnico, presupuesto operativo y especificación final. |
| Resolución de imágenes, fuentes y transparencias | No existe validación industrial integral demostrada. | Definir umbrales, casos permitidos y severidades según salida. |
| Colores, OutputIntents, perfiles y PDF/X | OutputIntents se rechaza en preparación; sin certificación de color/PDF/X. | Decidir política de gestión de color antes de ampliar soporte. |
| Correspondencia frente/dorso | Edición y salida de un pliego verificadas con fuente asimétrica; sin validación de registro industrial. | Comprobar orientación, registro, páginas y márgenes por cara/pliego según perfil productivo. |
| Secuencia editorial, firmas y páginas faltantes | No implementado. | Añadir solo cuando exista contrato de múltiples pliegos e imposición. |
| Preparación CTP | No operativa. | Validar plancha, pinza, separaciones, perfiles, naming y artefactos conforme al flujo decidido. |

El objetivo es que cada bloqueo sea verificable y que una advertencia no se confunda con autorización industrial. Los criterios de aceptación productiva deben fijarse por tipo de trabajo y perfil de salida.

## 11. Canvas, Preview y salida final

### Canvas: superficie de edición

**Existente:** muestra pliego, slots y arte mediante SVG, miniatura por caja o artwork preparado según el caso. Permite seleccionar y corregir. **Objetivo propuesto:** hacer visibles caja, bleed, cara, transformación, selección y advertencias sin presentar una aproximación raster de pantalla como prueba de archivo productivo.

### Preview: representación de control

**Existente:** compone el pliego y rasteriza a PNG a DPI solicitado, con límites y preflight propios. **Objetivo propuesto:** que el operador revise el resultado de la revisión guardada, cara/pliego y opciones elegidas, y pueda identificar diferencias frente al canvas antes de exportar.

### PDF final: artefacto productivo

**Existente:** salida nativa PDF de un pliego/caras soportadas; conserva el compuesto vectorial en modo habitual y tiene modo raster explícito. **Objetivo propuesto:** publicar un artefacto identificable, con páginas, cajas, contenido, resolución, marcas y metadata verificables para el perfil de producción elegido.

Estos tres recorridos no tienen por qué compartir implementación ni rasterizador. Sí deberían respetar una **misma geometría y contenido esperado** para una revisión/opciones equivalentes, dentro de tolerancias definidas. Hoy existen comparaciones puntuales, no paridad universal. Quedan por decidir la tolerancia visual/métrica, comportamiento de color, DPI, cajas de salida, política vector/raster, marcas avanzadas y requisitos CTP. Un HTTP 200 no constituye aceptación del PDF físico.

## 12. Política de derivados

**Existente:** el servicio materializa PDF y manifiesto antes de que el comando de UI añada source.derived al layout y autosave intente CAS. En un sondeo controlado, materialización 201 seguida de guardado stale 409 dejó ambos archivos sin referencia persistida. El arranque local habitual deja el gate de derivados apagado. Este documento no resuelve el destino de esos archivos.

**Objetivo funcional:** el operador nunca debe creer que una transformación quedó guardada si el layout no la referencia realmente. La UI debe distinguir “archivo preparado”, “cambio aplicado localmente”, “guardado confirmado” y “conflicto”. Cualquier recuperación debe preservar fuentes originales, historial y revisiones.

**Decisiones pendientes antes de establecer arquitectura:** cuándo materializar y cuándo usar preparación temporal; identidad/reutilización de derivado; invalidación al cambiar fuente/caja/transformación; limpieza o retención de huérfanos; recuperación tras fallo PDF–manifiesto; interacción con undo/redo, autosave y CAS; invocación y alcance de lifecycle; mensajes al operador; compatibilidad con jobs existentes. No se presupone eliminación inmediata ni reconciliación automática.

## 13. Experiencia de usuario

- Edición visual directa con medidas y selección comprensibles; mostrar la diferencia entre slot, footprint, trim y contenido.
- Operaciones reversibles y no destructivas cuando sea posible; un cambio automático debe quedar inspeccionable y editable.
- Estado de guardado inequívoco: borrador, guardando, guardado, conflicto y fallo de salida no deben verse iguales.
- Mensajes de preflight con ubicación, causa, severidad y acción sugerida; distinguir bloqueo de advertencia.
- Navegación de páginas, caras y futuros pliegos que conserve orientación y contexto del operador.
- Repeat y futura imposición deben crear un resultado que el operador pueda revisar y corregir manualmente antes de publicar.
- Progresión de controles: tareas habituales claras, opciones técnicas disponibles cuando afectan una decisión real, sin ocultar límites físicos.

Estos principios orientan diseño futuro; no invalidan los controles actuales por no cubrir todavía revistas o CTP.

## 14. Presets y automatización futura

**Candidatos conceptuales:** presets de pliego, máquina, marcas, Repeat, revista, CTP y plantillas de trabajo. Un preset debería declarar versión, parámetros visibles y compatibilidad con el tipo de job; aplicarlo no debería sobrescribir silenciosamente geometría, fuentes o correcciones manuales.

**Dependencias:** primero definir contratos de pliego/cara, perfil de salida y, para revistas, secuencia editorial. Un preset de máquina/CTP sin especificación industrial podría dar una falsa garantía. **Decisión pendiente:** qué parámetros son globales, cuáles se fijan por trabajo y quién mantiene presets verificados. No se implementa automatización en esta etapa documental.

## 15. Integración CTP futura

**Objetivo posible:** entregar archivos y un reporte compatibles con un flujo concreto de planchas, incluyendo formato de plancha, área imprimible, pinza, marcas, orientación, separaciones, perfiles, naming y validación previa. El operador debería poder identificar pliego, cara, revisión y perfil de máquina en cada artefacto.

**Estado actual:** CTP figura como operación no disponible en las decisiones de salida; PDF final V2 básico no equivale a archivo aprobado para CTP. **Decisiones pendientes:** máquina/RIP objetivo, requerimientos de color, PDF/X si corresponde, imposición/retirada de caras, tolerancias, separación de tintas, metadatos y método de aceptación física. No se afirma compatibilidad productiva presente.

## 16. Roadmap propuesto por dependencias, sin fechas

Las fases expresan un orden lógico, no una autorización automática ni una cola cerrada. Cada fase puede revisarse según trabajos reales y decisiones del propietario.

| Fase | Objetivo y alcance funcional | Dependencias | Riesgo principal | Criterio de “terminado” para la fase |
|---|---|---|---|---|
| **A — Consolidar núcleo actual** | Confirmar guardado/conflictos, referencias de derivados, integridad de salidas, paridad de casos habituales y diagnósticos que impiden pérdida de trabajo. | Definir política de huérfanos y de artefactos parciales; casos de aceptación física representativos. | Confundir un test verde o HTTP 200 con salida correcta; limpieza destructiva prematura. | Recorridos críticos completos y artefactos verificados, conflictos comprensibles, originales intactos y límites declarados. |
| **B — Mejorar herramientas actuales** | Refinar preparación/cajas/bleed, Repeat, visualización, preflight, Preview y modos PDF; considerar presets acotados. | Núcleo A confiable, políticas para PDF complejo y perfil de salida. | Aumentar opciones sin garantizar coherencia canvas/Preview/PDF o undo/autosave. | Operador puede preparar, comparar, corregir y producir los trabajos soportados con evidencia reproducible. |
| **C — Múltiples pliegos y correspondencia de caras** | Partir del Frente/Dorso manual ya operativo en un pliego; definir e implementar identidad/navegación de varios pliegos y correspondencia industrial de sus caras. | Contrato de datos/versionado, compatibilidad de jobs, reglas de flip/registro y revisión. | Migración incompatible o pérdida de geometría, historial y fuentes. | Job existente abre seguro; cada pliego/cara es editable y trazable; salidas y preflight cubren sus relaciones. |
| **D — Revistas e imposición editorial** | Añadir secuencia de páginas, firmas, plegado, creep y corrección manual por pliego/cara. | Fase C, decisiones de encuadernación y fixtures editoriales con resultados esperados. | Orden de páginas o correspondencia de caras incorrectos en un PDF aparentemente válido. | Un caso editorial definido produce orden verificable, Preview por pliego, correcciones persistidas y preflight de firmas. |
| **E — Producción avanzada** | Integración CTP, perfiles/PDF/X si se decide, presets de máquina y automatización acotada. | Requisitos de imprenta/RIP, gestión de color, tolerancias y aceptación física sobre fases anteriores. | Falsa declaración de compatibilidad industrial. | Artefactos y reportes aceptados contra un perfil productivo explícito y verificable, sin extrapolar a otros perfiles. |

## 17. Próximas funcionalidades candidatas, ordenadas por conveniencia

Estas son **candidatas**, no compromisos. “Schema” indica si parece necesario alterar el contrato persistido; toda respuesta requiere revisión de impacto antes de implementar.

| Orden y candidata | Utilidad para operador | Complejidad; dependencias | Impacto arquitectónico; schema; implementación incremental |
|---|---|---|---|
| 1. Estado confiable de materialización y guardado de derived | Evita creer que un cambio quedó guardado tras 409; permite decidir recuperación. | Media; política de huérfanos y estados UI. | Servicio–comando–autosave–CAS–lifecycle. Schema: por decidir según política. Incremental: sí, empezando por estado/mensaje y pruebas. |
| 2. Revisión comparada de canvas, Preview y PDF para perfiles soportados | Detecta desplazamientos y cambios de contenido antes de producción. | Media; fixture/asimetría, tolerancias, artefactos físicos. | Renderer, salida y QA; schema: no necesariamente. Incremental: sí, por casos concretos. |
| 3. Diagnóstico de preparación PDF más claro | Explica caja elegida, bleed insuficiente, espejo y hash/capacidad antes de colocar. | Media; contratos de caja/bleed actuales. | Inspector, UI y preflight; schema: no necesariamente para primera entrega. Incremental: sí. |
| 4. Revisión de Repeat y presets acotados al pliego actual | Hace comprensibles cantidades, zonas y alternativas; acelera trabajos repetidos. | Media; límites del packer y reglas de presets. | Repeat/UI; schema: posible si se persisten presets. Incremental: sí, sin varios pliegos. |
| 5. Perfil explícito de PDF raster/vector | Aclara DPI, cajas y preservación de contenido antes de exportar. | Media; política de salida y pruebas estructurales. | PDF final/preflight/UI; schema: campos actuales pueden bastar para primera etapa, verificar. Incremental: sí. |
| 6. Repeat Dorso en un pliego (MVP 3) | Automatiza propuestas y aplicación por cara sin alterar Frente. | Alta; fuente `back_source`, obstáculos, locks, cantidades y aceptación física. | Repeat/UI/servicio/packer, historial, persistencia y salida; reutilizar schema actual si el contrato lo permite. La navegación y edición manual de ambas caras ya están implementadas. |
| 7. Modelo de múltiples pliegos compatible con jobs existentes | Habilita trabajos extensos y base de imposición editorial. | Alta; contrato/versionado y migración segura. | Impacto transversal; schema: probablemente sí. Incremental: diseño/ensayo aislado antes de migrar jobs. |
| 8. Flujo piloto de revista cosida a caballo | Convierte páginas de lectura en pliegos/caras revisables para un caso real. | Muy alta; múltiples pliegos, frente/dorso, firma/plegado y criterios industriales. | Nuevo dominio editorial y salida; schema: sí o contrato nuevo. Incremental: solo después de un caso acotado y decisiones del propietario. |

El orden coloca primero confiabilidad y herramientas del pliego actual. Las candidatas 7–8 no se justifican solo por la existencia de PDFs multipágina o del campo imposition actual.

## 18. Qué no construir todavía

- **Imposición editorial completa antes del modelo de múltiples pliegos y correspondencia industrial de caras:** no habría identidad ni revisión confiable para asignar páginas a firmas y caras.
- **Limpieza automática de derivados antes de definir retención/recuperación:** un archivo sin referencia podría ser temporal, recuperable o realmente descartable; borrarlo sin contrato arriesga datos.
- **Integración CTP o presets de máquina sin perfil real de producción:** marcas y PDF básico no prueban aceptación por RIP/plancha.
- **Certificación PDF/X o aceptación general de OutputIntents sin gestión de color acordada:** el rechazo explícito actual no debe transformarse en aceptación silenciosa.
- **Optimización global de revista/varios pliegos sobre el packer actual:** Repeat distribuye piezas en el pliego actual; la secuencia editorial es otro problema.
- **Automatización que publique sin revisión del operador:** los riesgos actuales de conflicto, paridad y artefactos físicos exigen confirmación y trazabilidad.

Estas reservas no impiden explorar prototipos aislados o recopilar requisitos; impiden presentar una capacidad no validada como operativa.

## 19. Definición gradual de “terminado”

| Nivel | Significado | Evidencia mínima esperada |
|---|---|---|
| **Implementada** | Existe un recorrido ejecutable que cumple un contrato acotado. | Código integrado, límites explícitos, pruebas focalizadas y ausencia de mutación inesperada. |
| **Usable** | Un operador puede completar y corregir una tarea real comprendiendo estado y errores. | Recorrido UI/HTTP, guardado/recarga, undo cuando corresponda, mensajes y artefacto inspeccionable. |
| **Validada** | Los casos representativos y sus fallos están caracterizados. | Tests unitarios/integración/navegador pertinentes, fixtures realistas, paridad física/geométrica y concurrencia según riesgo. |
| **Apta para producción** | Un perfil de trabajo/salida concreto cumple requisitos acordados con la imprenta. | Contrato de aceptación, preflight y artefactos físicos auditados, límites medidos, recuperación y evidencia del flujo RIP/CTP si aplica. |

Una función puede estar terminada en un nivel y pendiente en el siguiente. “Apta para producción” siempre debe indicar **para qué perfil y tipo de trabajo**; no es una etiqueta global para todo V2.

## 20. Relación documental

- **44:** mapa de arquitectura, rutas y conexiones actuales.
- **46:** auditoría de cobertura, riesgos, deuda y decisiones abiertas observadas.
- **47:** visión funcional propuesta, frontera actual/futuro y roadmap por dependencias.
- **Futura GUIA_PARA_AGENTES_EDITOR_V2.md:** reglas operativas para agentes cuando arquitectura y objetivo funcional estén suficientemente estabilizados.
- **41:** trabajo diario y trazabilidad de intervenciones; no reemplaza el objetivo funcional.

Ante diferencias entre propuesta y comportamiento real, contrastar el código y los artefactos, registrar el conflicto y resolver la decisión de producto antes de tratar 47 como contrato implementable.
