# Fase 32B — Correcciones gráficas de contenido V2

## Objetivo

Permitir ajustes gráficos controlados sobre uno o varios slots sin alterar el PDF
fuente ni el contrato de assets físicos.

## Operaciones disponibles

- ajuste `actual_size`, `contain`, `cover` o `stretch`;
- escala X/Y positiva;
- desplazamiento interno X/Y en milímetros;
- rotación cardinal del contenido;
- espejo horizontal y vertical;
- clipping a `trim_box`, `bleed_box` o sin clipping.

El inspector puede aplicarse a un slot o a una selección múltiple. El cambio se
registra como una única operación reversible y respeta los locks de contenido.

## Límites

Esta fase usa el campo persistente `slot.content_transform`, que ya formaba parte
del contrato V2. No recorta físicamente el PDF, no extiende fondos, no convierte
color y no modifica el asset fuente. Esas operaciones requieren una capa derivada
de página y pertenecen a la Fase 32C.

## Archivos

- `static/js/editor_offset_v2/commands.js`: normalización y
  `SetContentTransformCommand`.
- `static/js/editor_offset_v2/content_transform_inspector.js`: inspector de
  correcciones y aplicación reversible.
- `static/js/editor_offset_v2/bootstrap.js`, `dom_refs.js` y la plantilla V2:
  integración del panel.
- `static/css/editor_offset_visual_v2.css`: presentación del inspector.
- `tests/editor_offset_v2/js/assets_commands_v2.test.cjs`: validación de cambios,
  undo/redo y bloqueo por contenido.

