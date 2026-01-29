<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_api_is_ready(): bool {
    if (!defined('GC_CORE_GLOBAL_VERSION') || !function_exists('gc_get_table')) {
        return false;
    }

    global $wpdb;
    $table = gc_get_table('gc_documentos');
    $table_exists = $wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $table));
    if (!$table_exists) {
        return false;
    }

    $required_columns = array('origen', 'ref_id');
    foreach ($required_columns as $column) {
        $exists = $wpdb->get_var($wpdb->prepare("SHOW COLUMNS FROM {$table} LIKE %s", $column));
        if (!$exists) {
            return false;
        }
    }

    return true;
}

function gc_api_get_client_options(): array {
    global $wpdb;
    $table = gc_get_table('gc_clientes');
    $rows = $wpdb->get_results("SELECT id, nombre FROM {$table} ORDER BY nombre ASC", ARRAY_A);
    $options = array();
    foreach ($rows as $row) {
        $options[(int) $row['id']] = $row['nombre'];
    }
    return $options;
}

function gc_api_create_documento_venta(array $args) {
    if (!gc_api_is_ready()) {
        return new WP_Error('gc_api_not_ready', 'El core no está listo para crear documentos.');
    }

    global $wpdb;
    $table = gc_get_table('gc_documentos');

    $total = isset($args['total']) ? (float) str_replace(',', '.', (string) $args['total']) : 0;
    $cliente_id = isset($args['cliente_id']) ? absint($args['cliente_id']) : 0;

    if ($total <= 0) {
        return new WP_Error('gc_api_invalid_total', 'El total del documento debe ser mayor a cero.');
    }

    if (!$cliente_id) {
        return new WP_Error('gc_api_missing_cliente', 'El cliente es obligatorio para crear un documento de venta.');
    }

    $fecha = gc_parse_date($args['fecha'] ?? '');
    $numero = sanitize_text_field(wp_unslash($args['numero'] ?? ''));
    if (!$numero) {
        $numero = 'VENTA-' . gmdate('Ymd-His');
    }

    $notas = sanitize_textarea_field(wp_unslash($args['notas'] ?? ''));

    $data = array(
        'numero' => $numero,
        'fecha' => $fecha,
        'tipo' => 'factura_venta',
        'cliente_id' => $cliente_id,
        'total' => $total,
        'estado' => 'pendiente',
        'monto_pagado' => 0,
        'saldo' => $total,
        'notas' => $notas,
        'created_at' => gc_now(),
        'updated_at' => gc_now(),
    );

    $inserted = $wpdb->insert(
        $table,
        $data,
        array('%s', '%s', '%s', '%d', '%f', '%s', '%f', '%f', '%s', '%s', '%s')
    );

    if (!$inserted) {
        return new WP_Error('gc_api_insert_failed', 'No se pudo crear el documento de venta.');
    }

    return (int) $wpdb->insert_id;
}

function gc_api_add_documento_item(int $documento_id, array $item) {
    global $wpdb;
    $table = gc_get_table('gc_documento_items');
    $exists = $wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $table));

    if (!$exists) {
        return new WP_Error('gc_api_items_unavailable', 'El core no tiene soporte de ítems por documento.');
    }

    $data = array(
        'documento_id' => $documento_id,
        'descripcion' => sanitize_text_field(wp_unslash($item['descripcion'] ?? '')),
        'cantidad' => isset($item['cantidad']) ? (float) $item['cantidad'] : 0,
        'precio_unit' => isset($item['precio_unit']) ? (float) $item['precio_unit'] : 0,
        'total' => isset($item['total']) ? (float) $item['total'] : 0,
        'created_at' => gc_now(),
    );

    $wpdb->insert(
        $table,
        $data,
        array('%d', '%s', '%f', '%f', '%f', '%s')
    );

    return null;
}

function gc_api_link_external_ref(int $documento_id, string $origin, $ref_id): void {
    if (!gc_api_is_ready()) {
        return;
    }

    global $wpdb;
    $table = gc_get_table('gc_documentos');
    $origin = sanitize_text_field($origin);
    $ref_id = is_numeric($ref_id) ? (int) $ref_id : null;

    $wpdb->update(
        $table,
        array(
            'origen' => $origin,
            'ref_id' => $ref_id,
            'updated_at' => gc_now(),
        ),
        array('id' => $documento_id),
        array('%s', '%d', '%s'),
        array('%d')
    );
}

function gc_api_get_documento(int $documento_id) {
    if (!gc_api_is_ready()) {
        return new WP_Error('gc_api_not_ready', 'El core no está listo para consultar documentos.');
    }

    global $wpdb;
    $table = gc_get_table('gc_documentos');
    $documento = $wpdb->get_row(
        $wpdb->prepare("SELECT * FROM {$table} WHERE id = %d", $documento_id),
        ARRAY_A
    );

    if (!$documento) {
        return new WP_Error('gc_api_documento_not_found', 'Documento no encontrado.');
    }

    return $documento;
}

function core_global_get_clients($args = array()) {
    $callback = apply_filters('core_global_get_clients_callback', 'gc_api_get_client_options');

    if (is_string($callback) && function_exists($callback)) {
        if (empty($args)) {
            return call_user_func($callback);
        }
        return call_user_func($callback, $args);
    }

    return new WP_Error('core_global_missing_clients', 'Core Global activo pero sin callback de clientes.');
}

function core_global_create_document($args) {
    $callback = apply_filters('core_global_create_document_callback', 'gc_api_create_documento_venta');

    if (is_string($callback) && function_exists($callback)) {
        return call_user_func($callback, $args);
    }

    return new WP_Error('core_global_missing_create_document', 'Core Global activo pero sin callback para crear documentos.');
}

function core_global_get_document($id) {
    if (!is_numeric($id)) {
        return new WP_Error('core_global_invalid_document', 'ID de documento inválido.');
    }

    if (function_exists('gc_api_get_documento')) {
        return gc_api_get_documento((int) $id);
    }

    return new WP_Error('core_global_missing_get_document', 'Core Global activo pero sin callback para obtener documentos.');
}
