# Administracion de Catalogos

Fase 9.1 agrega catalogos editables dentro del modulo aislado `sistema_presupuesto/`.

No integra con la app principal Flask, no registra el Blueprint principal y no toca el Editor Offset Visual.

## Archivos

Catalogos base no editables por API/UI:

- `data/catalogo/materiales_default.json`
- `data/catalogo/maquinas_default.json`
- `data/catalogo/procesos_default.json`

Catalogos custom editables:

- `data/catalogo/materiales_custom.json`
- `data/catalogo/maquinas_custom.json`
- `data/catalogo/procesos_custom.json`

## Regla default vs custom

- Los archivos `*_default.json` son la base del modulo.
- La API y la UI no modifican archivos `*_default.json`.
- Los archivos `*_custom.json` contienen items configurables por el usuario.
- Si un item custom usa el mismo `id` que un item default, el custom sobrescribe al default en el catalogo combinado.
- El catalogo combinado agrega `origen_catalogo` con valor `default` o `custom` para que la UI muestre el origen.
- La cotizacion interna usa catalogos combinados, por lo que un override custom puede afectar el calculo.

## Tipos soportados

- `materiales`
- `maquinas`
- `procesos`

Otros tipos deben rechazarse hasta que exista contrato documentado.

## Validacion minima

Todos los items requieren:

- `id` no vacio con letras, numeros, guion o guion bajo;
- `nombre`;
- `activo` boolean opcional.

Materiales requieren tambien:

- `tipo`;
- `gramaje_g_m2` mayor que cero;
- `formato_pliego_mm.ancho` y `formato_pliego_mm.alto` mayores que cero;
- `costo.modo`;
- `costo.moneda = PYG`;
- `costo.valor` no negativo;
- `costo.unidad`.

Maquinas requieren tambien:

- `tipo`;
- `cuerpos_color` entero positivo;
- formatos minimo y maximo con ancho/alto positivos;
- `costos.moneda = PYG`;
- `costos.costo_hora`, `costos.costo_arranque` y `costos.costo_lavado_por_color` no negativos;
- `rendimiento.velocidad_pliegos_hora` mayor que cero;
- `rendimiento.setup_horas` no negativo.

Procesos requieren tambien:

- `categoria`;
- `modo_cobro`;
- `base_calculo`;
- `tarifa.moneda = PYG`;
- `tarifa.valor` no negativo;
- `tarifa.unidad`.

Los importes se validan con `Decimal`. No usar `float`.

## Endpoints aislados

Base:

```text
/api/sistema-presupuesto
```

Listar catalogo combinado:

```text
GET /catalogos/<tipo>
```

Listar solo custom:

```text
GET /catalogos/<tipo>/custom
```

Crear custom:

```text
POST /catalogos/<tipo>/custom
```

Actualizar custom:

```text
PUT /catalogos/<tipo>/custom/<item_id>
```

Eliminar custom:

```text
DELETE /catalogos/<tipo>/custom/<item_id>
```

Los endpoints historicos siguen respondiendo y devuelven catalogo combinado:

```text
GET /catalogos/materiales
GET /catalogos/maquinas
GET /catalogos/procesos
```

## UI aislada

La UI en `dev_app.py` agrega una seccion `Catalogos`.

Permite:

- elegir tipo de catalogo;
- ver items default y custom;
- crear un item custom desde JSON;
- editar un item custom;
- crear un override custom tomando como base un item default;
- eliminar solo items custom.

La UI no calcula costos. Envia JSON y muestra errores devueltos por backend.

## Limites

- No hay autenticacion ni usuarios.
- No hay auditoria comercial avanzada.
- No hay historial de cambios de catalogos.
- No hay flujo de aprobacion de tarifas.
- No hay catalogo productivo real.
- No se editan catalogos default desde API/UI.
- No se integra con Editor Offset Visual.

## Valores y costos

Los valores existentes son ficticios de diseno.

Los valores nuevos deben ser configurables por el usuario o ficticios y marcarse como ejemplo cuando corresponda, por ejemplo con `es_valor_ejemplo: true`.
