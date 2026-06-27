# Propuestas Mejora Presupuesto

Propuestas SAFE posteriores a la auditoria del sistema actual.

Este documento no autoriza implementacion. Define prioridades y fases recomendadas.

## Principios de mejora

- No tocar Editor Offset Visual.
- No tocar `routes.py`.
- No cambiar contratos sin fase explicita.
- No mezclar estabilizacion, UX y Motor de Produccion en la misma pasada.
- Mantener backend como fuente de verdad.
- Preservar compatibilidad con presupuestos legacy.
- Agregar tests antes de cambios productivos.

## Mejoras de corto plazo

### 1. Reconciliar numeracion comercial

Problema:

- `data/quote_numbering.json` puede no existir aunque ya haya presupuestos con `numero_comercial`.

Riesgo:

- duplicar `PRES-2026-000001`.

Propuesta:

- crear fase documentada para reconciliar contador desde presupuestos existentes;
- agregar test de regresion;
- decidir si se hace herramienta CLI o migracion manual controlada.

Riesgo de cambio: alto si toca datos reales; debe hacerse con backup.

### 2. Bloquear modos de cobro no implementados

Problema:

- `pricing_engine._process_quantity()` devuelve `0` para `por_kg` y para modo desconocido.

Propuesta:

- antes de cambiar codigo, documentar enum de `modo_cobro`;
- agregar tests de caracterizacion;
- luego fallar con error controlado o warning bloqueante para modos no soportados.

Riesgo de cambio: moderado, porque puede afectar catalogos custom.

### 3. Decidir politica para pieza que no entra

Problema:

- si la pieza no entra en pliego, el motor agrega warning y cotiza con una unidad por pliego.

Propuesta:

- definir si `PIECE_DOES_NOT_FIT` debe bloquear cotizacion o permitir presupuesto con advertencia critica;
- agregar tests negativos.

Riesgo de cambio: alto funcional, porque cambia comportamiento visible.

### 4. Marcar docs 00-13 por vigencia

Problema:

- documentos historicos mezclan fases viejas y estado actual.

Propuesta:

- agregar nota de estado por documento: vigente, historico o pendiente de actualizacion;
- no borrar auditoria previa;
- usar docs 14-17 como mapa operativo actual.

Riesgo de cambio: bajo si solo documenta.

### 5. Fortalecer manejo JSON en API/CLI

Problemas:

- duplicacion usa JSON silencioso;
- CLI no captura `ValueError` para JSON raiz no objeto.

Propuesta:

- agregar tests primero;
- hacer consistente el manejo de errores en una fase pequena.

Riesgo de cambio: bajo/moderado.

## Mejoras de mediano plazo

### 1. Contratos mas formales

Propuesta:

- formalizar `QuoteRequest`, `QuoteResult` y `BudgetRecord` como contratos vigentes;
- separar fixture legacy `quote_response_example.json`;
- documentar campos obligatorios/opcionales por tipo de producto.

### 2. Mejorar cobertura de PDF

Propuesta:

- validar contenido del documento: numero comercial, cliente, producto, totales, impuestos, warnings y lineas de costo;
- probar HTML fallback y PDF con extraccion de texto cuando sea viable.

### 3. Playwright o flujo UI real

Propuesta:

- agregar pruebas de navegador para:
  - cargar UI;
  - cotizar;
  - guardar;
  - filtrar historial;
  - cambiar estado;
  - duplicar;
  - generar documento;
  - CRUD minimo de cliente;
  - CRUD minimo de catalogo custom.

### 4. Asociar clientes a presupuestos

Problema:

- existe CRUD de clientes, pero la cotizacion UI usa cliente fijo.

Propuesta:

- definir primero contrato: `cliente_id` en `QuoteRequest`, en `BudgetRecord`, o ambos;
- decidir comportamiento PDF;
- no implementar sin migracion/compatibilidad legacy.

### 5. Separar frontend por modulos

Problema:

- `presupuesto_offset.js` concentra salud API, cotizacion, historial, clientes, catalogos, documentos, render y helpers.

Propuesta:

- extraer en fases:
  - `api_client`;
  - `quote_form`;
  - `budget_panel`;
  - `client_panel`;
  - `catalog_panel`;
  - `formatters`.

Riesgo:

- alto acoplamiento con IDs `#sp-*`; requiere tests frontend antes.

## Mejoras de largo plazo

### 1. Seguridad y usuarios

Necesario antes de despliegue abierto:

- autenticacion;
- permisos para catalogos y presupuestos;
- auditoria de cambios de tarifas;
- control de datos personales de clientes.

### 2. Persistencia robusta

JSON local es adecuado para fase actual, pero para uso multiusuario conviene evaluar:

- base de datos;
- transacciones;
- locks;
- migraciones;
- indices de busqueda;
- backups.

### 3. Motor de Produccion

Crear capa nueva, no mutar el motor de cotizacion actual.

Objetivo:

- transformar presupuestos aceptados y datos tecnicos en planes productivos auditables.

No objetivo:

- integrarlo todavia con Editor Offset Visual.

### 4. Integracion read-only con Editor Offset Visual

Solo despues de contratos y tests:

- snapshot versionado;
- adaptador read-only;
- fixtures;
- validacion de no escritura en jobs;
- sin depender de internals no documentados.

## Motor de Produccion propuesto

La arquitectura recomendada se detalla en `17_PLAN_MOTOR_PRODUCCION.md`.

Resumen:

```text
BudgetRecord aceptado
  ↓
quote_adapter
  ↓
ProductionOrderRequest
  ↓
production_engine
  ↓
submotores tecnicos
  ↓
ProductionPlanResult
```

Submotores recomendados:

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

## Prioridades

### Prioridad 1: estabilidad de datos

- reconciliar numeracion;
- caracterizar concurrencia;
- proteger path/storage;
- revisar datos versionados en `data/`.

### Prioridad 2: contratos

- actualizar contrato vivo;
- marcar fixture legacy;
- definir campos de cliente;
- definir modos de cobro permitidos.

### Prioridad 3: cobertura

- tests de redondeo;
- tests de modos de cobro;
- tests de pieza que no entra;
- tests de PDF semantico;
- tests UI reales.

### Prioridad 4: UX operativa

- estados de carga;
- bloqueo de doble submit;
- debounce de busqueda;
- mejor editor de catalogos;
- selector de cliente.

### Prioridad 5: Motor de Produccion

- documentar contratos;
- crear modelos puros;
- adaptador desde presupuesto;
- motor puro;
- persistencia opcional;
- API/UI solo despues.

## Riesgos

- Cambiar formulas sin golden tests puede romper presupuestos actuales.
- Cambiar contratos sin migracion puede romper presupuestos guardados.
- Integrar clientes sin plan puede duplicar datos personales.
- Exponer catalogos sin permisos puede alterar tarifas.
- Convertir `estado=aceptado` en produccion automatica puede generar ordenes sin aprobacion tecnica.
- Integrar con Editor Offset Visual antes de tiempo puede acoplar dos sistemas fragiles.

## Fases sugeridas

### Fase A - Auditoria y documentos

Estado: esta rama.

Entregables:

- docs 14-17;
- README actualizado con referencias.

### Fase B - Estabilizacion de contratos y datos

Entregables:

- contrato vivo revisado;
- politica de datos generados;
- decision sobre `quote_response_example.json`;
- plan de reconciliacion de numeracion.

### Fase C - Tests de produccion inicial

Entregables:

- golden tests por producto;
- tests de redondeo;
- tests de concurrencia/numeracion;
- tests PDF semanticos;
- pruebas UI reales.

### Fase D - Correcciones pequenas

Solo despues de tests:

- errores JSON consistentes;
- modos de cobro no soportados;
- politica `PIECE_DOES_NOT_FIT`;
- lock o reconciliacion de numeracion.

### Fase E - Motor de Produccion documental

Entregables:

- contratos `ProductionOrderRequest` y `ProductionPlanResult`;
- fixtures;
- validadores conceptuales.

### Fase F - Motor de Produccion puro

Entregables:

- modelos;
- adaptador desde presupuesto;
- submotores puros;
- tests.

### Fase G - Persistencia/API/UI productiva

Solo si el motor puro esta validado.

## Que no se debe tocar todavia

- Editor Offset Visual.
- `routes.py`.
- `app.py` o rutas principales, salvo fase explicita.
- `production_math.py` para convertirlo en motor industrial.
- `BudgetRepository` para generar ordenes productivas automaticamente.
- `data/presupuestos/*.json` sin backup y plan de migracion.
- IDs `#sp-*` del frontend sin tests.
- contratos `schema_version` sin estrategia de compatibilidad.
