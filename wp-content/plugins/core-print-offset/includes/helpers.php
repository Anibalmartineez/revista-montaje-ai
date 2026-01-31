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

    return $payload;
}
