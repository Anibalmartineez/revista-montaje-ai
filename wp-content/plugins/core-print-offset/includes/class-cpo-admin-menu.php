<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Admin_Menu {
    private $core_bridge;
    private $core_active;
    private $core_api_available;
    private $notices = array();

    public function __construct() {
        $this->core_bridge = new CPO_Core_Bridge();
        $this->core_active = false;
        $this->core_api_available = false;

        add_action( 'plugins_loaded', array( $this, 'refresh_core_status' ), 20 );
        add_action( 'admin_notices', array( $this, 'maybe_show_core_notice' ) );
    }

    public function refresh_core_status() {
        $this->core_active = $this->core_bridge->check_core_active();
        $this->core_api_available = $this->core_active && $this->core_bridge->has_core_api();
    }

    public function register_menu() {
        $capability = 'manage_cpo_offset';

        add_menu_page(
            __( 'Offset (Imprentas)', 'core-print-offset' ),
            __( 'Offset (Imprentas)', 'core-print-offset' ),
            $capability,
            'cpo-dashboard',
            array( $this, 'render_dashboard' ),
            'dashicons-media-document'
        );

        add_submenu_page( 'cpo-dashboard', __( 'Dashboard', 'core-print-offset' ), __( 'Dashboard', 'core-print-offset' ), $capability, 'cpo-dashboard', array( $this, 'render_dashboard' ) );
        add_submenu_page( 'cpo-dashboard', __( 'Materiales', 'core-print-offset' ), __( 'Materiales', 'core-print-offset' ), $capability, 'cpo-materiales', array( $this, 'render_materiales' ) );
        add_submenu_page( 'cpo-dashboard', __( 'Máquinas', 'core-print-offset' ), __( 'Máquinas', 'core-print-offset' ), $capability, 'cpo-maquinas', array( $this, 'render_maquinas' ) );
        add_submenu_page( 'cpo-dashboard', __( 'Procesos', 'core-print-offset' ), __( 'Procesos', 'core-print-offset' ), $capability, 'cpo-procesos', array( $this, 'render_procesos' ) );
        add_submenu_page( 'cpo-dashboard', __( 'Presupuestos', 'core-print-offset' ), __( 'Presupuestos', 'core-print-offset' ), $capability, 'cpo-presupuestos', array( $this, 'render_presupuestos' ) );
        add_submenu_page( 'cpo-dashboard', __( 'Órdenes de Trabajo', 'core-print-offset' ), __( 'Órdenes de Trabajo', 'core-print-offset' ), $capability, 'cpo-ordenes', array( $this, 'render_ordenes' ) );
    }

    public function enqueue_assets( $hook ) {
        if ( strpos( $hook, 'cpo-' ) === false ) {
            return;
        }

        wp_enqueue_style( 'cpo-admin', CPO_PLUGIN_URL . 'admin/assets/css/admin.css', array(), CPO_VERSION );
        wp_enqueue_script( 'cpo-admin', CPO_PLUGIN_URL . 'admin/assets/js/admin.js', array( 'jquery' ), CPO_VERSION, true );
    }

    public function maybe_show_core_notice() {
        $this->refresh_core_status();

        if ( ! $this->core_active ) {
            echo '<div class="notice notice-warning"><p>' . esc_html__( 'Core Global no está activo. Activa el plugin Gestión Core Global para habilitar las pantallas de Offset.', 'core-print-offset' ) . '</p></div>';
        } elseif ( ! $this->core_api_available ) {
            echo '<div class="notice notice-warning"><p>' . esc_html__( 'Core activo, pero falta API (clientes/documentos).', 'core-print-offset' ) . '</p></div>';
        }

        $this->maybe_show_core_debug();
    }

    private function maybe_show_core_debug() {
        if ( ! defined( 'CPO_DEBUG_CORE' ) || ! CPO_DEBUG_CORE ) {
            return;
        }

        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }

        $details = $this->core_bridge->get_core_debug_details();
        $lines = array(
            sprintf(
                'cpo_core_is_active: %s',
                $details['filter_active'] ? 'true' : 'false'
            ),
            sprintf(
                'core_global_is_active(): %s',
                $details['function_exists'] ? ( $details['function_active'] ? 'true' : 'false' ) : 'missing'
            ),
            sprintf(
                'GC_CORE_GLOBAL_ACTIVE: %s',
                $details['gc_core_global_active_defined'] ? ( $details['gc_core_global_active_value'] ? 'true' : 'false' ) : 'undefined'
            ),
            sprintf(
                'CORE_GLOBAL_ACTIVE: %s',
                $details['core_global_active_defined'] ? ( $details['core_global_active_value'] ? 'true' : 'false' ) : 'undefined'
            ),
            sprintf(
                'CORE_GLOBAL_VERSION: %s',
                $details['core_global_version_defined'] ? 'defined' : 'undefined'
            ),
            sprintf(
                'GC_CORE_GLOBAL_VERSION: %s',
                $details['gc_core_global_version_defined'] ? 'defined' : 'undefined'
            ),
            sprintf(
                'Core bootstrap: %s',
                $details['bootstrap_path'] ? $details['bootstrap_path'] : 'unknown'
            ),
            sprintf(
                'Core active source: %s',
                $details['active_source']
            ),
        );

        $output = implode( '<br>', array_map( 'esc_html', $lines ) );
        echo '<div class="notice notice-info"><p>' . $output . '</p></div>';
    }

    private function add_notice( $message, $type = 'success' ) {
        $this->notices[] = array(
            'message' => $message,
            'type'    => $type,
        );
    }

    private function render_notices() {
        foreach ( $this->notices as $notice ) {
            printf(
                '<div class="notice notice-%1$s"><p>%2$s</p></div>',
                esc_attr( $notice['type'] ),
                esc_html( $notice['message'] )
            );
        }
    }

    public function render_dashboard() {
        $data = $this->get_dashboard_data();
        $this->render_notices();
        include CPO_PLUGIN_DIR . 'admin/views/dashboard.php';
    }

    public function render_materiales() {
        $data = $this->handle_materiales();
        $this->render_notices();
        include CPO_PLUGIN_DIR . 'admin/views/materiales.php';
    }

    public function render_maquinas() {
        $data = $this->handle_maquinas();
        $this->render_notices();
        include CPO_PLUGIN_DIR . 'admin/views/maquinas.php';
    }

    public function render_procesos() {
        $data = $this->handle_procesos();
        $this->render_notices();
        include CPO_PLUGIN_DIR . 'admin/views/procesos.php';
    }

    public function render_presupuestos() {
        $data = $this->handle_presupuestos();
        $this->render_notices();
        include CPO_PLUGIN_DIR . 'admin/views/presupuestos.php';
    }

    public function render_ordenes() {
        $data = $this->handle_ordenes();
        $this->render_notices();
        include CPO_PLUGIN_DIR . 'admin/views/ordenes.php';
    }

    private function get_dashboard_data() {
        global $wpdb;

        return array(
            'materiales'   => (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->prefix}cpo_materiales" ),
            'maquinas'     => (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->prefix}cpo_maquinas" ),
            'procesos'     => (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->prefix}cpo_procesos" ),
            'presupuestos' => (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->prefix}cpo_presupuestos" ),
            'ordenes'      => (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->prefix}cpo_ordenes" ),
        );
    }

    private function handle_materiales() {
        global $wpdb;

        $data = array(
            'materiales' => array(),
            'editing'    => null,
            'core_active' => $this->core_active,
        );

        if ( ! $this->core_active ) {
            $data['materiales'] = $this->get_materiales_list();
            return $data;
        }

        if ( isset( $_POST['cpo_material_save'] ) && check_admin_referer( 'cpo_material_save', 'cpo_material_nonce' ) ) {
            $id             = isset( $_POST['material_id'] ) ? intval( $_POST['material_id'] ) : 0;
            $nombre         = sanitize_text_field( wp_unslash( $_POST['nombre'] ?? '' ) );
            $gramaje        = sanitize_text_field( wp_unslash( $_POST['gramaje'] ?? '' ) );
            $formato_base   = sanitize_text_field( wp_unslash( $_POST['formato_base'] ?? '' ) );
            $unidad_costo   = sanitize_text_field( wp_unslash( $_POST['unidad_costo'] ?? 'pliego' ) );
            $desperdicio    = cpo_get_decimal( wp_unslash( $_POST['desperdicio_pct'] ?? 0 ) );
            $activo         = isset( $_POST['activo'] ) ? 1 : 0;
            $now            = cpo_now();

            $payload = array(
                'nombre'        => $nombre,
                'gramaje'       => $gramaje,
                'formato_base'  => $formato_base,
                'unidad_costo'  => $unidad_costo,
                'desperdicio_pct' => $desperdicio,
                'activo'        => $activo,
                'updated_at'    => $now,
            );

            if ( $id > 0 ) {
                $wpdb->update( $wpdb->prefix . 'cpo_materiales', $payload, array( 'id' => $id ) );
                $this->add_notice( __( 'Material actualizado.', 'core-print-offset' ) );
            } else {
                $payload['created_at'] = $now;
                $wpdb->insert( $wpdb->prefix . 'cpo_materiales', $payload );
                $this->add_notice( __( 'Material creado.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_POST['cpo_material_price_add'] ) && check_admin_referer( 'cpo_material_price_add', 'cpo_material_price_nonce' ) ) {
            $material_id = intval( $_POST['material_price_material_id'] ?? 0 );
            $precio      = cpo_get_decimal( wp_unslash( $_POST['precio'] ?? 0 ) );
            $moneda      = sanitize_text_field( wp_unslash( $_POST['moneda'] ?? 'PYG' ) );
            $proveedor   = sanitize_text_field( wp_unslash( $_POST['proveedor'] ?? '' ) );

            if ( $material_id > 0 ) {
                $wpdb->insert(
                    $wpdb->prefix . 'cpo_material_precios',
                    array(
                        'material_id'  => $material_id,
                        'precio'       => $precio,
                        'moneda'       => $moneda,
                        'proveedor'    => $proveedor,
                        'vigente_desde' => cpo_now(),
                        'created_at'   => cpo_now(),
                    )
                );
                $this->add_notice( __( 'Precio agregado.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['material_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'toggle_material' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_toggle_material' ) ) {
                $id     = intval( $_GET['material_id'] );
                $activo = (int) $wpdb->get_var( $wpdb->prepare( "SELECT activo FROM {$wpdb->prefix}cpo_materiales WHERE id = %d", $id ) );
                $wpdb->update( $wpdb->prefix . 'cpo_materiales', array( 'activo' => $activo ? 0 : 1, 'updated_at' => cpo_now() ), array( 'id' => $id ) );
                $this->add_notice( __( 'Estado actualizado.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['material_id'] ) && $_GET['cpo_action'] === 'edit_material' ) {
            $id = intval( $_GET['material_id'] );
            $data['editing'] = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_materiales WHERE id = %d", $id ), ARRAY_A );
        }

        $data['materiales'] = $this->get_materiales_list();

        return $data;
    }

    private function get_materiales_list() {
        global $wpdb;

        return $wpdb->get_results(
            "SELECT m.*, (
                SELECT precio FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS precio_vigente
            FROM {$wpdb->prefix}cpo_materiales m
            ORDER BY m.created_at DESC",
            ARRAY_A
        );
    }

    private function handle_maquinas() {
        global $wpdb;

        $data = array(
            'maquinas' => array(),
            'editing'  => null,
            'core_active' => $this->core_active,
        );

        if ( ! $this->core_active ) {
            $data['maquinas'] = $this->get_maquinas_list();
            return $data;
        }

        if ( isset( $_POST['cpo_maquina_save'] ) && check_admin_referer( 'cpo_maquina_save', 'cpo_maquina_nonce' ) ) {
            $id                  = isset( $_POST['maquina_id'] ) ? intval( $_POST['maquina_id'] ) : 0;
            $nombre              = sanitize_text_field( wp_unslash( $_POST['nombre'] ?? '' ) );
            $tipo                = sanitize_text_field( wp_unslash( $_POST['tipo'] ?? '' ) );
            $costo_hora          = cpo_get_decimal( wp_unslash( $_POST['costo_hora'] ?? 0 ) );
            $rendimiento         = isset( $_POST['rendimiento_hora'] ) ? intval( $_POST['rendimiento_hora'] ) : null;
            $rendimiento_pliegos_raw = isset( $_POST['rendimiento_pliegos_hora'] ) ? trim( (string) wp_unslash( $_POST['rendimiento_pliegos_hora'] ) ) : '';
            // Solo persistir rendimiento_pliegos_hora si tiene valor > 0; '' debe quedar como null para permitir fallback.
            $rendimiento_pliegos = $rendimiento_pliegos_raw !== '' ? intval( $rendimiento_pliegos_raw ) : null;
            if ( $rendimiento_pliegos !== null && $rendimiento_pliegos <= 0 ) {
                $rendimiento_pliegos = null;
            }
            $setup_min           = cpo_get_decimal( wp_unslash( $_POST['setup_min'] ?? 0 ) );
            $activo              = isset( $_POST['activo'] ) ? 1 : 0;
            $now                 = cpo_now();

            $payload = array(
                'nombre'                    => $nombre,
                'tipo'                      => $tipo,
                'costo_hora'                => $costo_hora,
                'rendimiento_hora'          => $rendimiento,
                'rendimiento_pliegos_hora'  => $rendimiento_pliegos,
                'setup_min'                 => $setup_min,
                'activo'                    => $activo,
                'updated_at'                => $now,
            );

            if ( $id > 0 ) {
                $wpdb->update( $wpdb->prefix . 'cpo_maquinas', $payload, array( 'id' => $id ) );
                $this->add_notice( __( 'Máquina actualizada.', 'core-print-offset' ) );
            } else {
                $payload['created_at'] = $now;
                $wpdb->insert( $wpdb->prefix . 'cpo_maquinas', $payload );
                $this->add_notice( __( 'Máquina creada.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['maquina_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'toggle_maquina' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_toggle_maquina' ) ) {
                $id     = intval( $_GET['maquina_id'] );
                $activo = (int) $wpdb->get_var( $wpdb->prepare( "SELECT activo FROM {$wpdb->prefix}cpo_maquinas WHERE id = %d", $id ) );
                $wpdb->update( $wpdb->prefix . 'cpo_maquinas', array( 'activo' => $activo ? 0 : 1, 'updated_at' => cpo_now() ), array( 'id' => $id ) );
                $this->add_notice( __( 'Estado actualizado.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['maquina_id'] ) && $_GET['cpo_action'] === 'edit_maquina' ) {
            $id = intval( $_GET['maquina_id'] );
            $data['editing'] = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_maquinas WHERE id = %d", $id ), ARRAY_A );
        }

        $data['maquinas'] = $this->get_maquinas_list();

        return $data;
    }

    private function get_maquinas_list() {
        global $wpdb;

        return $wpdb->get_results( "SELECT * FROM {$wpdb->prefix}cpo_maquinas ORDER BY created_at DESC", ARRAY_A );
    }

    private function handle_procesos() {
        global $wpdb;

        $data = array(
            'procesos' => array(),
            'editing'  => null,
            'core_active' => $this->core_active,
        );

        if ( ! $this->core_active ) {
            $data['procesos'] = $this->get_procesos_list();
            return $data;
        }

        if ( isset( $_POST['cpo_proceso_save'] ) && check_admin_referer( 'cpo_proceso_save', 'cpo_proceso_nonce' ) ) {
            $id                 = isset( $_POST['proceso_id'] ) ? intval( $_POST['proceso_id'] ) : 0;
            $nombre             = sanitize_text_field( wp_unslash( $_POST['nombre'] ?? '' ) );
            $modo_cobro         = sanitize_text_field( wp_unslash( $_POST['modo_cobro'] ?? 'fijo' ) );
            $costo_base         = cpo_get_decimal( wp_unslash( $_POST['costo_base'] ?? 0 ) );
            $unidad             = sanitize_text_field( wp_unslash( $_POST['unidad'] ?? '' ) );
            $consumo_g_m2        = cpo_get_decimal( wp_unslash( $_POST['consumo_g_m2'] ?? 0 ) );
            $merma_proceso_pct  = cpo_get_decimal( wp_unslash( $_POST['merma_proceso_pct'] ?? 0 ) );
            $setup_min          = cpo_get_decimal( wp_unslash( $_POST['setup_min'] ?? 0 ) );
            $activo             = isset( $_POST['activo'] ) ? 1 : 0;
            $now                = cpo_now();

            $payload = array(
                'nombre'            => $nombre,
                'modo_cobro'        => $modo_cobro,
                'costo_base'        => $costo_base,
                'unidad'            => $unidad,
                'consumo_g_m2'      => $consumo_g_m2 ?: null,
                'merma_proceso_pct' => $merma_proceso_pct ?: null,
                'setup_min'         => $setup_min ?: null,
                'activo'            => $activo,
                'updated_at'        => $now,
            );

            if ( $id > 0 ) {
                $wpdb->update( $wpdb->prefix . 'cpo_procesos', $payload, array( 'id' => $id ) );
                $this->add_notice( __( 'Proceso actualizado.', 'core-print-offset' ) );
            } else {
                $payload['created_at'] = $now;
                $wpdb->insert( $wpdb->prefix . 'cpo_procesos', $payload );
                $this->add_notice( __( 'Proceso creado.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['proceso_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'toggle_proceso' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_toggle_proceso' ) ) {
                $id     = intval( $_GET['proceso_id'] );
                $activo = (int) $wpdb->get_var( $wpdb->prepare( "SELECT activo FROM {$wpdb->prefix}cpo_procesos WHERE id = %d", $id ) );
                $wpdb->update( $wpdb->prefix . 'cpo_procesos', array( 'activo' => $activo ? 0 : 1, 'updated_at' => cpo_now() ), array( 'id' => $id ) );
                $this->add_notice( __( 'Estado actualizado.', 'core-print-offset' ) );
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['proceso_id'] ) && $_GET['cpo_action'] === 'edit_proceso' ) {
            $id = intval( $_GET['proceso_id'] );
            $data['editing'] = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_procesos WHERE id = %d", $id ), ARRAY_A );
        }

        $data['procesos'] = $this->get_procesos_list();

        return $data;
    }

    private function get_procesos_list() {
        global $wpdb;

        return $wpdb->get_results( "SELECT * FROM {$wpdb->prefix}cpo_procesos ORDER BY created_at DESC", ARRAY_A );
    }

    private function get_presupuesto_snapshot_payload( int $presupuesto_id ): array {
        if ( ! $presupuesto_id ) {
            return array();
        }

        global $wpdb;
        $snapshot = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT snapshot_json FROM {$wpdb->prefix}cpo_presupuesto_items WHERE presupuesto_id = %d AND tipo = 'otro' ORDER BY id DESC LIMIT 1",
                $presupuesto_id
            )
        );

        if ( ! $snapshot ) {
            return array();
        }

        $decoded = json_decode( $snapshot, true );
        if ( ! is_array( $decoded ) ) {
            return array();
        }

        return $decoded['inputs'] ?? array();
    }

    private function handle_presupuestos() {
        global $wpdb;

        $data = array(
            'presupuestos' => array(),
            'editing'      => null,
            'materiales'   => $this->get_materiales_list(),
            'procesos'     => $this->get_procesos_list(),
            'maquinas'     => $this->get_maquinas_list(),
            'core_active'  => $this->core_active,
            'core_clients' => array(),
        );

        if ( $this->core_active ) {
            $data['core_clients'] = $this->core_bridge->get_core_clients_list();
        }

        if ( $this->core_active && isset( $_POST['cpo_presupuesto_save'] ) && check_admin_referer( 'cpo_presupuesto_save', 'cpo_presupuesto_nonce' ) ) {
            $id             = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
            $cliente_id     = isset( $_POST['cliente_id'] ) ? intval( $_POST['cliente_id'] ) : 0;
            $cliente_texto  = sanitize_text_field( wp_unslash( $_POST['cliente_texto'] ?? '' ) );
            $titulo         = sanitize_text_field( wp_unslash( $_POST['titulo'] ?? '' ) );
            $producto       = sanitize_text_field( wp_unslash( $_POST['producto'] ?? '' ) );
            $formato_final  = sanitize_text_field( wp_unslash( $_POST['formato_final'] ?? '' ) );
            $cantidad       = intval( $_POST['cantidad'] ?? 0 );
            $material_id    = isset( $_POST['material_id'] ) ? intval( $_POST['material_id'] ) : null;
            $colores        = sanitize_text_field( wp_unslash( $_POST['colores'] ?? '' ) );
            $caras          = intval( $_POST['caras'] ?? 1 );
            $margen_pct     = cpo_get_decimal( wp_unslash( $_POST['margen_pct'] ?? 30 ) );
            $estado         = sanitize_text_field( wp_unslash( $_POST['estado'] ?? 'borrador' ) );
            $now            = cpo_now();
            if ( $cliente_id > 0 ) {
                $client_name = $this->get_core_client_name_from_list( $cliente_id, $data['core_clients'] );
                if ( $client_name ) {
                    $cliente_texto = $client_name;
                }
            }

            $snapshot_inputs = cpo_build_presupuesto_payload(
                $_POST,
                array(
                    'allow_machine_default' => false,
                )
            );

            $result = CPO_Calculator::calculate( $snapshot_inputs );
            $items = array();

            if ( $result['material'] ) {
                $items[] = array(
                    'tipo'        => 'papel',
                    'referencia'  => $result['material']['id'],
                    'descripcion' => sprintf( __( 'Papel: %s', 'core-print-offset' ), $result['material']['nombre'] ),
                    'cantidad'    => $result['pliegos_necesarios'],
                    'unitario'    => $result['precio_pliego'],
                    'subtotal'    => $result['costo_papel'],
                    'snapshot'    => array(
                        'material' => $result['material'],
                        'precio'   => $result['material_snapshot'],
                    ),
                );
            }

            if ( $result['maquina'] && $result['costo_maquina'] > 0 ) {
                $items[] = array(
                    'tipo'        => 'maquina',
                    'referencia'  => $result['maquina']['id'],
                    'descripcion' => sprintf( __( 'Máquina: %s', 'core-print-offset' ), $result['maquina']['nombre'] ),
                    'cantidad'    => $result['horas_maquina'],
                    'unitario'    => $result['costo_hora'],
                    'subtotal'    => $result['costo_maquina'],
                    'snapshot'    => array(
                        'horas'      => $result['horas_maquina'],
                        'costo_hora' => $result['costo_hora'],
                        'maquina'    => $result['maquina'],
                    ),
                );
            }

            if ( ! empty( $result['procesos'] ) ) {
                foreach ( $result['procesos'] as $proceso ) {
                    $items[] = array(
                        'tipo'        => 'proceso',
                        'referencia'  => $proceso['id'],
                        'descripcion' => sprintf( __( 'Proceso: %s', 'core-print-offset' ), $proceso['nombre'] ),
                        'cantidad'    => $proceso['cantidad'],
                        'unitario'    => $proceso['unitario'],
                        'subtotal'    => $proceso['subtotal'],
                        'snapshot'    => $proceso,
                    );
                }
            }

            $costo_total = $result['subtotal'];
            $precio_total = $result['total'];

            $payload = array(
                'core_cliente_id' => $cliente_id > 0 ? $cliente_id : null,
                'cliente_id'      => $cliente_id > 0 ? $cliente_id : null,
                'cliente_texto'   => $cliente_texto ?: null,
                'titulo'          => $titulo,
                'producto'        => $producto,
                'formato_final'   => $formato_final,
                'cantidad'        => $cantidad,
                'material_id'     => $material_id,
                'colores'         => $colores,
                'caras'           => $caras,
                'margen_pct'      => $margen_pct,
                'estado'          => $estado,
                'costo_total'     => $costo_total,
                'precio_total'    => $precio_total,
                'updated_at'      => $now,
            );

            if ( $id > 0 ) {
                $wpdb->update( $wpdb->prefix . 'cpo_presupuestos', $payload, array( 'id' => $id ) );
                $presupuesto_id = $id;
                $wpdb->delete( $wpdb->prefix . 'cpo_presupuesto_items', array( 'presupuesto_id' => $id ) );
                $this->add_notice( __( 'Presupuesto actualizado.', 'core-print-offset' ) );
            } else {
                $payload['created_at'] = $now;
                $wpdb->insert( $wpdb->prefix . 'cpo_presupuestos', $payload );
                $presupuesto_id = (int) $wpdb->insert_id;
                $this->add_notice( __( 'Presupuesto creado.', 'core-print-offset' ) );
            }

            foreach ( $items as $item ) {
                $wpdb->insert(
                    $wpdb->prefix . 'cpo_presupuesto_items',
                    array(
                        'presupuesto_id' => $presupuesto_id,
                        'tipo'           => $item['tipo'],
                        'referencia_id'  => $item['referencia'],
                        'descripcion'    => $item['descripcion'],
                        'cantidad'       => $item['cantidad'],
                        'unitario'       => $item['unitario'],
                        'subtotal'       => $item['subtotal'],
                        'snapshot_json'  => wp_json_encode( $item['snapshot'] ),
                        'created_at'     => $now,
                    )
                );
            }

            $snapshot_payload = array(
                'inputs'  => $snapshot_inputs,
                'totals'  => $result,
                'cliente' => $cliente_texto,
            );
            $wpdb->insert(
                $wpdb->prefix . 'cpo_presupuesto_items',
                array(
                    'presupuesto_id' => $presupuesto_id,
                    'tipo'           => 'otro',
                    'referencia_id'  => null,
                    'descripcion'    => __( 'Snapshot presupuesto', 'core-print-offset' ),
                    'cantidad'       => 1,
                    'unitario'       => 0,
                    'subtotal'       => 0,
                    'snapshot_json'  => wp_json_encode( $snapshot_payload, JSON_UNESCAPED_UNICODE ),
                    'created_at'     => $now,
                )
            );
        }

        if ( $this->core_active && isset( $_GET['cpo_action'], $_GET['presupuesto_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'generate_document' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_generate_document' ) ) {
                $id = intval( $_GET['presupuesto_id'] );
                $presupuesto = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $id ), ARRAY_A );
                if ( $presupuesto ) {
                    $existing_core_document_id = isset( $presupuesto['core_documento_id'] ) ? (int) $presupuesto['core_documento_id'] : 0;
                    if ( $existing_core_document_id > 0 ) {
                        $this->add_notice( __( 'Este presupuesto ya tiene un documento en Core.', 'core-print-offset' ), 'warning' );
                        return $data;
                    }

                    $cliente_id = isset( $presupuesto['cliente_id'] ) ? (int) $presupuesto['cliente_id'] : 0;
                    if ( ! $cliente_id && isset( $presupuesto['core_cliente_id'] ) ) {
                        $cliente_id = (int) $presupuesto['core_cliente_id'];
                    }

                    if ( ! $cliente_id ) {
                        $this->add_notice( __( 'Selecciona un cliente de Core antes de generar el documento.', 'core-print-offset' ), 'warning' );
                        return $data;
                    }

                    $response = $this->core_bridge->create_core_document(
                        array(
                            'tipo'    => 'presupuesto',
                            'titulo'  => $presupuesto['titulo'],
                            'cliente_id' => $cliente_id,
                            'total'   => $presupuesto['precio_total'],
                        )
                    );
                    if ( is_wp_error( $response ) ) {
                        $this->add_notice( $response->get_error_message(), 'error' );
                    } else {
                        $core_documento_id = is_array( $response ) && isset( $response['id'] ) ? (int) $response['id'] : (int) $response;
                        $wpdb->update( $wpdb->prefix . 'cpo_presupuestos', array( 'core_documento_id' => $core_documento_id ), array( 'id' => $id ) );
                        $this->maybe_add_core_document_items( $core_documento_id, $id );
                        $this->add_notice( __( 'Documento generado en Core.', 'core-print-offset' ) );
                    }
                }
            }
        }

        if ( isset( $_GET['cpo_action'], $_GET['presupuesto_id'] ) && $_GET['cpo_action'] === 'edit_presupuesto' ) {
            $id = intval( $_GET['presupuesto_id'] );
            $data['editing'] = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $id ), ARRAY_A );
            $data['editing_payload'] = $this->get_presupuesto_snapshot_payload( $id );
        }

        if ( $this->core_active && isset( $_GET['cpo_action'], $_GET['presupuesto_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'convert_to_order' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_convert_order' ) ) {
                $id = intval( $_GET['presupuesto_id'] );
                $presupuesto = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $id ), ARRAY_A );
                if ( $presupuesto && $presupuesto['estado'] === 'aceptado' ) {
                    $existing_order_id = $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT id FROM {$wpdb->prefix}cpo_ordenes WHERE presupuesto_id = %d LIMIT 1",
                            $id
                        )
                    );
                    if ( $existing_order_id ) {
                        $redirect_url = add_query_arg(
                            array(
                                'page'       => 'cpo-ordenes',
                                'cpo_notice' => 'orden_exists',
                                'orden_id'   => (int) $existing_order_id,
                            ),
                            admin_url( 'admin.php' )
                        );
                        wp_safe_redirect( $redirect_url );
                        exit;
                    }
                    $wpdb->insert(
                        $wpdb->prefix . 'cpo_ordenes',
                        array(
                            'presupuesto_id' => $id,
                            'core_cliente_id' => $presupuesto['core_cliente_id'],
                            'titulo'         => $presupuesto['titulo'],
                            'estado'         => 'pendiente',
                            'created_at'     => cpo_now(),
                            'updated_at'     => cpo_now(),
                        )
                    );
                    $this->add_notice( __( 'Orden creada desde presupuesto.', 'core-print-offset' ) );
                }
            }
        }

        $data['presupuestos'] = $wpdb->get_results( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos ORDER BY created_at DESC", ARRAY_A );

        return $data;
    }

    private function get_core_client_name_from_list( int $cliente_id, array $clients ): string {
        if ( ! $cliente_id ) {
            return '';
        }

        foreach ( $clients as $client ) {
            if ( (int) ( $client['id'] ?? 0 ) === $cliente_id ) {
                return (string) ( $client['nombre'] ?? '' );
            }
        }

        return '';
    }

    private function maybe_add_core_document_items( int $documento_id, int $presupuesto_id ): void {
        if ( ! function_exists( 'gc_api_add_documento_item' ) ) {
            return;
        }

        global $wpdb;
        $items = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT descripcion, cantidad, unitario, subtotal FROM {$wpdb->prefix}cpo_presupuesto_items WHERE presupuesto_id = %d",
                $presupuesto_id
            ),
            ARRAY_A
        );

        if ( empty( $items ) ) {
            return;
        }

        foreach ( $items as $item ) {
            gc_api_add_documento_item(
                $documento_id,
                array(
                    'descripcion' => $item['descripcion'],
                    'cantidad'    => $item['cantidad'],
                    'precio_unit' => $item['unitario'],
                    'total'       => $item['subtotal'],
                )
            );
        }
    }

    private function handle_ordenes() {
        global $wpdb;

        $data = array(
            'ordenes'     => array(),
            'core_active' => $this->core_active,
        );

        if ( isset( $_GET['cpo_notice'] ) && sanitize_text_field( wp_unslash( $_GET['cpo_notice'] ) ) === 'orden_exists' ) {
            $this->add_notice( __( 'OT ya creada para este presupuesto', 'core-print-offset' ), 'warning' );
        }

        if ( $this->core_active && isset( $_GET['cpo_action'], $_GET['orden_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'update_orden_status' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_update_orden' ) ) {
                $id     = intval( $_GET['orden_id'] );
                $estado = sanitize_text_field( wp_unslash( $_GET['estado'] ?? 'pendiente' ) );
                $wpdb->update( $wpdb->prefix . 'cpo_ordenes', array( 'estado' => $estado, 'updated_at' => cpo_now() ), array( 'id' => $id ) );
                $this->add_notice( __( 'Estado de orden actualizado.', 'core-print-offset' ) );
            }
        }

        if ( $this->core_active && isset( $_GET['cpo_action'], $_GET['orden_id'], $_GET['_wpnonce'] ) && $_GET['cpo_action'] === 'generate_invoice' ) {
            if ( wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ), 'cpo_generate_invoice' ) ) {
                $id = intval( $_GET['orden_id'] );
                $orden = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_ordenes WHERE id = %d", $id ), ARRAY_A );
                if ( $orden ) {
                    $response = $this->core_bridge->create_core_document(
                        array(
                            'tipo'    => 'factura',
                            'titulo'  => $orden['titulo'],
                            'cliente_id' => $orden['core_cliente_id'],
                        )
                    );
                    if ( is_wp_error( $response ) ) {
                        $this->add_notice( $response->get_error_message(), 'error' );
                    } else {
                        $core_documento_id = is_array( $response ) && isset( $response['id'] ) ? (int) $response['id'] : (int) $response;
                        $wpdb->update( $wpdb->prefix . 'cpo_ordenes', array( 'core_documento_id' => $core_documento_id ), array( 'id' => $id ) );
                        $this->add_notice( __( 'Factura generada en Core.', 'core-print-offset' ) );
                    }
                }
            }
        }

        $data['ordenes'] = $wpdb->get_results( "SELECT * FROM {$wpdb->prefix}cpo_ordenes ORDER BY created_at DESC", ARRAY_A );

        return $data;
    }
}
