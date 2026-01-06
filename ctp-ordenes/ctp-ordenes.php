<?php
/**
 * Plugin Name: CTP Órdenes
 * Description: MVP para cargar y listar órdenes de CTP mediante shortcodes.
 * Version: 0.4.1
 * Author: Equipo Revista Montaje AI
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

define('CTP_ORDENES_VERSION', '0.4.1');

/**
 * Crea la tabla necesaria al activar el plugin.
 */
function ctp_ordenes_create_tables() {
    global $wpdb;

    $table_name = $wpdb->prefix . 'ctp_ordenes';
    $table_clientes = $wpdb->prefix . 'ctp_clientes';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';
    $table_liquidaciones = $wpdb->prefix . 'ctp_liquidaciones_cliente';
    $table_liquidacion_ordenes = $wpdb->prefix . 'ctp_liquidacion_ordenes';
    $charset_collate = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE {$table_name} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        fecha DATE NOT NULL,
        numero_orden VARCHAR(50) NOT NULL,
        cliente VARCHAR(150) NOT NULL,
        cliente_id BIGINT UNSIGNED NULL,
        descripcion TEXT NULL,
        cantidad_chapas INT NOT NULL DEFAULT 1,
        medida_chapa VARCHAR(20) NOT NULL,
        precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0,
        total DECIMAL(12,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        UNIQUE KEY numero_orden (numero_orden),
        KEY cliente_id (cliente_id)
    ) {$charset_collate};";

    $sql_clientes = "CREATE TABLE {$table_clientes} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        ruc VARCHAR(50) NULL,
        telefono VARCHAR(80) NULL,
        email VARCHAR(120) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id)
    ) {$charset_collate};";

    $sql_proveedores = "CREATE TABLE {$table_proveedores} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        ruc VARCHAR(50) NULL,
        telefono VARCHAR(80) NULL,
        email VARCHAR(120) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id)
    ) {$charset_collate};";

    $sql_facturas = "CREATE TABLE {$table_facturas} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        proveedor_id BIGINT UNSIGNED NOT NULL,
        fecha_factura DATE NOT NULL,
        nro_factura VARCHAR(60) NOT NULL,
        concepto VARCHAR(255) NULL,
        monto_total DECIMAL(14,2) NOT NULL DEFAULT 0,
        vencimiento DATE NULL,
        estado_pago VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        monto_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
        saldo DECIMAL(14,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        KEY proveedor_id (proveedor_id),
        KEY estado_pago (estado_pago),
        UNIQUE KEY proveedor_factura_unique (proveedor_id, nro_factura)
    ) {$charset_collate};";

    $sql_pagos = "CREATE TABLE {$table_pagos} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        factura_id BIGINT UNSIGNED NOT NULL,
        fecha_pago DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        metodo VARCHAR(40) NULL,
        nota VARCHAR(255) NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        KEY factura_id (factura_id)
    ) {$charset_collate};";

    $sql_liquidaciones = "CREATE TABLE {$table_liquidaciones} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        cliente_id BIGINT UNSIGNED NOT NULL,
        desde DATE NOT NULL,
        hasta DATE NOT NULL,
        total DECIMAL(14,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        estado VARCHAR(20) NOT NULL DEFAULT 'generada',
        nota TEXT NULL,
        PRIMARY KEY  (id),
        KEY cliente_id (cliente_id),
        KEY estado (estado)
    ) {$charset_collate};";

    $sql_liquidacion_ordenes = "CREATE TABLE {$table_liquidacion_ordenes} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        liquidacion_id BIGINT UNSIGNED NOT NULL,
        orden_id BIGINT UNSIGNED NOT NULL,
        PRIMARY KEY  (id),
        UNIQUE KEY orden_id (orden_id),
        KEY liquidacion_id (liquidacion_id)
    ) {$charset_collate};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
    dbDelta($sql_clientes);
    dbDelta($sql_proveedores);
    dbDelta($sql_facturas);
    dbDelta($sql_pagos);
    dbDelta($sql_liquidaciones);
    dbDelta($sql_liquidacion_ordenes);
}

function ctp_ordenes_activate() {
    ctp_ordenes_create_tables();
    update_option('ctp_ordenes_version', CTP_ORDENES_VERSION);
}
register_activation_hook(__FILE__, 'ctp_ordenes_activate');

function ctp_ordenes_maybe_upgrade() {
    $version = get_option('ctp_ordenes_version');
    if ($version !== CTP_ORDENES_VERSION) {
        ctp_ordenes_create_tables();
        update_option('ctp_ordenes_version', CTP_ORDENES_VERSION);
    }
}
add_action('plugins_loaded', 'ctp_ordenes_maybe_upgrade');

function ctp_ordenes_should_enqueue_assets() {
    if (!is_singular()) {
        return false;
    }

    global $post;
    if (!$post instanceof WP_Post) {
        return false;
    }

    $shortcodes = array(
        'ctp_cargar_orden',
        'ctp_listar_ordenes',
        'ctp_clientes',
        'ctp_proveedores',
        'ctp_facturas_proveedor',
        'ctp_liquidaciones',
        'ctp_dashboard',
    );

    foreach ($shortcodes as $shortcode) {
        if (has_shortcode($post->post_content, $shortcode)) {
            return true;
        }
    }

    return false;
}

/**
 * Encola assets solo cuando se renderiza un shortcode.
 */
function ctp_ordenes_enqueue_assets($force = false) {
    static $enqueued = false;
    if ($enqueued) {
        return;
    }

    if (!$force && !ctp_ordenes_should_enqueue_assets()) {
        return;
    }

    $plugin_url = plugin_dir_url(__FILE__);
    $plugin_path = plugin_dir_path(__FILE__);
    $style_path = $plugin_path . 'assets/style.css';
    $script_path = $plugin_path . 'assets/app.js';
    $style_version = file_exists($style_path) ? filemtime($style_path) : CTP_ORDENES_VERSION;
    $script_version = file_exists($script_path) ? filemtime($script_path) : CTP_ORDENES_VERSION;

    wp_enqueue_style(
        'ctp-ordenes-style',
        $plugin_url . 'assets/style.css',
        array(),
        $style_version
    );

    wp_enqueue_script(
        'ctp-ordenes-app',
        $plugin_url . 'assets/app.js',
        array(),
        $script_version,
        true
    );

    $enqueued = true;
}
add_action('wp_enqueue_scripts', 'ctp_ordenes_enqueue_assets');

function ctp_ordenes_render_alerts($mensajes) {
    if (empty($mensajes)) {
        return;
    }

    foreach ($mensajes as $tipo => $items) {
        if (empty($items)) {
            continue;
        }

        $class = 'ctp-alert';
        if ($tipo === 'success') {
            $class .= ' ctp-alert-success';
        } elseif ($tipo === 'warning') {
            $class .= ' ctp-alert-warning';
        } else {
            $class .= ' ctp-alert-error';
        }
        echo '<div class="' . esc_attr($class) . '"><ul>';
        foreach ($items as $mensaje) {
            echo '<li>' . esc_html($mensaje) . '</li>';
        }
        echo '</ul></div>';
    }
}

function ctp_ordenes_wrap($html, $class = '') {
    $classes = 'ctp-app';
    if (!empty($class)) {
        $classes .= ' ' . $class;
    }
    return '<div class="' . esc_attr($classes) . '"><div class="ctp-shell"><div class="ctp-shell-content">' . $html . '</div></div></div>';
}

function ctp_ordenes_get_medidas_chapa() {
    return array('510x400', '650x550', '745x605', '1030x770');
}

function ctp_ordenes_format_currency($value, $decimals = 0) {
    return number_format((float) $value, $decimals, ',', '.');
}

function ctp_ordenes_is_valid_date($date, $format) {
    if (empty($date)) {
        return false;
    }

    $parsed = DateTime::createFromFormat($format, $date);
    return $parsed && $parsed->format($format) === $date;
}

function ctp_ordenes_get_ordenes_periodo() {
    $default_month = current_time('Y-m');
    $default_start = current_time('Y-m-01');
    $default_end = current_time('Y-m-t');

    $type = isset($_GET['ctp_period']) ? sanitize_key(wp_unslash($_GET['ctp_period'])) : 'month';
    if (!in_array($type, array('month', 'range'), true)) {
        $type = 'month';
    }

    $month = isset($_GET['ctp_month']) ? sanitize_text_field(wp_unslash($_GET['ctp_month'])) : '';
    $from = isset($_GET['ctp_from']) ? sanitize_text_field(wp_unslash($_GET['ctp_from'])) : '';
    $to = isset($_GET['ctp_to']) ? sanitize_text_field(wp_unslash($_GET['ctp_to'])) : '';

    $start = $default_start;
    $end = $default_end;

    if ($type === 'month') {
        if (!ctp_ordenes_is_valid_date($month, 'Y-m')) {
            $month = $default_month;
        }
        $start = $month . '-01';
        $end = date('Y-m-t', strtotime($start));
        $from = $start;
        $to = $end;
    } else {
        $valid_from = ctp_ordenes_is_valid_date($from, 'Y-m-d');
        $valid_to = ctp_ordenes_is_valid_date($to, 'Y-m-d');

        if (!$valid_from && !$valid_to) {
            $type = 'month';
            $month = $default_month;
            $start = $default_start;
            $end = $default_end;
            $from = $start;
            $to = $end;
        } else {
            if (!$valid_from) {
                $from = $to;
            }
            if (!$valid_to) {
                $to = $from;
            }

            if (strtotime($from) > strtotime($to)) {
                $temp = $from;
                $from = $to;
                $to = $temp;
            }

            $start = $from;
            $end = $to;
        }
    }

    $label = $type === 'month'
        ? sprintf('Mes: %s', date_i18n('F Y', strtotime($start)))
        : sprintf(
            'Del %s al %s',
            date_i18n('d/m/Y', strtotime($start)),
            date_i18n('d/m/Y', strtotime($end))
        );

    return array(
        'type' => $type,
        'month' => $month ?: $default_month,
        'from' => $from,
        'to' => $to,
        'start' => $start,
        'end' => $end,
        'label' => $label,
    );
}

function ctp_ordenes_get_cliente_periodo() {
    $from = isset($_GET['ctp_cliente_from']) ? sanitize_text_field(wp_unslash($_GET['ctp_cliente_from'])) : '';
    $to = isset($_GET['ctp_cliente_to']) ? sanitize_text_field(wp_unslash($_GET['ctp_cliente_to'])) : '';

    $valid_from = ctp_ordenes_is_valid_date($from, 'Y-m-d');
    $valid_to = ctp_ordenes_is_valid_date($to, 'Y-m-d');

    if (!$valid_from) {
        $from = '';
    }
    if (!$valid_to) {
        $to = '';
    }

    if ($from && !$to) {
        $to = $from;
    }
    if ($to && !$from) {
        $from = $to;
    }

    if ($from && $to && strtotime($from) > strtotime($to)) {
        $temp = $from;
        $from = $to;
        $to = $temp;
    }

    return array(
        'from' => $from,
        'to' => $to,
        'has_filter' => !empty($from) && !empty($to),
    );
}

function ctp_ordenes_get_cliente($id) {
    if ($id <= 0) {
        return null;
    }

    global $wpdb;
    $table_clientes = $wpdb->prefix . 'ctp_clientes';

    return $wpdb->get_row(
        $wpdb->prepare("SELECT * FROM {$table_clientes} WHERE id = %d", $id)
    );
}

function ctp_ordenes_get_cliente_kpis($cliente_id, $periodo = array()) {
    if ($cliente_id <= 0) {
        return array(
            'cantidad' => 0,
            'total' => 0,
            'ultima_fecha' => null,
        );
    }

    global $wpdb;
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';

    $where = 'cliente_id = %d';
    $params = array($cliente_id);

    if (!empty($periodo['has_filter'])) {
        $where .= ' AND fecha BETWEEN %s AND %s';
        $params[] = $periodo['from'];
        $params[] = $periodo['to'];
    }

    $row = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT COUNT(*) AS cantidad,
                    COALESCE(SUM(total), 0) AS total,
                    MAX(fecha) AS ultima_fecha
             FROM {$table_ordenes}
             WHERE {$where}",
            $params
        )
    );

    $cantidad = $row ? (int) $row->cantidad : 0;
    $total = $row ? (float) $row->total : 0;

    return array(
        'cantidad' => $cantidad,
        'total' => $total,
        'ultima_fecha' => $row ? $row->ultima_fecha : null,
    );
}

function ctp_ordenes_get_ordenes_by_cliente($cliente_id, $periodo = array(), $limit = 50) {
    if ($cliente_id <= 0) {
        return array();
    }

    global $wpdb;
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';

    $where = 'cliente_id = %d';
    $params = array($cliente_id);

    if (!empty($periodo['has_filter'])) {
        $where .= ' AND fecha BETWEEN %s AND %s';
        $params[] = $periodo['from'];
        $params[] = $periodo['to'];
    }

    $params[] = (int) $limit;

    return $wpdb->get_results(
        $wpdb->prepare(
            "SELECT fecha, numero_orden, descripcion, cantidad_chapas, medida_chapa, precio_unitario, total
             FROM {$table_ordenes}
             WHERE {$where}
             ORDER BY fecha DESC, id DESC
             LIMIT %d",
            $params
        )
    );
}

function ctp_ordenes_render_panel($title, $subtitle, $content, $extra_class = '') {
    $classes = 'ctp-panel';
    if (!empty($extra_class)) {
        $classes .= ' ' . $extra_class;
    }

    ob_start();
    ?>
    <div class="<?php echo esc_attr($classes); ?>">
        <?php if (!empty($title) || !empty($subtitle)) : ?>
            <div class="ctp-panel-header">
                <?php if (!empty($title)) : ?>
                    <h3 class="ctp-panel-title"><?php echo esc_html($title); ?></h3>
                <?php endif; ?>
                <?php if (!empty($subtitle)) : ?>
                    <p class="ctp-panel-subtitle"><?php echo esc_html($subtitle); ?></p>
                <?php endif; ?>
            </div>
        <?php endif; ?>
        <div class="ctp-panel-body">
            <?php echo $content; ?>
        </div>
    </div>
    <?php
    return ob_get_clean();
}

function ctp_ordenes_recalculate_factura($factura_id) {
    global $wpdb;

    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';

    $factura = $wpdb->get_row(
        $wpdb->prepare("SELECT id, monto_total FROM {$table_facturas} WHERE id = %d", $factura_id)
    );

    if (!$factura) {
        return false;
    }

    $monto_total = (float) $factura->monto_total;
    $monto_pagado = (float) $wpdb->get_var(
        $wpdb->prepare(
            "SELECT COALESCE(SUM(monto), 0) FROM {$table_pagos} WHERE factura_id = %d",
            $factura_id
        )
    );

    if ($monto_pagado > $monto_total) {
        $monto_pagado = $monto_total;
    }

    $saldo = $monto_total - $monto_pagado;
    if ($saldo < 0) {
        $saldo = 0;
    }

    if ($monto_pagado <= 0) {
        $estado = 'pendiente';
    } elseif ($monto_pagado < $monto_total) {
        $estado = 'parcial';
    } else {
        $estado = 'pagado';
    }

    $wpdb->update(
        $table_facturas,
        array(
            'monto_pagado' => $monto_pagado,
            'saldo' => $saldo,
            'estado_pago' => $estado,
            'updated_at' => current_time('mysql'),
        ),
        array('id' => $factura_id),
        array('%f', '%f', '%s', '%s'),
        array('%d')
    );

    return array(
        'monto_pagado' => $monto_pagado,
        'saldo' => $saldo,
        'estado_pago' => $estado,
    );
}

function ctp_ordenes_get_clientes_list() {
    global $wpdb;
    $table_clientes = $wpdb->prefix . 'ctp_clientes';

    return $wpdb->get_results(
        "SELECT id, nombre FROM {$table_clientes} ORDER BY nombre ASC"
    );
}

function ctp_ordenes_get_ordenes_no_liquidadas($cliente_id, $from, $to) {
    if ($cliente_id <= 0 || empty($from) || empty($to)) {
        return array();
    }

    global $wpdb;
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';
    $table_liquidacion_ordenes = $wpdb->prefix . 'ctp_liquidacion_ordenes';

    return $wpdb->get_results(
        $wpdb->prepare(
            "SELECT o.id, o.fecha, o.numero_orden, o.descripcion, o.cantidad_chapas,
                    o.medida_chapa, o.precio_unitario, o.total
             FROM {$table_ordenes} o
             LEFT JOIN {$table_liquidacion_ordenes} lo ON lo.orden_id = o.id
             WHERE o.cliente_id = %d
               AND o.fecha BETWEEN %s AND %s
               AND lo.id IS NULL
             ORDER BY o.fecha ASC, o.id ASC",
            $cliente_id,
            $from,
            $to
        )
    );
}

/**
 * Shortcode: formulario para cargar una orden.
 */
function ctp_cargar_orden_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    $mensaje = '';
    $errores = array();

    if (!empty($_POST['ctp_cargar_orden_submit'])) {
        if (!isset($_POST['ctp_cargar_orden_nonce']) || !check_admin_referer('ctp_cargar_orden', 'ctp_cargar_orden_nonce')) {
            $errores[] = 'No se pudo validar la solicitud. Inténtalo nuevamente.';
        } else {
            $fecha = sanitize_text_field($_POST['fecha'] ?? '');
            $numero_orden = sanitize_text_field($_POST['numero_orden'] ?? '');
            $cliente_id = absint($_POST['cliente_id'] ?? 0);
            $cliente = sanitize_text_field($_POST['cliente'] ?? '');
            $descripcion = sanitize_textarea_field($_POST['descripcion'] ?? '');
            $cantidad_chapas = absint($_POST['cantidad_chapas'] ?? 1);
            $medida_chapa = sanitize_text_field($_POST['medida_chapa'] ?? '');
            $precio_unitario = floatval($_POST['precio_unitario'] ?? 0);

            if (empty($fecha)) {
                $errores[] = 'La fecha es obligatoria.';
            }
            if (empty($numero_orden)) {
                $errores[] = 'El número de orden es obligatorio.';
            }
            if ($cliente_id > 0) {
                global $wpdb;
                $table_clientes = $wpdb->prefix . 'ctp_clientes';
                $cliente_obj = $wpdb->get_row(
                    $wpdb->prepare(
                        "SELECT id, nombre FROM {$table_clientes} WHERE id = %d",
                        $cliente_id
                    )
                );
                if (!$cliente_obj) {
                    $errores[] = 'El cliente seleccionado no existe.';
                } else {
                    $cliente = $cliente_obj->nombre;
                }
            } elseif (empty($cliente)) {
                $errores[] = 'El cliente es obligatorio.';
            }
            if ($cantidad_chapas < 1) {
                $cantidad_chapas = 1;
            }
            $medidas_validas = ctp_ordenes_get_medidas_chapa();
            if (!in_array($medida_chapa, $medidas_validas, true)) {
                $errores[] = 'Selecciona una medida de chapa válida.';
            }

            if (empty($errores)) {
                global $wpdb;
                $table_name = $wpdb->prefix . 'ctp_ordenes';

                $existe = $wpdb->get_var(
                    $wpdb->prepare(
                        "SELECT COUNT(*) FROM {$table_name} WHERE numero_orden = %s",
                        $numero_orden
                    )
                );

                if ($existe) {
                    $errores[] = 'El número de orden ya existe. Usa uno diferente.';
                } else {
                    $total = $cantidad_chapas * $precio_unitario;
                    $now = current_time('mysql');

                    $insertado = $wpdb->insert(
                        $table_name,
                        array(
                            'fecha' => $fecha,
                            'numero_orden' => $numero_orden,
                            'cliente' => $cliente,
                            'cliente_id' => $cliente_id > 0 ? $cliente_id : null,
                            'descripcion' => $descripcion,
                            'cantidad_chapas' => $cantidad_chapas,
                            'medida_chapa' => $medida_chapa,
                            'precio_unitario' => $precio_unitario,
                            'total' => $total,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%s', '%s', '%s', '%d', '%s', '%d', '%s', '%f', '%f', '%s', '%s')
                    );

                    if ($insertado) {
                        $mensaje = 'Orden guardada correctamente.';
                        $_POST = array();
                    } else {
                        $errores[] = 'No se pudo guardar la orden. Intenta nuevamente.';
                    }
                }
            }
        }
    }

    global $wpdb;
    $table_clientes = $wpdb->prefix . 'ctp_clientes';
    $clientes = $wpdb->get_results(
        "SELECT id, nombre FROM {$table_clientes} ORDER BY nombre ASC"
    );

    $fecha_default = !empty($_POST['fecha']) ? sanitize_text_field($_POST['fecha']) : current_time('Y-m-d');
    $numero_orden_val = !empty($_POST['numero_orden']) ? sanitize_text_field($_POST['numero_orden']) : '';
    $cliente_id_val = !empty($_POST['cliente_id']) ? absint($_POST['cliente_id']) : 0;
    $cliente_val = !empty($_POST['cliente']) ? sanitize_text_field($_POST['cliente']) : '';
    if ($cliente_id_val > 0 && empty($cliente_val)) {
        foreach ($clientes as $cliente_obj) {
            if ((int) $cliente_obj->id === $cliente_id_val) {
                $cliente_val = $cliente_obj->nombre;
                break;
            }
        }
    }
    $descripcion_val = !empty($_POST['descripcion']) ? sanitize_textarea_field($_POST['descripcion']) : '';
    $cantidad_val = !empty($_POST['cantidad_chapas']) ? absint($_POST['cantidad_chapas']) : 1;
    $medidas = ctp_ordenes_get_medidas_chapa();
    $medida_val = !empty($_POST['medida_chapa']) ? sanitize_text_field($_POST['medida_chapa']) : $medidas[0];
    $precio_val = isset($_POST['precio_unitario']) ? floatval($_POST['precio_unitario']) : 0;
    $total_val = $cantidad_val * $precio_val;

    ob_start();
    ?>
    <form method="post" class="ctp-form ctp-form-grid ctp-order-form">
            <?php wp_nonce_field('ctp_cargar_orden', 'ctp_cargar_orden_nonce'); ?>
            <input type="hidden" name="ctp_cargar_orden_submit" value="1">

            <div class="ctp-field">
                <label for="ctp-fecha">Fecha</label>
                <input type="date" id="ctp-fecha" name="fecha" required value="<?php echo esc_attr($fecha_default); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-numero-orden">Número de orden</label>
                <input type="text" id="ctp-numero-orden" name="numero_orden" required value="<?php echo esc_attr($numero_orden_val); ?>">
            </div>

            <div class="ctp-field ctp-field-full ctp-client-picker">
                <label for="ctp-cliente-select">Cliente registrado</label>
                <input type="text" id="ctp-orden-cliente-search" class="ctp-client-search" data-target="ctp-cliente-select" placeholder="Buscar cliente...">
                <select id="ctp-cliente-select" name="cliente_id" class="ctp-client-select">
                    <option value="0">Ingresar manual / Sin cliente</option>
                    <?php foreach ($clientes as $cliente_item) : ?>
                        <option value="<?php echo esc_attr($cliente_item->id); ?>" <?php selected($cliente_id_val, (int) $cliente_item->id); ?>>
                            <?php echo esc_html($cliente_item->nombre); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-cliente">Cliente (manual)</label>
                <input type="text" id="ctp-cliente" name="cliente" class="ctp-client-name" required value="<?php echo esc_attr($cliente_val); ?>">
            </div>

            <div class="ctp-field ctp-field-full">
                <label for="ctp-descripcion">Descripción</label>
                <textarea id="ctp-descripcion" name="descripcion" rows="3"><?php echo esc_textarea($descripcion_val); ?></textarea>
            </div>

            <div class="ctp-field">
                <label for="ctp-cantidad">Cantidad de chapas</label>
                <input type="number" id="ctp-cantidad" class="ctp-quantity" name="cantidad_chapas" min="1" value="<?php echo esc_attr($cantidad_val); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-medida">Medida de chapa</label>
                <select id="ctp-medida" name="medida_chapa" required>
                    <?php
                    foreach ($medidas as $medida) :
                        $selected = $medida === $medida_val ? 'selected' : '';
                        ?>
                        <option value="<?php echo esc_attr($medida); ?>" <?php echo esc_attr($selected); ?>>
                            <?php echo esc_html($medida); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-precio">Precio unitario</label>
                <input type="number" id="ctp-precio" class="ctp-price" name="precio_unitario" step="0.01" min="0" value="<?php echo esc_attr($precio_val); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-total">Total</label>
                <input type="number" id="ctp-total" class="ctp-total" name="total" readonly value="<?php echo esc_attr(number_format($total_val, 2, '.', '')); ?>">
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button">Guardar orden</button>
            </div>
        </form>
    <?php
    $form_html = ob_get_clean();

    ob_start();
    if (!empty($mensaje)) {
        echo '<div class="ctp-alert ctp-alert-success">' . esc_html($mensaje) . '</div>';
    }
    if (!empty($errores)) {
        echo '<div class="ctp-alert ctp-alert-error"><ul>';
        foreach ($errores as $error) {
            echo '<li>' . esc_html($error) . '</li>';
        }
        echo '</ul></div>';
    }
    echo $form_html;
    $panel_body = ob_get_clean();

    $html = ctp_ordenes_render_panel(
        'Nueva orden',
        'Registra una orden y calcula el total automáticamente.',
        $panel_body,
        'ctp-panel-form'
    );
    if (!empty($GLOBALS['ctp_in_dashboard'])) {
        return $html;
    }
    return ctp_ordenes_wrap($html, 'ctp-shell-page');
}
add_shortcode('ctp_cargar_orden', 'ctp_cargar_orden_shortcode');

/**
 * Shortcode: tabla con las últimas 50 órdenes.
 */
function ctp_listar_ordenes_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $wpdb = $GLOBALS['wpdb'];
    $table_name = $wpdb->prefix . 'ctp_ordenes';
    $table_clientes = $wpdb->prefix . 'ctp_clientes';

    $periodo = ctp_ordenes_get_ordenes_periodo();
    $where_clause = 'fecha BETWEEN %s AND %s';
    $where_params = array($periodo['start'], $periodo['end']);

    $ordenes = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT o.fecha, o.numero_orden, COALESCE(c.nombre, o.cliente) AS cliente_nombre,
                    o.medida_chapa, o.cantidad_chapas, o.precio_unitario, o.total
             FROM {$table_name} o
             LEFT JOIN {$table_clientes} c ON o.cliente_id = c.id
             WHERE {$where_clause}
             ORDER BY o.fecha DESC, o.id DESC
             LIMIT 50",
            $where_params
        )
    );

    $resumen = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS total
             FROM {$table_name}
             WHERE {$where_clause}",
            $where_params
        )
    );

    $ordenes_cantidad = $resumen ? (int) $resumen->cantidad : 0;
    $ordenes_total = $resumen ? (float) $resumen->total : 0;

    $base_url = remove_query_arg(array('ctp_period', 'ctp_month', 'ctp_from', 'ctp_to'));
    $tab = isset($_GET['tab']) ? sanitize_key(wp_unslash($_GET['tab'])) : '';
    $from_value = $periodo['from'];
    $to_value = $periodo['to'];

    ob_start();
    ?>
    <form method="get" action="<?php echo esc_url($base_url); ?>" class="ctp-order-filter">
        <?php if (!empty($tab)) : ?>
            <input type="hidden" name="tab" value="<?php echo esc_attr($tab); ?>">
        <?php endif; ?>
        <div class="ctp-filter-fields" data-mode="<?php echo esc_attr($periodo['type']); ?>">
            <div class="ctp-filter-type">
                <label class="ctp-choice">
                    <input type="radio" name="ctp_period" value="month" <?php checked($periodo['type'], 'month'); ?>>
                    <span>Mes</span>
                </label>
                <label class="ctp-choice">
                    <input type="radio" name="ctp_period" value="range" <?php checked($periodo['type'], 'range'); ?>>
                    <span>Rango</span>
                </label>
            </div>
            <div class="ctp-filter-group ctp-filter-month">
                <div class="ctp-field">
                    <label for="ctp-filter-month">Mes</label>
                    <input type="month" id="ctp-filter-month" name="ctp_month" value="<?php echo esc_attr($periodo['month']); ?>">
                </div>
            </div>
            <div class="ctp-filter-group ctp-filter-range">
                <div class="ctp-field">
                    <label for="ctp-filter-from">Desde</label>
                    <input type="date" id="ctp-filter-from" name="ctp_from" value="<?php echo esc_attr($from_value); ?>">
                </div>
                <div class="ctp-field">
                    <label for="ctp-filter-to">Hasta</label>
                    <input type="date" id="ctp-filter-to" name="ctp_to" value="<?php echo esc_attr($to_value); ?>">
                </div>
            </div>
            <div class="ctp-filter-actions">
                <button type="submit" class="ctp-button">Aplicar</button>
                <a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($base_url); ?>">Limpiar</a>
            </div>
        </div>
    </form>
    <div class="ctp-kpi-grid">
        <div class="ctp-kpi-card">
            <div class="ctp-kpi-title">Total de órdenes</div>
            <div class="ctp-kpi-value"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($ordenes_total)); ?></div>
            <div class="ctp-kpi-meta"><?php echo esc_html($periodo['label']); ?></div>
        </div>
        <div class="ctp-kpi-card">
            <div class="ctp-kpi-title">Cantidad de órdenes</div>
            <div class="ctp-kpi-value"><?php echo esc_html(ctp_ordenes_format_currency($ordenes_cantidad)); ?></div>
            <div class="ctp-kpi-meta"><?php echo esc_html($periodo['label']); ?></div>
        </div>
    </div>
    <div class="ctp-table-wrap">
        <table class="ctp-table">
        <thead>
            <tr>
                <th>Fecha</th>
                <th>Nº Orden</th>
                <th>Cliente</th>
                <th>Medida</th>
                <th>Cantidad</th>
                <th>Unitario</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            <?php if (!empty($ordenes)) : ?>
                <?php foreach ($ordenes as $orden) : ?>
                    <tr>
                        <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                        <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                        <td data-label="Cliente"><?php echo esc_html($orden->cliente_nombre); ?></td>
                        <td data-label="Medida"><?php echo esc_html($orden->medida_chapa); ?></td>
                        <td data-label="Cantidad"><?php echo esc_html($orden->cantidad_chapas); ?></td>
                        <td data-label="Unitario"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->precio_unitario)); ?></td>
                        <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                    </tr>
                <?php endforeach; ?>
            <?php else : ?>
                <tr>
                    <td colspan="7">No hay órdenes registradas.</td>
                </tr>
            <?php endif; ?>
        </tbody>
        </table>
    </div>
    <?php
    $table_html = ob_get_clean();
    $html = ctp_ordenes_render_panel(
        'Órdenes del período',
        'Listado filtrado según el período seleccionado (máximo 50 órdenes).',
        $table_html
    );
    if (!empty($GLOBALS['ctp_in_dashboard'])) {
        return $html;
    }
    return ctp_ordenes_wrap($html, 'ctp-shell-page');
}
add_shortcode('ctp_listar_ordenes', 'ctp_listar_ordenes_shortcode');

function ctp_ordenes_user_can_manage() {
    return current_user_can('edit_posts');
}

/**
 * Shortcode: gestión de clientes.
 */
function ctp_clientes_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_clientes = $wpdb->prefix . 'ctp_clientes';
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    $can_manage = ctp_ordenes_user_can_manage();

    if (!empty($_POST['ctp_cliente_action'])) {
        if (!$can_manage) {
            $mensajes['error'][] = 'No tienes permisos para gestionar clientes.';
        } else {
            $action = sanitize_text_field(wp_unslash($_POST['ctp_cliente_action']));

            if ($action === 'add') {
                if (!isset($_POST['ctp_cliente_nonce']) || !check_admin_referer('ctp_cliente_add', 'ctp_cliente_nonce')) {
                    $mensajes['error'][] = 'No se pudo validar la solicitud para agregar cliente.';
                } else {
                    $nombre = sanitize_text_field(wp_unslash($_POST['nombre'] ?? ''));
                    $ruc = sanitize_text_field(wp_unslash($_POST['ruc'] ?? ''));
                    $telefono = sanitize_text_field(wp_unslash($_POST['telefono'] ?? ''));
                    $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
                    $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

                    if (empty($nombre)) {
                        $mensajes['error'][] = 'El nombre del cliente es obligatorio.';
                    } else {
                        $now = current_time('mysql');
                        $inserted = $wpdb->insert(
                            $table_clientes,
                            array(
                                'nombre' => $nombre,
                                'ruc' => $ruc,
                                'telefono' => $telefono,
                                'email' => $email,
                                'notas' => $notas,
                                'created_at' => $now,
                                'updated_at' => $now,
                            ),
                            array('%s', '%s', '%s', '%s', '%s', '%s', '%s')
                        );

                        if ($inserted) {
                            $mensajes['success'][] = 'Cliente agregado correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo guardar el cliente.';
                        }
                    }
                }
            } elseif ($action === 'edit') {
                if (!isset($_POST['ctp_cliente_nonce']) || !check_admin_referer('ctp_cliente_edit', 'ctp_cliente_nonce')) {
                    $mensajes['error'][] = 'No se pudo validar la solicitud para editar cliente.';
                } else {
                    $cliente_id = absint($_POST['cliente_id'] ?? 0);
                    $nombre = sanitize_text_field(wp_unslash($_POST['nombre'] ?? ''));
                    $ruc = sanitize_text_field(wp_unslash($_POST['ruc'] ?? ''));
                    $telefono = sanitize_text_field(wp_unslash($_POST['telefono'] ?? ''));
                    $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
                    $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

                    if ($cliente_id <= 0 || empty($nombre)) {
                        $mensajes['error'][] = 'Datos inválidos para actualizar cliente.';
                    } else {
                        $actualizado = $wpdb->update(
                            $table_clientes,
                            array(
                                'nombre' => $nombre,
                                'ruc' => $ruc,
                                'telefono' => $telefono,
                                'email' => $email,
                                'notas' => $notas,
                                'updated_at' => current_time('mysql'),
                            ),
                            array('id' => $cliente_id),
                            array('%s', '%s', '%s', '%s', '%s', '%s'),
                            array('%d')
                        );

                        if ($actualizado !== false) {
                            $mensajes['success'][] = 'Cliente actualizado correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo actualizar el cliente.';
                        }
                    }
                }
            } elseif ($action === 'delete') {
                if (!isset($_POST['ctp_cliente_nonce']) || !check_admin_referer('ctp_cliente_delete', 'ctp_cliente_nonce')) {
                    $mensajes['error'][] = 'No se pudo validar la solicitud para eliminar cliente.';
                } else {
                    $cliente_id = absint($_POST['cliente_id'] ?? 0);
                    if ($cliente_id <= 0) {
                        $mensajes['error'][] = 'Cliente inválido.';
                    } else {
                        $tiene_ordenes = (int) $wpdb->get_var(
                            $wpdb->prepare(
                                "SELECT COUNT(*) FROM {$table_ordenes} WHERE cliente_id = %d",
                                $cliente_id
                            )
                        );

                        if ($tiene_ordenes > 0) {
                            $mensajes['error'][] = 'No se puede eliminar el cliente porque tiene órdenes asociadas.';
                        } else {
                            $deleted = $wpdb->delete($table_clientes, array('id' => $cliente_id), array('%d'));
                            if ($deleted) {
                                $mensajes['success'][] = 'Cliente eliminado correctamente.';
                            } else {
                                $mensajes['error'][] = 'No se pudo eliminar el cliente.';
                            }
                        }
                    }
                }
            }
        }
    }

    $search = sanitize_text_field(wp_unslash($_GET['ctp_cliente_search'] ?? ''));
    $where = array('1=1');
    $params = array();
    if (!empty($search)) {
        $where[] = 'nombre LIKE %s';
        $params[] = '%' . $wpdb->esc_like($search) . '%';
    }

    $sql = "SELECT * FROM {$table_clientes} WHERE " . implode(' AND ', $where) . " ORDER BY created_at DESC, id DESC LIMIT 200";
    if (!empty($params)) {
        $sql = $wpdb->prepare($sql, $params);
    }

    $clientes = $wpdb->get_results($sql);

    $base_url = remove_query_arg('ctp_cliente_search');
    $current_url = remove_query_arg(array('ctp_cliente_id', 'ctp_cliente_from', 'ctp_cliente_to'));
    if (isset($_GET['ctp_tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['ctp_tab']));
    } elseif (isset($_GET['tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['tab']));
    } else {
        $tab = '';
    }

    $cliente_id = isset($_GET['ctp_cliente_id']) ? absint($_GET['ctp_cliente_id']) : 0;
    if ($cliente_id > 0) {
        $cliente = ctp_ordenes_get_cliente($cliente_id);
        $periodo = ctp_ordenes_get_cliente_periodo();
        $ordenes = $cliente ? ctp_ordenes_get_ordenes_by_cliente($cliente_id, $periodo, 50) : array();
        $kpis = $cliente ? ctp_ordenes_get_cliente_kpis($cliente_id, $periodo) : array(
            'cantidad' => 0,
            'total' => 0,
            'ultima_fecha' => null,
        );

        $back_url = $current_url;
        if (!empty($tab)) {
            $back_url = add_query_arg('ctp_tab', $tab, $back_url);
        }

        $filter_url = $current_url;
        $filter_args = array('ctp_cliente_id' => $cliente_id);
        if (!empty($tab)) {
            $filter_args['ctp_tab'] = $tab;
        }
        $filter_url = add_query_arg($filter_args, $filter_url);

        $periodo_label = 'Todas las fechas';
        if (!empty($periodo['has_filter'])) {
            $periodo_label = sprintf(
                'Del %s al %s',
                date_i18n('d/m/Y', strtotime($periodo['from'])),
                date_i18n('d/m/Y', strtotime($periodo['to']))
            );
        }

        ob_start();
        if (!$cliente) {
            echo '<div class="ctp-alert ctp-alert-error">El cliente seleccionado no existe.</div>';
        } else {
            ?>
            <div class="ctp-stack">
                <div class="ctp-panel ctp-panel-client">
                    <div class="ctp-panel-body">
                        <div class="ctp-client-header">
                            <div class="ctp-client-meta">
                                <h3 class="ctp-client-title"><?php echo esc_html($cliente->nombre); ?></h3>
                                <div class="ctp-client-meta-list">
                                    <?php if (!empty($cliente->ruc)) : ?>
                                        <div class="ctp-client-meta-item"><span>RUC:</span> <?php echo esc_html($cliente->ruc); ?></div>
                                    <?php endif; ?>
                                    <?php if (!empty($cliente->telefono)) : ?>
                                        <div class="ctp-client-meta-item"><span>Teléfono:</span> <?php echo esc_html($cliente->telefono); ?></div>
                                    <?php endif; ?>
                                    <?php if (!empty($cliente->email)) : ?>
                                        <div class="ctp-client-meta-item"><span>Email:</span> <?php echo esc_html($cliente->email); ?></div>
                                    <?php endif; ?>
                                </div>
                                <?php if (!empty($cliente->notas)) : ?>
                                    <p class="ctp-client-notes"><?php echo esc_html($cliente->notas); ?></p>
                                <?php endif; ?>
                            </div>
                            <div class="ctp-client-actions">
                                <a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($back_url); ?>">Volver a clientes</a>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="ctp-panel">
                    <div class="ctp-panel-header">
                        <h3 class="ctp-panel-title">Resumen del cliente</h3>
                        <p class="ctp-panel-subtitle"><?php echo esc_html($periodo_label); ?></p>
                    </div>
                    <div class="ctp-panel-body">
                        <div class="ctp-kpi-grid">
                            <div class="ctp-kpi-card">
                                <div class="ctp-kpi-title">Cantidad de órdenes</div>
                                <div class="ctp-kpi-value"><?php echo esc_html(ctp_ordenes_format_currency($kpis['cantidad'])); ?></div>
                            </div>
                            <div class="ctp-kpi-card">
                                <div class="ctp-kpi-title">Total Gs</div>
                                <div class="ctp-kpi-value"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($kpis['total'])); ?></div>
                            </div>
                            <div class="ctp-kpi-card">
                                <div class="ctp-kpi-title">Última fecha</div>
                                <div class="ctp-kpi-value">
                                    <?php echo esc_html($kpis['ultima_fecha'] ? date_i18n('d/m/Y', strtotime($kpis['ultima_fecha'])) : '—'); ?>
                                </div>
                            </div>
                        </div>
                        <form method="get" action="<?php echo esc_url($filter_url); ?>" class="ctp-form ctp-form-inline ctp-client-filter">
                            <div class="ctp-field">
                                <label for="ctp-cliente-from">Desde</label>
                                <input type="date" id="ctp-cliente-from" name="ctp_cliente_from" value="<?php echo esc_attr($periodo['from']); ?>">
                            </div>
                            <div class="ctp-field">
                                <label for="ctp-cliente-to">Hasta</label>
                                <input type="date" id="ctp-cliente-to" name="ctp_cliente_to" value="<?php echo esc_attr($periodo['to']); ?>">
                            </div>
                            <div class="ctp-field">
                                <button type="submit" class="ctp-button">Filtrar</button>
                            </div>
                            <div class="ctp-field">
                                <a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($filter_url); ?>">Limpiar</a>
                            </div>
                        </form>
                    </div>
                </div>
                <div class="ctp-panel">
                    <div class="ctp-panel-header">
                        <h3 class="ctp-panel-title">Órdenes del cliente</h3>
                        <p class="ctp-panel-subtitle">Últimas 50 órdenes asociadas al cliente.</p>
                    </div>
                    <div class="ctp-panel-body">
                        <div class="ctp-table-wrap">
                            <table class="ctp-table">
                                <thead>
                                    <tr>
                                        <th>Fecha</th>
                                        <th>Nº Orden</th>
                                        <th>Descripción</th>
                                        <th>Cantidad</th>
                                        <th>Medida</th>
                                        <th>Unitario</th>
                                        <th>Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php if (!empty($ordenes)) : ?>
                                        <?php foreach ($ordenes as $orden) : ?>
                                            <tr>
                                                <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                                                <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                                                <td data-label="Descripción"><?php echo esc_html($orden->descripcion); ?></td>
                                                <td data-label="Cantidad"><?php echo esc_html($orden->cantidad_chapas); ?></td>
                                                <td data-label="Medida"><?php echo esc_html($orden->medida_chapa); ?></td>
                                                <td data-label="Unitario"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->precio_unitario)); ?></td>
                                                <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                                            </tr>
                                        <?php endforeach; ?>
                                    <?php else : ?>
                                        <tr>
                                            <td colspan="7">No hay órdenes asociadas.</td>
                                        </tr>
                                    <?php endif; ?>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <?php
        }
        $html = ob_get_clean();
        if (!empty($GLOBALS['ctp_in_dashboard'])) {
            return $html;
        }
        return ctp_ordenes_wrap($html, 'ctp-shell-page');
    }

    ob_start();
    ?>
    <?php ctp_ordenes_render_alerts($mensajes); ?>
    <div class="ctp-stack">
        <?php
        ob_start();
        ?>
        <form method="post" class="ctp-form ctp-form-grid">
            <?php wp_nonce_field('ctp_cliente_add', 'ctp_cliente_nonce'); ?>
            <input type="hidden" name="ctp_cliente_action" value="add">

            <div class="ctp-field">
                <label for="ctp-cliente-nombre">Nombre / Razón social</label>
                <input type="text" id="ctp-cliente-nombre" name="nombre" required <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field">
                <label for="ctp-cliente-ruc">RUC</label>
                <input type="text" id="ctp-cliente-ruc" name="ruc" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field">
                <label for="ctp-cliente-telefono">Teléfono</label>
                <input type="text" id="ctp-cliente-telefono" name="telefono" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field">
                <label for="ctp-cliente-email">Email</label>
                <input type="email" id="ctp-cliente-email" name="email" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field ctp-field-full">
                <label for="ctp-cliente-notas">Notas</label>
                <textarea id="ctp-cliente-notas" name="notas" rows="3" <?php disabled(!$can_manage); ?>></textarea>
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button" <?php disabled(!$can_manage); ?>>Agregar cliente</button>
            </div>
        </form>
        <?php
        $form_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Nuevo cliente',
            'Agrega clientes para reutilizarlos en las órdenes.',
            $form_html,
            'ctp-panel-form'
        );

        ob_start();
        ?>
        <form method="get" action="<?php echo esc_url($base_url); ?>" class="ctp-form ctp-form-inline">
            <?php if (!empty($tab)) : ?>
                <input type="hidden" name="ctp_tab" value="<?php echo esc_attr($tab); ?>">
            <?php endif; ?>
            <div class="ctp-field">
                <label for="ctp-cliente-search">Buscar</label>
                <input type="text" id="ctp-cliente-search" name="ctp_cliente_search" value="<?php echo esc_attr($search); ?>" placeholder="Nombre o razón social">
            </div>
            <div class="ctp-field">
                <button type="submit" class="ctp-button ctp-button-secondary">Buscar</button>
            </div>
        </form>
        <?php
        $filters_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Buscar clientes',
            'Filtra la lista por nombre o razón social.',
            $filters_html,
            'ctp-panel-filters'
        );

        ob_start();
        ?>
        <div class="ctp-table-wrap">
            <table class="ctp-table">
                <thead>
                    <tr>
                        <th>Nombre</th>
                        <th>RUC</th>
                        <th>Teléfono</th>
                        <th>Email</th>
                        <th class="ctp-table-text">Notas</th>
                        <th class="ctp-actions-cell">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($clientes)) : ?>
                        <?php foreach ($clientes as $cliente) : ?>
                            <?php
                            $cliente_id = (int) $cliente->id;
                            ?>
                            <tr>
                                <td data-label="Nombre"><?php echo esc_html($cliente->nombre); ?></td>
                                <td data-label="RUC"><?php echo esc_html($cliente->ruc); ?></td>
                                <td data-label="Teléfono"><?php echo esc_html($cliente->telefono); ?></td>
                                <td data-label="Email"><?php echo esc_html($cliente->email); ?></td>
                                <td class="ctp-table-text" data-label="Notas"><?php echo esc_html($cliente->notas); ?></td>
                                <td class="ctp-actions-cell" data-label="Acciones">
                                    <div class="ctp-actions">
                                        <?php
                                        $historial_url = add_query_arg('ctp_cliente_id', $cliente_id, $current_url);
                                        if (!empty($tab)) {
                                            $historial_url = add_query_arg('ctp_tab', $tab, $historial_url);
                                        }
                                        ?>
                                        <a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($historial_url); ?>">Ver historial</a>
                                        <details class="ctp-details">
                                            <summary class="ctp-button ctp-button-secondary">Editar</summary>
                                            <div class="ctp-details-panel">
                                                <form method="post" class="ctp-inline-form ctp-form-grid">
                                                    <?php wp_nonce_field('ctp_cliente_edit', 'ctp_cliente_nonce'); ?>
                                                    <input type="hidden" name="ctp_cliente_action" value="edit">
                                                    <input type="hidden" name="cliente_id" value="<?php echo esc_attr($cliente_id); ?>">
                                                    <div class="ctp-field">
                                                        <label for="ctp-cliente-nombre-<?php echo esc_attr($cliente_id); ?>">Nombre</label>
                                                        <input type="text" id="ctp-cliente-nombre-<?php echo esc_attr($cliente_id); ?>" name="nombre" required value="<?php echo esc_attr($cliente->nombre); ?>" <?php disabled(!$can_manage); ?>>
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-cliente-ruc-<?php echo esc_attr($cliente_id); ?>">RUC</label>
                                                        <input type="text" id="ctp-cliente-ruc-<?php echo esc_attr($cliente_id); ?>" name="ruc" value="<?php echo esc_attr($cliente->ruc); ?>" <?php disabled(!$can_manage); ?>>
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-cliente-telefono-<?php echo esc_attr($cliente_id); ?>">Teléfono</label>
                                                        <input type="text" id="ctp-cliente-telefono-<?php echo esc_attr($cliente_id); ?>" name="telefono" value="<?php echo esc_attr($cliente->telefono); ?>" <?php disabled(!$can_manage); ?>>
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-cliente-email-<?php echo esc_attr($cliente_id); ?>">Email</label>
                                                        <input type="email" id="ctp-cliente-email-<?php echo esc_attr($cliente_id); ?>" name="email" value="<?php echo esc_attr($cliente->email); ?>" <?php disabled(!$can_manage); ?>>
                                                    </div>
                                                    <div class="ctp-field ctp-field-full">
                                                        <label for="ctp-cliente-notas-<?php echo esc_attr($cliente_id); ?>">Notas</label>
                                                        <textarea id="ctp-cliente-notas-<?php echo esc_attr($cliente_id); ?>" name="notas" rows="2" <?php disabled(!$can_manage); ?>><?php echo esc_textarea($cliente->notas); ?></textarea>
                                                    </div>
                                                    <button type="submit" class="ctp-button ctp-field-full" <?php disabled(!$can_manage); ?>>Guardar</button>
                                                </form>
                                            </div>
                                        </details>
                                        <form method="post" class="ctp-inline-form">
                                            <?php wp_nonce_field('ctp_cliente_delete', 'ctp_cliente_nonce'); ?>
                                            <input type="hidden" name="ctp_cliente_action" value="delete">
                                            <input type="hidden" name="cliente_id" value="<?php echo esc_attr($cliente_id); ?>">
                                            <button type="submit" class="ctp-button ctp-button-danger" onclick="return confirm('¿Seguro que deseas eliminar?')" <?php disabled(!$can_manage); ?>>Eliminar</button>
                                        </form>
                                    </div>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else : ?>
                        <tr>
                            <td colspan="6">No hay clientes registrados.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
        <?php
        $table_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Clientes registrados',
            'Gestiona la base de clientes para reutilizarlos en órdenes.',
            $table_html
        );
        ?>
    </div>
    <?php
    $html = ob_get_clean();
    if (!empty($GLOBALS['ctp_in_dashboard'])) {
        return $html;
    }
    return ctp_ordenes_wrap($html, 'ctp-shell-page');
}
add_shortcode('ctp_clientes', 'ctp_clientes_shortcode');

/**
 * Shortcode: gestión de proveedores.
 */
function ctp_proveedores_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    if (!empty($_POST['ctp_proveedor_action'])) {
        $action = sanitize_text_field(wp_unslash($_POST['ctp_proveedor_action']));

        if ($action === 'add') {
            if (!isset($_POST['ctp_proveedor_nonce']) || !check_admin_referer('ctp_proveedor_add', 'ctp_proveedor_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para agregar proveedor.';
            } else {
                $nombre = sanitize_text_field(wp_unslash($_POST['nombre'] ?? ''));
                $ruc = sanitize_text_field(wp_unslash($_POST['ruc'] ?? ''));
                $telefono = sanitize_text_field(wp_unslash($_POST['telefono'] ?? ''));
                $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
                $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

                if (empty($nombre)) {
                    $mensajes['error'][] = 'El nombre del proveedor es obligatorio.';
                } else {
                    $now = current_time('mysql');
                    $inserted = $wpdb->insert(
                        $table_proveedores,
                        array(
                            'nombre' => $nombre,
                            'ruc' => $ruc,
                            'telefono' => $telefono,
                            'email' => $email,
                            'notas' => $notas,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%s', '%s', '%s', '%s', '%s', '%s', '%s')
                    );

                    if ($inserted) {
                        $mensajes['success'][] = 'Proveedor agregado correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo guardar el proveedor.';
                    }
                }
            }
        } elseif ($action === 'edit') {
            if (!isset($_POST['ctp_proveedor_nonce']) || !check_admin_referer('ctp_proveedor_edit', 'ctp_proveedor_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para editar proveedor.';
            } else {
                $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                $nombre = sanitize_text_field(wp_unslash($_POST['nombre'] ?? ''));
                $ruc = sanitize_text_field(wp_unslash($_POST['ruc'] ?? ''));
                $telefono = sanitize_text_field(wp_unslash($_POST['telefono'] ?? ''));
                $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
                $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

                if ($proveedor_id <= 0 || empty($nombre)) {
                    $mensajes['error'][] = 'Datos inválidos para actualizar proveedor.';
                } else {
                    $actualizado = $wpdb->update(
                        $table_proveedores,
                        array(
                            'nombre' => $nombre,
                            'ruc' => $ruc,
                            'telefono' => $telefono,
                            'email' => $email,
                            'notas' => $notas,
                            'updated_at' => current_time('mysql'),
                        ),
                        array('id' => $proveedor_id),
                        array('%s', '%s', '%s', '%s', '%s', '%s'),
                        array('%d')
                    );

                    if ($actualizado !== false) {
                        $mensajes['success'][] = 'Proveedor actualizado correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo actualizar el proveedor.';
                    }
                }
            }
        } elseif ($action === 'delete') {
            if (!isset($_POST['ctp_proveedor_nonce']) || !check_admin_referer('ctp_proveedor_delete', 'ctp_proveedor_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para eliminar proveedor.';
            } else {
                $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                if ($proveedor_id <= 0) {
                    $mensajes['error'][] = 'Proveedor inválido.';
                } else {
                    $tiene_facturas = (int) $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT COUNT(*) FROM {$table_facturas} WHERE proveedor_id = %d",
                            $proveedor_id
                        )
                    );

                    if ($tiene_facturas > 0) {
                        $mensajes['error'][] = 'No se puede eliminar el proveedor porque tiene facturas asociadas.';
                    } else {
                        $deleted = $wpdb->delete($table_proveedores, array('id' => $proveedor_id), array('%d'));
                        if ($deleted) {
                            $mensajes['success'][] = 'Proveedor eliminado correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo eliminar el proveedor.';
                        }
                    }
                }
            }
        }
    }

    $proveedores = $wpdb->get_results(
        "SELECT * FROM {$table_proveedores} ORDER BY created_at DESC, id DESC LIMIT 100"
    );

    ob_start();
    ?>
    <?php ctp_ordenes_render_alerts($mensajes); ?>
    <div class="ctp-stack">
        <?php
        ob_start();
        ?>
        <form method="post" class="ctp-form ctp-form-grid">
            <?php wp_nonce_field('ctp_proveedor_add', 'ctp_proveedor_nonce'); ?>
            <input type="hidden" name="ctp_proveedor_action" value="add">

            <div class="ctp-field">
                <label for="ctp-proveedor-nombre">Nombre</label>
                <input type="text" id="ctp-proveedor-nombre" name="nombre" required>
            </div>

            <div class="ctp-field">
                <label for="ctp-proveedor-ruc">RUC</label>
                <input type="text" id="ctp-proveedor-ruc" name="ruc">
            </div>

            <div class="ctp-field">
                <label for="ctp-proveedor-telefono">Teléfono</label>
                <input type="text" id="ctp-proveedor-telefono" name="telefono">
            </div>

            <div class="ctp-field">
                <label for="ctp-proveedor-email">Email</label>
                <input type="email" id="ctp-proveedor-email" name="email">
            </div>

            <div class="ctp-field ctp-field-full">
                <label for="ctp-proveedor-notas">Notas</label>
                <textarea id="ctp-proveedor-notas" name="notas" rows="3"></textarea>
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button">Agregar proveedor</button>
            </div>
        </form>
        <?php
        $form_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Nuevo proveedor',
            'Agrega un proveedor para asociarlo a facturas y pagos.',
            $form_html,
            'ctp-panel-form'
        );

        ob_start();
        ?>
        <div class="ctp-table-wrap">
            <table class="ctp-table">
                <thead>
                    <tr>
                        <th>Nombre</th>
                        <th>RUC</th>
                        <th>Teléfono</th>
                        <th>Email</th>
                        <th class="ctp-table-text">Notas</th>
                        <th class="ctp-actions-cell">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($proveedores)) : ?>
                        <?php foreach ($proveedores as $proveedor) : ?>
                            <?php
                            $proveedor_id = (int) $proveedor->id;
                            ?>
                            <tr>
                                <td data-label="Nombre"><?php echo esc_html($proveedor->nombre); ?></td>
                                <td data-label="RUC"><?php echo esc_html($proveedor->ruc); ?></td>
                                <td data-label="Teléfono"><?php echo esc_html($proveedor->telefono); ?></td>
                                <td data-label="Email"><?php echo esc_html($proveedor->email); ?></td>
                                <td class="ctp-table-text" data-label="Notas"><?php echo esc_html($proveedor->notas); ?></td>
                                <td class="ctp-actions-cell" data-label="Acciones">
                                    <div class="ctp-actions">
                                        <details class="ctp-details">
                                            <summary class="ctp-button ctp-button-secondary">Editar</summary>
                                            <div class="ctp-details-panel">
                                                <form method="post" class="ctp-inline-form ctp-form-grid">
                                                    <?php wp_nonce_field('ctp_proveedor_edit', 'ctp_proveedor_nonce'); ?>
                                                    <input type="hidden" name="ctp_proveedor_action" value="edit">
                                                    <input type="hidden" name="proveedor_id" value="<?php echo esc_attr($proveedor_id); ?>">
                                                    <div class="ctp-field">
                                                        <label for="ctp-proveedor-nombre-<?php echo esc_attr($proveedor_id); ?>">Nombre</label>
                                                        <input type="text" id="ctp-proveedor-nombre-<?php echo esc_attr($proveedor_id); ?>" name="nombre" required value="<?php echo esc_attr($proveedor->nombre); ?>">
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-proveedor-ruc-<?php echo esc_attr($proveedor_id); ?>">RUC</label>
                                                        <input type="text" id="ctp-proveedor-ruc-<?php echo esc_attr($proveedor_id); ?>" name="ruc" value="<?php echo esc_attr($proveedor->ruc); ?>">
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-proveedor-telefono-<?php echo esc_attr($proveedor_id); ?>">Teléfono</label>
                                                        <input type="text" id="ctp-proveedor-telefono-<?php echo esc_attr($proveedor_id); ?>" name="telefono" value="<?php echo esc_attr($proveedor->telefono); ?>">
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-proveedor-email-<?php echo esc_attr($proveedor_id); ?>">Email</label>
                                                        <input type="email" id="ctp-proveedor-email-<?php echo esc_attr($proveedor_id); ?>" name="email" value="<?php echo esc_attr($proveedor->email); ?>">
                                                    </div>
                                                    <div class="ctp-field ctp-field-full">
                                                        <label for="ctp-proveedor-notas-<?php echo esc_attr($proveedor_id); ?>">Notas</label>
                                                        <textarea id="ctp-proveedor-notas-<?php echo esc_attr($proveedor_id); ?>" name="notas" rows="2"><?php echo esc_textarea($proveedor->notas); ?></textarea>
                                                    </div>
                                                    <button type="submit" class="ctp-button ctp-field-full">Guardar</button>
                                                </form>
                                            </div>
                                        </details>
                                        <form method="post" class="ctp-inline-form">
                                            <?php wp_nonce_field('ctp_proveedor_delete', 'ctp_proveedor_nonce'); ?>
                                            <input type="hidden" name="ctp_proveedor_action" value="delete">
                                            <input type="hidden" name="proveedor_id" value="<?php echo esc_attr($proveedor_id); ?>">
                                            <button type="submit" class="ctp-button ctp-button-danger" onclick="return confirm('¿Seguro que deseas eliminar?')">Eliminar</button>
                                        </form>
                                    </div>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else : ?>
                        <tr>
                            <td colspan="6">No hay proveedores registrados.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
        <?php
        $table_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Proveedores registrados',
            'Gestiona los datos principales de cada proveedor.',
            $table_html
        );
        ?>
    </div>
    <?php
    $html = ob_get_clean();
    if (!empty($GLOBALS['ctp_in_dashboard'])) {
        return $html;
    }
    return ctp_ordenes_wrap($html, 'ctp-shell-page');
}
add_shortcode('ctp_proveedores', 'ctp_proveedores_shortcode');

/**
 * Shortcode: cuentas por pagar de proveedores.
 */
function ctp_facturas_proveedor_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    if (!empty($_POST['ctp_factura_action'])) {
        $action = sanitize_text_field(wp_unslash($_POST['ctp_factura_action']));

        if ($action === 'add_factura') {
            if (!isset($_POST['ctp_factura_nonce']) || !check_admin_referer('ctp_factura_add', 'ctp_factura_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para agregar factura.';
            } else {
                $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                $fecha_factura = sanitize_text_field(wp_unslash($_POST['fecha_factura'] ?? ''));
                $nro_factura = sanitize_text_field(wp_unslash($_POST['nro_factura'] ?? ''));
                $concepto = sanitize_text_field(wp_unslash($_POST['concepto'] ?? ''));
                $monto_total = floatval($_POST['monto_total'] ?? 0);
                $vencimiento = sanitize_text_field(wp_unslash($_POST['vencimiento'] ?? ''));

                if ($proveedor_id <= 0) {
                    $mensajes['error'][] = 'Selecciona un proveedor válido.';
                }
                if (empty($fecha_factura)) {
                    $mensajes['error'][] = 'La fecha de factura es obligatoria.';
                }
                if (empty($nro_factura)) {
                    $mensajes['error'][] = 'El número de factura es obligatorio.';
                }
                if ($monto_total <= 0) {
                    $mensajes['error'][] = 'El monto total debe ser mayor a 0.';
                }

                $proveedor_existe = (int) $wpdb->get_var(
                    $wpdb->prepare("SELECT COUNT(*) FROM {$table_proveedores} WHERE id = %d", $proveedor_id)
                );
                if ($proveedor_id > 0 && $proveedor_existe === 0) {
                    $mensajes['error'][] = 'El proveedor seleccionado no existe.';
                }

                if (empty($mensajes['error'])) {
                    $duplicado = (int) $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT COUNT(*) FROM {$table_facturas} WHERE proveedor_id = %d AND nro_factura = %s",
                            $proveedor_id,
                            $nro_factura
                        )
                    );
                    if ($duplicado > 0) {
                        $mensajes['error'][] = 'Ya existe una factura con ese número para este proveedor.';
                    }
                }

                if (empty($mensajes['error'])) {
                    $now = current_time('mysql');
                    $inserted = $wpdb->insert(
                        $table_facturas,
                        array(
                            'proveedor_id' => $proveedor_id,
                            'fecha_factura' => $fecha_factura,
                            'nro_factura' => $nro_factura,
                            'concepto' => $concepto,
                            'monto_total' => $monto_total,
                            'vencimiento' => $vencimiento ?: null,
                            'estado_pago' => 'pendiente',
                            'monto_pagado' => 0,
                            'saldo' => $monto_total,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%d', '%s', '%s', '%s', '%f', '%s', '%s', '%f', '%f', '%s', '%s')
                    );

                    if ($inserted) {
                        $mensajes['success'][] = 'Factura registrada correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo registrar la factura.';
                    }
                }
            }
        } elseif ($action === 'add_pago') {
            if (!isset($_POST['ctp_factura_nonce']) || !check_admin_referer('ctp_pago_add', 'ctp_factura_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para registrar el pago.';
            } else {
                $factura_id = absint($_POST['factura_id'] ?? 0);
                $fecha_pago = sanitize_text_field(wp_unslash($_POST['fecha_pago'] ?? ''));
                $monto = floatval($_POST['monto'] ?? 0);
                $metodo = sanitize_text_field(wp_unslash($_POST['metodo'] ?? ''));
                $nota = sanitize_text_field(wp_unslash($_POST['nota'] ?? ''));

                if ($factura_id <= 0) {
                    $mensajes['error'][] = 'Factura inválida.';
                }
                if (empty($fecha_pago)) {
                    $fecha_pago = current_time('Y-m-d');
                }
                if ($monto <= 0) {
                    $mensajes['error'][] = 'El monto del pago debe ser mayor a 0.';
                }

                $factura = null;
                if (empty($mensajes['error'])) {
                    $factura = $wpdb->get_row(
                        $wpdb->prepare(
                            "SELECT id, monto_total, monto_pagado FROM {$table_facturas} WHERE id = %d",
                            $factura_id
                        )
                    );
                    if (!$factura) {
                        $mensajes['error'][] = 'No se encontró la factura seleccionada.';
                    }
                }

                if ($factura && empty($mensajes['error'])) {
                    $monto_total = (float) $factura->monto_total;
                    $monto_pagado = (float) $factura->monto_pagado;
                    $saldo = $monto_total - $monto_pagado;

                    if ($saldo <= 0) {
                        $mensajes['error'][] = 'La factura ya está pagada.';
                    } else {
                        if ($monto > $saldo) {
                            $monto = $saldo;
                            $mensajes['warning'][] = 'El monto excedía el saldo. Se registró solo el saldo restante.';
                        }
                        if ($monto <= 0) {
                            $mensajes['error'][] = 'El monto del pago es inválido.';
                        }
                    }
                }

                if (empty($mensajes['error'])) {
                    $inserted = $wpdb->insert(
                        $table_pagos,
                        array(
                            'factura_id' => $factura_id,
                            'fecha_pago' => $fecha_pago,
                            'monto' => $monto,
                            'metodo' => $metodo,
                            'nota' => $nota,
                            'created_at' => current_time('mysql'),
                        ),
                        array('%d', '%s', '%f', '%s', '%s', '%s')
                    );

                    if ($inserted) {
                        ctp_ordenes_recalculate_factura($factura_id);
                        $mensajes['success'][] = 'Pago registrado correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo registrar el pago.';
                    }
                }
            }
        } elseif ($action === 'delete_factura') {
            if (!isset($_POST['ctp_factura_nonce']) || !check_admin_referer('ctp_factura_delete', 'ctp_factura_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para eliminar la factura.';
            } else {
                $factura_id = absint($_POST['factura_id'] ?? 0);
                if ($factura_id <= 0) {
                    $mensajes['error'][] = 'Factura inválida.';
                } else {
                    $tiene_pagos = (int) $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT COUNT(*) FROM {$table_pagos} WHERE factura_id = %d",
                            $factura_id
                        )
                    );
                    if ($tiene_pagos > 0) {
                        $mensajes['error'][] = 'No se puede eliminar la factura porque tiene pagos registrados.';
                    } else {
                        $deleted = $wpdb->delete($table_facturas, array('id' => $factura_id), array('%d'));
                        if ($deleted) {
                            $mensajes['success'][] = 'Factura eliminada correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo eliminar la factura.';
                        }
                    }
                }
            }
        }
    }

    $proveedores = $wpdb->get_results(
        "SELECT id, nombre FROM {$table_proveedores} ORDER BY nombre ASC"
    );

    $estado_filtro = sanitize_text_field(wp_unslash($_GET['estado'] ?? ''));
    $proveedor_filtro = absint($_GET['proveedor_id'] ?? 0);
    $estados_validos = array('pendiente', 'parcial', 'pagado');
    if (!in_array($estado_filtro, $estados_validos, true)) {
        $estado_filtro = '';
    }

    $where = array('1=1');
    $params = array();

    if (!empty($estado_filtro)) {
        $where[] = 'f.estado_pago = %s';
        $params[] = $estado_filtro;
    }
    if ($proveedor_filtro > 0) {
        $where[] = 'f.proveedor_id = %d';
        $params[] = $proveedor_filtro;
    }

    $sql = "SELECT f.*, p.nombre AS proveedor_nombre
            FROM {$table_facturas} f
            LEFT JOIN {$table_proveedores} p ON f.proveedor_id = p.id
            WHERE " . implode(' AND ', $where) . "
            ORDER BY f.fecha_factura DESC, f.id DESC
            LIMIT 100";

    if (!empty($params)) {
        $sql = $wpdb->prepare($sql, $params);
    }

    $facturas = $wpdb->get_results($sql);

    ob_start();
    ?>
    <?php ctp_ordenes_render_alerts($mensajes); ?>
    <div class="ctp-stack">
        <?php
        ob_start();
        ?>
        <form method="post" class="ctp-form ctp-form-grid">
            <?php wp_nonce_field('ctp_factura_add', 'ctp_factura_nonce'); ?>
            <input type="hidden" name="ctp_factura_action" value="add_factura">

            <div class="ctp-field">
                <label for="ctp-factura-proveedor">Proveedor</label>
                <select id="ctp-factura-proveedor" name="proveedor_id" required>
                    <option value="">Selecciona proveedor</option>
                    <?php foreach ($proveedores as $proveedor) : ?>
                        <option value="<?php echo esc_attr($proveedor->id); ?>"><?php echo esc_html($proveedor->nombre); ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-fecha">Fecha de factura</label>
                <input type="date" id="ctp-factura-fecha" name="fecha_factura" required value="<?php echo esc_attr(current_time('Y-m-d')); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-nro">Número de factura</label>
                <input type="text" id="ctp-factura-nro" name="nro_factura" required>
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-concepto">Concepto</label>
                <input type="text" id="ctp-factura-concepto" name="concepto">
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-monto">Monto total</label>
                <input type="number" id="ctp-factura-monto" name="monto_total" step="0.01" min="0.01" required>
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-vencimiento">Vencimiento</label>
                <input type="date" id="ctp-factura-vencimiento" name="vencimiento">
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button">Registrar factura</button>
            </div>
        </form>
        <?php
        $form_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Registrar factura',
            'Carga la factura y controla su estado de pago.',
            $form_html,
            'ctp-panel-form'
        );

        ob_start();
        ?>
        <form method="get" class="ctp-form ctp-form-inline">
            <div class="ctp-field">
                <label for="ctp-filter-estado">Estado</label>
                <select id="ctp-filter-estado" name="estado">
                    <option value="">Todos</option>
                    <?php foreach ($estados_validos as $estado) : ?>
                        <option value="<?php echo esc_attr($estado); ?>" <?php selected($estado_filtro, $estado); ?>>
                            <?php echo esc_html(ucfirst($estado)); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div class="ctp-field">
                <label for="ctp-filter-proveedor">Proveedor</label>
                <select id="ctp-filter-proveedor" name="proveedor_id">
                    <option value="">Todos</option>
                    <?php foreach ($proveedores as $proveedor) : ?>
                        <option value="<?php echo esc_attr($proveedor->id); ?>" <?php selected($proveedor_filtro, $proveedor->id); ?>>
                            <?php echo esc_html($proveedor->nombre); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div class="ctp-field">
                <button type="submit" class="ctp-button ctp-button-secondary">Filtrar</button>
            </div>
        </form>
        <?php
        $filters_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Filtrar facturas',
            'Aplica filtros para encontrar pagos pendientes o parciales.',
            $filters_html,
            'ctp-panel-filters'
        );

        ob_start();
        ?>
        <div class="ctp-table-wrap">
            <table class="ctp-table">
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Proveedor</th>
                        <th>Nro</th>
                        <th>Monto</th>
                        <th>Pagado</th>
                        <th>Saldo</th>
                        <th>Estado</th>
                        <th class="ctp-actions-cell">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($facturas)) : ?>
                        <?php foreach ($facturas as $factura) : ?>
                            <?php
                            $factura_id = (int) $factura->id;
                            $pagos = $wpdb->get_results(
                                $wpdb->prepare(
                                    "SELECT fecha_pago, monto, metodo, nota FROM {$table_pagos}
                                     WHERE factura_id = %d
                                     ORDER BY fecha_pago DESC, id DESC",
                                    $factura_id
                                )
                            );
                            $tiene_pagos = (int) $wpdb->get_var(
                                $wpdb->prepare(
                                    "SELECT COUNT(*) FROM {$table_pagos} WHERE factura_id = %d",
                                    $factura_id
                                )
                            );
                            ?>
                            <tr>
                                <td data-label="Fecha"><?php echo esc_html($factura->fecha_factura); ?></td>
                                <td data-label="Proveedor"><?php echo esc_html($factura->proveedor_nombre ?: ''); ?></td>
                                <td data-label="Nro"><?php echo esc_html($factura->nro_factura); ?></td>
                                <td data-label="Monto"><?php echo esc_html(ctp_ordenes_format_currency($factura->monto_total)); ?></td>
                                <td data-label="Pagado"><?php echo esc_html(ctp_ordenes_format_currency($factura->monto_pagado)); ?></td>
                                <td data-label="Saldo"><?php echo esc_html(ctp_ordenes_format_currency($factura->saldo)); ?></td>
                                <td class="ctp-actions-cell" data-label="Estado">
                                    <span class="ctp-badge ctp-badge-<?php echo esc_attr($factura->estado_pago); ?>">
                                        <?php echo esc_html(ucfirst($factura->estado_pago)); ?>
                                    </span>
                                </td>
                                <td data-label="Acciones">
                                    <div class="ctp-actions">
                                        <details class="ctp-details">
                                            <summary class="ctp-button ctp-button-secondary">Registrar pago</summary>
                                            <div class="ctp-details-panel">
                                                <form method="post" class="ctp-inline-form ctp-form-grid">
                                                    <?php wp_nonce_field('ctp_pago_add', 'ctp_factura_nonce'); ?>
                                                    <input type="hidden" name="ctp_factura_action" value="add_pago">
                                                    <input type="hidden" name="factura_id" value="<?php echo esc_attr($factura_id); ?>">
                                                    <div class="ctp-field">
                                                        <label for="ctp-pago-fecha-<?php echo esc_attr($factura_id); ?>">Fecha de pago</label>
                                                        <input type="date" id="ctp-pago-fecha-<?php echo esc_attr($factura_id); ?>" name="fecha_pago" value="<?php echo esc_attr(current_time('Y-m-d')); ?>">
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-pago-monto-<?php echo esc_attr($factura_id); ?>">Monto</label>
                                                        <input type="number" id="ctp-pago-monto-<?php echo esc_attr($factura_id); ?>" name="monto" step="0.01" min="0.01" required>
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-pago-metodo-<?php echo esc_attr($factura_id); ?>">Método</label>
                                                        <select id="ctp-pago-metodo-<?php echo esc_attr($factura_id); ?>" name="metodo">
                                                            <option value="">Selecciona</option>
                                                            <option value="efectivo">Efectivo</option>
                                                            <option value="transferencia">Transferencia</option>
                                                            <option value="cheque">Cheque</option>
                                                            <option value="otro">Otro</option>
                                                        </select>
                                                    </div>
                                                    <div class="ctp-field">
                                                        <label for="ctp-pago-nota-<?php echo esc_attr($factura_id); ?>">Nota</label>
                                                        <input type="text" id="ctp-pago-nota-<?php echo esc_attr($factura_id); ?>" name="nota">
                                                    </div>
                                                    <button type="submit" class="ctp-button ctp-field-full">Guardar pago</button>
                                                </form>
                                            </div>
                                        </details>
                                        <details class="ctp-details">
                                            <summary class="ctp-button ctp-button-secondary">Ver pagos</summary>
                                            <div class="ctp-details-panel ctp-payments">
                                                <?php if (!empty($pagos)) : ?>
                                                    <table class="ctp-table ctp-table-small">
                                                        <thead>
                                                            <tr>
                                                                <th>Fecha</th>
                                                                <th>Monto</th>
                                                                <th>Método</th>
                                                                <th class="ctp-table-text">Nota</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <?php foreach ($pagos as $pago) : ?>
                                                                <tr>
                                                                    <td data-label="Fecha"><?php echo esc_html($pago->fecha_pago); ?></td>
                                                                    <td data-label="Monto"><?php echo esc_html(ctp_ordenes_format_currency($pago->monto)); ?></td>
                                                                    <td data-label="Método"><?php echo esc_html($pago->metodo); ?></td>
                                                                    <td class="ctp-table-text" data-label="Nota"><?php echo esc_html($pago->nota); ?></td>
                                                                </tr>
                                                            <?php endforeach; ?>
                                                        </tbody>
                                                    </table>
                                                <?php else : ?>
                                                    <p>No hay pagos registrados.</p>
                                                <?php endif; ?>
                                            </div>
                                        </details>
                                        <?php if ($tiene_pagos === 0) : ?>
                                            <form method="post" class="ctp-inline-form">
                                                <?php wp_nonce_field('ctp_factura_delete', 'ctp_factura_nonce'); ?>
                                                <input type="hidden" name="ctp_factura_action" value="delete_factura">
                                                <input type="hidden" name="factura_id" value="<?php echo esc_attr($factura_id); ?>">
                                                <button type="submit" class="ctp-button ctp-button-danger" onclick="return confirm('¿Seguro que deseas eliminar?')">Eliminar</button>
                                            </form>
                                        <?php endif; ?>
                                    </div>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else : ?>
                        <tr>
                            <td colspan="8">No hay facturas registradas.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
        <?php
        $table_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Facturas registradas',
            'Seguimiento de saldos y pagos por proveedor.',
            $table_html
        );
        ?>
    </div>
    <?php
    $html = ob_get_clean();
    if (!empty($GLOBALS['ctp_in_dashboard'])) {
        return $html;
    }
    return ctp_ordenes_wrap($html, 'ctp-shell-page');
}
add_shortcode('ctp_facturas_proveedor', 'ctp_facturas_proveedor_shortcode');

function ctp_liquidaciones_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_clientes = $wpdb->prefix . 'ctp_clientes';
    $table_liquidaciones = $wpdb->prefix . 'ctp_liquidaciones_cliente';
    $table_liquidacion_ordenes = $wpdb->prefix . 'ctp_liquidacion_ordenes';
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    $can_manage = ctp_ordenes_user_can_manage();

    $selected_cliente_id = 0;
    $fecha_desde = '';
    $fecha_hasta = '';
    $nota = '';
    $preview_orders = array();
    $preview_total = 0;
    $show_preview = false;
    $created_liquidacion_id = 0;

    if (!empty($_POST['ctp_liquidacion_action'])) {
        if (!$can_manage) {
            $mensajes['error'][] = 'No tienes permisos para gestionar liquidaciones.';
        } else {
            $action = sanitize_text_field(wp_unslash($_POST['ctp_liquidacion_action']));
            $selected_cliente_id = absint($_POST['cliente_id'] ?? 0);
            $fecha_desde = sanitize_text_field(wp_unslash($_POST['fecha_desde'] ?? ''));
            $fecha_hasta = sanitize_text_field(wp_unslash($_POST['fecha_hasta'] ?? ''));
            $nota = sanitize_textarea_field(wp_unslash($_POST['nota'] ?? ''));

            $valid_from = ctp_ordenes_is_valid_date($fecha_desde, 'Y-m-d');
            $valid_to = ctp_ordenes_is_valid_date($fecha_hasta, 'Y-m-d');

            if (!$selected_cliente_id) {
                $mensajes['error'][] = 'Selecciona un cliente para generar la liquidación.';
            }
            if (!$valid_from || !$valid_to) {
                $mensajes['error'][] = 'Selecciona un rango de fechas válido.';
            } elseif (strtotime($fecha_desde) > strtotime($fecha_hasta)) {
                $mensajes['error'][] = 'La fecha desde no puede ser mayor que la fecha hasta.';
            }

            if (empty($mensajes['error'])) {
                if ($action === 'buscar') {
                    if (!isset($_POST['ctp_liquidacion_nonce']) || !check_admin_referer('ctp_liquidacion_buscar', 'ctp_liquidacion_nonce')) {
                        $mensajes['error'][] = 'No se pudo validar la búsqueda de órdenes.';
                    } else {
                        $preview_orders = ctp_ordenes_get_ordenes_no_liquidadas($selected_cliente_id, $fecha_desde, $fecha_hasta);
                        foreach ($preview_orders as $orden) {
                            $preview_total += (float) $orden->total;
                        }

                        if (empty($preview_orders)) {
                            $mensajes['warning'][] = 'No hay órdenes disponibles para liquidar en este rango.';
                        } else {
                            $show_preview = true;
                        }
                    }
                } elseif ($action === 'crear') {
                    if (!isset($_POST['ctp_liquidacion_nonce']) || !check_admin_referer('ctp_liquidacion_crear', 'ctp_liquidacion_nonce')) {
                        $mensajes['error'][] = 'No se pudo validar la solicitud de liquidación.';
                    } else {
                        $preview_orders = ctp_ordenes_get_ordenes_no_liquidadas($selected_cliente_id, $fecha_desde, $fecha_hasta);
                        foreach ($preview_orders as $orden) {
                            $preview_total += (float) $orden->total;
                        }

                        if (empty($preview_orders)) {
                            $mensajes['warning'][] = 'No se encontraron órdenes disponibles para crear la liquidación.';
                        } else {
                            $now = current_time('mysql');
                            $inserted = $wpdb->insert(
                                $table_liquidaciones,
                                array(
                                    'cliente_id' => $selected_cliente_id,
                                    'desde' => $fecha_desde,
                                    'hasta' => $fecha_hasta,
                                    'total' => $preview_total,
                                    'created_at' => $now,
                                    'estado' => 'generada',
                                    'nota' => $nota,
                                ),
                                array('%d', '%s', '%s', '%f', '%s', '%s', '%s')
                            );

                            if ($inserted) {
                                $liquidacion_id = (int) $wpdb->insert_id;
                                $fallos = 0;

                                foreach ($preview_orders as $orden) {
                                    $relacion = $wpdb->insert(
                                        $table_liquidacion_ordenes,
                                        array(
                                            'liquidacion_id' => $liquidacion_id,
                                            'orden_id' => $orden->id,
                                        ),
                                        array('%d', '%d')
                                    );
                                    if (!$relacion) {
                                        $fallos++;
                                    }
                                }

                                if ($fallos > 0) {
                                    $mensajes['warning'][] = 'La liquidación se creó, pero algunas órdenes no pudieron asociarse.';
                                }

                                $created_liquidacion_id = $liquidacion_id;
                                $show_preview = false;
                                $preview_orders = array();
                                $preview_total = 0;
                            } else {
                                $mensajes['error'][] = 'No se pudo crear la liquidación. Intenta nuevamente.';
                            }
                        }
                    }
                }
            }
        }
    }

    $clientes = ctp_ordenes_get_clientes_list();
    $tab = '';
    if (isset($_GET['ctp_tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['ctp_tab']));
    } elseif (isset($_GET['tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['tab']));
    }

    $liquidacion_id = isset($_GET['ctp_liquidacion_id']) ? absint($_GET['ctp_liquidacion_id']) : 0;
    if ($liquidacion_id > 0) {
        $liquidacion = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT f.*, COALESCE(c.nombre, '') AS cliente_nombre
                 FROM {$table_liquidaciones} f
                 LEFT JOIN {$table_clientes} c ON f.cliente_id = c.id
                 WHERE f.id = %d",
                $liquidacion_id
            )
        );

        $ordenes_liquidacion = array();
        if ($liquidacion) {
            $ordenes_liquidacion = $wpdb->get_results(
                $wpdb->prepare(
                    "SELECT o.fecha, o.numero_orden, o.descripcion, o.cantidad_chapas,
                            o.medida_chapa, o.precio_unitario, o.total
                     FROM {$table_ordenes} o
                     INNER JOIN {$table_liquidacion_ordenes} lo ON lo.orden_id = o.id
                     WHERE lo.liquidacion_id = %d
                     ORDER BY o.fecha ASC, o.id ASC",
                    $liquidacion_id
                )
            );
        }

        $back_url = remove_query_arg(array('ctp_liquidacion_id'));
        if (!empty($tab)) {
            $back_url = add_query_arg('ctp_tab', $tab, $back_url);
        }

        ob_start();
        ctp_ordenes_render_alerts($mensajes);

        if (!$liquidacion) {
            echo '<div class="ctp-alert ctp-alert-warning">La liquidación solicitada no existe.</div>';
        } else {
            ?>
            <div class="ctp-panel">
                <div class="ctp-panel-header">
                    <h3 class="ctp-panel-title">Detalle de liquidación</h3>
                    <p class="ctp-panel-subtitle">Cliente: <?php echo esc_html($liquidacion->cliente_nombre ?: 'Sin cliente'); ?></p>
                </div>
                <div class="ctp-panel-body">
                    <div class="ctp-kpi-grid">
                        <div class="ctp-kpi-card">
                            <div class="ctp-kpi-title">Período</div>
                            <div class="ctp-kpi-value">
                                <?php echo esc_html(date_i18n('d/m/Y', strtotime($liquidacion->desde))); ?>
                                -
                                <?php echo esc_html(date_i18n('d/m/Y', strtotime($liquidacion->hasta))); ?>
                            </div>
                            <div class="ctp-kpi-meta">Liquidación #<?php echo esc_html($liquidacion->id); ?></div>
                        </div>
                        <div class="ctp-kpi-card">
                            <div class="ctp-kpi-title">Total</div>
                            <div class="ctp-kpi-value"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($liquidacion->total)); ?></div>
                            <div class="ctp-kpi-meta">Creada: <?php echo esc_html(date_i18n('d/m/Y', strtotime($liquidacion->created_at))); ?></div>
                        </div>
                        <div class="ctp-kpi-card">
                            <div class="ctp-kpi-title">Estado</div>
                            <div class="ctp-kpi-value"><?php echo esc_html(ucfirst($liquidacion->estado)); ?></div>
                            <div class="ctp-kpi-meta"><?php echo esc_html($liquidacion->nota ?: 'Sin nota'); ?></div>
                        </div>
                    </div>
                    <div class="ctp-table-wrap">
                        <table class="ctp-table">
                            <thead>
                                <tr>
                                    <th>Fecha</th>
                                    <th>Nº Orden</th>
                                    <th>Descripción</th>
                                    <th>Medida</th>
                                    <th>Cantidad</th>
                                    <th>Unitario</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php if (!empty($ordenes_liquidacion)) : ?>
                                    <?php foreach ($ordenes_liquidacion as $orden) : ?>
                                        <tr>
                                            <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                                            <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                                            <td data-label="Descripción"><?php echo esc_html($orden->descripcion); ?></td>
                                            <td data-label="Medida"><?php echo esc_html($orden->medida_chapa); ?></td>
                                            <td data-label="Cantidad"><?php echo esc_html($orden->cantidad_chapas); ?></td>
                                            <td data-label="Unitario"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->precio_unitario)); ?></td>
                                            <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                                        </tr>
                                    <?php endforeach; ?>
                                <?php else : ?>
                                    <tr>
                                        <td colspan="7">No hay órdenes asociadas a esta liquidación.</td>
                                    </tr>
                                <?php endif; ?>
                            </tbody>
                        </table>
                    </div>
                    <div class="ctp-actions">
                        <a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($back_url); ?>">Volver</a>
                    </div>
                </div>
            </div>
            <?php
        }

        $html = ob_get_clean();
        if (!empty($GLOBALS['ctp_in_dashboard'])) {
            return $html;
        }
        return ctp_ordenes_wrap($html, 'ctp-shell-page');
    }

    $list_cliente_id = isset($_GET['ctp_liquidacion_cliente']) ? absint($_GET['ctp_liquidacion_cliente']) : 0;
    $list_where = '';
    $list_params = array();
    if ($list_cliente_id > 0) {
        $list_where = 'WHERE f.cliente_id = %d';
        $list_params[] = $list_cliente_id;
    }

    $liquidaciones = $wpdb->get_results(
        $list_where
            ? $wpdb->prepare(
                "SELECT f.id, f.created_at, f.desde, f.hasta, f.total, f.estado,
                        COALESCE(c.nombre, '') AS cliente_nombre
                 FROM {$table_liquidaciones} f
                 LEFT JOIN {$table_clientes} c ON f.cliente_id = c.id
                 {$list_where}
                 ORDER BY f.created_at DESC, f.id DESC",
                $list_params
            )
            : "SELECT f.id, f.created_at, f.desde, f.hasta, f.total, f.estado,
                      COALESCE(c.nombre, '') AS cliente_nombre
               FROM {$table_liquidaciones} f
               LEFT JOIN {$table_clientes} c ON f.cliente_id = c.id
               ORDER BY f.created_at DESC, f.id DESC"
    );

    $detail_url_base = remove_query_arg(array('ctp_liquidacion_id'));
    if (!empty($tab)) {
        $detail_url_base = add_query_arg('ctp_tab', $tab, $detail_url_base);
    }

    ob_start();
    ctp_ordenes_render_alerts($mensajes);

    if ($created_liquidacion_id > 0) {
        $liquidacion_url = add_query_arg('ctp_liquidacion_id', $created_liquidacion_id, $detail_url_base);
        echo '<div class="ctp-alert ctp-alert-success">Liquidación creada correctamente. <a href="' . esc_url($liquidacion_url) . '">Ver detalle</a></div>';
    }
    ?>
    <div class="ctp-panel">
        <div class="ctp-panel-header">
            <h3 class="ctp-panel-title">Liquidaciones de clientes</h3>
            <p class="ctp-panel-subtitle">Selecciona cliente y rango de fechas para buscar órdenes no liquidadas.</p>
        </div>
        <div class="ctp-panel-body">
            <form method="post" class="ctp-form ctp-form-inline">
                <?php wp_nonce_field('ctp_liquidacion_buscar', 'ctp_liquidacion_nonce'); ?>
                <input type="hidden" name="ctp_liquidacion_action" value="buscar">
                <div class="ctp-field">
                    <label for="ctp-liquidacion-cliente">Cliente</label>
                    <select id="ctp-liquidacion-cliente" name="cliente_id" required>
                        <option value="0">Seleccionar cliente</option>
                        <?php foreach ($clientes as $cliente_item) : ?>
                            <option value="<?php echo esc_attr($cliente_item->id); ?>" <?php selected($selected_cliente_id, (int) $cliente_item->id); ?>>
                                <?php echo esc_html($cliente_item->nombre); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="ctp-field">
                    <label for="ctp-liquidacion-desde">Fecha desde</label>
                    <input type="date" id="ctp-liquidacion-desde" name="fecha_desde" value="<?php echo esc_attr($fecha_desde); ?>">
                </div>
                <div class="ctp-field">
                    <label for="ctp-liquidacion-hasta">Fecha hasta</label>
                    <input type="date" id="ctp-liquidacion-hasta" name="fecha_hasta" value="<?php echo esc_attr($fecha_hasta); ?>">
                </div>
                <div class="ctp-field">
                    <button type="submit" class="ctp-button">Buscar órdenes no liquidadas</button>
                </div>
            </form>
            <?php if ($show_preview) : ?>
                <div class="ctp-table-wrap">
                    <table class="ctp-table">
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>Nº Orden</th>
                                <th>Descripción</th>
                                <th>Medida</th>
                                <th>Cantidad</th>
                                <th>Unitario</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($preview_orders as $orden) : ?>
                                <tr>
                                    <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                                    <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                                    <td data-label="Descripción"><?php echo esc_html($orden->descripcion); ?></td>
                                    <td data-label="Medida"><?php echo esc_html($orden->medida_chapa); ?></td>
                                    <td data-label="Cantidad"><?php echo esc_html($orden->cantidad_chapas); ?></td>
                                    <td data-label="Unitario"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->precio_unitario)); ?></td>
                                    <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                <form method="post" class="ctp-form ctp-form-inline">
                    <?php wp_nonce_field('ctp_liquidacion_crear', 'ctp_liquidacion_nonce'); ?>
                    <input type="hidden" name="ctp_liquidacion_action" value="crear">
                    <input type="hidden" name="cliente_id" value="<?php echo esc_attr($selected_cliente_id); ?>">
                    <input type="hidden" name="fecha_desde" value="<?php echo esc_attr($fecha_desde); ?>">
                    <input type="hidden" name="fecha_hasta" value="<?php echo esc_attr($fecha_hasta); ?>">
                    <div class="ctp-field ctp-field-full">
                        <label for="ctp-liquidacion-nota">Nota (opcional)</label>
                        <textarea id="ctp-liquidacion-nota" name="nota" rows="2"><?php echo esc_textarea($nota); ?></textarea>
                    </div>
                    <div class="ctp-field">
                        <strong>Total:</strong> <?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($preview_total)); ?>
                    </div>
                    <div class="ctp-field">
                        <button type="submit" class="ctp-button">Generar liquidación</button>
                    </div>
                </form>
            <?php endif; ?>
        </div>
    </div>
    <?php

    $list_base_url = remove_query_arg(array('ctp_liquidacion_cliente', 'ctp_liquidacion_id'));
    if (!empty($tab)) {
        $list_base_url = add_query_arg('ctp_tab', $tab, $list_base_url);
    }
    ?>
    <div class="ctp-panel">
        <div class="ctp-panel-header">
            <h3 class="ctp-panel-title">Liquidaciones emitidas</h3>
            <p class="ctp-panel-subtitle">Listado de liquidaciones por cliente.</p>
        </div>
        <div class="ctp-panel-body">
            <form method="get" class="ctp-form ctp-form-inline">
                <?php if (!empty($tab)) : ?>
                    <input type="hidden" name="ctp_tab" value="<?php echo esc_attr($tab); ?>">
                <?php endif; ?>
                <div class="ctp-field">
                    <label for="ctp-liquidacion-cliente-filter">Cliente</label>
                    <select id="ctp-liquidacion-cliente-filter" name="ctp_liquidacion_cliente">
                        <option value="0">Todos los clientes</option>
                        <?php foreach ($clientes as $cliente_item) : ?>
                            <option value="<?php echo esc_attr($cliente_item->id); ?>" <?php selected($list_cliente_id, (int) $cliente_item->id); ?>>
                                <?php echo esc_html($cliente_item->nombre); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="ctp-field">
                    <button type="submit" class="ctp-button ctp-button-secondary">Filtrar</button>
                    <a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($list_base_url); ?>">Limpiar</a>
                </div>
            </form>
            <div class="ctp-table-wrap">
                <table class="ctp-table">
                    <thead>
                        <tr>
                            <th>Fecha creación</th>
                            <th>Cliente</th>
                            <th>Período</th>
                            <th>Total</th>
                            <th>Estado</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (!empty($liquidaciones)) : ?>
                            <?php foreach ($liquidaciones as $liquidacion) : ?>
                                <?php
                                $detalle_url = add_query_arg('ctp_liquidacion_id', $liquidacion->id, $detail_url_base);
                                ?>
                                <tr>
                                    <td data-label="Fecha creación"><?php echo esc_html(date_i18n('d/m/Y', strtotime($liquidacion->created_at))); ?></td>
                                    <td data-label="Cliente"><?php echo esc_html($liquidacion->cliente_nombre ?: 'Sin cliente'); ?></td>
                                    <td data-label="Período">
                                        <?php echo esc_html(date_i18n('d/m/Y', strtotime($liquidacion->desde))); ?>
                                        -
                                        <?php echo esc_html(date_i18n('d/m/Y', strtotime($liquidacion->hasta))); ?>
                                    </td>
                                    <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($liquidacion->total)); ?></td>
                                    <td data-label="Estado"><?php echo esc_html(ucfirst($liquidacion->estado)); ?></td>
                                    <td><a class="ctp-button ctp-button-secondary" href="<?php echo esc_url($detalle_url); ?>">Ver detalle</a></td>
                                </tr>
                            <?php endforeach; ?>
                        <?php else : ?>
                            <tr>
                                <td colspan="6">No hay liquidaciones emitidas.</td>
                            </tr>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <?php
    $html = ob_get_clean();
    if (!empty($GLOBALS['ctp_in_dashboard'])) {
        return $html;
    }
    return ctp_ordenes_wrap($html, 'ctp-shell-page');
}
add_shortcode('ctp_liquidaciones', 'ctp_liquidaciones_shortcode');

function ctp_dashboard_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    if (isset($_GET['ctp_tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['ctp_tab']));
    } elseif (isset($_GET['tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['tab']));
    } else {
        $tab = 'ordenes';
    }

    if (!in_array($tab, array('ordenes', 'proveedores', 'facturas', 'liquidaciones', 'clientes'), true)) {
        $tab = 'ordenes';
    }

    global $wpdb;
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $recent_date = date('Y-m-d', strtotime('-30 days', current_time('timestamp')));

    $ordenes_total = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table_ordenes}");
    $ordenes_recientes = (int) $wpdb->get_var(
        $wpdb->prepare(
            "SELECT COUNT(*) FROM {$table_ordenes} WHERE fecha >= %s",
            $recent_date
        )
    );
    $proveedores_total = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table_proveedores}");
    $facturas_pendientes = (int) $wpdb->get_var(
        "SELECT COUNT(*) FROM {$table_facturas} WHERE estado_pago IN ('pendiente','parcial')"
    );
    $saldo_pendiente = (float) $wpdb->get_var(
        "SELECT COALESCE(SUM(saldo), 0) FROM {$table_facturas} WHERE estado_pago IN ('pendiente','parcial')"
    );
    $saldo_pendiente_formatted = ctp_ordenes_format_currency($saldo_pendiente);

    $base_url = get_permalink();
    $tabs = array(
        'ordenes' => 'Órdenes',
        'clientes' => 'Clientes',
        'proveedores' => 'Proveedores',
        'liquidaciones' => 'Liquidaciones',
        'facturas' => 'Facturas proveedor',
    );

    $GLOBALS['ctp_in_dashboard'] = true;

    ob_start();
    ?>
    <div class="ctp-app ctp-dashboard">
        <div class="ctp-shell">
            <div class="ctp-dashboard-header">
                <div>
                    <h2>Panel CTP</h2>
                    <p class="ctp-dashboard-subtitle">Centro de control para órdenes, proveedores, liquidaciones y facturación.</p>
                </div>
                <div class="ctp-dashboard-actions">
                    <span class="ctp-dashboard-label">Última actualización: <?php echo esc_html(current_time('d/m/Y')); ?></span>
                </div>
            </div>
            <div class="ctp-summary-grid">
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Órdenes</div>
                    <div class="ctp-summary-value"><?php echo esc_html(ctp_ordenes_format_currency($ordenes_total)); ?></div>
                    <div class="ctp-summary-meta">
                        <?php echo esc_html(sprintf('Últimos 30 días: %s', ctp_ordenes_format_currency($ordenes_recientes))); ?>
                    </div>
                </div>
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Proveedores</div>
                    <div class="ctp-summary-value"><?php echo esc_html(ctp_ordenes_format_currency($proveedores_total)); ?></div>
                    <div class="ctp-summary-meta">Total registrados</div>
                </div>
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Facturas pendientes</div>
                    <div class="ctp-summary-value"><?php echo esc_html(ctp_ordenes_format_currency($facturas_pendientes)); ?></div>
                    <div class="ctp-summary-meta">Pendiente o parcial</div>
                </div>
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Saldo pendiente</div>
                    <div class="ctp-summary-value"><?php echo esc_html('Gs. ' . $saldo_pendiente_formatted); ?></div>
                    <div class="ctp-summary-meta">Monto por pagar</div>
                </div>
            </div>
            <div class="ctp-dashboard-nav" role="tablist">
            <?php foreach ($tabs as $key => $label) : ?>
                <?php
                $url = add_query_arg('ctp_tab', $key, $base_url);
                $class = 'ctp-dashboard-button';
                if ($tab === $key) {
                    $class .= ' is-active';
                }
                ?>
                <a class="<?php echo esc_attr($class); ?>" href="<?php echo esc_url($url); ?>" role="tab" aria-selected="<?php echo $tab === $key ? 'true' : 'false'; ?>">
                    <?php echo esc_html($label); ?>
                </a>
            <?php endforeach; ?>
            </div>
            <div class="ctp-dashboard-content">
                <?php if ($tab === 'ordenes') : ?>
                    <div class="ctp-dashboard-grid">
                        <div class="ctp-dashboard-col">
                            <?php echo do_shortcode('[ctp_cargar_orden]'); ?>
                        </div>
                        <div class="ctp-dashboard-col">
                            <?php echo do_shortcode('[ctp_listar_ordenes]'); ?>
                        </div>
                    </div>
                <?php elseif ($tab === 'clientes') : ?>
                    <?php echo do_shortcode('[ctp_clientes]'); ?>
                <?php elseif ($tab === 'proveedores') : ?>
                    <?php echo do_shortcode('[ctp_proveedores]'); ?>
                <?php elseif ($tab === 'liquidaciones') : ?>
                    <?php echo do_shortcode('[ctp_liquidaciones]'); ?>
                <?php else : ?>
                    <?php echo do_shortcode('[ctp_facturas_proveedor]'); ?>
                <?php endif; ?>
            </div>
        </div>
    </div>
    <?php
    $contenido = ob_get_clean();
    unset($GLOBALS['ctp_in_dashboard']);
    return $contenido;
}
add_shortcode('ctp_dashboard', 'ctp_dashboard_shortcode');
