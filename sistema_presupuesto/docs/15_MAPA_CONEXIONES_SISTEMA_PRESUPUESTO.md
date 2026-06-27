# Mapa Conexiones Sistema Presupuesto

Documento de conexiones internas actuales del modulo `sistema_presupuesto/`.

Este mapa separa hechos confirmados de inferencias y mantiene el limite con el Editor Offset Visual.

## Vista global

```text
Usuario
  ↓
UI aislada / CLI
  ↓
API o comando interno
  ↓
Validadores y serializadores
  ↓
Motor de calculo
  ↓
Repositorios
  ↓
Storage JSON
  ↓
data/*.json
```

## Mapa backend

```text
api.py
  ↓
CatalogRepository
  ↓
calculation_engine.calculate_quote_from_dict()
  ↓
validators.validate_quote_request()
  ↓
serializers.quote_request_from_dict()
  ↓
production_math.estimate_production()
  ↓
pricing_engine.calculate_pricing()
  ↓
serializers.quote_result_to_dict()
```

Responsabilidades:

- `api.py`: capa HTTP, errores y wiring de repositorios.
- `cli.py`: entrada por linea de comandos.
- `dev_app.py`: servidor aislado para UI de desarrollo.
- `backend/models.py`: modelos internos.
- `backend/validators.py`: validacion de contratos.
- `backend/serializers.py`: conversion entre JSON y dataclasses.
- `backend/calculation_engine.py`: orquestacion pura.
- `backend/production_math.py`: estimacion tecnica.
- `backend/pricing_engine.py`: costos monetarios.
- `backend/storage.py`: persistencia JSON segura.
- `backend/repositories.py`: presupuestos.
- `backend/catalog_repository.py`: catalogos.
- `backend/client_repository.py`: clientes.
- `backend/quote_numbering.py`: numeracion.
- `backend/pdf_generator.py`: documentos.

## Mapa frontend

```text
presupuesto_offset_app.html
  ↓ carga
presupuesto_offset.css
presupuesto_offset.js
  ↓ DOMContentLoaded
init()
  ↓
bindEvents()
  ↓
fetch("/api/sistema-presupuesto/...")
```

Pantalla unica:

- cabecera y estado API;
- formulario de cotizacion;
- panel de resultado;
- historial de presupuestos;
- detalle de presupuesto;
- clientes;
- catalogos.

Eventos principales:

```text
#sp-quote-form submit
  ↓
calculate(false)
  ↓
POST /cotizar

#sp-save-button click
  ↓
calculate(true)
  ↓
POST /cotizar-y-guardar

#sp-budget-search input
  ↓
refreshBudgets()
  ↓
GET /presupuestos?q=...

#sp-update-budget-state click
  ↓
PATCH /presupuestos/<id>/estado

#sp-duplicate-budget click
  ↓
POST /presupuestos/<id>/duplicar

#sp-generate-document click
  ↓
POST /presupuestos/<id>/documento
```

## Mapa API

```text
Cliente HTTP
  ↓
/api/sistema-presupuesto
  ↓
Blueprint sistema_presupuesto_api
  ↓
helpers de repositorio
  ↓
servicios backend internos
```

Agrupacion de endpoints:

```text
Salud
  GET /health

Catalogos
  GET    /catalogos/materiales
  GET    /catalogos/maquinas
  GET    /catalogos/procesos
  GET    /catalogos/<tipo>
  GET    /catalogos/<tipo>/custom
  POST   /catalogos/<tipo>/custom
  PUT    /catalogos/<tipo>/custom/<item_id>
  DELETE /catalogos/<tipo>/custom/<item_id>

Cotizacion
  POST /cotizar
  POST /cotizar-y-guardar

Numeracion
  GET /numeracion

Clientes
  GET    /clientes
  POST   /clientes
  GET    /clientes/<cliente_id>
  PUT    /clientes/<cliente_id>
  DELETE /clientes/<cliente_id>

Presupuestos
  GET   /presupuestos
  GET   /presupuestos/<presupuesto_id>
  PATCH /presupuestos/<presupuesto_id>/estado
  POST  /presupuestos/<presupuesto_id>/duplicar

Documentos
  POST /presupuestos/<presupuesto_id>/documento
  GET  /documentos/<archivo>
```

## Mapa datos

```text
JsonStorage(base_dir)
  ↓
sistema_presupuesto/data/
  ├─ catalogo/
  ├─ clientes/
  ├─ fixtures/
  ├─ pdfs/
  ├─ presupuestos/
  └─ quote_numbering.json
```

Catalogos:

```text
catalogo/materiales_default.json
catalogo/materiales_custom.json
  ↓
CatalogRepository.list_combined("materiales")
  ↓
schema sistema_presupuesto.catalogo.materiales
```

La misma regla aplica a `maquinas` y `procesos`.

Presupuestos:

```text
POST /cotizar-y-guardar
  ↓
BudgetRepository.save_calculated_budget()
  ↓
presupuestos/psp_YYYYMMDD_<12hex>.json
```

Clientes:

```text
POST /clientes
  ↓
ClientRepository.create_client()
  ↓
clientes/cli_YYYYMMDD_<12hex>.json
```

Documentos:

```text
POST /presupuestos/<id>/documento
  ↓
CommercialDocumentGenerator
  ↓
pdfs/<numero_comercial|presupuesto_id>.pdf|html
```

## Mapa tests

```text
tests/
  ↓
contratos y validadores
  calculo tecnico
  calculo monetario
  storage
  repositorios
  API
  CLI
  frontend estatico
  integracion app principal
```

Cobertura por area:

- `test_validators.py`: contrato de entrada y errores.
- `test_serializers.py`: conversion a `Decimal`.
- `test_production_math.py`: sangrado, unidades, merma, revistas.
- `test_pricing_engine.py`: subtotales, margen/markup, impuestos.
- `test_calculation_engine.py`: flujo completo del motor.
- `test_storage.py`: lectura/escritura JSON y path traversal.
- `test_repositories.py`: presupuestos, legacy, filtros, estado, duplicacion.
- `test_catalog_repository.py`: catalogos default/custom.
- `test_client_repository.py`: clientes.
- `test_quote_numbering.py`: numeracion anual.
- `test_pdf_generator.py`: PDF/HTML y sanitizacion.
- `test_cli.py`: comandos internos.
- `test_api.py`: endpoints.
- `test_frontend_files.py`: presencia y aislamiento de frontend.
- `test_main_app_integration.py`: integracion basica con app principal.

## Dependencias internas

```text
api.py
  ├─ backend.calculation_engine
  ├─ backend.catalog_repository
  ├─ backend.client_repository
  ├─ backend.pdf_generator
  ├─ backend.quote_numbering
  ├─ backend.repositories
  └─ backend.storage

calculation_engine.py
  ├─ validators.py
  ├─ serializers.py
  ├─ production_math.py
  └─ pricing_engine.py

repositories.py
  ├─ quote_numbering.py
  ├─ serializers.py
  └─ storage.py

pdf_generator.py
  ├─ catalog_repository.py
  ├─ client_repository.py
  └─ storage.py
```

## Diagramas de flujo

### Cotizacion simple

```text
Usuario
  ↓
UI
  ↓
POST /api/sistema-presupuesto/cotizar
  ↓
CatalogRepository
  ↓
CalculationEngine
  ↓
QuoteResult
  ↓
Respuesta JSON
  ↓
Render resultado
```

### Guardado

```text
Usuario
  ↓
UI
  ↓
POST /api/sistema-presupuesto/cotizar-y-guardar
  ↓
CalculationEngine
  ↓
BudgetRepository
  ↓
QuoteNumbering
  ↓
JsonStorage
  ↓
data/presupuestos/<id>.json
```

### Catalogos

```text
Usuario
  ↓
UI Catalogos
  ↓
API Catalogos
  ↓
CatalogRepository
  ↓
Default JSON + Custom JSON
  ↓
Catalogo combinado
```

### Clientes

```text
Usuario
  ↓
UI Clientes
  ↓
API Clientes
  ↓
ClientRepository
  ↓
JsonStorage
  ↓
data/clientes/<id>.json
```

### Documento comercial

```text
Usuario
  ↓
Presupuesto abierto
  ↓
POST /documento
  ↓
BudgetRepository
  ↓
CommercialDocumentGenerator
  ↓
data/pdfs/<archivo>
  ↓
GET /documentos/<archivo>
```

### Futuro Motor de Produccion

```text
Presupuesto aceptado
  ↓
BudgetRecord
  ↓
Adaptador read-only
  ↓
ProductionOrderRequest
  ↓
Motor de Produccion
  ↓
ProductionPlanResult
```

Este flujo futuro es una propuesta. No esta implementado actualmente.

## Superficies de compatibilidad

No cambiar sin fase aprobada:

- `schema` y `schema_version` de `QuoteRequest`, `QuoteResult`, `BudgetRecord`;
- formato `psp_YYYYMMDD_<12hex>`;
- formato `PRES-YYYY-000001`;
- endpoints bajo `/api/sistema-presupuesto`;
- estructura `data/catalogo/*_default.json` y `*_custom.json`;
- campos principales de `request` y `result` persistidos;
- IDs frontend `#sp-*` usados por JS.

## Conexiones que NO existen actualmente

No hay conexion funcional actual con:

- Editor Offset Visual;
- `layout_constructor.json`;
- jobs del editor;
- `routes.py`;
- motores `step_repeat` o `nesting`;
- `montaje_offset_inteligente.py`;
- base de datos externa;
- autenticacion/usuarios;
- ordenes de produccion.
