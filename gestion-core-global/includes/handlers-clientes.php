<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_gc_save_cliente', 'gc_handle_save_cliente');
add_action('admin_post_gc_delete_cliente', 'gc_handle_delete_cliente');

function gc_handle_save_cliente(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_save_cliente');

    global $wpdb;
    $table = gc_get_table('gc_clientes');

    $data = array(
        'nombre' => sanitize_text_field(wp_unslash($_POST['nombre'] ?? '')),
        'ruc' => sanitize_text_field(wp_unslash($_POST['ruc'] ?? '')),
        'telefono' => sanitize_text_field(wp_unslash($_POST['telefono'] ?? '')),
        'email' => sanitize_email(wp_unslash($_POST['email'] ?? '')),
        'direccion' => sanitize_text_field(wp_unslash($_POST['direccion'] ?? '')),
        'notas' => sanitize_textarea_field(wp_unslash($_POST['notas'] ?? '')),
        'updated_at' => gc_now(),
    );

    if (!$data['nombre']) {
        gc_redirect_with_notice('El nombre del cliente es obligatorio.', 'error');
    }

    $id = absint($_POST['cliente_id'] ?? 0);
    if ($id) {
        $wpdb->update($table, $data, array('id' => $id), array('%s', '%s', '%s', '%s', '%s', '%s', '%s'), array('%d'));
        gc_redirect_with_notice('Cliente actualizado.', 'success');
    }

    $data['created_at'] = gc_now();
    $wpdb->insert($table, $data, array('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'));
    gc_redirect_with_notice('Cliente creado.', 'success');
}

function gc_handle_delete_cliente(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_delete_cliente');

    global $wpdb;
    $table = gc_get_table('gc_clientes');
    $id = absint($_POST['cliente_id'] ?? 0);

    if ($id) {
        $wpdb->delete($table, array('id' => $id), array('%d'));
        gc_redirect_with_notice('Cliente eliminado.', 'success');
    }

    gc_redirect_with_notice('Cliente no encontrado.', 'error');
}
