# Plan Motor Produccion

Plan SAFE para un futuro Motor de Produccion dentro de `sistema_presupuesto/`.

Estado: propuesta arquitectonica. No implementado.

Limite estricto: sin integrar todavia con Editor Offset Visual.

## Objetivo del motor

Transformar datos comerciales y tecnicos de un presupuesto aprobado en un plan productivo auditable.

El motor debe responder:

- que se va a producir;
- en que formato;
- con que papel;
- en que maquina;
- cuantas chapas;
- cuantas pasadas;
- cuanta merma;
- que terminaciones;
- que costos y rentabilidad quedan;
- que advertencias tecnicas existen;
- que recomendaciones conviene mostrar al operador.

## No objetivos

- No reemplazar el Editor Offset Visual.
- No leer ni escribir `layout_constructor.json`.
- No crear jobs del Editor Offset Visual.
- No llamar motores `step_repeat`, `nesting` ni `montaje_offset_inteligente.py`.
- No disparar produccion automaticamente por `estado=aceptado`.
- No persistir ordenes productivas antes de cerrar contrato.

## Arquitectura propuesta

Crear una capa nueva hermana del backend actual:

```text
sistema_presupuesto/
  production/
    __init__.py
    models.py
    contracts.py
    serializers.py
    validators.py
    quote_adapter.py
    production_engine.py
    product_profiles.py
    sheet_optimizer.py
    imposition_engine.py
    machine_selector.py
    plate_engine.py
    pass_engine.py
    paper_engine.py
    ink_engine.py
    finishing_engine.py
    profitability_engine.py
    recommendation_engine.py
```

Flujo:

```text
BudgetRecord
  ↓
quote_adapter
  ↓
ProductionOrderRequest
  ↓
production_engine
  ↓
submotores
  ↓
ProductionPlanResult
```

## Modulos sugeridos

### product_profiles

Responsabilidad:

- normalizar tipos de producto;
- definir perfiles por `volante`, `tarjeta`, `revista`, `folleto_diptico`, `folleto_triptico`;
- declarar requisitos minimos por tipo.

Entradas:

- `QuoteRequest.producto`;
- reglas de negocio por tipo.

Salidas:

- perfil tecnico normalizado;
- advertencias de datos faltantes.

### sheet_optimizer

Responsabilidad:

- calcular alternativas de uso de pliego;
- evaluar orientacion, grilla, margen util y formas;
- comparar contra `formas_por_pliego_manual`.

No debe:

- asumir nesting real si no esta implementado;
- usar datos del Editor Offset Visual sin adaptador aprobado.

### imposition_engine

Responsabilidad:

- producir una imposicion conceptual para costos y planificacion;
- separar `manual`, `grid`, `external_snapshot` y futuros modos.

Limite:

- no debe reemplazar la imposicion visual del Editor Offset Visual.

### machine_selector

Responsabilidad:

- elegir maquina o validar maquina solicitada;
- considerar formato minimo/maximo, cuerpos, rendimiento, costos y disponibilidad futura.

Entrada:

- catalogo de maquinas combinado;
- perfil de producto;
- necesidades de pliego/pasadas.

### plate_engine

Responsabilidad:

- calcular chapas por forma, cara y color;
- distinguir frente/dorso;
- preparar datos para CTP.

Debe emitir warnings si:

- colores o caras son ambiguos;
- se usa aproximacion de revista;
- faltan datos de tinta especial.

### pass_engine

Responsabilidad:

- calcular pasadas e impresiones;
- considerar cuerpos de maquina, frente/dorso y setup;
- separar pasadas tecnicas de impresiones fisicas.

### paper_engine

Responsabilidad:

- calcular papel bruto, bueno y merma;
- soportar compra por pliego o por kg;
- preparar requerimientos de material.

Debe contemplar:

- pliego base vs pliego util;
- sangrado;
- merma por arranque;
- merma porcentual;
- merma por terminacion;
- compra minima futura.

### ink_engine

Responsabilidad:

- estimar consumo de tinta;
- separar modelo simplificado de modelo por area/cobertura;
- declarar fuente y precision.

Estado actual:

- no existe calculo de tinta productivo en el motor actual.

### finishing_engine

Responsabilidad:

- convertir `procesos_ids` en pasos productivos;
- calcular cantidad por modo de cobro;
- advertir modos no soportados;
- diferenciar terminaciones internas y tercerizadas en una fase futura.

### profitability_engine

Responsabilidad:

- comparar costo tecnico, precio final, margen, markup y rentabilidad;
- detectar presupuestos con margen insuficiente;
- explicar impacto de cada decision productiva.

### recommendation_engine

Responsabilidad:

- recomendar alternativas al operador;
- sugerir maquina, pliego o formato mas conveniente;
- marcar riesgos tecnicos o comerciales.

No debe:

- modificar presupuestos automaticamente;
- generar ordenes sin aprobacion.

## Contratos de entrada

### ProductionOrderRequest

Contrato propuesto:

```json
{
  "schema": "sistema_presupuesto.production_order_request",
  "schema_version": 1,
  "source": {
    "type": "budget_record",
    "presupuesto_id": "psp_YYYYMMDD_abcdef123456",
    "numero_comercial": "PRES-2026-000001"
  },
  "cliente": {
    "cliente_id": null,
    "nombre": "Cliente"
  },
  "producto": {},
  "produccion": {},
  "costos": {},
  "catalogos": {
    "material_id": "couche_150",
    "maquina_id": "offset_4_colores",
    "procesos_ids": []
  },
  "constraints": {
    "allow_approximation": true,
    "require_fit": false,
    "allow_example_tariffs": false
  }
}
```

Campos obligatorios propuestos:

- `schema`;
- `schema_version`;
- `source.type`;
- `source.presupuesto_id`;
- `producto`;
- `produccion`;
- `costos`;
- `catalogos`.

Campos opcionales:

- `numero_comercial`;
- `cliente_id`;
- `constraints`.

### Fuente desde presupuesto

El input inicial debe generarse desde:

- `BudgetRecord.request`;
- `BudgetRecord.result`;
- catalogos combinados vigentes o snapshot de catalogos, segun decision futura.

Pregunta abierta:

- si el plan productivo debe usar catalogos vigentes al momento de generar produccion o snapshot historico del presupuesto.

## Contratos de salida

### ProductionPlanResult

Contrato propuesto:

```json
{
  "schema": "sistema_presupuesto.production_plan_result",
  "schema_version": 1,
  "ok": true,
  "source": {
    "presupuesto_id": "psp_YYYYMMDD_abcdef123456",
    "numero_comercial": "PRES-2026-000001"
  },
  "plan": {
    "product_profile": {},
    "sheet_plan": {},
    "imposition_plan": {},
    "machine_plan": {},
    "plate_plan": {},
    "pass_plan": {},
    "paper_plan": {},
    "ink_plan": {},
    "finishing_plan": {},
    "profitability": {},
    "recommendations": []
  },
  "warnings": [],
  "blocking_issues": []
}
```

Reglas:

- `warnings` no bloquean necesariamente;
- `blocking_issues` impiden emitir una orden productiva;
- todo calculo debe declarar unidad, fuente y precision.

## Integracion con motor de costos actual

El motor actual aporta:

- `QuoteRequest`: contrato de entrada comercial/tecnico;
- `ProductionEstimate`: estimacion inicial de produccion;
- `PricingResult`: resultado monetario;
- `QuoteResult`: salida auditable;
- catalogos: materiales, maquinas y procesos;
- warnings existentes.

El Motor de Produccion no debe alterar `QuoteResult`. Debe consumirlo y producir un resultado propio.

```text
calculation_engine.py
  ↓
QuoteResult
  ↓
production.quote_adapter
  ↓
ProductionOrderRequest
```

## Fases de implementacion

### Fase 1 - Contrato documental

Crear solo docs y fixtures conceptuales.

No codigo funcional.

Entregables:

- contrato `ProductionOrderRequest`;
- contrato `ProductionPlanResult`;
- fixtures positivos y negativos;
- lista de warnings/bloqueos.

### Fase 2 - Modelos puros

Agregar dataclasses en `production/models.py`.

Sin API.
Sin persistencia.
Sin UI.

Tests:

- serializacion;
- validacion;
- compatibilidad de schema.

### Fase 3 - Adaptador desde presupuesto

Crear `quote_adapter.py`.

Entrada:

- `BudgetRecord`;
- catalogos;
- constraints.

Salida:

- `ProductionOrderRequest`.

Debe emitir warnings si:

- presupuesto usa tarifas de ejemplo;
- imposicion fue grilla no rotada;
- revista usa aproximacion;
- falta cliente formal;
- falta snapshot de catalogos.

### Fase 4 - Submotores puros

Implementar submotores sin efectos secundarios:

- `product_profiles`;
- `sheet_optimizer`;
- `imposition_engine`;
- `machine_selector`;
- `plate_engine`;
- `pass_engine`;
- `paper_engine`;
- `ink_engine`;
- `finishing_engine`;
- `profitability_engine`;
- `recommendation_engine`.

### Fase 5 - Orquestador

Implementar `production_engine.py`.

Debe:

- llamar submotores;
- unir warnings;
- separar bloqueos de advertencias;
- devolver `ProductionPlanResult`.

### Fase 6 - Persistencia opcional

Solo despues de validar motor puro.

Propuesta:

```text
data/produccion/<production_order_id>.json
```

Reglas:

- no sobrescribir ordenes cerradas;
- schema versionado;
- estado productivo separado del estado comercial.

### Fase 7 - API opcional

Endpoints futuros bajo:

```text
/api/sistema-presupuesto/produccion/...
```

No usar rutas `/editor_offset*`.

### Fase 8 - UI opcional

Mostrar plan productivo de forma read-only primero.

No permitir liberar produccion sin aprobacion y validaciones.

### Fase 9 - Integracion read-only con Editor Offset Visual

Solo si:

- existe snapshot versionado;
- hay fixtures;
- hay tests de no escritura;
- hay aprobacion explicita.

## Tests necesarios

### Contratos

- `ProductionOrderRequest` valido;
- `ProductionOrderRequest` invalido;
- campos obligatorios;
- schema version.

### Adaptador

- presupuesto nuevo con `numero_comercial`;
- presupuesto legacy sin `numero_comercial`;
- presupuesto con `estado=calculado`;
- presupuesto con warnings de grilla;
- presupuesto con cliente fijo UI;
- presupuesto con catalogo faltante.

### Submotores

- producto simple;
- tarjeta frente/dorso;
- revista multipagina;
- diptico/triptico;
- pieza que no entra;
- maquina incompatible;
- modo de cobro no soportado;
- proceso por m2;
- tinta sin datos suficientes.

### Integracion

- `BudgetRecord` -> `ProductionPlanResult`;
- warnings propagados;
- bloqueos propagados;
- no mutacion del presupuesto original.

### No acoplamiento

- no referencias a `layout_constructor.json`;
- no referencias a `static/constructor_offset_jobs`;
- no endpoints `/editor_offset`;
- no imports de servicios del Editor Offset Visual.

## Limites con Editor Offset Visual

El Editor Offset Visual sigue siendo propietario de:

- montaje visual;
- slots;
- preview;
- PDF final productivo;
- CTP visual/productivo del editor;
- jobs y `layout_constructor.json`;
- doble cara visual;
- imposicion visual.

El Motor de Produccion de `sistema_presupuesto` seria propietario de:

- plan productivo desde presupuesto;
- requerimientos de papel;
- requerimientos de maquina;
- chapas y pasadas;
- terminaciones;
- rentabilidad;
- recomendaciones.

Integracion futura permitida solo por adaptador read-only:

```text
Editor Offset Visual snapshot
  ↓
Adaptador versionado
  ↓
ProductionOrderRequest enriquecido
```

No se debe escribir en jobs del editor desde este motor.

## Decisiones pendientes

- Si `estado=aceptado` habilita boton de produccion o no.
- Si el motor usa catalogos vigentes o snapshot historico.
- Si `PIECE_DOES_NOT_FIT` bloquea siempre.
- Como representar tinta.
- Como representar compra minima de papel.
- Como representar tercerizados.
- Como versionar reglas productivas.
- Como auditar cambios de plan productivo.

## Recomendacion final

Construir primero el contrato y los tests. Luego implementar el motor puro. Recien despues considerar persistencia, API y UI.

La integracion con Editor Offset Visual debe quedar fuera de las primeras fases del Motor de Produccion.
