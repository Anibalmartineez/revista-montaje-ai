from dotenv import load_dotenv
load_dotenv()
import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

from routes import routes_bp
from pdf_medidor_pro.api import pdf_medidor_pro_bp
from sistema_presupuesto.api import presupuesto_api_bp

app = Flask(__name__)
app.config.from_object("config")
app.config.setdefault("MAX_CONTENT_LENGTH", 32 * 1024 * 1024)
PRESUPUESTO_MODULE_ROOT = Path(__file__).resolve().parent / "sistema_presupuesto"
PRESUPUESTO_FRONTEND_DIR = PRESUPUESTO_MODULE_ROOT / "frontend"
PRESUPUESTO_TEMPLATE_PATH = PRESUPUESTO_FRONTEND_DIR / "templates" / "presupuesto_offset_app.html"
PRESUPUESTO_STATIC_DIR = PRESUPUESTO_FRONTEND_DIR / "static"
app.config.setdefault("SISTEMA_PRESUPUESTO_DATA_DIR", str(PRESUPUESTO_MODULE_ROOT / "data"))
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["USE_PIPELINE_V2"] = os.getenv("USE_PIPELINE_V2", "false").lower() in (
    "1",
    "true",
    "yes",
    "y",
)
os.makedirs(os.path.join(app.static_folder, "previews"), exist_ok=True)
os.makedirs(os.path.join(app.static_folder, "outputs"), exist_ok=True)


@app.errorhandler(RequestEntityTooLarge)
def handle_413(e):
    return jsonify(
        ok=False,
        error="Payload demasiado grande. Reduce DPI o cantidad de archivos.",
    ), 413


@app.get("/sistema-presupuesto")
def sistema_presupuesto_ui():
    html = PRESUPUESTO_TEMPLATE_PATH.read_text(encoding="utf-8")
    return render_template_string(html)


@app.get("/sistema-presupuesto/static/<path:filename>")
def presupuesto_static(filename):
    return send_from_directory(PRESUPUESTO_STATIC_DIR, filename)


app.register_blueprint(routes_bp)
if pdf_medidor_pro_bp.name not in app.blueprints:
    app.register_blueprint(pdf_medidor_pro_bp)
if presupuesto_api_bp.name not in app.blueprints:
    app.register_blueprint(presupuesto_api_bp)
app.add_url_rule('/revision', endpoint='revision', view_func=app.view_functions['routes.revision'])

if __name__ == "__main__":
    app.run(debug=True)

