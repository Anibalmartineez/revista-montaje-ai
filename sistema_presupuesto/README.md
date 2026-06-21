# Sistema Presupuesto

Modulo aislado para disenar, calcular, versionar y validar presupuestos automaticos para imprentas offset.

Este modulo no forma parte del Editor Offset Visual y no debe modificar rutas, servicios, contratos, templates, JavaScript, CSS, motores ni archivos productivos del editor.

## Vision general

El sistema debe permitir que una imprenta cargue sus parametros personalizados de costos y genere presupuestos trazables para trabajos offset.

La prioridad inicial es construir una base segura:

- contratos JSON claros;
- reglas de calculo documentadas;
- plan de implementacion por fases;
- estructura aislada;
- preparacion para tests;
- integracion futura por adaptador, no por acoplamiento directo.

## Objetivo

Construir un modulo determinista y auditable para presupuestos offset:

- papel;
- formato de pliego;
- merma;
- chapas;
- tinta;
- maquina;
- mano de obra;
- terminaciones;
- utilidad o margen;
- impuestos;
- precio final;
- precio unitario.

## Estado actual

Fase actual: **Fase 8 - UI frontend aislada**.

Incluye:

- `AGENTS.md`;
- documentacion inicial;
- carpetas base para backend, frontend, datos y tests.
- catalogos JSON de ejemplo;
- fixtures JSON de solicitudes de presupuesto;
- ejemplo de respuesta futura.
- modelos internos con `dataclasses`;
- validadores puros de contratos;
- serializadores base para convertir JSON validado en modelos;
- errores de dominio;
- tests minimos de contratos y serializacion.
- matematica tecnica de produccion;
- motor monetario con `Decimal`;
- orquestador de calculo puro;
- desglose auditable con advertencias.
- persistencia JSON local;
- repositorio de catalogos;
- repositorio de presupuestos calculados.
- CLI interno para calcular, guardar, listar y ver presupuestos.
- Blueprint Flask aislado e importable para pruebas internas.
- UI frontend aislada para cargar datos, calcular, guardar, listar y ver presupuestos.

No incluye todavia:

- rutas Flask;
- API;
- frontend funcional;
- motor de calculo;
- archivos Python funcionales;
- integracion con Editor Offset Visual;
- lectura de `layout_constructor.json`;
- escritura de presupuestos reales;
- rutas Flask;
- UI;
- integracion con el Editor Offset Visual.
- base de datos.
- API publica productiva.
- integracion con Editor Offset Visual.

## Fases previstas

1. Crear estructura y documentacion base.
2. Definir contratos JSON y fixtures de calculo.
3. Implementar modelos puros y validadores.
4. Implementar motor determinista con `Decimal`.
5. Agregar tests unitarios de casos reales.
6. Agregar almacenamiento JSON interno.
7. Crear UI aislada.
8. Evaluar API o Blueprint propio.
9. Evaluar adaptador read-only con Editor Offset Visual.

## Principio de diseno

Misma entrada + mismas tarifas + misma version de reglas = mismo resultado.

El resultado debe explicar cada componente del presupuesto. Si un dato tecnico no esta confirmado, el sistema debe emitir advertencias en lugar de inferir silenciosamente.

## Documentacion

- `docs/00_CONTEXTO.md`: vision, limites y dependencias permitidas.
- `docs/01_CONTRATOS.md`: contratos JSON futuros.
- `docs/02_REGLAS_CALCULO.md`: reglas y formulas principales.
- `docs/03_TESTS_VALIDACION.md`: estrategia de pruebas.
- `docs/04_PLAN_SAFE.md`: plan por fases.
- `docs/05_INTEGRACION_FUTURA_EDITOR_OFFSET.md`: integracion futura con el Editor Offset Visual.
- `docs/06_USO_CLI.md`: uso del CLI interno de prueba.
- `docs/07_API_INTERNA.md`: Blueprint Flask aislado.
- `docs/08_UI_AISLADA.md`: UI frontend aislada.
