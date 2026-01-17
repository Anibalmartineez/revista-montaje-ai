<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_render_proveedores_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $table = gc_get_table('gc_proveedores');
    $rows = $wpdb->get_results("SELECT * FROM {$table} ORDER BY nombre ASC", ARRAY_A);

    $edit_id = absint($_GET['edit_proveedor'] ?? 0);
    $edit_data = array(
        'nombre' => '',
        'ruc' => '',
        'telefono' => '',
        'email' => '',
        'direccion' => '',
        'notas' => '',
    );

    if ($edit_id) {
        $edit_row = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $edit_id), ARRAY_A);
        if ($edit_row) {
            $edit_data = array_merge($edit_data, $edit_row);
        }
    }

    $form = '<form class="gc-form" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_save_proveedor', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_save_proveedor">';
    if ($edit_id) {
        $form .= '<input type="hidden" name="proveedor_id" value="' . esc_attr($edit_id) . '">';
    }
    $form .= '<div class="gc-form-grid">'
        . '<label>Nombre<input type="text" name="nombre" value="' . esc_attr(gc_field_value($edit_data, 'nombre')) . '"></label>'
        . '<label>RUC<input type="text" name="ruc" value="' . esc_attr(gc_field_value($edit_data, 'ruc')) . '"></label>'
        . '<label>Teléfono<input type="text" name="telefono" value="' . esc_attr(gc_field_value($edit_data, 'telefono')) . '"></label>'
        . '<label>Email<input type="email" name="email" value="' . esc_attr(gc_field_value($edit_data, 'email')) . '"></label>'
        . '<label>Dirección<input type="text" name="direccion" value="' . esc_attr(gc_field_value($edit_data, 'direccion')) . '"></label>'
        . '</div>'
        . '<label>Notas<textarea name="notas" rows="2">' . esc_textarea(gc_field_value($edit_data, 'notas')) . '</textarea></label>'
        . '<button class="gc-button" type="submit">' . ($edit_id ? 'Actualizar proveedor' : 'Agregar proveedor') . '</button>'
        . '</form>';

    $rows_html = '';
    foreach ($rows as $row) {
        $rows_html .= '<tr>'
            . '<td>' . esc_html($row['nombre']) . '</td>'
            . '<td>' . esc_html($row['ruc']) . '</td>'
            . '<td>' . esc_html($row['telefono']) . '</td>'
            . '<td>' . esc_html($row['email']) . '</td>'
            . '<td>' . esc_html($row['direccion']) . '</td>'
            . '<td class="gc-table-actions">'
            . '<a class="gc-link" href="' . esc_url(add_query_arg('edit_proveedor', $row['id'])) . '">Editar</a>'
            . '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'¿Eliminar proveedor?\')">'
            . wp_nonce_field('gc_delete_proveedor', '_wpnonce', true, false)
            . '<input type="hidden" name="action" value="gc_delete_proveedor">'
            . '<input type="hidden" name="proveedor_id" value="' . esc_attr($row['id']) . '">'
            . '<button type="submit" class="gc-link is-danger">Eliminar</button>'
            . '</form>'
            . '</td>'
            . '</tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="6" class="gc-table-empty">Sin proveedores cargados.</td></tr>';
    }

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Nombre</th><th>RUC</th><th>Teléfono</th><th>Email</th><th>Dirección</th><th>Acciones</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';

    $panel_content = gc_render_notice();
    $panel_content .= $form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Proveedores', 'Gestiona los datos básicos de proveedores.', $panel_content) . '</div>';
}
