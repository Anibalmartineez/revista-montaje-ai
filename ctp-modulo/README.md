# CTP Módulo

Módulo para gestionar el copiado de chapas CTP integrado con el core **Gestión Core Global**.

## Instalación

1. Activar el plugin **gestión-core-global**.
2. Activar el plugin **ctp-modulo**.
3. Crear páginas con los shortcodes:
   - `[ctp_ordenes]`
   - `[ctp_liquidaciones]`

## Requisitos

- **Gestión Core Global** activo y actualizado (API mínima disponible).
- PHP 8.0 o superior.

## Flujo recomendado

1. Cargar órdenes desde **[ctp_ordenes]**.
2. Seleccionar órdenes pendientes desde **[ctp_liquidaciones]** por cliente y rango de fechas.
3. Generar la liquidación para crear un documento tipo **factura_venta** en el core.
4. Registrar cobros en el core si aplica.

## Notas

- Si el core no está activo, el módulo muestra un aviso en el admin y no carga sus shortcodes.
- Si el core está activo pero la API no está disponible, el módulo muestra un aviso para actualizar el core.
- Las liquidaciones crean documentos en `gc_documentos` con tipo `factura_venta`.
