<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_core_global_install(): void {
    global $wpdb;
    $charset_collate = $wpdb->get_charset_collate();

    $tables = array();

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_movimientos (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        fecha DATE NOT NULL,
        tipo VARCHAR(20) NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        metodo VARCHAR(40) NULL,
        categoria VARCHAR(80) NULL,
        descripcion TEXT NULL,
        cliente_id BIGINT UNSIGNED NULL,
        proveedor_id BIGINT UNSIGNED NULL,
        documento_id BIGINT UNSIGNED NULL,
        origen VARCHAR(40) NULL,
        ref_id BIGINT UNSIGNED NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY tipo (tipo),
        KEY fecha (fecha),
        KEY categoria (categoria),
        KEY origen (origen),
        KEY ref_id (ref_id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_clientes (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        ruc VARCHAR(50) NULL,
        telefono VARCHAR(80) NULL,
        email VARCHAR(120) NULL,
        direccion VARCHAR(255) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_proveedores (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        ruc VARCHAR(50) NULL,
        telefono VARCHAR(80) NULL,
        email VARCHAR(120) NULL,
        direccion VARCHAR(255) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_documentos (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        numero VARCHAR(60) NOT NULL,
        fecha DATE NOT NULL,
        tipo VARCHAR(30) NOT NULL,
        cliente_id BIGINT UNSIGNED NULL,
        proveedor_id BIGINT UNSIGNED NULL,
        total DECIMAL(14,2) NOT NULL DEFAULT 0,
        estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        monto_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
        saldo DECIMAL(14,2) NOT NULL DEFAULT 0,
        notas TEXT NULL,
        origen VARCHAR(40) NULL,
        ref_id BIGINT UNSIGNED NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY tipo (tipo),
        KEY estado (estado),
        KEY origen (origen),
        KEY ref_id (ref_id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_documento_pagos (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        documento_id BIGINT UNSIGNED NOT NULL,
        movimiento_id BIGINT UNSIGNED NULL,
        fecha_pago DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        metodo VARCHAR(40) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY documento_id (documento_id),
        KEY movimiento_id (movimiento_id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_deudas (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        categoria VARCHAR(80) NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        monto_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
        saldo DECIMAL(14,2) NOT NULL DEFAULT 0,
        tipo_deuda ENUM('unica','recurrente','prestamo') NOT NULL DEFAULT 'recurrente',
        frecuencia ENUM('semanal','mensual','anual') NULL,
        dia_sugerido TINYINT UNSIGNED NULL,
        vencimiento DATE NULL,
        dia_vencimiento INT NULL,
        dia_semana INT NULL,
        cuotas_total INT NULL,
        cuota_monto DECIMAL(14,2) NULL,
        fecha_inicio DATE NULL,
        total_calculado DECIMAL(14,2) NULL,
        activo TINYINT UNSIGNED NOT NULL DEFAULT 1,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY frecuencia (frecuencia),
        KEY activo (activo)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_deuda_instancias (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        deuda_id BIGINT UNSIGNED NOT NULL,
        periodo VARCHAR(7) NOT NULL,
        vencimiento DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        monto_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
        saldo DECIMAL(14,2) NOT NULL DEFAULT 0,
        estado ENUM('pendiente','parcial','pagada') NOT NULL DEFAULT 'pendiente',
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY deuda_periodo (deuda_id, periodo),
        KEY deuda_id (deuda_id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_deuda_pagos (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        deuda_id BIGINT UNSIGNED NOT NULL,
        movimiento_id BIGINT UNSIGNED NULL,
        fecha_pago DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        metodo VARCHAR(40) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY deuda_id (deuda_id),
        KEY movimiento_id (movimiento_id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_categorias (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(120) NOT NULL,
        tipo VARCHAR(20) NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY nombre (nombre)
    ) {$charset_collate};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';

    foreach ($tables as $sql) {
        dbDelta($sql);
    }

    gc_core_global_maybe_add_column(gc_get_table('gc_documento_pagos'), 'movimiento_id', 'BIGINT UNSIGNED NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deuda_pagos'), 'movimiento_id', 'BIGINT UNSIGNED NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deuda_pagos'), 'metodo', 'VARCHAR(40) NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deuda_pagos'), 'instancia_id', 'BIGINT UNSIGNED NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'estado', "VARCHAR(20) NOT NULL DEFAULT 'pendiente'");
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'monto_pagado', 'DECIMAL(14,2) NOT NULL DEFAULT 0');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'saldo', 'DECIMAL(14,2) NOT NULL DEFAULT 0');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'tipo_deuda', "ENUM('unica','recurrente','prestamo') NOT NULL DEFAULT 'recurrente'");
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'categoria', 'VARCHAR(80) NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'vencimiento', 'DATE NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'frecuencia', "ENUM('semanal','mensual','anual') NULL");
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'dia_vencimiento', 'INT NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'dia_semana', 'INT NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'cuotas_total', 'INT NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'cuota_monto', 'DECIMAL(14,2) NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'fecha_inicio', 'DATE NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_deudas'), 'total_calculado', 'DECIMAL(14,2) NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_documentos'), 'origen', 'VARCHAR(40) NULL');
    gc_core_global_maybe_add_column(gc_get_table('gc_documentos'), 'ref_id', 'BIGINT UNSIGNED NULL');

    gc_core_global_migrate_deudas();

    update_option('gc_core_global_db_version', GC_CORE_GLOBAL_DB_VERSION);
}

function gc_core_global_maybe_upgrade(): void {
    $installed_version = get_option('gc_core_global_db_version', '');

    if ($installed_version && version_compare($installed_version, GC_CORE_GLOBAL_DB_VERSION, '>=')) {
        return;
    }

    gc_core_global_install();
    update_option('gc_core_global_db_version', GC_CORE_GLOBAL_DB_VERSION);
}

function gc_core_global_maybe_add_column(string $table, string $column, string $definition): void {
    global $wpdb;
    $exists = $wpdb->get_var($wpdb->prepare("SHOW COLUMNS FROM {$table} LIKE %s", $column));
    if ($exists) {
        return;
    }
    $wpdb->query("ALTER TABLE {$table} ADD COLUMN {$column} {$definition}");
}

function gc_core_global_migrate_deudas(): void {
    global $wpdb;
    $table = gc_get_table('gc_deudas');

    $wpdb->query(
        "UPDATE {$table}
        SET tipo_deuda = CASE
            WHEN frecuencia = 'unico' THEN 'unica'
            WHEN frecuencia IN ('semanal','mensual','anual') THEN 'recurrente'
            ELSE tipo_deuda
        END
        WHERE tipo_deuda IS NULL OR tipo_deuda = ''"
    );

    $wpdb->query(
        "UPDATE {$table}
        SET dia_vencimiento = dia_sugerido
        WHERE dia_vencimiento IS NULL AND dia_sugerido IS NOT NULL AND frecuencia IN ('mensual','anual')"
    );
}
