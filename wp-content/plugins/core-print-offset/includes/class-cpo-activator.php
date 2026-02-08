<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Activator {
    public static function activate() {
        global $wpdb;

        require_once ABSPATH . 'wp-admin/includes/upgrade.php';

        $charset_collate = $wpdb->get_charset_collate();

        $tables = self::get_schema_tables( $charset_collate );

        foreach ( $tables as $table_sql ) {
            dbDelta( $table_sql );
        }

        $stored_version = (int) get_option( 'cpo_schema_version', 0 );
        if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
            error_log(
                sprintf(
                    'CPO schema migration starting: %d -> %d.',
                    $stored_version,
                    CPO_SCHEMA_VERSION
                )
            );
        }

        $updated = update_option( 'cpo_schema_version', CPO_SCHEMA_VERSION );

        if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
            if ( $updated ) {
                error_log(
                    sprintf(
                        'CPO schema migration completed: %d -> %d.',
                        $stored_version,
                        CPO_SCHEMA_VERSION
                    )
                );
            } else {
                error_log(
                    sprintf(
                        'CPO schema migration failed to update version: %d -> %d.',
                        $stored_version,
                        CPO_SCHEMA_VERSION
                    )
                );
            }
        }

        $role = get_role( 'administrator' );
        if ( $role && ! $role->has_cap( 'manage_cpo_offset' ) ) {
            $role->add_cap( 'manage_cpo_offset' );
        }
    }

    public static function maybe_update_schema() {
        self::maybe_update_schema_versioned();
    }

    public static function maybe_update_schema_versioned(): void {
        global $wpdb;

        $stored_version = (int) get_option( 'cpo_schema_version', 0 );
        if ( $stored_version >= CPO_SCHEMA_VERSION ) {
            return;
        }

        if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
            error_log(
                sprintf(
                    'CPO schema migration starting: %d -> %d.',
                    $stored_version,
                    CPO_SCHEMA_VERSION
                )
            );
        }

        require_once ABSPATH . 'wp-admin/includes/upgrade.php';

        $charset_collate = $wpdb->get_charset_collate();

        $tables = self::get_schema_tables( $charset_collate );

        foreach ( $tables as $table_sql ) {
            dbDelta( $table_sql );
        }

        $updated = update_option( 'cpo_schema_version', CPO_SCHEMA_VERSION );

        if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
            if ( $updated ) {
                error_log(
                    sprintf(
                        'CPO schema migration completed: %d -> %d.',
                        $stored_version,
                        CPO_SCHEMA_VERSION
                    )
                );
            } else {
                error_log(
                    sprintf(
                        'CPO schema migration failed to update version: %d -> %d.',
                        $stored_version,
                        CPO_SCHEMA_VERSION
                    )
                );
            }
        }
    }

    private static function get_schema_tables( string $charset_collate ): array {
        global $wpdb;

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
            rendimiento_pliegos_hora int(11) DEFAULT NULL,
            setup_min decimal(10,2) DEFAULT NULL,
            activo tinyint(1) NOT NULL DEFAULT 1,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_procesos (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            nombre varchar(190) NOT NULL,
            modo_cobro enum('por_hora','por_unidad','por_pliego','por_millar','por_m2','por_kg','fijo') NOT NULL DEFAULT 'fijo',
            costo_base decimal(14,2) NOT NULL DEFAULT 0,
            unidad varchar(40) DEFAULT NULL,
            consumo_g_m2 decimal(14,4) DEFAULT NULL,
            merma_proceso_pct decimal(5,2) DEFAULT NULL,
            setup_min decimal(10,2) DEFAULT NULL,
            activo tinyint(1) NOT NULL DEFAULT 1,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        $tables[] = "CREATE TABLE {$wpdb->prefix}cpo_presupuestos (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            core_cliente_id bigint(20) unsigned DEFAULT NULL,
            cliente_id bigint(20) unsigned DEFAULT NULL,
            cliente_texto varchar(190) DEFAULT NULL,
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
            snapshot_json longtext DEFAULT NULL,
            calc_result_json longtext DEFAULT NULL,
            snapshot_version int(11) DEFAULT NULL,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id),
            KEY core_cliente_id (core_cliente_id),
            KEY cliente_id (cliente_id)
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
            UNIQUE KEY presupuesto_id_unique (presupuesto_id),
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

        return $tables;
    }
}
