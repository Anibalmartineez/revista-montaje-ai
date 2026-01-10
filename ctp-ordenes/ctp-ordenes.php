<?php
/**
 * Plugin Name: CTP Órdenes
 * Description: MVP para cargar y listar órdenes de CTP mediante shortcodes.
 * Version: 0.6.1
 * Author: Equipo Revista Montaje AI
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

define('CTP_ORDENES_VERSION', '0.6.1');

/**
 * Crea la tabla necesaria al activar el plugin.
 */
function ctp_ordenes_create_tables() {
    global $wpdb;

    $table_name = $wpdb->prefix . 'ctp_ordenes';
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';
    $table_clientes = $wpdb->prefix . 'ctp_clientes';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';
    $table_liquidaciones = $wpdb->prefix . 'ctp_liquidaciones_cliente';
    $table_liquidacion_ordenes = $wpdb->prefix . 'ctp_liquidacion_ordenes';
    $table_deudas = $wpdb->prefix . 'ctp_deudas_empresa';
    $table_deudas_pagos = $wpdb->prefix . 'ctp_deudas_empresa_pagos';
    $charset_collate = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE {$table_name} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        fecha DATE NOT NULL,
        numero_orden VARCHAR(50) NOT NULL,
        cliente VARCHAR(150) NOT NULL,
        cliente_id BIGINT UNSIGNED NULL,
        nombre_trabajo VARCHAR(255) NULL,
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

    $sql_items = "CREATE TABLE {$table_items} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        orden_id BIGINT UNSIGNED NOT NULL,
        medida_chapa VARCHAR(20) NOT NULL,
        cantidad_chapas INT NOT NULL DEFAULT 1,
        precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0,
        total_item DECIMAL(12,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        KEY orden_id (orden_id)
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

    $sql_deudas = "CREATE TABLE {$table_deudas} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        categoria VARCHAR(30) NOT NULL,
        tipo VARCHAR(20) NOT NULL,
        descripcion TEXT NULL,
        proveedor_id BIGINT UNSIGNED NULL,
        monto_total DECIMAL(14,2) NOT NULL DEFAULT 0,
        monto_mensual DECIMAL(14,2) NOT NULL DEFAULT 0,
        cuotas_total INT UNSIGNED NULL,
        fecha_inicio DATE NOT NULL,
        fecha_fin DATE NULL,
        dia_vencimiento TINYINT UNSIGNED NULL,
        estado VARCHAR(20) NOT NULL DEFAULT 'activa',
        source_type VARCHAR(50) NULL,
        source_id BIGINT UNSIGNED NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        KEY proveedor_id (proveedor_id),
        KEY tipo (tipo),
        KEY categoria (categoria),
        KEY estado (estado),
        KEY source_ref (source_type, source_id)
    ) {$charset_collate};";

    $sql_deudas_pagos = "CREATE TABLE {$table_deudas_pagos} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        deuda_id BIGINT UNSIGNED NOT NULL,
        periodo CHAR(7) NOT NULL,
        fecha_pago DATE NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        notas VARCHAR(255) NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        UNIQUE KEY deuda_periodo (deuda_id, periodo),
        KEY deuda_id (deuda_id),
        KEY periodo (periodo)
    ) {$charset_collate};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
    dbDelta($sql_items);
    dbDelta($sql_clientes);
    dbDelta($sql_proveedores);
    dbDelta($sql_facturas);
    dbDelta($sql_pagos);
    dbDelta($sql_liquidaciones);
    dbDelta($sql_liquidacion_ordenes);
    dbDelta($sql_deudas);
    dbDelta($sql_deudas_pagos);
}

function ctp_ordenes_activate() {
    ctp_ordenes_create_tables();
    ctp_ordenes_migrate_items();
    update_option('ctp_ordenes_version', CTP_ORDENES_VERSION);
}
register_activation_hook(__FILE__, 'ctp_ordenes_activate');

function ctp_ordenes_migrate_items() {
    global $wpdb;

    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

    $exists = $wpdb->get_var(
        $wpdb->prepare('SHOW TABLES LIKE %s', $table_items)
    );

    if ($exists !== $table_items) {
        return;
    }

    $wpdb->query(
        "INSERT INTO {$table_items}
            (orden_id, medida_chapa, cantidad_chapas, precio_unitario, total_item, created_at, updated_at)
         SELECT o.id, o.medida_chapa, o.cantidad_chapas, o.precio_unitario, o.total, o.created_at, o.updated_at
         FROM {$table_ordenes} o
         LEFT JOIN {$table_items} i ON i.orden_id = o.id
         WHERE i.id IS NULL"
    );
}

function ctp_ordenes_maybe_upgrade() {
    $version = get_option('ctp_ordenes_version');
    if ($version !== CTP_ORDENES_VERSION) {
        ctp_ordenes_create_tables();
        ctp_ordenes_migrate_items();
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
        'ctp_deudas_empresa',
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

    wp_localize_script(
        'ctp-ordenes-app',
        'ctpOrdenesData',
        array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
        )
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

function ctp_ordenes_format_currency_i18n($value, $decimals = 0) {
    return number_format_i18n((float) $value, $decimals);
}

function ctp_ordenes_get_deudas_periodo($period = '') {
    $default_period = current_time('Y-m');
    $period = $period !== '' ? $period : (isset($_GET['ctp_period']) ? sanitize_text_field(wp_unslash($_GET['ctp_period'])) : '');

    if (!ctp_ordenes_is_valid_date($period, 'Y-m')) {
        $period = $default_period;
    }

    $label = date_i18n('F Y', strtotime($period . '-01'));

    return array(
        'period' => $period,
        'label' => $label,
    );
}

function ctp_ordenes_month_diff($from, $to) {
    if (!ctp_ordenes_is_valid_date($from, 'Y-m') || !ctp_ordenes_is_valid_date($to, 'Y-m')) {
        return null;
    }

    $from_parts = array_map('intval', explode('-', $from));
    $to_parts = array_map('intval', explode('-', $to));

    return ($to_parts[0] - $from_parts[0]) * 12 + ($to_parts[1] - $from_parts[1]);
}

function ctp_ordenes_deuda_aplica_periodo($deuda, $periodo) {
    if (!ctp_ordenes_is_valid_date($periodo, 'Y-m') || empty($deuda->fecha_inicio)) {
        return false;
    }

    $inicio = date('Y-m', strtotime($deuda->fecha_inicio));
    $tipo = $deuda->tipo ?? '';

    if ($tipo === 'mensual') {
        if ($periodo < $inicio) {
            return false;
        }

        if (!empty($deuda->fecha_fin)) {
            $fin = date('Y-m', strtotime($deuda->fecha_fin));
            if ($periodo > $fin) {
                return false;
            }
        }

        return true;
    }

    if ($tipo === 'unico') {
        return $periodo === $inicio;
    }

    if ($tipo === 'cuotas') {
        $cuotas_total = (int) ($deuda->cuotas_total ?? 0);
        if ($cuotas_total <= 0) {
            return false;
        }

        $diff = ctp_ordenes_month_diff($inicio, $periodo);
        return $diff !== null && $diff >= 0 && $diff < $cuotas_total;
    }

    return false;
}

function ctp_ordenes_deuda_get_monto_periodo($deuda, $periodo) {
    if (!ctp_ordenes_deuda_aplica_periodo($deuda, $periodo)) {
        return 0;
    }

    $tipo = $deuda->tipo ?? '';

    if ($tipo === 'unico') {
        return (float) ($deuda->monto_total ?? 0);
    }

    return (float) ($deuda->monto_mensual ?? 0);
}

function ctp_ordenes_format_items_count($count) {
    $formatted = ctp_ordenes_format_currency($count, 0);
    return $count === 1 ? '1 trabajo' : sprintf('%s trabajos', $formatted);
}

function ctp_ordenes_format_job_name($nombre_trabajo) {
    $nombre_trabajo = trim((string) $nombre_trabajo);
    return $nombre_trabajo !== '' ? $nombre_trabajo : '—';
}

function ctp_ordenes_ai_format_text($value) {
    if ($value === null) {
        return '—';
    }

    $value = trim((string) $value);
    return $value !== '' ? $value : '—';
}

function ctp_ordenes_ai_format_currency($value) {
    if ($value === null || $value === '') {
        return '—';
    }

    return 'Gs. ' . ctp_ordenes_format_currency($value);
}

function ctp_ordenes_ai_format_quantity($value) {
    if ($value === null || $value === '') {
        return '—';
    }

    return ctp_ordenes_format_currency($value, 0);
}

function ctp_ordenes_get_items_map_for_ai($ordenes) {
    if (empty($ordenes)) {
        return array();
    }

    $order_ids = array();
    foreach ($ordenes as $orden) {
        if (!empty($orden->id)) {
            $order_ids[] = (int) $orden->id;
        }
    }

    if (empty($order_ids)) {
        return array();
    }

    global $wpdb;
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

    $placeholders = implode(',', array_fill(0, count($order_ids), '%d'));
    $items = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT orden_id, medida_chapa, cantidad_chapas, precio_unitario, total_item
             FROM {$table_items}
             WHERE orden_id IN ({$placeholders})
             ORDER BY id ASC",
            $order_ids
        )
    );

    $items_map = array();
    foreach ($items as $item) {
        $items_map[(int) $item->orden_id][] = $item;
    }

    return $items_map;
}

function ctp_ordenes_build_liquidacion_ai_data($liquidacion, $ordenes, $items_map) {
    $cliente = ctp_ordenes_ai_format_text($liquidacion->cliente_nombre ?? '');
    $periodo_desde = !empty($liquidacion->desde) ? date_i18n('d/m/Y', strtotime($liquidacion->desde)) : '—';
    $periodo_hasta = !empty($liquidacion->hasta) ? date_i18n('d/m/Y', strtotime($liquidacion->hasta)) : '—';
    $total = ctp_ordenes_ai_format_currency($liquidacion->total ?? '');
    $cantidad_ordenes = count($ordenes);

    $ordenes_payload = array();
    foreach ($ordenes as $orden) {
        $orden_id = (int) ($orden->id ?? 0);
        $fecha = !empty($orden->fecha) ? date_i18n('d/m/Y', strtotime($orden->fecha)) : '—';
        $trabajo = ctp_ordenes_format_job_name($orden->nombre_trabajo ?? '');
        $total_orden = ctp_ordenes_ai_format_currency($orden->total ?? '');
        $items = $items_map[$orden_id] ?? array();

        $items_payload = array();
        foreach ($items as $item) {
            $items_payload[] = array(
                'medida' => ctp_ordenes_ai_format_text($item->medida_chapa ?? ''),
                'cantidad' => ctp_ordenes_ai_format_quantity($item->cantidad_chapas ?? ''),
                'unitario' => ctp_ordenes_ai_format_currency($item->precio_unitario ?? ''),
                'total_item' => ctp_ordenes_ai_format_currency($item->total_item ?? ''),
            );
        }

        $ordenes_payload[] = array(
            'fecha' => $fecha,
            'numero_orden' => ctp_ordenes_ai_format_text($orden->numero_orden ?? ''),
            'cliente' => $cliente,
            'nombre_trabajo' => $trabajo,
            'total_ot' => $total_orden,
            'items' => $items_payload,
        );
    }

    return array(
        'liquidacion' => array(
            'cliente' => $cliente,
            'desde' => $periodo_desde,
            'hasta' => $periodo_hasta,
            'total' => $total,
            'cantidad_ordenes' => $cantidad_ordenes,
        ),
        'ordenes' => $ordenes_payload,
    );
}

function ctp_ordenes_get_items_count_map($ordenes) {
    if (empty($ordenes)) {
        return array();
    }

    $order_ids = array();
    foreach ($ordenes as $orden) {
        if (!empty($orden->id)) {
            $order_ids[] = (int) $orden->id;
        }
    }

    if (empty($order_ids)) {
        return array();
    }

    global $wpdb;
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';
    $placeholders = implode(',', array_fill(0, count($order_ids), '%d'));

    $counts = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT orden_id, COUNT(*) AS items_count
             FROM {$table_items}
             WHERE orden_id IN ({$placeholders})
             GROUP BY orden_id",
            $order_ids
        )
    );

    $count_map = array();
    foreach ($counts as $row) {
        $count_map[(int) $row->orden_id] = (int) $row->items_count;
    }

    return $count_map;
}

function ctp_ordenes_build_liquidacion_ai_prompt($liquidacion, $ordenes, $ai_data = null) {
    if ($ai_data === null) {
        $items_map = ctp_ordenes_get_items_map_for_ai($ordenes);
        $ai_data = ctp_ordenes_build_liquidacion_ai_data($liquidacion, $ordenes, $items_map);
    }

    $prompt = "Genera un resumen en TEXTO PLANO con el formato exacto indicado. No uses Markdown ni tablas.\n";
    $prompt .= "Usa SOLO los datos entregados. No inventes datos ni agregues texto fuera del formato. Si falta un dato, usa \"—\".\n";
    $prompt .= "Reglas:\n";
    $prompt .= "- Fecha: dd/mm/yyyy.\n";
    $prompt .= "- Moneda: \"Gs. 603.000\".\n";
    $prompt .= "- Listar TODAS las órdenes.\n";
    $prompt .= "- Si una OT no tiene ítems, incluye una línea de ítems con valores \"—\".\n\n";
    $prompt .= "FORMATO EXACTO:\n";
    $prompt .= "Liquidación: {Cliente}\n";
    $prompt .= "Período: dd/mm/yyyy – dd/mm/yyyy\n";
    $prompt .= "Total: Gs. X\n";
    $prompt .= "Órdenes: N\n\n";
    $prompt .= "Luego por cada OT:\n";
    $prompt .= "- dd/mm/yyyy | OT 123 | Cliente: X | Trabajo: Y | Total: Gs. Z\n";
    $prompt .= "  Ítems:\n";
    $prompt .= "  - Medida: 510x400 | Cant: 1 | Unit: Gs. 20.000 | Total: Gs. 20.000\n\n";
    $prompt .= "Datos estructurados (JSON):\n";
    $prompt .= wp_json_encode($ai_data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

    return $prompt;
}

function ctp_ordenes_get_order_total($orden_id, $fallback_total = 0) {
    global $wpdb;
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

    $sum = $wpdb->get_var(
        $wpdb->prepare(
            "SELECT SUM(total_item) FROM {$table_items} WHERE orden_id = %d",
            $orden_id
        )
    );

    if ($sum === null) {
        return (float) $fallback_total;
    }

    return (float) $sum;
}

function ctp_ordenes_get_items_map($ordenes) {
    if (empty($ordenes)) {
        return array();
    }

    $order_ids = array();
    foreach ($ordenes as $orden) {
        if (!empty($orden->id)) {
            $order_ids[] = (int) $orden->id;
        }
    }

    if (empty($order_ids)) {
        return array();
    }

    global $wpdb;
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

    $placeholders = implode(',', array_fill(0, count($order_ids), '%d'));
    $items = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT orden_id, medida_chapa, cantidad_chapas, precio_unitario, total_item
             FROM {$table_items}
             WHERE orden_id IN ({$placeholders})
             ORDER BY id ASC",
            $order_ids
        )
    );

    $items_map = array();
    foreach ($items as $item) {
        $items_map[(int) $item->orden_id][] = $item;
    }

    foreach ($ordenes as $orden) {
        $orden_id = (int) $orden->id;
        if (empty($items_map[$orden_id])) {
            $items_map[$orden_id] = array(
                (object) array(
                    'medida_chapa' => $orden->medida_chapa ?? '',
                    'cantidad_chapas' => $orden->cantidad_chapas ?? 0,
                    'precio_unitario' => $orden->precio_unitario ?? 0,
                    'total_item' => $orden->total ?? 0,
                ),
            );
        }
    }

    return $items_map;
}

function ctp_ordenes_render_items_table($items) {
    if (empty($items)) {
        return '<p>No hay ítems cargados.</p>';
    }

    ob_start();
    ?>
    <table class="ctp-table ctp-table-small">
        <thead>
            <tr>
                <th>Medida</th>
                <th>Cantidad</th>
                <th>Unitario</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($items as $item) : ?>
                <tr>
                    <td data-label="Medida"><?php echo esc_html($item->medida_chapa); ?></td>
                    <td data-label="Cantidad"><?php echo esc_html($item->cantidad_chapas); ?></td>
                    <td data-label="Unitario"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($item->precio_unitario)); ?></td>
                    <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($item->total_item)); ?></td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
    <?php
    return ob_get_clean();
}

function ctp_ordenes_is_valid_date($date, $format) {
    if (empty($date)) {
        return false;
    }

    $parsed = DateTime::createFromFormat($format, $date);
    return $parsed && $parsed->format($format) === $date;
}

function ctp_period_from_date($date) {
    if (ctp_ordenes_is_valid_date($date, 'Y-m-d')) {
        return date('Y-m', strtotime($date));
    }

    return current_time('Y-m');
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
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

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
                    COALESCE(SUM(order_total), 0) AS total,
                    MAX(fecha) AS ultima_fecha
             FROM (
                SELECT o.id,
                       o.fecha,
                       COALESCE(SUM(i.total_item), o.total) AS order_total
                FROM {$table_ordenes} o
                LEFT JOIN {$table_items} i ON i.orden_id = o.id
                WHERE {$where}
                GROUP BY o.id
             ) AS ordenes",
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
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

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
            "SELECT o.id,
                    o.fecha,
                    o.numero_orden,
                    o.nombre_trabajo,
                    o.descripcion,
                    o.cantidad_chapas,
                    o.medida_chapa,
                    o.precio_unitario,
                    COALESCE(SUM(i.total_item), o.total) AS total,
                    CASE WHEN COUNT(i.id) > 0 THEN COUNT(i.id) ELSE 1 END AS items_count
             FROM {$table_ordenes} o
             LEFT JOIN {$table_items} i ON i.orden_id = o.id
             WHERE {$where}
             GROUP BY o.id
             ORDER BY o.fecha DESC, o.id DESC
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

function ctp_upsert_deuda_from_factura_proveedor($factura_id) {
    global $wpdb;

    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_deudas = $wpdb->prefix . 'ctp_deudas_empresa';

    $factura = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT f.*, p.nombre AS proveedor_nombre
             FROM {$table_facturas} f
             LEFT JOIN {$table_proveedores} p ON f.proveedor_id = p.id
             WHERE f.id = %d",
            $factura_id
        )
    );

    if (!$factura) {
        return false;
    }

    $fecha_inicio = $factura->vencimiento && ctp_ordenes_is_valid_date($factura->vencimiento, 'Y-m-d')
        ? $factura->vencimiento
        : $factura->fecha_factura;

    if (!ctp_ordenes_is_valid_date($fecha_inicio, 'Y-m-d')) {
        $fecha_inicio = current_time('Y-m-d');
    }

    $descripcion = 'Factura proveedor';
    if (!empty($factura->nro_factura)) {
        $descripcion .= ' #' . $factura->nro_factura;
    }
    $proveedor_nombre = trim((string) ($factura->proveedor_nombre ?? ''));
    if ($proveedor_nombre !== '') {
        $descripcion .= ' - ' . $proveedor_nombre;
    }

    $data = array(
        'categoria' => 'proveedores',
        'tipo' => 'unico',
        'descripcion' => $descripcion,
        'proveedor_id' => (int) $factura->proveedor_id,
        'monto_total' => (float) $factura->monto_total,
        'monto_mensual' => 0,
        'cuotas_total' => 0,
        'fecha_inicio' => $fecha_inicio,
        'fecha_fin' => null,
        'dia_vencimiento' => 0,
        'estado' => 'activa',
        'source_type' => 'factura_proveedor',
        'source_id' => (int) $factura->id,
        'updated_at' => current_time('mysql'),
    );

    $existing_id = (int) $wpdb->get_var(
        $wpdb->prepare(
            "SELECT id FROM {$table_deudas} WHERE source_type = %s AND source_id = %d",
            'factura_proveedor',
            $factura->id
        )
    );

    $formats = array('%s', '%s', '%s', '%d', '%f', '%f', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s');

    if ($existing_id > 0) {
        $updated = $wpdb->update(
            $table_deudas,
            $data,
            array('id' => $existing_id),
            $formats,
            array('%d')
        );
        return $updated !== false ? $existing_id : false;
    }

    $data['created_at'] = current_time('mysql');
    $formats[] = '%s';

    $inserted = $wpdb->insert($table_deudas, $data, $formats);
    return $inserted ? (int) $wpdb->insert_id : false;
}

function ctp_register_deuda_pago_from_factura($factura, $deuda_id) {
    if (!$factura || $deuda_id <= 0) {
        return false;
    }

    $monto = isset($factura->pago_monto) ? (float) $factura->pago_monto : 0;
    if ($monto <= 0) {
        return false;
    }

    $fecha_pago = '';
    if (!empty($factura->pago_fecha)) {
        $fecha_pago = $factura->pago_fecha;
    } elseif (!empty($factura->vencimiento)) {
        $fecha_pago = $factura->vencimiento;
    } elseif (!empty($factura->fecha_factura)) {
        $fecha_pago = $factura->fecha_factura;
    }

    if (!ctp_ordenes_is_valid_date($fecha_pago, 'Y-m-d')) {
        $fecha_pago = current_time('Y-m-d');
    }

    $periodo = ctp_period_from_date($fecha_pago);

    global $wpdb;
    $table_pagos = $wpdb->prefix . 'ctp_deudas_empresa_pagos';

    $existing = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT id, monto FROM {$table_pagos} WHERE deuda_id = %d AND periodo = %s",
            $deuda_id,
            $periodo
        )
    );

    if ($existing) {
        $nuevo_monto = (float) $existing->monto + $monto;
        return $wpdb->update(
            $table_pagos,
            array(
                'monto' => $nuevo_monto,
                'fecha_pago' => $fecha_pago,
            ),
            array('id' => $existing->id),
            array('%f', '%s'),
            array('%d')
        );
    }

    return $wpdb->insert(
        $table_pagos,
        array(
            'deuda_id' => $deuda_id,
            'periodo' => $periodo,
            'fecha_pago' => $fecha_pago,
            'monto' => $monto,
            'notas' => !empty($factura->nro_factura) ? 'Pago factura proveedor #' . $factura->nro_factura : '',
            'created_at' => current_time('mysql'),
        ),
        array('%d', '%s', '%s', '%f', '%s', '%s')
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
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

    return $wpdb->get_results(
        $wpdb->prepare(
            "SELECT o.id,
                    o.fecha,
                    o.numero_orden,
                    o.nombre_trabajo,
                    o.descripcion,
                    o.cantidad_chapas,
                    o.medida_chapa,
                    o.precio_unitario,
                    COALESCE(SUM(i.total_item), o.total) AS total,
                    CASE WHEN COUNT(i.id) > 0 THEN COUNT(i.id) ELSE 1 END AS items_count
             FROM {$table_ordenes} o
             LEFT JOIN {$table_liquidacion_ordenes} lo ON lo.orden_id = o.id
             LEFT JOIN {$table_items} i ON i.orden_id = o.id
             WHERE o.cliente_id = %d
               AND o.fecha BETWEEN %s AND %s
               AND lo.id IS NULL
             GROUP BY o.id
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
            $nombre_trabajo = sanitize_text_field($_POST['nombre_trabajo'] ?? '');
            $descripcion = sanitize_textarea_field($_POST['descripcion'] ?? '');
            $cantidad_chapas_raw = isset($_POST['cantidad_chapas']) ? (array) wp_unslash($_POST['cantidad_chapas']) : array();
            $medida_chapa_raw = isset($_POST['medida_chapa']) ? (array) wp_unslash($_POST['medida_chapa']) : array();
            $precio_unitario_raw = isset($_POST['precio_unitario']) ? (array) wp_unslash($_POST['precio_unitario']) : array();

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
            $medidas_validas = ctp_ordenes_get_medidas_chapa();
            $max_items = max(count($cantidad_chapas_raw), count($medida_chapa_raw), count($precio_unitario_raw), 1);
            $items = array();

            for ($i = 0; $i < $max_items; $i++) {
                $medida_chapa = sanitize_text_field($medida_chapa_raw[$i] ?? '');
                $cantidad_chapas = absint($cantidad_chapas_raw[$i] ?? 0);
                $precio_unitario = floatval($precio_unitario_raw[$i] ?? 0);

                if ($medida_chapa === '' && $cantidad_chapas === 0 && $precio_unitario === 0.0) {
                    continue;
                }

                if (!in_array($medida_chapa, $medidas_validas, true)) {
                    $errores[] = sprintf('Selecciona una medida de chapa válida para el ítem %d.', $i + 1);
                }

                if ($cantidad_chapas < 1) {
                    $errores[] = sprintf('La cantidad del ítem %d debe ser mayor a cero.', $i + 1);
                }

                if ($precio_unitario < 0) {
                    $errores[] = sprintf('El precio del ítem %d no puede ser negativo.', $i + 1);
                }

                if (empty($errores)) {
                    $items[] = array(
                        'medida_chapa' => $medida_chapa,
                        'cantidad_chapas' => $cantidad_chapas,
                        'precio_unitario' => $precio_unitario,
                        'total_item' => $cantidad_chapas * $precio_unitario,
                    );
                }
            }

            if (empty($items) && empty($errores)) {
                $errores[] = 'Agrega al menos un trabajo a la orden.';
            }

            if (empty($errores)) {
                global $wpdb;
                $table_name = $wpdb->prefix . 'ctp_ordenes';
                $table_items = $wpdb->prefix . 'ctp_ordenes_items';

                $orden_existente = $wpdb->get_row(
                    $wpdb->prepare(
                        "SELECT id, total FROM {$table_name} WHERE numero_orden = %s",
                        $numero_orden
                    )
                );

                $now = current_time('mysql');
                $orden_id = 0;
                $creada = false;

                if ($orden_existente) {
                    $orden_id = (int) $orden_existente->id;
                } else {
                    $primer_item = $items[0];
                    $orden_total = 0;
                    foreach ($items as $item) {
                        $orden_total += $item['total_item'];
                    }

                    $insertado = $wpdb->insert(
                        $table_name,
                        array(
                            'fecha' => $fecha,
                            'numero_orden' => $numero_orden,
                            'cliente' => $cliente,
                            'cliente_id' => $cliente_id > 0 ? $cliente_id : null,
                            'nombre_trabajo' => $nombre_trabajo,
                            'descripcion' => $descripcion,
                            'cantidad_chapas' => $primer_item['cantidad_chapas'],
                            'medida_chapa' => $primer_item['medida_chapa'],
                            'precio_unitario' => $primer_item['precio_unitario'],
                            'total' => $orden_total,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%s', '%s', '%s', '%d', '%s', '%s', '%d', '%s', '%f', '%f', '%s', '%s')
                    );

                    if ($insertado) {
                        $orden_id = (int) $wpdb->insert_id;
                        $creada = true;
                    } else {
                        $errores[] = 'No se pudo guardar la orden. Intenta nuevamente.';
                    }
                }

                if (empty($errores) && $orden_id > 0) {
                    $insertados = 0;
                    foreach ($items as $item) {
                        $result = $wpdb->insert(
                            $table_items,
                            array(
                                'orden_id' => $orden_id,
                                'medida_chapa' => $item['medida_chapa'],
                                'cantidad_chapas' => $item['cantidad_chapas'],
                                'precio_unitario' => $item['precio_unitario'],
                                'total_item' => $item['total_item'],
                                'created_at' => $now,
                                'updated_at' => $now,
                            ),
                            array('%d', '%s', '%d', '%f', '%f', '%s', '%s')
                        );
                        if ($result) {
                            $insertados++;
                        }
                    }

                    $orden_total = ctp_ordenes_get_order_total($orden_id, $orden_existente ? $orden_existente->total : 0);
                    $wpdb->update(
                        $table_name,
                        array(
                            'total' => $orden_total,
                            'updated_at' => $now,
                        ),
                        array('id' => $orden_id),
                        array('%f', '%s'),
                        array('%d')
                    );

                    if ($creada) {
                        $mensaje = 'Orden guardada correctamente.';
                    } else {
                        $mensaje = sprintf('Se agregaron %d trabajos a la orden existente.', $insertados);
                    }

                    $_POST = array();
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
    $nombre_trabajo_val = !empty($_POST['nombre_trabajo']) ? sanitize_text_field($_POST['nombre_trabajo']) : '';
    $descripcion_val = !empty($_POST['descripcion']) ? sanitize_textarea_field($_POST['descripcion']) : '';
    $medidas = ctp_ordenes_get_medidas_chapa();
    $cantidad_chapas_raw = isset($_POST['cantidad_chapas']) ? (array) wp_unslash($_POST['cantidad_chapas']) : array();
    $medida_chapa_raw = isset($_POST['medida_chapa']) ? (array) wp_unslash($_POST['medida_chapa']) : array();
    $precio_unitario_raw = isset($_POST['precio_unitario']) ? (array) wp_unslash($_POST['precio_unitario']) : array();
    $items_form = array();

    if (!empty($cantidad_chapas_raw) || !empty($medida_chapa_raw) || !empty($precio_unitario_raw)) {
        $max_items = max(count($cantidad_chapas_raw), count($medida_chapa_raw), count($precio_unitario_raw), 1);
        for ($i = 0; $i < $max_items; $i++) {
            $items_form[] = array(
                'cantidad_chapas' => absint($cantidad_chapas_raw[$i] ?? 1),
                'medida_chapa' => sanitize_text_field($medida_chapa_raw[$i] ?? $medidas[0]),
                'precio_unitario' => floatval($precio_unitario_raw[$i] ?? 0),
            );
        }
    }

    if (empty($items_form)) {
        $items_form[] = array(
            'cantidad_chapas' => 1,
            'medida_chapa' => $medidas[0],
            'precio_unitario' => 0,
        );
    }

    $total_val = 0;
    foreach ($items_form as $item) {
        $total_val += $item['cantidad_chapas'] * $item['precio_unitario'];
    }

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
                <label for="ctp-nombre-trabajo">Nombre del trabajo</label>
                <input type="text" id="ctp-nombre-trabajo" name="nombre_trabajo" value="<?php echo esc_attr($nombre_trabajo_val); ?>" maxlength="255">
            </div>

            <div class="ctp-field ctp-field-full">
                <label for="ctp-descripcion">Descripción</label>
                <textarea id="ctp-descripcion" name="descripcion" rows="3"><?php echo esc_textarea($descripcion_val); ?></textarea>
            </div>

            <div class="ctp-field ctp-field-full">
                <div class="ctp-order-items-header">
                    <h4>Trabajos / Ítems</h4>
                    <p>Agrega una o más medidas para la misma orden.</p>
                </div>
                <div class="ctp-order-items" data-ctp-items>
                    <?php foreach ($items_form as $index => $item) : ?>
                        <?php
                        $row_total = $item['cantidad_chapas'] * $item['precio_unitario'];
                        ?>
                        <div class="ctp-order-item-row" data-ctp-item>
                            <div class="ctp-field">
                                <label>Medida de chapa</label>
                                <select name="medida_chapa[]" class="ctp-item-measure" required>
                                    <?php foreach ($medidas as $medida) : ?>
                                        <option value="<?php echo esc_attr($medida); ?>" <?php selected($medida, $item['medida_chapa']); ?>>
                                            <?php echo esc_html($medida); ?>
                                        </option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                            <div class="ctp-field">
                                <label>Cantidad</label>
                                <input type="number" class="ctp-item-quantity" name="cantidad_chapas[]" min="1" value="<?php echo esc_attr($item['cantidad_chapas']); ?>" required>
                            </div>
                            <div class="ctp-field">
                                <label>Precio unitario</label>
                                <input type="number" class="ctp-item-price" name="precio_unitario[]" step="0.01" min="0" value="<?php echo esc_attr($item['precio_unitario']); ?>" required>
                            </div>
                            <div class="ctp-field">
                                <label>Total ítem</label>
                                <input type="number" class="ctp-item-total" readonly value="<?php echo esc_attr(number_format($row_total, 2, '.', '')); ?>">
                            </div>
                            <div class="ctp-field ctp-order-item-remove">
                                <button type="button" class="ctp-button ctp-button-danger ctp-remove-item" <?php disabled($index === 0); ?>>Quitar</button>
                            </div>
                        </div>
                    <?php endforeach; ?>
                </div>
                <div class="ctp-order-item-actions">
                    <button type="button" class="ctp-button ctp-button-secondary ctp-add-item">+ Agregar otro trabajo</button>
                </div>
                <template class="ctp-order-item-template">
                    <div class="ctp-order-item-row" data-ctp-item>
                        <div class="ctp-field">
                            <label>Medida de chapa</label>
                            <select name="medida_chapa[]" class="ctp-item-measure" required>
                                <?php foreach ($medidas as $medida) : ?>
                                    <option value="<?php echo esc_attr($medida); ?>">
                                        <?php echo esc_html($medida); ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="ctp-field">
                            <label>Cantidad</label>
                            <input type="number" class="ctp-item-quantity" name="cantidad_chapas[]" min="1" value="1" required>
                        </div>
                        <div class="ctp-field">
                            <label>Precio unitario</label>
                            <input type="number" class="ctp-item-price" name="precio_unitario[]" step="0.01" min="0" value="0" required>
                        </div>
                        <div class="ctp-field">
                            <label>Total ítem</label>
                            <input type="number" class="ctp-item-total" readonly value="0.00">
                        </div>
                        <div class="ctp-field ctp-order-item-remove">
                            <button type="button" class="ctp-button ctp-button-danger ctp-remove-item">Quitar</button>
                        </div>
                    </div>
                </template>
            </div>

            <div class="ctp-field">
                <label for="ctp-total-orden">Total</label>
                <input type="number" id="ctp-total-orden" class="ctp-order-total" name="total_orden" readonly value="<?php echo esc_attr(number_format($total_val, 2, '.', '')); ?>">
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
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

    $periodo = ctp_ordenes_get_ordenes_periodo();
    $where_clause = 'fecha BETWEEN %s AND %s';
    $where_params = array($periodo['start'], $periodo['end']);

    $ordenes = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT o.id,
                    o.fecha,
                    o.numero_orden,
                    COALESCE(c.nombre, o.cliente) AS cliente_nombre,
                    o.nombre_trabajo,
                    o.descripcion,
                    o.cantidad_chapas,
                    o.medida_chapa,
                    o.precio_unitario,
                    COALESCE(SUM(i.total_item), o.total) AS total,
                    CASE WHEN COUNT(i.id) > 0 THEN COUNT(i.id) ELSE 1 END AS items_count
             FROM {$table_name} o
             LEFT JOIN {$table_clientes} c ON o.cliente_id = c.id
             LEFT JOIN {$table_items} i ON i.orden_id = o.id
             WHERE {$where_clause}
             GROUP BY o.id
             ORDER BY o.fecha DESC, o.id DESC
             LIMIT 50",
            $where_params
        )
    );

    $resumen = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT COUNT(*) AS cantidad,
                    COALESCE(SUM(order_total), 0) AS total
             FROM (
                SELECT o.id,
                       COALESCE(SUM(i.total_item), o.total) AS order_total
                FROM {$table_name} o
                LEFT JOIN {$table_items} i ON i.orden_id = o.id
                WHERE {$where_clause}
                GROUP BY o.id
             ) AS ordenes",
            $where_params
        )
    );

    $ordenes_cantidad = $resumen ? (int) $resumen->cantidad : 0;
    $ordenes_total = $resumen ? (float) $resumen->total : 0;

    $base_url = remove_query_arg(array('ctp_period', 'ctp_month', 'ctp_from', 'ctp_to'));
    $items_map = ctp_ordenes_get_items_map($ordenes);
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
                <th>Nombre del trabajo</th>
                <th>Cliente</th>
                <th>Trabajos</th>
                <th>Total</th>
                <th>Detalle</th>
            </tr>
        </thead>
        <tbody>
            <?php if (!empty($ordenes)) : ?>
                <?php foreach ($ordenes as $orden) : ?>
                    <tr>
                        <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                        <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                        <td data-label="Nombre del trabajo"><?php echo esc_html(ctp_ordenes_format_job_name($orden->nombre_trabajo ?? '')); ?></td>
                        <td data-label="Cliente"><?php echo esc_html($orden->cliente_nombre); ?></td>
                        <td data-label="Trabajos"><?php echo esc_html(ctp_ordenes_format_items_count((int) $orden->items_count)); ?></td>
                        <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                        <td data-label="Detalle">
                            <details class="ctp-details">
                                <summary class="ctp-button ctp-button-secondary">Ver ítems</summary>
                                <div class="ctp-details-panel">
                                    <?php echo ctp_ordenes_render_items_table($items_map[(int) $orden->id] ?? array()); ?>
                                </div>
                            </details>
                        </td>
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
        $items_map = ctp_ordenes_get_items_map($ordenes);
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
                                        <th>Nombre del trabajo</th>
                                        <th>Descripción</th>
                                        <th>Trabajos</th>
                                        <th>Total</th>
                                        <th>Detalle</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php if (!empty($ordenes)) : ?>
                                        <?php foreach ($ordenes as $orden) : ?>
                                            <tr>
                                                <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                                                <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                                                <td data-label="Nombre del trabajo"><?php echo esc_html(ctp_ordenes_format_job_name($orden->nombre_trabajo ?? '')); ?></td>
                                                <td data-label="Descripción"><?php echo esc_html($orden->descripcion); ?></td>
                                                <td data-label="Trabajos"><?php echo esc_html(ctp_ordenes_format_items_count((int) $orden->items_count)); ?></td>
                                                <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                                                <td data-label="Detalle">
                                                    <details class="ctp-details">
                                                        <summary class="ctp-button ctp-button-secondary">Ver ítems</summary>
                                                        <div class="ctp-details-panel">
                                                            <?php echo ctp_ordenes_render_items_table($items_map[(int) $orden->id] ?? array()); ?>
                                                        </div>
                                                    </details>
                                                </td>
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
                        $deuda_id = ctp_upsert_deuda_from_factura_proveedor((int) $wpdb->insert_id);
                        if (!$deuda_id) {
                            $mensajes['warning'][] = 'La factura se guardó, pero no se pudo sincronizar la deuda.';
                        }
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
                        $deuda_id = ctp_upsert_deuda_from_factura_proveedor($factura_id);
                        if ($deuda_id) {
                            $factura->pago_monto = $monto;
                            $factura->pago_fecha = $fecha_pago;
                            ctp_register_deuda_pago_from_factura($factura, $deuda_id);
                        } else {
                            $mensajes['warning'][] = 'El pago se registró, pero no se pudo sincronizar la deuda.';
                        }
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
                        $deuda_id = (int) $wpdb->get_var(
                            $wpdb->prepare(
                                "SELECT id FROM {$wpdb->prefix}ctp_deudas_empresa WHERE source_type = %s AND source_id = %d",
                                'factura_proveedor',
                                $factura_id
                            )
                        );
                        if ($deuda_id > 0) {
                            $wpdb->delete($wpdb->prefix . 'ctp_deudas_empresa_pagos', array('deuda_id' => $deuda_id), array('%d'));
                            $wpdb->delete($wpdb->prefix . 'ctp_deudas_empresa', array('id' => $deuda_id), array('%d'));
                        }
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

function ctp_deudas_empresa_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_deudas = $wpdb->prefix . 'ctp_deudas_empresa';
    $table_pagos = $wpdb->prefix . 'ctp_deudas_empresa_pagos';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    $can_manage = ctp_ordenes_user_can_manage();

    $periodo_data = ctp_ordenes_get_deudas_periodo();
    if (isset($_POST['ctp_period'])) {
        $periodo_post = sanitize_text_field(wp_unslash($_POST['ctp_period']));
        if (ctp_ordenes_is_valid_date($periodo_post, 'Y-m')) {
            $periodo_data = ctp_ordenes_get_deudas_periodo($periodo_post);
        }
    }

    $periodo = $periodo_data['period'];
    $periodo_label = $periodo_data['label'];
    $tab = isset($_GET['ctp_tab']) ? sanitize_key(wp_unslash($_GET['ctp_tab'])) : '';

    $categorias = array(
        'prestamo' => 'Préstamo',
        'alquiler' => 'Alquiler',
        'servicios' => 'Servicios',
        'sueldos' => 'Sueldos',
        'proveedores' => 'Proveedores',
        'otros' => 'Otros',
    );

    $tipos = array(
        'mensual' => 'Mensual',
        'unico' => 'Único',
        'cuotas' => 'Cuotas',
    );

    if (!empty($_POST['ctp_deuda_action'])) {
        if (!$can_manage) {
            $mensajes['error'][] = 'No tienes permisos para gestionar deudas.';
        } else {
            $action = sanitize_text_field(wp_unslash($_POST['ctp_deuda_action']));

            if ($action === 'add') {
                if (!isset($_POST['ctp_deuda_nonce']) || !check_admin_referer('ctp_deuda_add', 'ctp_deuda_nonce')) {
                    $mensajes['error'][] = 'No se pudo validar la solicitud para agregar la deuda.';
                } else {
                    $categoria = sanitize_text_field(wp_unslash($_POST['categoria'] ?? ''));
                    $tipo = sanitize_text_field(wp_unslash($_POST['tipo'] ?? ''));
                    $descripcion = sanitize_textarea_field(wp_unslash($_POST['descripcion'] ?? ''));
                    $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                    $monto_total = isset($_POST['monto_total']) ? floatval(str_replace(',', '.', sanitize_text_field(wp_unslash($_POST['monto_total'])))) : 0;
                    $monto_mensual = isset($_POST['monto_mensual']) ? floatval(str_replace(',', '.', sanitize_text_field(wp_unslash($_POST['monto_mensual'])))) : 0;
                    $cuotas_total = absint($_POST['cuotas_total'] ?? 0);
                    $fecha_inicio = sanitize_text_field(wp_unslash($_POST['fecha_inicio'] ?? ''));
                    $fecha_fin = sanitize_text_field(wp_unslash($_POST['fecha_fin'] ?? ''));
                    $dia_vencimiento = absint($_POST['dia_vencimiento'] ?? 0);

                    if (!array_key_exists($categoria, $categorias)) {
                        $mensajes['error'][] = 'Selecciona una categoría válida.';
                    }

                    if (!array_key_exists($tipo, $tipos)) {
                        $mensajes['error'][] = 'Selecciona un tipo válido.';
                    }

                    if (!ctp_ordenes_is_valid_date($fecha_inicio, 'Y-m-d')) {
                        $mensajes['error'][] = 'La fecha de inicio es obligatoria.';
                    }

                    if ($fecha_fin !== '' && !ctp_ordenes_is_valid_date($fecha_fin, 'Y-m-d')) {
                        $mensajes['error'][] = 'La fecha de fin no es válida.';
                    }

                    if ($fecha_fin !== '' && $fecha_inicio !== '' && strtotime($fecha_fin) < strtotime($fecha_inicio)) {
                        $mensajes['error'][] = 'La fecha de fin no puede ser anterior a la fecha de inicio.';
                    }

                    if ($dia_vencimiento > 31) {
                        $mensajes['error'][] = 'El día de vencimiento debe estar entre 1 y 31.';
                    }

                    if ($proveedor_id > 0) {
                        $proveedor_exists = $wpdb->get_var(
                            $wpdb->prepare(
                                "SELECT id FROM {$table_proveedores} WHERE id = %d",
                                $proveedor_id
                            )
                        );
                        if (!$proveedor_exists) {
                            $mensajes['error'][] = 'El proveedor seleccionado no existe.';
                        }
                    }

                    if ($tipo === 'mensual') {
                        if ($monto_mensual <= 0 && $monto_total > 0) {
                            $monto_mensual = $monto_total;
                        }
                        if ($monto_mensual <= 0) {
                            $mensajes['error'][] = 'Ingresa un monto mensual válido.';
                        }
                        if ($monto_total <= 0) {
                            $monto_total = $monto_mensual;
                        }
                        $cuotas_total = 0;
                    } elseif ($tipo === 'unico') {
                        if ($monto_total <= 0 && $monto_mensual > 0) {
                            $monto_total = $monto_mensual;
                        }
                        if ($monto_total <= 0) {
                            $mensajes['error'][] = 'Ingresa un monto total válido.';
                        }
                        $monto_mensual = 0;
                        $cuotas_total = 0;
                    } elseif ($tipo === 'cuotas') {
                        if ($cuotas_total <= 0) {
                            $mensajes['error'][] = 'Ingresa la cantidad de cuotas.';
                        }
                        if ($monto_mensual <= 0 && $monto_total > 0 && $cuotas_total > 0) {
                            $monto_mensual = $monto_total / $cuotas_total;
                        }
                        if ($monto_total <= 0 && $monto_mensual > 0 && $cuotas_total > 0) {
                            $monto_total = $monto_mensual * $cuotas_total;
                        }
                        if ($monto_mensual <= 0 || $monto_total <= 0) {
                            $mensajes['error'][] = 'Ingresa montos válidos para la deuda en cuotas.';
                        }
                    }

                    if (empty($mensajes['error'])) {
                        $now = current_time('mysql');
                        $inserted = $wpdb->insert(
                            $table_deudas,
                            array(
                                'categoria' => $categoria,
                                'tipo' => $tipo,
                                'descripcion' => $descripcion,
                                'proveedor_id' => $proveedor_id > 0 ? $proveedor_id : null,
                                'monto_total' => $monto_total,
                                'monto_mensual' => $monto_mensual,
                                'cuotas_total' => $cuotas_total > 0 ? $cuotas_total : null,
                                'fecha_inicio' => $fecha_inicio,
                                'fecha_fin' => $fecha_fin !== '' ? $fecha_fin : null,
                                'dia_vencimiento' => $dia_vencimiento > 0 ? $dia_vencimiento : null,
                                'estado' => 'activa',
                                'created_at' => $now,
                                'updated_at' => $now,
                            ),
                            array('%s', '%s', '%s', '%d', '%f', '%f', '%d', '%s', '%s', '%d', '%s', '%s', '%s')
                        );

                        if ($inserted) {
                            $mensajes['success'][] = 'Deuda agregada correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo guardar la deuda.';
                        }
                    }
                }
            } elseif ($action === 'delete') {
                if (!isset($_POST['ctp_deuda_nonce']) || !check_admin_referer('ctp_deuda_delete', 'ctp_deuda_nonce')) {
                    $mensajes['error'][] = 'No se pudo validar la solicitud para eliminar la deuda.';
                } else {
                    $deuda_id = absint($_POST['deuda_id'] ?? 0);
                    if ($deuda_id <= 0) {
                        $mensajes['error'][] = 'No se recibió una deuda válida.';
                    } else {
                        $wpdb->delete($table_pagos, array('deuda_id' => $deuda_id), array('%d'));
                        $deleted = $wpdb->delete($table_deudas, array('id' => $deuda_id), array('%d'));
                        if ($deleted) {
                            $mensajes['success'][] = 'Deuda eliminada correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo eliminar la deuda.';
                        }
                    }
                }
            } elseif ($action === 'toggle_pago') {
                if (!isset($_POST['ctp_deuda_nonce']) || !check_admin_referer('ctp_deuda_toggle_pago', 'ctp_deuda_nonce')) {
                    $mensajes['error'][] = 'No se pudo validar la solicitud de pago.';
                } else {
                    $deuda_id = absint($_POST['deuda_id'] ?? 0);
                    if ($deuda_id <= 0) {
                        $mensajes['error'][] = 'No se recibió una deuda válida.';
                    } else {
                        $deuda = $wpdb->get_row(
                            $wpdb->prepare(
                                "SELECT * FROM {$table_deudas} WHERE id = %d",
                                $deuda_id
                            )
                        );
                        if (!$deuda) {
                            $mensajes['error'][] = 'La deuda seleccionada no existe.';
                        } elseif (!ctp_ordenes_deuda_aplica_periodo($deuda, $periodo)) {
                            $mensajes['warning'][] = 'La deuda no aplica al período seleccionado.';
                        } else {
                            $pago = $wpdb->get_row(
                                $wpdb->prepare(
                                    "SELECT id FROM {$table_pagos} WHERE deuda_id = %d AND periodo = %s",
                                    $deuda_id,
                                    $periodo
                                )
                            );

                            if ($pago) {
                                $deleted = $wpdb->delete($table_pagos, array('id' => $pago->id), array('%d'));
                                if ($deleted) {
                                    $mensajes['success'][] = 'Pago desmarcado correctamente.';
                                } else {
                                    $mensajes['error'][] = 'No se pudo desmarcar el pago.';
                                }
                            } else {
                                $monto_mes = ctp_ordenes_deuda_get_monto_periodo($deuda, $periodo);
                                if ($monto_mes <= 0) {
                                    $mensajes['error'][] = 'No se pudo determinar el monto del período.';
                                } else {
                                    $inserted = $wpdb->insert(
                                        $table_pagos,
                                        array(
                                            'deuda_id' => $deuda_id,
                                            'periodo' => $periodo,
                                            'fecha_pago' => current_time('Y-m-d'),
                                            'monto' => $monto_mes,
                                            'notas' => '',
                                            'created_at' => current_time('mysql'),
                                        ),
                                        array('%d', '%s', '%s', '%f', '%s', '%s')
                                    );
                                    if ($inserted) {
                                        $mensajes['success'][] = 'Pago registrado correctamente.';
                                    } else {
                                        $mensajes['error'][] = 'No se pudo registrar el pago.';
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    $proveedores = $wpdb->get_results(
        "SELECT id, nombre FROM {$table_proveedores} ORDER BY nombre ASC"
    );

    $deudas = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT d.*, p.id AS pago_id, p.monto AS pago_monto, p.fecha_pago
             FROM {$table_deudas} d
             LEFT JOIN {$table_pagos} p
                ON p.deuda_id = d.id
               AND p.periodo = %s
             ORDER BY d.created_at DESC, d.id DESC",
            $periodo
        )
    );

    $total_estimado = 0;
    $total_pagado = 0;
    foreach ($deudas as $deuda) {
        $monto_mes = ctp_ordenes_deuda_get_monto_periodo($deuda, $periodo);
        if ($monto_mes > 0) {
            $total_estimado += $monto_mes;
            if (!empty($deuda->pago_id)) {
                $total_pagado += (float) $deuda->pago_monto;
            }
        }
    }
    $total_pendiente = max($total_estimado - $total_pagado, 0);

    ob_start();
    ?>
    <?php ctp_ordenes_render_alerts($mensajes); ?>
    <div class="ctp-stack">
        <form method="get" action="<?php echo esc_url(remove_query_arg('ctp_period')); ?>" class="ctp-order-filter">
            <?php if (!empty($tab)) : ?>
                <input type="hidden" name="ctp_tab" value="<?php echo esc_attr($tab); ?>">
            <?php endif; ?>
            <div class="ctp-filter-group">
                <div class="ctp-field">
                    <label for="ctp-deudas-periodo">Periodo</label>
                    <input type="month" id="ctp-deudas-periodo" name="ctp_period" value="<?php echo esc_attr($periodo); ?>">
                </div>
                <div class="ctp-field">
                    <label>&nbsp;</label>
                    <button type="submit" class="ctp-button">Ver</button>
                </div>
            </div>
        </form>
        <div class="ctp-kpi-grid">
            <div class="ctp-kpi-card">
                <div class="ctp-kpi-title">Total estimado</div>
                <div class="ctp-kpi-value"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency_i18n($total_estimado, 0)); ?></div>
                <div class="ctp-kpi-meta"><?php echo esc_html($periodo_label); ?></div>
            </div>
            <div class="ctp-kpi-card">
                <div class="ctp-kpi-title">Total pagado</div>
                <div class="ctp-kpi-value"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency_i18n($total_pagado, 0)); ?></div>
                <div class="ctp-kpi-meta"><?php echo esc_html($periodo_label); ?></div>
            </div>
            <div class="ctp-kpi-card">
                <div class="ctp-kpi-title">Total pendiente</div>
                <div class="ctp-kpi-value"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency_i18n($total_pendiente, 0)); ?></div>
                <div class="ctp-kpi-meta"><?php echo esc_html($periodo_label); ?></div>
            </div>
        </div>
        <?php
        ob_start();
        ?>
        <form method="post" class="ctp-form ctp-form-grid" id="ctp-deuda-form">
            <?php wp_nonce_field('ctp_deuda_add', 'ctp_deuda_nonce'); ?>
            <input type="hidden" name="ctp_deuda_action" value="add">
            <input type="hidden" name="ctp_period" value="<?php echo esc_attr($periodo); ?>">
            <?php if (!empty($tab)) : ?>
                <input type="hidden" name="ctp_tab" value="<?php echo esc_attr($tab); ?>">
            <?php endif; ?>

            <div class="ctp-field">
                <label for="ctp-deuda-categoria">Categoría</label>
                <select id="ctp-deuda-categoria" name="categoria" required <?php disabled(!$can_manage); ?>>
                    <?php foreach ($categorias as $value => $label) : ?>
                        <option value="<?php echo esc_attr($value); ?>"><?php echo esc_html($label); ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-deuda-tipo">Tipo</label>
                <select id="ctp-deuda-tipo" name="tipo" required <?php disabled(!$can_manage); ?>>
                    <?php foreach ($tipos as $value => $label) : ?>
                        <option value="<?php echo esc_attr($value); ?>"><?php echo esc_html($label); ?></option>
                    <?php endforeach; ?>
                </select>
                <p class="ctp-helper-text" id="ctp-deuda-tipo-helper">Mensual: se repite cada mes desde inicio hasta fin (si se define).</p>
            </div>

            <div class="ctp-field ctp-field-full">
                <label for="ctp-deuda-descripcion">Descripción</label>
                <textarea id="ctp-deuda-descripcion" name="descripcion" rows="3" <?php disabled(!$can_manage); ?>></textarea>
            </div>

            <div class="ctp-field">
                <label for="ctp-deuda-proveedor">Proveedor (opcional)</label>
                <select id="ctp-deuda-proveedor" name="proveedor_id" <?php disabled(!$can_manage); ?>>
                    <option value="0">Sin proveedor</option>
                    <?php foreach ($proveedores as $proveedor) : ?>
                        <option value="<?php echo esc_attr($proveedor->id); ?>"><?php echo esc_html($proveedor->nombre); ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-deuda-fecha-inicio">Fecha inicio</label>
                <input type="date" id="ctp-deuda-fecha-inicio" name="fecha_inicio" required <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field ctp-deuda-field ctp-deuda-field-total">
                <label for="ctp-deuda-monto-total">Monto total</label>
                <input type="number" id="ctp-deuda-monto-total" name="monto_total" step="0.01" min="0" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field ctp-deuda-field ctp-deuda-field-mensual">
                <label for="ctp-deuda-monto-mensual">Monto mensual</label>
                <input type="number" id="ctp-deuda-monto-mensual" name="monto_mensual" step="0.01" min="0" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field ctp-deuda-field ctp-deuda-field-cuotas">
                <label for="ctp-deuda-cuotas">Cantidad de cuotas</label>
                <input type="number" id="ctp-deuda-cuotas" name="cuotas_total" min="0" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field">
                <label for="ctp-deuda-vencimiento">Día de vencimiento</label>
                <input type="number" id="ctp-deuda-vencimiento" name="dia_vencimiento" min="1" max="31" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field">
                <label for="ctp-deuda-fecha-fin">Fecha fin (opcional)</label>
                <input type="date" id="ctp-deuda-fecha-fin" name="fecha_fin" <?php disabled(!$can_manage); ?>>
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button" <?php disabled(!$can_manage); ?>>Guardar deuda</button>
            </div>
            <div class="ctp-field ctp-field-full">
                <p class="ctp-form-error" id="ctp-deuda-form-error" role="alert" aria-live="polite"></p>
            </div>
        </form>
        <?php
        $form_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Agregar deuda',
            'Registra préstamos, gastos mensuales y compromisos únicos.',
            $form_html,
            'ctp-panel-form'
        );
        ?>
        <script>
            document.addEventListener('DOMContentLoaded', function () {
                var form = document.getElementById('ctp-deuda-form');
                if (!form) {
                    return;
                }
                var tipoSelect = document.getElementById('ctp-deuda-tipo');
                var helper = document.getElementById('ctp-deuda-tipo-helper');
                var errorEl = document.getElementById('ctp-deuda-form-error');
                var fields = {
                    total: {
                        wrapper: form.querySelector('.ctp-deuda-field-total'),
                        input: document.getElementById('ctp-deuda-monto-total'),
                        required: false,
                    },
                    mensual: {
                        wrapper: form.querySelector('.ctp-deuda-field-mensual'),
                        input: document.getElementById('ctp-deuda-monto-mensual'),
                        required: false,
                    },
                    cuotas: {
                        wrapper: form.querySelector('.ctp-deuda-field-cuotas'),
                        input: document.getElementById('ctp-deuda-cuotas'),
                        required: false,
                    },
                };

                Object.keys(fields).forEach(function (key) {
                    var input = fields[key].input;
                    if (input) {
                        input.dataset.ctpInitialDisabled = input.disabled ? 'true' : 'false';
                    }
                });

                var helperMessages = {
                    unico: 'Único: se registra solo para el mes de la fecha de inicio.',
                    mensual: 'Mensual: se repite cada mes desde inicio hasta fin (si se define).',
                    cuotas: 'Cuotas: se repite por N cuotas desde el mes de inicio.',
                };

                var setFieldState = function (field, visible, required) {
                    if (!field || !field.wrapper || !field.input) {
                        return;
                    }
                    field.wrapper.style.display = visible ? '' : 'none';
                    if (!visible) {
                        field.input.value = '';
                    }
                    if (field.input.dataset.ctpInitialDisabled !== 'true') {
                        field.input.disabled = !visible;
                    }
                    field.input.required = visible && required;
                };

                var applyTipo = function (tipo) {
                    if (!tipoSelect) {
                        return;
                    }
                    if (helper && helperMessages[tipo]) {
                        helper.textContent = helperMessages[tipo];
                    }
                    if (errorEl) {
                        errorEl.textContent = '';
                    }
                    if (tipo === 'unico') {
                        setFieldState(fields.total, true, true);
                        setFieldState(fields.mensual, false, false);
                        setFieldState(fields.cuotas, false, false);
                    } else if (tipo === 'mensual') {
                        setFieldState(fields.total, true, false);
                        setFieldState(fields.mensual, true, false);
                        setFieldState(fields.cuotas, false, false);
                    } else if (tipo === 'cuotas') {
                        setFieldState(fields.total, true, false);
                        setFieldState(fields.mensual, true, false);
                        setFieldState(fields.cuotas, true, true);
                    }
                };

                if (tipoSelect) {
                    tipoSelect.addEventListener('change', function (event) {
                        applyTipo(event.target.value);
                    });
                    applyTipo(tipoSelect.value);
                }

                form.addEventListener('submit', function (event) {
                    if (!tipoSelect) {
                        return;
                    }
                    var tipo = tipoSelect.value;
                    var mensajes = [];
                    var totalValue = fields.total.input ? fields.total.input.value.trim() : '';
                    var mensualValue = fields.mensual.input ? fields.mensual.input.value.trim() : '';
                    var cuotasValue = fields.cuotas.input ? fields.cuotas.input.value.trim() : '';

                    if (tipo === 'unico' && totalValue === '') {
                        mensajes.push('Ingresa el monto total para una deuda única.');
                    }
                    if (tipo === 'mensual' && mensualValue === '' && totalValue === '') {
                        mensajes.push('Ingresa el monto mensual o el monto total para una deuda mensual.');
                    }
                    if (tipo === 'cuotas' && cuotasValue === '') {
                        mensajes.push('Ingresa la cantidad de cuotas.');
                    }
                    if (tipo === 'cuotas' && mensualValue === '' && totalValue === '') {
                        mensajes.push('Ingresa el monto mensual o el monto total para una deuda en cuotas.');
                    }

                    if (mensajes.length > 0) {
                        event.preventDefault();
                        if (errorEl) {
                            errorEl.textContent = mensajes.join(' ');
                        }
                    } else if (errorEl) {
                        errorEl.textContent = '';
                    }
                });
            });
        </script>

        <?php
        ob_start();
        ?>
        <div class="ctp-table-wrap">
            <table class="ctp-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Categoría</th>
                        <th>Tipo</th>
                        <th class="ctp-table-text">Descripción</th>
                        <th>Monto del mes</th>
                        <th>Aplica</th>
                        <th>Estado pago</th>
                        <th class="ctp-actions-cell">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($deudas)) : ?>
                        <?php foreach ($deudas as $deuda) : ?>
                            <?php
                            $deuda_id = (int) $deuda->id;
                            $aplica = ctp_ordenes_deuda_aplica_periodo($deuda, $periodo);
                            $monto_mes = ctp_ordenes_deuda_get_monto_periodo($deuda, $periodo);
                            $estado_pago = $aplica ? (!empty($deuda->pago_id) ? 'Pagado' : 'Pendiente') : 'No aplica';
                            $is_factura_sync = !empty($deuda->source_type) && $deuda->source_type === 'factura_proveedor';
                            ?>
                            <tr>
                                <td data-label="ID"><?php echo esc_html($deuda_id); ?></td>
                                <td data-label="Categoría"><?php echo esc_html($categorias[$deuda->categoria] ?? $deuda->categoria); ?></td>
                                <td data-label="Tipo"><?php echo esc_html($tipos[$deuda->tipo] ?? $deuda->tipo); ?></td>
                                <td class="ctp-table-text" data-label="Descripción">
                                    <div class="ctp-deuda-desc">
                                        <span><?php echo esc_html($deuda->descripcion); ?></span>
                                        <?php if ($is_factura_sync) : ?>
                                            <span class="ctp-badge ctp-badge-sync">Factura proveedor</span>
                                        <?php endif; ?>
                                    </div>
                                </td>
                                <td data-label="Monto del mes">
                                    <?php echo esc_html($aplica ? 'Gs. ' . ctp_ordenes_format_currency_i18n($monto_mes, 0) : '—'); ?>
                                </td>
                                <td data-label="Aplica"><?php echo esc_html($aplica ? 'Sí' : 'No'); ?></td>
                                <td data-label="Estado pago"><?php echo esc_html($estado_pago); ?></td>
                                <td class="ctp-actions-cell" data-label="Acciones">
                                    <div class="ctp-actions">
                                        <?php if ($aplica) : ?>
                                            <form method="post" class="ctp-inline-form">
                                                <?php wp_nonce_field('ctp_deuda_toggle_pago', 'ctp_deuda_nonce'); ?>
                                                <input type="hidden" name="ctp_deuda_action" value="toggle_pago">
                                                <input type="hidden" name="deuda_id" value="<?php echo esc_attr($deuda_id); ?>">
                                                <input type="hidden" name="ctp_period" value="<?php echo esc_attr($periodo); ?>">
                                                <?php if (!empty($tab)) : ?>
                                                    <input type="hidden" name="ctp_tab" value="<?php echo esc_attr($tab); ?>">
                                                <?php endif; ?>
                                                <button type="submit" class="ctp-button ctp-button-secondary" <?php disabled(!$can_manage); ?>>
                                                    <?php echo esc_html(!empty($deuda->pago_id) ? 'Desmarcar' : 'Marcar pagado'); ?>
                                                </button>
                                            </form>
                                        <?php endif; ?>
                                        <form method="post" class="ctp-inline-form">
                                            <?php wp_nonce_field('ctp_deuda_delete', 'ctp_deuda_nonce'); ?>
                                            <input type="hidden" name="ctp_deuda_action" value="delete">
                                            <input type="hidden" name="deuda_id" value="<?php echo esc_attr($deuda_id); ?>">
                                            <input type="hidden" name="ctp_period" value="<?php echo esc_attr($periodo); ?>">
                                            <?php if (!empty($tab)) : ?>
                                                <input type="hidden" name="ctp_tab" value="<?php echo esc_attr($tab); ?>">
                                            <?php endif; ?>
                                            <button type="submit" class="ctp-button ctp-button-danger" onclick="return confirm('¿Seguro que deseas eliminar?')" <?php disabled(!$can_manage); ?>>Eliminar</button>
                                        </form>
                                    </div>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else : ?>
                        <tr>
                            <td colspan="8">No hay deudas registradas.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
        <?php
        $table_html = ob_get_clean();
        echo ctp_ordenes_render_panel(
            'Deudas registradas',
            'Controla lo que aplica al período seleccionado y registra pagos mensuales.',
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
add_shortcode('ctp_deudas_empresa', 'ctp_deudas_empresa_shortcode');

function ctp_liquidaciones_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_clientes = $wpdb->prefix . 'ctp_clientes';
    $table_liquidaciones = $wpdb->prefix . 'ctp_liquidaciones_cliente';
    $table_liquidacion_ordenes = $wpdb->prefix . 'ctp_liquidacion_ordenes';
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';

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

                                $total_real = (float) $wpdb->get_var(
                                    $wpdb->prepare(
                                        "SELECT COALESCE(SUM(order_total), 0)
                                         FROM (
                                            SELECT o.id,
                                                   COALESCE(SUM(i.total_item), o.total) AS order_total
                                            FROM {$table_ordenes} o
                                            INNER JOIN {$table_liquidacion_ordenes} lo ON lo.orden_id = o.id
                                            LEFT JOIN {$table_items} i ON i.orden_id = o.id
                                            WHERE lo.liquidacion_id = %d
                                            GROUP BY o.id
                                         ) AS ordenes",
                                        $liquidacion_id
                                    )
                                );

                                $wpdb->update(
                                    $table_liquidaciones,
                                    array('total' => $total_real),
                                    array('id' => $liquidacion_id),
                                    array('%f'),
                                    array('%d')
                                );

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
                    "SELECT o.id,
                            o.fecha,
                            o.numero_orden,
                            o.nombre_trabajo,
                            o.descripcion,
                            o.cantidad_chapas,
                            o.medida_chapa,
                            o.precio_unitario,
                            COALESCE(SUM(i.total_item), o.total) AS total,
                            CASE WHEN COUNT(i.id) > 0 THEN COUNT(i.id) ELSE 1 END AS items_count
                     FROM {$table_ordenes} o
                     INNER JOIN {$table_liquidacion_ordenes} lo ON lo.orden_id = o.id
                     LEFT JOIN {$table_items} i ON i.orden_id = o.id
                     WHERE lo.liquidacion_id = %d
                     GROUP BY o.id
                     ORDER BY o.fecha ASC, o.id ASC",
                    $liquidacion_id
                )
            );
        }
        $items_map = ctp_ordenes_get_items_map($ordenes_liquidacion);

        $back_url = remove_query_arg(array('ctp_liquidacion_id'));
        if (!empty($tab)) {
            $back_url = add_query_arg('ctp_tab', $tab, $back_url);
        }
        $has_ai_key = defined('OPENAI_API_KEY') && OPENAI_API_KEY !== '';
        $ai_generate_nonce = wp_create_nonce('ctp_ai_resumen_liquidacion');
        $ai_save_nonce = wp_create_nonce('ctp_ai_guardar_resumen_liquidacion');
        $initial_summary = $liquidacion ? (string) $liquidacion->nota : '';

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
                                    <th>Nombre del trabajo</th>
                                    <th>Descripción</th>
                                    <th>Trabajos</th>
                                    <th>Total</th>
                                    <th>Detalle</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php if (!empty($ordenes_liquidacion)) : ?>
                                    <?php foreach ($ordenes_liquidacion as $orden) : ?>
                                        <tr>
                                            <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                                            <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                                            <td data-label="Nombre del trabajo"><?php echo esc_html(ctp_ordenes_format_job_name($orden->nombre_trabajo ?? '')); ?></td>
                                            <td data-label="Descripción"><?php echo esc_html($orden->descripcion); ?></td>
                                            <td data-label="Trabajos"><?php echo esc_html(ctp_ordenes_format_items_count((int) $orden->items_count)); ?></td>
                                            <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                                            <td data-label="Detalle">
                                                <details class="ctp-details">
                                                    <summary class="ctp-button ctp-button-secondary">Ver ítems</summary>
                                                    <div class="ctp-details-panel">
                                                        <?php echo ctp_ordenes_render_items_table($items_map[(int) $orden->id] ?? array()); ?>
                                                    </div>
                                                </details>
                                            </td>
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
                    <div class="ctp-panel ctp-ai-panel">
                        <div class="ctp-panel-header">
                            <h4 class="ctp-panel-title">Resumen IA</h4>
                            <p class="ctp-panel-subtitle">Genera un resumen detallado con el estado real de las órdenes e ítems.</p>
                        </div>
                        <div class="ctp-panel-body ctp-ai-summary"
                             data-liquidacion-id="<?php echo esc_attr($liquidacion->id); ?>"
                             data-generate-nonce="<?php echo esc_attr($ai_generate_nonce); ?>"
                             data-save-nonce="<?php echo esc_attr($ai_save_nonce); ?>">
                            <?php if (!$has_ai_key) : ?>
                                <div class="ctp-alert ctp-alert-warning">La API key de OpenAI no está configurada. Agrega OPENAI_API_KEY en wp-config.php.</div>
                            <?php endif; ?>
                            <div class="ctp-ai-actions">
                                <button type="button" class="ctp-button ctp-button-secondary ctp-ai-generate" <?php disabled(!$has_ai_key); ?>>Generar resumen con IA</button>
                                <button type="button" class="ctp-button ctp-ai-save" <?php disabled(trim($initial_summary) === ''); ?>>Guardar resumen como nota</button>
                            </div>
                            <p class="ctp-ai-status" role="status" aria-live="polite"></p>
                            <div class="ctp-ai-preview" aria-live="polite"></div>
                            <textarea class="ctp-ai-text" rows="6" placeholder="El resumen aparecerá aquí. Puedes editarlo antes de guardar o copiar."><?php echo esc_textarea($initial_summary); ?></textarea>
                        </div>
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
                <?php $preview_items_map = ctp_ordenes_get_items_map($preview_orders); ?>
                <div class="ctp-table-wrap">
                    <table class="ctp-table">
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>Nº Orden</th>
                                <th>Nombre del trabajo</th>
                                <th>Descripción</th>
                                <th>Total</th>
                                <th>Trabajos</th>
                                <th>Detalle</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($preview_orders as $orden) : ?>
                                <tr>
                                    <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                                    <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                                    <td data-label="Nombre del trabajo"><?php echo esc_html(ctp_ordenes_format_job_name($orden->nombre_trabajo ?? '')); ?></td>
                                    <td data-label="Descripción"><?php echo esc_html($orden->descripcion); ?></td>
                                    <td data-label="Total"><?php echo esc_html('Gs. ' . ctp_ordenes_format_currency($orden->total)); ?></td>
                                    <td data-label="Trabajos"><?php echo esc_html(ctp_ordenes_format_items_count((int) $orden->items_count)); ?></td>
                                    <td data-label="Detalle">
                                        <details class="ctp-details">
                                            <summary class="ctp-button ctp-button-secondary">Ver ítems</summary>
                                            <div class="ctp-details-panel">
                                                <?php echo ctp_ordenes_render_items_table($preview_items_map[(int) $orden->id] ?? array()); ?>
                                            </div>
                                        </details>
                                    </td>
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

function ctp_ordenes_ajax_generate_liquidacion_summary() {
    if (!ctp_ordenes_user_can_manage()) {
        wp_send_json_error(array('message' => 'No tienes permisos para generar el resumen.'), 403);
    }

    check_ajax_referer('ctp_ai_resumen_liquidacion', 'nonce');

    $liquidacion_id = isset($_POST['liquidacion_id']) ? absint($_POST['liquidacion_id']) : 0;
    if ($liquidacion_id <= 0) {
        wp_send_json_error(array('message' => 'No se recibió una liquidación válida.'), 400);
    }

    if (!defined('OPENAI_API_KEY') || OPENAI_API_KEY === '') {
        wp_send_json_error(array('message' => 'La API key de OpenAI no está configurada en wp-config.php.'), 400);
    }

    global $wpdb;
    $table_liquidaciones = $wpdb->prefix . 'ctp_liquidaciones_cliente';
    $table_liquidacion_ordenes = $wpdb->prefix . 'ctp_liquidacion_ordenes';
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';
    $table_items = $wpdb->prefix . 'ctp_ordenes_items';
    $table_clientes = $wpdb->prefix . 'ctp_clientes';

    $liquidacion = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT f.*, COALESCE(c.nombre, '') AS cliente_nombre
             FROM {$table_liquidaciones} f
             LEFT JOIN {$table_clientes} c ON f.cliente_id = c.id
             WHERE f.id = %d",
            $liquidacion_id
        )
    );

    if (!$liquidacion) {
        wp_send_json_error(array('message' => 'La liquidación indicada no existe.'), 404);
    }

    $ordenes = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT o.id,
                    o.fecha,
                    o.numero_orden,
                    o.nombre_trabajo,
                    COALESCE(SUM(i.total_item), o.total) AS total,
                    COUNT(i.id) AS items_count
             FROM {$table_ordenes} o
             INNER JOIN {$table_liquidacion_ordenes} lo ON lo.orden_id = o.id
             LEFT JOIN {$table_items} i ON i.orden_id = o.id
             WHERE lo.liquidacion_id = %d
             GROUP BY o.id
             ORDER BY o.fecha ASC, o.id ASC",
            $liquidacion_id
        )
    );

    $items_map = ctp_ordenes_get_items_map_for_ai($ordenes);
    $ai_data = ctp_ordenes_build_liquidacion_ai_data($liquidacion, $ordenes, $items_map);
    $prompt = ctp_ordenes_build_liquidacion_ai_prompt($liquidacion, $ordenes, $ai_data);

    $request_body = array(
        'model' => 'gpt-4o-mini',
        'messages' => array(
            array(
                'role' => 'system',
                'content' => 'Eres un asistente que redacta resúmenes comerciales claros para liquidaciones.',
            ),
            array(
                'role' => 'user',
                'content' => $prompt,
            ),
        ),
        'temperature' => 0.3,
        'max_tokens' => 400,
    );

    $response = wp_remote_post(
        'https://api.openai.com/v1/chat/completions',
        array(
            'headers' => array(
                'Authorization' => 'Bearer ' . OPENAI_API_KEY,
                'Content-Type' => 'application/json',
            ),
            'timeout' => 30,
            'body' => wp_json_encode($request_body),
        )
    );

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => 'No se pudo contactar con OpenAI. ' . $response->get_error_message()), 500);
    }

    $status = wp_remote_retrieve_response_code($response);
    $body = wp_remote_retrieve_body($response);
    if ($status < 200 || $status >= 300) {
        wp_send_json_error(array('message' => 'OpenAI devolvió un error al generar el resumen.'), $status);
    }

    $data = json_decode($body, true);
    $summary = $data['choices'][0]['message']['content'] ?? '';
    $summary = trim((string) $summary);
    if ($summary === '') {
        wp_send_json_error(array('message' => 'No se recibió un resumen válido.'), 500);
    }

    wp_send_json_success(
        array(
            'text' => $summary,
            'data' => $ai_data,
        )
    );
}
add_action('wp_ajax_ctp_generar_resumen_liquidacion', 'ctp_ordenes_ajax_generate_liquidacion_summary');

function ctp_ordenes_ajax_save_liquidacion_summary() {
    if (!ctp_ordenes_user_can_manage()) {
        wp_send_json_error(array('message' => 'No tienes permisos para guardar la nota.'), 403);
    }

    check_ajax_referer('ctp_ai_guardar_resumen_liquidacion', 'nonce');

    $liquidacion_id = isset($_POST['liquidacion_id']) ? absint($_POST['liquidacion_id']) : 0;
    if ($liquidacion_id <= 0) {
        wp_send_json_error(array('message' => 'No se recibió una liquidación válida.'), 400);
    }

    $summary = isset($_POST['summary']) ? sanitize_textarea_field(wp_unslash($_POST['summary'])) : '';
    if ($summary === '') {
        wp_send_json_error(array('message' => 'El resumen está vacío.'), 400);
    }

    global $wpdb;
    $table_liquidaciones = $wpdb->prefix . 'ctp_liquidaciones_cliente';

    $updated = $wpdb->update(
        $table_liquidaciones,
        array('nota' => $summary),
        array('id' => $liquidacion_id),
        array('%s'),
        array('%d')
    );

    if ($updated === false) {
        wp_send_json_error(array('message' => 'No se pudo guardar la nota.'), 500);
    }

    wp_send_json_success(array('message' => 'Resumen guardado en la nota de la liquidación.'));
}
add_action('wp_ajax_ctp_guardar_resumen_liquidacion', 'ctp_ordenes_ajax_save_liquidacion_summary');

function ctp_dashboard_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    if (isset($_GET['ctp_tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['ctp_tab']));
    } elseif (isset($_GET['tab'])) {
        $tab = sanitize_key(wp_unslash($_GET['tab']));
    } else {
        $tab = 'ordenes';
    }

    if (!in_array($tab, array('ordenes', 'proveedores', 'facturas', 'liquidaciones', 'clientes', 'deudas'), true)) {
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
        'deudas' => 'Deudas empresa',
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
                <?php elseif ($tab === 'deudas') : ?>
                    <?php echo do_shortcode('[ctp_deudas_empresa]'); ?>
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
