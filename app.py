from flask import Flask

from routes import routes_bp

app = Flask(__name__)
app.config.from_object("config")
app.register_blueprint(routes_bp)

