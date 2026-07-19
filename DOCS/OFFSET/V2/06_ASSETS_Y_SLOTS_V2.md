# Fase 6 — Assets PDF, páginas, miniaturas y slots reales

## Objetivo

Esta fase incorpora PDFs físicos al Editor Offset Visual V2 sin conectar Repeat, preview productivo, PDF final ni CTP. El flujo implementado es:

```text
PDF multipart
    ↓
AssetService
    ↓
staging privado + firma + SHA-256
    ↓
PdfInspector + ThumbnailRenderer
    ↓
AssetRepository
    ↓
Layout V2 revisionado
    ↓
work y slot real mediante comandos del store
    ↓
miniatura dentro del canvas SVG
```

## Almacenamiento inmutable

Cada job mantiene sus archivos fuera de `static/`:

```text
instance/editor_offset_v2_jobs/<job_id>/assets/<asset_id>/
├── source.pdf
├── metadata.json
└── thumbnails/
    ├── page_1.png
    └── page_n.png
```

`source.pdf` se crea con modo exclusivo y nunca se sobrescribe. El servidor genera un ID `asset_` seguido de 24 caracteres hexadecimales; el nombre original es solo metadata y nunca determina la ruta física. Subir dos veces un archivo con el mismo nombre produce dos assets independientes.

El layout guarda únicamente claves POSIX relativas al job, por ejemplo `assets/asset_<id>/source.pdf`. No persiste rutas absolutas.

## Upload y estrategia transaccional

`POST /api/editor-offset-v2/jobs/<job_id>/assets` recibe `file` y `base_revision` en multipart. El límite se configura con `EDITOR_OFFSET_V2_MAX_UPLOAD_BYTES` y por defecto es 50 MiB.

La incorporación usa una transacción compensatoria de sistema de archivos:

1. comprueba el job y la revisión antes de consumir el archivo;
2. crea un directorio de staging dentro de `assets/`;
3. escribe `source.pdf` por streaming, calcula SHA-256 y sincroniza el archivo;
4. valida tamaño, firma `%PDF-`, estructura PDF, páginas y cajas;
5. genera las miniaturas y `metadata.json`;
6. renombra atómicamente el directorio de staging a su ID definitivo;
7. agrega el asset a una copia del Layout V2 y lo guarda con el control de revisión existente;
8. si falla el layout, elimina únicamente el directorio recién incorporado y validado como hijo directo del job.

Así no se declara listo un asset físico invisible en el layout. No existe una transacción ACID entre archivos, pero la publicación tardía y la compensación limitan el estado intermedio.

## Identidad, hash y metadata

Cada asset físico registra:

* ID seguro generado por el servidor;
* nombre original Unicode;
* `storage_key` relativo;
* MIME canónico `application/pdf`;
* SHA-256 del contenido efectivamente guardado;
* cantidad y detalle de páginas;
* estado y fecha UTC;
* estado resumido de preflight, inicialmente `not_run`.

Los campos resumidos `preflight_status`, `preflight_report_id` y `preflight_updated_at` se añadieron al contrato como opcionales para preservar los layouts V2 ya creados. Todos los uploads físicos nuevos los escriben de forma explícita.

`metadata.json` tiene una versión propia y añade el tamaño en bytes, la caja sugerida y el tamaño sugerido por página. Es metadata del asset, no una segunda fuente de geometría del montaje.

## Inspección PDF y cajas

`pdf_inspector.py` usa PyMuPDF, ya disponible en el proyecto. Lee las cajas nativas desde los objetos PDF y convierte puntos a milímetros con `25.4 / 72`.

Por página obtiene:

* número basado en 1;
* rotación intrínseca cardinal;
* MediaBox;
* CropBox;
* TrimBox;
* BleedBox.

MediaBox y CropBox pueden heredarse por la jerarquía de páginas. TrimBox y BleedBox solo se registran si existen realmente: no se rellenan con MediaBox. Las cajas ausentes quedan como `null` en el Layout V2.

La sugerencia inicial es TrimBox, luego CropBox y finalmente MediaBox. Esta política solo selecciona una caja para la UI; no altera ni inventa cajas del PDF. El sistema de coordenadas de estas cajas conserva el origen inferior izquierdo nativo del PDF.

No se realiza todavía preflight profundo de color, resolución efectiva, transparencias, sobreimpresión o perfiles.

## Miniaturas

`thumbnail_renderer.py` crea PNG RGB por página, con proporción conservada y lado máximo limitado. Se eligió PNG porque PyMuPDF lo produce de manera segura con las dependencias actuales; no se añadió un codificador WebP.

Las imágenes se sirven mediante:

```text
GET /api/editor-offset-v2/jobs/<job_id>/assets/<asset_id>/thumbnails/<page>
```

La ruta valida job, asset, página, claves persistidas, existencia física, contención y ausencia de symlinks. `send_file` recibe únicamente la ruta resuelta por el servidor; el cliente nunca envía una ruta de archivos.

## Works reales

El panel de assets permite elegir asset, página y una caja existente. La caja seleccionada propone el trim, considerando la rotación intrínseca de 90° o 270°. El operador confirma:

* nombre;
* ancho y alto trim;
* bleed, inicialmente 0 mm;
* cantidad solicitada;
* rotaciones cardinales permitidas;
* fuente frontal;
* fuente posterior opcional, que en esta fase puede reutilizar la selección actual.

`CreateWorkCommand` construye un work válido y reversible. No infiere bleed a partir de MediaBox ni genera una fuente posterior no solicitada.

## Slots reales

`CreateSlotFromWorkCommand` crea un slot manual en el centro visible del pliego. Conserva:

* `work_id`;
* asset, página y caja PDF;
* centro trim;
* dimensiones trim sin rotar;
* bleed;
* rotación cardinal 0° inicial;
* `content_transform` compatible (`actual_size`, escala 1, offsets 0, sin espejo);
* locks y datos de producción explícitos;
* `generated_by.type = manual`.

La creación no permite slots sin work ni fuentes inexistentes. El movimiento posterior continúa usando `MoveSlotsCommand`, centro trim y milímetros.

## Artwork en el canvas SVG

El renderer agrega un `<image>` SVG para los slots respaldados por un asset `ready`. La URL siempre apunta al endpoint de miniaturas. La imagen:

* se mantiene dentro del grupo geométrico del slot;
* se recorta con un `clipPath` trim;
* conserva proporción con `preserveAspectRatio="xMidYMid meet"`;
* rota junto con el slot alrededor de su centro trim;
* queda debajo de los overlays de bleed, trim y selección.

El renderer no modifica el layout para adaptarlo a SVG. La inversión del eje Y sigue confinada a `geometry_view.js`.

Limitación visual conocida: la miniatura representa la página renderizada completa; todavía no se genera una miniatura recortada diferente por cada caja PDF seleccionada. El clip trim evita dibujar fuera del slot, pero la previsualización exacta de cajas desplazadas se completará antes de habilitar salida productiva desde el canvas.

## Sustitución de fuente

`ReplaceSlotSourceCommand` cambia asset, página y caja de un único slot seleccionado. Mantiene su work y geometría trim, no modifica otros slots ni borra el asset anterior. Undo y redo restauran exactamente la fuente previa.

Si el tamaño efectivo de la nueva caja difiere del trim del slot, el comando emite una advertencia visible. La discrepancia no se corrige ni escala silenciosamente.

## Store, revisión y persistencia

El upload físico no pertenece al historial undo: cuando termina, el servidor devuelve el Layout V2 canónico con revisión incrementada y el store solo lo aplica si no existen cambios locales, guardado activo o drag activo. Crear works, crear slots y sustituir fuentes sí son comandos locales, dejan el documento `dirty` y usan el guardado general:

```text
PUT /api/editor-offset-v2/jobs/<job_id>/layout
```

Undo nunca elimina archivos. El autosave, los conflictos 409 y la serialización de guardados mantienen las reglas de la Fase 5.

## Seguridad e invariantes

* IDs de job y asset usan formatos estrictos.
* Se rechazan slash, backslash, traversal y rutas absolutas.
* El nombre original no participa en resolución física.
* Se comprueban extensión, MIME, tamaño, contenido no vacío y firma PDF.
* Un PDF estructuralmente corrupto se rechaza antes de publicar el asset.
* Los archivos se escriben y publican únicamente dentro de la raíz configurada del job.
* No se siguen symlinks al servir miniaturas.
* No se sobrescribe `source.pdf`, metadata ni directorios de assets existentes.
* El hash corresponde al archivo almacenado.
* La revisión se verifica antes de leer el upload y vuelve a aplicarse al guardar el layout.
* Los errores no modifican la revisión ni agregan assets al layout.

## API mínima

Upload:

```http
POST /api/editor-offset-v2/jobs/ev2_<id>/assets
Content-Type: multipart/form-data

base_revision=1
file=@arte.pdf
```

Respuesta exitosa `201`:

```json
{
  "job_id": "ev2_<id>",
  "asset_id": "asset_<id>",
  "revision": 2,
  "asset": {"status": "ready", "page_count": 1},
  "layout": {"layout_schema_version": 2}
}
```

Miniatura:

```http
GET /api/editor-offset-v2/jobs/ev2_<id>/assets/asset_<id>/thumbnails/1
```

## Placeholders de desarrollo

El botón de placeholder de la Fase 5 se mantiene identificado como herramienta de desarrollo para caracterización y tests. Los assets placeholder tienen estado de error, no se muestran en el panel de assets reales y el adaptador de salida continúa rechazándolos. Podrán retirarse cuando los tests de canvas y comandos ya no dependan de esa fábrica y la creación real sea la única ruta de pruebas.

## Límites y próxima fase

Esta fase no implementa uploads asíncronos, procesamiento en cola, recorte exacto de miniatura por caja, fuente posterior distinta en un mismo formulario, drag de páginas al canvas, preflight profundo, PreparedAssetService, Repeat, preview, PDF final, CTP, resize, snap ni corrección PDF.

La próxima fase debe conectar Repeat V2 usando únicamente works y slots reales, mantener la semántica del kernel geométrico y dejar los assets físicos inmutables.
