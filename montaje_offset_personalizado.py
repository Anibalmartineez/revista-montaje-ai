import os
import tempfile
from typing import Dict, List

from PyPDF2 import PdfReader, PdfWriter

from montaje_offset_inteligente import montar_pliego_offset_inteligente


def montar_pliego_offset_personalizado(specs: List[Dict], pro_config: Dict) -> str:
    """Modo super personalizado básico reutilizando motor estándar.

    Parameters
    ----------
    specs: lista de dicts por archivo
    pro_config: configuración general del pliego

    Returns
    -------
    str
        Ruta del PDF generado.
    """
    diseños = []
    tmp_paths: List[str] = []
    for spec in specs:
        file_storage = spec.get("file")
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(tmp_fd, "wb") as tmp:
            tmp.write(file_storage.read())
        if spec.get("rotate"):
            reader = PdfReader(tmp_path)
            writer = PdfWriter()
            for page in reader.pages:
                try:
                    page.rotate_clockwise(90)
                except Exception:
                    page.rotate(90)
                writer.add_page(page)
            with open(tmp_path, "wb") as out_f:
                writer.write(out_f)
        repeticiones = spec.get("reps") or 1
        diseños.append((tmp_path, repeticiones))
        tmp_paths.append(tmp_path)

    output_path = os.path.join("output", "pliego_offset_pro.pdf")
    montar_pliego_offset_inteligente(
        diseños,
        pro_config.get("ancho_pliego", 0),
        pro_config.get("alto_pliego", 0),
        separacion=pro_config.get("separacion", 4),
        sangrado=0.0,
        espaciado_horizontal=pro_config.get("espaciado_horizontal", 0),
        espaciado_vertical=pro_config.get("espaciado_vertical", 0),
        margen_izq=pro_config.get("margen_izq", 10),
        margen_der=pro_config.get("margen_der", 10),
        margen_sup=pro_config.get("margen_sup", 10),
        margen_inf=pro_config.get("margen_inf", 10),
        cutmarks_por_forma=pro_config.get("cutmarks_global", False),
        export_area_util=pro_config.get("export_area_util", False),
        output_path=output_path,
    )

    for p in tmp_paths:
        try:
            os.remove(p)
        except OSError:
            pass

    return output_path
