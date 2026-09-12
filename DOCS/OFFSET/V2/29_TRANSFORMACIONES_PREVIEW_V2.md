# Fase 29 — Transformaciones y clipping en Preview V2

Fecha de corte: 2026-09-11.

Esta fase amplía la Preview propia de V2 para representar el contenido transformado dentro de cada slot. El cambio sigue detrás de `EDITOR_OFFSET_V2_PREVIEW_ENABLED`; no habilita PDF final ni CTP.

## 1. Alcance implementado

La Preview admite ahora, por slot:

- `fit_mode`: `actual_size`, `contain`, `cover` y `stretch`;
- escala independiente X/Y;
- offset interno en milímetros;
- rotación cardinal interna;
- espejo horizontal y vertical;
- clipping explícito a `trim_box` o `bleed_box`;
- bleed por espejo solo cuando la solicitud incluye `allow_mirror_bleed=true` y la fuente no aporta cobertura física.

El footprint del slot continúa derivándose del kernel V2. Las transformaciones se aplican sobre una copia raster en memoria y no modifican el Layout, el asset original ni la revisión guardada.

## 2. Orden de composición

La implementación usa este orden verificable:

1. normalizar página, caja y rotación intrínseca de la fuente;
2. calcular el ajuste al área de clipping;
3. aplicar escala X/Y;
4. aplicar espejo y rotación interna;
5. aplicar la rotación cardinal del slot;
6. desplazar el centro por `offset_mm`;
7. recortar contra el polígono trim o bleed del slot.

Las marcas técnicas y el flip dúplex del dorso siguen bloqueados hasta la fase de contrato de paridad visual.

## 3. Validación

La prueba focalizada `tests/editor_offset_v2/test_preview_v2.py` verifica:

- los tres modos de ajuste distintos de `actual_size`;
- escala, offset, espejo y rotación interna;
- rechazo de bleed sin cobertura física cuando no se concede la opción explícita;
- generación exitosa cuando se concede el espejo;
- límites y orientación del contenido asimétrico frente a la geometría del canvas;
- preservación exacta del layout y la revisión.

Resultados:

```text
venv\Scripts\python.exe -m pytest tests/editor_offset_v2/test_preview_v2.py -q
9 passed

venv\Scripts\python.exe -m pytest tests/editor_offset_v2 -q
421 passed, 1 omitido
```

## 4. Límites pendientes

Esta fase no cierra todavía la equivalencia visual completa con el SVG del canvas ni el PDF final. La Preview rasteriza el contenido a la resolución solicitada; la calidad vectorial y la normalización de color pertenecen al renderer PDF V2. Marcas, flip dúplex, clipping sin límite (`clip_to=none`) y la tolerancia visual de producción requieren fixtures y decisiones propias.

No se modificaron el schema Layout V2, persistencia, Repeat, motores compartidos, rutas V1 ni CTP.
