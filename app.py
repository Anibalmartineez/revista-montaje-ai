import os
from flask import Flask

app = Flask(__name__)

import routes  # noqa: E402, F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
