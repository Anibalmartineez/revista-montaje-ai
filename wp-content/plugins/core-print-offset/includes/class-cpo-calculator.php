<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Calculator {
    public static function calculate( array $payload ): array {
        global $wpdb;

        $payload = wp_parse_args(
            $payload,
            array(
                'cantidad'         => 1,
                'formas_por_pliego'=> 1,
                'merma_pct'        => 0,
                'material_id'      => 0,
                'procesos'         => array(),
                'margin_pct'       => 0,
                'maquina_id'       => 0,
                'horas_maquina'    => 0,
                'costo_hora'       => 0,
            )
        );

        $cantidad = max( 1, (int) $payload['cantidad'] );
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

        if ( $material_id ) {
            $material = self::get_material_by_id( $material_id );
            if ( $material && $material['precio_vigente'] !== null ) {
                $precio_pliego = (float) $material['precio_vigente'];
                $precio_snapshot = array(
                    'precio'        => $precio_pliego,
                    'vigente_desde' => $material['vigente_desde'] ?? null,
                    'formas_por_pliego' => $formas_por_pliego,
                );
            } else {
                $precio_note = __( 'No hay precio vigente para este material. Cargalo en Offset > Materiales/Precios', 'core-print-offset' );
            }
        }

        $pliegos_necesarios = (int) ceil(
            ( $cantidad / $formas_por_pliego ) * ( 1 + ( $merma_pct / 100 ) )
        );

        $costo_papel = $pliegos_necesarios * $precio_pliego;

        $procesos = self::get_processes_by_ids( $payload['procesos'] );
        $costo_procesos = 0;
        $procesos_detalle = array();

        $maquina = null;
        $maquina_defaulted = false;
        if ( ! $maquina_id ) {
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
            $rendimiento = isset( $maquina['rendimiento_hora'] ) ? (int) $maquina['rendimiento_hora'] : 0;
            if ( $rendimiento > 0 ) {
                $horas_maquina = round( $pliegos_necesarios / $rendimiento, 2 );
            }
        }

        $costo_hora = $maquina ? (float) $maquina['costo_hora'] : 0;
        if ( $costo_hora_override > 0 && current_user_can( 'manage_options' ) ) {
            $costo_hora = $costo_hora_override;
        }

        foreach ( $procesos as $proceso ) {
            $multiplier = 1;
            if ( $proceso['modo_cobro'] === 'por_unidad' ) {
                $multiplier = $cantidad;
            } elseif ( $proceso['modo_cobro'] === 'por_pliego' ) {
                $multiplier = max( 1, $pliegos_necesarios );
            } elseif ( $proceso['modo_cobro'] === 'por_hora' ) {
                $multiplier = max( 1, $horas_maquina );
            }

            $subtotal_proceso = (float) $proceso['costo_base'] * $multiplier;
            $costo_procesos += $subtotal_proceso;

            $procesos_detalle[] = array(
                'id'       => $proceso['id'],
                'nombre'   => $proceso['nombre'],
                'cantidad' => $multiplier,
                'unitario' => (float) $proceso['costo_base'],
                'subtotal' => $subtotal_proceso,
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
            'pliegos_necesarios' => $pliegos_necesarios,
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
            'procesos'            => $procesos_detalle,
            'maquina'             => $maquina,
            'maquina_id'          => $maquina_id,
            'maquina_defaulted'   => $maquina_defaulted,
            'horas_maquina'       => $horas_maquina,
            'costo_hora'          => $costo_hora,
            'price_note'          => $precio_note,
        );
    }

    private static function get_material_by_id( int $material_id ): ?array {
        global $wpdb;

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

        return $row ?: null;
    }

    private static function get_processes_by_ids( array $ids ): array {
        global $wpdb;

        if ( empty( $ids ) ) {
            return array();
        }

        $placeholders = implode( ',', array_fill( 0, count( $ids ), '%d' ) );
        $sql = "SELECT * FROM {$wpdb->prefix}cpo_procesos WHERE id IN ($placeholders) AND activo = 1";

        return $wpdb->get_results( $wpdb->prepare( $sql, $ids ), ARRAY_A );
    }

    private static function get_machine_by_id( int $machine_id ): ?array {
        global $wpdb;

        $machine = $wpdb->get_row(
            $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}cpo_maquinas WHERE id = %d", $machine_id ),
            ARRAY_A
        );

        return $machine ?: null;
    }

    private static function get_default_machine(): ?array {
        global $wpdb;

        $machine = $wpdb->get_row(
            "SELECT * FROM {$wpdb->prefix}cpo_maquinas WHERE activo = 1 ORDER BY costo_hora ASC, created_at ASC LIMIT 1",
            ARRAY_A
        );

        return $machine ?: null;
    }
}
