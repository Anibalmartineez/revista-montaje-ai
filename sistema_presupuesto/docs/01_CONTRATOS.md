# Contratos

Este documento describe contratos JSON futuros para `sistema_presupuesto/`.

No hay API implementada en Fase 1. Los contratos son una base de diseno para fases posteriores.

## Principios

- Los contratos deben ser versionados.
- Los totales enviados por frontend no son fuente de verdad.
- El backend o motor debe recalcular siempre.
- Los presupuestos aceptados no deben sobrescribirse; deben versionarse o duplicarse.
- Los datos monetarios deben incluir moneda.
- Las unidades fisicas deben declarar unidad de medida.

## QuoteRequest futuro

Entrada conceptual para cotizar un trabajo.

```json
{
  "schema": "sistema_presupuesto.quote_request",
  "schema_version": 1,
  "cliente": {
    "nombre": "Cliente ejemplo",
    "referencia": null
  },
  "producto": {
    "titulo": "Volante A5",
    "tipo": "volante",
    "cantidad": 1000,
    "ancho_mm": 148,
    "alto_mm": 210,
    "sangrado_mm": 3,
    "paginas": null,
    "caras": 2,
    "colores": {
      "frente": 4,
      "dorso": 4,
      "texto": "4/4"
    }
  },
  "produccion": {
    "pliego_base_mm": [700, 1000],
    "pliego_util_mm": [680, 980],
    "formas_por_pliego_manual": null,
    "merma_arranque_pliegos": 30,
    "merma_pct": 3
  },
  "costos": {
    "material_id": "couche_150",
    "maquina_id": "offset_4_colores",
    "procesos_ids": ["corte"],
    "moneda": "PYG",
    "margen_pct": 30,
    "markup_pct": null,
    "impuestos": []
  }
}
```

## QuoteResult futuro

Salida conceptual de calculo.

```json
{
  "schema": "sistema_presupuesto.quote_result",
  "schema_version": 1,
  "ok": true,
  "produccion": {
    "formas_por_pliego": 16,
    "pliegos_netos": 63,
    "pliegos_brutos": 95,
    "chapas": 8,
    "pasadas": 2,
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
    "costo_tecnico": "0",
    "margen": "0",
    "descuento": "0",
    "impuestos": "0",
    "precio_final": "0",
    "precio_unitario": "0"
  },
  "warnings": []
}
```

## BudgetRecord futuro

Registro persistido de presupuesto.

```json
{
  "schema": "sistema_presupuesto.budget_record",
  "schema_version": 1,
  "presupuesto_id": "psp_20260621_abcd12",
  "version": 1,
  "estado": "borrador",
  "request": {},
  "result": {},
  "created_at": "2026-06-21T00:00:00Z",
  "updated_at": "2026-06-21T00:00:00Z"
}
```

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
