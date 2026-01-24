<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Activator {
    public static function activate() {
        global $wpdb;

        require_once ABSPATH . 'wp-admin/includes/upgrade.php';

        $charset_collate = $wpdb->get_charset_collate();

        $tables = array();

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_materiales (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            nombre varchar(190) NOT NULL,
            gramaje varchar(50) DEFAULT NULL,
            formato_base varchar(50) DEFAULT NULL,
            unidad_costo enum('pliego','resma','kg','metro') NOT NULL DEFAULT 'pliego',
            desperdicio_pct decimal(5,2) NOT NULL DEFAULT 0,
            activo tinyint(1) NOT NULL DEFAULT 1,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_material_precios (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            material_id bigint(20) unsigned NOT NULL,
            precio decimal(14,2) NOT NULL,
            moneda varchar(8) NOT NULL DEFAULT 'PYG',
            proveedor varchar(190) DEFAULT NULL,
            vigente_desde datetime NOT NULL,
            created_at datetime NOT NULL,
            PRIMARY KEY  (id),
            KEY material_id (material_id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_maquinas (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            nombre varchar(190) NOT NULL,
            tipo varchar(100) NOT NULL,
            costo_hora decimal(14,2) NOT NULL,
            rendimiento_hora int(11) DEFAULT NULL,
            activo tinyint(1) NOT NULL DEFAULT 1,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_procesos (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            nombre varchar(190) NOT NULL,
            modo_cobro enum('por_hora','por_unidad','por_pliego','fijo') NOT NULL DEFAULT 'fijo',
            costo_base decimal(14,2) NOT NULL DEFAULT 0,
            unidad varchar(40) DEFAULT NULL,
            activo tinyint(1) NOT NULL DEFAULT 1,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_presupuestos (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            core_cliente_id bigint(20) unsigned DEFAULT NULL,
            core_documento_id bigint(20) unsigned DEFAULT NULL,
            titulo varchar(190) NOT NULL,
            producto varchar(190) DEFAULT NULL,
            formato_final varchar(50) DEFAULT NULL,
            cantidad int(11) NOT NULL,
            material_id bigint(20) unsigned DEFAULT NULL,
            colores varchar(20) DEFAULT NULL,
            caras int(11) NOT NULL DEFAULT 1,
            margen_pct decimal(5,2) NOT NULL DEFAULT 30,
            estado enum('borrador','enviado','aceptado','rechazado') NOT NULL DEFAULT 'borrador',
            costo_total decimal(14,2) NOT NULL DEFAULT 0,
            precio_total decimal(14,2) NOT NULL DEFAULT 0,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id),
            KEY core_cliente_id (core_cliente_id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_presupuesto_items (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            presupuesto_id bigint(20) unsigned NOT NULL,
            tipo enum('papel','maquina','proceso','otro') NOT NULL,
            referencia_id bigint(20) unsigned DEFAULT NULL,
            descripcion varchar(255) NOT NULL,
            cantidad decimal(14,2) NOT NULL DEFAULT 1,
            unitario decimal(14,2) NOT NULL DEFAULT 0,
            subtotal decimal(14,2) NOT NULL DEFAULT 0,
            snapshot_json longtext DEFAULT NULL,
            created_at datetime NOT NULL,
            PRIMARY KEY  (id),
            KEY presupuesto_id (presupuesto_id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_ordenes (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            presupuesto_id bigint(20) unsigned DEFAULT NULL,
            core_cliente_id bigint(20) unsigned DEFAULT NULL,
            core_documento_id bigint(20) unsigned DEFAULT NULL,
            titulo varchar(190) NOT NULL,
            estado enum('pendiente','en_produccion','terminado','entregado') NOT NULL DEFAULT 'pendiente',
            fecha_entrega date DEFAULT NULL,
            notas text DEFAULT NULL,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id),
            KEY presupuesto_id (presupuesto_id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_orden_eventos (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            orden_id bigint(20) unsigned NOT NULL,
            evento varchar(100) NOT NULL,
            inicio datetime DEFAULT NULL,
            fin datetime DEFAULT NULL,
            notas text DEFAULT NULL,
            created_at datetime NOT NULL,
            PRIMARY KEY  (id),
            KEY orden_id (orden_id)
        ) $charset_collate;";

        foreach ( $tables as $table_sql ) {
            dbDelta( $table_sql );
        }

        $role = get_role( 'administrator' );
        if ( $role && ! $role->has_cap( 'manage_cpo_offset' ) ) {
            $role->add_cap( 'manage_cpo_offset' );
        }
    }
}
