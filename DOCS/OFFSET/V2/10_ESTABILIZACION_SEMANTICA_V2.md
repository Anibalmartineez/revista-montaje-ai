# Fase 8P — Estabilización semántica del Editor Offset Visual V2

## 1. Objetivo

Esta fase estabiliza las capacidades existentes antes de incorporar inspector X/Y, nudge y demás herramientas manuales. No cambia `layout_schema_version`, no añade campos persistentes y no conecta preview, PDF final, CTP ni el renderer legacy.

## 2. Problemas resueltos

- Repeat registraba procedencia mediante un lock de geometría y dejaba una contradicción entre intención editable y contrato.
- Drag y comandos no defendían locks de forma uniforme.
- La UI no distinguía fuente predeterminada del work y fuente efectiva del slot.
- `imposition.last_result` podía interpretarse como estado actual.
- El aprovechamiento de la propuesta podía confundirse con el total proyectado.
- `exact_quantity` aparecía como política independiente aunque el algoritmo visible depende de parcialidad y fill.
- Canvas no mostraba márgenes imprimibles ni distinguía dos tipos de salida de bounds.
- La UI podía solicitar back sin poder navegar a esa cara.
- El placeholder de desarrollo aparecía en el editor normal.
- Un layout válido podía confundirse con uno compatible con el puente de salida.
- El artwork SVG podía parecer productivamente exacto.
- Los documentos de fase podían usarse como descripción vigente.

## 3. Procedencia y locks

Procedencia y capacidad de edición son conceptos independientes:

```text
slot.generated_by -> quién/qué creó el slot
slot.locks        -> qué operaciones están bloqueadas ahora
```

Los slots normales creados por Repeat conservan:

```json
{
  "generated_by": {
    "type": "engine",
    "engine": "repeat",
    "operation_id": "repeat_..."
  },
  "locks": {
    "geometry": [],
    "content": [],
    "production": [],
    "delete": []
  }
}
```

Repeat no usa `engine` como lock por defecto. Si un slot posee realmente un lock `engine`, `user`, `ctp` o `system`, la política lo respeta.

## 4. Política central de capacidades

`static/js/editor_offset_v2/edit_policy.js` es pura y resuelve:

- `move` → `locks.geometry`;
- `delete` → `locks.delete`;
- `replace_content` → `locks.content`;
- `replace_by_repeat` → `locks.delete`.

Las operaciones múltiples son atómicas. Si un ID está bloqueado, se rechaza el conjunto completo y el error expone los IDs. Drag consulta la política antes de iniciar; `MoveSlotsCommand`, `DeleteSlotsCommand`, `ReplaceSlotSourceCommand` y `ApplyRepeatCommand` vuelven a defenderla. La UI deshabilita acciones cuando puede anticiparlo, pero no es la única defensa.

Esta fase no incorpora controles para bloquear o desbloquear. La futura UI solo podrá modificar de forma explícita la fuente `user` y nunca retirar implícitamente locks `engine`, `ctp` o `system`.

## 5. Work source y slot source

- `work.front_source` y `work.back_source` son fuentes predeterminadas para crear slots y calcular propuestas nuevas.
- `slot.source` es la fuente efectiva de la instancia.
- Sustituir `slot.source` no cambia el work ni otros slots.
- Repeat usa la fuente predeterminada del work.
- El override se deriva comparando `{asset_id, page, pdf_box}`; no se persiste un campo adicional.

La lista de slots y el inspector muestran `Fuente sobrescrita en este slot` cuando corresponde. Undo/redo y el guardado normal conservan la fuente efectiva.

## 6. Historial y métricas actuales

`imposition.last_result` se conserva sin reescribirlo cuando el operador mueve, elimina o sustituye slots. La etiqueta es `Resultado al aplicar la última imposición`.

`layout_metrics.js` deriva de `slots[]`:

- slots actuales de la cara;
- slots actuales por work;
- slots cuya `generated_by.operation_id` coincide con la última operación y todavía están presentes.

Estos conteos no se persisten.

## 7. Métricas Repeat

`RepeatMetricsV2` mantiene `utilization_percent` por compatibilidad y declara que representa la propuesta. Añade en la respuesta no persistente:

```text
proposal_utilization_pct
projected_total_utilization_pct
projected_total_occupied_productive_area_mm2
```

El total proyectado suma footprints productivos con bleed de slots retenidos y propuestos en la cara. En `replace_work_face` excluye los slots que serán reemplazados. Los cálculos usan `productive_size()` del kernel V2 y son deterministas. Una propuesta fallida informa área de propuesta cero; no inventa colocaciones.

## 8. `exact_quantity`

El backend continúa aceptando el booleano por compatibilidad. La UI ya no renderiza checkbox y envía siempre `exact_quantity = true`. Las políticas visibles son:

- permitir parcial;
- completar espacio.

`fill_remaining_space` sigue siendo la autorización de sobreproducción. No se inventa una tercera política.

## 9. Área imprimible

`geometry_view.js` deriva el rectángulo de `sheet.printable_margins_mm` en milímetros. El SVG solo transforma esta frontera visual. El canvas diferencia:

- `is-outside-sheet` → `Fuera del pliego`;
- `is-outside-printable` → `Fuera del área imprimible`.

La clasificación usa footprint productivo con bleed y rotación cardinal. No corrige ni bloquea el movimiento y no introduce snap o guías.

## 10. Dorso temporalmente limitado

El backend conserva Repeat `back` y los layouts existentes con slots back siguen siendo válidos. La opción back del panel Repeat normal queda deshabilitada y explica que se habilitará con navegación de caras. La UI no copia frente a dorso ni crea una navegación parcial.

## 11. Placeholder de desarrollo

La fábrica y sus tests permanecen. `EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED` es un flag independiente, `false` por defecto. Solo con `true` se renderizan el botón y la nota de placeholder.

El asset placeholder mantiene `status = error`, issue `DEVELOPMENT_PLACEHOLDER` y rechazo por Repeat/output. Editor V1 y `EDITOR_OFFSET_V2_ENABLED` no cambian.

## 12. Compatibilidad con la salida temporal

Ruta de solo lectura:

```http
GET /api/editor-offset-v2/jobs/<job_id>/output-capabilities
```

Carga el layout persistido, ejecuta `validate_output_capabilities()` y devuelve revisión, `compatible`, `errors`, `warnings` e `issues` con código, path, slot y asset cuando existen. No persiste, no incrementa revisión, no resuelve archivos y no ejecuta el renderer legacy.

La UI guarda primero cambios locales. Presenta `Compatible con salida temporal` o `No compatible con salida temporal`. No usa los términos PDF listo, preview o preflight final.

## 13. Artwork aproximado

Toda miniatura PDF real del canvas se considera aproximada mientras el renderer use la página completa con `meet` y clip trim. Lista e inspector muestran `Vista aproximada del PDF` y explican que offsets de cajas y transformaciones productivas exactas aún no están conectados. Slots sin artwork real no reciben una advertencia falsa.

## 14. Documentación viva e histórica

Documentos vivos:

- `01_CONTRATO_LAYOUT_V2.md`;
- `02_KERNEL_GEOMETRICO_V2.md`;
- `03_ADAPTADOR_SALIDA_V2.md`;
- `08_AUDITORIA_ESTADO_ACTUAL_V2.md`;
- `09_PLAN_HERRAMIENTAS_MANUALES_V2.md`;
- este documento y `11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md`.

Documentos históricos de fase:

- `04_SHELL_Y_JOBS_V2.md`;
- `05_CANVAS_STORE_V2.md`;
- `06_ASSETS_Y_SLOTS_V2.md`;
- `07_REPEAT_V2.md`.

Se conserva su contenido original y se añade un encabezado que redirige al estado y roadmap vigentes.

## 15. Cobertura

Python cubre slots Repeat editables/procedencia, métricas add/replace/fallo, compatibilidad de `exact_quantity`, flags y endpoint de capabilities sin persistencia. Node cubre fuentes de lock, atomicidad, comandos, source override, historial/conteos, área imprimible, artwork aproximado y defaults de UI. Playwright cubre Repeat editable con drag/undo/redo/reload, locks visibles y estado visual/capabilities.

## 16. Límites

No se implementaron inspector X/Y, nudge, rotación manual, duplicado, clipboard, alineación, distribución, box select, snap, guías, resize, transformaciones internas del artwork, navegación de cara, mesa de luz, preflight profundo, corrección PDF, preview, PDF final, CTP ni motor de salida nativo.

## 17. Siguiente fase

Fase 8A incorpora posicionamiento manual preciso: inspector X/Y, delta multiselección, nudge y atajo de guardado. Debe reutilizar `edit_policy.js`, área imprimible, output capabilities y las semánticas estabilizadas; no debe volver a implementarlas.
