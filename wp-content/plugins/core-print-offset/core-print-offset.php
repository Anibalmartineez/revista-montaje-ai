<?php
/**
 * Plugin Name: Core Print Offset
 * Description: Módulo de imprentas offset integrado con Core Global.
 * Version: 0.1.0
 * Author: Revista Montaje AI
 * Text Domain: core-print-offset
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

define( 'CPO_VERSION', '0.1.0' );
define( 'CPO_SCHEMA_VERSION', 3 );
define( 'CPO_SNAPSHOT_VERSION', 1 );

define( 'CPO_PLUGIN_FILE', __FILE__ );

define( 'CPO_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );

define( 'CPO_PLUGIN_URL', plugin_dir_url( __FILE__ ) );

require_once CPO_PLUGIN_DIR . 'includes/helpers.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-activator.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-deactivator.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-calculator.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-core-bridge.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-admin-menu.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-public.php';
require_once CPO_PLUGIN_DIR . 'includes/class-cpo-loader.php';

register_activation_hook( __FILE__, array( 'CPO_Activator', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'CPO_Deactivator', 'deactivate' ) );

function cpo_run_plugin() {
    $loader = new CPO_Loader();
    $loader->run();
}

cpo_run_plugin();
