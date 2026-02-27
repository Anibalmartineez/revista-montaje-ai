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
    $liquidacion_ordenes_table = ctp_get_table('ctp_liquidacion_ordenes');

    $cliente_id = absint($_POST['cliente_id'] ?? 0);
    $ordenes_ids = isset($_POST['orden_ids']) ? array_unique(array_filter(array_map('absint', (array) wp_unslash($_POST['orden_ids'])))) : array();
    $detalle_items = isset($_POST['detalle_items']) ? sanitize_key(wp_unslash($_POST['detalle_items'])) : 'orden';

    if (!in_array($detalle_items, array('orden', 'item'), true)) {
        $detalle_items = 'orden';
    }

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

    if (count($ordenes) !== count($ordenes_ids)) {
        ctp_redirect_with_notice('Alguna orden seleccionada no es válida para liquidar.', 'error');
    }

    $total = 0.0;
    $nros = array();
    $document_items = array();

    foreach ($ordenes as $orden) {
        $orden_total = (float) $orden['total_orden'];
        $total += $orden_total;
        $nros[] = $orden['nro_orden'];

        if ($detalle_items === 'item') {
            $orden_items = ctp_get_order_items((int) $orden['id']);
            if (!$orden_items) {
                ctp_redirect_with_notice('No se encontraron ítems en una de las órdenes seleccionadas.', 'error');
            }

            foreach ($orden_items as $item) {
                $item_total = isset($item['total']) ? (float) $item['total'] : 0.0;
                $item_cantidad = isset($item['cantidad']) ? (float) $item['cantidad'] : 0.0;
                $item_precio_unit = isset($item['precio_unit']) ? (float) $item['precio_unit'] : 0.0;

                if ($item_total <= 0 || $item_cantidad <= 0) {
                    ctp_redirect_with_notice('Hay ítems inválidos (cantidad/total) en las órdenes seleccionadas.', 'error');
                }

                $document_items[] = array(
                    'descripcion' => sprintf('CTP Orden #%s - %s', $orden['nro_orden'], (string) $item['medida']),
                    'cantidad' => $item_cantidad,
                    'precio_unit' => $item_precio_unit,
                    'total' => $item_total,
                );
            }

            continue;
        }

        if ($orden_total <= 0) {
            ctp_redirect_with_notice('Hay órdenes con total inválido para liquidar.', 'error');
        }

        $document_items[] = array(
            'descripcion' => sprintf('CTP Orden #%s - %s', $orden['nro_orden'], $orden['nombre_trabajo']),
            'cantidad' => 1,
            'precio_unit' => $orden_total,
            'total' => $orden_total,
        );
    }

    if ($total <= 0) {
        ctp_redirect_with_notice('El total de la liquidación debe ser mayor a cero.', 'error');
    }

    $sum_items = 0.0;
    foreach ($document_items as $doc_item) {
        $sum_items += (float) $doc_item['total'];
    }

    if (abs($sum_items - $total) > 0.01) {
        ctp_redirect_with_notice('La suma de ítems no coincide con el total de la liquidación.', 'error');
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

    $wpdb->query('START TRANSACTION');

    foreach ($document_items as $doc_item) {
        $item_result = gc_api_add_documento_item((int) $documento_id, $doc_item);
        if (is_wp_error($item_result)) {
            $wpdb->query('ROLLBACK');
            ctp_redirect_with_notice($item_result->get_error_message(), 'error');
        }
    }

    foreach ($ordenes as $orden) {
        $updated = $wpdb->update(
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

        if ($updated === false) {
            $wpdb->query('ROLLBACK');
            ctp_redirect_with_notice('No se pudo actualizar el estado de una orden. No se aplicaron cambios.', 'error');
        }

        $inserted_relation = $wpdb->insert(
            $liquidacion_ordenes_table,
            array(
                'documento_id' => (int) $documento_id,
                'orden_id' => (int) $orden['id'],
                'created_at' => gc_now(),
            ),
            array('%d', '%d', '%s')
        );

        if (!$inserted_relation) {
            $wpdb->query('ROLLBACK');
            ctp_redirect_with_notice('No se pudo registrar la relación documento-orden. No se aplicaron cambios.', 'error');
        }
    }

    $wpdb->query('COMMIT');

    gc_api_link_external_ref((int) $documento_id, 'ctp_liquidacion', (int) $documento_id);

    ctp_redirect_with_notice('Liquidación generada correctamente.', 'success');
}
