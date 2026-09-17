# Fase 23 — Preparación de fuentes y ensayo de salida V2

> Corte posterior 39B: compositor PDF nativo y artwork transformado; capacidades v3. Perfil, marcas, limites y evidencia actual en [plan 39](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md). Este documento conserva la evidencia de su fase.

Fecha: 2026-09-06. Estado: adaptación implementada y validada en alcance
experimental; Preview/PDF final productivos todavía no habilitados.

## 1. Autorización y objetivo

El usuario aprobó avanzar con cambios pequeños y pruebas, aprovechando lo ya
preparado en V2 y las funciones de salida que funcionan en V1. Aprobó también
**permitir generar sangrado por espejo mediante una opción explícita**.

V2 sigue siendo el editor principal y la independencia es el destino. Esta fase
continúa el ensayo [22](22_ENSAYO_REUTILIZACION_SALIDA_V1.md); no reabre la Fase 19,
no implementa el preflight canónico del documento 21 ni conecta botones PDF/CTP.

## 2. Flujo implementado y reutilización

```text
Layout V2 guardado + revisión esperada
  -> validación estructural y restricciones aún aplicables del puente
  -> misma conversión geométrica V2 a OutputJob
  -> snapshots físicos con hash y metadata comprobados
  -> preparación propia V2 de página, caja, orientación y bleed
  -> posiciones manuales existentes, sin recentrado ni nueva imposición
  -> renderer V1 raster/vector_hybrid, con fuentes derivadas y bleed adicional 0
  -> marcas solicitadas por slot, dibujadas sobre cada cara
  -> combinación de caras y preview del mismo PDF
  -> reporte, snapshot y publicación exclusiva del ensayo
```

| Archivo | Responsabilidad y frontera |
| --- | --- |
| `infrastructure/prepared_pdf_source.py` | Nuevo propietario V2 de página/caja, normalización y sangrado explícito. |
| `infrastructure/prepared_output_adapter.py` | Adapta derivados al renderer temporal y aplica marcas por slot. |
| `infrastructure/editor_output_adapter.py` | Reutiliza su conversión a OutputJob mediante un helper privado; conserva las restricciones del adaptador público. |
| `infrastructure/legacy_output_probe.py` | Conserva el ensayo 22 y agrega `run_prepared_output_probe(..., allow_mirror_bleed=False)`. |
| `infrastructure/pdf_inspector.py` | Admite bytes para inspeccionar exactamente el snapshot capturado. |
| `application/asset_service.py`, `infrastructure/thumbnail_renderer.py`, `blueprint.py` | Miniatura de la caja seleccionada, sin escribir derivados ni cambiar el job. |
| `static/js/editor_offset_v2/canvas_renderer.js` | Solicita esa miniatura para el artwork de cada slot. |

Los paths de infraestructura/aplicación de esta tabla son relativos a
`editor_offset_v2/`. Se reutilizan Layout V2, schema, kernel, OutputJob,
serialización, resolución segura de assets y restricciones existentes. No se
duplicó la imposición ni se incorporó Layout V1 a V2.

Dependencias V1 efectivamente utilizadas: `Diseno`, `MontajeConfig`,
`realizar_montaje_inteligente`, `draw_cutmarks_around_form_reportlab` en
`montaje_offset_inteligente.py`; preview de `montaje_offset.generar_vista_previa`
y concatenación con PyPDF2. Ninguno de esos módulos compartidos fue modificado.

El algoritmo de ocho bandas reflejadas de `_render_vector_hybrid_bleed` fue
adaptado dentro de V2: las bandas se ubican en rectángulos milimétricos exactos
alrededor del centro vectorial. La llamada directa al marco transparente V1
dejaba líneas blancas por redondeos independientes de píxeles. La revisión visual
detectó ese defecto durante esta fase; la adaptación propia lo corrige en los
fixtures verificados, sin alterar el motor V1.

## 3. Contrato acotado del ensayo

- Página y caja físicas seleccionadas explícitamente: Media, Crop, Trim o Bleed.
  Una caja ausente se rechaza; no se sustituye silenciosamente por otra.
- Se normaliza la rotación intrínseca PDF antes del giro cardinal del slot. Las
  fuentes originales nunca se guardan ni se modifican.
- El PDF derivado tiene una página de tamaño completo, incluido el bleed
  preparado. Su caja completa sirve como portador para V1; el trim real permanece
  definido por el slot V2. No se persiste ese portador como un nuevo asset.
- Con `clip_to=bleed_box`, se conserva el contenido que cubre el sangrado pedido
  cuando la BleedBox física y MediaBox contienen toda esa región. Esto demuestra
  cobertura geométrica, no que un margen blanco tenga contenido imprimible.
- Con clipping trim, o sin cobertura física suficiente, un bleed positivo bloquea
  salvo `allow_mirror_bleed=True`. No se combina silenciosamente bleed parcial con
  espejo. El permiso no reemplaza bleed fuente válido cuando se usa clipping bleed.
- El espejo rasteriza únicamente bandas RGB a aproximadamente 300 dpi; el centro
  sigue vectorial en `vector_hybrid`. El giro del slot se aplica al conjunto.
- `clip_to=none`, escalas/offsets internos no soportados, CTP y dúplex automático
  permanecen bloqueados. La preparación reemplaza cuatro restricciones antiguas
  solamente dentro del ensayo y siempre ejecuta sus comprobaciones físicas.
- Las marcas respetan el flag por slot. Sin bleed se usan trazos de 3 mm como
  decisión experimental explícita; su estilo y conflictos necesitan gate productivo.
- El resultado conserva `production_ready=false`. El reporte experimental no es
  el reporte canónico del documento 21.

Se mantienen controles de revisión, hashes, cajas físicas, rutas seguras,
publicación sin sobrescritura y limpieza del staging propio ante errores. Se
rechazan UserUnit distinto de 1 y anotaciones/widgets sin política de aplanado.
Hay límites experimentales de fuentes/pliego/cantidad; no equivalen todavía a
un presupuesto de recursos o un servicio concurrente de producción.

## 4. Canvas y miniaturas

La ruta existente acepta `?box=media|crop|trim|bleed`. Comprueba identidad del
asset, página y metadata física y devuelve PNG acotado con ETag. Sin query se
conserva la miniatura original de las tarjetas de fuentes.

El canvas usa la caja del slot y la misma preparación de página/orientación que
el ensayo. No se añaden campos al layout, comandos o escrituras. Template, CSS,
DOM, bootstrap y registro de acciones conservan su contrato. Continúa siendo
artwork aproximado: no muestra todavía el espejo generado ni una simulación de
color/overprint, y no certifica transformaciones internas avanzadas. Las guías,
selección y overlays editoriales no forman parte del PDF.

Las miniaturas por caja se calculan en memoria por solicitud; el navegador puede
reutilizarlas durante una hora. Caché de derivados en servidor, retención y
mensajes visuales específicos para PDFs rechazados requieren trabajo posterior.

## 5. Evidencia y pruebas

Baseline Python V2 antes de cambios: **354 passed, 1 skipped**. Al cierre:

| Validación | Resultado |
| --- | --- |
| Python V2 completo | 404 passed, 1 skipped |
| Node V2 completo | 117 passed |
| Ambos archivos Playwright V2 | 21 passed |
| Sintaxis JS del canvas modificado | Correcta |
| Diff y enlaces documentales | Comprobados |

Los 50 tests Python agregados cubren 33 preparaciones de fuente, 12 ensayos
completos y 5 casos adicionales de ruta de miniaturas. El test de navegador
agregado carga un PDF con bordes magenta y trim verde: verifica que el artwork
del canvas solicite TrimBox y reciba 400 × 200 px verdes, sin margen externo.

Fixtures generados dentro de pruebas: cuatro cajas, segunda página distinguible,
rotaciones intrínsecas/cardinales, cajas desplazadas, bleed fuente magenta frente
a espejo de cuadrantes, marcas mixtas y bleed cero, originales inmutables,
bloqueo sin permiso y ausencia de artefactos parciales. Las uniones del espejo
se muestrean a 600 dpi en cuatro orientaciones para detectar huecos blancos.

Tolerancias del ensayo: metadata/dimensiones/posiciones 0,01 mm; contención de
cajas 0,001 mm para redondeos PDF; color interior 35 niveles RGB y hasta 80 en
antialiasing de uniones a 600 dpi. Son tolerancias de estos fixtures, no umbrales
generales de certificación productiva.

La suite mantiene avisos de deprecación de dependencias. El skipped corresponde
a creación de symlinks no disponible en el entorno Windows; no se acreditó esa
variante por ejecución. Playwright utilizó servidores de fixtures con puertos
efímeros y jobs temporales. No se ejecutó la suite global ni Playwright V1.

### Montaje guardado del usuario

Se copió aisladamente el job `ev2_14d0c6f8f60e601aed51f833`, revisión 58. Se
generó una página de 650 × 550 mm, ocho posiciones manuales conservadas dentro
de 0,01 mm, CropBox y espejo explícito de 3 mm. Hashes antes/después confirmaron
que el job real y sus archivos quedaron intactos.

Evidencia local ignorada por Git:

- `output/pdf/offset-v2-prepared/montaje-actual-9lbpc4i_/artifacts-corrected/`:
  PDF, preview, fuentes, snapshot, reporte y `verification.json`.
- `output/pdf/offset-v2-prepared-fixed/trial-s1gx32av/artifacts/`:
  cuatro giros híbridos con espejo corregido y revisión Poppler.

Se inspeccionaron visualmente rasterizaciones Poppler del montaje y del fixture
de cuatro giros. Poppler terminó correctamente; el fixture Helvetica emitió
avisos de fuentes de sustitución Symbol/ArialUnicode. La evidencia real mide
las cajas efectivas de pliego; no se definieron TrimBox/BleedBox productivas del
pliego ni se trasladó el trim de cada pieza a cajas globales del PDF.

## 6. Pendientes, aceptación y próximo gate

Confirmado: selección de página/caja y orientación, posiciones manuales sin
recentrado, conservación del bleed fuente cubierto, espejo explícito con centro
y bandas coherentes, marcas por slot y miniatura del recorte elegido.

Pendiente: paridad visual integral canvas/PDF, color CMYK/ICC, sobreimpresión,
transparencias complejas, fuentes especiales, recursos concurrentes y política
de anotaciones. La existencia de un PDF de ensayo no resuelve esos puntos.

Próxima fase recomendada: servicio V2 de preflight mínimo ejecutable y preview
con alcance limitado a capacidades demostradas. Deberá recibir revisión y una
opción visible de espejo, mostrar bloqueos/advertencias, generar un artefacto
estable y mostrar la preview derivada de ese mismo PDF. Hay que fijar primero
la política de marcas, cajas de pliego y presentación del sangrado en canvas.
Solo después corresponde habilitar la descarga final.

No incorporar en ese gate CTP, PDF/X, resize, nuevas transformaciones internas,
nuevos modos dúplex, IA ni extracción completa de Repeat. No tocar V1 ni fuentes
originales como atajo para resolver esos pendientes.

Rollback: retirar la solicitud `?box=` del canvas y su rama de ruta devuelve el
artwork a las miniaturas anteriores. Retirar el invocador preparado y módulos
nuevos devuelve el ensayo al comportamiento 22. La extracción privada de
OutputJob puede revertirse sin cambiar su contrato público. No hay migración de
layout ni jobs que deshacer. No se hizo commit ni push.
