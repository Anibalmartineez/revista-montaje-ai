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

function gc_calculate_estado_documento(float $total, float $pagado): string {
    if ($pagado <= 0) {
        return 'pendiente';
    }
    if ($pagado + 0.01 >= $total) {
        return 'pagado';
    }
    return 'parcial';
}

function gc_recalculate_documento_estado(int $documento_id): void {
    global $wpdb;
    $documentos_table = gc_get_table('gc_documentos');
    $pagos_table = gc_get_table('gc_documento_pagos');

    $documento = $wpdb->get_row($wpdb->prepare("SELECT id, total FROM {$documentos_table} WHERE id = %d", $documento_id), ARRAY_A);
    if (!$documento) {
        return;
    }

    $pagado = (float) $wpdb->get_var($wpdb->prepare("SELECT COALESCE(SUM(monto), 0) FROM {$pagos_table} WHERE documento_id = %d", $documento_id));
    $saldo = max(0, (float) $documento['total'] - $pagado);
    $estado = gc_calculate_estado_documento((float) $documento['total'], $pagado);

    $wpdb->update(
        $documentos_table,
        array(
            'monto_pagado' => $pagado,
            'saldo' => $saldo,
            'estado' => $estado,
            'updated_at' => gc_now(),
        ),
        array('id' => $documento_id),
        array('%f', '%f', '%s', '%s'),
        array('%d')
    );
}

function gc_recalculate_deuda_estado(int $deuda_id): void {
    global $wpdb;
    $deudas_table = gc_get_table('gc_deudas');
    $pagos_table = gc_get_table('gc_deuda_pagos');

    $deuda = $wpdb->get_row(
        $wpdb->prepare("SELECT id, monto, tipo_deuda, total_calculado FROM {$deudas_table} WHERE id = %d", $deuda_id),
        ARRAY_A
    );
    if (!$deuda) {
        return;
    }

    $tipo_deuda = gc_get_deuda_tipo($deuda);
    if ($tipo_deuda === 'prestamo') {
        gc_recalculate_prestamo_estado($deuda_id);
        return;
    }
    if ($tipo_deuda !== 'unica') {
        return;
    }

    $pagado = (float) $wpdb->get_var($wpdb->prepare("SELECT COALESCE(SUM(monto), 0) FROM {$pagos_table} WHERE deuda_id = %d", $deuda_id));
    $saldo = max(0, (float) $deuda['monto'] - $pagado);
    $estado = ($pagado + 0.01 >= (float) $deuda['monto']) ? 'pagada' : 'pendiente';

    $wpdb->update(
        $deudas_table,
        array(
            'monto_pagado' => $pagado,
            'saldo' => $saldo,
            'estado' => $estado,
            'updated_at' => gc_now(),
        ),
        array('id' => $deuda_id),
        array('%f', '%f', '%s', '%s'),
        array('%d')
    );
}

function gc_get_deuda_tipo(array $deuda): string {
    if (!empty($deuda['tipo_deuda'])) {
        return $deuda['tipo_deuda'];
    }
    $frecuencia = $deuda['frecuencia'] ?? '';
    if ($frecuencia === 'unico') {
        return 'unica';
    }
    return 'recurrente';
}

function gc_get_periodo_actual(): string {
    return wp_date('Y-m', current_time('timestamp'));
}

function gc_calculate_vencimiento_recurrente(array $deuda, string $periodo): string {
    $parts = explode('-', $periodo);
    $year = (int) ($parts[0] ?? wp_date('Y'));
    $month = (int) ($parts[1] ?? wp_date('m'));
    $month = max(1, min(12, $month));
    $max_day = (int) wp_date('t', strtotime(sprintf('%04d-%02d-01', $year, $month)));
    $frecuencia = $deuda['frecuencia'] ?? 'mensual';

    if ($frecuencia === 'semanal') {
        $day_week = isset($deuda['dia_semana']) ? (int) $deuda['dia_semana'] : 0;
        $period_start = new DateTimeImmutable(sprintf('%04d-%02d-01', $year, $month));
        $period_end = new DateTimeImmutable(sprintf('%04d-%02d-%02d', $year, $month, $max_day));
        $reference = new DateTimeImmutable(wp_date('Y-m-d', current_time('timestamp')));
        if ($reference < $period_start || $reference > $period_end) {
            $reference = $period_start;
        }
        $current_dow = (int) $reference->format('w');
        $days_ahead = ($day_week - $current_dow + 7) % 7;
        $target = $reference->modify('+' . $days_ahead . ' days');
        if ($target > $period_end) {
            $target = $period_end;
            while ((int) $target->format('w') !== $day_week) {
                $target = $target->modify('-1 day');
            }
        }
        return $target->format('Y-m-d');
    }

    $day = isset($deuda['dia_vencimiento']) ? (int) $deuda['dia_vencimiento'] : 1;
    $day = max(1, min($day, $max_day));

    return sprintf('%04d-%02d-%02d', $year, $month, $day);
}

function gc_get_deuda_instancia(int $deuda_id, string $periodo): ?array {
    global $wpdb;
    $instancias_table = gc_get_table('gc_deuda_instancias');
    $instancia = $wpdb->get_row(
        $wpdb->prepare("SELECT * FROM {$instancias_table} WHERE deuda_id = %d AND periodo = %s", $deuda_id, $periodo),
        ARRAY_A
    );
    return $instancia ?: null;
}

function gc_ensure_recurrente_instancia(array $deuda, ?string $periodo = null): array {
    global $wpdb;
    $instancias_table = gc_get_table('gc_deuda_instancias');
    $periodo = $periodo ?: gc_get_periodo_actual();

    $instancia = gc_get_deuda_instancia((int) $deuda['id'], $periodo);
    if ($instancia) {
        return $instancia;
    }

    $vencimiento = gc_calculate_vencimiento_recurrente($deuda, $periodo);
    $monto = isset($deuda['monto']) ? (float) $deuda['monto'] : 0;
    $wpdb->insert(
        $instancias_table,
        array(
            'deuda_id' => (int) $deuda['id'],
            'periodo' => $periodo,
            'vencimiento' => $vencimiento,
            'monto' => $monto,
            'monto_pagado' => 0,
            'saldo' => $monto,
            'estado' => 'pendiente',
            'created_at' => gc_now(),
        ),
        array('%d', '%s', '%s', '%f', '%f', '%f', '%s', '%s')
    );

    return gc_get_deuda_instancia((int) $deuda['id'], $periodo) ?: array();
}

function gc_generate_prestamo_instancias(array $deuda): void {
    global $wpdb;
    $instancias_table = gc_get_table('gc_deuda_instancias');

    $cuotas_total = isset($deuda['cuotas_total']) ? (int) $deuda['cuotas_total'] : 0;
    $cuota_monto = isset($deuda['cuota_monto']) ? (float) $deuda['cuota_monto'] : 0;
    if ($cuotas_total <= 0 || $cuota_monto <= 0) {
        return;
    }

    $fecha_inicio = !empty($deuda['fecha_inicio']) ? $deuda['fecha_inicio'] : wp_date('Y-m-d', current_time('timestamp'));
    $start_date = new DateTimeImmutable($fecha_inicio);
    $start_day = (int) $start_date->format('d');

    $existing = $wpdb->get_col(
        $wpdb->prepare("SELECT periodo FROM {$instancias_table} WHERE deuda_id = %d", (int) $deuda['id'])
    );
    $existing_map = array_fill_keys($existing, true);

    for ($i = 0; $i < $cuotas_total; $i++) {
        $current = $start_date->modify('+' . $i . ' months');
        $year = (int) $current->format('Y');
        $month = (int) $current->format('m');
        $max_day = (int) wp_date('t', strtotime(sprintf('%04d-%02d-01', $year, $month)));
        $day = min($start_day, $max_day);
        $vencimiento = sprintf('%04d-%02d-%02d', $year, $month, $day);
        $periodo = $current->format('Y-m');

        if (isset($existing_map[$periodo])) {
            continue;
        }

        $wpdb->insert(
            $instancias_table,
            array(
                'deuda_id' => (int) $deuda['id'],
                'periodo' => $periodo,
                'vencimiento' => $vencimiento,
                'monto' => $cuota_monto,
                'monto_pagado' => 0,
                'saldo' => $cuota_monto,
                'estado' => 'pendiente',
                'created_at' => gc_now(),
            ),
            array('%d', '%s', '%s', '%f', '%f', '%f', '%s', '%s')
        );
    }
}

function gc_get_prestamo_instancia_actual(array $deuda): ?array {
    global $wpdb;
    $instancias_table = gc_get_table('gc_deuda_instancias');
    $periodo = gc_get_periodo_actual();

    $instancia = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT * FROM {$instancias_table} WHERE deuda_id = %d AND periodo = %s",
            (int) $deuda['id'],
            $periodo
        ),
        ARRAY_A
    );
    if ($instancia && $instancia['estado'] !== 'pagada') {
        return $instancia;
    }

    $instancia = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT * FROM {$instancias_table} WHERE deuda_id = %d AND estado != 'pagada' ORDER BY vencimiento ASC LIMIT 1",
            (int) $deuda['id']
        ),
        ARRAY_A
    );

    return $instancia ?: null;
}

function gc_apply_pago_a_instancia(array $instancia, float $monto): void {
    global $wpdb;
    $instancias_table = gc_get_table('gc_deuda_instancias');
    $monto = max(0, $monto);
    $nuevo_pagado = (float) $instancia['monto_pagado'] + $monto;
    $saldo = max(0, (float) $instancia['monto'] - $nuevo_pagado);
    $estado = 'pendiente';
    if ($nuevo_pagado > 0 && $saldo > 0) {
        $estado = 'parcial';
    } elseif ($saldo <= 0) {
        $estado = 'pagada';
    }

    $wpdb->update(
        $instancias_table,
        array(
            'monto_pagado' => $nuevo_pagado,
            'saldo' => $saldo,
            'estado' => $estado,
        ),
        array('id' => (int) $instancia['id']),
        array('%f', '%f', '%s'),
        array('%d')
    );
}

function gc_recalculate_prestamo_estado(int $deuda_id): array {
    global $wpdb;
    $deudas_table = gc_get_table('gc_deudas');
    $instancias_table = gc_get_table('gc_deuda_instancias');

    $deuda = $wpdb->get_row(
        $wpdb->prepare("SELECT id, total_calculado, cuotas_total, cuota_monto FROM {$deudas_table} WHERE id = %d", $deuda_id),
        ARRAY_A
    );
    if (!$deuda) {
        return array();
    }

    $total_calculado = isset($deuda['total_calculado']) && $deuda['total_calculado'] !== null
        ? (float) $deuda['total_calculado']
        : max(0, (int) $deuda['cuotas_total'] * (float) $deuda['cuota_monto']);

    $pagado = (float) $wpdb->get_var(
        $wpdb->prepare("SELECT COALESCE(SUM(monto_pagado), 0) FROM {$instancias_table} WHERE deuda_id = %d", $deuda_id)
    );
    $saldo = max(0, $total_calculado - $pagado);
    $estado = 'pendiente';
    if ($pagado > 0 && $saldo > 0) {
        $estado = 'parcial';
    } elseif ($saldo <= 0 && $total_calculado > 0) {
        $estado = 'pagada';
    }

    $wpdb->update(
        $deudas_table,
        array(
            'monto_pagado' => $pagado,
            'saldo' => $saldo,
            'estado' => $estado,
            'total_calculado' => $total_calculado,
            'updated_at' => gc_now(),
        ),
        array('id' => $deuda_id),
        array('%f', '%f', '%s', '%f', '%s'),
        array('%d')
    );

    return array(
        'total_calculado' => $total_calculado,
        'monto_pagado' => $pagado,
        'saldo' => $saldo,
        'estado' => $estado,
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

function gc_get_deudas_options(bool $solo_activas = false): array {
    global $wpdb;
    $table = gc_get_table('gc_deudas');
    if ($solo_activas) {
        $rows = $wpdb->get_results("SELECT id, nombre FROM {$table} WHERE activo = 1 ORDER BY nombre ASC", ARRAY_A);
    } else {
        $rows = $wpdb->get_results("SELECT id, nombre FROM {$table} ORDER BY activo DESC, nombre ASC", ARRAY_A);
    }
    $options = array('' => 'Sin deuda');
    foreach ($rows as $row) {
        $options[$row['id']] = $row['nombre'];
    }
    return $options;
}
