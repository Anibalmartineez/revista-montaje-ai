# UI Aislada

Interfaz frontend separada para probar presupuestos offset sin tocar la app principal ni el Editor Offset Visual.

## Archivos

```text
frontend/templates/presupuesto_offset_app.html
frontend/static/css/presupuesto_offset.css
frontend/static/js/presupuesto_offset.js
dev_app.py
```

## Uso de desarrollo

Ejecutar:

```bash
venv\Scripts\python.exe -m sistema_presupuesto.dev_app
```

Abrir:

```text
http://127.0.0.1:5057/sistema-presupuesto-ui
```

La app de desarrollo registra el Blueprint interno solo en esa app temporal.
No registra nada en la aplicacion principal.

Por defecto usa:

```text
sistema_presupuesto/data/
```

Para pruebas manuales sin escribir en los datos del modulo, crear un directorio temporal con la carpeta `catalogo/` y ejecutar:

```bash
$env:SISTEMA_PRESUPUESTO_DATA_DIR="C:\tmp\sistema-presupuesto-data"
venv\Scripts\python.exe -m sistema_presupuesto.dev_app
```

El directorio alternativo debe contener:

```text
catalogo/materiales_default.json
catalogo/maquinas_default.json
catalogo/procesos_default.json
```

## Flujo

1. La UI carga salud de API y catalogos.
2. El usuario completa producto, produccion y costos.
3. La UI envia `QuoteRequest` a `/api/sistema-presupuesto/cotizar`.
4. El backend calcula y devuelve desglose.
5. La UI puede enviar a `/api/sistema-presupuesto/cotizar-y-guardar`.
6. La UI lista y abre presupuestos guardados.

## Reglas

- El frontend no calcula precios.
- El backend/API es la fuente de verdad.
- No usa endpoints del Editor Offset Visual.
- No toca `routes.py`.
- No modifica templates, JS o CSS existentes del sistema principal.
- Los catalogos siguen siendo ficticios de diseno.
