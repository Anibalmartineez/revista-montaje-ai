from typing import Any, Dict, List, Tuple


class BaseMontajeStrategy:
    def calcular(
        self,
        disenos: List[Tuple[str, int]],
        config,
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Debe devolver un dict compatible con lo que espera
        'montar_pliego_offset_inteligente' para generar preview o PDF.
        """
        raise NotImplementedError()
