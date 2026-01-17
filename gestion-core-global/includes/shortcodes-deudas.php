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
    $periodo_actual = gc_get_periodo_actual();
    $hide_paid = isset($_GET['ocultar_pagadas']) && sanitize_text_field(wp_unslash($_GET['ocultar_pagadas'])) === '1';

    $edit_id = absint($_GET['edit_deuda'] ?? 0);
    $edit_data = array(
        'nombre' => '',
        'categoria' => '',
        'tipo_deuda' => 'recurrente',
        'monto' => '',
        'frecuencia' => 'mensual',
        'dia_vencimiento' => '',
        'dia_semana' => '',
        'vencimiento' => '',
        'cuotas_total' => '',
        'cuota_monto' => '',
        'fecha_inicio' => '',
        'activo' => 1,
        'notas' => '',
    );

    if ($edit_id) {
        $edit_row = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $edit_id), ARRAY_A);
        if ($edit_row) {
            $edit_data = array_merge($edit_data, $edit_row);
            $edit_data['tipo_deuda'] = gc_get_deuda_tipo($edit_data);
            if (empty($edit_data['dia_vencimiento']) && !empty($edit_data['dia_sugerido'])) {
                $edit_data['dia_vencimiento'] = $edit_data['dia_sugerido'];
            }
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
        . '<label>Categoría<input type="text" name="categoria" value="' . esc_attr(gc_field_value($edit_data, 'categoria')) . '"></label>'
        . '<label>Tipo<select name="tipo_deuda">' . gc_select_options(array('unica' => 'Única', 'recurrente' => 'Recurrente', 'prestamo' => 'Préstamo'), gc_field_value($edit_data, 'tipo_deuda')) . '</select></label>'
        . '<label data-gc-show-deuda="unica,recurrente">Monto<input type="number" step="0.01" name="monto" value="' . esc_attr(gc_field_value($edit_data, 'monto')) . '"></label>'
        . '<label data-gc-show-deuda="unica">Vencimiento<input type="date" name="vencimiento" value="' . esc_attr(gc_field_value($edit_data, 'vencimiento')) . '"></label>'
        . '<label data-gc-show-deuda="recurrente">Frecuencia<select name="frecuencia">' . gc_select_options(array('mensual' => 'Mensual', 'semanal' => 'Semanal', 'anual' => 'Anual'), gc_field_value($edit_data, 'frecuencia')) . '</select></label>'
        . '<label data-gc-show-deuda="recurrente" data-gc-show-frecuencia="mensual,anual">Día vencimiento<input type="number" min="1" max="31" name="dia_vencimiento" value="' . esc_attr(gc_field_value($edit_data, 'dia_vencimiento')) . '"></label>'
        . '<label data-gc-show-deuda="recurrente" data-gc-show-frecuencia="semanal">Día semana<select name="dia_semana">' . gc_select_options(array('0' => 'Domingo', '1' => 'Lunes', '2' => 'Martes', '3' => 'Miércoles', '4' => 'Jueves', '5' => 'Viernes', '6' => 'Sábado'), gc_field_value($edit_data, 'dia_semana')) . '</select></label>'
        . '<label data-gc-show-deuda="prestamo">Cuotas total<input type="number" min="1" name="cuotas_total" value="' . esc_attr(gc_field_value($edit_data, 'cuotas_total')) . '"></label>'
        . '<label data-gc-show-deuda="prestamo">Monto cuota<input type="number" step="0.01" name="cuota_monto" value="' . esc_attr(gc_field_value($edit_data, 'cuota_monto')) . '"></label>'
        . '<label data-gc-show-deuda="prestamo">Fecha inicio<input type="date" name="fecha_inicio" value="' . esc_attr(gc_field_value($edit_data, 'fecha_inicio')) . '"></label>'
        . '</div>';

    $total_calculado = 0;
    if (gc_field_value($edit_data, 'cuotas_total') && gc_field_value($edit_data, 'cuota_monto')) {
        $total_calculado = (float) gc_field_value($edit_data, 'cuotas_total') * (float) gc_field_value($edit_data, 'cuota_monto');
    }

    $form .= '<p class="gc-help" data-gc-show-deuda="prestamo">Total calculado: ' . esc_html(gc_format_currency($total_calculado)) . '</p>'
        . '<label class="gc-checkbox"><input type="checkbox" name="activo" value="1"' . (gc_field_value($edit_data, 'activo') ? ' checked' : '') . '> Activa</label>'
        . '<label>Notas<textarea name="notas" rows="2">' . esc_textarea(gc_field_value($edit_data, 'notas')) . '</textarea></label>'
        . '<button class="gc-button" type="submit">' . ($edit_id ? 'Actualizar deuda' : 'Agregar deuda') . '</button>'
        . '</form>';

    $rows_html = '';
    foreach ($rows as $row) {
        $tipo = gc_get_deuda_tipo($row);
        $estado = $row['estado'] ?? 'pendiente';
        $monto = (float) $row['monto'];
        $pagado = (float) ($row['monto_pagado'] ?? 0);
        $saldo = (float) ($row['saldo'] ?? 0);
        $vencimiento = $row['vencimiento'] ?: '-';
        $detalle = '';

        if ($tipo === 'recurrente') {
            $instancia = gc_ensure_recurrente_instancia($row, $periodo_actual);
            $estado = $instancia['estado'] ?? 'pendiente';
            $monto = isset($instancia['monto']) ? (float) $instancia['monto'] : 0;
            $pagado = isset($instancia['monto_pagado']) ? (float) $instancia['monto_pagado'] : 0;
            $saldo = isset($instancia['saldo']) ? (float) $instancia['saldo'] : 0;
            $vencimiento = $instancia['vencimiento'] ?? '-';
            $detalle = 'Periodo ' . $periodo_actual;
        } elseif ($tipo === 'prestamo') {
            gc_generate_prestamo_instancias($row);
            $totals = gc_recalculate_prestamo_estado((int) $row['id']);
            $estado = $totals['estado'] ?? $estado;
            $monto = $totals['total_calculado'] ?? $monto;
            $pagado = $totals['monto_pagado'] ?? $pagado;
            $saldo = $totals['saldo'] ?? $saldo;
            $instancia = gc_get_prestamo_instancia_actual($row);
            if ($instancia) {
                $detalle = 'Cuota actual ' . $instancia['periodo'] . ' (' . $instancia['estado'] . ')';
                $vencimiento = $instancia['vencimiento'] ?? $vencimiento;
            } else {
                $detalle = 'Sin cuotas pendientes';
                $vencimiento = '-';
            }
        }

        if ($tipo === 'unica') {
            $estado = $row['estado'] ?? 'pendiente';
            $detalle = $row['vencimiento'] ? 'Vencimiento ' . $row['vencimiento'] : '';
        }

        if ($hide_paid && $estado === 'pagada') {
            continue;
        }

        $estado_activo = $row['activo'] ? 'Activa' : 'Inactiva';
        $rows_html .= '<tr>'
            . '<td>' . esc_html($row['nombre']) . '</td>'
            . '<td>' . esc_html(ucfirst($tipo)) . '</td>'
            . '<td>' . esc_html($row['categoria'] ?: '-') . '</td>'
            . '<td>' . esc_html(gc_format_currency($monto)) . '</td>'
            . '<td>' . esc_html(gc_format_currency($pagado)) . '</td>'
            . '<td>' . esc_html(gc_format_currency($saldo)) . '</td>'
            . '<td>' . esc_html($vencimiento) . '</td>'
            . '<td>' . esc_html($estado) . '</td>'
            . '<td>' . esc_html($estado_activo) . '</td>'
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
        $rows_html .= '<tr class="gc-table-secondary"><td colspan="10">'
            . ($detalle ? '<p class="gc-help">' . esc_html($detalle) . '</p>' : '')
            . gc_render_deuda_pago_form($row)
            . '</td></tr>';
    }

    if (!$rows_html) {
        $rows_html = '<tr><td colspan="10" class="gc-table-empty">Sin deudas registradas.</td></tr>';
    }

    $table_html = '<div class="gc-table-wrap"><table class="gc-table">'
        . '<thead><tr><th>Nombre</th><th>Tipo</th><th>Categoría</th><th>Monto</th><th>Pagado</th><th>Saldo</th><th>Vencimiento</th><th>Estado</th><th>Activa</th><th>Acciones</th></tr></thead>'
        . '<tbody>' . $rows_html . '</tbody></table></div>';

    $filter_form = '<form class="gc-form gc-form-inline" method="get">'
        . '<label class="gc-checkbox"><input type="checkbox" name="ocultar_pagadas" value="1"' . ($hide_paid ? ' checked' : '') . '> Ocultar pagadas</label>'
        . '<button class="gc-button is-light" type="submit">Aplicar</button>'
        . '</form>';

    $panel_content = gc_render_notice();
    $panel_content .= $form;
    $panel_content .= $filter_form;
    $panel_content .= $table_html;

    return '<div class="gc-app">' . gc_wrap_panel('Deudas de la empresa', 'Controla compromisos recurrentes y pagos parciales.', $panel_content) . '</div>';
}

function gc_render_deuda_pago_form(array $deuda): string {
    $tipo = gc_get_deuda_tipo($deuda);
    $monto_default = (float) ($deuda['monto'] ?? 0);
    $titulo = 'Registrar pago';
    if ($tipo === 'recurrente') {
        $instancia = gc_ensure_recurrente_instancia($deuda);
        if ($instancia) {
            $titulo = 'Registrar pago (periodo ' . $instancia['periodo'] . ')';
            $monto_default = (float) ($instancia['saldo'] ?? $instancia['monto'] ?? 0);
        }
    } elseif ($tipo === 'prestamo') {
        gc_generate_prestamo_instancias($deuda);
        $instancia = gc_get_prestamo_instancia_actual($deuda);
        if ($instancia) {
            $titulo = 'Registrar pago cuota ' . $instancia['periodo'];
            $monto_default = (float) ($instancia['saldo'] ?? $instancia['monto'] ?? 0);
        } else {
            $titulo = 'Préstamo sin cuotas pendientes';
            $monto_default = 0;
        }
    } else {
        $monto_default = (float) ($deuda['saldo'] ?? $monto_default);
    }

    $form = '<form class="gc-form gc-form-inline" method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
    $form .= wp_nonce_field('gc_add_deuda_pago', '_wpnonce', true, false);
    $form .= '<input type="hidden" name="action" value="gc_add_deuda_pago">';
    $form .= '<input type="hidden" name="deuda_id" value="' . esc_attr($deuda['id']) . '">';
    $form .= '<strong>' . esc_html($titulo) . '</strong>';
    $form .= '<label>Fecha<input type="date" name="fecha_pago" value="' . esc_attr(current_time('Y-m-d')) . '"></label>';
    $form .= '<label>Monto<input type="number" step="0.01" name="monto" value="' . esc_attr($monto_default) . '"></label>';
    $form .= '<label>Notas<input type="text" name="notas"></label>';
    $form .= '<button class="gc-button is-light" type="submit">Registrar</button>';
    $form .= '</form>';

    return $form;
}
