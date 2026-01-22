<?php

if (!defined('ABSPATH')) {
    exit;
}

function ctp_render_ordenes_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '';
    }

    global $wpdb;
    $ordenes_table = ctp_get_table('ctp_ordenes');
    $clientes_table = gc_get_table('gc_clientes');

    $cliente_filter = absint($_GET['ctp_cliente'] ?? 0);
    $estado_filter = sanitize_text_field(wp_unslash($_GET['ctp_estado'] ?? ''));
    list($start_date, $end_date) = ctp_get_date_range_from_request('ctp_start', 'ctp_end');

    $where = array('o.fecha BETWEEN %s AND %s');
    $params = array($start_date, $end_date);

    if ($cliente_filter) {
        $where[] = 'o.cliente_id = %d';
        $params[] = $cliente_filter;
    }

    if ($estado_filter && in_array($estado_filter, array('pendiente', 'liquidada', 'anulada'), true)) {
        $where[] = 'o.estado = %s';
        $params[] = $estado_filter;
    }

    $where_sql = implode(' AND ', $where);

    $query = $wpdb->prepare(
        "SELECT o.*, c.nombre as cliente_nombre, COALESCE(SUM(i.total), 0) as total_orden
        FROM {$ordenes_table} o
        LEFT JOIN {$clientes_table} c ON c.id = o.cliente_id
        LEFT JOIN " . ctp_get_table('ctp_orden_items') . " i ON i.orden_id = o.id
        WHERE {$where_sql}
        GROUP BY o.id
        ORDER BY o.fecha DESC, o.id DESC",
        $params
    );

    $ordenes = $wpdb->get_results($query, ARRAY_A);

    $items_by_order = array();
    if ($ordenes) {
        $order_ids = wp_list_pluck($ordenes, 'id');
        $placeholders = implode(',', array_fill(0, count($order_ids), '%d'));
        $items_query = $wpdb->prepare(
            "SELECT * FROM " . ctp_get_table('ctp_orden_items') . " WHERE orden_id IN ({$placeholders}) ORDER BY id ASC",
            $order_ids
        );
        $items = $wpdb->get_results($items_query, ARRAY_A);
        foreach ($items as $item) {
            $items_by_order[$item['orden_id']][] = $item;
        }
    }

    $medidas = array(
        '510x400' => '510x400',
        '650x550' => '650x550',
        '745x605' => '745x605',
        '1030x770' => '1030x770',
        '1030x790' => '1030x790',
        'otra' => 'Otra…',
    );

    $form = '<form class="gc-form ctp-form" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('ctp_save_orden', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="ctp_save_orden">';
    $form .= '<div class="gc-form-grid">'
        . '<label>Fecha<input type="date" name="fecha" value="' . esc_attr(current_time('Y-m-d')) . '"></label>'
        . '<label>N° Orden<input type="text" name="nro_orden" required></label>'
        . '<label>Cliente<select name="cliente_id" required>' . gc_select_options(ctp_get_clientes_options(), '') . '</select></label>'
        . '<label>Nombre del trabajo<input type="text" name="nombre_trabajo" required></label>'
        . '</div>'
        . '<label>Descripción<textarea name="descripcion" rows="2"></textarea></label>';

    $form .= '<div class="ctp-items" data-ctp-items>
        <div class="ctp-item-row" data-ctp-item>
            <label>Medida
                <select name="item_medida[]" class="ctp-medida" required>' . gc_select_options($medidas, '') . '</select>
                <input type="text" name="item_medida_otro[]" class="ctp-medida-otro" placeholder="Medida" style="display:none;">
            </label>
            <label>Cantidad<input type="number" min="1" name="item_cantidad[]" class="ctp-cantidad" required></label>
            <label>Precio unitario<input type="number" step="0.01" min="0" name="item_precio_unit[]" class="ctp-precio" required></label>
            <label>Total<input type="number" step="0.01" name="item_total[]" class="ctp-total" readonly></label>
        </div>
    </div>';

    $form .= '<button class="gc-button is-light ctp-add-item" type="button">+ Agregar otro trabajo</button>';
    $form .= '<div class="ctp-total-general">Total orden: <strong data-ctp-total-general>0</strong></div>';
    $form .= '<button class="gc-button" type="submit">Guardar orden</button>';
    $form .= '</form>';

    $filter_form = '<form class="gc-form gc-form-inline ctp-filters" method="get">';
    $filter_form .= '<label>Cliente<select name="ctp_cliente">' . gc_select_options(ctp_get_clientes_options(), $cliente_filter) . '</select></label>';
    $filter_form .= '<label>Desde<input type="date" name="ctp_start" value="' . esc_attr($start_date) . '"></label>';
    $filter_form .= '<label>Hasta<input type="date" name="ctp_end" value="' . esc_attr($end_date) . '"></label>';
    $filter_form .= '<label>Estado<select name="ctp_estado">' . gc_select_options(array('' => 'Todos', 'pendiente' => 'Pendiente', 'liquidada' => 'Liquidada', 'anulada' => 'Anulada'), $estado_filter) . '</select></label>';
    $filter_form .= '<button class="gc-button is-light" type="submit">Filtrar</button>';
    $filter_form .= '</form>';

    $rows_html = '';
    foreach ($ordenes as $orden) {
        $estado_label = ucfirst($orden['estado']);
        $estado_class = 'is-' . $orden['estado'];
        $actions = '';

        if ($orden['estado'] !== 'liquidada') {
            if ($orden['estado'] === 'anulada') {
                $actions .= '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '">'
                    . wp_nonce_field('ctp_update_estado_orden', '_wpnonce', true, false)
                    . '<input type="hidden" name="action" value="ctp_update_estado_orden">'
                    . '<input type="hidden" name="orden_id" value="' . esc_attr($orden['id']) . '">' 
                    . '<input type="hidden" name="estado" value="pendiente">'
                    . '<button type="submit" class="gc-link">Marcar pendiente</button>'
                    . '</form>';
            } else {
                $actions .= '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'¿Anular orden?\')">'
                    . wp_nonce_field('ctp_update_estado_orden', '_wpnonce', true, false)
                    . '<input type="hidden" name="action" value="ctp_update_estado_orden">'
                    . '<input type="hidden" name="orden_id" value="' . esc_attr($orden['id']) . '">' 
                    . '<input type="hidden" name="estado" value="anulada">'
                    . '<button type="submit" class="gc-link is-danger">Anular</button>'
                    . '</form>';
            }
        }

        $items_html = '';
        $items = $items_by_order[$orden['id']] ?? array();
        foreach ($items as $item) {
            $items_html .= '<li>' . esc_html($item['medida']) . ' - ' . esc_html($item['cantidad']) . ' x ' . esc_html(ctp_format_currency($item['precio_unit'])) . ' = ' . esc_html(ctp_format_currency($item['total'])) . '</li>';
        }
        if (!$items_html) {
            $items_html = '<li>Sin ítems.</li>';
        }

        $rows_html .= '<tr>'
            . '<td>' . esc_html($orden['fecha']) . '</td>'
            . '<td>' . esc_html($orden['nro_orden']) . '</td>'
            . '<td>' . esc_html($orden['cliente_nombre']) . '</td>'
            . '<td>' . esc_html($orden['nombre_trabajo']) . '</td>'
            . '<td><span class="gc-badge ' . esc_attr($estado_class) . '">' . esc_html($estado_label) . '</span></td>'
            . '<td>' . esc_html(ctp_format_currency($orden['total_orden'])) . '</td>'
            . '<td class="gc-table-actions">'
            . '<details><summary class="gc-link">Ver detalle</summary><ul class="ctp-items-list">' . $items_html . '</ul></details>'
            . $actions
            . '</td>'
            . '</tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="7" class="gc-table-empty">Sin órdenes registradas.</td></tr>';
    }

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Fecha</th><th>N° Orden</th><th>Cliente</th><th>Trabajo</th><th>Estado</th><th>Total</th><th>Acciones</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';

    $panel_content = gc_render_notice();
    $panel_content .= $form;
    $panel_content .= '<hr class="ctp-divider">';
    $panel_content .= $filter_form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Órdenes CTP', 'Carga y gestiona las órdenes de copiado de chapas.', $panel_content) . '</div>';
}
