# Fase 32A — Trabajos multipágina de Editor Offset Visual V2

## Objetivo

Permitir que un PDF de revista, calendario o catálogo se prepare página por página
sin cambiar el contrato persistente de Layout V2.

## Comportamiento

- El asset físico sigue siendo un PDF inmutable con todas sus páginas inspeccionadas.
- El panel muestra un planificador por página para el asset seleccionado.
- Cada página puede seleccionarse o excluirse y recibe una cantidad de formas propia.
- “Crear works seleccionados” crea un work independiente por página seleccionada.
- Cada work conserva una referencia `asset_id + page + pdf_box` válida.
- La operación completa se registra como un único comando reversible.
- Las dimensiones y la caja PDF se calculan por página, respetando la rotación intrínseca.

## Decisión de compatibilidad

Esta fase no añade campos a `layout-v2.schema.json`. Se mantiene el modelo actual de
un work con `front_source` y `back_source`; el soporte de firmas, encuadernaciones y
relaciones de publicación multipágina queda para una fase posterior.

## Archivos

- `static/js/editor_offset_v2/commands.js`: `CreateWorksCommand` y
  `createWorksFromSources`.
- `static/js/editor_offset_v2/assets_panel.js`: planificador y creación masiva.
- `static/js/editor_offset_v2/dom_refs.js`: referencias DOM nuevas.
- `templates/editor_offset_visual_v2.html`: planificador de páginas.
- `static/css/editor_offset_visual_v2.css`: presentación del planificador.
- `tests/editor_offset_v2/js/assets_commands_v2.test.cjs`: cobertura de creación,
  cantidades, referencias, undo y redo.

## Límites

La fase no implementa firmas automáticas, cosido a caballo, calendarios semánticos,
reordenamiento editorial, edición física del PDF ni cambios en V1.

