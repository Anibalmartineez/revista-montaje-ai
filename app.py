import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, request, send_file, render_template, render_template_string, redirect, url_for
import tempfile
from montaje_flexo import generar_montaje
from reportlab.lib.pagesizes import A4
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import openai
import os
from werkzeug.utils import secure_filename
from flask import url_for
from flask import send_from_directory
chat_historial = []


# Cliente OpenAI moderno
openai.api_key = os.environ["OPENAI_API_KEY"]



app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("preview_temp", exist_ok=True)
output_pdf_path = "output/montado.pdf"

# Carpetas específicas para flexografía
UPLOAD_FOLDER_FLEXO = "uploads_flexo"
OUTPUT_FOLDER_FLEXO = "output_flexo"

os.makedirs(UPLOAD_FOLDER_FLEXO, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_FLEXO, exist_ok=True)


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
<button name='action' value='montar'>Montar Revista</button>
<button name='action' value='diagnostico'>Diagnóstico Técnico (IA)</button>
<button name='action' value='corregir_sangrado'>Corregir Márgenes y Sangrado</button>
<button name='action' value='redimensionar'>Redimensionar PDF</button>
<button name='action' value='analisis_grafico'>Analizar Gráfico Técnico</button>
</form>

<!-- Botones de acceso externo -->
<a href="https://creativactp.com/habla-en-ingles-con-ia/" target="_blank">
  <button style="background-color: #1e90ff; color: white; padding: 12px 25px; margin-top: 15px; border: none; border-radius: 8px; font-size: 16px; width: 100%;">
    🎤 Hablar en Inglés con IA
  </button>
</a>

<a href="https://creativactp.com/simular-conversacion-en-ingles/" target="_blank">
  <button style="background-color: #00b894; color: white; padding: 12px 25px; margin-top: 10px; border: none; border-radius: 8px; font-size: 16px; width: 100%;">
    🗣️ Simular Conversación en Inglés
  </button>
</a>


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
HTML_SIMULA_INGLES = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>🗣️ Simulador de Conversación en Inglés</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {
      background: #f0f4ff;
      font-family: 'Poppins', sans-serif;
      margin: 0;
      padding: 0;
    }
    .chat-container {
      max-width: 700px;
      margin: 50px auto;
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 0 20px rgba(0,0,0,0.1);
      padding: 30px;
    }
    h1 {
      text-align: center;
      font-size: 26px;
      margin-bottom: 20px;
    }
    .modo-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: center;
      margin-bottom: 20px;
    }
    .modo-buttons button {
      padding: 10px 16px;
      font-size: 14px;
      border: none;
      border-radius: 20px;
      cursor: pointer;
      background: #805dff;
      color: white;
      transition: transform 0.2s;
    }
    .modo-buttons button:hover {
      transform: scale(1.05);
      background: #6949d1;
    }
    form {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 20px;
    }
    textarea {
      padding: 12px;
      font-size: 15px;
      border-radius: 8px;
      border: 1px solid #ccc;
      resize: none;
    }
    button.enviar {
      background: #007bff;
      color: white;
      font-weight: bold;
      border: none;
      border-radius: 8px;
      padding: 10px;
      cursor: pointer;
      transition: 0.3s;
    }
    button.enviar:hover {
      background: #0056b3;
    }
    button.reset {
      background: #dc3545;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
      font-size: 13px;
    }
    #respuesta, #chat-history {
      margin-top: 25px;
    }
    .bubble {
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 10px;
      max-width: 80%;
      animation: fadeIn 0.3s ease-in-out;
    }
    .user-msg {
      background: #dbeafe;
      align-self: flex-end;
    }
    .ia-msg {
      background: #e7fce4;
      align-self: flex-start;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>
  <div class="chat-container">
    <h1>🧠 Simulador de Conversación en Inglés</h1>
    
    <div class="modo-buttons">
      <button type="button" onclick="setModo('turismo')">🧳 Turismo</button>
      <button type="button" onclick="setModo('negocios')">💼 Negocios</button>
      <button type="button" onclick="setModo('entrevista')">📋 Entrevista</button>
      <button type="button" onclick="setModo('educacion')">📚 Educación</button>
      <button type="button" onclick="setModo('vocabulario')">🧠 Vocabulario</button>
      <button type="button" onclick="setModo('quiz')">🎯 Mini Quiz</button>
    </div>

    <form method="POST" onsubmit="scrollToBottom()">
  <input type="hidden" name="modo" id="modo" value="{{ contexto }}">
  <textarea name="texto" rows="3" placeholder="Escribí algo en inglés o español..." required>{{ texto_usuario }}</textarea>
  <button type="submit" class="enviar">💬 Enviar</button>
</form>

<form method="GET" action="/reset-chat" style="margin-top: 10px;">
  <button class="reset-btn" type="submit">🗑️ Reset</button>
</form>


    <div id="chat-history">
      {{ historial|safe }}
    </div>

    <div id="respuesta">
      {{ respuesta|safe }}
    </div>
  </div>

  <script>
    function setModo(m) {
      document.getElementById('modo').value = m;
    }

    function resetChat() {
      document.querySelector('textarea').value = "";
      document.getElementById('chat-history').innerHTML = "";
      document.getElementById('respuesta').innerHTML = "";
    }

    function scrollToBottom() {
      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: 'smooth'
        });
      }, 100);
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
                    if modo_montaje == 2:
                        # Mostrar vista previa interactiva antes de montar
                        generar_preview_interactivo(path_pdf)
                        return send_from_directory("preview_temp", "preview.html")
                    else:
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
            frente = [paginas[-1], paginas[0]]   # izquierda: última, derecha: primera
            dorso = [paginas[1], paginas[-2]]   # izquierda: segunda, derecha: penúltima
            hojas.append((frente, dorso))
            paginas = paginas[2:-2]
        else:
            frente = paginas[:paginas_por_cara]
            dorso = paginas[paginas_por_cara:paginas_por_cara*2]
            hojas.append((frente, dorso))
            paginas = paginas[paginas_por_cara*2:]

    def insertar_pagina(nueva_pagina, idx, pos, paginas_por_cara, rotar=0):
        if not idx or idx < 1 or idx > len(doc):
            return
        pagina = doc[idx - 1]
        pix = pagina.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if rotar != 0:
            img = img.rotate(rotar, expand=True)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        if paginas_por_cara == 4:
            x = (pos % 2) * (A4_WIDTH / 2)
            y = (pos // 2) * (A4_HEIGHT / 2)
            rect = fitz.Rect(x, y, x + A4_WIDTH / 2, y + A4_HEIGHT / 2)
        elif paginas_por_cara == 2:
            ancho_paisaje = A4_HEIGHT
            alto_paisaje = A4_WIDTH
            x = (pos % 2) * (ancho_paisaje / 2)
            y = 0
            rect = fitz.Rect(x, y, x + (ancho_paisaje / 2), alto_paisaje)
        else:
            rect = fitz.Rect(0, 0, A4_WIDTH, A4_HEIGHT)

        nueva_pagina.insert_image(rect, stream=buffer)
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
            insertar_pagina(pag_frente, idx, j, paginas_por_cara, rotar=0)

        pag_dorso = salida.new_page(width=ancho, height=alto)
        for j, idx in enumerate(dorso):
            rotacion = 180 if paginas_por_cara == 2 else 0
            insertar_pagina(pag_dorso, idx, j, paginas_por_cara, rotar=rotacion)

    salida.save(output_path)








def diagnosticar_pdf(path):
    import fitz
    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    # Usamos MediaBox como referencia base (más confiable)
    media = first_page.rect
    crop = first_page.cropbox or media
    trim = first_page.trimbox or crop
    bleed = first_page.bleedbox or crop
    art = first_page.artbox or crop

    def pts_to_mm(p): return round(p.width * 25.4 / 72, 2), round(p.height * 25.4 / 72, 2)

    media_mm = pts_to_mm(media)
    crop_mm = pts_to_mm(crop)
    trim_mm = pts_to_mm(trim)
    bleed_mm = pts_to_mm(bleed)
    art_mm = pts_to_mm(art)

    contenido_dict = first_page.get_text("dict")
    drawings = first_page.get_drawings()
    objetos_visibles = []
    page_width, page_height = media.width, media.height

    def dentro_de_media(x0, y0, x1, y1):
        return 0 <= x0 <= page_width and 0 <= y0 <= page_height and 0 <= x1 <= page_width and 0 <= y1 <= page_height

    # Vectores visibles y marcas de corte
    for d in drawings:
        for item in d.get("items", []):
            if len(item) == 4:
                x0, y0, x1, y1 = item
                if dentro_de_media(x0, y0, x1, y1):
                    objetos_visibles.append((x0, y0, x1, y1))

    # Imágenes visibles
    for img in first_page.get_images(full=True):
        try:
            bbox = first_page.get_image_bbox(img)
            if dentro_de_media(bbox.x0, bbox.y0, bbox.x1, bbox.y1):
                objetos_visibles.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
        except:
            continue

    # Bloques de texto visibles
    for bloque in contenido_dict.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            if dentro_de_media(x0, y0, x1, y1):
                objetos_visibles.append((x0, y0, x1, y1))

    # Calcular bbox total en mm
    if not objetos_visibles:
        medida_util = "No se detectaron objetos visuales significativos."
    else:
        x_min = min([x0 for x0, _, _, _ in objetos_visibles])
        y_min = min([y0 for _, y0, _, _ in objetos_visibles])
        x_max = max([x1 for _, _, x1, _ in objetos_visibles])
        y_max = max([y1 for _, _, _, y1 in objetos_visibles])

        ancho_mm = round((x_max - x_min) * 25.4 / 72, 2)
        alto_mm = round((y_max - y_min) * 25.4 / 72, 2)

        medida_util = f"{ancho_mm} x {alto_mm} mm (área útil detectada visualmente)"

    # DPI de la primera imagen (si existe)
    dpi_info = "No se detectaron imágenes rasterizadas."
    image_list = first_page.get_images(full=True)
    if image_list:
        xref = image_list[0][0]
        base_image = doc.extract_image(xref)
        img_width = base_image["width"]
        img_height = base_image["height"]
        width_inch = media.width / 72
        height_inch = media.height / 72
        dpi_x = round(img_width / width_inch, 1)
        dpi_y = round(img_height / height_inch, 1)
        dpi_info = f"{dpi_x} x {dpi_y} DPI"

    resumen = f"""
 Diagnóstico Técnico del PDF:

📄 Tamaño real de página (MediaBox): {media_mm[0]} × {media_mm[1]} mm
1️⃣ Tamaño visible (CropBox): {crop_mm[0]} × {crop_mm[1]} mm
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
        response = openai.ChatCompletion.create(
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




# Historial de conversación en memoria
chat_historial = []

@app.route("/simula-ingles", methods=["GET", "POST"])
def simula_ingles():
    global chat_historial
    texto_usuario = ""
    respuesta_ia = ""
    modo = "general"

    if request.method == "POST":
        texto_usuario = request.form.get("texto", "").strip()
        modo = request.form.get("modo", "general")

        if modo == "quiz":
            # Mini quiz aleatorio en inglés
            prompt = f"""
Act as an English quiz coach. Based on the user's last message: "{texto_usuario}", create a 1-question multiple-choice quiz in English.
Include:
- The question
- 3 answer choices (A, B, C)
- Indicate the correct one
- Explain why it's correct in Spanish
"""
        else:
            contexto = {
                "general": "Conversación general",
                "turismo": "Viaje y turismo en el extranjero",
                "negocios": "Negociación y negocios",
                "entrevista": "Entrevista de trabajo",
                "educacion": "Presentación o entorno educativo",
                "vocabulario": "Práctica de nuevo vocabulario"
            }.get(modo, "Conversación general")

            prompt = f"""
Act as a friendly English tutor for a Spanish-speaking student. Simulate a conversation in the context: "{contexto}".

The student says: "{texto_usuario}"

Your response should follow this format:
**Respuesta en inglés:**
...

**Traducción al español:**
...

**Correcciones:**
...

End with a natural question or comment to keep the conversation going.
"""

        try:
            completado = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            respuesta_ia = completado.choices[0].message.content.strip()

            # Guardar en historial
            if texto_usuario:
                chat_historial.append(("🧑", texto_usuario))
            if respuesta_ia:
                chat_historial.append(("🤖", respuesta_ia))

            # Limitar historial a los últimos 10 mensajes
            chat_historial = chat_historial[-10:]

        except Exception as e:
            respuesta_ia = f"[ERROR] No se pudo generar respuesta: {str(e)}"

    # Convertir historial a HTML
    historial_html = ""
    for quien, mensaje in chat_historial:
        clase = "user-msg" if quien == "🧑" else "ia-msg"
        historial_html += f"<div class='bubble {clase}'>{quien} {mensaje}</div>"

    return render_template_string(HTML_SIMULA_INGLES,
                                  texto_usuario=texto_usuario,
                                  respuesta=respuesta_ia,
                                  contexto=modo,
                                  historial=historial_html)



@app.route("/reset-chat")
def reset_chat():
    try:
        global chat_historial
        chat_historial = []
        return redirect(url_for('simula_ingles'))
    except Exception as e:
        return f"Error al resetear el chat: {e}", 500




def generar_preview_interactivo(input_path, output_folder="preview_temp"):
    import os
    import fitz
    from PIL import Image

    os.makedirs(output_folder, exist_ok=True)
    doc = fitz.open(input_path)
    total_paginas = len(doc)
    while total_paginas % 4 != 0:
        doc.insert_page(-1)
        total_paginas += 1

    paginas = list(range(1, total_paginas + 1))
    hojas = []
    while len(paginas) >= 4:
        frente = [paginas[0], paginas[-1]]
        dorso = [paginas[1], paginas[-2]]
        hojas.append((frente, dorso))
        paginas = paginas[2:-2]

    imagenes = {}
    for i in range(1, total_paginas + 1):
        page = doc[i - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        img_path = os.path.join(output_folder, f"pag_{i}.jpg")
        pix.save(img_path)
        imagenes[i] = img_path

    # Crear archivo HTML
    vista = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Vista previa del montaje</title>
  <style>
    body {{
      font-family: 'Poppins', sans-serif;
      background: #f4f4f4;
      text-align: center;
      margin: 0;
      padding: 40px;
    }}
    h1 {{
      color: #333;
      margin-bottom: 20px;
    }}
    .hoja {{
      display: flex;
      justify-content: center;
      gap: 30px;
      margin: 30px auto;
    }}
    .pagina {{
      background: #fff;
      box-shadow: 0 0 15px rgba(0,0,0,0.2);
      padding: 10px;
      border-radius: 12px;
      transition: transform 0.3s;
    }}
    .pagina:hover {{
      transform: scale(1.05);
    }}
    .pagina img {{
      width: 300px;
      border-radius: 8px;
    }}
    button {{
      margin: 8px;
      padding: 12px 24px;
      font-size: 16px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      background-color: #007bff;
      color: white;
      transition: 0.3s;
    }}
    button:hover {{
      background-color: #0056b3;
    }}
    #dorso {{ display: none; }}
  </style>
</head>
<body>
  <h1>📰 Vista previa del Pliego <span id="nro">1</span></h1>

  <div id="frente" class="hoja"></div>
  <div id="dorso" class="hoja"></div>

  <div>
    <button onclick="mostrarDorso()">Ver dorso</button>
    <button onclick="anterior()">Anterior</button>
    <button onclick="siguiente()">Siguiente</button>
  </div>

  <form action="/generar_pdf_final" method="post" style="margin-top: 30px;">
    <input type="hidden" name="modo_montaje" value="2">
    <button type="submit">🖨️ Montar PDF final</button>
  </form>

  <script>
    const hojas = {str([[[f"/preview_temp/pag_{i}.jpg" for i in frente], [f"/preview_temp/pag_{i}.jpg" for i in dorso]] for frente, dorso in hojas])};
    let indice = 0;

    function cargar() {{
      document.getElementById("nro").innerText = indice + 1;
      const frente = document.getElementById("frente");
      const dorso = document.getElementById("dorso");
      frente.innerHTML = "";
      dorso.innerHTML = "";

      hojas[indice][0].forEach(p => {{
        frente.innerHTML += `<div class='pagina'><img src='${{p}}'><br>${{p}}</div>`;
      }});

      hojas[indice][1].forEach(p => {{
        dorso.innerHTML += `<div class='pagina'><img src='${{p}}'><br>${{p}}</div>`;
      }});

      frente.style.display = "flex";
      dorso.style.display = "none";
    }}

    function mostrarDorso() {{
      const frente = document.getElementById("frente");
      const dorso = document.getElementById("dorso");
      if (frente.style.display === "flex") {{
        frente.style.display = "none";
        dorso.style.display = "flex";
      }} else {{
        dorso.style.display = "none";
        frente.style.display = "flex";
      }}
    }}

    function siguiente() {{
      if (indice < hojas.length - 1) {{
        indice++;
        cargar();
      }}
    }}

    function anterior() {{
      if (indice > 0) {{
        indice--;
        cargar();
      }}
    }}

    cargar();
  </script>
</body>
</html>
"""




    with open(os.path.join(output_folder, "preview.html"), "w", encoding="utf-8") as f:
        f.write(vista)

@app.route("/vista_previa", methods=["POST"])
def vista_previa():
    archivo = request.files["archivo"]
    modo = int(request.form.get("modo", "2"))
    filename = secure_filename(archivo.filename)
    ruta_pdf = os.path.join("uploads", filename)
    archivo.save(ruta_pdf)

    if modo == 2:
        generar_preview_interactivo(ruta_pdf)
        return send_from_directory("preview_temp", "preview.html")
    else:
        montar_pdf(ruta_pdf, "output/montado.pdf", paginas_por_cara=modo)
        return send_file("output/montado.pdf", as_attachment=True)
from pdf2image import convert_from_path
import base64

def generar_preview_virtual(ruta_pdf):
    from pathlib import Path
    output_dir = "preview_temp"
    os.makedirs(output_dir, exist_ok=True)

    # Limpiar la carpeta anterior
    for archivo in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, archivo))

    # Convertir páginas del PDF a imágenes
    paginas = convert_from_path(ruta_pdf, dpi=150)
    for i, pagina in enumerate(paginas):
        nombre = f"pag_{i+1}.jpg"
        pagina.save(os.path.join(output_dir, nombre), "JPEG")
@app.route('/preview_temp/<filename>')
def mostrar_preview_temp(filename):
    return send_from_directory('preview_temp', filename)
@app.route("/preview")
def vista_preview():
    pagina = int(request.args.get("p", 1))
    modo = int(request.args.get("modo", 2))

    files = sorted(os.listdir("preview_temp"))
    total = len(files)
    total_paginas = total

    pag1 = files[pagina - 1] if pagina - 1 < total else None
    pag2 = files[pagina] if pagina < total else None

    anterior = pagina - 2 if pagina > 2 else 1
    siguiente = pagina + 2 if pagina + 1 < total else pagina

    html = f"""
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Vista previa del Pliego</title>
        <style>
            body {{
                font-family: sans-serif;
                text-align: center;
                padding: 20px;
            }}
            img {{
                height: 480px;
                margin: 0 10px;
                border: 2px solid #ccc;
                border-radius: 10px;
            }}
            .nav-buttons {{
                margin-top: 20px;
            }}
            button {{
                padding: 10px 20px;
                font-size: 16px;
                margin: 0 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Vista previa del Pliego {pagina // 2 + 1}</h1>
        <div>
            {f'<img src="/preview_temp/{pag1}">' if pag1 else ''}
            {f'<img src="/preview_temp/{pag2}">' if pag2 else ''}
        </div>
        <div class="nav-buttons">
            <a href="/preview?p={anterior}&modo={modo}"><button>Anterior</button></a>
            <a href="/preview?p={siguiente}&modo={modo}"><button>Siguiente</button></a>
        </div>
        <form action="/generar_pdf_final" method="post">
            <input type="hidden" name="modo_montaje" value="{modo}">
            <button type="submit">Montar PDF final</button>
        </form>
    </body>
    </html>
    """
    return html

@app.route("/generar_pdf_final", methods=["POST"])
def generar_pdf_final():
    modo = int(request.form.get("modo_montaje", 2))
    pdfs = [f for f in os.listdir("uploads") if f.endswith(".pdf")]
    if not pdfs:
        return "No hay archivo para montar."
    path_pdf = os.path.join("uploads", pdfs[-1])
    output_pdf_path = "output/montado.pdf"
    montar_pdf(path_pdf, output_pdf_path, paginas_por_cara=modo)
    return send_file(output_pdf_path, as_attachment=True)

from werkzeug.utils import secure_filename

@app.route('/montaje-flexo', methods=['GET', 'POST'])
def montaje_flexo_view():
    mensaje = ""
    if request.method == 'POST':
        archivo_pdf = request.files.get('archivo')
        if not archivo_pdf or archivo_pdf.filename == '':
            mensaje = "⚠️ No se cargó ningún archivo PDF válido."
            return render_template('montaje_flexo.html', mensaje=mensaje), 400

        try:
            # Guardar el archivo PDF con nombre seguro
            filename = secure_filename(archivo_pdf.filename)
            ruta_pdf = os.path.join(UPLOAD_FOLDER_FLEXO, filename)
            archivo_pdf.save(ruta_pdf)

            # Obtener y validar parámetros
            ancho = int(request.form['ancho'])
            alto = int(request.form['alto'])
            separacion = int(request.form['separacion'])
            bobina = int(request.form['bobina'])
            cantidad = int(request.form['cantidad'])

            if ancho <= 0 or alto <= 0 or bobina <= 0 or cantidad <= 0:
                raise ValueError("Los valores ingresados deben ser mayores a cero.")

            # Generar montaje
            archivo_final = generar_montaje(
                ruta_pdf, ancho, alto, separacion, bobina, cantidad
            )

            return send_file(archivo_final, as_attachment=True)

        except Exception as e:
            mensaje = f"❌ Error al procesar el montaje: {str(e)}"
            return render_template('montaje_flexo.html', mensaje=mensaje), 500

    return render_template('montaje_flexo.html', mensaje=mensaje)




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
