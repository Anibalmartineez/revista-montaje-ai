# Fase 35 — Preflight obligatorio para Preview y PDF final V2

> Actualización 39A (2026-09-16): preflight nativo V2, política/capacidades versión 2; snapshot de layout, opciones y archivos efectivos. Se rechazan reportes incompletos, obsoletos o incompatibles y derivados ausentes/alterados. Publicación y limpieza coordinadas; entrega desde bytes de la petición. El candidato PDF raster bloquea preservación vectorial hasta 39B. Gates globales apagados. Evidencia y continuación: [plan 39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md). Lo que sigue conserva el corte histórico indicado.

## Objetivo

Toda salida V2 debe estar respaldada por un reporte de preflight completo,
vigente y habilitado para la operación solicitada. Un HTTP 200 de la ruta de
salida no sustituye esta comprobación.

## Contrato operativo aplicado

`PreflightService.run(job_id, enabled_operations=...)` produce un reporte
persistido con:

- revisión y SHA-256 exactos del `layout_v2.json` inspeccionado;
- evidencia física de assets, páginas y cajas PDF;
- decisiones independientes para `preview`, `pdf_final` y `ctp`;
- severidad y operación bloqueada por cada hallazgo;
- gate de capacidad explícito por operación.

`PreflightService.consume(...)` verifica antes de producir un artefacto que:

1. el job y el layout siguen disponibles;
2. la revisión y el hash del layout coinciden con el reporte;
3. existe una decisión para la operación;
4. la decisión es `eligible`.

Si alguna condición falla, la salida se bloquea con un código estable:
`PREFLIGHT_STALE`, `PREFLIGHT_BLOCKED` o `PREFLIGHT_INVALID_REPORT`.

## Integración

- Preview ejecuta y consume un reporte habilitado para `preview`.
- PDF final ejecuta y consume un reporte habilitado para `pdf_final`, y usa el
  renderer de Preview únicamente como implementación interna de páginas.
- Los errores conservan sus hallazgos para que la interfaz pueda mostrar qué
  operación está bloqueada y por qué.
- El reporte continúa siendo diagnóstico cuando el gate de la operación está
  apagado; no se habilita producción implícitamente.

## Evidencia

Las pruebas cubren salida elegible, reporte obsoleto después de una revisión y
bloqueo de PDF con hallazgos sin crear un PDF parcial. La validación completa
de cajas, bleed, clipping y paridad visual permanece en los fixtures de la
fase 33 y en la fase de PDF final.

## Fuera de alcance

CTP, marcas productivas, cambios de schema Layout V2, autosave, locks, undo/redo
y el motor compartido V1 no se modifican en esta fase.
