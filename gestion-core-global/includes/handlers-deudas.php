<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_gc_save_deuda', 'gc_handle_save_deuda');
add_action('admin_post_gc_delete_deuda', 'gc_handle_delete_deuda');
add_action('admin_post_gc_add_deuda_pago', 'gc_handle_add_deuda_pago');

function gc_handle_save_deuda(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_save_deuda');

    global $wpdb;
    $table = gc_get_table('gc_deudas');

    $tipo_deuda = sanitize_text_field(wp_unslash($_POST['tipo_deuda'] ?? 'recurrente'));
    if (!in_array($tipo_deuda, array('unica', 'recurrente', 'prestamo'), true)) {
        $tipo_deuda = 'recurrente';
    }

    $monto = (float) str_replace(',', '.', wp_unslash($_POST['monto'] ?? 0));
    $cuotas_total = absint($_POST['cuotas_total'] ?? 0);
    $cuota_monto = (float) str_replace(',', '.', wp_unslash($_POST['cuota_monto'] ?? 0));
    $fecha_inicio_input = sanitize_text_field(wp_unslash($_POST['fecha_inicio'] ?? ''));
    $fecha_inicio = $fecha_inicio_input ? gc_parse_date($fecha_inicio_input) : wp_date('Y-m-d', current_time('timestamp'));

    $data = array(
        'nombre' => sanitize_text_field(wp_unslash($_POST['nombre'] ?? '')),
        'categoria' => sanitize_text_field(wp_unslash($_POST['categoria'] ?? '')) ?: null,
        'monto' => $monto,
        'tipo_deuda' => $tipo_deuda,
        'frecuencia' => sanitize_text_field(wp_unslash($_POST['frecuencia'] ?? 'mensual')) ?: null,
        'dia_sugerido' => absint($_POST['dia_vencimiento'] ?? 0) ?: null,
        'vencimiento' => null,
        'dia_vencimiento' => absint($_POST['dia_vencimiento'] ?? 0) ?: null,
        'dia_semana' => isset($_POST['dia_semana']) ? (int) $_POST['dia_semana'] : null,
        'cuotas_total' => $cuotas_total ?: null,
        'cuota_monto' => $cuota_monto ?: null,
        'fecha_inicio' => $fecha_inicio ?: null,
        'total_calculado' => null,
        'activo' => isset($_POST['activo']) ? 1 : 0,
        'notas' => sanitize_textarea_field(wp_unslash($_POST['notas'] ?? '')),
        'updated_at' => gc_now(),
    );

    if (!$data['nombre']) {
        gc_redirect_with_notice('El nombre de la deuda es obligatorio.', 'error');
    }

    if ($tipo_deuda === 'unica') {
        $vencimiento_input = sanitize_text_field(wp_unslash($_POST['vencimiento'] ?? ''));
        $data['vencimiento'] = $vencimiento_input ? gc_parse_date($vencimiento_input) : null;
        $data['frecuencia'] = null;
        $data['dia_sugerido'] = null;
        $data['dia_vencimiento'] = null;
        $data['dia_semana'] = null;
        $data['cuotas_total'] = null;
        $data['cuota_monto'] = null;
        $data['fecha_inicio'] = null;
        $data['total_calculado'] = null;
    } elseif ($tipo_deuda === 'prestamo') {
        $data['frecuencia'] = null;
        $data['vencimiento'] = null;
        $data['dia_sugerido'] = null;
        $data['dia_vencimiento'] = null;
        $data['dia_semana'] = null;
        $data['cuotas_total'] = $cuotas_total ?: null;
        $data['cuota_monto'] = $cuota_monto ?: null;
        $data['fecha_inicio'] = $fecha_inicio;
        $data['total_calculado'] = ($cuotas_total > 0 && $cuota_monto > 0) ? ($cuotas_total * $cuota_monto) : 0;
        $data['monto'] = $data['total_calculado'];
    } else {
        $data['vencimiento'] = null;
        $data['cuotas_total'] = null;
        $data['cuota_monto'] = null;
        $data['fecha_inicio'] = null;
        $data['total_calculado'] = null;
        if ($data['frecuencia'] === 'semanal') {
            $data['dia_vencimiento'] = null;
            $data['dia_sugerido'] = null;
        } else {
            $data['dia_semana'] = null;
            $data['dia_sugerido'] = $data['dia_vencimiento'];
        }
    }

    $id = absint($_POST['deuda_id'] ?? 0);
    if ($id) {
        $wpdb->update(
            $table,
            $data,
            array('id' => $id),
            array('%s', '%s', '%f', '%s', '%s', '%d', '%s', '%d', '%d', '%d', '%f', '%s', '%f', '%d', '%s', '%s'),
            array('%d')
        );
        if ($tipo_deuda === 'prestamo') {
            $deuda = array_merge($data, array('id' => $id));
            gc_generate_prestamo_instancias($deuda);
            gc_recalculate_prestamo_estado($id);
        } elseif ($tipo_deuda === 'recurrente') {
            $deuda = array_merge($data, array('id' => $id));
            gc_ensure_recurrente_instancia($deuda);
        } else {
            gc_recalculate_deuda_estado($id);
        }
        gc_redirect_with_notice('Deuda actualizada.', 'success');
    }

    $data['estado'] = 'pendiente';
    $data['monto_pagado'] = 0;
    $data['saldo'] = $data['monto'];
    $data['created_at'] = gc_now();
    $wpdb->insert(
        $table,
        $data,
        array('%s', '%s', '%f', '%s', '%s', '%d', '%s', '%d', '%d', '%d', '%f', '%s', '%f', '%d', '%s', '%s', '%s', '%f', '%f', '%s')
    );
    $new_id = (int) $wpdb->insert_id;
    if ($new_id) {
        $deuda = array_merge($data, array('id' => $new_id));
        if ($tipo_deuda === 'prestamo') {
            gc_generate_prestamo_instancias($deuda);
            gc_recalculate_prestamo_estado($new_id);
        } elseif ($tipo_deuda === 'recurrente') {
            gc_ensure_recurrente_instancia($deuda);
        }
    }
    gc_redirect_with_notice('Deuda creada.', 'success');
}

function gc_handle_delete_deuda(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_delete_deuda');

    global $wpdb;
    $table = gc_get_table('gc_deudas');
    $id = absint($_POST['deuda_id'] ?? 0);

    if ($id) {
        $wpdb->delete($table, array('id' => $id), array('%d'));
        gc_redirect_with_notice('Deuda eliminada.', 'success');
    }

    gc_redirect_with_notice('Deuda no encontrada.', 'error');
}

function gc_handle_add_deuda_pago(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_add_deuda_pago');

    global $wpdb;
    $deudas_table = gc_get_table('gc_deudas');
    $pagos_table = gc_get_table('gc_deuda_pagos');

    $deuda_id = absint($_POST['deuda_id'] ?? 0);
    $monto = (float) str_replace(',', '.', wp_unslash($_POST['monto'] ?? 0));
    $fecha = gc_parse_date($_POST['fecha_pago'] ?? '');
    $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

    if (!$deuda_id || $monto <= 0) {
        gc_redirect_with_notice('Selecciona una deuda y un monto válido.', 'error');
    }

    $deuda = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$deudas_table} WHERE id = %d", $deuda_id), ARRAY_A);
    if (!$deuda) {
        gc_redirect_with_notice('Deuda no encontrada.', 'error');
    }

    $tipo_deuda = gc_get_deuda_tipo($deuda);
    $metodo = 'transferencia';
    $instancia = null;

    if ($tipo_deuda === 'recurrente' || $tipo_deuda === 'prestamo') {
        $periodo = $fecha ? wp_date('Y-m', strtotime($fecha)) : gc_get_periodo_actual();
        $instancia = gc_get_or_create_instancia_para_periodo($deuda, $periodo, $fecha);
        if (!$instancia) {
            gc_redirect_with_notice('No se encontró una cuota pendiente para la deuda.', 'error');
        }
    }

    $movimiento_id = gc_insert_movimiento_from_deuda_pago($deuda, $monto, $fecha, $metodo, $instancia);

    if ($movimiento_id) {
        $wpdb->insert(
            $pagos_table,
            array(
                'deuda_id' => $deuda_id,
                'instancia_id' => $instancia['id'] ?? null,
                'movimiento_id' => $movimiento_id,
                'fecha_pago' => $fecha,
                'monto' => $monto,
                'metodo' => $metodo,
                'notas' => $notas,
                'created_at' => gc_now(),
            ),
            array('%d', '%d', '%d', '%s', '%f', '%s', '%s', '%s')
        );
    }

    if ($instancia) {
        gc_apply_pago_a_instancia($instancia, $monto);
    }

    if ($tipo_deuda === 'prestamo') {
        gc_recalculate_prestamo_estado($deuda_id);
    } else {
        gc_recalculate_deuda_estado($deuda_id);
    }

    if ($tipo_deuda === 'unica') {
        $updated = $wpdb->get_row($wpdb->prepare("SELECT saldo FROM {$deudas_table} WHERE id = %d", $deuda_id), ARRAY_A);
        if ($updated && isset($updated['saldo']) && (float) $updated['saldo'] <= 0) {
            $wpdb->update($deudas_table, array('activo' => 0), array('id' => $deuda_id), array('%d'), array('%d'));
        }
    }

    gc_redirect_with_notice('Pago registrado y movimiento generado.', 'success');
}

function gc_insert_movimiento_from_deuda_pago(array $deuda, float $monto, string $fecha, string $metodo, ?array $instancia = null): int {
    global $wpdb;
    $tabla = gc_get_table('gc_movimientos');
    $tipo_deuda = gc_get_deuda_tipo($deuda);
    $descripcion = 'Pago deuda: ' . $deuda['nombre'];
    if ($tipo_deuda === 'recurrente' && $instancia) {
        $descripcion = 'Pago deuda recurrente ' . $deuda['nombre'] . ' (' . $instancia['periodo'] . ')';
    } elseif ($tipo_deuda === 'prestamo' && $instancia) {
        $descripcion = 'Pago cuota préstamo ' . $deuda['nombre'] . ' (' . $instancia['periodo'] . ')';
    }

    $wpdb->insert(
        $tabla,
        array(
            'fecha' => $fecha,
            'tipo' => 'egreso',
            'monto' => $monto,
            'metodo' => $metodo,
            'categoria' => 'Deudas',
            'descripcion' => $descripcion,
            'cliente_id' => null,
            'proveedor_id' => null,
            'documento_id' => null,
            'origen' => 'deuda_pago',
            'ref_id' => (int) $deuda['id'],
            'created_at' => gc_now(),
            'updated_at' => gc_now(),
        ),
        array('%s', '%s', '%f', '%s', '%s', '%s', '%d', '%d', '%d', '%s', '%d', '%s', '%s')
    );

    return (int) $wpdb->insert_id;
}
