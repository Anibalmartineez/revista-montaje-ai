import os
from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from routes import routes_bp

app = Flask(__name__)
app.config.from_object("config")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
os.makedirs(os.path.join(app.static_folder, "previews"), exist_ok=True)


@app.errorhandler(RequestEntityTooLarge)
def handle_413(e):
    return jsonify(ok=False, error="Payload demasiado grande."), 413


app.register_blueprint(routes_bp)

