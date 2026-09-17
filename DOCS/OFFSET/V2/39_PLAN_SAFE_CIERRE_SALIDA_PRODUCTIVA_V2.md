# Plan SAFE — Cierre de salida V2 en tres fases

**Estado: plan completo aprobado; ejecución secuencial 39A–39C.**

## 1. Objetivo y autorización

Entregar un recorrido V2 verificable: preparar PDFs y sus páginas, montar y corregir contenido, comprobar el resultado, generar Preview y descargar un PDF que respete el montaje aprobado.

Este documento autoriza únicamente su propia preparación. El usuario pidió revisar y aprobar primero el plan completo. No se inicia implementación ni se crean commits en esta entrega.

Tras aprobar este plan, la ejecución propuesta es secuencial: **39A → pruebas → commit local → 39B → pruebas → commit local → 39C → pruebas → commit local**. La aprobación del conjunto permite continuar entre fases cuando se cumplen sus criterios; no hace falta otra confirmación rutinaria. Una ampliación material del contrato, del alcance o del impacto sobre V1 sí exige presentar la decisión concreta antes de actuar.

Rama de partida comprobada: `codex/editor-offset-v2-output-contract-parity`, HEAD `4c41604`. Worktree limpio antes de crear este documento. Se propone conservar esta rama para el cierre autorizado, con commits diferenciados. No se incluyen merge, push, rebase ni eliminación de ramas.

## 2. Base de evidencia y límites

La auditoría previa leyó los 43 documentos V2 existentes y examinó código, pruebas, interfaz, persistencia y artefactos. Evidencia local complementaria:

- [Auditoría detallada](../../../.codex-runtime/audit-v2-20260916/AUDITORIA_Y_PLAN_SAFE.md).
- [Matriz backend](../../../.codex-runtime/audit-v2-20260916/results.json).
- [Pruebas complementarias](../../../.codex-runtime/audit-v2-20260916/followup.json).

Estos artefactos locales no se versionan automáticamente. Este plan conserva los hallazgos necesarios para poder ejecutar el trabajo en otro entorno. Las reproducciones se convertirán en tests sintéticos versionados; no se agregarán al repositorio los PDFs privados del escritorio ni los jobs personales.

Baseline observado, no reejecutado al redactar este plan: 448 pruebas Python aprobadas, una omitida; 122 JavaScript aprobadas; 22 Playwright V2 aprobadas. Los casos adicionales encontraron defectos a pesar de esa suite verde. Ningún conteo constituye garantía de ausencia de errores.

| ID | Hecho confirmado por la auditoría | Tratamiento |
|---|---|---|
| H1 | Preflight PDF incorpora restricciones del puente: página 1, TrimBox y transformaciones identidad | 39A: capacidades específicas del renderer |
| H2 | Escala/espejo se guardan sin cambiar el artwork SVG; la fuente derivada tampoco se representa | 39B: representación fiel y comparación real |
| H3 | PDF rasterizado aun con preservación vectorial solicitada; pliego 700×500 falla a 300 dpi | 39A: declarar límite; 39B: compositor nativo y presupuesto |
| H4 | Un guardado después de consume permite renderizar una revisión no analizada | 39A: snapshot y publicación vinculados |
| H5 | Derivado ausente declarado elegible; consume acepta reporte incompleto si conserva decisión eligible | 39A: inputs efectivos y validación del consumidor |
| H6 | Recuperación borra temporal conocido aun con publicación activa | 39A: coordinación y pruebas concurrentes |
| H7 | El planificador no se actualiza al cambiar entre assets de una y varias páginas | 39A: integración de selector/planificador |
| H8 | Bleed geométrico puede quedar recortado por trim; reset propone none no exportable; faltan marcas en vista | 39A: diagnóstico; 39B: política y representación; 39C: opciones visibles |
| H9 | face=[]; bleed NaN; escala infinita producen excepciones no controladas | 39A: validación y límites antes de asignar recursos |
| H10 | Inspector gráfico reaparece en otras etapas tras eventos del Store | 39A: propietario único de visibilidad |
| H11 | Salida no tiene controles operativos; gates locales de Preview/PDF apagados | 39C: interfaz, descarga y habilitación local controlada |
| H12 | Repeat añadir bloquea solapamientos pero no busca todos los huecos disponibles | Conservar protección, documentar limitación; no cambiar motor |

La cantidad por página introducida mediante automatización fill tuvo resultados distintos al teclado nativo. Es un pendiente de reproducción, no un defecto confirmado. Se verificará con ambos recorridos antes de atribuirlo al producto.

## 3. Decisiones propuestas para aprobar junto con el plan

1. **V2 es el sistema principal y conserva código propio.** Reutilizar sus repositorios, contratos, geometría, comandos, fixtures y preparación física. No llamar al renderer V1 para entregar el PDF nuevo. Cualquier algoritmo útil de V1 se adapta dentro de V2 únicamente si aporta valor y queda cubierto por pruebas.
2. **La salida describe una revisión y opciones exactas.** El render consume un snapshot; jamás relee silenciosamente otro layout entre caras. Si el job cambia antes de publicar, la operación se cancela como obsoleta; si cambia después, el artefacto sigue identificado con su revisión y la UI pide regenerar para la actual.
3. **Perfil inicial: composición PDF nativa con preservación de objetos fuente.** Mantener texto/vectores/espacios de color cuando se puedan preservar; no convertir todo el pliego a RGB ni rasterizar sin declararlo. No prometer conversión CMYK, prueba de color, separación de tintas o certificación PDF/X en esta entrega.
4. **Contenido ya rasterizado permanece rasterizado.** Un derivado horneado o una imagen original no recupera vectores. Informar resolución y origen; si la política exige vector y solo hay representación raster incompatible, bloquear o requerir una elección explícita admitida por el contrato, nunca degradar silenciosamente.
5. **Bleed por espejo solo mediante opción explícita**, decisión ya tomada por el usuario. Comprobar primero cobertura física real. No inferir 3 mm porque exista BleedBox. No modificar silenciosamente clipping de layouts guardados; advertir/bloquear si la salida solicita bleed que su recorte descarta y ofrecer corrección reversible.
6. **PDF del pliego a tamaño físico.** Propuesta para el perfil inicial: MediaBox y CropBox iguales al pliego, sin crop-to-content. No inventar TrimBox/BleedBox de una pieza para el pliego completo. Las cajas de piezas siguen gobernando la composición; cualquier otra política de cajas de salida requiere una decisión explícita documentada antes de habilitarla.
7. **Marcas de corte dentro del alcance; CTP separado.** Representar y validar las marcas de corte soportadas. No incorporar barras de color, registros o textos técnicos no implementados. Sus solicitudes deben generar un bloqueo claro. Las medidas/política de marcas se fijan en 39B antes de programar su compositor, conservando el contrato persistente existente.
8. **Frente/dorso:** renderizar caras ya definidas, con orden y flip exactos. No añadir generación automática del dorso, encuadernación o un sistema nuevo de imposición editorial. La UI solo ofrece caras disponibles y declara las funciones pendientes.
9. **Retención explícita, no automática.** Corregir el servicio para que respete publicaciones/lecturas activas. No habilitar borrado periódico ni limpieza al arranque dentro de estas fases.
10. **Gates separados y ámbito local.** Mantener defaults globales desactivados durante desarrollo. En 39C, habilitar para el proceso local de QA las capacidades aceptadas y documentar el comando de uso; no cambiar variables de usuario/máquina ni desplegar a terceros.

No se prevé cambiar `layout-v2.schema.json` ni la semántica persistente de Layout V2. La identidad de exportación y sus opciones viven en un contrato interno/artefacto separado. Si la implementación exige ampliar el reporte preflight, coordinar schema del reporte, versión, productores, consumidores y tests; los reportes antiguos incompatibles se regeneran. No migrar layouts por conveniencia.

## 4. Protocolo obligatorio de ejecución por fase

1. Comprobar rama, status, diff y último cierre aceptado; conservar trabajo ajeno.
2. Reproducir el defecto o comportamiento objetivo con fixtures pequeños. Crear tests que fallen por la causa correcta antes del cambio cuando haya regresión confirmada.
3. Implementar únicamente el bloque de esa fase, en incrementos revisables.
4. Ejecutar tests focalizados; corregir fallos. Verificar éxito, límites, errores, no mutación, repetición y concurrencia cuando corresponda.
5. Comprobar sintaxis de JavaScript modificado y ejecutar regresión Python/Node/Playwright V2 al cierre. No sustituir evidencia de artefacto por mocks o HTTP 200.
6. Usar `editor-offset-local-qa` target `v2`: comprobar Flask, iniciarlo solo si hace falta, verificar HTTP y proceso. Mantener dev tools en 0. Si el código Python cambió y el servidor no recarga, reiniciar únicamente el proceso registrado y comprobar que sirve el código nuevo.
7. Probar desde el ordenador/navegador autorizado con jobs QA nuevos: URL V2, controles reales, consola, foco, teclado, responsive, persistencia y ausencia de cambios en jobs del usuario. En fases sin botones de salida, validar el panel disponible y el backend por pruebas API aisladas, sin fingir una descarga UI inexistente.
8. Inspeccionar los artefactos aplicables: páginas, dimensiones, cajas, clipping, bleed, marcas, identidad de revisión y representación de objetos. Guardar evidencia reproducible y tiempos.
9. Actualizar trazabilidad y estado operativo; revisar diff de código/tests/docs, archivos no rastreados y `git diff --check`.
10. Solo con criterios satisfechos: agregar exclusivamente los archivos de la fase, crear commit local descriptivo y comprobar worktree limpio. Registrar hash y pruebas. Avanzar a la fase siguiente.

Si una prueba nueva o existente falla por el cambio, no hacer el commit de cierre ni avanzar. Si falta evidencia esencial, la fase continúa abierta. Una prueba omitida exige motivo registrado; no permite declarar aceptado el comportamiento que debía cubrir.

La aprobación futura incluye los commits locales de las fases solicitados por el usuario. No incluye publicar la rama ni integrar main. El documento del plan se incluye en el primer cierre aprobado; no se comitea ahora.

### Comandos de referencia

```powershell
git status
git rev-parse --show-toplevel
venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py --target v2
# Solo si no existe un servidor V2 válido:
powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\start_flask.ps1 -Target v2
venv\Scripts\python.exe -m pytest tests\editor_offset_v2 -q
$editorV2JsTests = Get-ChildItem -LiteralPath tests\editor_offset_v2\js -Filter *.test.cjs | ForEach-Object { $_.FullName }
node --test $editorV2JsTests
venv\Scripts\python.exe -m pytest tests\playwright\test_editor_offset_v2.py tests\playwright\test_editor_offset_v2_ux_characterization.py -q
git diff --check
```

Comprobar `node --check` sobre cada JS modificado. Incorporar al cierre cualquier test V2 nuevo que se ubique en otro archivo de integración. La suite global y Playwright V1 no son la validación predeterminada de este plan.

## 5. Fase 39A — Preflight coherente, snapshot y correcciones de integración

**Resultado:** decisiones de salida que representan las capacidades reales y una operación ligada a inputs comprobados. Esta fase no entrega aún el nuevo PDF vectorial.

### Pasos

1. **39A.1 — Regresiones y mapa de capacidades.** Convertir H1/H4/H5/H6/H9 en reproducciones deterministas. Distinguir `legacy_bridge`, Preview V2 experimental y PDF V2 experimental/nativo, con versión y capacidades verificadas. No liberar una capacidad solo porque Preview devuelva 200.
2. **39A.2 — Contexto inmutable de salida.** Capturar una sola lectura coherente del layout, revisión, hash, fuentes efectivas y opciones normalizadas: operación, caras/orden, dpi, mirror bleed y perfil. Establecer identidad de petición e inputs. Evitar mantener el lock de escritura durante todo el render; realizar captura y comprobación/publicación final con coordinación acotada y orden de locks documentado.
3. **39A.3 — Preflight del renderer elegido.** Separar reglas legacy; inspeccionar originales y derivados, hashes, rutas, número de páginas, dimensiones y correspondencia del derivado con su fuente. Incluir límites de clipping, marcas y recursos antes de componer. Mantener bloqueos de capacidades nativas todavía pendientes, incluida preservación vectorial hasta 39B.
4. **39A.4 — Consumidor y errores.** Validar contrato, completitud, versión/política, operación, opciones e identidad del reporte. Rechazar obsoletos, checks no ejecutados e inputs alterados. Controlar tipos, finitud y presupuestos de transformaciones antes de reservar imágenes; devolver errores 400/409/422 consistentes.
5. **39A.5 — Publicación y limpieza.** Vincular nombre/manifiesto/hash a revisión y opciones, evitando colisiones. Rechazar publicación si el snapshot dejó de ser actual. Coordinar publicación, recuperación, retención y entrega a lectores. Proteger fuentes y derivados referenciados; mantener limpieza manual desactivada por defecto.
6. **39A.6 — Preparación e inspector.** Refrescar planificador con cada cambio de PDF, conservar selección/cantidad por asset y página, probar blur/teclado/fill. Respetar etapas al actualizar el inspector. Los controles nuevos pasan por acciones registradas; no mutan el layout desde listeners.
7. **39A.7 — Diagnóstico comprensible.** Mostrar motivo específico, operación y elementos afectados. Separar error del documento, advertencia, función no soportada y gate apagado. Evitar agrupar motivos distintos bajo una etiqueta que oculta el problema.
8. **39A.8 — Cierre.** Actualizar documentos 20/21/24/35/38 según comportamiento real y corregir las afirmaciones operativas obsoletas pertinentes de AGENTS.md, sin cambiar sus reglas SAFE. Añadir bitácora al presente plan; validar y guardar.

### Archivos previstos

- `application/{preflight_service,output_service,preview_service,pdf_final_service,derived_asset_service}.py` y `blueprint.py`.
- `domain/preflight_contract.py`, `schemas/preflight-report.schema.json` si la nueva identidad requiere versión; módulo interno nuevo de snapshot/capacidades si resulta necesario.
- `infrastructure/{job_repository,process_lock,artifact_lifecycle}.py`: solo lectura coherente/coordinación necesarias, sin reescribir autosave/CAS.
- `static/js/editor_offset_v2/{assets_panel,content_transform_inspector,output_panel,workflow_navigation,command_registry}.js` y cableado/DOM afectados.
- Tests V2 específicos de cada frontera y fixtures sintéticos.

### Pruebas y aceptación

- Crop/Media/Trim/Bleed presentes/ausentes, páginas 1/2/N y rotaciones: decisión conforme a la capacidad declarada, manteniendo límites reales.
- Cambio 1→3→1 páginas inmediato; cantidades distintas por página, deselección, retorno al asset, creación de works y undo/redo.
- Fuente derivada ausente, corrupta, hash cambiado, fuente distinta, página/medida incompatible y ruta insegura: rechazo antes de render.
- Reporte incompleto, decisión falsamente eligible, opciones/caras distintas, hash/revisión cambiados y política antigua: rechazo controlado.
- Guardado entre consume y render, entre caras, y antes de publicación: ninguna mezcla de revisiones ni artefacto presentado como actual incorrectamente.
- Dos procesos publicando/limpiando/leyendo, con barreras deterministas y timeout: no borrar activos, no interbloqueo, no archivo parcial; recuperación repetible tras interrupción simulada.
- Argumentos inválidos y escalas extremas rechazados sin excepción no controlada ni agotamiento de memoria.
- Recorrido live: nuevos jobs, ambos PDFs, multipágina, diagnóstico, inspector por etapas, save/undo/redo/reload y conflicto entre dos pestañas QA.
- Documentación distingue capacidades experimentales de productivas. Sin regresiones de las herramientas existentes. Commit local de cierre con evidencia.

## 6. Fase 39B — Artwork fiel y compositor PDF nativo

**Entrada:** 39A aceptada y guardada. **Resultado:** PDF V2 inspeccionable y fiel detrás del gate; aún no se declara terminada la entrega de interfaz.

### Pasos

1. **39B.1 — Especificación ejecutable de composición.** Reutilizar geometría canónica y preparación de fuentes. Fijar orden de transformaciones, sistema de offsets, fit, espejo, rotaciones, clipping, bleed, caras y marcas con fixtures asimétricos. Resolver discrepancias entre documentos/kernel/render antes de programar; no cambiar semántica persistente sin decisión explícita.
2. **39B.2 — Preparación visual y fuente efectiva.** Dar al canvas una representación correcta de la caja/página/derivado; aplicar las transformaciones sin repetir las ya horneadas. Cachear por identidad/opciones y rechazar respuestas visuales obsoletas. Hacer distinguibles contenido imprimible y overlays de selección, reglas, etiquetas y límites.
3. **39B.3 — Sangrado y clipping.** Representar cobertura real y síntesis explícita. Corregir reset para volver a una configuración soportada y coherente con la fuente. No recortar silenciosamente el bleed solicitado. Una corrección persistente del operador usa comando reversible; los layouts guardados se diagnostican sin reescritura automática.
4. **39B.4 — PDF propio.** Componer páginas/objetos PDF en el pliego conservando texto/vectores cuando corresponda; usar `prepared_pdf_source` y derivados ya implementados. Preview y PDF consumen la misma descripción de composición. El rasterizador de Preview no debe ser el único origen del PDF nativo.
5. **39B.5 — Color y recursos.** Preservar sin conversión implícita; verificar fuentes, color/transparencia/sobreimpresión para el subconjunto soportado. Emitir bloqueo específico para lo que no pueda inspeccionarse/preservarse con evidencia. Limitar tamaño de imágenes intermedias, cachés y peticiones. Comprobar pliego 700×500 con fuentes/partes raster de 300 dpi sin exigir una imagen única de todo el pliego.
6. **39B.6 — Marcas, cajas y caras.** Fijar y probar el perfil de marcas de corte ya soportado: geometría, separación respecto a trim/bleed, colisiones, imprimible y límites del pliego. Dibujarlo igual en la vista imprimible y PDF. Media/Crop del pliego según sección 3; orden y flip exactos para caras existentes. No activar marcas avanzadas o CTP.
7. **39B.7 — Paridad y capacidad.** Capturar SVG real cargado en navegador y compararlo con Preview y PDF rasterizado a escala conocida. Añadir análisis independiente de geometría/objetos. Solo entonces declarar soportadas las nuevas capacidades del PDF nativo.
8. **39B.8 — Cierre.** Actualizar 20/23/26–33/37 mediante estado vigente y notas precisas, preservando historia. Validar artefactos y navegación live, registrar límites, hacer commit de cierre.

### Archivos previstos

- `domain/output_parity_contract.py`, geometría de composición V2 y contrato interno nuevo si se necesita.
- `infrastructure/{prepared_pdf_source,thumbnail_renderer}.py` y compositor PDF V2 propio.
- `application/{preview_service,pdf_final_service,derived_asset_service,preflight_service}.py`.
- `static/js/editor_offset_v2/{canvas_renderer,geometry_view,content_transform_inspector,commands}.js`, estilos y cableado estrictamente necesarios.
- Fixtures PDF sintéticos, expectativas métricas y tests browser de artwork/objetos.

### Matriz de paridad y aceptación

| Dimensión | Casos mínimos |
|---|---|
| Fuentes | cajas desplazadas/ausentes, Media/Crop/Trim/Bleed, tres páginas con contenido identificable, originales y derivados |
| Geometría | slots 0/90/180/270; intrínseca 0/90/180/270; offsets positivos/negativos; medidas asimétricas |
| Contenido | actual_size/contain/cover/stretch, escala uniforme/no uniforme, rotación interna cardinal, espejo X/Y/XY; clip trim/bleed y rechazo de none no soportado |
| Bleed | 0/3 mm, cobertura real suficiente/insuficiente, espejo off/on explícito, esquinas y uniones sin franjas blancas |
| Producción | marcas off/on, límites/colisiones, cara front/back y flips soportados, orden exacto, una/dos páginas según selección |
| Objetos | texto seleccionable/preservado donde exista, dibujos vectoriales, imágenes, transparencia y color admitidos; ausencia de rasterización total encubierta |
| Robustez | regeneración, derivado sin doble transformación, respuesta tardía del thumbnail, cambio de revisión durante salida, fallo de escritura, recursos acotados |

Mantener tolerancia métrica de 0.01 mm donde aplica y orden/cara/flip exactos. Reutilizar umbrales existentes de Preview/PDF (2% y delta media 8) y derivados (8% y 12) únicamente para sus comparaciones definidas. Para SVG real fijar antes de implementar la captura resolución, registro, antialiasing, regiones de contenido y máscara de overlays; no usar el fondo blanco del pliego para diluir errores de las piezas. Cualquier tolerancia adicional debe justificarse con baseline, no aumentarse para ocultar un fallo.

Prueba independiente: un error deliberado de página, espejo, desplazamiento o ausencia de marcas debe hacer fallar la comparación. Comparar solo dos salidas del mismo código no detecta todos los errores compartidos.

Con Torrente verificar preservación de texto y vectores sin exigir un número exacto de objetos internos después de la composición; con el cupón verificar escala, imagen y cobertura. Ambos PDFs privados se usan en QA local, con fixtures sintéticos equivalentes para CI. Medir también el resultado de siete formas por archivo, gap 1 mm y bleed 3 mm.

La fase cierra cuando los casos soportados pasan artefacto y navegador, los no soportados se bloquean con motivo, y se mantiene todo el comportamiento manual existente. No se etiqueta el resultado como PDF/X ni como prueba de color certificada.

## 7. Fase 39C — Preview, descarga y aceptación de uso real

**Entrada:** 39B aceptada y guardada. **Resultado:** el operador puede generar Preview y descargar el PDF del perfil soportado desde V2.

### Pasos

1. **39C.1 — Panel Salida.** Crear acciones Preview y Descargar PDF con estado de guardado, cara disponible, perfil, resolución pertinente y mirror bleed explícito. Mostrar qué contenido será imprimible y qué controles del canvas son overlays.
2. **39C.2 — Preflight integrado.** Guardar/resolver conflicto antes de iniciar; presentar errores y advertencias por pieza/asset/página/operación. Distinguir gate apagado de defecto del documento. Un reporte visual válido no sustituye la comprobación backend del snapshot.
3. **39C.3 — Generación y entrega.** Controlar solicitudes duplicadas, espera, errores, reintento y respuestas tardías. Mostrar revisión y opciones del archivo; no presentar como actual un PDF de otra revisión. Descargar solo el artefacto completo y verificado; no revelar rutas físicas del servidor.
4. **39C.4 — Recuperación.** Probar fallo de publicación, red interrumpida, navegador recargado, cambio concurrente y regeneración. Mantener layout y originales intactos. Comprobar retención manual durante lectura sin habilitar purgas automáticas.
5. **39C.5 — Carga acotada.** Ejecutar progresivamente 14, 100 y 500 placements sintéticos, PDFs multipágina (3, 20 y un caso cercano al límite configurado), varias regeneraciones y 2–4 peticiones concurrentes. Registrar tiempos/memoria/bytes y umbral de rechazo antes de cada nivel. No agotar deliberadamente el equipo; si un límite se excede, rechazar limpiamente y no dar por aceptada esa carga.
6. **39C.6 — QA live de principio a fin.** Mediante la skill, usar Flask con gates de proceso requeridos y dev tools=0, sin duplicados. Ordenador/navegador: crear jobs nuevos, cargar PDFs, crear works por página, Repeat, corrección, guardar, preflight, Preview, descargar, abrir e inspeccionar el archivo. Repetir con entrada inválida, falta de bleed, mirror explícito, derivado y conflicto de revisión.
7. **39C.7 — Entrega local.** Reemplazar el mensaje «Salida pendiente» únicamente por funciones aceptadas; conservar indicación de límites de CTP y funciones no soportadas. Documentar arranque, flags efectivos, flujo y recuperación. Mantener defaults globales sin habilitación automática no acordada.
8. **39C.8 — Cierre.** Ejecutar regresión V2 completa y prueba de aceptación final; actualizar documento 20 y trazabilidad, revisar diff, commit local y status limpio. Entregar comando de arranque, job QA, PDF de ejemplo, resultados y límites conocidos.

### Archivos previstos

- `templates/editor_offset_visual_v2.html`, `static/css/editor_offset_visual_v2.css`.
- `static/js/editor_offset_v2/{dom_refs,bootstrap,command_registry,api_client,output_panel,workflow_navigation}.js` y controlador de salida si se necesita.
- `blueprint.py`, `config.py` y entrega de artefactos para el contrato ya definido; sin rutas ni persistencia V1.
- Tests V2 de integración y Playwright con fixture de server/gates aislados.
- Guía de ejecución/aceptación y estado operativo actualizados.

### Aceptación final

- Un operador completa desde cero un montaje con PDFs reales y otro multipágina, ve los ajustes correctos y descarga su PDF sin comandos API manuales.
- El archivo respeta pliego, páginas/caras, trim, bleed explícito, clipping, transformaciones y marcas soportadas.
- El PDF conserva objetos fuente según perfil y declara elementos rasterizados; 300 dpi no implica rasterizar toda la hoja.
- Revisión, opciones y fuentes del reporte coinciden con el archivo; errores/incompletitud/obsolescencia no producen una falsa entrega exitosa.
- No hay excepciones de consola/servidor en los recorridos aceptados; foco, teclado, responsive y mensajes permiten recuperar errores.
- Undo/redo, autosave, locks, selección, Repeat y operaciones manuales mantienen sus pruebas y recorridos.
- Fuentes originales con hashes intactos, jobs personales intactos, artefactos sin parciales ni carreras demostradas.
- Evidencia de cada nivel de carga, omisiones y límites publicada en trazabilidad; commits locales realizados y worktree limpio.

**El PDF final estará disponible para el perfil soportado al cerrar 39C.** Al cerrar 39B ya existirá el artefacto nativo validado mediante backend/QA; no se confunde eso con una descarga terminada en la interfaz.

## 8. Riesgos, exclusiones y rollback

Mayor riesgo: orden de transformaciones y doble aplicación en derivados; preservación de objetos/color; carrera entre revisión, salida y limpieza; falsa confianza en tolerancias globales; cache visual obsoleto. Mitigación: fixtures asimétricos, oráculo métrico independiente, comparación de regiones, límites de recursos y pruebas deterministas con barreras.

No tocar como efecto lateral: motores compartidos V1, renderer/rutas V1, Layout V2 persistente, CAS/undo/redo como refactor, imposición editorial, nesting/hybrid, IA, resize, generación automática de dorso, CTP y marcas avanzadas. H12 se mantiene documentado y protegido; mejorar el aprovechamiento de huecos será otro alcance.

Rollback por fase: gates desactivados, commits pequeños reversibles y contratos de artefacto versionados. No borrar ni reescribir originales; no migrar jobs. Un rollback no debe borrar artefactos del usuario ni restaurar a escondidas un diagnóstico legacy como autoridad nativa. Antes de habilitar capacidad nueva debe existir un modo explícito de retirarla sin alterar el layout.

Si aparece una necesidad contractual fuera de las decisiones aprobadas, preparar evidencia, opciones y cambio mínimo; continuar mientras tanto con tareas independientes. No inventar una aprobación por el transcurso del tiempo.

## 9. Bitácora de ejecución

| Fase | Estado | Commit de cierre | Pruebas/artefactos |
|---|---|---|---|
| Plan | Aprobado por el usuario | `1647be8` | Documento aprobado y guardado antes del código |
| 39A | Implementada y validada | Commit de esta entrega | 461 Python + 1 omitida; 122 Node; 23 Playwright V2 (21 iniciales + 2 focalizados); QA local |
| 39B | No iniciada | — | Pendiente |
| 39C | No iniciada | — | Pendiente |

Actualizar esta tabla con evidencia real al ejecutar. No sustituir pendientes por afirmaciones de éxito anticipadas.

### Evidencia 39A

- Trece regresiones nuevas de snapshot, fuente efectiva, tipos/finitud, completitud, limpieza activa, retención y capacidad nativa; ocho iniciales reprodujeron siete fallos antes del arreglo. Política 2 obliga a regenerar reportes anteriores; el envelope 1 sigue siendo compatible estructuralmente (inputs permite evidencia adicional).
- Prueba de navegador añadida: assets 1→3→1, cantidades 2/7, selección, creación, undo/redo, guardado y recarga; inspector oculto fuera de Ajustar. El test anterior de preflight se corrigió para exigir el aviso de vector pendiente.
- Flask V2 reiniciado mediante la skill, dev tools=0; raíz y shell HTTP 200. CUA verificó planner 1→3→1→3 y conservación de 7 formas en página 2 en el job QA de auditoría, sin modificar sus slots/revisión.
- Regresión Python 461 aprobadas/1 omitida, Node 122. Playwright completo: 21 aprobadas y una expectativa histórica fallida; corregida y reejecutada junto con la regresión nueva, ambas aprobadas. Tras el límite preventivo del espejo: 46 pruebas focalizadas aprobadas.
- Se mantiene el renderer raster experimental hasta 39B; sin controles de descarga hasta 39C. No se ejecutó suite global ni V1. La carga extensa y aceptación final de salida pertenecen a 39C.
- No cambió Layout V2, CAS, originales, motores compartidos ni rutas V1. Recuperación y retención siguen siendo explícitas.
