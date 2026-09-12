# Fase 24 — Preflight ejecutable mínimo del Editor Offset Visual V2

Fecha: 2026-09-11.

## Alcance

Esta fase convierte el contrato documental de [21](21_CONTRATO_PREFLIGHT_V2.md) en una primera comprobación ejecutable, aislada del renderer y de V1. La ruta `POST /api/editor-offset-v2/jobs/<job_id>/preflight` analiza la revisión guardada y publica un reporte JSON inmutable en `reports/<report_id>.json` mediante escritura temporal y reemplazo atómico.

El servicio comprueba:

- contrato y revisión de Layout V2;
- existencia, ruta segura, hash, legibilidad, páginas, rotación y cajas del PDF físico;
- coherencia entre la fuente seleccionada y el slot;
- contención del trim en el pliego, bleed frente al área imprimible y solapes por cara;
- las restricciones conocidas del adaptador de salida temporal.

Los resultados se identifican con `report_schema_version = 1`, política `editor-offset-v2-minimal/1`, analizador `editor-offset-v2-preflight/1` y tolerancia de metadata PDF de `0.01 mm`. La respuesta incluye decisiones para `preview`, `pdf_final` y `ctp`; todas permanecen bloqueadas porque el gate de capacidades productivas sigue deshabilitado. Esta fase no genera PDF, preview ni CTP.

## Frontera de código

- `editor_offset_v2/domain/preflight_contract.py`: envelope y referencias del reporte.
- `editor_offset_v2/application/preflight_service.py`: análisis físico y geométrico, sin mutar Layout V2.
- `editor_offset_v2/schemas/preflight-report.schema.json`: forma transportable del envelope.
- `editor_offset_v2/blueprint.py`: endpoint V2 y URL de contexto.
- `static/js/editor_offset_v2/output_panel.js`: ejecución manual, estado desactualizado y agrupación visual.
- `reports/`: artefacto persistente por job; no se incorpora al Layout V2.

`GET /output-capabilities` continúa siendo el diagnóstico temporal existente. No se renombró ni se convirtió silenciosamente en preflight.

## Validación

- `tests/editor_offset_v2/test_preflight_v2.py`: publicación atómica, bloqueo del gate, detección de identidad física alterada y rechazo de opciones no definidas.
- suites Node V2 y sintaxis JavaScript para conservar la UI existente.
- suites Python V2 y Playwright V2 deben ejecutarse como validación de integración de esta fase.

## Rollback

La reversión consiste en retirar el endpoint, servicio, contrato, schema, UI y pruebas de esta fase. No requiere migrar Layout V2 ni borrar layouts; los reportes publicados quedan como artefactos históricos del job.

## Siguiente fase

La siguiente fase debe definir fixtures PDF y criterios de paridad canvas/preview antes de habilitar una preview productiva limitada. PDF final, marcas y CTP siguen fuera de alcance.
