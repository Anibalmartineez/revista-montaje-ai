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
    if (!defined('GC_CORE_GLOBAL_API_VERSION')) {
        return false;
    }

    if (!function_exists('gc_api_is_ready')) {
        return false;
    }

    return gc_api_is_ready() && version_compare(GC_CORE_GLOBAL_API_VERSION, '1.0.0', '>=');
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
    echo '<div class="notice notice-warning"><p>'
        . esc_html__('Core Global activo pero la API mínima no está disponible. Actualiza el core para usar CTP Módulo.', 'ctp-modulo')
        . '</p></div>';
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
