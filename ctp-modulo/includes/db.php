<?php

if (!defined('ABSPATH')) {
    exit;
}

function ctp_modulo_install(): void {
    if (!function_exists('gc_get_table')) {
        return;
    }

    global $wpdb;
    $charset_collate = $wpdb->get_charset_collate();

    $ordenes_table = $wpdb->prefix . 'ctp_ordenes';
    $items_table = $wpdb->prefix . 'ctp_orden_items';

    $sql_ordenes = "CREATE TABLE {$ordenes_table} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        fecha DATE NOT NULL,
        nro_orden VARCHAR(50) NOT NULL,
        cliente_id BIGINT UNSIGNED NOT NULL,
        nombre_trabajo VARCHAR(200) NOT NULL,
        descripcion TEXT NULL,
        estado ENUM('pendiente','liquidada','anulada') NOT NULL DEFAULT 'pendiente',
        documento_id BIGINT UNSIGNED NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY nro_orden (nro_orden),
        KEY cliente_id (cliente_id),
        KEY fecha (fecha)
    ) {$charset_collate};";

    $sql_items = "CREATE TABLE {$items_table} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        orden_id BIGINT UNSIGNED NOT NULL,
        medida VARCHAR(50) NOT NULL,
        cantidad INT NOT NULL,
        precio_unit DECIMAL(14,2) NOT NULL,
        total DECIMAL(14,2) NOT NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY orden_id (orden_id)
    ) {$charset_collate};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';

    dbDelta($sql_ordenes);
    dbDelta($sql_items);

    ctp_modulo_maybe_add_column($ordenes_table, 'documento_id', 'BIGINT UNSIGNED NULL');
    ctp_modulo_maybe_add_column($ordenes_table, 'estado', "ENUM('pendiente','liquidada','anulada') NOT NULL DEFAULT 'pendiente'");
}

function ctp_modulo_maybe_add_column(string $table, string $column, string $definition): void {
    global $wpdb;

    $exists = $wpdb->get_var($wpdb->prepare("SHOW COLUMNS FROM {$table} LIKE %s", $column));
    if ($exists) {
        return;
    }

    $wpdb->query("ALTER TABLE {$table} ADD COLUMN {$column} {$definition}");
}
