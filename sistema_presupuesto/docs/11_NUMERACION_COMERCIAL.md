# Numeracion Comercial

Fase 9.3 agrega numeracion comercial aislada para presupuestos guardados.

No genera PDF, no integra con la app principal Flask y no toca el Editor Offset Visual.

## Formato

El formato del numero comercial es:

```text
PRES-YYYY-000001
```

Ejemplos:

```text
PRES-2026-000001
PRES-2026-000002
```

## Reglas

- `YYYY` sale de la fecha actual del backend.
- El backend siempre genera el numero.
- No se confia en numeros enviados por frontend.
- El contador es persistente.
- Si cambia el anio, el contador de ese anio empieza en `000001`.
- No se renumeran presupuestos antiguos.
- No se reutiliza un numero aunque luego se elimine o descarte el presupuesto.

## Persistencia

El estado del contador vive en:

```text
data/quote_numbering.json
```

Estructura:

```json
{
  "schema": "sistema_presupuesto.quote_numbering",
  "schema_version": 1,
  "counters": {
    "2026": 2
  }
}
```

Si el archivo no existe, el backend usa estado inicial en memoria y lo crea al emitir el primer numero.

Si el JSON esta mal formado o tiene estructura invalida, se devuelve error controlado.

## Integracion con presupuestos

Al crear un presupuesto guardado, `BudgetRepository` agrega:

```json
{
  "presupuesto_id": "psp_20260622_abcd1234abcd",
  "numero_comercial": "PRES-2026-000001"
}
```

`presupuesto_id` sigue siendo el ID tecnico interno.
`numero_comercial` es la referencia comercial visible.

Los presupuestos antiguos sin `numero_comercial` siguen siendo validos.
El sistema no los recalcula ni renumera automaticamente.

Al duplicar un presupuesto, el backend genera un nuevo `numero_comercial`.
No se reutiliza el numero del presupuesto original.

## API aislada

`POST /api/sistema-presupuesto/cotizar-y-guardar` devuelve:

```json
{
  "ok": true,
  "presupuesto_id": "psp_...",
  "numero_comercial": "PRES-2026-000001",
  "record": {}
}
```

Endpoint de estado:

```text
GET /api/sistema-presupuesto/numeracion
```

Este endpoint no incrementa el contador. Solo muestra el estado actual y el siguiente numero previsto.

## UI aislada

La UI muestra `numero_comercial`:

- despues de guardar un presupuesto;
- en la lista de presupuestos guardados;
- al abrir el JSON de un presupuesto guardado.

## Limitaciones

- El PDF comercial usa `numero_comercial` cuando existe.
- La duplicacion de presupuestos crea nuevo numero comercial.
- El historial avanzado muestra `numero_comercial` cuando existe y conserva compatibilidad legacy.
- No se asocian clientes a presupuestos todavia.
- No hay configuracion UI del prefijo `PRES`.
- No hay multiples sucursales o series.
