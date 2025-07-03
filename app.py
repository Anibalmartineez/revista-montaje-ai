from flask import Flask, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import openai
import os
from werkzeug.utils import secure_filename
from validador import validar_archivo_pdf


# Cliente OpenAI moderno
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("output", exist_ok=True)
output_pdf_path = "output/montado.pdf"

HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Creativa CTP – Diagnóstico y Montaje</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --color-bg: #f5f9ff;
      --color-primary: #007bff;
      --color-secondary: #28a745;
      --color-danger: #dc3545;
      --color-gray: #6c757d;
    }

    body {
      font-family: 'Poppins', sans-serif;
      background: var(--color-bg);
      margin: 0;
      padding: 0;
    }

    .container {
      max-width: 720px;
      margin: 60px auto;
      background: #fff;
      border-radius: 20px;
      padding: 40px 30px;
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.1);
      animation: fadeIn 1s ease-in-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }

    h2 {
      text-align: center;
      color: #222;
      font-size: 28px;
      margin-bottom: 30px;
    }

    form {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 15px;
    }

    input[type="file"], input[type="number"] {
      border: 2px dashed var(--color-primary);
      padding: 14px;
      border-radius: 12px;
      width: 100%;
      background: #f8fbff;
      font-size: 15px;
      cursor: pointer;
    }

    input[type="number"] {
      border-style: solid;
      border-color: #ccc;
    }

    button {
      width: 100%;
      max-width: 360px;
      padding: 14px;
      font-size: 16px;
      border-radius: 10px;
      border: none;
      color: white;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
    }

    button[value="montar"] {
      background-color: var(--color-primary);
    }

    button[value="montar"]:hover {
      background-color: #0056b3;
    }

    button[value="diagnostico"] {
      background-color: var(--color-secondary);
    }

    button[value="diagnostico"]:hover {
      background-color: #1e7e34;
    }

    button[value="corregir_sangrado"] {
      background-color: var(--color-danger);
    }

    button[value="corregir_sangrado"]:hover {
      background-color: #bd2130;
    }

    button[value="redimensionar"] {
      background-color: var(--color-gray);
    }

    button[value="redimensionar"]:hover {
      background-color: #5a6268;
    }

    .mensaje {
      text-align: center;
      color: red;
      font-weight: bold;
      margin-top: 20px;
    }

    pre {
      background: #f1f1f1;
      padding: 20px;
      border-radius: 10px;
      font-size: 14px;
      overflow-x: auto;
      margin-top: 30px;
      white-space: pre-wrap;
    }

    .diagnostico-titulo {
      font-size: 20px;
      margin-top: 35px;
      color: var(--color-primary);
      border-bottom: 2px solid var(--color-primary);
      padding-bottom: 8px;
    }

    .descargar-link {
      display: block;
      text-align: center;
      margin-top: 30px;
      font-size: 16px;
      text-decoration: none;
      color: var(--color-primary);
      font-weight: 600;
    }

    .descargar-link:hover {
      text-decoration: underline;
    }

    @media (max-width: 600px) {
      .container {
        margin: 20px auto;
        padding: 25px 20px;
        border-radius: 14px;
      }

      h2 {
        font-size: 24px;
        margin-bottom: 20px;
      }

      input[type="file"], input[type="number"] {
        font-size: 14px;
        padding: 12px;
      }

      button {
        font-size: 14px;
        padding: 12px;
        max-width: 100%;
      }

      pre {
        font-size: 13px;
        padding: 15px;
      }

      .diagnostico-titulo {
        font-size: 18px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>🧠 Diagnóstico & Montaje de Revista PDF</h2>
    <form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf" required>
  <input type="number" step="0.1" name="nuevo_ancho" placeholder="Nuevo ancho en mm (para redimensionar)">
  <input type="number" step="0.1" name="nuevo_alto" placeholder="Nuevo alto en mm (opcional)">

  <select name="modo_montaje" required style="padding: 12px; border-radius: 10px; border: 2px solid #ccc; font-size: 15px; width: 100%;">
    <option value="4" selected>🗞️ Montaje 4 páginas por cara (revista cosido a caballete)</option>
    <option value="2">📰 Montaje 2 páginas por cara (libro frente/dorso)</option>
  </select>

  <button name='action' value='montar'>📄 Montar Revista</button>
  <button name='action' value='diagnostico'>🔍 Diagnóstico Técnico (IA)</button>
  <button name='action' value='corregir_sangrado'>✂️ Corregir Márgenes y Sangrado</button>
  <button name='action' value='redimensionar'>📐 Redimensionar PDF</button>
</form>


    {% if mensaje %}
      <p class="mensaje">{{ mensaje }}</p>
    {% endif %}

    {% if output_pdf %}
      <a href="{{ url_for('descargar_pdf') }}" class="descargar-link">📥 Descargar PDF Procesado</a>
    {% endif %}

    {% if diagnostico %}
      <h3 class="diagnostico-titulo">📊 Diagnóstico IA:</h3>
      <pre>{{ diagnostico }}</pre>
    {% endif %}
  </div>
</body>
</html>
"""



@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = ""
    if request.method == "POST":
        try:
            if 'pdf' not in request.files:
                raise Exception("No se seleccionó ningún archivo.")
            archivo = request.files['pdf']
            if archivo.filename == '':
                raise Exception("Debes subir un archivo PDF válido.")

            path_pdf = validar_archivo_pdf(archivo, UPLOAD_FOLDER)
            action = request.form.get("action")
            modo_montaje = int(request.form.get("modo_montaje", 4))
            output_path = os.path.join("output", "montado.pdf")

            if action == "montar":
                montar_pdf(path_pdf, output_path, paginas_por_cara=modo_montaje)
                return send_file(output_path, as_attachment=True)

            mensaje = "⚠️ Función no implementada para esta acción."
        except Exception as e:
            mensaje = f"❌ Error al procesar el archivo: {str(e)}"
    return render_template_string(HTML, mensaje=mensaje)


@app.route('/descargar')
def descargar_pdf():
    return send_file(output_pdf_path, as_attachment=True)

def montar_pdf(input_path, output_path, paginas_por_cara=4):
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    doc = fitz.open(input_path)
    if len(doc) == 0:
        raise Exception("El PDF está vacío o corrupto.")
    total_paginas = len(doc)
    while total_paginas % 4 != 0:
        doc.insert_page(-1)
        total_paginas += 1

    salida = fitz.open()
    A4_WIDTH, A4_HEIGHT = fitz.paper_size("a4")
    paginas = list(range(1, total_paginas + 1))
    hojas = []

    while paginas:
        if paginas_por_cara == 4 and len(paginas) >= 8:
            frente = [paginas[-1], paginas[0], paginas[2], paginas[-3]]
            dorso = [paginas[1], paginas[-2], paginas[-4], paginas[3]]
            hojas.append((frente, dorso))
            paginas = paginas[4:-4]
        elif paginas_por_cara == 2 and len(paginas) >= 4:
            frente = [paginas[-1], paginas[0]]
            dorso = [paginas[1], paginas[-2]]
            hojas.append((frente, dorso))
            paginas = paginas[2:-2]
        else:
            frente = paginas[:paginas_por_cara]
            dorso = paginas[paginas_por_cara:paginas_por_cara*2]
            hojas.append((frente, dorso))
            paginas = paginas[paginas_por_cara*2:]

    def insertar_pagina(nueva_pagina, idx, pos):
        if not idx or idx < 1 or idx > len(doc): return
        pagina = doc[idx - 1]
        pix = pagina.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        if paginas_por_cara == 4:
            x = (pos % 2) * (A4_WIDTH / 2)
            y = (pos // 2) * (A4_HEIGHT / 2)
            rect = fitz.Rect(x, y, x + A4_WIDTH / 2, y + A4_HEIGHT / 2)
        else:
            x = (pos % 2) * (A4_WIDTH / 2)
            y = 0
            rect = fitz.Rect(x, y, x + A4_WIDTH / 2, A4_HEIGHT)
        rotar = 180 if pos >= 2 else 0 if paginas_por_cara == 4 else 0
        nueva_pagina.insert_image(rect, stream=buffer, rotate=rotar)
        buffer.close()

    for frente, dorso in hojas:
        pag_frente = salida.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        for j, idx in enumerate(frente):
            insertar_pagina(pag_frente, idx, j)
        pag_dorso = salida.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        for j, idx in enumerate(dorso):
            insertar_pagina(pag_dorso, idx, j)

    salida.save(output_path)



def diagnosticar_pdf(path):
    import fitz
    import math

    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    crop = first_page.cropbox
    ancho_mm = round(crop.width * 25.4 / 72, 2)
    alto_mm = round(crop.height * 25.4 / 72, 2)

    contenido_dict = first_page.get_text("dict")
    drawings = first_page.get_drawings()

    # -------------------------------
    # DETECCIÓN DE TROQUEL RECTANGULAR
    # -------------------------------
    rectangulos_detectados = []
    tolerancia = 5  # en puntos PDF (~1.8 mm)

    for d in drawings:
        puntos = []
        for item in d["items"]:
            if len(item) == 4:
                x0, y0, x1, y1 = item
                puntos.append((x0, y0))
                puntos.append((x1, y1))
        if not puntos:
            continue

        xs = [p[0] for p in puntos]
        ys = [p[1] for p in puntos]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        ancho = max_x - min_x
        alto = max_y - min_y

        if ancho > 40 and alto > 40:
            rectangulos_detectados.append((min_x, min_y, max_x, max_y))

    if rectangulos_detectados:
        # Elegimos el más grande como troquel
        troquel = max(rectangulos_detectados, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        min_x, min_y, max_x, max_y = troquel
        troquel_ancho_mm = round((max_x - min_x) * 25.4 / 72, 2)
        troquel_alto_mm = round((max_y - min_y) * 25.4 / 72, 2)
        medida_util = f"{troquel_ancho_mm} × {troquel_alto_mm} mm (Detectado como troquel por vectores)"
    else:
        # Fallback → contenido visual
        bloques = []
        for bloque in contenido_dict.get("blocks", []):
            if "bbox" in bloque:
                x0, y0, x1, y1 = bloque["bbox"]
                if (x1 - x0) * (y1 - y0) > 1000:
                    bloques.append((x0, y0, x1, y1))
        for img in first_page.get_images(full=True):
            try:
                bbox = first_page.get_image_bbox(img)
                x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
                if (x1 - x0) * (y1 - y0) > 1000:
                    bloques.append((x0, y0, x1, y1))
            except:
                continue
        if bloques:
            min_x = min(b[0] for b in bloques)
            min_y = min(b[1] for b in bloques)
            max_x = max(b[2] for b in bloques)
            max_y = max(b[3] for b in bloques)
            util_ancho_mm = round((max_x - min_x) * 25.4 / 72, 2)
            util_alto_mm = round((max_y - min_y) * 25.4 / 72, 2)
            medida_util = f"{util_ancho_mm} × {util_alto_mm} mm (Detectado por contenido visual)"
        else:
            medida_util = "No se detectó contenido útil significativo"

    # -------------------------------
    # RESOLUCIÓN IMAGEN RASTER
    # -------------------------------
    dpi_info = "No se detectaron imágenes rasterizadas."
    image_list = first_page.get_images(full=True)
    if image_list:
        xref = image_list[0][0]
        base_image = doc.extract_image(xref)
        img_width = base_image["width"]
        img_height = base_image["height"]
        width_inch = crop.width / 72
        height_inch = crop.height / 72
        dpi_x = round(img_width / width_inch, 1)
        dpi_y = round(img_height / height_inch, 1)
        dpi_info = f"{dpi_x} x {dpi_y} DPI (1.ª imagen)"

    # -------------------------------
    # RESOLUCIÓN TEXTO
    # -------------------------------
    try:
        resolution = contenido_dict["width"]
    except:
        resolution = "No se pudo detectar"

    resumen = f"""
A) Tamaño de página: {ancho_mm} × {alto_mm} mm
B) Medida útil detectada: {medida_util}
C) Resolución estimada del texto: {resolution}
D) Resolución imagen raster: {dpi_info}
E) Páginas: {len(doc)}
F) Metadatos: {info}
"""

    prompt = f"""Sos un experto en preprensa. Analizá este diagnóstico técnico y explicalo para un operador gráfico. La clave está en el punto B, que es el área útil real, basada en el troquel si se detecta.\n\n{resumen}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"[ERROR] No se pudo generar el diagnóstico con OpenAI: {e}"








def corregir_sangrado(input_path, output_path):
    import fitz  # PyMuPDF
    from PIL import Image
    import numpy as np
    from io import BytesIO

    margen_mm = 3
    dpi = 150  # calidad razonable
    margen_px = int((margen_mm / 25.4) * dpi)

    def replicar_bordes(img, margen_px):
        arr = np.array(img)

        top = np.tile(arr[0:1, :, :], (margen_px, 1, 1))
        bottom = np.tile(arr[-1:, :, :], (margen_px, 1, 1))
        extended_vertical = np.vstack([top, arr, bottom])

        left = np.tile(extended_vertical[:, 0:1, :], (1, margen_px, 1))
        right = np.tile(extended_vertical[:, -1:, :], (1, margen_px, 1))
        extended_full = np.hstack([left, extended_vertical, right])

        return Image.fromarray(extended_full)

    doc = fitz.open(input_path)
    nuevo_doc = fitz.open()

    for pagina in doc:
        pix = pagina.get_pixmap(dpi=dpi, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Replicar bordes como sangrado
        img_con_sangrado = replicar_bordes(img, margen_px)

        # Convertir imagen extendida a bytes
        buffer = BytesIO()
        img_con_sangrado.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        # Crear nueva página del tamaño correspondiente
        ancho_pts = img_con_sangrado.width * 72 / dpi
        alto_pts = img_con_sangrado.height * 72 / dpi
        nueva_pagina = nuevo_doc.new_page(width=ancho_pts, height=alto_pts)

        rect = fitz.Rect(0, 0, ancho_pts, alto_pts)
        nueva_pagina.insert_image(rect, stream=buffer)

        buffer.close()
        del pix, img, img_con_sangrado

    nuevo_doc.save(output_path)



def redimensionar_pdf(input_path, output_path, nuevo_ancho_mm, nuevo_alto_mm=None):
    import fitz  # PyMuPDF

    doc = fitz.open(input_path)
    nuevo_doc = fitz.open()

    ancho_pts = nuevo_ancho_mm * 72 / 25.4

    if nuevo_alto_mm:
        alto_pts = nuevo_alto_mm * 72 / 25.4
    else:
        # Escalado proporcional según la primera página
        pagina = doc[0]
        proporcion = pagina.rect.height / pagina.rect.width
        alto_pts = ancho_pts * proporcion

    for pagina in doc:
        pix = pagina.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        ancho_original = pagina.rect.width
        alto_original = pagina.rect.height
        escala_x = ancho_pts / ancho_original
        escala_y = alto_pts / alto_original
        escala = min(escala_x, escala_y)

        nueva_pagina = nuevo_doc.new_page(width=ancho_pts, height=alto_pts)
        nueva_pagina.show_pdf_page(
            fitz.Rect(0, 0, ancho_pts, alto_pts),
            doc,
            pagina.number,
            rotate=0,
            clip=None,
            oc=0,
            overlay=False,
            keep_proportion=True,
            scale=escala
        )

    nuevo_doc.save(output_path)



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
