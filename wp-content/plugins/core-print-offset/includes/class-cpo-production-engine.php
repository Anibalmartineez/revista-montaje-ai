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
        $ancho_trabajo = max( 0.0, (float) ( $snapshot['ancho_mm'] ?? 0 ) );
        $alto_trabajo = max( 0.0, (float) ( $snapshot['alto_mm'] ?? 0 ) );
        $sangrado_mm = max( 0.0, (float) ( $snapshot['sangrado_mm'] ?? 0 ) );

        if ( $sangrado_mm > 0 ) {
            $ancho_trabajo += ( $sangrado_mm * 2 );
            $alto_trabajo += ( $sangrado_mm * 2 );
        }

        $pliego_ancho_mm = max( 0.0, (float) ( $snapshot['pliego_ancho_mm'] ?? 0 ) );
        $pliego_alto_mm = max( 0.0, (float) ( $snapshot['pliego_alto_mm'] ?? 0 ) );
        if ( ( ! $pliego_ancho_mm || ! $pliego_alto_mm ) && ! empty( $snapshot['pliego_formato'] ) ) {
            $parsed = self::parse_pliego_format( (string) $snapshot['pliego_formato'] );
            if ( $parsed ) {
                $pliego_ancho_mm = (float) $parsed['ancho_mm'];
                $pliego_alto_mm = (float) $parsed['alto_mm'];
            }
        }

        $colores = self::parse_colores( (string) ( $snapshot['colores'] ?? '0/0' ) );
        $colores_frente = $colores['frente'];
        $colores_dorso = $colores['dorso'];

        $util_ancho = max( 0.0, $pliego_ancho_mm - ( self::MARGEN_LATERAL_MM * 2 ) );
        $util_alto = max( 0.0, $pliego_alto_mm - self::PINZA_MM - self::COLA_MM );

        $formas_horizontal = $ancho_trabajo > 0 ? (int) floor( $util_ancho / $ancho_trabajo ) : 0;
        $formas_vertical = $alto_trabajo > 0 ? (int) floor( $util_alto / $alto_trabajo ) : 0;
        $formas_por_pliego = max( 0, $formas_horizontal * $formas_vertical );
        $is_viable = $formas_por_pliego > 0;

        $pliegos_base = $is_viable ? (int) ceil( $cantidad / $formas_por_pliego ) : 0;
        $merma_setup_pliegos = self::get_setup_merma_pliegos( $maquina );
        $merma_pct = self::MERMA_BASE_PCT;
        if ( $pliegos_base > 0 ) {
            $merma_pct += floor( $pliegos_base / 1000 ) * self::MERMA_EXTRA_EVERY_1000_PCT;
        }
        $merma_porcentaje_pliegos = (int) ceil( $pliegos_base * ( $merma_pct / 100 ) );
        $merma_pliegos = $merma_porcentaje_pliegos + $merma_setup_pliegos;
        $pliegos_final = $pliegos_base + $merma_pliegos;

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
        $tiempo_tirada_horas = $rendimiento_hora > 0 ? ( $pliegos_final / $rendimiento_hora ) : 0.0;
        $tiempo_total_horas = $setup_horas + $tiempo_tirada_horas;

        $costo_hora = isset( $maquina['costo_hora'] ) ? max( 0.0, (float) $maquina['costo_hora'] ) : 0.0;
        $costo_produccion = $tiempo_total_horas * $costo_hora;

        $warnings = array();
        if ( ! $is_viable ) {
            $warnings[] = __( 'Trabajo inviable: no entra en pliego con área útil actual.', 'core-print-offset' );
        }
        if ( $rendimiento_hora <= 0 ) {
            $warnings[] = __( 'Sin rendimiento de máquina para estimar tiempo de tirada.', 'core-print-offset' );
        }

        return array(
            'pliegos'            => (int) $pliegos_final,
            'pliegos_base'       => (int) $pliegos_base,
            'formas_por_pliego'  => (int) $formas_por_pliego,
            'chapas'             => (int) $chapas,
            'pasadas'            => (int) $pasadas,
            'tiempo_horas'       => round( $tiempo_total_horas, 2 ),
            'merma_pliegos'      => (int) $merma_pliegos,
            'is_viable'          => $is_viable,
            'costo_produccion'   => round( $costo_produccion, 2 ),
            'colores_frente'     => (int) $colores_frente,
            'colores_dorso'      => (int) $colores_dorso,
            'production_summary' => self::build_summary(
                $formas_por_pliego,
                $merma_pliegos,
                $chapas,
                $colores_frente,
                $colores_dorso,
                $pasadas,
                $pliegos_final,
                $tiempo_total_horas
            ),
            'warnings'           => $warnings,
        );
    }

    private static function parse_pliego_format( string $format ): ?array {
        $normalized = str_replace( ',', '.', strtolower( trim( $format ) ) );
        if ( ! preg_match( '/([0-9]+(?:\\.[0-9]+)?)\\s*[x×]\\s*([0-9]+(?:\\.[0-9]+)?)/', $normalized, $matches ) ) {
            return null;
        }

        return array(
            'ancho_mm' => (float) $matches[1],
            'alto_mm'  => (float) $matches[2],
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
        if ( preg_match( '/(\\d+)/', $tipo, $matches ) ) {
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
        int $pliegos,
        float $tiempo_horas
    ): string {
        return sprintf(
            'Pliego: %1$d formas/pliego • Merma: %2$d pliegos • Pasadas: %3$d (%4$d/%5$d) • Chapas frente/dorso: %6$d • Tirada: %7$d pliegos • %8$s hs máquina',
            $formas_por_pliego,
            $merma_pliegos,
            $pasadas,
            $colores_frente,
            $colores_dorso,
            $chapas,
            $pliegos,
            number_format( $tiempo_horas, 1, '.', '' )
        );
    }
}
