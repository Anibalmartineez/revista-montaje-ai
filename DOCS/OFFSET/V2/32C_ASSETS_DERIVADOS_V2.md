# Fase 32C — Derivados de página V2

## Objetivo

Preparar una edición física controlada de una página PDF durante el armado sin
alterar el asset original.

## Comportamiento implementado

- Endpoint optativo `POST /api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/derived-page`.
- El endpoint permanece bloqueado por `EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED`.
- Valida asset, hash físico, página, caja PDF, sangrado y opción explícita de espejo.
- Materializa una página normalizada V2 con el preparador PDF existente.
- Publica el PDF derivado y un manifiesto JSON mediante escritura atómica.
- El manifiesto conserva asset fuente, página, caja, bleed, permiso de espejo,
  revisión del layout, tamaños físicos y hashes.
- El PDF fuente y Layout V2 no se modifican.

## Alcance y límite

Esta fase entrega la infraestructura segura de derivados. El derivado todavía no
reemplaza automáticamente `slot.source` ni se usa en la salida productiva; esa
conexión requiere un contrato explícito de revisiones de asset y paridad canvas,
preview y PDF.

## Archivos

- `editor_offset_v2/application/derived_asset_service.py`.
- `editor_offset_v2/blueprint.py` y `editor_offset_v2/config.py`.
- `tests/editor_offset_v2/test_assets_routes_v2.py`.

