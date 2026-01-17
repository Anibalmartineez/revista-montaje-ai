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
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY tipo (tipo),
        KEY estado (estado)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_documento_pagos (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        documento_id BIGINT UNSIGNED NOT NULL,
        fecha_pago DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        metodo VARCHAR(40) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY documento_id (documento_id)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_deudas (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        frecuencia VARCHAR(20) NOT NULL DEFAULT 'mensual',
        dia_sugerido TINYINT UNSIGNED NULL,
        activo TINYINT UNSIGNED NOT NULL DEFAULT 1,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY frecuencia (frecuencia),
        KEY activo (activo)
    ) {$charset_collate};";

    $tables[] = "CREATE TABLE {$wpdb->prefix}gc_deuda_pagos (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        deuda_id BIGINT UNSIGNED NOT NULL,
        fecha_pago DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY deuda_id (deuda_id)
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
}
