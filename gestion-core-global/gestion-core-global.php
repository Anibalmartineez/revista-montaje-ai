<?php
/**
 * Plugin Name: Gestión Core Global
 * Description: Core global de gestión financiera y administrativa con shortcodes.
 * Version: 0.1.0
 * Author: Equipo Revista Montaje AI
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

// Official handshake for Core Global detection.
define('GC_CORE_GLOBAL_ACTIVE', true);
define('GC_CORE_GLOBAL_VERSION', '0.1.0');

// Legacy aliases for modules still using CORE_GLOBAL_*.
if (!defined('CORE_GLOBAL_ACTIVE')) {
    define('CORE_GLOBAL_ACTIVE', GC_CORE_GLOBAL_ACTIVE);
}
if (!defined('CORE_GLOBAL_VERSION')) {
    define('CORE_GLOBAL_VERSION', GC_CORE_GLOBAL_VERSION);
}

if (!function_exists('core_global_is_active')) {
    function core_global_is_active(): bool {
        return true;
    }
}
if (!defined('GC_CORE_GLOBAL_API_VERSION')) {
    if (defined('GC_CORE_GLOBAL_API_MIN_VERSION')) {
        define('GC_CORE_GLOBAL_API_VERSION', GC_CORE_GLOBAL_API_MIN_VERSION);
    } else {
        define('GC_CORE_GLOBAL_API_VERSION', '1.0.0');
    }
}
define('GC_CORE_GLOBAL_DB_VERSION', '1.0.0');
define('GC_CORE_GLOBAL_PATH', plugin_dir_path(__FILE__));
define('GC_CORE_GLOBAL_URL', plugin_dir_url(__FILE__));

require_once GC_CORE_GLOBAL_PATH . 'includes/db.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/helpers.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/handlers-movimientos.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/handlers-clientes.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/handlers-proveedores.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/handlers-documentos.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/handlers-deudas.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/handlers-reportes.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/api.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-dashboard.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-movimientos.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-clientes.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-proveedores.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-documentos.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-deudas.php';
require_once GC_CORE_GLOBAL_PATH . 'includes/shortcodes-reportes.php';

register_activation_hook(__FILE__, 'gc_core_global_install');

add_action('wp_enqueue_scripts', 'gc_core_global_enqueue_assets');
add_action('init', 'gc_core_global_maybe_upgrade');
add_action('admin_init', 'gc_core_global_maybe_upgrade');
add_action('init', 'gc_core_global_register_shortcodes');

function gc_core_global_enqueue_assets(): void {
    wp_register_style(
        'gc-core-global-style',
        GC_CORE_GLOBAL_URL . 'assets/style.css',
        array(),
        filemtime(GC_CORE_GLOBAL_PATH . 'assets/style.css')
    );
    wp_register_script(
        'gc-core-global-app',
        GC_CORE_GLOBAL_URL . 'assets/app.js',
        array(),
        filemtime(GC_CORE_GLOBAL_PATH . 'assets/app.js'),
        true
    );

    if (gc_core_global_is_frontend_panel()) {
        wp_enqueue_style('gc-core-global-style');
        wp_enqueue_script('gc-core-global-app');
        wp_localize_script(
            'gc-core-global-app',
            'gcCoreGlobal',
            array(
                'ajaxUrl' => admin_url('admin-ajax.php'),
                'pendingAmountNonce' => wp_create_nonce('gc_pending_amount'),
            )
        );
    }
}

function gc_core_global_is_frontend_panel(): bool {
    if (!is_singular()) {
        return false;
    }
    $post = get_post();
    if (!$post instanceof WP_Post) {
        return false;
    }
    $content = $post->post_content;
    $shortcodes = array(
        'gc_dashboard',
        'gc_movimientos',
        'gc_clientes',
        'gc_proveedores',
        'gc_facturas_venta',
        'gc_facturas_compra',
        'gc_deudas',
        'gc_reportes',
    );

    foreach ($shortcodes as $shortcode) {
        if (has_shortcode($content, $shortcode)) {
            return true;
        }
    }

    return false;
}

function gc_core_global_register_shortcodes(): void {
    add_shortcode('gc_dashboard', 'gc_render_dashboard_shortcode');
    add_shortcode('gc_movimientos', 'gc_render_movimientos_shortcode');
    add_shortcode('gc_clientes', 'gc_render_clientes_shortcode');
    add_shortcode('gc_proveedores', 'gc_render_proveedores_shortcode');
    add_shortcode('gc_facturas_venta', 'gc_render_facturas_venta_shortcode');
    add_shortcode('gc_facturas_compra', 'gc_render_facturas_compra_shortcode');
    add_shortcode('gc_deudas', 'gc_render_deudas_shortcode');
    add_shortcode('gc_reportes', 'gc_render_reportes_shortcode');
}
