# Auditoria Sistema Actual

Documento de auditoria read-only del modulo `sistema_presupuesto/`.

Fecha de auditoria: 2026-06-27.

Rama de trabajo: `audit/sistema-presupuesto-mapa-completo`.

Alcance: inspeccion estatica de archivos Python, frontend, datos, docs y tests dentro de `sistema_presupuesto/`, con apoyo de subagentes especializados.

Limites respetados:

- no se modifico codigo funcional;
- no se modifico Editor Offset Visual;
- no se modifico `routes.py`;
- no se modifico logica de la app principal;
- no se implementaron nuevas funciones;
- no se refactorizo codigo.

## Resumen ejecutivo

`sistema_presupuesto/` es un modulo ya operativo para cotizacion interna offset. Tiene API Flask propia, CLI, app de desarrollo aislada, UI frontend propia, persistencia JSON local, repositorios de presupuestos/clientes/catalogos, numeracion comercial, generacion de documento comercial y tests especificos.

El nucleo esta razonablemente separado:

```text
QuoteRequest JSON
  -> validadores
  -> dataclasses internas
  -> calculo tecnico
  -> calculo monetario
  -> QuoteResult
  -> BudgetRecord opcional
```

El sistema todavia no es un Motor de Produccion industrial. La imposicion actual es una aproximacion por grilla no rotada o `formas_por_pliego_manual`, los catalogos declaran valores ficticios de diseno y el resultado emite warnings como `GRID_IMPOSITION_APPROXIMATION` y `NO_REAL_TARIFFS`.

Riesgos principales:

- numeracion comercial sin lock y posible duplicacion si falta `data/quote_numbering.json`;
- procesos custom con `modo_cobro` no implementado pueden terminar con cantidad `0`;
- pieza que no entra en pliego puede cotizarse con warning y `units = 1`;
- administracion de catalogos/clientes/presupuestos no tiene autenticacion propia;
- documentacion 00-13 mezcla estado historico y estado actual.

## Estructura actual del modulo

```text
sistema_presupuesto/
  __init__.py
  AGENTS.md
  README.md
  api.py
  cli.py
  dev_app.py
  backend/
    calculation_engine.py
    catalog_repository.py
    client_repository.py
    defaults.py
    errors.py
    models.py
    pdf_generator.py
    pricing_engine.py
    production_math.py
    quote_numbering.py
    repositories.py
    serializers.py
    storage.py
    validators.py
  data/
    catalogo/
    clientes/
    fixtures/
    pdfs/
    presupuestos/
  docs/
    00_CONTEXTO.md ... 13_HISTORIAL_Y_DUPLICACION.md
    14_AUDITORIA_SISTEMA_ACTUAL.md
  frontend/
    templates/presupuesto_offset_app.html
    static/js/presupuesto_offset.js
    static/css/presupuesto_offset.css
  tests/
    test_*.py
```

## Responsabilidades por archivo

### Entrada HTTP y CLI

- `api.py`: define el Blueprint `sistema_presupuesto_api` con prefijo `/api/sistema-presupuesto`. Expone health, catalogos, clientes, cotizacion, guardado, presupuestos, estado, duplicacion, numeracion y documentos.
- `cli.py`: CLI interno con comandos `calcular`, `calcular-y-guardar`, `listar` y `ver`.
- `dev_app.py`: app Flask aislada para desarrollo, con UI en `/sistema-presupuesto-ui` y assets propios.

### Dominio, contratos y calculo

- `backend/models.py`: dataclasses internas: `QuoteRequest`, `ProductionEstimate`, `PricingResult`, `QuoteResult`, `ValidationReport`, entre otras.
- `backend/validators.py`: validacion de `QuoteRequest`, moneda, medidas, tipos de producto, referencias de catalogos, margen vs markup e impuestos.
- `backend/serializers.py`: conversion JSON <-> modelos internos con `Decimal`, y serializacion de `QuoteResult`.
- `backend/calculation_engine.py`: orquestador puro del calculo.
- `backend/production_math.py`: calculo tecnico inicial: sangrado, unidades por pliego, factor paginas, chapas, pasadas, merma, impresiones y horas.
- `backend/pricing_engine.py`: calculo monetario: papel, CTP, maquina, procesos, margen/markup, impuestos y precio unitario.
- `backend/defaults.py`: schemas, versiones y constantes como `CTP_COST_PER_PLATE_EXAMPLE`.
- `backend/errors.py`: jerarquia de errores controlados del modulo.

### Persistencia y repositorios

- `backend/storage.py`: adaptador JSON local bajo `sistema_presupuesto/data/`, con bloqueo de rutas absolutas y path traversal.
- `backend/repositories.py`: `BudgetRepository`, guarda, lista, lee, cambia estado y duplica presupuestos.
- `backend/catalog_repository.py`: carga y administra catalogos default/custom; el custom sobrescribe al default por `id` en la vista combinada.
- `backend/client_repository.py`: CRUD de clientes JSON locales.
- `backend/quote_numbering.py`: genera numeracion comercial `PRES-YYYY-000001`.
- `backend/pdf_generator.py`: genera documento comercial PDF con ReportLab o HTML fallback.

### Frontend

- `frontend/templates/presupuesto_offset_app.html`: pantalla unica del sistema.
- `frontend/static/js/presupuesto_offset.js`: IIFE con estado interno, eventos, llamadas API, render de resultados, presupuestos, clientes y catalogos.
- `frontend/static/css/presupuesto_offset.css`: estilos aislados con prefijo `.sp-*`.

### Datos

- `data/catalogo/*_default.json`: catalogos base versionados de materiales, maquinas y procesos.
- `data/catalogo/*_custom.json`: catalogos editables por API/UI.
- `data/fixtures/quote_request_*.json`: fixtures de entrada.
- `data/fixtures/quote_response_example.json`: fixture/documento legacy de salida conceptual, no equivalente exacto a la salida viva actual.
- `data/presupuestos/*.json`: presupuestos guardados.
- `data/pdfs/*`: documentos generados.
- `data/clientes/`: clientes JSON locales.

### Tests

Hay tests para API, CLI, storage, repositorios, catalogos, clientes, validadores, serializadores, calculo, pricing, produccion, PDF, numeracion, frontend estatico e integracion basica con app principal.

## Flujo actual de cotizacion

```text
Usuario
  ↓
UI aislada / CLI
  ↓
QuoteRequest JSON
  ↓
api.py o cli.py
  ↓
CatalogRepository.load_all_combined()
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
  ↓
Respuesta JSON
```

Hechos confirmados:

- el backend recalcula siempre;
- el frontend no envia totales como fuente de verdad;
- el contrato vivo usa `schema: sistema_presupuesto.quote_request` y `schema_version: 1`;
- los numeros decimales viajan como strings o enteros, no floats.

Inferencias:

- el motor actual sirve para cotizacion inicial y trazabilidad, no para compromiso productivo final;
- `QuoteResult.produccion` puede alimentar un futuro motor, pero no reemplaza una orden de produccion.

## Flujo actual de guardado

```text
POST /api/sistema-presupuesto/cotizar-y-guardar
  ↓
_request_json()
  ↓
CatalogRepository + calculate_quote_from_dict()
  ↓
BudgetRepository.save_calculated_budget()
  ↓
QuoteNumbering.next_number()
  ↓
JsonStorage.write_json("presupuestos/<id>.json")
  ↓
Respuesta con presupuesto_id, numero_comercial y record
```

Campos principales de `BudgetRecord`:

- `schema`;
- `schema_version`;
- `presupuesto_id`;
- `numero_comercial` en registros nuevos;
- `version`;
- `estado`;
- `created_at`;
- `updated_at`;
- `request`;
- `result`;
- `duplicado_de` opcional;
- `observaciones` opcional.

Compatibilidad confirmada:

- presupuestos sin `numero_comercial` siguen cargando;
- presupuestos sin `estado` o con `estado: calculado` se presentan como `borrador` en resumen;
- no se sobrescribe un presupuesto existente por defecto.

Riesgo confirmado:

- si `data/quote_numbering.json` no existe pero ya hay presupuestos con `numero_comercial`, la proxima numeracion puede reiniciar desde `PRES-YYYY-000001`.

## Flujo actual de PDF

```text
Usuario abre presupuesto guardado
  ↓
POST /api/sistema-presupuesto/presupuestos/<presupuesto_id>/documento
  ↓
BudgetRepository.get_budget()
  ↓
CommercialDocumentGenerator.generate()
  ↓
data/pdfs/<numero_o_id>.pdf|html
  ↓
GET /api/sistema-presupuesto/documentos/<archivo>
```

Hechos confirmados:

- el documento se genera desde un presupuesto guardado;
- no recalcula el presupuesto para emitir documento;
- usa PDF si ReportLab esta disponible;
- usa HTML imprimible como fallback;
- sanitiza nombre de archivo;
- la descarga valida que el archivo este bajo `data/pdfs/`.

Limitaciones:

- no hay plantillas comerciales configurables;
- no hay historial de documentos emitidos;
- las pruebas actuales verifican formato minimo, no contenido semantico completo.

## Flujo actual de clientes

```text
UI Clientes
  ↓
/api/sistema-presupuesto/clientes
  ↓
ClientRepository
  ↓
data/clientes/<cliente_id>.json
```

Endpoints:

- `GET /clientes`;
- `POST /clientes`;
- `GET /clientes/<cliente_id>`;
- `PUT /clientes/<cliente_id>`;
- `DELETE /clientes/<cliente_id>`.

Contrato de cliente:

- `cliente_id` generado por backend;
- `nombre` obligatorio;
- `empresa`, `telefono`, `email`, `ruc`, `notas` opcionales;
- `email` con validacion basica si existe;
- `created_at` y `updated_at` generados por backend.

Limitacion importante:

- el CRUD de clientes existe, pero la cotizacion UI todavia usa cliente fijo `Cliente UI aislada`; no hay asociacion formal cliente-presupuesto.

## Flujo actual de catalogos

```text
UI Catalogos
  ↓
/api/sistema-presupuesto/catalogos/<tipo>
  ↓
CatalogRepository
  ↓
default + custom
  ↓
catalogo combinado
```

Tipos soportados:

- `materiales`;
- `maquinas`;
- `procesos`.

Reglas:

- los default no se editan por API/UI;
- los custom se guardan en `data/catalogo/*_custom.json`;
- si un custom usa el mismo `id` que un default, sobrescribe al default en el catalogo combinado;
- el catalogo combinado agrega `origen_catalogo`.

Riesgos:

- no hay autenticacion ni permisos;
- la validacion profunda aplica al custom, pero los default se validan superficialmente al cargar;
- `modo_cobro` desconocido o `por_kg` puede producir cantidad `0` en pricing.

## Flujo actual de historial y duplicacion

```text
GET /api/sistema-presupuesto/presupuestos
  ↓
BudgetRepository.list_budgets(q, estado)
  ↓
resumen ordenado por created_at descendente
```

Filtros:

- `q`: busca por `presupuesto_id`, `numero_comercial`, producto u observaciones;
- `estado`: filtra por estado permitido.

Estados permitidos:

- `borrador`;
- `enviado`;
- `aceptado`;
- `rechazado`;
- `vencido`.

Duplicacion:

```text
POST /api/sistema-presupuesto/presupuestos/<presupuesto_id>/duplicar
  ↓
copia request/result
  ↓
genera nuevo presupuesto_id
  ↓
genera nuevo numero_comercial
  ↓
estado inicial borrador
  ↓
duplicado_de = original
```

Limitaciones:

- duplicar no recalcula cantidades ni tarifas;
- solo acepta patch `observaciones`;
- no reutiliza documentos generados.

## Endpoints actuales

Base:

```text
/api/sistema-presupuesto
```

Listado consolidado:

```text
GET    /health
GET    /catalogos/materiales
GET    /catalogos/maquinas
GET    /catalogos/procesos
GET    /catalogos/<tipo>
GET    /catalogos/<tipo>/custom
POST   /catalogos/<tipo>/custom
PUT    /catalogos/<tipo>/custom/<item_id>
DELETE /catalogos/<tipo>/custom/<item_id>
POST   /cotizar
POST   /cotizar-y-guardar
GET    /numeracion
GET    /clientes
POST   /clientes
GET    /clientes/<cliente_id>
PUT    /clientes/<cliente_id>
DELETE /clientes/<cliente_id>
GET    /presupuestos
GET    /presupuestos/<presupuesto_id>
PATCH  /presupuestos/<presupuesto_id>/estado
POST   /presupuestos/<presupuesto_id>/duplicar
POST   /presupuestos/<presupuesto_id>/documento
GET    /documentos/<archivo>
```

## Llamadas frontend/backend

El frontend usa `API_BASE = "/api/sistema-presupuesto"`.

Eventos principales:

- submit de `#sp-quote-form` llama `POST /cotizar`;
- boton `#sp-save-button` llama `POST /cotizar-y-guardar`;
- carga inicial llama `GET /health`, `GET /catalogos/*`, `GET /presupuestos`, `GET /clientes`;
- busqueda y filtro llaman `GET /presupuestos?q=&estado=`;
- detalle llama `GET /presupuestos/<id>`;
- estado llama `PATCH /presupuestos/<id>/estado`;
- duplicacion llama `POST /presupuestos/<id>/duplicar`;
- documento llama `POST /presupuestos/<id>/documento` y abre `GET /documentos/<archivo>`;
- clientes usan CRUD bajo `/clientes`;
- catalogos custom usan CRUD bajo `/catalogos/<tipo>/custom`.

## Riesgos actuales

### Alto

- `QuoteNumbering.next_number()` no tiene lock ni reconciliacion con presupuestos existentes.
- Si falta `data/quote_numbering.json`, puede repetirse un `numero_comercial` ya usado.
- `modo_cobro` desconocido o `por_kg` puede cotizar procesos con cantidad `0`.

### Medio alto

- Si la pieza no entra en pliego, el motor agrega warning pero sigue con `units = 1`.
- Los calculos de produccion son aproximados y no industriales.
- No hay autenticacion/permisos para modificar catalogos custom si la API queda expuesta.

### Medio

- `duplicar_presupuesto()` usa JSON silencioso y puede tratar JSON malformado como body vacio.
- CLI no captura `ValueError` para JSON raiz no objeto.
- La semantica de `costos.impuestos[].base` no altera el calculo; se calcula sobre `precio_antes_impuestos`.
- `quote_response_example.json` no coincide con la salida viva actual.
- Frontend monolitico y acoplado a IDs `#sp-*`.

## Deudas tecnicas

- Documentacion 00-13 con textos de fases antiguas.
- Falta documento de estado actual posterior a Fase 10, cubierto por esta auditoria.
- Falta politica formal de datos generados.
- Falta asociacion real cliente-presupuesto.
- Falta validacion semantica completa de PDF/documento.
- Falta Playwright o prueba real del flujo UI.
- Falta politica de concurrencia para JSON local.
- Falta schema formal de orden de produccion.

## Conclusiones

El modulo esta en buen estado para seguir evolucionando de forma SAFE. La separacion actual permite construir un Motor de Produccion como capa nueva, alimentada por `BudgetRecord`, `QuoteRequest`, `QuoteResult` y catalogos, sin tocar todavia el Editor Offset Visual.

No conviene convertir `production_math.py` en motor industrial. Ese archivo debe seguir siendo el motor tecnico inicial de cotizacion hasta que existan contratos y pruebas para una capa productiva nueva.

La siguiente fase recomendada es estabilizacion de contratos y riesgos de datos antes de implementar nuevas funciones productivas.
