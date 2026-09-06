# Ensayo controlado de reutilización de salida V1 desde V2

## 1. Autorización y resultado

Fecha: 2026-09-06. Rama de trabajo: `codex/editor-offset-v2-output-preflight`.

El usuario aprobó el ensayo después de identificar el recorrido funcional de
salida V1. Aclaró que se pueden compartir temporalmente sus funciones, con V2
como editor principal y propietario del montaje. La independencia completa es
el destino, no una condición previa para este ensayo. La Fase 19 sigue cerrada.

Resultado: conexión offline implementada y ejecutada, con 78 pruebas focalizadas
aprobadas. Hay evidencia de posiciones, tamaños y cuatro giros sin bleed en
raster y vector_hybrid. También hay reproducciones de incompatibilidades de
bleed y marcas. No es una salida productiva ni una certificación del canvas.

Referencias: [20, estado vigente](20_ESTADO_ACTUAL_POST_REDISENO_UX_V2.md),
[01, contrato Layout V2](01_CONTRATO_LAYOUT_V2.md),
[02, geometría](02_KERNEL_GEOMETRICO_V2.md),
[03, adaptador](03_ADAPTADOR_SALIDA_V2.md),
[21, propuesta de preflight](21_CONTRATO_PREFLIGHT_V2.md).

## 2. Implementación y frontera temporal

Nuevo módulo: `editor_offset_v2/infrastructure/legacy_output_probe.py`.
Entrada: `run_legacy_output_probe(job_root, output_directory,
expected_revision=..., observe_legacy_bleed=False)`.

```text
layout_v2.json guardado
  -> adapt_layout_v2_to_output existente
  -> comprobación de revisión, hash, páginas y cajas físicas
  -> copias byte a byte de fuentes en directorio experimental
  -> serialize_output_job existente
  -> Diseno + MontajeConfig explícitos
  -> realizar_montaje_inteligente -> estrategia manual V1
  -> PDF por cara
  -> generar_vista_previa del PDF de cada cara
  -> concatenación de caras y evidencia del ensayo
```

Imports V1 concentrados y diferidos dentro de infraestructura:

- `Diseno`, `MontajeConfig`, `realizar_montaje_inteligente` de
  `montaje_offset_inteligente.py`;
- `generar_vista_previa` de `montaje_offset.py`;
- concatenación con `PyPDF2.PdfReader/PdfWriter`, siguiendo el patrón del servicio
  V1, sin importar el servicio que interpreta `layout_constructor.json`.

Se reutilizan el adaptador y kernel V2 sin cambiar su comportamiento. Se fija
`modo_manual=True`, `estrategia=manual`, `centrar=False`, `usar_trimbox=True`, sin
rotación automática, pinza, CTP, crop-to-content ni conversiones PDF/X. Las
posiciones proceden exclusivamente del montaje guardado.

El giro raster se traduce a `(-rotation_deg) % 360` en esta frontera porque V1
aplica `c.rotate(-rot)`. El overlay vectorial recibe el giro V2 positivo. Las
pruebas con colores asimétricos corroboran esta traducción sin bleed. El caso
híbrido con bleed tiene la incompatibilidad descrita abajo; no se corrige V1.

## 3. Aislamiento y límites

- Sin rutas Flask, controles nuevos, cambios de canvas ni activación de flags.
- Sin escribir el layout ni los assets fuente. El renderer recibe snapshots.
- Directorio de salida nuevo, fuera del job; no se permite sobrescribir una
  salida existente. Staging propio y publicación por rename al finalizar.
- Se compara otra vez el layout y los hashes originales antes de publicar.
  Esto detecta cambios durante la ejecución, pero no es una transacción
  multiproceso ni sustituye el protocolo productivo propuesto en 21.
- Revisión inesperada, hash distinto, archivo ausente, metadatos discordantes o
  fallo de render no producen un directorio final con resultado parcial.
- Límite del ensayo: 200 slots, pliego hasta 1000 x 1400 mm y 50 MiB por fuente.
- Se conserva el veto actual del adaptador a páginas distintas de 1, cajas
  distintas de TrimBox, rotación intrínseca y transformaciones no soportadas.
- Dos caras explícitas se ensayan en orden front/back; el volteo dúplex se
  rechaza. No hay nueva semántica de caras.
- Bleed positivo se rechaza salvo `observe_legacy_bleed=True`. Esa opción
  autoriza observar la sustitución por espejo, no decide la política V2 ni
  declara que el resultado coincide con el contenido solicitado.
- UserUnit distinto de 1 queda fuera de este ensayo. La inspección reutilizada
  conserva sus límites conocidos con cajas indirectas e información de color.

El archivo `report.json` tiene formato exclusivamente experimental
`probe_version=1` y siempre `production_ready=false`. No es el contrato canónico
de preflight del documento 21. Guarda revisión, huella del layout, fuentes,
selecciones de página/caja, versión PyMuPDF, orden de caras, posiciones recibidas
del motor y observaciones. Se conserva `layout_v2.snapshot.json`, copias de
fuentes, PDFs por cara, `trial.pdf` y sus previews PNG.

## 4. Fixtures, criterios y resultados

Fuente reproducible de fixtures y pruebas:
`tests/editor_offset_v2/test_legacy_output_probe_v2.py`.

Los PDFs se generan localmente con ReportLab y PyPDF2. El arte contiene cuatro
cuadrantes rojo/verde/azul/amarillo y texto de página; el bleed original es
magenta. Hay cajas desplazadas respecto de MediaBox y dos páginas identificables.
No se versionan PDFs binarios ni se utiliza un PDF privado como fixture.

Criterios propios del ensayo, no tolerancias productivas aprobadas:

- dimensiones del pliego y posiciones: 0.01 mm;
- footprint medido en píxeles a 150 dpi: 0.35 mm (aproximadamente dos píxeles);
- muestras RGB interiores: diferencia máxima de 35 por canal;
- preview del mismo PDF: igualdad de bytes RGB al rasterizar a 150 dpi;
- identidad de fuentes y layout: igualdad de bytes/hashes.

| Caso | Resultado demostrado por ejecución |
| --- | --- |
| Cuatro slots descentrados, giros 0/90/180/270, raster y vector, sin bleed | Posiciones y footprint conservados; orientación del arte coherente con V2 |
| Contenido vectorial | Texto recuperable en vector_hybrid; raster no conserva ese texto como objetos PDF |
| TrimBox desplazado, ambos modos | Se conserva el recorte del arte en el fixture ensayado |
| Dos caras explícitas | Dos páginas, orden front/back y posiciones distintas conservadas |
| Preview del PDF | Coincide con la rasterización del PDF de la prueba; no usa la preview gris legacy |
| Bleed nativo magenta frente a espejo | V1 lo reemplaza por colores reflejados del trim en ambos modos |
| Híbrido con bleed y giro 90 | Centro vectorial y marco raster giran en sentidos distintos; discontinuidad de colores reproducida |
| Crop marks con bleed cero | No aparecen líneas de corte aunque estén solicitadas |
| Dos perfiles de marcas con bleed positivo | Aparecen 16 líneas: 8 en cada slot, aunque el segundo las desactiva |
| CropBox, bleed 3 y clip trim, equivalente al caso actual V2 | Rechazo del puente; no se genera un PDF aparente ni se cambian las referencias |
| Página 2, rotación intrínseca, escala interna, CTP | Rechazos estructurados del adaptador actual |
| Fuente ausente/modificada, metadatos físicos distintos, revisión obsoleta | Rechazo antes de publicar |
| Fallo durante render o cambio de revisión durante render | Sin resultado parcial; staging propio retirado |
| Destino dentro del job o ya existente | Rechazo; datos existentes conservados |

Se ejecutó:

```powershell
venv/Scripts/python.exe -m pytest tests/editor_offset_v2/test_legacy_output_probe_v2.py tests/editor_offset_v2/test_output_adapter_v2.py tests/editor_offset_v2/test_pdf_inspector_v2.py -q
```

Resultado: **78 passed** (23 ensayo + 50 adaptador + 5 inspector), 7 avisos de
deprecación de dependencias. La primera ejecución del ensayo tuvo 18 passed y
un fallo en el nombre esperado del código CTP; se corrigió el test al código
existente `UNSUPPORTED_CTP_CONFIGURATION`, sin cambiar el validador.

Para conservar artefactos de una nueva ejecución puede definirse
`EDITOR_V2_PROBE_ARTIFACT_ROOT` a una carpeta de pruebas. Cada caso crea un
subdirectorio exclusivo. Sin esa variable se usa el temporal de pytest.

Evidencia local de esta ejecución, ignorada por Git:

- `output/pdf/offset-v2-output-probe/trial-dzhst049/artifacts/`: cuatro giros vector;
- `output/pdf/offset-v2-output-probe/trial-i_w6sire/artifacts/`: cuatro giros raster;
- `output/pdf/offset-v2-output-probe/trial-2_a4lp2r/artifacts/`: discontinuidad del
  marco de bleed híbrido a 90 grados.

Se rasterizaron con Poppler y se inspeccionaron visualmente el pliego de cuatro
giros vectoriales y un detalle de la discontinuidad del bleed. Poppler terminó
con código 0 y avisos sobre fuentes de sustitución Symbol/ArialUnicode; el texto
Helvetica y los cuadrantes se observaron correctamente. Las mediciones de la
suite usan PyMuPDF; la revisión Poppler constituye evidencia visual adicional,
no una equivalencia certificada entre todos los renderizadores.

## 5. Qué podemos aprovechar y qué falta

**Confirmado:** el recorrido manual V1 se puede invocar desde el montaje V2 sin
recalcular imposición, y la preview puede provenir del PDF. La restricción de
centrado se resuelve por configuración. La diferencia de giro raster sin bleed
se resuelve dentro de la frontera V2.

**No demostrado:** paridad completa con el canvas SVG, conservación de color de
preprensa, sobreimpresión, transparencias, fuentes complejas, todas las cajas
PDF, páginas preparadas o casos reales de producción. El canvas actual sigue
mostrando miniaturas aproximadas.

**Siguiente adaptación recomendada, todavía no implementada:**

1. Preparar la página y caja seleccionadas por V2, incluyendo CropBox sin
   TrimBox, en derivados explícitos sin cambiar el original.
2. Resolver la política de bleed cuando la fuente no lo contiene. El espejo
   debe ser una decisión visible; no se infiere de `bleed_mm=3`.
3. Corregir dentro de V2 la composición de centro/bleed y las marcas por slot,
   reutilizando el dibujo útil de V1 sin modificar el motor compartido.
4. Hacer que canvas y salida representen el mismo recorte y contenido; comprobar
   el montaje actual V2 y las variantes autorizadas antes de abrir una ruta.
5. Habilitar preview/PDF mediante un gate explícito de capacidades demostradas y
   errores; no basta con que el invocador devuelva un archivo.

Siguen fuera de alcance CTP, PDF/X, nuevos comportamientos dúplex, resize,
transformaciones avanzadas, IA y extracción completa de Repeat. El diagnóstico
`output-capabilities` no cambia de significado por existir este ensayo.

## 6. Rollback y trazabilidad

Retirar el módulo experimental y sus pruebas desconecta completamente este
ensayo: no tiene consumidores en rutas ni frontend. Los artefactos locales se
pueden retirar de su carpeta de pruebas sin tocar fuentes ni jobs. Los cambios
documentales de 03/11/20/21 reflejan la aclaración del usuario y deben conservarse
como decisión aunque se retire el invocador.

No se ejecutaron Flask, navegador, Playwright, suite global ni trabajos de
producción. No se modificaron motores/servicios V1, esquema, adaptador existente,
persistencia, comandos ni canvas. No se hizo commit ni push.
