# Fase 30 — Marcas de corte y dúplex en Preview V2

> Corte posterior 39B: compositor PDF nativo y artwork transformado; capacidades v3. Perfil, marcas, limites y evidencia actual en [plan 39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md). Este documento conserva la evidencia de su fase.

Fecha de corte: 2026-09-11.

Esta fase completa la representación diagnóstica de marcas de corte por slot y el volteo dúplex básico en la Preview propia de V2. No habilita PDF final ni CTP.

## 1. Alcance implementado

- `crop_marks` dibuja cuatro pares de marcas alrededor del trim de cada slot, respetando su rotación cardinal.
- Las marcas se dibujan en la capa de la hoja y no se recortan al artwork del slot.
- `faces.duplex.flip = long_edge` refleja la cara posterior horizontalmente.
- `faces.duplex.flip = short_edge` refleja la cara posterior verticalmente.
- La reflexión afecta simultáneamente a posiciones, orientación de slot, contenido y clipping.
- `registration_marks`, `technical_text` y `color_bar` continúan bloqueados con `PREVIEW_MARKS_UNSUPPORTED`.

La operación sigue siendo solo lectura respecto del Layout: genera un PNG atómico bajo `previews/` sin cambiar revisión, assets ni slots.

## 2. Política de seguridad

El perfil debe pedir explícitamente `crop_marks` para dibujarlas. Ninguna marca no soportada se descarta silenciosamente. El flip se aplica únicamente a la cara `back` cuando el dúplex está habilitado; no se inventa un dorso ni se copia el frente.

## 3. Validación

La prueba `tests/editor_offset_v2/test_preview_v2.py` verifica:

- generación con marcas de corte;
- orientación asimétrica del contenido tras `long_edge`;
- preservación del layout y la revisión;
- bloqueo de registro, texto técnico y barra de color;
- compatibilidad conjunta con transformaciones y bleed por espejo.

Resultados:

```text
venv\Scripts\python.exe -m pytest tests/editor_offset_v2/test_preview_v2.py -q
10 passed

venv\Scripts\python.exe -m pytest tests/editor_offset_v2 -q
422 passed, 1 omitido
```

## 4. Límites pendientes

La geometría de marcas está definida para Preview diagnóstica y aún no es un contrato de CTP: faltan perfiles de color, registro, texto técnico, barras, offsets de placa, safe areas y tolerancias de imprenta. El flip dúplex requiere todavía comparación visual con un PDF final y fixtures de lectura frente/dorso.

El gate `EDITOR_OFFSET_V2_PREVIEW_ENABLED` permanece apagado por defecto. El siguiente paso implementará un PDF final V2 propio con gate independiente y verificación de cajas, páginas, bleed, transformaciones, marcas y caras.
