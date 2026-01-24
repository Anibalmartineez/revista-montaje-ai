<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$core_active = $data['core_active'];
?>
<div class="wrap">
    <h1><?php esc_html_e( 'Órdenes de Trabajo', 'core-print-offset' ); ?></h1>

    <?php if ( ! $core_active ) : ?>
        <p><?php esc_html_e( 'Core Global no está activo. Las acciones están deshabilitadas.', 'core-print-offset' ); ?></p>
    <?php endif; ?>

    <table class="widefat striped">
        <thead>
            <tr>
                <th><?php esc_html_e( 'Título', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Entrega', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Acciones', 'core-print-offset' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ( $data['ordenes'] as $orden ) : ?>
                <tr>
                    <td><?php echo esc_html( $orden['titulo'] ); ?></td>
                    <td><?php echo esc_html( ucfirst( $orden['estado'] ) ); ?></td>
                    <td><?php echo esc_html( $orden['fecha_entrega'] ); ?></td>
                    <td>
                        <?php if ( $core_active ) : ?>
                            <?php foreach ( array( 'pendiente', 'en_produccion', 'terminado', 'entregado' ) as $estado ) : ?>
                                <?php
                                $status_url = wp_nonce_url(
                                    add_query_arg(
                                        array(
                                            'page' => 'cpo-ordenes',
                                            'cpo_action' => 'update_orden_status',
                                            'orden_id' => $orden['id'],
                                            'estado' => $estado,
                                        )
                                    ),
                                    'cpo_update_orden'
                                );
                                ?>
                                <a href="<?php echo esc_url( $status_url ); ?>" class="button-link"><?php echo esc_html( ucfirst( str_replace( '_', ' ', $estado ) ) ); ?></a>
                            <?php endforeach; ?>
                            <?php $invoice_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-ordenes', 'cpo_action' => 'generate_invoice', 'orden_id' => $orden['id'] ) ), 'cpo_generate_invoice' ); ?>
                            <a href="<?php echo esc_url( $invoice_url ); ?>" class="button-link"><?php esc_html_e( 'Generar factura', 'core-print-offset' ); ?></a>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
</div>
