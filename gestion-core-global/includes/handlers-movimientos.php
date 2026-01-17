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
        'updated_at' => gc_now(),
    );

    $id = absint($_POST['movimiento_id'] ?? 0);

    if (!$data['tipo'] || !in_array($data['tipo'], array('ingreso', 'egreso'), true)) {
        gc_redirect_with_notice('Selecciona un tipo válido para el movimiento.', 'error');
    }

    if ($data['monto'] <= 0) {
        gc_redirect_with_notice('El monto debe ser mayor a cero.', 'error');
    }

    if ($id) {
        $wpdb->update($table, $data, array('id' => $id), array('%s', '%s', '%f', '%s', '%s', '%s', '%d', '%d', '%d', '%s'), array('%d'));
        gc_redirect_with_notice('Movimiento actualizado.', 'success');
    }

    $data['created_at'] = gc_now();
    $wpdb->insert(
        $table,
        $data,
        array('%s', '%s', '%f', '%s', '%s', '%s', '%d', '%d', '%d', '%s', '%s')
    );

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
