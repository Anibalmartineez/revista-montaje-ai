import base64
import json
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from ia_sugerencias import chat_completion
from diagnostico_pdf import diagnosticar_pdf


def analizar_grafico_tecnico(path_img):
    """Analiza un gráfico financiero detectando líneas y genera interpretación IA."""
    image = cv2.imread(path_img)
    if image is None:
        raise Exception("No se pudo leer la imagen.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    lineas_detectadas = cv2.HoughLinesP(
        edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10
    )
    lineas = []

    if lineas_detectadas is not None:
        for linea in lineas_detectadas[:20]:
            x1, y1, x2, y2 = map(int, linea[0])
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            lineas.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    buffer = BytesIO()
    img_pil.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    prompt = f"""
Eres un experto en análisis técnico bursátil. Se detectaron las siguientes líneas principales en un gráfico financiero (líneas de soporte, resistencia o tendencias). Basado en estas coordenadas (en formato de líneas con punto inicial y final):

{json.dumps(lineas, indent=2)}

Simula una breve interpretación como si fueras un analista técnico. Indica si se observa un canal, una tendencia, y si sería un buen momento para comprar, vender o esperar. Usa un tono profesional y claro.
"""
    try:
        resumen = chat_completion(prompt)
    except Exception as e:
        resumen = f"No se pudo generar el análisis técnico automático. Detalle: {str(e)}"

    return resumen, img_base64


__all__ = ["diagnosticar_pdf", "analizar_grafico_tecnico"]
