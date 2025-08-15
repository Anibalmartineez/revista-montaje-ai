import os
from flask import Flask

from routes import routes_bp

app = Flask(__name__)
app.config.from_object("config")
os.makedirs(os.path.join(app.static_folder, "previews"), exist_ok=True)
app.register_blueprint(routes_bp)

