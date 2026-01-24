<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
?>
<div class="wrap cpo-dashboard">
    <h1><?php esc_html_e( 'Dashboard Offset', 'core-print-offset' ); ?></h1>
    <div class="cpo-cards">
        <div class="cpo-card">
            <h3><?php esc_html_e( 'Materiales', 'core-print-offset' ); ?></h3>
            <p><?php echo esc_html( $data['materiales'] ); ?></p>
        </div>
        <div class="cpo-card">
            <h3><?php esc_html_e( 'Máquinas', 'core-print-offset' ); ?></h3>
            <p><?php echo esc_html( $data['maquinas'] ); ?></p>
        </div>
        <div class="cpo-card">
            <h3><?php esc_html_e( 'Procesos', 'core-print-offset' ); ?></h3>
            <p><?php echo esc_html( $data['procesos'] ); ?></p>
        </div>
        <div class="cpo-card">
            <h3><?php esc_html_e( 'Presupuestos', 'core-print-offset' ); ?></h3>
            <p><?php echo esc_html( $data['presupuestos'] ); ?></p>
        </div>
        <div class="cpo-card">
            <h3><?php esc_html_e( 'Órdenes', 'core-print-offset' ); ?></h3>
            <p><?php echo esc_html( $data['ordenes'] ); ?></p>
        </div>
    </div>
</div>
