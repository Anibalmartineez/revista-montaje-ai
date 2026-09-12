# Fase 28 — Evidencia de paridad Preview–canvas V2

Fecha de corte: 2026-09-11.

Esta fase valida la Preview mínima de la Fase 27 contra la geometría persistida de Layout V2. Es una fase de evidencia y contrato de prueba; no habilita Preview por defecto, PDF final ni CTP.

## 1. Alcance

Se añadió una prueba focalizada que construye un PDF asimétrico reproducible, lo carga en un job V2 aislado y renderiza una cara con el gate de Preview activado solo dentro de la prueba. El layout usa una hoja de 120 × 80 mm y un slot de 40 × 20 mm centrado en 60 × 40 mm, sin bleed ni marcas.

La prueba comprueba:

- que el PNG conserva las dimensiones físicas de la hoja, permitiendo únicamente el redondeo de un píxel propio del rasterizador;
- que el contenido visible queda dentro de los límites del slot calculados desde el centro trim del Layout V2;
- que las dos mitades asimétricas mantienen su orden izquierda/derecha;
- que la generación no cambia la revisión ni el layout guardado.

La tolerancia de esta prueba es de ±2 píxeles para los bordes rasterizados. La tolerancia física propuesta para la futura comparación métrica continúa siendo 0.01 mm; esta prueba no la sustituye.

## 2. Evidencia ejecutada

Prueba focalizada:

```text
venv\Scripts\python.exe -m pytest tests/editor_offset_v2/test_preview_v2.py tests/editor_offset_v2/test_pdf_fixture_parity_v2.py -q
```

Resultado: **9 passed**.

Suite Python V2:

```text
venv\Scripts\python.exe -m pytest tests/editor_offset_v2 -q
```

Resultado: **417 passed, 1 omitido**.

La validación de fixtures de la Fase 26 continúa cubriendo cajas, páginas, rotaciones, ausencia de bleed físico y artwork asimétrico. Esta fase agrega la primera comprobación automática de que una Preview derivada ocupa el footprint geométrico esperado.

## 3. Límites de la evidencia

La prueba usa una fuente sintética y transformación interna identidad. Todavía no demuestra:

- equivalencia visual completa entre SVG del canvas, PNG Preview y PDF final;
- clipping con contenido fuera de TrimBox;
- bleed por espejo autorizado;
- offsets, escalas, rotaciones internas o flip del dorso;
- marcas técnicas, perfiles de color, fuentes o antialiasing de producción.

El gate `EDITOR_OFFSET_V2_PREVIEW_ENABLED` debe permanecer apagado en despliegues normales. El preflight continúa siendo quien bloquea operaciones no demostradas.

## 4. Próximo gate

El siguiente trabajo debe cerrar, con fixtures asimétricos y tolerancias aprobadas, el orden matricial de transformaciones internas, clipping, bleed por espejo, marcas y flip dúplex. Después se podrá diseñar la comparación estable canvas–Preview–PDF y el renderer PDF propio de V2.

No se modificaron el schema Layout V2, persistencia, Repeat, motores compartidos, rutas V1, CTP ni el PDF final.
