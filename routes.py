import os
import base64
import io
import math
import fitz
import uuid
import tempfile
import shutil
import json
from threading import Lock
from PIL import Image
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
    jsonify,
    current_app,
    session,
    flash,
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from montaje import montar_pdf
from diagnostico import diagnosticar_pdf, analizar_grafico_tecnico
from diagnostico_pdf import diagnostico_offset_pro
from utils import (
    corregir_sangrado,
    redimensionar_pdf,
    calcular_etiquetas_por_fila,
    normalizar_material,
    convertir_pts_a_mm,
)
from simulacion import (
    generar_preview_interactivo,
    generar_preview_virtual,
    generar_simulacion_avanzada,
)
from ia_sugerencias import chat_completion, transcribir_audio
from montaje_flexo import (
    revisar_diseño_flexo,
    generar_sugerencia_produccion,
    corregir_sangrado_y_marcas,
)
from preview_tecnico import generar_preview_tecnico, analizar_riesgos_pdf
from montaje_offset import montar_pliego_offset
from montaje_offset_inteligente import montar_pliego_offset_inteligente
from montaje_offset_personalizado import montar_pliego_offset_personalizado
from imposicion_offset_auto import imponer_pliego_offset_auto
from diagnostico_flexo import (
    generar_preview_diagnostico,
    inyectar_parametros_simulacion,
    resumen_advertencias,
    indicadores_advertencias,
)
from simulador_riesgos import simular_riesgos

# Carpeta de subidas dentro de ``static`` para persistir archivos entre
# formularios y poder servirlos directamente.
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
try:
    os.chmod(UPLOAD_FOLDER, 0o775)
except OSError:
    pass
os.makedirs("output", exist_ok=True)
os.makedirs("preview_temp", exist_ok=True)
UPLOAD_FOLDER_FLEXO = UPLOAD_FOLDER
OUTPUT_FOLDER_FLEXO = "output_flexo"
os.makedirs(OUTPUT_FOLDER_FLEXO, exist_ok=True)

chat_historial = []


routes_bp = Blueprint("routes", __name__)

heavy_lock = Lock()

def _json_error(msg, code=422):
    return jsonify(ok=False, error=msg), code


@routes_bp.app_errorhandler(RequestEntityTooLarge)
def _too_large(e):
    return _json_error("Payload demasiado grande. Reduce DPI o cantidad de archivos.", 413)


def _resolve_uploads():
    return current_app.config.get("LAST_UPLOADS", [])


def _tmp_static(*parts):
    p = os.path.join(current_app.static_folder, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def _unpack_preview_result(res, preview_path, ancho_pliego, alto_pliego):
    """Adapta retornos posibles de ``montar_pliego_offset_inteligente``.

    Acepta un ``dict`` con claves ``preview_path``, ``resumen_html``,
    ``positions`` y ``sheet_mm``; una tupla ``(bytes, str)`` donde se espera
    que la función haya devuelto los bytes de la imagen y un resumen HTML; o
    simplemente un ``str`` con la ruta al PNG generado previamente.

    Devuelve siempre una tupla ``(preview_path_abs, resumen_html,
    positions, sheet_mm)``.
    """
    import os

    if isinstance(res, dict):
        pp = res.get("preview_path") or preview_path
        return (pp, res.get("resumen_html"), res.get("positions"), res.get("sheet_mm"))
    if isinstance(res, tuple):
        img_bytes, resumen_html = res
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)
        with open(preview_path, "wb") as f:
            f.write(img_bytes)
        return (preview_path, resumen_html, None, {"w": ancho_pliego, "h": alto_pliego})
    if isinstance(res, str):
        return (res, None, None, {"w": ancho_pliego, "h": alto_pliego})
    return (preview_path, None, None, {"w": ancho_pliego, "h": alto_pliego})


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


@routes_bp.route("/diagnostico_offset", methods=["POST"])
def diagnostico_offset_endpoint():
    with heavy_lock:
        archivo = request.files.get("pdf")
        if not archivo or archivo.filename == "":
            return jsonify({"ok": False, "error": "Debe subir un PDF"}), 400
        filename = secure_filename(archivo.filename)
        path_pdf = os.path.join(UPLOAD_FOLDER, filename)
        archivo.save(path_pdf)

        doc = fitz.open(path_pdf)
        pdf_page_count = doc.page_count
        doc.close()
        if pdf_page_count > current_app.config.get("MAX_PAGES_DIAG", 3):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "PDF demasiado largo para diagnóstico en modo free. Suba ≤3 páginas.",
                    }
                ),
                413,
            )

        report, preview_bytes = diagnostico_offset_pro(path_pdf)
        bleed = report.get("bleed_mm", {})
        summary_html = (
            "<table border='1' cellpadding='4'>"
            f"<tr><th>Método</th><td>{report['detected_by']}</td></tr>"
            f"<tr><th>Confianza</th><td>{report['confidence']:.2f}</td></tr>"
            f"<tr><th>Tamaño final (mm)</th><td>{report['final_size_mm']['w']} x {report['final_size_mm']['h']}</td></tr>"
            f"<tr><th>Sangrado (mm)</th><td>Top {bleed.get('top',0)} | Right {bleed.get('right',0)} | Bottom {bleed.get('bottom',0)} | Left {bleed.get('left',0)}</td></tr>"
            "</table>"
        )

        b64 = base64.b64encode(preview_bytes).decode("ascii")
        return jsonify(
            {
                "ok": True,
                "report": report,
                "preview_data": f"data:image/jpeg;base64,{b64}",
                "summary_html": summary_html,
            }
        )


@routes_bp.route('/descargar')
def descargar_pdf():
    return send_file("output/montado.pdf", as_attachment=True)


@routes_bp.route('/outputs/<path:filename>')
def outputs_static(filename):
    return send_from_directory('outputs', filename)


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


def _parse_montaje_offset_form(req):
    archivos = req.files.getlist("archivos[]")
    if not archivos or len(archivos) > 5:
        raise ValueError("Debe subir entre 1 y 5 archivos PDF")

    pliego = req.form.get("pliego", "700x1000")
    if pliego == "640x880":
        ancho_pliego, alto_pliego = 640.0, 880.0
    elif pliego == "700x1000":
        ancho_pliego, alto_pliego = 700.0, 1000.0
    elif pliego == "personalizado":
        ancho_pliego = float(req.form.get("ancho_pliego_custom"))
        alto_pliego = float(req.form.get("alto_pliego_custom"))
    else:
        raise ValueError("Formato de pliego inválido")

    diseños = []
    for i, f in enumerate(archivos):
        filename = secure_filename(f.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(path)
        repeticiones = int(req.form.get(f"repeticiones_{i}", 1))
        diseños.append((path, repeticiones))

    current_app.config["LAST_UPLOADS"] = [path for path, _ in diseños]

    estrategia = req.form.get("estrategia", "flujo")
    if req.form.get("forzar_grilla"):
        estrategia = "grid"

    ordenar_tamano = bool(req.form.get("ordenar_tamano"))
    alinear_filas = bool(req.form.get("alinear_filas"))
    preferir_horizontal = bool(req.form.get("preferir_horizontal"))

    centrar = True
    if "centrar" in req.form or "centrar_montaje" in req.form:
        centrar = bool(req.form.get("centrar") or req.form.get("centrar_montaje"))

    filas = int(req.form.get("filas", 0) or 0)
    columnas = int(req.form.get("columnas", 0) or 0)
    celda_ancho = float(req.form.get("celda_ancho", 0) or 0)
    celda_alto = float(req.form.get("celda_alto", 0) or 0)

    pinza_mm = float(req.form.get("pinza_mm", 0) or 0)
    lateral_mm = float(req.form.get("lateral_mm", 0) or 0)
    marcas_registro = bool(req.form.get("marcas_registro"))
    marcas_corte = bool(req.form.get("marcas_corte"))
    cutmarks_por_forma = bool(req.form.get("cutmarks_por_forma"))
    debug_grilla = bool(req.form.get("debug_grilla"))

    # Opciones de sangrado
    modo_sangrado = req.form.get("modo_sangrado", "original")
    sangrado_mm = 0.0
    usar_trimbox = False
    if modo_sangrado == "add":
        sangrado_mm = float(req.form.get("sangrado_add", 0) or 0)
    elif modo_sangrado == "replace":
        sangrado_mm = float(req.form.get("sangrado_replace", 0) or 0)
        usar_trimbox = True

    if estrategia == "flujo":
        ordenar_tamano = False if "ordenar_tamano" not in req.form else ordenar_tamano
        alinear_filas = True if "alinear_filas" not in req.form else alinear_filas
    elif estrategia == "grid":
        alinear_filas = False
    elif estrategia == "maxrects":
        ordenar_tamano = True if "ordenar_tamano" not in req.form else ordenar_tamano
        alinear_filas = False
        preferir_horizontal = False

    params = {
        "separacion": float(req.form.get("separacion", 4)),
        "ordenar_tamano": ordenar_tamano,
        "alinear_filas": alinear_filas,
        "preferir_horizontal": preferir_horizontal,
        "centrar": centrar,
        "debug_grilla": debug_grilla,
        "espaciado_horizontal": float(req.form.get("espaciado_horizontal", 0)),
        "espaciado_vertical": float(req.form.get("espaciado_vertical", 0)),
        "margen_izq": float(req.form.get("margen_izq", 10)),
        "margen_der": float(req.form.get("margen_der", 10)),
        "margen_sup": float(req.form.get("margen_sup", 10)),
        "margen_inf": float(req.form.get("margen_inf", 10)),
        "estrategia": estrategia,
        "filas": filas,
        "columnas": columnas,
        "celda_ancho": celda_ancho,
        "celda_alto": celda_alto,
        "pinza_mm": pinza_mm,
        "lateral_mm": lateral_mm,
        "marcas_registro": marcas_registro,
        "marcas_corte": marcas_corte,
        "cutmarks_por_forma": cutmarks_por_forma,
        "sangrado": sangrado_mm,
        "usar_trimbox": usar_trimbox,
    }

    return diseños, ancho_pliego, alto_pliego, params


@routes_bp.route("/montaje_offset_inteligente", methods=["GET", "POST"])
def montaje_offset_inteligente_view():
    if request.method == "GET":
        return render_template(
            "montaje_offset_inteligente.html",
            resultado=None,
            preview_url=None,
            resumen_html=None,
        )

    accion = request.form.get("accion") or "generar"
    mode = request.form.get("mode", "std")
    if mode != "pro":
        try:
            diseños, ancho_pliego, alto_pliego, params = _parse_montaje_offset_form(request)
            export_area_util = request.form.get("export_area_util") == "on"
            opciones_extra = {"export_area_util": export_area_util}
        except Exception as e:
            return str(e), 400

        if accion == "preview":
            previews_dir = os.path.join(current_app.static_folder, "previews")
            os.makedirs(previews_dir, exist_ok=True)
            job_id = str(uuid.uuid4())[:8]
            preview_path = os.path.join(
                previews_dir, f"offset_inteligente_{job_id}.png"
            )
            # NUEVO: generamos preview real y pedimos posiciones/sheet
            res = montar_pliego_offset_inteligente(
                diseños,
                ancho_pliego,
                alto_pliego,
                separacion=params["separacion"],
                sangrado=params["sangrado"],
                usar_trimbox=params["usar_trimbox"],
                ordenar_tamano=params["ordenar_tamano"],
                alinear_filas=params["alinear_filas"],
                preferir_horizontal=params["preferir_horizontal"],
                centrar=params["centrar"],
                debug_grilla=params["debug_grilla"],
                espaciado_horizontal=params["espaciado_horizontal"],
                espaciado_vertical=params["espaciado_vertical"],
                margen_izq=params["margen_izq"],
                margen_der=params["margen_der"],
                margen_sup=params["margen_sup"],
                margen_inf=params["margen_inf"],
                estrategia=params["estrategia"],
                filas=params["filas"],
                columnas=params["columnas"],
                celda_ancho=params["celda_ancho"],
                celda_alto=params["celda_alto"],
                pinza_mm=params["pinza_mm"],
                lateral_mm=params["lateral_mm"],
                marcas_registro=params["marcas_registro"],
                marcas_corte=params["marcas_corte"],
                cutmarks_por_forma=params["cutmarks_por_forma"],
                preview_path=preview_path,          # << genera archivo real
                devolver_posiciones=True,           # << pedimos positions + sheet
                preview_only=False,
                **opciones_extra,
            )

            ppath_abs, resumen_html, positions, sheet_mm = _unpack_preview_result(
                res, preview_path, ancho_pliego, alto_pliego
            )
            rel_path = os.path.relpath(ppath_abs, current_app.static_folder).replace(
                "\\", "/"
            )
            preview_url = url_for("static", filename=rel_path)
            files_list = [ruta for ruta, _ in diseños]

            current_app.config["LAST_SHEET_MM"] = sheet_mm
            current_app.config["LAST_SANGRADO_MM"] = params["sangrado"]

            return render_template(
                "montaje_offset_inteligente.html",
                resultado=None,
                preview_url=preview_url,
                resumen_html=resumen_html,
                positions=positions,
                sheet_mm=sheet_mm,
                sangrado_mm=params["sangrado"],
                files_list=files_list,
            )

        output_path = os.path.join("output", "pliego_offset_inteligente.pdf")
        montar_pliego_offset_inteligente(
            diseños,
            ancho_pliego,
            alto_pliego,
            separacion=params["separacion"],
            sangrado=params["sangrado"],
            usar_trimbox=params["usar_trimbox"],
            ordenar_tamano=params["ordenar_tamano"],
            alinear_filas=params["alinear_filas"],
            preferir_horizontal=params["preferir_horizontal"],
            centrar=params["centrar"],
            debug_grilla=params["debug_grilla"],
            espaciado_horizontal=params["espaciado_horizontal"],
            espaciado_vertical=params["espaciado_vertical"],
            margen_izq=params["margen_izq"],
            margen_der=params["margen_der"],
            margen_sup=params["margen_sup"],
            margen_inf=params["margen_inf"],
            estrategia=params["estrategia"],
            filas=params["filas"],
            columnas=params["columnas"],
            celda_ancho=params["celda_ancho"],
            celda_alto=params["celda_alto"],
            pinza_mm=params["pinza_mm"],
            lateral_mm=params["lateral_mm"],
            marcas_registro=params["marcas_registro"],
            marcas_corte=params["marcas_corte"],
            cutmarks_por_forma=params["cutmarks_por_forma"],
            output_path=output_path,
            **opciones_extra,
        )
        return send_file(output_path, as_attachment=True)

    # === MODO PRO ===
    files = request.files.getlist("pro_files")
    filenames = request.form.getlist("pro_filename[]")
    reps = [x.strip() for x in request.form.getlist("pro_reps[]")]
    rotate = [(x == "on") for x in request.form.getlist("pro_rotate[]")]
    bleeds = [
        (float(x) if x.strip() else None) for x in request.form.getlist("pro_bleed_mm[]")
    ]
    cutmarks = [(x == "on") for x in request.form.getlist("pro_cutmarks[]")]
    priority = [
        int(x) if x.strip() else (i + 1)
        for i, x in enumerate(request.form.getlist("pro_priority[]"))
    ]
    aligns = request.form.getlist("pro_align[]")

    pliego = request.form.get("pro_pliego")
    if pliego == "640x880":
        ancho_pliego, alto_pliego = 640.0, 880.0
    elif pliego == "700x1000":
        ancho_pliego, alto_pliego = 700.0, 1000.0
    elif pliego == "personalizado":
        ancho_pliego = float(request.form.get("pro_ancho_pliego_custom", 0) or 0)
        alto_pliego = float(request.form.get("pro_alto_pliego_custom", 0) or 0)
    else:
        return "Formato de pliego inválido", 400

    margen_izq = float(request.form.get("pro_margen_izq", 10) or 10)
    margen_der = float(request.form.get("pro_margen_der", margen_izq) or margen_izq)
    margen_sup = float(request.form.get("pro_margen_sup", 10) or 10)
    margen_inf = float(request.form.get("pro_margen_inf", margen_sup) or margen_sup)
    esp_h = float(request.form.get("pro_espaciado_horizontal", 0) or 0)
    esp_v = float(request.form.get("pro_espaciado_vertical", 0) or 0)
    export_area_util = request.form.get("pro_export_area_util") == "on"
    preview = request.form.get("pro_preview") == "on"

    specs = []
    for i, f in enumerate(files):
        specs.append(
            {
                "file": f,
                "filename": filenames[i]
                if i < len(filenames)
                else getattr(f, "filename", f"file_{i+1}.pdf"),
                "reps": int(reps[i]) if (i < len(reps) and reps[i]) else 0,
                "rotate": rotate[i] if i < len(rotate) else False,
                "bleed_mm": bleeds[i] if i < len(bleeds) else None,
                "cutmarks": cutmarks[i] if i < len(cutmarks) else False,
                "priority": priority[i] if i < len(priority) else i + 1,
                "align": aligns[i] if i < len(aligns) else "center",
            }
        )

    specs.sort(key=lambda s: s["priority"])

    pro_config = {
        "pliego_w_mm": ancho_pliego,
        "pliego_h_mm": alto_pliego,
        "margen_izq_mm": margen_izq,
        "margen_der_mm": margen_der,
        "margen_sup_mm": margen_sup,
        "margen_inf_mm": margen_inf,
        "sep_h_mm": esp_h,
        "sep_v_mm": esp_v,
        "export_area_util": export_area_util,
        "preview": preview,
    }

    output_path, resumen = montar_pliego_offset_personalizado(
        specs=specs, pro_config=pro_config
    )
    return send_file(output_path, as_attachment=True)


@routes_bp.route("/montaje_offset/preview", methods=["POST"])
def montaje_offset_preview():
    try:
        with heavy_lock:
            diseños, ancho_pliego, alto_pliego, params = _parse_montaje_offset_form(request)
            export_area_util = request.form.get("export_area_util") == "on"
            opciones_extra = {"export_area_util": export_area_util}
            png_bytes, resumen_html = montar_pliego_offset_inteligente(
                diseños,
                ancho_pliego,
                alto_pliego,
                separacion=params["separacion"],
                sangrado=params["sangrado"],
                usar_trimbox=params["usar_trimbox"],
                ordenar_tamano=params["ordenar_tamano"],
                alinear_filas=params["alinear_filas"],
                preferir_horizontal=params["preferir_horizontal"],
                centrar=params["centrar"],
                debug_grilla=params["debug_grilla"],
                espaciado_horizontal=params["espaciado_horizontal"],
                espaciado_vertical=params["espaciado_vertical"],
                margen_izq=params["margen_izq"],
                margen_der=params["margen_der"],
                margen_sup=params["margen_sup"],
                margen_inf=params["margen_inf"],
                estrategia=params["estrategia"],
                filas=params["filas"],
                columnas=params["columnas"],
                celda_ancho=params["celda_ancho"],
                celda_alto=params["celda_alto"],
                pinza_mm=params["pinza_mm"],
                lateral_mm=params["lateral_mm"],
                marcas_registro=params["marcas_registro"],
                marcas_corte=params["marcas_corte"],
                cutmarks_por_forma=params["cutmarks_por_forma"],
                preview_only=True,
                **opciones_extra,
            )
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return jsonify(
            {
                "ok": True,
                "preview_data": f"data:image/jpeg;base64,{b64}",
                "resumen_html": resumen_html or "",
            }
        )
    except TypeError as e:
        return jsonify({"ok": False, "error": f"TypeError: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
@routes_bp.route("/api/manual/preview", methods=["POST"])
def api_manual_preview():
    positions = request.json.get("positions", [])
    if not isinstance(positions, list):
        return _json_error("'positions' debe ser una lista.")

    positions = [p for p in positions if p and isinstance(p, dict)]
    if not positions:
        return _json_error("No hay posiciones válidas para aplicar.")

    diseños = [(ruta, 1) for ruta in _resolve_uploads()]
    name_to_idx = {os.path.basename(r): i for i, (r, _) in enumerate(diseños)}
    path_to_idx = {r: i for i, (r, _) in enumerate(diseños)}

    def _resolve_idx(p):
        # 1) file_idx explícito válido
        try:
            idx = int(p.get("file_idx"))
            if 0 <= idx < len(diseños):
                return idx
        except Exception:
            pass
        # 2) archivo exacto por ruta
        archivo = p.get("archivo")
        if archivo in path_to_idx:
            return path_to_idx[archivo]
        # 3) por nombre de archivo (basename)
        if archivo:
            idx = name_to_idx.get(os.path.basename(archivo))
            if idx is not None:
                return idx
        # 4) fallback
        return 0 if diseños else None

    for i, p in enumerate(positions):
        idx = _resolve_idx(p)
        if idx is None or not (0 <= idx < len(diseños)):
            return _json_error(f"file_idx inválido en positions[{i}]")
        try:
            x = float(p.get("x_mm")); y = float(p.get("y_mm"))
            w = float(p.get("w_mm")); h = float(p.get("h_mm"))
            # rotación por posición, en grados, con compatibilidad:
            rot_deg = p.get("rot_deg", None)
            if rot_deg is None:
                rot_deg = p.get("rot", 0)
                if rot_deg in (True, False):   # legacy 'rotado' boolean
                    rot_deg = 180 if rot_deg else 0
            rot_deg = int(rot_deg) % 360
        except Exception:
            return _json_error(f"positions[{i}] contiene valores no numéricos.")
        if w <= 0 or h <= 0:
            return _json_error(f"positions[{i}] ancho/alto deben ser > 0")
        uid = p.get("uid")
        p["uid"] = uid
        p["file_idx"] = idx
        p["rot_deg"] = rot_deg             # <-- normalizado y pegado a ESA posición
        real_path = diseños[idx][0]
        if not os.path.exists(real_path):
            return _json_error(
                f"El archivo no está disponible en el servidor: {os.path.basename(real_path)}. Volvé a subirlo."
            )

    sheet_mm = current_app.config.get("LAST_SHEET_MM", {})
    sangrado = current_app.config.get("LAST_SANGRADO_MM", 0)
    try:
        w_mm = float(sheet_mm.get("w"))
        h_mm = float(sheet_mm.get("h"))
        sangrado = float(sangrado)
    except Exception:
        return _json_error("Dimensiones del pliego inválidas en el servidor.")

    prev_dir = os.path.join(current_app.static_folder, "previews")
    os.makedirs(prev_dir, exist_ok=True)
    token = uuid.uuid4().hex
    preview_path = os.path.join(prev_dir, f"manual_{token}.png")

    for j, pos in enumerate(positions[:3]):
        current_app.logger.info(
            "[MANUAL] pos[%d] uid=%s idx=%s rot=%s x=%.2f y=%.2f w=%.2f h=%.2f",
            j,
            pos.get("uid"),
            pos.get("file_idx"),
            pos.get("rot_deg"),
            float(pos.get("x_mm", 0)),
            float(pos.get("y_mm", 0)),
            float(pos.get("w_mm", 0)),
            float(pos.get("h_mm", 0)),
        )

    try:
        res = montar_pliego_offset_inteligente(
            diseños,
            w_mm,
            h_mm,
            posiciones_manual=positions,
            sangrado=sangrado,
            preview_only=True,
            preview_path=preview_path,
        )
        rel = os.path.relpath(preview_path, current_app.static_folder).replace("\\", "/")
        url = url_for("static", filename=rel)
        if isinstance(res, dict):
            res["preview_path"] = url
        else:
            res = {"preview_path": url}
        res["positions_applied"] = [
            {
                "uid": p.get("uid"),
                "file_idx": p["file_idx"],
                "x_mm": float(p["x_mm"]),
                "y_mm": float(p["y_mm"]),
                "w_mm": float(p["w_mm"]),
                "h_mm": float(p["h_mm"]),
                "rot_deg": int(p["rot_deg"]) % 360,
            }
            for p in positions
        ]
        return jsonify(res), 200
    except Exception as e:
        current_app.logger.exception("api_manual_preview error")
        return _json_error(f"Fallo en preview: {str(e)}")


@routes_bp.route("/api/manual/impose", methods=["POST"])
def api_manual_impose():
    positions = request.json.get("positions", [])
    if not isinstance(positions, list):
        return _json_error("'positions' debe ser una lista.")

    positions = [p for p in positions if p and isinstance(p, dict)]
    if not positions:
        return _json_error("No hay posiciones válidas para aplicar.")

    diseños = [(ruta, 1) for ruta in _resolve_uploads()]
    name_to_idx = {os.path.basename(r): i for i, (r, _) in enumerate(diseños)}
    path_to_idx = {r: i for i, (r, _) in enumerate(diseños)}

    def _resolve_idx(p):
        try:
            idx = int(p.get("file_idx"))
            if 0 <= idx < len(diseños):
                return idx
        except Exception:
            pass
        archivo = p.get("archivo")
        if archivo in path_to_idx:
            return path_to_idx[archivo]
        if archivo:
            idx = name_to_idx.get(os.path.basename(archivo))
            if idx is not None:
                return idx
        return 0 if diseños else None

    for i, p in enumerate(positions):
        idx = _resolve_idx(p)
        if idx is None or not (0 <= idx < len(diseños)):
            return _json_error(f"file_idx inválido en positions[{i}]")
        try:
            x = float(p.get("x_mm")); y = float(p.get("y_mm"))
            w = float(p.get("w_mm")); h = float(p.get("h_mm"))
            # rotación por posición, en grados, con compatibilidad:
            rot_deg = p.get("rot_deg", None)
            if rot_deg is None:
                rot_deg = p.get("rot", 0)
                if rot_deg in (True, False):   # legacy 'rotado' boolean
                    rot_deg = 180 if rot_deg else 0
            rot_deg = int(rot_deg) % 360
        except Exception:
            return _json_error(f"positions[{i}] contiene valores no numéricos.")
        if w <= 0 or h <= 0:
            return _json_error(f"positions[{i}] ancho/alto deben ser > 0")
        uid = p.get("uid")
        p["uid"] = uid
        p["file_idx"] = idx
        p["rot_deg"] = rot_deg             # <-- normalizado y pegado a ESA posición
        real_path = diseños[idx][0]
        if not os.path.exists(real_path):
            return _json_error(
                f"El archivo no está disponible en el servidor: {os.path.basename(real_path)}. Volvé a subirlo."
            )

    sheet_mm = current_app.config.get("LAST_SHEET_MM", {})
    sangrado = current_app.config.get("LAST_SANGRADO_MM", 0)
    try:
        w_mm = float(sheet_mm.get("w"))
        h_mm = float(sheet_mm.get("h"))
        sangrado = float(sangrado)
    except Exception:
        return _json_error("Dimensiones del pliego inválidas en el servidor.")

    out_dir = os.path.join(current_app.static_folder, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    token = uuid.uuid4().hex
    pdf_path = os.path.join(out_dir, f"manual_{token}.pdf")

    for j, pos in enumerate(positions[:3]):
        current_app.logger.info(
            "[MANUAL] pos[%d] uid=%s idx=%s rot=%s x=%.2f y=%.2f w=%.2f h=%.2f",
            j,
            pos.get("uid"),
            pos.get("file_idx"),
            pos.get("rot_deg"),
            float(pos.get("x_mm", 0)),
            float(pos.get("y_mm", 0)),
            float(pos.get("w_mm", 0)),
            float(pos.get("h_mm", 0)),
        )

    try:
        montar_pliego_offset_inteligente(
            diseños,
            w_mm,
            h_mm,
            posiciones_manual=positions,
            sangrado=sangrado,
            preview_only=False,
            output_pdf_path=pdf_path,
        )
        if not os.path.exists(pdf_path):
            return _json_error("El motor no generó el PDF.", 500)
        rel = os.path.relpath(pdf_path, current_app.static_folder).replace("\\", "/")
        pdf_url = url_for("static", filename=rel)
        return jsonify(
            pdf_url=pdf_url,
            positions_applied=[
                {
                    "uid": p.get("uid"),
                    "file_idx": p["file_idx"],
                    "x_mm": float(p["x_mm"]),
                    "y_mm": float(p["y_mm"]),
                    "w_mm": float(p["w_mm"]),
                    "h_mm": float(p["h_mm"]),
                    "rot_deg": int(p["rot_deg"]) % 360,
                }
                for p in positions
            ],
        ), 200
    except Exception as e:
        current_app.logger.exception("api_manual_impose error")
        return _json_error(f"Fallo en impose: {str(e)}")


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

    sangrado_izq = sangrado_der = 3 if auto_sangrado else 0
    marcas_de_corte = 4 if auto_marcas else 0
    ancho_total_etiqueta = ancho + sangrado_izq + sangrado_der + marcas_de_corte
    espacio_disponible = ancho_bobina - 2 * margen
    if espacio_disponible <= 0:
        return "Las dimensiones no permiten ninguna etiqueta", 400

    cantidad_pistas = calcular_etiquetas_por_fila(
        ancho_bobina=ancho_bobina,
        ancho_etiqueta=ancho_total_etiqueta,
        separacion_horizontal=sep_h,
        margen_lateral=margen,
    )
    cantidad_pistas = max(1, cantidad_pistas)

    espacio_utilizado = (
        cantidad_pistas * ancho_total_etiqueta
    ) + ((cantidad_pistas - 1) * sep_h)

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

    posiciones_x = []
    for i in range(cantidad_pistas):
        x = offset_x + i * (ancho_total_etiqueta + sep_h)
        posiciones_x.append(x)

    filas = max(1, math.floor((paso + sep_v) / (alto + sep_v)))
    etiquetas_por_repeticion = cantidad_pistas * filas
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

    for x_mm in posiciones_x:
        x = x_mm * mm
        for j in range(filas):
            y = (paso - alto - j * (alto + sep_v)) * mm
            c.drawImage(
                label_img_path, x, y, ancho_total_etiqueta * mm, alto * mm
            )
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
            <p>Pistas: {cantidad_pistas}</p>
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
        preview=f"data:image/png;base64,{preview_b64}",
        pistas=cantidad_pistas,
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


@routes_bp.route("/revision", methods=["GET", "POST"], endpoint="revision")
def revision():
    if request.method == "GET":
        return render_template("revision_flexo.html")

    current_app.logger.info(
        "REV FLEXO: method=%s form=%s files=%s",
        request.method,
        list(request.form.keys()),
        list(request.files.keys()),
    )

    file = request.files.get("archivo_revision")
    material = (request.form.get("material") or "").strip()

    def _parse_parametro_float(nombre, descripcion, minimo=0.0):
        raw = (request.form.get(nombre) or "").strip()
        if not raw:
            flash(f"Ingresá {descripcion}.", "warning")
            return None
        raw = raw.replace(",", ".")
        try:
            valor = float(raw)
        except ValueError:
            flash(f"El valor ingresado para {descripcion} no es numérico.", "warning")
            return None
        if valor <= minimo:
            flash(
                f"El valor de {descripcion} debe ser mayor a {minimo if minimo else 0}.",
                "warning",
            )
            return None
        return valor

    if not file or file.filename == "":
        flash("Subí un PDF válido.", "warning")
        return render_template("revision_flexo.html")
    if not material:
        flash("Elegí el material de impresión.", "warning")
        return render_template("revision_flexo.html")
    if not file.filename.lower().endswith(".pdf"):
        flash("Formato no permitido. Solo PDF.", "warning")
        return render_template("revision_flexo.html")

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 20 * 1024 * 1024)
    if size > max_size:
        flash("El PDF supera el tamaño permitido.", "danger")
        return render_template("revision_flexo.html")

    base_upload = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(base_upload, exist_ok=True)

    tmpdir = tempfile.mkdtemp()
    save_path = os.path.join(tmpdir, secure_filename(file.filename))
    file.save(save_path)
    current_app.logger.info(
        "REV FLEXO: guardado %s (%d bytes)", save_path, os.path.getsize(save_path)
    )

    material_norm = normalizar_material(material)
    current_app.logger.info(
        "REV FLEXO: material='%s' -> '%s'", material, material_norm
    )

    anilox_lpi_val = _parse_parametro_float(
        "anilox_lpi", "la lineatura del anilox (LPI)", minimo=0.0
    )
    anilox_bcm = _parse_parametro_float(
        "anilox_bcm", "el BCM del anilox (cm³/m²)", minimo=0.0
    )
    paso_mm = _parse_parametro_float(
        "paso_cilindro", "el paso del cilindro (mm)", minimo=0.0
    )
    velocidad = _parse_parametro_float(
        "velocidad_impresion", "la velocidad estimada de impresión (m/min)", minimo=0.0
    )

    if any(v is None for v in [anilox_lpi_val, anilox_bcm, paso_mm, velocidad]):
        return render_template("revision_flexo.html")

    anilox_lpi = int(round(anilox_lpi_val))
    cobertura = 25.0

    parametros_maquina = {
        "anilox_lpi": anilox_lpi,
        "anilox_bcm": anilox_bcm,
        "paso_del_cilindro": paso_mm,
        "velocidad_impresion": velocidad,
    }

    revision_id = uuid.uuid4().hex
    rev_dir = os.path.join(base_upload, revision_id)
    os.makedirs(rev_dir, exist_ok=True)

    try:
        (
            resumen,
            _imagen_tinta,
            texto,
            analisis_detallado,
            advertencias_overlay,
        ) = revisar_diseño_flexo(
            save_path,
            anilox_lpi,
            paso_mm,
            material_norm,
            anilox_bcm,
            velocidad,
            cobertura,
        )
        overlay_info = analizar_riesgos_pdf(
            save_path, advertencias=advertencias_overlay
        )
        if overlay_info.get("overlay_path"):
            overlay_persist = os.path.join(rev_dir, "overlay.png")
            shutil.copy(overlay_info["overlay_path"], overlay_persist)
            overlay_info["overlay_path"] = overlay_persist
        base_img_path, imagen_rel, imagen_iconos_rel, advertencias_iconos = generar_preview_diagnostico(
            save_path, overlay_info["advertencias"], dpi=overlay_info["dpi"]
        )

        # Persistir imágenes de diagnóstico en uploads/<revision_id>
        diag_abs = os.path.join(rev_dir, "diagnostico.png")
        shutil.copy(base_img_path, diag_abs)
        base_img_path = diag_abs
        diag_rel = os.path.relpath(diag_abs, current_app.static_folder)

        iconos_src = os.path.join(current_app.static_folder, imagen_iconos_rel)
        iconos_abs = os.path.join(rev_dir, "diagnostico_iconos.png")
        shutil.copy(iconos_src, iconos_abs)
        imagen_rel = diag_rel
        imagen_iconos_rel = os.path.relpath(iconos_abs, current_app.static_folder)

        tabla_riesgos = simular_riesgos(resumen)

        sim_dir = os.path.join(current_app.static_folder, "simulaciones")
        os.makedirs(sim_dir, exist_ok=True)
        sim_filename = f"sim_{revision_id}.png"
        sim_abs = os.path.join(sim_dir, sim_filename)
        generar_simulacion_avanzada(base_img_path, advertencias_iconos, anilox_lpi, sim_abs)
        sim_rel = os.path.relpath(sim_abs, current_app.static_folder)

        try:
            with fitz.open(save_path) as doc_dimensiones:
                page0 = doc_dimensiones.load_page(0)
                ancho_mm = convertir_pts_a_mm(page0.rect.width)
                alto_mm = convertir_pts_a_mm(page0.rect.height)
        except Exception:
            ancho_mm = 0.0
            alto_mm = 0.0

        advertencias_stats = indicadores_advertencias(advertencias_iconos)
        advertencias_resumen_txt = resumen_advertencias(advertencias_iconos)

        cobertura_dict = analisis_detallado.get("cobertura_por_canal", {})

        def _as_float(valor):
            try:
                return float(valor)
            except (TypeError, ValueError):
                return 0.0

        cobertura_letras = {
            "C": round(_as_float(cobertura_dict.get("Cyan")), 2),
            "M": round(_as_float(cobertura_dict.get("Magenta")), 2),
            "Y": round(_as_float(cobertura_dict.get("Amarillo")), 2),
            "K": round(_as_float(cobertura_dict.get("Negro")), 2),
        }
        cobertura_por_canal = {
            "Cyan": cobertura_letras["C"],
            "Magenta": cobertura_letras["M"],
            "Amarillo": cobertura_letras["Y"],
            "Negro": cobertura_letras["K"],
        }
        cobertura_total = round(
            cobertura_letras["C"]
            + cobertura_letras["M"]
            + cobertura_letras["Y"]
            + cobertura_letras["K"],
            2,
        )

        final_pdf_path = os.path.join(rev_dir, f"{revision_id}.pdf")
        shutil.copy(save_path, final_pdf_path)
        pdf_rel = os.path.relpath(final_pdf_path, current_app.static_folder)

        diagnostico_json = {
            "archivo": secure_filename(file.filename),
            "pdf_path": pdf_rel,
            "cobertura": cobertura_letras,
            "cobertura_por_canal": cobertura_por_canal,
            "cobertura_estimada": cobertura_total,
            "tac_total": cobertura_total,
            "cobertura_base_sum": cobertura_total,
            "anilox_lpi": anilox_lpi,
            "anilox_bcm": anilox_bcm,
            "paso": paso_mm,
            "paso_cilindro": paso_mm,
            "paso_del_cilindro": paso_mm,
            "material": material_norm,
            "velocidad_impresion": velocidad,
            "ancho_mm": round(ancho_mm, 2) if ancho_mm else 0.0,
            "alto_mm": round(alto_mm, 2) if alto_mm else 0.0,
            "ancho_util_m": round(ancho_mm / 1000.0, 4) if ancho_mm else 0.0,
            "advertencias_resumen": advertencias_resumen_txt,
            "indicadores_advertencias": advertencias_stats,
            "advertencias_total": advertencias_stats.get("total", 0),
            "tiene_tramas_debiles": advertencias_stats.get("hay_tramas_debiles", False),
            "tiene_overprint": advertencias_stats.get("hay_overprint", False),
            "tiene_texto_pequeno": advertencias_stats.get("hay_texto_pequeno", False),
            "conteo_overprint": advertencias_stats.get("conteo_overprint", 0),
            "conteo_tramas": advertencias_stats.get("conteo_tramas", 0),
        }
        diagnostico_json = inyectar_parametros_simulacion(
            diagnostico_json, parametros_maquina
        )

        diagnostico_data = {
            "pdf_path": final_pdf_path,
            "resultados_diagnostico": analisis_detallado,
            "datos_formulario": {
                "anilox_lpi": anilox_lpi,
                "anilox_bcm": anilox_bcm,
                "paso_cilindro": paso_mm,
                "paso_del_cilindro": paso_mm,
                "material": material_norm,
                "velocidad_impresion": velocidad,
                "cobertura": cobertura_total,
                "advertencias": overlay_info.get("advertencias", []),
            },
            "overlay_path": overlay_info["overlay_path"],
            "dpi": overlay_info["dpi"],
            "advertencias_resumen": advertencias_resumen_txt,
            "indicadores_advertencias": advertencias_stats,
            "cobertura_por_canal": cobertura_por_canal,
            "tac_total": cobertura_total,
            "ancho_mm": ancho_mm,
            "alto_mm": alto_mm,
            # Persistimos las rutas web del diagnóstico para que sigan
            # disponibles incluso si la simulación avanzada no se usa.
            "diag_base_web": diag_rel,
            "diag_img_web": imagen_iconos_rel,
        }

        resultado_data = {
            "resumen": resumen,
            "tabla_riesgos": tabla_riesgos,
            "imagen_path_web": imagen_rel,
            "imagen_iconos_web": imagen_iconos_rel,
            "pdf_path_web": pdf_rel,
            "texto": texto,
            "analisis": analisis_detallado,
            "advertencias_iconos": advertencias_iconos,
            "diagnostico_json": diagnostico_json,
            "advertencias_resumen": advertencias_resumen_txt,
            "indicadores_advertencias": advertencias_stats,
            "sim_img_web": sim_rel,
            "diag_base_web": diag_rel,
            # Persistir la ruta web de la imagen del diagnóstico con advertencias.
            # Se usará como base de la simulación avanzada y permite que, al
            # recargar la página de resultados, el canvas dibuje de inmediato la
            # misma imagen analizada.
            "diag_img_web": imagen_iconos_rel,
        }

        diag_json_path = os.path.join(rev_dir, "diag.json")
        res_json_path = os.path.join(rev_dir, "res.json")
        with open(diag_json_path, "w", encoding="utf-8") as f:
            json.dump(diagnostico_data, f)
        with open(res_json_path, "w", encoding="utf-8") as f:
            json.dump(resultado_data, f)

        session["revision_flexo_id"] = revision_id
        session["archivo_pdf"] = pdf_rel

    except Exception as e:
        current_app.logger.exception("REV FLEXO: fallo analizando")
        flash(f"Ocurrió un error procesando el PDF: {e}", "danger")
        return render_template("revision_flexo.html")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return render_template(
        "resultado_flexo.html",
        **resultado_data,
        revision_id=revision_id,
        # Usar la imagen de diagnóstico con advertencias como base inicial
        # para la simulación.  Si no existiera, el frontend mostrará un patrón
        # de puntos como fallback.
        sim_base_img=imagen_iconos_rel,
    )


@routes_bp.route("/resultado", methods=["GET"])
def resultado_flexo():
    revision_id = session.get("revision_flexo_id")
    if not revision_id:
        return redirect(url_for("revision"))
    res_json_path = os.path.join(
        current_app.static_folder, "uploads", revision_id, "res.json"
    )
    try:
        with open(res_json_path, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        current_app.logger.error(
            "REV FLEXO: resultados no encontrados en %s", res_json_path
        )
        flash(
            "No se encontraron los resultados de la revisión. Volvé a cargar el PDF.",
            "warning",
        )
        return redirect(url_for("revision"))
    # Asegurar que la simulación avanzada reciba la ruta de la imagen del
    # diagnóstico.  Versiones anteriores podían no incluir ``diag_img_web`` en
    # ``res.json``; en ese caso, reutilizamos la imagen con iconos si existe.
    if "diag_img_web" not in datos:
        datos["diag_img_web"] = datos.get("imagen_iconos_web") or datos.get("imagen_path_web")

    return render_template(
        "resultado_flexo.html",
        **datos,
        revision_id=revision_id,
        sim_base_img=datos.get("diag_img_web"),
    )


@routes_bp.route("/simulacion/exportar/<revision_id>", methods=["POST"])
def exportar_simulacion(revision_id):
    """Guarda la imagen de la simulación enviada desde el frontend."""
    img_file = request.files.get("image")
    if not img_file:
        return jsonify({"error": "No se recibió imagen"}), 400
    sim_dir = os.path.join(current_app.static_folder, "simulaciones")
    os.makedirs(sim_dir, exist_ok=True)
    filename = f"sim_{revision_id}.png"
    save_path = os.path.join(sim_dir, filename)
    img_file.save(save_path)
    rel_path = os.path.relpath(save_path, current_app.static_folder)
    url = url_for("static", filename=rel_path)
    return jsonify({"path": rel_path, "url": url})


@routes_bp.route("/vista_previa_tecnica", methods=["POST"])
def vista_previa_tecnica():
    try:
        pdf_path = request.form.get("archivo_guardado")
        revision_id = session.get("revision_flexo_id")
        if not pdf_path and revision_id:
            pdf_rel = os.path.join("uploads", revision_id, f"{revision_id}.pdf")
            pdf_path = os.path.join(current_app.static_folder, pdf_rel)
        elif pdf_path and not os.path.isabs(pdf_path):
            pdf_path = os.path.join(current_app.static_folder, pdf_path)
        if not pdf_path:
            return (
                jsonify(
                    {
                        "error": "Primero hacé clic en 'Revisar diseño' para generar el diagnóstico técnico.",
                    }
                ),
                400,
            )

        if not os.path.exists(pdf_path):
            current_app.logger.error("REV FLEXO: archivo PDF faltante %s", pdf_path)
            return (
                jsonify(
                    {
                        "error": "El archivo PDF del diseño ya no está disponible. Por favor, volvé a cargar el archivo.",
                    }
                ),
                400,
            )

        diag = {}
        if revision_id:
            diag_path = os.path.join(
                current_app.static_folder, "uploads", revision_id, "diag.json"
            )
            try:
                with open(diag_path, "r", encoding="utf-8") as f:
                    diag = json.load(f)
            except FileNotFoundError:
                current_app.logger.error(
                    "REV FLEXO: datos de diagnóstico faltantes %s", diag_path
                )

        rel_path = generar_preview_tecnico(
            pdf_path,
            diag.get("datos_formulario"),
            overlay_path=diag.get("overlay_path"),
            dpi=diag.get("dpi", 200),
        )
        url = url_for("static", filename=rel_path)
        print("🌐 URL pública vista previa técnica:", url)
        return jsonify({"preview_url": url})
    except Exception as e:
        current_app.logger.exception("vista_previa_tecnica")
        return jsonify({"error": str(e)}), 500


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


@routes_bp.route("/imposicion_offset_auto", methods=["GET", "POST"])
def imposicion_offset_auto_route():
    if request.method == "GET":
        return render_template("imposicion_offset_auto.html")

    file = request.files.get("file")
    if not file:
        return jsonify({"ok": False, "error": "Falta archivo PDF."}), 400

    filename = secure_filename(file.filename or "pieza.pdf")
    job_dir = os.path.join("uploads", "imposicion_auto")
    os.makedirs(job_dir, exist_ok=True)
    pdf_path = os.path.join(job_dir, filename)
    file.save(pdf_path)

    def _get_float(name, default):
        try:
            return float(request.form.get(name, default))
        except:
            return default

    def _get_bool(name, default):
        v = (request.form.get(name, str(default)).lower().strip())
        return v in ("1", "true", "t", "yes", "si", "on")

    cantidad = int(request.form.get("cantidad", "1000"))
    permitir_rotar_90 = _get_bool("permitir_rotar_90", True)
    margen_mm = _get_float("margen_mm", 10.0)
    pinza_mm = _get_float("pinza_mm", 12.0)
    gap_x_mm = _get_float("gap_x_mm", 3.0)
    gap_y_mm = _get_float("gap_y_mm", 3.0)
    guia_lateral = request.form.get("guia_lateral", "izquierda")

    formatos_pliego_mm = request.form.get("formatos_pliego_mm", "")
    if formatos_pliego_mm:
        pares = []
        for tok in formatos_pliego_mm.split(","):
            tok = tok.strip().lower().replace("mm", "")
            if "x" in tok:
                a, b = tok.split("x")
                pares.append([float(a), float(b)])
        if not pares:
            pares = [[700, 1000], [640, 880], [500, 700]]
    else:
        pares = [[700, 1000], [640, 880], [500, 700]]

    res = imponer_pliego_offset_auto(
        pdf_path=pdf_path,
        cantidad=cantidad,
        formatos_pliego_mm=pares,
        margen_mm=margen_mm,
        pinza_mm=pinza_mm,
        guia_lateral=guia_lateral,
        gap_x_mm=gap_x_mm,
        gap_y_mm=gap_y_mm,
        permitir_rotar_90=permitir_rotar_90,
        agregar_marcas=True,
        agregar_colorbar=True,
        salida_dir="outputs",
    )

    if request.headers.get("Accept") == "application/json":
        return jsonify(res)

    if res.get("ok"):
        return render_template("imposicion_offset_auto_result.html", data=res)
    else:
        return render_template("imposicion_offset_auto_error.html", data=res), 400
