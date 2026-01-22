<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_ctp_generar_liquidacion', 'ctp_handle_generar_liquidacion');

function ctp_handle_generar_liquidacion(): void {
    gc_guard_manage_access();
    check_admin_referer('ctp_generar_liquidacion');

    global $wpdb;
    $ordenes_table = ctp_get_table('ctp_ordenes');
    $documentos_table = gc_get_table('gc_documentos');

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
    $count = (int) $wpdb->get_var(
        $wpdb->prepare("SELECT COUNT(*) FROM {$documentos_table} WHERE numero LIKE %s", $prefix . '%')
    );
    $numero = $prefix . ($count + 1);

    $notas = 'Liquidación CTP. Órdenes: #' . implode(', #', $nros);

    $wpdb->insert(
        $documentos_table,
        array(
            'numero' => $numero,
            'fecha' => current_time('Y-m-d'),
            'tipo' => 'venta',
            'cliente_id' => $cliente_id,
            'total' => $total,
            'estado' => 'pendiente',
            'monto_pagado' => 0,
            'saldo' => $total,
            'notas' => $notas,
            'created_at' => gc_now(),
            'updated_at' => gc_now(),
        ),
        array('%s', '%s', '%s', '%d', '%f', '%s', '%f', '%f', '%s', '%s', '%s')
    );

    $documento_id = (int) $wpdb->insert_id;

    foreach ($ordenes as $orden) {
        $wpdb->update(
            $ordenes_table,
            array(
                'estado' => 'liquidada',
                'documento_id' => $documento_id,
                'updated_at' => gc_now(),
            ),
            array('id' => (int) $orden['id']),
            array('%s', '%d', '%s'),
            array('%d')
        );
    }

    ctp_redirect_with_notice('Liquidación generada correctamente.', 'success');
}
