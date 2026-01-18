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
    return function_exists('gc_get_table') && function_exists('gc_user_can_manage');
}

function ctp_modulo_admin_notice_missing_core(): void {
    if (!current_user_can('activate_plugins')) {
        return;
    }
    echo '<div class="notice notice-error"><p>'
        . esc_html__('CTP Módulo requiere el plugin "Gestión Core Global" activo para funcionar.', 'ctp-modulo')
        . '</p></div>';
}

function ctp_modulo_maybe_install_tables(): void {
    if (ctp_modulo_tables_exist()) {
        return;
    }

    ctp_modulo_install();
}

add_action('admin_init', 'ctp_modulo_maybe_install_tables');

if (!ctp_modulo_is_core_active()) {
    add_action('admin_notices', 'ctp_modulo_admin_notice_missing_core');
    return;
}

require_once CTP_MODULO_PATH . 'includes/helpers.php';
require_once CTP_MODULO_PATH . 'includes/handlers-ordenes.php';
require_once CTP_MODULO_PATH . 'includes/handlers-liquidaciones.php';
require_once CTP_MODULO_PATH . 'includes/shortcodes-ordenes.php';
require_once CTP_MODULO_PATH . 'includes/shortcodes-liquidaciones.php';

add_action('wp_enqueue_scripts', 'ctp_modulo_enqueue_assets');
add_action('init', 'ctp_modulo_register_shortcodes');

function ctp_modulo_register_shortcodes(): void {
    add_shortcode('ctp_ordenes', 'ctp_render_ordenes_shortcode');
    add_shortcode('ctp_liquidaciones', 'ctp_render_liquidaciones_shortcode');
}

function ctp_modulo_enqueue_assets(): void {
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

    if (ctp_modulo_is_frontend_panel()) {
        wp_enqueue_style('ctp-modulo-style');
        wp_enqueue_script('ctp-modulo-app');
    }
}

function ctp_modulo_is_frontend_panel(): bool {
    if (!is_singular()) {
        return false;
    }
    $post = get_post();
    if (!$post instanceof WP_Post) {
        return false;
    }

    $shortcodes = array(
        'ctp_ordenes',
        'ctp_liquidaciones',
    );

    foreach ($shortcodes as $shortcode) {
        if (has_shortcode($post->post_content, $shortcode)) {
            return true;
        }
    }

    return false;
}
