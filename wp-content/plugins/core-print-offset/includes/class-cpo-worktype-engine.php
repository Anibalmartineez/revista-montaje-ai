<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class CPO_WorkType_Engine {
    private const DEFAULT_WORK_TYPE = 'afiche_folleto';

    private const LEGACY_WORK_TYPE_MAP = array(
        'revista' => 'revista_catalogo',
        'folleto' => 'afiche_folleto',
        'etiqueta' => 'etiqueta_offset',
        'caja' => 'caja_packaging',
        'troquel' => 'caja_packaging',
    );

    private const CONFIGS = array(
        'afiche_folleto' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => true,
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
        'tarjeta' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => true,
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
        'revista_catalogo' => array(
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
        'caja_packaging' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => true,
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
        'etiqueta_offset' => array(
            'requiere_paginas'          => false,
            'requiere_pliego'           => true,
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
        $work_type = $this->sanitize_work_type( $work_type );
        $fields = array( 'cantidad', 'ancho_mm', 'alto_mm', 'colores', 'material_id' );

        if ( in_array( $work_type, array( 'afiche_folleto', 'tarjeta', 'revista_catalogo', 'caja_packaging', 'etiqueta_offset' ), true ) ) {
            $fields[] = 'pliego_formato';
        }

        if ( 'revista_catalogo' === $work_type ) {
            $fields[] = 'paginas';
            $fields[] = 'encuadernacion';
        }

        return array_values( array_unique( $fields ) );
    }

    public function validate_job_structure( $data ): array {
        $work_type = $this->sanitize_work_type( $data['work_type'] ?? self::DEFAULT_WORK_TYPE );
        $warnings = array();

        $paginas = isset( $data['paginas'] ) ? (int) $data['paginas'] : 0;
        $troquel = ! empty( $data['troquel'] );
        $encuadernacion = sanitize_text_field( (string) ( $data['encuadernacion'] ?? '' ) );

        if ( 'revista_catalogo' === $work_type ) {
            if ( $paginas <= 0 ) {
                $warnings[] = __( 'Revista/Catálogo requiere definir páginas.', 'core-print-offset' );
            } elseif ( $paginas % 4 !== 0 ) {
                $warnings[] = __( 'Revista/Catálogo requiere múltiplos de 4 páginas.', 'core-print-offset' );
            }

            if ( '' === $encuadernacion ) {
                $warnings[] = __( 'Revista/Catálogo requiere encuadernación.', 'core-print-offset' );
            }
        }

        if ( 'tarjeta' === $work_type ) {
            if ( $paginas > 1 ) {
                $warnings[] = __( 'Tarjeta se calcula como pieza simple (1 cara o frente/dorso).', 'core-print-offset' );
            }
            $warnings[] = __( 'Tip: para tarjeta agrega laminado o barniz desde Procesos extras.', 'core-print-offset' );
        }

        if ( 'caja_packaging' === $work_type ) {
            if ( ! $troquel ) {
                $warnings[] = __( 'Caja/Packaging suele requerir troquel y pegado según terminación.', 'core-print-offset' );
            }
        }

        if ( 'etiqueta_offset' === $work_type && ! empty( $data['paginas'] ) ) {
            $warnings[] = __( 'Etiqueta offset en pliego no utiliza páginas.', 'core-print-offset' );
        }

        return array(
            'valid' => empty( $warnings ),
            'work_type' => $work_type,
            'config' => $this->get_config( $work_type ),
            'required_fields' => $this->get_required_fields( $work_type ),
            'warnings' => $warnings,
        );
    }

    private function sanitize_work_type( $work_type ): string {
        $work_type = sanitize_key( (string) $work_type );
        if ( isset( self::LEGACY_WORK_TYPE_MAP[ $work_type ] ) ) {
            $work_type = self::LEGACY_WORK_TYPE_MAP[ $work_type ];
        }

        if ( ! isset( self::CONFIGS[ $work_type ] ) ) {
            return self::DEFAULT_WORK_TYPE;
        }

        return $work_type;
    }
}
