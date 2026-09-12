# Fase 25 — Auditoría amplia de QA del Editor Offset Visual V2

Fecha de ejecución: 2026-09-11.

Esta guía registra la comprobación amplia realizada sobre la rama `codex/editor-offset-v2-output-preflight`. Se probó desde un job nuevo y se contrastó con las suites automatizadas V2. No se hizo commit ni push.

## 1. Alcance y límites

Se cubrieron todas las superficies V2 implementadas: arranque, shell, jobs, persistencia, carga e inspección PDF, miniaturas, works, slots, canvas, edición manual, selección, historial, undo/redo, autosave, conflictos, Repeat, pliego, alineación, distribución, precisión, guías, snap, objetos, clipboard, locks, responsive, compatibilidad de salida y preflight.

No fue posible probar como funciones operativas aquello que todavía no existe: Preview productiva, PDF final, CTP, Nesting, Hybrid, navegación de caras completa, Resize 8F y transformaciones internas avanzadas. Su ausencia se considera estado pendiente, no fallo de una prueba.

## 2. Entorno reproducido

- Rama: `codex/editor-offset-v2-output-preflight`.
- Árbol limpio al comenzar; los cambios que aparecen después corresponden únicamente a esta documentación y a los artefactos de la fase anterior.
- Flask V2 iniciado con `EDITOR_OFFSET_V2_ENABLED=1` y `EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED=0` mediante `editor-offset-local-qa`.
- Ruta comprobada: `http://127.0.0.1:5000/editor_offset_visual_v2`.
- Servidor QA dejado activo con PID `10864`.
- Job nuevo de recorrido manual: `ev2_43760f81373fb72c4165da9e`.

## 3. Recorrido manual desde cero

| Paso | Resultado observado |
| --- | --- |
| Abrir shell sin job | HTTP 200, mensaje para crear job y controles bloqueados correctamente |
| Crear job | URL V2 válida, revisión 1, pliego 700 × 500 mm |
| Cargar PDF con TrimBox | Asset `ready`, revisión 2, una miniatura servida |
| Crear work real | Revisión 3, formulario y selección de fuente operativos |
| Crear slot manual | Un slot en canvas, revisión 4, autosave terminado |
| Undo / redo | Undo elimina el slot sin perder historial; redo lo restaura y persiste revisión 5 |
| Repeat cantidad 3 | Propuesta solicitada 3, colocada 3, no colocada 0 |
| Aplicar Repeat | Cuatro slots visibles, revisión 6, procedencia e historial mostrados |
| Compatibilidad temporal | “Compatible con salida temporal”, revisión 6, sin issues en ese caso |
| Preflight | Reporte completo, revisión 6, 0 errores; `preview`, `pdf_final` y `ctp` bloqueados por gate |
| Editar con teclado | Revisión 7 y preflight marcado desactualizado |
| Undo | Revisión 8, cuatro slots, el reporte sigue correctamente obsoleto |
| Recargar | Persisten revisión 8, cuatro slots y etapa Ajustar |
| Consola | No se observaron errores de consola durante el recorrido |

La selección del archivo requirió abrir el selector de archivos antes de cargarlo. El primer intento del controlador de navegador expiró, se reintentó sin modificar la aplicación y la carga final funcionó. Es una incidencia de la herramienta de automatización, no un fallo del editor.

## 4. Validación automatizada

| Batería | Resultado |
| --- | --- |
| Python `tests/editor_offset_v2` | 408 aprobadas, 1 omitida |
| Node `tests/editor_offset_v2/js` | 117 aprobadas |
| Playwright V2 completo | 22 aprobadas |
| Pruebas nuevas de preflight | 4 Python y 1 Playwright aprobadas |
| Sintaxis JavaScript V2 | Aprobada |
| `git diff --check` | Aprobado |
| Comprobación Flask V2 | `/` y `/editor_offset_visual_v2` HTTP 200 |

Las suites automatizadas cubren además anchos responsive de escritorio, compacto y móvil, selección avanzada, 500 slots, locks, conflictos, persistencia, Repeat, geometría y paridad Python/JavaScript.

## 5. Fallos encontrados

No quedó ningún fallo funcional reproducible en las funciones implementadas después de los arreglos de la Fase 24. Durante la implementación del preflight se detectaron y corrigieron estos defectos:

1. La geometría del pliego se enviaba como `Size` donde el kernel exige `Bounds`.
2. Los hallazgos físicos, geométricos y de capacidades no se agregaban al arreglo común `issues` del reporte.
3. Los issues físicos usaban un `check_id` dinámico que no coincidía con el check publicado.
4. Un job inexistente podía terminar como error 500 porque se leía el archivo antes de confirmar la existencia del job; ahora responde 404 controlado.
5. El conteo de páginas PDF no se comparaba con la metadata persistida; ahora genera `PDF_METADATA_MISMATCH`.

Estos arreglos están cubiertos por las pruebas de `tests/editor_offset_v2/test_preflight_v2.py` y por el recorrido Playwright.

## 6. Estado correcto pero limitado

- `output-capabilities` puede informar compatibilidad con el puente temporal mientras el preflight mantiene bloqueada la producción. Son decisiones distintas y la interfaz las muestra separadas.
- Un reporte sin errores no habilita salida: el gate productivo permanece desactivado deliberadamente.
- La compatibilidad temporal sigue limitada a las capacidades conocidas del adaptador; no demuestra fidelidad canvas/PDF.
- Los campos resumidos de preflight del asset permanecen `not_run` porque esta fase publica un reporte de job y no muta metadata de assets.
- El preflight actual no calcula color, DPI efectivo, transparencias, sobreimpresión, perfiles ICC, marcas, dúplex físico ni clipping PDF completo.

## 7. Documentación histórica que requiere alineación futura

| Documento | Situación |
| --- | --- |
| `20_ESTADO_ACTUAL_POST_REDISENO_UX_V2.md` | Sus párrafos iniciales ya fueron actualizados, pero algunas secciones históricas todavía dicen que schema, ejecución y endpoint de preflight están pendientes. Deben conservarse como historia o marcarse con fecha. |
| `21_CONTRATO_PREFLIGHT_V2.md` | El contrato fue implementado parcialmente en Fase 24; las reglas productivas profundas siguen siendo propuestas. No debe describirse todo el documento como “no ejecutable”. |
| `08_AUDITORIA_ESTADO_ACTUAL_V2.md` | Es histórico. La frase sobre ausencia de preflight profundo sigue correcta, pero no debe interpretarse como ausencia del preflight mínimo actual. |
| `03_ADAPTADOR_SALIDA_V2.md` | Continúa vigente para el puente temporal. Sus afirmaciones de que no hay PDF/CTP productivos siguen correctas. |
| `06_ASSETS_Y_SLOTS_V2.md` | La ausencia de preflight profundo sigue correcta; la miniatura por caja y la inspección física completa continúan pendientes. |
| `19_PLAN_Y_TRAZABILIDAD_REDISENO_UX_V2.md` | Es bitácora histórica de la Fase 19. No debe extenderse como 19-H ni usarse como estado operativo actual. |

## 8. Recomendaciones de interfaz

1. Mantener visibles en el panel de Preflight tres datos juntos: revisión analizada, fecha del reporte y estado de cada operación.
2. Reforzar visualmente la diferencia entre “compatible con salida temporal” y “elegible para producción”.
3. Mostrar un resumen de conteos por severidad antes de la lista detallada y permitir filtrar por cara, slot, asset y código.
4. Ofrecer un enlace “Volver a ejecutar” cuando el reporte quede obsoleto después de una edición.
5. Mantener el panel cerrado por defecto, pero conservar su estado de apertura al cambiar de etapa durante la sesión.
6. Cuando se habilite la navegación front/back, mostrar siempre la cara activa y el alcance del reporte para evitar mezclar resultados.
7. Añadir una vista de evidencia por asset con página, caja, hash y dimensiones físicas antes de activar Preview.

## 9. Próxima fase recomendada

La siguiente fase debe crear fixtures PDF canónicos y criterios de paridad métrica/visual:

- MediaBox, CropBox, TrimBox y BleedBox desplazadas o ausentes;
- páginas múltiples y rotaciones intrínsecas;
- bleed real y bleed por espejo mediante opción explícita;
- transformaciones cardinales y offsets internos;
- frente y dorso con flip definido;
- marcas y clipping;
- comparación canvas, preview y PDF con tolerancias documentadas.

Solo después de esa evidencia debe habilitarse una Preview productiva mínima detrás de un gate separado. PDF final, CTP y extracción de código compartido V1 siguen siendo fases independientes.

## 10. Elementos que no deben tocarse todavía

- `layout-v2.schema.json` y la semántica persistente de Layout V2.
- Autosave, compare-and-swap, revisiones, locks y undo/redo.
- `engines/step_repeat_pro_engine.py` y cualquier módulo compartido con V1.
- El renderer productivo legacy y las rutas V1.
- CTP, marcas, dúplex y Preview productiva sin fixtures y contrato cerrados.
- Resize, transformaciones internas, nesting, hybrid e IA dentro de esta fase de salida.

## 11. Criterio de cierre

La auditoría se considera cerrada cuando las suites indicadas permanecen aprobadas, Flask V2 responde, el recorrido desde cero conserva persistencia y el documento 25 se usa como referencia para la fase de fixtures. La evidencia no acredita todavía que V2 pueda producir un PDF final.
