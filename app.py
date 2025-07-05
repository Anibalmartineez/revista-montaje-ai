from flask import Flask, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import openai
import os
from werkzeug.utils import secure_filename

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
    button[value="analisis_grafico"] {
  background-color: #004aad;
}

button[value="analisis_grafico"]:hover {
  background-color: #00367a;
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
    <form method="post" enctype="multipart/form-data" id="formulario">
      
      <!-- Campo PDF -->
      <div id="grupo-pdf">
        <input type="file" name="pdf" id="pdf" required>
      </div>

      <!-- Campos de redimensionar -->
      <div id="grupo-redimensionar" style="display: none;">
        <input type="number" step="0.1" name="nuevo_ancho" placeholder="Nuevo ancho en mm (para redimensionar)">
        <input type="number" step="0.1" name="nuevo_alto" placeholder="Nuevo alto en mm (opcional)">
      </div>

      <!-- Imagen para análisis gráfico -->
      <div id="grupo-grafico" style="margin-bottom: 15px;">
        <input type="file" name="grafico" id="grafico" accept="image/png, image/jpeg">
      </div>

      <!-- Selector modo montaje -->
      <div id="grupo-montaje">
        <select name="modo_montaje" id="modo_montaje" required style="padding: 12px; border-radius: 10px; border: 2px solid #ccc; font-size: 15px; width: 100%;">
          <option value="4" selected>🗞️ Montaje 4 páginas por cara (revista cosido a caballete)</option>
          <option value="2">📰 Montaje 2 páginas por cara (libro frente/dorso)</option>
        </select>
      </div>

      <!-- Botones de acción -->
      <button name='action' value='montar'>📄 Montar Revista</button>
      <button name='action' value='diagnostico'>🔍 Diagnóstico Técnico (IA)</button>
      <button name='action' value='corregir_sangrado'>✂️ Corregir Márgenes y Sangrado</button>
      <button name='action' value='redimensionar'>📐 Redimensionar PDF</button>
      <button name='action' value='analisis_grafico'>📈 Analizar Gráfico Técnico</button>
    </form>

    {% if mensaje %}
      <p class="mensaje">{{ mensaje }}</p>
    {% endif %}

    {% if output_pdf %}
      <a href="{{ url_for('descargar_pdf') }}" class="descargar-link">📥 Descargar PDF Procesado</a>
    {% endif %}

    {% if diagnostico %}
      <h3 class="diagnostico-titulo">📊 Diagnóstico IA:</h3>
      <pre>{{ diagnostico|safe }}</pre>
    {% endif %}
  </div>

  <!-- Script para mostrar/ocultar campos -->
<script>
  function setModo(accion) {
    const grupoPDF = document.getElementById("grupo-pdf");
    const grupoGrafico = document.getElementById("grupo-grafico");
    const grupoRedimensionar = document.getElementById("grupo-redimensionar");
    const grupoMontaje = document.getElementById("grupo-montaje");

    const inputPDF = document.getElementById("pdf");
    const inputGrafico = document.getElementById("grafico");

    // Reset visibilidad
    grupoPDF.style.display = "block";
    grupoGrafico.style.display = "none";
    grupoRedimensionar.style.display = "none";
    grupoMontaje.style.display = "block";

    // Reset campos requeridos
    if (inputPDF) inputPDF.required = true;
    if (inputGrafico) inputGrafico.required = false;

    // Mostrar u ocultar según la acción
    if (accion === "analisis_grafico") {
      grupoPDF.style.display = "none";
      grupoGrafico.style.display = "block";
      grupoMontaje.style.display = "none";
      if (inputGrafico) inputGrafico.required = true;
      if (inputPDF) inputPDF.required = false;
    }

    if (accion === "redimensionar") {
      grupoRedimensionar.style.display = "block";
    }

    if (accion === "corregir_sangrado" || accion === "diagnostico") {
      grupoMontaje.style.display = "none";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const formulario = document.getElementById("formulario");
    const botones = formulario.querySelectorAll("button[name='action']");

    botones.forEach(boton => {
      boton.addEventListener("click", function () {
        setModo(this.value);
      });
    });
  });
</script>


</body>
</html>
"""




@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = ""
    diagnostico = None
    output_pdf = False

    if request.method == "POST":
        try:
            action = request.form.get("action")
            modo_montaje = int(request.form.get("modo_montaje", 4) or 4)
            nuevo_ancho = request.form.get("nuevo_ancho")
            nuevo_alto = request.form.get("nuevo_alto")

            if action == "analisis_grafico":
                imagen = request.files.get("grafico")
                if imagen and imagen.filename != '':
                    path_img = os.path.join(UPLOAD_FOLDER, secure_filename(imagen.filename))
                    imagen.save(path_img)
                    resumen, img_base64 = analizar_grafico_tecnico(path_img)
                    diagnostico = f"{resumen}\n\n<img src='data:image/png;base64,{img_base64}' style='width:100%;margin-top:20px;border:2px solid #ccc;border-radius:12px;'>"
                else:
                    raise Exception("Debe subir una imagen válida para análisis técnico.")

            elif action in ["montar", "diagnostico", "corregir_sangrado", "redimensionar"]:
                if 'pdf' not in request.files or request.files['pdf'].filename == '':
                    raise Exception("Debes subir un archivo PDF válido.")

                archivo = request.files['pdf']
                filename = secure_filename(archivo.filename)
                path_pdf = os.path.join(UPLOAD_FOLDER, filename)
                archivo.save(path_pdf)

                output_path = os.path.join("output", "montado.pdf")

                if action == "montar":
                    montar_pdf(path_pdf, output_path, paginas_por_cara=modo_montaje)
                    output_pdf = True
                elif action == "diagnostico":
                    diagnostico = diagnosticar_pdf(path_pdf)
                elif action == "corregir_sangrado":
                    corregir_sangrado(path_pdf, output_path)
                    output_pdf = True
                elif action == "redimensionar":
                    if not nuevo_ancho:
                        raise Exception("Debes ingresar al menos un nuevo ancho.")
                    nuevo_ancho = float(nuevo_ancho)
                    nuevo_alto = float(nuevo_alto) if nuevo_alto else None
                    redimensionar_pdf(path_pdf, output_path, nuevo_ancho, nuevo_alto)
                    output_pdf = True
                else:
                    mensaje = "⚠️ Función no implementada para esta acción."

        except Exception as e:
            mensaje = f"❌ Error al procesar el archivo: {str(e)}"

    return render_template_string(HTML, mensaje=mensaje, diagnostico=diagnostico, output_pdf=output_pdf)




@app.route('/descargar')
def descargar_pdf():
    return send_file(output_pdf_path, as_attachment=True)

def montar_pdf(input_path, output_path, paginas_por_cara=4):
    import fitz
    from PIL import Image
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

    def insertar_pagina(nueva_pagina, idx, pos, paginas_por_cara):
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
            rotar = 180 if pos >= 2 else 0
        elif paginas_por_cara == 2:
            ancho_paisaje = A4_HEIGHT
            alto_paisaje = A4_WIDTH
            x = (pos % 2) * (ancho_paisaje / 2)
            y = 0
            rect = fitz.Rect(x, y, x + (ancho_paisaje / 2), alto_paisaje)
            rotar = 0
        else:
            rect = fitz.Rect(0, 0, A4_WIDTH, A4_HEIGHT)
            rotar = 0

        nueva_pagina.insert_image(rect, stream=buffer, rotate=rotar)
        buffer.close()

    for frente, dorso in hojas:
        if paginas_por_cara == 2:
            ancho = A4_HEIGHT  # horizontal
            alto = A4_WIDTH
        else:
            ancho = A4_WIDTH
            alto = A4_HEIGHT

        pag_frente = salida.new_page(width=ancho, height=alto)
        for j, idx in enumerate(frente):
            insertar_pagina(pag_frente, idx, j, paginas_por_cara)

        pag_dorso = salida.new_page(width=ancho, height=alto)
        for j, idx in enumerate(dorso):
            insertar_pagina(pag_dorso, idx, j, paginas_por_cara)

    salida.save(output_path)




def diagnosticar_pdf(path):
    import fitz
    import math

    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    crop = first_page.cropbox
    page_width = crop.width
    page_height = crop.height
    ancho_mm = round(page_width * 25.4 / 72, 2)
    alto_mm = round(page_height * 25.4 / 72, 2)

    contenido_dict = first_page.get_text("dict")
    drawings = first_page.get_drawings()
    objetos_visibles = []

    # -------------------------------
    # DETECCIÓN DE OBJETOS VISIBLES
    # -------------------------------
    def dentro_de_pagina(x0, y0, x1, y1):
        return (
            0 <= x0 <= page_width and
            0 <= y0 <= page_height and
            0 <= x1 <= page_width and
            0 <= y1 <= page_height
        )

    # Vectores visibles
    for d in drawings:
        for item in d["items"]:
            if len(item) == 4:
                x0, y0, x1, y1 = item
                if dentro_de_pagina(x0, y0, x1, y1):
                    min_x = min(x0, x1)
                    min_y = min(y0, y1)
                    max_x = max(x0, x1)
                    max_y = max(y0, y1)
                    if (max_x - min_x) > 10 and (max_y - min_y) > 10:
                        objetos_visibles.append((min_x, min_y, max_x, max_y))

    # Imágenes visibles
    for img in first_page.get_images(full=True):
        try:
            bbox = first_page.get_image_bbox(img)
            x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
            if dentro_de_pagina(x0, y0, x1, y1):
                objetos_visibles.append((x0, y0, x1, y1))
        except:
            continue

    # Bloques de texto o layout visibles
    for bloque in contenido_dict.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            if dentro_de_pagina(x0, y0, x1, y1):
                objetos_visibles.append((x0, y0, x1, y1))

    # -------------------------------
    # PROCESAR LOS OBJETOS VISIBLES
    # -------------------------------
    objetos_finales = []
    for obj in objetos_visibles:
        x0, y0, x1, y1 = obj
        w = round((x1 - x0) * 25.4 / 72, 2)
        h = round((y1 - y0) * 25.4 / 72, 2)
        if w > 10 and h > 10:  # solo objetos significativos
            objetos_finales.append((w, h))

    if not objetos_finales:
        medida_util = "No se detectaron objetos visuales significativos dentro de la página."
    else:
        # Agrupar por tamaño aproximado (redondeo a 5 mm)
        from collections import defaultdict
        grupos = defaultdict(int)
        for w, h in objetos_finales:
            clave = (round(w/5)*5, round(h/5)*5)
            grupos[clave] += 1

        detalle_objetos = []
        for (w_aprox, h_aprox), cantidad in grupos.items():
            detalle_objetos.append(f"{cantidad} objeto(s) de aprox. {w_aprox}×{h_aprox} mm")

        medida_util = "; ".join(detalle_objetos)

    resumen = f"""
A) Tamaño de página: {ancho_mm} × {alto_mm} mm
B) Objetos detectados visualmente: {medida_util}
C) Metadatos: {info}
"""

    prompt = f"""Sos un experto en preprensa. Analizá este diagnóstico técnico y explicalo para un operador gráfico. En especial, el punto B indica cuántos elementos hay realmente dentro de la página y qué medidas útiles tienen.\n\n{resumen}"""

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

def analizar_grafico_tecnico(image_path):
    import cv2
    import numpy as np
    import base64
    from io import BytesIO
    from PIL import Image

    image = cv2.imread(image_path)
    if image is None:
        raise Exception("No se pudo leer la imagen")
    
    resized = cv2.resize(image, (1000, 600))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=80, maxLineGap=10)

    resultado = resized.copy()
    datos_lineas = []

    if lines is not None:
        for line in lines[:20]:
            x1, y1, x2, y2 = line[0]
            cv2.line(resultado, (x1, y1), (x2, y2), (0, 0, 255), 2)
            datos_lineas.append((x1, y1, x2, y2))

    resultado_rgb = cv2.cvtColor(resultado, cv2.COLOR_BGR2RGB)
    im_pil = Image.fromarray(resultado_rgb)
    buffer = BytesIO()
    im_pil.save(buffer, format="PNG")
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    
    resumen = f"🔍 Se detectaron {len(datos_lineas)} líneas principales en el gráfico. Coordenadas aproximadas:\n"
    for i, (x1, y1, x2, y2) in enumerate(datos_lineas[:10], 1):
        resumen += f"{i}) Línea de ({x1}, {y1}) a ({x2}, {y2})\n"

    return resumen, imagen_base64


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
