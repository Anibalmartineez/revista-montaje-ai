# Fase 37 — Contrato canónico de paridad de salida V2

## Objetivo

Fijar las reglas de aceptación que deben compartir el canvas SVG, Preview y
PDF antes de ampliar la operación concurrente o habilitar una salida
productiva.

## Contrato

`editor_offset_v2/domain/output_parity_contract.py` centraliza la versión y las
tolerancias de evidencia:

- cajas PDF y geometría del canvas: `0.01 mm`;
- orden de páginas, cara, rotación y flip: exactos;
- Preview/PDF raster: máximo 2% de píxeles modificados y delta media de 8 por
  canal para el fixture de salida;
- página derivada frente a Preview: máximo 8% y delta media de 12 por canal,
  debido a la rasterización intermedia.

Estas constantes describen aceptación de pruebas. No modifican el schema
persistente ni habilitan ningún gate.

## Evidencia cubierta

El manifiesto PDF y sus pruebas verifican cajas desplazadas o ausentes,
selección Trim/Crop/Media, multipágina, rotaciones intrínsecas, bleed real,
bleed por espejo explícito, clipping, marcas y expectativas frente/dorso.
La prueba de paridad transformada compara Preview, página derivada y PDF
usando las tolerancias centralizadas.

## Límites declarados

La comparación actual usa rasterización controlada de Preview/PDF; todavía no
es una prueba de captura del DOM SVG en un navegador ni de preservación
vectorial/color de imprenta. La implementación de bleed por espejo, el motor
PDF vectorial definitivo y CTP requieren fases independientes.

## Aceptación

No se cambia Layout V2, Repeat, V1, CTP, autosave, locks ni persistencia. El
siguiente gate puede trabajar sobre concurrencia y retención con un contrato de
paridad explícito y versionado.
