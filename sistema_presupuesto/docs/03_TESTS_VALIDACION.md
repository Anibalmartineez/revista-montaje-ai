# Tests y Validacion

Este documento define la estrategia inicial de validacion para `sistema_presupuesto/`.

No hay tests implementados en Fase 1.

## Principios

- Probar primero funciones puras.
- No depender del Editor Offset Visual.
- No depender de Flask para validar formulas.
- Usar fixtures con numeros esperados.
- Separar tests de contratos, calculos y persistencia.

## Casos reales minimos

### Volante simple

- Cantidad: 1000.
- Formato final: 148 x 210 mm.
- Sangrado: 3 mm.
- Colores: `4/0`.
- Validar formas por pliego, pliegos netos, merma, chapas y costo de papel.

### Tarjeta

- Cantidad: 500.
- Formato final: 90 x 50 mm.
- Sangrado: 3 mm.
- Colores: `4/4`.
- Validar que el dorso no duplique papel, pero si afecte chapas y pasadas.

### Revista

- Cantidad: 1000.
- Formato cerrado: 210 x 297 mm.
- Paginas: 32.
- Encuadernacion: caballete.
- Validar que paginas y encuadernacion sean obligatorias y que las paginas sean multiplo de 4.

### Folleto diptico

- Formato abierto: 297 x 210 mm.
- Formato cerrado: 148.5 x 210 mm.
- Paneles: 2.
- Pliegues: 1.
- Validar que la impresion use formato abierto.

### Folleto triptico

- Formato abierto: 297 x 210 mm.
- Paneles: 3.
- Pliegues: 2.
- Validar que no se multiplique la tirada por cantidad de paneles.

### Frente/dorso

- Colores: `4/1`.
- Validar chapas esperadas, pasadas y caras activas.

### Trabajo con terminacion

- Laminado por metro cuadrado.
- Guillotina fija.
- Redondeado por unidad.
- Validar subtotales por modo de cobro.

### Trabajo con merma

- Tirada alta.
- Validar merma porcentual, merma de arranque y redondeo hacia arriba.

## Tests automaticos futuros

Nombres sugeridos:

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
