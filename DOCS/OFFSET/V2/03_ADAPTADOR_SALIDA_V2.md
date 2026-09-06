# Adaptador de salida del Editor Offset Visual V2

## 1. Objetivo

La Fase 3 creó una frontera aislada entre el contrato limpio del Editor Offset
Visual V2 y la salida productiva existente. El adaptador traduce solamente un
`layout_schema_version = 2` válido. No abre Layout V1, no migra jobs, no infiere
dimensiones y no ejecuta el renderer.

```text
Layout V2
  -> validador estricto V2
  -> preflight de capacidades de salida
  -> kernel geométrico V2
  -> modelos inmutables Output*
  -> serialización temporal legacy
  -> fin de la adaptación; renderer no conectado
```

El adaptador continúa siendo un puente temporal, no el destino arquitectónico final. Jobs y uploads ya existen, y Flask expone un diagnóstico de capacidades de solo lectura; preview y PDF final siguen desconectados. `montaje_offset_inteligente.py` y los servicios V1 permanecen sin cambios. El destino futuro es `Editor V2 -> motor de salida V2 propio`.

Decisión posterior aprobada el 2026-09-06: V2 será el editor principal y tendrá código productivo independiente. Puede copiar y adaptar código útil de V1 para mantenerlo dentro de V2; no debe depender de servicios o motores de negocio compartidos con V1 como arquitectura final. Este puente se conserva para diagnóstico/caracterización y no se ampliará como camino productivo por defecto. Ver [11](11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md) y [21 — Contrato de preflight](21_CONTRATO_PREFLIGHT_V2.md).

## 2. Frontera V2/legacy

El módulo responsable de traducir Layout V2 y emitir los diccionarios temporales
del renderer actual es:

```text
editor_offset_v2/infrastructure/editor_output_adapter.py
```

El dominio V2, el canvas futuro y el store futuro no deben conocer:

- `posiciones_manual`;
- `modo_manual`;
- `slot_box_final`;
- `designs` del contrato V1;
- `design_export`;
- `bleed_default_mm`.

`posiciones_manual` y `modo_manual` se emiten al serializar `OutputJob`. La auditoría de 2026-09-06 identificó una excepción a la separación prevista: `OutputPosition` en `domain/output_contract.py` ya contiene `slot_box_final`. Es deuda del contrato temporal; no se persiste en Layout V2 y no debe heredarse en el contrato nativo. Esta corrección documental no modifica el modelo existente.

## 3. Responsabilidades

El adaptador:

1. valida el layout completo con `validate_layout_v2()`;
2. compara las opciones declaradas con las restricciones modeladas del puente temporal; esa comprobación no demuestra fidelidad del renderer;
3. resuelve los assets físicos dentro de una raíz V2 suministrada por el
   servidor;
4. crea diseños de salida por combinación de asset, página y caja PDF;
5. deriva trim, bleed, bounds y footprint con el kernel geométrico;
6. conserva por separado `front` y `back`;
7. construye modelos inmutables y explícitos;
8. genera el diccionario temporal legacy mediante una serialización separada;
9. devuelve issues estructurados y nunca presenta un contrato parcial como
   exportable.

No corrige datos inválidos, no normaliza rotaciones, no aplica defaults, no
interpreta `w_mm`/`h_mm`, no llama `_resolve_slot_box_final()` y no inspecciona
layouts antiguos.

## 4. Modelos

`editor_offset_v2/domain/output_contract.py` define:

- `OutputIssue`: error o warning con `code`, `message`, `path`, `slot_id` y
  `asset_id`;
- `OutputSourceBox`: caja PDF fuente seleccionada;
- `OutputDesign`: archivo físico resuelto y fuente asset/página/caja;
- `OutputMarksProfile`: marcas solicitadas por el contrato V2;
- `OutputPosition`: geometría inequívoca de un slot para la salida;
- `OutputFace`: posiciones de una cara, sin duplicación implícita;
- `OutputExportConfig`: configuración explícita de exportación;
- `OutputCtpConfig`: configuración CTP tipada, aunque CTP activo permanezca
  bloqueado;
- `OutputJob`: contrato interno completo;
- `OutputAdapterResult`: `success`, `job` e `issues`.

Todos son `dataclass(frozen=True)`. Los diccionarios legacy no son el contrato
interno principal.

## 5. Resolución segura de assets

La API recibe `job_root: Path`. Para cada asset utilizado por un slot:

- `storage_key` debe ser relativo;
- se rechazan rutas POSIX absolutas, rutas Windows absolutas y rutas con drive;
- se rechazan segmentos vacíos, `.` y `..`;
- se resuelve la ruta final y se comprueba que continúe dentro de `job_root`;
- la resolución real también impide que un symlink existente escape de la raíz;
- el destino debe existir y ser un archivo;
- un archivo ausente genera `ASSET_FILE_NOT_FOUND`;
- el adaptador no acepta una ruta absoluta enviada por el layout.

El validador V2 comprueba además que el asset, la página y la caja seleccionada
existan en el contrato. El adaptador exige que el asset tenga estado `ready` y
no omite assets faltantes.

## 6. Conversión geométrica

Layout V2 persiste el centro trim, el trim sin rotar, el bleed separado y una
rotación cardinal antihoraria. El contrato temporal requiere la esquina
inferior izquierda del footprint productivo.

Para cada slot se construye `SlotGeometry` y se llama exclusivamente a:

- `trim_bounds()`;
- `bleed_bounds()`;
- `productive_size()`;
- `oriented_size()`.

La posición temporal usa:

```text
x_mm = productive_bounds.left
y_mm = productive_bounds.bottom
w_mm = oriented_productive_size.width
h_mm = oriented_productive_size.height
slot_box_final = true
source_w_mm = trim_size.width
source_h_mm = trim_size.height
```

No se resta manualmente ancho/alto al centro dentro del adaptador. Para un trim
de `90 x 50 mm`, bleed `3 mm` y centro `(60, 55)`:

| Rotación | Footprint productivo | Esquina inferior izquierda |
| --- | --- | --- |
| 0° | 96 x 56 | (12, 27) |
| 90° | 56 x 96 | (32, 7) |
| 180° | 96 x 56 | (12, 27) |
| 270° | 56 x 96 | (32, 7) |

`slot_box_final = true` declara al renderer que `w_mm`/`h_mm` ya son la caja
productiva orientada. Este campo es una propiedad del contrato temporal, no una
propiedad geométrica persistente de V2.

## 7. Frente y dorso

`OutputJob` siempre mantiene dos objetos `OutputFace`, `front` y `back`, con su
estado de exportación y sus posiciones propias. El adaptador:

- soporta solo frente;
- soporta frente y dorso;
- conserva assets y rotaciones diferentes por cara;
- no inventa el dorso;
- no copia slots del frente;
- no elimina posiciones de una cara para agregarlas a la otra.

En la capacidad temporal actual, si ambas caras se exportan deben solicitarse
en orden `front`, `back` y combinarse en un único PDF. La generación de PDFs
separados queda bloqueada hasta que exista una conexión que la represente.

## 8. Transformaciones de contenido

La rotación geométrica del slot y la rotación interna del contenido siguen
siendo conceptos diferentes. En esta fase la salida segura admite:

- `fit_mode = actual_size`;
- `scale_x = scale_y = 1.0`;
- offset `(0, 0)`;
- rotación interna `0`;
- `mirror_x = mirror_y = false`;
- caja PDF fuente `trim`;
- página fuente `1`;
- `clip_to = bleed_box` cuando el BleedBox físico coincide exactamente con el
  trim más el bleed uniforme del slot;
- `clip_to = trim_box` únicamente cuando el bleed del slot es cero.

El tamaño de la caja trim fuente debe coincidir con el trim del slot cuando se
usa `actual_size`.

La compatibilidad dimensional usa una tolerancia propia de `0.01 mm`, separada de `DEFAULT_TOLERANCE_MM` del kernel. Las cajas PDF provienen de puntos convertidos con `25.4 / 72`; diferencias normales dentro de esa tolerancia no bloquean. Para rotación intrínseca 90/270 se orienta la medida fuente durante la comparación, sin intercambiar ni reescribir el trim persistido. La rotación geométrica del slot no cambia esta comparación.

El adaptador bloquea explícitamente:

- `UNSUPPORTED_CONTENT_FIT_MODE`;
- `UNSUPPORTED_CONTENT_SCALE`;
- `UNSUPPORTED_CONTENT_OFFSET`;
- `UNSUPPORTED_CONTENT_ROTATION`;
- `UNSUPPORTED_CONTENT_MIRROR`;
- `UNSUPPORTED_CONTENT_CLIP`;
- `UNSUPPORTED_SOURCE_PAGE`;
- `UNSUPPORTED_PDF_BOX`;
- `UNSUPPORTED_INTRINSIC_ROTATION`.

Estas funciones requerirán posteriormente un `PreparedAssetService`; dicho
servicio no forma parte de la Fase 3.

## 9. Exportación y marcas

La configuración V2 es la única fuente de traducción. No se aplican las
precedencias de `design_export`, overrides o defaults del editor anterior.

La frontera temporal conserva:

- perfil de exportación;
- modo `raster` o `vector_hybrid`;
- DPI;
- caras habilitadas, orden y combinación;
- política `slot_geometry` para bleed;
- perfil de marcas de cada slot;
- crop marks por slot;
- preservación vectorial.

La salida raster actual está fijada a 300 dpi. `vector_hybrid` exige
`preserve_vector_content = true`; `raster` exige `false`. También se bloquea
`crop_to_content = true`.

Los crop marks por slot se conservan en la serialización, pero su equivalencia productiva no está demostrada. La auditoría de código de 2026-09-06 observó que la normalización manual del renderer legacy no conserva `crop_marks` por posición y que su dibujado está condicionado a bleed positivo. Se requieren fixtures con perfiles mixtos y bleed cero antes de reutilizar esa lógica. No se ejecutó una reproducción durante esa auditoría.

Las marcas de registro, texto técnico y barra de color por perfil no tienen todavía una representación segura por slot en el puente y generan `UNSUPPORTED_MARKS_PROFILE_FEATURE`. No se ignoran.

## 10. CTP pendiente

Con `ctp.enabled = false`, la adaptación puede continuar. La configuración se
conserva en un modelo tipado y la serialización temporal declara CTP desactivado.

Con `ctp.enabled = true`, el resultado contiene
`UNSUPPORTED_CTP_CONFIGURATION` y no produce `OutputJob`. Aunque existen
algunas equivalencias parciales, la semántica completa de placa, cara, pinza,
offsets, barra de color, texto técnico y registro debe resolverse en una fase específica del roadmap vigente.
El adaptador no finge compatibilidad parcial.

## 11. Errores, warnings e invariantes

Cada issue tiene nivel `error` o `warning`. Si existe cualquier error:

```text
success = false
job = null
```

Los warnings de preflight del asset se conservan sin convertir el resultado en
fallido. Invariantes:

- solo entra Layout V2 válido;
- no hay coerciones ni heurísticas;
- el input no se modifica;
- la adaptación es determinista e idempotente;
- ningún path del layout se usa como ruta absoluta;
- toda geometría derivada proviene del kernel;
- un slot conserva asset, página, caja, cara, rotación, bleed y perfil de
  marcas;
- no existe job parcial cuando falla el preflight;
- la serialización temporal es una operación explícita y separada.

## 12. API pública

```python
from pathlib import Path

from editor_offset_v2.infrastructure.editor_output_adapter import (
    adapt_layout_v2_to_output,
    serialize_output_job,
)

result = adapt_layout_v2_to_output(layout, Path("job-v2"))
if result.success:
    temporary_contract = serialize_output_job(result.job)
else:
    issues = [issue.as_dict() for issue in result.issues]
```

El preflight de capacidades también puede ejecutarse sin resolver archivos:

```python
from editor_offset_v2.application.output_service import (
    validate_output_capabilities,
)

issues = validate_output_capabilities(layout)
```

La aplicación expone esta misma frontera sobre el layout persistido:

```http
GET /api/editor-offset-v2/jobs/<job_id>/output-capabilities
```

El endpoint informa revisión, compatibilidad, errores y warnings estructurados sin modificar el layout ni incrementar la revisión. Este diagnóstico significa **compatibilidad con la salida temporal actual**; no equivale a PDF listo para imprimir, preflight final, preview ni ejecución del renderer legacy.

## 13. Serialización temporal

`serialize_output_job()` genera una estructura determinista con:

- `designs` y sus rutas ya resueltas por el servidor;
- `faces.front` y `faces.back`;
- `modo_manual` y `posiciones_manual` por cara;
- `sheet_mm` y `margins_mm`;
- `export_settings`;
- `ctp_config`;
- trazabilidad de asset, página, caja y slot.

Cada posición manual contiene `file_idx`, coordenadas bottom-left, footprint
productivo, rotación, bleed, crop marks y dimensiones trim de la fuente. Esta
forma apunta a la rama manual de `montaje_offset_inteligente.py`, pero aún no se la entrega automáticamente ni se ha demostrado paridad productiva. El diccionario no es un `layout_constructor.json` ni puede pasarse directamente al servicio de salida V1 como si lo fuera.

## 14. Evolución futura de salida

La Fase 3 contemplaba una futura conexión mediante `Diseno` y `MontajeConfig`. La dirección aprobada el 2026-09-06 prioriza salida propia V2 y deja esa conexión como posibilidad de caracterización aislada, no como próximo paso productivo. Una caracterización autorizada deberá:

1. volver a rechazar un resultado no exitoso;
2. usar exclusivamente las rutas resueltas del adaptador;
3. pasar `posiciones_manual` sin recalcular geometría;
4. respetar el orden de caras y la combinación solicitada;
5. comparar preview y PDF final con fixtures de paridad;
6. mantener `montaje_offset_inteligente.py` sin semántica V2.

El destino arquitectónico es un motor de salida nativo V2. Sus capacidades se demostrarán contra el contrato V2 y fixtures propios; no deben replicar errores legacy para alcanzar una paridad aparente. El renderer y el preflight consumirán el kernel V2 para centro, rotación, bleed y footprint. La retirada del diagnóstico temporal tendrá un gate propio y no exige conectarlo antes a producción.

Riesgos adicionales confirmados por lectura: capabilities no inspecciona archivos y admite páginas con preflight `not_run`; el adaptador verifica existencia pero no hash ni cajas físicas; el modelo temporal no transporta `faces.duplex.flip`. El renderer legacy puede recentrar, sintetizar bleed reflejado y producir preview por una ruta distinta del PDF. Por ello `success`/`compatible` nunca significan preflight productivo aprobado. La resolución está especificada como diseño pendiente en el documento 21.

## 15. Fuera de alcance

El alcance de salida todavía no implementa generación PDF, preview, CTP productivo,
transformaciones de contenido ni preparación física de assets. Tampoco modifica
el Editor V1 ni adapta layouts anteriores.

Los casos JSON de `output_adapter_cases.json` son independientes de Python y pueden reutilizarse como caracterización del puente y referencia geométrica. No son fixtures PDF renderizados ni obligan a implementar un adaptador TypeScript o una conexión productiva legacy.
