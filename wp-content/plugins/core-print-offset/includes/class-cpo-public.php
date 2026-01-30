<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Public {
    private $core_bridge;

    public function __construct() {
        $this->core_bridge = new CPO_Core_Bridge();

        add_shortcode( 'cpo_offset_presupuesto', array( $this, 'render_presupuesto_shortcode' ) );

        add_action( 'wp_ajax_cpo_offset_calculate', array( $this, 'handle_calculate' ) );
        add_action( 'wp_ajax_nopriv_cpo_offset_calculate', array( $this, 'handle_calculate' ) );
        add_action( 'wp_ajax_cpo_offset_save_presupuesto', array( $this, 'handle_save_presupuesto' ) );

        add_action( 'init', array( $this, 'maybe_register_dashboard_sections' ) );
    }

    public function maybe_register_dashboard_sections(): void {
        if ( $this->core_bridge->check_core_active() ) {
            add_filter( 'gc_dashboard_sections', array( $this, 'register_dashboard_sections' ) );
        }
    }

    public function register_dashboard_sections( array $sections ): array {
        $sections[] = array(
            'id' => 'cpo-presupuesto',
            'label' => __( 'Presupuesto Offset', 'core-print-offset' ),
            'shortcode' => '[cpo_offset_presupuesto]',
            'order' => 100,
        );

        return $sections;
    }

    public function render_presupuesto_shortcode() {
        $materials = $this->get_materiales_list();
        $processes = $this->get_procesos_list();

        wp_enqueue_style(
            'cpo-offset-presupuesto',
            CPO_PLUGIN_URL . 'public/assets/css/offset-presupuesto.css',
            array(),
            CPO_VERSION
        );

        wp_enqueue_script(
            'cpo-offset-presupuesto',
            CPO_PLUGIN_URL . 'public/assets/js/offset-presupuesto.js',
            array(),
            CPO_VERSION,
            true
        );

        wp_localize_script(
            'cpo-offset-presupuesto',
            'cpoOffsetPresupuesto',
            array(
                'ajaxUrl'       => admin_url( 'admin-ajax.php' ),
                'nonce'         => wp_create_nonce( 'cpo_offset_presupuesto' ),
                'canSave'       => is_user_logged_in(),
                'coreAvailable' => $this->core_bridge->has_core_api(),
                'strings'       => array(
                    'priceMissing' => __( 'Precio no cargado', 'core-print-offset' ),
                    'savingError'  => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ),
                    'saved'        => __( 'Presupuesto guardado.', 'core-print-offset' ),
                ),
            )
        );

        ob_start();
        ?>
        <div class="cpo-offset-presupuesto">
            <div class="cpo-card">
                <div class="cpo-card__header">
                    <h2><?php esc_html_e( 'Presupuesto Offset', 'core-print-offset' ); ?></h2>
                    <p><?php esc_html_e( 'Completa los datos para calcular el costo del trabajo de impresión.', 'core-print-offset' ); ?></p>
                </div>
                <form class="cpo-form" data-cpo-presupuesto>
                    <div class="cpo-grid">
                        <section class="cpo-section">
                            <h3><?php esc_html_e( 'A) Trabajo', 'core-print-offset' ); ?></h3>
                            <label>
                                <?php esc_html_e( 'Cliente (opcional)', 'core-print-offset' ); ?>
                                <input type="text" name="cliente" placeholder="<?php esc_attr_e( 'Nombre del cliente', 'core-print-offset' ); ?>">
                            </label>
                            <label>
                                <?php esc_html_e( 'Descripción', 'core-print-offset' ); ?>
                                <input type="text" name="descripcion" required placeholder="<?php esc_attr_e( 'Ej: Catálogo 24 páginas', 'core-print-offset' ); ?>">
                            </label>
                            <label>
                                <?php esc_html_e( 'Cantidad', 'core-print-offset' ); ?>
                                <input type="number" name="cantidad" min="1" required value="1000">
                            </label>
                        </section>

                        <section class="cpo-section">
                            <h3><?php esc_html_e( 'B) Formato', 'core-print-offset' ); ?></h3>
                            <div class="cpo-inline">
                                <label>
                                    <?php esc_html_e( 'Ancho (mm)', 'core-print-offset' ); ?>
                                    <input type="number" name="ancho_mm" min="1" step="0.1" required>
                                </label>
                                <label>
                                    <?php esc_html_e( 'Alto (mm)', 'core-print-offset' ); ?>
                                    <input type="number" name="alto_mm" min="1" step="0.1" required>
                                </label>
                            </div>
                            <label>
                                <?php esc_html_e( 'Colores', 'core-print-offset' ); ?>
                                <select name="colores">
                                    <option value="1/0">1/0</option>
                                    <option value="1/1">1/1</option>
                                    <option value="4/0" selected>4/0</option>
                                    <option value="4/4">4/4</option>
                                </select>
                            </label>
                            <label>
                                <?php esc_html_e( 'Sangrado (mm)', 'core-print-offset' ); ?>
                                <input type="number" name="sangrado_mm" min="0" step="0.1" value="3">
                            </label>
                        </section>

                        <section class="cpo-section">
                            <h3><?php esc_html_e( 'C) Papel', 'core-print-offset' ); ?></h3>
                            <label>
                                <?php esc_html_e( 'Material', 'core-print-offset' ); ?>
                                <select name="material_id" data-material-select>
                                    <option value="0"><?php esc_html_e( 'Selecciona un material', 'core-print-offset' ); ?></option>
                                    <?php foreach ( $materials as $material ) : ?>
                                        <option value="<?php echo esc_attr( $material['id'] ); ?>"
                                                data-price="<?php echo esc_attr( $material['precio_vigente'] ?? '' ); ?>"
                                                data-moneda="<?php echo esc_attr( $material['moneda'] ?? 'PYG' ); ?>">
                                            <?php echo esc_html( $material['nombre'] ); ?>
                                        </option>
                                    <?php endforeach; ?>
                                </select>
                            </label>
                            <p class="cpo-hint" data-material-price>
                                <?php esc_html_e( 'Precio vigente: -', 'core-print-offset' ); ?>
                            </p>
                        </section>

                        <section class="cpo-section">
                            <h3><?php esc_html_e( 'D) Producción', 'core-print-offset' ); ?></h3>
                            <label>
                                <?php esc_html_e( 'Pliego / Formato', 'core-print-offset' ); ?>
                                <select name="pliego_formato" data-pliego-select>
                                    <option value="64x88">64 x 88 cm</option>
                                    <option value="70x100" selected>70 x 100 cm</option>
                                    <option value="custom"><?php esc_html_e( 'Personalizado (mm)', 'core-print-offset' ); ?></option>
                                </select>
                            </label>
                            <div class="cpo-inline" data-pliego-custom hidden>
                                <label>
                                    <?php esc_html_e( 'Ancho (mm)', 'core-print-offset' ); ?>
                                    <input type="number" name="pliego_ancho_mm" min="1" step="0.1">
                                </label>
                                <label>
                                    <?php esc_html_e( 'Alto (mm)', 'core-print-offset' ); ?>
                                    <input type="number" name="pliego_alto_mm" min="1" step="0.1">
                                </label>
                            </div>
                            <label>
                                <?php esc_html_e( 'Formas por pliego', 'core-print-offset' ); ?>
                                <input type="number" name="formas_por_pliego" min="1" required value="4">
                            </label>
                            <label>
                                <?php esc_html_e( 'Merma %', 'core-print-offset' ); ?>
                                <input type="number" name="merma_pct" min="0" step="0.1" value="5">
                            </label>
                        </section>

                        <section class="cpo-section">
                            <h3><?php esc_html_e( 'E) Procesos extras', 'core-print-offset' ); ?></h3>
                            <div class="cpo-checks">
                                <?php if ( empty( $processes ) ) : ?>
                                    <p><?php esc_html_e( 'No hay procesos cargados.', 'core-print-offset' ); ?></p>
                                <?php else : ?>
                                    <?php foreach ( $processes as $process ) : ?>
                                        <label>
                                            <input type="checkbox" name="procesos[]" value="<?php echo esc_attr( $process['id'] ); ?>">
                                            <span><?php echo esc_html( $process['nombre'] ); ?></span>
                                            <span class="cpo-tag">
                                                <?php echo esc_html( number_format_i18n( $process['costo_base'], 2 ) ); ?>
                                            </span>
                                        </label>
                                    <?php endforeach; ?>
                                <?php endif; ?>
                            </div>
                        </section>

                        <section class="cpo-section cpo-results">
                            <h3><?php esc_html_e( 'F) Resultados', 'core-print-offset' ); ?></h3>
                            <div class="cpo-results__grid">
                                <div>
                                    <span><?php esc_html_e( 'Pliegos necesarios', 'core-print-offset' ); ?></span>
                                    <strong data-result="pliegos_necesarios">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Costo papel', 'core-print-offset' ); ?></span>
                                    <strong data-result="paper_cost">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Costo procesos', 'core-print-offset' ); ?></span>
                                    <strong data-result="process_cost">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Subtotal', 'core-print-offset' ); ?></span>
                                    <strong data-result="subtotal">-</strong>
                                </div>
                            </div>
                            <label>
                                <?php esc_html_e( 'Margen %', 'core-print-offset' ); ?>
                                <input type="number" name="margin_pct" min="0" step="0.1" value="30">
                            </label>
                            <div class="cpo-total">
                                <span><?php esc_html_e( 'Total final', 'core-print-offset' ); ?></span>
                                <strong data-result="total_final">-</strong>
                            </div>
                            <p class="cpo-hint" data-result="price_note"></p>
                        </section>
                    </div>

                    <div class="cpo-actions">
                        <button type="button" class="cpo-button" data-cpo-calc><?php esc_html_e( 'Calcular', 'core-print-offset' ); ?></button>
                        <button type="button" class="cpo-button cpo-button--primary" data-cpo-save><?php esc_html_e( 'Guardar Presupuesto', 'core-print-offset' ); ?></button>
                        <button type="button" class="cpo-button cpo-button--ghost" data-cpo-core disabled><?php esc_html_e( 'Crear documento en Core', 'core-print-offset' ); ?></button>
                    </div>

                    <div class="cpo-alert" data-cpo-alert hidden></div>
                </form>
            </div>
        </div>
        <?php
        return ob_get_clean();
    }

    public function handle_calculate() {
        $this->ensure_valid_nonce();

        $payload = $this->sanitize_payload( $_POST );
        $result  = $this->calculate_totals( $payload );

        wp_send_json_success( $result );
    }

    public function handle_save_presupuesto() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para guardar.', 'core-print-offset' ) ), 401 );
        }

        $payload = $this->sanitize_payload( $_POST );
        $result  = $this->calculate_totals( $payload );

        global $wpdb;

        $titulo = $payload['descripcion'] ? $payload['descripcion'] : __( 'Presupuesto Offset', 'core-print-offset' );
        $formato_final = '';
        if ( $payload['ancho_mm'] && $payload['alto_mm'] ) {
            $formato_final = sprintf( '%s x %s mm', $payload['ancho_mm'], $payload['alto_mm'] );
        }

        $caras = 1;
        if ( strpos( $payload['colores'], '/' ) !== false ) {
            list( $frente, $dorso ) = array_pad( explode( '/', $payload['colores'] ), 2, '0' );
            if ( (int) $dorso > 0 ) {
                $caras = 2;
            }
        }

        $now = cpo_now();

        $inserted = $wpdb->insert(
            $wpdb->prefix . 'cpo_presupuestos',
            array(
                'core_cliente_id' => null,
                'core_documento_id' => null,
                'titulo'         => $titulo,
                'producto'       => $payload['descripcion'],
                'formato_final'  => $formato_final,
                'cantidad'       => $payload['cantidad'],
                'material_id'    => $payload['material_id'] ?: null,
                'colores'        => $payload['colores'],
                'caras'          => $caras,
                'margen_pct'     => $payload['margin_pct'],
                'estado'         => 'borrador',
                'costo_total'    => $result['subtotal'],
                'precio_total'   => $result['total_final'],
                'created_at'     => $now,
                'updated_at'     => $now,
            ),
            array( '%d', '%d', '%s', '%s', '%s', '%d', '%d', '%s', '%d', '%f', '%s', '%f', '%f', '%s', '%s' )
        );

        if ( ! $inserted ) {
            wp_send_json_error( array( 'message' => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ) ), 500 );
        }

        $presupuesto_id = (int) $wpdb->insert_id;
        $snapshot = wp_json_encode(
            array(
                'inputs'  => $payload,
                'totals'  => $result,
                'cliente' => $payload['cliente'],
            ),
            JSON_UNESCAPED_UNICODE
        );

        if ( $result['material'] ) {
            $wpdb->insert(
                $wpdb->prefix . 'cpo_presupuesto_items',
                array(
                    'presupuesto_id' => $presupuesto_id,
                    'tipo'           => 'papel',
                    'referencia_id'  => $result['material']['id'],
                    'descripcion'    => $result['material']['nombre'],
                    'cantidad'       => $result['pliegos_necesarios'],
                    'unitario'       => $result['precio_pliego'],
                    'subtotal'       => $result['paper_cost'],
                    'snapshot_json'  => $snapshot,
                    'created_at'     => $now,
                ),
                array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
            );
        } else {
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
                    'snapshot_json'  => $snapshot,
                    'created_at'     => $now,
                ),
                array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
            );
        }

        if ( ! empty( $result['processes'] ) ) {
            foreach ( $result['processes'] as $process ) {
                $wpdb->insert(
                    $wpdb->prefix . 'cpo_presupuesto_items',
                    array(
                        'presupuesto_id' => $presupuesto_id,
                        'tipo'           => 'proceso',
                        'referencia_id'  => $process['id'],
                        'descripcion'    => $process['nombre'],
                        'cantidad'       => $process['cantidad'],
                        'unitario'       => $process['unitario'],
                        'subtotal'       => $process['subtotal'],
                        'snapshot_json'  => null,
                        'created_at'     => $now,
                    ),
                    array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
                );
            }
        }

        wp_send_json_success(
            array(
                'message' => __( 'Presupuesto guardado.', 'core-print-offset' ),
                'id'      => $presupuesto_id,
            )
        );
    }

    private function ensure_valid_nonce() {
        $nonce = sanitize_text_field( wp_unslash( $_POST['nonce'] ?? '' ) );
        if ( ! wp_verify_nonce( $nonce, 'cpo_offset_presupuesto' ) ) {
            wp_send_json_error( array( 'message' => __( 'Nonce inválido.', 'core-print-offset' ) ), 403 );
        }
    }

    private function sanitize_payload( $raw ) {
        $payload = array();

        $payload['cliente'] = sanitize_text_field( wp_unslash( $raw['cliente'] ?? '' ) );
        $payload['descripcion'] = sanitize_text_field( wp_unslash( $raw['descripcion'] ?? '' ) );
        $payload['cantidad'] = max( 1, (int) ( $raw['cantidad'] ?? 1 ) );
        $payload['ancho_mm'] = cpo_get_decimal( wp_unslash( $raw['ancho_mm'] ?? 0 ) );
        $payload['alto_mm'] = cpo_get_decimal( wp_unslash( $raw['alto_mm'] ?? 0 ) );
        $payload['colores'] = sanitize_text_field( wp_unslash( $raw['colores'] ?? '4/0' ) );
        $payload['sangrado_mm'] = cpo_get_decimal( wp_unslash( $raw['sangrado_mm'] ?? 0 ) );
        $payload['material_id'] = (int) ( $raw['material_id'] ?? 0 );
        $payload['pliego_formato'] = sanitize_text_field( wp_unslash( $raw['pliego_formato'] ?? '' ) );
        $payload['pliego_ancho_mm'] = cpo_get_decimal( wp_unslash( $raw['pliego_ancho_mm'] ?? 0 ) );
        $payload['pliego_alto_mm'] = cpo_get_decimal( wp_unslash( $raw['pliego_alto_mm'] ?? 0 ) );
        $payload['formas_por_pliego'] = max( 1, (int) ( $raw['formas_por_pliego'] ?? 1 ) );
        $payload['merma_pct'] = max( 0, cpo_get_decimal( wp_unslash( $raw['merma_pct'] ?? 0 ) ) );
        $payload['margin_pct'] = max( 0, cpo_get_decimal( wp_unslash( $raw['margin_pct'] ?? 0 ) ) );

        $processes = $raw['procesos'] ?? array();
        if ( ! is_array( $processes ) ) {
            $processes = array();
        }
        $payload['procesos'] = array_values( array_filter( array_map( 'intval', $processes ) ) );

        return $payload;
    }

    private function calculate_totals( $payload ) {
        $material = null;
        $precio_pliego = 0;
        $precio_note = '';

        if ( $payload['material_id'] ) {
            $material = $this->get_material_by_id( $payload['material_id'] );
            if ( $material && $material['precio_vigente'] !== null ) {
                $precio_pliego = (float) $material['precio_vigente'];
            } else {
                $precio_note = __( 'Precio no cargado', 'core-print-offset' );
            }
        }

        $pliegos_necesarios = (int) ceil(
            ( $payload['cantidad'] / max( 1, $payload['formas_por_pliego'] ) ) * ( 1 + $payload['merma_pct'] / 100 )
        );

        $paper_cost = $pliegos_necesarios * $precio_pliego;

        $processes = $this->get_processes_by_ids( $payload['procesos'] );
        $process_cost = 0;
        $process_breakdown = array();

        foreach ( $processes as $process ) {
            $multiplier = 1;
            if ( $process['modo_cobro'] === 'por_unidad' ) {
                $multiplier = $payload['cantidad'];
            } elseif ( $process['modo_cobro'] === 'por_pliego' ) {
                $multiplier = max( 1, $pliegos_necesarios );
            }

            $subtotal = $process['costo_base'] * $multiplier;
            $process_cost += $subtotal;

            $process_breakdown[] = array(
                'id'       => $process['id'],
                'nombre'   => $process['nombre'],
                'cantidad' => $multiplier,
                'unitario' => (float) $process['costo_base'],
                'subtotal' => $subtotal,
            );
        }

        $machine_cost = 0;
        $subtotal = $paper_cost + $process_cost + $machine_cost;
        $total_final = $subtotal * ( 1 + $payload['margin_pct'] / 100 );

        return array(
            'pliegos_necesarios' => $pliegos_necesarios,
            'precio_pliego'      => $precio_pliego,
            'paper_cost'         => $paper_cost,
            'process_cost'       => $process_cost,
            'machine_cost'       => $machine_cost,
            'subtotal'           => $subtotal,
            'total_final'        => $total_final,
            'material'           => $material,
            'processes'          => $process_breakdown,
            'price_note'         => $precio_note,
        );
    }

    private function get_materiales_list() {
        global $wpdb;

        $sql = "SELECT m.*, (
                SELECT precio FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS precio_vigente,
            (
                SELECT moneda FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS moneda
            FROM {$wpdb->prefix}cpo_materiales m
            WHERE m.activo = 1
            ORDER BY m.nombre ASC";

        return $wpdb->get_results( $sql, ARRAY_A );
    }

    private function get_material_by_id( $material_id ) {
        global $wpdb;

        $sql = "SELECT m.*, (
                SELECT precio FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS precio_vigente,
            (
                SELECT moneda FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS moneda
            FROM {$wpdb->prefix}cpo_materiales m
            WHERE m.id = %d
            LIMIT 1";

        return $wpdb->get_row( $wpdb->prepare( $sql, $material_id ), ARRAY_A );
    }

    private function get_procesos_list() {
        global $wpdb;

        return $wpdb->get_results(
            "SELECT * FROM {$wpdb->prefix}cpo_procesos WHERE activo = 1 ORDER BY nombre ASC",
            ARRAY_A
        );
    }

    private function get_processes_by_ids( $ids ) {
        global $wpdb;

        if ( empty( $ids ) ) {
            return array();
        }

        $placeholders = implode( ',', array_fill( 0, count( $ids ), '%d' ) );
        $sql = "SELECT * FROM {$wpdb->prefix}cpo_procesos WHERE id IN ($placeholders) AND activo = 1";

        return $wpdb->get_results( $wpdb->prepare( $sql, $ids ), ARRAY_A );
    }
}
