<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Core_Bridge {
    public function check_core_active() {
        if ( function_exists( 'core_global_init' ) || defined( 'CORE_GLOBAL_VERSION' ) ) {
            return true;
        }

        return false;
    }

    public function create_core_document( $args ) {
        $callback = apply_filters( 'cpo_core_create_document_callback', 'core_global_create_document' );

        if ( is_string( $callback ) && function_exists( $callback ) ) {
            return call_user_func( $callback, $args );
        }

        return new WP_Error( 'cpo_core_missing', __( 'Core API no disponible', 'core-print-offset' ) );
    }

    public function get_core_clients() {
        $callback = apply_filters( 'cpo_core_get_clients_callback', 'core_global_get_clients' );

        if ( is_string( $callback ) && function_exists( $callback ) ) {
            return call_user_func( $callback );
        }

        return new WP_Error( 'cpo_core_missing', __( 'Core API no disponible', 'core-print-offset' ) );
    }
}
