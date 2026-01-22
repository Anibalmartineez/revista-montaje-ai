<?php

if (!defined('ABSPATH')) {
    exit;
}

function ctp_get_table(string $name): string {
    global $wpdb;
    return $wpdb->prefix . $name;
}

function ctp_get_clientes_options(): array {
    if (function_exists('gc_api_get_client_options')) {
        $options = gc_api_get_client_options();
        if ($options) {
            return array('' => 'Seleccionar...') + $options;
        }
    }

    if (!function_exists('gc_get_table')) {
        return array();
    }

    global $wpdb;
    $table = gc_get_table('gc_clientes');
    $rows = $wpdb->get_results("SELECT id, nombre FROM {$table} ORDER BY nombre ASC", ARRAY_A);
    $options = array('' => 'Seleccionar...');

    foreach ($rows as $row) {
        $options[$row['id']] = $row['nombre'];
    }

    return $options;
}

function ctp_core_api_ready(): bool {
    return defined('GC_CORE_GLOBAL_API_VERSION')
        && function_exists('gc_api_is_ready')
        && gc_api_is_ready()
        && version_compare(GC_CORE_GLOBAL_API_VERSION, '1.0.0', '>=');
}

function ctp_render_core_api_notice(): string {
    if (ctp_core_api_ready()) {
        return '';
    }

    return '<div class="ctp-alert is-warning">Core Global activo pero la API mínima no está disponible. Actualiza el core.</div>';
}

function ctp_get_order_items(int $orden_id): array {
    global $wpdb;
    $items_table = ctp_get_table('ctp_orden_items');

    return $wpdb->get_results(
        $wpdb->prepare("SELECT * FROM {$items_table} WHERE orden_id = %d ORDER BY id ASC", $orden_id),
        ARRAY_A
    );
}

function ctp_get_date_range_from_request(string $start_key, string $end_key): array {
    $start = isset($_GET[$start_key]) ? sanitize_text_field(wp_unslash($_GET[$start_key])) : '';
    $end = isset($_GET[$end_key]) ? sanitize_text_field(wp_unslash($_GET[$end_key])) : '';
    if (!$start || !$end) {
        $start = gmdate('Y-m-01');
        $end = gmdate('Y-m-t');
    }
    return array($start, $end);
}

function ctp_redirect_with_notice(string $message, string $status = 'success'): void {
    if (function_exists('gc_redirect_with_notice')) {
        gc_redirect_with_notice($message, $status);
    }

    $url = add_query_arg(
        array(
            'gc_notice' => rawurlencode($message),
            'gc_status' => $status,
        ),
        wp_get_referer() ?: home_url('/')
    );
    wp_safe_redirect($url);
    exit;
}

function ctp_format_currency($amount): string {
    if (function_exists('gc_format_currency')) {
        return gc_format_currency($amount);
    }
    $amount = is_numeric($amount) ? (float) $amount : 0;
    return number_format($amount, 2, ',', '.');
}
