# CTP Módulo

Módulo para gestionar el copiado de chapas CTP integrado con el core **Gestión Core Global**.

## Instalación

1. Activar el plugin **gestión-core-global**.
2. Activar el plugin **ctp-modulo**.
3. Crear páginas con los shortcodes:
   - `[ctp_ordenes]`
   - `[ctp_liquidaciones]`

## Flujo recomendado

1. Cargar órdenes desde **[ctp_ordenes]**.
2. Seleccionar órdenes pendientes desde **[ctp_liquidaciones]**.
3. Generar la liquidación (factura de venta) para el cliente.
4. Registrar cobros en el core si aplica.

## Notas

- Si el core no está activo, el módulo muestra un aviso en el admin y no carga sus shortcodes.
- Las liquidaciones crean documentos en `gc_documentos` con tipo `venta`.
