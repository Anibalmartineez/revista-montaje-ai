# Fase 32E — Guardia de paridad para páginas derivadas V2

> Fase cerrada y superada por 32F. Se conserva como registro de la protección
> intermedia que bloqueaba transformaciones no identidad.

## Objetivo

Evitar que una página derivada se publique con una representación distinta del
canvas mientras el materializador todavía no aplica la matriz completa de
`content_transform`.

## Comportamiento

- La petición de materialización puede declarar `content_transform`.
- El servicio acepta únicamente la transformación identidad y un clipping
  explícito a `trim_box` o `bleed_box`.
- Escala, ajuste, offsets, rotación interna y espejos se rechazan con
  `DERIVED_TRANSFORM_UNSUPPORTED`.
- El inspector deshabilita “Guardar página derivada” para esos casos y explica
  que primero debe restablecerse la transformación.
- El manifiesto conserva la transformación efectiva identidad y la caja usada.
- El asset PDF original, el Layout V2 y los derivados existentes permanecen
  inmutables.

## Motivo

Preview ya representa transformaciones internas en memoria. El materializador de
32C todavía prepara una página PDF sin rasterizar ni aplicar esa matriz. Bloquear
la operación evita declarar una salida WYSIWYG cuando solo se habría aplicado
caja y sangrado.

## Validación

- Prueba API de rechazo de escala no identidad.
- Prueba JavaScript del estado habilitable del inspector.
- Suites V2 de Python y Node.

La aplicación completa de la matriz a un PDF derivado queda como fase propia,
con fixtures de paridad canvas/Preview/PDF y tolerancias documentadas.
