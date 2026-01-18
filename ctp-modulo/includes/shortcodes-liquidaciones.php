<?php

if (!defined('ABSPATH')) {
    exit;
}

function ctp_render_liquidaciones_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $ordenes_table = ctp_get_table('ctp_ordenes');
    $clientes_table = gc_get_table('gc_clientes');

    $cliente_id = absint($_GET['ctp_liq_cliente'] ?? 0);
    list($start_date, $end_date) = ctp_get_date_range_from_request('ctp_liq_start', 'ctp_liq_end');

    $ordenes = array();
    if ($cliente_id) {
        $ordenes = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT o.*, COALESCE(SUM(i.total), 0) as total_orden
                FROM {$ordenes_table} o
                LEFT JOIN " . ctp_get_table('ctp_orden_items') . " i ON i.orden_id = o.id
                WHERE o.cliente_id = %d
                  AND o.estado = 'pendiente'
                  AND o.documento_id IS NULL
                  AND o.fecha BETWEEN %s AND %s
                GROUP BY o.id
                ORDER BY o.fecha ASC",
                $cliente_id,
                $start_date,
                $end_date
            ),
            ARRAY_A
        );
    }

    $filter_form = '<form class="gc-form gc-form-inline ctp-filters" method="get">';
    $filter_form .= '<label>Cliente<select name="ctp_liq_cliente">' . gc_select_options(ctp_get_clientes_options(), $cliente_id) . '</select></label>';
    $filter_form .= '<label>Desde<input type="date" name="ctp_liq_start" value="' . esc_attr($start_date) . '"></label>';
    $filter_form .= '<label>Hasta<input type="date" name="ctp_liq_end" value="' . esc_attr($end_date) . '"></label>';
    $filter_form .= '<button class="gc-button is-light" type="submit">Buscar</button>';
    $filter_form .= '</form>';

    $rows_html = '';
    $total_general = 0;
    foreach ($ordenes as $orden) {
        $total_general += (float) $orden['total_orden'];
        $rows_html .= '<tr>'
            . '<td><input type="checkbox" name="orden_ids[]" value="' . esc_attr($orden['id']) . '" class="ctp-liq-check"></td>'
            . '<td>' . esc_html($orden['fecha']) . '</td>'
            . '<td>' . esc_html($orden['nro_orden']) . '</td>'
            . '<td>' . esc_html($orden['nombre_trabajo']) . '</td>'
            . '<td>' . esc_html(ctp_format_currency($orden['total_orden'])) . '</td>'
            . '</tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="5" class="gc-table-empty">Sin órdenes pendientes para liquidar.</td></tr>';
    }

    $table_html = '<form class="gc-form" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $table_html .= wp_nonce_field('ctp_generar_liquidacion', '_wpnonce', true, false);
    $table_html .= '<input type="hidden" name="action" value="ctp_generar_liquidacion">';
    $table_html .= '<input type="hidden" name="cliente_id" value="' . esc_attr($cliente_id) . '">';
    $table_html .= '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th></th><th>Fecha</th><th>N° Orden</th><th>Trabajo</th><th>Total</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';
    $table_html .= '<div class="ctp-total-general">Total general: <strong data-ctp-total-liquidacion>' . esc_html(ctp_format_currency($total_general)) . '</strong></div>';
    $table_html .= '<button class="gc-button" type="submit">Generar liquidación (Factura Venta)</button>';
    $table_html .= '</form>';

    $panel_content = gc_render_notice();
    $panel_content .= $filter_form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Liquidaciones CTP', 'Selecciona órdenes pendientes para generar una factura de venta.', $panel_content) . '</div>';
}
