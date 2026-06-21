# Contexto

`sistema_presupuesto/` es un modulo nuevo y aislado para presupuestos automaticos de imprentas offset.

Su objetivo es modelar costos de produccion, reglas comerciales y resultados auditables sin mezclar responsabilidades con el Editor Offset Visual.

## Alcance inicial

Incluye diseno documental para:

- contratos internos;
- reglas de calculo;
- estructura de carpetas;
- futuras validaciones;
- futura persistencia;
- futura UI aislada;
- futura integracion por adaptadores.

## Fuera de alcance en Fase 1

No se implementa:

- motor de calculo;
- rutas Flask;
- API;
- templates activos;
- JavaScript activo;
- CSS activo;
- integracion con Editor Offset Visual;
- lectura de jobs existentes;
- modificacion de `layout_constructor.json`.

## Limite con el Editor Offset Visual

El Editor Offset Visual sigue siendo propietario de montaje, imposicion visual, slots, preview, PDF final, CTP y persistencia de jobs.

El Sistema Presupuesto debe ser propietario de:

- solicitud de presupuesto;
- tarifas;
- reglas de calculo;
- resultado economico;
- desglose de costos;
- versionado futuro de presupuestos.

## Dependencias iniciales permitidas

En fases futuras, el motor de calculo debe poder funcionar con libreria estandar de Python y `Decimal`.

No se deben importar servicios del Editor Offset Visual ni depender de rutas actuales del sistema principal.

## Criterio operativo

El sistema debe favorecer trazabilidad sobre automatizacion opaca. Un presupuesto con advertencias claras es preferible a un precio final que no explique sus supuestos.
