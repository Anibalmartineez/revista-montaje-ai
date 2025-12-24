<?php
/**
 * Plugin Name: CTP Órdenes
 * Description: MVP para cargar y listar órdenes de CTP mediante shortcodes.
 * Version: 0.1.0
 * Author: Equipo Revista Montaje AI
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Crea la tabla necesaria al activar el plugin.
 */
function ctp_ordenes_activate() {
    global $wpdb;

    $table_name = $wpdb->prefix . 'ctp_ordenes';
    $charset_collate = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE {$table_name} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        fecha DATE NOT NULL,
        numero_orden VARCHAR(50) NOT NULL,
        cliente VARCHAR(150) NOT NULL,
        descripcion TEXT NULL,
        cantidad_chapas INT NOT NULL DEFAULT 1,
        medida_chapa VARCHAR(20) NOT NULL,
        precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0,
        total DECIMAL(12,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        UNIQUE KEY numero_orden (numero_orden)
    ) {$charset_collate};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
}
register_activation_hook(__FILE__, 'ctp_ordenes_activate');

/**
 * Encola assets solo cuando se renderiza un shortcode.
 */
function ctp_ordenes_enqueue_assets() {
    static $enqueued = false;
    if ($enqueued) {
        return;
    }

    $plugin_url = plugin_dir_url(__FILE__);

    wp_enqueue_style(
        'ctp-ordenes-style',
        $plugin_url . 'assets/style.css',
        array(),
        '0.1.0'
    );

    wp_enqueue_script(
        'ctp-ordenes-app',
        $plugin_url . 'assets/app.js',
        array(),
        '0.1.0',
        true
    );

    $enqueued = true;
}

/**
 * Shortcode: formulario para cargar una orden.
 */
function ctp_cargar_orden_shortcode() {
    ctp_ordenes_enqueue_assets();

    $mensaje = '';
    $errores = array();

    if (!empty($_POST['ctp_cargar_orden_submit'])) {
        if (!isset($_POST['ctp_cargar_orden_nonce']) || !check_admin_referer('ctp_cargar_orden', 'ctp_cargar_orden_nonce')) {
            $errores[] = 'No se pudo validar la solicitud. Inténtalo nuevamente.';
        } else {
            $fecha = sanitize_text_field($_POST['fecha'] ?? '');
            $numero_orden = sanitize_text_field($_POST['numero_orden'] ?? '');
            $cliente = sanitize_text_field($_POST['cliente'] ?? '');
            $descripcion = sanitize_textarea_field($_POST['descripcion'] ?? '');
            $cantidad_chapas = absint($_POST['cantidad_chapas'] ?? 1);
            $medida_chapa = sanitize_text_field($_POST['medida_chapa'] ?? '');
            $precio_unitario = floatval($_POST['precio_unitario'] ?? 0);

            if (empty($fecha)) {
                $errores[] = 'La fecha es obligatoria.';
            }
            if (empty($numero_orden)) {
                $errores[] = 'El número de orden es obligatorio.';
            }
            if (empty($cliente)) {
                $errores[] = 'El cliente es obligatorio.';
            }
            if ($cantidad_chapas < 1) {
                $cantidad_chapas = 1;
            }
            $medidas_validas = array('510x400', '650x550', '745x605', '1030x770');
            if (!in_array($medida_chapa, $medidas_validas, true)) {
                $errores[] = 'Selecciona una medida de chapa válida.';
            }

            if (empty($errores)) {
                global $wpdb;
                $table_name = $wpdb->prefix . 'ctp_ordenes';

                $existe = $wpdb->get_var(
                    $wpdb->prepare(
                        "SELECT COUNT(*) FROM {$table_name} WHERE numero_orden = %s",
                        $numero_orden
                    )
                );

                if ($existe) {
                    $errores[] = 'El número de orden ya existe. Usa uno diferente.';
                } else {
                    $total = $cantidad_chapas * $precio_unitario;
                    $now = current_time('mysql');

                    $insertado = $wpdb->insert(
                        $table_name,
                        array(
                            'fecha' => $fecha,
                            'numero_orden' => $numero_orden,
                            'cliente' => $cliente,
                            'descripcion' => $descripcion,
                            'cantidad_chapas' => $cantidad_chapas,
                            'medida_chapa' => $medida_chapa,
                            'precio_unitario' => $precio_unitario,
                            'total' => $total,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%s', '%s', '%s', '%s', '%d', '%s', '%f', '%f', '%s', '%s')
                    );

                    if ($insertado) {
                        $mensaje = 'Orden guardada correctamente.';
                        $_POST = array();
                    } else {
                        $errores[] = 'No se pudo guardar la orden. Intenta nuevamente.';
                    }
                }
            }
        }
    }

    $fecha_default = !empty($_POST['fecha']) ? sanitize_text_field($_POST['fecha']) : current_time('Y-m-d');
    $numero_orden_val = !empty($_POST['numero_orden']) ? sanitize_text_field($_POST['numero_orden']) : '';
    $cliente_val = !empty($_POST['cliente']) ? sanitize_text_field($_POST['cliente']) : '';
    $descripcion_val = !empty($_POST['descripcion']) ? sanitize_textarea_field($_POST['descripcion']) : '';
    $cantidad_val = !empty($_POST['cantidad_chapas']) ? absint($_POST['cantidad_chapas']) : 1;
    $medida_val = !empty($_POST['medida_chapa']) ? sanitize_text_field($_POST['medida_chapa']) : '510x400';
    $precio_val = isset($_POST['precio_unitario']) ? floatval($_POST['precio_unitario']) : 0;
    $total_val = $cantidad_val * $precio_val;

    ob_start();
    ?>
    <div class="ctp-form-wrap">
        <?php if (!empty($mensaje)) : ?>
            <div class="ctp-alert ctp-alert-success">
                <?php echo esc_html($mensaje); ?>
            </div>
        <?php endif; ?>

        <?php if (!empty($errores)) : ?>
            <div class="ctp-alert ctp-alert-error">
                <ul>
                    <?php foreach ($errores as $error) : ?>
                        <li><?php echo esc_html($error); ?></li>
                    <?php endforeach; ?>
                </ul>
            </div>
        <?php endif; ?>

        <form method="post" class="ctp-form">
            <?php wp_nonce_field('ctp_cargar_orden', 'ctp_cargar_orden_nonce'); ?>
            <input type="hidden" name="ctp_cargar_orden_submit" value="1">

            <div class="ctp-field">
                <label for="ctp-fecha">Fecha</label>
                <input type="date" id="ctp-fecha" name="fecha" required value="<?php echo esc_attr($fecha_default); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-numero-orden">Número de orden</label>
                <input type="text" id="ctp-numero-orden" name="numero_orden" required value="<?php echo esc_attr($numero_orden_val); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-cliente">Cliente</label>
                <input type="text" id="ctp-cliente" name="cliente" required value="<?php echo esc_attr($cliente_val); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-descripcion">Descripción</label>
                <textarea id="ctp-descripcion" name="descripcion" rows="3"><?php echo esc_textarea($descripcion_val); ?></textarea>
            </div>

            <div class="ctp-field">
                <label for="ctp-cantidad">Cantidad de chapas</label>
                <input type="number" id="ctp-cantidad" class="ctp-quantity" name="cantidad_chapas" min="1" value="<?php echo esc_attr($cantidad_val); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-medida">Medida de chapa</label>
                <select id="ctp-medida" name="medida_chapa" required>
                    <?php
                    $medidas = array('510x400', '650x550', '745x605', '1030x770');
                    foreach ($medidas as $medida) :
                        $selected = $medida === $medida_val ? 'selected' : '';
                        ?>
                        <option value="<?php echo esc_attr($medida); ?>" <?php echo esc_attr($selected); ?>>
                            <?php echo esc_html($medida); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-precio">Precio unitario</label>
                <input type="number" id="ctp-precio" class="ctp-price" name="precio_unitario" step="0.01" min="0" value="<?php echo esc_attr($precio_val); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-total">Total</label>
                <input type="number" id="ctp-total" class="ctp-total" name="total" readonly value="<?php echo esc_attr(number_format($total_val, 2, '.', '')); ?>">
            </div>

            <div class="ctp-field">
                <button type="submit" class="ctp-button">Guardar orden</button>
            </div>
        </form>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('ctp_cargar_orden', 'ctp_cargar_orden_shortcode');

/**
 * Shortcode: tabla con las últimas 50 órdenes.
 */
function ctp_listar_ordenes_shortcode() {
    ctp_ordenes_enqueue_assets();

    global $wpdb;
    $table_name = $wpdb->prefix . 'ctp_ordenes';

    $ordenes = $wpdb->get_results(
        "SELECT fecha, numero_orden, cliente, medida_chapa, cantidad_chapas, precio_unitario, total
         FROM {$table_name}
         ORDER BY fecha DESC, id DESC
         LIMIT 50"
    );

    ob_start();
    ?>
    <div class="ctp-table-wrap">
        <table class="ctp-table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Nº Orden</th>
                    <th>Cliente</th>
                    <th>Medida</th>
                    <th>Cantidad</th>
                    <th>Unitario</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                <?php if (!empty($ordenes)) : ?>
                    <?php foreach ($ordenes as $orden) : ?>
                        <tr>
                            <td><?php echo esc_html($orden->fecha); ?></td>
                            <td><?php echo esc_html($orden->numero_orden); ?></td>
                            <td><?php echo esc_html($orden->cliente); ?></td>
                            <td><?php echo esc_html($orden->medida_chapa); ?></td>
                            <td><?php echo esc_html($orden->cantidad_chapas); ?></td>
                            <td><?php echo esc_html(number_format((float) $orden->precio_unitario, 2, '.', '')); ?></td>
                            <td><?php echo esc_html(number_format((float) $orden->total, 2, '.', '')); ?></td>
                        </tr>
                    <?php endforeach; ?>
                <?php else : ?>
                    <tr>
                        <td colspan="7">No hay órdenes registradas.</td>
                    </tr>
                <?php endif; ?>
            </tbody>
        </table>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('ctp_listar_ordenes', 'ctp_listar_ordenes_shortcode');
