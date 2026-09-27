# AGENTS.md — Reglas operativas de `revista-montaje-ai`

## Directriz actual para V2 — trabajo diario e independencia

Por instrucción explícita del usuario, la entrada de trabajo es [41 — Trabajo diario y bitácora V2](DOCS/OFFSET/V2/41_TRABAJO_DIARIO_Y_BITACORA_V2.md). Esta directriz sustituye las indicaciones inferiores que impongan jerarquía de documentos antiguos, lectura inicial obligatoria, roadmap, próximo gate o secuencia de fases para V2.

- Continuar desde el código existente, probando, corrigiendo y mejorando según lo observado y la solicitud de la sesión. El agente conduce el trabajo técnico; no exigir planes formales ni aprobaciones repetidas para ajustes rutinarios ya comprendidos en la tarea.
- Determinar el comportamiento con código, schema ejecutable, datos, pruebas y artefactos. Los documentos previos son referencias opcionales, no fuente de verdad ni agenda de trabajo. No confundir comportamiento existente con comportamiento correcto.
- V2 debe tener código propio, sin dependencia de código de producto compartido con V1 u otras superficies. Si se detecta una dependencia activa, tratarla como deuda que debe resolverse en V2, no como invariante que conservar. No arreglar V2 modificando motores comunes ni ocultar la dependencia tras wrappers. Verificar también dependencias transitivas y arranque antes de declarar independencia.
- Registrar en 41 lo observado, cambiado y verificado después de cada intervención. No mantener por rutina 20/40 como estados operativos paralelos ni crear otro plan o habilidad automáticamente.
- Preservar datos del usuario, originales, geometría, guardado e historial durante los cambios. Consultar decisiones incompatibles o destructivas cuando sea necesario. Las reglas de cuidado de datos y Git siguen aplicando; ninguna documentación acredita por sí sola el estado actual del código.

El resto de este archivo conserva reglas técnicas y referencias del trabajo previo. Aplicarlas cuando sean pertinentes y compatibles con esta directriz; sus planes y afirmaciones de estado necesitan contraste con la ejecución actual.

## 1. Propósito y prioridad actual

Este repositorio contiene `revista-montaje-ai` y varias superficies de preprensa.

El agente debe trabajar como:

- arquitecto técnico y analista SAFE;
- desarrollador senior;
- especialista en preprensa e imposición offset;
- revisor de contratos, persistencia y salida productiva;
- acompañante técnico del usuario.

El usuario define la visión y resuelve las decisiones incompatibles o destructivas que no puedan inferirse. El agente convierte esa visión en evidencia, documentación, pruebas y cambios pequeños y verificables, sin exigir planes formales para el trabajo rutinario autorizado.

La prioridad activa es **Editor Offset Visual V2**. Editor V1 se conserva como sistema legacy y superficie de compatibilidad. No tratar V1 y V2 como variantes intercambiables.

## 2. Regla SAFE central

Antes de un cambio importante:

1. determinar versión y alcance;
2. leer las instrucciones y documentación vigentes;
3. inspeccionar el código y la persistencia relacionados;
4. reconstruir el flujo real;
5. identificar contratos, dependencias y riesgos;
6. separar hechos, inferencias y pendientes;
7. elegir una intervención reversible y verificable;
8. consultar al usuario si una decisión incompatible, destructiva o de producto requiere su criterio;
9. implementar sin mezclar fases;
10. validar en proporción al riesgo;
11. actualizar la trazabilidad cuando cambie el comportamiento real.

No confundir velocidad con progreso. Al cambiar la salida, definir cómo se demuestra que sigue siendo correcta.

## 3. Resolución obligatoria de versión

### Cuando el trabajo es V2

Si la solicitud menciona V2, Layout V2, `editor_offset_v2`, `/editor_offset_visual_v2` o documentación `DOCS/OFFSET/V2/`:

- permanecer en superficies V2;
- no abrir, ejecutar ni modificar V1 salvo dependencia compartida demostrada;
- no ejecutar Playwright legacy como validación predeterminada;
- no reutilizar contratos, campos, rutas o persistencia V1 dentro de V2;
- tratar cualquier cruce V2/legacy como una frontera explícita de compatibilidad.

### Cuando el trabajo es V1

Trabajar sobre V1 únicamente cuando el usuario lo solicite o cuando un análisis de impacto confirme que una dependencia compartida exige revisarlo. Declarar ese alcance antes de actuar.

### Cuando la versión es ambigua

Usar el contexto más reciente y los archivos mencionados. Si elegir una versión alteraría materialmente el resultado, pedir una aclaración breve. No asumir V1 por costumbre.

## 4. Fuentes de verdad y jerarquía documental

Las instrucciones explícitas del usuario y las instrucciones superiores del entorno prevalecen. Este archivo gobierna el trabajo dentro del repositorio.

Para comportamiento actual:

- código ejecutable, schema, datos persistidos, ejecución y pruebas aportan evidencia;
- la documentación contractual define intención e invariantes;
- la documentación operativa vigente organiza el estado conocido;
- los documentos históricos conservan evidencia, pero no prueban el estado presente.

Si código y documentación se contradicen, no elegir silenciosamente. Registrar el conflicto y determinar si existe un defecto de implementación, documentación obsoleta o una decisión pendiente.

### Referencias para Editor V2

Partir de la solicitud y del código afectado. [41 — Trabajo diario y bitácora](DOCS/OFFSET/V2/41_TRABAJO_DIARIO_Y_BITACORA_V2.md) fija el método y registra intervenciones; [44 — Mapa de conexiones](DOCS/OFFSET/V2/44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md) localiza entradas, módulos, persistencia, pruebas y referencias. Consultar el contrato o antecedente específico solo cuando aporte a la tarea: 01 para Layout, 02 para geometría, 21 para preflight, 42 para preparación/Repeat y 43 para la salida PDF habitual. `README.md` clasifica los demás documentos. Los cortes 20/39/40 son referencias históricas o auditorías con límites propios; no son la entrada operativa ni una cola de trabajo obligatoria.

Para V1, consultar `DOCS/OFFSET/` solo cuando V1 o una dependencia legacy esté dentro del alcance. No usar esos documentos como contrato de V2.

## 5. Modos de trabajo y autorización

### Auditoría

- Inspección de solo lectura, salvo que la solicitud incluya expresamente crear o actualizar el informe, mapa o documentación.
- No ejecutar tests, iniciar Flask o usar recorridos interactivos si el usuario no lo autorizó.
- Entregar hechos, inferencias, riesgos y dependencias pertinentes; un plan solo cuando se solicite o resulte necesario para decidir un cambio.

### Alineación documental

- Contrastar documentación con código y evidencia actual.
- Clasificar cada documento como contractual, operativo, histórico, propuesta o pendiente.
- No reescribir evidencia histórica como si fuera estado presente.
- Modificar únicamente los documentos autorizados.

### Planificación

- No editar código.
- Definir objetivo, alcance, no objetivos, riesgos, contratos, archivos, fases, pruebas, aceptación y rollback.
- No convertir la planificación en un requisito previo para ajustes rutinarios ya autorizados.

### Implementación

- La solicitud debe autorizar el cambio.
- Mantener cada fase pequeña, reversible y trazable.
- No incorporar refactors oportunistas ni funciones futuras.
- Explicar qué cambió, qué no cambió y qué quedó pendiente.

### Validación

- Ejecutar solamente validaciones autorizadas y pertinentes al alcance.
- Una validación focalizada no demuestra que todo el repositorio esté verde.
- No llamar “preexistente” a un fallo sin ejecutar una comparación equivalente contra la base apropiada.

### Git

- No crear commits, merge, push, rebase ni borrar ramas salvo petición explícita.
- Las comprobaciones de estado y diff son de solo lectura y pueden usarse cuando sean relevantes.

## 6. Límite real de Editor V2

### Backend y contrato

- `app.py`: registra la superficie V2.
- `editor_offset_v2/blueprint.py`: rutas HTML y API V2.
- `editor_offset_v2/config.py`: flags, jobs root y límites.
- `editor_offset_v2/domain/`: Layout V2, validación, geometría, sangrado por trabajo, Repeat, marcas y contratos de salida.
- `editor_offset_v2/application/`: jobs, assets, artwork, Repeat, preflight, Preview, PDF final y derivados; el diagnóstico del puente histórico está separado.
- `editor_offset_v2/infrastructure/`: persistencia, inspección y preparación PDF, compositor nativo, snapshots de salida, miniaturas y adaptador Repeat propio; las sondas legacy son auxiliares.
- `editor_offset_v2/schemas/`: schemas de layout y reporte de preflight. La validación runtime del layout está en `domain/validation.py`.

### Frontend

- `templates/editor_offset_visual_v2.html`.
- `static/css/editor_offset_visual_v2.css`.
- `static/js/editor_offset_visual_v2.js`.
- `static/js/editor_offset_v2/`.

### Persistencia

- raíz predeterminada: `instance/editor_offset_v2_jobs/`;
- job: `instance/editor_offset_v2_jobs/<job_id>/`;
- layout: `layout_v2.json`;
- subdirectorios previstos: `assets/`, `derived/`, `previews/`, `outputs/` y `reports/`.

La raíz puede cambiar mediante configuración. Nunca fijar rutas absolutas del entorno del usuario dentro del contrato o del código productivo.

### Pruebas V2

- Python: `tests/editor_offset_v2/`.
- Fixtures: `tests/fixtures/editor_offset_v2/`.
- Node: `tests/editor_offset_v2/js/`.
- Playwright: `tests/playwright/test_editor_offset_v2.py`.
- Caracterización UX: `tests/playwright/test_editor_offset_v2_ux_characterization.py`.
- Integración de salida: `tests/playwright/test_editor_offset_v2_output_integration.py`.
- Preparación, Repeat nativo y sangrado: `tests/playwright/test_editor_offset_v2_preparation.py`, `test_editor_offset_v2_native_repeat.py` y `test_editor_offset_v2_work_bleed.py`.

El inventario completo de archivos y conexiones está en [44](DOCS/OFFSET/V2/44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md); revisar el árbol real antes de asumir que sigue completo.

## 7. V1 y dependencias compartidas

V1 vive principalmente en:

- `templates/editor_offset_visual.html`;
- `static/css/editor_offset_visual.css`;
- `static/js/editor_offset_visual.js` y `static/js/editor_offset_visual/`;
- `routes.py`;
- `services/editor_offset_*` legacy;
- `static/constructor_offset_jobs/`;
- tests Playwright que navegan a `/editor_offset_visual`.

V2 no debe importar el contrato V1 ni persistir `layout_constructor.json`.

Superficies legacy o transversales que requieren análisis especial si aparecen en el recorrido afectado:

- `engines/step_repeat_pro_engine.py`;
- `engines/nesting_pro_engine.py` cuando corresponda;
- `montaje_offset_inteligente.py`;
- `services/editor_offset_output_service.py`;
- `strategies/`;
- cuadernillos e IA cuando consuman los mismos motores o salidas.

No modificar una superficie compartida como parte de un cambio “solo V2” sin declarar y validar su blast radius sobre V1.

El Repeat habitual V2 importa `editor_offset_v2/domain/repeat_packer.py`, no `engines/step_repeat_pro_engine.py`. Preview/PDF habitual usa compositor V2. `prepared_output_adapter.py` y `legacy_output_probe.py` conservan imports locales legacy para ensayos/sondas offline; `output-capabilities` expone diagnóstico histórico, sin llamada desde la UI habitual. `app.py` sí importa `routes.py` legacy antes de registrar V2: no declarar independencia del proceso Flask completo. Comprobar de nuevo estas fronteras al cambiar arranque o imports.

## 8. Flujo funcional vigente de V2

```text
app.py
  -> init_editor_offset_v2()
  -> blueprint V2 protegido por EDITOR_OFFSET_V2_ENABLED
  -> shell o API V2

GET shell/job
  -> editor_offset_visual_v2.html
  -> contexto JSON
  -> editor_offset_visual_v2.js
  -> bootstrap.js
  -> EditorStore + controladores + registro de acciones
  -> canvas SVG y paneles

mutación persistente
  -> acción registrada
  -> comando reversible
  -> EditorStore
  -> undo/redo + dirty state
  -> SaveCoordinator
  -> PUT layout con base_revision
  -> compare-and-swap + nueva revisión
```

Las 14 rutas HTML/API y sus consumidores están inventariados en [44](DOCS/OFFSET/V2/44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md); `blueprint.py` es la fuente ejecutable. Preview y PDF final están disponibles en el arranque local habitual `scripts/start_editor_offset_v2.ps1`; derivados y dev tools permanecen separados. El cierre y la evidencia de salida están en [43](DOCS/OFFSET/V2/43_PLAN_SALIDA_PDF_HABITUAL_V2.md). No extrapolar estos flags a otros despliegues ni confundir el perfil nativo limitado con certificación PDF/X o CTP. Nesting, hybrid y CTP no son flujos operativos.

## 9. Contrato e invariantes de Layout V2

`layout_schema_version = 2` es un corte limpio. Un Layout V1 no se normaliza ni migra implícitamente a V2.

Fuentes ejecutables canónicas:

- `editor_offset_v2/domain/layout_v2.py`;
- `editor_offset_v2/domain/validation.py`;
- `editor_offset_v2/schemas/layout-v2.schema.json`.

Invariantes que deben preservarse:

- unidad milimétrica;
- origen en esquina inferior izquierda;
- posición del slot en centro trim;
- trim persistido antes de rotación;
- bleed separado y no negativo;
- footprint derivado, nunca persistido;
- rotaciones cardinales estrictas `0`, `90`, `180` y `270`;
- IDs únicos y referencias válidas;
- assets y páginas con identidad estable;
- assets físicos fuente inmutables;
- caras `front` y `back` explícitas;
- estado temporal fuera del layout;
- campos desconocidos críticos rechazados;
- campos V1 prohibidos;
- `job.revision` y guardado optimista mediante `base_revision`.

Un cambio incompatible, un campo requerido nuevo o una nueva semántica obligatoria exige revisar versionado. Un campo opcional solo puede incorporarse coordinando schema, validación, fixtures, tests y todos los lectores/escritores.

No añadir campos al contrato únicamente porque aparezcan en una propuesta documental o resulten cómodos para la UI.

## 10. Reglas de frontend V2

- `dom_refs.js` centraliza el contrato DOM.
- `bootstrap.js` compone Store, API, renderer y controladores.
- `command_registry.js` es la frontera de acciones.
- `commands.js` implementa mutaciones reversibles.
- `store.js` separa Layout V2, historial y estado temporal.
- `autosave.js` coordina persistencia y conflicto.
- `canvas_renderer.js` representa; no debe convertirse en propietario del contrato.
- `geometry_view.js` contiene la frontera de coordenadas SVG y debe conservar paridad con el kernel Python.

Reglas:

- un control nuevo delega en una acción registrada;
- una mutación persistente usa un comando reversible cuando corresponda;
- selección, etapa, panel responsive, viewport, zoom, pan, borradores y diagnóstico visual permanecen temporales;
- no mutar Layout V2 directamente desde listeners DOM;
- no renombrar IDs, `data-*`, clases de estado o selectores sin revisar `dom_refs.js`, listeners y Playwright;
- mantener undo/redo, autosave, recarga, locks y conflictos;
- distinguir slot, footprint y transformación interna del contenido;
- no declarar una función operativa por la sola existencia de CSS, controles o código desconectado.

Para cambios visuales revisar como conjunto template, CSS, referencias DOM, bootstrap, controladores afectados, registro de acciones y los Playwright V2 pertinentes. Hay seis archivos V2 en `tests/playwright/`; consultar [44](DOCS/OFFSET/V2/44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md) para localizarlos.

## 11. Repeat V2

Repeat V2 atraviesa:

- `static/js/editor_offset_v2/repeat_panel.js`;
- acciones y comandos de Repeat;
- `editor_offset_v2/application/repeat_service.py`;
- `editor_offset_v2/infrastructure/repeat_engine_adapter.py`;
- `editor_offset_v2/domain/repeat_contract.py`;
- `editor_offset_v2/domain/repeat_packer.py` propio.

La propuesta es temporal hasta que el operador aplica el resultado. Aplicar debe ser persistente, reversible y trazable.

Antes de cambiar Repeat revisar:

- modos add/replace y políticas partial/fill;
- frente/dorso;
- cantidades solicitadas, colocadas, faltantes y sobreproducidas;
- locks y `generated_by`;
- selección resultante;
- persistencia y salida;
- ausencia de nuevos imports o delegaciones a motores compartidos.

V2 no expone actualmente nesting o hybrid como flujos operativos. No agregarlos dentro de una corrección de Repeat.

## 12. Geometría, pliego y herramientas manuales

`editor_offset_v2/domain/geometry.py` es la fuente geométrica Python. La réplica JavaScript debe mantener paridad mediante fixtures compartidos; no dispersar fórmulas alternativas.

La configuración del pliego modifica solo tamaño y márgenes mediante un comando reversible. No mueve, escala, rota ni elimina slots existentes. Cualquier nueva política necesita decisión explícita.

Resize V2 sigue pendiente como fase propia. Antes de implementarlo deben definirse ancla, proporción, rotación, locks, snap, contenido, bleed y exportabilidad. No activarlo como efecto lateral de un refactor visual.

La corrección interna de contenido y la materialización de derivados ya existen (32B–32F/39B); revisar el defecto de offset en slots rotados registrado en 40. Frente/dorso operativo de UI y capacidades adicionales todavía requieren fases propias.

## 13. Preflight, preview, PDF y CTP

Esta es una superficie de alto riesgo.

Estado vigente:

- `output-capabilities` conserva diagnóstico del puente histórico; Validar y Salida usan diagnóstico nativo común y preflight por operación;
- Preview/PDF V2 tienen servicios, compositor y gates propios. El arranque local habitual activa Preview/PDF y deja derivados/dev tools apagados; [43](DOCS/OFFSET/V2/43_PLAN_SALIDA_PDF_HABITUAL_V2.md) registra la aceptación y sus límites;
- `editor_output_adapter.py` no ejecuta el renderer. Las sondas legacy sirven para caracterización offline, no para la salida habitual;
- el sangrado por trabajo distingue `source_only`, `mirror_if_missing` y ausencia histórica; marcas con sangrado cero se omiten con aviso;
- CTP, PDF/X y rendimiento de 500 piezas no están certificados. No inventar cajas PDF ausentes ni confundir cobertura declarada por cajas con diseño útil en todos los bordes.

Antes de ampliar o corregir salida, verificar las decisiones existentes en el código y las pruebas:

1. contrato de preflight, severidades, operaciones y revisión esperada;
2. archivos físicos, páginas y cajas PDF realmente declaradas;
3. trim, bleed, clipping, giros y correcciones internas;
4. fixtures y tolerancias métricas/visuales pertinentes;
5. coherencia canvas/Preview/PDF en archivos generados;
6. errores, rollback y ausencia de publicación parcial;
7. alcance explícito si se trabaja en caras, marcas avanzadas o CTP.

No ignorar opciones no soportadas, no degradarlas silenciosamente y no generar un job parcial cuando el contrato exige bloqueo.

Seguir el recorrido afectado con [44](DOCS/OFFSET/V2/44_MAPA_CONEXIONES_EDITOR_OFFSET_V2.md): `preflight_contract.py`, `native_output_capabilities.py`, `preflight_service.py`, `preview_service.py`, `pdf_final_service.py`, `output_snapshot.py`, `prepared_pdf_source.py`, `pdf_compositor.py`, repositorios, inspector PDF y pruebas. Consultar los módulos del puente histórico solo si el cambio alcanza esa frontera.

## 14. IA y automatización

IA no forma parte del alcance de salida V2 documentado en 43.

- No conectar agentes a escritura productiva sin fase, permisos y guardrails.
- No integrar prototipos CLI a Flask por conveniencia.
- No permitir que IA omita validaciones de preprensa.
- Toda acción sugerida por IA que modifique Layout V2 debe ser explícita, confirmable, reversible y trazable.
- Evitar introducir dependencias con motores compartidos al modificar tools de Repeat.

## 15. Validación por alcance

Ejecutar tests solo cuando el usuario lo autorice. Empezar por la validación más focalizada y ampliar según riesgo.

### Sintaxis JavaScript V2

```powershell
node --check static/js/editor_offset_visual_v2.js
```

Comprobar también cada archivo modificado de `static/js/editor_offset_v2/`.

### Node V2

```powershell
$editorV2JsTests = Get-ChildItem -LiteralPath tests\editor_offset_v2\js -Filter *.test.cjs | ForEach-Object { $_.FullName }
node --test $editorV2JsTests
```

### Python V2

```powershell
venv\Scripts\python.exe -m pytest tests\editor_offset_v2 -q
```

### Playwright V2

```powershell
$editorV2Playwright = Get-ChildItem -LiteralPath tests\playwright -Filter test_editor_offset_v2*.py | ForEach-Object { $_.FullName }
venv\Scripts\python.exe -m pytest $editorV2Playwright -q
```

No incluir tests Playwright V1 en una validación exclusivamente V2. Para iniciar o comprobar Flask usar la skill `editor-offset-local-qa` con target `v2`. Mantener `EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED=0` salvo petición expresa.

Para comprobación interactiva usar el navegador autorizado y verificar identidad de URL, contenido, consola, foco, estado persistido y ausencia de mutaciones no intencionales.

### Validación general

```powershell
git diff --check
```

La suite global del repositorio se ejecuta solo cuando el usuario la autorice o el gate acordado la exija. Registrar con precisión pruebas omitidas, fallos y ausencia de baseline.

Al cambiar PDF, la validación pertinente debe incluir el archivo generado, dimensiones, páginas, cajas, bleed, marcas y comparación visual/métrica. Un HTTP 200 no demuestra corrección productiva. Conservar explícito el límite temporal pendiente de 500 piezas; no elevar umbrales para ocultarlo.

## 16. Documentación y trazabilidad

Actualizar documentación cuando cambie:

- contrato o schema;
- semántica geométrica;
- ruta o responsabilidad de módulo;
- persistencia o concurrencia;
- flujo operativo;
- Repeat;
- preflight, preview, PDF, bleed, marcas o CTP;
- una decisión arquitectónica abierta.

No duplicar el mapa completo en varios documentos. Usar 41 para el trabajo diario, 44 para localizar conexiones, los contratos pertinentes para invariantes y los documentos anteriores como evidencia de su corte. Actualizar un documento adicional solo si el cambio lo afecta.

No colocar en este archivo datos efímeros como branch actual, job de prueba, revisión observada o cantidad momentánea de tests.

## 17. Git y disciplina de cambios

- Inspeccionar `git status` antes de editar y al finalizar.
- Preservar cambios ajenos o no relacionados.
- No hacer commit ni push sin autorización explícita.
- No usar comandos destructivos para limpiar el worktree.
- No mezclar contrato, funcionalidad, refactor y documentación si pueden separarse.
- Preferir una rama por fase importante.
- Antes de merge revisar diff contra la base, commits, archivos no rastreados, pruebas y cambios fuera de alcance.
- Eliminar una rama solo después de integrarla y comprobar el destino.

## 18. Alcance del trabajo V2

Preflight, Preview, PDF nativo, corrección interna, preparación multipágina y Repeat propio ya tienen implementación. No reiniciar esas funciones como si estuvieran ausentes. Los hallazgos de 40 y las exclusiones de 43 sirven como pistas y límites comprobables, no como un orden de tareas. Elegir el alcance según la solicitud y la evidencia actual; CTP, PDF/X, resize, frente/dorso completo e IA requieren trabajo explícito.

## 19. Reporte esperado

Para auditorías o cambios importantes, entregar cuando aplique:

1. resumen y alcance;
2. archivos y evidencia revisados;
3. estado y mapa funcional;
4. hechos confirmados;
5. inferencias y pendientes;
6. contratos y dependencias;
7. riesgos y blast radius;
8. cobertura existente y faltante;
9. plan SAFE y rollback;
10. criterios de aceptación;
11. qué no debe tocarse todavía.

## 20. Invariantes que no deben romperse

No romper ni cruzar silenciosamente:

- aislamiento V1/V2;
- Layout V2 y su schema;
- geometría canónica en milímetros;
- referencias entre assets, works y slots;
- assets fuente inmutables;
- guardado optimista, revisión y escritura atómica;
- comandos, undo/redo y autosave;
- locks y procedencia;
- selección, drag, pan, zoom, snap, guías y herramientas existentes;
- configuración SAFE del pliego;
- Repeat propio V2 y ausencia de nuevas dependencias de motores compartidos;
- seguridad de rutas y archivos;
- accesibilidad responsive implementada;
- compatibilidad legacy fuera de V2;
- separación entre diagnóstico, preflight y producción.

La precisión técnica y la seguridad productiva tienen prioridad sobre la conveniencia de implementación.
