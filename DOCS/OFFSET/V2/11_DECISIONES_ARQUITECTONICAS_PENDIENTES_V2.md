# Decisiones arquitectónicas pendientes del Editor Offset Visual V2

## 1. Propósito

Este documento registra decisiones para fases futuras sin modificar todavía el contrato, almacenamiento o salida. Ningún modelo conceptual descrito aquí autoriza por sí solo agregar campos a Layout V2.

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

## 6. Motor de salida nativo

Destino arquitectónico:

```text
Editor V2 -> motor de salida V2 propio
```

El OutputAdapter legacy sigue siendo un puente temporal. Puede utilizarse para caracterizar compatibilidad, pero no debe condicionar indefinidamente el dominio V2 ni introducir vocabulario legacy en el layout.

Antes de sustituir el puente, el motor nativo deberá demostrar paridad y cobertura para:

- centro trim, rotación cardinal y footprint con bleed;
- cajas PDF y offsets;
- transformaciones internas autorizadas;
- caras y orden dúplex;
- marcas y CTP cuando se habiliten;
- preview y PDF final coherentes;
- rutas de assets seguras;
- errores estructurados y resultados deterministas.

`montaje_offset_inteligente.py` permanece sin cambios. La existencia de `output-capabilities` no conecta ni ejecuta ese renderer.

## 7. Decisiones que siguen abiertas

- formato, versionado y atomicidad de `reports/<report_id>.json`;
- lifecycle/retención de assets derivados;
- política explícita para migración masiva de slots a un asset corregido;
- tecnología de concurrencia multiproceso;
- contrato interno y estrategia de paridad del motor de salida nativo;
- momento en que el puente legacy puede retirarse;
- expansión de la paridad geométrica JavaScript o migración futura a TypeScript.

Cada decisión debe cerrarse en una fase propia con código, contratos, fixtures, tests y rollback definidos.
