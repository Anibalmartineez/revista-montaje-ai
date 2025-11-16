import os
import base64
import io
import math
import fitz
import uuid
import tempfile
import shutil
import json
from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple
from threading import Lock
from openai import OpenAI
from PIL import Image, ImageDraw
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
    abort,
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
from tinta_utils import normalizar_coberturas
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
from montaje_offset_inteligente import (
    Diseno,
    MontajeConfig,
    realizar_montaje_inteligente,
    generar_preview_pliego,
)
from montaje_offset_personalizado import montar_pliego_offset_personalizado
from imposicion_offset_auto import imponer_pliego_offset_auto
from diagnostico_flexo import (
    generar_preview_diagnostico,
    inyectar_parametros_simulacion,
    resumen_advertencias,
    indicadores_advertencias,
    coeficiente_material,
    obtener_coeficientes_material,
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
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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


POST_EDITOR_DIR = "ia_jobs"
LAYOUT_FILENAME = "layout.json"
META_FILENAME = "meta.json"
ASSETS_DIRNAME = "assets"
ORIGINAL_PDF_NAME = "pliego.pdf"
EDITED_PDF_NAME = "pliego_edit.pdf"
EDITED_PREVIEW_NAME = "preview_edit.png"


def _safe_job_id(job_id: str | None) -> str | None:
    if not job_id:
        return None
    token = job_id.strip()
    if not token or not token.isalnum():
        return None
    return token


def _jobs_root() -> str:
    root = os.path.join(current_app.static_folder, POST_EDITOR_DIR)
    os.makedirs(root, exist_ok=True)
    return root


def _job_dir(job_id: str | None) -> str | None:
    token = _safe_job_id(job_id)
    if not token:
        return None
    path = os.path.join(_jobs_root(), token)
    return path


def _job_relpath(job_id: str, *parts: str) -> str:
    return os.path.join(POST_EDITOR_DIR, job_id, *parts).replace("\\", "/")


def _layout_path(job_dir: str) -> str:
    return os.path.join(job_dir, LAYOUT_FILENAME)


def _meta_path(job_dir: str) -> str:
    return os.path.join(job_dir, META_FILENAME)


def _load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _load_job_meta(job_dir: str) -> Dict | None:
    path = _meta_path(job_dir)
    if not os.path.exists(path):
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _post_editor_enabled() -> bool:
    return bool(current_app.config.get("ENABLE_POST_EDITOR", False))


def call_openai_for_editor_chat(user_message: str, layout_state: Dict, job_id: str) -> Dict:
    system_prompt = """
Sos un asistente de montaje offset/flexográfico dentro de un editor visual de imposición.

SIEMPRE respondé en JSON con esta estructura EXACTA:
{
"assistant_message": "texto corto en español explicando qué harás",
"actions": [ ... lista de acciones ... ]
}

No devuelvas texto suelto fuera de ese JSON.

El backend te envía:

El estado actual del layout (layout_state) con información de:

Hoja (sheet)

Assets (archivos PDF)

Piezas (pieces) con posición y rotación en mm

Selección actual

Configuración relevante (sangrado, separación mínima, etc.)

Podés proponer acciones sobre el montaje usando estos tipos:

Limpiar selección:
{ "type": "clear_selection" }

Filtrar/seleccionar por nombre de archivo (asset):
{ "type": "filter_by_asset", "asset_name_contains": "Parmalat" }

Seleccionar por IDs de pieza:
{ "type": "select_pieces", "piece_ids": ["piece_1", "piece_7"] }

Alinear selección:
{
"type": "align",
"target": "selection",
"mode": "left|right|top|bottom|center-sheet|center-horizontal|center-vertical"
}

Distribuir selección:
{
"type": "distribute",
"target": "selection",
"direction": "horizontal|vertical",
"spacing_mm": 2
}

Mover selección:
{
"type": "move",
"target": "selection",
"dx_mm": 2,
"dy_mm": 0
}

Duplicar selección:
{
"type": "duplicate",
"target": "selection"
}

Calcular bounding box del grupo seleccionado y guardarlo:
{
"type": "compute_group_bbox",
"target": "selection",
"save_as": "bbox_torrente"
}

Organizar la selección actual como grilla relativa a un bounding box guardado:
{
"type": "arrange_grid_relative",
"target": "selection",
"rows": 3,
"gap_mm": 2,
"relative_to": "bbox_torrente",
"position": "above"
}

Ejemplos de instrucciones del usuario:

"Seleccioná todas las formas de Parmalat."

"Alineá todas las etiquetas de Parmalat a la derecha."

"Distribuí estas piezas con 2mm de separación."

"Poné todas las formas de Parmalat arriba de los archivos de Torrente, en 3 filas, separadas por 2mm."

En ese último caso:

Primero seleccionás las piezas de Torrente y calculás su bbox con compute_group_bbox guardado en, por ejemplo, "bbox_torrente".

Después seleccionás las piezas de Parmalat y usás arrange_grid_relative con "relative_to": "bbox_torrente" y "position": "above".

Reglas IMPORTANTES:

Usá SOLO IDs de piezas y assets que existan en el layout_state enviado.

NO cambies el tamaño de la hoja, NO borres piezas, NO cambies assets; sólo trabajá con selección, posición, distribución, alineación, duplicación y organización en grilla.

Si la instrucción es ambigua o no estás seguro, devolvé "actions": [] y explicá el motivo en "assistant_message".
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Estado actual del layout (JSON):\n" + json.dumps(layout_state)},
        {"role": "user", "content": user_message},
    ]

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            messages=messages,
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
    except Exception:
        current_app.logger.exception("Fallo en editor_chat con OpenAI")
        data = {
            "assistant_message": "Ocurrió un problema al comunicarse con la IA. No se aplicaron cambios.",
            "actions": [],
        }

    if "assistant_message" not in data:
        data["assistant_message"] = "Tengo una propuesta de cambios sobre el montaje."
    if "actions" not in data or not isinstance(data.get("actions"), list):
        data["actions"] = []

    return data

def _build_diseno_objs(disenos: List[Tuple[str, int]]) -> List[Diseno]:
    return [Diseno(ruta=path, cantidad=copias) for path, copias in disenos]


def _montaje_config_from_params(
    tamano_pliego: Tuple[float, float],
    params: Dict,
    **overrides,
) -> MontajeConfig:
    base_kwargs = {
        "tamano_pliego": tamano_pliego,
        "separacion": params.get("separacion"),
        "margen_izquierdo": params.get("margen_izq", 10.0),
        "margen_derecho": params.get("margen_der", 10.0),
        "margen_superior": params.get("margen_sup", 10.0),
        "margen_inferior": params.get("margen_inf", 10.0),
        "espaciado_horizontal": params.get("espaciado_horizontal", 0.0),
        "espaciado_vertical": params.get("espaciado_vertical", 0.0),
        "sangrado": params.get("sangrado"),
        "permitir_rotacion": params.get("permitir_rotacion", False),
        "ordenar_tamano": params.get("ordenar_tamano", False),
        "centrar": params.get("centrar", True),
        "alinear_filas": params.get("alinear_filas", False),
        "forzar_grilla": params.get("estrategia") == "grid",
        "filas_grilla": params.get("filas"),
        "columnas_grilla": params.get("columnas"),
        "ancho_grilla_mm": params.get("celda_ancho"),
        "alto_grilla_mm": params.get("celda_alto"),
        "pref_orientacion_horizontal": params.get("preferir_horizontal", False),
        "debug_grilla": params.get("debug_grilla", False),
        "pinza_mm": params.get("pinza_mm", 0.0),
        "lateral_mm": params.get("lateral_mm", 0.0),
        "marcas_registro": params.get("marcas_registro", False),
        "marcas_corte": params.get("marcas_corte", False),
        "cutmarks_por_forma": params.get("cutmarks_por_forma", False),
        "usar_trimbox": params.get("usar_trimbox", False),
        "estrategia": params.get("estrategia", "flujo"),
        "agregar_marcas": bool(
            params.get("marcas_registro") or params.get("marcas_corte")
        ),
        "export_compat": params.get("export_compat"),
    }
    base_kwargs.update(overrides)
    return MontajeConfig(**base_kwargs)


def _unpack_preview_result(res, preview_path, ancho_pliego, alto_pliego):
    """Adapta retornos posibles de ``realizar_montaje_inteligente``.

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

    modo_ia = "modo_ia" in req.form
    estrategia = req.form.get("estrategia", "flujo")
    if modo_ia:
        estrategia = "auto"
    elif req.form.get("forzar_grilla"):
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

    export_compat = req.form.get("export_compat")

    # Opciones de sangrado
    modo_sangrado = req.form.get("modo_sangrado", "original")
    sangrado_mm = 0.0
    usar_trimbox = False
    if modo_sangrado == "add":
        sangrado_mm = float(req.form.get("sangrado_add", 0) or 0)
    elif modo_sangrado == "replace":
        sangrado_mm = float(req.form.get("sangrado_replace", 0) or 0)
        usar_trimbox = True

    if modo_ia:
        ordenar_tamano = False
        alinear_filas = False
        preferir_horizontal = False
        filas = 0
        columnas = 0
        celda_ancho = 0.0
        celda_alto = 0.0
    elif estrategia == "flujo":
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
        "modo_ia": modo_ia,
        "export_compat": export_compat or None,
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
            modo_ia=False,
            layout_json_exists=False,
            job_id=None,
            pdf_url=None,
            ENABLE_POST_EDITOR=current_app.config.get("ENABLE_POST_EDITOR", False),
        )

    accion = request.form.get("accion") or "generar"
    mode = request.form.get("mode", "std")
    if mode != "pro":
        try:
            diseños, ancho_pliego, alto_pliego, params = _parse_montaje_offset_form(request)
            export_area_util = request.form.get("export_area_util") == "on"
            export_compat = request.form.get("export_compat")
            opciones_extra = {
                "export_area_util": export_area_util,
                "export_compat": (export_compat or None),
            }
        except Exception as e:
            return str(e), 400

        diseno_objs = _build_diseno_objs(diseños)
        tamano_pliego = (ancho_pliego, alto_pliego)

        if accion == "preview":
            previews_dir = os.path.join(current_app.static_folder, "previews")
            os.makedirs(previews_dir, exist_ok=True)
            job_id = str(uuid.uuid4())[:8]
            preview_path = os.path.join(
                previews_dir, f"offset_inteligente_{job_id}.png"
            )
            # NUEVO: generamos preview real y pedimos posiciones/sheet
            config = _montaje_config_from_params(
                tamano_pliego,
                params,
                es_pdf_final=False,
                preview_path=preview_path,
                devolver_posiciones=True,
                export_area_util=opciones_extra.get("export_area_util", False),
                export_compat=opciones_extra.get("export_compat"),
            )
            res = realizar_montaje_inteligente(diseno_objs, config)

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
                modo_ia=params.get("modo_ia", False),
                layout_json_exists=False,
                job_id=None,
                pdf_url=None,
                ENABLE_POST_EDITOR=current_app.config.get("ENABLE_POST_EDITOR", False),
            )

        modo_ia = bool(params.get("modo_ia"))
        output_path = os.path.join("output", "pliego_offset_inteligente.pdf")
        config = _montaje_config_from_params(
            tamano_pliego,
            params,
            es_pdf_final=True,
            output_path=output_path,
            devolver_posiciones=modo_ia,
            export_area_util=opciones_extra.get("export_area_util", False),
            export_compat=opciones_extra.get("export_compat"),
        )
        result_path = realizar_montaje_inteligente(diseno_objs, config)
        final_path = result_path if isinstance(result_path, str) else output_path

        if not modo_ia:
            return send_file(final_path, as_attachment=True)

        result_dict = result_path if isinstance(result_path, dict) else None
        if not result_dict:
            # Intentamos obtener posiciones en una segunda pasada si el backend no las devolvió
            config_pos = _montaje_config_from_params(
                tamano_pliego,
                params,
                es_pdf_final=False,
                devolver_posiciones=True,
                export_area_util=opciones_extra.get("export_area_util", False),
                export_compat=opciones_extra.get("export_compat"),
            )
            try:
                preview_res = realizar_montaje_inteligente(diseno_objs, config_pos)
                if isinstance(preview_res, dict):
                    result_dict = {
                        "positions": preview_res.get("positions"),
                        "sheet_mm": preview_res.get("sheet_mm"),
                    }
            except Exception:
                result_dict = None

        if not result_dict or not result_dict.get("positions"):
            return send_file(final_path, as_attachment=True)

        positions = result_dict.get("positions", [])
        sheet_info = result_dict.get("sheet_mm") or {}
        sheet_w = float(sheet_info.get("w", tamano_pliego[0]))
        sheet_h = float(sheet_info.get("h", tamano_pliego[1]))

        job_id = uuid.uuid4().hex[:12]
        job_dir = _job_dir(job_id)
        if not job_dir:
            return send_file(final_path, as_attachment=True)
        os.makedirs(job_dir, exist_ok=True)
        assets_dir = os.path.join(job_dir, ASSETS_DIRNAME)
        os.makedirs(assets_dir, exist_ok=True)

        design_records = []
        for idx, diseno in enumerate(diseno_objs):
            src_abs = diseno.ruta
            basename = os.path.basename(src_abs)
            safe_name = f"{idx:02d}_{basename}"
            dest_abs = os.path.join(assets_dir, safe_name)
            try:
                shutil.copy2(src_abs, dest_abs)
            except Exception:
                shutil.copy(src_abs, dest_abs)
            rel_path = os.path.relpath(dest_abs, job_dir).replace("\\", "/")
            design_records.append(
                {
                    "index": idx,
                    "cantidad": diseno.cantidad,
                    "src": rel_path,
                    "abs_src": dest_abs,
                    "original_src": src_abs,
                }
            )

        final_pdf_basename = ORIGINAL_PDF_NAME
        final_pdf_path = os.path.join(job_dir, final_pdf_basename)
        try:
            shutil.copy2(final_path, final_pdf_path)
        except Exception:
            shutil.copy(final_path, final_pdf_path)

        margins = {
            "top": float(config.margen_superior),
            "bottom": float(config.margen_inferior),
            "left": float(config.margen_izquierdo),
            "right": float(config.margen_derecho),
        }
        grid_data = {
            "enabled": bool(config.forzar_grilla),
            "rows": config.filas_grilla,
            "cols": config.columnas_grilla,
            "cell_w": config.ancho_grilla_mm,
            "cell_h": config.alto_grilla_mm,
        }
        bleed_mm = float(config.sangrado or 0.0)

        items = []
        for i, pos in enumerate(positions):
            idx = int(pos.get("file_idx", 0))
            if idx < 0 or idx >= len(design_records):
                continue
            record = design_records[idx]
            items.append(
                {
                    "id": f"item{i}",
                    "src": record["src"],
                    "page": 0,
                    "x_mm": float(pos.get("x_mm", 0.0)),
                    "y_mm": float(pos.get("y_mm", 0.0)),
                    "w_mm": float(pos.get("w_mm", 0.0)),
                    "h_mm": float(pos.get("h_mm", 0.0)),
                    "rotation": int(pos.get("rot_deg", 0)) % 360,
                    "flip_x": False,
                    "flip_y": False,
                    "file_idx": idx,
                }
            )

        # Guardamos un layout estructurado que describe el pliego y todas las piezas.
        # 1. ``realizar_montaje_inteligente`` genera el PDF base y expone ``positions``
        #    con coordenadas absolutas en mm.
        # 2. Aquí serializamos esas posiciones junto a los recursos copiados en
        #    ``static/ia_jobs/<job_id>/assets``.
        # 3. ``/editor`` carga ``layout.json`` y lo inyecta en la plantilla del editor
        #    para que el JavaScript pueda renderizar y editar las piezas sin volver a
        #    consultar al motor de montaje.
        layout_payload = {
            "version": 1,
            "job_id": job_id,
            "sheet": {
                "w_mm": sheet_w,
                "h_mm": sheet_h,
                "pinza_mm": float(config.pinza_mm or 0.0),
                "margins_mm": margins,
            },
            "grid_mm": grid_data,
            "bleed_mm": bleed_mm,
            "items": items,
            "assets": [
                {
                    "id": f"asset{rec['index']}",
                    "src": rec["src"],
                    "original_src": rec["original_src"],
                    "cantidad": rec["cantidad"],
                    "file_idx": rec["index"],
                }
                for rec in design_records
            ],
            "pdf_filename": final_pdf_basename,
            "preview_filename": EDITED_PREVIEW_NAME,
        }

        layout_path = _layout_path(job_dir)
        _save_json(layout_path, layout_payload)

        meta_payload = {
            "job_id": job_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sheet": layout_payload["sheet"],
            "grid_mm": grid_data,
            "bleed_mm": bleed_mm,
            "designs": [
                {
                    "index": rec["index"],
                    "cantidad": rec["cantidad"],
                    "src": rec["src"],
                    "abs_src": rec["abs_src"],
                    "original_src": rec["original_src"],
                }
                for rec in design_records
            ],
            "params": params,
            "options": opciones_extra,
            "pdf_filename": final_pdf_basename,
            "preview_filename": EDITED_PREVIEW_NAME,
        }
        _save_json(_meta_path(job_dir), meta_payload)

        pdf_rel = _job_relpath(job_id, final_pdf_basename)
        return render_template(
            "montaje_offset_inteligente.html",
            resultado={"pdf_url": url_for("static", filename=pdf_rel)},
            preview_url=None,
            resumen_html=None,
            modo_ia=True,
            layout_json_exists=True,
            job_id=job_id,
            pdf_url=url_for("static", filename=pdf_rel),
            ENABLE_POST_EDITOR=current_app.config.get("ENABLE_POST_EDITOR", False),
        )

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
            diseno_objs = _build_diseno_objs(diseños)
            config = _montaje_config_from_params(
                (ancho_pliego, alto_pliego),
                params,
                es_pdf_final=False,
                export_area_util=opciones_extra.get("export_area_util", False),
            )
            png_bytes, resumen_html = realizar_montaje_inteligente(diseno_objs, config)
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
    payload = request.get_json(silent=True) or {}
    positions = payload.get("positions", [])
    if not isinstance(positions, list):
        return _json_error("'positions' debe ser una lista.")

    positions = [p for p in positions if p and isinstance(p, dict)]
    if not positions:
        return _json_error("No hay posiciones válidas para aplicar.")

    diseños = [(ruta, 1) for ruta in _resolve_uploads()]
    diseno_objs = _build_diseno_objs(diseños)
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

    export_compat = payload.get("export_compat")

    try:
        config = _montaje_config_from_params(
            (w_mm, h_mm),
            {},
            sangrado=sangrado,
            es_pdf_final=False,
            modo_manual=True,
            posiciones_manual=positions,
            preview_path=preview_path,
            export_compat=export_compat,
        )
        res = realizar_montaje_inteligente(diseno_objs, config)
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
    payload = request.get_json(silent=True) or {}
    positions = payload.get("positions", [])
    if not isinstance(positions, list):
        return _json_error("'positions' debe ser una lista.")

    positions = [p for p in positions if p and isinstance(p, dict)]
    if not positions:
        return _json_error("No hay posiciones válidas para aplicar.")

    diseños = [(ruta, 1) for ruta in _resolve_uploads()]
    diseno_objs = _build_diseno_objs(diseños)
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

    export_compat = payload.get("export_compat")

    try:
        config = _montaje_config_from_params(
            (w_mm, h_mm),
            {},
            sangrado=sangrado,
            es_pdf_final=True,
            modo_manual=True,
            posiciones_manual=positions,
            output_path=pdf_path,
            export_compat=export_compat,
        )
        result_path = realizar_montaje_inteligente(diseno_objs, config)
        final_pdf = result_path if isinstance(result_path, str) else pdf_path
        if not os.path.exists(final_pdf):
            return _json_error("El motor no generó el PDF.", 500)
        rel = os.path.relpath(final_pdf, current_app.static_folder).replace("\\", "/")
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
    material_coeffs = obtener_coeficientes_material()
    material_coef = coeficiente_material(material_norm)
    if material_coef is None:
        material_coef = material_coeffs.get("default")

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
            None,
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

        channel_names = {"C": "Cian", "M": "Magenta", "Y": "Amarillo", "K": "Negro"}

        diagnostico_json = dict(analisis_detallado.get("diagnostico_json") or {})

        def _as_number(valor):
            if valor is None:
                return None
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(numero):
                return None
            return numero

        raw_cobertura = diagnostico_json.get("cobertura_por_canal")
        if not raw_cobertura:
            raw_cobertura = analisis_detallado.get("cobertura_por_canal")
        cobertura_letras = (
            normalizar_coberturas(raw_cobertura)
            if isinstance(raw_cobertura, dict)
            else {}
        )
        cobertura_letras = {
            letra: round(valor, 2)
            for letra, valor in cobertura_letras.items()
            if letra in channel_names
        }
        if cobertura_letras:
            for letra in channel_names:
                cobertura_letras.setdefault(letra, 0.0)
            cobertura_sum = round(sum(cobertura_letras.values()), 2)
        else:
            cobertura_sum = None
        cobertura_por_canal = {
            channel_names[letra]: cobertura_letras.get(letra, 0.0)
            for letra in channel_names
        }

        tac_total_v2_val = _as_number(diagnostico_json.get("tac_total_v2"))
        if tac_total_v2_val is None:
            tac_total_v2_val = _as_number(analisis_detallado.get("tac_total_v2"))
        if tac_total_v2_val is not None:
            tac_total_v2_val = round(tac_total_v2_val, 2)

        tac_total_val = _as_number(diagnostico_json.get("tac_total"))
        if tac_total_val is None:
            tac_total_val = _as_number(analisis_detallado.get("tac_total"))
        if tac_total_val is None:
            tac_total_val = tac_total_v2_val
        if tac_total_val is None and cobertura_sum is not None:
            tac_total_val = cobertura_sum

        tac_p95_val = _as_number(diagnostico_json.get("tac_p95"))
        if tac_p95_val is None:
            tac_p95_val = _as_number(analisis_detallado.get("tac_p95"))
        if tac_p95_val is not None:
            tac_p95_val = round(tac_p95_val, 2)

        tac_max_val = _as_number(diagnostico_json.get("tac_max"))
        if tac_max_val is None:
            tac_max_val = _as_number(analisis_detallado.get("tac_max"))
        if tac_max_val is not None:
            tac_max_val = round(tac_max_val, 2)

        cobertura_total_val = _as_number(diagnostico_json.get("cobertura_total"))
        if cobertura_total_val is None:
            cobertura_total_val = _as_number(analisis_detallado.get("cobertura_total"))
        if cobertura_total_val is not None:
            cobertura_total_val = round(cobertura_total_val, 2)

        final_pdf_path = os.path.join(rev_dir, f"{revision_id}.pdf")
        shutil.copy(save_path, final_pdf_path)
        pdf_rel = os.path.relpath(final_pdf_path, current_app.static_folder)

        diagnostico_json.update(
            {
                "archivo": secure_filename(file.filename),
                "pdf_path": pdf_rel,
                "anilox_lpi": anilox_lpi,
                "anilox_bcm": anilox_bcm,
                "paso": paso_mm,
                "paso_cilindro": paso_mm,
                "paso_del_cilindro": paso_mm,
                "material": material_norm,
                "coef_material": material_coef,
                "velocidad_impresion": velocidad,
                "ancho_mm": round(ancho_mm, 2) if ancho_mm else 0.0,
                "alto_mm": round(alto_mm, 2) if alto_mm else 0.0,
                "ancho_util_m": diagnostico_json.get("ancho_util_m")
                or (round(ancho_mm / 1000.0, 4) if ancho_mm else 0.0),
                "advertencias_resumen": advertencias_resumen_txt,
                "indicadores_advertencias": advertencias_stats,
                "advertencias_total": advertencias_stats.get("total", 0),
                "tiene_tramas_debiles": advertencias_stats.get("hay_tramas_debiles", False),
                "tiene_overprint": advertencias_stats.get("hay_overprint", False),
                "tiene_texto_pequeno": advertencias_stats.get("hay_texto_pequeno", False),
                "conteo_overprint": advertencias_stats.get("conteo_overprint", 0),
                "conteo_tramas": advertencias_stats.get("conteo_tramas", 0),
            }
        )
        diagnostico_json["cobertura_por_canal"] = (
            cobertura_letras if cobertura_letras else None
        )
        diagnostico_json["cobertura"] = cobertura_letras if cobertura_letras else None
        diagnostico_json["cobertura_total"] = cobertura_total_val
        diagnostico_json["tac_total_v2"] = tac_total_v2_val
        diagnostico_json["tac_p95"] = tac_p95_val
        diagnostico_json["tac_max"] = tac_max_val
        diagnostico_json["tac_total"] = tac_total_val
        diagnostico_json["cobertura_estimada"] = tac_total_val
        diagnostico_json["cobertura_base_sum"] = tac_total_val
        diagnostico_json.setdefault("tinta_ml_min", diagnostico_json.get("tinta_ml_min"))
        diagnostico_json.setdefault(
            "tinta_por_canal_ml_min", diagnostico_json.get("tinta_por_canal_ml_min")
        )
        diagnostico_json.setdefault("lpi", diagnostico_json.get("anilox_lpi"))
        diagnostico_json.setdefault("bcm", diagnostico_json.get("anilox_bcm"))
        diagnostico_json.setdefault(
            "paso",
            diagnostico_json.get("paso_del_cilindro")
            or diagnostico_json.get("paso_cilindro"),
        )
        diagnostico_json.setdefault(
            "velocidad", diagnostico_json.get("velocidad_impresion")
        )

        diagnostico_json = inyectar_parametros_simulacion(
            diagnostico_json, parametros_maquina
        )
        for clave in (
            "tac_total_v2",
            "tac_total",
            "cobertura_estimada",
            "cobertura_base_sum",
            "cobertura_por_canal",
        ):
            diagnostico_json.setdefault(clave, diagnostico_json.get(clave))

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
                "cobertura": tac_total_val,
                "advertencias": overlay_info.get("advertencias", []),
            },
            "overlay_path": overlay_info["overlay_path"],
            "dpi": overlay_info["dpi"],
            "advertencias_resumen": advertencias_resumen_txt,
            "indicadores_advertencias": advertencias_stats,
            "cobertura_por_canal": cobertura_por_canal if cobertura_por_canal else None,
            "cobertura_total": cobertura_total_val,
            "tac_total": tac_total_val,
            "tac_total_v2": tac_total_v2_val,
            "tac_p95": tac_p95_val,
            "tac_max": tac_max_val,
            "ancho_mm": ancho_mm,
            "alto_mm": alto_mm,
            "coef_material": material_coef,
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
            "tac_total_v2": tac_total_v2_val,
            "tac_p95": tac_p95_val,
            "tac_max": tac_max_val,
            # Persistir la ruta web de la imagen del diagnóstico con advertencias.
            # Se usará como base de la simulación avanzada y permite que, al
            # recargar la página de resultados, el canvas dibuje de inmediato la
            # misma imagen analizada.
            "diag_img_web": imagen_iconos_rel,
            "material_coeficiente": material_coef,
            "material_coefficients": material_coeffs,
            "cobertura_total": cobertura_total_val,
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
        USE_PIPELINE_V2=current_app.config.get("USE_PIPELINE_V2", True),
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

    diag_json = datos.get("diagnostico_json")
    if not isinstance(diag_json, dict):
        diag_json = {}
        datos["diagnostico_json"] = diag_json
    else:
        diag_json.setdefault("lpi", diag_json.get("anilox_lpi"))
        diag_json.setdefault("bcm", diag_json.get("anilox_bcm"))
        diag_json.setdefault(
            "paso",
            diag_json.get("paso_del_cilindro") or diag_json.get("paso_cilindro"),
        )
        diag_json.setdefault("velocidad", diag_json.get("velocidad_impresion"))
        for clave in (
            "tac_total_v2",
            "tac_total",
            "cobertura_estimada",
            "cobertura_base_sum",
            "cobertura_por_canal",
        ):
            diag_json.setdefault(clave, diag_json.get(clave))

    material_coeffs = obtener_coeficientes_material()
    if "material_coefficients" not in datos:
        datos["material_coefficients"] = material_coeffs

    material_nombre = diag_json.get("material") if isinstance(diag_json, dict) else ""
    if not material_nombre:
        material_nombre = datos.get("material") or ""

    coef_actual = diag_json.get("coef_material") if isinstance(diag_json, dict) else None
    if coef_actual is None:
        coef_actual = coeficiente_material(material_nombre)
        if coef_actual is None:
            coef_actual = material_coeffs.get("default")
        if isinstance(diag_json, dict):
            diag_json["coef_material"] = coef_actual

    if datos.get("material_coeficiente") is None:
        datos["material_coeficiente"] = coef_actual

    return render_template(
        "resultado_flexo.html",
        **datos,
        revision_id=revision_id,
        sim_base_img=datos.get("diag_img_web"),
        USE_PIPELINE_V2=current_app.config.get("USE_PIPELINE_V2", True),
    )


@routes_bp.route("/simulacion/exportar/<revision_id>", methods=["POST"])
def exportar_simulacion(revision_id):
    """Genera el PNG final de la simulación en memoria y lo devuelve como descarga."""

    def _as_number(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return None
            return float(value)
        if isinstance(value, str):
            texto = value.strip().replace(",", ".")
            if not texto:
                return None
            try:
                return float(texto)
            except ValueError:
                return None
        return None

    def _resolve_value(diag, keys):
        for key in keys:
            if isinstance(diag, dict) and key in diag:
                val = _as_number(diag.get(key))
                if val is not None:
                    return val
        return None

    def _parse_coverage_base(diag):
        channel_names = {"C": "Cyan", "M": "Magenta", "Y": "Amarillo", "K": "Negro"}
        base = {canal: 0.0 for canal in "CMYK"}
        cobertura = diag.get("cobertura") if isinstance(diag, dict) else {}
        por_nombre = diag.get("cobertura_por_canal") if isinstance(diag, dict) else {}
        base_sum = 0.0
        for canal in "CMYK":
            valor = _as_number(cobertura.get(canal) if isinstance(cobertura, dict) else None)
            if valor is None and isinstance(por_nombre, dict):
                valor = _as_number(por_nombre.get(channel_names[canal]))
            if valor is None:
                valor = 0.0
            base[canal] = max(0.0, valor)
            base_sum += base[canal]
        fallback = _as_number(diag.get("tac_total") if isinstance(diag, dict) else None)
        if fallback is None:
            fallback = _as_number(diag.get("cobertura_estimada") if isinstance(diag, dict) else None)
        if fallback is None:
            fallback = _as_number(diag.get("cobertura") if isinstance(diag, dict) else None)
        if base_sum <= 0 and fallback:
            per = fallback / 4.0
            for canal in "CMYK":
                base[canal] = max(0.0, per)
            base_sum = fallback
        return base, base_sum, fallback or 0.0

    def _scale_coverage(base_tuple, slider_value):
        base, base_sum, fallback = base_tuple
        values = dict(base)
        factor = 1.0
        slider = _as_number(slider_value)
        if slider is not None:
            if base_sum > 0:
                factor = slider / base_sum if base_sum else 1.0
            elif slider > 0:
                per = slider / 4.0
                for canal in "CMYK":
                    values[canal] = per
                factor = 1.0
        scaled = {canal: max(0.0, min(120.0, values[canal] * factor)) for canal in "CMYK"}
        total = sum(scaled.values())
        return scaled, total

    def _cmyk_to_rgb(c, m, y, k):
        r = int(round(255 * (1 - c) * (1 - k)))
        g = int(round(255 * (1 - m) * (1 - k)))
        b = int(round(255 * (1 - y) * (1 - k)))
        return max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))

    revision = (revision_id or "").strip()
    if not revision or revision.lower() in {"actual", "undefined", "null"}:
        revision = session.get("revision_flexo_id")
    if not revision:
        return jsonify({"error": "No se encontró la revisión solicitada."}), 404

    res_json_path = os.path.join(current_app.static_folder, "uploads", revision, "res.json")
    try:
        with open(res_json_path, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        current_app.logger.error("REV FLEXO: resultados faltantes en %s", res_json_path)
        return jsonify({"error": "Los datos de la simulación ya no están disponibles."}), 404
    except json.JSONDecodeError:
        current_app.logger.exception("REV FLEXO: resultados corruptos en %s", res_json_path)
        return jsonify({"error": "No se pudieron leer los datos guardados de la simulación."}), 500

    payload = request.get_json(silent=True) or {}
    diagnostico = datos.get("diagnostico_json") if isinstance(datos, dict) else {}

    lpi = _as_number(payload.get("lpi"))
    if lpi is None:
        lpi = _resolve_value(diagnostico, ["anilox_lpi", "lpi"])
    bcm = _as_number(payload.get("bcm"))
    if bcm is None:
        bcm = _resolve_value(diagnostico, ["anilox_bcm", "bcm"])
    paso = _as_number(payload.get("paso"))
    if paso is None:
        paso = _resolve_value(diagnostico, ["paso_del_cilindro", "paso_cilindro", "paso"])
    velocidad = _as_number(payload.get("velocidad"))
    if velocidad is None:
        velocidad = _resolve_value(diagnostico, ["velocidad_impresion", "velocidad"])

    cobertura_mapa = {}
    cobertura_payload = payload.get("cobertura")
    if isinstance(cobertura_payload, dict):
        for canal in "CMYK":
            valor = _as_number(cobertura_payload.get(canal))
            cobertura_mapa[canal] = max(0.0, valor or 0.0)

    cobertura_total = sum(cobertura_mapa.values())
    if cobertura_total <= 0:
        cobertura_base = _parse_coverage_base(diagnostico)
        cobertura_mapa, cobertura_total = _scale_coverage(
            cobertura_base, payload.get("tacObjetivo")
        )

    base_rel = (
        datos.get("diag_base_web")
        or datos.get("diag_img_web")
        or datos.get("imagen_iconos_web")
        or datos.get("imagen_path_web")
    )
    base_rel = (base_rel or "").lstrip("/\\")
    base_path = os.path.join(current_app.static_folder, base_rel) if base_rel else None

    try:
        if base_path and os.path.exists(base_path):
            base_image = Image.open(base_path).convert("RGBA")
        else:
            raise FileNotFoundError(base_path or "")
    except FileNotFoundError:
        current_app.logger.warning("REV FLEXO: imagen base no encontrada en %s", base_path)
        base_image = Image.new("RGBA", (1600, 1200), (238, 247, 255, 255))
    except Exception:  # pragma: no cover - protección ante imágenes corruptas
        current_app.logger.exception("REV FLEXO: error abriendo imagen base %s", base_path)
        base_image = Image.new("RGBA", (1600, 1200), (238, 247, 255, 255))

    width, height = base_image.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    if cobertura_total > 0 and width > 0 and height > 0:
        lpi_val = lpi or 0.0
        spacing_raw = max(2.5, (540.0 / max(lpi_val or 0.0, 40.0)) * 3.0)
        spacing = max(6.0, spacing_raw)
        bcm_factor = min(1.2, (bcm or 0.0) / 12.0)
        coverage_factor = max(0.05, min(1.0, cobertura_total / 300.0))
        density = min(0.9, 0.12 + coverage_factor * (0.6 + bcm_factor))
        offset = ((paso or 0.0) % spacing) / 2.0 if spacing else 0.0
        c_val = min(1.0, (cobertura_mapa.get("C", 0.0) or 0.0) / 100.0)
        m_val = min(1.0, (cobertura_mapa.get("M", 0.0) or 0.0) / 100.0)
        y_val = min(1.0, (cobertura_mapa.get("Y", 0.0) or 0.0) / 100.0)
        k_val = min(1.0, (cobertura_mapa.get("K", 0.0) or 0.0) / 100.0)
        rgb = _cmyk_to_rgb(c_val, m_val, y_val, k_val)
        radius_base = max(1.2, (spacing / 2.0) * min(0.85, 0.25 + coverage_factor))
        radius = min(radius_base, spacing * 0.48)
        rotation_rad = math.sin((paso or 0.0) / 90.0)
        rotation_deg = math.degrees(rotation_rad)

        tile_size = max(8, int(round(spacing)))
        tile_size = max(tile_size, int(math.ceil(radius * 2 + 4)))
        dot = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
        draw_dot = ImageDraw.Draw(dot)
        radius_y = radius * 0.82
        cx = tile_size / 2.0
        cy = tile_size / 2.0
        bbox = (cx - radius, cy - radius_y, cx + radius, cy + radius_y)
        draw_dot.ellipse(
            bbox,
            fill=(rgb[0], rgb[1], rgb[2], int(round(density * 255))),
        )
        if rotation_deg:
            dot = dot.rotate(rotation_deg, resample=Image.BICUBIC, expand=True)

        tile = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
        paste_x = tile_size // 2 - dot.width // 2
        paste_y = tile_size // 2 - dot.height // 2
        tile.paste(dot, (paste_x, paste_y), dot)

        pattern_width = width + tile_size * 2
        pattern_height = height + tile_size * 2
        tiled = Image.new("RGBA", (pattern_width, pattern_height), (0, 0, 0, 0))
        for pos_y in range(0, pattern_height, tile_size):
            for pos_x in range(0, pattern_width, tile_size):
                tiled.paste(tile, (pos_x, pos_y), tile)

        offset_px = int(round(offset % tile_size)) if tile_size else 0
        pattern_cropped = tiled.crop(
            (offset_px, offset_px, offset_px + width, offset_px + height)
        )
        overlay.paste(pattern_cropped, (0, 0), pattern_cropped)

        shadow_alpha = max(0.0, min(1.0, density * 0.3))
        if shadow_alpha > 0:
            shadow = Image.new(
                "RGBA", (width, height), (20, 40, 60, int(round(shadow_alpha * 255)))
            )
            overlay.paste(shadow, (0, 0), shadow)

    advertencias = datos.get("advertencias_iconos") if isinstance(datos, dict) else []
    if isinstance(advertencias, list) and advertencias:
        warning_colors = {
            "texto_pequeno": {"stroke": (220, 53, 69, 230), "fill": (220, 53, 69, 46)},
            "trama_debil": {"stroke": (128, 0, 128, 230), "fill": (128, 0, 128, 46)},
            "imagen_baja": {"stroke": (255, 140, 0, 230), "fill": (255, 140, 0, 46)},
            "overprint": {"stroke": (0, 123, 255, 230), "fill": (0, 123, 255, 46)},
            "sin_sangrado": {"stroke": (0, 150, 0, 230), "fill": (0, 150, 0, 46)},
            "default": {"stroke": (255, 193, 7, 230), "fill": (255, 193, 7, 46)},
        }
        draw_overlay = ImageDraw.Draw(overlay)
        line_width = max(2, int(round(2)))
        for adv in advertencias:
            bbox = None
            if isinstance(adv, dict):
                bbox = adv.get("bbox") or adv.get("box")
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                continue
            try:
                x0, y0, x1, y1 = [float(v) for v in bbox]
            except (TypeError, ValueError):
                continue
            tipo_raw = str(adv.get("tipo") or adv.get("type") or "").lower()
            tipo = "trama_debil" if tipo_raw.startswith("trama") else tipo_raw
            colores = warning_colors.get(tipo, warning_colors["default"])
            draw_overlay.rectangle(
                [(x0, y0), (x1, y1)],
                fill=colores["fill"],
                outline=colores["stroke"],
                width=line_width,
            )

    resultado = base_image.convert("RGBA")
    resultado.paste(overlay, (0, 0), overlay)

    output = io.BytesIO()
    resultado.save(output, format="PNG")
    output.seek(0)

    safe_revision = secure_filename(str(revision)) or "resultado"
    filename = f"sim_{safe_revision}.png"
    return send_file(
        output,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename,
    )


@routes_bp.route("/layout/<job_id>.json")
def obtener_layout_job(job_id: str):
    if not _post_editor_enabled():
        abort(404)
    job_dir = _job_dir(job_id)
    if not job_dir or not os.path.isdir(job_dir):
        abort(404)
    layout_path = _layout_path(job_dir)
    if not os.path.exists(layout_path):
        abort(404)
    try:
        data = _load_json(layout_path)
    except Exception:
        abort(404)
    return jsonify(data)


@routes_bp.route("/editor")
def editor():
    """Renderiza el editor post-imposición con el layout precargado."""
    if not _post_editor_enabled():
        abort(404)
    job_id = request.args.get("id")
    job_dir = _job_dir(job_id)
    if not job_id or not job_dir or not os.path.isdir(job_dir):
        abort(404)

    layout_path = _layout_path(job_dir)
    if not os.path.exists(layout_path):
        abort(404)

    try:
        layout_payload = _load_json(layout_path)
    except Exception:
        abort(404)

    return render_template(
        "editor_post_imposicion.html",
        job_id=job_id,
        layout=layout_payload,
        ENABLE_POST_EDITOR=True,
    )


@routes_bp.route("/editor_chat/<job_id>", methods=["POST"])
def editor_chat(job_id: str):
    if not _post_editor_enabled():
        abort(404)
    job_dir = _job_dir(job_id)
    if not job_dir or not os.path.isdir(job_dir):
        return _json_error("Trabajo no encontrado", 404)

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    layout_state = data.get("layout_state", {})

    response_obj = call_openai_for_editor_chat(user_message, layout_state, job_id)
    return jsonify(response_obj)


def _sanitize_layout_items(job_id: str, job_dir: str, meta: Dict, items: List[Dict]):
    sheet_info = meta.get("sheet") or {}
    margins = sheet_info.get("margins_mm", {})
    pinza_mm = float(sheet_info.get("pinza_mm", 0.0))
    sheet_w = float(sheet_info.get("w_mm", 0.0))
    sheet_h = float(sheet_info.get("h_mm", 0.0))
    if sheet_w <= 0 or sheet_h <= 0:
        raise ValueError("Dimensiones de pliego inválidas en metadatos")

    left_margin = float(margins.get("left", 0.0))
    right_margin = float(margins.get("right", 0.0))
    top_margin = float(margins.get("top", 0.0))
    bottom_margin = float(margins.get("bottom", 0.0)) + pinza_mm

    designs_meta = meta.get("designs", [])
    design_by_src = {d.get("src"): d for d in designs_meta}
    if not design_by_src:
        raise ValueError("Metadatos del trabajo incompletos")

    sanitized = []
    posiciones_manual = []
    counts = Counter()

    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("Cada item debe ser un objeto")
        src_rel = raw.get("src")
        if not isinstance(src_rel, str):
            raise ValueError("Cada item necesita un 'src'")
        record = design_by_src.get(src_rel)
        if not record:
            raise ValueError(f"Recurso no permitido: {src_rel}")
        abs_src = os.path.normpath(os.path.join(job_dir, record.get("src", "")))
        try:
            common = os.path.commonpath([abs_src, os.path.normpath(job_dir)])
        except ValueError:
            common = ""
        if common != os.path.normpath(job_dir):
            raise ValueError("Ruta de recurso fuera del directorio del trabajo")
        if not os.path.exists(abs_src):
            raise ValueError(f"El recurso no existe en el servidor: {src_rel}")

        try:
            x_mm = float(raw.get("x_mm"))
            y_mm = float(raw.get("y_mm"))
            w_mm = float(raw.get("w_mm"))
            h_mm = float(raw.get("h_mm"))
        except Exception as exc:
            raise ValueError("Coordenadas inválidas en layout") from exc

        if w_mm <= 0 or h_mm <= 0:
            raise ValueError("El ancho/alto debe ser mayor que cero")

        rotation = int(raw.get("rotation", 0)) % 360
        if rotation not in (0, 90, 180, 270):
            raise ValueError("La rotación debe ser 0, 90, 180 o 270")

        eps = 1e-6
        if x_mm < left_margin - eps or y_mm < bottom_margin - eps:
            raise ValueError("Una pieza está fuera de los márgenes permitidos")
        if x_mm + w_mm > sheet_w - right_margin + eps:
            raise ValueError("Una pieza excede el ancho disponible")
        if y_mm + h_mm > sheet_h - top_margin + eps:
            raise ValueError("Una pieza excede el alto disponible")

        sanitized.append(
            {
                "id": raw.get("id") or f"item{len(sanitized)}",
                "src": src_rel,
                "page": int(raw.get("page", 0)),
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": w_mm,
                "h_mm": h_mm,
                "rotation": rotation,
                "flip_x": bool(raw.get("flip_x", False)),
                "flip_y": bool(raw.get("flip_y", False)),
                "file_idx": int(record.get("index", 0)),
            }
        )
        posiciones_manual.append(
            {
                "file_idx": int(record.get("index", 0)),
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": w_mm,
                "h_mm": h_mm,
                "rot_deg": rotation,
            }
        )
        counts[int(record.get("index", 0))] += 1

    expected = {int(d.get("index", 0)): int(d.get("cantidad", 0)) for d in designs_meta}
    for idx, total in expected.items():
        if counts.get(idx, 0) != total:
            raise ValueError(
                f"La cantidad de piezas para el diseño {idx} no coincide con el montaje original"
            )

    for i, a in enumerate(sanitized):
        ax1, ay1 = a["x_mm"], a["y_mm"]
        ax2, ay2 = ax1 + a["w_mm"], ay1 + a["h_mm"]
        for b in sanitized[i + 1 :]:
            bx1, by1 = b["x_mm"], b["y_mm"]
            bx2, by2 = bx1 + b["w_mm"], by1 + b["h_mm"]
            if ax1 >= bx2 - eps or bx1 >= ax2 - eps:
                continue
            if ay1 >= by2 - eps or by1 >= ay2 - eps:
                continue
            raise ValueError("Hay piezas solapadas en el layout propuesto")

    return sanitized, posiciones_manual


@routes_bp.route("/layout/<job_id>/apply", methods=["POST"])
def aplicar_layout_job(job_id: str):
    if not _post_editor_enabled():
        abort(404)
    job_dir = _job_dir(job_id)
    if not job_dir or not os.path.isdir(job_dir):
        return _json_error("Trabajo no encontrado", 404)
    meta = _load_job_meta(job_dir)
    if not meta:
        return _json_error("Metadatos del trabajo no disponibles", 404)

    payload = request.get_json(silent=True) or {}
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return _json_error("'items' debe ser una lista con elementos")

    try:
        sanitized_items, posiciones_manual = _sanitize_layout_items(job_id, job_dir, meta, items)
    except ValueError as exc:
        return _json_error(str(exc))

    options = meta.get("options", {})
    params = meta.get("params", {})
    sheet_info = meta.get("sheet") or {}
    sheet_w = float(sheet_info.get("w_mm", 0))
    sheet_h = float(sheet_info.get("h_mm", 0))
    if sheet_w <= 0 or sheet_h <= 0:
        return _json_error("Metadatos del pliego inválidos")

    designs_meta = meta.get("designs", [])
    if not designs_meta:
        return _json_error("Diseños originales no disponibles")

    designs_tuples: List[Tuple[str, int]] = []
    for d in designs_meta:
        abs_src = d.get("abs_src")
        qty = int(d.get("cantidad", 0))
        if not abs_src or not os.path.exists(abs_src):
            return _json_error("Alguno de los archivos del trabajo ya no está disponible")
        designs_tuples.append((abs_src, qty))

    diseno_objs = _build_diseno_objs(designs_tuples)

    pdf_path = os.path.join(job_dir, EDITED_PDF_NAME)
    preview_path = os.path.join(job_dir, EDITED_PREVIEW_NAME)

    config = _montaje_config_from_params(
        (sheet_w, sheet_h),
        params,
        es_pdf_final=True,
        output_path=pdf_path,
        posiciones_manual=posiciones_manual,
        modo_manual=True,
        export_area_util=options.get("export_area_util", False),
        export_compat=options.get("export_compat"),
    )

    try:
        result_pdf = realizar_montaje_inteligente(diseno_objs, config)
    except Exception as exc:
        current_app.logger.exception("Fallo al regenerar montaje IA editado")
        return _json_error(f"No se pudo generar el PDF editado: {str(exc)}")

    final_pdf_path = result_pdf if isinstance(result_pdf, str) else pdf_path

    try:
        generar_preview_pliego(
            disenos=designs_tuples,
            positions=[
                {
                    "file_idx": item["file_idx"],
                    "x_mm": item["x_mm"],
                    "y_mm": item["y_mm"],
                    "w_mm": item["w_mm"],
                    "h_mm": item["h_mm"],
                    "rot_deg": item["rotation"],
                }
                for item in sanitized_items
            ],
            hoja_ancho_mm=sheet_w,
            hoja_alto_mm=sheet_h,
            preview_path=preview_path,
        )
    except Exception as exc:
        current_app.logger.warning("No se pudo regenerar preview editado: %s", exc)

    layout_payload = {
        "version": int(payload.get("version", 1)),
        "job_id": job_id,
        "sheet": sheet_info,
        "grid_mm": meta.get("grid_mm"),
        "bleed_mm": meta.get("bleed_mm"),
        "items": sanitized_items,
        "assets": [
            {
                "id": f"asset{d.get('index')}",
                "src": d.get("src"),
                "original_src": d.get("original_src"),
                "cantidad": d.get("cantidad"),
                "file_idx": d.get("index"),
            }
            for d in designs_meta
        ],
        "pdf_filename": meta.get("edited_pdf_filename") or meta.get("pdf_filename") or EDITED_PDF_NAME,
        "preview_filename": EDITED_PREVIEW_NAME,
    }
    _save_json(_layout_path(job_dir), layout_payload)

    meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
    meta["edited_pdf_filename"] = EDITED_PDF_NAME
    meta["preview_filename"] = EDITED_PREVIEW_NAME
    _save_json(_meta_path(job_dir), meta)

    pdf_rel = _job_relpath(job_id, EDITED_PDF_NAME)
    preview_rel = _job_relpath(job_id, EDITED_PREVIEW_NAME)

    return jsonify(
        {
            "ok": True,
            "pliego": pdf_rel,
            "preview": preview_rel,
            "pdf_url": url_for("static", filename=pdf_rel),
            "preview_url": url_for("static", filename=preview_rel),
        }
    )


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
