
from flask import Flask, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
output_pdf_path = "output/montado.pdf"

HTML = """
<!doctype html>
<title>Montaje y Diagnóstico de PDF</title>
<h2>Subí tu PDF</h2>
<form method=post enctype=multipart/form-data>
  <input type=file name=pdf required>
  <button name='action' value='montar'>Montar Revista (4 páginas por cara)</button>
  <button name='action' value='diagnostico'>Diagnóstico Técnico (IA)</button>
</form>
{% if mensaje %}<p style="color:red;">{{ mensaje }}</p>{% endif %}
{% if output_pdf %}<p><a href="{{ url_for('descargar_pdf') }}">📥 Descargar PDF Montado</a></p>{% endif %}
{% if diagnostico %}<h3>Diagnóstico IA:</h3><pre>{{ diagnostico }}</pre>{% endif %}
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

    return render_template_string(HTML, mensaje=mensaje, output_pdf=output_pdf, diagnostico=diagnostico)

@app.route('/descargar')
def descargar_pdf():
    return send_file(output_pdf_path, as_attachment=True)

def montar_pdf(input_path, output_path):
    reader = fitz.open(input_path)
    total_pages = len(reader)
    if total_pages % 4 != 0:
        raise ValueError("El PDF debe tener un número de páginas múltiplo de 4.")
    writer = fitz.open()

    for i in range(0, total_pages, 4):
        new_page = writer.new_page(width=A4[0], height=A4[1])
        for j in range(4):
            page = reader[i + j].get_pixmap()
            img = Image.frombytes("RGB", [page.width, page.height], page.samples)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            rect = fitz.Rect((j % 2) * (A4[0] / 2), (j // 2) * (A4[1] / 2), ((j % 2) + 1) * (A4[0] / 2), ((j // 2) + 1) * (A4[1] / 2))
            new_page.insert_image(rect, stream=buffer)

    writer.save(output_path)

def diagnosticar_pdf(path):
    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata
    size = first_page.rect
    resolution = first_page.get_text("dict")["width"]
    diag = f"""
### Diagnóstico técnico

1. Tamaño de página y área útil: {size}
2. Resolución estimada: {resolution} px de ancho
3. Cantidad de páginas: {len(doc)}
4. Metadatos del documento: {info}
"""
    return diag

if __name__ == '__main__':
    app.run(debug=True)
