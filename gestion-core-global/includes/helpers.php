<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_user_can_manage(): bool {
    return current_user_can('manage_options');
}

function gc_guard_manage_access(): void {
    if (!gc_user_can_manage()) {
        wp_die('No tienes permisos para acceder a este panel.', 'Acceso denegado', array('response' => 403));
    }
}

function gc_get_table(string $name): string {
    global $wpdb;
    return $wpdb->prefix . $name;
}

function gc_now(): string {
    return current_time('mysql');
}

function gc_format_currency($amount): string {
    $amount = is_numeric($amount) ? (float) $amount : 0;
    return number_format($amount, 2, ',', '.');
}

function gc_parse_date(?string $value): string {
    $value = $value ? sanitize_text_field($value) : '';
    if (!$value) {
        return wp_date('Y-m-d', current_time('timestamp'));
    }
    $timestamp = strtotime($value);
    if (!$timestamp) {
        return wp_date('Y-m-d', current_time('timestamp'));
    }
    return wp_date('Y-m-d', $timestamp);
}

function gc_csv_safe($value): string {
    $string = (string) $value;
    $string = str_replace(array("\r\n", "\r", "\n"), ' ', $string);
    if ($string !== '' && in_array($string[0], array('=', '+', '-', '@'), true)) {
        $string = "'" . $string;
    }
    return $string;
}

function gc_get_notice(): array {
    $message = isset($_GET['gc_notice']) ? sanitize_text_field(wp_unslash($_GET['gc_notice'])) : '';
    $status = isset($_GET['gc_status']) ? sanitize_text_field(wp_unslash($_GET['gc_status'])) : '';
    return array($message, $status);
}

function gc_render_notice(): string {
    list($message, $status) = gc_get_notice();
    if (!$message) {
        return '';
    }
    $class = 'gc-alert';
    if ($status === 'success') {
        $class .= ' is-success';
    } elseif ($status === 'warning') {
        $class .= ' is-warning';
    } elseif ($status === 'error') {
        $class .= ' is-error';
    }

    return '<div class="' . esc_attr($class) . '">' . esc_html($message) . '</div>';
}

function gc_wrap_panel(string $title, string $subtitle, string $content): string {
    $html = '<div class="gc-panel">';
    $html .= '<div class="gc-panel-header">';
    $html .= '<h3 class="gc-panel-title">' . esc_html($title) . '</h3>';
    if ($subtitle) {
        $html .= '<p class="gc-panel-subtitle">' . esc_html($subtitle) . '</p>';
    }
    $html .= '</div>';
    $html .= '<div class="gc-panel-body">' . $content . '</div>';
    $html .= '</div>';
    return $html;
}

function gc_field_value(array $data, string $key, $fallback = '') {
    return isset($data[$key]) ? $data[$key] : $fallback;
}

function gc_select_options(array $options, $selected): string {
    $html = '';
    foreach ($options as $value => $label) {
        $is_selected = ((string) $value === (string) $selected) ? ' selected' : '';
        $html .= '<option value="' . esc_attr($value) . '"' . $is_selected . '>' . esc_html($label) . '</option>';
    }
    return $html;
}

function gc_build_back_url(): string {
    $referer = wp_get_referer();
    return $referer ? $referer : home_url('/');
}

function gc_redirect_with_notice(string $message, string $status = 'success'): void {
    $url = add_query_arg(
        array(
            'gc_notice' => rawurlencode($message),
            'gc_status' => $status,
        ),
        gc_build_back_url()
    );
    wp_safe_redirect($url);
    exit;
}

function gc_get_date_range_from_request(): array {
    $start = isset($_GET['gc_start']) ? sanitize_text_field(wp_unslash($_GET['gc_start'])) : '';
    $end = isset($_GET['gc_end']) ? sanitize_text_field(wp_unslash($_GET['gc_end'])) : '';
    if (!$start || !$end) {
        $start = gmdate('Y-m-01');
        $end = gmdate('Y-m-t');
    }
    return array($start, $end);
}

function gc_get_movimientos_totals(string $start, string $end): array {
    global $wpdb;
    $table = gc_get_table('gc_movimientos');
    $results = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT
                SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE 0 END) as ingresos,
                SUM(CASE WHEN tipo = 'egreso' THEN monto ELSE 0 END) as egresos
            FROM {$table}
            WHERE fecha BETWEEN %s AND %s",
            $start,
            $end
        ),
        ARRAY_A
    );

    $ingresos = isset($results['ingresos']) ? (float) $results['ingresos'] : 0;
    $egresos = isset($results['egresos']) ? (float) $results['egresos'] : 0;

    return array(
        'ingresos' => $ingresos,
        'egresos' => $egresos,
        'neto' => $ingresos - $egresos,
    );
}

function gc_get_clientes_options(): array {
    global $wpdb;
    $table = gc_get_table('gc_clientes');
    $rows = $wpdb->get_results("SELECT id, nombre FROM {$table} ORDER BY nombre ASC", ARRAY_A);
    $options = array('' => 'Sin cliente');
    foreach ($rows as $row) {
        $options[$row['id']] = $row['nombre'];
    }
    return $options;
}

function gc_get_proveedores_options(): array {
    global $wpdb;
    $table = gc_get_table('gc_proveedores');
    $rows = $wpdb->get_results("SELECT id, nombre FROM {$table} ORDER BY nombre ASC", ARRAY_A);
    $options = array('' => 'Sin proveedor');
    foreach ($rows as $row) {
        $options[$row['id']] = $row['nombre'];
    }
    return $options;
}

function gc_get_documentos_options(string $tipo = ''): array {
    global $wpdb;
    $table = gc_get_table('gc_documentos');
    if ($tipo) {
        $rows = $wpdb->get_results($wpdb->prepare("SELECT id, numero FROM {$table} WHERE tipo = %s ORDER BY fecha DESC", $tipo), ARRAY_A);
    } else {
        $rows = $wpdb->get_results("SELECT id, numero FROM {$table} ORDER BY fecha DESC", ARRAY_A);
    }
    $options = array('' => 'Sin documento');
    foreach ($rows as $row) {
        $options[$row['id']] = $row['numero'];
    }
    return $options;
}
