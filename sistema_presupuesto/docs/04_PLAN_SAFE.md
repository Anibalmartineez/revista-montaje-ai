# Plan SAFE

Plan de evolucion por fases para `sistema_presupuesto/`.

## Fase 1 - Estructura y documentacion

Objetivo:

- crear carpeta aislada;
- crear `AGENTS.md`;
- crear `README.md`;
- crear documentos base;
- crear carpetas para backend, frontend, datos y tests.

Fuera de alcance:

- codigo funcional;
- rutas Flask;
- API;
- motor de calculo;
- UI activa;
- integracion con Editor Offset Visual.

Estado: en implementacion inicial.

## Fase 2 - Contratos y fixtures

Objetivo:

- cerrar `QuoteRequest`;
- cerrar `QuoteResult`;
- cerrar `BudgetRecord`;
- definir catalogos iniciales;
- crear fixtures numericos para volante, tarjeta, revista, diptico, triptico, frente/dorso, terminaciones y merma.

Entregables:

- `data/catalogo/materiales_default.json`
- `data/catalogo/maquinas_default.json`
- `data/catalogo/procesos_default.json`
- `data/fixtures/quote_request_volante.json`
- `data/fixtures/quote_request_tarjeta.json`
- `data/fixtures/quote_request_revista.json`
- `data/fixtures/quote_request_diptico.json`
- `data/fixtures/quote_request_triptico.json`
- `data/fixtures/quote_response_example.json`

Validacion:

- revision manual de contratos;
- `git diff --check`;
- validacion de JSON en una fase posterior o con herramienta puntual si se autoriza;
- aprobacion del usuario antes de motor.

Fuera de alcance:

- motor funcional;
- rutas Flask;
- UI;
- integracion con Editor Offset Visual;
- persistencia real de presupuestos.

## Fase 3 - Modelos y validadores

Objetivo:

- implementar modelos puros;
- validar cantidades, medidas, moneda, colores, materiales, maquinas, procesos y estados.

Regla:

- sin Flask;
- sin Editor Offset Visual;
- sin persistencia compleja.

## Fase 4 - Motor determinista

Objetivo:

- implementar calculo tecnico;
- implementar calculo monetario con `Decimal`;
- emitir desglose y advertencias.

Validacion:

- tests unitarios de formulas;
- reconciliacion de subtotales;
- pruebas de margen vs markup.

## Fase 5 - Persistencia JSON interna

Objetivo:

- guardar catalogos y presupuestos dentro de `sistema_presupuesto/data/`;
- versionar presupuestos;
- evitar sobrescribir presupuestos aceptados.

No usar `static/constructor_offset_jobs/`.

## Fase 6 - UI aislada

Objetivo:

- crear pantalla de parametros;
- crear pantalla de presupuesto;
- mostrar desglose;
- preparar vista imprimible.

Regla:

- usar `frontend/` dentro del modulo;
- no tocar templates, CSS ni JS del Editor Offset Visual.

## Fase 7 - API o Blueprint propio

Objetivo:

- evaluar endpoints propios bajo `/sistema_presupuesto`;
- mantener separacion con `routes.py` del Editor.

No crear rutas `/editor_offset*`.

## Fase 8 - Integracion futura por adaptador

Objetivo:

- crear adaptador read-only desde snapshots del Editor Offset Visual;
- no mutar `layout_constructor.json`;
- no depender de internals del Editor sin contrato documentado.

Requiere aprobacion explicita.

## Criterios de exito

- El modulo puede entenderse sin leer el Editor.
- Los calculos son reproducibles.
- Los contratos son versionados.
- Las advertencias son visibles.
- La integracion futura queda aislada por adaptador.

## Criterios de bloqueo

Bloquear cambios si:

- se requiere modificar el Editor sin aprobacion;
- se desconoce la semantica de una medida critica;
- faltan tarifas obligatorias;
- no hay tests para cambio de formula;
- se intenta mezclar margen y markup sin regla explicita.
