<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_Production_Engine {
    private const PINZA_MM = 10.0;
    private const COLA_MM = 10.0;
    private const MARGEN_LATERAL_MM = 10.0;
    private const MERMA_BASE_PCT = 3.0;
    private const MERMA_EXTRA_EVERY_1000_PCT = 1.0;

    public static function calculate( array $snapshot, ?array $maquina = null ): array {
        $cantidad = max( 1, (int) ( $snapshot['cantidad'] ?? 1 ) );
        $sheet_context = self::derive_sheet_context( $snapshot );

        $ancho_trabajo = max( 0.0, (float) ( $snapshot['ancho_mm'] ?? 0 ) );
        $alto_trabajo = max( 0.0, (float) ( $snapshot['alto_mm'] ?? 0 ) );
        $sangrado_mm = max( 0.0, (float) ( $snapshot['sangrado_mm'] ?? 0 ) );

        if ( $sangrado_mm > 0 ) {
            $ancho_trabajo += ( $sangrado_mm * 2 );
            $alto_trabajo += ( $sangrado_mm * 2 );
        }

        $colores = self::parse_colores( (string) ( $snapshot['colores'] ?? '0/0' ) );
        $colores_frente = $colores['frente'];
        $colores_dorso = $colores['dorso'];

        $util_ancho = max( 0.0, $sheet_context['useful_sheet_mm'][0] - ( self::MARGEN_LATERAL_MM * 2 ) );
        $util_alto = max( 0.0, $sheet_context['useful_sheet_mm'][1] - self::PINZA_MM - self::COLA_MM );

        $formas_horizontal = $ancho_trabajo > 0 ? (int) floor( $util_ancho / $ancho_trabajo ) : 0;
        $formas_vertical = $alto_trabajo > 0 ? (int) floor( $util_alto / $alto_trabajo ) : 0;
        $formas_por_pliego_auto = max( 0, $formas_horizontal * $formas_vertical );

        $allow_manual_forms = ! empty( $snapshot['enable_manual_forms'] ) || ! empty( $snapshot['edit_formas_por_pliego'] );
        $formas_por_pliego_override = $allow_manual_forms ? max( 0, (int) ( $snapshot['formas_por_pliego'] ?? 0 ) ) : 0;
        $formas_por_pliego = $formas_por_pliego_override > 0 ? $formas_por_pliego_override : $formas_por_pliego_auto;

        $is_viable = $formas_por_pliego > 0;

        $pliegos_utiles_base = $is_viable ? (int) ceil( $cantidad / $formas_por_pliego ) : 0;
        $merma_setup_pliegos = self::get_setup_merma_pliegos( $maquina );
        $merma_pct = self::MERMA_BASE_PCT;
        if ( $pliegos_utiles_base > 0 ) {
            $merma_pct += floor( $pliegos_utiles_base / 1000 ) * self::MERMA_EXTRA_EVERY_1000_PCT;
        }
        $merma_porcentaje_pliegos = (int) ceil( $pliegos_utiles_base * ( $merma_pct / 100 ) );
        $merma_pliegos = $merma_porcentaje_pliegos + $merma_setup_pliegos;
        $pliegos_utiles = $pliegos_utiles_base + $merma_pliegos;

        $pieces_per_base = max( 1, (int) $sheet_context['pieces_per_base'] );
        $pliegos_base = (int) ceil( $pliegos_utiles / $pieces_per_base );

        $chapas = $colores_frente + $colores_dorso;

        $capacidad_maquina = self::get_machine_color_capacity( $maquina );
        $caras_activas = max( $colores_frente, $colores_dorso );
        $pasadas = 0;
        if ( $caras_activas > 0 ) {
            $pasadas = (int) ceil( $caras_activas / $capacidad_maquina );
            if ( $colores_dorso > 0 ) {
                $pasadas *= 2;
            }
        }

        $setup_horas = self::get_setup_horas( $maquina );
        $rendimiento_hora = self::get_machine_rendimiento( $maquina );
        $tiempo_tirada_horas = $rendimiento_hora > 0 ? ( $pliegos_utiles / $rendimiento_hora ) : 0.0;
        $tiempo_total_horas = $setup_horas + $tiempo_tirada_horas;

        $costo_hora = isset( $maquina['costo_hora'] ) ? max( 0.0, (float) $maquina['costo_hora'] ) : 0.0;
        $costo_produccion = $tiempo_total_horas * $costo_hora;

        $warnings = $sheet_context['warnings'];
        if ( ! $is_viable ) {
            $warnings[] = __( 'Trabajo inviable: no entra en el pliego útil configurado.', 'core-print-offset' );
        }
        if ( $rendimiento_hora <= 0 ) {
            $warnings[] = __( 'Sin rendimiento de máquina para estimar tiempo de tirada.', 'core-print-offset' );
        }

        return array(
            'pliegos'                  => (int) $pliegos_utiles,
            'pliegos_utiles'           => (int) $pliegos_utiles,
            'pliegos_base'             => (int) $pliegos_base,
            'pliegos_base_compra'      => (int) $pliegos_base,
            'pliegos_base_tecnicos'    => (int) $pliegos_base,
            'pliegos_necesarios'       => (int) $pliegos_base,
            'formas_por_pliego'        => (int) $formas_por_pliego,
            'forms_per_sheet_auto'     => (int) $formas_por_pliego_auto,
            'forms_per_sheet_override' => $formas_por_pliego_override > 0 ? (int) $formas_por_pliego_override : null,
            'chapas'                   => (int) $chapas,
            'pasadas'                  => (int) $pasadas,
            'tiempo_horas'             => round( $tiempo_total_horas, 2 ),
            'merma_pliegos'            => (int) $merma_pliegos,
            'is_viable'                => $is_viable,
            'costo_produccion'         => round( $costo_produccion, 2 ),
            'colores_frente'           => (int) $colores_frente,
            'colores_dorso'            => (int) $colores_dorso,
            'base_sheet_mm'            => $sheet_context['base_sheet_mm'],
            'use_cut_sheet'            => $sheet_context['use_cut_sheet'],
            'cut_mode'                 => $sheet_context['cut_mode'],
            'cut_fraction'             => $sheet_context['cut_fraction'],
            'useful_sheet_mm'          => $sheet_context['useful_sheet_mm'],
            'pieces_per_base'          => (int) $pieces_per_base,
            'production_summary'       => self::build_summary(
                $formas_por_pliego,
                $merma_pliegos,
                $chapas,
                $colores_frente,
                $colores_dorso,
                $pasadas,
                $pliegos_utiles,
                $pliegos_base,
                $pieces_per_base,
                $tiempo_total_horas
            ),
            'warnings'                 => array_values( array_unique( $warnings ) ),
        );
    }

    public static function derive_sheet_context( array $snapshot ): array {
        $base_sheet_mm = self::resolve_base_sheet_mm( $snapshot );
        $use_cut_sheet = ! empty( $snapshot['use_cut_sheet'] );
        $cut_mode = $use_cut_sheet ? sanitize_key( (string) ( $snapshot['cut_mode'] ?? 'fraction' ) ) : 'none';
        if ( ! in_array( $cut_mode, array( 'fraction', 'custom' ), true ) ) {
            $cut_mode = 'fraction';
        }

        $cut_fraction = null;
        $pieces_per_base = 1;
        $useful_sheet_mm = $base_sheet_mm;
        $warnings = array();

        if ( $use_cut_sheet ) {
            if ( 'custom' === $cut_mode ) {
                $custom_w = max( 0.0, (float) ( $snapshot['useful_sheet_ancho_mm'] ?? $snapshot['pliego_ancho_mm'] ?? 0 ) );
                $custom_h = max( 0.0, (float) ( $snapshot['useful_sheet_alto_mm'] ?? $snapshot['pliego_alto_mm'] ?? 0 ) );
                if ( $custom_w > 0 && $custom_h > 0 ) {
                    $useful_sheet_mm = array( $custom_w, $custom_h );
                } else {
                    $warnings[] = __( 'Definí ancho y alto del pliego útil personalizado.', 'core-print-offset' );
                }

                $pieces_override = max( 0, (int) ( $snapshot['pieces_per_base'] ?? 0 ) );
                if ( $pieces_override > 0 ) {
                    $pieces_per_base = $pieces_override;
                } else {
                    $estimated = self::estimate_custom_pieces_per_base( $base_sheet_mm, $useful_sheet_mm );
                    $pieces_per_base = max( 1, $estimated );
                }
            } else {
                $fraction_map = array(
                    '1/2' => 2,
                    '1/3' => 3,
                    '1/4' => 4,
                );
                $cut_fraction = (string) ( $snapshot['cut_fraction'] ?? '' );
                if ( ! isset( $fraction_map[ $cut_fraction ] ) ) {
                    $cut_fraction = '1/2';
                }
                $pieces_per_base = $fraction_map[ $cut_fraction ];
                $useful_sheet_mm = self::calculate_fraction_sheet( $base_sheet_mm, $pieces_per_base );
            }
        }

        return array(
            'base_sheet_mm'   => $base_sheet_mm,
            'use_cut_sheet'   => $use_cut_sheet,
            'cut_mode'        => $use_cut_sheet ? $cut_mode : 'none',
            'cut_fraction'    => $cut_fraction,
            'useful_sheet_mm' => $useful_sheet_mm,
            'pieces_per_base' => max( 1, (int) $pieces_per_base ),
            'warnings'        => $warnings,
        );
    }

    private static function resolve_base_sheet_mm( array $snapshot ): array {
        $base_w = max( 0.0, (float) ( $snapshot['base_sheet_ancho_mm'] ?? 0 ) );
        $base_h = max( 0.0, (float) ( $snapshot['base_sheet_alto_mm'] ?? 0 ) );

        if ( $base_w > 0 && $base_h > 0 ) {
            return array( $base_w, $base_h );
        }

        $pliego_w = max( 0.0, (float) ( $snapshot['pliego_ancho_mm'] ?? 0 ) );
        $pliego_h = max( 0.0, (float) ( $snapshot['pliego_alto_mm'] ?? 0 ) );
        if ( $pliego_w > 0 && $pliego_h > 0 ) {
            return array( $pliego_w, $pliego_h );
        }

        if ( ! empty( $snapshot['pliego_formato'] ) ) {
            $parsed = self::parse_pliego_format( (string) $snapshot['pliego_formato'] );
            if ( $parsed ) {
                return array( (float) $parsed['ancho_mm'], (float) $parsed['alto_mm'] );
            }
        }

        if ( ! empty( $snapshot['material_formato_base'] ) ) {
            $parsed = self::parse_pliego_format( (string) $snapshot['material_formato_base'] );
            if ( $parsed ) {
                return array( (float) $parsed['ancho_mm'], (float) $parsed['alto_mm'] );
            }
        }

        return array( 700.0, 1000.0 );
    }

    private static function calculate_fraction_sheet( array $base_sheet_mm, int $pieces ): array {
        $base_w = (float) $base_sheet_mm[0];
        $base_h = (float) $base_sheet_mm[1];
        if ( $pieces <= 1 ) {
            return array( $base_w, $base_h );
        }

        $candidate_w = $base_w / $pieces;
        $candidate_h = $base_h / $pieces;

        if ( $candidate_w >= $candidate_h ) {
            return array( round( $candidate_w, 2 ), round( $base_h, 2 ) );
        }

        return array( round( $base_w, 2 ), round( $candidate_h, 2 ) );
    }

    private static function estimate_custom_pieces_per_base( array $base_sheet_mm, array $useful_sheet_mm ): int {
        $base_w = max( 0.0, (float) $base_sheet_mm[0] );
        $base_h = max( 0.0, (float) $base_sheet_mm[1] );
        $useful_w = max( 0.0, (float) $useful_sheet_mm[0] );
        $useful_h = max( 0.0, (float) $useful_sheet_mm[1] );

        if ( $base_w <= 0 || $base_h <= 0 || $useful_w <= 0 || $useful_h <= 0 ) {
            return 1;
        }

        $fit_normal = (int) floor( $base_w / $useful_w ) * (int) floor( $base_h / $useful_h );
        $fit_rotated = (int) floor( $base_w / $useful_h ) * (int) floor( $base_h / $useful_w );

        return max( 1, max( $fit_normal, $fit_rotated ) );
    }

    private static function parse_pliego_format( string $format ): ?array {
        $normalized = str_replace( ',', '.', strtolower( trim( $format ) ) );
        if ( ! preg_match( '/([0-9]+(?:\.[0-9]+)?)\s*[x×]\s*([0-9]+(?:\.[0-9]+)?)/', $normalized, $matches ) ) {
            return null;
        }

        $raw_w = (float) $matches[1];
        $raw_h = (float) $matches[2];
        $is_cm = strpos( $normalized, 'cm' ) !== false || ( $raw_w <= 200 && $raw_h <= 200 );

        return array(
            'ancho_mm' => $is_cm ? ( $raw_w * 10 ) : $raw_w,
            'alto_mm'  => $is_cm ? ( $raw_h * 10 ) : $raw_h,
        );
    }

    private static function parse_colores( string $colores ): array {
        $parts = array_pad( explode( '/', $colores ), 2, '0' );

        return array(
            'frente' => max( 0, (int) trim( $parts[0] ) ),
            'dorso'  => max( 0, (int) trim( $parts[1] ) ),
        );
    }

    private static function get_machine_color_capacity( ?array $maquina ): int {
        if ( ! $maquina ) {
            return 4;
        }

        $tipo = isset( $maquina['tipo'] ) ? (string) $maquina['tipo'] : '';
        if ( preg_match( '/(\d+)/', $tipo, $matches ) ) {
            return max( 1, (int) $matches[1] );
        }

        return 4;
    }

    private static function get_machine_rendimiento( ?array $maquina ): int {
        if ( ! $maquina ) {
            return 0;
        }

        $rendimiento = 0;
        if ( isset( $maquina['rendimiento_pliegos_hora'] ) && $maquina['rendimiento_pliegos_hora'] !== null ) {
            $rendimiento = (int) $maquina['rendimiento_pliegos_hora'];
        } elseif ( isset( $maquina['rendimiento_hora'] ) ) {
            $rendimiento = (int) $maquina['rendimiento_hora'];
        }

        return max( 0, $rendimiento );
    }

    private static function get_setup_horas( ?array $maquina ): float {
        if ( ! $maquina ) {
            return 0.0;
        }

        $setup_min = isset( $maquina['setup_min'] ) ? max( 0.0, (float) $maquina['setup_min'] ) : 0.0;

        return $setup_min / 60;
    }

    private static function get_setup_merma_pliegos( ?array $maquina ): int {
        if ( ! $maquina ) {
            return 0;
        }

        $setup_min = isset( $maquina['setup_min'] ) ? max( 0.0, (float) $maquina['setup_min'] ) : 0.0;

        return (int) ceil( $setup_min );
    }

    private static function build_summary(
        int $formas_por_pliego,
        int $merma_pliegos,
        int $chapas,
        int $colores_frente,
        int $colores_dorso,
        int $pasadas,
        int $pliegos_utiles,
        int $pliegos_base,
        int $pieces_per_base,
        float $tiempo_horas
    ): string {
        return sprintf(
            'Pliego útil: %1$d formas/pliego • Merma: %2$d pliegos • Pasadas: %3$d (%4$d/%5$d) • Chapas: %6$d • Pliegos útiles: %7$d • Piezas/base: %8$d • Pliegos base: %9$d • %10$s hs máquina',
            $formas_por_pliego,
            $merma_pliegos,
            $pasadas,
            $colores_frente,
            $colores_dorso,
            $chapas,
            $pliegos_utiles,
            $pieces_per_base,
            $pliegos_base,
            number_format( $tiempo_horas, 1, '.', '' )
        );
    }
}
