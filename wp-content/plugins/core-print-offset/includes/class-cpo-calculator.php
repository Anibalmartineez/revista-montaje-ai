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
            $parsed = cpo_parse_sheet_size_to_mm( (string) $payload['pliego_formato'] );
            if ( ! empty( $parsed['normalized'] ) ) {
                $pliego_ancho_mm = (float) $parsed['w_mm'];
                $pliego_alto_mm = (float) $parsed['h_mm'];
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
        $useful_sheet_mm = $production_result['useful_sheet_mm'] ?? $sheet_context['useful_sheet_mm'];
        $base_sheet_mm = $production_result['base_sheet_mm'] ?? $sheet_context['base_sheet_mm'];
        $area_pliego_util_m2 = ( ! empty( $useful_sheet_mm[0] ) && ! empty( $useful_sheet_mm[1] ) )
            ? ( (float) $useful_sheet_mm[0] / 1000 ) * ( (float) $useful_sheet_mm[1] / 1000 )
            : 0;
        $m2_por_pliego = ( ! empty( $base_sheet_mm[0] ) && ! empty( $base_sheet_mm[1] ) )
            ? ( (float) $base_sheet_mm[0] * (float) $base_sheet_mm[1] ) / 1000000
            : 0;

        $machine_rendimiento = 0;
        if ( $maquina ) {
            if ( isset( $maquina['rendimiento_pliegos_hora'] ) && $maquina['rendimiento_pliegos_hora'] !== null ) {
                $machine_rendimiento = (float) $maquina['rendimiento_pliegos_hora'];
            } elseif ( isset( $maquina['rendimiento_hora'] ) ) {
                $machine_rendimiento = (float) $maquina['rendimiento_hora'];
            }
        }

        foreach ( $procesos as $proceso ) {
            $multiplier = 1;
            $detalle_calculo = '';
            $unidad = $proceso['unidad'] ?? '';
            $modo_cobro = $proceso['modo_cobro'] ?? 'fijo';
            $base_calculo = cpo_get_process_base_calculo( $proceso );
            $consumo = isset( $proceso['consumo_g_m2'] ) ? (float) $proceso['consumo_g_m2'] : 0;
            $merma_proceso = isset( $proceso['merma_proceso_pct'] ) ? max( 0.0, (float) $proceso['merma_proceso_pct'] ) : 0.0;
            $setup_min = isset( $proceso['setup_min'] ) ? max( 0.0, (float) $proceso['setup_min'] ) : 0.0;

            $cantidad_base = $cantidad;
            if ( 'pliego_util' === $base_calculo ) {
                $cantidad_base = max( 1, $pliegos_utiles );
                if ( $merma_proceso > 0 ) {
                    $cantidad_base = (int) ceil( $cantidad_base * ( 1 + ( $merma_proceso / 100 ) ) );
                }
            } elseif ( 'pliego_base' === $base_calculo ) {
                $cantidad_base = max( 1, $pliegos_base );
            } elseif ( 'unidad_final' === $base_calculo ) {
                $cantidad_base = max( 1, $cantidad );
                if ( $merma_proceso > 0 ) {
                    $cantidad_base = (float) $cantidad_base * ( 1 + ( $merma_proceso / 100 ) );
                }
            }

            if ( $modo_cobro === 'por_unidad' ) {
                $multiplier = $cantidad_base;
                $detalle_calculo = sprintf( '%s unidades x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_pliego' ) {
                $multiplier = max( 1, (float) $cantidad_base );
                $detalle_calculo = sprintf( '%s pliegos x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_hora' ) {
                if ( $machine_rendimiento > 0 && 'none' !== $base_calculo ) {
                    $multiplier = ( $setup_min / 60 ) + ( (float) $cantidad_base / $machine_rendimiento );
                    $detalle_calculo = sprintf( '%s h (setup+tirada) x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
                } else {
                    $multiplier = $maquina ? max( 1, $horas_maquina ) : 0;
                    $detalle_calculo = sprintf( '%s h x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
                }
            } elseif ( $modo_cobro === 'por_millar' ) {
                $multiplier = (float) $cantidad_base / 1000;
                $detalle_calculo = sprintf( '%s x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
            } elseif ( $modo_cobro === 'por_m2' ) {
                if ( $area_pliego_util_m2 > 0 && 'pliego_util' === $base_calculo ) {
                    $consumo_total = $area_pliego_util_m2 * $pliegos_utiles * max( 0, $consumo );
                    if ( $consumo > 0 ) {
                        $multiplier = $consumo_total;
                        $detalle_calculo = sprintf( '%s m² × %s pliegos útiles × %s = %s consumo x %s', round( $area_pliego_util_m2, 4 ), $pliegos_utiles, $consumo, round( $consumo_total, 4 ), $proceso['costo_base'] );
                    } else {
                        $multiplier = $area_pliego_util_m2 * $pliegos_utiles;
                        $detalle_calculo = sprintf( '%s m² x %s pliegos útiles x %s', round( $area_pliego_util_m2, 4 ), $pliegos_utiles, $proceso['costo_base'] );
                    }
                } else {
                    $base_area = $m2_por_pliego > 0 ? $m2_por_pliego : $area_pliego_util_m2;
                    $multiplier = $base_area * max( 1, (float) $cantidad_base );
                    $detalle_calculo = sprintf( '%s m² x %s x %s', round( $base_area, 4 ), round( $cantidad_base, 3 ), $proceso['costo_base'] );
                }
                if ( $area_pliego_util_m2 <= 0 && $m2_por_pliego <= 0 ) {
                    $warnings[] = __( 'Proceso por m² requiere formato de pliego útil/base.', 'core-print-offset' );
                }
            } elseif ( $modo_cobro === 'por_kg' ) {
                $base_area = 'pliego_base' === $base_calculo ? $m2_por_pliego : $area_pliego_util_m2;
                $kg = 0;
                if ( $base_area > 0 ) {
                    $kg = ( $base_area * max( 1, (float) $cantidad_base ) * $consumo ) / 1000;
                }
                $multiplier = $kg;
                $detalle_calculo = sprintf( '%s kg x %s', round( $multiplier, 3 ), $proceso['costo_base'] );
                if ( $base_area <= 0 ) {
                    $warnings[] = __( 'Proceso por kg requiere formato de pliego.', 'core-print-offset' );
                }
            }

            if ( 'por_m2' === $modo_cobro && 'pliego_util' === $base_calculo && $area_pliego_util_m2 <= 0 ) {
                $warnings[] = sprintf( __( 'Proceso %s requiere pliego útil para cálculo por m².', 'core-print-offset' ), $proceso['nombre'] );
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
                'base_calculo'    => $base_calculo,
                'unidad'          => $unidad,
                'detalle_calculo' => $detalle_calculo,
                'consumo_g_m2'    => isset( $proceso['consumo_g_m2'] ) ? (float) $proceso['consumo_g_m2'] : null,
                'consumo_total_estimado' => ( 'por_m2' === $modo_cobro && $consumo > 0 && 'pliego_util' === $base_calculo ) ? round( $area_pliego_util_m2 * $pliegos_utiles * $consumo, 4 ) : null,
                'area_pliego_util_m2' => $area_pliego_util_m2 > 0 ? round( $area_pliego_util_m2, 4 ) : null,
                'pliegos_utiles' => $pliegos_utiles,
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
            'area_pliego_util_m2' => $area_pliego_util_m2,
            'base_calculo_summary' => array(
                'pliego_base' => $production_result['base_sheet_mm'] ?? $sheet_context['base_sheet_mm'],
                'pliego_util' => $production_result['useful_sheet_mm'] ?? $sheet_context['useful_sheet_mm'],
                'unidad_final' => $cantidad,
            ),
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
        foreach ( $results as &$process ) {
            $decoded_unit = cpo_decode_process_unit_meta( (string) ( $process['unidad'] ?? '' ) );
            $process['unidad'] = $decoded_unit['unidad'];
            $process['base_calculo'] = cpo_get_process_base_calculo( $process );
        }
        unset( $process );

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
}
