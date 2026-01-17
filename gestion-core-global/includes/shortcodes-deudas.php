<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_render_deudas_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $table = gc_get_table('gc_deudas');
    $rows = $wpdb->get_results("SELECT * FROM {$table} ORDER BY activo DESC, nombre ASC", ARRAY_A);

    $edit_id = absint($_GET['edit_deuda'] ?? 0);
    $edit_data = array(
        'nombre' => '',
        'monto' => '',
        'frecuencia' => 'mensual',
        'dia_sugerido' => '',
        'activo' => 1,
        'notas' => '',
    );

    if ($edit_id) {
        $edit_row = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $edit_id), ARRAY_A);
        if ($edit_row) {
            $edit_data = array_merge($edit_data, $edit_row);
        }
    }

    $form = '<form class="gc-form" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_save_deuda', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_save_deuda">';
    if ($edit_id) {
        $form .= '<input type="hidden" name="deuda_id" value="' . esc_attr($edit_id) . '">';
    }

    $form .= '<div class="gc-form-grid">'
        . '<label>Nombre<input type="text" name="nombre" value="' . esc_attr(gc_field_value($edit_data, 'nombre')) . '"></label>'
        . '<label>Monto<input type="number" step="0.01" name="monto" value="' . esc_attr(gc_field_value($edit_data, 'monto')) . '"></label>'
        . '<label>Frecuencia<select name="frecuencia">' . gc_select_options(array('mensual' => 'Mensual', 'semanal' => 'Semanal', 'anual' => 'Anual', 'unica' => 'Única'), gc_field_value($edit_data, 'frecuencia')) . '</select></label>'
        . '<label>Día sugerido<input type="number" min="1" max="31" name="dia_sugerido" value="' . esc_attr(gc_field_value($edit_data, 'dia_sugerido')) . '"></label>'
        . '</div>'
        . '<label class="gc-checkbox"><input type="checkbox" name="activo" value="1"' . (gc_field_value($edit_data, 'activo') ? ' checked' : '') . '> Activa</label>'
        . '<label>Notas<textarea name="notas" rows="2">' . esc_textarea(gc_field_value($edit_data, 'notas')) . '</textarea></label>'
        . '<button class="gc-button" type="submit">' . ($edit_id ? 'Actualizar deuda' : 'Agregar deuda') . '</button>'
        . '</form>';

    $rows_html = '';
    foreach ($rows as $row) {
        $frecuencia = ucfirst($row['frecuencia']);
        $estado = $row['activo'] ? 'Activa' : 'Inactiva';
        $rows_html .= '<tr>'
            . '<td>' . esc_html($row['nombre']) . '</td>'
            . '<td>' . esc_html(gc_format_currency($row['monto'])) . '</td>'
            . '<td>' . esc_html($frecuencia) . '</td>'
            . '<td>' . esc_html($row['dia_sugerido'] ?: '-') . '</td>'
            . '<td>' . esc_html($estado) . '</td>'
            . '<td class="gc-table-actions">'
            . '<a class="gc-link" href="' . esc_url(add_query_arg('edit_deuda', $row['id'])) . '">Editar</a>'
            . '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'¿Eliminar deuda?\')">'
            . wp_nonce_field('gc_delete_deuda', '_wpnonce', true, false)
            . '<input type="hidden" name="action" value="gc_delete_deuda">'
            . '<input type="hidden" name="deuda_id" value="' . esc_attr($row['id']) . '">'
            . '<button type="submit" class="gc-link is-danger">Eliminar</button>'
            . '</form>'
            . '</td>'
            . '</tr>';
        $rows_html .= '<tr class="gc-table-secondary"><td colspan="6">'
            . gc_render_deuda_pago_form($row)
            . '</td></tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="6" class="gc-table-empty">Sin deudas registradas.</td></tr>';
    }

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Nombre</th><th>Monto</th><th>Frecuencia</th><th>Día sugerido</th><th>Estado</th><th>Acciones</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';

    $panel_content = gc_render_notice();
    $panel_content .= $form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Deudas de la empresa', 'Controla compromisos recurrentes y pagos parciales.', $panel_content) . '</div>';
}

function gc_render_deuda_pago_form(array $deuda): string {
    $form = '<form class="gc-form gc-form-inline" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_add_deuda_pago', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_add_deuda_pago">';
    $form .= '<input type="hidden" name="deuda_id" value="' . esc_attr($deuda['id']) . '">';
    $form .= '<strong>Registrar pago</strong>';
    $form .= '<label>Fecha<input type="date" name="fecha_pago" value="' . esc_attr(current_time('Y-m-d')) . '"></label>';
    $form .= '<label>Monto<input type="number" step="0.01" name="monto" value="' . esc_attr($deuda['monto']) . '"></label>';
    $form .= '<label>Notas<input type="text" name="notas"></label>';
    $form .= '<button class="gc-button is-light" type="submit">Registrar</button>';
    $form .= '</form>';

    return $form;
}
