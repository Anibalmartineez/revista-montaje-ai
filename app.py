import os
from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from routes import routes_bp

app = Flask(__name__)
app.config.from_object("config")
app.config.setdefault("MAX_CONTENT_LENGTH", 32 * 1024 * 1024)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
os.makedirs(os.path.join(app.static_folder, "previews"), exist_ok=True)
os.makedirs(os.path.join(app.static_folder, "outputs"), exist_ok=True)


@app.errorhandler(RequestEntityTooLarge)
def handle_413(e):
    return jsonify(
        ok=False,
        error="Payload demasiado grande. Reduce DPI o cantidad de archivos.",
    ), 413


app.register_blueprint(routes_bp)

