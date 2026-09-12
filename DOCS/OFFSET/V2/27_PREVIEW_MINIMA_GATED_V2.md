# Fase 27 — Preview mínima V2 detrás de gate

Fecha de corte: 2026-09-11.

Esta fase incorpora una primera superficie de Preview propia de V2 para comprobar el recorrido canvas → representación física, usando los fixtures y criterios de la Fase 26. Es una salida derivada PNG por cara; no es PDF final ni CTP.

## 1. Gate y ruta

La capacidad se controla con:

```text
EDITOR_OFFSET_V2_PREVIEW_ENABLED
```

Su valor predeterminado es `false`. Cuando está desactivada, la ruta responde `404 PREVIEW_DISABLED`; V1 no resulta afectado.

Con el gate activado:

```text
POST /api/editor-offset-v2/jobs/<job_id>/preview
```

Acepta únicamente `face`, `dpi` y `allow_mirror_bleed`. La respuesta es un PNG servido desde `previews/`, con nombre ligado a revisión, cara y DPI. El layout no se modifica y el archivo se publica atómicamente.

## 2. Alcance soportado

La Preview mínima:

- lee exclusivamente el Layout V2 guardado y los PDFs físicos identificados por hash;
- admite una cara por solicitud;
- conserva la página, caja física, rotación intrínseca y medida de la fuente;
- coloca cada slot con el kernel V2, su centro trim, bleed y rotación cardinal;
- permite bleed por espejo solo si `allow_mirror_bleed=true` cuando la fuente no tiene cobertura física;
- rechaza fuentes ausentes, hash cambiado, cajas discrepantes, páginas inválidas y tamaños incompatibles;
- limita el DPI a 36–300 y el raster a 24 millones de píxeles.

La transformación interna debe ser identidad (`actual_size`, escala 1, offset 0, rotación 0 y sin espejo). Las marcas, el flip dúplex del dorso, perfiles de color, registro, texto técnico y barras siguen bloqueados con errores explícitos hasta cerrar sus contratos.

## 3. Propiedad e independencia

El código vive en `editor_offset_v2/application/preview_service.py` y usa PyMuPDF, el inspector físico, la preparación de fuentes y el kernel V2. No importa `montaje_offset_inteligente.py`, `services/editor_offset_output_service.py`, `strategies/` ni el OutputJob temporal V1. La ruta no invoca el renderer legacy.

La preparación de fuente se reutiliza como utilidad V2 ya adaptada y mantiene el PDF original inmutable. Esta fase no elimina todavía las dependencias legacy del ensayo offline ni modifica Repeat.

## 4. Contrato de error

Los errores de solicitud se devuelven como JSON estructurado. Entre los bloqueos iniciales están:

- `PREVIEW_DISABLED`;
- `PREVIEW_FACE_DISABLED` y `PREVIEW_NO_SLOTS`;
- `INVALID_PREVIEW_DPI` y `INVALID_PREVIEW_REQUEST`;
- `ASSET_MISSING`, `ASSET_IDENTITY_MISMATCH` y `PDF_UNREADABLE`;
- `MISSING_SOURCE_BOX`, `PDF_METADATA_MISMATCH` y `PREVIEW_SOURCE_SIZE_MISMATCH`;
- `PREVIEW_TRANSFORM_UNSUPPORTED`, `PREVIEW_MARKS_UNSUPPORTED` y `PREVIEW_DUPLEX_FLIP_UNSUPPORTED`.

No se genera un PNG parcial si falla un slot. No se corrigen metadatos ni se actualiza la revisión para producir la vista.

## 5. Pruebas

`tests/editor_offset_v2/test_preview_v2.py` cubre:

1. gate separado y apagado por defecto;
2. generación PNG de una cara con layout y fuente física reales;
3. preservación exacta del layout y publicación en `previews/`;
4. rechazo de marcas y transformaciones internas no resueltas.

Resultado del corte: **4 passed** en la prueba focalizada y **416 passed, 1 omitido** en la suite Python V2.

La suite de fixtures de la Fase 26 continúa verificando cajas, páginas, rotaciones y ausencia de bleed inventado. Las comparaciones canvas/Preview/PDF todavía requieren incorporar una captura canónica del canvas y cerrar las tolerancias visuales.

## 6. Pendientes antes de declarar Preview productiva

- definir y aprobar la tolerancia visual y el normalizador de rasterización;
- implementar y probar offsets, escalas, rotaciones internas y espejos dentro del orden matricial aprobado;
- resolver clipping, marcas y flip dúplex con fixtures asimétricos;
- añadir comparación métrica de bounds y comparación visual estable;
- decidir si la UI expone la ruta y cómo presenta revisión, cara y obsolescencia;
- probar concurrencia, retención y regeneración de artefactos derivados.

Hasta cerrar esos puntos, la bandera debe permanecer desactivada en despliegues normales. PDF final, CTP y extracción de código compartido V1 siguen siendo fases independientes.
