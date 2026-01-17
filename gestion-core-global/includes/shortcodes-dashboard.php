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

    $nav = '<div class="gc-dashboard-nav">'
        . '<a class="gc-dashboard-button" href="#movimientos">Movimientos</a>'
        . '<a class="gc-dashboard-button" href="#clientes">Clientes</a>'
        . '<a class="gc-dashboard-button" href="#proveedores">Proveedores</a>'
        . '<a class="gc-dashboard-button" href="#facturas-venta">Facturas venta</a>'
        . '<a class="gc-dashboard-button" href="#facturas-compra">Facturas compra</a>'
        . '<a class="gc-dashboard-button" href="#deudas">Deudas</a>'
        . '<a class="gc-dashboard-button" href="#reportes">Reportes</a>'
        . '</div>';

    $content = gc_render_notice();
    $content .= $summary;
    $content .= $nav;
    $content .= '<div class="gc-dashboard-content">'
        . '<div id="movimientos">' . do_shortcode('[gc_movimientos]') . '</div>'
        . '<div id="clientes">' . do_shortcode('[gc_clientes]') . '</div>'
        . '<div id="proveedores">' . do_shortcode('[gc_proveedores]') . '</div>'
        . '<div id="facturas-venta">' . do_shortcode('[gc_facturas_venta]') . '</div>'
        . '<div id="facturas-compra">' . do_shortcode('[gc_facturas_compra]') . '</div>'
        . '<div id="deudas">' . do_shortcode('[gc_deudas]') . '</div>'
        . '<div id="reportes">' . do_shortcode('[gc_reportes]') . '</div>'
        . '</div>';

    return '<div class="gc-app gc-dashboard"><div class="gc-shell">'
        . '<div class="gc-dashboard-header"><div><h2>Panel global de gestión</h2><p class="gc-dashboard-subtitle">Visión general financiera y administrativa.</p></div>'
        . '<span class="gc-dashboard-label">Core global</span></div>'
        . $content
        . '</div></div>';
}
