<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_render_reportes_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $table = gc_get_table('gc_movimientos');

    list($start, $end) = gc_get_date_range_from_request();
    $totals = gc_get_movimientos_totals($start, $end);

    $categorias = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT categoria, SUM(monto) as total
            FROM {$table}
            WHERE fecha BETWEEN %s AND %s
            GROUP BY categoria
            ORDER BY total DESC",
            $start,
            $end
        ),
        ARRAY_A
    );

    $filters = '<form class="gc-form gc-form-inline" method="get">'
        . '<label>Desde<input type="date" name="gc_start" value="' . esc_attr($start) . '"></label>'
        . '<label>Hasta<input type="date" name="gc_end" value="' . esc_attr($end) . '"></label>'
        . '<button class="gc-button is-light" type="submit">Actualizar</button>'
        . '</form>';

    $summary = '<div class="gc-summary-grid">'
        . '<div class="gc-summary-card"><span class="gc-summary-title">Ingresos</span><span class="gc-summary-value">' . esc_html(gc_format_currency($totals['ingresos'])) . '</span><span class="gc-summary-meta">Período</span></div>'
        . '<div class="gc-summary-card"><span class="gc-summary-title">Egresos</span><span class="gc-summary-value">' . esc_html(gc_format_currency($totals['egresos'])) . '</span><span class="gc-summary-meta">Período</span></div>'
        . '<div class="gc-summary-card"><span class="gc-summary-title">Neto</span><span class="gc-summary-value">' . esc_html(gc_format_currency($totals['neto'])) . '</span><span class="gc-summary-meta">Período</span></div>'
        . '</div>';

    $categorias_html = '';
    foreach ($categorias as $categoria) {
        $label = $categoria['categoria'] ? $categoria['categoria'] : 'Sin categoría';
        $categorias_html .= '<tr><td>' . esc_html($label) . '</td><td>' . esc_html(gc_format_currency($categoria['total'])) . '</td></tr>';
    }

    if (!$categorias_html) {
        $categorias_html = '<tr><td colspan="2" class="gc-table-empty">Sin movimientos en el período.</td></tr>';
    }

    $export_url = wp_nonce_url(
        add_query_arg(
            array(
                'action' => 'gc_export_movimientos',
                'gc_start' => $start,
                'gc_end' => $end,
            ),
            admin_url('admin-post.php')
        ),
        'gc_export_movimientos'
    );

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Categoría</th><th>Total</th></tr></thead>'
        . '<tbody>' . $categorias_html . '</tbody></table></div>';

    $content = gc_render_notice();
    $content .= $filters;
    $content .= $summary;
    $content .= '<div class="gc-panel-note"><a class="gc-button" href="' . esc_url($export_url) . '">Exportar movimientos CSV</a></div>';
    $content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Balance y reportes', 'Analiza ingresos, egresos y categorías.', $content) . '</div>';
}
