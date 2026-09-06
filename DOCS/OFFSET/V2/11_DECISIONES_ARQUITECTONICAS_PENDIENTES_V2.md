# Decisiones arquitectónicas pendientes del Editor Offset Visual V2

## 1. Propósito

Este documento registra decisiones para fases futuras sin modificar todavía el contrato, almacenamiento o salida. Ningún modelo conceptual descrito aquí autoriza por sí solo agregar campos a Layout V2.

Actualización documental 2026-09-06, posterior a la Fase 19: la independencia de V2 es una decisión explícita aprobada por el usuario (sección 6). La especificación propuesta del reporte está en [21_CONTRATO_PREFLIGHT_V2.md](21_CONTRATO_PREFLIGHT_V2.md); sus detalles pendientes no se consideran implementados ni aprobados por la sola autorización para redactarlos.

## 2. Linaje de assets corregidos

Una corrección PDF nunca sobrescribirá el original. Creará un asset nuevo e inmutable con un linaje conceptual equivalente a:

```json
{
  "derived_from": {
    "asset_id": "asset_original",
    "operation": "normalización o corrección identificable",
    "parameters": {}
  }
}
```

Reglas futuras:

- el original se conserva byte a byte;
- una corrección produce identidad, hash y archivos nuevos;
- migrar slots al asset derivado es una operación explícita y reversible sobre referencias;
- undo de una referencia de slot no borra archivos físicos;
- garbage collection y retención de derivados requieren una política separada;
- esta fase no añade `derived_from` al schema.

## 3. Fuente canónica de preflight

El reporte completo canónico futuro será:

```text
reports/<report_id>.json
```

Campos de layout como:

```text
preflight_status
preflight_report_id
preflight_updated_at
pages[].preflight
```

serán resúmenes, índices o caches derivados para la UI. No deben competir con dos reportes completos divergentes. La actualización del resumen y la publicación del reporte necesitarán una frontera transaccional o una estrategia compensatoria explícita.

El documento 21 distingue reporte físico de asset y reporte de montaje. Propone publicar inicialmente reportes inmutables sin actualizar Layout V2, para no cambiar revisión e invalidar el propio snapshot. Los campos actuales del asset se conservan por compatibilidad; no alojarán un reporte de montaje. Su sincronización futura requiere una fase propia. El reporte tendrá versión independiente del layout, cobertura explícita y decisiones por operación; un control obligatorio no ejecutado no podrá aprobar producción.

No se implementa preflight profundo en Fase 8P. El diagnóstico `output-capabilities` solo compara el layout con las restricciones del puente temporal y no sustituye este reporte.

## 4. Evolución del contrato

Obligan a aumentar `layout_schema_version`:

- cambios incompatibles;
- campos nuevos requeridos;
- eliminación o cambio de tipo de campos;
- cambios semánticos obligatorios en datos existentes;
- nuevas invariantes que invaliden layouts V2 previamente válidos sin una ruta compatible.

Un campo opcional aditivo puede permanecer en V2 únicamente con actualización coordinada de:

- JSON Schema;
- validador semántico;
- fixtures;
- tests;
- lectores y escritores;
- adaptadores y UI que necesiten interpretarlo.

No se introduce `layout_schema_revision` sin una necesidad real. Ningún campo se añade de forma improvisada desde documentación, renderer o comando aislado.

## 5. Concurrencia

El lock actual de `JobRepository` vive dentro del proceso Flask y es suficiente para desarrollo local y despliegue de un solo proceso. No protege dos workers o dos hosts.

Una producción multiproceso requerirá seleccionar y probar una solución compartida:

- file lock con semántica y timeout definidos;
- SQLite con transacciones;
- base de datos;
- almacenamiento transaccional equivalente.

La revisión optimista y el compare-and-swap deberán conservarse. Fase 8P no cambia almacenamiento ni migra jobs.

## 6. V2 principal e independiente — decisión aprobada

Destino arquitectónico:

```text
Editor V2 -> dominio, preflight, imposición y salida propios
```

El usuario definió el 2026-09-06 que V2 será el editor principal, con código propio y sin dependencia futura de código productivo V1 o de módulos de negocio compartidos con V1. V1 permanece como legacy. Es una dirección aprobada, no una independencia ya alcanzada.

Se permite copiar selectivamente código útil del editor anterior dentro de V2, identificando origen y dependencias, conservando avisos de licencia aplicables, adaptándolo al contrato V2 y aportando pruebas propias. La copia se mantendrá de forma independiente; no conservará imports a servicios/motores legacy ni sus defaults o heurísticas por obligación. El uso de bibliotecas externas no contradice esta independencia.

Las dependencias actuales, incluido Repeat sobre `engines/step_repeat_pro_engine.py` y el registro compartido en `app.py`, requieren fases de extracción propias. La decisión no autoriza modificarlas dentro del preflight documental, ni decide aún separación de repositorio o despliegue.

El OutputAdapter legacy sigue siendo una superficie temporal de diagnóstico y posible caracterización. No se ampliará como camino productivo por defecto ni definirá las capacidades del nuevo dominio. La futura salida se diseñará nativa V2, sin introducir vocabulario legacy en Layout V2.

Antes de habilitar cada capacidad nativa, el motor deberá demostrar coherencia con el contrato V2 y cobertura para:

- centro trim, rotación cardinal y footprint con bleed;
- cajas PDF y offsets;
- transformaciones internas autorizadas;
- caras y orden dúplex;
- marcas y CTP cuando se habiliten;
- preview y PDF final coherentes;
- rutas de assets seguras;
- errores estructurados y resultados deterministas.

`montaje_offset_inteligente.py` permanece sin cambios. La existencia de `output-capabilities` no conecta ni ejecuta ese renderer.

La paridad se mide contra geometría y fixtures esperados; comparar con legacy aporta caracterización, pero no obliga a reproducir sus defectos. El retiro del diagnóstico temporal es posterior y no exige construir primero una conexión productiva con V1.

## 7. Decisiones que siguen abiertas

- revisión de la especificación de reporte del documento 21, schema ejecutable y detalles de lectura estable/publicación;
- política de bloqueos, tolerancias productivas y cobertura obligatoria por operación;
- orden de transformaciones y semántica exacta de clipping;
- lifecycle/retención de assets derivados;
- política explícita para migración masiva de slots a un asset corregido;
- tecnología de concurrencia multiproceso;
- contrato interno y estrategia de paridad del motor de salida nativo;
- momento en que el puente legacy puede retirarse;
- inventario y plan de extracción de las dependencias compartidas actuales;
- ampliación de cobertura geométrica/PDF; una migración futura a TypeScript es opcional y no condiciona el preflight.

Cada decisión debe cerrarse en una fase propia con código, contratos, fixtures, tests y rollback definidos.
