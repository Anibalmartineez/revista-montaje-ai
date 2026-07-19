# Fase 7 — Motor Repeat para Editor Offset Visual V2

## Objetivo

Esta fase conecta Layout V2 con el motor productivo `engines/step_repeat_pro_engine.py` mediante una frontera aislada. El motor no se modificó y ningún campo legacy entra en `layout_v2.json`.

```text
Layout V2 persistido
    ↓
RepeatService
    ↓
RepeatEngineAdapter
    ↓
Step & Repeat PRO existente
    ↓
RepeatResultV2 no persistido
    ↓
ApplyRepeatCommand
    ↓
Store + undo/redo + autosave
```

## Responsabilidades

`RepeatService` valida la petición, el job y su revisión, carga exclusivamente el layout persistido y genera un `operation_id` determinista a partir de job, revisión, works, cara, settings y modo de aplicación.

`RepeatEngineAdapter` es el único componente que conoce simultáneamente:

* works, assets, fuentes y geometría V2;
* el kernel geométrico V2;
* la entrada temporal requerida por Step & Repeat PRO;
* la salida legacy del motor;
* la conversión de esa salida a slots V2.

El endpoint solo calcula. No guarda slots, no incrementa revisión y no modifica el layout recibido.

## Endpoint

```http
POST /api/editor-offset-v2/jobs/<job_id>/imposition/repeat
Content-Type: application/json
```

Ejemplo:

```json
{
  "base_revision": 4,
  "work_ids": ["work_001"],
  "face": "front",
  "settings": {
    "horizontal_gap_mm": 4,
    "vertical_gap_mm": 3,
    "exact_quantity": true,
    "fill_remaining_space": false,
    "allow_partial": false
  },
  "apply_mode": "add"
}
```

`apply_mode` admite:

* `add`: conserva todos los slots existentes;
* `replace_work_face`: al aplicar, reemplaza únicamente slots de los works seleccionados en la cara solicitada.

Una petición estructuralmente incorrecta, un job inexistente o un conflicto de revisión usa errores HTTP controlados. Una petición válida cuyo montaje no es aplicable devuelve `ok = true` con `result.success = false`, `slots = []` e issues estructurados. Esto permite mostrar el diagnóstico sin confundirlo con un fallo de transporte.

## Contrato de salida

La propuesta usa modelos explícitos:

* `RepeatResultV2`;
* `RepeatIssueV2`;
* `RepeatMetricsV2`.

Incluye:

```text
success
operation_id
generated_at
slots
requested
placed
unplaced
overproduced
warnings
metrics
issues
```

Si existe un error geométrico o de capacidad, `success` es falso y `slots` siempre está vacío. No se entrega una lista parcial como si fuera una propuesta aplicable cuando `allow_partial` es falso.

## Validación de works y fuentes

Cada work seleccionado aporta:

* trim sin rotar;
* bleed separado;
* cantidad solicitada;
* rotaciones cardinales permitidas;
* prioridad;
* zona y flujo preferidos;
* fuente de la cara solicitada.

La operación bloquea explícitamente:

* work inexistente;
* fuente frontal o posterior ausente;
* asset inexistente o con estado distinto de `ready`;
* página inexistente;
* caja PDF ausente;
* placeholder de desarrollo;
* cara no habilitada;
* layout, cantidad, dimensiones o rotaciones inválidas según el contrato V2.

El validador Layout V2 se ejecuta al leer el job. El adaptador vuelve a validar sus capacidades y referencias específicas antes de invocar el motor.

## Conversión V2 → motor

La representación temporal entrega al motor:

```text
sheet.size_mm                  → sheet_mm
sheet.printable_margins_mm    → margins_mm [left, right, top, bottom]
imposition gaps               → spacingSettings
work.id                       → design.ref
work.trim_size_mm             → design.width_mm / height_mm temporales
work.bleed_mm                 → design.bleed_mm
work.requested_forms          → design.forms_per_plate
work.allowed_rotations_deg    → orientación permitida
```

Los nombres `width_mm`, `height_mm`, `designs` y demás vocabulario legacy solo existen dentro del adaptador. Nunca se serializan en Layout V2.

`preferred_zone = none` se traduce explícitamente a `auto`. Los flujos V2 `rows` y `columns` se traducen a `horizontal` y `vertical`; `manual` se traduce a `auto`. Estos aliases son una política declarada, no una heurística sobre geometría.

## Conversión motor → V2

El motor devuelve `x_mm/y_mm` como esquina inferior izquierda del footprint productivo y, para 90°, devuelve `w_mm/h_mm` intercambiados.

El adaptador no reutiliza esas dimensiones como trim persistido. Para cada resultado:

1. recupera el trim original del work;
2. recupera el bleed original;
3. determina la rotación cardinal autorizada;
4. calcula `productive_size(trim, bleed)` con el kernel;
5. calcula el tamaño orientado con `oriented_size()`;
6. construye `Bounds` desde la esquina productiva devuelta;
7. usa `Bounds.center` como centro trim V2;
8. persiste el trim original, nunca el tamaño orientado;
9. genera fuente, transformación, locks, marcas y `generated_by` V2.

Ejemplo:

```text
Work trim:              70 × 20 mm
Rotación elegida:       90°
Salida temporal motor:  w=20, h=70
Slot V2 persistible:    trim=70 × 20, rotation=90
```

No se crea `slot_box_final`, `design_ref`, `posiciones_manual`, bleed expandido ni footprint persistido.

## Rotaciones

El motor público elige orientación 0° o 90°. El adaptador representa las cuatro rotaciones V2:

* 0° y 180° comparten footprint horizontal;
* 90° y 270° comparten footprint vertical.

Si un work solo permite 180°, el motor calcula el footprint horizontal y el slot V2 se etiqueta 180°. Si solo permite 90° o 270°, el adaptador intercambia únicamente la entrada temporal para obligar el footprint vertical y restaura el trim original al normalizar.

No se normalizan ángulos fuera del contrato.

## Geometría e invariantes

Antes de declarar éxito se usa el kernel V2 para comprobar:

* footprint con bleed dentro del área imprimible;
* rotación cardinal;
* ausencia de overlap entre slots propuestos;
* ausencia de overlap con slots existentes en modo add;
* ausencia de overlap con slots no reemplazados en modo replace.

El área imprimible usa los cuatro `sheet.printable_margins_mm`. Dos footprints que solo se tocan en el borde no se consideran solapados, conforme al kernel.

El motor actual no acepta obstáculos existentes como entrada. En modo add, si una propuesta colisiona con un slot existente, el adaptador la bloquea; no intenta recolocarla mediante una fórmula paralela.

## Cantidades

El resultado distingue:

* `requested`: suma de `requested_forms` de los works seleccionados;
* `placed`: slots realmente propuestos para la cara;
* `unplaced`: `max(requested - placed, 0)`;
* `overproduced`: `max(placed - requested, 0)`.

Cada slot equivale a una forma de un work en una cara. No se confunden slots físicos con páginas PDF ni con caras combinadas.

### Cantidad exacta

Con `fill_remaining_space = false` nunca se supera lo solicitado. `exact_quantity` queda registrado en la configuración de imposición y expresa que la cantidad es el objetivo exacto. Desactivarlo no autoriza por sí solo sobrantes: la única autorización explícita para sobreproducción es `fill_remaining_space`.

### Parcialidad

El motor original falla de forma atómica cuando no caben todas las formas. Si `allow_partial = true`, el adaptador usa los conteos de intento informados por el motor, reduce determinísticamente la solicitud temporal y vuelve a calcular hasta obtener una propuesta válida. Si no cabe ninguna forma, el resultado sigue siendo error.

### Completar espacio

Con `fill_remaining_space = true`, primero se garantiza la cantidad base —o la parcial aceptada— y después se busca capacidad adicional mediante llamadas acotadas por el área imprimible. Para varios works, la capacidad adicional se asigna determinísticamente en orden de prioridad. Toda sobreproducción se informa.

## Frente y dorso

Repeat se calcula independientemente para `front` o `back`. La fuente se toma de `front_source` o `back_source` según la cara. El adaptador no inventa dorso, no copia posiciones del frente y no aplica volteos dúplex automáticos.

Una operación posterior solo puede ejecutarse si la cara está habilitada en `faces.enabled`.

## Aplicación como comando

`ApplyRepeatCommand` recibe una propuesta exitosa y todos sus slots. Al ejecutar:

* añade o reemplaza según el modo elegido;
* actualiza `imposition.engine`, settings y `last_result`;
* conserva assets y works;
* genera una única entrada de historial;
* deja el layout dirty;
* activa el autosave normal.

Undo elimina todos los slots propuestos juntos, restaura los slots reemplazados en sus posiciones originales y restaura el bloque `imposition` previo. Redo vuelve a aplicar exactamente la propuesta.

Un resultado fallido o vacío no puede construir el comando.

## Panel Repeat

El inspector derecho incorpora:

* selección múltiple de works;
* cara;
* gaps horizontal y vertical;
* cantidad exacta;
* parcialidad;
* completar espacio;
* add/replace;
* cálculo separado de aplicación;
* resumen de solicitadas, colocadas, faltantes, sobrantes y aprovechamiento;
* issues y warnings sin `alert()`.

Si existen cambios locales, el panel guarda primero. Un conflicto 409 usa el estado de conflicto ya definido por el store. Cambiar cualquier control invalida la propuesta anterior.

## Métricas

El aprovechamiento es:

```text
suma de áreas productivas de slots propuestos / área imprimible × 100
```

El área productiva incluye bleed. Como no existe overlap en una propuesta válida, la suma es una métrica directa y determinista.

## Seguridad y pureza

* El servidor carga el layout por ID de job validado.
* La revisión debe coincidir antes de calcular.
* El payload usa campos y tipos estrictos; no acepta NaN, infinitos ni gaps negativos.
* El endpoint no recibe rutas ni archivos.
* El adaptador trabaja sobre copias y no modifica el layout recibido.
* La respuesta no persiste slots ni revisión.
* Los IDs de operación y slots se derivan del request y la revisión.
* El motor legacy permanece encapsulado y sin modificaciones.

## Tests

La cobertura incluye un work, varios works, bleed 0 y 3 mm, rotación 0 y 90, trim sin rotar, centro trim, bounds, overlap interno y externo, exactitud, parcialidad, fill, sobreproducción, frente/dorso, referencias rotas, placeholders, pureza, determinismo, endpoint sin persistencia, add/replace, undo/redo, dirty state, autosave y un flujo Playwright completo.

Los fixtures en `repeat_cases.json` no dependen de Python y podrán reutilizarse en un futuro adaptador TypeScript.

## Limitaciones y próxima fase

* El motor no reacomoda propuestas alrededor de slots existentes; add bloquea la colisión.
* Fill distribuye excedentes por prioridad, no mediante optimización multiobjetivo.
* No hay preview fantasma de slots sobre el canvas antes de aplicar; existe resumen productivo.
* No se espeja ni sincroniza automáticamente el dorso.
* No se implementan Nesting, Hybrid, CTP, preview productivo ni PDF final.

La siguiente fase debe conectar preview y exportación a través del OutputAdapter V2, consumiendo exactamente los slots persistidos por este flujo y sin volver a implementar la geometría Repeat.
