<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_render_movimientos_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $table = gc_get_table('gc_movimientos');

    $filters = array(
        'gc_start' => isset($_GET['gc_start']) ? sanitize_text_field(wp_unslash($_GET['gc_start'])) : '',
        'gc_end' => isset($_GET['gc_end']) ? sanitize_text_field(wp_unslash($_GET['gc_end'])) : '',
        'gc_tipo' => isset($_GET['gc_tipo']) ? sanitize_text_field(wp_unslash($_GET['gc_tipo'])) : '',
        'gc_categoria' => isset($_GET['gc_categoria']) ? sanitize_text_field(wp_unslash($_GET['gc_categoria'])) : '',
        'gc_metodo' => isset($_GET['gc_metodo']) ? sanitize_text_field(wp_unslash($_GET['gc_metodo'])) : '',
    );

    $where = array();
    $params = array();

    if ($filters['gc_start'] && $filters['gc_end']) {
        $where[] = 'fecha BETWEEN %s AND %s';
        $params[] = $filters['gc_start'];
        $params[] = $filters['gc_end'];
    }

    if ($filters['gc_tipo']) {
        $where[] = 'tipo = %s';
        $params[] = $filters['gc_tipo'];
    }

    if ($filters['gc_categoria']) {
        $where[] = 'categoria = %s';
        $params[] = $filters['gc_categoria'];
    }

    if ($filters['gc_metodo']) {
        $where[] = 'metodo = %s';
        $params[] = $filters['gc_metodo'];
    }

    $where_sql = $where ? ('WHERE ' . implode(' AND ', $where)) : '';
    $query = "SELECT * FROM {$table} {$where_sql} ORDER BY fecha DESC, id DESC";
    $rows = $params ? $wpdb->get_results($wpdb->prepare($query, $params), ARRAY_A) : $wpdb->get_results($query, ARRAY_A);

    $edit_id = absint($_GET['edit_movimiento'] ?? 0);
    $edit_data = array(
        'fecha' => current_time('Y-m-d'),
        'tipo' => 'ingreso',
        'monto' => '',
        'metodo' => 'efectivo',
        'categoria' => '',
        'descripcion' => '',
        'cliente_id' => '',
        'proveedor_id' => '',
        'documento_id' => '',
        'deuda_id' => '',
    );

    if ($edit_id) {
        $edit_row = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $edit_id), ARRAY_A);
        if ($edit_row) {
            if ($edit_row['origen'] === 'deuda_pago') {
                $edit_row['deuda_id'] = $edit_row['ref_id'];
            }
            $edit_data = array_merge($edit_data, $edit_row);
        }
    }

    $form = '<form class="gc-form gc-form-movimientos" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_save_movimiento', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_save_movimiento">';
    if ($edit_id) {
        $form .= '<input type="hidden" name="movimiento_id" value="' . esc_attr($edit_id) . '">';
    }
    $form .= '<div class="gc-form-grid">'
        . '<label>Fecha<input type="date" name="fecha" value="' . esc_attr(gc_field_value($edit_data, 'fecha')) . '"></label>'
        . '<label>Tipo<select name="tipo">' . gc_select_options(array('ingreso' => 'Ingreso', 'egreso' => 'Egreso'), gc_field_value($edit_data, 'tipo')) . '</select></label>'
        . '<label>Monto<input type="number" step="0.01" name="monto" value="' . esc_attr(gc_field_value($edit_data, 'monto')) . '"></label>'
        . '<label>Método<select name="metodo">' . gc_select_options(array('efectivo' => 'Efectivo', 'transferencia' => 'Transferencia', 'tarjeta' => 'Tarjeta'), gc_field_value($edit_data, 'metodo')) . '</select></label>'
        . '<label>Categoría<input type="text" name="categoria" value="' . esc_attr(gc_field_value($edit_data, 'categoria')) . '"></label>'
        . '<label>Cliente<select name="cliente_id">' . gc_select_options(gc_get_clientes_options(), gc_field_value($edit_data, 'cliente_id')) . '</select></label>'
        . '<label>Proveedor<select name="proveedor_id">' . gc_select_options(gc_get_proveedores_options(), gc_field_value($edit_data, 'proveedor_id')) . '</select></label>'
        . '<label>Documento<select name="documento_id">' . gc_select_options(gc_get_documentos_options('', true, (int) gc_field_value($edit_data, 'documento_id')), gc_field_value($edit_data, 'documento_id')) . '</select></label>'
        . '<label class="gc-form-conditional" data-gc-show="egreso">Vincular a deuda<select name="deuda_id">' . gc_select_options(gc_get_deudas_options(true), gc_field_value($edit_data, 'deuda_id')) . '</select></label>'
        . '</div>'
        . '<label>Descripción<textarea name="descripcion" rows="2">' . esc_textarea(gc_field_value($edit_data, 'descripcion')) . '</textarea></label>'
        . '<button class="gc-button" type="submit">' . ($edit_id ? 'Actualizar movimiento' : 'Agregar movimiento') . '</button>'
        . '</form>';

    $filter_form = '<form class="gc-form gc-form-inline" method="get">'
        . '<label>Desde<input type="date" name="gc_start" value="' . esc_attr($filters['gc_start']) . '"></label>'
        . '<label>Hasta<input type="date" name="gc_end" value="' . esc_attr($filters['gc_end']) . '"></label>'
        . '<label>Tipo<select name="gc_tipo">' . gc_select_options(array('' => 'Todos', 'ingreso' => 'Ingreso', 'egreso' => 'Egreso'), $filters['gc_tipo']) . '</select></label>'
        . '<label>Categoría<input type="text" name="gc_categoria" value="' . esc_attr($filters['gc_categoria']) . '"></label>'
        . '<label>Método<select name="gc_metodo">' . gc_select_options(array('' => 'Todos', 'efectivo' => 'Efectivo', 'transferencia' => 'Transferencia', 'tarjeta' => 'Tarjeta'), $filters['gc_metodo']) . '</select></label>'
        . '<button class="gc-button is-light" type="submit">Filtrar</button>'
        . '</form>';

    $rows_html = '';
    foreach ($rows as $row) {
        $rows_html .= '<tr>'
            . '<td>' . esc_html($row['fecha']) . '</td>'
            . '<td><span class="gc-badge is-' . esc_attr($row['tipo']) . '">' . esc_html(ucfirst($row['tipo'])) . '</span></td>'
            . '<td>' . esc_html(gc_format_currency($row['monto'])) . '</td>'
            . '<td>' . esc_html($row['metodo']) . '</td>'
            . '<td>' . esc_html($row['categoria']) . '</td>'
            . '<td>' . esc_html($row['descripcion']) . '</td>'
            . '<td class="gc-table-actions">'
            . '<a class="gc-link" href="' . esc_url(add_query_arg('edit_movimiento', $row['id'])) . '">Editar</a>'
            . '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'¿Eliminar movimiento?\')">'
            . wp_nonce_field('gc_delete_movimiento', '_wpnonce', true, false)
            . '<input type="hidden" name="action" value="gc_delete_movimiento">'
            . '<input type="hidden" name="movimiento_id" value="' . esc_attr($row['id']) . '">'
            . '<button type="submit" class="gc-link is-danger">Eliminar</button>'
            . '</form>'
            . '</td>'
            . '</tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="7" class="gc-table-empty">Sin movimientos registrados.</td></tr>';
    }

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Fecha</th><th>Tipo</th><th>Monto</th><th>Método</th><th>Categoría</th><th>Descripción</th><th>Acciones</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';

    $panel_content = gc_render_notice();
    $panel_content .= $form;
    $panel_content .= $filter_form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Movimientos de caja', 'Registra ingresos y egresos manuales.', $panel_content) . '</div>';
}
