<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_gc_save_proveedor', 'gc_handle_save_proveedor');
add_action('admin_post_gc_delete_proveedor', 'gc_handle_delete_proveedor');

function gc_handle_save_proveedor(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_save_proveedor');

    global $wpdb;
    $table = gc_get_table('gc_proveedores');

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
        gc_redirect_with_notice('El nombre del proveedor es obligatorio.', 'error');
    }

    $id = absint($_POST['proveedor_id'] ?? 0);
    if ($id) {
        $wpdb->update($table, $data, array('id' => $id), array('%s', '%s', '%s', '%s', '%s', '%s', '%s'), array('%d'));
        gc_redirect_with_notice('Proveedor actualizado.', 'success');
    }

    $data['created_at'] = gc_now();
    $wpdb->insert($table, $data, array('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'));
    gc_redirect_with_notice('Proveedor creado.', 'success');
}

function gc_handle_delete_proveedor(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_delete_proveedor');

    global $wpdb;
    $table = gc_get_table('gc_proveedores');
    $id = absint($_POST['proveedor_id'] ?? 0);

    if ($id) {
        $wpdb->delete($table, array('id' => $id), array('%d'));
        gc_redirect_with_notice('Proveedor eliminado.', 'success');
    }

    gc_redirect_with_notice('Proveedor no encontrado.', 'error');
}
