<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$editing = $data['editing'];
$core_active = $data['core_active'];
?>
<div class="wrap">
    <h1><?php esc_html_e( 'Máquinas', 'core-print-offset' ); ?></h1>

    <?php if ( ! $core_active ) : ?>
        <p><?php esc_html_e( 'Core Global no está activo. Las acciones están deshabilitadas.', 'core-print-offset' ); ?></p>
    <?php else : ?>
        <form method="post" class="cpo-form">
            <?php wp_nonce_field( 'cpo_maquina_save', 'cpo_maquina_nonce' ); ?>
            <input type="hidden" name="maquina_id" value="<?php echo esc_attr( $editing['id'] ?? 0 ); ?>">
            <table class="form-table">
                <tr>
                    <th><label for="nombre"><?php esc_html_e( 'Nombre', 'core-print-offset' ); ?></label></th>
                    <td><input name="nombre" id="nombre" type="text" value="<?php echo esc_attr( $editing['nombre'] ?? '' ); ?>" required></td>
                </tr>
                <tr>
                    <th><label for="tipo"><?php esc_html_e( 'Tipo', 'core-print-offset' ); ?></label></th>
                    <td><input name="tipo" id="tipo" type="text" value="<?php echo esc_attr( $editing['tipo'] ?? '' ); ?>" required></td>
                </tr>
                <tr>
                    <th><label for="costo_hora"><?php esc_html_e( 'Costo por hora', 'core-print-offset' ); ?></label></th>
                    <td><input name="costo_hora" id="costo_hora" type="number" step="0.01" value="<?php echo esc_attr( $editing['costo_hora'] ?? 0 ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="rendimiento_hora"><?php esc_html_e( 'Rendimiento / hora', 'core-print-offset' ); ?></label></th>
                    <td><input name="rendimiento_hora" id="rendimiento_hora" type="number" value="<?php echo esc_attr( $editing['rendimiento_hora'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="rendimiento_pliegos_hora"><?php esc_html_e( 'Rendimiento pliegos / hora', 'core-print-offset' ); ?></label></th>
                    <td><input name="rendimiento_pliegos_hora" id="rendimiento_pliegos_hora" type="number" value="<?php echo esc_attr( $editing['rendimiento_pliegos_hora'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="setup_min"><?php esc_html_e( 'Setup (min)', 'core-print-offset' ); ?></label></th>
                    <td><input name="setup_min" id="setup_min" type="number" step="0.01" value="<?php echo esc_attr( $editing['setup_min'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="activo"><?php esc_html_e( 'Activo', 'core-print-offset' ); ?></label></th>
                    <td><input name="activo" id="activo" type="checkbox" <?php checked( (int) ( $editing['activo'] ?? 1 ), 1 ); ?>></td>
                </tr>
            </table>
            <p><button type="submit" class="button button-primary" name="cpo_maquina_save"><?php esc_html_e( 'Guardar máquina', 'core-print-offset' ); ?></button></p>
        </form>
    <?php endif; ?>

    <hr>
    <h2><?php esc_html_e( 'Listado de máquinas', 'core-print-offset' ); ?></h2>
    <table class="widefat striped">
        <thead>
            <tr>
                <th><?php esc_html_e( 'Nombre', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Tipo', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Costo/hora', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Acciones', 'core-print-offset' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ( $data['maquinas'] as $maquina ) : ?>
                <tr>
                    <td><?php echo esc_html( $maquina['nombre'] ); ?></td>
                    <td><?php echo esc_html( $maquina['tipo'] ); ?></td>
                    <td><?php echo esc_html( $maquina['costo_hora'] ); ?></td>
                    <td><?php echo esc_html( $maquina['activo'] ? __( 'Activo', 'core-print-offset' ) : __( 'Inactivo', 'core-print-offset' ) ); ?></td>
                    <td>
                        <a href="<?php echo esc_url( add_query_arg( array( 'page' => 'cpo-maquinas', 'cpo_action' => 'edit_maquina', 'maquina_id' => $maquina['id'] ) ) ); ?>" class="button-link"><?php esc_html_e( 'Editar', 'core-print-offset' ); ?></a>
                        <?php if ( $core_active ) : ?>
                            <?php $toggle_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-maquinas', 'cpo_action' => 'toggle_maquina', 'maquina_id' => $maquina['id'] ) ), 'cpo_toggle_maquina' ); ?>
                            <a href="<?php echo esc_url( $toggle_url ); ?>" class="button-link"><?php echo esc_html( $maquina['activo'] ? __( 'Desactivar', 'core-print-offset' ) : __( 'Activar', 'core-print-offset' ) ); ?></a>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
</div>
