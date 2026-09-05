# Plan y trazabilidad del rediseño UX incremental del Editor Offset Visual V2

## 1. Estado y propósito

Fecha de creación: 2026-09-05.

Rama de trabajo prevista:

    codex/editor-offset-v2-ux-foundation

Estado inicial del documento: planificación aprobada para documentación; implementación de código todavía no iniciada.

Este documento define cómo mejorar la usabilidad y la organización visual del Editor Offset Visual V2 sin reescribir el editor ni adelantar funciones productivas que todavía no existen.

Sus objetivos son:

- conservar un mapa actualizado entre interfaz, JavaScript, backend, persistencia y pruebas;
- registrar las decisiones tomadas antes y durante el rediseño;
- separar mejoras visuales, cambios funcionales y trabajo productivo futuro;
- evitar que una reorganización de HTML o CSS rompa IDs, listeners, comandos, autosave o contratos;
- definir fases pequeñas, reversibles y verificables;
- establecer qué debe documentarse después de cada cambio;
- dejar preparada la interfaz para preview, PDF y CTP sin declarar esas capacidades como operativas.

Este documento es un plan vivo de fase. No reemplaza el estado operativo registrado en:

- 18_ESTADO_ACTUAL_POST_EXPLORACIONES_1_A_4_V2.md;
- 01_CONTRATO_LAYOUT_V2.md;
- 02_KERNEL_GEOMETRICO_V2.md;
- 03_ADAPTADOR_SALIDA_V2.md;
- 11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md.

El documento 18 debe conservarse como fotografía histórica previa al rediseño. Este documento 19 registrará la evolución de la fase. Cuando la fase termine y haya sido validada, deberá redactarse un nuevo estado operativo posterior al rediseño.

## 2. Evidencia utilizada

### Confirmado por ejecución y documentación operativa

- cuatro exploraciones interactivas registradas en el documento 18;
- editor funcionando con un job real, un asset, un work y ocho slots;
- persistencia, revisión optimista, undo/redo, autosave y recarga operativos en los recorridos explorados;
- herramientas principales de selección, drag, Repeat, clipboard, alineación, matriz, reglas, guías, snap y medición presentes;
- problemas reproducidos en nudge, eliminación con dependencias, matriz, estados temporales y recuperación de conflicto;
- incomodidad responsive observada alrededor de 1050 px y 820 px;
- ausencia de preview productivo V2, PDF final V2, CTP productivo V2 y preflight final.

### Confirmado por código

- la estructura visual vive principalmente en templates/editor_offset_visual_v2.html;
- el contrato de referencias DOM está centralizado en static/js/editor_offset_v2/dom_refs.js;
- la composición principal y los listeners de alto nivel viven en static/js/editor_offset_v2/bootstrap.js;
- el canvas y parte del inspector son renderizados por static/js/editor_offset_v2/canvas_renderer.js;
- los paneles especializados conservan responsabilidades separadas;
- el layout de escritorio usa cuatro columnas en static/css/editor_offset_visual_v2.css;
- existen reglas responsive específicas para 1050 px y 820 px;
- JobService crea actualmente pliegos de 700 x 500 mm con márgenes imprimibles en cero;
- POST /api/editor-offset-v2/jobs acepta actualmente solo el campo opcional name;
- el botón Nuevo job crea el job directamente y navega a su URL, sin un paso de configuración;
- Layout V2 ya contiene sheet.size_mm y sheet.printable_margins_mm.

### Pendiente de confirmación automatizada

- la suite Python no fue ejecutada durante las exploraciones;
- los tests Node no fueron ejecutados durante las exploraciones;
- la suite Playwright existente no fue ejecutada durante las exploraciones;
- todavía no existen baselines automatizados específicos para el rediseño;
- todavía no se ha validado la propuesta visual en HTML/CSS real.

## 3. Decisión principal del rediseño

El rediseño será incremental y utilizará el editor actual como base.

No se construirá una interfaz nueva desde cero. Se conservarán:

- la aplicación Flask actual;
- el template V2 actual;
- el canvas SVG actual;
- los módulos JavaScript actuales;
- el store y el command system;
- undo y redo;
- autosave y control de revisión;
- selección, drag y Alt+drag;
- Repeat y herramientas manuales;
- assets, works y slots;
- los contratos de Layout V2;
- las rutas públicas V2;
- el aislamiento respecto de V1.

La mejora se concentrará en jerarquía, agrupación, legibilidad, descubrimiento de herramientas, estados, configuración del pliego y adaptación responsive.

## 4. Referencias visuales

### Estado actual usado como base

Captura real principal:

    output/playwright/v2-fourth-exploration-20260904/01-baseline.png

Otras evidencias visuales:

    output/playwright/v2-baseline-20260830/
    output/playwright/v2-second-exploration-20260903/
    output/playwright/v2-third-exploration-20260903/
    output/playwright/v2-fourth-exploration-20260904/

### Propuesta visual incremental

Archivo conservado con esta documentación:

    DOCS/OFFSET/V2/assets/19_propuesta_visual_redisenio_incremental_v2.png

Vista:

![Propuesta visual incremental del Editor Offset Visual V2](assets/19_propuesta_visual_redisenio_incremental_v2.png)

La imagen es una referencia de dirección visual, no una especificación ejecutable ni una prueba de funcionamiento.

Si la imagen contiene textos aproximados, iconos ilustrativos o controles aún inexistentes, prevalecen las decisiones y restricciones escritas en este documento.

## 5. Objetivo del producto

El operador debe poder comprender y ejecutar el flujo principal del montaje sin recorrer un inspector de varios miles de píxeles ni buscar las acciones más importantes entre controles secundarios.

Flujo de producto propuesto:

    Preparar -> Imponer -> Ajustar -> Validar -> Salida

Significado:

1. Preparar: crear job, configurar pliego, importar PDF y definir work.
2. Imponer: configurar y aplicar Repeat; en el futuro podrá alojar otros motores si se implementan.
3. Ajustar: seleccionar, mover, duplicar, alinear, distribuir, medir y editar propiedades.
4. Validar: reunir avisos geométricos y, en el futuro, el preflight productivo.
5. Salida: alojar preview, PDF y CTP cuando existan realmente.

Los pasos representan una jerarquía de trabajo. No deben presentarse todos como funciones completas si su backend todavía no existe.

## 6. Criterios de éxito

El rediseño se considerará exitoso cuando:

- el editor siga abriendo los mismos jobs V2;
- el layout persistido conserve el mismo contrato;
- todas las herramientas existentes continúen siendo alcanzables;
- las acciones primarias sean visibles sin recorrer todo el inspector;
- la configuración del pliego tenga una ubicación clara;
- el canvas siga siendo la superficie dominante;
- el inspector responda a la selección y muestre primero la información relevante;
- Repeat sea localizable desde la etapa de imposición;
- los avisos geométricos y de compatibilidad tengan revisión y procedencia comprensibles;
- PDF y CTP no aparezcan como operativos antes de su implementación;
- teclado, foco, aria-live y estados disabled continúen funcionando;
- los recorridos críticos no produzcan pageerror ni errores de aplicación en consola;
- 1440 px ofrezca la experiencia principal completa;
- 1050 px y 820 px mantengan accesibles las tareas esenciales mediante una composición decidida, no solo columnas comprimidas;
- undo/redo, autosave, recarga y conflicto sigan siendo correctos después de la reorganización.

## 7. Alcance aprobado para esta fase

### Dentro del alcance

- mejorar tipografía, contraste, espaciado y tamaños de controles;
- reducir densidad visual innecesaria;
- establecer una navegación de flujo comprensible;
- reorganizar las herramientas existentes por tarea;
- conservar o envolver elementos existentes sin cambiar inicialmente sus IDs;
- priorizar importar PDF, configurar pliego, imponer, ajustar y validar;
- hacer contextual el inspector;
- reducir scrolls anidados y bloques siempre abiertos;
- mejorar feedback de selección, revisión, guardado, conflicto y diagnóstico;
- diseñar una configuración de pliego segura;
- mejorar responsive y accesibilidad operativa;
- crear pruebas de caracterización antes de la implementación;
- documentar cada cambio real y su validación.

### Fuera del alcance

- preview productivo V2;
- generación PDF final V2;
- producción CTP V2;
- preflight PDF profundo;
- motor PDF nativo V2;
- Nesting o Hybrid V2;
- dúplex productivo y navegación completa front/back;
- resize;
- transformaciones internas del artwork;
- rotación libre;
- cambio de Layout Schema Version;
- refactor masivo de JavaScript;
- migración a framework frontend, TypeScript o bundler;
- cambios en V1;
- conexión directa a montaje_offset_inteligente.py;
- cambios oportunistas en engines/step_repeat_pro_engine.py.

Estas exclusiones no impiden reservar lugares comprensibles para capacidades futuras. Impiden presentarlas como terminadas o mezclarlas con la fase UX.

## 8. Jerarquía visual objetivo

### Encabezado global

Debe conservar:

- identidad Editor Offset Visual V2;
- nombre e ID del job;
- revisión;
- estado de guardado;
- Deshacer;
- Rehacer;
- Guardar;
- Atajos;
- Nuevo job;
- recuperación de conflicto cuando corresponda.

Mejora prevista:

- separar información del job de acciones globales;
- hacer Guardar y Nuevo job distinguibles sin competir entre sí;
- mostrar conflictos y cambios sin guardar con mensajes comprensibles;
- evitar que datos esenciales desaparezcan sin alternativa responsive.

### Navegación de flujo

Se propone una franja compacta con:

- Preparar;
- Imponer;
- Ajustar;
- Validar;
- Salida.

Esta franja no debe cambiar automáticamente el layout persistido. Su primera implementación puede controlar únicamente qué grupo de herramientas está visible.

El estado activo debe ser temporal y no necesita formar parte de Layout V2 salvo decisión posterior explícita.

### Herramientas laterales

Debe conservar las herramientas actuales, especialmente Selección, creación de slot cuando corresponda y Eliminación.

Mejora prevista:

- targets mayores;
- etiquetas legibles;
- estados activos y disabled inequívocos;
- tooltips o ayudas breves para acciones no evidentes;
- no duplicar acciones destructivas en varios lugares sin una jerarquía clara.

### Panel de preparación

Debe reunir:

- assets PDF;
- carga de PDF;
- selección de página y caja;
- metadata de medida;
- creación de work;
- cantidad y rotaciones permitidas;
- creación de slot y sustitución de fuente cuando corresponda.

Mejora prevista:

- distinguir fuente PDF de work lógico;
- ordenar los campos por dependencia;
- evitar que la lista de slots desplace las tareas primarias;
- mostrar errores de upload y validación junto al control que los originó.

### Canvas

Debe seguir siendo la mayor superficie visible.

Debe conservar:

- SVG del pliego;
- slots y artwork aproximado;
- selección;
- drag;
- marquee;
- pan y zoom;
- reglas, guías, snap y medición;
- estados fuera de pliego, fuera de imprimible y overlap;
- etiquetas temporales.

Mejora prevista:

- mostrar el tamaño del pliego junto al canvas;
- acercar acciones frecuentes como duplicar, alinear, distribuir y Repeat sin ocultar el pliego;
- mostrar un resumen geométrico compacto;
- no convertir el canvas en un dashboard.

### Inspector contextual

El inspector actual contiene operaciones de objeto, posición, alineación, precisión, selección, árbol, Repeat y output en una sola columna larga.

La propuesta separa esas responsabilidades por contexto:

- selección de slot: geometría, rotación, locks y operaciones;
- selección múltiple: alineación, distribución y gaps;
- imposición: Repeat;
- precisión: reglas, guías, snap y medición;
- objetos: árbol, filtros y visibilidad;
- validación: problemas geométricos y output-capabilities;
- salida: estado pendiente hasta que exista implementación productiva.

No se eliminarán paneles existentes para simplificar visualmente. Primero se hará un inventario de cada control y su consumidor.

### Barra de estado

Debe conservar:

- cara activa;
- cursor cuando corresponda;
- zoom;
- restablecer vista;
- etiquetas;
- cantidad de slots;
- mensajes globales.

Mejora prevista:

- distinguir estado persistente, estado temporal y feedback de herramienta;
- evitar que un mensaje de medición o diagnóstico antiguo parezca vigente;
- mantener información crítica visible en responsive.

## 9. Mapa de conexiones de la interfaz

| Superficie | HTML actual | JavaScript principal | Estado o contrato relacionado | Riesgo al moverla |
| --- | --- | --- | --- | --- |
| Job y acciones globales | ev2-job-name, ev2-job-id, ev2-revision, ev2-save, ev2-new-job | bootstrap.js, autosave.js | revision, cambios locales, conflicto | Alto |
| Herramienta de selección | ev2-select-tool | bootstrap.js, interactions.js, command_registry.js | selección temporal y pointer sessions | Alto |
| Eliminación | ev2-delete-slots, ev2-object-delete | command_registry.js, commands.js, edit_policy.js | locks y generated_by.source_slot_id | Alto |
| Upload PDF | ev2-asset-upload-form y controles ev2-asset-* | assets_panel.js, api_client.js | assets inmutables, revisión, archivos físicos | Alto |
| Creación de work | controles ev2-work-* | assets_panel.js, commands.js | works, fuentes, trim, bleed, cantidad | Alto |
| Canvas | ev2-canvas | canvas_renderer.js, interactions.js, geometry_view.js | Layout V2, coordenadas, selección, viewport | Alto |
| Operaciones de objeto | controles ev2-object-* | objects_panel.js, command_registry.js, object_operations.js | comandos, clipboard, locks | Alto |
| Posición precisa | controles ev2-position-* | position_inspector.js, nudge_controller.js | centro trim, selección, historial | Alto |
| Alineación y matriz | controles ev2-arrangement-* | arrangement_panel.js, alignment_operations.js | selección, slot clave, comandos | Alto |
| Precisión | controles ev2-precision-* | precision_panel.js, precision_tools.js, snap_engine.js | estado temporal, geometría | Moderado |
| Selección avanzada y árbol | ev2-object-tree y controles relacionados | advanced_selection.js, object_tree.js | selección y visibilidad temporal | Moderado |
| Repeat | controles ev2-repeat-* | repeat_panel.js, api_client.js | propuesta temporal, base_revision, ApplyRepeatCommand | Alto |
| Compatibilidad de salida | controles ev2-output-* | output_panel.js, api_client.js | revisión persistida analizada | Alto |
| Barra de estado | ev2-active-face, ev2-zoom, ev2-slot-count, ev2-status-message | canvas_renderer.js, bootstrap.js, varios paneles | mezcla de estados globales y temporales | Moderado |

## 10. Contratos que deben preservarse

### Contrato Layout V2

No cambiar durante las fases puramente visuales:

- layout_schema_version = 2;
- milímetros;
- origen inferior izquierdo;
- centro trim como posición persistida;
- rotaciones cardinales;
- bleed separado;
- referencias entre assets, páginas, cajas, works y slots;
- IDs únicos;
- generated_by;
- locks;
- revisión optimista;
- estado temporal fuera del layout.

### Contrato DOM

Regla inicial:

- conservar IDs ev2-* existentes;
- conservar data attributes funcionales;
- conservar names de radio buttons y formularios;
- conservar relaciones label/for;
- conservar aria-live y role;
- conservar los elementos requeridos por DomRefs.collect();
- no duplicar un mismo ID al mostrar una herramienta en otra región;
- si una acción necesita dos accesos visuales, ambos deben delegar en la misma acción del command registry.

Antes de renombrar o retirar cualquier control se debe buscar:

- referencia en dom_refs.js;
- listener en bootstrap.js o paneles;
- uso en render;
- uso en tests Node;
- uso en Playwright;
- dependencia de accesibilidad o foco.

### Contrato de acciones

Las nuevas superficies visuales no deben implementar mutaciones paralelas.

Las acciones deben seguir pasando por:

- command_registry.js cuando exista una acción registrada;
- commands.js para mutaciones reversibles;
- store.executeCommand() para historial;
- edit_policy.js para locks;
- autosave para persistencia;
- api_client.js para comunicación HTTP.

## 11. Configuración del pliego

### Estado actual confirmado

- el job se crea directamente desde Nuevo job;
- el frontend envía un body vacío o solo name;
- el endpoint de creación rechaza campos distintos de name;
- JobService inicializa sheet.size_mm en 700 x 500 mm;
- JobService inicializa los cuatro márgenes imprimibles en 0 mm;
- el contrato Layout V2 ya posee tamaño y márgenes;
- no existe actualmente un control de interfaz para configurarlos.

### Resultado deseado

El operador debe poder:

- seleccionar un formato predefinido o ingresar ancho y alto;
- elegir orientación sin perder la medida original;
- configurar márgenes imprimibles;
- ver una vista previa del área útil;
- conocer cuántos slots quedarían fuera del pliego o del área imprimible;
- confirmar el cambio de forma explícita cuando ya existan slots.

### Política SAFE propuesta

- no escalar automáticamente works, slots ni artwork;
- no mover automáticamente slots existentes sin una acción explícita posterior;
- validar ancho y alto mayores que cero;
- impedir márgenes negativos;
- impedir que izquierda + derecha alcance o supere el ancho;
- impedir que inferior + superior alcance o supere el alto;
- recalcular geometría visual después del cambio;
- invalidar o marcar pendiente output-capabilities al cambiar la revisión;
- aplicar el cambio mediante un comando reversible;
- incluirlo en undo/redo y autosave;
- mantener compatibilidad con jobs existentes;
- conservar 700 x 500 mm como fallback mientras no se apruebe otra política.

### Decisiones todavía abiertas

1. ¿La configuración debe ocurrir antes de crear el job o inmediatamente después?
2. ¿Se permitirá modificar el pliego cuando existan slots fuera de bounds?
3. ¿La confirmación mostrará solo conteos o una lista de slots afectados?
4. ¿Los presets pertenecerán al frontend, a configuración global o al layout?
5. ¿Se guardará el último formato usado por operador?
6. ¿Un cambio de orientación intercambia ancho y alto o usa presets separados?

### Impacto probable

Frontend:

- templates/editor_offset_visual_v2.html;
- static/css/editor_offset_visual_v2.css;
- static/js/editor_offset_v2/dom_refs.js;
- static/js/editor_offset_v2/bootstrap.js;
- static/js/editor_offset_v2/commands.js;
- static/js/editor_offset_v2/command_registry.js;
- static/js/editor_offset_v2/canvas_renderer.js;
- posiblemente un nuevo módulo específico para el panel de pliego.

Backend, solo si se configura antes de crear el job:

- editor_offset_v2/blueprint.py;
- editor_offset_v2/application/job_service.py;
- tests del servicio y del endpoint.

El cambio puede ser aditivo dentro de Layout V2 porque los campos ya existen. Esto es una inferencia de planificación, no una autorización para cambiar el endpoint ni una decisión definitiva sobre versionado.

## 12. PDF, validación y CTP futuros

### Situación actual

- output-capabilities es un diagnóstico limitado;
- no es preview;
- no genera PDF;
- no es preflight final;
- no valida todos los problemas geométricos;
- no existe producción CTP V2;
- el adaptador temporal no equivale a un motor de salida completo.

### Representación permitida durante el rediseño

La interfaz puede mostrar:

- una etapa Validar;
- el diagnóstico output-capabilities con revisión analizada;
- problemas geométricos ya calculados por el frontend;
- una etapa Salida marcada como pendiente;
- texto informativo indicando que PDF y CTP se incorporarán después.

La interfaz no debe mostrar como operativos:

- Generar PDF;
- Preview productivo;
- Enviar a CTP;
- Trabajo listo para imprenta;
- preflight aprobado;
- dúplex validado.

### Regla de ramas futuras

Después de estabilizar y cerrar la base UX, las capacidades productivas deben trabajarse en ramas independientes, por ejemplo:

    codex/editor-offset-v2-pdf-output
    codex/editor-offset-v2-ctp-production

Los nombres son propuestas y no crean esas ramas.

## 13. Plan SAFE por fases

### Fase 19-0: documentación y baseline visual

Estado: en curso.

Objetivos:

- conservar la propuesta visual;
- registrar decisiones, alcance y no objetivos;
- mapear controles actuales y consumidores;
- establecer la matriz inicial de trazabilidad.

Cambios permitidos:

- documentación y recursos visuales de documentación.

Gate de salida:

- documento 19 revisado;
- propuesta visual aceptada o refinada;
- ninguna modificación de código mezclada.

### Fase 19-A: caracterización previa

Estado: pendiente de autorización.

Objetivos:

- congelar el comportamiento actual antes de mover la interfaz;
- capturar errores JavaScript además del resultado funcional;
- establecer screenshots comparables en estados representativos.

Cobertura focalizada:

- creación de job;
- upload y creación de work;
- creación de slot y Repeat;
- selección, drag y Alt+drag;
- undo/redo/autosave/recarga;
- locks;
- nudge sin pageerror;
- delete con dependientes;
- matriz y segundo submit;
- conflicto 409;
- invalidación del diagnóstico de salida;
- responsive en 1440, 1050 y 820 px;
- consola limpia en recorridos críticos.

Gate de salida:

- comportamiento actual registrado;
- fallos conocidos reproducidos por tests específicos;
- baselines independientes de IDs aleatorios y timestamps;
- ninguna corrección mezclada con la caracterización.

### Fase 19-B: estabilización mínima

Estado: pendiente.

Orden recomendado:

1. corregir nudge y su batching;
2. aplicar una política aprobada para delete con dependientes;
3. invalidar o marcar obsoleto output-capabilities;
4. proteger la matriz contra el segundo submit accidental;
5. mejorar recuperación de conflicto;
6. sincronizar feedback temporal de clipboard y medición.

Gate de salida:

- tests focalizados en verde;
- pageerror y consola limpios;
- sin cambio visual amplio;
- cada corrección documentada por separado.

### Fase 19-C: fundamentos visuales

Estado: pendiente.

Alcance:

- tipografía;
- tamaños mínimos de texto;
- tamaños de botones;
- contraste;
- espaciado;
- divisores;
- estados focus, hover, active y disabled;
- reducción de bordes y cajas anidadas;
- variables CSS reutilizables cuando no alteren comportamiento.

Restricción:

- no mover todavía controles entre módulos;
- no cambiar IDs;
- no introducir acciones nuevas.

Gate de salida:

- comparativa visual en el mismo viewport;
- herramientas actuales operativas;
- foco visible;
- ausencia de clipping y overflow nuevo.

### Fase 19-D: jerarquía y organización funcional

Estado: pendiente.

Alcance:

- navegación Preparar, Imponer, Ajustar, Validar y Salida;
- agrupación del inspector por contexto;
- acceso visible a acciones frecuentes;
- reubicación controlada de paneles existentes;
- reducción de scrolls anidados;
- estado temporal del modo activo.

Restricciones:

- mantener los mismos consumidores JavaScript;
- no duplicar mutaciones;
- no eliminar controles no auditados;
- Salida debe continuar pendiente;
- navegación no debe modificar Layout V2.

Gate de salida:

- inventario control por control reconciliado;
- todos los IDs requeridos presentes una sola vez;
- recorridos Playwright actualizados sin perder cobertura;
- atajos y foco validados.

### Fase 19-E: configuración funcional del pliego

Estado: pendiente de decisiones de producto.

Alcance:

- formulario de medida y márgenes;
- presets si se aprueban;
- validación;
- impacto geométrico visible;
- comando reversible;
- autosave y persistencia;
- compatibilidad con jobs existentes.

Gate de salida:

- política de cambio aprobada;
- pruebas de contrato y comandos;
- prueba Playwright de creación y modificación;
- slots nunca escalados ni movidos silenciosamente;
- revisión e invalidación de output coherentes.

### Fase 19-F: responsive y accesibilidad operativa

Estado: pendiente.

Alcance:

- estrategia explícita para 1440, 1050 y 820 px;
- paneles colapsables o modos cuando no caben cuatro columnas;
- navegación por teclado;
- orden de foco;
- labels y nombres accesibles;
- aria-live sin anuncios duplicados;
- targets táctiles razonables;
- zoom del navegador y textos ampliados.

Gate de salida:

- tareas principales accesibles en los tres anchos;
- canvas no queda inutilizable;
- no existen controles críticos inaccesibles;
- sin nuevos errores de consola.

### Fase 19-G: cierre y documentación de estado

Estado: pendiente.

Objetivos:

- ejecutar validaciones aprobadas;
- revisar el diff completo contra main;
- actualizar la trazabilidad real;
- registrar qué cambió y qué no;
- crear el nuevo estado operativo posterior al rediseño;
- mantener el documento 18 como evidencia histórica.

Gate de salida:

- criterios de aceptación cumplidos;
- riesgos residuales explícitos;
- documentación alineada con ejecución;
- branch preparada para revisión, sin commit o push automático.

## 14. Estrategia de pruebas

### Antes de modificar la interfaz

- ampliar Playwright para capturar pageerror;
- capturar errores de consola de aplicación;
- crear estados de caracterización reproducibles;
- comprobar recorrido base con job real aislado;
- capturar screenshots en viewport constante;
- documentar los fallos conocidos como fallos esperados antes de corregirlos.

### Durante cada fase

- ejecutar únicamente tests focalizados relacionados con el cambio;
- validar sintaxis JavaScript;
- comprobar git diff --check;
- comprobar manualmente el flujo modificado;
- verificar undo/redo/autosave/recarga cuando haya mutación;
- verificar layout_v2.json cuando cambie estado persistente;
- comparar visualmente antes y después en el mismo viewport;
- revisar foco, disabled, mensajes y consola.

### Antes del cierre

La suite completa solo se ejecutará con autorización expresa.

Validaciones candidatas:

    node --check static/js/editor_offset_visual_v2.js
    node --check static/js/editor_offset_v2/*.js
    venv/Scripts/pytest.exe tests/playwright/test_editor_offset_v2.py -s
    venv/Scripts/pytest.exe tests/editor_offset_v2
    git diff --check

Estos comandos son una planificación. La creación de este documento no los ejecutó.

## 15. Riesgos y contención

| Riesgo | Nivel | Contención |
| --- | --- | --- |
| Romper listeners al mover HTML | Alto | Conservar IDs, revisar DomRefs y ejecutar caracterización |
| Duplicar acciones con implementaciones distintas | Alto | Delegar siempre en command registry o módulo propietario |
| Alterar historial/autosave desde controles nuevos | Alto | Usar comandos reversibles y pruebas de revisión |
| Ocultar herramientas avanzadas | Moderado | Inventario control por control y rutas de acceso verificadas |
| Mezclar estado de navegación con Layout V2 | Moderado | Mantener modo activo como estado temporal |
| Presentar PDF/CTP como operativos | Alto | Etiquetar Salida como pendiente y no crear CTAs productivos |
| Cambiar pliego y dejar slots inválidos | Alto | Vista de impacto, confirmación y ninguna transformación silenciosa |
| Empeorar responsive al ampliar controles | Moderado | Diseñar por breakpoint y probar tareas, no solo screenshots |
| Perder accesibilidad al usar paneles colapsables | Moderado | Gestión de foco, aria-expanded y navegación por teclado |
| Refactor visual demasiado amplio | Alto | Separar CSS, jerarquía, pliego y responsive en cambios distintos |

## 16. Estrategia de rollback

- mantener cada fase en cambios pequeños y distinguibles;
- no mezclar estabilización con rediseño visual;
- no mezclar configuración del pliego con PDF o CTP;
- conservar el template funcional hasta que el reemplazo incremental pase los recorridos;
- evitar migraciones de layout en esta fase;
- conservar compatibilidad con jobs existentes;
- si una fase falla, revertir solo esa fase sin eliminar documentación ni evidencia;
- no usar reset destructivo ni sobrescribir trabajo del usuario.

## 17. Matriz inicial de trazabilidad

Estados permitidos:

- Propuesto;
- Aprobado;
- En caracterización;
- En implementación;
- Validado;
- Pospuesto;
- Bloqueado.

| ID | Requisito o hallazgo | Evidencia u origen | Fase | Estado inicial | Validación prevista |
| --- | --- | --- | --- | --- | --- |
| UX-001 | Conservar diseño V2 como base, sin reescritura | Decisión del usuario y propuesta visual | 19-0 | Aprobado | Revisión visual y diff limitado |
| UX-002 | Flujo Preparar-Imponer-Ajustar-Validar-Salida | Exploraciones y propuesta visual | 19-D | Propuesto | Recorridos por tarea y foco |
| UX-003 | Mejorar legibilidad y tamaño de controles | Exploraciones responsive | 19-C | Propuesto | Comparativa visual y accesibilidad |
| UX-004 | Mantener canvas como superficie principal | Propuesta visual | 19-C/19-D | Aprobado | Screenshots y medición de layout |
| UX-005 | Reducir longitud y densidad del inspector | Exploraciones 1-4 | 19-D | Propuesto | Acceso a todos los controles existentes |
| UX-006 | Dar acceso primario a Repeat y composición | Inventario del template | 19-D | Propuesto | Repeat calculate/apply y undo |
| UX-007 | Separar validación de salida productiva | Documento 18 y output_panel.js | 19-D | Aprobado | Revisión analizada visible y estado pendiente |
| UX-008 | Mejorar responsive en 1050 y 820 px | Capturas de exploración | 19-F | Propuesto | Playwright por viewport y tareas |
| UX-009 | Mantener barra de estado útil | Interfaz actual | 19-C/19-F | Propuesto | Zoom, cara, slots y feedback visibles |
| SHEET-001 | Mostrar medida del pliego junto al canvas | Falta observada por el usuario | 19-D | Aprobado | Render correcto del valor persistido |
| SHEET-002 | Permitir configurar medida y márgenes | Default fijo confirmado por código | 19-E | Propuesto | Contrato, comando, autosave y recarga |
| SHEET-003 | No escalar o mover slots silenciosamente | Política SAFE | 19-E | Propuesto | Test de impacto con slots existentes |
| STAB-001 | Nudge sin pageerror | Exploración 2 | 19-A/19-B | Pendiente | Playwright con captura de pageerror |
| STAB-002 | Delete respeta source_slot_id | Exploración 1 | 19-A/19-B | Pendiente | Test de referencia dependiente |
| STAB-003 | Output-capabilities no queda obsoleto sin aviso | Exploración 4 | 19-A/19-B | Pendiente | Cambio de revisión y panel invalidado |
| STAB-004 | Matriz evita segundo submit accidental | Exploración 3 | 19-A/19-B | Pendiente | Submit repetido controlado |
| STAB-005 | Conflicto 409 comprensible | Exploración 3 | 19-A/19-B | Pendiente | Dos clientes y recuperación visible |
| STAB-006 | Feedback temporal se limpia correctamente | Exploración 3 | 19-A/19-B | Pendiente | Clipboard y medición con undo/clear |
| OUT-001 | Preview V2 productivo | Documento 18 | Futura | Pospuesto | Contrato y comparación renderizada |
| OUT-002 | PDF final V2 | Documento 18 | Futura | Pospuesto | Fixtures PDF y tolerancias productivas |
| OUT-003 | Preflight productivo unificado | Documento 18 | Futura | Pospuesto | Gate de contrato, PDF, geometría y salida |
| CTP-001 | Producción CTP V2 | Documento 18 | Futura | Pospuesto | Contrato específico de plancha y marcas |
| DOC-001 | Registrar cada cambio material | Solicitud del usuario | Todas | Aprobado | Bitácora y matriz actualizadas |
| DOC-002 | Crear estado posterior al rediseño | Política documental | 19-G | Propuesto | Documento nuevo contrastado con ejecución |

## 18. Registro de decisiones

| ID | Fecha | Decisión | Motivo | Estado |
| --- | --- | --- | --- | --- |
| DEC-001 | 2026-09-05 | Mejorar el editor actual en lugar de reconstruirlo desde cero | Reduce riesgo y conserva funcionalidad ya comprobada | Aprobada |
| DEC-002 | 2026-09-05 | Usar una sola propuesta visual incremental | Evita dispersión y mantiene continuidad con V2 | Aprobada |
| DEC-003 | 2026-09-05 | Trabajar en codex/editor-offset-v2-ux-foundation | Aísla cambios respecto de main | Aplicada |
| DEC-004 | 2026-09-05 | Diseñar primero y agregar PDF/CTP después | La salida productiva todavía no existe en V2 | Aprobada |
| DEC-005 | 2026-09-05 | No presentar PDF o CTP como funciones activas | Evita una promesa falsa y errores operativos | Aprobada |
| DEC-006 | 2026-09-05 | Conservar el documento 18 como snapshot | Mantiene evidencia histórica verificable | Aprobada |
| DEC-007 | 2026-09-05 | Registrar el rediseño en un documento de fase separado | Permite trazabilidad sin reescribir historia | Aplicada |
| DEC-008 | Pendiente | Política de eliminación con dependientes | Afecta integridad referencial | Abierta |
| DEC-009 | Pendiente | Flujo exacto de configuración del pliego | Afecta creación, persistencia y geometría | Abierta |
| DEC-010 | Pendiente | Modelo responsive de paneles | Afecta acceso y foco | Abierta |

## 19. Bitácora de cambios de la fase

| Fecha | Cambio | Archivos | Comportamiento productivo | Validación | Resultado |
| --- | --- | --- | --- | --- | --- |
| 2026-09-05 | Creación de rama de trabajo | Git, sin archivos de producción | Sin cambios | git status | Rama creada limpia desde main |
| 2026-09-05 | Propuesta visual incremental | DOCS/OFFSET/V2/assets/19_propuesta_visual_redisenio_incremental_v2.png | Sin cambios | Inspección visual | Referencia conservada |
| 2026-09-05 | Creación del plan y trazabilidad | DOCS/OFFSET/V2/19_PLAN_Y_TRAZABILIDAD_REDISENO_UX_V2.md | Sin cambios | Revisión de estructura, espacios finales y git diff --check | Sin errores detectados |

Después de cada cambio futuro se debe agregar una fila con:

- fecha;
- objetivo;
- archivos tocados;
- comportamiento anterior y nuevo;
- pruebas ejecutadas;
- resultados;
- riesgo residual;
- documento relacionado.

## 20. Checklist obligatorio antes de comenzar código

- [ ] La propuesta visual fue revisada y aceptada como dirección.
- [ ] Las diferencias entre maqueta y funcionalidad real fueron identificadas.
- [ ] El inventario de controles e IDs está completo para la fase a modificar.
- [ ] Existen pruebas de caracterización focalizadas.
- [ ] Los fallos conocidos se reproducen de manera controlada.
- [ ] Se decidió la política de delete con dependientes.
- [ ] Se definió qué se cambia en una única fase.
- [ ] Se definieron criterios de aceptación y rollback.
- [ ] Se confirmó que Layout V2 no necesita cambiar para esa fase.
- [ ] Se confirmó que V1 no será tocado.
- [ ] Se obtuvo autorización para ejecutar las pruebas necesarias.
- [ ] Se obtuvo aprobación antes de cambiar contrato, persistencia, PDF, CTP o motores.

## 21. Qué debe actualizarse después de cada fase

Actualizar este documento cuando:

- cambie una decisión;
- cambie el estado de una fila de trazabilidad;
- se implemente una fase;
- se ejecute una validación;
- se descubra una dependencia nueva;
- cambie el alcance;
- un riesgo se resuelva o aumente;
- una pregunta abierta reciba respuesta.

Actualizar otros documentos solo cuando corresponda:

- 01_CONTRATO_LAYOUT_V2.md si cambia el contrato;
- 02_KERNEL_GEOMETRICO_V2.md si cambia geometría;
- 03_ADAPTADOR_SALIDA_V2.md si cambia la frontera de salida;
- 11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md si se resuelve una decisión transversal;
- documento específico de la herramienta si cambia su comportamiento;
- nuevo estado operativo al cerrar la fase.

No actualizar documentación para afirmar funciones que no fueron validadas.

## 22. Preguntas abiertas para las siguientes decisiones

1. ¿La propuesta visual queda aceptada como referencia principal o requiere una revisión?
2. ¿La navegación de flujo funcionará como modos exclusivos o como accesos que abren paneles?
3. ¿Qué acciones deben permanecer siempre visibles aunque cambie el modo?
4. ¿Dónde debe vivir el árbol de objetos en la experiencia final?
5. ¿Repeat será un modo completo o un panel contextual dentro de Imponer?
6. ¿La configuración del pliego ocurrirá antes de crear el job, después o en ambos lugares?
7. ¿Qué presets de pliego necesita realmente la imprenta?
8. ¿Qué advertencias deben bloquear salida y cuáles solo informar?
9. ¿Cómo se representará Salida mientras PDF y CTP estén pendientes?
10. ¿Qué comportamiento responsive es prioritario para operación real?

## 23. Próximo paso SAFE

El próximo cambio no debe ser todavía la reorganización del template.

El siguiente paso recomendado es preparar y aprobar la Fase 19-A de caracterización focalizada, comenzando por captura global de pageerror y consola y por los defectos ya reproducidos. Después debe ejecutarse la estabilización mínima de la Fase 19-B. Solo entonces debe comenzar el rediseño visual productivo de las Fases 19-C y 19-D.
