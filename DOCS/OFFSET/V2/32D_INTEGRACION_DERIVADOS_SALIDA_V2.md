# Fase 32D — Integración de derivados con slots y salida V2

## Objetivo

Conectar de forma explícita una página derivada de 32C con un slot V2 y hacer que
Preview y PDF final utilicen esa fuente verificada.

## Contrato

`sourceRef` admite opcionalmente `derived` con:

- `derived_key`: ruta relativa bajo `derived/` del job;
- `derived_sha256`: hash del PDF derivado;
- `source_sha256`: hash del asset físico del que procede.

La referencia es compatible con layouts anteriores porque sigue siendo opcional.
La validación comprueba la forma, la seguridad de la ruta y que el hash fuente
coincida con el asset referenciado.

## Flujo

1. El operador materializa una página mediante el endpoint de 32C.
2. El inspector puede vincular el resultado a un slot con un comando reversible.
3. El slot conserva su `asset_id`, `page` y `pdf_box`, además de la referencia derivada.
4. Preview verifica ruta, hash, legibilidad y correspondencia del asset antes de leerla.
5. PDF final reutiliza Preview y, por tanto, consume la misma fuente derivada.
6. Quitar la referencia vuelve a la fuente original sin eliminarla.

## Gates y límites

La materialización sigue detrás de `EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED`, apagado
por defecto. Preview y PDF final mantienen sus propios gates. El original y los
derivados anteriores se conservan; no se sobrescribe un asset físico.

## Archivos

- `layout-v2.schema.json` y `domain/validation.py`.
- `static/js/editor_offset_v2/commands.js`, `api_client.js`,
  `content_transform_inspector.js` y `bootstrap.js`.
- `editor_offset_v2/application/preview_service.py`.
- pruebas de contrato, rutas, Preview y comandos.

