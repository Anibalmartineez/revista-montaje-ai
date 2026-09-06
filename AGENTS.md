# AGENTS.md — Reglas operativas de `revista-montaje-ai`

## 1. Propósito y prioridad actual

Este repositorio contiene `revista-montaje-ai` y varias superficies de preprensa.

El agente debe trabajar como:

- arquitecto técnico y analista SAFE;
- desarrollador senior;
- especialista en preprensa e imposición offset;
- revisor de contratos, persistencia y salida productiva;
- acompañante técnico del usuario.

El usuario define la visión y aprueba las decisiones relevantes. El agente convierte esa visión en evidencia, planes, documentación, pruebas y cambios pequeños y verificables.

La prioridad activa es **Editor Offset Visual V2**. Editor V1 se conserva como sistema legacy y superficie de compatibilidad. No tratar V1 y V2 como variantes intercambiables.

## 2. Regla SAFE central

Antes de un cambio importante:

1. determinar versión y alcance;
2. leer las instrucciones y documentación vigentes;
3. inspeccionar el código y la persistencia relacionados;
4. reconstruir el flujo real;
5. identificar contratos, dependencias y riesgos;
6. separar hechos, inferencias y pendientes;
7. proponer un plan reversible;
8. obtener aprobación cuando el cambio sea amplio, riesgoso o contractual;
9. implementar sin mezclar fases;
10. validar en proporción al riesgo;
11. actualizar la trazabilidad cuando cambie el comportamiento real.

No confundir velocidad con progreso. No programar una salida productiva antes de definir cómo se demuestra que es correcta.

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

### Lectura inicial para Editor V2

Consultar solo los documentos necesarios para el alcance, comenzando por:

1. `DOCS/OFFSET/V2/20_ESTADO_ACTUAL_POST_REDISENO_UX_V2.md`: entrada operativa vigente y próximo gate SAFE.
2. `DOCS/OFFSET/V2/01_CONTRATO_LAYOUT_V2.md`: contrato persistente.
3. `DOCS/OFFSET/V2/02_KERNEL_GEOMETRICO_V2.md`: semántica geométrica canónica.
4. `DOCS/OFFSET/V2/03_ADAPTADOR_SALIDA_V2.md`: frontera temporal de salida.
5. `DOCS/OFFSET/V2/11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md`: decisiones que aún no autorizan implementación.
6. El documento específico de la funcionalidad afectada entre 04 y 17.
7. `DOCS/OFFSET/V2/19_PLAN_Y_TRAZABILIDAD_REDISENO_UX_V2.md` cuando se necesite la historia detallada del rediseño.

Clasificación importante:

- documento 01: contrato vigente;
- documento 02: fuente geométrica; sus descripciones de alcance histórico no sustituyen el estado del documento 20;
- documento 03: adaptador temporal vigente, no salida productiva;
- documentos 04 a 17: decisiones y fases específicas, con posibles cortes históricos;
- documento 18: snapshot histórico de las exploraciones 1 a 4;
- documento 19: plan, decisiones y bitácora de la Fase 19 cerrada;
- documento 20: estado operativo vigente posterior al rediseño.

Para V1, consultar `DOCS/OFFSET/` solo cuando V1 o una dependencia legacy esté dentro del alcance. No usar esos documentos como contrato de V2.

## 5. Modos de trabajo y autorización

### Auditoría

- Solo lectura.
- No modificar código ni documentación.
- No ejecutar tests, iniciar Flask o usar recorridos interactivos si el usuario no lo autorizó.
- Entregar hechos, inferencias, riesgos, dependencias, preguntas y plan SAFE.

### Alineación documental

- Contrastar documentación con código y evidencia actual.
- Clasificar cada documento como contractual, operativo, histórico, propuesta o pendiente.
- No reescribir evidencia histórica como si fuera estado presente.
- Modificar únicamente los documentos autorizados.

### Planificación

- No editar código.
- Definir objetivo, alcance, no objetivos, riesgos, contratos, archivos, fases, pruebas, aceptación y rollback.
- Esperar aprobación antes de cambios importantes.

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
- `editor_offset_v2/domain/`: Layout V2, validación, geometría, Repeat y contrato interno de salida.
- `editor_offset_v2/application/`: servicios de jobs, assets, Repeat y diagnóstico de salida.
- `editor_offset_v2/infrastructure/`: persistencia, PDF inspector, thumbnails, Repeat adapter y OutputAdapter temporal.
- `editor_offset_v2/schemas/layout-v2.schema.json`: schema persistente.

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

Superficies compartidas o de impacto transversal que requieren análisis especial:

- `engines/step_repeat_pro_engine.py`;
- `engines/nesting_pro_engine.py` cuando corresponda;
- `montaje_offset_inteligente.py`;
- `services/editor_offset_output_service.py`;
- `strategies/`;
- cuadernillos e IA cuando consuman los mismos motores o salidas.

No modificar una superficie compartida como parte de un cambio “solo V2” sin declarar y validar su blast radius sobre V1.

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

Rutas V2 activas:

- `GET /editor_offset_visual_v2`;
- `GET /editor_offset_visual_v2/<job_id>`;
- `POST /api/editor-offset-v2/jobs`;
- `GET /api/editor-offset-v2/jobs/<job_id>`;
- `PUT /api/editor-offset-v2/jobs/<job_id>/layout`;
- `POST /api/editor-offset-v2/jobs/<job_id>/assets`;
- `GET /api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/thumbnails/<page>`;
- `POST /api/editor-offset-v2/jobs/<job_id>/imposition/repeat`;
- `GET /api/editor-offset-v2/jobs/<job_id>/output-capabilities`.

No existen todavía rutas V2 productivas de preview, PDF final, nesting, hybrid, preflight profundo o CTP.

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

Para cambios visuales revisar como conjunto template, CSS, referencias DOM, bootstrap, controladores afectados, registro de acciones y ambos Playwright V2.

## 11. Repeat V2

Repeat V2 atraviesa:

- `static/js/editor_offset_v2/repeat_panel.js`;
- acciones y comandos de Repeat;
- `editor_offset_v2/application/repeat_service.py`;
- `editor_offset_v2/infrastructure/repeat_engine_adapter.py`;
- `editor_offset_v2/domain/repeat_contract.py`;
- `engines/step_repeat_pro_engine.py` compartido.

La propuesta es temporal hasta que el operador aplica el resultado. Aplicar debe ser persistente, reversible y trazable.

Antes de cambiar Repeat revisar:

- modos add/replace y políticas partial/fill;
- frente/dorso;
- cantidades solicitadas, colocadas, faltantes y sobreproducidas;
- locks y `generated_by`;
- selección resultante;
- persistencia y salida;
- compatibilidad del motor compartido con V1.

V2 no expone actualmente nesting o hybrid como flujos operativos. No agregarlos dentro de una corrección de Repeat.

## 12. Geometría, pliego y herramientas manuales

`editor_offset_v2/domain/geometry.py` es la fuente geométrica Python. La réplica JavaScript debe mantener paridad mediante fixtures compartidos; no dispersar fórmulas alternativas.

La configuración del pliego modifica solo tamaño y márgenes mediante un comando reversible. No mueve, escala, rota ni elimina slots existentes. Cualquier nueva política necesita decisión explícita.

Resize V2 sigue pendiente como fase propia. Antes de implementarlo deben definirse ancla, proporción, rotación, locks, snap, contenido, bleed y exportabilidad. No activarlo como efecto lateral de un refactor visual.

Frente/dorso y transformaciones internas avanzadas también requieren fases propias.

## 13. Preflight, preview, PDF y CTP

Esta es una superficie de alto riesgo.

Estado vigente:

- `output-capabilities` compara Layout V2 con las restricciones del puente temporal;
- no equivale a preflight productivo;
- `editor_output_adapter.py` no ejecuta el renderer;
- Preview y PDF final V2 no están conectados;
- CTP habilitado continúa bloqueado;
- el destino arquitectónico previsto es un motor de salida V2 propio;
- el puente legacy puede servir para caracterización, no para contaminar el dominio V2.

Antes de programar salida:

1. definir contrato canónico de preflight y severidades;
2. resolver archivos físicos, páginas y cajas PDF;
3. definir trim, bleed, clipping, escalas, offsets y rotaciones internas;
4. crear fixtures PDF y tolerancias métricas/visuales;
5. demostrar coherencia canvas/preview/PDF;
6. diseñar errores, rollback y artefactos reproducibles;
7. resolver caras, marcas y CTP en alcance explícito.

No ignorar opciones no soportadas, no degradarlas silenciosamente y no generar un job parcial cuando el contrato exige bloqueo.

Revisar al menos:

- documentos 01, 02, 03, 11 y 20;
- `editor_offset_v2/domain/output_contract.py`;
- `editor_offset_v2/application/output_service.py`;
- `editor_offset_v2/infrastructure/editor_output_adapter.py`;
- repositorios e inspección física de assets;
- superficies legacy compartidas de salida;
- fixtures y pruebas de contrato/render.

## 14. IA y automatización

IA no forma parte del próximo gate productivo de V2.

- No conectar agentes a escritura productiva sin fase, permisos y guardrails.
- No integrar prototipos CLI a Flask por conveniencia.
- No permitir que IA omita validaciones de preprensa.
- Toda acción sugerida por IA que modifique Layout V2 debe ser explícita, confirmable, reversible y trazable.
- Revisar dependencias con motores compartidos antes de modificar tools de Repeat.

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
venv\Scripts\python.exe -m pytest tests\playwright\test_editor_offset_v2.py tests\playwright\test_editor_offset_v2_ux_characterization.py -q
```

No incluir tests Playwright V1 en una validación exclusivamente V2. Para iniciar o comprobar Flask usar la skill `editor-offset-local-qa` con target `v2`. Mantener `EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED=0` salvo petición expresa.

Para comprobación interactiva usar el navegador autorizado y verificar identidad de URL, contenido, consola, foco, estado persistido y ausencia de mutaciones no intencionales.

### Validación general

```powershell
git diff --check
```

La suite global del repositorio se ejecuta solo cuando el usuario la autorice o el gate acordado la exija. Registrar con precisión pruebas omitidas, fallos y ausencia de baseline.

Cuando se implemente PDF, la validación deberá incluir archivo generado, dimensiones, páginas, cajas, bleed, marcas y comparación visual/métrica. Un HTTP 200 no demuestra corrección productiva.

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

No duplicar el mapa completo en varios documentos. Mantener:

- un estado operativo vigente;
- contratos canónicos;
- una trazabilidad por fase;
- snapshots históricos claramente rotulados.

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

## 18. Próxima evolución recomendada de V2

La Fase 19 de rediseño UX está cerrada. No continuarla como 19-H.

Orden SAFE vigente:

1. auditoría focalizada de salida y preflight, inicialmente de solo lectura;
2. contrato canónico de preflight;
3. fixtures PDF y criterios de paridad;
4. preview productivo mínimo detrás de un gate explícito;
5. PDF final V2;
6. CTP y marcas en una fase propia;
7. concurrencia, retención y recuperación operativa;
8. Resize y transformaciones avanzadas;
9. frente/dorso operativo;
10. automatización e IA con guardrails.

No mezclar preflight, PDF, CTP, resize e IA en una misma fase.

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
- Repeat y su dependencia compartida;
- seguridad de rutas y archivos;
- accesibilidad responsive implementada;
- compatibilidad legacy fuera de V2;
- separación entre diagnóstico, preflight y producción.

La precisión técnica y la seguridad productiva tienen prioridad sobre la conveniencia de implementación.
