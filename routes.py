import os
import base64
import math
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from flask import (
    Blueprint,
    request,
    send_file,
    render_template,
    render_template_string,
    redirect,
    url_for,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from montaje import montar_pdf
from diagnostico import diagnosticar_pdf, analizar_grafico_tecnico
from utils import corregir_sangrado, redimensionar_pdf
from simulacion import generar_preview_interactivo, generar_preview_virtual
from ia_sugerencias import chat_completion, transcribir_audio
from montaje_flexo import (
    revisar_diseño_flexo,
    generar_sugerencia_produccion,
    corregir_sangrado_y_marcas,
)
from montaje_offset import montar_pliego_offset

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("preview_temp", exist_ok=True)
UPLOAD_FOLDER_FLEXO = "uploads_flexo"
OUTPUT_FOLDER_FLEXO = "output_flexo"
os.makedirs(UPLOAD_FOLDER_FLEXO, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_FLEXO, exist_ok=True)

chat_historial = []


routes_bp = Blueprint("routes", __name__)


@routes_bp.route("/", methods=["GET", "POST"])
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

    return render_template("index.html", mensaje=mensaje, diagnostico=diagnostico, output_pdf=output_pdf)


@routes_bp.route('/descargar')
def descargar_pdf():
    return send_file("output/montado.pdf", as_attachment=True)


@routes_bp.route("/montaje_offset", methods=["GET", "POST"])
def montaje_offset_view():
    if request.method == "GET":
        return render_template("montaje_offset.html")
    if request.method == "POST":
        archivos = request.files.getlist("pdfs")
        if not archivos:
            return "No se cargaron PDFs", 400
        formato = request.form.get("formato_pliego", "700x1000")
        try:
            ancho = float(request.form.get("ancho_trabajo", 0))
            alto = float(request.form.get("alto_trabajo", 0))
        except ValueError:
            return "Dimensiones inválidas", 400
        modo_dorso = request.form.get("modo_dorso")  # 'tirada' | 'retiracion'
        margen_sup = float(request.form.get("margen_superior", 10))
        margen_inf = float(request.form.get("margen_inferior", 10))
        margen_izq = float(request.form.get("margen_izquierdo", 10))
        margen_der = float(request.form.get("margen_derecho", 10))
        espaciado_h = float(request.form.get("espaciado_h", 5))
        espaciado_v = float(request.form.get("espaciado_v", 5))
        sangrado = float(request.form.get("sangrado", 0))
        file_paths = []
        for f in archivos:
            filename = secure_filename(f.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(path)
            file_paths.append(path)
        pdf_path, preview_path, reporte_path = montar_pliego_offset(
            file_paths,
            formato,
            (ancho, alto),
            modo_dorso=modo_dorso,
            margen_sup=margen_sup,
            margen_inf=margen_inf,
            margen_izq=margen_izq,
            margen_der=margen_der,
            espaciado_h=espaciado_h,
            espaciado_v=espaciado_v,
            sangrado=sangrado,
        )
        with open(preview_path, "rb") as img_f:
            preview_b64 = base64.b64encode(img_f.read()).decode("utf-8")
        return render_template_string(
            """
            <h2>Pliego generado</h2>
            <a href='/descargar_pliego_offset'>Descargar PDF</a> |
            <a href='/descargar_reporte_offset'>Reporte técnico</a>
            <div style='margin-top:20px;'>
                <img src='data:image/png;base64,{{preview}}' style='width:100%;max-width:800px;border:1px solid #ccc;'>
            </div>
            """,
            preview=preview_b64,
        )
    return "Método no permitido", 405


@routes_bp.route('/descargar_pliego_offset')
def descargar_pliego_offset():
    return send_file('output/pliego_offset.pdf', as_attachment=True)


@routes_bp.route('/descargar_reporte_offset')
def descargar_reporte_offset():
    return send_file('output/reporte_tecnico.html', as_attachment=True)


@routes_bp.route("/montaje_flexo_avanzado", methods=["GET", "POST"])
def montaje_flexo_avanzado():
    if request.method == "GET":
        return render_template("montaje_flexo_avanzado.html")

    archivo = request.files.get("pdf")
    if not archivo or archivo.filename == "":
        return "Debe subir un PDF", 400
    filename = secure_filename(archivo.filename)
    path_pdf = os.path.join(UPLOAD_FOLDER_FLEXO, filename)
    archivo.save(path_pdf)

    auto_sangrado = request.form.get("auto_sangrado") == "on"
    auto_marcas = request.form.get("auto_marcas") == "on"
    correccion_aplicada = False
    if auto_sangrado or auto_marcas:
        nuevo_pdf = corregir_sangrado_y_marcas(path_pdf)
        if nuevo_pdf != path_pdf:
            path_pdf = nuevo_pdf
            correccion_aplicada = True

    try:
        ancho = float(request.form.get("ancho_etiqueta", 0))
        alto = float(request.form.get("alto_etiqueta", 0))
        ancho_bobina = float(request.form.get("ancho_bobina", 0))
        paso = float(request.form.get("paso", 0))
        sep_h = float(request.form.get("sep_h", 0))
        sep_v = float(request.form.get("sep_v", 0))
        # La alineación se determinará automáticamente más adelante
        cantidad = int(request.form.get("cantidad", 0))
        margen = float(request.form.get("margen_lateral", 0))
    except ValueError:
        return "Dimensiones inválidas", 400

    espacio_disponible = ancho_bobina - 2 * margen
    if espacio_disponible <= 0:
        return "Las dimensiones no permiten ninguna etiqueta", 400

    pistas = int((espacio_disponible + sep_h) / (ancho + sep_h))
    pistas = max(1, pistas)

    espacio_utilizado = (pistas * ancho) + ((pistas - 1) * sep_h)

    espacio_sobrante = espacio_disponible - espacio_utilizado
    if espacio_sobrante < 10:
        alignment = "center"
    else:
        alignment = "left"

    if alignment == "left":
        offset_x = margen
    elif alignment == "center":
        offset_x = (ancho_bobina - espacio_utilizado) / 2
    else:
        offset_x = margen  # fallback

    x_positions = []
    for i in range(pistas):
        x_positions.append(offset_x + i * (ancho + sep_h))

    filas = max(1, math.floor((paso + sep_v) / (alto + sep_v)))
    etiquetas_por_repeticion = pistas * filas
    if etiquetas_por_repeticion <= 0:
        return "Las dimensiones no permiten ninguna etiqueta", 400
    repeticiones = math.ceil(cantidad / etiquetas_por_repeticion)
    metros_totales = repeticiones * paso / 1000

    doc = fitz.open(path_pdf)
    label_pix = doc.load_page(0).get_pixmap()
    label_img_path = os.path.join(OUTPUT_FOLDER_FLEXO, "temp_label.png")
    label_pix.save(label_img_path)

    output_pdf_path = os.path.join(OUTPUT_FOLDER_FLEXO, "montaje_flexo_avanzado.pdf")
    c = canvas.Canvas(output_pdf_path, pagesize=(ancho_bobina * mm, paso * mm))

    for x_mm in x_positions:
        x = x_mm * mm
        for j in range(filas):
            y = (paso - alto - j * (alto + sep_v)) * mm
            c.drawImage(label_img_path, x, y, ancho * mm, alto * mm)
    c.save()

    preview_path = os.path.join(OUTPUT_FOLDER_FLEXO, "preview_flexo_avanzado.png")
    out_doc = fitz.open(output_pdf_path)
    out_doc.load_page(0).get_pixmap().save(preview_path)

    reporte_path = os.path.join(OUTPUT_FOLDER_FLEXO, "reporte_flexo_avanzado.html")
    aviso = ""
    if correccion_aplicada:
        aviso = (
            "<div style='padding:10px;border:2px solid #f39c12;background:#fff3cd;margin-bottom:10px;'>"
            "⚠️ Archivo original no contenía sangrado o marcas de corte.<br>"
            "Se aplicó corrección automática antes del montaje." "</div>"
        )
    with open(reporte_path, "w", encoding="utf-8") as f:
        f.write(
            f"""<html><body><h2>Reporte Montaje Flexo Avanzado</h2>{aviso}
            <p>Pistas: {pistas}</p>
            <p>Etiquetas por repetición: {etiquetas_por_repeticion}</p>
            <p>Repeticiones necesarias: {repeticiones}</p>
            <p>Metros totales: {round(metros_totales, 2)} m</p>
            <p>Alineación: {alignment}</p>
            </body></html>"""
        )

    with open(preview_path, "rb") as img_f:
        preview_b64 = base64.b64encode(img_f.read()).decode("utf-8")

    return render_template(
        "montaje_flexo_avanzado.html",
        preview=preview_b64,
        pistas=pistas,
        etiquetas_por_repeticion=etiquetas_por_repeticion,
        repeticiones=repeticiones,
        metros_totales=round(metros_totales, 2),
        alignment=alignment,
    )


@routes_bp.route("/descargar_montaje_flexo_avanzado")
def descargar_montaje_flexo_avanzado():
    return send_file(
        os.path.join(OUTPUT_FOLDER_FLEXO, "montaje_flexo_avanzado.pdf"),
        as_attachment=True,
    )


@routes_bp.route("/descargar_reporte_flexo_avanzado")
def descargar_reporte_flexo_avanzado():
    return send_file(
        os.path.join(OUTPUT_FOLDER_FLEXO, "reporte_flexo_avanzado.html"),
        as_attachment=True,
    )


@routes_bp.route("/habla-ingles", methods=["GET", "POST"])
def habla_ingles():
    mensaje = ""
    transcripcion = ""
    analisis = ""
    if request.method == "POST":
        audio = request.files.get("audio")
        if audio and audio.filename.endswith(".mp3"):
            try:
                transcripcion = transcribir_audio(audio)
                prompt = f"""
El siguiente texto fue hablado por un estudiante de inglés. Analiza su nivel de pronunciación y gramática (en base al texto transcrito), y sugiere cómo podría mejorar. Sé claro, breve y amable. También indica el nivel estimado (A1, B1, C1, etc).

Texto: "{transcripcion}"
"""
                analisis = chat_completion(prompt)
            except Exception as e:
                mensaje = f" Error al procesar audio: {str(e)}"
        else:
            mensaje = " Por favor, subí un archivo .mp3 válido."
    return render_template("habla_ingles.html", mensaje=mensaje, transcripcion=transcripcion, analisis=analisis)


@routes_bp.route("/simula-ingles", methods=["GET", "POST"])
def simula_ingles():
    global chat_historial
    texto_usuario = ""
    respuesta_ia = ""
    modo = "general"

    if request.method == "POST":
        texto_usuario = request.form.get("texto", "").strip()
        modo = request.form.get("modo", "general")
        if modo == "quiz":
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
            respuesta_ia = chat_completion(prompt)
            if texto_usuario:
                chat_historial.append(("🧑", texto_usuario))
            if respuesta_ia:
                chat_historial.append(("🤖", respuesta_ia))
            chat_historial = chat_historial[-10:]
        except Exception as e:
            respuesta_ia = f"[ERROR] No se pudo generar respuesta: {str(e)}"

    historial_html = ""
    for quien, mensaje in chat_historial:
        clase = "user-msg" if quien == "🧑" else "ia-msg"
        historial_html += f"<div class='bubble {clase}'>{quien} {mensaje}</div>"

    return render_template("simula_ingles.html", texto_usuario=texto_usuario, respuesta=respuesta_ia, contexto=modo, historial=historial_html)


@routes_bp.route("/reset-chat")
def reset_chat():
    global chat_historial
    chat_historial = []
    return redirect(url_for('routes.simula_ingles'))


@routes_bp.route("/vista_previa", methods=["POST"])
def vista_previa():
    archivo = request.files["archivo"]
    modo = int(request.form.get("modo", "2"))
    filename = secure_filename(archivo.filename)
    ruta_pdf = os.path.join(UPLOAD_FOLDER, filename)
    archivo.save(ruta_pdf)

    if modo == 2:
        generar_preview_interactivo(ruta_pdf)
        return send_from_directory("preview_temp", "preview.html")
    else:
        montar_pdf(ruta_pdf, "output/montado.pdf", paginas_por_cara=modo)
        return send_file("output/montado.pdf", as_attachment=True)


@routes_bp.route('/preview_temp/<filename>')
def mostrar_preview_temp(filename):
    return send_from_directory('preview_temp', filename)


@routes_bp.route("/preview")
def vista_preview():
    pagina = int(request.args.get("p", 1))
    modo = int(request.args.get("modo", 2))
    files = sorted(os.listdir("preview_temp"))
    total = len(files)
    pag1 = files[pagina - 1] if pagina - 1 < total else None
    pag2 = files[pagina] if pagina < total else None
    anterior = pagina - 2 if pagina > 2 else 1
    siguiente = pagina + 2 if pagina + 1 < total else pagina
    html = f"""
    <!doctype html>
    <html lang='es'>
    <head>
        <meta charset='utf-8'>
        <title>Vista previa del Pliego</title>
        <style>
            body {{font-family: sans-serif; text-align: center; padding: 20px;}}
            img {{height: 480px; margin: 0 10px; border: 2px solid #ccc; border-radius: 10px;}}
            .nav-buttons {{margin-top: 20px;}}
            button {{padding: 10px 20px; font-size: 16px; margin: 0 10px;}}
        </style>
    </head>
    <body>
        <h1>Vista previa del Pliego {pagina // 2 + 1}</h1>
        <div>
            {f'<img src="/preview_temp/{pag1}">' if pag1 else ''}
            {f'<img src="/preview_temp/{pag2}">' if pag2 else ''}
        </div>
        <div class='nav-buttons'>
            <a href='/preview?p={anterior}&modo={modo}'><button>Anterior</button></a>
            <a href='/preview?p={siguiente}&modo={modo}'><button>Siguiente</button></a>
        </div>
        <form action='/generar_pdf_final' method='post'>
            <input type='hidden' name='modo_montaje' value='{modo}'>
            <button type='submit'>Montar PDF final</button>
        </form>
    </body>
    </html>
    """
    return html


@routes_bp.route("/generar_pdf_final", methods=["POST"])
def generar_pdf_final():
    modo = int(request.form.get("modo_montaje", 2))
    pdfs = [f for f in os.listdir("uploads") if f.endswith(".pdf")]
    if not pdfs:
        return "No hay archivo para montar."
    path_pdf = os.path.join("uploads", pdfs[-1])
    output_pdf_path = "output/montado.pdf"
    montar_pdf(path_pdf, output_pdf_path, paginas_por_cara=modo)
    return send_file(output_pdf_path, as_attachment=True)


@routes_bp.route("/revision", methods=["GET", "POST"])
def revision_flexo():
    mensaje = ""
    resultado_revision = ""
    grafico_tinta = ""
    diagnostico_texto = ""
    resultado_revision_b64 = ""
    diagnostico_texto_b64 = ""

    if request.method == "POST":
        try:
            archivo = request.files.get("archivo_revision")
            anilox_lpi = int(request.form.get("anilox_lpi", 360))
            paso_mm = int(request.form.get("paso_cilindro", 330))
            material = request.form.get("material", "")
            anilox_bcm = request.form.get("anilox_bcm")
            velocidad = request.form.get("velocidad_impresion")
            cobertura = request.form.get("cobertura_estimada")

            if anilox_bcm and velocidad and cobertura:
                anilox_bcm = float(anilox_bcm)
                velocidad = float(velocidad)
                cobertura = float(cobertura)
            else:
                anilox_bcm = velocidad = cobertura = None

            if archivo and archivo.filename.endswith(".pdf"):
                filename = secure_filename(archivo.filename)
                path = os.path.join(UPLOAD_FOLDER_FLEXO, filename)
                archivo.save(path)

                resultado_revision, grafico_tinta, diagnostico_texto = revisar_diseño_flexo(
                    path,
                    anilox_lpi,
                    paso_mm,
                    material,
                    anilox_bcm,
                    velocidad,
                    cobertura,
                )
                resultado_revision_b64 = base64.b64encode(resultado_revision.encode("utf-8")).decode("utf-8")
                diagnostico_texto_b64 = base64.b64encode(diagnostico_texto.encode("utf-8")).decode("utf-8")
            else:
                mensaje = "Archivo inválido. Subí un PDF."
        except Exception as e:
            mensaje = f"Error al revisar diseño: {str(e)}"

    return render_template(
        "revision_flexo.html",
        mensaje=mensaje,
        resultado_revision=resultado_revision,
        grafico_tinta=grafico_tinta,
        diagnostico_texto=diagnostico_texto,
        diagnostico_texto_b64=diagnostico_texto_b64,
        resultado_revision_b64=resultado_revision_b64,
    )


@routes_bp.route("/sugerencia_ia", methods=["POST"])
def sugerencia_ia():
    resultado_revision_b64 = request.form.get("resultado_revision_b64", "")
    diagnostico_texto_b64 = request.form.get("diagnostico_texto_b64", "")
    grafico_tinta = request.form.get("grafico_tinta", "")
    try:
        resultado_revision = base64.b64decode(resultado_revision_b64).decode("utf-8")
        diagnostico_texto = base64.b64decode(diagnostico_texto_b64).decode("utf-8")
    except Exception:
        resultado_revision = ""
        diagnostico_texto = ""
    sugerencia = ""
    if diagnostico_texto:
        try:
            prompt = diagnostico_texto
            sugerencia = chat_completion(prompt, model="gpt-4", temperature=0.3)
        except Exception as e:
            sugerencia = f"Error al obtener sugerencia de IA: {str(e)}"
    return render_template(
        "revision_flexo.html",
        resultado_revision=resultado_revision,
        grafico_tinta=grafico_tinta,
        diagnostico_texto=diagnostico_texto,
        diagnostico_texto_b64=diagnostico_texto_b64,
        resultado_revision_b64=resultado_revision_b64,
        sugerencia_ia=sugerencia,
    )


@routes_bp.route("/sugerencia_produccion", methods=["POST"])
def sugerencia_produccion():
    resultado_revision_b64 = request.form.get("resultado_revision_b64", "")
    diagnostico_texto_b64 = request.form.get("diagnostico_texto_b64", "")
    grafico_tinta = request.form.get("grafico_tinta", "")
    try:
        resultado_revision = base64.b64decode(resultado_revision_b64).decode("utf-8")
        diagnostico_texto = base64.b64decode(diagnostico_texto_b64).decode("utf-8")
    except Exception:
        resultado_revision = ""
        diagnostico_texto = ""
    sugerencia = generar_sugerencia_produccion(diagnostico_texto, resultado_revision)
    return render_template(
        "revision_flexo.html",
        resultado_revision=resultado_revision,
        grafico_tinta=grafico_tinta,
        diagnostico_texto=diagnostico_texto,
        diagnostico_texto_b64=diagnostico_texto_b64,
        resultado_revision_b64=resultado_revision_b64,
        sugerencia_produccion=sugerencia,
    )
