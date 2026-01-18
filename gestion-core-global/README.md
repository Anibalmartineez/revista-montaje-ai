# Gestión Core Global (MVP)

Core global de gestión financiera y administrativa pensado para cualquier rubro (heladerías, ferreterías, imprentas, talleres, etc.).

## Instalación

1. Copia la carpeta `gestion-core-global` en `wp-content/plugins/`.
2. Activa el plugin **Gestión Core Global** desde el panel de WordPress.
3. Crea páginas y agrega los shortcodes necesarios (ver sección siguiente).
4. Al activar el plugin se crearán las tablas con prefijo `wp_gc_`.

## Shortcodes disponibles

- `[gc_dashboard]` Panel completo con todas las secciones.
- `[gc_movimientos]` Movimientos de caja (ingresos/egresos).
- `[gc_clientes]` CRUD de clientes.
- `[gc_proveedores]` CRUD de proveedores.
- `[gc_facturas_venta]` Documentos tipo factura de venta.
- `[gc_facturas_compra]` Documentos tipo factura de compra.
- `[gc_deudas]` Deudas recurrentes o únicas.
- `[gc_reportes]` Balance por período + export CSV.

## Estructura

```
gestion-core-global/
├── assets/
│   ├── app.js
│   └── style.css
├── includes/
│   ├── db.php
│   ├── handlers-clientes.php
│   ├── handlers-deudas.php
│   ├── handlers-documentos.php
│   ├── handlers-movimientos.php
│   ├── handlers-proveedores.php
│   ├── handlers-reportes.php
│   ├── helpers.php
│   ├── shortcodes-clientes.php
│   ├── shortcodes-dashboard.php
│   ├── shortcodes-deudas.php
│   ├── shortcodes-documentos.php
│   ├── shortcodes-movimientos.php
│   ├── shortcodes-proveedores.php
│   └── shortcodes-reportes.php
└── gestion-core-global.php
```

## Notas funcionales

- Todos los vínculos a clientes/proveedores/documentos son opcionales.
- Los pagos/cobros parciales de documentos generan movimientos automáticos en caja con origen `documento_pago`.
- Los pagos de deudas generan movimientos automáticos en caja con origen `deuda_pago`.
- Pagos de deudas recurrentes y préstamos se aplican al período de la fecha de pago.
- El balance se calcula con base en la tabla `gc_movimientos`.
- El export CSV aplica endurecimiento básico para prevenir inyección de fórmulas.
- En Movimientos, al seleccionar un documento o deuda pendiente, el monto se autocompleta con el saldo actual (editable para pagos parciales).

## Pruebas manuales rápidas

1. Crear una factura de venta desde **Facturas de venta**.
2. Registrar un cobro desde la factura y validar que:
   - Se crea un movimiento en **Movimientos** con el mismo monto.
   - El documento recalcula su estado/saldo.
3. Crear un movimiento desde **Movimientos** vinculando el documento y confirmar que:
   - Se registra un pago en el documento sin duplicar movimientos.
   - El estado del documento se recalcula con el nuevo pago.
4. Crear una deuda única por 100.000 y pagarla desde **Movimientos**:
   - La deuda queda en estado pagada y se auto-inactiva.
5. Crear una deuda recurrente mensual (alquiler 500.000, día 5):
   - Al pagar enero, la instancia de enero queda pagada.
   - Al avanzar al siguiente mes, la instancia de febrero aparece pendiente.
6. Crear un préstamo de 12 cuotas x 800.000 desde hoy:
   - Se crean 12 instancias mensuales.
   - Al pagar la cuota del mes, el movimiento queda como egreso mensual y el saldo global baja.
