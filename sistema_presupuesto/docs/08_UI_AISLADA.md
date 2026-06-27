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
7. La seccion `Catalogos` permite administrar items custom de materiales, maquinas y procesos.
8. La seccion `Clientes` permite administrar clientes aislados.
9. Al guardar un presupuesto, la UI muestra el `numero_comercial` generado por backend.
10. Desde un presupuesto guardado, la UI permite generar y abrir documento comercial.
11. La seccion de presupuestos guardados permite buscar, filtrar por estado, cambiar estado y duplicar presupuestos.

## Catalogos

La seccion `Catalogos` consume exclusivamente endpoints internos bajo `/api/sistema-presupuesto`.

Permite:

- elegir tipo de catalogo;
- ver catalogo combinado default + custom;
- distinguir `origen_catalogo` entre `default` y `custom`;
- crear items custom;
- editar items custom;
- crear un override custom desde un item default;
- eliminar solo items custom;
- mostrar errores de validacion devueltos por backend.

La UI no modifica catalogos default.
La UI no calcula costos ni valida reglas de negocio; el backend valida y recalcula siempre.

## Clientes

La seccion `Clientes` consume endpoints internos bajo `/api/sistema-presupuesto/clientes`.

Permite:

- listar clientes;
- crear cliente;
- editar cliente;
- eliminar cliente;
- mostrar errores de validacion devueltos por backend.

La UI no asocia clientes con presupuestos todavia.
La UI no genera PDF por si misma; solicita el documento al backend aislado.

## Numeracion comercial

La UI muestra `numero_comercial` cuando existe:

- despues de `cotizar-y-guardar`;
- en la lista de presupuestos guardados;
- al abrir un presupuesto guardado.

El frontend no genera numeros comerciales.
El backend es la unica fuente del formato `PRES-YYYY-000001`.

## Documento comercial

La UI muestra un boton `Generar documento` al abrir un presupuesto guardado.

Permite:

- generar PDF comercial si el backend tiene soporte disponible;
- mostrar fallback HTML si el backend no puede generar PDF;
- abrir el documento generado mediante endpoint seguro.

## Historial y duplicacion

La UI de presupuestos guardados muestra:

- `numero_comercial` si existe;
- estado;
- producto;
- cantidad;
- precio final;
- precio unitario.

Permite:

- buscar por texto contra el historial;
- filtrar por estado;
- abrir un presupuesto guardado;
- cambiar estado mediante endpoint dedicado;
- duplicar un presupuesto con nuevo numero comercial;
- generar documento desde el presupuesto abierto.

La duplicacion no recalcula cantidades desde la UI.
Si se informa observacion, se guarda como dato comercial del duplicado.

## Reglas

- El frontend no calcula precios.
- El backend/API es la fuente de verdad.
- No usa endpoints del Editor Offset Visual.
- No toca `routes.py`.
- No modifica templates, JS o CSS existentes del sistema principal.
- Los catalogos siguen siendo ficticios de diseno.
- Los valores custom deben ser configurables o ficticios.
- Los clientes se administran aislados y aun no forman parte del `QuoteRequest`.
- Los presupuestos antiguos pueden no tener `numero_comercial`.
- Los presupuestos antiguos sin `estado` se muestran como `borrador`.
- Los documentos generados viven bajo `data/pdfs/`.
