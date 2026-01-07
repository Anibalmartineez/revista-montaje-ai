# CTP Órdenes (MVP)

Plugin WordPress para cargar y listar órdenes de CTP, con gestión básica de proveedores, facturas y pagos parciales mediante shortcodes.

## Instalación (ZIP)
1. Desde la raíz del repo, comprime la carpeta `ctp-ordenes/` como ZIP.
   - Ejemplo: `zip -r ctp-ordenes.zip ctp-ordenes`
2. En WordPress, ve a **Plugins → Añadir nuevo → Subir plugin**.
3. Selecciona el ZIP y activa el plugin.

> **Nota:** El ZIP debe contener la carpeta del plugin (`ctp-ordenes/`) en su raíz.

## Uso de shortcodes (Divi o editor clásico)
- **Formulario de carga:**
  - Inserta el shortcode `[ctp_cargar_orden]` en una página o módulo de código de Divi.
- **Listado de órdenes:**
  - Inserta el shortcode `[ctp_listar_ordenes]` en una página o módulo de código de Divi.
- **Gestión de proveedores:**
  - Inserta el shortcode `[ctp_proveedores]` para crear, editar y eliminar proveedores.
- **Facturas de proveedores (cuentas por pagar):**
  - Inserta el shortcode `[ctp_facturas_proveedor]` para registrar facturas, pagos parciales y ver estados.

## Consideraciones
- Al activar el plugin se crea la tabla `{prefijo_wp}ctp_ordenes` y las nuevas tablas:
  - `{prefijo_wp}ctp_proveedores`
  - `{prefijo_wp}ctp_facturas_proveedor`
  - `{prefijo_wp}ctp_pagos_factura`
- El total se calcula en vivo con JavaScript y se recalcula en el servidor antes de guardar.
- Las órdenes ahora aceptan un campo opcional "Nombre del trabajo" para identificar mejor cada pedido.
