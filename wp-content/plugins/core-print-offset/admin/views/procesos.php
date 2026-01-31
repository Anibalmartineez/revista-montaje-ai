<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$editing = $data['editing'];
$core_active = $data['core_active'];
?>
<div class="wrap">
    <h1><?php esc_html_e( 'Procesos', 'core-print-offset' ); ?></h1>

    <?php if ( ! $core_active ) : ?>
        <p><?php esc_html_e( 'Core Global no está activo. Las acciones están deshabilitadas.', 'core-print-offset' ); ?></p>
    <?php else : ?>
        <form method="post" class="cpo-form">
            <?php wp_nonce_field( 'cpo_proceso_save', 'cpo_proceso_nonce' ); ?>
            <input type="hidden" name="proceso_id" value="<?php echo esc_attr( $editing['id'] ?? 0 ); ?>">
            <table class="form-table">
                <tr>
                    <th><label for="nombre"><?php esc_html_e( 'Nombre', 'core-print-offset' ); ?></label></th>
                    <td><input name="nombre" id="nombre" type="text" value="<?php echo esc_attr( $editing['nombre'] ?? '' ); ?>" required></td>
                </tr>
                <tr>
                    <th><label for="modo_cobro"><?php esc_html_e( 'Modo de cobro', 'core-print-offset' ); ?></label></th>
                    <td>
                        <select name="modo_cobro" id="modo_cobro">
                            <?php
                            $modo = $editing['modo_cobro'] ?? 'fijo';
                            foreach ( array( 'por_hora', 'por_unidad', 'por_pliego', 'por_millar', 'por_m2', 'por_kg', 'fijo' ) as $option ) :
                                printf(
                                    '<option value="%1$s" %2$s>%1$s</option>',
                                    esc_attr( $option ),
                                    selected( $modo, $option, false )
                                );
                            endforeach;
                            ?>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th><label for="costo_base"><?php esc_html_e( 'Costo base', 'core-print-offset' ); ?></label></th>
                    <td><input name="costo_base" id="costo_base" type="number" step="0.01" value="<?php echo esc_attr( $editing['costo_base'] ?? 0 ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="unidad"><?php esc_html_e( 'Unidad', 'core-print-offset' ); ?></label></th>
                    <td><input name="unidad" id="unidad" type="text" value="<?php echo esc_attr( $editing['unidad'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="consumo_g_m2"><?php esc_html_e( 'Consumo (g/m²)', 'core-print-offset' ); ?></label></th>
                    <td><input name="consumo_g_m2" id="consumo_g_m2" type="number" step="0.01" value="<?php echo esc_attr( $editing['consumo_g_m2'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="merma_proceso_pct"><?php esc_html_e( 'Merma proceso %', 'core-print-offset' ); ?></label></th>
                    <td><input name="merma_proceso_pct" id="merma_proceso_pct" type="number" step="0.01" value="<?php echo esc_attr( $editing['merma_proceso_pct'] ?? '' ); ?>"></td>
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
            <p><button type="submit" class="button button-primary" name="cpo_proceso_save"><?php esc_html_e( 'Guardar proceso', 'core-print-offset' ); ?></button></p>
        </form>
    <?php endif; ?>

    <hr>
    <h2><?php esc_html_e( 'Listado de procesos', 'core-print-offset' ); ?></h2>
    <table class="widefat striped">
        <thead>
            <tr>
                <th><?php esc_html_e( 'Nombre', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Modo', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Costo base', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Acciones', 'core-print-offset' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ( $data['procesos'] as $proceso ) : ?>
                <tr>
                    <td><?php echo esc_html( $proceso['nombre'] ); ?></td>
                    <td><?php echo esc_html( $proceso['modo_cobro'] ); ?></td>
                    <td><?php echo esc_html( $proceso['costo_base'] ); ?></td>
                    <td><?php echo esc_html( $proceso['activo'] ? __( 'Activo', 'core-print-offset' ) : __( 'Inactivo', 'core-print-offset' ) ); ?></td>
                    <td>
                        <a href="<?php echo esc_url( add_query_arg( array( 'page' => 'cpo-procesos', 'cpo_action' => 'edit_proceso', 'proceso_id' => $proceso['id'] ) ) ); ?>" class="button-link"><?php esc_html_e( 'Editar', 'core-print-offset' ); ?></a>
                        <?php if ( $core_active ) : ?>
                            <?php $toggle_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-procesos', 'cpo_action' => 'toggle_proceso', 'proceso_id' => $proceso['id'] ) ), 'cpo_toggle_proceso' ); ?>
                            <a href="<?php echo esc_url( $toggle_url ); ?>" class="button-link"><?php echo esc_html( $proceso['activo'] ? __( 'Desactivar', 'core-print-offset' ) : __( 'Activar', 'core-print-offset' ) ); ?></a>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
</div>
