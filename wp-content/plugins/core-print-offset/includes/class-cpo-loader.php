<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Loader {
    public function run() {
        $admin_menu = new CPO_Admin_Menu();
        add_action( 'admin_menu', array( $admin_menu, 'register_menu' ) );
        add_action( 'admin_enqueue_scripts', array( $admin_menu, 'enqueue_assets' ) );
    }
}
