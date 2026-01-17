<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_gc_save_movimiento', 'gc_handle_save_movimiento');
add_action('admin_post_gc_delete_movimiento', 'gc_handle_delete_movimiento');

function gc_handle_save_movimiento(): void {
    gc_guard_manage_access();

    check_admin_referer('gc_save_movimiento');

    global $wpdb;
    $table = gc_get_table('gc_movimientos');

    $data = array(
        'fecha' => gc_parse_date($_POST['fecha'] ?? ''),
        'tipo' => sanitize_text_field(wp_unslash($_POST['tipo'] ?? '')),
        'monto' => (float) str_replace(',', '.', wp_unslash($_POST['monto'] ?? 0)),
        'metodo' => sanitize_text_field(wp_unslash($_POST['metodo'] ?? '')),
        'categoria' => sanitize_text_field(wp_unslash($_POST['categoria'] ?? '')),
        'descripcion' => sanitize_textarea_field(wp_unslash($_POST['descripcion'] ?? '')),
        'cliente_id' => absint($_POST['cliente_id'] ?? 0) ?: null,
        'proveedor_id' => absint($_POST['proveedor_id'] ?? 0) ?: null,
        'documento_id' => absint($_POST['documento_id'] ?? 0) ?: null,
        'origen' => null,
        'ref_id' => null,
        'updated_at' => gc_now(),
    );

    $id = absint($_POST['movimiento_id'] ?? 0);
    $deuda_id = absint($_POST['deuda_id'] ?? 0) ?: null;
    $documento = null;

    if ($id) {
        $existing_movimiento = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $id), ARRAY_A);
        if (!$existing_movimiento) {
            gc_redirect_with_notice('Movimiento no encontrado.', 'error');
        }

        $documento_pagos_table = gc_get_table('gc_documento_pagos');
        $deuda_pagos_table = gc_get_table('gc_deuda_pagos');
        $linked_via_origen = in_array($existing_movimiento['origen'], array('documento_pago', 'deuda_pago'), true) && $existing_movimiento['ref_id'];
        $linked_via_documento_pago = (bool) $wpdb->get_var(
            $wpdb->prepare("SELECT 1 FROM {$documento_pagos_table} WHERE movimiento_id = %d LIMIT 1", $id)
        );
        $linked_via_deuda_pago = (bool) $wpdb->get_var(
            $wpdb->prepare("SELECT 1 FROM {$deuda_pagos_table} WHERE movimiento_id = %d LIMIT 1", $id)
        );
        $is_linked = $linked_via_origen || $linked_via_documento_pago || $linked_via_deuda_pago;

        if ($is_linked) {
            $existing_deuda_id = ($existing_movimiento['origen'] === 'deuda_pago') ? (int) $existing_movimiento['ref_id'] : null;
            $existing_documento_id = $existing_movimiento['documento_id'] ? (int) $existing_movimiento['documento_id'] : null;
            $data_documento_id = $data['documento_id'] ?: null;
            $data_deuda_id = $deuda_id ?: null;
            $critical_changed = $data['tipo'] !== $existing_movimiento['tipo']
                || (float) $data['monto'] !== (float) $existing_movimiento['monto']
                || $data['fecha'] !== $existing_movimiento['fecha']
                || $data['metodo'] !== $existing_movimiento['metodo']
                || $data_documento_id !== $existing_documento_id
                || $data_deuda_id !== $existing_deuda_id;

            if ($critical_changed) {
                gc_redirect_with_notice(
                    'Este movimiento está vinculado a un pago. Para corregir, elimine el pago y regístrelo nuevamente.',
                    'error'
                );
            }

            $wpdb->update(
                $table,
                array(
                    'descripcion' => $data['descripcion'],
                    'updated_at' => gc_now(),
                ),
                array('id' => $id),
                array('%s', '%s'),
                array('%d')
            );
            gc_redirect_with_notice('Movimiento actualizado.', 'success');
        }
    }

    if (!$data['tipo'] || !in_array($data['tipo'], array('ingreso', 'egreso'), true)) {
        gc_redirect_with_notice('Selecciona un tipo válido para el movimiento.', 'error');
    }

    if ($data['monto'] <= 0) {
        gc_redirect_with_notice('El monto debe ser mayor a cero.', 'error');
    }

    if ($data['documento_id'] && $deuda_id) {
        gc_redirect_with_notice('Selecciona solo un documento o una deuda para vincular.', 'error');
    }

    if ($data['documento_id']) {
        $documentos_table = gc_get_table('gc_documentos');
        $documento = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$documentos_table} WHERE id = %d", $data['documento_id']), ARRAY_A);
        if (!$documento) {
            gc_redirect_with_notice('Documento no encontrado.', 'error');
        }
        $tipo_esperado = ($documento['tipo'] === 'factura_compra') ? 'egreso' : 'ingreso';
        if ($data['tipo'] !== $tipo_esperado) {
            gc_redirect_with_notice('El tipo de movimiento no coincide con el documento seleccionado.', 'error');
        }
        $data['origen'] = 'documento_pago';
        $data['ref_id'] = (int) $documento['id'];
        $data['cliente_id'] = $documento['cliente_id'] ? (int) $documento['cliente_id'] : $data['cliente_id'];
        $data['proveedor_id'] = $documento['proveedor_id'] ? (int) $documento['proveedor_id'] : $data['proveedor_id'];
    }

    if ($deuda_id) {
        if ($data['tipo'] !== 'egreso') {
            gc_redirect_with_notice('Las deudas solo se pueden vincular a egresos.', 'error');
        }
        $deudas_table = gc_get_table('gc_deudas');
        $deuda = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$deudas_table} WHERE id = %d", $deuda_id), ARRAY_A);
        if (!$deuda) {
            gc_redirect_with_notice('Deuda no encontrada.', 'error');
        }
        $data['origen'] = 'deuda_pago';
        $data['ref_id'] = (int) $deuda['id'];
    }

    if ($id) {
        $wpdb->update(
            $table,
            $data,
            array('id' => $id),
            array('%s', '%s', '%f', '%s', '%s', '%s', '%d', '%d', '%d', '%s', '%d', '%s'),
            array('%d')
        );
        gc_redirect_with_notice('Movimiento actualizado.', 'success');
    }

    $data['created_at'] = gc_now();
    $wpdb->insert(
        $table,
        $data,
        array('%s', '%s', '%f', '%s', '%s', '%s', '%d', '%d', '%d', '%s', '%d', '%s', '%s')
    );

    $movimiento_id = (int) $wpdb->insert_id;

    if ($movimiento_id && $data['documento_id']) {
        $pagos_table = gc_get_table('gc_documento_pagos');
        $wpdb->insert(
            $pagos_table,
            array(
                'documento_id' => (int) $data['documento_id'],
                'movimiento_id' => $movimiento_id,
                'fecha_pago' => $data['fecha'],
                'monto' => $data['monto'],
                'metodo' => $data['metodo'],
                'notas' => $data['descripcion'],
                'created_at' => gc_now(),
            ),
            array('%d', '%d', '%s', '%f', '%s', '%s', '%s')
        );
        gc_recalculate_documento_estado((int) $data['documento_id']);
    }

    if ($movimiento_id && $deuda_id) {
        $pagos_table = gc_get_table('gc_deuda_pagos');
        $wpdb->insert(
            $pagos_table,
            array(
                'deuda_id' => (int) $deuda_id,
                'movimiento_id' => $movimiento_id,
                'fecha_pago' => $data['fecha'],
                'monto' => $data['monto'],
                'metodo' => $data['metodo'],
                'notas' => $data['descripcion'],
                'created_at' => gc_now(),
            ),
            array('%d', '%d', '%s', '%f', '%s', '%s', '%s')
        );
        gc_recalculate_deuda_estado((int) $deuda_id);
    }

    gc_redirect_with_notice('Movimiento creado.', 'success');
}

function gc_handle_delete_movimiento(): void {
    gc_guard_manage_access();

    check_admin_referer('gc_delete_movimiento');

    global $wpdb;
    $table = gc_get_table('gc_movimientos');
    $id = absint($_POST['movimiento_id'] ?? 0);

    if ($id) {
        $wpdb->delete($table, array('id' => $id), array('%d'));
        gc_redirect_with_notice('Movimiento eliminado.', 'success');
    }

    gc_redirect_with_notice('Movimiento no encontrado.', 'error');
}
