# Plan técnico de herramientas manuales del Editor Offset Visual V2

## 1. Objetivo y punto de partida real

Este plan parte del código auditado después de las fases 1–7. No propone reconstruir el editor ni introducir un framework. Extiende la arquitectura que ya funciona:

> ACTUALIZACIÓN VIGENTE — 8P, CORRECCIÓN DE MEDIDA/ETIQUETAS Y 8A–8D COMPLETADAS
>
> La estabilización semántica está en `10_ESTABILIZACION_SEMANTICA_V2.md`; la corrección de tolerancia/etiquetas en `12_CORRECCION_COMPATIBILIDAD_DE_MEDIDA_Y_ETIQUETAS_V2.md`; el cierre de posicionamiento/acciones en `13_POSICIONAMIENTO_Y_COMANDOS_V2.md`; las operaciones de objeto en `14_OPERACIONES_DE_OBJETO_Y_CLIPBOARD_V2.md`; alineación/distribución/matriz en `15_ALINEACION_DISTRIBUCION_Y_MATRIZ_V2.md`; y selección avanzada/árbol en `16_SELECCION_AVANZADA_Y_ARBOL_V2.md`. Ya existen marquee, ciclo de superpuestos, selección por propiedades/locks/issues, árbol accesible y visibilidad temporal además de las capacidades previas. Las fases futuras no deben reimplementar estas piezas.

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
- comandos de move, rotate, duplicate, delete y locks de usuario;
- undo/redo, dirty state, autosave y conflicto 409;
- geometría cardinal de vista con fixtures compartidos;
- assets, works, slots reales y Repeat;
- contrato de locks y `generated_by.type = duplicate`;
- clipboard interno same-job y selección por cara/work/asset efectivo;
- marquee trim/footprint, ciclo, árbol cara/work/slot y `hiddenSlotIds` temporal;
- kernel Python con polígonos, bounds, SAT y distancias.

Deudas que condicionan el orden después de 8D:

- el inspector de posición solo edita X/Y; la rotación cardinal vive en el panel
  de objetos y tamaño/contenido siguen fuera de alcance;
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
| Inspector editable | **Implementada en 8A para posición; rotación cardinal disponible en el panel 8B.** Formulario accesible con Centro X/Y absoluto o Delta X/Y multi. | Extensiones futuras deben añadir tamaño sin mezclar geometría de slot y `content_transform`. | Confirmar crea un `MoveSlotsCommand`; Escape descarta borrador; dirty/autosave solo tras confirmar. | Node y Playwright cubren parsing, no-op, multi delta, locks, undo/redo, guardado y recarga. Tamaño sigue pendiente. |
| Movimiento numérico | **Implementado en 8A.** Punto/coma, un eje o ambos, absoluto y delta explícito. | Reutilizar el registro `selection.move.*`, `MoveSlotsCommand` y política `move`; no crear un segundo camino. | Una confirmación atómica; no-op no ensucia. No cambia contrato ni salida. | Cubierto en Node/Playwright. Riesgo futuro: mantener centro trim y precisión al añadir alineación/resize. |
| Rotación cardinal | **Implementada y probada en 8B.** `RotateSlotsCommand`, `+90/-90`, selector 0/90/180/270, `R/Shift+R` y lock de geometría. | Reutilizar la misma acción/comando en futuras superficies; no introducir rotación libre. | Un comando por acción; dirty/autosave. OutputAdapter admite rotación geométrica cardinal. | Node y Playwright cubren cardinales, conservación de centro/trim/bleed/source, no-op, locks, undo/redo y reload. |
| Duplicar | **Implementada y probada en 8B.** Acción, Ctrl/Cmd+D y Alt+drag crean IDs nuevos, offset explícito y `source_slot_id`. | Matriz pertenece a 8C; no reutilizar Repeat como duplicado manual. | Una operación para todas las copias; undo las elimina juntas; redo reutiliza IDs; autosave. | Node y Playwright cubren datos preservados, procedencia, offset, locks, Alt+drag, cancelación y persistencia. |
| Copiar, cortar y pegar | **Implementada y probada en 8B.** Clipboard profundo interno, same-job, referencias validadas y paste acumulativo. | Cruce entre jobs/pestañas requeriría una decisión posterior y transferencia explícita de assets. | Copiar no ensucia; cut/delete y paste son comandos. Clipboard y contador son temporales. | Node y Playwright cubren inmutabilidad, referencias, job mismatch, paste repetido, cut atómico y scopes de inputs. |
| Seleccionar todo | **Implementada en 8B y ajustada en 8D.** Ctrl/Cmd+A selecciona visibles de `activeFace`; excluye `hiddenSlotIds`. | Mantener el scope actual al añadir navegación de cara. | Temporal, sin historial/autosave/salida. | Node y Playwright cubren cara, visibles y alcance determinista. |
| Seleccionar por work | **Implementada en 8B y ampliada en 8D.** Unión de works de la selección o acción explícita desde el árbol, limitada a cara activa y visibles. | Reutilizar las acciones centrales. | Temporal. | Node y Playwright cubren unión, cara, árbol y ocultos. |
| Seleccionar por asset | **Implementada en 8B y ampliada en 8D.** Usa fuente efectiva, incluido override, y excluye ocultos. | Mantener `SourceSemantics` como frontera. | Temporal. | Node cubre override; Playwright cubre acciones visibles. |
| Seleccionar por cara | **No implementada en UI.** Necesaria para dúplex. | Requiere navegación de cara o acción “todas las caras”. Store debe ofrecer setter de `activeFace` en fase de caras. | Temporal. | Node para filtros; Playwright front/back. Riesgo: editar objetos invisibles. Aceptación: selección y canvas indican claramente la cara. |
| Bloquear/desbloquear | **Implementado y probado en 8B.** `SetSlotUserLocksCommand` y UI explícita para geometry/content/delete; estados none/all/mixed. | Futuras superficies deben consumir la misma política. Solo alternar `user`; nunca retirar otras fuentes implícitamente. | Persistente, reversible y autosave. Locks gobiernan acciones productivas. | Node/Playwright cubren creación/retiro, mezcla, otras fuentes, no-op, atomicidad y undo/redo. |
| Ocultar/mostrar | **Implementada y probada en 8D como estado temporal.** `hiddenSlotIds`, ocultar, aislar, restaurar, mostrar todos y toggle por slot/work. | Una exclusión productiva sería otra función y exigiría contrato; no reutilizar este estado. | Sin dirty, historial, autosave ni salida. | Node/Playwright cubren canvas, hit test, selección, clave, layout y recarga. |
| Eliminar | **Implementada y centralizada en 8B.** Botones, Delete y cut delegan en `ActionRegistry`; `DeleteSlotsCommand` vuelve a validar `locks.delete`. | Mantener atomicidad y feedback de IDs bloqueados; no crear rutas paralelas. | Reversible/dirty/autosave. Elimina de futura salida. | Node/Playwright prueban política, teclado, foco editable, cut y undo. |
| Centrar en pliego | **Implementada y probada en 8C.** Centra selección contra pliego o área imprimible con referencia trim/footprint. | Reutilizar acciones y `MoveSlotsCommand`. | Un comando, autosave; output compatible. | Node/Playwright cubren rotación, bleed, grupo, locks y destinos. |
| Nudge de teclado | **Implementado en 8A.** Flechas `0.1 mm`, Shift `1 mm`, Ctrl/Cmd+Shift `10 mm`, multi y locks. | El paso configurable queda para 8I. Mantener batching y coordenada Y canónica. | Una ráfaga = un comando; autosave tras finalizar por keyup/timeout/cambio/blur. | Node y Playwright cubren pasos, grupo, un undo e inputs protegidos. |
| Atajos | **Sistema central ampliado en 8B.** R/Shift+R, A/C/X/V/D, Delete y acciones de objeto comparten registro, scopes y ayuda. | 8I añadirá paleta. No devolver listeners globales a módulos de interacción. | Botones y teclado delegan a la misma acción; solo comandos persistentes ensucian. | Node/Playwright cubren operaciones, `?`, Escape, Alt+drag y foco editable. |

## 5. Selección avanzada

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Box select | **Implementada y probada en 8D.** Inclusión/intersección sobre bounds trim o footprint, overlay SVG, umbral y cancelación. | Reutilizar su sesión y filtros; no crear un selector paralelo. | Temporal, sin historial/autosave. | Node y Playwright cubren zoom/pan, rotaciones, bleed, modificadores y cancelación. |
| Selección múltiple | **Implementada y endurecida en 8D.** Canvas, árbol y filtros comparten `EditorStore.selection`. | Conservar modos replace/add/toggle/subtract y exclusión de ocultos. | Temporal. | Node/Playwright cubren sincronización, rangos y modificadores. |
| Por intersección o inclusión | **Implementada y probada en 8D.** Usa AABB cardinales de la referencia 8C; “tocar/intersectar” incluye contacto dentro de tolerancia. | SAT/polígonos para ángulos futuros pertenece a la paridad 8E, no debe cambiar la semántica cardinal cerrada. | Temporal. | Casos trim/footprint, 0/90/180/270 y bleed. |
| Ciclar objetos superpuestos | **Implementada y probada en 8D.** Alt+click respeta orden inverso de render, punto/cara/layout/visibilidad y no interfiere con Alt+drag. | Reutilizar acción y estado temporal del Store. | Temporal. | Node y Playwright cubren dos/tres objetos, reinicios y feedback. |
| Árbol de objetos | **Implementado y probado en 8D.** Jerarquía cara/work/slot, ARIA, teclado, rango, locks/issues/clave y visibilidad temporal. | Mantener orden de layout, listeners delegados y selección única; no agregar reorder. | Expansión, ancla y visibilidad temporales. | Node/Playwright cubren árbol, rango, teclado, sincronización y recarga. |
| Agrupación | **No implementada ni contratada.** Beneficio limitado mientras ya existe multiselección. | Recomendación: comenzar con “grupo temporal de selección” sin persistir. Un grupo productivo persistente requeriría `group_id`/árbol en schema y semántica de duplicado/cara/locks. | Temporal: sin autosave. Persistente: comando/contrato/migración V2. | Tests según opción. Riesgo alto de complejidad prematura. Aceptación inicial: no introducir grupo persistente hasta existir caso operativo concreto. |

## 6. Alineación, distribución y duplicación matricial

Referencia recomendada inicial: **bounds trim**. Las operaciones que usen footprint con bleed deben ofrecer una opción explícita; nunca alternar automáticamente.

| Herramienta | Estado actual y beneficio | Implementación requerida | Historial, autosave y salida | Tests, riesgos y aceptación |
| --- | --- | --- | --- | --- |
| Alinear izquierda/derecha | **Implementada y probada en 8C.** Alinea bounds trim o footprint contra selección o clave. | Reutilizar planes 8C y `MoveSlotsCommand`. | Un comando para selección; autosave. | Node/Playwright cubren rotaciones, bleed y locks. |
| Alinear arriba/abajo | **Implementada y probada en 8C.** Respeta dominio Y arriba. | Reutilizar la misma frontera. | Igual. | Node/Playwright cubren inversión visual y exactitud de dominio. |
| Alinear centros H/V | **Implementada y probada en 8C.** Centros deterministas de bounds. | Reutilizar la misma frontera. | Un comando/autosave. | Node cubre selección y clave estable. |
| Centrar selección en pliego | **Implementada y probada en 8C.** Pliego o área imprimible sin perder el patrón. | Mantener operación atómica y locks. | Un comando/autosave. | Node/Playwright con grupo, bleed y destinos. |
| Distribuir horizontal/vertical | **Implementada y probada en 8C.** Conserva endpoints y produce gaps deterministas. | Reutilizar planes 8C. | Un comando/autosave. | Node/Playwright con tamaños diferentes, rotaciones y orden estable. |
| Separación exacta | **Implementada y probada en 8C.** Gap firmado H/V con ancla inicio/final/clave. | Reutilizar la referencia y acciones actuales. | Un comando/autosave. | Node/Playwright cubren positivo, cero, overlap y locks. |
| Trim vs footprint con bleed | **Implementada en 8C y reutilizada por 8D.** `geometryReference = trim|productive` es temporal y visible. | Debe seguir siendo preferencia transversal para 8E. | La preferencia no ensucia; operaciones confirmadas sí. | Fixtures y Node/Playwright cubren ambas referencias. |
| Duplicación matricial | **Implementada y probada en 8C.** Filas/columnas, gap/pitch, celda multiselección, IDs estables y límite 500. | No sustituye Repeat. | Una matriz = un comando, undo total, autosave. | Node/Playwright cubren cantidades, IDs, locks y persistencia. |

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
| Transformación del contenido | **Pendiente y bloqueada para salida.** Contrato existe, renderer no la aplica. | 8G incorpora módulo/overlay independiente, comandos `SetContentTransformCommand`, matriz y clipping exactos en canvas. | Persistente, reversible, autosave. OutputAdapter debe seguir bloqueando combinaciones no representables; el motor PDF espera a Fase 9. | Node matrices/cajas y Playwright de canvas en 8G; comparación preview/PDF en Fase 9. Riesgo muy alto de WYSIWYG falso. |
| Fit | **Declarado (`contain`), no implementado.** | Calcular escala interna desde caja fuente/trim, sin tocar slot. | Comando de contenido; output hoy bloquea. | Tests caja/rotación intrínseca. Aceptación tras adapter compatible. |
| Cover | **Declarado, no implementado.** | Escala y crop internos deterministas. | Igual; bloqueado para salida actual. | Tests de crop y caja desplazada. Riesgo pérdida de contenido. |
| Tamaño real | **Parcial:** slots se crean con `actual_size`, renderer usa `meet`. | Renderer debe usar dimensiones/caja fuente reales y offsets; preflight confirma coincidencia. | Comando reset de contenido; salida actual lo admite bajo restricciones. | Node/Python/Playwright. Aceptación: 1 mm fuente = 1 mm slot y mismatch visible/bloqueante. |
| Offset interno | **Declarado, no implementado.** | Pointer session específica dentro del clip y comando de contenido; no mover centro trim. | Reversible/autosave; output hoy bloquea. | Node separación de coordenadas; Playwright. Riesgo: mover slot por error. Aceptación: geometry permanece byte a byte igual. |
| Clipping | **Parcial y divergente:** SVG siempre trim; contrato permite none/trim/bleed. | Renderer y output deben usar la misma política/caja exacta; UI contextual. | Comando de contenido/autosave. Output solo admite casos restringidos. | Tests por caja ausente/bleed. Riesgo de mostrar arte que no sale. Aceptación: paridad render/productivo. |
| Espejo | **Declarado, no implementado.** | Matriz interna alrededor del centro del contenido; comando reversible. | Autosave; OutputAdapter hoy bloquea. | Node matrices y PDF visual. Riesgo alto en textos/dorso. Aceptación solo con salida compatible. |

## 9. Cambios transversales recomendados

### 9.1 Política de capacidades y locks

`static/js/editor_offset_v2/edit_policy.js` ya existe y gobierna las capacidades:

```text
move | resize | rotate | content | production | delete | replace
```

Los comandos actuales validan la política antes de mutar y la UI la consulta para deshabilitar y explicar; nunca es la única defensa. Toda capacidad futura debe extender este módulo, no crear una política paralela.

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

- **Estado:** completada y validada.
- **Rama de implementación:** `feat/editor-offset-v2-positioning-and-command-system`.
- **Alcance completado:** registro central de acciones, shortcut manager, scopes seguros, ayuda `?`, inspector centro X/Y, delta multi, parseo punto/coma, nudge `0.1/1/10 mm`, batching, Ctrl/Cmd+S y undo/redo por teclado.
- **Arquitectura:** un solo Store/historial; botones y teclado comparten acciones; las mutaciones de posición siguen usando `MoveSlotsCommand` y `edit_policy.js`.
- **Tests:** Node y Playwright cubren valores, locks, no-op, historial, autosave, foco editable, persistencia, ayuda y continuidad de capacidades previas.
- **Riesgo residual:** bajo; las ampliaciones deben preservar scopes, batching y precisión numérica.
- **No tocar:** trim/bleed, rotación, contenido, contrato Python, output, Repeat, assets, V1.
- **Evidencia:** `13_POSICIONAMIENTO_Y_COMANDOS_V2.md`.

### Fase 8B — Rotación cardinal, duplicado, clipboard y locks de usuario

- **Estado:** completada y validada.
- **Rama de implementación:** `feat/editor-offset-v2-object-operations`.
- **Alcance completado:** rotación 0/90/180/270, duplicar, clipboard
  copy/cut/paste same-job, offset acumulado, select all/work/asset efectivo,
  lock/unlock `user`, Delete central y Alt+drag.
- **Arquitectura:** acciones únicas para botones/teclado, comandos reversibles,
  clipboard/previews temporales y política atómica con defensa en comandos.
- **Tests:** Node y Playwright cubren IDs, procedencia, cuatro rotaciones, locks
  por superficie, referencias, criterios, undo/redo/autosave, inputs,
  cancelación y persistencia.
- **Riesgo residual:** bajo-moderado; clipboard no cruza jobs y las copias
  preservan locks deliberadamente.
- **No tocar:** resize, grupos persistentes, output capabilities, cara back manual.
- **Evidencia:** `14_OPERACIONES_DE_OBJETO_Y_CLIPBOARD_V2.md`.

### Fase 8C — Alineación, centrado, distribución y matriz

- **Estado:** completada y validada.
- **Rama:** `feat/editor-offset-v2-alignment-distribution-matrix`.
- **Alcance completado:** seis alineaciones, centrado, selección/clave/pliego/área imprimible, distribución H/V, gap exacto, matriz, resumen y badge de clave.
- **Arquitectura:** planes puros, acciones centrales, `MoveSlotsCommand` y `DuplicateSlotsCommand`; referencia, destino, clave y borradores temporales.
- **Tests:** trim/productive, rotaciones, tamaños distintos, locks, determinismo, no-op, undo/redo, IDs, persistencia y Playwright real.
- **Riesgo residual:** bajo-moderado; no hay auto-fit ni prevención automática de salida de pliego.
- **No tocar:** snap durante drag, resize, artwork.
- **Finalización:** todas las operaciones declaran caja/referencia y producen un único comando.
- **Evidencia:** `15_ALINEACION_DISTRIBUCION_Y_MATRIZ_V2.md`.

### Fase 8D — Box select y árbol de objetos

- **Estado:** completada y validada.
- **Rama:** `feat/editor-offset-v2-advanced-selection-object-tree`.
- **Alcance completado:** marquee inclusión/intersección, modificadores, ciclo de superpuestos, filtros por propiedades/locks/issues, árbol cara/work/slot, rango, teclado y visibilidad temporal.
- **Arquitectura:** selección única del Store, referencia trim/footprint de 8C, acciones centrales, hit testing por orden de render y `hiddenSlotIds` fuera del layout.
- **Tests:** 10 casos Node adicionales y un octavo flujo Playwright; incluye 500 slots, zoom/pan, orden, filtros, ocultos, recarga y continuidad 8B/8C.
- **Riesgo residual:** bajo-moderado; overlaps usa bounds cardinales y búsqueda cuadrática sobre visibles.
- **No tocar:** agrupación persistente, export exclusion.
- **Finalización:** selección idéntica desde canvas/árbol, ocultos excluidos de interacción y cero mutación documental por estado temporal.
- **Evidencia:** `16_SELECCION_AVANZADA_Y_ARBOL_V2.md`.

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
- **Alcance:** actual_size exacto, contain, cover, offset, clip, espejo y rotación interna cardinal, con canvas que aplique fielmente `content_transform`.
- **Archivos:** renderer/comandos/store/interactions/UI y geometría de canvas; capacidades de output solo como diagnóstico de compatibilidad, sin motor PDF.
- **Tests:** matrices frontend, cajas PDF, clipping, canvas y Playwright; los tests productivos de PDF pertenecen a Fase 9.
- **Riesgo:** alto por caja, clip y paridad entre modelo y canvas.
- **No tocar:** slot geometry salvo herramienta explícita; PDF fuente inmutable.
- **Finalización:** canvas representa exactamente el modelo interno y toda combinación aún no exportable queda señalada/bloqueada. Preview/PDF nativos quedan para Fase 9.

### Fase 8H — Frente/dorso y mesa de luz

- **Rama:** `feat/editor-offset-v2-duplex-workbench`
- **Alcance:** navegación de cara, crear slot manual back, selección por cara, fuente posterior distinta, overlay mesa de luz con reglas de flip explícitas.
- **Archivos:** store/assets panel/commands/renderer/UI; posiblemente servicio de preflight dúplex.
- **Tests:** front/back independientes, cambio de cara, locks, persistencia y Playwright.
- **Riesgo:** alto por orientación productiva de dorso.
- **No tocar:** duplicación automática del dorso sin contrato, CTP o PDF hasta caracterización.
- **Finalización:** el operador sabe qué cara edita y la mesa de luz no modifica geometría persistida.

### Fase 8I — Productividad inteligente

- **Rama:** `feat/editor-offset-v2-smart-productivity`.
- **Alcance:** paleta Ctrl/Cmd+Shift+P, búsqueda/favoritos, repetir última acción o transformación, presets, nudge configurable, gaps habituales, historial visible, macros deterministas y órdenes textuales confirmables.
- **Arquitectura:** consumir el registro central de acciones de 8A; ninguna orden textual muta el layout de forma ambigua o sin confirmación.
- **Tests:** búsqueda/filtrado, enabled contextual, repetición, macros deterministas, confirmación y accesibilidad.
- **Riesgo:** moderado-alto por composición de acciones y expectativas de repetición.
- **No tocar:** IA con escritura autónoma, acciones no registradas ni bypass del historial.
- **Finalización:** toda productividad avanzada se resuelve a acciones conocidas y comandos auditables.

### Fase 8J — Modos operativos y recetas

- **Rama:** `feat/editor-offset-v2-operating-modes-recipes`.
- **Alcance:** modos de trabajo explícitos, recetas deterministas de operaciones
  registradas, parámetros visibles, preview de intención, confirmación y
  trazabilidad de la secuencia aplicada.
- **Arquitectura:** una receta compone acciones/comandos conocidos; no escribe el
  layout por fuera del registro ni incorpora IA autónoma.
- **Tests:** resolución de receta, parámetros, disponibilidad contextual,
  confirmación, rollback atómico y accesibilidad.
- **Riesgo:** moderado-alto por composición y expectativas operativas.
- **No tocar:** preflight PDF, planificación de producción, renderer final.
- **Finalización:** cada receta se puede explicar, previsualizar, confirmar,
  deshacer y auditar.

### Fase 8K — Preflight y utilidades PDF

- **Rama:** `feat/editor-offset-v2-pdf-preflight`.
- **Alcance:** RGB/CMYK, negros compuestos, tintas, fuentes, resolución, transparencias, sobreimpresión, cajas, páginas, rotaciones intrínsecas, normalización, reportes canónicos y assets derivados.
- **Arquitectura:** el asset original permanece byte a byte; toda corrección genera un asset inmutable con linaje y reemplazo reversible.
- **Tests:** fixtures PDF, reportes deterministas, seguridad de rutas, linaje, rollback y sustitución.
- **Riesgo:** alto por interpretación PDF y trazabilidad de producción.
- **No tocar:** render final del pliego; corresponde a Fase 9.
- **Finalización:** preflight reproducible y correcciones nunca destructivas.

### Fase 8L — Planificación productiva

- **Rama:** `feat/editor-offset-v2-production-planning`.
- **Alcance:** alternativas de montaje, cantidades, desperdicio, caras, pasadas,
  pliegos, placas y resumen productivo trazable antes de salida.
- **Arquitectura:** cálculos derivados y propuestas explícitas; cualquier cambio
  de layout pasa por comandos. No sustituye el presupuesto económico.
- **Tests:** determinismo, cantidades, parciales, frente/dorso, locks, unidades y
  escenarios de imprenta.
- **Riesgo:** alto por semántica industrial y datos incompletos.
- **No tocar:** generación PDF ni costos/precios.
- **Finalización:** el operador puede elegir un plan productivo validado y
  reproducible antes de exportar.

### Fase 9 — Motor de salida PDF nativo V2

- **Rama:** `feat/editor-offset-v2-native-pdf-output`.
- **Prerequisito:** consolidar herramientas, transformaciones, dúplex y preflight.
- **Alcance:** preview fiel, PDF final, front/back, cajas, bleed, rotaciones, `content_transform`, clipping, marcas, barras, CTP, rutas seguras, errores estructurados y determinismo.
- **Destino:** `Layout V2 -> validación V2 -> motor nativo V2 -> preview/PDF coherentes`.
- **Riesgo:** crítico; requiere caracterización visual/productiva y no debe depender permanentemente de `montaje_offset_inteligente.py`.
- **Finalización:** canvas, preview y PDF comparten semántica verificada y trazable.

### Fase 10 — Presupuesto

- **Prerequisito:** planificación productiva y salida V2 estables.
- **Alcance:** consumo planificado, materiales, placas, pasadas, merma, tiempos,
  costos y precios mediante una integración explícita con presupuesto.
- **Riesgo:** crítico por impacto comercial y necesidad de contratos económicos
  separados del layout gráfico.
- **No tocar antes:** no incrustar costos, precios ni reglas comerciales dentro
  de Layout V2.
- **Finalización:** presupuesto reproducible, versionado y trazable desde un plan
  productivo aprobado, sin acoplar el editor al motor económico.

## 11. Orden recomendado

```text
8P Estabilización semántica (completada)
  -> Corrección de medida/etiquetas (completada)
  -> 8A Posición precisa + acciones/atajos centrales (completada)
  -> 8B Operaciones de objeto y rotación cardinal (completada)
  -> 8C Alinear/distribuir/matriz (completada)
  -> 8D Selección avanzada y árbol (completada)
  -> 8E Paridad completa, snap y medición
  -> 8F Resize productivo
  -> 8G Transformación de artwork + canvas exacto
  -> 8H Frente/dorso y mesa de luz
  -> 8I Productividad inteligente
  -> 8J Modos operativos y recetas
  -> 8K Preflight y utilidades PDF
  -> 8L Planificación productiva
  -> 9 Motor de salida PDF nativo V2
  -> 10 Presupuesto
```

8D está completada. 8F no debe adelantarse a la señal de exportabilidad. 8G debe conseguir un canvas exacto, pero no incorporar el motor PDF; la salida nativa comienza en Fase 9 después de 8K y 8L. Presupuesto permanece separado hasta Fase 10.

## 12. Siguiente fase recomendada

Fases 8A, 8B, 8C y 8D están completadas. La siguiente fase segura es **Fase 8E —
Reglas, guías, snap, smart guides y medición**. Debe consumir la selección,
visibilidad temporal, referencia geométrica y sesiones de puntero existentes,
ampliando paridad geométrica sin adelantar resize 8F.

## 13. Especificación histórica de implementación 8A

> El bloque siguiente se conserva como trazabilidad de la planificación original. Fases 8A y 8B ya están completadas; su estado vigente está en el apartado 10 y en `13_POSICIONAMIENTO_Y_COMANDOS_V2.md` / `14_OPERACIONES_DE_OBJETO_Y_CLIPBOARD_V2.md`. El bloque no autoriza trabajo nuevo ni sustituye el roadmap 8C–8L/Fases 9–10.

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
- DOCS/OFFSET/V2/12_CORRECCION_COMPATIBILIDAD_DE_MEDIDA_Y_ETIQUETAS_V2.md
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

Crea DOCS/OFFSET/V2/13_POSICIONAMIENTO_MANUAL_V2.md con:

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
