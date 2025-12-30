<?php
/**
 * Plugin Name: CTP Órdenes
 * Description: MVP para cargar y listar órdenes de CTP mediante shortcodes.
 * Version: 0.2.0
 * Author: Equipo Revista Montaje AI
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

define('CTP_ORDENES_VERSION', '0.2.0');

/**
 * Crea la tabla necesaria al activar el plugin.
 */
function ctp_ordenes_create_tables() {
    global $wpdb;

    $table_name = $wpdb->prefix . 'ctp_ordenes';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';
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

    $sql_proveedores = "CREATE TABLE {$table_proveedores} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        nombre VARCHAR(190) NOT NULL,
        ruc VARCHAR(50) NULL,
        telefono VARCHAR(80) NULL,
        email VARCHAR(120) NULL,
        notas TEXT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id)
    ) {$charset_collate};";

    $sql_facturas = "CREATE TABLE {$table_facturas} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        proveedor_id BIGINT UNSIGNED NOT NULL,
        fecha_factura DATE NOT NULL,
        nro_factura VARCHAR(60) NOT NULL,
        concepto VARCHAR(255) NULL,
        monto_total DECIMAL(14,2) NOT NULL DEFAULT 0,
        vencimiento DATE NULL,
        estado_pago VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        monto_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
        saldo DECIMAL(14,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        KEY proveedor_id (proveedor_id),
        KEY estado_pago (estado_pago),
        UNIQUE KEY proveedor_factura_unique (proveedor_id, nro_factura)
    ) {$charset_collate};";

    $sql_pagos = "CREATE TABLE {$table_pagos} (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        factura_id BIGINT UNSIGNED NOT NULL,
        fecha_pago DATE NOT NULL,
        monto DECIMAL(14,2) NOT NULL DEFAULT 0,
        metodo VARCHAR(40) NULL,
        nota VARCHAR(255) NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY  (id),
        KEY factura_id (factura_id)
    ) {$charset_collate};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
    dbDelta($sql_proveedores);
    dbDelta($sql_facturas);
    dbDelta($sql_pagos);
}

function ctp_ordenes_activate() {
    ctp_ordenes_create_tables();
    update_option('ctp_ordenes_version', CTP_ORDENES_VERSION);
}
register_activation_hook(__FILE__, 'ctp_ordenes_activate');

function ctp_ordenes_maybe_upgrade() {
    $version = get_option('ctp_ordenes_version');
    if ($version !== CTP_ORDENES_VERSION) {
        ctp_ordenes_create_tables();
        update_option('ctp_ordenes_version', CTP_ORDENES_VERSION);
    }
}
add_action('plugins_loaded', 'ctp_ordenes_maybe_upgrade');

function ctp_ordenes_should_enqueue_assets() {
    if (!is_singular()) {
        return false;
    }

    global $post;
    if (!$post instanceof WP_Post) {
        return false;
    }

    $shortcodes = array(
        'ctp_cargar_orden',
        'ctp_listar_ordenes',
        'ctp_proveedores',
        'ctp_facturas_proveedor',
        'ctp_dashboard',
    );

    foreach ($shortcodes as $shortcode) {
        if (has_shortcode($post->post_content, $shortcode)) {
            return true;
        }
    }

    return false;
}

/**
 * Encola assets solo cuando se renderiza un shortcode.
 */
function ctp_ordenes_enqueue_assets($force = false) {
    static $enqueued = false;
    if ($enqueued) {
        return;
    }

    if (!$force && !ctp_ordenes_should_enqueue_assets()) {
        return;
    }

    $plugin_url = plugin_dir_url(__FILE__);
    $plugin_path = plugin_dir_path(__FILE__);
    $style_path = $plugin_path . 'assets/style.css';
    $script_path = $plugin_path . 'assets/app.js';
    $style_version = file_exists($style_path) ? filemtime($style_path) : CTP_ORDENES_VERSION;
    $script_version = file_exists($script_path) ? filemtime($script_path) : CTP_ORDENES_VERSION;

    wp_enqueue_style(
        'ctp-ordenes-style',
        $plugin_url . 'assets/style.css',
        array(),
        $style_version
    );

    wp_enqueue_script(
        'ctp-ordenes-app',
        $plugin_url . 'assets/app.js',
        array(),
        $script_version,
        true
    );

    $enqueued = true;
}
add_action('wp_enqueue_scripts', 'ctp_ordenes_enqueue_assets');

function ctp_ordenes_render_alerts($mensajes) {
    if (empty($mensajes)) {
        return;
    }

    foreach ($mensajes as $tipo => $items) {
        if (empty($items)) {
            continue;
        }

        $class = 'ctp-alert';
        if ($tipo === 'success') {
            $class .= ' ctp-alert-success';
        } elseif ($tipo === 'warning') {
            $class .= ' ctp-alert-warning';
        } else {
            $class .= ' ctp-alert-error';
        }
        echo '<div class="' . esc_attr($class) . '"><ul>';
        foreach ($items as $mensaje) {
            echo '<li>' . esc_html($mensaje) . '</li>';
        }
        echo '</ul></div>';
    }
}

function ctp_is_in_dashboard() {
    return !empty($GLOBALS['ctp_in_dashboard']);
}

function ctp_wrap_base($html) {
    return '<div class="ctp-app"><div class="ctp-container"><div class="ctp-content">' . $html . '</div></div></div>';
}

function ctp_wrap_dashboard($html) {
    return '<div class="ctp-app ctp-dashboard"><div class="ctp-dashboard-container">' . $html . '</div></div>';
}

function ctp_ordenes_recalculate_factura($factura_id) {
    global $wpdb;

    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';

    $factura = $wpdb->get_row(
        $wpdb->prepare("SELECT id, monto_total FROM {$table_facturas} WHERE id = %d", $factura_id)
    );

    if (!$factura) {
        return false;
    }

    $monto_total = (float) $factura->monto_total;
    $monto_pagado = (float) $wpdb->get_var(
        $wpdb->prepare(
            "SELECT COALESCE(SUM(monto), 0) FROM {$table_pagos} WHERE factura_id = %d",
            $factura_id
        )
    );

    if ($monto_pagado > $monto_total) {
        $monto_pagado = $monto_total;
    }

    $saldo = $monto_total - $monto_pagado;
    if ($saldo < 0) {
        $saldo = 0;
    }

    if ($monto_pagado <= 0) {
        $estado = 'pendiente';
    } elseif ($monto_pagado < $monto_total) {
        $estado = 'parcial';
    } else {
        $estado = 'pagado';
    }

    $wpdb->update(
        $table_facturas,
        array(
            'monto_pagado' => $monto_pagado,
            'saldo' => $saldo,
            'estado_pago' => $estado,
            'updated_at' => current_time('mysql'),
        ),
        array('id' => $factura_id),
        array('%f', '%f', '%s', '%s'),
        array('%d')
    );

    return array(
        'monto_pagado' => $monto_pagado,
        'saldo' => $saldo,
        'estado_pago' => $estado,
    );
}

/**
 * Shortcode: formulario para cargar una orden.
 */
function ctp_cargar_orden_shortcode() {
    ctp_ordenes_enqueue_assets(true);

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
    <div class="ctp-card ctp-form-wrap">
        <div class="ctp-card-header">
            <h3 class="ctp-card-title">Nueva orden</h3>
            <p class="ctp-card-subtitle">Registra una orden y calcula el total automáticamente.</p>
        </div>
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

        <form method="post" class="ctp-form ctp-form-grid">
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

            <div class="ctp-field ctp-field-full">
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

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button">Guardar orden</button>
            </div>
        </form>
    </div>
    <?php
    $html = ob_get_clean();
    if (ctp_is_in_dashboard()) {
        return $html;
    }
    return ctp_wrap_base($html);
}
add_shortcode('ctp_cargar_orden', 'ctp_cargar_orden_shortcode');

/**
 * Shortcode: tabla con las últimas 50 órdenes.
 */
function ctp_listar_ordenes_shortcode() {
    ctp_ordenes_enqueue_assets(true);

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
    <div class="ctp-card">
        <div class="ctp-card-header">
            <h3 class="ctp-card-title">Últimas órdenes</h3>
            <p class="ctp-card-subtitle">Las 50 órdenes más recientes registradas.</p>
        </div>
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
                            <td data-label="Fecha"><?php echo esc_html($orden->fecha); ?></td>
                            <td data-label="Nº Orden"><?php echo esc_html($orden->numero_orden); ?></td>
                            <td data-label="Cliente"><?php echo esc_html($orden->cliente); ?></td>
                            <td data-label="Medida"><?php echo esc_html($orden->medida_chapa); ?></td>
                            <td data-label="Cantidad"><?php echo esc_html($orden->cantidad_chapas); ?></td>
                            <td data-label="Unitario"><?php echo esc_html(number_format((float) $orden->precio_unitario, 0, ',', '.')); ?></td>
                            <td data-label="Total"><?php echo esc_html(number_format((float) $orden->total, 0, ',', '.')); ?></td>
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
    </div>
    <?php
    $html = ob_get_clean();
    if (ctp_is_in_dashboard()) {
        return $html;
    }
    return ctp_wrap_base($html);
}
add_shortcode('ctp_listar_ordenes', 'ctp_listar_ordenes_shortcode');

/**
 * Shortcode: gestión de proveedores.
 */
function ctp_proveedores_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    if (!empty($_POST['ctp_proveedor_action'])) {
        $action = sanitize_text_field(wp_unslash($_POST['ctp_proveedor_action']));

        if ($action === 'add') {
            if (!isset($_POST['ctp_proveedor_nonce']) || !check_admin_referer('ctp_proveedor_add', 'ctp_proveedor_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para agregar proveedor.';
            } else {
                $nombre = sanitize_text_field(wp_unslash($_POST['nombre'] ?? ''));
                $ruc = sanitize_text_field(wp_unslash($_POST['ruc'] ?? ''));
                $telefono = sanitize_text_field(wp_unslash($_POST['telefono'] ?? ''));
                $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
                $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

                if (empty($nombre)) {
                    $mensajes['error'][] = 'El nombre del proveedor es obligatorio.';
                } else {
                    $now = current_time('mysql');
                    $inserted = $wpdb->insert(
                        $table_proveedores,
                        array(
                            'nombre' => $nombre,
                            'ruc' => $ruc,
                            'telefono' => $telefono,
                            'email' => $email,
                            'notas' => $notas,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%s', '%s', '%s', '%s', '%s', '%s', '%s')
                    );

                    if ($inserted) {
                        $mensajes['success'][] = 'Proveedor agregado correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo guardar el proveedor.';
                    }
                }
            }
        } elseif ($action === 'edit') {
            if (!isset($_POST['ctp_proveedor_nonce']) || !check_admin_referer('ctp_proveedor_edit', 'ctp_proveedor_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para editar proveedor.';
            } else {
                $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                $nombre = sanitize_text_field(wp_unslash($_POST['nombre'] ?? ''));
                $ruc = sanitize_text_field(wp_unslash($_POST['ruc'] ?? ''));
                $telefono = sanitize_text_field(wp_unslash($_POST['telefono'] ?? ''));
                $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
                $notas = sanitize_textarea_field(wp_unslash($_POST['notas'] ?? ''));

                if ($proveedor_id <= 0 || empty($nombre)) {
                    $mensajes['error'][] = 'Datos inválidos para actualizar proveedor.';
                } else {
                    $actualizado = $wpdb->update(
                        $table_proveedores,
                        array(
                            'nombre' => $nombre,
                            'ruc' => $ruc,
                            'telefono' => $telefono,
                            'email' => $email,
                            'notas' => $notas,
                            'updated_at' => current_time('mysql'),
                        ),
                        array('id' => $proveedor_id),
                        array('%s', '%s', '%s', '%s', '%s', '%s'),
                        array('%d')
                    );

                    if ($actualizado !== false) {
                        $mensajes['success'][] = 'Proveedor actualizado correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo actualizar el proveedor.';
                    }
                }
            }
        } elseif ($action === 'delete') {
            if (!isset($_POST['ctp_proveedor_nonce']) || !check_admin_referer('ctp_proveedor_delete', 'ctp_proveedor_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para eliminar proveedor.';
            } else {
                $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                if ($proveedor_id <= 0) {
                    $mensajes['error'][] = 'Proveedor inválido.';
                } else {
                    $tiene_facturas = (int) $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT COUNT(*) FROM {$table_facturas} WHERE proveedor_id = %d",
                            $proveedor_id
                        )
                    );

                    if ($tiene_facturas > 0) {
                        $mensajes['error'][] = 'No se puede eliminar el proveedor porque tiene facturas asociadas.';
                    } else {
                        $deleted = $wpdb->delete($table_proveedores, array('id' => $proveedor_id), array('%d'));
                        if ($deleted) {
                            $mensajes['success'][] = 'Proveedor eliminado correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo eliminar el proveedor.';
                        }
                    }
                }
            }
        }
    }

    $proveedores = $wpdb->get_results(
        "SELECT * FROM {$table_proveedores} ORDER BY created_at DESC, id DESC LIMIT 100"
    );

    ob_start();
    ?>
    <?php ctp_ordenes_render_alerts($mensajes); ?>
    <div class="ctp-stack">
        <div class="ctp-card ctp-form-wrap">
            <div class="ctp-card-header">
                <h3 class="ctp-card-title">Nuevo proveedor</h3>
                <p class="ctp-card-subtitle">Agrega un proveedor para asociarlo a facturas y pagos.</p>
            </div>
            <form method="post" class="ctp-form ctp-form-grid">
            <?php wp_nonce_field('ctp_proveedor_add', 'ctp_proveedor_nonce'); ?>
            <input type="hidden" name="ctp_proveedor_action" value="add">

            <div class="ctp-field">
                <label for="ctp-proveedor-nombre">Nombre</label>
                <input type="text" id="ctp-proveedor-nombre" name="nombre" required>
            </div>

            <div class="ctp-field">
                <label for="ctp-proveedor-ruc">RUC</label>
                <input type="text" id="ctp-proveedor-ruc" name="ruc">
            </div>

            <div class="ctp-field">
                <label for="ctp-proveedor-telefono">Teléfono</label>
                <input type="text" id="ctp-proveedor-telefono" name="telefono">
            </div>

            <div class="ctp-field">
                <label for="ctp-proveedor-email">Email</label>
                <input type="email" id="ctp-proveedor-email" name="email">
            </div>

            <div class="ctp-field ctp-field-full">
                <label for="ctp-proveedor-notas">Notas</label>
                <textarea id="ctp-proveedor-notas" name="notas" rows="3"></textarea>
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button">Agregar proveedor</button>
            </div>
        </form>
        </div>

        <div class="ctp-card">
            <div class="ctp-card-header">
                <h3 class="ctp-card-title">Proveedores registrados</h3>
                <p class="ctp-card-subtitle">Gestiona los datos principales de cada proveedor.</p>
            </div>
            <div class="ctp-table-wrap">
                <table class="ctp-table">
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>RUC</th>
                    <th>Teléfono</th>
                    <th>Email</th>
                    <th class="ctp-table-text">Notas</th>
                    <th class="ctp-actions-cell">Acciones</th>
                </tr>
            </thead>
            <tbody>
                <?php if (!empty($proveedores)) : ?>
                    <?php foreach ($proveedores as $proveedor) : ?>
                        <tr>
                            <td data-label="Nombre"><?php echo esc_html($proveedor->nombre); ?></td>
                            <td data-label="RUC"><?php echo esc_html($proveedor->ruc); ?></td>
                            <td data-label="Teléfono"><?php echo esc_html($proveedor->telefono); ?></td>
                            <td data-label="Email"><?php echo esc_html($proveedor->email); ?></td>
                            <td class="ctp-table-text" data-label="Notas"><?php echo esc_html($proveedor->notas); ?></td>
                            <td class="ctp-actions-cell" data-label="Acciones">
                                <div class="ctp-actions">
                                    <details class="ctp-details">
                                        <summary class="ctp-button ctp-button-secondary">Editar</summary>
                                        <div class="ctp-details-panel">
                                            <form method="post" class="ctp-inline-form ctp-form-grid">
                                                <?php wp_nonce_field('ctp_proveedor_edit', 'ctp_proveedor_nonce'); ?>
                                                <input type="hidden" name="ctp_proveedor_action" value="edit">
                                                <input type="hidden" name="proveedor_id" value="<?php echo esc_attr($proveedor->id); ?>">
                                                <div class="ctp-field">
                                                    <label>Nombre</label>
                                                    <input type="text" name="nombre" required value="<?php echo esc_attr($proveedor->nombre); ?>">
                                                </div>
                                                <div class="ctp-field">
                                                    <label>RUC</label>
                                                    <input type="text" name="ruc" value="<?php echo esc_attr($proveedor->ruc); ?>">
                                                </div>
                                                <div class="ctp-field">
                                                    <label>Teléfono</label>
                                                    <input type="text" name="telefono" value="<?php echo esc_attr($proveedor->telefono); ?>">
                                                </div>
                                                <div class="ctp-field">
                                                    <label>Email</label>
                                                    <input type="email" name="email" value="<?php echo esc_attr($proveedor->email); ?>">
                                                </div>
                                                <div class="ctp-field ctp-field-full">
                                                    <label>Notas</label>
                                                    <textarea name="notas" rows="2"><?php echo esc_textarea($proveedor->notas); ?></textarea>
                                                </div>
                                                <button type="submit" class="ctp-button ctp-field-full">Guardar</button>
                                            </form>
                                        </div>
                                    </details>
                                    <form method="post" class="ctp-inline-form">
                                        <?php wp_nonce_field('ctp_proveedor_delete', 'ctp_proveedor_nonce'); ?>
                                        <input type="hidden" name="ctp_proveedor_action" value="delete">
                                        <input type="hidden" name="proveedor_id" value="<?php echo esc_attr($proveedor->id); ?>">
                                        <button type="submit" class="ctp-button ctp-button-danger" onclick="return confirm('¿Seguro que deseas eliminar?')">Eliminar</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                <?php else : ?>
                    <tr>
                        <td colspan="6">No hay proveedores registrados.</td>
                    </tr>
                <?php endif; ?>
            </tbody>
                </table>
            </div>
        </div>
    </div>
    <?php
    $html = ob_get_clean();
    if (ctp_is_in_dashboard()) {
        return $html;
    }
    return ctp_wrap_base($html);
}
add_shortcode('ctp_proveedores', 'ctp_proveedores_shortcode');

/**
 * Shortcode: cuentas por pagar de proveedores.
 */
function ctp_facturas_proveedor_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    global $wpdb;
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $table_pagos = $wpdb->prefix . 'ctp_pagos_factura';

    $mensajes = array(
        'success' => array(),
        'error' => array(),
        'warning' => array(),
    );

    if (!empty($_POST['ctp_factura_action'])) {
        $action = sanitize_text_field(wp_unslash($_POST['ctp_factura_action']));

        if ($action === 'add_factura') {
            if (!isset($_POST['ctp_factura_nonce']) || !check_admin_referer('ctp_factura_add', 'ctp_factura_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para agregar factura.';
            } else {
                $proveedor_id = absint($_POST['proveedor_id'] ?? 0);
                $fecha_factura = sanitize_text_field(wp_unslash($_POST['fecha_factura'] ?? ''));
                $nro_factura = sanitize_text_field(wp_unslash($_POST['nro_factura'] ?? ''));
                $concepto = sanitize_text_field(wp_unslash($_POST['concepto'] ?? ''));
                $monto_total = floatval($_POST['monto_total'] ?? 0);
                $vencimiento = sanitize_text_field(wp_unslash($_POST['vencimiento'] ?? ''));

                if ($proveedor_id <= 0) {
                    $mensajes['error'][] = 'Selecciona un proveedor válido.';
                }
                if (empty($fecha_factura)) {
                    $mensajes['error'][] = 'La fecha de factura es obligatoria.';
                }
                if (empty($nro_factura)) {
                    $mensajes['error'][] = 'El número de factura es obligatorio.';
                }
                if ($monto_total <= 0) {
                    $mensajes['error'][] = 'El monto total debe ser mayor a 0.';
                }

                $proveedor_existe = (int) $wpdb->get_var(
                    $wpdb->prepare("SELECT COUNT(*) FROM {$table_proveedores} WHERE id = %d", $proveedor_id)
                );
                if ($proveedor_id > 0 && $proveedor_existe === 0) {
                    $mensajes['error'][] = 'El proveedor seleccionado no existe.';
                }

                if (empty($mensajes['error'])) {
                    $duplicado = (int) $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT COUNT(*) FROM {$table_facturas} WHERE proveedor_id = %d AND nro_factura = %s",
                            $proveedor_id,
                            $nro_factura
                        )
                    );
                    if ($duplicado > 0) {
                        $mensajes['error'][] = 'Ya existe una factura con ese número para este proveedor.';
                    }
                }

                if (empty($mensajes['error'])) {
                    $now = current_time('mysql');
                    $inserted = $wpdb->insert(
                        $table_facturas,
                        array(
                            'proveedor_id' => $proveedor_id,
                            'fecha_factura' => $fecha_factura,
                            'nro_factura' => $nro_factura,
                            'concepto' => $concepto,
                            'monto_total' => $monto_total,
                            'vencimiento' => $vencimiento ?: null,
                            'estado_pago' => 'pendiente',
                            'monto_pagado' => 0,
                            'saldo' => $monto_total,
                            'created_at' => $now,
                            'updated_at' => $now,
                        ),
                        array('%d', '%s', '%s', '%s', '%f', '%s', '%s', '%f', '%f', '%s', '%s')
                    );

                    if ($inserted) {
                        $mensajes['success'][] = 'Factura registrada correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo registrar la factura.';
                    }
                }
            }
        } elseif ($action === 'add_pago') {
            if (!isset($_POST['ctp_factura_nonce']) || !check_admin_referer('ctp_pago_add', 'ctp_factura_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para registrar el pago.';
            } else {
                $factura_id = absint($_POST['factura_id'] ?? 0);
                $fecha_pago = sanitize_text_field(wp_unslash($_POST['fecha_pago'] ?? ''));
                $monto = floatval($_POST['monto'] ?? 0);
                $metodo = sanitize_text_field(wp_unslash($_POST['metodo'] ?? ''));
                $nota = sanitize_text_field(wp_unslash($_POST['nota'] ?? ''));

                if ($factura_id <= 0) {
                    $mensajes['error'][] = 'Factura inválida.';
                }
                if (empty($fecha_pago)) {
                    $fecha_pago = current_time('Y-m-d');
                }
                if ($monto <= 0) {
                    $mensajes['error'][] = 'El monto del pago debe ser mayor a 0.';
                }

                $factura = null;
                if (empty($mensajes['error'])) {
                    $factura = $wpdb->get_row(
                        $wpdb->prepare(
                            "SELECT id, monto_total, monto_pagado FROM {$table_facturas} WHERE id = %d",
                            $factura_id
                        )
                    );
                    if (!$factura) {
                        $mensajes['error'][] = 'No se encontró la factura seleccionada.';
                    }
                }

                if ($factura && empty($mensajes['error'])) {
                    $monto_total = (float) $factura->monto_total;
                    $monto_pagado = (float) $factura->monto_pagado;
                    $saldo = $monto_total - $monto_pagado;

                    if ($saldo <= 0) {
                        $mensajes['error'][] = 'La factura ya está pagada.';
                    } else {
                        if ($monto > $saldo) {
                            $monto = $saldo;
                            $mensajes['warning'][] = 'El monto excedía el saldo. Se registró solo el saldo restante.';
                        }
                        if ($monto <= 0) {
                            $mensajes['error'][] = 'El monto del pago es inválido.';
                        }
                    }
                }

                if (empty($mensajes['error'])) {
                    $inserted = $wpdb->insert(
                        $table_pagos,
                        array(
                            'factura_id' => $factura_id,
                            'fecha_pago' => $fecha_pago,
                            'monto' => $monto,
                            'metodo' => $metodo,
                            'nota' => $nota,
                            'created_at' => current_time('mysql'),
                        ),
                        array('%d', '%s', '%f', '%s', '%s', '%s')
                    );

                    if ($inserted) {
                        ctp_ordenes_recalculate_factura($factura_id);
                        $mensajes['success'][] = 'Pago registrado correctamente.';
                    } else {
                        $mensajes['error'][] = 'No se pudo registrar el pago.';
                    }
                }
            }
        } elseif ($action === 'delete_factura') {
            if (!isset($_POST['ctp_factura_nonce']) || !check_admin_referer('ctp_factura_delete', 'ctp_factura_nonce')) {
                $mensajes['error'][] = 'No se pudo validar la solicitud para eliminar la factura.';
            } else {
                $factura_id = absint($_POST['factura_id'] ?? 0);
                if ($factura_id <= 0) {
                    $mensajes['error'][] = 'Factura inválida.';
                } else {
                    $tiene_pagos = (int) $wpdb->get_var(
                        $wpdb->prepare(
                            "SELECT COUNT(*) FROM {$table_pagos} WHERE factura_id = %d",
                            $factura_id
                        )
                    );
                    if ($tiene_pagos > 0) {
                        $mensajes['error'][] = 'No se puede eliminar la factura porque tiene pagos registrados.';
                    } else {
                        $deleted = $wpdb->delete($table_facturas, array('id' => $factura_id), array('%d'));
                        if ($deleted) {
                            $mensajes['success'][] = 'Factura eliminada correctamente.';
                        } else {
                            $mensajes['error'][] = 'No se pudo eliminar la factura.';
                        }
                    }
                }
            }
        }
    }

    $proveedores = $wpdb->get_results(
        "SELECT id, nombre FROM {$table_proveedores} ORDER BY nombre ASC"
    );

    $estado_filtro = sanitize_text_field(wp_unslash($_GET['estado'] ?? ''));
    $proveedor_filtro = absint($_GET['proveedor_id'] ?? 0);
    $estados_validos = array('pendiente', 'parcial', 'pagado');
    if (!in_array($estado_filtro, $estados_validos, true)) {
        $estado_filtro = '';
    }

    $where = array('1=1');
    $params = array();

    if (!empty($estado_filtro)) {
        $where[] = 'f.estado_pago = %s';
        $params[] = $estado_filtro;
    }
    if ($proveedor_filtro > 0) {
        $where[] = 'f.proveedor_id = %d';
        $params[] = $proveedor_filtro;
    }

    $sql = "SELECT f.*, p.nombre AS proveedor_nombre
            FROM {$table_facturas} f
            LEFT JOIN {$table_proveedores} p ON f.proveedor_id = p.id
            WHERE " . implode(' AND ', $where) . "
            ORDER BY f.fecha_factura DESC, f.id DESC
            LIMIT 100";

    if (!empty($params)) {
        $sql = $wpdb->prepare($sql, $params);
    }

    $facturas = $wpdb->get_results($sql);

    ob_start();
    ?>
    <?php ctp_ordenes_render_alerts($mensajes); ?>
    <div class="ctp-stack">
        <div class="ctp-card ctp-form-wrap">
            <div class="ctp-card-header">
                <h3 class="ctp-card-title">Registrar factura</h3>
                <p class="ctp-card-subtitle">Carga la factura y controla su estado de pago.</p>
            </div>
            <form method="post" class="ctp-form ctp-form-grid">
            <?php wp_nonce_field('ctp_factura_add', 'ctp_factura_nonce'); ?>
            <input type="hidden" name="ctp_factura_action" value="add_factura">

            <div class="ctp-field">
                <label for="ctp-factura-proveedor">Proveedor</label>
                <select id="ctp-factura-proveedor" name="proveedor_id" required>
                    <option value="">Selecciona proveedor</option>
                    <?php foreach ($proveedores as $proveedor) : ?>
                        <option value="<?php echo esc_attr($proveedor->id); ?>"><?php echo esc_html($proveedor->nombre); ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-fecha">Fecha de factura</label>
                <input type="date" id="ctp-factura-fecha" name="fecha_factura" required value="<?php echo esc_attr(current_time('Y-m-d')); ?>">
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-nro">Número de factura</label>
                <input type="text" id="ctp-factura-nro" name="nro_factura" required>
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-concepto">Concepto</label>
                <input type="text" id="ctp-factura-concepto" name="concepto">
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-monto">Monto total</label>
                <input type="number" id="ctp-factura-monto" name="monto_total" step="0.01" min="0.01" required>
            </div>

            <div class="ctp-field">
                <label for="ctp-factura-vencimiento">Vencimiento</label>
                <input type="date" id="ctp-factura-vencimiento" name="vencimiento">
            </div>

            <div class="ctp-field ctp-field-full">
                <button type="submit" class="ctp-button">Registrar factura</button>
            </div>
        </form>
        </div>

        <div class="ctp-card ctp-form-wrap ctp-filters">
            <div class="ctp-card-header">
                <h3 class="ctp-card-title">Filtrar facturas</h3>
                <p class="ctp-card-subtitle">Aplica filtros para encontrar pagos pendientes o parciales.</p>
            </div>
            <form method="get" class="ctp-form ctp-form-inline">
            <div class="ctp-field">
                <label for="ctp-filter-estado">Estado</label>
                <select id="ctp-filter-estado" name="estado">
                    <option value="">Todos</option>
                    <?php foreach ($estados_validos as $estado) : ?>
                        <option value="<?php echo esc_attr($estado); ?>" <?php selected($estado_filtro, $estado); ?>>
                            <?php echo esc_html(ucfirst($estado)); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div class="ctp-field">
                <label for="ctp-filter-proveedor">Proveedor</label>
                <select id="ctp-filter-proveedor" name="proveedor_id">
                    <option value="">Todos</option>
                    <?php foreach ($proveedores as $proveedor) : ?>
                        <option value="<?php echo esc_attr($proveedor->id); ?>" <?php selected($proveedor_filtro, $proveedor->id); ?>>
                            <?php echo esc_html($proveedor->nombre); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div class="ctp-field">
                <button type="submit" class="ctp-button ctp-button-secondary">Filtrar</button>
            </div>
        </form>
        </div>

        <div class="ctp-card">
            <div class="ctp-card-header">
                <h3 class="ctp-card-title">Facturas registradas</h3>
                <p class="ctp-card-subtitle">Seguimiento de saldos y pagos por proveedor.</p>
            </div>
            <div class="ctp-table-wrap">
                <table class="ctp-table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Proveedor</th>
                    <th>Nro</th>
                    <th>Monto</th>
                    <th>Pagado</th>
                    <th>Saldo</th>
                    <th>Estado</th>
                    <th class="ctp-actions-cell">Acciones</th>
                </tr>
            </thead>
            <tbody>
                <?php if (!empty($facturas)) : ?>
                    <?php foreach ($facturas as $factura) : ?>
                        <tr>
                            <td data-label="Fecha"><?php echo esc_html($factura->fecha_factura); ?></td>
                            <td data-label="Proveedor"><?php echo esc_html($factura->proveedor_nombre ?: ''); ?></td>
                            <td data-label="Nro"><?php echo esc_html($factura->nro_factura); ?></td>
                            <td data-label="Monto"><?php echo esc_html(number_format((float) $factura->monto_total, 0, ',', '.')); ?></td>
                            <td data-label="Pagado"><?php echo esc_html(number_format((float) $factura->monto_pagado, 0, ',', '.')); ?></td>
                            <td data-label="Saldo"><?php echo esc_html(number_format((float) $factura->saldo, 0, ',', '.')); ?></td>
                            <td class="ctp-actions-cell" data-label="Estado">
                                <span class="ctp-status ctp-status-<?php echo esc_attr($factura->estado_pago); ?>">
                                    <?php echo esc_html(ucfirst($factura->estado_pago)); ?>
                                </span>
                            </td>
                            <td data-label="Acciones">
                                <div class="ctp-actions">
                                    <details class="ctp-details">
                                        <summary class="ctp-button ctp-button-secondary">Registrar pago</summary>
                                        <div class="ctp-details-panel">
                                            <form method="post" class="ctp-inline-form ctp-form-grid">
                                                <?php wp_nonce_field('ctp_pago_add', 'ctp_factura_nonce'); ?>
                                                <input type="hidden" name="ctp_factura_action" value="add_pago">
                                                <input type="hidden" name="factura_id" value="<?php echo esc_attr($factura->id); ?>">
                                                <div class="ctp-field">
                                                    <label>Fecha de pago</label>
                                                    <input type="date" name="fecha_pago" value="<?php echo esc_attr(current_time('Y-m-d')); ?>">
                                                </div>
                                                <div class="ctp-field">
                                                    <label>Monto</label>
                                                    <input type="number" name="monto" step="0.01" min="0.01" required>
                                                </div>
                                                <div class="ctp-field">
                                                    <label>Método</label>
                                                    <select name="metodo">
                                                        <option value="">Selecciona</option>
                                                        <option value="efectivo">Efectivo</option>
                                                        <option value="transferencia">Transferencia</option>
                                                        <option value="cheque">Cheque</option>
                                                        <option value="otro">Otro</option>
                                                    </select>
                                                </div>
                                                <div class="ctp-field">
                                                    <label>Nota</label>
                                                    <input type="text" name="nota">
                                                </div>
                                                <button type="submit" class="ctp-button ctp-field-full">Guardar pago</button>
                                            </form>
                                        </div>
                                    </details>
                                    <details class="ctp-details">
                                        <summary class="ctp-button ctp-button-secondary">Ver pagos</summary>
                                        <?php
                                        $pagos = $wpdb->get_results(
                                            $wpdb->prepare(
                                                "SELECT fecha_pago, monto, metodo, nota FROM {$table_pagos}
                                                 WHERE factura_id = %d
                                                 ORDER BY fecha_pago DESC, id DESC",
                                                $factura->id
                                            )
                                        );
                                        ?>
                                        <div class="ctp-details-panel ctp-payments">
                                            <?php if (!empty($pagos)) : ?>
                                                <table class="ctp-table ctp-table-small">
                                                    <thead>
                                                        <tr>
                                                            <th>Fecha</th>
                                                            <th>Monto</th>
                                                            <th>Método</th>
                                                            <th class="ctp-table-text">Nota</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        <?php foreach ($pagos as $pago) : ?>
                                                            <tr>
                                                                <td data-label="Fecha"><?php echo esc_html($pago->fecha_pago); ?></td>
                                                                <td data-label="Monto"><?php echo esc_html(number_format((float) $pago->monto, 0, ',', '.')); ?></td>
                                                                <td data-label="Método"><?php echo esc_html($pago->metodo); ?></td>
                                                                <td class="ctp-table-text" data-label="Nota"><?php echo esc_html($pago->nota); ?></td>
                                                            </tr>
                                                        <?php endforeach; ?>
                                                    </tbody>
                                                </table>
                                            <?php else : ?>
                                                <p>No hay pagos registrados.</p>
                                            <?php endif; ?>
                                        </div>
                                    </details>
                                    <?php
                                    $tiene_pagos = (int) $wpdb->get_var(
                                        $wpdb->prepare(
                                            "SELECT COUNT(*) FROM {$table_pagos} WHERE factura_id = %d",
                                            $factura->id
                                        )
                                    );
                                    ?>
                                    <?php if ($tiene_pagos === 0) : ?>
                                        <form method="post" class="ctp-inline-form">
                                            <?php wp_nonce_field('ctp_factura_delete', 'ctp_factura_nonce'); ?>
                                            <input type="hidden" name="ctp_factura_action" value="delete_factura">
                                            <input type="hidden" name="factura_id" value="<?php echo esc_attr($factura->id); ?>">
                                            <button type="submit" class="ctp-button ctp-button-danger" onclick="return confirm('¿Seguro que deseas eliminar?')">Eliminar</button>
                                        </form>
                                    <?php endif; ?>
                                </div>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                <?php else : ?>
                    <tr>
                        <td colspan="8">No hay facturas registradas.</td>
                    </tr>
                <?php endif; ?>
            </tbody>
                </table>
            </div>
        </div>
    </div>
    <?php
    $html = ob_get_clean();
    if (ctp_is_in_dashboard()) {
        return $html;
    }
    return ctp_wrap_base($html);
}
add_shortcode('ctp_facturas_proveedor', 'ctp_facturas_proveedor_shortcode');

function ctp_dashboard_shortcode() {
    ctp_ordenes_enqueue_assets(true);

    $tab = isset($_GET['tab']) ? sanitize_key(wp_unslash($_GET['tab'])) : 'ordenes';
    if (!in_array($tab, array('ordenes', 'proveedores', 'facturas'), true)) {
        $tab = 'ordenes';
    }

    global $wpdb;
    $table_ordenes = $wpdb->prefix . 'ctp_ordenes';
    $table_proveedores = $wpdb->prefix . 'ctp_proveedores';
    $table_facturas = $wpdb->prefix . 'ctp_facturas_proveedor';
    $recent_date = date('Y-m-d', strtotime('-30 days', current_time('timestamp')));

    $ordenes_total = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table_ordenes}");
    $ordenes_recientes = (int) $wpdb->get_var(
        $wpdb->prepare(
            "SELECT COUNT(*) FROM {$table_ordenes} WHERE fecha >= %s",
            $recent_date
        )
    );
    $proveedores_total = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table_proveedores}");
    $facturas_pendientes = (int) $wpdb->get_var(
        "SELECT COUNT(*) FROM {$table_facturas} WHERE estado_pago IN ('pendiente','parcial')"
    );
    $saldo_pendiente = (float) $wpdb->get_var(
        "SELECT COALESCE(SUM(saldo), 0) FROM {$table_facturas} WHERE estado_pago IN ('pendiente','parcial')"
    );
    $saldo_pendiente_formatted = number_format($saldo_pendiente, 0, ',', '.');

    $base_url = get_permalink();
    $tabs = array(
        'ordenes' => 'Órdenes',
        'proveedores' => 'Proveedores',
        'facturas' => 'Facturas',
    );

    $GLOBALS['ctp_in_dashboard'] = true;

    try {
        ob_start();
        ?>
            <div class="ctp-dashboard-header">
                <h2>Sistema CTP</h2>
                <p class="ctp-dashboard-subtitle">Panel central para órdenes, proveedores y facturación.</p>
            </div>
            <div class="ctp-summary-grid">
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Órdenes</div>
                    <div class="ctp-summary-value"><?php echo esc_html(number_format($ordenes_total, 0, ',', '.')); ?></div>
                    <div class="ctp-summary-meta">
                        <?php echo esc_html(sprintf('Últimos 30 días: %s', number_format($ordenes_recientes, 0, ',', '.'))); ?>
                    </div>
                </div>
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Proveedores</div>
                    <div class="ctp-summary-value"><?php echo esc_html(number_format($proveedores_total, 0, ',', '.')); ?></div>
                    <div class="ctp-summary-meta">Total registrados</div>
                </div>
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Facturas pendientes</div>
                    <div class="ctp-summary-value"><?php echo esc_html(number_format($facturas_pendientes, 0, ',', '.')); ?></div>
                    <div class="ctp-summary-meta">Pendiente o parcial</div>
                </div>
                <div class="ctp-summary-card">
                    <div class="ctp-summary-title">Saldo pendiente</div>
                    <div class="ctp-summary-value"><?php echo esc_html('Gs. ' . $saldo_pendiente_formatted); ?></div>
                    <div class="ctp-summary-meta">Monto por pagar</div>
                </div>
            </div>
            <div class="ctp-dashboard-nav">
            <?php foreach ($tabs as $key => $label) : ?>
                <?php
                $url = add_query_arg('tab', $key, $base_url);
                $class = 'ctp-dashboard-button';
                if ($tab === $key) {
                    $class .= ' is-active';
                }
                ?>
                <a class="<?php echo esc_attr($class); ?>" href="<?php echo esc_url($url); ?>">
                    <?php echo esc_html($label); ?>
                </a>
            <?php endforeach; ?>
            </div>
            <div class="ctp-dashboard-content">
                <?php if ($tab === 'ordenes') : ?>
                    <div class="ctp-dashboard-grid">
                        <div class="ctp-dashboard-col">
                            <?php echo do_shortcode('[ctp_cargar_orden]'); ?>
                        </div>
                        <div class="ctp-dashboard-col">
                            <?php echo do_shortcode('[ctp_listar_ordenes]'); ?>
                        </div>
                    </div>
                <?php elseif ($tab === 'proveedores') : ?>
                    <?php echo do_shortcode('[ctp_proveedores]'); ?>
                <?php else : ?>
                    <?php echo do_shortcode('[ctp_facturas_proveedor]'); ?>
                <?php endif; ?>
            </div>
        <?php
        $contenido = ob_get_clean();
    } finally {
        unset($GLOBALS['ctp_in_dashboard']);
    }

    return ctp_wrap_dashboard($contenido);
}
add_shortcode('ctp_dashboard', 'ctp_dashboard_shortcode');
