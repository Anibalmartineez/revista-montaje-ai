<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Core_Bridge {
    public function check_core_active() {
        if ( apply_filters( 'cpo_core_is_active', false ) ) {
            return true;
        }

        if ( function_exists( 'core_global_is_active' ) && core_global_is_active() ) {
            return true;
        }

        if ( defined( 'CORE_GLOBAL_ACTIVE' ) && CORE_GLOBAL_ACTIVE ) {
            return true;
        }

        if ( function_exists( 'core_global_init' ) ) {
            return true;
        }

        return false;
    }

    public function has_core_api() {
        $create_callback  = apply_filters( 'cpo_core_create_document_callback', 'core_global_create_document' );
        $clients_callback = apply_filters( 'cpo_core_get_clients_callback', 'core_global_get_clients' );

        $create_available  = is_string( $create_callback ) && function_exists( $create_callback );
        $clients_available = is_string( $clients_callback ) && function_exists( $clients_callback );

        return $create_available && $clients_available;
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
