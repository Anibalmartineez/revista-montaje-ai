from flask import Flask, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import openai
import os

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
    body {
      font-family: 'Poppins', sans-serif;
      background: linear-gradient(to right, #e0eafc, #cfdef3);
      margin: 0;
      padding: 0;
    }
    .container {
      max-width: 700px;
      margin: 60px auto;
      background: #fff;
      border-radius: 16px;
      padding: 40px 30px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.1);
      animation: fadeIn 0.8s ease-in-out;
    }
    @keyframes fadeIn {
      from {opacity: 0; transform: translateY(20px);}
      to {opacity: 1; transform: translateY(0);}
    }
    h2 {
      text-align: center;
      color: #222;
      font-size: 26px;
      margin-bottom: 25px;
    }
    form {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    input[type="file"] {
      border: 2px dashed #ccc;
      padding: 12px;
      border-radius: 10px;
      width: 100%;
      margin-bottom: 20px;
      background-color: #f9f9f9;
    }
    button {
      margin: 8px 0;
      padding: 12px 24px;
      background-color: #007bff;
      color: white;
      border: none;
      border-radius: 8px;
      font-weight: bold;
      font-size: 15px;
      width: 100%;
      max-width: 350px;
      transition: background-color 0.3s;
      cursor: pointer;
    }
    button:hover {
      background-color: #0056b3;
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
      color: #333;
      border-bottom: 2px solid #007bff;
      padding-bottom: 8px;
    }
    @media (max-width: 600px) {
  .container {
    margin: 20px auto;
    padding: 20px 15px;
    border-radius: 12px;
  }

  h2 {
    font-size: 22px;
    margin-bottom: 20px;
  }

  input[type="file"] {
    font-size: 14px;
    padding: 10px;
  }

  button {
    font-size: 14px;
    padding: 10px 16px;
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
      <button name='action' value='montar'>📄 Montar Revista (4 páginas por cara)</button>
      <button name='action' value='diagnostico'>🔍 Diagnóstico Técnico (IA)</button>
      <button name='action' value='corregir_sangrado'>✂️ Corregir Márgenes y Sangrado</button>
    </form>
    {% if mensaje %}<p class="mensaje">{{ mensaje }}</p>{% endif %}
    {% if output_pdf %}<p style="text-align:center;"><a href="{{ url_for('descargar_pdf') }}">📥 Descargar PDF Montado</a></p>{% endif %}
    {% if diagnostico %}
      <h3 class="diagnostico-titulo">📊 Diagnóstico IA:</h3>
      <pre>{{ diagnostico }}</pre>
    {% endif %}
  </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    mensaje = ''
    output_pdf = False
    diagnostico = ''

    if request.method == 'POST':
        archivo = request.files['pdf']
        if archivo.filename == '':
            mensaje = 'Ningún archivo seleccionado'
        else:
            path_pdf = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(path_pdf)

            if request.form['action'] == 'montar':
                try:
                    montar_pdf(path_pdf, output_pdf_path)
                    output_pdf = True
                except Exception as e:
                    mensaje = f"Error al procesar el archivo: {e}"

            elif request.form['action'] == 'diagnostico':
                diagnostico = diagnosticar_pdf(path_pdf)

            elif request.form['action'] == 'corregir_sangrado':
                try:
                    corregir_sangrado(path_pdf, output_pdf_path)
                    output_pdf = True
                except Exception as e:
                    mensaje = f"Error al corregir márgenes: {e}"

    return render_template_string(HTML, mensaje=mensaje, output_pdf=output_pdf, diagnostico=diagnostico)

@app.route('/descargar')
def descargar_pdf():
    return send_file(output_pdf_path, as_attachment=True)

def montar_pdf(input_path, output_path):
    from reportlab.lib.pagesizes import A4
    import fitz
    from PIL import Image
    from io import BytesIO

    def generar_compaginacion_cosido(paginas_total):
        paginas = list(range(1, paginas_total + 1))
        while len(paginas) % 4 != 0:
            paginas.append(0)  # Página en blanco

        hojas = []
        while paginas:
            if len(paginas) >= 8:
                frente = [paginas[-1], paginas[0], paginas[1], paginas[-2]]
                dorso  = [paginas[2], paginas[-3], paginas[-4], paginas[3]]
                hojas.append((frente, dorso))
                paginas = paginas[4:-4]
            elif len(paginas) == 4:
                # vuelta y vuelta final
                frente = [paginas[3], paginas[0]]
                dorso = [paginas[1], paginas[2]]
                hojas.append((frente, dorso))
                paginas = []
        return hojas

    doc = fitz.open(input_path)
    total_paginas = len(doc)
    hojas = generar_compaginacion_cosido(total_paginas)
    salida = fitz.open()

    for frente, dorso in hojas:
        for i, cara in enumerate([frente, dorso]):
            nueva_pagina = salida.new_page(width=A4[0], height=A4[1])
            for j, idx in enumerate(cara):
                if idx == 0:
                    continue
                pagina = doc[idx - 1]
                pix = pagina.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=95)
                buffer.seek(0)

                x = (j % 2) * (A4[0] / 2)
                y = (j // 2) * (A4[1] / 2)
                rect = fitz.Rect(x, y, x + A4[0] / 2, y + A4[1] / 2)

                rotar = 180 if j in [0, 1] else 0

                # 🚫 Sin transform, compatible con PyMuPDF antiguo
                nueva_pagina.insert_image(rect, stream=buffer, rotate=rotar)

                buffer.close()
                del pix
                del img

    salida.save(output_path)





def diagnosticar_pdf(path):
    import fitz

    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    crop = first_page.cropbox
    ancho_mm = round(crop.width * 25.4 / 72, 2)
    alto_mm = round(crop.height * 25.4 / 72, 2)

    contenido_dict = first_page.get_text("dict")
    drawings = first_page.get_drawings()

    troquel_lines = []

    for d in drawings:
        for item in d["items"]:
            if len(item) == 4:
                x0, y0, x1, y1 = item
                w = abs(x1 - x0)
                h = abs(y1 - y0)
                if w > 30 or h > 30:  # líneas largas, no decorativas
                    troquel_lines.append((x0, y0, x1, y1))

    if len(troquel_lines) >= 4:
        min_x = min(p[0] for p in troquel_lines)
        min_y = min(p[1] for p in troquel_lines)
        max_x = max(p[2] for p in troquel_lines)
        max_y = max(p[3] for p in troquel_lines)

        troquel_ancho_mm = round((max_x - min_x) * 25.4 / 72, 2)
        troquel_alto_mm = round((max_y - min_y) * 25.4 / 72, 2)
        medida_util = f"{troquel_ancho_mm} × {troquel_alto_mm} mm (Detectado como área de troquel)"
    else:
        # fallback por elementos visuales (texto + imagenes + vectores)
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

    # Resolución de imagen
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

    # Resolución texto
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
    import fitz

    doc = fitz.open(input_path)
    nuevo_doc = fitz.open()

    margen_mm = 3
    margen_pts = margen_mm * 72 / 25.4  # 3 mm en puntos

    for pagina in doc:
        ancho_original = pagina.rect.width
        alto_original = pagina.rect.height

        nuevo_ancho = ancho_original + 2 * margen_pts
        nuevo_alto = alto_original + 2 * margen_pts

        nueva_pagina = nuevo_doc.new_page(width=nuevo_ancho, height=nuevo_alto)

        # Mostrar la página original centrada en la nueva con sangrado
        nueva_pagina.show_pdf_page(
            fitz.Rect(margen_pts, margen_pts, margen_pts + ancho_original, margen_pts + alto_original),
            doc,
            pagina.number
        )

    nuevo_doc.save(output_path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
