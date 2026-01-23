<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_ctp_save_orden', 'ctp_handle_save_orden');
add_action('admin_post_ctp_update_estado_orden', 'ctp_handle_update_estado_orden');

function ctp_handle_save_orden(): void {
    gc_guard_manage_access();
    check_admin_referer('ctp_save_orden');

    global $wpdb;
    $ordenes_table = ctp_get_table('ctp_ordenes');
    $items_table = ctp_get_table('ctp_orden_items');

    $fecha = gc_parse_date($_POST['fecha'] ?? '');
    $nro_orden = sanitize_text_field(wp_unslash($_POST['nro_orden'] ?? ''));
    $cliente_id = absint($_POST['cliente_id'] ?? 0);
    $nombre_trabajo = sanitize_text_field(wp_unslash($_POST['nombre_trabajo'] ?? ''));
    $descripcion = sanitize_textarea_field(wp_unslash($_POST['descripcion'] ?? ''));

    if (!$fecha || !$nro_orden || !$cliente_id || !$nombre_trabajo) {
        ctp_redirect_with_notice('Completa todos los campos obligatorios.', 'error');
    }

    $existing = $wpdb->get_var(
        $wpdb->prepare("SELECT id FROM {$ordenes_table} WHERE nro_orden = %s", $nro_orden)
    );
    if ($existing) {
        ctp_redirect_with_notice('El número de orden ya existe. Usa un número diferente.', 'error');
    }

    $medidas = isset($_POST['item_medida']) ? (array) wp_unslash($_POST['item_medida']) : array();
    $cantidades = isset($_POST['item_cantidad']) ? (array) wp_unslash($_POST['item_cantidad']) : array();
    $precios = isset($_POST['item_precio_unit']) ? (array) wp_unslash($_POST['item_precio_unit']) : array();

    $medidas_validas = array('510x400', '650x550', '745x605', '1030x770', '1030x790');

    $items = array();
    foreach ($medidas as $index => $medida_raw) {
        $medida = sanitize_text_field($medida_raw);
        $cantidad = isset($cantidades[$index]) ? (int) $cantidades[$index] : 0;
        $precio = isset($precios[$index]) ? (float) str_replace(',', '.', $precios[$index]) : 0;

        if (!$medida || !in_array($medida, $medidas_validas, true) || $cantidad <= 0 || $precio <= 0) {
            continue;
        }

        $total = $cantidad * $precio;

        $items[] = array(
            'medida' => $medida,
            'cantidad' => $cantidad,
            'precio_unit' => $precio,
            'total' => $total,
        );
    }

    if (!$items) {
        ctp_redirect_with_notice('Agrega al menos un ítem válido.', 'error');
    }

    $wpdb->insert(
        $ordenes_table,
        array(
            'fecha' => $fecha,
            'nro_orden' => $nro_orden,
            'cliente_id' => $cliente_id,
            'nombre_trabajo' => $nombre_trabajo,
            'descripcion' => $descripcion,
            'estado' => 'pendiente',
            'created_at' => gc_now(),
            'updated_at' => gc_now(),
        ),
        array('%s', '%s', '%d', '%s', '%s', '%s', '%s', '%s')
    );

    $orden_id = (int) $wpdb->insert_id;
    foreach ($items as $item) {
        $wpdb->insert(
            $items_table,
            array(
                'orden_id' => $orden_id,
                'medida' => $item['medida'],
                'cantidad' => $item['cantidad'],
                'precio_unit' => $item['precio_unit'],
                'total' => $item['total'],
                'created_at' => gc_now(),
            ),
            array('%d', '%s', '%d', '%f', '%f', '%s')
        );
    }

    ctp_redirect_with_notice('Orden creada correctamente.', 'success');
}

function ctp_handle_update_estado_orden(): void {
    gc_guard_manage_access();
    check_admin_referer('ctp_update_estado_orden');

    global $wpdb;
    $ordenes_table = ctp_get_table('ctp_ordenes');

    $orden_id = absint($_POST['orden_id'] ?? 0);
    $estado = sanitize_text_field(wp_unslash($_POST['estado'] ?? ''));

    if (!$orden_id || !in_array($estado, array('pendiente', 'anulada'), true)) {
        ctp_redirect_with_notice('Acción inválida.', 'error');
    }

    $orden = $wpdb->get_row(
        $wpdb->prepare("SELECT estado FROM {$ordenes_table} WHERE id = %d", $orden_id),
        ARRAY_A
    );

    if (!$orden) {
        ctp_redirect_with_notice('Orden no encontrada.', 'error');
    }

    if ($orden['estado'] === 'liquidada') {
        ctp_redirect_with_notice('No se puede modificar una orden liquidada.', 'error');
    }

    $wpdb->update(
        $ordenes_table,
        array(
            'estado' => $estado,
            'updated_at' => gc_now(),
        ),
        array('id' => $orden_id),
        array('%s', '%s'),
        array('%d')
    );

    ctp_redirect_with_notice('Estado actualizado.', 'success');
}
