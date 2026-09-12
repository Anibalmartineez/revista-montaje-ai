# Fase 34 — Repeat V2 y orientaciones cardinales en trabajos multipágina

## Objetivo

Los trabajos creados desde varias páginas de un PDF deben conservar las cuatro
rotaciones cardinales permitidas por Layout V2. Esto permite que Repeat evalúe
la orientación física más conveniente cuando una página no cabe sin girarla.

## Problema observado

El planificador de páginas de `editor_offset_visual_v2` mostraba 0° y 90°
seleccionados, pero dejaba 180° y 270° desactivados. Por tanto, cada work
creado desde una página multipágina persistía con un subconjunto de
orientaciones y podía quedar limitado a una sola familia física.

## Cambio aplicado

- Las cuatro casillas (0°, 90°, 180° y 270°) quedan activadas por defecto en
  el constructor de works.
- `createWorksFromSources` conserva el conjunto de rotaciones de forma
  independiente para cada página.
- El adaptador V2 mantiene la traducción explícita de 180° y 270° aunque el
  motor temporal solo devuelva sus clases físicas equivalentes (0° y 90°).
- No se modificó `engines/step_repeat_pro_engine.py` ni ningún contrato V1.

Repeat sigue eligiendo una orientación física por work y por zona de cálculo;
la mezcla arbitraria de rotaciones dentro de una misma fila requiere un motor
V2 propio y queda fuera de esta fase.

## Evidencia

- Node: `assets_commands_v2.test.cjs` verifica que las tres páginas reciben
  `[0, 90, 180, 270]` y que la creación es reversible.
- Python: `test_repeat_engine_adapter_v2.py` verifica la conservación de 180°
  y 270° en la frontera del adaptador.
- Validación focalizada: 10 pruebas Node y 35 pruebas Python en verde.

## Próximos límites

La salida productiva continúa bloqueada por el preflight obligatorio. La
paridad canvas/preview/PDF, las cajas PDF, el bleed, el clipping y la
regeneración se validan en las fases de salida correspondientes.
