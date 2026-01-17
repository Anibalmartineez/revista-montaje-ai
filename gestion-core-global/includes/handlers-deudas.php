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

    $data = array(
        'nombre' => sanitize_text_field(wp_unslash($_POST['nombre'] ?? '')),
        'monto' => (float) str_replace(',', '.', wp_unslash($_POST['monto'] ?? 0)),
        'frecuencia' => sanitize_text_field(wp_unslash($_POST['frecuencia'] ?? 'mensual')),
        'dia_sugerido' => absint($_POST['dia_sugerido'] ?? 0) ?: null,
        'activo' => isset($_POST['activo']) ? 1 : 0,
        'notas' => sanitize_textarea_field(wp_unslash($_POST['notas'] ?? '')),
        'updated_at' => gc_now(),
    );

    if (!$data['nombre']) {
        gc_redirect_with_notice('El nombre de la deuda es obligatorio.', 'error');
    }

    $id = absint($_POST['deuda_id'] ?? 0);
    if ($id) {
        $wpdb->update($table, $data, array('id' => $id), array('%s', '%f', '%s', '%d', '%d', '%s', '%s'), array('%d'));
        gc_recalculate_deuda_estado($id);
        gc_redirect_with_notice('Deuda actualizada.', 'success');
    }

    $data['estado'] = 'pendiente';
    $data['monto_pagado'] = 0;
    $data['saldo'] = $data['monto'];
    $data['created_at'] = gc_now();
    $wpdb->insert($table, $data, array('%s', '%f', '%s', '%d', '%d', '%s', '%s', '%s', '%s', '%f', '%f'));
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

    $metodo = 'transferencia';
    $movimiento_id = gc_insert_movimiento_from_deuda_pago($deuda, $monto, $fecha, $metodo);

    if ($movimiento_id) {
        $wpdb->insert(
            $pagos_table,
            array(
                'deuda_id' => $deuda_id,
                'movimiento_id' => $movimiento_id,
                'fecha_pago' => $fecha,
                'monto' => $monto,
                'metodo' => $metodo,
                'notas' => $notas,
                'created_at' => gc_now(),
            ),
            array('%d', '%d', '%s', '%f', '%s', '%s', '%s')
        );
    }

    gc_recalculate_deuda_estado($deuda_id);
    gc_redirect_with_notice('Pago registrado y movimiento generado.', 'success');
}

function gc_insert_movimiento_from_deuda_pago(array $deuda, float $monto, string $fecha, string $metodo): int {
    global $wpdb;
    $tabla = gc_get_table('gc_movimientos');

    $wpdb->insert(
        $tabla,
        array(
            'fecha' => $fecha,
            'tipo' => 'egreso',
            'monto' => $monto,
            'metodo' => $metodo,
            'categoria' => 'Deudas',
            'descripcion' => 'Pago deuda: ' . $deuda['nombre'],
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
