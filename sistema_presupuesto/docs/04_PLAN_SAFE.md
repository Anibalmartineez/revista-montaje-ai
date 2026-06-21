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
- diferenciar errores bloqueantes de advertencias;
- serializar JSON validado a modelos internos;
- preparar campos numericos para `Decimal`.

Regla:

- sin Flask;
- sin Editor Offset Visual;
- sin persistencia compleja.

Entregables:

- `backend/__init__.py`
- `backend/models.py`
- `backend/validators.py`
- `backend/errors.py`
- `backend/serializers.py`
- `tests/test_validators.py`
- `tests/test_serializers.py`

## Fase 4 - Motor determinista

Objetivo:

- implementar calculo tecnico;
- implementar calculo monetario con `Decimal`;
- emitir desglose y advertencias.

Validacion:

- tests unitarios de formulas;
- reconciliacion de subtotales;
- pruebas de margen vs markup.

Entregables:

- `backend/defaults.py`
- `backend/production_math.py`
- `backend/pricing_engine.py`
- `backend/calculation_engine.py`
- `tests/test_production_math.py`
- `tests/test_pricing_engine.py`
- `tests/test_calculation_engine.py`

Supuestos controlados:

- imposicion por grilla no rotada;
- revista aproximada por factor `paginas / 4`;
- costos de catalogo ficticios;
- CTP con costo de ejemplo;
- sin persistencia, rutas, UI ni integracion con Editor.

## Fase 5 - Persistencia JSON interna

Objetivo:

- guardar catalogos y presupuestos dentro de `sistema_presupuesto/data/`;
- versionar presupuestos;
- evitar sobrescribir presupuestos aceptados.
- cargar catalogos default;
- leer presupuesto guardado por ID;
- listar presupuestos guardados;
- bloquear path traversal.

No usar `static/constructor_offset_jobs/`.

Entregables:

- `backend/storage.py`
- `backend/catalog_repository.py`
- `backend/repositories.py`
- `tests/test_storage.py`
- `tests/test_catalog_repository.py`
- `tests/test_repositories.py`

Fuera de alcance:

- base de datos;
- rutas Flask;
- UI;
- integracion con Editor Offset Visual.

## Fase 6 - CLI interno de prueba

Objetivo:

- calcular presupuestos desde fixtures JSON;
- calcular y guardar presupuestos;
- listar presupuestos guardados;
- ver presupuesto por ID;
- exponer salida JSON legible para pruebas internas.

Entregables:

- `cli.py`
- `tests/test_cli.py`
- `docs/06_USO_CLI.md`

Fuera de alcance:

- rutas Flask;
- UI;
- integracion con Editor Offset Visual.

## Fase 7 - API Flask aislada / Blueprint no registrado

Objetivo:

- crear Blueprint Flask importable;
- no registrar el Blueprint en la app principal;
- exponer endpoints internos para catalogos, cotizacion y presupuestos;
- probar con una app Flask temporal.

Entregables:

- `api.py`
- `tests/test_api.py`
- `docs/07_API_INTERNA.md`

Fuera de alcance:

- tocar `routes.py`;
- registrar Blueprint;
- UI;
- integracion con Editor Offset Visual.

## Fase 8 - UI aislada

Objetivo:

- crear pantalla de parametros;
- crear pantalla de presupuesto;
- mostrar desglose;
- preparar vista imprimible.

Regla:

- usar `frontend/` dentro del modulo;
- no tocar templates, CSS ni JS del Editor Offset Visual.

## Fase 9 - Registro API en app principal, si se aprueba

Objetivo:

- evaluar endpoints propios bajo `/sistema_presupuesto`;
- mantener separacion con `routes.py` del Editor.

No crear rutas `/editor_offset*`.

## Fase 10 - Integracion futura por adaptador

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
