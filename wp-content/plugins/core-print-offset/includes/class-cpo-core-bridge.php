<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Core_Bridge {
    public function get_core_status() {
        if ( defined( 'GC_CORE_GLOBAL_ACTIVE' ) && GC_CORE_GLOBAL_ACTIVE ) {
            return array(
                'active' => true,
                'filter_active' => false,
                'source' => 'GC_CORE_GLOBAL_ACTIVE',
            );
        }

        if ( defined( 'GC_CORE_GLOBAL_VERSION' ) ) {
            return array(
                'active' => true,
                'filter_active' => false,
                'source' => 'GC_CORE_GLOBAL_VERSION',
            );
        }

        if ( defined( 'CORE_GLOBAL_ACTIVE' ) && CORE_GLOBAL_ACTIVE ) {
            return array(
                'active' => true,
                'filter_active' => false,
                'source' => 'CORE_GLOBAL_ACTIVE',
            );
        }

        if ( defined( 'CORE_GLOBAL_VERSION' ) ) {
            return array(
                'active' => true,
                'filter_active' => false,
                'source' => 'CORE_GLOBAL_VERSION',
            );
        }

        $function_exists = function_exists( 'core_global_is_active' );
        $function_active = $function_exists ? core_global_is_active() : false;
        if ( $function_active ) {
            return array(
                'active' => true,
                'filter_active' => false,
                'source' => 'core_global_is_active',
            );
        }

        $filter_active = apply_filters( 'cpo_core_is_active', false );
        if ( $filter_active ) {
            return array(
                'active' => true,
                'filter_active' => true,
                'source' => 'filter',
            );
        }

        return array(
            'active' => false,
            'filter_active' => false,
            'source' => 'none',
        );
    }

    public function check_core_active() {
        $status = $this->get_core_status();
        return (bool) $status['active'];
    }

    public function get_core_debug_details() {
        $status = $this->get_core_status();
        $bootstrap_path = '';
        $bootstrap_source = '';

        if ( function_exists( 'core_global_is_active' ) ) {
            try {
                $reflection = new ReflectionFunction( 'core_global_is_active' );
                $bootstrap_path = (string) $reflection->getFileName();
                $bootstrap_source = 'core_global_is_active';
            } catch ( ReflectionException $exception ) {
                $bootstrap_path = '';
                $bootstrap_source = 'core_global_is_active';
            }
        } elseif ( function_exists( 'gc_api_is_ready' ) ) {
            try {
                $reflection = new ReflectionFunction( 'gc_api_is_ready' );
                $bootstrap_path = (string) $reflection->getFileName();
                $bootstrap_source = 'gc_api_is_ready';
            } catch ( ReflectionException $exception ) {
                $bootstrap_path = '';
                $bootstrap_source = 'gc_api_is_ready';
            }
        }

        return array(
            'filter_active' => $status['filter_active'],
            'function_exists' => function_exists( 'core_global_is_active' ),
            'function_active' => function_exists( 'core_global_is_active' ) ? core_global_is_active() : false,
            'gc_core_global_active_defined' => defined( 'GC_CORE_GLOBAL_ACTIVE' ),
            'gc_core_global_active_value' => defined( 'GC_CORE_GLOBAL_ACTIVE' ) ? GC_CORE_GLOBAL_ACTIVE : null,
            'core_global_active_defined' => defined( 'CORE_GLOBAL_ACTIVE' ),
            'core_global_active_value' => defined( 'CORE_GLOBAL_ACTIVE' ) ? CORE_GLOBAL_ACTIVE : null,
            'core_global_version_defined' => defined( 'CORE_GLOBAL_VERSION' ),
            'gc_core_global_version_defined' => defined( 'GC_CORE_GLOBAL_VERSION' ),
            'bootstrap_source' => $bootstrap_source,
            'bootstrap_path' => $bootstrap_path,
            'active_source' => $status['source'],
        );
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

    public function get_core_clients_list(): array {
        if ( ! $this->check_core_active() ) {
            return array();
        }

        $cache_key = 'core_clients_list';
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return is_array( $cached ) ? $cached : array();
        }

        $clients = $this->get_core_clients();
        if ( is_wp_error( $clients ) || ! is_array( $clients ) ) {
            $clients = $this->query_core_clients_table();
        }

        if ( empty( $clients ) || ! is_array( $clients ) ) {
            return array();
        }

        $normalized = array();

        $is_list = isset( $clients[0] ) && is_array( $clients[0] );
        if ( $is_list ) {
            foreach ( $clients as $client ) {
                if ( ! is_array( $client ) ) {
                    continue;
                }
                $client_id = (int) ( $client['id'] ?? $client['cliente_id'] ?? 0 );
                $client_name = $client['nombre'] ?? $client['name'] ?? '';
                if ( $client_id && $client_name !== '' ) {
                    $normalized[] = array(
                        'id' => $client_id,
                        'nombre' => $client_name,
                    );
                }
            }
        } else {
            foreach ( $clients as $client_id => $client_name ) {
                if ( ! is_numeric( $client_id ) ) {
                    continue;
                }
                $client_name = is_scalar( $client_name ) ? (string) $client_name : '';
                if ( $client_name === '' ) {
                    continue;
                }
                $normalized[] = array(
                    'id' => (int) $client_id,
                    'nombre' => $client_name,
                );
            }
        }

        usort(
            $normalized,
            function ( $a, $b ) {
                return strcasecmp( $a['nombre'], $b['nombre'] );
            }
        );

        wp_cache_set( $cache_key, $normalized, 'cpo', 300 );

        return $normalized;
    }

    private function query_core_clients_table(): array {
        if ( ! function_exists( 'gc_get_table' ) ) {
            return array();
        }

        global $wpdb;
        $table = gc_get_table( 'gc_clientes' );
        $exists = $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $table ) );
        if ( ! $exists ) {
            return array();
        }

        return $wpdb->get_results( "SELECT id, nombre FROM {$table} ORDER BY nombre ASC", ARRAY_A );
    }
}
