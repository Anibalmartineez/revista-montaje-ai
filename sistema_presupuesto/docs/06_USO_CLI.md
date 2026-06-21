# Uso CLI

CLI interno para probar el Sistema Presupuesto sin Flask, sin UI y sin integracion con el Editor Offset Visual.

## Comandos

Calcular desde fixture:

```bash
python -m sistema_presupuesto.cli calcular sistema_presupuesto/data/fixtures/quote_request_volante.json
```

Calcular y guardar:

```bash
python -m sistema_presupuesto.cli calcular-y-guardar sistema_presupuesto/data/fixtures/quote_request_volante.json
```

Listar presupuestos guardados:

```bash
python -m sistema_presupuesto.cli listar
```

Ver presupuesto por ID:

```bash
python -m sistema_presupuesto.cli ver <presupuesto_id>
```

## Salida

La salida normal es JSON legible por stdout.

Los errores salen como JSON por stderr con `ok: false`.

## Directorio de datos

Por defecto usa:

```text
sistema_presupuesto/data/
```

Para pruebas se puede usar otro directorio:

```bash
python -m sistema_presupuesto.cli --data-dir C:/tmp/presupuesto-data listar
```

El directorio alternativo debe contener `catalogo/materiales_default.json`, `catalogo/maquinas_default.json` y `catalogo/procesos_default.json` si se quiere calcular.

## Limites

- No crea rutas Flask.
- No crea UI.
- No integra con Editor Offset Visual.
- Usa catalogos ficticios de diseno.
- Mantiene warnings de valores no productivos.
