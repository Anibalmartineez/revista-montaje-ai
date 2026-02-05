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
        add_action( 'wp_ajax_cpo_offset_create_core_document', array( $this, 'handle_create_core_document' ) );

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
        $machines  = $this->get_maquinas_list();
        $core_clients = $this->core_bridge->get_core_clients_list();
        $core_active = $this->core_bridge->check_core_active();
        $has_core_clients = $core_active && ! empty( $core_clients );

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
                'canEditMachineCost' => current_user_can( 'manage_options' ),
                'strings'       => array(
                    'priceMissing' => __( 'No hay precio vigente para este material. Cargalo en Offset > Materiales/Precios', 'core-print-offset' ),
                    'savingError'  => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ),
                    'saved'        => __( 'Presupuesto guardado.', 'core-print-offset' ),
                    'coreClientRequired' => __( 'Selecciona un cliente de Core para crear el documento.', 'core-print-offset' ),
                    'coreSaveRequired'   => __( 'Guarda el presupuesto antes de crear el documento en Core.', 'core-print-offset' ),
                    'coreCreated'        => __( 'Documento creado en Core.', 'core-print-offset' ),
                    'coreUnavailable'    => __( 'Core Global no está disponible.', 'core-print-offset' ),
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
                            <?php if ( $has_core_clients ) : ?>
                                <label>
                                    <?php esc_html_e( 'Cliente (Core)', 'core-print-offset' ); ?>
                                    <select name="cliente_id" data-cliente-select>
                                        <option value="0"><?php esc_html_e( 'Seleccionar cliente', 'core-print-offset' ); ?></option>
                                        <?php foreach ( $core_clients as $client ) : ?>
                                            <option value="<?php echo esc_attr( $client['id'] ); ?>">
                                                <?php echo esc_html( $client['nombre'] ); ?>
                                            </option>
                                        <?php endforeach; ?>
                                        <option value="other"><?php esc_html_e( 'Otro / No está en lista', 'core-print-offset' ); ?></option>
                                    </select>
                                </label>
                                <label data-cliente-text hidden>
                                    <?php esc_html_e( 'Cliente (otro)', 'core-print-offset' ); ?>
                                    <input type="text" name="cliente_texto" placeholder="<?php esc_attr_e( 'Nombre del cliente', 'core-print-offset' ); ?>">
                                </label>
                            <?php else : ?>
                                <label>
                                    <?php esc_html_e( 'Cliente (opcional)', 'core-print-offset' ); ?>
                                    <input type="text" name="cliente_texto" placeholder="<?php esc_attr_e( 'Nombre del cliente', 'core-print-offset' ); ?>">
                                </label>
                                <?php if ( $core_active ) : ?>
                                    <p class="cpo-hint"><?php esc_html_e( 'Core Global está activo pero no se encontraron clientes.', 'core-print-offset' ); ?></p>
                                <?php endif; ?>
                            <?php endif; ?>
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
                                <select name="material_id" data-material-select <?php echo empty( $materials ) ? 'disabled' : ''; ?>>
                                    <option value="0"><?php esc_html_e( 'Selecciona un material', 'core-print-offset' ); ?></option>
                                    <?php foreach ( $materials as $material ) : ?>
                                        <option value="<?php echo esc_attr( $material['id'] ); ?>"
                                                data-price="<?php echo esc_attr( $material['precio_vigente'] ?? '' ); ?>"
                                                data-moneda="<?php echo esc_attr( $material['moneda'] ?? 'PYG' ); ?>"
                                                data-formato-base="<?php echo esc_attr( $material['formato_base'] ?? '' ); ?>">
                                            <?php echo esc_html( $material['nombre'] ); ?>
                                        </option>
                                    <?php endforeach; ?>
                                </select>
                            </label>
                            <?php if ( empty( $materials ) ) : ?>
                                <p class="cpo-hint"><?php esc_html_e( 'No hay materiales cargados.', 'core-print-offset' ); ?></p>
                            <?php endif; ?>
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
                            <label class="cpo-inline">
                                <input type="checkbox" name="pliego_personalizado" value="1" data-pliego-override>
                                <?php esc_html_e( 'Usar pliego personalizado', 'core-print-offset' ); ?>
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

                        <section class="cpo-section">
                            <details class="cpo-advanced" data-advanced>
                                <summary><?php esc_html_e( 'Modo avanzado', 'core-print-offset' ); ?></summary>
                                <div class="cpo-advanced__content">
                                    <label>
                                        <?php esc_html_e( 'Máquina', 'core-print-offset' ); ?>
                                        <select name="maquina_id" data-machine-select>
                                            <option value=""><?php esc_html_e( 'Automática', 'core-print-offset' ); ?></option>
                                            <?php foreach ( $machines as $machine ) : ?>
                                                <option value="<?php echo esc_attr( $machine['id'] ); ?>"
                                                        data-cost="<?php echo esc_attr( $machine['costo_hora'] ); ?>"
                                                        data-rendimiento="<?php echo esc_attr( $machine['rendimiento_pliegos_hora'] ?? $machine['rendimiento_hora'] ); ?>"
                                                        data-setup="<?php echo esc_attr( $machine['setup_min'] ?? 0 ); ?>">
                                                    <?php echo esc_html( $machine['nombre'] ); ?>
                                                </option>
                                            <?php endforeach; ?>
                                        </select>
                                    </label>
                                    <div class="cpo-inline">
                                        <label>
                                            <?php esc_html_e( 'Horas estimadas', 'core-print-offset' ); ?>
                                            <input type="number" name="horas_maquina" min="0" step="0.01" data-horas-input>
                                        </label>
                                        <label>
                                            <?php esc_html_e( 'Costo / hora', 'core-print-offset' ); ?>
                                            <input type="number" name="costo_hora" min="0" step="0.01" data-costo-input <?php echo current_user_can( 'manage_options' ) ? '' : 'readonly'; ?>>
                                        </label>
                                    </div>
                                    <p class="cpo-hint"><?php esc_html_e( 'Si no seleccionás máquina, se usa la más económica activa.', 'core-print-offset' ); ?></p>
                                </div>
                            </details>
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
                                    <strong data-result="costo_papel">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Costo procesos', 'core-print-offset' ); ?></span>
                                    <strong data-result="costo_procesos">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Costo máquina', 'core-print-offset' ); ?></span>
                                    <strong data-result="costo_maquina">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Subtotal', 'core-print-offset' ); ?></span>
                                    <strong data-result="subtotal">-</strong>
                                </div>
                                <div>
                                    <span><?php esc_html_e( 'Margen', 'core-print-offset' ); ?></span>
                                    <strong data-result="margen">-</strong>
                                </div>
                            </div>
                            <label>
                                <?php esc_html_e( 'Margen %', 'core-print-offset' ); ?>
                                <input type="number" name="margin_pct" min="0" step="0.1" value="30">
                            </label>
                            <div class="cpo-total">
                                <span><?php esc_html_e( 'Total final', 'core-print-offset' ); ?></span>
                                <strong data-result="total">-</strong>
                            </div>
                            <p class="cpo-hint" data-result="price_note"></p>
                            <div class="cpo-breakdown" data-result-breakdown hidden></div>
                        </section>
                    </div>

                    <div class="cpo-actions">
                        <button type="button" class="cpo-button" data-cpo-calc><?php esc_html_e( 'Calcular', 'core-print-offset' ); ?></button>
                        <button type="button" class="cpo-button cpo-button--primary" data-cpo-save><?php esc_html_e( 'Guardar Presupuesto', 'core-print-offset' ); ?></button>
                        <button type="button" class="cpo-button cpo-button--ghost" data-cpo-core disabled><?php esc_html_e( 'Crear documento en Core', 'core-print-offset' ); ?></button>
                        <input type="hidden" name="presupuesto_id" value="" data-presupuesto-id>
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
        $result  = CPO_Calculator::calculate( $payload );

        wp_send_json_success( $result );
    }

    public function handle_save_presupuesto() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para guardar.', 'core-print-offset' ) ), 401 );
        }

        $payload = $this->sanitize_payload( $_POST );
        $result  = CPO_Calculator::calculate( $payload );

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
        $cliente_id = $payload['cliente_id'] > 0 ? (int) $payload['cliente_id'] : null;
        $cliente_texto = $payload['cliente_texto'];
        if ( $cliente_id ) {
            $client_name = $this->get_core_client_name( $cliente_id );
            if ( $client_name ) {
                $cliente_texto = $client_name;
            }
        }

        $snapshot_json = wp_json_encode( $payload, JSON_UNESCAPED_UNICODE );
        $calc_result_json = wp_json_encode( $result, JSON_UNESCAPED_UNICODE );

        $inserted = $wpdb->insert(
            $wpdb->prefix . 'cpo_presupuestos',
            array(
                'core_cliente_id' => $cliente_id,
                'cliente_id'    => $cliente_id,
                'cliente_texto' => $cliente_texto ?: null,
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
                'precio_total'   => $result['total'],
                'snapshot_json'  => $snapshot_json,
                'calc_result_json' => $calc_result_json,
                'snapshot_version' => CPO_SNAPSHOT_VERSION,
                'created_at'     => $now,
                'updated_at'     => $now,
            ),
            array( '%d', '%d', '%s', '%d', '%s', '%s', '%s', '%d', '%d', '%s', '%d', '%f', '%s', '%f', '%f', '%s', '%s', '%d', '%s', '%s' )
        );

        if ( ! $inserted ) {
            wp_send_json_error( array( 'message' => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ) ), 500 );
        }

        $presupuesto_id = (int) $wpdb->insert_id;
        $snapshot_payload = array(
            'inputs'  => $payload,
            'totals'  => $result,
            'cliente' => $cliente_texto,
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
                    'subtotal'       => $result['costo_papel'],
                    'snapshot_json'  => wp_json_encode(
                        array(
                            'material' => $result['material'],
                            'precio'   => $result['material_snapshot'],
                        )
                    ),
                    'created_at'     => $now,
                ),
                array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
            );
        }

        if ( $result['maquina'] && $result['costo_maquina'] > 0 ) {
            $wpdb->insert(
                $wpdb->prefix . 'cpo_presupuesto_items',
                array(
                    'presupuesto_id' => $presupuesto_id,
                    'tipo'           => 'maquina',
                    'referencia_id'  => $result['maquina']['id'],
                    'descripcion'    => sprintf( __( 'Máquina: %s', 'core-print-offset' ), $result['maquina']['nombre'] ),
                    'cantidad'       => $result['horas_maquina'],
                    'unitario'       => $result['costo_hora'],
                    'subtotal'       => $result['costo_maquina'],
                    'snapshot_json'  => wp_json_encode(
                        array(
                            'horas'      => $result['horas_maquina'],
                            'costo_hora' => $result['costo_hora'],
                            'maquina'    => $result['maquina'],
                        )
                    ),
                    'created_at'     => $now,
                ),
                array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
            );
        }

        if ( ! empty( $result['procesos'] ) ) {
            foreach ( $result['procesos'] as $process ) {
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
                        'snapshot_json'  => wp_json_encode( $process ),
                        'created_at'     => $now,
                    ),
                    array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
                );
            }
        }

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
            ),
            array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
        );

        wp_send_json_success(
            array(
                'message' => __( 'Presupuesto guardado.', 'core-print-offset' ),
                'id'      => $presupuesto_id,
                'cliente_id' => $cliente_id,
            )
        );
    }

    public function handle_create_core_document() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para crear documentos.', 'core-print-offset' ) ), 401 );
        }

        if ( ! current_user_can( 'manage_cpo_offset' ) ) {
            if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
                error_log(
                    sprintf(
                        'CPO core document blocked for user %d (capability manage_cpo_offset).',
                        get_current_user_id()
                    )
                );
            }
            wp_send_json_error( array( 'message' => __( 'No tienes permisos para crear documentos en Core.', 'core-print-offset' ) ), 403 );
        }

        if ( ! $this->core_bridge->has_core_api() ) {
            wp_send_json_error( array( 'message' => __( 'Core Global no está disponible.', 'core-print-offset' ) ), 400 );
        }

        $presupuesto_id = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
        if ( ! $presupuesto_id ) {
            wp_send_json_error( array( 'message' => __( 'Guarda el presupuesto antes de crear el documento en Core.', 'core-print-offset' ) ), 400 );
        }

        global $wpdb;
        $presupuesto = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
            ARRAY_A
        );

        if ( ! $presupuesto ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto no encontrado.', 'core-print-offset' ) ), 404 );
        }

        $existing_core_document_id = isset( $presupuesto['core_documento_id'] ) ? (int) $presupuesto['core_documento_id'] : 0;
        if ( $existing_core_document_id > 0 ) {
            wp_send_json_success(
                array(
                    'message'            => __( 'Este presupuesto ya tiene un documento en Core.', 'core-print-offset' ),
                    'core_documento_id'  => $existing_core_document_id,
                )
            );
        }

        $cliente_id = isset( $presupuesto['cliente_id'] ) ? (int) $presupuesto['cliente_id'] : 0;
        if ( ! $cliente_id && isset( $presupuesto['core_cliente_id'] ) ) {
            $cliente_id = (int) $presupuesto['core_cliente_id'];
        }

        if ( ! $cliente_id ) {
            wp_send_json_error( array( 'message' => __( 'Selecciona un cliente de Core para crear el documento.', 'core-print-offset' ) ), 400 );
        }

        $response = $this->core_bridge->create_core_document(
            array(
                'tipo'       => 'presupuesto',
                'titulo'     => $presupuesto['titulo'],
                'cliente_id' => $cliente_id,
                'total'      => $presupuesto['precio_total'],
            )
        );

        if ( is_wp_error( $response ) ) {
            wp_send_json_error( array( 'message' => $response->get_error_message() ), 400 );
        }

        $core_documento_id = is_array( $response ) && isset( $response['id'] ) ? (int) $response['id'] : (int) $response;
        if ( $core_documento_id ) {
            $wpdb->update(
                $wpdb->prefix . 'cpo_presupuestos',
                array( 'core_documento_id' => $core_documento_id ),
                array( 'id' => $presupuesto_id )
            );
            $this->maybe_add_core_document_items( $core_documento_id, $presupuesto_id );
        }

        wp_send_json_success(
            array(
                'message' => __( 'Documento creado en Core.', 'core-print-offset' ),
                'core_documento_id' => $core_documento_id,
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
        return cpo_build_presupuesto_payload(
            $raw,
            array(
                'allow_machine_default' => true,
            )
        );
    }

    private function get_core_client_name( int $client_id ): string {
        if ( ! $client_id ) {
            return '';
        }

        $clients = $this->core_bridge->get_core_clients_list();
        foreach ( $clients as $client ) {
            if ( (int) $client['id'] === $client_id ) {
                return (string) $client['nombre'];
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

    private function get_materiales_list() {
        global $wpdb;

        $cache_version = cpo_get_cache_version( 'material' );
        $cache_key = cpo_get_cache_key( sprintf( 'materiales_list:%s', $cache_version ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return is_array( $cached ) ? $cached : array();
        }

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

        $results = $wpdb->get_results( $sql, ARRAY_A );
        wp_cache_set( $cache_key, $results, 'cpo', 300 );

        return $results;
    }

    private function get_maquinas_list() {
        global $wpdb;

        $cache_version = cpo_get_cache_version( 'maquina' );
        $cache_key = cpo_get_cache_key( sprintf( 'maquinas_list:%s', $cache_version ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return is_array( $cached ) ? $cached : array();
        }

        $results = $wpdb->get_results(
            "SELECT * FROM {$wpdb->prefix}cpo_maquinas WHERE activo = 1 ORDER BY costo_hora ASC, created_at ASC",
            ARRAY_A
        );

        wp_cache_set( $cache_key, $results, 'cpo', 300 );

        return $results;
    }

    private function get_procesos_list() {
        global $wpdb;

        $cache_version = cpo_get_cache_version( 'proceso' );
        $cache_key = cpo_get_cache_key( sprintf( 'procesos_list:%s', $cache_version ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return is_array( $cached ) ? $cached : array();
        }

        $results = $wpdb->get_results(
            "SELECT * FROM {$wpdb->prefix}cpo_procesos WHERE activo = 1 ORDER BY nombre ASC",
            ARRAY_A
        );

        wp_cache_set( $cache_key, $results, 'cpo', 300 );

        return $results;
    }

}
