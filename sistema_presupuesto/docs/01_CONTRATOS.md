# Contratos

Este documento describe contratos JSON futuros para `sistema_presupuesto/`.

No hay API ni motor implementados en Fase 3. Los contratos y fixtures ya pueden validarse con `backend/validators.py`.

## Principios

- Los contratos deben ser versionados.
- Los totales enviados por frontend no son fuente de verdad.
- El backend o motor debe recalcular siempre.
- Los presupuestos aceptados no deben sobrescribirse; deben versionarse o duplicarse.
- Los datos monetarios deben incluir moneda.
- Las unidades fisicas deben declarar unidad de medida.
- Los importes deben viajar como strings para que la futura implementacion los convierta a `Decimal`.
- Los fixtures pueden incluir `expected_assertions`, pero esos valores no son calculados en Fase 2.

## Archivos definidos en Fase 2

Catalogos:

- `data/catalogo/materiales_default.json`
- `data/catalogo/maquinas_default.json`
- `data/catalogo/procesos_default.json`

Fixtures de entrada:

- `data/fixtures/quote_request_volante.json`
- `data/fixtures/quote_request_tarjeta.json`
- `data/fixtures/quote_request_revista.json`
- `data/fixtures/quote_request_diptico.json`
- `data/fixtures/quote_request_triptico.json`

Fixture de salida:

- `data/fixtures/quote_response_example.json`

## QuoteRequest futuro

Entrada conceptual para cotizar un trabajo. La estructura real de Fase 2 vive en los fixtures `quote_request_*.json`.

```json
{
  "schema": "sistema_presupuesto.quote_request",
  "schema_version": 1,
  "fixture_id": "quote_request_volante",
  "descripcion": "Volante A5 simple 4/0 para validar papel, chapas, pliegos y merma.",
  "cliente": {
    "nombre": "Cliente ejemplo",
    "referencia": null
  },
  "producto": {
    "titulo": "Volante A5",
    "tipo": "volante",
    "cantidad": "1000",
    "unidad_cantidad": "unidad",
    "ancho_mm": "148",
    "alto_mm": "210",
    "sangrado_mm": "3",
    "paginas": null,
    "caras": 2,
    "colores": {
      "frente": 4,
      "dorso": 0,
      "texto": "4/0"
    }
  },
  "produccion": {
    "pliego_base_mm": {
      "ancho": "700",
      "alto": "1000"
    },
    "pliego_util_mm": {
      "ancho": "680",
      "alto": "980"
    },
    "formas_por_pliego_manual": null,
    "merma_arranque_pliegos": "30",
    "merma_pct": "3",
    "imposicion_origen": "fixture_formula_simple"
  },
  "costos": {
    "material_id": "couche_150",
    "maquina_id": "offset_4_colores",
    "procesos_ids": ["corte"],
    "moneda": "PYG",
    "margen_pct": "30",
    "markup_pct": null,
    "impuestos": []
  }
}
```

## QuoteResult futuro

Salida conceptual de calculo. En Fase 2 solo existe como fixture de ejemplo, no como resultado de motor.

```json
{
  "schema": "sistema_presupuesto.quote_result",
  "schema_version": 1,
  "fixture_id": "quote_response_example",
  "ok": true,
  "calculation": {
    "engine_version": "pendiente",
    "rules_version": "fase_2_contrato",
    "uses_decimal_strings": true,
    "implemented": false
  },
  "produccion": {
    "formas_por_pliego": "16",
    "pliegos_netos": "63",
    "pliegos_brutos": "95",
    "chapas": "4",
    "pasadas": "1",
    "horas_maquina": "1.40"
  },
  "costos": {
    "moneda": "PYG",
    "items": [
      {
        "codigo": "papel",
        "descripcion": "Papel couche 150 g/m2",
        "cantidad": "95",
        "unidad": "pliego",
        "costo_unitario": "3500",
        "subtotal": "332500"
      }
    ],
    "costo_tecnico": "606100",
    "margen": {
      "tipo": "margen_sobre_venta",
      "pct": "30",
      "monto": "259757.14"
    },
    "markup": null,
    "descuento": "0",
    "impuestos": [],
    "precio_final": "865857.14",
    "precio_unitario": "865.86"
  },
  "warnings": [
    {
      "code": "EXAMPLE_VALUES",
      "message": "Los importes de este fixture son valores ficticios de diseno."
    }
  ]
}
```

## BudgetRecord futuro

Registro persistido de presupuesto.

```json
{
  "schema": "sistema_presupuesto.budget_record",
  "schema_version": 1,
  "presupuesto_id": "psp_20260621_abcd12",
  "numero_comercial": "PRES-2026-000001",
  "version": 1,
  "estado": "borrador",
  "request": {},
  "result": {},
  "created_at": "2026-06-21T00:00:00Z",
  "updated_at": "2026-06-21T00:00:00Z"
}
```

En Fase 5 los presupuestos guardados se escriben como JSON local bajo:

```text
data/presupuestos/<presupuesto_id>.json
```

Reglas:

- `presupuesto_id` debe cumplir `psp_YYYYMMDD_<12 hex>`.
- `numero_comercial` usa formato `PRES-YYYY-000001` para presupuestos creados desde Fase 9.3.
- `schema` debe ser `sistema_presupuesto.budget_record`.
- `schema_version` debe ser `1`.
- `estado` inicial es `calculado`.
- `result` contiene el desglose auditable serializado.
- no se sobrescribe un presupuesto existente por defecto.
- presupuestos antiguos sin `numero_comercial` siguen siendo compatibles y no se renumeran automaticamente.

## Estados futuros

- `borrador`
- `calculado`
- `enviado`
- `aceptado`
- `rechazado`
- `anulado`

## Catalogos futuros

Catalogos previstos:

- materiales;
- maquinas;
- procesos;
- terminaciones;
- impuestos;
- reglas de merma;
- formatos de pliego.

Cada tarifa debe declarar vigencia, fuente y moneda.

## Convenciones de unidades

- medidas lineales: `mm`;
- area: `m2`;
- cantidades impresas: `unidad`, `ejemplar`, `pliego`, `hoja`;
- tiempo: `horas`;
- moneda: `PYG`;
- porcentajes: strings numericos en campos con sufijo `_pct`;
- dinero: strings numericos para uso futuro con `Decimal`.

## Reglas de compatibilidad

Los contratos de Fase 2 no son API publica todavia. Pueden ajustarse antes de implementar modelos, pero cualquier cambio debe actualizar fixtures y documentacion al mismo tiempo.

## Validadores de Fase 3

Archivos agregados:

- `backend/models.py`
- `backend/validators.py`
- `backend/errors.py`
- `backend/serializers.py`

Reglas bloqueantes actuales:

- `schema` debe ser `sistema_presupuesto.quote_request`.
- `schema_version` debe ser `1`.
- `moneda` debe ser `PYG`.
- cantidades y medidas deben ser mayores que cero.
- sangrado, merma y porcentajes no deben ser negativos.
- `margen_pct` y `markup_pct` no pueden venir activos al mismo tiempo.
- `revista` requiere `paginas` positivas, multiplo de 4, y `encuadernacion.tipo`.
- `folleto_diptico` requiere `paneles=2`.
- `folleto_triptico` requiere `paneles=3`.
- `material_id`, `maquina_id` y `procesos_ids[]` deben existir en catalogos activos cuando se validan con catalogo.

Reglas de advertencia actuales:

- si falta `producto.colores.texto`, se agrega advertencia no bloqueante.

Los validadores no calculan precios ni aceptan totales enviados por frontend como fuente de verdad.
