<?php
/**
 * Plugin Name: CTP Módulo
 * Description: Módulo de Copiado de Chapas CTP integrado con Gestión Core Global.
 * Version: 0.1.0
 * Author: Equipo Revista Montaje AI
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

define('CTP_MODULO_VERSION', '0.1.0');
define('CTP_MODULO_PATH', plugin_dir_path(__FILE__));
define('CTP_MODULO_URL', plugin_dir_url(__FILE__));

require_once CTP_MODULO_PATH . 'includes/db.php';

register_activation_hook(__FILE__, 'ctp_modulo_install');

function ctp_modulo_is_core_active(): bool {
    // Si el core ya cargó, esta constante existe.
    if (defined('GC_CORE_GLOBAL_VERSION')) {
        return true;
    }

    // Fallback: verificar por ruta del plugin activo
    if (!function_exists('is_plugin_active')) {
        include_once ABSPATH . 'wp-admin/includes/plugin.php';
    }

    return is_plugin_active('gestion-core-global/gestion-core-global.php');
}

function ctp_modulo_is_core_api_ready(): bool {
    $diagnostics = ctp_modulo_get_core_api_diagnostics();
    return $diagnostics['ready'];
}

function ctp_modulo_get_core_api_diagnostics(): array {
    $issues = array();
    $required_version = '1.0.0';
    $found_version = defined('GC_CORE_GLOBAL_API_VERSION') ? GC_CORE_GLOBAL_API_VERSION : null;

    if (!defined('GC_CORE_GLOBAL_API_VERSION')) {
        $issues[] = 'Falta la constante GC_CORE_GLOBAL_API_VERSION en el core.';
    }

    $required_functions = array(
        'gc_api_is_ready',
        'gc_api_get_client_options',
        'gc_api_create_documento_venta',
        'gc_api_add_documento_item',
        'gc_api_link_external_ref',
    );

    $missing_functions = array();
    foreach ($required_functions as $function_name) {
        if (!function_exists($function_name)) {
            $missing_functions[] = $function_name;
        }
    }
    if ($missing_functions) {
        $issues[] = 'Faltan funciones de la API del core: ' . implode(', ', $missing_functions) . '.';
    }

    if (function_exists('gc_api_is_ready') && !gc_api_is_ready()) {
        $issues[] = 'La API del core existe pero no está lista (gc_api_is_ready devolvió false).';
    }

    if ($found_version !== null && version_compare($found_version, $required_version, '<')) {
        $issues[] = sprintf(
            'Versión de API incompatible. Requerida %s, encontrada %s.',
            $required_version,
            $found_version
        );
    }

    return array(
        'ready' => empty($issues),
        'issues' => $issues,
        'required_version' => $required_version,
        'found_version' => $found_version,
    );
}


function ctp_modulo_admin_notice_missing_core(): void {
    if (!current_user_can('activate_plugins')) {
        return;
    }
    echo '<div class="notice notice-error"><p>'
        . esc_html__('CTP Módulo requiere el plugin "Gestión Core Global" activo para funcionar.', 'ctp-modulo')
        . '</p></div>';
}

function ctp_modulo_admin_notice_missing_api(): void {
    if (!current_user_can('activate_plugins')) {
        return;
    }
    $diagnostics = ctp_modulo_get_core_api_diagnostics();
    $message = esc_html__('Core Global activo pero la API mínima no está disponible. Actualiza el core para usar CTP Módulo.', 'ctp-modulo');
    $details = '';
    if (!empty($diagnostics['issues'])) {
        $items = '';
        foreach ($diagnostics['issues'] as $issue) {
            $items .= '<li>' . esc_html($issue) . '</li>';
        }
        $details = '<ul class="ctp-api-details">' . $items . '</ul>';
    }
    echo '<div class="notice notice-warning"><p>' . $message . '</p>' . $details . '</div>';
}

function ctp_modulo_maybe_install_tables(): void {
    if (ctp_modulo_tables_exist()) {
        return;
    }

    ctp_modulo_install();
}

add_action('admin_init', 'ctp_modulo_maybe_install_tables');
add_action('wp_enqueue_scripts', 'ctp_modulo_register_assets');

if (!ctp_modulo_is_core_active()) {
    add_action('admin_notices', 'ctp_modulo_admin_notice_missing_core');
} else {
    if (!ctp_modulo_is_core_api_ready()) {
        add_action('admin_notices', 'ctp_modulo_admin_notice_missing_api');
    }

    require_once CTP_MODULO_PATH . 'includes/helpers.php';
    require_once CTP_MODULO_PATH . 'includes/handlers-ordenes.php';
    require_once CTP_MODULO_PATH . 'includes/handlers-liquidaciones.php';
    require_once CTP_MODULO_PATH . 'includes/shortcodes-ordenes.php';
    require_once CTP_MODULO_PATH . 'includes/shortcodes-liquidaciones.php';

    add_action('init', 'ctp_modulo_register_shortcodes');
}

function ctp_modulo_register_shortcodes(): void {
    add_shortcode('ctp_ordenes', 'ctp_render_ordenes_shortcode');
    add_shortcode('ctp_liquidaciones', 'ctp_render_liquidaciones_shortcode');
}

function ctp_modulo_register_assets(): void {
    wp_register_style(
        'ctp-modulo-style',
        CTP_MODULO_URL . 'assets/style.css',
        array(),
        CTP_MODULO_VERSION
    );
    wp_register_script(
        'ctp-modulo-app',
        CTP_MODULO_URL . 'assets/app.js',
        array(),
        CTP_MODULO_VERSION,
        true
    );
}

function ctp_modulo_enqueue_assets(): void {
    ctp_modulo_register_assets();
    wp_enqueue_style('ctp-modulo-style');
    wp_enqueue_script('ctp-modulo-app');
    wp_localize_script(
        'ctp-modulo-app',
        'ctpModuloData',
        array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('ctp_modulo_nonce'),
        )
    );
}
