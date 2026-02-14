<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Calculator {
    private const CACHE_TTL = 300;

    public static function calculate( array $payload ): array {
        global $wpdb;

        $has_maquina_id = array_key_exists( 'maquina_id', $payload );
        $maquina_id_raw = $payload['maquina_id'] ?? null;
        $allow_machine_default = ! empty( $payload['allow_machine_default'] );
        $warnings = array();

        $snapshot_version = isset( $payload['snapshot_version'] ) ? (int) $payload['snapshot_version'] : ( defined( 'CPO_SNAPSHOT_VERSION' ) ? (int) CPO_SNAPSHOT_VERSION : 1 );
        $production_result = array();

        $payload = wp_parse_args(
            $payload,
            array(
                'cantidad'              => 1,
                'formas_por_pliego'     => 1,
                'merma_pct'             => 0,
                'material_id'           => 0,
                'procesos'              => array(),
                'margin_pct'            => 0,
                'maquina_id'            => 0,
                'horas_maquina'         => 0,
                'costo_hora'            => 0,
                'pliego_formato'        => '',
                'pliego_ancho_mm'       => 0,
                'pliego_alto_mm'        => 0,
                'pliego_personalizado'  => false,
                'allow_machine_default' => false,
            )
        );

        $cantidad = max( 1, (int) $payload['cantidad'] );
        if ( (int) $payload['formas_por_pliego'] <= 0 ) {
            $warnings[] = __( 'Formas por pliego vacías.', 'core-print-offset' );
        }
        $formas_por_pliego = max( 1, (int) $payload['formas_por_pliego'] );
        $merma_pct = max( 0, (float) $payload['merma_pct'] );
        $material_id = (int) $payload['material_id'];
        $margin_pct = max( 0, (float) $payload['margin_pct'] );
        $maquina_id = (int) $payload['maquina_id'];
        $horas_maquina = max( 0, (float) $payload['horas_maquina'] );
        $costo_hora_override = max( 0, (float) $payload['costo_hora'] );

        $material = null;
        $precio_pliego = 0;
        $precio_note = '';
        $precio_snapshot = array();
        $pliego_ancho_mm = max( 0, (float) $payload['pliego_ancho_mm'] );
        $pliego_alto_mm = max( 0, (float) $payload['pliego_alto_mm'] );
        $sheet_context = class_exists( 'CPO_Production_Engine' )
            ? CPO_Production_Engine::derive_sheet_context( $payload )
            : array(
                'base_sheet_mm' => array( $pliego_ancho_mm, $pliego_alto_mm ),
                'useful_sheet_mm' => array( $pliego_ancho_mm, $pliego_alto_mm ),
                'pieces_per_base' => 1,
                'use_cut_sheet' => false,
                'cut_mode' => 'none',
                'cut_fraction' => null,
                'warnings' => array(),
            );

        if ( $material_id ) {
            $material = self::get_material_by_id( $material_id );
            if ( $material && $material['precio_vigente'] !== null ) {
                $precio_pliego = (float) $material['precio_vigente'];
                $precio_snapshot = array(
                    'precio'        => $precio_pliego,
                    'vigente_desde' => $material['vigente_desde'] ?? null,
                    'moneda'        => $material['moneda'] ?? null,
                    'formas_por_pliego' => $formas_por_pliego,
                );
            } else {
                $precio_note = __( 'No hay precio vigente para este material. Cargalo en Offset > Materiales/Precios', 'core-print-offset' );
                $warnings[] = __( 'Material sin precio vigente.', 'core-print-offset' );
            }

            if ( ! $payload['pliego_personalizado'] && empty( $payload['pliego_formato'] ) && ! empty( $material['formato_base'] ) ) {
                $payload['pliego_formato'] = $material['formato_base'];
            }
        }

        if ( ! $pliego_ancho_mm || ! $pliego_alto_mm ) {
            $parsed = self::parse_pliego_format( $payload['pliego_formato'] );
            if ( $parsed ) {
                $pliego_ancho_mm = $parsed['ancho_mm'];
                $pliego_alto_mm = $parsed['alto_mm'];
            }
        }

        if ( ! $pliego_ancho_mm || ! $pliego_alto_mm ) {
            $warnings[] = __( 'Formato de pliego incompleto.', 'core-print-offset' );
        }

        $pliegos_netos = (int) ceil( $cantidad / $formas_por_pliego );
        $pliegos_con_merma = (int) ceil( $pliegos_netos * ( 1 + ( $merma_pct / 100 ) ) );
        $pliegos_necesarios = $pliegos_con_merma;
        $pliegos_utiles = $pliegos_necesarios;
        $pieces_per_base = max( 1, (int) ( $sheet_context['pieces_per_base'] ?? 1 ) );
        $pliegos_base = (int) ceil( $pliegos_utiles / $pieces_per_base );

        $costo_papel = $pliegos_base * $precio_pliego;

        $procesos = self::get_processes_by_ids( $payload['procesos'] );
        $costo_procesos = 0;
        $procesos_detalle = array();
        $m2_por_pliego = ( $pliego_ancho_mm && $pliego_alto_mm ) ? ( $pliego_ancho_mm * $pliego_alto_mm ) / 1000000 : 0;

        $maquina = null;
        $maquina_defaulted = false;
        $explicit_no_machine = $has_maquina_id && ( $maquina_id_raw === 0 || $maquina_id_raw === '0' );
        $machine_missing = ( ! $has_maquina_id || $maquina_id_raw === '' || $maquina_id_raw === null );
        if ( $allow_machine_default && $machine_missing && ! $explicit_no_machine ) {
            $maquina = self::get_default_machine();
            if ( $maquina ) {
                $maquina_id = (int) $maquina['id'];
                $maquina_defaulted = true;
            }
        }

        if ( ! $maquina ) {
            $maquina = $maquina_id ? self::get_machine_by_id( $maquina_id ) : null;
        }

        if ( $maquina && ! $horas_maquina ) {
            $rendimiento = 0;
            if ( isset( $maquina['rendimiento_pliegos_hora'] ) && $maquina['rendimiento_pliegos_hora'] !== null ) {
                $rendimiento = (int) $maquina['rendimiento_pliegos_hora'];
            } elseif ( isset( $maquina['rendimiento_hora'] ) ) {
                $rendimiento = (int) $maquina['rendimiento_hora'];
            }
            $setup_min = isset( $maquina['setup_min'] ) ? (float) $maquina['setup_min'] : 0;
            if ( $rendimiento > 0 ) {
                $horas_maquina = round( ( $setup_min / 60 ) + ( $pliegos_necesarios / $rendimiento ), 2 );
            }
        }

        $costo_hora = $maquina ? (float) $maquina['costo_hora'] : 0;
        if ( $costo_hora_override > 0 && current_user_can( 'manage_options' ) ) {
            $costo_hora = $costo_hora_override;
        }

        foreach ( $procesos as $proceso ) {
            $multiplier = 1;
            $detalle_calculo = '';
            $unidad = $proceso['unidad'] ?? '';
            $modo_cobro = $proceso['modo_cobro'] ?? 'fijo';

            if ( $modo_cobro === 'por_unidad' ) {
                $multiplier = $cantidad;
                $detalle_calculo = sprintf( '%s x %s', $cantidad, $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_pliego' ) {
                $multiplier = max( 1, $pliegos_necesarios );
                $detalle_calculo = sprintf( '%s pliegos x %s', $multiplier, $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_hora' ) {
                $multiplier = $maquina ? max( 1, $horas_maquina ) : 0;
                $detalle_calculo = sprintf( '%s h x %s', $multiplier, $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_millar' ) {
                $multiplier = $cantidad / 1000;
                $detalle_calculo = sprintf( '%s x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_m2' ) {
                $multiplier = $m2_por_pliego * $pliegos_necesarios;
                $detalle_calculo = sprintf( '%s m² x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
                if ( ! $m2_por_pliego ) {
                    $warnings[] = __( 'Proceso por m² requiere formato de pliego.', 'core-print-offset' );
                }
            } elseif ( $modo_cobro === 'por_kg' ) {
                $consumo = isset( $proceso['consumo_g_m2'] ) ? (float) $proceso['consumo_g_m2'] : 0;
                $merma_proceso = isset( $proceso['merma_proceso_pct'] ) ? (float) $proceso['merma_proceso_pct'] : 0;
                $kg = 0;
                if ( $m2_por_pliego ) {
                    $kg = ( $m2_por_pliego * $pliegos_necesarios * $consumo / 1000 ) * ( 1 + ( $merma_proceso / 100 ) );
                }
                $multiplier = $kg;
                $detalle_calculo = sprintf( '%s kg x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
                if ( ! $m2_por_pliego ) {
                    $warnings[] = __( 'Proceso por kg requiere formato de pliego.', 'core-print-offset' );
                }
            }

            $subtotal_proceso = (float) $proceso['costo_base'] * $multiplier;
            $costo_procesos += $subtotal_proceso;

            $procesos_detalle[] = array(
                'id'              => $proceso['id'],
                'nombre'          => $proceso['nombre'],
                'cantidad'        => $multiplier,
                'unitario'        => (float) $proceso['costo_base'],
                'subtotal'        => $subtotal_proceso,
                'modo_cobro'      => $modo_cobro,
                'unidad'          => $unidad,
                'detalle_calculo' => $detalle_calculo,
                'consumo_g_m2'    => isset( $proceso['consumo_g_m2'] ) ? (float) $proceso['consumo_g_m2'] : null,
                'merma_proceso_pct' => isset( $proceso['merma_proceso_pct'] ) ? (float) $proceso['merma_proceso_pct'] : null,
                'setup_min'       => isset( $proceso['setup_min'] ) ? (float) $proceso['setup_min'] : null,
            );
        }

        $costo_maquina = 0;
        if ( $maquina && $horas_maquina > 0 ) {
            $costo_maquina = $costo_hora * $horas_maquina;
        }

        $subtotal = $costo_papel + $costo_procesos + $costo_maquina;
        $margen = $subtotal * ( $margin_pct / 100 );
        $total = $subtotal + $margen;

        if ( $snapshot_version >= 2 && class_exists( 'CPO_Production_Engine' ) ) {
            $production_result = CPO_Production_Engine::calculate( $payload, $maquina );
            if ( ! empty( $production_result['warnings'] ) && is_array( $production_result['warnings'] ) ) {
                $warnings = array_merge( $warnings, $production_result['warnings'] );
            }

            if ( isset( $production_result['pliegos_utiles'] ) ) {
                $pliegos_utiles = (int) $production_result['pliegos_utiles'];
            }
            if ( isset( $production_result['pieces_per_base'] ) ) {
                $pieces_per_base = max( 1, (int) $production_result['pieces_per_base'] );
            }
            if ( isset( $production_result['pliegos_base'] ) ) {
                $pliegos_base = (int) $production_result['pliegos_base'];
            } else {
                $pliegos_base = (int) ceil( $pliegos_utiles / $pieces_per_base );
            }

            $pliegos_necesarios = $pliegos_base;
            $pliegos_con_merma = $pliegos_utiles;
            $costo_papel = $pliegos_base * $precio_pliego;

            if ( isset( $production_result['forms_per_sheet_auto'] ) ) {
                $formas_por_pliego = (int) $production_result['forms_per_sheet_auto'];
            }
        }

        return array(
            'pliegos_netos'       => $pliegos_netos,
            'pliegos_con_merma'   => $pliegos_con_merma,
            'pliegos_necesarios' => $pliegos_necesarios,
            'pliegos_utiles'      => $pliegos_utiles,
            'pliegos_base'        => $pliegos_base,
            'pieces_per_base'     => $pieces_per_base,
            'precio_pliego'      => $precio_pliego,
            'costo_papel'         => $costo_papel,
            'costo_procesos'      => $costo_procesos,
            'costo_maquina'       => $costo_maquina,
            'subtotal'            => $subtotal,
            'margen'              => $margen,
            'total'               => $total,
            'margen_pct'          => $margin_pct,
            'material'            => $material,
            'material_snapshot'   => $precio_snapshot,
            'pliego_ancho_mm'     => $pliego_ancho_mm,
            'pliego_alto_mm'      => $pliego_alto_mm,
            'm2_por_pliego'       => $m2_por_pliego,
            'procesos'            => $procesos_detalle,
            'maquina'             => $maquina,
            'maquina_id'          => $maquina_id,
            'maquina_defaulted'   => $maquina_defaulted,
            'horas_maquina'       => $horas_maquina,
            'costo_hora'          => $costo_hora,
            'price_note'          => $precio_note,
            'production'          => $production_result,
            'production_summary'  => $production_result['production_summary'] ?? '',
            'base_sheet_mm'       => $production_result['base_sheet_mm'] ?? $sheet_context['base_sheet_mm'],
            'useful_sheet_mm'     => $production_result['useful_sheet_mm'] ?? $sheet_context['useful_sheet_mm'],
            'use_cut_sheet'       => $production_result['use_cut_sheet'] ?? $sheet_context['use_cut_sheet'],
            'cut_mode'            => $production_result['cut_mode'] ?? $sheet_context['cut_mode'],
            'cut_fraction'        => $production_result['cut_fraction'] ?? $sheet_context['cut_fraction'],
            'forms_per_sheet_auto' => $production_result['forms_per_sheet_auto'] ?? $formas_por_pliego,
            'forms_per_sheet_override' => $production_result['forms_per_sheet_override'] ?? null,
            'warnings'            => $warnings,
        );
    }

    private static function get_material_by_id( int $material_id ): ?array {
        global $wpdb;

        $cache_version = cpo_get_cache_version( 'material' );
        $cache_key = cpo_get_cache_key( sprintf( 'material_by_id:%s:%d', $cache_version, $material_id ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return $cached ?: null;
        }

        $sql = "SELECT m.*, (
                SELECT precio FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS precio_vigente,
            (
                SELECT vigente_desde FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS vigente_desde,
            (
                SELECT moneda FROM {$wpdb->prefix}cpo_material_precios p
                WHERE p.material_id = m.id
                ORDER BY p.vigente_desde DESC
                LIMIT 1
            ) AS moneda
            FROM {$wpdb->prefix}cpo_materiales m
            WHERE m.id = %d
            LIMIT 1";

        $row = $wpdb->get_row( $wpdb->prepare( $sql, $material_id ), ARRAY_A );

        wp_cache_set( $cache_key, $row ?: null, 'cpo', self::CACHE_TTL );
        if ( $row ) {
            $price_key = cpo_get_cache_key( sprintf( 'price_vigente:%s:%d:latest', $cache_version, $material_id ) );
            wp_cache_set(
                $price_key,
                array(
                    'precio'        => $row['precio_vigente'],
                    'vigente_desde' => $row['vigente_desde'],
                    'moneda'        => $row['moneda'],
                ),
                'cpo',
                self::CACHE_TTL
            );
        }

        return $row ?: null;
    }

    private static function get_processes_by_ids( array $ids ): array {
        global $wpdb;

        if ( empty( $ids ) ) {
            return array();
        }

        sort( $ids, SORT_NUMERIC );
        $cache_version = cpo_get_cache_version( 'proceso' );
        $cache_key = cpo_get_cache_key( sprintf( 'process_by_ids:%s:%s', $cache_version, md5( wp_json_encode( $ids ) ) ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return $cached ?: array();
        }

        $placeholders = implode( ',', array_fill( 0, count( $ids ), '%d' ) );
        $sql = "SELECT * FROM {$wpdb->prefix}cpo_procesos WHERE id IN ($placeholders) AND activo = 1";

        $results = $wpdb->get_results( $wpdb->prepare( $sql, $ids ), ARRAY_A );
        wp_cache_set( $cache_key, $results, 'cpo', self::CACHE_TTL );
        foreach ( $results as $process ) {
            if ( isset( $process['id'] ) ) {
                $process_key = cpo_get_cache_key( sprintf( 'process_by_id:%s:%d', $cache_version, (int) $process['id'] ) );
                wp_cache_set( $process_key, $process, 'cpo', self::CACHE_TTL );
            }
        }

        return $results;
    }

    private static function get_machine_by_id( int $machine_id ): ?array {
        global $wpdb;

        $cache_version = cpo_get_cache_version( 'maquina' );
        $cache_key = cpo_get_cache_key( sprintf( 'machine_by_id:%s:%d', $cache_version, $machine_id ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return $cached ?: null;
        }

        $machine = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_maquinas WHERE id = %d", $machine_id ),
            ARRAY_A
        );

        wp_cache_set( $cache_key, $machine ?: null, 'cpo', self::CACHE_TTL );

        return $machine ?: null;
    }

    private static function get_default_machine(): ?array {
        global $wpdb;

        $cache_version = cpo_get_cache_version( 'maquina' );
        $cache_key = cpo_get_cache_key( sprintf( 'machine_default:%s', $cache_version ) );
        $found = false;
        $cached = wp_cache_get( $cache_key, 'cpo', false, $found );
        if ( $found ) {
            return $cached ?: null;
        }

        $machine = $wpdb->get_row(
            "SELECT * FROM {$wpdb->prefix}cpo_maquinas WHERE activo = 1 ORDER BY costo_hora ASC, created_at ASC LIMIT 1",
            ARRAY_A
        );

        wp_cache_set( $cache_key, $machine ?: null, 'cpo', self::CACHE_TTL );

        return $machine ?: null;
    }

    private static function parse_pliego_format( string $format ): ?array {
        if ( ! $format ) {
            return null;
        }

        if ( preg_match( '/(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)/', $format, $matches ) ) {
            $ancho = (float) $matches[1];
            $alto = (float) $matches[2];
            $is_cm = $ancho <= 300 && $alto <= 300;
            $factor = $is_cm ? 10 : 1;

            return array(
                'ancho_mm' => $ancho * $factor,
                'alto_mm'  => $alto * $factor,
            );
        }

        return null;
    }
}
