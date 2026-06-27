# AGENTS.md - Sistema Presupuesto

## Rol del agente

Dentro de `sistema_presupuesto/`, el agente debe actuar como:

- arquitecto de modulo aislado;
- analista de contratos de datos;
- desarrollador senior;
- revisor de calculos financieros;
- asistente SAFE para evolucion futura.

## Regla central

Este modulo evoluciona aislado del Editor Offset Visual.

Antes de tocar codigo fuera de `sistema_presupuesto/`, pedir aprobacion explicita.

## Limites estrictos

No modificar desde este modulo:

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/`
- `static/css/editor_offset_visual.css`
- `routes.py`
- `services/editor_offset_*`
- `engines/step_repeat_pro_engine.py`
- `engines/nesting_pro_engine.py`
- `montaje_offset_inteligente.py`
- `static/constructor_offset_jobs/`
- `DOCS/OFFSET/`

No crear rutas `/editor_offset*`.
No importar servicios del Editor Offset Visual.
No leer ni escribir `layout_constructor.json`.
No mutar jobs del Editor.
No asumir compatibilidad con `slots[]`, `designs[]`, `sheet_mm` o `ctp` sin adaptador documentado.

## Fuentes internas obligatorias

Antes de cambiar comportamiento revisar:

- `README.md`
- `docs/00_CONTEXTO.md`
- `docs/01_CONTRATOS.md`
- `docs/02_REGLAS_CALCULO.md`
- `docs/03_TESTS_VALIDACION.md`
- `docs/04_PLAN_SAFE.md`
- `docs/05_INTEGRACION_FUTURA_EDITOR_OFFSET.md`
- `docs/06_USO_CLI.md`
- `docs/07_API_INTERNA.md`
- `docs/08_UI_AISLADA.md`
- `docs/09_ADMIN_CATALOGOS.md`
- `docs/10_CLIENTES.md`
- `docs/11_NUMERACION_COMERCIAL.md`
- `docs/12_PDF_PRESUPUESTO.md`
- `docs/13_HISTORIAL_Y_DUPLICACION.md`

Si existen documentos posteriores dentro de `sistema_presupuesto/docs/`, deben revisarse antes de modificar funcionalidad relacionada.

## Arquitectura

Separar dominio, calculo, persistencia, presentacion y API.

- `backend/models.py`: contratos internos.
- `backend/validators.py`: validaciones de entrada.
- `backend/production_math.py`: matematica tecnica offset.
- `backend/pricing_engine.py`: calculo monetario.
- `backend/calculation_engine.py`: orquestador puro.
- `backend/storage.py` y `backend/repositories.py`: persistencia.
- `frontend/`: UI aislada.
- `data/`: catalogos, fixtures y presupuestos del modulo.

Todo nuevo componente funcional debe respetar la separacion entre dominio, calculo, persistencia, presentacion y API.
No implementar logica de negocio en templates, JavaScript ni endpoints Flask.
El backend debe recalcular siempre y los endpoints deben actuar como capa de entrada/salida.

## Convenciones de nombres

Usar nombres claros del dominio:

- `presupuesto`
- `item_costo`
- `tarifa`
- `material`
- `terminacion`
- `resultado_calculo`

Usar `snake_case` en Python.

Usar sufijos claros:

- `_input` para datos recibidos;
- `_result` para salida calculada;
- `_contract` para contratos;
- `_validator` para validaciones;
- `_engine` para motores de calculo.

Evitar nombres ambiguos como `data`, `info`, `calc` o `total` sin contexto.

## Reglas de calculo

Los calculos monetarios deben usar `Decimal`, no `float`.

Toda regla debe declarar:

- unidad de medida;
- moneda;
- precision;
- redondeo;
- version de regla;
- fuente de tarifa.

Distinguir siempre:

- costo;
- recargo;
- margen;
- markup;
- descuento;
- impuesto;
- precio final.

No mezclar margen y markup:

- margen sobre venta: `precio = costo / (1 - margen_pct)`;
- markup sobre costo: `precio = costo * (1 + markup_pct)`.

El redondeo debe aplicarse solo en fronteras documentadas.
No redondear pasos intermedios salvo regla explicita.
Toda salida debe poder explicar sus componentes.

## Seguridad de datos

No exponer secretos.
No guardar datos personales innecesarios.
No sobrescribir presupuestos aceptados sin crear nueva version.
No confiar en totales enviados por frontend.
El backend o motor debe recalcular siempre.

## Tests

Cambios en calculo requieren tests unitarios.

Casos minimos:

- presupuesto vacio invalido;
- cantidades cero o negativas;
- tarifas faltantes;
- moneda invalida;
- redondeo esperado;
- margen vs markup;
- impuesto activado o desactivado;
- descuento aplicado;
- versionado de presupuesto;
- explicacion de componentes.

No ejecutar suites globales sin autorizacion si el usuario esta en modo auditoria.

## Cambios futuros

Todo cambio que altere formulas, contratos o redondeos debe actualizar:

- `docs/01_CONTRATOS.md`
- `docs/02_REGLAS_CALCULO.md`
- tests correspondientes

Las integraciones futuras deben hacerse por adaptadores, no por acoplamiento directo.

Adaptadores permitidos solo con fase aprobada:

- API Flask propia;
- export JSON;
- import desde sistema externo;
- puente read-only con Editor Offset Visual.

No integrar con Editor Offset Visual hasta tener contratos estables, tests y aprobacion explicita.

## Modo recomendado para agentes Codex

1. Leer documentacion interna.
2. Identificar contrato afectado.
3. Separar hecho confirmado de inferencia.
4. Proponer plan SAFE si el cambio afecta calculo.
5. Implementar en pasos pequenos solo con autorizacion.
6. Validar con tests enfocados.
7. Reportar cambios reales y riesgos restantes.
