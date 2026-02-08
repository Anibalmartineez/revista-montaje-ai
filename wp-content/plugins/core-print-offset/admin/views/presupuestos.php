<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$editing = $data['editing'];
$payload = $data['editing_payload'] ?? array();
$core_active = $data['core_active'];
$can_edit = ! empty( $data['can_edit'] );
$editing_mode = $data['editing_mode'] ?? '';
$selected_cliente_id = (int) ( $editing['cliente_id'] ?? $editing['core_cliente_id'] ?? 0 );
$selected_material_id = isset( $payload['material_id'] ) ? (int) $payload['material_id'] : (int) ( $editing['material_id'] ?? 0 );
$selected_maquina_id = isset( $payload['maquina_id'] ) ? (int) $payload['maquina_id'] : 0;
$selected_procesos = isset( $payload['procesos'] ) && is_array( $payload['procesos'] ) ? $payload['procesos'] : array();
$dashboard_base_url = cpo_get_offset_dashboard_url();
?>
<div class="wrap">
    <h1><?php esc_html_e( 'Presupuestos', 'core-print-offset' ); ?></h1>

    <?php if ( ! $core_active ) : ?>
        <p><?php esc_html_e( 'Core Global no está activo. Las acciones están deshabilitadas.', 'core-print-offset' ); ?></p>
    <?php else : ?>
        <?php if ( $editing ) : ?>
            <h2><?php esc_html_e( 'Detalle del presupuesto', 'core-print-offset' ); ?></h2>
            <table class="widefat striped" style="max-width: 900px;">
                <tbody>
                    <tr><th><?php esc_html_e( 'ID', 'core-print-offset' ); ?></th><td><?php echo esc_html( $editing['id'] ); ?></td></tr>
                    <tr><th><?php esc_html_e( 'Título', 'core-print-offset' ); ?></th><td><?php echo esc_html( $editing['titulo'] ); ?></td></tr>
                    <tr><th><?php esc_html_e( 'Cliente', 'core-print-offset' ); ?></th><td><?php echo esc_html( $editing['cliente_texto'] ?: '-' ); ?></td></tr>
                    <tr><th><?php esc_html_e( 'Cantidad', 'core-print-offset' ); ?></th><td><?php echo esc_html( $editing['cantidad'] ); ?></td></tr>
                    <tr><th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th><td><?php echo esc_html( ucfirst( $editing['estado'] ) ); ?></td></tr>
                    <tr><th><?php esc_html_e( 'Total', 'core-print-offset' ); ?></th><td><?php echo esc_html( $editing['precio_total'] ); ?></td></tr>
                </tbody>
            </table>

            <h3><?php esc_html_e( 'Snapshot (solo lectura)', 'core-print-offset' ); ?></h3>
            <pre style="background:#fff;border:1px solid #e2e8f0;padding:12px;max-width:900px;white-space:pre-wrap;"><?php echo esc_html( wp_json_encode( $payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE ) ); ?></pre>

            <?php if ( $can_edit && $editing_mode === 'edit_presupuesto' ) : ?>
                <p><?php esc_html_e( 'Modo de edición de emergencia habilitado (solo administradores).', 'core-print-offset' ); ?></p>
                <form method="post" class="cpo-form">
                    <?php wp_nonce_field( 'cpo_presupuesto_save', 'cpo_presupuesto_nonce' ); ?>
                    <input type="hidden" name="presupuesto_id" value="<?php echo esc_attr( $editing['id'] ?? 0 ); ?>">
                    <table class="form-table">
                        <tr>
                            <th><label for="cliente_id"><?php esc_html_e( 'Cliente (Core)', 'core-print-offset' ); ?></label></th>
                            <td>
                                <?php if ( ! empty( $data['core_clients'] ) ) : ?>
                                    <select name="cliente_id" id="cliente_id">
                                        <option value="0"><?php esc_html_e( 'Seleccionar', 'core-print-offset' ); ?></option>
                                        <?php foreach ( $data['core_clients'] as $client ) : ?>
                                            <?php $client_id = is_array( $client ) ? ( $client['id'] ?? 0 ) : 0; ?>
                                            <?php $client_name = is_array( $client ) ? ( $client['nombre'] ?? $client['name'] ?? '' ) : ''; ?>
                                            <option value="<?php echo esc_attr( $client_id ); ?>" <?php selected( $selected_cliente_id, (int) $client_id ); ?>><?php echo esc_html( $client_name ); ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                <?php else : ?>
                                    <input name="cliente_id" id="cliente_id" type="number" value="<?php echo esc_attr( $selected_cliente_id ?: '' ); ?>">
                                <?php endif; ?>
                            </td>
                        </tr>
                        <tr>
                            <th><label for="cliente_texto"><?php esc_html_e( 'Cliente (texto)', 'core-print-offset' ); ?></label></th>
                            <td><input name="cliente_texto" id="cliente_texto" type="text" value="<?php echo esc_attr( $editing['cliente_texto'] ?? '' ); ?>"></td>
                        </tr>
                        <tr>
                            <th><label for="titulo"><?php esc_html_e( 'Título', 'core-print-offset' ); ?></label></th>
                            <td><input name="titulo" id="titulo" type="text" value="<?php echo esc_attr( $editing['titulo'] ?? '' ); ?>" required></td>
                        </tr>
                        <tr>
                            <th><label for="producto"><?php esc_html_e( 'Producto', 'core-print-offset' ); ?></label></th>
                            <td><input name="producto" id="producto" type="text" value="<?php echo esc_attr( $editing['producto'] ?? '' ); ?>"></td>
                        </tr>
                        <tr>
                            <th><label for="formato_final"><?php esc_html_e( 'Formato final', 'core-print-offset' ); ?></label></th>
                            <td><input name="formato_final" id="formato_final" type="text" value="<?php echo esc_attr( $editing['formato_final'] ?? '' ); ?>"></td>
                        </tr>
                        <tr>
                            <th><?php esc_html_e( 'Formato final (mm)', 'core-print-offset' ); ?></th>
                            <td class="cpo-inline">
                                <input name="ancho_mm" type="number" step="0.1" placeholder="<?php esc_attr_e( 'Ancho', 'core-print-offset' ); ?>" value="<?php echo esc_attr( $payload['ancho_mm'] ?? '' ); ?>">
                                <input name="alto_mm" type="number" step="0.1" placeholder="<?php esc_attr_e( 'Alto', 'core-print-offset' ); ?>" value="<?php echo esc_attr( $payload['alto_mm'] ?? '' ); ?>">
                            </td>
                        </tr>
                        <tr>
                            <th><label for="cantidad"><?php esc_html_e( 'Cantidad', 'core-print-offset' ); ?></label></th>
                            <td><input name="cantidad" id="cantidad" type="number" value="<?php echo esc_attr( $editing['cantidad'] ?? 0 ); ?>" required></td>
                        </tr>
                        <tr>
                            <th><label for="material_id"><?php esc_html_e( 'Material', 'core-print-offset' ); ?></label></th>
                            <td>
                                <select name="material_id" id="material_id">
                                    <option value="0"><?php esc_html_e( 'Seleccionar', 'core-print-offset' ); ?></option>
                                    <?php foreach ( $data['materiales'] as $material ) : ?>
                                        <option value="<?php echo esc_attr( $material['id'] ); ?>" <?php selected( $selected_material_id, (int) $material['id'] ); ?>><?php echo esc_html( $material['nombre'] ); ?></option>
                                    <?php endforeach; ?>
                                </select>
                            </td>
                        </tr>
                        <tr>
                            <th><label for="colores"><?php esc_html_e( 'Colores', 'core-print-offset' ); ?></label></th>
                            <td><input name="colores" id="colores" type="text" value="<?php echo esc_attr( $editing['colores'] ?? '' ); ?>" placeholder="4+0"></td>
                        </tr>
                        <tr>
                            <th><label for="caras"><?php esc_html_e( 'Caras', 'core-print-offset' ); ?></label></th>
                            <td><input name="caras" id="caras" type="number" value="<?php echo esc_attr( $editing['caras'] ?? 1 ); ?>"></td>
                        </tr>
                        <tr>
                            <th><label for="formas_por_pliego"><?php esc_html_e( 'Formas por pliego', 'core-print-offset' ); ?></label></th>
                            <td><input name="formas_por_pliego" id="formas_por_pliego" type="number" value="<?php echo esc_attr( $payload['formas_por_pliego'] ?? 1 ); ?>"></td>
                        </tr>
                        <tr>
                            <th><label for="merma_pct"><?php esc_html_e( 'Merma %', 'core-print-offset' ); ?></label></th>
                            <td><input name="merma_pct" id="merma_pct" type="number" step="0.1" value="<?php echo esc_attr( $payload['merma_pct'] ?? 0 ); ?>"></td>
                        </tr>
                        <tr>
                            <th><label for="sangrado_mm"><?php esc_html_e( 'Sangrado (mm)', 'core-print-offset' ); ?></label></th>
                            <td><input name="sangrado_mm" id="sangrado_mm" type="number" step="0.1" value="<?php echo esc_attr( $payload['sangrado_mm'] ?? 0 ); ?>"></td>
                        </tr>
                        <tr>
                            <th><?php esc_html_e( 'Pliego / Formato', 'core-print-offset' ); ?></th>
                            <td class="cpo-inline">
                                <select name="pliego_formato">
                                    <?php
                                    $pliego_formato = $payload['pliego_formato'] ?? '70x100';
                                    $pliego_options = array( '64x88', '70x100', 'custom' );
                                    if ( $pliego_formato && ! in_array( $pliego_formato, $pliego_options, true ) ) {
                                        $pliego_options[] = $pliego_formato;
                                    }
                                    foreach ( $pliego_options as $option ) :
                                        printf(
                                            '<option value="%1$s" %2$s>%1$s</option>',
                                            esc_attr( $option ),
                                            selected( $pliego_formato, $option, false )
                                        );
                                    endforeach;
                                    ?>
                                </select>
                                <label>
                                    <input type="checkbox" name="pliego_personalizado" value="1" <?php checked( ! empty( $payload['pliego_personalizado'] ) ); ?>>
                                    <?php esc_html_e( 'Personalizado', 'core-print-offset' ); ?>
                                </label>
                                <input name="pliego_ancho_mm" type="number" step="0.1" placeholder="<?php esc_attr_e( 'Ancho', 'core-print-offset' ); ?>" value="<?php echo esc_attr( $payload['pliego_ancho_mm'] ?? '' ); ?>">
                                <input name="pliego_alto_mm" type="number" step="0.1" placeholder="<?php esc_attr_e( 'Alto', 'core-print-offset' ); ?>" value="<?php echo esc_attr( $payload['pliego_alto_mm'] ?? '' ); ?>">
                            </td>
                        </tr>
                        <tr>
                            <th><label for="maquina_id"><?php esc_html_e( 'Máquina', 'core-print-offset' ); ?></label></th>
                            <td>
                                <select name="maquina_id" id="maquina_id">
                                    <option value="0"><?php esc_html_e( 'Sin máquina', 'core-print-offset' ); ?></option>
                                    <?php foreach ( $data['maquinas'] as $maquina ) : ?>
                                        <option value="<?php echo esc_attr( $maquina['id'] ); ?>" <?php selected( $selected_maquina_id, (int) $maquina['id'] ); ?>><?php echo esc_html( $maquina['nombre'] ); ?></option>
                                    <?php endforeach; ?>
                                </select>
                            </td>
                        </tr>
                        <tr>
                            <th><label for="horas_maquina"><?php esc_html_e( 'Horas estimadas', 'core-print-offset' ); ?></label></th>
                            <td><input name="horas_maquina" id="horas_maquina" type="number" step="0.01" value="<?php echo esc_attr( $payload['horas_maquina'] ?? 0 ); ?>"></td>
                        </tr>
                        <tr>
                            <th><?php esc_html_e( 'Procesos', 'core-print-offset' ); ?></th>
                            <td>
                                <?php foreach ( $data['procesos'] as $proceso ) : ?>
                                    <label>
                                        <input type="checkbox" name="procesos[]" value="<?php echo esc_attr( $proceso['id'] ); ?>" <?php checked( in_array( (int) $proceso['id'], $selected_procesos, true ) ); ?>>
                                        <?php echo esc_html( $proceso['nombre'] ); ?>
                                    </label><br>
                                <?php endforeach; ?>
                            </td>
                        </tr>
                        <tr>
                            <th><label for="margen_pct"><?php esc_html_e( 'Margen %', 'core-print-offset' ); ?></label></th>
                            <td><input name="margen_pct" id="margen_pct" type="number" step="0.01" value="<?php echo esc_attr( $editing['margen_pct'] ?? 30 ); ?>"></td>
                        </tr>
                        <tr>
                            <th><label for="estado"><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></label></th>
                            <td>
                                <select name="estado" id="estado">
                                    <?php foreach ( array( 'borrador', 'enviado', 'aceptado', 'rechazado' ) as $estado ) : ?>
                                        <option value="<?php echo esc_attr( $estado ); ?>" <?php selected( $editing['estado'] ?? 'borrador', $estado ); ?>><?php echo esc_html( ucfirst( $estado ) ); ?></option>
                                    <?php endforeach; ?>
                                </select>
                            </td>
                        </tr>
                    </table>
                    <p><button type="submit" class="button button-primary" name="cpo_presupuesto_save"><?php esc_html_e( 'Guardar presupuesto', 'core-print-offset' ); ?></button></p>
                </form>
            <?php endif; ?>
        <?php elseif ( ! $can_edit ) : ?>
            <p><?php esc_html_e( 'La edición de presupuestos se gestiona desde el panel web. Aquí solo puedes revisar y ejecutar acciones seguras.', 'core-print-offset' ); ?></p>
        <?php endif; ?>
    <?php endif; ?>

    <hr>
    <h2><?php esc_html_e( 'Listado de presupuestos', 'core-print-offset' ); ?></h2>
    <table class="widefat striped">
        <thead>
            <tr>
                <th><?php esc_html_e( 'Título', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Cliente', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Cantidad', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Estado', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Total', 'core-print-offset' ); ?></th>
                <th><?php esc_html_e( 'Acciones', 'core-print-offset' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ( $data['presupuestos'] as $presupuesto ) : ?>
                <?php
                $cliente_label = $presupuesto['cliente_texto'] ?? '';
                if ( ! $cliente_label && ! empty( $data['core_clients'] ) ) {
                    $cliente_id = (int) ( $presupuesto['cliente_id'] ?? $presupuesto['core_cliente_id'] ?? 0 );
                    foreach ( $data['core_clients'] as $client ) {
                        if ( (int) ( $client['id'] ?? 0 ) === $cliente_id ) {
                            $cliente_label = $client['nombre'] ?? '';
                            break;
                        }
                    }
                }
                ?>
                <tr>
                    <td><?php echo esc_html( $presupuesto['titulo'] ); ?></td>
                    <td><?php echo $cliente_label ? esc_html( $cliente_label ) : '-'; ?></td>
                    <td><?php echo esc_html( $presupuesto['cantidad'] ); ?></td>
                    <td><?php echo esc_html( ucfirst( $presupuesto['estado'] ) ); ?></td>
                    <td><?php echo esc_html( $presupuesto['precio_total'] ); ?></td>
                    <td>
                        <a href="<?php echo esc_url( add_query_arg( array( 'page' => 'cpo-presupuestos', 'cpo_action' => 'view_presupuesto', 'presupuesto_id' => $presupuesto['id'] ) ) ); ?>" class="button-link"><?php esc_html_e( 'Ver', 'core-print-offset' ); ?></a>
                        <?php if ( $can_edit ) : ?>
                            <a href="<?php echo esc_url( add_query_arg( array( 'page' => 'cpo-presupuestos', 'cpo_action' => 'edit_presupuesto', 'presupuesto_id' => $presupuesto['id'] ) ) ); ?>" class="button-link"><?php esc_html_e( 'Editar', 'core-print-offset' ); ?></a>
                        <?php endif; ?>
                        <?php if ( $dashboard_base_url ) : ?>
                            <?php
                            $open_url = add_query_arg( 'cpo_presupuesto_id', $presupuesto['id'], $dashboard_base_url );
                            $open_url .= '#cpo-presupuesto';
                            ?>
                            <a href="<?php echo esc_url( $open_url ); ?>" class="button-link"><?php esc_html_e( 'Abrir en panel web', 'core-print-offset' ); ?></a>
                        <?php endif; ?>
                        <?php $dup_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-presupuestos', 'cpo_action' => 'duplicate_presupuesto', 'presupuesto_id' => $presupuesto['id'] ) ), 'cpo_duplicate_presupuesto' ); ?>
                        <a href="<?php echo esc_url( $dup_url ); ?>" class="button-link"><?php esc_html_e( 'Duplicar', 'core-print-offset' ); ?></a>
                        <?php if ( $core_active ) : ?>
                            <?php $doc_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-presupuestos', 'cpo_action' => 'generate_document', 'presupuesto_id' => $presupuesto['id'] ) ), 'cpo_generate_document' ); ?>
                            <?php if ( ! empty( $presupuesto['core_documento_id'] ) ) : ?>
                                <span class="button-link"><?php echo esc_html( sprintf( __( 'Documento Core #%d', 'core-print-offset' ), (int) $presupuesto['core_documento_id'] ) ); ?></span>
                            <?php else : ?>
                                <a href="<?php echo esc_url( $doc_url ); ?>" class="button-link"><?php esc_html_e( 'Generar documento', 'core-print-offset' ); ?></a>
                            <?php endif; ?>
                            <?php if ( $presupuesto['estado'] === 'aceptado' ) : ?>
                                <?php $orden_url = wp_nonce_url( add_query_arg( array( 'page' => 'cpo-presupuestos', 'cpo_action' => 'convert_to_order', 'presupuesto_id' => $presupuesto['id'] ) ), 'cpo_convert_order' ); ?>
                                <a href="<?php echo esc_url( $orden_url ); ?>" class="button-link"><?php esc_html_e( 'Crear orden', 'core-print-offset' ); ?></a>
                            <?php endif; ?>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
</div>
