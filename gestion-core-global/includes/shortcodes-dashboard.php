<?php

if (!defined('ABSPATH')) {
    exit;
}

function gc_render_dashboard_shortcode(): string {
    if (!gc_user_can_manage()) {
        return '<div class="gc-alert is-warning">Debes iniciar sesión con permisos de administrador.</div>';
    }

    $start = gmdate('Y-m-01');
    $end = gmdate('Y-m-t');
    $totals = gc_get_movimientos_totals($start, $end);

    $summary = '<div class="gc-summary-grid">'
        . '<div class="gc-summary-card"><span class="gc-summary-title">Ingresos del mes</span><span class="gc-summary-value">' . esc_html(gc_format_currency($totals['ingresos'])) . '</span></div>'
        . '<div class="gc-summary-card"><span class="gc-summary-title">Egresos del mes</span><span class="gc-summary-value">' . esc_html(gc_format_currency($totals['egresos'])) . '</span></div>'
        . '<div class="gc-summary-card"><span class="gc-summary-title">Neto del mes</span><span class="gc-summary-value">' . esc_html(gc_format_currency($totals['neto'])) . '</span></div>'
        . '</div>';

    $sections = array(
        array(
            'id' => 'movimientos',
            'label' => 'Movimientos',
            'shortcode' => '[gc_movimientos]',
            'order' => 10,
        ),
        array(
            'id' => 'clientes',
            'label' => 'Clientes',
            'shortcode' => '[gc_clientes]',
            'order' => 20,
        ),
        array(
            'id' => 'proveedores',
            'label' => 'Proveedores',
            'shortcode' => '[gc_proveedores]',
            'order' => 30,
        ),
        array(
            'id' => 'facturas-venta',
            'label' => 'Facturas venta',
            'shortcode' => '[gc_facturas_venta]',
            'order' => 40,
        ),
        array(
            'id' => 'facturas-compra',
            'label' => 'Facturas compra',
            'shortcode' => '[gc_facturas_compra]',
            'order' => 50,
        ),
        array(
            'id' => 'deudas',
            'label' => 'Deudas',
            'shortcode' => '[gc_deudas]',
            'order' => 60,
        ),
        array(
            'id' => 'reportes',
            'label' => 'Reportes',
            'shortcode' => '[gc_reportes]',
            'order' => 70,
        ),
    );

    $sections = apply_filters('gc_dashboard_sections', $sections);
    if (!is_array($sections)) {
        $sections = array();
    }

    $normalized_sections = array();
    foreach ($sections as $section) {
        if (!is_array($section)) {
            continue;
        }
        $id = isset($section['id']) ? sanitize_title($section['id']) : '';
        $label = isset($section['label']) ? (string) $section['label'] : '';
        $shortcode = isset($section['shortcode']) ? (string) $section['shortcode'] : '';
        if (!$id || !$label || !$shortcode) {
            continue;
        }
        $normalized_sections[] = array(
            'id' => $id,
            'label' => $label,
            'shortcode' => $shortcode,
            'icon' => isset($section['icon']) ? (string) $section['icon'] : '',
            'order' => isset($section['order']) ? (int) $section['order'] : 100,
        );
    }

    usort(
        $normalized_sections,
        static function (array $a, array $b): int {
            return $a['order'] <=> $b['order'];
        }
    );

    $nav_items = '';
    $sections_html = '';
    foreach ($normalized_sections as $section) {
        $icon_html = $section['icon'] ? '<span class="gc-dashboard-icon">' . esc_html($section['icon']) . '</span>' : '';
        $nav_items .= '<a class="gc-dashboard-button" href="#' . esc_attr($section['id']) . '">' . $icon_html . esc_html($section['label']) . '</a>';
        $sections_html .= '<div id="' . esc_attr($section['id']) . '" class="gc-module" data-gc-module="' . esc_attr($section['id']) . '">'
            . '<div class="gc-module__header">'
            . '<button class="gc-module__toggle" type="button" aria-expanded="false" aria-controls="gc-module-' . esc_attr($section['id']) . '">'
            . $icon_html . esc_html($section['label'])
            . '</button>'
            . '</div>'
            . '<div id="gc-module-' . esc_attr($section['id']) . '" class="gc-module__body" role="region" aria-label="' . esc_attr($section['label']) . '">'
            . do_shortcode($section['shortcode'])
            . '</div>'
            . '</div>';
    }

    $nav = '<div class="gc-dashboard-nav">' . $nav_items . '</div>';

    $content = gc_render_notice();
    $content .= $summary;
    $content .= $nav;
    $content .= '<div class="gc-dashboard-content">' . $sections_html . '</div>';

    return '<div class="gc-app gc-dashboard"><div class="gc-shell">'
        . '<div class="gc-dashboard-header"><div><h2>Panel global de gestión</h2><p class="gc-dashboard-subtitle">Visión general financiera y administrativa.</p></div>'
        . '<span class="gc-dashboard-label">Core global</span></div>'
        . $content
        . '</div></div>';
}
