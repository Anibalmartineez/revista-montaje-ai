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
    <h2> Diagnóstico & Montaje de Revista PDF</h2>
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
          <option value="4" selected> Montaje 4 páginas por cara (revista cosido a caballete)</option>
          <option value="2"> Montaje 2 páginas por cara (libro frente/dorso)</option>
        </select>
      </div>

      <!-- Botones de acción -->
      <button name='action' value='montar'> Montar Revista</button>
      <button name='action' value='diagnostico'> Diagnóstico Técnico (IA)</button>
      <button name='action' value='corregir_sangrado'> Corregir Márgenes y Sangrado</button>
      <button name='action' value='redimensionar'> Redimensionar PDF</button>
      <button name='action' value='analisis_grafico'> Analizar Gráfico Técnico</button>
    </form>

    {% if mensaje %}
      <p class="mensaje">{{ mensaje }}</p>
    {% endif %}

    {% if output_pdf %}
      <a href="{{ url_for('descargar_pdf') }}" class="descargar-link"> Descargar PDF Procesado</a>
    {% endif %}

    {% if diagnostico %}
      <h3 class="diagnostico-titulo"> Diagnóstico IA:</h3>
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
<script>
function validarFormulario() {
  const accion = document.activeElement.value;
  const archivoGrafico = document.getElementById("grafico");

  if (accion === "analisis_grafico" && (!archivoGrafico.files || archivoGrafico.files.length === 0)) {
    alert("Debes subir una imagen para análisis gráfico.");
    return false;
  }
  return true;
}
</script>



</body>
</html>
"""
HTML_HABLA_INGLES = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Habla en Inglés – IA Coach</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f2f9ff;
      padding: 30px;
    }
    .container {
      max-width: 700px;
      margin: auto;
      background: white;
      padding: 30px;
      border-radius: 14px;
      box-shadow: 0 0 20px rgba(0,0,0,0.1);
    }
    h1 {
      text-align: center;
      color: #0077cc;
    }
    input[type="file"], button {
      margin: 20px 0;
      padding: 12px;
      font-size: 16px;
    }
    .box {
      background: #eef4ff;
      padding: 15px;
      border-left: 4px solid #0077cc;
      margin-top: 20px;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>&#127908; Habla en Inglés con IA</h1>
    <p>Subí un archivo de voz en inglés (.mp3) o grabá directamente desde el navegador. Te diremos qué tan bien estás hablando y cómo mejorar.</p>

    <form method="post" enctype="multipart/form-data">
      <input type="file" name="audio" accept=".mp3">
      <br>
      <button type="submit">&#128228; Subir y Analizar</button>
    </form>

    <!-- Grabador de audio -->
    <div style="text-align:center; margin-top: 30px;">
      <button onclick="iniciarGrabacion()">&#127908; Iniciar Grabación</button>
      <button onclick="detenerGrabacion()">&#128721; Detener y Analizar</button>
      <p id="estado" style="color:#0077cc; margin-top:10px;"></p>
    </div>

    {% if mensaje %}
      <div class="box" style="color:red">{{ mensaje }}</div>
    {% endif %}

    {% if transcripcion %}
      <div class="box"><strong>&#128221; Transcripción IA:</strong><br>{{ transcripcion }}</div>
    {% endif %}

    {% if analisis %}
      <div class="box"><strong>&#129504; Análisis del Habla:</strong><br>{{ analisis }}</div>
    {% endif %}
  </div>

  <script>
    let mediaRecorder;
    let audioChunks = [];

    async function iniciarGrabacion() {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = event => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'grabacion.mp3');

        fetch('/habla-ingles', {
          method: 'POST',
          body: formData
        })
        .then(res => location.reload())
        .catch(err => alert('Error al subir el audio'));

        audioChunks = [];
      };

      mediaRecorder.start();
      document.getElementById('estado').innerText = ' Grabando...';
    }

    function detenerGrabacion() {
      mediaRecorder.stop();
      document.getElementById('estado').innerText = ' Procesando audio...';
    }
  </script>
</body>
</html>
"""
HTML_GRABACION_JS = """
<!-- HTML y JS para grabar audio en /habla-ingles -->
<script>
  let mediaRecorder;
  let audioChunks = [];

  async function iniciarGrabacion() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = event => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'grabacion.mp3');

      fetch('/habla-ingles', {
        method: 'POST',
        body: formData
      })
      .then(res => location.reload())
      .catch(err => alert('Error al subir el audio'));

      audioChunks = [];
    };

    mediaRecorder.start();
    document.getElementById('estado').innerText = ' Grabando...';
  }

  function detenerGrabacion() {
    mediaRecorder.stop();
    document.getElementById('estado').innerText = ' Procesando audio...';
  }
</script>
"""

HTML_HABLA_INGLES = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Habla en Inglés – IA Coach</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f2f9ff;
      padding: 30px;
    }
    .container {
      max-width: 700px;
      margin: auto;
      background: white;
      padding: 30px;
      border-radius: 14px;
      box-shadow: 0 0 20px rgba(0,0,0,0.1);
    }
    h1 {
      text-align: center;
      color: #0077cc;
    }
    input[type="file"], button {
      margin: 20px 0;
      padding: 12px;
      font-size: 16px;
    }
    .box {
      background: #eef4ff;
      padding: 15px;
      border-left: 4px solid #0077cc;
      margin-top: 20px;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>&#127908; Habla en Inglés con IA</h1>
    <p>Subí un archivo de voz en inglés (.mp3) o grabá directamente desde el navegador. Te diremos qué tan bien estás hablando y cómo mejorar.</p>

    <form method="post" enctype="multipart/form-data">
      <input type="file" name="audio" accept=".mp3">
      <br>
      <button type="submit">&#128228; Subir y Analizar</button>
    </form>

    <div style="text-align:center; margin-top: 30px;">
      <button onclick="iniciarGrabacion()">🎙️ Iniciar Grabación</button>
      <button onclick="detenerGrabacion()">🛑 Detener y Analizar</button>
      <p id="estado" style="color:#0077cc; margin-top:10px;"></p>
    </div>

    {% if mensaje %}
      <div class="box" style="color:red">{{ mensaje }}</div>
    {% endif %}

    {% if transcripcion %}
      <div class="box"><strong>📝 Transcripción IA:</strong><br>{{ transcripcion }}</div>
    {% endif %}

    {% if analisis %}
      <div class="box"><strong>🧠 Análisis del Habla:</strong><br>{{ analisis }}</div>
    {% endif %}
  </div>

  <script>
    let mediaRecorder;
    let audioChunks = [];

    async function iniciarGrabacion() {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = event => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'grabacion.mp3');

        fetch('/habla-ingles', {
          method: 'POST',
          body: formData
        })
        .then(res => location.reload())
        .catch(err => alert('Error al subir el audio'));

        audioChunks = [];
      };

      mediaRecorder.start();
      document.getElementById('estado').innerText = ' Grabando...';
    }

    function detenerGrabacion() {
      mediaRecorder.stop();
      document.getElementById('estado').innerText = ' Procesando audio...';
    }
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

                    #  Análisis gráfico técnico
                    estrategia, img_base64 = analizar_grafico_tecnico(path_img)

                    diagnostico = f"""
                    <h3 style='margin-top:20px;'> Gráfico Técnico Simulado</h3>
                    <img src='data:image/png;base64,{img_base64}' style='width:100%;margin:15px 0;border:2px solid #007bff;border-radius:12px;'>

                    <h3> Estrategia Sugerida (IA)</h3>
                    <div style='background:#eef6ff;border-left:5px solid #007bff;padding:15px;border-radius:10px;font-size:15px;white-space:pre-wrap;'>{estrategia}</div>
                    """
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
                    mensaje = "⚠ Función no implementada para esta acción."

        except Exception as e:
            mensaje = f" Error al procesar el archivo: {str(e)}"

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
    from collections import defaultdict

    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    crop = first_page.cropbox
    trim = first_page.trimbox
    bleed = first_page.bleedbox
    art = first_page.artbox

    def pts_to_mm(p): return round(p.width * 25.4 / 72, 2), round(p.height * 25.4 / 72, 2)

    crop_mm = pts_to_mm(crop)
    trim_mm = pts_to_mm(trim)
    bleed_mm = pts_to_mm(bleed)
    art_mm = pts_to_mm(art)

    contenido_dict = first_page.get_text("dict")
    drawings = first_page.get_drawings()
    objetos_visibles = []
    page_width, page_height = crop.width, crop.height

    def dentro_de_pagina(x0, y0, x1, y1):
        return 0 <= x0 <= page_width and 0 <= y0 <= page_height and 0 <= x1 <= page_width and 0 <= y1 <= page_height

    #  Vectores visibles
    for d in drawings:
        for item in d.get("items", []):
            if len(item) == 4:
                x0, y0, x1, y1 = item
                if dentro_de_pagina(x0, y0, x1, y1):
                    objetos_visibles.append((x0, y0, x1, y1))

    #  Imágenes visibles
    for img in first_page.get_images(full=True):
        try:
            bbox = first_page.get_image_bbox(img)
            if dentro_de_pagina(bbox.x0, bbox.y0, bbox.x1, bbox.y1):
                objetos_visibles.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
        except:
            continue

    #  Bloques de texto visibles
    for bloque in contenido_dict.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            if dentro_de_pagina(x0, y0, x1, y1):
                objetos_visibles.append((x0, y0, x1, y1))

    #  Calcular área útil visual
    objetos_finales = []
    for obj in objetos_visibles:
        x0, y0, x1, y1 = obj
        w = round((x1 - x0) * 25.4 / 72, 2)
        h = round((y1 - y0) * 25.4 / 72, 2)
        if w > 10 and h > 10:
            objetos_finales.append((w, h))

    if not objetos_finales:
        medida_util = "No se detectaron objetos visuales significativos."
    else:
        grupos = defaultdict(int)
        for w, h in objetos_finales:
            clave = (round(w / 5) * 5, round(h / 5) * 5)
            grupos[clave] += 1
        medida_util = "; ".join([f"{v} objeto(s) de aprox. {k[0]}×{k[1]} mm" for k, v in grupos.items()])

    #  DPI de la 1ra imagen
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
        dpi_info = f"{dpi_x} x {dpi_y} DPI"

    resumen = f"""
 Diagnóstico Técnico del PDF:

1️⃣ Tamaño de página (CropBox): {crop_mm[0]} × {crop_mm[1]} mm
2️⃣ Área de corte final (TrimBox): {trim_mm[0]} × {trim_mm[1]} mm
3️⃣ Zona de sangrado (BleedBox): {bleed_mm[0]} × {bleed_mm[1]} mm
4️⃣ Área artística (ArtBox): {art_mm[0]} × {art_mm[1]} mm
5️⃣ Resolución estimada: {dpi_info}
6️⃣ Elementos visuales encontrados: {medida_util}
7️⃣ Metadatos del archivo: {info}
"""

    prompt = f"""Sos un experto en preprensa profesional. Explicá este informe técnico como si fueras el jefe de control de calidad de una imprenta. Comentá si el área útil coincide con el tamaño final, si hay marcas de corte o troquel, si hay buen sangrado, y cualquier advertencia importante. Usá un lenguaje claro para operadores gráficos.

{resumen}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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

def analizar_grafico_tecnico(path_img):
    import cv2
    import numpy as np
    import base64
    import json  # ✅ NECESARIO para serializar el array
    from io import BytesIO
    from PIL import Image

    # Leer imagen
    image = cv2.imread(path_img)
    if image is None:
        raise Exception("No se pudo leer la imagen.")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detección de líneas
    lineas_detectadas = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    lineas = []

    if lineas_detectadas is not None:
        for linea in lineas_detectadas[:20]:  # Máximo 20 líneas
            x1, y1, x2, y2 = map(int, linea[0])  #  conversión a int nativo
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            lineas.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    # Convertir imagen a base64 para mostrar en HTML
    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    buffer = BytesIO()
    img_pil.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Análisis inteligente con OpenAI
    try:
        prompt = f"""
Eres un experto en análisis técnico bursátil. Se detectaron las siguientes líneas principales en un gráfico financiero (líneas de soporte, resistencia o tendencias). Basado en estas coordenadas (en formato de líneas con punto inicial y final):

{json.dumps(lineas, indent=2)}

Simula una breve interpretación como si fueras un analista técnico. Indica si se observa un canal, una tendencia, y si sería un buen momento para comprar, vender o esperar. Usa un tono profesional y claro.
"""

        respuesta = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        resumen = respuesta.choices[0].message.content.strip()

    except Exception as e:
        resumen = f"No se pudo generar el análisis técnico automático. Detalle: {str(e)}"

    return resumen, img_base64
  
@app.route("/simula-ingles", methods=["GET", "POST"])
def simula_ingles():
    respuesta_ia = ""
    texto_usuario = ""

    if request.method == "POST":
        texto_usuario = request.form.get("texto", "")
        contexto = request.form.get("contexto", "Conversación general")

        prompt = f"""
You are an English conversation partner for a Spanish-speaking learner. 
Simulate a realistic conversation in English under the context: "{contexto}".

User's message: "{texto_usuario}"

Please reply naturally in English. After your answer, explain briefly any errors or improvements in Spanish.
"""

        try:
            completado = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            respuesta_ia = completado.choices[0].message.content
        except Exception as e:
            respuesta_ia = f"[ERROR] No se pudo generar respuesta: {str(e)}"

    return render_template_string(HTML_SIMULA_INGLES, respuesta=respuesta_ia, texto_usuario=texto_usuario)

    
@app.route("/habla-ingles", methods=["GET", "POST"])
def habla_ingles():
    mensaje = ""
    transcripcion = ""
    analisis = ""

    if request.method == "POST":
        audio = request.files.get("audio")
        if audio and audio.filename.endswith(".mp3"):
            try:
                #  Transcripción con Whisper
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
                transcripcion = transcript.text

                #  Análisis del inglés con GPT-4o
                prompt = f"""
El siguiente texto fue hablado por un estudiante de inglés. Analiza su nivel de pronunciación y gramática (en base al texto transcrito), y sugiere cómo podría mejorar. Sé claro, breve y amable. También indica el nivel estimado (A1, B1, C1, etc).

Texto: "{transcripcion}"
"""

                respuesta = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}]
                )
                analisis = respuesta.choices[0].message.content

            except Exception as e:
                mensaje = f" Error al procesar audio: {str(e)}"
        else:
            mensaje = " Por favor, subí un archivo .mp3 válido."

    return render_template_string(HTML_HABLA_INGLES, mensaje=mensaje, transcripcion=transcripcion, analisis=analisis)








if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
