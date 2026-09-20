# Documentación de Editor Offset Visual V2

## Por dónde empezar

1. [20 — Estado operativo vigente](20_ESTADO_ACTUAL_POST_REDISENO_UX_V2.md).
2. [40 — Auditoría integral, mapa funcional y plan de mejoras](40_AUDITORIA_INTEGRAL_MAPA_Y_PLAN_DE_MEJORAS_V2.md).
3. Contratos [01 — Layout](01_CONTRATO_LAYOUT_V2.md), [02 — Geometría](02_KERNEL_GEOMETRICO_V2.md) y [21 — Preflight](21_CONTRATO_PREFLIGHT_V2.md).
4. [39 — Cierre de salida 39A–39C](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md), para implementación, límites y operación.
5. [11 — Decisiones pendientes](11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md), antes de ampliar alcance.

El editor tiene Preview/PDF nativos, corrección interna y derivados. Hay defectos abiertos de preflight, derivados y Repeat. Dev tools no controla la capacidad de colocar páginas. Seleccionar todos existe; separar una cuadrícula conservando sus filas/columnas sigue siendo una propuesta.

## Índice completo y autoridad

Un documento de fase conserva lo que se decidió/probó entonces. Sus exclusiones y próximos pasos no son automáticamente pendientes actuales. Un contrato define intención; una brecha de implementación debe registrarse, no ocultarse cambiando su texto. Este índice y 40 alinean la lectura sin borrar evidencia histórica.

| Documento | Clasificación | Cómo usarlo ahora |
|---|---|---|
| [01 — Contrato Layout V2 del Editor Offset Visual](01_CONTRATO_LAYOUT_V2.md) | Contrato | Layout V2; extensión derivada aclarada; no describe todo el estado de salida. |
| [02 — Kernel geométrico V2 del Editor Offset Visual](02_KERNEL_GEOMETRICO_V2.md) | Contrato geométrico | Kernel canónico; alcance de su fase no sustituye el estado 20. |
| [03 — Adaptador de salida del Editor Offset Visual V2](03_ADAPTADOR_SALIDA_V2.md) | Contrato de frontera temporal | Puente/diagnóstico legacy; separado del compositor nativo. |
| [04 — Shell, Blueprint y repositorio de jobs del Editor Offset Visual V2](04_SHELL_Y_JOBS_V2.md) | Fase histórica | Shell y jobs; conservar decisiones, consultar 20/40 para actualidad. |
| [05 — Fase 5 — Store, comandos, guardado y canvas SVG básico](05_CANVAS_STORE_V2.md) | Fase histórica | Canvas/store iniciales; ampliados posteriormente. |
| [06 — Fase 6 — Assets PDF, páginas, miniaturas y slots reales](06_ASSETS_Y_SLOTS_V2.md) | Fase histórica | Assets y slots iniciales; posteriores capacidades en 32/39. |
| [07 — Fase 7 — Motor Repeat para Editor Offset Visual V2](07_REPEAT_V2.md) | Fase y contrato Repeat | Base Repeat; limitación de huecos confirmada en AUD-013. |
| [08 — Auditoría técnica del estado actual del Editor Offset Visual V2](08_AUDITORIA_ESTADO_ACTUAL_V2.md) | Auditoría histórica | Corte previo a rediseño y salida nativa; no es estado vigente. |
| [09 — Plan técnico de herramientas manuales del Editor Offset Visual V2](09_PLAN_HERRAMIENTAS_MANUALES_V2.md) | Plan histórico | 8A–8E implementadas; corrección interna también existe; resize pendiente. |
| [10 — Fase 8P — Estabilización semántica del Editor Offset Visual V2](10_ESTABILIZACION_SEMANTICA_V2.md) | Fase histórica | Estabilización 8P; sus exclusiones corresponden a esa fase. |
| [11 — Decisiones arquitectónicas pendientes del Editor Offset Visual V2](11_DECISIONES_ARQUITECTONICAS_PENDIENTES_V2.md) | Decisiones vigentes + archivo histórico | Tabla actual separa resuelto, defectos y decisiones abiertas. |
| [12 — Corrección V2 de compatibilidad de medida PDF/trim y etiquetas de slots](12_CORRECCION_COMPATIBILIDAD_DE_MEDIDA_Y_ETIQUETAS_V2.md) | Fase histórica | Tolerancias/etiquetas y diagnóstico del puente temporal. |
| [13 — Fase 8A — Posicionamiento manual preciso y sistema central de acciones/atajos](13_POSICIONAMIENTO_Y_COMANDOS_V2.md) | Contrato de herramienta + fase | Posición/acciones; no reimplementar 8A. |
| [14 — Fase 8B — Operaciones de objeto y clipboard interno](14_OPERACIONES_DE_OBJETO_Y_CLIPBOARD_V2.md) | Contrato de herramienta + fase | Objetos/clipboard; seleccionar todos ya existe. |
| [15 — Fase 8C — Alineación, distribución, gap exacto y matriz](15_ALINEACION_DISTRIBUCION_Y_MATRIZ_V2.md) | Contrato de herramienta + fase | Gap secuencial y matriz; no redistribuye cuadrículas existentes. |
| [16 — Selección avanzada, árbol de objetos y visibilidad temporal V2](16_SELECCION_AVANZADA_Y_ARBOL_V2.md) | Contrato de herramienta + fase | Selección/árbol/ocultos temporales. |
| [17 — Reglas, guías, snap y medición del Editor Offset Visual V2](17_REGLAS_GUIAS_SNAP_Y_MEDICION_V2.md) | Contrato de herramienta + fase | Reglas/guías/snap/medición; geometría compartida con Python. |
| [18 — Estado actual del Editor Offset Visual V2 después de las exploraciones 1 a 4](18_ESTADO_ACTUAL_POST_EXPLORACIONES_1_A_4_V2.md) | Snapshot histórico | Exploraciones 1–4 previas al rediseño. |
| [19 — Plan y trazabilidad del rediseño UX incremental del Editor Offset Visual V2](19_PLAN_Y_TRAZABILIDAD_REDISENO_UX_V2.md) | Plan y bitácora histórica cerrada | 19-A–19-G; no abrir 19-H ni repetir el rediseño. |
| [20 — Estado actual del Editor Offset Visual V2 después del rediseño UX](20_ESTADO_ACTUAL_POST_REDISENO_UX_V2.md) | Estado operativo vigente | Resumen actual; cuerpo anterior preservado como archivo histórico. |
| [21 — Contrato canónico de preflight del Editor Offset Visual V2](21_CONTRATO_PREFLIGHT_V2.md) | Contrato de preflight | Con brechas de implementación registradas en AUD-001/003/005. |
| [22 — Ensayo controlado de reutilización de salida V1 desde V2](22_ENSAYO_REUTILIZACION_SALIDA_V1.md) | Ensayo histórico offline | Caracterización legacy; no es ruta productiva V2. |
| [23 — Fase 23 — Preparación de fuentes y ensayo de salida V2](23_PREPARACION_FUENTES_Y_PARIDAD_SALIDA_V2.md) | Fase histórica de preparación | Parte se reutiliza; evolución nativa en 39B. |
| [24 — Fase 24 — Preflight ejecutable mínimo del Editor Offset Visual V2](24_PREFLIGHT_EJECUTABLE_V2.md) | Fase histórica de preflight | Implementación inicial ampliada por 35/39A. |
| [25 — Fase 25 — Auditoría amplia de QA del Editor Offset Visual V2](25_AUDITORIA_COMPLETA_QA_V2.md) | Auditoría histórica | Sus pendientes deben contrastarse con 39/40. |
| [26 — Fase 26 — Fixtures canónicos y criterios de paridad PDF V2](26_FIXTURES_Y_PARIDAD_PDF_V2.md) | Fixtures y contrato de evidencia | Base de paridad ampliada por 37/39; no prueba todas las combinaciones. |
| [27 — Fase 27 — Preview mínima V2 detrás de gate](27_PREVIEW_MINIMA_GATED_V2.md) | Fase histórica Preview | Mínimo inicial ampliado por 29/30/39. |
| [28 — Fase 28 — Evidencia de paridad Preview–canvas V2](28_PARIDAD_PREVIEW_CANVAS_V2.md) | Fase de paridad histórica | Evidencia inicial; ampliada después. |
| [29 — Fase 29 — Transformaciones y clipping en Preview V2](29_TRANSFORMACIONES_PREVIEW_V2.md) | Semántica y fase de transformaciones | Contenido interno implementado; revisar defectos de derivados. |
| [30 — Fase 30 — Marcas de corte y dúplex en Preview V2](30_MARCAS_Y_DUPLEX_PREVIEW_V2.md) | Fase de marcas/dúplex | Backend/Preview; no equivale a UI completa de caras o marcas. |
| [31 — Fase 31 — PDF V2 propio detrás de gate](31_PDF_FINAL_GATED_V2.md) | Fase PDF inicial histórica | Candidato raster superado por compositor nativo 39B. |
| [32A — Fase 32A — Trabajos multipágina de Editor Offset Visual V2](32A_TRABAJOS_MULTIPAGINA_V2.md) | Fase implementada | Trabajos multipágina; aprovechamiento Repeat pendiente AUD-013. |
| [32B — Fase 32B — Correcciones gráficas de contenido V2](32B_CORRECCIONES_GRAFICAS_V2.md) | Fase implementada | Correcciones gráficas internas, distintas de resize del slot. |
| [32C — Fase 32C — Derivados de página V2](32C_ASSETS_DERIVADOS_V2.md) | Fase implementada | Assets derivados sin sobrescribir originales. |
| [32D — Fase 32D — Integración de derivados con slots y salida V2](32D_INTEGRACION_DERIVADOS_SALIDA_V2.md) | Fase implementada / extensión opcional | Referencia source.derived y salida. |
| [32E — Fase 32E — Guardia de paridad para páginas derivadas V2](32E_GUARDIA_PARIDAD_DERIVADOS_V2.md) | Fase implementada | Guardia de paridad; no cubre todos los giros con offset. |
| [32F — Fase 32F — Materialización transformada V2](32F_MATERIALIZACION_TRANSFORMADA_V2.md) | Fase implementada con defecto abierto | Materialización transformada; AUD-002. |
| [33 — Fase 33 — Paridad de derivados, Preview y PDF V2](33_PARIDAD_DERIVADOS_PREVIEW_PDF_V2.md) | Evidencia de paridad | Conservar umbrales y ampliar regresión de AUD-002. |
| [34 — Fase 34 — Repeat V2 y orientaciones cardinales en trabajos multipágina](34_REPEAT_MULTIPAGINA_ORIENTACIONES_V2.md) | Fase Repeat implementada | Orientaciones cardinales; no garantiza mejor empaquetado. |
| [35 — Fase 35 — Preflight obligatorio para Preview y PDF final V2](35_PREFLIGHT_OBLIGATORIO_SALIDA_V2.md) | Fase implementada | Preflight obligatorio; bloqueo real requiere corregir AUD-001. |
| [36 — Fase 36 — Endurecimiento operativo de salida V2](36_ENDURECIMIENTO_OPERATIVO_V2.md) | Fase implementada | Endurecimiento y recuperación, ampliados por 38/39. |
| [37 — Fase 37 — Contrato canónico de paridad de salida V2](37_CONTRATO_PARIDAD_SALIDA_V2.md) | Contrato de aceptación y evidencia | Paridad limitada al perfil/casos documentados. |
| [38 — Fase 38 — Concurrencia, retención y recuperación operativa V2](38_CONCURRENCIA_RETENCION_RECUPERACION_V2.md) | Fase implementada | Concurrencia por archivo y retención explícita; no multi-host certificado. |
| [39 — Plan SAFE — Cierre de salida V2 en tres fases](39_PLAN_SAFE_CIERRE_SALIDA_PRODUCTIVA_V2.md) | Plan y cierre histórico reciente | 39A–39C implementadas; riesgos posteriores en 40. |
| [40 — Auditoría integral, mapa vigente y plan de mejoras de Editor Offset Visual V2](40_AUDITORIA_INTEGRAL_MAPA_Y_PLAN_DE_MEJORAS_V2.md) | Auditoría vigente y propuesta SAFE | Hallazgos abiertos, mapa funcional, evidencias y mejoras; no implementación. |

## Regla de mantenimiento

Actualizar 20 al cambiar comportamiento; registrar evidencia y estado de cada hallazgo en 40 durante su corrección; actualizar el contrato específico cuando corresponda. Una nueva fase debe declarar alcance y aceptación, sin convertir una propuesta del roadmap en autorización automática. La historia permanece identificada por su fase/fecha.
