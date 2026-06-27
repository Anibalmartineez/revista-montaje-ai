# API Interna

Blueprint Flask aislado del Sistema Presupuesto.

Desde Fase 10, la app principal Flask registra este Blueprint para exponer la API bajo `/api/sistema-presupuesto/...`.

## Blueprint

```python
from sistema_presupuesto.api import presupuesto_api_bp
```

Registro en la app principal:

```python
app.register_blueprint(presupuesto_api_bp)
```

El registro debe mantenerse como el unico Blueprint agregado para esta fase del modulo presupuesto.

## Configuracion

Por defecto usa:

```text
sistema_presupuesto/data/
```

Para pruebas se puede configurar:

```python
app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = "/tmp/presupuesto-data"
```

## Endpoints

```text
GET  /api/sistema-presupuesto/health
GET  /api/sistema-presupuesto/catalogos/materiales
GET  /api/sistema-presupuesto/catalogos/maquinas
GET  /api/sistema-presupuesto/catalogos/procesos
GET  /api/sistema-presupuesto/catalogos/<tipo>
GET  /api/sistema-presupuesto/catalogos/<tipo>/custom
POST /api/sistema-presupuesto/catalogos/<tipo>/custom
PUT  /api/sistema-presupuesto/catalogos/<tipo>/custom/<item_id>
DELETE /api/sistema-presupuesto/catalogos/<tipo>/custom/<item_id>
GET  /api/sistema-presupuesto/clientes
POST /api/sistema-presupuesto/clientes
GET  /api/sistema-presupuesto/clientes/<cliente_id>
PUT  /api/sistema-presupuesto/clientes/<cliente_id>
DELETE /api/sistema-presupuesto/clientes/<cliente_id>
GET  /api/sistema-presupuesto/numeracion
POST /api/sistema-presupuesto/cotizar
POST /api/sistema-presupuesto/cotizar-y-guardar
GET  /api/sistema-presupuesto/presupuestos
GET  /api/sistema-presupuesto/presupuestos/<presupuesto_id>
PATCH /api/sistema-presupuesto/presupuestos/<presupuesto_id>/estado
POST /api/sistema-presupuesto/presupuestos/<presupuesto_id>/duplicar
POST /api/sistema-presupuesto/presupuestos/<presupuesto_id>/documento
GET  /api/sistema-presupuesto/documentos/<archivo>
```

Tipos de catalogo permitidos:

- `materiales`
- `maquinas`
- `procesos`

Los endpoints historicos de catalogos siguen existiendo y devuelven el catalogo combinado default + custom.
Los endpoints `/custom` leen y escriben solo los archivos custom.
Si un `id` custom coincide con uno default, custom sobrescribe default en la respuesta combinada.

Los endpoints de clientes leen y escriben JSON local en `data/clientes/`.
El backend genera `cliente_id`, `created_at` y `updated_at`.
Clientes todavia no se asocian a presupuestos.

El endpoint `GET /numeracion` muestra el estado actual del contador comercial sin incrementarlo.
`POST /cotizar-y-guardar` genera y devuelve `numero_comercial` con formato `PRES-YYYY-000001`.

`POST /presupuestos/<presupuesto_id>/documento` genera un documento comercial desde el presupuesto guardado.
`GET /documentos/<archivo>` sirve solo archivos generados bajo `data/pdfs/`.

`GET /presupuestos` devuelve historial resumido y acepta filtros query string:

- `q`: busca por `numero_comercial`, producto, observaciones o `presupuesto_id`.
- `estado`: filtra por `borrador`, `enviado`, `aceptado`, `rechazado` o `vencido`.

El historial se ordena por `created_at` descendente y mantiene compatibilidad con registros antiguos sin `numero_comercial` o `estado`.

`PATCH /presupuestos/<presupuesto_id>/estado` cambia solo el campo `estado` y `updated_at`.
No reemplaza el presupuesto completo.

`POST /presupuestos/<presupuesto_id>/duplicar` crea un presupuesto nuevo con nuevo `presupuesto_id`, nuevo `numero_comercial`, `estado: "borrador"` y `duplicado_de` apuntando al original.
Puede recibir `observaciones` como patch simple.
No recalcula cantidades ni reusa documentos generados.

## Errores

Las respuestas de error usan JSON:

```json
{
  "ok": false,
  "error": {
    "code": "CONTRACT_INVALID",
    "type": "ContractValidationError",
    "message": "QuoteRequest invalido."
  }
}
```

Si hay errores de validacion, se agrega `validation`.

## Limites

- No integra con Editor Offset Visual.
- No lee ni escribe `layout_constructor.json`.
- No usa jobs, slots, pliegos, CTP ni montajes del Editor Offset Visual.
- Usa catalogos ficticios de diseno.
- No asocia clientes a presupuestos todavia.
