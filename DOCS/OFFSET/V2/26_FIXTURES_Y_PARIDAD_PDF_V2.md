# Fase 26 — Fixtures canónicos y criterios de paridad PDF V2

Fecha de corte: 2026-09-11.

Esta fase prepara evidencia reproducible para decidir cómo una futura salida V2 debe conservar la representación del canvas. No habilita Preview, PDF final ni CTP, y no modifica el contrato persistente de Layout V2.

## 1. Alcance

Se incorporan entradas PDF pequeñas, deterministas y versionables para cubrir:

- MediaBox, CropBox, TrimBox y BleedBox desplazadas;
- ausencia de TrimBox y BleedBox sin inventar valores;
- documentos multipágina y rotaciones intrínsecas 0°, 90° y 180°;
- candidato sin bleed físico para la opción explícita de bleed por espejo;
- artwork asimétrico con marcas de corte para observar clipping;
- plan explícito de frente, dorso, flip horizontal, rotación interna y offsets.

La última categoría expresa expectativas semánticas en el manifiesto. El PDF fuente no demuestra todavía que un renderer haya aplicado ese flip o transformación; esa comprobación pertenece a la futura paridad canvas/preview/PDF.

## 2. Artefactos

Los artefactos viven en `tests/fixtures/editor_offset_v2/`:

| Archivo | Evidencia |
| --- | --- |
| `boxes-offset.pdf` | Las cuatro cajas presentes y desplazadas. |
| `boxes-missing.pdf` | Solo MediaBox y CropBox; TrimBox/BleedBox ausentes. |
| `multipage-rotations.pdf` | Tres páginas con rotaciones 0°, 90° y 180°; la página central carece de trim y bleed. |
| `marks-clipping.pdf` | Cajas desplazadas, artwork asimétrico y marcas de corte. |
| `mirror-bleed-candidate.pdf` | Fuente sin bleed físico; requiere opción explícita de espejo. |
| `front-back-flip.pdf` | Dos páginas con `front`/`back` y expectativas de flip y transformación en el manifiesto. |
| `pdf_fixture_manifest.json` | Valores físicos esperados en milímetros y metadatos semánticos de cada caso. |
| `generate_pdf_fixtures.py` | Regeneración controlada de todos los PDFs. |

Regeneración:

```text
venv\Scripts\python.exe tests/fixtures/editor_offset_v2/generate_pdf_fixtures.py
```

El manifiesto es la referencia de la prueba; el inspector no debe derivar TrimBox o BleedBox cuando el PDF no las declara.

## 3. Criterios métricos

La prueba `tests/editor_offset_v2/test_pdf_fixture_parity_v2.py` verifica actualmente:

- cantidad de páginas y orden exactos;
- rotación intrínseca cardinal exacta;
- coordenadas, ancho y alto de cada caja con tolerancia de `0.001 mm` para el fixture redondeado;
- selección de caja sugerida: TrimBox, luego CropBox y finalmente MediaBox;
- intercambio de ancho y alto de la medida sugerida en páginas giradas 90°/270°;
- ausencia real de TrimBox/BleedBox en los casos que no las declaran;
- semántica declarada de cara, flip, rotación interna, offset y clipping;
- que el caso de marcas produzca una rasterización asimétrica y con variación de color.

Para el contrato de salida futuro se propone ratificar:

| Comparación | Tolerancia propuesta | Estado |
| --- | ---: | --- |
| Caja PDF ↔ medida física del Layout | 0.01 mm | Pendiente de aprobación de imprenta. |
| Canvas SVG ↔ geometría normalizada | 0.01 mm por coordenada y dimensión | Pendiente de renderer V2. |
| Página, orden y cara | Exactos | Criterio obligatorio. |
| Rotación cardinal y flip | Exactos | Criterio obligatorio. |
| Preview raster ↔ PDF raster | Umbral por porcentaje de píxeles, aún sin fijar | Requiere elegir DPI, motor, perfil de color y normalización. |

El umbral visual no se declara cerrado con un simple HTTP 200 ni con una comparación de screenshots de navegadores. Debe definirse junto con el motor de rasterización, DPI, color, antialiasing y política de fuentes.

## 4. Política de bleed

Un BleedBox físico se conserva como `source`. Un PDF sin bleed físico permanece sin bleed en la inspección y no se amplía silenciosamente. El caso `mirror-bleed-candidate.pdf` exige la opción explícita `mirror_explicit_option`; si se usa en una fase posterior, el reporte deberá distinguir `source` de `mirror` y conservar la medida solicitada.

La generación del espejo, sus límites, clipping y tolerancias no están implementados por esta fase.

## 5. Hechos e inferencias

Confirmado por ejecución:

- los seis PDFs se regeneran desde un único script;
- `inspect_pdf` lee cajas desplazadas, ausentes, páginas y rotaciones sin sintetizar cajas opcionales;
- las cuatro pruebas de paridad de fixtures pasan;
- la prueba visual mínima detecta artwork asimétrico y marcas en `marks-clipping.pdf`.

Inferido o todavía pendiente:

- las expectativas de frente/dorso y transformación están declaradas, pero no existe renderer V2 que las aplique;
- aún no hay comparación canvas/preview/PDF porque Preview productiva está bloqueada;
- la rasterización de marcas y clipping no fija todavía si las marcas pertenecen al slot, al pliego o a una capa técnica;
- la tolerancia visual final depende de decisiones de color, fuentes, DPI y antialiasing.

## 6. Pruebas necesarias para la fase de renderer

Antes de habilitar Preview productiva deberán existir, como mínimo:

1. prueba de contrato de cada caja y página contra el manifiesto;
2. fixture con contenido fuera de TrimBox para demostrar clipping y bleed;
3. fixture con transformaciones 0°/90°/180°/270° y offsets internos medidos;
4. fixture de frente/dorso con flip verificado por una marca asimétrica;
5. render reproducible de canvas, preview y PDF con la misma geometría;
6. comparación métrica y visual con tolerancias aprobadas;
7. pruebas de error para caja ausente, página inválida, asset cambiado y operación no soportada;
8. artefactos reproducibles y rollback cuando el preflight bloquee la salida.

## 7. Decisiones que siguen abiertas

- algoritmo exacto y límites del bleed por espejo;
- semántica de clipping respecto a TrimBox, BleedBox y área de pliego;
- flip físico del dorso y orientación de lectura;
- propietario de marcas, capas técnicas y offsets internos;
- motor de render y normalización de color/fuentes;
- tolerancia visual y criterio de aceptación de diferencias antialiasing;
- formato del reporte de paridad y retención de sus artefactos.

## 8. Elementos fuera de alcance

No se modificaron `layout-v2.schema.json`, autosave, revisiones, locks, undo/redo, Repeat ni motores compartidos con V1. Tampoco se tocaron rutas o renderer legacy, ni se habilitaron Preview, PDF final, CTP, dúplex productivo, Resize, nesting, hybrid o IA.

## 9. Gate siguiente

La evidencia de esta fase permite diseñar el renderer propio V2, pero no lo implementa. El siguiente gate debe aprobar las tolerancias y decisiones abiertas, y después implementar una Preview mínima detrás de un flag separado. PDF final, CTP y la extracción de código compartido V1 continúan como fases independientes.
