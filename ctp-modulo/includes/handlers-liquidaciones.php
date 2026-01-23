<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_ctp_generar_liquidacion', 'ctp_handle_generar_liquidacion');

function ctp_handle_generar_liquidacion(): void {
    gc_guard_manage_access();
    check_admin_referer('ctp_generar_liquidacion');

    if (!ctp_core_api_ready()) {
        ctp_redirect_with_notice('Core Global activo pero la API mínima no está disponible. Actualiza el core.', 'error');
    }

    global $wpdb;
    $ordenes_table = ctp_get_table('ctp_ordenes');

    $cliente_id = absint($_POST['cliente_id'] ?? 0);
    $ordenes_ids = isset($_POST['orden_ids']) ? array_map('absint', (array) wp_unslash($_POST['orden_ids'])) : array();

    if (!$cliente_id || !$ordenes_ids) {
        ctp_redirect_with_notice('Selecciona un cliente y al menos una orden.', 'error');
    }

    $placeholders = implode(',', array_fill(0, count($ordenes_ids), '%d'));
    $query = $wpdb->prepare(
        "SELECT o.*, COALESCE(SUM(i.total), 0) as total_orden
        FROM {$ordenes_table} o
        LEFT JOIN " . ctp_get_table('ctp_orden_items') . " i ON i.orden_id = o.id
        WHERE o.id IN ({$placeholders})
          AND o.cliente_id = %d
          AND o.estado = 'pendiente'
          AND o.documento_id IS NULL
        GROUP BY o.id",
        array_merge($ordenes_ids, array($cliente_id))
    );

    $ordenes = $wpdb->get_results($query, ARRAY_A);
    if (!$ordenes) {
        ctp_redirect_with_notice('No hay órdenes pendientes válidas para liquidar.', 'error');
    }

    $total = 0;
    $nros = array();
    foreach ($ordenes as $orden) {
        $total += (float) $orden['total_orden'];
        $nros[] = $orden['nro_orden'];
    }

    if ($total <= 0) {
        ctp_redirect_with_notice('El total de la liquidación debe ser mayor a cero.', 'error');
    }

    $prefix = 'LIQ-CTP-' . gmdate('Ym') . '-' . $cliente_id . '-';
    $numero = $prefix . wp_generate_password(6, false, false);

    $notas = 'Liquidación CTP. Órdenes: #' . implode(', #', $nros);

    $documento_id = gc_api_create_documento_venta(
        array(
            'numero' => $numero,
            'fecha' => current_time('Y-m-d'),
            'cliente_id' => $cliente_id,
            'total' => $total,
            'notas' => $notas,
        )
    );

    if (is_wp_error($documento_id)) {
        ctp_redirect_with_notice($documento_id->get_error_message(), 'error');
    }

    foreach ($ordenes as $orden) {
        $wpdb->update(
            $ordenes_table,
            array(
                'estado' => 'liquidada',
                'documento_id' => (int) $documento_id,
                'updated_at' => gc_now(),
            ),
            array('id' => (int) $orden['id']),
            array('%s', '%d', '%s'),
            array('%d')
        );
    }

    $ref_id = isset($ordenes[0]['id']) ? (int) $ordenes[0]['id'] : 0;
    gc_api_link_external_ref((int) $documento_id, 'ctp_liquidacion', $ref_id);

    ctp_redirect_with_notice('Liquidación generada correctamente.', 'success');
}
