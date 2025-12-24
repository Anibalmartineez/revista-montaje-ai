# CTP Órdenes (MVP)

Plugin WordPress para cargar y listar órdenes de CTP mediante shortcodes.

## Instalación (ZIP)
1. Desde la raíz del repo, comprime la carpeta `wp-plugin-ctp-ordenes/` como ZIP.
2. En WordPress, ve a **Plugins → Añadir nuevo → Subir plugin**.
3. Selecciona el ZIP y activa el plugin.

> **Nota:** El ZIP debe contener la carpeta del plugin (`wp-plugin-ctp-ordenes/`) en su raíz.

## Uso de shortcodes (Divi o editor clásico)
- **Formulario de carga:**
  - Inserta el shortcode `[ctp_cargar_orden]` en una página o módulo de código de Divi.
- **Listado de órdenes:**
  - Inserta el shortcode `[ctp_listar_ordenes]` en una página o módulo de código de Divi.

## Consideraciones
- Al activar el plugin se crea la tabla `{prefijo_wp}ctp_ordenes`.
- El total se calcula en vivo con JavaScript y se recalcula en el servidor antes de guardar.
