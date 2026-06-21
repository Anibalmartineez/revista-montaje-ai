# API Interna

Blueprint Flask aislado para probar el Sistema Presupuesto.

El Blueprint es importable, pero no se registra automaticamente en la app principal.

## Blueprint

```python
from sistema_presupuesto.api import presupuesto_api_bp
```

Para pruebas:

```python
app.register_blueprint(presupuesto_api_bp)
```

No registrar en la aplicacion principal sin una fase aprobada.

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
POST /api/sistema-presupuesto/cotizar
POST /api/sistema-presupuesto/cotizar-y-guardar
GET  /api/sistema-presupuesto/presupuestos
GET  /api/sistema-presupuesto/presupuestos/<presupuesto_id>
```

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

- No toca `routes.py`.
- No se registra en Flask principal.
- No integra con Editor Offset Visual.
- No crea UI.
- Usa catalogos ficticios de diseno.
