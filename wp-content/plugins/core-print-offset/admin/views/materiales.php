<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$editing = $data['editing'];
$core_active = $data['core_active'];
?>
<div class="wrap">
    <h1><?php esc_html_e( 'Materiales', 'core-print-offset' ); ?></h1>

    <?php if ( ! $core_active ) : ?>
        <p><?php esc_html_e( 'Core Global no está activo. Las acciones están deshabilitadas.', 'core-print-offset' ); ?></p>
    <?php else : ?>
        <form method="post" class="cpo-form">
            <?php wp_nonce_field( 'cpo_material_save', 'cpo_material_nonce' ); ?>
            <input type="hidden" name="material_id" value="<?php echo esc_attr( $editing['id'] ?? 0 ); ?>">
            <table class="form-table">
                <tr>
                    <th><label for="nombre"><?php esc_html_e( 'Nombre', 'core-print-offset' ); ?></label></th>
                    <td><input name="nombre" id="nombre" type="text" value="<?php echo esc_attr( $editing['nombre'] ?? '' ); ?>" required></td>
                </tr>
                <tr>
                    <th><label for="gramaje"><?php esc_html_e( 'Gramaje', 'core-print-offset' ); ?></label></th>
                    <td><input name="gramaje" id="gramaje" type="text" value="<?php echo esc_attr( $editing['gramaje'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="formato_base"><?php esc_html_e( 'Formato base', 'core-print-offset' ); ?></label></th>
                    <td><input name="formato_base" id="formato_base" type="text" value="<?php echo esc_attr( $editing['formato_base'] ?? '' ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="unidad_costo"><?php esc_html_e( 'Unidad de costo', 'core-print-offset' ); ?></label></th>
                    <td>
                        <select name="unidad_costo" id="unidad_costo">
                            <?php
                            $unidad_costo = $editing['unidad_costo'] ?? 'pliego';
                            $options = array( 'pliego', 'resma', 'kg', 'metro' );
                            foreach ( $options as $option ) :
                                printf(
                                    '<option value="%1$s" %2$s>%1$s</option>',
                                    esc_attr( $option ),
                                    selected( $unidad_costo, $option, false )
                                );
                            endforeach;
                            ?>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th><label for="desperdicio_pct"><?php esc_html_e( 'Desperdicio %', 'core-print-offset' ); ?></label></th>
                    <td><input name="desperdicio_pct" id="desperdicio_pct" type="number" step="0.01" value="<?php echo esc_attr( $editing['desperdicio_pct'] ?? 0 ); ?>"></td>
                </tr>
                <tr>
                    <th><label for="activo"><?php esc_html_e( 'Activo', 'core-print-offset' ); ?></label></th>
                    <td><input name="activo" id="activo" type="checkbox" <?php checked( (int) ( $editing['activo'] ?? 1 ), 1 ); ?>></td>
                </tr>
            </table>
            <p><button type="submit" class="button button-primary" name="cpo_material_save"><?php esc_html_e( 'Guardar material', 'core-print-offset' ); ?></button></p>
        </form>

        <hr>
        <h2><?php esc_html_e( 'Agregar precio vigente', 'core-print-offset' ); ?></h2>
        <form method="post" class="cpo-form">
            <?php wp_nonce_field( 'cpo_material_price_add', 'cpo_material_price_nonce' ); ?>
            <table class="form-table">
                <tr>
                    <th><label for="material_price_material_id"><?php esc_html_e( 'Material', 'core-print-offset' ); ?></label></th>
                    <td>
                        <select name="material_price_material_id" id="material_price_material_id">
                            <?php foreach ( $data['materiales'] as $material ) : ?>
                                <option value="<?php echo esc_attr( $material['id'] ); ?>"><?php echo esc_html( $material['nombre'] ); ?></option>
                            <?php endforeach; ?>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th><label for="precio"><?php esc_html_e( 'Precio', 'core-print-offset' ); ?></label></th>
                    <td><input name="precio" id="precio" type="number" step="0.01" required></td>
                </tr>
                <tr>
                    <th><label for="moneda"><?php esc_html_e( 'Moneda', 'core-print-offset' ); ?></label></th>
                    <td><input name="moneda" id="moneda" type="text" value="PYG"></td>
                </tr>
                <tr>
                    <th><label for="proveedor"><?php esc_html_e( 'Proveedor', 'core-print-offset' ); ?></label></th>
                    <td><input name="proveedor" id="proveedor" type="text"></td>
                </tr>
            </table>
            <p><button type="submit" class="button" name="cpo_material_price_add"><?php esc_html_e( 'Agregar precio', 'core-print-offset' ); ?></button></p>
        </form>
    <?php endif; ?>

    <hr>
    <h2><?php esc_html_e( 'Listado de materiales', 'core-print-offset' ); ?></h2>
    <table class="widefat striped">
        <thead>
            <tr>
                <th><?php esc_html_e( 'Nombre', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Formato', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Precio vigente', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Acciones', 'core-print-offset' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ( $data['materiales'] as $material ) : ?>
                <tr>
                    <td><?php echo esc_html( $material['nombre'] ); ?></td>
                    <td><?php echo esc_html( $material['formato_base'] ); ?></td>
                    <td><?php echo esc_html( $material['precio_vigente'] ?? 0 ); ?></td>
                    <td><?php echo esc_html( $material['activo'] ? __( 'Activo', 'core-print-offset' ) : __( 'Inactivo', 'core-print-offset' ) ); ?></td>
                    <td>
                        <a href="<?php echo esc_url( add_query_arg( array( 'page' => 'cpo-materiales', 'cpo_action' => 'edit_material', 'material_id' => $material['id'] ) ) ); ?>" class="button-link"><?php esc_html_e( 'Editar', 'core-print-offset' ); ?></a>
                        <?php if ( $core_active ) : ?>
                            <?php $toggle_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-materiales', 'cpo_action' => 'toggle_material', 'material_id' => $material['id'] ) ), 'cpo_toggle_material' ); ?>
                            <a href="<?php echo esc_url( $toggle_url ); ?>" class="button-link"><?php echo esc_html( $material['activo'] ? __( 'Desactivar', 'core-print-offset' ) : __( 'Activar', 'core-print-offset' ) ); ?></a>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
</div>
