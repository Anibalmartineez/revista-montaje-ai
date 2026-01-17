<?php

if (!defined('ABSPATH')) {
    exit;
}

add_action('admin_post_gc_export_movimientos', 'gc_handle_export_movimientos');

function gc_handle_export_movimientos(): void {
    gc_guard_manage_access();
    check_admin_referer('gc_export_movimientos');

    global $wpdb;
    $table = gc_get_table('gc_movimientos');

    $start = isset($_GET['gc_start']) ? sanitize_text_field(wp_unslash($_GET['gc_start'])) : gmdate('Y-m-01');
    $end = isset($_GET['gc_end']) ? sanitize_text_field(wp_unslash($_GET['gc_end'])) : gmdate('Y-m-t');

    $rows = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT * FROM {$table} WHERE fecha BETWEEN %s AND %s ORDER BY fecha DESC",
            $start,
            $end
        ),
        ARRAY_A
    );

    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename=gc-movimientos.csv');

    $output = fopen('php://output', 'w');
    fputcsv($output, array('ID', 'Fecha', 'Tipo', 'Monto', 'Metodo', 'Categoria', 'Descripcion', 'Cliente ID', 'Proveedor ID', 'Documento ID', 'Origen'));

    foreach ($rows as $row) {
        $fields = array(
            $row['id'],
            $row['fecha'],
            $row['tipo'],
            $row['monto'],
            $row['metodo'],
            $row['categoria'],
            $row['descripcion'],
            $row['cliente_id'],
            $row['proveedor_id'],
            $row['documento_id'],
            $row['origen'],
        );
        $safe_fields = array_map('gc_csv_safe', $fields);
        fputcsv($output, $safe_fields);
    }

    fclose($output);
    exit;
}
