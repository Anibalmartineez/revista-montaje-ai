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
