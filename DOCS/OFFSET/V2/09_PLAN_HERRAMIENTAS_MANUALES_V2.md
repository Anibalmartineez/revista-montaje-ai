# Plan técnico de herramientas manuales del Editor Offset Visual V2

## 1. Objetivo y punto de partida real

Este plan parte del código auditado después de las fases 1–7. No propone reconstruir el editor ni introducir un framework. Extiende la arquitectura que ya funciona:

> ACTUALIZACIÓN VIGENTE — FASE 8P COMPLETADA
>
> La estabilización semántica descrita en `10_ESTABILIZACION_SEMANTICA_V2.md` precede a 8A. Ya existen política base de locks, slots Repeat editables, área imprimible visible, source override, historial/conteos Repeat, métricas propuesta/total, placeholder oculto, back bloqueado en UI, output capabilities y advertencia de artwork aproximado. Las fases 8A–8H no deben reimplementar estas piezas.

```text
EditorStore
  -> comando reversible
  -> Layout V2 dirty
  -> Renderer SVG
  -> SaveCoordinator
  -> PUT revisionado
```

Base disponible:

- selección simple y múltiple;
- drag por centro trim con preview temporal;
- `MoveSlotsCommand` y `DeleteSlotsCommand`;
- undo/redo, dirty state, autosave y conflicto 409;
- geometría cardinal de vista con fixtures compartidos;
- assets, works, slots reales y Repeat;
- contrato de locks y `generated_by.type = duplicate`;
- kernel Python con polígonos, bounds, SAT y distancias.

Deudas que condicionan el orden después de 8P:

- la UI todavía no permite crear ni retirar locks de usuario, aunque el enforcement base ya existe;
- el inspector es de solo lectura;
- el kernel JS solo cubre bounds cardinales;
- no hay navegación de cara;
- el renderer no aplica `content_transform`;
- OutputAdapter bloquea resize incompatible y transformaciones internas avanzadas.

## 2. Regla conceptual obligatoria

### 2.1 Geometría productiva del slot

Campos:

```text
slot.geometry.position_mm
slot.geometry.trim_size_mm
slot.geometry.bleed_mm
slot.geometry.rotation_deg
```

Define dónde y cuánto ocupa la pieza en el pliego. Afecta footprint, bounds, colisiones, Repeat, marcas y salida. El pivote es centro trim y el trim permanece anterior a rotación.

### 2.2 Transformación interna del artwork

Campos:

```text
slot.content_transform.fit_mode
slot.content_transform.scale_x / scale_y
slot.content_transform.offset_mm
slot.content_transform.rotation_deg
slot.content_transform.mirror_x / mirror_y
slot.content_transform.clip_to
```

Define cómo se coloca la página PDF dentro del slot. No debe mover, redimensionar ni rotar el footprint productivo.

### 2.3 Prohibición de mezcla

- Rotar el slot no debe escribir `content_transform.rotation_deg`.
- Desplazar artwork no debe cambiar `geometry.position_mm`.
- Resize de slot no puede presentarse como resize del PDF.
- Fit/cover no puede cambiar trim o bleed.
- Una herramienta visual no se declarará exportable mientras OutputAdapter la bloquee.

## 3. Convenciones del plan

Abreviaturas de superficie:

- **Comandos:** `static/js/editor_offset_v2/commands.js`.
- **Store:** `static/js/editor_offset_v2/store.js`.
- **Interacción:** `static/js/editor_offset_v2/interactions.js`.
- **Geometría JS:** `static/js/editor_offset_v2/geometry_view.js`.
- **Renderer:** `static/js/editor_offset_v2/canvas_renderer.js`.
- **UI:** `templates/editor_offset_visual_v2.html`, `static/css/editor_offset_visual_v2.css`, `dom_refs.js`, `bootstrap.js`.
- **Salida:** `application/output_service.py`, `infrastructure/editor_output_adapter.py` y sus tests; solo cuando una fase autorice cambios.

Reglas comunes:

1. Toda mutación persistente pasa por un comando con `execute`, `undo`, `redo`, `description` y `affectedIds`.
2. Un gesto continuo produce un solo comando al confirmar.
3. Todo comando persistente deja dirty y activa el autosave existente.
4. Selección, hover, viewport, clipboard interno, guías temporales y previews no se persisten ni activan autosave.
5. La política central `edit_policy.js` ya resuelve move/delete/content/Repeat replace; toda capacidad nueva debe extender esa misma frontera y mantener defensa en UI y comando.
6. Las operaciones geométricas consumen Geometría JS con paridad de fixtures; no se dispersan fórmulas en el renderer.
7. El backend vuelve a validar siempre el Layout V2 al guardar.

## 4. Inventario detallado de herramientas esenciales

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Inspector editable | **No implementada.** El `<dl>` es solo lectura. Permite precisión sin drag. | Renderer debe separar vista/formulario; UI añade X/Y y después rotación. Comandos: reutilizar `MoveSlotsCommand`; no editar objeto directamente. Store: validación de selección única/múltiple. Kernel: finitud/cardinalidad. Sin cambio de contrato para posición/rotación. | Confirmar crea un comando; Escape revierte edición local; dirty/autosave normales. X/Y y rotación cardinal son representables por OutputAdapter. | Node: parsing, no-op, multi delta, locks, undo/redo. Playwright: editar, guardar, recargar. Riesgo: commit por cada tecla. Aceptación: una confirmación = un comando y nunca persiste NaN. |
| Movimiento numérico | **Parcial:** existe drag, no entrada numérica. Mejora registro y repetibilidad. | Inputs X/Y; para multi-selección usar delta explícito, no un centro ambiguo. Comando `MoveSlotsCommand`. Store puede exponer bounds/centro de selección. | Una confirmación atómica; autosave posterior. No cambia contrato ni capacidad de salida. | Node para valores decimales, múltiples, no-op y locks; Playwright para posición exacta tras reload. Riesgo: interpretar absoluto vs delta. Aceptación: semántica visible y centro trim exacto. |
| Rotación cardinal | **Latente:** contrato, renderer, kernel y output la admiten; no hay comando/UI. | Nuevo `RotateSlotsCommand` o `SetSlotGeometryCommand`; UI 0/90/180/270; geometría JS valida. Mantener trim sin intercambiar. Respetar locks de geometría. | Un comando por acción; dirty/autosave. OutputAdapter admite rotación geométrica cardinal. | Node con las cuatro rotaciones, centro conservado, undo/redo; paridad fixture; Playwright 90° + reload. Riesgo: invertir signo SVG o intercambiar trim. Aceptación: centro/trim persistido idénticos salvo `rotation_deg`. |
| Duplicar | **Latente:** `generated_by.type=duplicate` existe. Acelera repetición manual. | `DuplicateSlotsCommand`; IDs seguros en cliente, copia de slot, offset explícito, `source_slot_id`, selección de copias. Puede usar Geometría JS para evitar colocar exactamente encima. | Una operación para todas las copias; undo las elimina juntas; autosave. Mismo asset/work es exportable si original lo era. | Node para múltiples, IDs, fuentes, locks y undo; Playwright duplicar/guardar. Riesgo: IDs colisionados y referencias de origen. Aceptación: copia exacta salvo ID/posición/procedencia. |
| Copiar y pegar | **No implementada.** Facilita reutilización dentro del job. | Clipboard temporal en Store con slots serializados y contexto del job; `PasteSlotsCommand`. Inicialmente solo mismo job y assets/works existentes. UI/atajos Ctrl/Cmd+C/V. | Copiar no ensucia; pegar sí, como un comando. No copiar assets físicos. Salida igual que duplicar. | Node para clipboard inmutable, IDs, paste repetido y job mismatch; Playwright atajos. Riesgo: referencias inexistentes o pegar entre jobs. Aceptación: nunca crea referencias rotas ni usa clipboard del sistema como contrato principal. |
| Seleccionar todo | **No implementada.** Reduce operaciones repetitivas. | Atajo Ctrl/Cmd+A y acción UI. Store usa `setSelection`; alcance por defecto = slots visibles de `activeFace`. | Temporal, sin historial/autosave/salida. | Node para filtro de cara; Playwright selección visible. Riesgo: seleccionar slots ocultos/otra cara. Aceptación: alcance se muestra y es determinista. |
| Seleccionar por work | **No implementada.** Útil tras Repeat. | Acción desde work/tree; filtro Store por `work_id` y cara, con replace/add. | Temporal. | Node por cara/modo; Playwright desde panel. Riesgo: work con slots en ambas caras. Aceptación: el usuario elige cara activa o todas. |
| Seleccionar por asset | **No implementada.** Permite sustituir/revisar una fuente. | Filtro por `slot.source.asset_id`, no por asset del work. Integración assets/tree. | Temporal. | Node con work compartido y fuentes sustituidas; Playwright. Riesgo: confundir fuente del slot con work. Aceptación: usa la referencia efectiva del slot. |
| Seleccionar por cara | **No implementada en UI.** Necesaria para dúplex. | Requiere navegación de cara o acción “todas las caras”. Store debe ofrecer setter de `activeFace` en fase de caras. | Temporal. | Node para filtros; Playwright front/back. Riesgo: editar objetos invisibles. Aceptación: selección y canvas indican claramente la cara. |
| Bloquear/desbloquear | **Latente y no aplicado.** El contrato ya separa cuatro superficies. Evita cambios accidentales. | Primero `canMutateSlot(slot, capability)` común. Después `SetSlotUserLocksCommand`. UI muestra iconos y motivo. Solo alternar fuente `user`; no retirar `engine/ctp/system` implícitamente. | Persistente, reversible y autosave. Locks no cambian salida visual, pero gobiernan acciones productivas. | Node para precedencia de fuentes, drag/delete/replace/Repeat replace; Playwright bloqueo visible. Riesgo alto: semántica de “desbloquear engine”. Aceptación: ninguna ruta de comando evade locks. |
| Ocultar/mostrar | **No implementada y sin campo contractual.** Despeja el canvas. | Primera versión recomendada: visibilidad temporal `hiddenSlotIds` en Store, árbol y Renderer. Una exclusión productiva sería otra función y exigiría contrato. | Visibilidad temporal: sin undo/autosave/salida; puede tener historial de UI separado, no el de documento. | Node de filtro y selección; Playwright ocultar/mostrar. Riesgo: que “oculto” parezca “no exportar”. Aceptación: etiqueta “solo vista” y exportación no cambia. |
| Eliminar | **Implementada y probada**, pero ignora `locks.delete`. | Mantener `DeleteSlotsCommand`, añadir política central y feedback de IDs omitidos/bloqueados; decidir si operación mixta bloquea todo o elimina solo permitidos. Recomendado: atómica y bloquea todo. | Ya reversible/dirty/autosave. Elimina de futura salida. | Añadir Node/Playwright para delete lock y multi. Riesgo: borrar slots engine protegidos. Aceptación: ningún slot con delete lock desaparece. |
| Centrar en pliego | **No implementada.** Posiciona con precisión. | `MoveSlotsCommand`; para uno usa centro del sheet/área imprimible elegida. Para grupo traslada bounds completos conservando distancias. UI debe distinguir pliego vs área imprimible. Kernel bounds. | Un comando, autosave; output compatible. | Node para rotación/bleed/grupo; Playwright. Riesgo: centrar por trim o bleed sin indicarlo. Aceptación: referencia seleccionada y resultado exacto. |
| Nudge de teclado | **No implementada.** Ajuste fino. | Registro de atajos; flechas con paso configurable, Shift para paso mayor. Agrupar autorepeat de teclado en un solo `MoveSlotsCommand` por sesión. Respeta locks. | Una ráfaga = un comando; autosave al keyup/debounce de gesto. | Node para pasos, multi y agrupación; Playwright. Riesgo: cientos de comandos o interferencia con inputs. Aceptación: inputs no disparan nudge y unidades son mm. |
| Atajos | **Parcial:** undo/redo, delete, Escape y espacio-pan. | Crear mapa central en `interactions.js` o módulo `shortcuts.js`; añadir Ctrl/Cmd+S, A, C, V, D y flechas. Mostrar cheatsheet. | Cada atajo delega a la misma acción/comando; no duplica lógica. | Node para resolución de teclas y foco editable; Playwright para atajos críticos. Riesgo: colisión navegador. Aceptación: Windows/macOS y campos de formulario seguros. |

## 5. Selección avanzada

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Box select | **No implementada.** Selección espacial rápida. | Pointer session `box_select`, overlay SVG y consulta geométrica. Debe usar polígonos/bounds de Geometría JS, no DOM rectangles. | Temporal, sin historial/autosave. | Fixtures inclusión/overlap, zoom/pan y rotación; Playwright arrastre. Riesgo: coordenadas SVG/Y. Aceptación: mismo resultado a cualquier zoom/pan. |
| Selección múltiple | **Implementada y probada en Store.** Necesita endurecimiento visible. | Conservar Shift/Ctrl/Cmd; añadir feedback para slots bloqueados/ocultos y selección desde tree/box. | Temporal. | Ampliar Playwright multi y bounds. Riesgo bajo. Aceptación: modos replace/add/toggle consistentes en todas las superficies. |
| Por solapamiento o inclusión | **No implementada.** Permite selección CAD. | Toggle “tocar” vs “contenido”. Requiere polígono de ventana y SAT/point-in-polygon paritario en JS. | Temporal. | Node contra fixtures Python y casos de borde. Riesgo: usar solo AABB para futuros ángulos. Aceptación: política visible y contacto de borde documentado. |
| Ciclar objetos superpuestos | **No implementada.** Hace accesibles slots coincidentes. | Hit-test geométrico ordenado y tecla/click repetido; Store guarda ciclo temporal por punto/cara. | Temporal. | Node para orden estable; Playwright clicks repetidos. Riesgo: depender del orden DOM cambiante. Aceptación: ciclo determinista y se reinicia al mover cursor. |
| Árbol de objetos | **Parcial:** lista plana de slots de cara activa. | Nuevo módulo `objects_panel.js`; jerarquía cara > work > slots, estado lock/visibility/asset y selección unificada. | Expansión/scroll temporal; acciones persistentes delegan comandos. | DOM/Playwright para selección, filtros y grandes listas. Riesgo: rerender costoso y dos fuentes de selección. Aceptación: Store sigue siendo única fuente. |
| Agrupación | **No implementada ni contratada.** Beneficio limitado mientras ya existe multiselección. | Recomendación: comenzar con “grupo temporal de selección” sin persistir. Un grupo productivo persistente requeriría `group_id`/árbol en schema y semántica de duplicado/cara/locks. | Temporal: sin autosave. Persistente: comando/contrato/migración V2. | Tests según opción. Riesgo alto de complejidad prematura. Aceptación inicial: no introducir grupo persistente hasta existir caso operativo concreto. |

## 6. Alineación, distribución y duplicación matricial

Referencia recomendada inicial: **bounds trim**. Las operaciones que usen footprint con bleed deben ofrecer una opción explícita; nunca alternar automáticamente.

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Alinear izquierda/derecha | **No implementada.** Ordena bordes. | `AlignSlotsCommand` puede producir before/after positions; Geometría JS obtiene bounds trim o bleed orientados. UI indica referencia y caja. | Un comando para selección; autosave; output compatible. | Node rotaciones/bleed/locks; Playwright. Riesgo: confundir centro con borde. Aceptación: el borde elegido coincide dentro de tolerancia. |
| Alinear arriba/abajo | **No implementada.** Igual beneficio vertical. | Igual que anterior, respetando dominio Y arriba y sin fórmulas SVG. | Igual. | Casos Y invertida en Node/Playwright. Riesgo: usar top visual como bottom de dominio. Aceptación: cálculo en dominio. |
| Alinear centros H/V | **No implementada.** Centra ejes comunes. | `AlignSlotsCommand`, centro de bounds/slot según modo. | Un comando/autosave. | Node selección par/impar; riesgo bajo. Aceptación: centros exactos, slot de referencia estable. |
| Centrar selección en pliego | **No implementada.** Centra grupo sin perder patrón. | Trasladar unión de bounds al centro de sheet o printable bounds. Reutilizar comando de movimiento. | Un comando/autosave. | Node con grupo rotado/bleed. Riesgo: mover locks mezclados. Aceptación: operación atómica o bloqueada completa. |
| Distribuir horizontal/vertical | **No implementada.** Uniformiza montaje manual. | `DistributeSlotsCommand`; ordenar por centro/bounds; conservar extremos o elegir referencia. Mínimo 3 objetos. | Un comando/autosave. | Node para orden, tamaños diferentes y rotaciones; Playwright. Riesgo: orden inestable si centros iguales. Aceptación: gaps iguales y deterministas. |
| Separación exacta | **No implementada.** Control productivo de calles. | `SetExactGapCommand`; gap entre bounds trim o footprint bleed, dirección y ancla. Kernel gaps firmados. | Un comando/autosave. | Node con gap positivo/cero/overlap; output compatible. Riesgo: confundir gap con bleed. Aceptación: gap medido coincide con valor solicitado. |
| Trim vs footprint con bleed | **Parcial como concepto; no opción UI.** Evita colisiones productivas. | Selector transversal de caja para align/distribute/measure/snap. Store temporal `geometryReference = trim|productive`. | Temporal por sí solo; operaciones resultantes sí generan comando. | Paridad fixtures. Riesgo crítico de defaults ambiguos. Aceptación: badge visible y default documentado. |
| Duplicación matricial | **No implementada.** Crea filas/columnas manuales sin Repeat. | `DuplicateMatrixCommand`; filas, columnas, pitch/gap y caja de referencia. `generated_by=duplicate`. Validar IDs/bounds/overlap; no reemplaza Repeat. | Una matriz = un comando, undo total, autosave. | Node cantidades/rotaciones/bleed; Playwright. Riesgo: sobreproducción y solapamiento. Aceptación: resumen previo y número exacto de copias. |

## 7. Guías y precisión

Estas herramientas requieren ampliar primero la paridad JS con polígonos, distancias y tolerancias del kernel Python.

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Reglas | **No implementada.** Da referencia espacial continua. | Capa SVG/HTML sincronizada con viewBox; ticks derivados de mm y zoom. Store viewport existente. | Temporal. | DOM/Playwright a varios zooms. Riesgo: reglas desincronizadas del pan. Aceptación: tick y cursor coinciden en mm. |
| Guías arrastrables | **No implementada, sin contrato.** Repite referencias. | `guides` temporal en Store en primera versión; drag desde reglas, overlay SVG y borrar. Persistencia futura requeriría sección UI/documento decidida. | Temporal inicialmente; sin autosave. | Node conversión y Playwright. Riesgo: aparentar persistencia. Aceptación: etiqueta/estado claro y coordenada exacta. |
| Snap general | **No implementada.** Reduce errores. | Motor puro `snap_engine.js` sobre candidatos en mm; pointer preview usa resultado, comando solo posición final. Store guarda settings temporales. | Un drag = un comando; autosave al final. | Node determinista con tolerancias; Playwright. Riesgo: jitter y usar tolerancia productiva como epsilon. Aceptación: umbral en mm/píxel documentado y Escape restaura. |
| Snap a pliego | **No implementada.** Alinea footprint/borde. | Candidatos sheet bounds, caja trim/productive explícita. | Igual snap. | Node cuatro bordes/rotaciones. Aceptación: borde exacto. |
| Snap a márgenes | **No implementada.** Respeta área imprimible. | Candidatos de `printable_margins_mm`; mostrar su rectángulo en canvas. | Igual. | Python/Node parity de printable bounds. Riesgo: margen inválido mayor al sheet; backend ya valida no negativo, no suma. Aceptación: área válida/preflight. |
| Snap a centros | **No implementada.** Centra en sheet/selección. | Candidatos ejes central X/Y. | Igual. | Node y Playwright. Aceptación: smart line visible. |
| Snap entre slots | **No implementada.** Iguala bordes/centros/gaps. | Índice de bounds de slots visibles; excluir selección; respetar cara y ocultos. | Igual. | Node con múltiples candidatos/locks. Riesgo de rendimiento. Aceptación: candidato estable y prioridad explícita. |
| Smart guides | **No implementada.** Explica el snap y relaciones. | Resultado del motor incluye líneas, etiquetas y distancias; Renderer dibuja overlay temporal. | Sin persistencia; no historial. | Node para prioridad; Playwright visual/DOM. Riesgo: lógica duplicada respecto a snap. Aceptación: guía deriva del mismo resultado usado para mover. |
| Medición | **Latente en Python:** existen gaps/distancias; no JS/UI. | Tool temporal con dos puntos/slots; JS paritario para bounds, gap y distancia. | No persistente. | Fixtures Python/Node; Playwright. Riesgo: medir trim cuando usuario espera bleed. Aceptación: caja/unidad visibles. |
| Distancias | **Latente.** Útil para calles y diagnóstico. | Etiquetas entre selección y vecinos; usar gaps firmados. | Temporal. | Node contacto/overlap/decimales. Aceptación: positivo, cero y solapamiento distinguibles. |
| Indicadores de overlap | **Parcial:** Repeat bloquea en servidor; canvas no muestra. | SAT/polígonos JS paritarios y overlay por cara; footprint bleed por default. Puede ser warning, no corrección automática. | Derivado, sin autosave. | Fixtures SAT/bleed y Playwright. Riesgo: falsos positivos AABB. Aceptación: coincide con kernel Python, contacto de borde no es overlap. |

## 8. Transformación de slot y artwork

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Resize del slot | **No implementada.** Cambia trim productivo. | `ResizeSlotsCommand`, pointer session con handles, geometría JS completa y política de ancla. Edita solo `trim_size_mm`. Inspector width/height. | Un gesto = un comando/autosave. Puede provocar `SOURCE_TRIM_SIZE_MISMATCH`; preview/export deben quedar bloqueados hasta resolver contenido. | Python contrato/preflight, Node handles/rotación/undo, Playwright. Riesgo alto de mezclar artwork. Aceptación: trim previo a rotación, centro/ancla documentados y exportabilidad visible. |
| Rotación interactiva | **No implementada; solo cardinal permitida.** | Handle puede previsualizar, pero debe cuantizar exclusivamente a 0/90/180/270 y rechazar libre. Reutilizar comando cardinal. | Un gesto = un comando/autosave; output cardinal compatible. | Node cuadrantes y Escape; Playwright. Riesgo: normalización silenciosa. Aceptación: nunca persiste 89/360/-90. |
| Resize múltiple | **No implementada.** | Diferir hasta resize individual estable. Definir si escala posiciones, trims o ambos; probablemente nuevo `TransformSelectionCommand`. | Atómico/autosave; impacto de salida por cada slot. | Amplia matriz de tests. Riesgo alto. Aceptación requiere semántica aprobada antes de código. |
| Mantener proporción | **No implementada.** | Modificador/lock de ratio durante resize de slot. Ratio productivo del trim, no de thumbnail. | Parte del mismo comando. | Node para Shift y rotación. Riesgo: confundir ratio de PDF. Aceptación: ratio inicial conservado dentro de tolerancia. |
| Transformación del contenido | **Bloqueada por salida.** Contrato existe, renderer no la aplica. | Módulo/overlay de content edit independiente; comandos `SetContentTransformCommand`; renderer debe aplicar matriz interna y clipping exacto. OutputAdapter/PreparedAssetService debe representar o bloquear. | Persistente, reversible, autosave. No habilitar producción hasta paridad canvas/preview/PDF. | Python capability/output, Node matrices, Playwright y comparación render/PDF. Riesgo muy alto de WYSIWYG falso. Aceptación: misma transformación en canvas, preview y final. |
| Fit | **Declarado (`contain`), no implementado.** | Calcular escala interna desde caja fuente/trim, sin tocar slot. | Comando de contenido; output hoy bloquea. | Tests caja/rotación intrínseca. Aceptación tras adapter compatible. |
| Cover | **Declarado, no implementado.** | Escala y crop internos deterministas. | Igual; bloqueado para salida actual. | Tests de crop y caja desplazada. Riesgo pérdida de contenido. |
| Tamaño real | **Parcial:** slots se crean con `actual_size`, renderer usa `meet`. | Renderer debe usar dimensiones/caja fuente reales y offsets; preflight confirma coincidencia. | Comando reset de contenido; salida actual lo admite bajo restricciones. | Node/Python/Playwright. Aceptación: 1 mm fuente = 1 mm slot y mismatch visible/bloqueante. |
| Offset interno | **Declarado, no implementado.** | Pointer session específica dentro del clip y comando de contenido; no mover centro trim. | Reversible/autosave; output hoy bloquea. | Node separación de coordenadas; Playwright. Riesgo: mover slot por error. Aceptación: geometry permanece byte a byte igual. |
| Clipping | **Parcial y divergente:** SVG siempre trim; contrato permite none/trim/bleed. | Renderer y output deben usar la misma política/caja exacta; UI contextual. | Comando de contenido/autosave. Output solo admite casos restringidos. | Tests por caja ausente/bleed. Riesgo de mostrar arte que no sale. Aceptación: paridad render/productivo. |
| Espejo | **Declarado, no implementado.** | Matriz interna alrededor del centro del contenido; comando reversible. | Autosave; OutputAdapter hoy bloquea. | Node matrices y PDF visual. Riesgo alto en textos/dorso. Aceptación solo con salida compatible. |

## 9. Cambios transversales recomendados

### 9.1 Política de capacidades y locks

Crear un módulo puro, por ejemplo `static/js/editor_offset_v2/edit_policy.js`, con capacidades:

```text
move | resize | rotate | content | production | delete | replace
```

Los comandos deben validar la política al construir y ejecutar. La UI la consulta para deshabilitar y explicar; nunca es la única defensa.

Decisión recomendada:

- cualquier fuente en `locks.geometry` bloquea move/rotate/resize;
- cualquier fuente en `locks.content` bloquea replace y content transform;
- cualquier fuente en `locks.delete` bloquea delete y replace de Repeat que lo eliminaría;
- “Desbloquear” solo agrega/quita `user`;
- locks `engine`, `ctp` o `system` requieren una acción futura explícita, no se borran por accidente.

### 9.2 Paridad geométrica

Antes de box select por polígono, snap, overlap o resize, ampliar `geometry_view.js` o extraer `geometry_kernel.js` para cubrir las mismas fixtures que Python:

- puntos/polígonos;
- bounds;
- SAT;
- contención;
- gaps/distancias;
- tolerancia.

No es necesario introducir TypeScript en la primera fase, pero la API debe quedar pura y portable para una migración gradual posterior.

### 9.3 Preflight de editabilidad y exportabilidad

El shell debe diferenciar:

- **editable**: el comando puede ejecutarse según locks;
- **válido**: el layout cumple schema/validador;
- **dentro de área**: geometría productiva aceptable;
- **exportable**: OutputAdapter puede representar todo.

Una marca roja de bounds no reemplaza un preflight. Una transformación visual no equivale a exportabilidad.

## 10. Roadmap por fases pequeñas

### Fase 8A — Posicionamiento manual preciso sobre la base 8P

- **Rama:** `feat/editor-offset-v2-manual-positioning`
- **Alcance:** reutilizar la política `move` existente; inspector editable solo para centro X/Y; nudge; Ctrl/Cmd+S; agrupación de key repeat; feedback consistente de slot bloqueado.
- **Archivos:** `commands.js`, `store.js`, `interactions.js`, `canvas_renderer.js`, `dom_refs.js`, `bootstrap.js`, template/CSS; `edit_policy.js` solo si la API `move` necesita una extensión compatible; tests Node/Playwright y doc de fase.
- **Tests:** valores finitos/decimales, multi delta, locks, no-op, undo/redo, dirty/autosave, input focus, save shortcut y persistencia visible.
- **Riesgo:** bajo-moderado; toca rutas comunes de movimiento.
- **No tocar:** trim/bleed, rotación, contenido, contrato Python, output, Repeat, assets, V1.
- **Finalización:** drag, inspector y nudge pasan por la misma política/comando; una acción = un historial; Playwright persiste una coordenada exacta.

### Fase 8B — Rotación cardinal, duplicado, clipboard y locks de usuario

- **Rama:** `feat/editor-offset-v2-object-operations`
- **Alcance:** rotación 0/90/180/270, duplicar, copiar/pegar dentro del job, select all/work/asset y UI/comandos de lock/unlock `user`; reutilizar enforcement delete/content ya creado en 8P.
- **Archivos:** comandos/store/interactions/panel assets/objects/renderer/UI; posiblemente `objects_panel.js` inicial.
- **Tests:** IDs, generated_by, cuatro rotaciones, locks por superficie, clipboard, criterios, undo/redo/autosave y Playwright.
- **Riesgo:** moderado por política de locks y referencias.
- **No tocar:** resize, grupos persistentes, output capabilities, cara back manual.
- **Finalización:** ninguna operación evade locks; copias son Layout V2 válido y exportables si la fuente lo era.

### Fase 8C — Alineación, centrado, distribución y matriz

- **Rama:** `feat/editor-offset-v2-align-distribute`
- **Alcance:** alinear seis variantes, centrar sheet/printable, distribuir H/V, gap exacto y matriz con preview/resumen.
- **Archivos:** nuevo módulo puro de operaciones geométricas, comandos, geometry JS, inspector/toolbar, tests.
- **Tests:** trim/productive, rotaciones, tamaños distintos, locks, determinismo, undo/redo y Playwright.
- **Riesgo:** moderado por referencia trim/bleed.
- **No tocar:** snap durante drag, resize, artwork.
- **Finalización:** todas las operaciones declaran caja/referencia y producen un único comando.

### Fase 8D — Box select y árbol de objetos

- **Rama:** `feat/editor-offset-v2-advanced-selection`
- **Alcance:** box select inclusión/solapamiento, ciclo de superpuestos, árbol cara/work/slot, visibilidad temporal y selección por cara.
- **Archivos:** `objects_panel.js`, interactions/store/renderer/geometry/UI.
- **Tests:** hit testing, zoom/pan, orden, filtros, ocultos y Playwright.
- **Riesgo:** moderado; requiere geometría JS poligonal para modo overlap.
- **No tocar:** agrupación persistente, export exclusion.
- **Finalización:** selección idéntica desde canvas/árbol y sin mutar layout.

### Fase 8E — Reglas, guías, snap, smart guides y medición

- **Rama:** `feat/editor-offset-v2-guides-snap-measure`
- **Alcance:** completar paridad JS; reglas, guías temporales, snap a sheet/márgenes/centros/slots, smart guides, medidas, gaps e overlap visual.
- **Archivos:** kernel JS/snap engine/renderer/interactions/store/UI; fixtures y tests Python/Node de paridad.
- **Tests:** SAT, contacto, tolerancias, prioridades, zoom/pan y Playwright.
- **Riesgo:** alto por precisión e interacción.
- **No tocar:** corrección automática, persistencia de guías, resize.
- **Finalización:** mismo resultado geométrico Python/JS y un drag continúa siendo un comando.

### Fase 8F — Resize productivo del slot

- **Rama:** `feat/editor-offset-v2-slot-resize`
- **Alcance:** inspector width/height, handles, anclas, proporción y resize individual; multi-resize solo tras decisión expresa.
- **Archivos:** comandos, geometry, interactions, renderer/UI, preflight de exportabilidad y tests.
- **Tests:** cardinales, anchors, Escape, locks, mismatch con fuente, undo/redo, autosave, Playwright.
- **Riesgo:** alto; puede bloquear actual_size/output.
- **No tocar:** escalado interno automático, PDF fuente, rotación libre.
- **Finalización:** slot y artwork permanecen conceptos distintos y el estado no exportable es explícito.

### Fase 8G — Transformaciones internas del artwork

- **Rama:** `feat/editor-offset-v2-content-transform`
- **Alcance:** actual_size exacto, contain, cover, offset, clip y espejo solo junto con capacidad segura de salida; rotación interna cardinal.
- **Archivos:** renderer/comandos/store/interactions/UI, OutputAdapter/output service y probablemente PreparedAssetService en fase propia.
- **Tests:** matrices frontend, capability Python, render de preview/PDF y Playwright.
- **Riesgo:** muy alto por paridad visual/productiva.
- **No tocar:** slot geometry salvo herramienta explícita; PDF fuente inmutable.
- **Finalización:** canvas, preview y PDF representan el mismo resultado o la exportación queda bloqueada con código explícito.

### Fase 8H — Frente/dorso y mesa de luz

- **Rama:** `feat/editor-offset-v2-duplex-workbench`
- **Alcance:** navegación de cara, crear slot manual back, selección por cara, fuente posterior distinta, overlay mesa de luz con reglas de flip explícitas.
- **Archivos:** store/assets panel/commands/renderer/UI; posiblemente servicio de preflight dúplex.
- **Tests:** front/back independientes, cambio de cara, locks, persistencia y Playwright.
- **Riesgo:** alto por orientación productiva de dorso.
- **No tocar:** duplicación automática del dorso sin contrato, CTP o PDF hasta caracterización.
- **Finalización:** el operador sabe qué cara edita y la mesa de luz no modifica geometría persistida.

## 11. Orden recomendado

```text
8P Estabilización semántica (completada)
  -> 8A Posición precisa sobre política de locks existente
  -> 8B Operaciones de objeto y rotación cardinal
  -> 8C Alinear/distribuir/matriz
  -> 8D Selección avanzada y árbol
  -> 8E Paridad completa, snap y medición
  -> 8F Resize productivo
  -> 8G Transformación de artwork + salida segura
  -> 8H Frente/dorso y mesa de luz
```

8D y 8C pueden intercambiarse si el volumen de slots hace urgente el árbol. 8F no debe adelantarse a la política de locks ni a la señal de exportabilidad. 8G no debe implementarse como una mejora únicamente visual.

## 12. Primera fase recomendada

La primera fase segura es **Fase 8A — Posicionamiento manual preciso**. Aprovecha contrato, comando y política de locks ya existentes; no cambia schema ni backend y no reabre las decisiones cerradas en 8P.

Alcance exacto:

- reutilizar la capacidad pura `move` de `edit_policy.js`;
- mantener el drag actual y su enforcement de `locks.geometry`;
- editar X/Y desde inspector para una selección única;
- mover selección múltiple mediante delta explícito;
- nudge con flechas y paso definido en mm;
- agrupar una ráfaga de nudge en un comando;
- añadir Ctrl/Cmd+S;
- mantener undo/redo, dirty, autosave y 409 existentes;
- no modificar rotación, tamaño, bleed ni contenido.

## 13. Prompt completo para implementar Fase 8A

```text
Quiero continuar con el Editor Offset Visual V2.

Las fases 1 a 7, la auditoría y la estabilización semántica 8P ya están integradas en mi rama local main.

Implementa únicamente:

# Fase 8A — Posicionamiento manual preciso sobre política de locks existente

## Preparación Git

1. Confirma la raíz C:\Users\USER\revista-montaje-ai.
2. Ejecuta git branch --show-current y git status.
3. Debe estar en main y limpio.
4. No ejecutes git pull.
5. Crea y cambia a:

   git switch -c feat/editor-offset-v2-manual-positioning

6. Confirma rama y estado.
7. Si hay cambios locales, no los descartes ni sobrescribas; detén la implementación y repórtalos.

No hagas stage, commit, merge ni push.

## Fuente de verdad

Revisa antes de modificar:

- DOCS/OFFSET/V2/08_AUDITORIA_ESTADO_ACTUAL_V2.md
- DOCS/OFFSET/V2/09_PLAN_HERRAMIENTAS_MANUALES_V2.md
- DOCS/OFFSET/V2/10_ESTABILIZACION_SEMANTICA_V2.md
- DOCS/OFFSET/V2/11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md
- editor_offset_v2/domain/layout_v2.py
- editor_offset_v2/domain/geometry.py
- static/js/editor_offset_v2/store.js
- static/js/editor_offset_v2/commands.js
- static/js/editor_offset_v2/interactions.js
- static/js/editor_offset_v2/geometry_view.js
- static/js/editor_offset_v2/canvas_renderer.js
- static/js/editor_offset_v2/dom_refs.js
- static/js/editor_offset_v2/bootstrap.js
- templates/editor_offset_visual_v2.html
- tests/editor_offset_v2/js/editor_core_v2.test.cjs
- tests/playwright/test_editor_offset_v2.py

## Objetivo

Permitir posicionamiento manual preciso sin ampliar todavía la geometría productiva:

- editar centro trim X/Y;
- mover una selección mediante delta;
- nudge con teclado;
- guardar con Ctrl/Cmd+S;
- reutilizar y preservar el enforcement de locks geométricos ya existente en todas las rutas de movimiento;
- mantener un comando por acción confirmada.

No implementar rotación, resize, snap, alineación, box select, transformación de artwork ni navegación de cara.

## Política de locks existente

Reutiliza `static/js/editor_offset_v2/edit_policy.js` y su capacidad `move`. No crees una segunda política ni cambies la semántica cerrada en 8P.

Reglas vigentes:

- un slot puede moverse solo si locks.geometry está vacío;
- cualquier fuente user, engine, ctp o system bloquea;
- no elimines ni normalices locks;
- el drag y `MoveSlotsCommand` ya la defienden; inspector y nudge deben usar la misma frontera;
- una operación multiselección con al menos un slot bloqueado debe rechazarse completamente, no mover un subconjunto silenciosamente;
- mostrar feedback visible con IDs y motivo;
- `MoveSlotsCommand` debe continuar defendiendo la regla, no solo los botones.

No agregues todavía UI para quitar locks.

## Inspector editable

Para selección única, mostrar inputs numéricos de:

- Centro X mm.
- Centro Y mm.

Para selección múltiple, mostrar:

- Delta X mm.
- Delta Y mm.

Reglas:

- valores finitos;
- decimales permitidos;
- Enter o botón Aplicar confirma;
- Escape cancela el formulario;
- un no-op no crea comando ni dirty;
- no guardar por cada pulsación;
- no modificar directamente el layout desde el DOM;
- usar MoveSlotsCommand o una extensión compatible y reversible;
- mantener anchor=trim_center;
- no corregir automáticamente posiciones fuera del pliego;
- conservar la señal visual existente de fuera del pliego.

## Nudge

Implementa:

- flechas: 0.1 mm;
- Shift + flechas: 1 mm;
- no actuar cuando el foco está en input, textarea, select o contenteditable;
- no actuar durante drag/pan;
- respetar locks;
- una ráfaga de autorepeat debe producir un solo MoveSlotsCommand al terminar la sesión de teclado;
- Escape cancela una sesión todavía no confirmada;
- mantener preview temporal si resulta necesario, sin mutar layout hasta confirmar.

Define los pasos como constantes claras.

## Atajo de guardado

Ctrl+S y Cmd+S deben:

- prevenir el diálogo del navegador;
- delegar a SaveCoordinator.manualSave();
- no crear una segunda implementación de guardado;
- respetar saving/conflict/pointer session.

La resolución de atajos debe quedar centralizada y probada.

## Store y comandos

- No uses snapshots completos del layout.
- Un movimiento confirmado debe contener posiciones before/after.
- Undo y redo deben restaurar exactamente todos los centros.
- Ejecutar, undo y redo mantienen dirty state existente.
- Autosave solo comienza después de confirmar el comando.
- No guardar durante preview de nudge o drag.
- No cambies la revisión local fuera de SaveCoordinator.

## UI

Actualiza únicamente el shell V2:

- inspector editable contextual;
- mensaje de lock;
- ayuda breve de flechas/Shift;
- estado accesible para errores de validación;
- botones/inputs deshabilitados cuando la selección está bloqueada.

No modifiques V1 ni agregues controles de herramientas futuras.

## Tests Node

Cubre como mínimo:

- política con locks vacíos y user/engine/ctp/system;
- defensa del comando ante slot bloqueado;
- movimiento absoluto único;
- delta multiselección;
- decimales;
- NaN/infinito rechazados;
- no-op sin historial/dirty;
- undo/redo exacto;
- nudge 0.1 y 1 mm;
- agrupación de autorepeat en un comando;
- foco editable no dispara atajo;
- Ctrl/Cmd+S delega una sola vez;
- dirty/autosave después de confirmación, nunca durante preview.

## Playwright aislado

Amplía el test V2 o crea uno focalizado:

1. crear job;
2. subir PDF y crear work/slot real;
3. seleccionar slot;
4. editar X/Y a valores decimales;
5. hacer nudge;
6. undo y redo;
7. guardar con Ctrl+S;
8. recargar;
9. verificar posición persistida;
10. crear o inyectar un slot con geometry lock y comprobar que drag, inspector y nudge no lo mueven.

No dejes Flask persistente; usa el fixture/servidor controlado existente.

## Documentación

Crea DOCS/OFFSET/V2/12_POSICIONAMIENTO_MANUAL_V2.md con:

- política de locks;
- inspector;
- movimiento absoluto y delta;
- nudge;
- atajos;
- comandos;
- undo/redo/autosave;
- tests;
- límites y siguiente fase.

## Archivos permitidos

- static/js/editor_offset_v2/
- templates/editor_offset_visual_v2.html
- static/css/editor_offset_visual_v2.css
- tests/editor_offset_v2/
- tests/playwright/test_editor_offset_v2.py
- DOCS/OFFSET/V2/

No modifiques Python de dominio/backend salvo que detectes un bloqueo real; si ocurre, detente y repórtalo antes.

## Restricciones

No:

- cambies Layout V2 ni el JSON Schema;
- cambies assets, Repeat, output capabilities u OutputAdapter;
- reimplementes área imprimible, source override, historial/métricas Repeat, placeholder dev o advertencia de artwork aproximado;
- conectes preview/PDF/CTP;
- implementes rotación;
- implementes resize;
- implementes snap/alineación/box select;
- implementes content_transform;
- agregues dependencias, TypeScript o Vite;
- modifiques Editor V1;
- hagas commit o push.

## Validación final

Ejecuta:

- venv\Scripts\python.exe -m pytest tests\editor_offset_v2 -q
- todos los tests Node V2;
- node --check sobre todos los módulos JS V2;
- Playwright V2 aislado;
- venv\Scripts\python.exe -m compileall editor_offset_v2
- git diff --check
- git status --short
- git diff --stat

Confirma que fases 1–7 siguen pasando, V1 no fue modificado, no se agregaron dependencias y no quedó Flask persistente.

Informa rama, archivos, política, comandos, inspector, nudge, atajos, tests y estado Git. No hagas stage, commit, merge ni push.
```

## 14. Criterio global de éxito del programa de herramientas

El programa se considerará listo para producción manual cuando:

- todas las mutaciones estén mediadas por comandos y locks;
- JavaScript y Python compartan resultados geométricos verificables;
- selección y viewport no contaminen Layout V2;
- cada herramienta indique si opera sobre trim o footprint productivo;
- slot y artwork se transformen con comandos distintos;
- canvas, preflight, preview y PDF no diverjan;
- Playwright cubra los flujos manuales críticos además de Repeat;
- ninguna función visual prometa una capacidad que OutputAdapter todavía bloquea.
