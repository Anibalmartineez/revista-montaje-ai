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

Fase actual: **Fase 9.2 - Clientes aislados completada**.

Proxima fase propuesta: **Fase 9.3 - Numeracion comercial aislada**.

Implementado:

- `AGENTS.md`;
- documentacion `00` a `10`;
- contratos JSON;
- catalogos default;
- catalogos custom editables;
- fixtures;
- modelos internos con `dataclasses`;
- validadores;
- serializadores;
- errores de dominio;
- matematica tecnica de produccion;
- motor monetario con `Decimal`;
- orquestador de calculo;
- persistencia JSON local;
- repositorio de catalogos;
- repositorio de presupuestos;
- CLI interno;
- Blueprint Flask aislado;
- API interna aislada;
- UI frontend aislada;
- administracion aislada de catalogos desde UI/API;
- clientes aislados desde UI/API;
- repositorio JSON local de clientes;
- `dev_app.py`;
- tests automatizados.

No incluye todavia:

- integracion con app principal Flask;
- registro del Blueprint en la app principal;
- integracion con Editor Offset Visual;
- lectura de `layout_constructor.json`;
- escritura en jobs del Editor Offset Visual;
- base de datos;
- autenticacion/usuarios;
- API publica productiva;
- asociacion de clientes con presupuestos;
- numeracion comercial;
- PDF comercial;
- historial avanzado;
- duplicacion de presupuestos.

## Fases previstas

1. Estructura y documentacion base.
2. Contratos JSON y fixtures.
3. Modelos, validadores y serializadores.
4. Motor determinista con `Decimal`.
5. Persistencia JSON y repositorios.
6. CLI interno.
7. API Flask aislada / Blueprint no registrado.
8. UI frontend aislada.
9. Gestion comercial aislada:
   - catalogos editables completados en Fase 9.1;
   - clientes completados en Fase 9.2;
   - numeracion comercial;
   - duplicacion de presupuestos;
   - PDF comercial;
   - historial.
10. Activacion dentro de app principal Flask.
11. Integracion read-only futura con Editor Offset Visual.

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
- `docs/09_ADMIN_CATALOGOS.md`: administracion aislada de catalogos editables.
- `docs/10_CLIENTES.md`: modelo y flujo aislado de clientes.

Documentos planificados para Fase 9:

- `docs/11_PDF_PRESUPUESTO.md`: generacion de PDF comercial.
- `docs/12_HISTORIAL_Y_DUPLICACION.md`: historial avanzado y duplicacion de presupuestos.
