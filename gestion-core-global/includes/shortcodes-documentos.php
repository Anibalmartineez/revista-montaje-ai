<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_render_facturas_venta_shortcode(): string {
    return gc_render_documentos_panel('factura_venta', 'Facturas de venta', 'Registra facturas emitidas y cobros parciales.');
}

function gc_render_facturas_compra_shortcode(): string {
    return gc_render_documentos_panel('factura_compra', 'Facturas de compra', 'Registra facturas recibidas y pagos parciales.');
}

function gc_render_documentos_panel(string $tipo, string $title, string $subtitle): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $table = gc_get_table('gc_documentos');

    $rows = $wpdb->get_results(
        $wpdb->prepare("SELECT * FROM {$table} WHERE tipo = %s ORDER BY fecha DESC", $tipo),
        ARRAY_A
    );

    $edit_id = absint($_GET['edit_documento'] ?? 0);
    $edit_data = array(
        'numero' => '',
        'fecha' => current_time('Y-m-d'),
        'cliente_id' => '',
        'proveedor_id' => '',
        'total' => '',
        'notas' => '',
    );

    if ($edit_id) {
        $edit_row = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $edit_id), ARRAY_A);
        if ($edit_row && $edit_row['tipo'] === $tipo) {
            $edit_data = array_merge($edit_data, $edit_row);
        }
    }

    $form = '<form class="gc-form" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_save_documento', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_save_documento">';
    $form .= '<input type="hidden" name="tipo" value="' . esc_attr($tipo) . '">';
    if ($edit_id) {
        $form .= '<input type="hidden" name="documento_id" value="' . esc_attr($edit_id) . '">';
    }

    $cliente_select = '<label>Cliente<select name="cliente_id">' . gc_select_options(gc_get_clientes_options(), gc_field_value($edit_data, 'cliente_id')) . '</select></label>';
    $proveedor_select = '<label>Proveedor<select name="proveedor_id">' . gc_select_options(gc_get_proveedores_options(), gc_field_value($edit_data, 'proveedor_id')) . '</select></label>';

    $form .= '<div class="gc-form-grid">'
        . '<label>Número<input type="text" name="numero" value="' . esc_attr(gc_field_value($edit_data, 'numero')) . '"></label>'
        . '<label>Fecha<input type="date" name="fecha" value="' . esc_attr(gc_field_value($edit_data, 'fecha')) . '"></label>'
        . ($tipo === 'factura_venta' ? $cliente_select : $proveedor_select)
        . '<label>Total<input type="number" step="0.01" name="total" value="' . esc_attr(gc_field_value($edit_data, 'total')) . '"></label>'
        . '</div>'
        . '<label>Notas<textarea name="notas" rows="2">' . esc_textarea(gc_field_value($edit_data, 'notas')) . '</textarea></label>'
        . '<button class="gc-button" type="submit">' . ($edit_id ? 'Actualizar documento' : 'Agregar documento') . '</button>'
        . '</form>';

    $rows_html = '';
    foreach ($rows as $row) {
        $rows_html .= '<tr>'
            . '<td>' . esc_html($row['numero']) . '</td>'
            . '<td>' . esc_html($row['fecha']) . '</td>'
            . '<td>' . esc_html(gc_format_currency($row['total'])) . '</td>'
            . '<td>' . esc_html(gc_format_currency($row['monto_pagado'])) . '</td>'
            . '<td>' . esc_html(gc_format_currency($row['saldo'])) . '</td>'
            . '<td><span class="gc-badge is-' . esc_attr($row['estado']) . '">' . esc_html(ucfirst($row['estado'])) . '</span></td>'
            . '<td class="gc-table-actions">'
            . '<a class="gc-link" href="' . esc_url(add_query_arg('edit_documento', $row['id'])) . '">Editar</a>'
            . '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'¿Eliminar documento?\')">'
            . wp_nonce_field('gc_delete_documento', '_wpnonce', true, false)
            . '<input type="hidden" name="action" value="gc_delete_documento">'
            . '<input type="hidden" name="documento_id" value="' . esc_attr($row['id']) . '">'
            . '<button type="submit" class="gc-link is-danger">Eliminar</button>'
            . '</form>'
            . '</td>'
            . '</tr>';
        $rows_html .= '<tr class="gc-table-secondary"><td colspan="7">'
            . gc_render_documento_pago_form($row)
            . '</td></tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="7" class="gc-table-empty">Sin documentos registrados.</td></tr>';
    }

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Número</th><th>Fecha</th><th>Total</th><th>Pagado</th><th>Saldo</th><th>Estado</th><th>Acciones</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';

    $panel_content = gc_render_notice();
    $panel_content .= $form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel($title, $subtitle, $panel_content) . '</div>';
}

function gc_render_documento_pago_form(array $documento): string {
    $form = '<form class="gc-form gc-form-inline" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_add_documento_pago', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_add_documento_pago">';
    $form .= '<input type="hidden" name="documento_id" value="' . esc_attr($documento['id']) . '">';
    $form .= '<strong>Registrar pago/cobro</strong>';
    $form .= '<label>Fecha<input type="date" name="fecha_pago" value="' . esc_attr(current_time('Y-m-d')) . '"></label>';
    $form .= '<label>Monto<input type="number" step="0.01" name="monto" value="' . esc_attr($documento['saldo']) . '"></label>';
    $form .= '<label>Método<select name="metodo">' . gc_select_options(array('efectivo' => 'Efectivo', 'transferencia' => 'Transferencia', 'tarjeta' => 'Tarjeta'), '') . '</select></label>';
    $form .= '<label>Notas<input type="text" name="notas"></label>';
    $form .= '<button class="gc-button is-light" type="submit">Registrar</button>';
    $form .= '</form>';

    return $form;
}
