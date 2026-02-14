<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

function cpo_get_table_name( $suffix ) {
    global $wpdb;

    return $wpdb->prefix . 'cpo_' . $suffix;
}

function cpo_now() {
    return current_time( 'mysql' );
}

function cpo_get_decimal( $value ) {
    return (float) str_replace( ',', '.', $value );
}

function cpo_admin_notice( $message, $type = 'info' ) {
    add_action(
        'admin_notices',
        function () use ( $message, $type ) {
            printf(
                '<div class="notice notice-%1$s"><p>%2$s</p></div>',
                esc_attr( $type ),
                esc_html( $message )
            );
        }
    );
}

function cpo_get_cache_bust_version(): string {
    $version = (int) get_option( 'cpo_cache_bust_version', 1 );

    return (string) max( 1, $version );
}

function cpo_bump_cache_bust_version(): void {
    $version = (int) get_option( 'cpo_cache_bust_version', 1 );
    $version++;
    update_option( 'cpo_cache_bust_version', (string) $version );
}

function cpo_get_cache_key( string $key ): string {
    return sprintf( '%s:%s', cpo_get_cache_bust_version(), $key );
}

function cpo_get_cache_version( string $group ): string {
    $key = 'cpo_cache_version_' . $group;
    $cache_key = cpo_get_cache_key( $key );
    $version = wp_cache_get( $cache_key, 'cpo' );
    if ( ! $version ) {
        $version = (string) get_option( $key, '1' );
        wp_cache_set( $cache_key, $version, 'cpo' );
    }

    return (string) $version;
}

function cpo_bump_cache_version( string $group ): void {
    $key = 'cpo_cache_version_' . $group;
    $cache_key = cpo_get_cache_key( $key );
    $version = (int) get_option( $key, 1 );
    $version++;
    update_option( $key, (string) $version );
    wp_cache_set( $cache_key, (string) $version, 'cpo' );
}

function cpo_build_presupuesto_payload( array $raw, array $options = array() ): array {
    $options = wp_parse_args(
        $options,
        array(
            'allow_machine_default' => true,
        )
    );

    $payload = array();

    $cliente_id_raw = $raw['cliente_id'] ?? 0;
    $payload['cliente_id'] = is_numeric( $cliente_id_raw ) ? (int) $cliente_id_raw : 0;
    $payload['cliente_texto'] = sanitize_text_field( wp_unslash( $raw['cliente_texto'] ?? '' ) );

    $descripcion_raw = $raw['descripcion'] ?? ( $raw['producto'] ?? '' );
    $payload['descripcion'] = sanitize_text_field( wp_unslash( $descripcion_raw ) );

    $payload['cantidad'] = max( 1, (int) ( $raw['cantidad'] ?? 1 ) );
    $payload['ancho_mm'] = cpo_get_decimal( wp_unslash( $raw['ancho_mm'] ?? ( $raw['ancho_final_mm'] ?? 0 ) ) );
    $payload['alto_mm'] = cpo_get_decimal( wp_unslash( $raw['alto_mm'] ?? ( $raw['alto_final_mm'] ?? 0 ) ) );
    $payload['colores'] = sanitize_text_field( wp_unslash( $raw['colores'] ?? '4/0' ) );
    $payload['sangrado_mm'] = cpo_get_decimal( wp_unslash( $raw['sangrado_mm'] ?? 0 ) );
    $payload['material_id'] = (int) ( $raw['material_id'] ?? 0 );
    $payload['pliego_formato'] = sanitize_text_field( wp_unslash( $raw['pliego_formato'] ?? '' ) );
    $payload['pliego_ancho_mm'] = cpo_get_decimal( wp_unslash( $raw['pliego_ancho_mm'] ?? 0 ) );
    $payload['pliego_alto_mm'] = cpo_get_decimal( wp_unslash( $raw['pliego_alto_mm'] ?? 0 ) );
    $payload['pliego_personalizado'] = ! empty( $raw['pliego_personalizado'] ) && $raw['pliego_personalizado'] !== '0';
    $payload['formas_por_pliego'] = max( 1, (int) ( $raw['formas_por_pliego'] ?? 1 ) );
    $payload['merma_pct'] = max( 0, cpo_get_decimal( wp_unslash( $raw['merma_pct'] ?? 0 ) ) );
    $payload['margin_pct'] = max(
        0,
        cpo_get_decimal( wp_unslash( $raw['margin_pct'] ?? ( $raw['margen_pct'] ?? 0 ) ) )
    );

    if ( array_key_exists( 'maquina_id', $raw ) && $raw['maquina_id'] !== '' ) {
        $payload['maquina_id'] = (int) $raw['maquina_id'];
    } else {
        $payload['maquina_id'] = null;
    }

    $payload['horas_maquina'] = max( 0, cpo_get_decimal( wp_unslash( $raw['horas_maquina'] ?? 0 ) ) );
    $payload['costo_hora'] = max( 0, cpo_get_decimal( wp_unslash( $raw['costo_hora'] ?? 0 ) ) );
    $payload['allow_machine_default'] = (bool) $options['allow_machine_default'];

    $processes = $raw['procesos'] ?? array();
    if ( ! is_array( $processes ) ) {
        $processes = array();
    }
    $payload['procesos'] = array_values( array_filter( array_map( 'intval', $processes ) ) );

    $payload['work_type'] = sanitize_key( wp_unslash( $raw['work_type'] ?? 'afiche_folleto' ) );
    if ( '' === $payload['work_type'] ) {
        $payload['work_type'] = 'afiche_folleto';
    }
    $legacy_work_types = array(
        'revista' => 'revista_catalogo',
        'folleto' => 'afiche_folleto',
        'etiqueta' => 'etiqueta_offset',
        'caja' => 'caja_packaging',
        'troquel' => 'caja_packaging',
    );
    if ( isset( $legacy_work_types[ $payload['work_type'] ] ) ) {
        $payload['work_type'] = $legacy_work_types[ $payload['work_type'] ];
    }
    $payload['paginas'] = max( 0, (int) ( $raw['paginas'] ?? 0 ) );
    $payload['encuadernacion'] = sanitize_text_field( wp_unslash( $raw['encuadernacion'] ?? '' ) );
    $payload['troquel'] = sanitize_text_field( wp_unslash( $raw['troquel'] ?? '' ) );
    $payload['material_bobina'] = sanitize_text_field( wp_unslash( $raw['material_bobina'] ?? '' ) );
    $payload['anilox'] = sanitize_text_field( wp_unslash( $raw['anilox'] ?? '' ) );
    $payload['cilindro'] = sanitize_text_field( wp_unslash( $raw['cilindro'] ?? '' ) );
    $payload['pliego_doble'] = ! empty( $raw['pliego_doble'] ) && '0' !== (string) $raw['pliego_doble'];
    $payload['costo_troquel'] = max( 0, cpo_get_decimal( wp_unslash( $raw['costo_troquel'] ?? 0 ) ) );
    $payload['merma_troquel_extra'] = max( 0, cpo_get_decimal( wp_unslash( $raw['merma_troquel_extra'] ?? 0 ) ) );

    return $payload;
}

function cpo_get_presupuesto_snapshot_payload( int $presupuesto_id ): array {
    if ( ! $presupuesto_id ) {
        return array();
    }

    global $wpdb;

    $snapshot = $wpdb->get_var(
        $wpdb->prepare( "SELECT snapshot_json FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id )
    );

    if ( $snapshot ) {
        $decoded = json_decode( $snapshot, true );
        if ( is_array( $decoded ) ) {
            return $decoded;
        }
    }

    $item_snapshot = $wpdb->get_var(
        $wpdb->prepare(
            "SELECT snapshot_json FROM {$wpdb->prefix}cpo_presupuesto_items WHERE presupuesto_id = %d AND tipo = 'otro' ORDER BY id DESC LIMIT 1",
            $presupuesto_id
        )
    );
    if ( $item_snapshot ) {
        $decoded = json_decode( $item_snapshot, true );
        if ( is_array( $decoded ) ) {
            if ( isset( $decoded['inputs'] ) && is_array( $decoded['inputs'] ) ) {
                if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
                    error_log(
                        sprintf( 'CPO snapshot payload for presupuesto %d recovered from items.', $presupuesto_id )
                    );
                }
                return $decoded['inputs'];
            }
            return $decoded;
        }
    }

    $presupuesto = $wpdb->get_row(
        $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
        ARRAY_A
    );
    if ( ! $presupuesto ) {
        return array();
    }

    if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
        error_log(
            sprintf( 'CPO snapshot payload for presupuesto %d recovered from columns.', $presupuesto_id )
        );
    }

    return array(
        'descripcion' => $presupuesto['producto'] ?? $presupuesto['titulo'] ?? '',
        'cantidad'    => (int) ( $presupuesto['cantidad'] ?? 0 ),
        'material_id' => (int) ( $presupuesto['material_id'] ?? 0 ),
        'colores'     => $presupuesto['colores'] ?? '',
        'margin_pct'  => $presupuesto['margen_pct'] ?? 0,
    );
}

function cpo_duplicate_presupuesto( int $presupuesto_id, ?int $created_by = null ) {
    if ( ! $presupuesto_id ) {
        return new WP_Error( 'cpo_invalid_presupuesto', __( 'Presupuesto inválido.', 'core-print-offset' ) );
    }

    global $wpdb;

    $presupuesto = $wpdb->get_row(
        $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
        ARRAY_A
    );
    if ( ! $presupuesto ) {
        return new WP_Error( 'cpo_presupuesto_missing', __( 'Presupuesto no encontrado.', 'core-print-offset' ) );
    }

    $now = cpo_now();
    $titulo = $presupuesto['titulo'] ? sprintf( __( '%s (copia)', 'core-print-offset' ), $presupuesto['titulo'] ) : __( 'Presupuesto Offset (copia)', 'core-print-offset' );
    $payload = $presupuesto;
    unset( $payload['id'] );
    $payload['titulo'] = $titulo;
    $payload['estado'] = 'borrador';
    $payload['core_documento_id'] = null;
    if ( null !== $created_by ) {
        $payload['created_by'] = $created_by;
    }
    $payload['created_at'] = $now;
    $payload['updated_at'] = $now;

    $inserted = $wpdb->insert( $wpdb->prefix . 'cpo_presupuestos', $payload );
    if ( ! $inserted ) {
        return new WP_Error( 'cpo_presupuesto_duplicate_failed', __( 'No se pudo duplicar el presupuesto.', 'core-print-offset' ) );
    }

    $new_id = (int) $wpdb->insert_id;

    $items = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT tipo, referencia_id, descripcion, cantidad, unitario, subtotal, snapshot_json FROM {$wpdb->prefix}cpo_presupuesto_items WHERE presupuesto_id = %d",
            $presupuesto_id
        ),
        ARRAY_A
    );

    foreach ( $items as $item ) {
        $wpdb->insert(
            $wpdb->prefix . 'cpo_presupuesto_items',
            array(
                'presupuesto_id' => $new_id,
                'tipo'           => $item['tipo'],
                'referencia_id'  => $item['referencia_id'],
                'descripcion'    => $item['descripcion'],
                'cantidad'       => $item['cantidad'],
                'unitario'       => $item['unitario'],
                'subtotal'       => $item['subtotal'],
                'snapshot_json'  => $item['snapshot_json'],
                'created_at'     => $now,
            )
        );
    }

    return $new_id;
}

function cpo_get_offset_dashboard_url(): string {
    $url = (string) apply_filters( 'cpo_offset_dashboard_url', '' );
    if ( ! $url ) {
        $url = home_url( '/' );
    }

    return $url;
}
