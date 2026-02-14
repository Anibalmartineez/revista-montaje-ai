<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Public {
    private $core_bridge;
    private $worktype_engine;

    public function __construct() {
        $this->core_bridge = new CPO_Core_Bridge();
        $this->worktype_engine = class_exists( 'CPO_WorkType_Engine' ) ? new CPO_WorkType_Engine() : null;

        add_shortcode( 'cpo_offset_presupuesto', array( $this, 'render_presupuesto_shortcode' ) );
        add_shortcode( 'cpo_offset_presupuestos_list', array( $this, 'render_presupuestos_list_shortcode' ) );

        add_action( 'wp_ajax_cpo_offset_calculate', array( $this, 'handle_calculate' ) );
        add_action( 'wp_ajax_nopriv_cpo_offset_calculate', array( $this, 'handle_calculate' ) );
        add_action( 'wp_ajax_cpo_offset_save_presupuesto', array( $this, 'handle_save_presupuesto' ) );
        add_action( 'wp_ajax_cpo_offset_validate_structure', array( $this, 'handle_validate_structure' ) );
        add_action( 'wp_ajax_nopriv_cpo_offset_validate_structure', array( $this, 'handle_validate_structure' ) );
        add_action( 'wp_ajax_cpo_offset_create_core_document', array( $this, 'handle_create_core_document' ) );
        add_action( 'wp_ajax_cpo_offset_get_presupuesto', array( $this, 'handle_get_presupuesto' ) );
        add_action( 'wp_ajax_cpo_offset_duplicate_presupuesto', array( $this, 'handle_duplicate_presupuesto' ) );
        add_action( 'wp_ajax_cpo_offset_convert_to_order', array( $this, 'handle_convert_to_order' ) );
        add_action( 'wp_ajax_cpo_offset_get_ordenes', array( $this, 'handle_get_ordenes' ) );
        add_action( 'wp_ajax_cpo_offset_generate_core_document_from_order', array( $this, 'handle_generate_core_document_from_order' ) );

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
        $sections[] = array(
            'id' => 'cpo-presupuestos',
            'label' => __( 'Mis Presupuestos', 'core-print-offset' ),
            'shortcode' => '[cpo_offset_presupuestos_list]',
            'order' => 110,
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

        wp_localize_script( 'cpo-offset-presupuesto', 'cpoOffsetPresupuesto', $this->get_offset_script_config() );

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
                            <label>
                                <?php esc_html_e( 'Tipo de trabajo', 'core-print-offset' ); ?>
                                <select name="work_type" data-work-type>
                                    <option value="otro" selected><?php esc_html_e( 'Otro', 'core-print-offset' ); ?></option>
                                    <option value="revista"><?php esc_html_e( 'Revista', 'core-print-offset' ); ?></option>
                                    <option value="folleto"><?php esc_html_e( 'Folleto', 'core-print-offset' ); ?></option>
                                    <option value="tarjeta"><?php esc_html_e( 'Tarjeta', 'core-print-offset' ); ?></option>
                                    <option value="etiqueta"><?php esc_html_e( 'Etiqueta', 'core-print-offset' ); ?></option>
                                    <option value="caja"><?php esc_html_e( 'Caja', 'core-print-offset' ); ?></option>
                                    <option value="troquel"><?php esc_html_e( 'Troquel', 'core-print-offset' ); ?></option>
                                </select>
                            </label>
                            <div class="cpo-structure" data-work-structure>
                                <h4><?php esc_html_e( 'Estructura del trabajo', 'core-print-offset' ); ?></h4>
                                <div class="cpo-inline">
                                    <label data-work-field="paginas">
                                        <?php esc_html_e( 'Páginas', 'core-print-offset' ); ?>
                                        <input type="number" name="paginas" min="0" step="1">
                                    </label>
                                    <label data-work-field="encuadernacion">
                                        <?php esc_html_e( 'Encuadernación', 'core-print-offset' ); ?>
                                        <select name="encuadernacion">
                                            <option value=""><?php esc_html_e( 'Seleccionar', 'core-print-offset' ); ?></option>
                                            <option value="caballete"><?php esc_html_e( 'Caballete', 'core-print-offset' ); ?></option>
                                            <option value="pegado"><?php esc_html_e( 'Pegado', 'core-print-offset' ); ?></option>
                                            <option value="espiral"><?php esc_html_e( 'Espiral', 'core-print-offset' ); ?></option>
                                            <option value="suelto"><?php esc_html_e( 'Suelto', 'core-print-offset' ); ?></option>
                                        </select>
                                    </label>
                                </div>
                                <div class="cpo-inline">
                                    <label class="cpo-checkbox" data-work-field="troquel">
                                        <input type="checkbox" name="troquel" value="1">
                                        <?php esc_html_e( 'Incluye troquel', 'core-print-offset' ); ?>
                                    </label>
                                    <label data-work-field="costo_troquel">
                                        <?php esc_html_e( 'Costo troquel', 'core-print-offset' ); ?>
                                        <input type="number" name="costo_troquel" min="0" step="0.01">
                                    </label>
                                    <label data-work-field="merma_troquel_extra">
                                        <?php esc_html_e( 'Merma troquel extra %', 'core-print-offset' ); ?>
                                        <input type="number" name="merma_troquel_extra" min="0" step="0.1">
                                    </label>
                                </div>
                                <div class="cpo-inline">
                                    <label data-work-field="material_bobina">
                                        <?php esc_html_e( 'Material bobina', 'core-print-offset' ); ?>
                                        <input type="text" name="material_bobina" placeholder="BOPP, couché, etc.">
                                    </label>
                                    <label data-work-field="anilox">
                                        <?php esc_html_e( 'Anilox', 'core-print-offset' ); ?>
                                        <input type="text" name="anilox" placeholder="Ej: 360">
                                    </label>
                                    <label data-work-field="cilindro">
                                        <?php esc_html_e( 'Cilindro / paso', 'core-print-offset' ); ?>
                                        <input type="text" name="cilindro" placeholder="Ej: 18">
                                    </label>
                                </div>
                            </div>
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
                            <div class="cpo-tech-summary" data-technical-summary>
                                <h4><?php esc_html_e( 'Resumen técnico', 'core-print-offset' ); ?></h4>
                                <div class="cpo-tech-summary__chips" data-production-chips></div>
                                <p class="cpo-hint" data-production-summary></p>
                                <div class="cpo-tech-summary__warnings" data-technical-warnings hidden></div>
                                <p class="cpo-tech-summary__missing" data-cannot-calculate hidden></p>
                            </div>
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
                        <button type="button" class="cpo-button cpo-button--ghost" data-cpo-create-order-primary disabled><?php esc_html_e( 'Crear OT', 'core-print-offset' ); ?></button>
                        <input type="hidden" name="presupuesto_id" value="" data-presupuesto-id>
                    </div>

                    <div class="cpo-alert" data-cpo-alert hidden></div>
                </form>
            </div>
        </div>
        <?php
        return ob_get_clean();
    }

    public function render_presupuestos_list_shortcode() {
        if ( ! is_user_logged_in() ) {
            return '<div class="cpo-offset-presupuesto"><div class="cpo-card"><p>' . esc_html__( 'Debes iniciar sesión para ver tus presupuestos.', 'core-print-offset' ) . '</p></div></div>';
        }

        global $wpdb;

        $search = sanitize_text_field( wp_unslash( $_GET['cpo_search'] ?? '' ) );
        $estado = sanitize_text_field( wp_unslash( $_GET['cpo_estado'] ?? '' ) );
        $from = sanitize_text_field( wp_unslash( $_GET['cpo_from'] ?? '' ) );
        $to = sanitize_text_field( wp_unslash( $_GET['cpo_to'] ?? '' ) );

        $where = array( '1=1' );
        $params = array();
        $current_user_id = get_current_user_id();

        if ( ! $this->user_can_manage_all_presupuestos() ) {
            $where[] = 'p.created_by = %d';
            $params[] = $current_user_id;
        }

        if ( $search ) {
            $where[] = '(p.titulo LIKE %s OR p.cliente_texto LIKE %s)';
            $like = '%' . $wpdb->esc_like( $search ) . '%';
            $params[] = $like;
            $params[] = $like;
        }

        if ( $estado ) {
            $where[] = 'p.estado = %s';
            $params[] = $estado;
        }

        if ( $from ) {
            $where[] = 'DATE(p.created_at) >= %s';
            $params[] = $from;
        }

        if ( $to ) {
            $where[] = 'DATE(p.created_at) <= %s';
            $params[] = $to;
        }

        $sql = "SELECT p.*, o.id AS orden_id, o.estado AS orden_estado, o.fecha_entrega AS orden_fecha_entrega, o.core_documento_id AS orden_core_documento_id FROM {$wpdb->prefix}cpo_presupuestos p LEFT JOIN {$wpdb->prefix}cpo_ordenes o ON o.presupuesto_id = p.id WHERE " . implode( ' AND ', $where ) . ' ORDER BY p.created_at DESC LIMIT 200';
        if ( $params ) {
            $sql = $wpdb->prepare( $sql, $params );
        }

        $presupuestos = $wpdb->get_results( $sql, ARRAY_A );

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
        wp_localize_script( 'cpo-offset-presupuesto', 'cpoOffsetPresupuesto', $this->get_offset_script_config() );

        ob_start();
        ?>
        <div class="cpo-offset-presupuesto">
            <div class="cpo-card cpo-card--list">
                <div class="cpo-card__header">
                    <h2><?php esc_html_e( 'Mis Presupuestos', 'core-print-offset' ); ?></h2>
                    <p><?php esc_html_e( 'Reabre presupuestos, duplica o genera documentos de Core.', 'core-print-offset' ); ?></p>
                </div>
                <form method="get" class="cpo-filters">
                    <input type="hidden" name="page_id" value="<?php echo esc_attr( get_queried_object_id() ); ?>">
                    <label>
                        <?php esc_html_e( 'Buscar', 'core-print-offset' ); ?>
                        <input type="text" name="cpo_search" value="<?php echo esc_attr( $search ); ?>" placeholder="<?php esc_attr_e( 'Cliente o título', 'core-print-offset' ); ?>">
                    </label>
                    <label>
                        <?php esc_html_e( 'Estado', 'core-print-offset' ); ?>
                        <select name="cpo_estado">
                            <option value=""><?php esc_html_e( 'Todos', 'core-print-offset' ); ?></option>
                            <?php foreach ( array( 'borrador', 'enviado', 'aceptado', 'rechazado' ) as $estado_option ) : ?>
                                <option value="<?php echo esc_attr( $estado_option ); ?>" <?php selected( $estado, $estado_option ); ?>><?php echo esc_html( ucfirst( $estado_option ) ); ?></option>
                            <?php endforeach; ?>
                        </select>
                    </label>
                    <label>
                        <?php esc_html_e( 'Desde', 'core-print-offset' ); ?>
                        <input type="date" name="cpo_from" value="<?php echo esc_attr( $from ); ?>">
                    </label>
                    <label>
                        <?php esc_html_e( 'Hasta', 'core-print-offset' ); ?>
                        <input type="date" name="cpo_to" value="<?php echo esc_attr( $to ); ?>">
                    </label>
                    <button type="submit" class="cpo-button"><?php esc_html_e( 'Filtrar', 'core-print-offset' ); ?></button>
                </form>

                <div class="cpo-table-wrap">
                    <table class="cpo-table">
                        <thead>
                            <tr>
                                <th><?php esc_html_e( 'Título', 'core-print-offset' ); ?></th>
                                <th><?php esc_html_e( 'Cliente', 'core-print-offset' ); ?></th>
                                <th><?php esc_html_e( 'Fecha', 'core-print-offset' ); ?></th>
                                <th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th>
                                <th><?php esc_html_e( 'Total', 'core-print-offset' ); ?></th>
                                <th><?php esc_html_e( 'Acciones', 'core-print-offset' ); ?></th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php if ( empty( $presupuestos ) ) : ?>
                                <tr>
                                    <td colspan="6"><?php esc_html_e( 'No hay presupuestos para mostrar.', 'core-print-offset' ); ?></td>
                                </tr>
                            <?php else : ?>
                                <?php foreach ( $presupuestos as $presupuesto ) : ?>
                                    <tr data-presupuesto-id="<?php echo esc_attr( $presupuesto['id'] ); ?>">
                                        <td><?php echo esc_html( $presupuesto['titulo'] ); ?></td>
                                        <td><?php echo esc_html( $presupuesto['cliente_texto'] ?: '-' ); ?></td>
                                        <td><?php echo esc_html( mysql2date( 'd/m/Y', $presupuesto['created_at'] ) ); ?></td>
                                        <td><?php echo esc_html( ucfirst( $presupuesto['estado'] ) ); ?></td>
                                        <td><?php echo esc_html( $presupuesto['precio_total'] ); ?></td>
                                        <td class="cpo-table__actions">
                                            <?php $documento_id = (int) $presupuesto['orden_core_documento_id']; ?>
                                            <button type="button" class="cpo-link" data-cpo-open="<?php echo esc_attr( $presupuesto['id'] ); ?>"><?php esc_html_e( 'Abrir', 'core-print-offset' ); ?></button>
                                            <button type="button" class="cpo-link" data-cpo-duplicate="<?php echo esc_attr( $presupuesto['id'] ); ?>"><?php esc_html_e( 'Duplicar', 'core-print-offset' ); ?></button>
                                            <?php if ( $presupuesto['estado'] === 'aceptado' && empty( $presupuesto['orden_id'] ) ) : ?>
                                                <button type="button" class="cpo-link" data-cpo-create-order="<?php echo esc_attr( $presupuesto['id'] ); ?>"><?php esc_html_e( 'Crear OT', 'core-print-offset' ); ?></button>
                                            <?php elseif ( ! empty( $presupuesto['orden_id'] ) ) : ?>
                                                <?php if ( $documento_id > 0 ) : ?>
                                                    <span class="cpo-link"><?php echo esc_html( sprintf( __( 'Ver factura #%d', 'core-print-offset' ), $documento_id ) ); ?></span>
                                                <?php else : ?>
                                                    <button type="button" class="cpo-link" data-cpo-generate-invoice="<?php echo esc_attr( $presupuesto['orden_id'] ); ?>"><?php esc_html_e( 'Generar factura', 'core-print-offset' ); ?></button>
                                                <?php endif; ?>
                                            <?php endif; ?>
                                        </td>
                                    </tr>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </tbody>
                    </table>
                </div>

                <div class="cpo-list-cards">
                    <?php if ( empty( $presupuestos ) ) : ?>
                        <p><?php esc_html_e( 'No hay presupuestos para mostrar.', 'core-print-offset' ); ?></p>
                    <?php else : ?>
                        <?php foreach ( $presupuestos as $presupuesto ) : ?>
                            <?php $documento_id = (int) $presupuesto['orden_core_documento_id']; ?>
                            <article class="cpo-list-card" data-presupuesto-id="<?php echo esc_attr( $presupuesto['id'] ); ?>">
                                <h4><?php echo esc_html( $presupuesto['titulo'] ); ?></h4>
                                <p><strong><?php esc_html_e( 'Cliente:', 'core-print-offset' ); ?></strong> <?php echo esc_html( $presupuesto['cliente_texto'] ?: '-' ); ?></p>
                                <p><strong><?php esc_html_e( 'Fecha:', 'core-print-offset' ); ?></strong> <?php echo esc_html( mysql2date( 'd/m/Y', $presupuesto['created_at'] ) ); ?></p>
                                <p><strong><?php esc_html_e( 'Estado:', 'core-print-offset' ); ?></strong> <?php echo esc_html( ucfirst( $presupuesto['estado'] ) ); ?></p>
                                <p><strong><?php esc_html_e( 'Total:', 'core-print-offset' ); ?></strong> <?php echo esc_html( $presupuesto['precio_total'] ); ?></p>
                                <div class="cpo-list-card__actions">
                                    <button type="button" class="cpo-link" data-cpo-open="<?php echo esc_attr( $presupuesto['id'] ); ?>"><?php esc_html_e( 'Abrir', 'core-print-offset' ); ?></button>
                                    <button type="button" class="cpo-link" data-cpo-duplicate="<?php echo esc_attr( $presupuesto['id'] ); ?>"><?php esc_html_e( 'Duplicar', 'core-print-offset' ); ?></button>
                                    <?php if ( $presupuesto['estado'] === 'aceptado' && empty( $presupuesto['orden_id'] ) ) : ?>
                                        <button type="button" class="cpo-link" data-cpo-create-order="<?php echo esc_attr( $presupuesto['id'] ); ?>"><?php esc_html_e( 'Crear OT', 'core-print-offset' ); ?></button>
                                    <?php elseif ( ! empty( $presupuesto['orden_id'] ) ) : ?>
                                        <?php if ( $documento_id > 0 ) : ?>
                                            <span class="cpo-link"><?php echo esc_html( sprintf( __( 'Ver factura #%d', 'core-print-offset' ), $documento_id ) ); ?></span>
                                        <?php else : ?>
                                            <button type="button" class="cpo-link" data-cpo-generate-invoice="<?php echo esc_attr( $presupuesto['orden_id'] ); ?>"><?php esc_html_e( 'Generar factura', 'core-print-offset' ); ?></button>
                                        <?php endif; ?>
                                    <?php endif; ?>
                                </div>
                            </article>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </div>
            </div>
        </div>
        <?php
        return ob_get_clean();
    }

    private function get_offset_script_config(): array {
        return array(
            'ajaxUrl'       => admin_url( 'admin-ajax.php' ),
            'nonce'         => wp_create_nonce( 'cpo_offset_presupuesto' ),
            'canSave'       => is_user_logged_in(),
            'coreAvailable' => $this->core_bridge->has_core_api(),
            'canEditMachineCost' => current_user_can( 'manage_options' ),
            'canManageCoreDocs'  => current_user_can( 'manage_cpo_offset' ) || current_user_can( 'manage_options' ),
            'strings'       => array(
                'priceMissing' => __( 'No hay precio vigente para este material. Cargalo en Offset > Materiales/Precios', 'core-print-offset' ),
                'savingError'  => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ),
                'saved'        => __( 'Presupuesto guardado.', 'core-print-offset' ),
                'coreClientRequired' => __( 'Selecciona un cliente de Core para generar factura desde la OT.', 'core-print-offset' ),
                'coreSaveRequired'   => __( 'Guarda y acepta el presupuesto para crear la OT.', 'core-print-offset' ),
                'coreCreated'        => __( 'Factura generada en Core.', 'core-print-offset' ),
                'coreUnavailable'    => __( 'Core Global no está disponible.', 'core-print-offset' ),
                'loadFailed'         => __( 'No se pudo cargar el presupuesto.', 'core-print-offset' ),
                'duplicateFailed'    => __( 'No se pudo duplicar el presupuesto.', 'core-print-offset' ),
                'orderCreateFailed'  => __( 'No se pudo crear la orden de trabajo.', 'core-print-offset' ),
                'orderCreated'       => __( 'Orden de trabajo creada.', 'core-print-offset' ),
                'invoiceFromOrderFailed' => __( 'No se pudo generar la factura.', 'core-print-offset' ),
                'technicalIncomplete' => __( 'Complete los datos técnicos para continuar', 'core-print-offset' ),
            ),
        );
    }

    public function handle_convert_to_order() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para crear órdenes.', 'core-print-offset' ) ), 401 );
        }

        $presupuesto_id = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
        $numero_orden = sanitize_text_field( wp_unslash( $_POST['numero_orden'] ?? '' ) );
        $fecha_entrega = sanitize_text_field( wp_unslash( $_POST['fecha_entrega'] ?? '' ) );
        $notas = sanitize_textarea_field( wp_unslash( $_POST['notas'] ?? '' ) );

        if ( ! $presupuesto_id ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto inválido.', 'core-print-offset' ) ), 400 );
        }

        global $wpdb;
        $presupuesto = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
            ARRAY_A
        );

        if ( ! $presupuesto ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto no encontrado.', 'core-print-offset' ) ), 404 );
        }

        if ( ! $this->user_can_access_presupuesto( $presupuesto ) ) {
            wp_send_json_error( array( 'message' => __( 'forbidden', 'core-print-offset' ) ), 403 );
        }

        if ( ( $presupuesto['estado'] ?? '' ) !== 'aceptado' ) {
            wp_send_json_error( array( 'message' => __( 'Solo se pueden convertir presupuestos aceptados.', 'core-print-offset' ) ), 400 );
        }

        $existing_order = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_ordenes WHERE presupuesto_id = %d LIMIT 1", $presupuesto_id ),
            ARRAY_A
        );

        if ( $existing_order ) {
            wp_send_json_success(
                array(
                    'message' => __( 'La OT ya existe para este presupuesto.', 'core-print-offset' ),
                    'orden_id' => (int) $existing_order['id'],
                    'orden' => $existing_order,
                )
            );
        }

        $final_notas = $notas;
        if ( $numero_orden !== '' ) {
            $final_notas = trim( sprintf( "N° OT: %s\n%s", $numero_orden, $notas ) );
        }

        $inserted = $wpdb->insert(
            $wpdb->prefix . 'cpo_ordenes',
            array(
                'presupuesto_id'   => $presupuesto_id,
                'core_cliente_id'  => $presupuesto['core_cliente_id'],
                'core_documento_id'=> null,
                'titulo'           => $presupuesto['titulo'],
                'fecha_entrega'    => $fecha_entrega ?: null,
                'notas'            => $final_notas,
                'estado'           => 'pendiente',
                'created_at'       => cpo_now(),
                'updated_at'       => cpo_now(),
            )
        );

        if ( false === $inserted ) {
            wp_send_json_error( array( 'message' => __( 'No se pudo crear la OT.', 'core-print-offset' ) ), 500 );
        }

        $orden_id = (int) $wpdb->insert_id;
        $orden = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_ordenes WHERE id = %d", $orden_id ), ARRAY_A );

        wp_send_json_success(
            array(
                'message' => __( 'Orden de trabajo creada.', 'core-print-offset' ),
                'orden_id' => $orden_id,
                'orden' => $orden,
            )
        );
    }

    public function handle_get_ordenes() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para ver órdenes.', 'core-print-offset' ) ), 401 );
        }

        global $wpdb;

        $where = array( '1=1' );
        $params = array();

        if ( ! $this->user_can_manage_all_presupuestos() ) {
            $where[] = 'p.created_by = %d';
            $params[] = get_current_user_id();
        }

        $sql = "SELECT o.*, p.titulo AS presupuesto_titulo, p.estado AS presupuesto_estado, p.core_documento_id AS presupuesto_core_documento_id FROM {$wpdb->prefix}cpo_ordenes o INNER JOIN {$wpdb->prefix}cpo_presupuestos p ON p.id = o.presupuesto_id WHERE " . implode( ' AND ', $where ) . ' ORDER BY o.created_at DESC';
        if ( ! empty( $params ) ) {
            $sql = $wpdb->prepare( $sql, $params );
        }

        $ordenes = $wpdb->get_results( $sql, ARRAY_A );
        foreach ( $ordenes as &$orden ) {
            $orden['core_documento_id'] = isset( $orden['core_documento_id'] ) ? (int) $orden['core_documento_id'] : 0;
        }

        wp_send_json_success( array( 'ordenes' => $ordenes ) );
    }

    public function handle_generate_core_document_from_order() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para generar facturas.', 'core-print-offset' ) ), 401 );
        }

        if ( ! $this->core_bridge->has_core_api() ) {
            wp_send_json_error( array( 'message' => __( 'Core Global no está disponible.', 'core-print-offset' ) ), 400 );
        }

        $orden_id = isset( $_POST['orden_id'] ) ? intval( $_POST['orden_id'] ) : 0;
        if ( ! $orden_id ) {
            wp_send_json_error( array( 'message' => __( 'Orden inválida.', 'core-print-offset' ) ), 400 );
        }

        global $wpdb;
        $orden = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT o.*, p.id AS presupuesto_real_id, p.precio_total AS presupuesto_precio_total, p.core_documento_id AS presupuesto_core_documento_id, p.core_cliente_id AS presupuesto_core_cliente_id, p.cliente_id AS presupuesto_cliente_id, p.titulo AS presupuesto_titulo, p.created_by AS presupuesto_created_by FROM {$wpdb->prefix}cpo_ordenes o INNER JOIN {$wpdb->prefix}cpo_presupuestos p ON p.id = o.presupuesto_id WHERE o.id = %d",
                $orden_id
            ),
            ARRAY_A
        );

        if ( ! $orden ) {
            wp_send_json_error( array( 'message' => __( 'Orden no encontrada.', 'core-print-offset' ) ), 404 );
        }

        if ( ! $this->user_can_manage_all_presupuestos() ) {
            $created_by = isset( $orden['presupuesto_created_by'] ) ? (int) $orden['presupuesto_created_by'] : 0;
            if ( $created_by > 0 && $created_by !== get_current_user_id() ) {
                wp_send_json_error( array( 'message' => __( 'forbidden', 'core-print-offset' ) ), 403 );
            }
        }

        $existing_core_document_id = isset( $orden['core_documento_id'] ) ? (int) $orden['core_documento_id'] : 0;
        if ( $existing_core_document_id > 0 ) {
            wp_send_json_success(
                array(
                    'message' => __( 'La OT ya tiene factura en Core.', 'core-print-offset' ),
                    'core_documento_id' => $existing_core_document_id,
                )
            );
        }

        $total = isset( $orden['presupuesto_precio_total'] ) ? (float) $orden['presupuesto_precio_total'] : 0;
        if ( $total <= 0 ) {
            wp_send_json_error( array( 'message' => __( 'No se puede generar factura: el presupuesto tiene total en 0.', 'core-print-offset' ) ), 400 );
        }

        $cliente_id = isset( $orden['presupuesto_core_cliente_id'] ) ? (int) $orden['presupuesto_core_cliente_id'] : 0;
        if ( ! $cliente_id && isset( $orden['presupuesto_cliente_id'] ) ) {
            $cliente_id = (int) $orden['presupuesto_cliente_id'];
        }
        if ( ! $cliente_id ) {
            wp_send_json_error( array( 'message' => __( 'Selecciona un cliente de Core antes de generar factura.', 'core-print-offset' ) ), 400 );
        }

        $response = $this->core_bridge->create_core_document(
            array(
                'tipo'       => 'factura_venta',
                'titulo'     => $orden['presupuesto_titulo'],
                'cliente_id' => $cliente_id,
                'total'      => $total,
            )
        );

        if ( is_wp_error( $response ) ) {
            wp_send_json_error( array( 'message' => $response->get_error_message() ), 400 );
        }

        $core_documento_id = is_array( $response ) && isset( $response['id'] ) ? (int) $response['id'] : (int) $response;
        if ( $core_documento_id <= 0 ) {
            wp_send_json_error( array( 'message' => __( 'Core no devolvió un ID de documento válido.', 'core-print-offset' ) ), 400 );
        }

        $wpdb->update(
            $wpdb->prefix . 'cpo_presupuestos',
            array( 'core_documento_id' => $core_documento_id, 'updated_at' => cpo_now() ),
            array( 'id' => (int) $orden['presupuesto_real_id'] )
        );
        $wpdb->update(
            $wpdb->prefix . 'cpo_ordenes',
            array( 'core_documento_id' => $core_documento_id, 'updated_at' => cpo_now() ),
            array( 'id' => $orden_id )
        );

        $this->maybe_add_core_document_items( $core_documento_id, (int) $orden['presupuesto_real_id'] );

        wp_send_json_success(
            array(
                'message' => __( 'Factura generada en Core.', 'core-print-offset' ),
                'core_documento_id' => $core_documento_id,
            )
        );
    }

    public function handle_calculate() {
        $this->ensure_valid_nonce();

        $payload = $this->sanitize_payload( $_POST );
        $result  = CPO_Calculator::calculate( $payload );

        wp_send_json_success( $result );
    }

    public function handle_validate_structure() {
        $this->ensure_valid_nonce();

        $payload = $this->sanitize_payload( $_POST );
        $work_type = $this->resolve_work_type( $payload );
        $payload['work_type'] = $work_type;

        $validation = $this->validate_work_structure( $payload );
        $required_fields = $validation['required_fields'] ?? array();
        $missing_fields = $this->get_missing_required_fields( $required_fields, $payload );
        $can_calculate = empty( $missing_fields );

        $production_summary = '';
        if ( $can_calculate ) {
            $result = CPO_Calculator::calculate( $payload );
            $production_summary = (string) ( $result['production_summary'] ?? '' );
            if ( ! empty( $result['warnings'] ) && is_array( $result['warnings'] ) ) {
                $validation['warnings'] = array_values( array_unique( array_merge( $validation['warnings'] ?? array(), $result['warnings'] ) ) );
            }
        }

        wp_send_json_success(
            array(
                'work_structure' => array(
                    'tipo' => $work_type,
                    'multiplo' => (int) ( $validation['config']['multiplo_paginas'] ?? 0 ),
                ),
                'required_fields' => $required_fields,
                'missing_fields' => $missing_fields,
                'warnings' => $validation['warnings'] ?? array(),
                'production_summary' => $production_summary,
                'can_calculate' => $can_calculate,
            )
        );
    }

    public function handle_save_presupuesto() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para guardar.', 'core-print-offset' ) ), 401 );
        }

        $payload = $this->sanitize_payload( $_POST );
        $work_type = $this->resolve_work_type( $payload );
        $payload['work_type'] = $work_type;

        $worktype_validation = $this->validate_work_structure( $payload );
        $required_fields = $worktype_validation['required_fields'] ?? array();
        $missing_fields = $this->get_missing_required_fields( $required_fields, $payload );
        if ( ! empty( $missing_fields ) ) {
            wp_send_json_error(
                array(
                    'type' => 'missing_fields',
                    'fields' => $missing_fields,
                    'message' => __( 'Faltan datos para poder producir este trabajo', 'core-print-offset' ),
                    'required_fields' => $required_fields,
                    'warnings' => $worktype_validation['warnings'] ?? array(),
                ),
                422
            );
        }

        $result  = CPO_Calculator::calculate( $payload );

        if ( ! empty( $worktype_validation['warnings'] ) ) {
            $result['warnings'] = array_values(
                array_unique(
                    array_merge(
                        isset( $result['warnings'] ) && is_array( $result['warnings'] ) ? $result['warnings'] : array(),
                        $worktype_validation['warnings']
                    )
                )
            );
        }

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

        $presupuesto_id = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
        if ( $presupuesto_id ) {
            $presupuesto = $wpdb->get_row(
                $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
                ARRAY_A
            );

            if ( ! $presupuesto ) {
                wp_send_json_error( array( 'message' => __( 'Presupuesto no encontrado.', 'core-print-offset' ) ), 404 );
            }

            if ( ! $this->user_can_access_presupuesto( $presupuesto ) ) {
                wp_send_json_error( array( 'message' => __( 'forbidden', 'core-print-offset' ) ), 403 );
            }

            $update_payload = array(
                'core_cliente_id' => $cliente_id,
                'cliente_id'    => $cliente_id,
                'cliente_texto' => $cliente_texto ?: null,
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
                'updated_at'     => $now,
            );

            if ( empty( $presupuesto['created_by'] ) ) {
                $update_payload['created_by'] = get_current_user_id();
            }

            $updated = $wpdb->update(
                $wpdb->prefix . 'cpo_presupuestos',
                $update_payload,
                array( 'id' => $presupuesto_id )
            );

            if ( false === $updated ) {
                wp_send_json_error( array( 'message' => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ) ), 500 );
            }

            $wpdb->delete( $wpdb->prefix . 'cpo_presupuesto_items', array( 'presupuesto_id' => $presupuesto_id ) );
        } else {
            $inserted = $wpdb->insert(
                $wpdb->prefix . 'cpo_presupuestos',
                array(
                    'created_by'   => get_current_user_id(),
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
                array( '%d', '%d', '%d', '%s', '%d', '%s', '%s', '%s', '%d', '%d', '%s', '%d', '%f', '%s', '%f', '%f', '%s', '%s', '%d', '%s', '%s' )
            );

            if ( ! $inserted ) {
                wp_send_json_error( array( 'message' => __( 'No se pudo guardar el presupuesto.', 'core-print-offset' ) ), 500 );
            }

            $presupuesto_id = (int) $wpdb->insert_id;
        }
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

        $this->save_presupuesto_meta_value( $presupuesto_id, 'work_type', $work_type );

        wp_send_json_success(
            array(
                'message' => __( 'Presupuesto guardado.', 'core-print-offset' ),
                'id'      => $presupuesto_id,
                'cliente_id' => $cliente_id,
                'production_summary' => $result['production_summary'] ?? '',
                'work_structure' => array(
                    'tipo' => $work_type,
                    'multiplo' => (int) ( $worktype_validation['config']['multiplo_paginas'] ?? 0 ),
                ),
                'required_fields' => $required_fields,
                'missing_fields' => array(),
                'warnings' => $result['warnings'] ?? array(),
                'can_calculate' => true,
            )
        );
    }

    public function handle_get_presupuesto() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión.', 'core-print-offset' ) ), 401 );
        }

        $presupuesto_id = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
        if ( ! $presupuesto_id ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto inválido.', 'core-print-offset' ) ), 400 );
        }

        global $wpdb;
        $presupuesto = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
            ARRAY_A
        );
        if ( ! $presupuesto ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto no encontrado.', 'core-print-offset' ) ), 404 );
        }

        if ( ! $this->user_can_access_presupuesto( $presupuesto ) ) {
            wp_send_json_error( array( 'message' => __( 'forbidden', 'core-print-offset' ) ), 403 );
        }

        if ( empty( $presupuesto['created_by'] ) ) {
            $wpdb->update(
                $wpdb->prefix . 'cpo_presupuestos',
                array( 'created_by' => get_current_user_id() ),
                array( 'id' => $presupuesto_id )
            );
        }

        $payload = cpo_get_presupuesto_snapshot_payload( $presupuesto_id );
        $calc_result = array();
        if ( ! empty( $presupuesto['calc_result_json'] ) ) {
            $decoded = json_decode( $presupuesto['calc_result_json'], true );
            if ( is_array( $decoded ) ) {
                $calc_result = $decoded;
            }
        }

        wp_send_json_success(
            array(
                'id' => $presupuesto_id,
                'payload' => $payload,
                'calc_result' => $calc_result,
                'cliente_id' => (int) ( $presupuesto['cliente_id'] ?? $presupuesto['core_cliente_id'] ?? 0 ),
                'cliente_texto' => $presupuesto['cliente_texto'] ?? '',
            )
        );
    }

    public function handle_duplicate_presupuesto() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión.', 'core-print-offset' ) ), 401 );
        }

        $presupuesto_id = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
        if ( ! $presupuesto_id ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto inválido.', 'core-print-offset' ) ), 400 );
        }

        global $wpdb;
        $presupuesto = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
            ARRAY_A
        );
        if ( ! $presupuesto ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto no encontrado.', 'core-print-offset' ) ), 404 );
        }

        if ( ! $this->user_can_access_presupuesto( $presupuesto ) ) {
            wp_send_json_error( array( 'message' => __( 'forbidden', 'core-print-offset' ) ), 403 );
        }

        if ( empty( $presupuesto['created_by'] ) ) {
            $wpdb->update(
                $wpdb->prefix . 'cpo_presupuestos',
                array( 'created_by' => get_current_user_id() ),
                array( 'id' => $presupuesto_id )
            );
        }

        $result = cpo_duplicate_presupuesto( $presupuesto_id, get_current_user_id() );
        if ( is_wp_error( $result ) ) {
            wp_send_json_error( array( 'message' => $result->get_error_message() ), 400 );
        }

        wp_send_json_success(
            array(
                'message' => __( 'Presupuesto duplicado.', 'core-print-offset' ),
                'id'      => (int) $result,
            )
        );
    }

    public function handle_create_core_document() {
        $this->ensure_valid_nonce();

        if ( ! is_user_logged_in() ) {
            wp_send_json_error( array( 'message' => __( 'Debes iniciar sesión para crear órdenes.', 'core-print-offset' ) ), 401 );
        }

        $presupuesto_id = isset( $_POST['presupuesto_id'] ) ? intval( $_POST['presupuesto_id'] ) : 0;
        if ( ! $presupuesto_id ) {
            wp_send_json_error( array( 'message' => __( 'Guarda el presupuesto antes de crear la OT.', 'core-print-offset' ) ), 400 );
        }

        global $wpdb;
        $presupuesto = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_presupuestos WHERE id = %d", $presupuesto_id ),
            ARRAY_A
        );

        if ( ! $presupuesto ) {
            wp_send_json_error( array( 'message' => __( 'Presupuesto no encontrado.', 'core-print-offset' ) ), 404 );
        }

        if ( ! $this->user_can_access_presupuesto( $presupuesto ) ) {
            wp_send_json_error( array( 'message' => __( 'forbidden', 'core-print-offset' ) ), 403 );
        }

        if ( empty( $presupuesto['created_by'] ) ) {
            $wpdb->update(
                $wpdb->prefix . 'cpo_presupuestos',
                array( 'created_by' => get_current_user_id() ),
                array( 'id' => $presupuesto_id )
            );
        }

        $existing_order = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_ordenes WHERE presupuesto_id = %d LIMIT 1", $presupuesto_id ),
            ARRAY_A
        );
        if ( $existing_order ) {
            wp_send_json_success(
                array(
                    'message' => __( 'La OT ya existe para este presupuesto.', 'core-print-offset' ),
                    'orden_id' => (int) $existing_order['id'],
                    'orden' => $existing_order,
                )
            );
        }

        if ( ( $presupuesto['estado'] ?? '' ) !== 'aceptado' ) {
            wp_send_json_error( array( 'message' => __( 'Solo se pueden convertir presupuestos aceptados.', 'core-print-offset' ) ), 400 );
        }

        $inserted = $wpdb->insert(
            $wpdb->prefix . 'cpo_ordenes',
            array(
                'presupuesto_id'   => $presupuesto_id,
                'core_cliente_id'  => $presupuesto['core_cliente_id'],
                'core_documento_id'=> null,
                'titulo'           => $presupuesto['titulo'],
                'fecha_entrega'    => null,
                'notas'            => null,
                'estado'           => 'pendiente',
                'created_at'       => cpo_now(),
                'updated_at'       => cpo_now(),
            )
        );

        if ( false === $inserted ) {
            wp_send_json_error( array( 'message' => __( 'No se pudo crear la OT.', 'core-print-offset' ) ), 500 );
        }

        $orden_id = (int) $wpdb->insert_id;
        $orden = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_ordenes WHERE id = %d", $orden_id ), ARRAY_A );

        wp_send_json_success(
            array(
                'message' => __( 'Orden de trabajo creada.', 'core-print-offset' ),
                'orden_id' => $orden_id,
                'orden' => $orden,
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

    private function resolve_work_type( array $payload ): string {
        $work_type = sanitize_key( (string) ( $payload['work_type'] ?? 'otro' ) );
        if ( '' === $work_type ) {
            $work_type = 'otro';
        }

        return $work_type;
    }

    private function validate_work_structure( array $payload ): array {
        if ( ! $this->worktype_engine ) {
            return array(
                'work_type' => $this->resolve_work_type( $payload ),
                'config' => array(),
                'required_fields' => array(),
                'warnings' => array(),
            );
        }

        return $this->worktype_engine->validate_job_structure( $payload );
    }

    private function get_missing_required_fields( array $required_fields, array $payload ): array {
        $missing = array();

        foreach ( $required_fields as $field ) {
            if ( ! $this->has_payload_value( $payload, (string) $field ) ) {
                $missing[] = (string) $field;
            }
        }

        return array_values( array_unique( $missing ) );
    }

    private function has_payload_value( array $payload, string $field ): bool {
        if ( ! array_key_exists( $field, $payload ) ) {
            return false;
        }

        $value = $payload[ $field ];
        if ( is_bool( $value ) ) {
            return $value;
        }

        if ( is_numeric( $value ) ) {
            return (float) $value > 0;
        }

        return '' !== trim( (string) $value );
    }

    private function save_presupuesto_meta_value( int $presupuesto_id, string $meta_key, $meta_value ): void {
        if ( $presupuesto_id <= 0 || '' === $meta_key ) {
            return;
        }

        global $wpdb;

        $snapshot = wp_json_encode(
            array(
                'key' => $meta_key,
                'value' => $meta_value,
            ),
            JSON_UNESCAPED_UNICODE
        );

        $existing_id = (int) $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$wpdb->prefix}cpo_presupuesto_items WHERE presupuesto_id = %d AND tipo = 'meta' AND descripcion = %s ORDER BY id DESC LIMIT 1",
                $presupuesto_id,
                $meta_key
            )
        );

        if ( $existing_id > 0 ) {
            $wpdb->update(
                $wpdb->prefix . 'cpo_presupuesto_items',
                array(
                    'snapshot_json' => $snapshot,
                ),
                array( 'id' => $existing_id ),
                array( '%s' ),
                array( '%d' )
            );

            return;
        }

        $wpdb->insert(
            $wpdb->prefix . 'cpo_presupuesto_items',
            array(
                'presupuesto_id' => $presupuesto_id,
                'tipo' => 'meta',
                'referencia_id' => null,
                'descripcion' => $meta_key,
                'cantidad' => 1,
                'unitario' => 0,
                'subtotal' => 0,
                'snapshot_json' => $snapshot,
                'created_at' => cpo_now(),
            ),
            array( '%d', '%s', '%d', '%s', '%f', '%f', '%f', '%s', '%s' )
        );
    }

    private function user_can_manage_all_presupuestos(): bool {
        return current_user_can( 'manage_cpo_offset' ) || current_user_can( 'manage_options' );
    }

    private function user_can_access_presupuesto( array $presupuesto ): bool {
        if ( $this->user_can_manage_all_presupuestos() ) {
            return true;
        }

        $created_by = isset( $presupuesto['created_by'] ) ? (int) $presupuesto['created_by'] : 0;
        if ( ! $created_by ) {
            return true;
        }

        return $created_by === get_current_user_id();
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
