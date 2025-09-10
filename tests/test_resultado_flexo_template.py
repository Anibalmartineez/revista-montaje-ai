from flask import Flask, render_template
from pathlib import Path


def test_default_warning_message_in_template():
    base_path = Path(__file__).resolve().parents[1]
    app = Flask(__name__, template_folder=str(base_path / 'templates'), static_folder=str(base_path / 'static'))
    app.add_url_rule('/', endpoint='routes.revision_flexo', view_func=lambda: '')
    with app.app_context():
        with app.test_request_context():
            html = render_template(
                'resultado_flexo.html',
                imagen_path_web='dummy.png',
                advertencias_iconos=[{'tipo': 'texto_pequeno', 'pos': [0, 0], 'mensaje': None}],
                resumen='',
                tabla_riesgos='',
                imagen_iconos_web='dummy.png',
            )
    assert 'Advertencia sin descripción detallada.' in html
