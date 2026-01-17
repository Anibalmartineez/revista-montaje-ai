<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_gc_save_documento', 'gc_handle_save_documento');
add_action('admin_post_gc_delete_documento', 'gc_handle_delete_documento');
add_action('admin_post_gc_add_documento_pago', 'gc_handle_add_documento_pago');

function gc_handle_save_documento(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_save_documento');

    global $wpdb;
    $table = gc_get_table('gc_documentos');

    $data = array(
        'numero' => sanitize_text_field(wp_unslash($_POST['numero'] ?? '')),
        'fecha' => gc_parse_date($_POST['fecha'] ?? ''),
        'tipo' => sanitize_text_field(wp_unslash($_POST['tipo'] ?? '')),
        'cliente_id' => absint($_POST['cliente_id'] ?? 0) ?: null,
        'proveedor_id' => absint($_POST['proveedor_id'] ?? 0) ?: null,
        'total' => (float) str_replace(',', '.', wp_unslash($_POST['total'] ?? 0)),
        'notas' => sanitize_textarea_field(wp_unslash($_POST['notas'] ?? '')),
        'updated_at' => gc_now(),
    );

    if (!$data['numero'] || !$data['tipo']) {
        gc_redirect_with_notice('El número y tipo de documento son obligatorios.', 'error');
    }

    if (!in_array($data['tipo'], array('factura_venta', 'factura_compra'), true)) {
        gc_redirect_with_notice('Tipo de documento inválido.', 'error');
    }

    if ($data['total'] < 0) {
        gc_redirect_with_notice('El total del documento debe ser positivo.', 'error');
    }

    $id = absint($_POST['documento_id'] ?? 0);

    if ($id) {
        $documento = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $id), ARRAY_A);
        if (!$documento) {
            gc_redirect_with_notice('Documento no encontrado.', 'error');
        }
        $monto_pagado = (float) $documento['monto_pagado'];
        $saldo = max(0, $data['total'] - $monto_pagado);
        $data['saldo'] = $saldo;
        $data['estado'] = gc_calculate_estado_documento($data['total'], $monto_pagado);
        $wpdb->update(
            $table,
            $data,
            array('id' => $id),
            array('%s', '%s', '%s', '%d', '%d', '%f', '%s', '%s', '%f', '%s'),
            array('%d')
        );
        gc_redirect_with_notice('Documento actualizado.', 'success');
    }

    $data['monto_pagado'] = 0;
    $data['saldo'] = $data['total'];
    $data['estado'] = gc_calculate_estado_documento($data['total'], 0);
    $data['created_at'] = gc_now();
    $wpdb->insert(
        $table,
        $data,
        array('%s', '%s', '%s', '%d', '%d', '%f', '%s', '%s', '%f', '%f', '%s', '%s')
    );

    gc_redirect_with_notice('Documento creado.', 'success');
}

function gc_handle_delete_documento(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_delete_documento');

    global $wpdb;
    $table = gc_get_table('gc_documentos');
    $id = absint($_POST['documento_id'] ?? 0);

    if ($id) {
        $wpdb->delete($table, array('id' => $id), array('%d'));
        gc_redirect_with_notice('Documento eliminado.', 'success');
    }

    gc_redirect_with_notice('Documento no encontrado.', 'error');
}

function gc_handle_add_documento_pago(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_add_documento_pago');

    global $wpdb;
    $documentos_table = gc_get_table('gc_documentos');
    $pagos_table = gc_get_table('gc_documento_pagos');

    $documento_id = absint($_POST['documento_id'] ?? 0);
    $monto = (float) str_replace(',', '.', wp_unslash($_POST['monto'] ?? 0));
    $fecha = gc_parse_date($_POST['fecha_pago'] ?? '');
    $metodo = sanitize_text_field(wp_unslash($_POST['metodo'] ?? ''));
    $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

    if (!$documento_id || $monto <= 0) {
        gc_redirect_with_notice('Selecciona un documento y un monto válido.', 'error');
    }

    $documento = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$documentos_table} WHERE id = %d", $documento_id), ARRAY_A);
    if (!$documento) {
        gc_redirect_with_notice('Documento no encontrado.', 'error');
    }

    $movimiento_id = gc_insert_movimiento_from_documento_pago($documento, $monto, $fecha, $metodo);
    if ($movimiento_id) {
        $exists = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$pagos_table} WHERE documento_id = %d AND movimiento_id = %d",
                $documento_id,
                $movimiento_id
            )
        );
        if (!$exists) {
            $wpdb->insert(
                $pagos_table,
                array(
                    'documento_id' => $documento_id,
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
    }

    gc_recalculate_documento_estado($documento_id);

    gc_redirect_with_notice('Pago/cobro registrado y movimiento generado.', 'success');
}

function gc_insert_movimiento_from_documento_pago(array $documento, float $monto, string $fecha, string $metodo): int {
    global $wpdb;
    $tabla = gc_get_table('gc_movimientos');
    $tipo = ($documento['tipo'] === 'factura_compra') ? 'egreso' : 'ingreso';

    $wpdb->insert(
        $tabla,
        array(
            'fecha' => $fecha,
            'tipo' => $tipo,
            'monto' => $monto,
            'metodo' => $metodo,
            'categoria' => 'Documento',
            'descripcion' => 'Pago/Cobro de documento #' . $documento['numero'],
            'cliente_id' => $documento['cliente_id'] ? (int) $documento['cliente_id'] : null,
            'proveedor_id' => $documento['proveedor_id'] ? (int) $documento['proveedor_id'] : null,
            'documento_id' => (int) $documento['id'],
            'origen' => 'documento_pago',
            'ref_id' => (int) $documento['id'],
            'created_at' => gc_now(),
            'updated_at' => gc_now(),
        ),
        array('%s', '%s', '%f', '%s', '%s', '%s', '%d', '%d', '%d', '%s', '%d', '%s', '%s')
    );

    return (int) $wpdb->insert_id;
}
