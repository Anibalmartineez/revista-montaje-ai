# Tests y Validacion

Este documento define la estrategia inicial de validacion para `sistema_presupuesto/`.

Fase 3 agrega tests minimos para validar contratos y serializadores sobre los fixtures de Fase 2.

Fase 4 agrega tests del motor tecnico, monetario y orquestador de calculo.

Fase 5 agrega tests para persistencia JSON local y repositorios.

Fase 6 agrega tests del CLI interno.

## Principios

- Probar primero funciones puras.
- No depender del Editor Offset Visual.
- No depender de Flask para validar formulas.
- Usar fixtures con numeros esperados.
- Separar tests de contratos, calculos y persistencia.

## Casos reales minimos

### Volante simple

- Fixture: `data/fixtures/quote_request_volante.json`.
- Cantidad: 1000.
- Formato final: 148 x 210 mm.
- Sangrado: 3 mm.
- Colores: `4/0`.
- Validar formas por pliego, pliegos netos, merma, chapas y costo de papel.
- Expectativas iniciales: pieza con sangrado 154 x 216 mm, 16 formas teoricas, 63 pliegos netos, 4 chapas, 1 pasada.

### Tarjeta

- Fixture: `data/fixtures/quote_request_tarjeta.json`.
- Cantidad: 500.
- Formato final: 90 x 50 mm.
- Sangrado: 3 mm.
- Colores: `4/4`.
- Validar que el dorso no duplique papel, pero si afecte chapas y pasadas.
- Expectativas iniciales: pieza con sangrado 96 x 56 mm, 119 formas teoricas, 5 pliegos netos, 8 chapas, 2 pasadas.

### Revista

- Fixture: `data/fixtures/quote_request_revista.json`.
- Cantidad: 1000.
- Formato cerrado: 210 x 297 mm.
- Paginas: 32.
- Encuadernacion: caballete.
- Validar que paginas y encuadernacion sean obligatorias y que las paginas sean multiplo de 4.
- Validar que una revista no se trate como una pieza simple.

### Folleto diptico

- Fixture: `data/fixtures/quote_request_diptico.json`.
- Formato abierto: 297 x 210 mm.
- Formato cerrado: 148.5 x 210 mm.
- Paneles: 2.
- Pliegues: 1.
- Validar que la impresion use formato abierto.
- Validar que el plegado se cobre por unidad final.

### Folleto triptico

- Fixture: `data/fixtures/quote_request_triptico.json`.
- Formato abierto: 297 x 210 mm.
- Paneles: 3.
- Pliegues: 2.
- Validar que no se multiplique la tirada por cantidad de paneles.

### Frente/dorso

- Colores: `4/1`.
- Validar chapas esperadas, pasadas y caras activas.

### Trabajo con terminacion

- Fixtures relacionados: `quote_request_tarjeta.json`, `quote_request_diptico.json`, `quote_request_triptico.json`.
- Laminado por metro cuadrado.
- Guillotina fija.
- Redondeado por unidad.
- Validar subtotales por modo de cobro.

### Trabajo con merma

- Tirada alta.
- Validar merma porcentual, merma de arranque y redondeo hacia arriba.

## Tests automaticos futuros

Tests implementados:

- `tests/test_validators.py`
- `tests/test_serializers.py`
- `tests/test_production_math.py`
- `tests/test_pricing_engine.py`
- `tests/test_calculation_engine.py`
- `tests/test_storage.py`
- `tests/test_catalog_repository.py`
- `tests/test_repositories.py`
- `tests/test_cli.py`

Nombres sugeridos para fases futuras:

- `test_bleed_expands_final_size`
- `test_forms_per_sheet_uses_useful_area`
- `test_front_back_chapas_pasadas`
- `test_waste_policy`
- `test_process_cost_modes`
- `test_budget_totals_reconcile`
- `test_required_fields_by_work_type`
- `test_inviable_job`
- `test_no_negative_inputs`
- `test_margin_vs_markup_rejected_when_both_are_present`

## Casos limite

- cantidad cero;
- cantidad negativa;
- medidas cero;
- sangrado excesivo;
- pieza igual al limite del pliego util;
- material sin precio vigente;
- maquina sin rendimiento;
- proceso por metro cuadrado sin area calculable;
- revista con 30 paginas;
- margen 0%;
- margen invalido mayor o igual a 100%;
- moneda desconocida;
- redondeo por moneda.

## Validacion manual futura

Antes de considerar productivo el motor:

1. Comparar fixtures contra una planilla independiente.
2. Revisar formas por pliego con operador de preprensa.
3. Revisar merma con operador o jefe de produccion.
4. Revisar terminaciones tercerizadas con tarifas reales.
5. Revisar impuestos con criterio contable del usuario.

## Comandos futuros

Cuando existan archivos Python y tests:

```bash
python -m compileall sistema_presupuesto
pytest sistema_presupuesto/tests
git diff --check
```

No usar tests del Editor Offset Visual como validacion principal del Sistema Presupuesto.

## Validacion de fixtures JSON

Antes de implementar motor, cada fixture debe ser validado manualmente:

- JSON valido;
- `schema` y `schema_version` presentes;
- moneda `PYG`;
- importes como strings;
- `margen_pct` y `markup_pct` no activos al mismo tiempo;
- unidades explicitas para mm, pliegos, horas, porcentajes y dinero;
- valores marcados como ejemplo cuando no sean tarifas reales.

## Oraculos futuros

Usar tres capas:

- oraculo matematico: formulas simples con resultados esperados;
- invariantes: costos no negativos, totales reconciliados, mas paginas no cuesta igual;
- revision humana: operador o responsable de imprenta valida supuestos.
