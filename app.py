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
    import fitz
    from io import BytesIO
    from PIL import Image
    from reportlab.lib.pagesizes import A4

    def generar_compaginacion(total_paginas):
        """
        Genera la compaginación para cosido a caballete en pliegos de 8 páginas (4 por cara A4).
        """
        paginas = list(range(1, total_paginas + 1))

        # Agrega páginas en blanco para completar múltiplos de 4
        while len(paginas) % 4 != 0:
            paginas.append(0)

        montajes = []
        for i in range(0, len(paginas), 16):  # 16 páginas = 2 caras (frente/dorso)
            seccion = paginas[i:i+16]
            if len(seccion) == 16:
                frente = [
                    [seccion[0], seccion[15], seccion[2], seccion[13]],
                    [seccion[4], seccion[11], seccion[6], seccion[9]]
                ]
                dorso = [
                    [seccion[1], seccion[14], seccion[3], seccion[12]],
                    [seccion[5], seccion[10], seccion[7], seccion[8]]
                ]
                montajes.extend(frente + dorso)
            else:
                # Si quedan menos de 16, crear grupos de 4
                while len(seccion) < 4:
                    seccion.append(0)
                montajes.append(seccion[:4])
        return montajes

    doc = fitz.open(input_path)
    total_paginas = len(doc)

    compaginacion = generar_compaginacion(total_paginas)
    pdf_salida = fitz.open()

    for grupo in compaginacion:
        nueva_pagina = pdf_salida.new_page(width=A4[0], height=A4[1])
        for j, idx in enumerate(grupo):
            if idx == 0:
                continue  # Página en blanco
            pagina = doc[idx - 1]
            pix = pagina.get_pixmap(matrix=fitz.Matrix(1, 1))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            x = (j % 2) * (A4[0] / 2)
            y = (j // 2) * (A4[1] / 2)
            rect = fitz.Rect(x, y, x + A4[0] / 2, y + A4[1] / 2)

            # Cabeza con cabeza: girar las páginas superiores
            if j in [0, 1]:
                nueva_pagina.insert_image(rect, stream=buffer, rotate=180)
            else:
                nueva_pagina.insert_image(rect, stream=buffer)

    pdf_salida.save(output_path)



def diagnosticar_pdf(path):
    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    crop = first_page.cropbox
    ancho_mm = round(crop.width * 25.4 / 72, 2)
    alto_mm = round(crop.height * 25.4 / 72, 2)

    trim = first_page.trimbox
    trim_ancho_mm = round(trim.width * 25.4 / 72, 2)
    trim_alto_mm = round(trim.height * 25.4 / 72, 2)

    art = first_page.artbox
    art_ancho_mm = round(art.width * 25.4 / 72, 2)
    art_alto_mm = round(art.height * 25.4 / 72, 2)

    try:
        resolution = first_page.get_text("dict")["width"]
    except:
        resolution = "No se pudo detectar"

    dpi_info = "No se detectaron imágenes rasterizadas en la primera página."
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
        dpi_info = f"{dpi_x} x {dpi_y} DPI (basado en la 1.ª imagen y cropbox)"

    resumen = f"""
1. Tamaño de página (desde CropBox): {ancho_mm} × {alto_mm} mm
2. Área de corte final (TrimBox): {trim_ancho_mm} × {trim_alto_mm} mm
3. Área artística o troquel (ArtBox): {art_ancho_mm} × {art_alto_mm} mm
4. Resolución estimada (texto): {resolution}
5. Resolución efectiva (imagen): {dpi_info}
6. Cantidad de páginas: {len(doc)}
7. Metadatos del documento: {info}
"""

    prompt = f"""Sos un experto en preprensa. Explicá de forma clara y profesional el siguiente diagnóstico técnico para que un operador gráfico lo entienda fácilmente. Usá un lenguaje humano claro, con consejos si detectás problemas:\n\n{resumen}"""

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
