<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_WorkType_Engine {
    private const DEFAULT_WORK_TYPE = 'otro';

    private const CONFIGS = array(
        'revista' => array(
            'requiere_paginas'          => true,
            'requiere_pliego'           => true,
            'requiere_troquel'          => false,
            'requiere_encuadernacion'   => true,
            'requiere_material_bobina'  => false,
            'requiere_anilox'           => false,
            'requiere_cilindro'         => false,
            'permite_varios_gramajes'   => true,
            'multiplo_paginas'          => 4,
            'usa_frente_dorso'          => true,
            'usa_colores_especiales'    => true,
        ),
        'folleto' => array(
            'requiere_paginas'          => true,
            'requiere_pliego'           => true,
            'requiere_troquel'          => false,
            'requiere_encuadernacion'   => false,
            'requiere_material_bobina'  => false,
            'requiere_anilox'           => false,
            'requiere_cilindro'         => false,
            'permite_varios_gramajes'   => false,
            'multiplo_paginas'          => 2,
            'usa_frente_dorso'          => true,
            'usa_colores_especiales'    => true,
        ),
        'tarjeta' => array(
            'requiere_paginas'          => true,
            'requiere_pliego'           => false,
            'requiere_troquel'          => false,
            'requiere_encuadernacion'   => false,
            'requiere_material_bobina'  => false,
            'requiere_anilox'           => false,
            'requiere_cilindro'         => false,
            'permite_varios_gramajes'   => false,
            'multiplo_paginas'          => 0,
            'usa_frente_dorso'          => true,
            'usa_colores_especiales'    => true,
        ),
        'etiqueta' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => false,
            'requiere_troquel'          => false,
            'requiere_encuadernacion'   => false,
            'requiere_material_bobina'  => true,
            'requiere_anilox'           => true,
            'requiere_cilindro'         => false,
            'permite_varios_gramajes'   => false,
            'multiplo_paginas'          => 0,
            'usa_frente_dorso'          => false,
            'usa_colores_especiales'    => true,
        ),
        'caja' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => true,
            'requiere_troquel'          => true,
            'requiere_encuadernacion'   => false,
            'requiere_material_bobina'  => false,
            'requiere_anilox'           => false,
            'requiere_cilindro'         => false,
            'permite_varios_gramajes'   => false,
            'multiplo_paginas'          => 0,
            'usa_frente_dorso'          => false,
            'usa_colores_especiales'    => true,
        ),
        'otro' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => false,
            'requiere_troquel'          => false,
            'requiere_encuadernacion'   => false,
            'requiere_material_bobina'  => false,
            'requiere_anilox'           => false,
            'requiere_cilindro'         => false,
            'permite_varios_gramajes'   => false,
            'multiplo_paginas'          => 0,
            'usa_frente_dorso'          => true,
            'usa_colores_especiales'    => true,
        ),
    );

    public function get_config( $work_type ): array {
        $work_type = $this->sanitize_work_type( $work_type );

        return self::CONFIGS[ $work_type ];
    }

    public function get_required_fields( $work_type ): array {
        $config = $this->get_config( $work_type );
        $fields = array();

        if ( ! empty( $config['requiere_paginas'] ) ) {
            $fields[] = 'paginas';
        }
        if ( ! empty( $config['requiere_pliego'] ) ) {
            $fields[] = 'pliego_formato';
        }
        if ( ! empty( $config['requiere_troquel'] ) ) {
            $fields[] = 'troquel';
        }
        if ( ! empty( $config['requiere_encuadernacion'] ) ) {
            $fields[] = 'encuadernacion';
        }
        if ( ! empty( $config['requiere_material_bobina'] ) ) {
            $fields[] = 'material_bobina';
        }
        if ( ! empty( $config['requiere_anilox'] ) ) {
            $fields[] = 'anilox';
        }
        if ( ! empty( $config['requiere_cilindro'] ) ) {
            $fields[] = 'cilindro';
        }
        if ( ! empty( $config['permite_varios_gramajes'] ) ) {
            $fields[] = 'gramaje_interior';
            $fields[] = 'gramaje_tapa';
        }
        if ( ! empty( $config['usa_frente_dorso'] ) ) {
            $fields[] = 'colores';
        }
        if ( ! empty( $config['usa_colores_especiales'] ) ) {
            $fields[] = 'colores_especiales';
        }

        return array_values( array_unique( $fields ) );
    }

    public function validate_job_structure( $data ): array {
        $work_type = $this->sanitize_work_type( $data['work_type'] ?? self::DEFAULT_WORK_TYPE );
        $config = $this->get_config( $work_type );
        $warnings = array();

        $paginas = isset( $data['paginas'] ) ? (int) $data['paginas'] : 0;

        if ( ! empty( $config['requiere_paginas'] ) && $paginas <= 0 ) {
            $warnings[] = __( 'Este tipo de trabajo requiere cantidad de páginas.', 'core-print-offset' );
        }

        $multiplo_paginas = isset( $config['multiplo_paginas'] ) ? (int) $config['multiplo_paginas'] : 0;
        if ( $multiplo_paginas > 0 && $paginas > 0 && $paginas % $multiplo_paginas !== 0 ) {
            $warnings[] = sprintf( __( 'Cantidad de páginas no múltiplo de %d', 'core-print-offset' ), $multiplo_paginas );
        }

        if ( 'revista' === $work_type && empty( $data['encuadernacion'] ) ) {
            $warnings[] = __( 'Revista requiere encuadernación.', 'core-print-offset' );
        }

        if ( 'folleto' === $work_type && ! empty( $data['encuadernacion'] ) ) {
            $warnings[] = __( 'Folleto no usa encuadernación.', 'core-print-offset' );
        }

        if ( 'tarjeta' === $work_type ) {
            if ( $paginas > 0 && 1 !== $paginas ) {
                $warnings[] = __( 'Tarjeta debe tener 1 página.', 'core-print-offset' );
            }
            if ( ! empty( $data['pliego_doble'] ) ) {
                $warnings[] = __( 'Tarjeta no admite pliego doble.', 'core-print-offset' );
            }
        }

        if ( 'etiqueta' === $work_type ) {
            if ( empty( $data['material_bobina'] ) ) {
                $warnings[] = __( 'Etiqueta requiere material bobina.', 'core-print-offset' );
            }
            if ( empty( $data['anilox'] ) ) {
                $warnings[] = __( 'Etiqueta requiere anilox.', 'core-print-offset' );
            }
            if ( $paginas > 0 ) {
                $warnings[] = __( 'Etiqueta no utiliza páginas.', 'core-print-offset' );
            }
        }

        if ( 'caja' === $work_type ) {
            if ( empty( $data['troquel'] ) ) {
                $warnings[] = __( 'Caja requiere troquel.', 'core-print-offset' );
            }
            if ( empty( $data['pliego_formato'] ) ) {
                $warnings[] = __( 'Caja requiere pliego.', 'core-print-offset' );
            }
        }

        return array(
            'valid' => empty( $warnings ),
            'work_type' => $work_type,
            'config' => $config,
            'required_fields' => $this->get_required_fields( $work_type ),
            'warnings' => $warnings,
        );
    }

    private function sanitize_work_type( $work_type ): string {
        $work_type = sanitize_key( (string) $work_type );

        if ( ! isset( self::CONFIGS[ $work_type ] ) ) {
            return self::DEFAULT_WORK_TYPE;
        }

        return $work_type;
    }
}
