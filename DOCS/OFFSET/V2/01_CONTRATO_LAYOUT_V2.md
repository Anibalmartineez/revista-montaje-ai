# Contrato Layout V2 del Editor Offset Visual

## 1. Propósito

`layout_schema_version = 2` es el contrato persistente exclusivo del Editor Offset Visual V2.

Es un corte limpio. No interpreta, normaliza ni migra layouts del editor anterior. Un documento sin la versión exacta `2` no es un Layout V2.

Esta primera fase solo define:

* vocabulario canónico;
* JSON Schema;
* validación estricta en Python;
* fixtures mínimo y completo.

Todavía no conecta el contrato con Flask, persistencia de jobs, motores, preview o PDF.

## 2. Fuentes canónicas

Las fuentes ejecutables del contrato son:

* `editor_offset_v2/domain/layout_v2.py`;
* `editor_offset_v2/domain/validation.py`;
* `editor_offset_v2/schemas/layout-v2.schema.json`.

Fixtures de referencia:

* `tests/fixtures/editor_offset_v2/layout_v2_minimal.json`;
* `tests/fixtures/editor_offset_v2/layout_v2_complete.json`.

El validador Python es estricto y no depende de servicios del editor anterior.

## 3. Principios del contrato

1. Trim, bleed, contenido y footprint son conceptos distintos.
2. Las dimensiones trim se persisten antes de rotación.
3. El bleed se persiste como un valor separado.
4. El footprint es derivado y nunca se guarda.
5. La posición persistida es el centro de la caja trim.
6. El contenido de un PDF tiene su propia transformación, independiente del slot.
7. Los assets y las páginas se referencian por identidad estable.
8. Una caja PDF ausente se representa con `null`; no se inventa.
9. Los bloqueos conservan su origen.
10. Las referencias rotas son errores, no advertencias.
11. El contrato no aplica defaults durante la lectura.
12. Campos desconocidos en estructuras críticas son inválidos.

## 4. Datos persistidos

El documento contiene únicamente estado productivo:

* identidad y revisión del job;
* sistema de coordenadas;
* pliego;
* caras habilitadas y modo dúplex;
* assets PDF y metadatos de páginas;
* trabajos lógicos;
* slots;
* configuración y último resultado de imposición;
* exportación y perfiles de marcas;
* configuración CTP.

## 5. Estado que no se persiste

Estos valores pertenecen al store temporal del frontend:

* cara activa;
* selección;
* hover;
* herramienta activa;
* zoom y pan;
* viewport;
* drag o resize en progreso;
* diálogos;
* dirty state;
* estado de autosave;
* errores temporales de red;
* historial undo/redo.

El estado de guardado recomendado es:

```json
{
  "status": "clean",
  "base_revision": 4,
  "last_saved_revision": 4,
  "last_saved_at": "2026-07-18T14:25:00Z",
  "pending_commands": 0,
  "error": null
}
```

Estados previstos: `clean`, `dirty`, `saving`, `save_error` y `conflict`.

## 6. Sistema de coordenadas

El sistema es fijo:

* unidad: milímetros;
* origen: esquina inferior izquierda del pliego;
* X positivo: derecha;
* Y positivo: arriba;
* rotación positiva: antihoraria;
* pivote de rotación: centro trim.

No se permite declarar otro sistema por layout.

## 7. Geometría de un slot

Ejemplo:

```json
{
  "position_mm": {
    "x_mm": 60.0,
    "y_mm": 55.0,
    "anchor": "trim_center"
  },
  "trim_size_mm": {
    "width": 90.0,
    "height": 50.0
  },
  "bleed_mm": 3.0,
  "rotation_deg": 90.0
}
```

`x_mm` e `y_mm` representan el centro trim en coordenadas del pliego.

`trim_size_mm.width` y `trim_size_mm.height` representan dimensiones sin rotar. Una tarjeta `90 × 50` rotada a 90 grados continúa guardándose como `90 × 50`.

`bleed_mm` es uniforme en los cuatro lados y no modifica las dimensiones trim persistidas.

La rotación geométrica del slot admite exclusivamente `0`, `90`, `180` o `270` grados. El contrato no normaliza valores equivalentes: `-90`, `360`, `450`, `89` o `90.0001` son inválidos.

## 8. Footprint derivado

El footprint es la caja productiva con bleed, después de rotación.

Antes de rotar:

```text
productive_width  = trim_width  + 2 × bleed
productive_height = trim_height + 2 × bleed
```

Para un ángulo `θ`:

```text
footprint_width =
    abs(productive_width × cos θ)
  + abs(productive_height × sin θ)

footprint_height =
    abs(productive_width × sin θ)
  + abs(productive_height × cos θ)
```

El futuro kernel geométrico debe calcular además los cuatro vértices rotados. No se permite guardar una copia calculada del footprint dentro del layout, porque podría quedar desincronizada.

## 9. Assets y páginas

Un asset representa un PDF inmutable e incluye:

* ID estable;
* nombre original;
* storage key controlada por el servidor;
* MIME type;
* SHA-256;
* cantidad de páginas;
* estado;
* metadatos por página;
* miniatura derivada;
* resultado de preflight.

Las páginas se numeran desde `1`.

Cada página declara explícitamente:

* MediaBox;
* TrimBox;
* BleedBox;
* CropBox.

MediaBox es obligatoria. Las otras cajas pueden ser `null`. Seleccionar desde un slot una caja con valor `null` es un error de referencia.

Los archivos derivados o corregidos deberán crear otra revisión de asset en una fase posterior; no deberán sobrescribir el PDF fuente.

## 10. Trabajos lógicos

`works[]` define la intención de producción:

* identidad y nombre;
* trim esperado;
* bleed;
* formas solicitadas;
* rotaciones permitidas;
* prioridad;
* zona y flujo preferidos;
* fuente frontal;
* fuente posterior opcional.

Una fuente de trabajo puede ser `null` mientras el trabajo todavía no tenga PDF. Un slot, en cambio, siempre requiere una fuente válida.

`allowed_rotations_deg` solo puede contener valores de la enumeración cardinal `0`, `90`, `180` y `270`, sin duplicados.

## 11. Slots

Cada slot contiene:

* ID único;
* cara;
* referencia a work;
* referencia a asset, página y caja PDF;
* geometría trim;
* transformación de contenido;
* bloqueos;
* perfil productivo;
* procedencia de la operación que lo creó.

El slot no guarda dimensiones expandidas ni footprint.

## 12. Frente y dorso

Las caras válidas son `front` y `back`.

`faces.enabled` declara las caras productivas del documento. Un slot no puede pertenecer a una cara deshabilitada.

El modo dúplex declara:

* si está activo;
* volteo por borde largo;
* volteo por borde corto;
* o ausencia de volteo.

La cara que el operador está viendo no se persiste.

## 13. Transformación de contenido

`content_transform` modifica la colocación del PDF dentro del slot, no el slot:

* `fit_mode`;
* escalas X/Y;
* offset interno en milímetros;
* rotación propia del contenido;
* espejos X/Y;
* clipping a trim, bleed o sin clipping.

`geometry.rotation_deg` rota la caja trim y su footprint productivo alrededor del centro trim. `content_transform.rotation_deg` rota internamente el contenido de la página PDF dentro de esa caja, sin cambiar el footprint del slot.

En la versión inicial ambas rotaciones son cardinales y solo admiten `0`, `90`, `180` o `270`. La rotación interna también queda restringida porque el adaptador de salida todavía no soporta rotaciones libres del contenido. La exportabilidad de las demás transformaciones avanzadas será responsabilidad del preflight y del futuro adaptador de salida.

## 14. Bloqueos

Los bloqueos se separan por superficie:

* geometría;
* contenido;
* producción;
* eliminación.

Cada bloqueo conserva una lista de fuentes:

* `user`;
* `ctp`;
* `engine`;
* `system`.

Una superficie está bloqueada cuando su lista no está vacía. Esto permite retirar un bloqueo CTP sin eliminar un bloqueo manual.

## 15. Imposición

El layout declara:

* motor;
* versión del motor;
* separación horizontal y vertical;
* política de cantidad exacta;
* fill;
* prioridad;
* zonas;
* último resultado.

Motores reconocidos inicialmente:

* `manual`;
* `repeat`;
* `nesting`;
* `hybrid`.

El resultado contiene cantidades solicitadas, colocadas, faltantes y sobreproducidas. Es trazabilidad de la última operación, no reemplaza la lista de slots.

## 16. Exportación y marcas

`export` contiene una sola configuración canónica. No existen cadenas implícitas de precedencia entre slot, diseño y global.

Incluye:

* perfil;
* modo raster o vector hybrid;
* DPI;
* caras y orden;
* combinación en un PDF;
* perfiles de marcas;
* política de bleed;
* preservación vectorial.

Cada slot referencia un perfil de marcas existente.

## 17. CTP

CTP contiene de forma explícita:

* estado habilitado;
* cara de referencia;
* borde y profundidad de pinza;
* offsets de plancha;
* barra de color;
* texto técnico;
* marcas de registro.

La validación geométrica de la envolvente CTP se implementará en el kernel y preflight, no en esta primera fase.

## 18. Revisiones

`job.revision` es un entero no negativo.

En la futura API:

1. el cliente carga una revisión;
2. edita localmente;
3. guarda enviando `base_revision`;
4. el servidor solo acepta el cambio si coincide con la revisión persistida;
5. el servidor incrementa la revisión;
6. una diferencia produce conflicto, no sobrescritura silenciosa.

## 19. Invariantes

El validador comprueba como mínimo:

* versión exacta `2`;
* claves requeridas;
* ausencia de claves desconocidas en estructuras críticas;
* ausencia de campos legacy;
* IDs únicos de assets, works, slots y perfiles;
* referencias válidas;
* páginas y cajas existentes;
* dimensiones positivas;
* bleed no negativo;
* números finitos;
* caras válidas y habilitadas;
* rotaciones geométricas y de contenido limitadas a `0`, `90`, `180` o `270`;
* fuentes de lock conocidas;
* revisión no negativa;
* exportación, imposición y CTP estructuralmente completos.

El validador devuelve todos los problemas encontrados y también ofrece una función que lanza `LayoutV2ValidationError`.

## 20. Campos prohibidos

Layout V2 no permite campos del contrato anterior, entre ellos:

* `w_mm`;
* `h_mm`;
* `slot_box_final`;
* `designs`;
* `design_export`;
* `bleed_default_mm`;
* `gap_default_mm`;
* `spacingSettings`;
* `snapSettings`;
* `active_face`.

Si cualquiera aparece en cualquier nivel, el layout es inválido.

## 21. Ejemplos

El ejemplo mínimo ejecutable está en:

`tests/fixtures/editor_offset_v2/layout_v2_minimal.json`

El ejemplo completo con assets, frente/dorso, Repeat, exportación y CTP está en:

`tests/fixtures/editor_offset_v2/layout_v2_complete.json`

Ambos fixtures forman parte de los tests del contrato y deben permanecer sincronizados con el JSON Schema y el validador Python.
