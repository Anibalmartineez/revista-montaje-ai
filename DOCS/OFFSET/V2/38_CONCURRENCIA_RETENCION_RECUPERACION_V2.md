# Fase 38 — Concurrencia, retención y recuperación operativa V2

> Vigente tras 39C: publicación y limpieza adquieren lock de job y después lock del directorio; las respuestas entregan bytes de la petición. Se limitan Preview/PDF a dos generaciones simultáneas **por proceso**, con 429 `OUTPUT_BUSY` y recuperación del permiso incluso ante errores. Esto no constituye un límite global entre varios workers. Snapshot de fuentes limitado a 128 MiB; perfil limitado a 500 slots y raster a 24 MP. La retención y recuperación se invocan explícitamente: no hay scheduler, purga automática ni limpieza al arrancar. Pruebas de cuatro peticiones y fallo de publicación conservan layout/originales y no dejan PDF parcial. Carga y límites detallados en [39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md).

> Actualización 39A (2026-09-16): preflight nativo V2, política/capacidades versión 2; snapshot de layout, opciones y archivos efectivos. Se rechazan reportes incompletos, obsoletos o incompatibles y derivados ausentes/alterados. Publicación y limpieza coordinadas; entrega desde bytes de la petición. El candidato PDF raster bloquea preservación vectorial hasta 39B. Gates globales apagados. Evidencia y continuación: [plan 39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md). Lo que sigue conserva el corte histórico indicado.

## Objetivo

Evitar carreras entre procesos y ofrecer una limpieza conservadora de
artefactos derivados sin tocar Layout V2 ni los assets fuente.

## Implementación

- `process_lock.py` proporciona un lock de archivo exclusivo para Windows y
  Unix.
- `JobRepository.replace_layout_if_revision` mantiene el compare-and-swap y
  además serializa la escritura entre procesos.
- Preview, PDF final, preflight y páginas derivadas serializan su publicación
  atómica dentro de su directorio.
- `ArtifactLifecycleService` recupera únicamente temporales conocidos y
  conserva los últimos N reportes de preflight, previews y PDFs finales
  gestionados.
- Los derivados de página y los assets fuente no se eliminan mediante la
  retención automática.

## Pruebas

- lock entre hilos y entre dos procesos Python;
- recuperación que elimina solo temporales de publicación reconocidos;
- retención que conserva los artefactos más recientes y no toca fuentes;
- regresión de escritura atómica y compare-and-swap del repositorio;
- validación de publicación de Preview, PDF y derivados.

## Límites

La política de retención aún no se ejecuta automáticamente al iniciar Flask ni
se expone como endpoint público. Requiere una decisión operativa sobre
periodos, permisos y auditoría antes de automatizarla. CTP y el PDF vectorial
definitivo siguen fuera de alcance.
