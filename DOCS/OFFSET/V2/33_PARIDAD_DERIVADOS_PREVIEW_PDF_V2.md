# Fase 33 — Paridad de derivados, Preview y PDF V2

## Objetivo

Demostrar que una transformación gráfica materializada por 32F se representa una
sola vez y conserva la apariencia observable del canvas en la Preview y en el PDF
candidato V2.

## Alcance

- fixture asimétrico `marks-clipping.pdf`;
- escala X/Y, offset interno, rotación cardinal y espejo;
- clipping a `trim_box`;
- materialización de la transformación a una página derivada;
- vinculación reversible del derivado con el transform del slot reiniciado a
  identidad;
- comparación del recorte de Preview contra el PDF derivado;
- comparación de la Preview completa contra el PDF candidato rasterizado.

La fase es evidencia automatizada. No cambia `layout-v2.schema.json`, no activa
gates por defecto y no declara aprobado el PDF productivo.

## Criterios de comparación

- páginas, orden y dimensiones físicas: exactos dentro de la tolerancia PDF ya
  definida;
- Preview frente a PDF candidato: hasta 2% de píxeles con diferencia superior a
  12 niveles por canal y media absoluta de diferencia de 8 niveles;
- recorte de Preview frente al PDF derivado: hasta 8% de píxeles por clipping y
  redondeo de rasterización, media absoluta de diferencia de 12 niveles;
- layout y revisión: permanecen sin cambios durante la generación; el enlace del
  derivado incrementa revisión una sola vez.

Estas tolerancias son de caracterización para este fixture y DPI 36. No son aún
umbrales de certificación de imprenta. La política productiva debe fijar DPI,
normalización de color, fuentes, antialiasing y tolerancias por perfil.

## Evidencia y límites

La prueba `tests/editor_offset_v2/test_derived_parity_v2.py` verifica que el PDF
derivado transformado y la Preview no sufren una segunda aplicación de escala,
offset, giro o espejo, y que el PDF candidato consume la misma Preview.

No se resuelven en esta fase color CMYK/ICC, preservación vectorial, overprint,
fuentes complejas, tolerancias de registro, CTP ni la publicación productiva.
Los gates de derivados, Preview y PDF final siguen separados y apagados en el
entorno normal.

## Rollback

Retirar el test y este documento no altera código productivo, layouts ni jobs. La
fase 32F continúa proporcionando la materialización transformada y puede
revertirse independientemente mediante su commit.
